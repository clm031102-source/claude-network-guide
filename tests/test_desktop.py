import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import desktop


class DesktopTests(unittest.TestCase):
    def test_navigation_policy_keeps_only_owned_origin(self):
        base = "http://127.0.0.1:12345"
        for url in (base, base + "/#results", "about:blank", "blob:" + base + "/id"):
            self.assertEqual(desktop.navigation_action(url, base), "allow", url)
        for url in ("https://github.com/clm031102-source/claude-network-guide", "http://127.0.0.1:99"):
            self.assertEqual(desktop.navigation_action(url, base), "external", url)
        for url in ("file:///C:/secret", "javascript:alert(1)", "data:text/html,hello", "ms-appx:test",
                    "http://user@127.0.0.1:12345", "http://127.0.0.1:bad", "blob:https://evil.test/id"):
            self.assertEqual(desktop.navigation_action(url, base), "block", url)

    def test_self_test_never_scans_or_launches(self):
        with patch.object(desktop.core, "scan", side_effect=AssertionError("must not scan")):
            result = desktop.self_test()
        self.assertTrue(result["ok"])
        self.assertTrue(result["server_stopped"])
        self.assertFalse(result["network_scan"])
        self.assertFalse(result["claude_launched"])
        self.assertTrue(result["tls_context"])
        self.assertTrue(result["certificate_validation"])
        self.assertTrue(result["hostname_validation"])

    def test_self_test_catches_missing_tls_runtime_data(self):
        with patch.object(desktop.ssl, "create_default_context", side_effect=FileNotFoundError("policy")):
            with self.assertRaises(FileNotFoundError):
                desktop.self_test()

    def test_native_navigation_cancels_before_external_open(self):
        guard = desktop.NavigationGuard(None, "http://127.0.0.1:12345")
        external = SimpleNamespace(Uri="https://github.com/clm031102-source/claude-network-guide", Cancel=False)
        unsafe = SimpleNamespace(Uri="file:///C:/private.txt", Cancel=False)
        with patch.object(desktop.webbrowser, "open") as browser:
            guard.navigate(None, external)
            guard.navigate(None, unsafe)
        self.assertTrue(external.Cancel)
        self.assertTrue(unsafe.Cancel)
        browser.assert_called_once_with(external.Uri, new=2)

    def test_popups_never_create_an_embedded_remote_window(self):
        guard = desktop.NavigationGuard(None, "http://127.0.0.1:12345")
        unsafe = SimpleNamespace(Uri="javascript:alert(1)", Handled=False)
        external = SimpleNamespace(Uri="https://example.com/", Handled=False)
        with patch.object(desktop.webbrowser, "open") as browser:
            guard.popup(None, unsafe)
            guard.popup(None, external)
        self.assertTrue(unsafe.Handled)
        self.assertTrue(external.Handled)
        browser.assert_called_once_with(external.Uri, new=2)

    def test_report_uses_core_redaction(self):
        private = {"resolved_config": {"claude_path": "private"}, "detected": {"secret": "private"}}
        public = {"report": {"checks": []}, "notice": "redacted"}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "report.json"
            with patch.object(desktop.core, "scan", return_value=private), \
                    patch.object(desktop.core, "redact_export", return_value=public) as redact:
                desktop.scan_report(output, Path(folder) / "missing-config.json")
            redact.assert_called_once_with(private)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), public)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_self_test_failure_is_generic(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "result.json"
            with patch.object(desktop, "self_test", side_effect=RuntimeError("private-data")):
                code = desktop.main(["--self-test", "--self-test-output", str(output)])
            self.assertEqual(code, 1)
            self.assertNotIn("private-data", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
