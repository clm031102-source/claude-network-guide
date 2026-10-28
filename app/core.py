"""Read-only probes. Missing observations never count as successful checks.

Scan/launch actions call the network and read relevant local network settings.
No account files, browser profiles or operating-system settings are changed.
Local controller authentication stays in memory and is never reported.
Each scan has a wall-clock deadline, including discovery and DNS resolution.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import locale
import os
from pathlib import Path
import platform
import queue
import re
import secrets
import socket
import ssl
import struct
import subprocess
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from . import discovery

DEFAULT_CONFIG = {
    "expected_ip": "", "proxy_url": "", "claude_path": "",
    "residential_ip_confirmed": False, "require_tun": True, "require_udp": False,
}
PROBE_TIMEOUT = 4.0
SCAN_DEADLINE = 25.0
MAX_RESPONSE = 16384
TARGETS = ("claude.ai", "api.anthropic.com", "s-cdn.anthropic.com")
IP_SERVICES = ("https://www.cloudflare.com/cdn-cgi/trace", "https://api.ipify.org/")
STUN_SERVERS = (("stun.cloudflare.com", 3478), ("stun.l.google.com", 19302))
_PROXY_NAMES = r"mihomo|sing-box|clash|wireguard|openvpn|tailscale|surge|v2ray|xray"
_TUN_NAMES = r"\btun\b|utun|tap|wintun|wireguard|vpn|tailscale|mihomo|clash|meta"
_PROBE_SLOTS = threading.BoundedSemaphore(40)


def validate_config(value: object) -> dict:
    if not isinstance(value, dict) or set(value) - set(DEFAULT_CONFIG):
        raise ValueError("配置只能包含界面列出的字段。")
    result = dict(DEFAULT_CONFIG)
    result.update(value)
    for key in ("residential_ip_confirmed", "require_tun", "require_udp"):
        if type(result[key]) is not bool:
            raise ValueError(f"{key} 必须是布尔值。")
    for key in ("expected_ip", "proxy_url", "claude_path"):
        if not isinstance(result[key], str) or len(result[key]) > 1024:
            raise ValueError(f"{key} 格式或长度无效。")
        result[key] = result[key].strip()
        if any(ord(char) < 32 or ord(char) == 127 for char in result[key]):
            raise ValueError("配置不能包含控制字符。")
    if result["expected_ip"]:
        try:
            address = ipaddress.ip_address(result["expected_ip"])
            if address.version != 4 or not address.is_global or address.is_multicast or address.is_reserved:
                raise ValueError()
        except ValueError:
            raise ValueError("预期出口必须是购买后确认的公网 IPv4 地址。") from None
        result["expected_ip"] = str(address)
    if result["proxy_url"]:
        parse_proxy(result["proxy_url"])
    return result


def parse_proxy(value: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or not parsed.hostname or parsed.port is None
                or not 1 <= parsed.port <= 65535 or parsed.username is not None
                or parsed.password is not None or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or any(c.isspace() for c in value)
                or "\\" in value or "%" in parsed.hostname):
            raise ValueError()
        return parsed.hostname, parsed.port
    except ValueError:
        raise ValueError("代理须为 http://主机:端口；不支持凭证、SOCKS、路径或查询参数。") from None


def clean_text(value: object, limit: int = 1200) -> str:
    text = str(value)
    text = re.sub(r"(?i)(?:bearer\s+|sk-(?:ant-)?)[A-Za-z0-9_\-.]+", "[已隐藏凭证]", text)
    text = re.sub(r"(?i)(token|password|secret|authorization)\s*[=:]\s*[^\s,;]+", r"\1=[已隐藏]", text)
    text = re.sub(r"https?://[^\s/@]+:[^\s/@]+@", "http://[已隐藏]@", text)
    return "".join(c for c in text if c in "\n\t" or ord(c) >= 32)[:limit]


def _connection(host: str, proxy_url: str | None = None) -> http.client.HTTPSConnection:
    context = ssl.create_default_context()
    if proxy_url:
        proxy_host, proxy_port = parse_proxy(proxy_url)
        conn = http.client.HTTPSConnection(proxy_host, proxy_port, timeout=PROBE_TIMEOUT, context=context)
        conn.set_tunnel(host, 443)
        return conn
    # Deliberately ignore HTTP(S)_PROXY, NO_PROXY and WinINET. This is a sample
    # of system TCP routing, not a claim about a particular app's proxy policy.
    return http.client.HTTPSConnection(host, 443, timeout=PROBE_TIMEOUT, context=context)


def fetch_text(url: str, proxy_url: str | None = None) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS probe endpoints are supported")
    conn = _connection(parsed.hostname, proxy_url)
    try:
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        conn.request("GET", path, headers={"User-Agent": "claude-network-guide/0.1", "Accept": "text/plain, application/json"})
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("probe response exceeds limit")
        return raw.decode("utf-8", errors="replace")
    finally:
        conn.close()


def probe_ip(url: str, proxy_url: str | None = None) -> str:
    text = fetch_text(url, proxy_url).strip()
    if "cdn-cgi/trace" in url:
        text = next((line[3:] for line in text.splitlines() if line.startswith("ip=")), "")
    address = ipaddress.ip_address(text)
    if not address.is_global or address.is_multicast or address.is_reserved:
        raise ValueError("response is not a public address")
    return str(address)


def probe_tls(host: str, proxy_url: str | None = None) -> str:
    conn = _connection(host, proxy_url)
    try:
        conn.connect()  # Default TLS context verifies certificate and hostname.
        return "证书与主机名校验成功"
    finally:
        conn.close()


def parse_stun(data: bytes, transaction: bytes) -> str | None:
    if len(data) < 20 or len(transaction) != 12:
        return None
    kind, length, cookie = struct.unpack("!HHI", data[:8])
    if (kind != 0x0101 or cookie != 0x2112A442 or data[8:20] != transaction
            or length % 4 or length != len(data) - 20):
        return None
    offset = 20
    while offset + 4 <= len(data):
        attr, size = struct.unpack("!HH", data[offset:offset + 4])
        end = offset + 4 + size
        if end > len(data):
            return None
        payload = data[offset + 4:end]
        if attr in (0x0001, 0x0020) and size == 8 and payload[1] == 1:
            raw = struct.unpack("!I", payload[4:8])[0]
            if attr == 0x0020:
                raw ^= 0x2112A442
            address = ipaddress.IPv4Address(raw)
            return str(address) if address.is_global and not address.is_multicast and not address.is_reserved else None
        offset = end + ((4 - size % 4) % 4)
    return None


def probe_stun(host: str, port: int) -> str:
    address = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
    transaction = secrets.token_bytes(12)
    packet = struct.pack("!HHI", 1, 0, 0x2112A442) + transaction
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.settimeout(PROBE_TIMEOUT)
        udp.connect(address)  # Ignore packets from unrelated source addresses.
        udp.send(packet)
        data = udp.recv(2048)
    observed = parse_stun(data, transaction)
    if not observed:
        raise ValueError("STUN response invalid or missing a public mapped address")
    return observed


def _run(command: list[str], timeout: float = 5.0, env: dict | None = None) -> str:
    options = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace",
               "timeout": timeout, "check": True, "env": env}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    completed = subprocess.run(command, **options)
    return completed.stdout[:32768]


def probe_tun() -> dict:
    system = platform.system()
    if system == "Windows":
        script = (
            "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; "
            "$p=@(Get-Process | Select-Object -ExpandProperty ProcessName); "
            "$a=@(Get-NetAdapter | Where-Object Status -eq 'Up' | "
            "ForEach-Object { $_.Name+' '+$_.InterfaceDescription }); "
            "@{processes=$p;adapters=$a}|ConvertTo-Json -Compress"
        )
        result = json.loads(_run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]))
        processes, adapters = result["processes"], result["adapters"]
    elif system == "Linux":
        processes = _run(["ps", "-A", "-o", "comm="]).splitlines()
        links = json.loads(_run(["ip", "-j", "link", "show"]))
        adapters = [link["ifname"] for link in links if "UP" in link.get("flags", [])]
    elif system == "Darwin":
        processes = _run(["ps", "-A", "-o", "comm="]).splitlines()
        text = _run(["/sbin/ifconfig"])
        adapters = [line.split(":", 1)[0] for line in text.splitlines()
                    if line and not line[0].isspace() and "UP" in line]
    else:
        raise RuntimeError("unsupported adapter inspection platform")
    return {"processes": [clean_text(Path(item).name, 80) for item in processes
                          if re.search(_PROXY_NAMES, item, re.I)],
            "adapters": [clean_text(item, 120) for item in adapters
                         if re.search(_TUN_NAMES, item, re.I)]}


def probe_dns() -> list[str]:
    return sorted({record[4][0] for record in socket.getaddrinfo("claude.ai", 443, socket.AF_INET)})[:8]


def probe_asn(proxy_url: str | None) -> dict:
    data = json.loads(fetch_text("https://ipinfo.io/json", proxy_url))
    return {"ip": str(ipaddress.ip_address(data["ip"])), "org": clean_text(data.get("org", "未知"), 160),
            "country": clean_text(data.get("country", "未知"), 12)}


def validate_claude_path(value: str) -> Path:
    if not value:
        raise ValueError("尚未发现已安装的 Claude 客户端。")
    supplied = Path(value).expanduser()
    if not supplied.is_absolute() or str(supplied).startswith(("\\\\", "//")):
        raise ValueError("只能使用本机绝对路径，不能使用网络路径或命令。")
    path = supplied.resolve(strict=True)
    system = platform.system()
    if system == "Windows":
        if path.name.lower() != "claude.exe" or not path.is_file() or str(path).startswith("\\\\"):
            raise ValueError("Windows 仅允许本机 Claude.exe 文件。")
        with path.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise ValueError("不是 Windows 可执行文件。")
        env = os.environ.copy()
        env["NETWORK_GUIDE_CLAUDE_PATH"] = str(path)
        script = ("$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                  "Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1'); "
                  "$s=Get-AuthenticodeSignature -LiteralPath $env:NETWORK_GUIDE_CLAUDE_PATH; "
                  "@{status=[string]$s.Status;subject=[string]$s.SignerCertificate.Subject}|ConvertTo-Json -Compress")
        signature = json.loads(_run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], env=env))
        if signature.get("status") != "Valid" or not re.search(r"(?:^|,\s*)(?:CN|O)=\"?Anthropic(?:,? PBC|,? Inc\.?)?\"?(?:,|$)", signature.get("subject", ""), re.I):
            raise ValueError("未验证到有效的 Anthropic 数字签名，已阻止启动。")
    elif system == "Darwin":
        allowed = {Path("/Applications/Claude.app").resolve(), (Path.home() / "Applications/Claude.app").resolve()}
        if path not in allowed or not path.is_dir():
            raise ValueError("macOS 仅允许 /Applications/Claude.app 或 ~/Applications/Claude.app。")
        _run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(path)])
        completed = subprocess.run(["/usr/bin/codesign", "-dv", "--verbose=4", str(path)], capture_output=True,
                                   text=True, timeout=5, check=True)
        signature = completed.stderr[:16384]
        if "Identifier=com.anthropic.claudefordesktop\n" not in signature or not re.search(r"Authority=Developer ID Application: Anthropic(?:,? PBC|,? Inc\.?)? \(", signature):
            raise ValueError("未验证到 Claude 的 Anthropic 开发者签名，已阻止启动。")
    else:
        raise ValueError("此平台可以运行检测面板，但尚未提供经过验证的 Claude 客户端启动方式。")
    return path


def launch_claude(value: str) -> None:
    path = validate_claude_path(value)
    if platform.system() == "Windows":
        subprocess.Popen([str(path)], shell=False, close_fds=True)
    else:
        subprocess.Popen(["/usr/bin/open", "-a", str(path)], shell=False, close_fds=True)


def run_probes(tasks: dict, deadline: float = SCAN_DEADLINE) -> dict:
    """Bound the whole scan even when a platform DNS resolver hangs.

    Workers are daemon threads so they cannot keep application exit blocked.
    Their results are never added to an already returned report.
    """
    if deadline <= 0:
        return {name: {"ok": False, "error": "Timeout"} for name in tasks}
    results: queue.Queue = queue.Queue()
    def worker(name, function):
        try:
            results.put((name, {"ok": True, "value": function()}))
        except Exception as error:
            # Do not echo external exception text (URLs, paths, cert contents).
            results.put((name, {"ok": False, "error": type(error).__name__}))
        finally:
            _PROBE_SLOTS.release()
    started = time.monotonic()
    for name, function in tasks.items():
        if _PROBE_SLOTS.acquire(blocking=False):
            threading.Thread(target=worker, args=(name, function), daemon=True).start()
        else:
            results.put((name, {"ok": False, "error": "ProbeLimit"}))
    observed = {}
    while len(observed) < len(tasks):
        remaining = deadline - (time.monotonic() - started)
        if remaining <= 0:
            break
        try:
            name, result = results.get(timeout=remaining)
            observed[name] = result
        except queue.Empty:
            break
    for name in tasks:
        observed.setdefault(name, {"ok": False, "error": "Timeout"})
    return observed


def _resolve_claude(candidates: list[str]) -> str:
    for candidate in list(dict.fromkeys(candidates))[:4]:
        try:
            return str(validate_claude_path(candidate))
        except (ValueError, OSError, subprocess.SubprocessError):
            continue
    raise ValueError("No discovered Claude installation passed signature verification")


def scan(config: dict | None = None, *, deadline: float = SCAN_DEADLINE) -> dict:
    started = time.monotonic()
    config = validate_config(config or {})
    try:
        found = discovery.discover(config, deadline=min(discovery.DISCOVERY_BUDGET, max(0.0, deadline)))
    except Exception:
        found = {"detected": discovery.empty_detected(), "runtime": {}, "errors": ["discovery"]}
    detected = found.get("detected") or discovery.empty_detected()
    runtime = found.get("runtime", {})
    resolved = dict(config)
    resolved["proxy_url"] = config["proxy_url"] or detected.get("proxy_url", "")
    resolved["claude_path"] = config["claude_path"] or detected.get("claude_path", "")
    proxy, expected = resolved["proxy_url"], config["expected_ip"]
    paths = [resolved["claude_path"]] if resolved["claude_path"] else []
    if not config["claude_path"]:
        paths += found.get("claude_candidates", [])
    tasks = {"tun": lambda: {"processes": detected.get("clients", []), "adapters": detected.get("tun_adapters", [])},
             "dns": probe_dns, "ipv6": lambda: probe_ip("https://api6.ipify.org/"),
             "claude_path": lambda: _resolve_claude(paths)}
    for index, url in enumerate(IP_SERVICES):
        tasks[f"default_{index}"] = lambda url=url: probe_ip(url)
        if proxy:
            tasks[f"proxy_{index}"] = lambda url=url: probe_ip(url, proxy)
    for host in TARGETS:
        tasks[f"target_default_{host}"] = lambda host=host: probe_tls(host)
        if proxy:
            tasks[f"target_proxy_{host}"] = lambda host=host: probe_tls(host, proxy)
    for index, (host, port) in enumerate(STUN_SERVERS):
        tasks[f"stun_{index}"] = lambda host=host, port=port: probe_stun(host, port)
    tasks["asn"] = lambda: probe_asn(proxy or None)
    remaining = max(0.0, deadline-(time.monotonic()-started))
    results = run_probes(tasks, remaining)
    checks = []
    def add(name, title, status, detail, action="", blocking=False):
        checks.append({"id": name, "title": title, "status": status,
                       "detail": clean_text(detail), "action": clean_text(action), "blocking": blocking})
    errors = found.get("errors", [])
    add("discovery", "本机环境自动发现", "warning" if errors else "pass",
        f"已检查系统代理、网络接口、DNS、路由、运行进程及 Claude 安装信息；识别到 {len(detected.get('clients', []))} 个代理进程、{len(detected.get('tun_adapters', []))} 个活动 TUN/VPN 接口。"
        + (" 部分系统读取未完成；相关证据将保持未验证。" if errors else ""),
        "默认无需填写参数。只有自动识别不符合实际时，再使用高级覆盖。")
    samples = {name: [results.get(f"{name}_{index}", {"ok": False}) for index in range(len(IP_SERVICES))]
               for name in ("proxy", "default")}
    sample_ips = {name: [item["value"] for item in values if item["ok"]] for name, values in samples.items()}
    all_ips = sample_ips["proxy"] + sample_ips["default"]
    observed_ip = all_ips[0] if all_ips and len(set(all_ips)) == 1 else ""
    detected["observed_ip"] = observed_ip
    baseline = expected or observed_ip
    add("expected_ip", "出口比较基准", "pass" if expected else "warning",
        f"按高级设置指定的出口 {expected} 比较。" if expected else
        "未指定固定 IP，使用本轮实际出口做跨通道比较；空设置不是检测失败。单次一致不证明长期固定、住宅或独享。")
    explicit_failure = {"ConnectionRefusedError", "ConnectionResetError", "SSLCertVerificationError"}
    for name, title in (("proxy", "显式 HTTP 代理出口"), ("default", "系统 TCP 默认通道出口")):
        ips = sample_ips[name]
        if len(set(ips)) > 1 or (expected and any(ip != expected for ip in ips)):
            status, detail = "fail", f"观测到 {', '.join(sorted(set(ips)))}；服务间结果不一致或与指定基准不符。"
        elif len(ips) < len(IP_SERVICES):
            status = "fail" if any(item.get("error") in explicit_failure for item in samples[name]) else "unknown"
            detail = f"仅获得 {len(ips)}/{len(IP_SERVICES)} 个有效出口样本；实际失败或缺证据不能视为通过。"
            if name == "proxy" and not proxy:
                detail = "尚未发现可用的 HTTP/mixed 代理监听；已继续检测系统默认通道，不要求先填表。"
        else:
            status, detail = "pass", f"两个独立 HTTPS 服务均观测到 {ips[0]}。"
        if name == "default":
            detail += " 该通道不读取 HTTP 代理环境变量，依赖操作系统路由；并非 Claude 进程全流量证明。"
        else:
            detail += " 入口来源：" + (detected.get("proxy_source") or ("高级设置指定" if config["proxy_url"] else "未发现")) + "。"
        add(name+"_egress", title, status, detail, "核对正在使用的代理客户端、监听端口和实际路由。", True)
    complete = all(len(values) == len(IP_SERVICES) for values in sample_ips.values())
    if len(set(all_ips)) > 1:
        status, detail = "fail", "显式代理与系统默认通道观测到不同出口，当前路径不一致。"
    elif complete:
        status, detail = "pass", "本轮两个通道的四个 HTTPS 样本出口一致；这不认证住宅属性或所有应用的路由。"
    else:
        status, detail = "unknown", "跨通道样本不足，不能确认两条路径一致。"
    add("route_consistency", "跨通道出口一致性", status, detail, "检查 TUN、系统代理和客户端的运行时分流规则。", True)
    tun = results["tun"]
    controller = detected.get("controller", {})
    tun_enabled = controller.get("tun_enabled")
    if tun_enabled is False:
        status, detail = "fail", "已读到 Mihomo 当前运行配置：TUN 未启用。"
    elif not tun["ok"]:
        status, detail = "unknown", "无法取得完整的进程和活动网卡证据。"
    elif (tun_enabled is True and tun["value"]["adapters"] and runtime.get("tun_device")
          and any(name.casefold() == runtime["tun_device"].casefold()
                  or name.casefold().startswith(runtime["tun_device"].casefold()+" ")
                  for name in tun["value"]["adapters"])):
        status, detail = "pass", "已将所选代理监听与当前内核运行配置对应，TUN 已启用且存在对应的活动网卡证据；实际路径仍须结合出口与连接记录。"
    else:
        status, detail = "unknown", "尚未把所选代理、TUN 运行配置和活动网卡对应起来；其他 VPN 进程或网卡不能代替当前线路的证据。"
    add("tun", "TUN 当前运行状态", status, detail, "查看当前客户端的 TUN 状态及活动网卡。", config["require_tun"])
    target_keys = [key for key in tasks if key.startswith("target_")]
    success = sum(results[key]["ok"] for key in target_keys)
    target_status = "pass" if proxy and success == len(TARGETS)*2 else "unknown"
    if any(results[key].get("error") in explicit_failure for key in target_keys):
        target_status = "fail"
    add("target_tls", "Claude 相关域名的 TLS 可达性", target_status,
        f"{success}/{len(TARGETS)*2} 项证书与主机名校验成功（显式代理及系统通道）。目标：{', '.join(TARGETS)}。仅证明 TLS 连通，不代表登录、账号资格或服务功能可用。",
        "检查目标域名的实际代理规则、DNS 和网络。", True)
    if controller.get("status") == "connected":
        detail = f"已通过本机 {controller.get('transport', '')} 只读控制接口读取运行配置；当前模式 {controller.get('mode') or '未知'}。"
        status = "pass"
    else:
        detail, status = "未取得可用的本机 Mihomo 控制接口；其他网络取样继续执行。", "unknown"
    add("controller", "代理内核运行时配置", status, detail, "只读读取 /configs 与 /connections，不修改内核配置。")
    connections = runtime.get("claude_connections", [])
    if connections:
        direct = sum(item.get("direct") is True for item in connections)
        status, detail = ("warning" if direct else "pass"), f"当前内核观测到 {len(connections)} 条 Claude 相关连接，其中 {direct} 条记录为 DIRECT。仅描述现有连接，不代表已验证每条连接的最终公网出口。"
    else:
        status, detail = "unknown", "当前没有取得 Claude 实际连接记录；应用未运行或当前无连接均可能导致此结果，不会为检测而启动它。"
    add("claude_connections", "Claude 实际连接样本", status, detail, "应用正常使用时，可重新检测并核对内核记录。")
    dns = results["dns"]
    detail = f"自动发现 {len(detected.get('dns_servers', []))} 个系统 DNS 地址。"
    if dns["ok"] and dns["value"]:
        fake = any(ipaddress.ip_address(ip) in ipaddress.ip_network("198.18.0.0/15") for ip in dns["value"])
        detail += "本地解析样本：" + ", ".join(dns["value"]) + "。" + ("包含 fake-IP。" if fake else "未观察到 fake-IP。")
    else:
        detail += "本地 A 记录取样未完成。"
    dns_runtime = runtime.get("dns", {})
    if dns_runtime:
        detail += f"运行时 DNS 模式：{dns_runtime.get('enhanced_mode') or '未提供'}；respect-rules：{dns_runtime.get('respect_rules')}。"
    add("dns", "DNS 配置与证据边界", "unknown", detail+" 本地 A 记录、fake-IP 或配置声明均不能证明上游 DNS 没有旁路；完整上游路径未验证。",
        "结合当前运行配置、上游连接记录与受控查询证据判断。")
    udp_ips = [results[f"stun_{i}"]["value"] for i in range(len(STUN_SERVERS)) if results[f"stun_{i}"]["ok"]]
    udp_mismatch = len(set(udp_ips)) > 1 or bool(baseline and any(ip != baseline for ip in udp_ips))
    if udp_mismatch:
        status, detail = "fail", "UDP 样本之间或与本轮 TCP/指定基准出口不一致。"
    elif len(udp_ips) == len(STUN_SERVERS) and baseline:
        status, detail = "pass", f"两个 STUN 目标均返回与本轮比较基准一致的出口。"
    else:
        status, detail = "unknown", f"仅获得 {len(udp_ips)}/{len(STUN_SERVERS)} 个可比较 UDP/STUN 样本；部分响应或无响应均不能证明没有泄漏。"
    add("udp", "UDP / STUN 出口样本", status, detail+" 这不是浏览器 WebRTC 全面测试。",
        "按实际用途核对 UDP 路由及浏览器 WebRTC。", config["require_udp"] or udp_mismatch)
    v6 = results["ipv6"]
    if v6["ok"]:
        address = ipaddress.ip_address(v6["value"])
        if address.version == 4 and baseline == str(address):
            status, detail, blocking = "unknown", "IPv6 专用查询返回了相同 IPv4 出口，可能涉及代理或地址转换；尚不能证明本机原生 IPv6 路径。", False
        elif address.version == 4 and baseline:
            status, detail, blocking = "fail", "IPv6 专用目标返回了与当前 TCP 基准不同的 IPv4 出口。", True
        else:
            status, detail, blocking = "unknown", "已取得额外 IPv6 出口，但尚无可验证的 IPv6 路由基准；未确认该额外通道，启动暂被阻断。", True
    else:
        status, detail, blocking = "unknown", "IPv6 专用查询没有取得有效出口；可能是不可用、阻断、DNS 或服务超时，不能写成无泄漏。", False
    add("ipv6", "IPv6 配置与实际取样", status, detail, "结合系统 IPv6 路由和客户端支持情况核对；不会修改 IPv6 设置。", blocking)
    asn = results["asn"]
    asn_mismatch = bool(asn["ok"] and baseline and asn["value"]["ip"] != baseline)
    if asn["ok"]:
        detail = f"查询得到 {asn['value']['org']} / {asn['value']['country']}。"
        if asn_mismatch: detail += "该查询的实际出口与比较基准不一致。"
    else:
        detail = "网络归属服务未返回有效结果。"
    add("asn", "网络归属与住宅属性边界", "fail" if asn_mismatch else "warning" if asn["ok"] else "unknown",
        detail+" 不要求勾选采购声明；ASN 名称与单次取样都不能证明住宅、独享、长期固定或平台资格。",
        "已观察到出口差异时，检查该目标的路由规则。" if asn_mismatch else "", asn_mismatch)
    add("locale", "系统时区与语言", "warning", f"已读取系统时区 {detected.get('timezone') or '未知'}；语言 {detected.get('language') or '未知'}。仅为环境信息，不改变系统设置，也不作为账号安全评分。")
    client = results["claude_path"]
    if client["ok"]:
        resolved["claude_path"] = client["value"]
        detected["claude_path"] = client["value"]
    else:
        detected["claude_path"] = ""
    add("claude_path", "Claude 安装与发布者签名", "pass" if client["ok"] else "unknown",
        "已自动定位/核对本地 Claude，并验证 Anthropic 发布者签名。" if client["ok"] else
        "已检查运行进程、标准安装位置及商店安装信息，但尚未确认可启动且签名有效的客户端。未安装、读取受限、商店包签名差异或超时均会保持未验证；不因路径输入框为空判失败。",
        "若已安装但未识别，可在高级设置覆盖路径；不接受启动 URI、快捷方式或任意命令。", True)
    summary = {status: sum(check["status"] == status for check in checks) for status in ("pass", "warning", "fail", "unknown")}
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "summary": summary,
            "can_launch": not any(check["blocking"] and check["status"] != "pass" for check in checks),
            "checks": checks, "detected": detected, "resolved_config": resolved,
            "duration_ms": round((time.monotonic()-started)*1000)}


def redact_export(report: dict | None) -> dict:
    """Exclude configuration and hide all IP literals from shared reports."""
    if report is None:
        return {"report": None, "notice": "尚无检测报告。"}
    # Never export resolved configuration, detected paths, controller data or
    # a future raw inventory field. Export the public report schema only.
    result = json.loads(json.dumps({key: report[key] for key in
                                   ("timestamp", "summary", "can_launch", "checks", "duration_ms") if key in report}, ensure_ascii=False))
    for check in result["checks"]:
        for field in ("detail", "action"):
            text = clean_text(check[field])
            text = re.sub(r"(?i)\b[A-Z]:[\\/][^\n,;，；]+", "[本地路径已隐藏]", text)
            text = re.sub(r"/(?:Users|home)/[^\s,;，；]+", "[本地路径已隐藏]", text)
            # Candidate matching plus ipaddress validation avoids masking prose.
            def mask_v6(match):
                candidate = match.group().rstrip(".")
                try:
                    return "[IP已隐藏]" + match.group()[len(candidate):] if ipaddress.ip_address(candidate).version == 6 else match.group()
                except ValueError:
                    return match.group()
            text = re.sub(r"(?<![0-9a-zA-Z_:])[0-9a-fA-F]*:[0-9a-fA-F:.]+(?:%[a-zA-Z0-9_.-]+)?", mask_v6, text)
            # Avoid Unicode word boundaries: Chinese text can touch an address.
            text = re.sub(r"(?:\d{1,3}\.){3}\d{1,3}", "[IP已隐藏]", text)
            check[field] = text
    return {"report": result, "notice": "IP 已脱敏；不包含配置、客户端路径、账号数据或凭证。分享前仍请复核网络和网卡名称。"}
