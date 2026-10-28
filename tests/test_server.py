import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, call, patch

from app import core, server


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        web = root / "web"
        web.mkdir()
        (web / "index.html").write_text('<meta name="session-token" content="__SESSION_TOKEN__">', encoding="utf-8")
        self.config_path = root / "private/config.json"
        self.server = server.LocalServer(0, self.config_path, web)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.directory.cleanup()

    def request(self, method="GET", path="/api/config", data=None, *, token=True, headers=None, raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        supplied = {"Origin": self.server.base_url}
        if token:
            supplied["X-Session-Token"] = self.server.session_token
        if data is not None:
            raw = json.dumps(data)
            supplied["Content-Type"] = "application/json"
        supplied.update(headers or {})
        conn.request(method, path, body=raw, headers=supplied)
        response = conn.getresponse()
        payload = response.read()
        result = response.status, dict(response.getheaders()), payload
        conn.close()
        return result

    def test_startup_and_ui_do_not_scan_or_create_config(self):
        with patch("app.core.scan") as scan:
            status, headers, payload = self.request(path="/", token=False)
            self.assertEqual(status, 200)
            self.assertIn(self.server.session_token.encode(), payload)
            self.assertNotIn(b"__SESSION_TOKEN__", payload)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["X-Frame-Options"], "DENY")
            self.assertNotIn("Access-Control-Allow-Origin", headers)
            self.assertFalse(self.config_path.exists())
            scan.assert_not_called()

    def test_every_api_requires_session_token(self):
        for method, path in (("GET", "/api/config"), ("GET", "/api/status"), ("GET", "/api/export"),
                             ("POST", "/api/config"), ("POST", "/api/scan"), ("POST", "/api/launch")):
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path, token=False)[0], 403)

    def test_host_origin_and_cross_site_are_rejected(self):
        for headers in ({"Host": "attacker.example"}, {"Origin": "https://attacker.example"},
                        {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"}, {"X-Session-Token": "wrong"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request(headers=headers)[0], 403)

    def test_static_path_traversal_and_query_not_served(self):
        for path in ("/../core.py", "/%2e%2e/core.py", "/app/core.py", "/index.html?token=x", "/config.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path=path)[0], 404)

    def test_save_validates_and_invalidates_previous_report(self):
        self.server.state.report = {"can_launch": True}
        config = {**core.DEFAULT_CONFIG, "expected_ip": "1.1.1.1"}
        status, _, body = self.request("POST", "/api/config", config)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["config"], config)
        self.assertEqual(json.loads(self.config_path.read_text(encoding="utf-8")), config)
        self.assertIsNone(self.server.state.report)
        self.assertEqual(self.request("POST", "/api/config", {"proxy_url": "http://user:secret@localhost:7890"})[0], 400)
        self.assertNotIn("secret", self.config_path.read_text(encoding="utf-8"))

    def test_json_size_content_type_and_unsupported_payload(self):
        self.assertEqual(self.request("POST", "/api/config", raw="x" * 9000, headers={"Content-Type": "application/json"})[0], 413)
        self.assertEqual(self.request("POST", "/api/config", raw="{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/api/config", raw="[]", headers={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/api/scan", {"command": "anything"})[0], 400)
        self.assertEqual(self.request("OPTIONS", "/api/config")[0], 403)

    def test_running_scan_blocks_config_and_second_scan(self):
        entered, finish = threading.Event(), threading.Event()
        def slow_scan(config):
            entered.set()
            finish.wait(2)
            return server.failed_report()
        try:
            with patch("app.core.scan", side_effect=slow_scan):
                self.assertEqual(self.request("POST", "/api/scan", {})[0], 202)
                self.assertTrue(entered.wait(1))
                self.assertEqual(self.request("POST", "/api/scan", {})[0], 409)
                self.assertEqual(self.request("POST", "/api/config", {})[0], 409)
                self.assertTrue(json.loads(self.request(path="/api/status")[2])["running"])
                finish.set()
                for _ in range(100):
                    if not self.server.state.snapshot()["running"]:
                        break
                    time.sleep(0.005)
                self.assertFalse(self.server.state.snapshot()["running"])
        finally:
            finish.set()

    def test_launch_forces_fresh_scan_and_blocks_unknown(self):
        self.server.state.report = {"can_launch": True}
        with patch("app.core.scan", return_value=server.failed_report()) as scan, patch("app.core.launch_claude") as launch:
            status, _, payload = self.request("POST", "/api/launch", {})
            self.assertEqual(status, 409)
            self.assertFalse(json.loads(payload)["report"]["can_launch"])
            scan.assert_called_once()
            launch.assert_not_called()

    def test_launch_does_not_trust_a_truthy_non_boolean_gate(self):
        report = server.failed_report()
        report["can_launch"] = "false"
        with patch("app.core.scan", return_value=report), patch("app.core.launch_claude") as launch:
            self.assertEqual(self.request("POST", "/api/launch", {})[0], 409)
            launch.assert_not_called()

    def test_launch_success_and_launch_failure_gate(self):
        def good_report():
            report = server.failed_report()
            report.update(can_launch=True, summary={"pass": 1, "warning": 0, "fail": 0, "unknown": 0})
            report["checks"][0].update(id="claude_path", status="pass")
            return report
        with patch("app.core.scan", return_value=good_report()), patch("app.core.launch_claude") as launch:
            status, _, payload = self.request("POST", "/api/launch", {})
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(payload)["launched"])
            launch.assert_called_once()
        with patch("app.core.scan", return_value=good_report()), patch("app.core.launch_claude", side_effect=OSError()):
            status, _, payload = self.request("POST", "/api/launch", {})
            report = json.loads(payload)["report"]
            self.assertEqual(status, 409)
            self.assertFalse(report["can_launch"])
            self.assertEqual(report["summary"]["unknown"], 1)

    def test_export_is_attachment_and_hides_addresses(self):
        report = server.failed_report()
        report["checks"][0]["detail"] = "观察到 1.1.1.1 与 2606:4700::1111"
        self.server.state.report = report
        status, headers, payload = self.request(path="/api/export")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertNotIn(b"1.1.1.1", payload)
        self.assertNotIn(b"2606:4700::1111", payload)

    def test_corrupt_saved_config_is_preserved_and_does_not_pass(self):
        self.config_path.parent.mkdir()
        self.config_path.write_text('{"require_tun":"false"}', encoding="utf-8")
        state = server.State(self.config_path)
        self.assertIsNotNone(state.config_error)
        self.assertEqual(state.config, core.DEFAULT_CONFIG)
        self.assertEqual(self.config_path.read_text(encoding="utf-8"), '{"require_tun":"false"}')


class StartupTests(unittest.TestCase):
    def test_default_occupied_port_falls_back_and_explicit_port_does_not(self):
        instance = MagicMock()
        instance.base_url = "http://127.0.0.1:8766"
        with patch("app.server.LocalServer", side_effect=[OSError(), instance]) as local, patch("builtins.print"):
            server.main(["--no-browser"])
            self.assertEqual(local.call_args_list, [call(8765), call(8766)])
            instance.serve_forever.assert_called_once_with(poll_interval=0.25)
            instance.server_close.assert_called_once()
        with patch("app.server.LocalServer", side_effect=OSError()) as local, patch("sys.stderr"):
            with self.assertRaises(SystemExit) as error:
                server.main(["--port", "8765", "--no-browser"])
            self.assertEqual(error.exception.code, 1)
            local.assert_called_once_with(8765)

    def test_default_port_fallback_stops_after_ten_attempts(self):
        with patch("app.server.LocalServer", side_effect=OSError()) as local, patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                server.main(["--no-browser"])
            self.assertEqual(local.call_args_list, [call(port) for port in range(8765, 8775)])

    def test_local_server_always_binds_loopback(self):
        with patch("app.server.State"), patch("app.server.ThreadingHTTPServer.__init__", return_value=None) as initialize:
            server.LocalServer(8774)
            initialize.assert_called_once_with(("127.0.0.1", 8774), server.Handler)


if __name__ == "__main__":
    unittest.main()
