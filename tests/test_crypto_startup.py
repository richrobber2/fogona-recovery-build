#!/usr/bin/env python3
"""Exercise real shell policy with fake properties/mounts/commands, no root."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE/'device/recovery/root/system/bin/fogona-crypto-start.sh'
LIBS = '''libc++.so libxml2.so libdmabufheap.so libutils.so libcutils.so libbase.so libion.so
android.hardware.security.sharedsecret-V1-ndk.so libbinder.so
android.hardware.security.secureclock-V1-ndk.so android.hardware.security.keymint-V2-ndk.so
libcrypto.so libhidlbase.so libhardware.so'''.split()
class StartupTests(unittest.TestCase):
    def run_case(self, **changes):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); runtime=root/'runtime'; runtime.mkdir()
            for name in LIBS: (runtime/name).write_text('fixture')
            if changes.get('missing_library'): (runtime/LIBS[-1]).unlink()
            (root/'mounts').write_text('/dev/block/dm-1 /vendor erofs '+changes.get('mount','ro,seclabel')+' 0 0\n')
            (root/'manifest').write_text('<manifest/>')
            if changes.get('missing_manifest'): (root/'manifest').unlink()
            environment=dict(os.environ, FIXTURE=str(root), TEST_UID=str(changes.get('uid',0)),
                TEST_BOOTMODE=changes.get('bootmode','recovery'), TEST_TWRP='1', TEST_DEVICE='fogona',
                TEST_BOOTED=changes.get('booted',''), TEST_CHECK=str(changes.get('check',0)))
            commands=r'''
fixture_script=$1
set -- --library
. "$fixture_script"
mount_table="$FIXTURE/mounts"
runtime="$FIXTURE/runtime"
vendor_manifest="$FIXTURE/manifest"
id() { echo "$TEST_UID"; }
getprop() {
 case "$1" in
 ro.bootmode) echo "$TEST_BOOTMODE";; ro.twrp.boot) echo "$TEST_TWRP";;
 ro.product.vendor.device) echo "$TEST_DEVICE";; sys.boot_completed) echo "$TEST_BOOTED";;
 esac
}
setprop() { echo "$*" >> "$FIXTURE/trace"; }
timeout() { echo "check:$*" >> "$FIXTURE/trace"; return "$TEST_CHECK"; }
start_crypto
exit $?
'''
            p=subprocess.run(['sh','-c',commands,'test',str(SCRIPT)],env=environment,capture_output=True,text=True)
            trace=(root/'trace').read_text().splitlines() if (root/'trace').exists() else []
            return p.returncode,trace
    def test_success_orders_services_before_keystore_signal(self):
        code,trace=self.run_case()
        self.assertEqual(code,0)
        self.assertEqual(trace,['ctl.start fogona-qseecomd','ctl.start fogona-keymint',
            'check:-s KILL 3 fogona-check-keymint','fogona.crypto.keymint.ready 1'])
    def test_timeout_stops_both_services_and_never_signals_ready(self):
        code,trace=self.run_case(check=137)
        self.assertEqual(code,5)
        self.assertEqual(trace[-2:],['ctl.stop fogona-keymint','ctl.stop fogona-qseecomd'])
        self.assertNotIn('fogona.crypto.keymint.ready 1',trace)
    def test_normal_android_rejected(self): self.assertEqual(self.run_case(bootmode='normal'),(2,[]))
    def test_booted_android_rejected(self): self.assertEqual(self.run_case(booted='1'),(2,[]))
    def test_nonroot_rejected(self): self.assertEqual(self.run_case(uid=2000),(2,[]))
    def test_rw_vendor_rejected(self): self.assertEqual(self.run_case(mount='rw,seclabel'),(3,[]))
    def test_missing_library_rejected(self): self.assertEqual(self.run_case(missing_library=True),(3,[]))
    def test_missing_manifest_rejected(self): self.assertEqual(self.run_case(missing_manifest=True),(3,[]))
if __name__=='__main__': unittest.main()
