"""Loopback-only, session-protected local UI and API (Python standard library)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import webbrowser

from . import core

BODY_LIMIT = 8192
STATIC_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
                "/index.html": ("index.html", "text/html; charset=utf-8"),
                "/style.css": ("style.css", "text/css; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8")}


def default_config_path() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "claude-network-guide/config.json"
    return Path.home() / ".config/claude-network-guide/config.json"


class State:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.lock = threading.Lock()
        self.config = dict(core.DEFAULT_CONFIG)
        self.report = None
        self.running = False
        self.config_error = None
        try:
            if config_path.exists():
                if config_path.stat().st_size > BODY_LIMIT:
                    raise ValueError("configuration too large")
                self.config = core.validate_config(json.loads(config_path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            # Preserve the original file. An invalid config never grants launch.
            self.config_error = "已保存配置无法读取，当前使用默认值；请在界面重新核对并保存。"

    def save_config(self, config: dict):
        with self.lock:
            if self.running:
                raise RuntimeError("检测或启动正在进行，请稍后保存配置。")
            parent = self.config_path.parent
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = parent / (".config-" + secrets.token_hex(8) + ".tmp")
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    json.dump(config, stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.config_path)
            finally:
                temporary.unlink(missing_ok=True)
            self.config = config
            self.config_error = None
            self.report = None  # A previous configuration's report is invalid.

    def begin(self) -> dict | None:
        with self.lock:
            if self.running:
                return None
            self.running = True
            self.report = None  # Never show a stale launch permission during work.
            return dict(self.config)

    def finish(self, report: dict):
        with self.lock:
            self.report = report
            self.running = False

    def snapshot(self) -> dict:
        with self.lock:
            return {"running": self.running, "report": self.report}


def failed_report() -> dict:
    return {"timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {"pass": 0, "warning": 0, "fail": 0, "unknown": 1},
            "can_launch": False, "duration_ms": 0,
            "checks": [{"id": "internal", "title": "检测未完成", "status": "unknown",
                        "detail": "检测发生内部错误，未取得完整证据；已阻止启动。",
                        "action": "稍后重试或在项目中报告已脱敏的错误。", "blocking": True}]}


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int, config_path: Path | None = None, web_root: Path | None = None):
        self.state = State(config_path or default_config_path())
        self.session_token = secrets.token_urlsafe(32)
        self.web_root = web_root or Path(__file__).parent / "web"
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server_port}"


class Handler(BaseHTTPRequestHandler):
    server: LocalServer
    server_version = "LocalNetworkGuide"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def log_message(self, format, *args):
        # Request paths, headers and config values are deliberately not logged.
        pass

    def _respond(self, status: int, payload: bytes, content_type: str, *, attachment=False):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; connect-src 'self'")
        self.send_header("Connection", "close")
        if attachment:
            self.send_header("Content-Disposition", 'attachment; filename="network-preflight-redacted.json"')
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, status: int, value: dict, *, attachment=False):
        self._respond(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", attachment=attachment)

    def _guard(self, *, api=False) -> bool:
        hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        host_headers = self.headers.get_all("Host", [])
        if len(host_headers) != 1 or host_headers[0] not in hosts:
            self._json(403, {"error": "只接受本机面板地址。"})
            return False
        origins = self.headers.get_all("Origin", [])
        if len(origins) > 1 or (origins and origins[0] != "http://" + host_headers[0]):
            self._json(403, {"error": "拒绝跨来源请求。"})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._json(403, {"error": "拒绝跨站请求。"})
            return False
        if api:
            tokens = self.headers.get_all("X-Session-Token", [])
            if len(tokens) != 1 or not hmac.compare_digest(tokens[0].encode("utf-8"), self.server.session_token.encode("ascii")):
                self._json(403, {"error": "本地会话已失效，请重新打开面板。"})
                return False
        return True

    def _body(self) -> dict | None:
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) > 1:
            self._json(400, {"error": "不接受流式或重复长度的请求。"})
            return None
        try:
            length = int(lengths[0]) if lengths else 0
            if length < 0:
                raise ValueError()
        except ValueError:
            self._json(400, {"error": "请求长度无效。"})
            return None
        if length > BODY_LIMIT:
            self._json(413, {"error": "请求过大。"})
            return None
        if not length:
            return {}
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "请使用 JSON 请求。"})
            return None
        try:
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError()
            value = json.loads(data.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (UnicodeError, ValueError, OSError):
            self._json(400, {"error": "JSON 请求无效。"})
            return None

    def do_GET(self):
        api = self.path.startswith("/api/")
        if not self._guard(api=api):
            return
        if self.path == "/api/config":
            with self.server.state.lock:
                value = {"config": dict(self.server.state.config)}
                if self.server.state.config_error:
                    value["warning"] = self.server.state.config_error
            self._json(200, value)
        elif self.path == "/api/status":
            self._json(200, self.server.state.snapshot())
        elif self.path == "/api/export":
            self._json(200, core.redact_export(self.server.state.snapshot()["report"]), attachment=True)
        elif self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            try:
                payload = (self.server.web_root / filename).read_bytes()
                if filename == "index.html":
                    payload = payload.replace(b"__SESSION_TOKEN__", self.server.session_token.encode("ascii"))
                self._respond(200, payload, content_type)
            except OSError:
                self._json(404, {"error": "界面文件不存在，请检查项目文件是否完整。"})
        else:
            self._json(404, {"error": "不存在此路径。"})

    def do_POST(self):
        if not self._guard(api=True):
            return
        if self.path not in ("/api/config", "/api/scan", "/api/launch"):
            self._json(404, {"error": "不存在此接口。"})
            return
        body = self._body()
        if body is None:
            return
        if self.path == "/api/config":
            try:
                config = core.validate_config(body)
                self.server.state.save_config(config)
                self._json(200, {"config": config})
            except ValueError as error:
                self._json(400, {"error": core.clean_text(error)})
            except RuntimeError as error:
                self._json(409, {"error": core.clean_text(error)})
            except OSError:
                self._json(500, {"error": "本地配置保存失败，请检查用户目录权限。"})
            return
        if body:
            self._json(400, {"error": "此操作不接受额外参数。"})
            return
        config = self.server.state.begin()
        if config is None:
            self._json(409, {"error": "检测或启动正在进行，请等待当前操作完成。", **self.server.state.snapshot()})
            return
        if self.path == "/api/scan":
            threading.Thread(target=self._background_scan, args=(config,), daemon=True).start()
            self._json(202, {"running": True})
            return
        # A launch always uses a new full scan while config changes are locked.
        try:
            report = core.scan(config)
            if report["can_launch"] is not True:
                self.server.state.finish(report)
                self._json(409, {"error": "关键检查未通过，已阻止启动。", "report": report})
                return
            try:
                # Use this scan's freshly discovered installation, never a stale
                # browser field or an installation path from a previous scan.
                resolved = report.get("resolved_config", config)
                core.launch_claude(resolved["claude_path"])
            except Exception:
                for check in report["checks"]:
                    if check["id"] == "claude_path":
                        old_status = check["status"]
                        check.update(status="unknown", detail="启动前再次校验或操作系统启动失败，未确认启动成功。", blocking=True)
                        report["summary"][old_status] -= 1
                        report["summary"]["unknown"] += 1
                report["can_launch"] = False
                self.server.state.finish(report)
                self._json(409, {"error": "客户端启动失败。", "report": report})
                return
            self.server.state.finish(report)
            self._json(200, {"launched": True, "report": report})
        except Exception:
            report = failed_report()
            self.server.state.finish(report)
            self._json(500, {"error": "检测未完成，已阻止启动。", "report": report})

    def _background_scan(self, config):
        try:
            report = core.scan(config)
        except Exception:
            report = failed_report()
        self.server.state.finish(report)

    def do_OPTIONS(self):
        self._json(403, {"error": "不允许跨来源访问。"})


def main(argv=None):
    parser = argparse.ArgumentParser(description="只读网络检测与 Claude 启动前检查；仅监听本机。")
    parser.add_argument("--port", type=int, default=None, help="指定本机端口；省略时依次尝试 8765–8774")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args(argv)
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("端口必须介于 1 和 65535。")
    server = None
    for port in (range(8765, 8775) if args.port is None else (args.port,)):
        try:
            server = LocalServer(port)
            break
        except OSError:
            continue
    if server is None:
        parser.exit(1, "本机端口不可用，请用 --port 选择其他端口；已有面板不会被结束。\n")
    print(f"本地面板：{server.base_url}\n按 Ctrl+C 关闭。打开界面后自动体检一次；只读取本机配置并请求固定检测目标。")
    if not args.no_browser:
        webbrowser.open(server.base_url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
