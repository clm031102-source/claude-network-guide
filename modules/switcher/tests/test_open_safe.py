"""open-safe 隔离浏览器回归测试。

使用假浏览器脚本记录参数并短暂驻留；不启动真实浏览器、不访问网络。
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "core" / "claude-switch.sh"


@unittest.skipUnless(sys.platform == "darwin", "open-safe targets macOS")
class OpenSafeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fake = self.root / "fake-chrome"
        self.fake.write_text(
            "#!/bin/bash\nprintf '%s\\n' \"$@\" > \"$FAKE_LOG\"\nsleep 2\n",
            encoding="utf-8")
        self.fake.chmod(0o755)
        self.log = self.root / "args.log"

    def run_open(self, url):
        env = dict(os.environ,
                   CLAUDE_SWITCHER_CHROME=str(self.fake),
                   CLAUDE_SWITCHER_SKIP_NET_CHECK="1",
                   FAKE_LOG=str(self.log))
        return subprocess.run(["/bin/bash", str(SCRIPT), "open-safe", url],
                              env=env, text=True, capture_output=True, timeout=30)

    def wait_for_profile_removal(self, profile, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not Path(profile).exists():
                return True
            time.sleep(0.5)
        return False

    def test_https_opens_with_isolation_flags_and_cleans_up(self):
        result = self.run_open("https://example.com/login?token=abc")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        deadline = time.time() + 5
        while not self.log.exists() and time.time() < deadline:
            time.sleep(0.1)
        args = self.log.read_text(encoding="utf-8").splitlines()
        profile = next(a.split("=", 1)[1] for a in args if a.startswith("--user-data-dir="))
        self.assertIn("--force-webrtc-ip-handling-policy=disable_non_proxied_udp", args)
        self.assertIn("--disable-extensions", args)
        self.assertIn("--no-first-run", args)
        self.assertIn("https://example.com/login?token=abc", args)
        self.assertTrue(Path(profile).is_dir())
        self.assertTrue(self.wait_for_profile_removal(profile), "临时 profile 未按预期销毁")

    def test_http_is_allowed(self):
        result = self.run_open("http://example.com")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_non_http_schemes_are_rejected(self):
        for url in ("file:///etc/passwd", "javascript:alert(1)", "data:text/html,x", "ftp://x"):
            result = self.run_open(url)
            self.assertNotEqual(result.returncode, 0, url)
            self.assertIn("只允许 http/https", result.stdout)

    def test_missing_url_is_rejected(self):
        result = self.run_open("")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
