import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]

class RamdiskAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.build = Path(cls.tmp.name)
        (cls.build / 'fixture.c').write_text('void _start(void) {}\n')
        subprocess.run(['clang', '-nostdlib', '-static', '-Wl,-e,_start', str(cls.build/'fixture.c'), '-o', str(cls.build/'fixture')], check=True)

        (cls.build/'lib.c').write_text('void dependency(void) {}\n')
        (cls.build/'dynamic.c').write_text('extern void dependency(void); void _start(void) { dependency(); }\n')
        subprocess.run(['clang','-nostdlib','-shared',str(cls.build/'lib.c'),'-o',str(cls.build/'libfixture.so')],check=True)
        subprocess.run(['clang','-nostdlib',str(cls.build/'dynamic.c'),'-L'+str(cls.build),'-lfixture','-Wl,-e,_start','-Wl,--dynamic-linker=/system/bin/linker64','-o',str(cls.build/'dynamic')],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.tmp_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_root.cleanup)
        self.root = Path(self.tmp_root.name) / 'root'
        self.output = Path(self.tmp_root.name) / 'audit.json'
        for name in ['init','system/bin/recovery','system/bin/sh','system/bin/twrp','system/bin/keystore2','system/bin/fscryptpolicyget','system/bin/device-rescue.sh','system/etc/recovery.fstab','system/etc/task_profiles.json']:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            if name in ['init','system/bin/recovery','system/bin/sh']:
                shutil.copy2(self.build/'fixture',p)
            else:
                p.write_text('#!/system/bin/sh\n')
                p.chmod(0o755)

    def audit(self, logging=False, crypto=False):
        return subprocess.run([sys.executable,str(BASE/'verify-ramdisk.py'),str(self.root),str(self.output)]+(['--require-logging'] if logging else [])+(['--require-crypto-startup'] if crypto else []), capture_output=True,text=True)

    def test_valid_arm64_fixture(self):
        p=self.audit()
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(self.output.read_text())['errors'],[])

    def test_logging_option_requires_tools(self):
        p=self.audit(logging=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('system/bin/logd',p.stderr)

    def test_logging_tools_audited(self):
        for name in ['logd','logcat']:
            shutil.copy2(self.build/'fixture',self.root/'system/bin'/name)
        script=self.root/'system/bin/recovery-logsave.sh'
        script.write_text('#!/system/bin/sh\n'); script.chmod(0o755)
        (self.root/'init.recovery.logd.rc').write_text('on init\n    start logd\n')
        (self.root/'system/etc/event-log-tags').write_text('1 fixture_tag\n')
        p=self.audit(logging=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def stage_crypto(self):
        library=self.root/'system/lib64/libbinder_ndk.so'; library.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(self.build/'fixture',library)
        shutil.copy2(self.build/'fixture',self.root/'system/bin/fogona-check-keymint')
        helper=self.root/'system/bin/fogona-crypto-start.sh'
        helper.write_text('#!/system/bin/sh\n'); helper.chmod(0o755)
        (self.root/'init.recovery.fogona-crypto.rc').write_text('on init\n')
        (self.root/'init.recovery.qcom.rc').write_text('import /init.recovery.fogona-crypto.rc\n')
        (self.root/'system/etc/ld.config.fogona-crypto.txt').write_text('[fogona_crypto]\n')
        path=self.root/'system/etc/init/keystore2.rc';path.parent.mkdir(exist_ok=True)
        path.write_text('on property:fogona.crypto.keymint.ready=1\n    start keystore2\nservice keystore2 /system/bin/keystore2 /tmp/misc/keystore\n    disabled\n')

    def test_crypto_startup_audit_accepts_complete_fixture(self):
        self.stage_crypto()
        result=self.audit(crypto=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_crypto_startup_audit_rejects_early_keystore(self):
        self.stage_crypto()
        with (self.root/'system/etc/init/keystore2.rc').open('a') as stream:
            stream.write('on late-init\n    start keystore2\n')
        result=self.audit(crypto=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Keystore must wait',result.stderr)

    def test_crypto_startup_audit_rejects_nonelf_probe(self):
        self.stage_crypto()
        (self.root/'system/bin/fogona-check-keymint').write_text('#!/system/bin/sh\n')
        result=self.audit(crypto=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Critical program is not ELF',result.stderr)

    def test_absolute_android_symlink(self):
        (self.root/'init').unlink()
        (self.root/'init').symlink_to('/system/bin/recovery')
        p=self.audit()
        self.assertEqual(p.returncode,0,p.stderr)

    def test_missing_critical_program(self):
        (self.root/'system/bin/recovery').unlink()
        self.assertNotEqual(self.audit().returncode,0)

    def test_wrong_architecture(self):
        path=self.root/'system/bin/recovery'
        data=bytearray(path.read_bytes());data[18:20]=(62).to_bytes(2,'little');path.write_bytes(data)
        p=self.audit()
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ARM64',p.stderr)

    def test_non_executable(self):
        (self.root/'system/bin/device-rescue.sh').chmod(0o600)
        p=self.audit()
        self.assertNotEqual(p.returncode,0)
        self.assertIn('execute bits',p.stderr)

    def test_non_elf_critical_program(self):
        (self.root/'system/bin/recovery').write_text('#!/system/bin/sh\n')
        p=self.audit()
        self.assertNotEqual(p.returncode,0)
        self.assertIn('not ELF',p.stderr)

    def test_missing_shared_library(self):
        shutil.copy2(self.build/'dynamic',self.root/'system/bin/recovery')
        shutil.copy2(self.build/'fixture',self.root/'system/bin/linker64')
        p=self.audit()
        self.assertNotEqual(p.returncode,0)
        self.assertIn('libfixture.so',p.stderr)

    def test_shared_library_closure(self):
        shutil.copy2(self.build/'dynamic',self.root/'system/bin/recovery')
        shutil.copy2(self.build/'fixture',self.root/'system/bin/linker64')
        dest=self.root/'system/lib64/libfixture.so';dest.parent.mkdir(parents=True)
        shutil.copy2(self.build/'libfixture.so',dest)
        p=self.audit()
        self.assertEqual(p.returncode,0,p.stderr)

    def test_symlink_loop(self):
        path=self.root/'system/bin/twrp';path.unlink();path.symlink_to('twrp')
        self.assertNotEqual(self.audit().returncode,0)

if __name__ == '__main__':
    unittest.main()
