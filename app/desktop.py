"""Native Windows shell for the existing, loopback-only workbench.

The web page owns the automatic scan. This module starts no second scan and
provides no Python/JavaScript bridge. pywebview is imported only for GUI use.
"""
from __future__ import annotations

import argparse
import ctypes
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import tempfile
import threading
from urllib.parse import urlsplit
import webbrowser

from . import core
from .server import LocalServer, State, default_config_path

TITLE = "Claude 本机体检"
WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"


def web_root() -> Path:
    """__file__ is set to the bundle location by modern PyInstaller."""
    return Path(__file__).resolve().parent / "web"


class WorkbenchServer:
    """Own exactly one ephemeral listener, with deterministic teardown."""

    def __init__(self, config_path: Path | None = None):
        self.server = LocalServer(0, config_path=config_path, web_root=web_root())
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.1}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self.server

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


def navigation_action(url: str, base_url: str) -> str:
    """Only our exact loopback origin stays embedded; web links go outside."""
    if url == "about:blank":
        return "allow"
    if url.startswith("blob:"):
        return "allow" if navigation_action(url[5:], base_url) == "allow" else "block"
    try:
        target, base = urlsplit(url), urlsplit(base_url)
        if target.username is not None or target.password is not None:
            return "block"
        if (target.scheme, target.hostname, target.port) == (base.scheme, base.hostname, base.port):
            return "allow"
        if target.scheme in {"http", "https"} and target.hostname:
            return "external"
    except (ValueError, TypeError):
        pass
    return "block"


class NavigationGuard:
    """Attach before WebView2 displays its first document.

    The native hooks are deliberately specific to the pinned pywebview Windows
    renderer. All navigations are checked before content/bridge injection.
    """

    def __init__(self, window, base_url: str):
        self.window, self.base_url = window, base_url
        self.control = None
        self.popup_hooked = False
        self.error = False

    def navigate(self, _sender, args):
        action = navigation_action(str(args.Uri), self.base_url)
        if self.error or action != "allow":
            args.Cancel = True
        if not self.error and action == "external":
            webbrowser.open(str(args.Uri), new=2)

    def popup(self, _sender, args):
        args.Handled = True
        if not self.error and navigation_action(str(args.Uri), self.base_url) == "external":
            webbrowser.open(str(args.Uri), new=2)

    def initialized(self, _sender=None, _args=None):
        if _args is not None and not _args.IsSuccess:
            self.error = True
            self.window.native.Close()
            return
        if self.popup_hooked or self.control.CoreWebView2 is None:
            return
        try:
            native = self.window.native
            self.control.CoreWebView2.NewWindowRequested -= native.browser.on_new_window_request
            self.control.CoreWebView2.NewWindowRequested += self.popup
            self.popup_hooked = True
        except Exception:
            self.error = True
            self.control.Stop()
            native.Close()

    def attach(self):
        try:
            self.control = self.window.native.webview
            self.control.NavigationStarting += self.navigate
            self.control.CoreWebView2InitializationCompleted += self.initialized
            self.initialized()
        except Exception:
            self.error = True
            # Do not leave an unguarded view open if a renderer API changes.
            self.window.native.Close()


def webview2_installed() -> bool:
    """Read Microsoft's runtime registration; never install/update it here."""
    if sys.platform != "win32":
        return False
    import winreg
    runtime_key = r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(hive, runtime_key, 0, winreg.KEY_READ | view) as client:
                    version = tuple(int(part) for part in str(winreg.QueryValueEx(client, "pv")[0]).split("."))
                    if version >= (86, 0, 622, 0):
                        return True
            except (OSError, ValueError):
                continue
    return False


def dotnet_framework_available() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full") as key:
            return int(winreg.QueryValueEx(key, "Release")[0]) >= 394802
    except (OSError, ValueError):
        return False


def show_error(message: str):
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, message, TITLE, 0x10)
    elif sys.stderr:
        print(message, file=sys.stderr)


def write_json(path: Path, value: dict):
    """Atomic, local report; never include config or traceback details."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.parent / (".desktop-report-" + secrets.token_hex(8) + ".tmp")
    try:
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def self_test() -> dict:
    """Read our packaged assets/API without loading JS or probing the Internet."""
    for name in ("index.html", "app.js", "style.css"):
        if not (web_root() / name).is_file():
            raise RuntimeError("missing bundled UI resource")
    renderer_libraries = None
    if getattr(sys, "frozen", False) and sys.platform == "win32":
        # Load managed assemblies only: no native window, user profile or scan.
        from webview.platforms import edgechromium
        renderer_libraries = edgechromium.renderer == "edgechromium"
    with tempfile.TemporaryDirectory(prefix="claude-workbench-test-") as folder:
        config = Path(folder) / "config.json"
        with WorkbenchServer(config) as server:
            port = server.server_port
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            for path in ("/", "/style.css", "/app.js", "/api/config", "/api/status"):
                connection.request("GET", path, headers={"X-Session-Token": server.session_token})
                response = connection.getresponse()
                body = response.read()
                if response.status != 200 or not body:
                    raise RuntimeError("bundled resource/API unavailable")
                if path == "/" and (b"__SESSION_TOKEN__" in body or server.session_token.encode() not in body):
                    raise RuntimeError("session token not initialized")
            connection.close()
            if server.state.running or server.state.report is not None or config.exists():
                raise RuntimeError("self-test unexpectedly mutated state")
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("owned listener was not released")
    return {"ok": True, "resources": True, "loopback_api": True,
            "server_stopped": True, "network_scan": False, "claude_launched": False,
            "webview2_available": webview2_installed(), "renderer_libraries": renderer_libraries}


def scan_report(path: Path, config_path: Path | None = None):
    state = State(config_path or default_config_path())
    report = core.scan(dict(state.config))
    write_json(path, core.redact_export(report))


def run_gui(config_path: Path | None = None) -> int:
    if sys.platform != "win32":
        show_error("此桌面包用于 Windows。其他系统请使用仓库中的启动入口。")
        return 1
    if not dotnet_framework_available():
        show_error("此程序需要 Windows 的 .NET Framework 4.6.2 或更新版本。\n"
                   "请通过 Windows 更新或微软官方安装程序补齐后重新打开。")
        return 1
    if not webview2_installed():
        show_error("缺少 Microsoft Edge WebView2 Runtime，无法显示体检窗口。\n"
                   "请从微软官方页面安装后重新打开本程序：\n" + WEBVIEW2_URL)
        return 1
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.settings["ALLOW_FILE_URLS"] = False
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    webview.settings["IGNORE_SSL_ERRORS"] = False
    with WorkbenchServer(config_path) as server:
        window = webview.create_window(TITLE, server.base_url, width=1220, height=850,
                                       min_size=(960, 640), text_select=True)
        guard = NavigationGuard(window, server.base_url)
        window.events.before_show += guard.attach
        webview.start(gui="edgechromium", debug=False, private_mode=True)
        if guard.error:
            show_error("桌面窗口初始化失败，已安全关闭。请重新下载完整便携包。")
            return 1
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=TITLE)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--self-test", action="store_true", help="仅验证本机资源和自有服务")
    modes.add_argument("--scan-report", type=Path, help="无界面运行只读体检并保存脱敏 JSON")
    parser.add_argument("--self-test-output", type=Path, help="保存自测结果")
    parser.add_argument("--config", type=Path, help="使用指定的本地配置文件")
    args = parser.parse_args(argv)
    if args.self_test_output and not args.self_test:
        parser.error("--self-test-output requires --self-test")
    try:
        if args.self_test:
            result = self_test()
            if args.self_test_output:
                write_json(args.self_test_output, result)
            return 0
        if args.scan_report:
            scan_report(args.scan_report, args.config)
            return 0
        return run_gui(args.config)
    except Exception:
        if args.self_test_output:
            write_json(args.self_test_output, {"ok": False, "error": "桌面自测未完成。"})
        elif not args.scan_report and not args.self_test:
            show_error("程序未能正常启动。请确认已完整解压程序包并安装 WebView2。")
        return 1
