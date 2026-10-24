#!/usr/bin/env python3
"""Fail-closed, pinned compatibility repairs for the recovery-only source tree."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(sys.argv[1])
expected = {
    'build/make/core/main.mk': '971b6dc659ea8f78212017223d0531e2520e74894d947f028c683277e83a52ce',
    'bootable/recovery/Android.mk': '1d6f16957effa23e9323c2a40dd52ee7c809d571302becea774d1a89044e6f31',
    'bootable/recovery/prebuilt/Android.mk': '0d3545ba282e63099c689f31df41dd44d021bd042b00338fb16a8612a6e64cb5',
}
pruned_files = json.loads((Path(__file__).parent / 'pruned-makefiles.json').read_text())
expected.update({entry['path']: entry['sha256'] for entry in pruned_files})
contents = {}
for name, digest in expected.items():
    data = (root / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit(f'Upstream changed; review before applying compatibility patch: {name}')
    contents[name] = data.decode()
changes = []

def replace(name, old, new, count=1):
    text = contents[name]
    if text.count(old) != count:
        raise SystemExit(f'Expected {count} occurrences in {name}: {old!r}')
    contents[name] = text.replace(old, new)
    changes.append({'file': name, 'old': old, 'new': new})

mk = 'bootable/recovery/Android.mk'
# orscmd is the module; twrp is its installed executable stem.
replace(mk, '    teamwin \\\n', '')  # abandoned declaration with no BUILD rule
replace(mk, '    twrp \\\n', '    orscmd \\\n')
# No such script exists upstream. Do not invent a permissive SELinux script.
replace(mk, '    permissive.sh \\\n', '')
# libvold/fscryptpolicyget contain the current FBE implementation.
replace(mk, '    fscryptpolicyget.recovery \\\n', '    fscryptpolicyget \\\n')
replace(mk, '    keystore_auth \\\n', '')  # removed legacy auth executable; keystore2 remains
replace(mk, '    task_recovery_profiles.json \\\n', '    task_profiles.json \\\n')
replace(mk, '        fs_mgr \\\n', '')  # only libfs_mgr is defined in this branch

pre = 'bootable/recovery/prebuilt/Android.mk'
for module in ['keystore', 'keystore_auth', 'keystore_cli']:
    line = 'RECOVERY_BINARY_SOURCE_FILES += $(TARGET_OUT_EXECUTABLES)/' + module + '\n'
    # Indentation is intentionally preserved by replacing only the line body.
    replace(pre, line, '', 2 if module == 'keystore' else 1)
for module in ['libbinderthreadstate', 'libminadbd', 'libcryptfsfde', 'libtwrpfscrypt', 'libsoftkeymaster', 'libstatslog']:
    replace(pre, 'RECOVERY_LIBRARY_SOURCE_FILES += $(TARGET_' + ('RECOVERY_ROOT_OUT)/system/lib64/' if module == 'libbinderthreadstate' else 'OUT_SHARED_LIBRARIES)/') + module + '.so\n', '')
replace(pre, '    plat_hardware_contexts \\\n', '')  # typo; real hwservice contexts remain
# Relink file basenames must be mapped to the actual module names.
replace(pre, 'LOCAL_REQUIRED_MODULES += $(TARGET_BINARY_RELINK_FILES)', '''TARGET_BINARY_RELINK_MODULES := $(filter-out twrp ueventd unzip,$(TARGET_BINARY_RELINK_FILES))
TARGET_BINARY_RELINK_MODULES += orscmd init_second_stage.recovery ziptool.recovery
LOCAL_REQUIRED_MODULES += $(TARGET_BINARY_RELINK_MODULES)''')

# AOSP's global metadata scan checks every parsed module, including pruned CTS,
# framework and host-test packages outside the recovery image. Exempt ONLY the
# exact unrelated edges observed in run40079784663. Every new missing edge still
# errors; ALLOW_MISSING_DEPENDENCIES remains false; linking remains strict.
unrelated = '''HOST,brillo_update_payload,HOST,shflags
HOST,domainGeneratorPolicy.py,HOST,domainGeneratorConnector
HOST,linkerconfig,HOST,vndkcorevariant.libraries.txt
HOST,vts-tradefed,HOST,compatibility-host-util
TARGET,FrameworksCoreTests,TARGET,com.android.cts.helpers.aosp
TARGET,PermissionControllerInProcessTests,TARGET,CtsAppThatRequestsLocationPermission29
TARGET,PrintSpoolerOutOfProcessTests,TARGET,com.android.cts.helpers.aosp
TARGET,android.hardware.security.keymint-service,TARGET,RemoteProvisioner
TARGET,android.hardware.security.keymint-service.trusty,TARGET,RemoteProvisioner
TARGET,com.android.runtime,TARGET,vndkcorevariant.libraries.txt
TARGET,com.android.runtime.apex,TARGET,vndkcorevariant.libraries.txt
TARGET,com.android.tethering,TARGET,NetworkPermissionConfig
TARGET,com.android.tethering.apex,TARGET,NetworkPermissionConfig
TARGET,dumpstate,TARGET,ip
TARGET,dumpstate,TARGET,iptables
TARGET,dumpstate,TARGET,ss
TARGET,framework-minus-apex,TARGET,calendar-provider-compat-config
TARGET,framework-minus-apex,TARGET,documents-ui-compat-config
TARGET,framework-minus-apex-intdefs,TARGET,calendar-provider-compat-config
TARGET,framework-minus-apex-intdefs,TARGET,documents-ui-compat-config
TARGET,gpuservice,TARGET,bpfloader
TARGET,librs_jni,TARGET,libRS
TARGET,librs_jni_32,TARGET,libRS
TARGET,linkerconfig,TARGET,vndkcorevariant.libraries.txt
TARGET,netd,TARGET,bpfloader'''.splitlines()
compat = '\n# Pinned fogona recovery-only metadata exceptions; see patch-build.py.\n'
compat += '_fogona_unrelated_metadata_edges := ' + ' '.join(unrelated) + '\n'
compat += '$(foreach edge,$(filter $(_fogona_unrelated_metadata_edges),$(_nonexistent_required)),$(info Excluded non-recovery metadata edge: $(edge)))\n'
compat += '_nonexistent_required := $(filter-out $(_fogona_unrelated_metadata_edges),$(_nonexistent_required))\n'
replace('build/make/core/main.mk', 'check_missing_required_modules := true\n', compat + '\ncheck_missing_required_modules := true\n')
for entry in pruned_files:
    name = entry['path']
    contents[name] = '# Recovery-only pruning; original source retained below.\nifneq ($(TARGET_PRODUCT),twrp_fogona)\n' + contents[name] + '\nendif # non-recovery product\n'
    changes.append({'file': name, 'operation': 'exclude unused Android OS/test makefile for twrp_fogona', 'sha256': entry['sha256']})
for name, text in contents.items():
    (root / name).write_text(text)
Path('compatibility-repairs.json').write_text(json.dumps({'changes': changes, 'non_recovery_metadata_edges': unrelated}, indent=2) + '\n')
print(f'Applied {len(changes)} pinned source repairs; {len(unrelated)} explicit non-recovery metadata edges logged.')
