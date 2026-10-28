"""cli-info 只读体检回归测试。

使用隔离 HOME 与假 claude 可执行文件,不调用真实 CLI、不访问网络。
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "core" / "claude-switch.sh"


@unittest.skipUnless(sys.platform == "darwin", "cli-info targets macOS")
class CliInfoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.bin.mkdir()

    def run_info(self, with_cli=True):
        if with_cli:
            fake = self.bin / "claude"
            fake.write_text("#!/bin/bash\necho '9.9.9 (Claude Code)'\n", encoding="utf-8")
            fake.chmod(0o755)
        env = dict(os.environ, HOME=str(self.home),
                   PATH=f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin")
        return subprocess.run(["/bin/bash", str(SCRIPT), "cli-info"],
                              env=env, text=True, capture_output=True, timeout=30)

    def test_detects_cli_and_version(self):
        result = self.run_info()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CLI=ok:", result.stdout)
        self.assertIn("版本=ok:9.9.9 (Claude Code)", result.stdout)
        self.assertIn("安装方式=info:", result.stdout)

    def test_reports_missing_cli(self):
        result = self.run_info(with_cli=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CLI=warn:PATH 中没有 claude 命令", result.stdout)
        self.assertIn("桌面版内置=", result.stdout)

    def test_reports_config_dir_when_present(self):
        (self.home / ".claude").mkdir()
        (self.home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
        result = self.run_info()
        self.assertIn("配置目录=ok:", result.stdout)


if __name__ == "__main__":
    unittest.main()
