"""Exercise the exact Make closure emitted by patch-build.py, including failures."""
import ast
from pathlib import Path
import subprocess
import unittest

BASE=Path(__file__).resolve().parents[1]
TREE=ast.parse((BASE/'patch-build.py').read_text())
COMPAT=next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='compat' for t in n.targets))
ROOTS='recovery twrp_ramdisk relink_libraries relink_binaries relink_vendor_hw_binaries'

class RequiredScopeTests(unittest.TestCase):
    def run_make(self, fields='', missing='', extra_modules=''):
        source='''empty :=
space := $(empty) $(empty)
comma := ,
TARGET_PRODUCT := twrp_fogona
TARGET_RECOVERY_ROOT_OUT := out/recovery/root
ALL_MODULES := '''+ROOTS+' core crypto outsider custom hosttool '+extra_modules+'''
ALL_MODULES.recovery.REQUIRED_FROM_TARGET := core
ALL_MODULES.core.REQUIRED_FROM_TARGET := crypto
'''+fields+'\n_nonexistent_required := '+missing+'\n'+COMPAT+'\nall:\n\t@:\n'
        return subprocess.run(['make','--no-print-directory','-s','-f','-'],input=source,text=True,capture_output=True,timeout=10)

    def test_valid_closure(self):
        p=self.run_make();self.assertEqual(p.returncode,0,p.stderr);self.assertIn('missing=0',p.stdout)

    def test_direct_missing(self):
        p=self.run_make(missing='TARGET,recovery,TARGET,absent')
        self.assertNotEqual(p.returncode,0);self.assertIn('Missing required recovery modules',p.stderr)

    def test_transitive_missing(self):
        self.assertNotEqual(self.run_make(missing='TARGET,crypto,TARGET,absent').returncode,0)

    def test_unrelated_missing_does_not_block_image(self):
        p=self.run_make(missing='TARGET,outsider,TARGET,unused_cts_default')
        self.assertEqual(p.returncode,0,p.stderr)

    def test_recovery_installed_module_is_root(self):
        p=self.run_make(fields='ALL_MODULES.custom.INSTALLED := out/recovery/root/system/bin/custom\n',missing='TARGET,custom,TARGET,absent')
        self.assertNotEqual(p.returncode,0)

    def test_required_host_tool_is_checked(self):
        p=self.run_make(fields='ALL_MODULES.crypto.HOST_REQUIRED_FROM_TARGET := hosttool\n',missing='HOST,hosttool,HOST,absent')
        self.assertNotEqual(p.returncode,0)

    def test_cycle_terminates(self):
        p=self.run_make(fields='ALL_MODULES.crypto.REQUIRED_FROM_TARGET := recovery\n')
        self.assertEqual(p.returncode,0,p.stderr)

    def test_missing_root_is_fatal(self):
        p=self.run_make(fields='ALL_MODULES := recovery core crypto\n')
        self.assertNotEqual(p.returncode,0);self.assertIn('Missing recovery root modules',p.stderr)

if __name__=='__main__':
    unittest.main()
