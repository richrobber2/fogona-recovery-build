#!/usr/bin/env python3
"""Fail-closed, pinned compatibility repairs for the recovery-only source tree."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(sys.argv[1])
expected = {
    'system/libvintf/test/Android.bp': '35f754eacadcca3f29fe05d40986f252ed1c1babc40dc70da73dd1192ad27517',
    'system/security/keystore2/src/vintf/vintf.cpp': '0a309133335bce63a0e5fbd0f240ae700e530efb24aac60bc763efde756c9520',
    'system/vold/Keymaster.cpp': '0dd4d451a3ba35daf73beb59605b49afb9d78beb4fdd5c046d531aee3adbf3c7',
    'system/tools/hidl/build/hidl_interface.go': '1cd012ba9e55c17fca85bda47d07dfb717acb9148c0dc6d842713614e4dd04b2',
    'build/make/core/main.mk': '971b6dc659ea8f78212017223d0531e2520e74894d947f028c683277e83a52ce',
    'bootable/recovery/Android.mk': '1d6f16957effa23e9323c2a40dd52ee7c809d571302becea774d1a89044e6f31',
    'bootable/recovery/prebuilt/Android.mk': '0d3545ba282e63099c689f31df41dd44d021bd042b00338fb16a8612a6e64cb5',
}
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

# Android 12 Soong predates this Android 13 clang-tidy timeout metadata.
# Remove only the unsupported lint scheduling property, preserving test sources
# and all parser/runtime behavior. Do not suppress test/build failures.
for source in ['LibVintfTest.cpp', 'vintf_object_tests.cpp']:
    replace('system/libvintf/test/Android.bp',
            '    tidy_timeout_srcs: [\n        "' + source + '",\n    ],\n', '')

# libvintf returns a null manifest on missing or rejected vendor XML. Keep the
# FFI result allocated even when empty: Rust's slice contract requires a nonnull
# aligned pointer for zero-length slices too. Do not fabricate HAL instances.
replace('system/security/keystore2/src/vintf/vintf.cpp',
        '    auto manifest = android::vintf::VintfObject::GetDeviceHalManifest();\n',
        '    auto manifest = android::vintf::VintfObject::GetDeviceHalManifest();\n'
        '    if (!manifest) {\n'
        '        *len = 0;\n'
        '        return convert({});\n'
        '    }\n', 4)

# Recovery has an explicitly started keystore2. Do not let an absent/crashed
# service leave startup waiting forever. This does not bound later Binder calls.
replace('system/vold/Keymaster.cpp', '#include "Keymaster.h"\n',
        '#include "Keymaster.h"\n#include "FogonaKeystoreWait.h"\n#include <thread>\n')
replace('system/vold/Keymaster.cpp',
        '    ::ndk::SpAIBinder binder(AServiceManager_waitForService(keystore2_service_name));\n',
        '''    auto binder = fogona::WaitForKeystore(
            [] { return ::ndk::SpAIBinder(AServiceManager_checkService(keystore2_service_name)); },
            [] { return std::chrono::steady_clock::now(); },
            [](std::chrono::steady_clock::duration delay) { std::this_thread::sleep_for(delay); },
            std::chrono::milliseconds(5000), std::chrono::milliseconds(100));
    if (binder.get() == nullptr) {
        LOG(ERROR) << "Recovery keystore2 unavailable after 5 seconds; metadata decrypt aborted";
        return;
    }
''')
helper = Path(__file__).parent / 'tools/keystore-service-wait.h'
helper_target = root / 'system/vold/FogonaKeystoreWait.h'
if helper_target.exists():
    raise SystemExit('Unexpected existing FogonaKeystoreWait.h')
changes.append({'file': 'system/vold/FogonaKeystoreWait.h',
                'source': 'tools/keystore-service-wait.h',
                'sha256': hashlib.sha256(helper.read_bytes()).hexdigest()})

# HIDL generates VTS fuzzers even when their test framework is pruned. Do not
# emit test-only driver/profiler/fuzzer modules for this explicit recovery job.
replace('system/tools/hidl/build/hidl_interface.go',
        '\tshouldGenerateVts := shouldGenerateLibrary && proptools.BoolDefault(i.properties.Gen_vts, true)\n',
        '\tshouldGenerateVts := shouldGenerateLibrary && proptools.BoolDefault(i.properties.Gen_vts, true) && mctx.Config().Getenv("FOGONA_RECOVERY_BUILD") != "true"\n')

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
# Pinned Android12 logcat uses libbase/libprocessgroup and a static liblog.
# Older TWRP relink lists reference removed or unused logging libraries.
for module in ['libnl', 'libpcrecpp', 'liblogcat']:
    replace(pre, 'RECOVERY_LIBRARY_SOURCE_FILES += $(TARGET_OUT_SHARED_LIBRARIES)/' + module + '.so\n', '')
# event-log-tags is a generated Make target, not an ALL_MODULES entry.
# The device's real ETC module packages its output and owns the dependency.
replace(mk, '    TWRP_REQUIRED_MODULES += logcat event-log-tags',
        '    TWRP_REQUIRED_MODULES += logcat fogona-event-log-tags')
replace(mk, '        TWRP_REQUIRED_MODULES += logd libsysutils libnl init.recovery.logd.rc',
        '        TWRP_REQUIRED_MODULES += logd libsysutils init.recovery.logd.rc')
replace(pre, '    plat_hardware_contexts \\\n', '')  # typo; real hwservice contexts remain
# Relink file basenames must be mapped to the actual module names.
replace(pre, 'LOCAL_REQUIRED_MODULES += $(TARGET_BINARY_RELINK_FILES)', '''TARGET_BINARY_RELINK_MODULES := $(filter-out twrp ueventd unzip,$(TARGET_BINARY_RELINK_FILES))
TARGET_BINARY_RELINK_MODULES += orscmd init_second_stage.recovery ziptool.recovery
LOCAL_REQUIRED_MODULES += $(TARGET_BINARY_RELINK_MODULES)''')

# The minimal manifest deliberately omits unrelated OS/test packages. Use
# upstream deferred missing-dependency handling, then enforce REQUIRED closure
# for every recovery-installed module and the recovery/relink/ramdisk roots.
# Missing linked dependencies reachable by Ninja still produce error rules.
compat = r"""
# Fogona's recovery-only REQUIRED closure; never suppress missing image tools.
ifeq ($(TARGET_PRODUCT),twrp_fogona)
_fogona_reachable :=
define fogona-expand-required
$(eval _fogona_new := $(filter-out $(_fogona_reachable),$(1)))
$(if $(_fogona_new), \
  $(eval _fogona_reachable += $(_fogona_new)) \
  $(call fogona-expand-required,$(sort $(foreach m,$(_fogona_new), \
    $(ALL_MODULES.$(m).REQUIRED_FROM_TARGET) \
    $(ALL_MODULES.$(m).REQUIRED_FROM_HOST) \
    $(ALL_MODULES.$(m).HOST_REQUIRED_FROM_TARGET) \
    $(ALL_MODULES.$(m).TARGET_REQUIRED_FROM_HOST)))))
endef
_fogona_roots := recovery twrp_ramdisk relink_libraries relink_binaries relink_vendor_hw_binaries
_fogona_roots += $(foreach m,$(ALL_MODULES),$(if $(filter $(TARGET_RECOVERY_ROOT_OUT)/%,$(ALL_MODULES.$(m).INSTALLED)),$(m)))
ifneq ($(strip $(filter-out $(ALL_MODULES),$(_fogona_roots))),)
$(error Missing recovery root modules: $(filter-out $(ALL_MODULES),$(_fogona_roots)))
endif
_fogona_required_walk_output := $(strip $(call fogona-expand-required,$(_fogona_roots)))
ifneq ($(_fogona_required_walk_output),)
$(error Unexpected recovery REQUIRED traversal output: $(_fogona_required_walk_output))
endif
_fogona_missing := $(foreach edge,$(_nonexistent_required),$(if $(filter $(word 2,$(subst $(comma),$(space),$(edge))),$(_fogona_reachable)),$(edge)))
$(info FOGONA_REQUIRED_MODULE_AUDIT: reachable=$(words $(_fogona_reachable)) missing=$(words $(_fogona_missing)))
$(info FOGONA_REQUIRED_MODULES: $(sort $(_fogona_reachable)))
ifneq ($(strip $(_fogona_missing)),)
$(foreach edge,$(_fogona_missing),$(info Missing recovery REQUIRED edge: $(edge)))
$(error Missing required recovery modules)
endif
endif
"""
replace('build/make/core/main.mk', 'check_missing_required_modules := true\n', compat + '\ncheck_missing_required_modules := true\n')
# Keep Make native-link dependency validation strict over the same image scope,
# including transitive static/shared libraries and required host tools.
compat_links = r"""
_fogona_link_reachable :=
define fogona-expand-links
$(eval _fogona_new_links := $(filter-out $(_fogona_link_reachable),$(1)))
$(if $(_fogona_new_links), \
  $(eval _fogona_link_reachable += $(_fogona_new_links)) \
  $(call fogona-expand-links,$(sort $(foreach lt,$(_fogona_new_links),$($(lt).DEPS)))))
endef
_fogona_link_roots := $(foreach lt,$(ALL_LINK_TYPES),$(if $(filter $(call link-type-name,$(lt)),$(_fogona_reachable)),$(lt)))
_fogona_link_walk_output := $(strip $(call fogona-expand-links,$(_fogona_link_roots)))
ifneq ($(_fogona_link_walk_output),)
$(error Unexpected recovery link traversal output: $(_fogona_link_walk_output))
endif
$(info FOGONA_LINK_MODULE_AUDIT: reachable=$(words $(_fogona_link_reachable)))
"""
compat_missing = r"""  define link-type-missing
    $(if $(filter $(1),$(_fogona_link_reachable)), \
      $(shell $(call echo-error,$($(1).MAKEFILE),"Recovery dependency $(call link-type-name,$(1)) missing $(call link-type-name,$(2))")) \
      $(eval link_type_error := true), \
      $(eval $$(1).MISSING := true))
  endef"""
replace('build/make/core/main.mk', '  define link-type-missing\n    $(eval $$(1).MISSING := true)\n  endef', compat_missing)
replace('build/make/core/main.mk', '$(foreach lt,$(ALL_LINK_TYPES),\\\n', compat_links + '\n$(foreach lt,$(ALL_LINK_TYPES),\\\n')
helper_target.write_bytes(helper.read_bytes())
for name, text in contents.items():
    (root / name).write_text(text)
Path('compatibility-repairs.json').write_text(json.dumps({'changes': changes, 'validation_scope': 'Recursive REQUIRED closure from recovery-installed modules and explicit ramdisk/relink roots; Ninja errors for missing reachable linked modules; staged ELF/content audit.'}, indent=2) + '\n')
print(f'Applied {len(changes)} pinned source repairs; recovery-scoped required-module validation enabled.')
