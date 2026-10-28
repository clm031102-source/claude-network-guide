"""Bounded, read-only discovery of network settings and Claude installations.

Only known network configuration locations and installation metadata are read.
Controller credentials stay inside request workers and are never returned.
No account profiles, cookies, login files or system settings are modified.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import locale
import os
from pathlib import Path, PureWindowsPath
import platform
import queue
import re
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit

DISCOVERY_BUDGET = 10.0
MAX_CONFIG_BYTES = 524288
MAX_CONTROLLER_BYTES = 2097152
CLIENT_PATTERN = r"mihomo|sing-box|clash|wireguard|openvpn|tailscale|surge|v2ray|xray"
TUN_PATTERN = r"\btun\b|utun|tap|wintun|wireguard|vpn|tailscale|mihomo|clash|meta"
_SLOTS = threading.BoundedSemaphore(24)


def _safe_text(value, limit=160):
    value = str(value or "")
    value = re.sub(r"(?i)(?:bearer\s+|sk-(?:ant-)?)[A-Za-z0-9_.-]+", "[hidden]", value)
    value = re.sub(r"(?i)(token|password|secret|authorization)\s*[=:]\s*[^\s,;]+", r"\1=[hidden]", value)
    return "".join(char for char in value if ord(char) >= 32 and ord(char) != 127)[:limit]


def _parallel(tasks, budget):
    results = queue.Queue()
    stop = time.monotonic() + max(0.0, budget)
    def worker(name, function):
        try:
            results.put((name, {"ok": True, "value": function()}))
        except Exception as error:
            results.put((name, {"ok": False, "error": type(error).__name__}))
        finally:
            _SLOTS.release()
    for name, function in tasks.items():
        if time.monotonic() < stop and _SLOTS.acquire(blocking=False):
            threading.Thread(target=worker, args=(name, function), daemon=True).start()
        else:
            results.put((name, {"ok": False, "error": "DiscoveryLimit"}))
    observed = {}
    while len(observed) < len(tasks) and time.monotonic() < stop:
        try:
            name, value = results.get(timeout=max(0.001, stop-time.monotonic()))
            observed[name] = value
        except queue.Empty:
            break
    for name in tasks:
        observed.setdefault(name, {"ok": False, "error": "Timeout"})
    return observed


def _command(arguments, timeout=6.0):
    options = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace",
               "timeout": timeout, "check": True}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    result = subprocess.run(arguments, **options)
    if len(result.stdout) > MAX_CONFIG_BYTES:
        raise ValueError("Discovery output exceeds limit")
    return result.stdout


def normalize_proxy(value):
    """Accept usable HTTP proxy coordinates, never preserve credentials."""
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        return ""
    value = value.strip()
    if any(char.isspace() or ord(char) < 32 for char in value) or "\\" in value:
        return ""
    if "://" not in value:
        value = "http://" + value
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.port is None or not 1 <= parsed.port <= 65535
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment or "%" in parsed.hostname):
            return ""
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        return f"http://{host}:{parsed.port}"
    except ValueError:
        return ""


def environment_proxies(environ=None):
    environ = os.environ if environ is None else environ
    result = []
    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        proxy = normalize_proxy(environ.get(key, ""))
        if proxy and proxy not in [item["url"] for item in result]:
            result.append({"url": proxy, "source": "环境变量 " + key})
    return result


def parse_wininet(proxy_server, enabled=True):
    if not enabled or not isinstance(proxy_server, str):
        return []
    values = {}
    if "=" in proxy_server:
        for item in proxy_server.split(";"):
            protocol, separator, address = item.partition("=")
            if separator:
                values[protocol.strip().lower()] = address.strip()
        candidates = [values.get("https", ""), values.get("http", "")]
    else:
        candidates = [proxy_server]
    result = []
    for value in candidates:
        proxy = normalize_proxy(value)
        if proxy and proxy not in [item["url"] for item in result]:
            result.append({"url": proxy, "source": "Windows 系统代理（WinINET）"})
    return result


def wininet_settings():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
        def read(name, default=None):
            try:
                return winreg.QueryValueEx(key, name)[0]
            except OSError:
                return default
        return {"proxies": parse_wininet(read("ProxyServer", ""), bool(read("ProxyEnable", 0))),
                "pac_enabled": bool(read("AutoConfigURL", ""))}


def windows_inventory():
    # No command line arguments, account files or process memory are collected.
    script = r"""
$ErrorActionPreference='SilentlyContinue'; [Console]::OutputEncoding=[Text.Encoding]::UTF8
$p=@(Get-Process | Where-Object { $_.ProcessName -match 'mihomo|sing-box|clash|wireguard|openvpn|tailscale|surge|v2ray|xray|^claude$' } | ForEach-Object { @{name=$_.ProcessName;pid=$_.Id;path=$_.Path} })
$ids=@($p | ForEach-Object { $_.pid })
$a=@(Get-NetAdapter | Where-Object Status -eq 'Up' | ForEach-Object { @{name=$_.Name;description=$_.InterfaceDescription;index=$_.ifIndex} })
$r=@(Get-NetRoute | Where-Object { $_.DestinationPrefix -in @('0.0.0.0/0','::/0') } | ForEach-Object { @{destination=$_.DestinationPrefix;next_hop=$_.NextHop;interface=$_.InterfaceAlias;metric=$_.RouteMetric} })
$d=@(Get-DnsClientServerAddress | Where-Object { $_.ServerAddresses.Count -gt 0 -and $_.InterfaceIndex -in @($a | ForEach-Object { $_.index }) } | ForEach-Object { $_.ServerAddresses })
$l=@(Get-NetTCPConnection -State Listen | Where-Object { $_.OwningProcess -in $ids } | ForEach-Object { @{address=$_.LocalAddress;port=$_.LocalPort;pid=$_.OwningProcess} })
$v=@(Get-NetAdapterBinding -ComponentID ms_tcpip6 | Where-Object Enabled -eq $true)
$apps=@(Get-AppxPackage -Name '*Claude*' | Where-Object { $_.Publisher -match 'Anthropic' } | ForEach-Object { @{location=$_.InstallLocation;publisher=$_.Publisher;name=$_.Name} })
@{processes=$p;adapters=$a;routes=$r;dns=$d;listeners=$l;ipv6_enabled_count=$v.Count;packages=$apps;timezone=(Get-TimeZone).Id;language=(Get-Culture).Name}|ConvertTo-Json -Compress -Depth 6
"""
    return json.loads(_command(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], 7.5))


def portable_inventory():
    result = {"processes": [], "adapters": [], "routes": [], "dns": [], "listeners": [], "packages": []}
    process_names = _command(["ps", "-A", "-o", "comm="], 2).splitlines()
    result["processes"] = [{"name": Path(item).name, "path": item} for item in process_names
                           if re.search(CLIENT_PATTERN + r"|claude", item, re.I)]
    if platform.system() == "Linux":
        links = json.loads(_command(["ip", "-j", "link", "show"], 2))
        result["adapters"] = [{"name": item["ifname"], "description": ""} for item in links if "UP" in item.get("flags", [])]
        routes = json.loads(_command(["ip", "-j", "route", "show", "default"], 2))
        result["routes"] = [{"destination": "0.0.0.0/0", "next_hop": item.get("gateway", ""),
                             "interface": item.get("dev", ""), "metric": item.get("metric", 0)} for item in routes]
        text = Path("/etc/resolv.conf").read_text(encoding="utf-8")[:65536]
        result["dns"] = re.findall(r"^nameserver\s+(\S+)", text, re.M)
    elif platform.system() == "Darwin":
        text = _command(["/sbin/ifconfig"], 2)
        result["adapters"] = [{"name": line.split(":", 1)[0], "description": ""} for line in text.splitlines()
                              if line and not line[0].isspace() and "UP" in line]
        dns = _command(["/usr/sbin/scutil", "--dns"], 2)
        result["dns"] = sorted(set(re.findall(r"nameserver\[\d+\]\s*:\s*(\S+)", dns)))[:16]
    return result


def _yaml_scalars(text):
    """Read only the top-level listener/controller fields, not proxy accounts."""
    allowed = {"mixed-port", "port", "external-controller", "external-controller-pipe", "secret"}
    values = {}
    for line in text.splitlines():
        match = re.match(r"^([a-z][a-z-]*)\s*:\s*(.*?)\s*$", line)
        if not match or match.group(1) not in allowed:
            continue
        value = match.group(2)
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        elif value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except ValueError:
                continue
        else:
            value = re.sub(r"\s+#.*$", "", value).strip()
        if len(value) <= 2048:
            values[match.group(1)] = value
    return values


def _client_files():
    candidates = []
    for variable in ("APPDATA", "LOCALAPPDATA"):
        if os.environ.get(variable):
            base = Path(os.environ[variable]) / "io.github.clash-verge-rev.clash-verge-rev"
            candidates.extend(base / name for name in ("clash-verge.yaml", "config.yaml"))
    for folder in ("mihomo", "clash", "clash-verge"):
        candidates.append(Path.home() / ".config" / folder / "config.yaml")
    return list(dict.fromkeys(candidates))


def local_controller_candidates():
    controllers, proxies = [], []
    for path in _client_files():
        try:
            if not path.is_file() or path.stat().st_size > MAX_CONFIG_BYTES:
                continue
            settings = _yaml_scalars(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError):
            continue
        secret = settings.get("secret", "")
        for field in ("external-controller-pipe", "external-controller"):
            endpoint = settings.get(field, "")
            if field.endswith("pipe") and re.fullmatch(r"\\\\\.\\pipe\\[^\\/\r\n]{1,180}", endpoint):
                controllers.append({"transport": "named_pipe", "endpoint": endpoint, "secret": secret, "source_group": str(path)})
            elif endpoint:
                normalized = normalize_proxy(endpoint)
                if normalized and urlsplit(normalized).hostname in ("127.0.0.1", "localhost", "::1"):
                    controllers.append({"transport": "http", "endpoint": normalized, "secret": secret, "source_group": str(path)})
        for field in ("mixed-port", "port"):
            try:
                port = int(settings.get(field, 0))
                if 1 <= port <= 65535:
                    proxies.append({"url": f"http://127.0.0.1:{port}", "source": "Clash / Mihomo 本地配置"})
            except (ValueError, TypeError):
                pass
    if os.name == "nt":
        try:
            names = [name for name in os.listdir("\\\\.\\pipe\\") if re.search(r"mihomo|clash|verge", name, re.I)]
        except OSError:
            names = []
        for name in names[:8]:
            endpoint = "\\\\.\\pipe\\" + name
            if not any(item["endpoint"] == endpoint for item in controllers):
                controllers.append({"transport": "named_pipe", "endpoint": endpoint, "secret": ""})
    unique = []
    for item in controllers:
        if not any((item["endpoint"], item["secret"]) == (other["endpoint"], other["secret"]) for other in unique):
            unique.append(item)
    return unique[:8], proxies


def _controller_request(candidate, endpoint):
    if endpoint not in ("/configs", "/connections"):
        raise ValueError("Only read-only controller endpoints are allowed")
    headers = {"Connection": "close", "Accept": "application/json"}
    secret = candidate.get("secret", "")
    if secret:
        if any(ord(char) < 32 or ord(char) == 127 for char in secret):
            raise ValueError("Invalid controller authentication")
        headers["Authorization"] = "Bearer " + secret
    if candidate["transport"] == "http":
        parsed = urlsplit(candidate["endpoint"])
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("Controller must use loopback")
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=1.5)
        try:
            connection.request("GET", endpoint, headers=headers)
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError("Controller did not authorize or answer the request")
            raw = response.read(MAX_CONTROLLER_BYTES + 1)
        finally:
            connection.close()
    else:
        path = candidate["endpoint"]
        if not re.fullmatch(r"\\\\\.\\pipe\\[^\\/\r\n]{1,180}", path):
            raise ValueError("Invalid local pipe path")
        class PipeSocket:
            def __init__(self, stream): self.stream = stream
            def makefile(self, *args, **kwargs): return self.stream
        payload = "GET " + endpoint + " HTTP/1.1\r\nHost: localhost\r\n"
        payload += "".join(key + ": " + value + "\r\n" for key, value in headers.items()) + "\r\n"
        # A bounded daemon wrapper below caps Windows named-pipe I/O, which
        # does not provide the socket timeout API. Stuck workers are capped.
        with open(path, "r+b", buffering=0) as stream:
            stream.write(payload.encode("utf-8"))
            with http.client.HTTPResponse(PipeSocket(stream)) as response:
                response.begin()
                if response.status != 200:
                    raise RuntimeError("Controller did not authorize or answer the request")
                raw = response.read(MAX_CONTROLLER_BYTES + 1)
    if len(raw) > MAX_CONTROLLER_BYTES:
        raise ValueError("Controller response exceeds limit")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Unexpected controller response")
    return result


def _boolean(value):
    return value if type(value) is bool else None


def sanitize_controller(config, connections, transport):
    tun = config.get("tun") if isinstance(config.get("tun"), dict) else {}
    dns = config.get("dns") if isinstance(config.get("dns"), dict) else {}
    verified = isinstance(connections, dict) and isinstance(connections.get("connections"), list)
    matches = []
    for item in connections["connections"] if verified else []:
        if not isinstance(item, dict): continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        host = str(metadata.get("host", "")).lower().rstrip(".")
        process = PureWindowsPath(str(metadata.get("processPath") or metadata.get("process") or "")).name
        relevant_host = any(host == suffix or host.endswith("." + suffix)
                            for suffix in ("claude.ai", "claude.com", "anthropic.com", "claudeusercontent.com"))
        if not relevant_host and process.lower() not in ("claude.exe", "claude"):
            continue
        chains = item.get("chains", [])
        chains = chains if isinstance(chains, list) else []
        matches.append({"host": _safe_text(host, 120), "process": _safe_text(process, 80),
                        "network": _safe_text(metadata.get("network", ""), 8),
                        "rule": _safe_text(item.get("rule", ""), 80),
                        "direct": any(str(chain).upper() == "DIRECT" for chain in chains)})
        if len(matches) == 20: break
    ports = []
    for field in ("mixed-port", "port"):
        value = config.get(field)
        if type(value) is int and 1 <= value <= 65535:
            ports.append(value)
    return {"controller": {"status": "connected", "transport": transport,
                           "mode": _safe_text(config.get("mode", ""), 24), "tun_enabled": _boolean(tun.get("enable")),
                           "dns_mode": _safe_text(dns.get("enhanced-mode", ""), 40),
                           "claude_connection_count": len(matches) if verified else None},
            "dns": {"enabled": _boolean(dns.get("enable")), "respect_rules": _boolean(dns.get("respect-rules")),
                    "enhanced_mode": _safe_text(dns.get("enhanced-mode", ""), 40),
                    "nameserver_count": len(dns.get("nameserver", [])) if isinstance(dns.get("nameserver"), list) else 0},
            "claude_connections": matches, "connections_verified": verified,
            "tun_device": _safe_text(tun.get("device", ""), 80),
            "proxy_ports": list(dict.fromkeys(ports))}


def controller_discovery():
    candidates, proxies = local_controller_candidates()
    def probe(candidate):
        config = _controller_request(candidate, "/configs")
        if not any(key in config for key in ("mixed-port", "port", "tun", "mode")):
            raise ValueError("Not a recognized Mihomo controller")
        response = _parallel({"connections": lambda: _controller_request(candidate, "/connections")}, 1.8)
        connections = response["connections"].get("value")
        result = sanitize_controller(config, connections, candidate["transport"])
        return result
    results = _parallel({str(index): lambda candidate=candidate: probe(candidate) for index, candidate in enumerate(candidates)}, 4.5)
    runtimes, identities = [], set()
    for index, candidate in enumerate(candidates):
        result = results[str(index)]
        if result["ok"]:
            runtime = result["value"]
            # The two controller transports may be declared by the same
            # client config. Merge only that known shared source when their
            # actual listener/TUN state agrees; otherwise keep ambiguity.
            group = candidate.get("source_group")
            identity = (group, tuple(runtime["proxy_ports"]), runtime["tun_device"],
                        runtime["controller"]["tun_enabled"], runtime["controller"]["mode"])
            if group and identity in identities:
                continue
            if group: identities.add(identity)
            runtimes.append(runtime)
            proxies = [{"url": f"http://127.0.0.1:{port}", "source": "Mihomo 当前运行配置"}
                       for port in runtime["proxy_ports"]] + proxies
    return {"runtimes": runtimes, "proxies": proxies}


def claude_candidates(inventory=None):
    inventory = inventory or {}
    candidates = []
    for process in inventory.get("processes", []):
        if str(process.get("name", "")).lower() in ("claude", "claude.exe") and process.get("path"):
            candidates.append(Path(process["path"]))
    if platform.system() == "Windows":
        for variable, suffix in (("LOCALAPPDATA", "AnthropicClaude"), ("LOCALAPPDATA", "Claude"),
                                 ("LOCALAPPDATA", "Programs/Claude"), ("PROGRAMFILES", "Claude"),
                                 ("PROGRAMFILES(X86)", "Claude")):
            base = os.environ.get(variable)
            if not base: continue
            folder = Path(base) / suffix
            candidates.append(folder / "Claude.exe")
            try:
                candidates.extend(sorted(folder.glob("app-*/Claude.exe"), reverse=True)[:8])
            except OSError:
                pass
        for package in inventory.get("packages", []):
            location = package.get("location", "")
            if not location or not re.search(r"Anthropic", str(package.get("publisher", "")), re.I): continue
            folder = Path(location)
            for relative in ("Claude.exe", "app/Claude.exe", "bin/Claude.exe"):
                candidates.append(folder / relative)
    elif platform.system() == "Darwin":
        candidates.extend((Path("/Applications/Claude.app"), Path.home() / "Applications/Claude.app"))
    result = []
    for path in candidates:
        try:
            if path.is_absolute() and path.exists() and str(path) not in result:
                result.append(str(path))
        except OSError:
            continue
    return result[:12]


def _reachable(candidate):
    """A listening SOCKS/controller port is not an HTTP CONNECT proxy."""
    parsed = urlsplit(candidate["url"])
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=1.0) as connection:
            connection.settimeout(1.0)
            connection.sendall(b"CONNECT claude.ai:443 HTTP/1.1\r\nHost: claude.ai:443\r\nConnection: close\r\n\r\n")
            line = connection.makefile("rb").readline(512)
            return bool(re.match(rb"^HTTP/1\.[01] 200(?: |\r?\n)", line))
    except (OSError, ValueError):
        return False


def empty_detected():
    try:
        language = locale.getlocale()[0] or ""
    except ValueError:
        language = ""
    return {"os": platform.system() + " " + platform.release(), "timezone": ", ".join(time.tzname),
            "language": language, "proxy_url": "", "proxy_source": "", "claude_path": "",
            "clients": [], "tun_adapters": [], "dns_servers": [], "default_routes": [],
            "controller": {"status": "unavailable", "transport": "", "mode": "", "tun_enabled": None,
                           "dns_mode": "", "claude_connection_count": None}, "observed_ip": ""}


def discover(config=None, *, deadline=DISCOVERY_BUDGET):
    config = config or {}
    started = time.monotonic()
    budget = max(0.0, min(float(deadline), DISCOVERY_BUDGET))
    tasks = {"inventory": windows_inventory if platform.system() == "Windows" else portable_inventory,
             "controller": controller_discovery,
             "standard_claude": claude_candidates}
    if platform.system() == "Windows": tasks["wininet"] = wininet_settings
    responses = _parallel(tasks, max(0.0, budget-1.0))
    inventory = responses["inventory"].get("value", {})
    controls = responses["controller"].get("value", {})
    runtime = {}
    detected = empty_detected()
    detected["timezone"] = _safe_text(inventory.get("timezone") or detected["timezone"])
    detected["language"] = _safe_text(inventory.get("language") or detected["language"])
    detected["clients"] = sorted({_safe_text(item.get("name", ""), 80) for item in inventory.get("processes", [])
                                  if re.search(CLIENT_PATTERN, str(item.get("name", "")), re.I)})
    detected["tun_adapters"] = [_safe_text(str(item.get("name", "")) + " " + str(item.get("description", "")))
                                for item in inventory.get("adapters", [])
                                if re.search(TUN_PATTERN, str(item.get("name", "")) + " " + str(item.get("description", "")), re.I)][:12]
    detected["dns_servers"] = sorted({_safe_text(value, 100) for value in inventory.get("dns", [])})[:16]
    detected["default_routes"] = [{"destination": _safe_text(route.get("destination", ""), 50),
                                  "next_hop": _safe_text(route.get("next_hop", ""), 100),
                                  "interface": _safe_text(route.get("interface", ""), 80),
                                  "metric": route.get("metric", 0) if type(route.get("metric", 0)) is int else 0}
                                 for route in inventory.get("routes", [])][:16]
    candidates = []
    manual = normalize_proxy(config.get("proxy_url", ""))
    if manual: candidates.append({"url": manual, "source": "高级设置指定"})
    candidates.extend(responses.get("wininet", {}).get("value", {}).get("proxies", []))
    candidates.extend(controls.get("proxies", []))
    candidates.extend(environment_proxies())
    processes = {item.get("pid"): str(item.get("name", "")) for item in inventory.get("processes", [])}
    listeners = inventory.get("listeners", [])
    listeners = sorted(listeners, key=lambda item: (item.get("port") not in (7897, 7890, 10809, 8080, 8888), item.get("port", 0)))
    for item in listeners:
        if re.search(CLIENT_PATTERN, processes.get(item.get("pid"), ""), re.I) and type(item.get("port")) is int:
            address = item.get("address", "")
            if address not in ("127.0.0.1", "0.0.0.0", "::", "::1"): continue
            host = "[::1]" if ":" in address else "127.0.0.1"
            candidates.append({"url": f"http://{host}:{item['port']}", "source": "代理进程实际监听端口"})
    unique = []
    for candidate in candidates:
        if candidate["url"] not in [item["url"] for item in unique]: unique.append(candidate)
    # Store/process paths are inspected under the same discovery deadline.
    remaining = budget-(time.monotonic()-started)
    path_result = _parallel({"paths": lambda: claude_candidates(inventory)}, max(0.0, min(1.0, remaining)))
    paths = path_result["paths"].get("value", [])
    remaining = budget-(time.monotonic()-started)
    active = _parallel({str(i): lambda item=item: _reachable(item) for i, item in enumerate(unique[:12])}, max(0.0, remaining))
    chosen = next((item for i, item in enumerate(unique[:12]) if active[str(i)].get("value") is True), None)
    if manual:
        chosen = {"url": manual, "source": "高级设置指定"}
    if chosen:
        detected.update(proxy_url=chosen["url"], proxy_source=chosen["source"])
        selected = urlsplit(chosen["url"])
        # A controller belongs to the chosen proxy only when its runtime port
        # matches that loopback listener. Never borrow another core's TUN state.
        matches = [item for item in controls.get("runtimes", [])
                   if selected.hostname in ("127.0.0.1", "localhost", "::1")
                   and selected.port in item.get("proxy_ports", [])]
        if len(matches) == 1:
            runtime = matches[0]
            detected["controller"] = runtime["controller"]
    paths += [path for path in responses["standard_claude"].get("value", []) if path not in paths]
    # Only discovered existing paths may appear here; an optional override is
    # kept in resolved_config by core and still has to pass its signature check.
    detected["claude_path"] = paths[0] if paths else ""
    runtime["ipv6_enabled_count"] = inventory.get("ipv6_enabled_count")
    runtime["pac_enabled"] = responses.get("wininet", {}).get("value", {}).get("pac_enabled", False)
    return {"detected": detected, "runtime": runtime, "claude_candidates": paths,
            "proxy_candidates": unique[:12],
            "errors": [name for name, result in responses.items() if not result["ok"]],
            "duration_ms": round((time.monotonic()-started)*1000)}
