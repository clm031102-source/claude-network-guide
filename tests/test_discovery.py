import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from app import discovery


class ProxyDiscoveryTests(unittest.TestCase):
    def test_normalization_never_retains_credentials(self):
        for value in ("socks5://127.0.0.1:1080", "http://user:secret@127.0.0.1:7897",
                      "http://host:80/?secret=x", "http://host:80#token", "127.0.0.1", "http://ho%73t:80"):
            self.assertEqual(discovery.normalize_proxy(value), "")
        self.assertEqual(discovery.normalize_proxy("127.0.0.1:7897"), "http://127.0.0.1:7897")

    def test_system_proxy_order_and_disabled_proxy(self):
        result = discovery.parse_wininet("socks=127.0.0.1:1080;http=127.0.0.1:7890;https=127.0.0.1:7897")
        self.assertEqual([item["url"] for item in result], ["http://127.0.0.1:7897", "http://127.0.0.1:7890"])
        self.assertEqual(discovery.parse_wininet("127.0.0.1:7897", False), [])
        self.assertEqual(discovery.environment_proxies({"HTTPS_PROXY": "http://user:private@host:80", "HTTP_PROXY": "127.0.0.1:7897"}),
                         [{"url": "http://127.0.0.1:7897", "source": "环境变量 HTTP_PROXY"}])

    @patch("app.discovery.socket.create_connection")
    def test_only_http_connect_success_identifies_candidate(self, connect):
        connection = connect.return_value.__enter__.return_value
        for line, expected in ((b"HTTP/1.1 200 Connection established\r\n", True),
                               (b"HTTP/1.1 405 Method Not Allowed\r\n", False),
                               (b"\x05\x00", False), (b"HTTP/1.1 407 Authentication Required\r\n", False)):
            connection.makefile.return_value.readline.return_value = line
            self.assertEqual(discovery._reachable({"url": "http://127.0.0.1:7897"}), expected)
        self.assertIn(b"CONNECT claude.ai:443", connection.sendall.call_args.args[0])


class ControllerTests(unittest.TestCase):
    def test_yaml_reads_only_controller_top_level_fields(self):
        values = discovery._yaml_scalars("mixed-port: 7897\nsecret: 'private'\nproxies:\n  - password: account-secret\n  secret: nested-secret\nexternal-controller: 127.0.0.1:9090\n")
        self.assertEqual(values, {"mixed-port": "7897", "secret": "private", "external-controller": "127.0.0.1:9090"})

    def test_only_local_controller_candidates(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "config.yaml"
            file.write_text("external-controller: 8.8.8.8:9090\nexternal-controller-pipe: '\\\\.\\pipe\\verge-mihomo-test'\nsecret: private\nmixed-port: 7897\n", encoding="utf-8")
            with patch("app.discovery._client_files", return_value=[file]), patch("app.discovery.os.listdir", return_value=[]):
                controllers, proxies = discovery.local_controller_candidates()
        self.assertEqual(len(controllers), 1)
        self.assertEqual(controllers[0]["transport"], "named_pipe")
        self.assertEqual(proxies[0]["url"], "http://127.0.0.1:7897")

    def test_sanitizer_distinguishes_no_connections_from_unread(self):
        config = {"secret": "PRIVATE", "mixed-port": 7897, "tun": {"enable": True, "device": "Mihomo"}}
        missing = discovery.sanitize_controller(config, None, "named_pipe")
        empty = discovery.sanitize_controller(config, {"connections": []}, "named_pipe")
        self.assertIsNone(missing["controller"]["claude_connection_count"])
        self.assertEqual(empty["controller"]["claude_connection_count"], 0)
        full = discovery.sanitize_controller(config, {"connections": [
            {"metadata": {"host": "api.anthropic.com", "processPath": "C:\\Users\\Private\\Claude.exe", "network": "tcp"}, "chains": ["PRIVATE-NODE", "DIRECT"]},
            {"metadata": {"host": "unrelated.example"}, "chains": ["PRIVATE-NODE"]},
        ]}, "named_pipe")
        self.assertEqual(full["controller"]["claude_connection_count"], 1)
        self.assertTrue(full["claude_connections"][0]["direct"])
        self.assertNotIn("PRIVATE", json.dumps(full))
        self.assertNotIn("Users", json.dumps(full))

    @patch("app.discovery.http.client.HTTPConnection")
    def test_controller_only_reads_allowed_endpoints_and_localhost(self, connection):
        response = connection.return_value.getresponse.return_value
        response.status, response.read.return_value = 200, b'{"mode":"rule"}'
        candidate = {"transport": "http", "endpoint": "http://127.0.0.1:9090", "secret": "memory-only"}
        self.assertEqual(discovery._controller_request(candidate, "/configs"), {"mode": "rule"})
        self.assertEqual(connection.return_value.request.call_args.args, ("GET", "/configs"))
        self.assertEqual(connection.return_value.request.call_args.kwargs["headers"]["Authorization"], "Bearer memory-only")
        for endpoint in ("/restart", "/configs?patch=true"):
            with self.assertRaises(ValueError): discovery._controller_request(candidate, endpoint)
        with self.assertRaises(ValueError):
            discovery._controller_request({**candidate, "endpoint": "http://remote.example:9090"}, "/configs")
        response.read.return_value = b"x" * (discovery.MAX_CONTROLLER_BYTES + 1)
        with self.assertRaises(ValueError): discovery._controller_request(candidate, "/configs")

    def test_named_pipe_http_parser_and_secret_remain_in_memory(self):
        class Pipe(io.BytesIO):
            def write(self, data):
                self.request = data
                return len(data)
            def close(self): pass
        stream = Pipe(b'HTTP/1.1 200 OK\r\nContent-Length: 15\r\n\r\n{"mode":"rule"}')
        with patch("builtins.open", return_value=stream):
            result = discovery._controller_request({"transport": "named_pipe", "endpoint": r"\\.\pipe\verge-mihomo-test", "secret": "private"}, "/configs")
        self.assertEqual(result, {"mode": "rule"})
        self.assertIn(b"Authorization: Bearer private", stream.request)
        self.assertNotIn("private", json.dumps(result))

    def test_dual_transports_merge_only_same_config_source_and_runtime(self):
        pipe = {"transport": "named_pipe", "source_group": "same-config"}
        http = {"transport": "http", "source_group": "same-config"}
        def request(candidate, endpoint):
            return {"connections": []} if endpoint == "/connections" else {"mixed-port": 7897, "mode": "rule", "tun": {"enable": True, "device": "Mihomo"}}
        with patch("app.discovery.local_controller_candidates", return_value=([pipe, http], [])), patch("app.discovery._controller_request", side_effect=request):
            self.assertEqual(len(discovery.controller_discovery()["runtimes"]), 1)
        http["source_group"] = "other-config"
        with patch("app.discovery.local_controller_candidates", return_value=([pipe, http], [])), patch("app.discovery._controller_request", side_effect=request):
            self.assertEqual(len(discovery.controller_discovery()["runtimes"]), 2)


class DiscoveryIntegrationTests(unittest.TestCase):
    def discover(self, config=None, controls=None, reachable=None):
        inventory = {"processes": [{"name": "mihomo", "pid": 12}], "adapters": [{"name": "Mihomo", "description": "TUN"}],
                     "routes": [], "dns": ["198.18.0.1"], "listeners": [{"pid": 12, "address": "127.0.0.1", "port": 1080}], "packages": []}
        with patch("app.discovery.platform.system", return_value="Windows"), patch("app.discovery.windows_inventory", return_value=inventory), \
             patch("app.discovery.controller_discovery", return_value=controls or {"runtimes": [], "proxies": []}), \
             patch("app.discovery.wininet_settings", return_value={"proxies": [{"url": "http://127.0.0.1:7897", "source": "WinINET"}]}), \
             patch("app.discovery.environment_proxies", return_value=[]), patch("app.discovery.claude_candidates", return_value=["C:/Existing/Claude.exe"]), \
             patch("app.discovery._reachable", side_effect=reachable or (lambda item: item["url"].endswith(":7897"))):
            return discovery.discover(config or {})

    def test_proxy_matches_only_its_own_controller(self):
        wrong = discovery.sanitize_controller({"mixed-port": 7890, "tun": {"enable": False}}, None, "named_pipe")
        right = discovery.sanitize_controller({"mixed-port": 7897, "tun": {"enable": True}}, {"connections": []}, "named_pipe")
        found = self.discover(controls={"runtimes": [wrong, right], "proxies": []})
        self.assertTrue(found["detected"]["controller"]["tun_enabled"])
        other = self.discover(controls={"runtimes": [wrong], "proxies": []})
        self.assertEqual(other["detected"]["controller"]["status"], "unavailable")

    def test_ambiguous_controller_does_not_assert_tun(self):
        runtimes = [discovery.sanitize_controller({"mixed-port": 7897, "tun": {"enable": enabled}}, None, "named_pipe") for enabled in (False, True)]
        self.assertIsNone(self.discover(controls={"runtimes": runtimes, "proxies": []})["detected"]["controller"]["tun_enabled"])

    def test_unreachable_override_is_retained_for_actual_failure_detection(self):
        config = {"proxy_url": "http://127.0.0.1:12345", "claude_path": "C:/Missing/Claude.exe"}
        found = self.discover(config)
        self.assertEqual(found["detected"]["proxy_url"], config["proxy_url"])
        self.assertNotEqual(found["detected"]["claude_path"], config["claude_path"])
        self.assertEqual(config["claude_path"], "C:/Missing/Claude.exe")

    def test_bounded_workers_do_not_wait_for_stuck_pipe(self):
        release = threading.Event()
        started = time.monotonic()
        try:
            result = discovery._parallel({"pipe": lambda: release.wait(5), "quick": lambda: "yes"}, 0.04)
            self.assertLess(time.monotonic()-started, 0.5)
            self.assertEqual(result["pipe"], {"ok": False, "error": "Timeout"})
            self.assertEqual(result["quick"]["value"], "yes")
        finally: release.set()

    def test_running_and_anthropic_store_install_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            running = Path(directory) / "running" / "Claude.exe"
            store = Path(directory) / "store" / "app" / "Claude.exe"
            unrelated = Path(directory) / "other" / "Claude.exe"
            for file in (running, store, unrelated):
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b"MZ")
            inventory = {"processes": [{"name": "Claude", "path": str(running)}], "packages": [
                {"location": str(store.parent.parent), "publisher": "CN=Anthropic, PBC"},
                {"location": str(unrelated.parent), "publisher": "Other"}]}
            with patch("app.discovery.platform.system", return_value="Windows"), patch.dict(os.environ, {}, clear=True):
                paths = discovery.claude_candidates(inventory)
            self.assertEqual(paths, [str(running), str(store)])


if __name__ == "__main__":
    unittest.main()
