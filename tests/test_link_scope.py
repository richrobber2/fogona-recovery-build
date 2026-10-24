import ast
from pathlib import Path
import subprocess
import unittest

BASE=Path(__file__).resolve().parents[1]
TREE=ast.parse((BASE/'patch-build.py').read_text())
VALUES={t.id:ast.literal_eval(n.value) for n in TREE.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) for t in n.targets if isinstance(t,ast.Name)}
P='LINK_TYPE:TARGET:_:_:EXECUTABLES:recovery'
C='LINK_TYPE:TARGET:_:_:SHARED_LIBRARIES:crypto'
U='LINK_TYPE:TARGET:_:_:SHARED_LIBRARIES:unrelated'
M='LINK_TYPE:TARGET:_:_:SHARED_LIBRARIES:absent'

class LinkScopeTests(unittest.TestCase):
    def check_graph(self,parent_deps='',child_deps='',unused_deps=''):
        source='''empty :=
space := $(empty) $(empty)
TARGET_OS := android
define link-type-name
$(word 6,$(subst :,$(space),$(1)))
endef
echo-error = printf '%s\\n' '$(2)' >&2
verify-link-type =
_fogona_reachable := recovery
ALL_LINK_TYPES := '''+' '.join([P,C,U])+'\n'
        for index,(node,deps) in enumerate([(P,parent_deps),(C,child_deps),(U,unused_deps)]):
            source+=f'N{index} := {node}\n$(N{index}).TYPE := native\n$(N{index}).MAKEFILE := fixture.mk\n$(N{index}).DEPS := {deps}\n'
        source+=VALUES['compat_links']+'\n'+VALUES['compat_missing']+'''
$(foreach lt,$(ALL_LINK_TYPES),$(foreach d,$($(lt).DEPS),$(if $($(d).TYPE),$(call verify-link-type,$(lt),$(d)),$(call link-type-missing,$(lt),$(d)))))
ifdef link_type_error
$(error Missing linked recovery dependency)
endif
all:
	@:
'''
        return subprocess.run(['make','--no-print-directory','-s','-f','-'],input=source,text=True,capture_output=True,timeout=10)

    def test_valid_graph(self):
        p=self.check_graph(parent_deps=C);self.assertEqual(p.returncode,0,p.stderr)

    def test_direct_missing_library(self):
        p=self.check_graph(parent_deps=M);self.assertNotEqual(p.returncode,0);self.assertIn('missing absent',p.stderr)

    def test_transitive_missing_library(self):
        p=self.check_graph(parent_deps=C,child_deps=M);self.assertNotEqual(p.returncode,0);self.assertIn('crypto missing absent',p.stderr)

    def test_unused_missing_library_is_not_selected(self):
        p=self.check_graph(parent_deps=C,unused_deps=M);self.assertEqual(p.returncode,0,p.stderr)

    def test_cycle_terminates(self):
        p=self.check_graph(parent_deps=C,child_deps=P);self.assertEqual(p.returncode,0,p.stderr)

if __name__=='__main__':
    unittest.main()
