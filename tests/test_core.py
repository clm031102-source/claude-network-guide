import ipaddress
import os
from pathlib import Path
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from app import core


class ConfigTests(unittest.TestCase):
    def test_rejects_credentials_and_non_http_proxies(self):
        for value in ("http://user:password@127.0.0.1:7890", "socks5://127.0.0.1:7890",
                      "https://127.0.0.1:7890", "http://127.0.0.1", "http://host:0",
                      "http://host:65536", "http://host:80?token=abc", "http://host:80/commands",
                      "http://127.0.0.1:80\\@evil", "http://ho%73t:80"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.validate_config({"proxy_url": value})

    def test_requires_public_ipv4_and_actual_boolean(self):
        for value in ("127.0.0.1", "192.168.1.1", "198.18.0.1", "224.0.0.1", "::1", "2606:4700::1111", "garbage"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.validate_config({"expected_ip": value})
        with self.assertRaises(ValueError):
            core.validate_config({"residential_ip_confirmed": "true"})
        with self.assertRaises(ValueError):
            core.validate_config({"unknown_setting": True})

    def test_valid_config_and_proxy(self):
        config = core.validate_config({"expected_ip": "1.1.1.1", "proxy_url": "http://[::1]:7890"})
        self.assertTrue(config["require_tun"])
        self.assertFalse(config["require_udp"])
        self.assertEqual(core.parse_proxy(config["proxy_url"]), ("::1", 7890))


class TransportTests(unittest.TestCase):
    @patch.dict(os.environ, {"NO_PROXY": "*", "HTTPS_PROXY": "http://attacker:8888"})
    @patch("app.core.http.client.HTTPSConnection")
    def test_explicit_connect_proxy_ignores_environment(self, connection):
        result = core._connection("claude.ai", "http://127.0.0.1:7890")
        self.assertEqual(connection.call_args.args, ("127.0.0.1", 7890))
        result.set_tunnel.assert_called_once_with("claude.ai", 443)
        core._connection("claude.ai")
        self.assertEqual(connection.call_args.args, ("claude.ai", 443))

    @patch("app.core._connection")
    def test_response_limit_and_status_are_enforced(self, connection):
        response = connection.return_value.getresponse.return_value
        response.status = 200
        response.read.return_value = b"x" * (core.MAX_RESPONSE + 1)
        with self.assertRaises(ValueError):
            core.fetch_text("https://example.com/")
        connection.return_value.close.assert_called()
        response.status = 403
        with self.assertRaises(RuntimeError):
            core.fetch_text("https://example.com/")

    def test_whole_scan_deadline_includes_stuck_workers(self):
        release = threading.Event()
        before = time.monotonic()
        try:
            result = core.run_probes({"slow": lambda: release.wait(5), "fast": lambda: "ok"}, deadline=0.05)
            self.assertLess(time.monotonic() - before, 0.5)
            self.assertEqual(result["slow"], {"ok": False, "error": "Timeout"})
            self.assertEqual(result["fast"], {"ok": True, "value": "ok"})
        finally:
            release.set()

    def test_external_errors_do_not_echo_secret_text(self):
        def bad():
            raise RuntimeError("token=VERYSECRET http://user:password@host")
        result = core.run_probes({"bad": bad})
        self.assertEqual(result["bad"], {"ok": False, "error": "RuntimeError"})


class StunTests(unittest.TestCase):
    def setUp(self):
        self.transaction = b"123456789012"
        address = int(ipaddress.IPv4Address("1.1.1.1")) ^ 0x2112A442
        attribute = struct.pack("!HHBBHI", 0x0020, 8, 0, 1, 1234, address)
        self.packet = struct.pack("!HHI", 0x0101, len(attribute), 0x2112A442) + self.transaction + attribute

    def test_valid_xor_address(self):
        self.assertEqual(core.parse_stun(self.packet, self.transaction), "1.1.1.1")

    def test_wrong_transaction_or_cookie_rejected(self):
        self.assertIsNone(core.parse_stun(self.packet, b"000000000000"))
        self.assertIsNone(core.parse_stun(self.packet[:4] + b"XXXX" + self.packet[8:], self.transaction))

    def test_truncated_attribute_and_length_rejected(self):
        for packet in (self.packet[:-1], self.packet[:22], self.packet + b"junk", self.packet[:22] + b"\xff\xff" + self.packet[24:]):
            with self.subTest(packet=packet):
                self.assertIsNone(core.parse_stun(packet, self.transaction))


def successful_observations(tasks, deadline):
    result = {key: {"ok": True, "value": "1.1.1.1"} for key in tasks}
    result["tun"]["value"] = {"processes": ["mihomo"], "adapters": ["Wintun"]}
    result["dns"]["value"] = ["198.18.0.1"]
    result["ipv6"] = {"ok": False, "error": "Timeout"}
    result["asn"]["value"] = {"ip": "1.1.1.1", "org": "Example ISP", "country": "US"}
    result["claude_path"]["value"] = "/verified/Claude.exe"
    return result


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.config = core.validate_config({"expected_ip": "1.1.1.1", "residential_ip_confirmed": True,
                                           "claude_path": "C:/Example/Claude.exe"})

    def report(self, changes=None, config=None):
        def observations(tasks, deadline):
            result = successful_observations(tasks, deadline)
            result.update(changes or {})
            return result
        with patch("app.core.run_probes", side_effect=observations):
            return core.scan(config or self.config)

    def test_launch_gate_and_unknowns_are_visible(self):
        report = self.report()
        self.assertTrue(report["can_launch"])
        checks = {item["id"]: item for item in report["checks"]}
        self.assertEqual(checks["dns"]["status"], "unknown")
        self.assertEqual(checks["ipv6"]["status"], "unknown")
        self.assertEqual(checks["residential_purchase"]["status"], "warning")
        self.assertIn("不能证明", checks["dns"]["detail"])
        self.assertEqual(sum(report["summary"].values()), len(report["checks"]))

    def test_single_missing_proxy_sample_blocks(self):
        report = self.report({"proxy_1": {"ok": False, "error": "Timeout"}})
        self.assertFalse(report["can_launch"])
        self.assertEqual(next(c for c in report["checks"] if c["id"] == "proxy_egress")["status"], "unknown")

    def test_route_or_ipv6_mismatch_blocks(self):
        for key in ("default_1", "proxy_0", "stun_1", "ipv6"):
            with self.subTest(key=key):
                self.assertFalse(self.report({key: {"ok": True, "value": "8.8.8.8"}})["can_launch"])

    def test_missing_udp_is_unknown_and_policy_controls_blocking(self):
        changes = {f"stun_{i}": {"ok": False, "error": "Timeout"} for i in range(len(core.STUN_SERVERS))}
        report = self.report(changes)
        self.assertTrue(report["can_launch"])
        self.assertEqual(next(c for c in report["checks"] if c["id"] == "udp")["status"], "unknown")
        self.assertFalse(self.report(changes, {**self.config, "require_udp": True})["can_launch"])

    def test_partial_udp_sample_is_unknown_even_when_responding_ip_matches(self):
        report = self.report({"stun_1": {"ok": False, "error": "Timeout"}}, {**self.config, "require_udp": True})
        self.assertFalse(report["can_launch"])
        self.assertEqual(next(c for c in report["checks"] if c["id"] == "udp")["status"], "unknown")

    def test_optional_asn_unavailable_does_not_block_but_observed_mismatch_does(self):
        self.assertTrue(self.report({"asn": {"ok": False, "error": "Timeout"}})["can_launch"])
        report = self.report({"asn": {"ok": True, "value": {"ip": "8.8.8.8", "org": "Other ISP", "country": "US"}}})
        self.assertFalse(report["can_launch"])
        self.assertEqual(next(c for c in report["checks"] if c["id"] == "asn")["status"], "fail")

    def test_missing_critical_observation_blocks(self):
        for key in ("tun", "claude_path", "target_default_claude.ai", "target_proxy_api.anthropic.com"):
            with self.subTest(key=key):
                self.assertFalse(self.report({key: {"ok": False, "error": "Timeout"}})["can_launch"])

    def test_purchase_declaration_required(self):
        self.assertFalse(self.report(config={**self.config, "residential_ip_confirmed": False})["can_launch"])

    def test_export_hides_all_ip_literals_and_configuration(self):
        report = self.report({"ipv6": {"ok": True, "value": "2606:4700:4700::1111"}})
        import json
        exported = json.dumps(core.redact_export(report), ensure_ascii=False)
        self.assertNotIn("1.1.1.1", exported)
        self.assertNotIn("198.18.0.1", exported)
        self.assertNotIn("2606:4700:4700::1111", exported)
        self.assertNotIn("/verified/Claude.exe", exported)
        self.assertIn("[IP已隐藏]", exported)

    def test_export_handles_chinese_adjacency_and_sentence_punctuation(self):
        import json
        report = self.report()
        report["checks"][0]["detail"] = "出口1.1.1.1地址；出口2606:4700::1111地址；IP=::ffff:8.8.8.8."
        exported = json.dumps(core.redact_export(report), ensure_ascii=False)
        for literal in ("1.1.1.1", "2606:4700::1111", "8.8.8.8"):
            self.assertNotIn(literal, exported)
        self.assertNotIn("::ffff:", exported)


class LauncherTests(unittest.TestCase):
    def test_rejects_commands_relative_paths_and_network_paths(self):
        for path in ("", "claude.exe --flag", "relative/Claude.exe", "//remote/share/Claude.exe"):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                core.validate_claude_path(path)

    @patch("app.core.platform.system", return_value="Windows")
    @patch("app.core._run")
    def test_windows_requires_valid_anthropic_signature(self, run, system):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Claude.exe"
            path.write_bytes(b"MZ" + b"\0" * 32)
            for subject, status in (("CN=Other Publisher", "Valid"), ("CN=Anthropic, PBC", "NotSigned"),
                                    ("CN=Anthropic Evil LLC", "Valid")):
                run.return_value = '{"status":"' + status + '","subject":"' + subject + '"}'
                with self.subTest(subject=subject, status=status), self.assertRaises(ValueError):
                    core.validate_claude_path(str(path))
            run.return_value = '{"status":"Valid","subject":"CN=Anthropic, PBC, O=Anthropic, PBC, C=US"}'
            self.assertEqual(core.validate_claude_path(str(path)), path.resolve())

    @patch("app.core.subprocess.Popen")
    @patch("app.core.validate_claude_path")
    @patch("app.core.platform.system", return_value="Windows")
    def test_launch_uses_validated_path_without_shell(self, system, validate, popen):
        validate.return_value = Path("C:/Program Files/Claude/Claude.exe")
        core.launch_claude("candidate")
        validate.assert_called_once_with("candidate")
        popen.assert_called_once_with([str(validate.return_value)], shell=False, close_fds=True)


if __name__ == "__main__":
    unittest.main()
