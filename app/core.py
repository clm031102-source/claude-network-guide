"""Read-only probes. Missing observations never count as successful checks.

Only explicit scan/launch actions call the network. No account files, browser
profiles, credentials, proxy control APIs or operating-system settings are read
or changed. Each scan has a wall-clock deadline, including DNS resolution.
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

DEFAULT_CONFIG = {
    "expected_ip": "", "proxy_url": "http://127.0.0.1:7897", "claude_path": "",
    "residential_ip_confirmed": False, "require_tun": True, "require_udp": False,
}
PROBE_TIMEOUT = 4.0
SCAN_DEADLINE = 12.0
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


def probe_asn(proxy_url: str) -> dict:
    data = json.loads(fetch_text("https://ipinfo.io/json", proxy_url))
    return {"ip": str(ipaddress.ip_address(data["ip"])), "org": clean_text(data.get("org", "未知"), 160),
            "country": clean_text(data.get("country", "未知"), 12)}


def validate_claude_path(value: str) -> Path:
    if not value:
        raise ValueError("请填写已安装的 Claude 客户端完整路径。")
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


def scan(config: dict, *, deadline: float = SCAN_DEADLINE) -> dict:
    started = time.monotonic()
    config = validate_config(config)
    proxy, expected = config["proxy_url"], config["expected_ip"]
    tasks = {"tun": probe_tun, "dns": probe_dns,
             "ipv6": lambda: probe_ip("https://api6.ipify.org/"),
             "claude_path": lambda: str(validate_claude_path(config["claude_path"]))}
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
    if proxy:
        tasks["asn"] = lambda: probe_asn(proxy)
    results = run_probes(tasks, deadline)
    checks = []
    def add(name, title, status, detail, action="", blocking=False):
        checks.append({"id": name, "title": title, "status": status,
                       "detail": clean_text(detail), "action": clean_text(action), "blocking": blocking})
    add("expected_ip", "固定出口基准", "pass" if expected else "fail",
        f"已配置预期公网 IPv4：{expected}" if expected else "尚未配置购买后核对的固定出口 IPv4。",
        "从服务商订单与独立查询中核对实际住宅出口，再填写。", True)
    add("residential_purchase", "自行购买住宅 IP 的声明", "warning" if config["residential_ip_confirmed"] else "fail",
        "你已声明自行购买；程序无法证明住宅属性、独享性、滥用历史或平台许可。" if config["residential_ip_confirmed"] else "尚未确认自行购买固定住宅 IP。",
        "保留订单，核实固定、独享、住宅/ISP、换 IP 条款及合法用途。", not config["residential_ip_confirmed"])
    for name, title in (("proxy", "显式 HTTP 代理出口"), ("default", "系统 TCP 默认通道出口")):
        observed = [results.get(f"{name}_{index}", {"ok": False}) for index in range(len(IP_SERVICES))]
        ips = [item["value"] for item in observed if item["ok"]]
        if any(ip != expected for ip in ips) and expected:
            status, detail = "fail", f"观测到 {', '.join(sorted(set(ips)))}，与预期 {expected} 不一致。"
        elif not expected or (name == "proxy" and not proxy):
            status, detail = "fail", "缺少预期出口或显式代理配置，不能验证出口。"
        elif len(ips) < len(IP_SERVICES):
            status, detail = "unknown", f"仅获得 {len(ips)}/{len(IP_SERVICES)} 个有效出口样本；失败或超时不能视为通过。"
        else:
            status, detail = "pass", f"两个独立 HTTPS 查询均返回预期出口 {expected}。"
        if name == "default":
            detail += " 本样本不读取 HTTP_PROXY/系统应用代理，依赖操作系统路由；并非 Claude 进程流量证明。"
        add(name + "_egress", title, status, detail, "核对本地代理端口、TUN、规则及住宅出口。", True)
    tun = results["tun"]
    if not tun["ok"]:
        status, detail = "unknown", "无法取得完整的进程和活动网卡证据。"
    elif tun["value"]["processes"] and tun["value"]["adapters"]:
        status, detail = "pass", "运行进程：" + ", ".join(tun["value"]["processes"][:5]) + "；活动虚拟网卡：" + ", ".join(tun["value"]["adapters"][:4]) + "。名称匹配仅为证据，实际路由仍须结合出口比较。"
    else:
        status, detail = "unknown", "未同时找到已知代理进程及活动 TUN/VPN 网卡；自定义客户端或名称可能无法识别。"
    add("tun", "TUN 进程与网卡证据", status, detail, "开启所用代理客户端的 TUN，核对活动网卡和路由。", config["require_tun"])
    target_keys = [key for key in tasks if key.startswith("target_")]
    success = sum(results[key]["ok"] for key in target_keys)
    target_status = "pass" if proxy and success == len(TARGETS) * 2 else "unknown"
    add("target_tls", "Claude 相关域名的 TLS 可达性", target_status,
        f"{success}/{len(TARGETS) * 2} 项证书与主机名校验成功（显式代理及系统通道）。目标：{', '.join(TARGETS)}。仅证明 TLS 连通，不代表登录、账号资格或服务功能可用。",
        "检查目标域名的代理规则、DNS 解析和网络连通性。", True)
    dns = results["dns"]
    detail = "本地解析无有效响应，尚未验证。"
    if dns["ok"] and dns["value"]:
        fake = any(ipaddress.ip_address(ip) in ipaddress.ip_network("198.18.0.0/15") for ip in dns["value"])
        detail = f"本地解析样本：{', '.join(dns['value'])}。" + ("包含 fake-IP。" if fake else "未观察到 fake-IP。")
    add("dns", "DNS 路径证据边界", "unknown", detail + " 本地 A 记录或 fake-IP 均不能证明上游 DNS 经由代理；上游 DNS 泄漏未验证。",
        "结合代理运行配置、DNS 连接记录或独立受控域名测试核对上游。")
    udp_ips = [results[f"stun_{i}"]["value"] for i in range(len(STUN_SERVERS)) if results[f"stun_{i}"]["ok"]]
    udp_mismatch = bool(expected and any(ip != expected for ip in udp_ips))
    if udp_mismatch:
        status, detail = "fail", f"UDP 样本出口 {', '.join(sorted(set(udp_ips)))} 与预期不一致。"
    elif len(udp_ips) == len(STUN_SERVERS) and expected:
        status, detail = "pass", f"收到 {len(udp_ips)}/{len(STUN_SERVERS)} 个有效样本，已响应样本均匹配预期出口。"
    elif udp_ips and expected:
        status, detail = "unknown", f"仅收到 {len(udp_ips)}/{len(STUN_SERVERS)} 个有效样本，已响应样本匹配预期出口；其余目标未验证，不能整体判为通过。"
    else:
        status, detail = "unknown", "没有取得可比较的 UDP/STUN 出口；无响应不等于 UDP 已封禁或没有泄漏。"
    add("udp", "UDP / STUN 出口样本", status, detail + " 这不是浏览器 WebRTC 全面测试。",
        "核对 UDP 路由，并按实际使用场景另行测试浏览器 WebRTC。", config["require_udp"] or udp_mismatch)
    v6 = results["ipv6"]
    if v6["ok"]:
        status, detail, blocking = "fail", f"IPv6 专用查询返回 {v6['value']}；当前只配置 IPv4 基准，不能确认此额外通道的出口策略。", True
    else:
        status, detail, blocking = "unknown", "IPv6 专用查询未取得有效出口；无法区分不可用、被阻断、DNS 或服务超时，未验证 IPv6。", False
    add("ipv6", "IPv6 额外出口", status, detail, "按需核查 IPv6 路由与代理支持；程序不会修改 IPv6 设置。", blocking)
    asn = results.get("asn", {"ok": False})
    asn_mismatch = bool(asn["ok"] and expected and asn["value"]["ip"] != expected)
    if asn["ok"]:
        detail = f"查询返回 {asn['value']['ip']} / {asn['value']['org']} / {asn['value']['country']}。"
        if asn_mismatch:
            detail += "已观察到该查询出口与预期不一致，已阻止启动；不能用于认证预期 IP。"
    else:
        detail = "ASN 服务无有效结果。"
    add("asn", "ASN / 网络归属参考", "fail" if asn_mismatch else "warning" if asn["ok"] else "unknown",
        detail + " ASN 名称不证明住宅、独享、信誉或平台许可。",
        "核对 ipinfo.io 的路由规则和代理出口。" if asn_mismatch else "", asn_mismatch)
    try:
        language = locale.getlocale()[0] or "未知"
    except ValueError:
        language = "未知"
    add("locale", "时区与语言提示", "warning", f"系统时区标签：{', '.join(time.tzname)}；区域语言：{language}。仅用于解释环境，不是账号安全评分或准入条件。")
    path = results["claude_path"]
    add("claude_path", "Claude 本地客户端校验", "pass" if path["ok"] else "unknown",
        "本地安装路径与 Anthropic 发布者签名校验通过。" if path["ok"] else "未确认有效的 Claude 安装路径和 Anthropic 发布者签名；路径缺失、不支持的平台、签名失败或超时均不能通过。Windows 商店版可能采用包签名，本工具未确认其文件签名时会保守阻断，不表示软件有问题。",
        "填写官方安装的 Claude 客户端完整路径。只接受本地文件路径，不接受 file://、ms-appx:、启动 URI 或命令。", True)
    summary = {status: sum(check["status"] == status for check in checks) for status in ("pass", "warning", "fail", "unknown")}
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "summary": summary,
            "can_launch": not any(check["blocking"] and check["status"] != "pass" for check in checks),
            "checks": checks, "duration_ms": round((time.monotonic() - started) * 1000)}


def redact_export(report: dict | None) -> dict:
    """Exclude configuration and hide all IP literals from shared reports."""
    if report is None:
        return {"report": None, "notice": "尚无检测报告。"}
    result = json.loads(json.dumps(report, ensure_ascii=False))
    for check in result["checks"]:
        for field in ("detail", "action"):
            text = clean_text(check[field])
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
