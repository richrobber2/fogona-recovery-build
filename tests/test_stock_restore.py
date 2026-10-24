import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[2]
SCRIPT=Path(__file__).resolve().parents[1]/'tools/restore-stock-recovery.sh'

@unittest.skipUnless(BASE == Path('/data/data/com.termux/files/home/downloads/device-assistant/recovery') and Path('/system/bin/getprop').exists(), 'Android device-local restore tests')
class StockRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='restore-fixtures.',dir=BASE/'tests')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.original=b'O'*4096
        self.current=b'N'*4096
        (self.root/'original.img').write_bytes(self.original)
        (self.root/'partition.img').write_bytes(self.current)
        (self.root/'.restore-fixture').touch()
        (self.root/'expected.sha256').write_text(hashlib.sha256(self.original).hexdigest()+'\n')
        (self.root/'expected.bytes').write_text('4096\n')

    def run_tool(self,*args):
        return subprocess.run(['sh',str(SCRIPT),'--sandbox',str(self.root),*args],text=True,capture_output=True,timeout=10)

    def unchanged(self):
        self.assertEqual((self.root/'partition.img').read_bytes(),self.current)

    def test_default_is_read_only(self):
        p=self.run_tool();self.assertEqual(p.returncode,0,p.stderr);self.unchanged();self.assertIn('Read-only',p.stdout)

    def test_check_is_read_only(self):
        p=self.run_tool('--check');self.assertEqual(p.returncode,0,p.stderr);self.unchanged()

    def test_explicit_restore_and_readback(self):
        p=self.run_tool('--restore');self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual((self.root/'partition.img').read_bytes(),self.original)
        self.assertIn('complete partition readback verified',p.stdout)

    def test_corrupt_backup_refused(self):
        (self.root/'original.img').write_bytes(b'X'*4096)
        p=self.run_tool('--restore');self.assertNotEqual(p.returncode,0);self.unchanged();self.assertIn('SHA256 mismatch',p.stderr)

    def test_backup_size_refused(self):
        (self.root/'original.img').write_bytes(b'O'*4095)
        self.assertNotEqual(self.run_tool('--restore').returncode,0);self.unchanged()

    def test_target_size_refused(self):
        (self.root/'partition.img').write_bytes(b'N'*4095)
        self.assertNotEqual(self.run_tool('--restore').returncode,0)
        self.assertEqual((self.root/'partition.img').read_bytes(),b'N'*4095)

    def test_backup_symlink_refused(self):
        (self.root/'original.img').rename(self.root/'other.img')
        (self.root/'original.img').symlink_to('other.img')
        self.assertNotEqual(self.run_tool('--restore').returncode,0);self.unchanged()

    def test_target_symlink_refused(self):
        (self.root/'partition.img').rename(self.root/'other.img')
        (self.root/'partition.img').symlink_to('other.img')
        self.assertNotEqual(self.run_tool('--restore').returncode,0)
        self.assertEqual((self.root/'other.img').read_bytes(),self.current)

    def test_bad_action_refused(self):
        self.assertNotEqual(self.run_tool('--write-anything').returncode,0);self.unchanged()

    def test_extra_arguments_refused(self):
        self.assertNotEqual(self.run_tool('--restore','extra').returncode,0);self.unchanged()

    def test_fixture_marker_required(self):
        (self.root/'.restore-fixture').unlink()
        self.assertNotEqual(self.run_tool('--restore').returncode,0);self.unchanged()

    def test_unprivileged_real_mode_refused(self):
        p=subprocess.run(['sh',str(SCRIPT),'--restore'],text=True,capture_output=True,timeout=10)
        self.assertNotEqual(p.returncode,0);self.assertIn('Local root required',p.stderr)

if __name__=='__main__':
    if os.getuid()==0:
        raise SystemExit('Run fixture tests as the unprivileged Termux user')
    unittest.main()
