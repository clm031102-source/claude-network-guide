"""账号快照加密导出/导入回归测试(仅 macOS)。

使用隔离 HOME 与临时目录,不接触真实账号、登录态或系统设置。
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "core" / "claude-switch.sh"
PASSWORD = "test-password-123"


@unittest.skipUnless(sys.platform == "darwin", "snapshot transfer uses hdiutil (macOS)")
class SnapshotTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.accounts = self.home / ".claude-switcher" / "accounts"
        (self.accounts / "A" / "sub").mkdir(parents=True)
        (self.accounts / "A" / "sub" / "marker.txt").write_text("account-a", encoding="utf-8")
        (self.home / ".claude-switcher" / "current").write_text("B", encoding="utf-8")
        self.image = self.root / "account-a.dmg"

    def run_core(self, *args, password=None, home=None):
        env = dict(os.environ, HOME=str(home or self.home))
        return subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            input=(password + "\n") if password is not None else None,
            text=True, capture_output=True, env=env, timeout=90,
        )

    def export(self, target="A", image=None):
        return self.run_core("snapshot-export", target, str(image or self.image),
                             "--password-stdin", password=PASSWORD)

    def import_into(self, target, image=None, password=PASSWORD):
        return self.run_core("snapshot-import", str(image or self.image), target,
                             "--password-stdin", password=password)

    def test_roundtrip_restores_snapshot(self):
        result = self.export()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.image.is_file())

        home2 = self.root / "home2"
        (home2 / ".claude-switcher" / "accounts").mkdir(parents=True)
        result = self.run_core(
            "snapshot-import", str(self.image), "A", "--password-stdin",
            password=PASSWORD, home=home2)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        restored = home2 / ".claude-switcher" / "accounts" / "A" / "sub" / "marker.txt"
        self.assertEqual(restored.read_text(encoding="utf-8"), "account-a")
        self.assertFalse((home2 / ".claude-switcher" / "accounts" / "A"
                          / ".claude-switcher-snapshot.json").exists())

    def test_wrong_password_leaves_no_snapshot(self):
        self.assertEqual(self.export().returncode, 0)
        home2 = self.root / "home2"
        (home2 / ".claude-switcher" / "accounts").mkdir(parents=True)
        result = self.run_core("snapshot-import", str(self.image), "A",
                               "--password-stdin", password="wrong-password", home=home2)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((home2 / ".claude-switcher" / "accounts" / "A").exists())

    def test_account_mismatch_is_rejected(self):
        self.assertEqual(self.export().returncode, 0)
        home2 = self.root / "home2"
        (home2 / ".claude-switcher" / "accounts").mkdir(parents=True)
        result = self.run_core("snapshot-import", str(self.image), "B",
                               "--password-stdin", password=PASSWORD, home=home2)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((home2 / ".claude-switcher" / "accounts" / "B").exists())

    def test_existing_target_is_not_overwritten(self):
        self.assertEqual(self.export().returncode, 0)
        (self.accounts / "B").mkdir()
        result = self.import_into("B")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.accounts / "B" / "sub").exists())

    def test_short_password_is_rejected(self):
        result = self.run_core("snapshot-export", "A", str(self.image),
                               "--password-stdin", password="short")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.image.exists())

    def test_current_account_cannot_be_exported(self):
        (self.home / ".claude-switcher" / "current").write_text("A", encoding="utf-8")
        result = self.export()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.image.exists())


if __name__ == "__main__":
    unittest.main()
