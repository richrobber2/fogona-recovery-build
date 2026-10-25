#!/usr/bin/env python3
"""Compile the actual patched wrapper against controlled manifest lookup results.

This tests the FFI null/allocation contract, not Android's XML parser or Binder.
Run after patch-build.py: python3 tests/test_vintf_wrapper.py android
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).resolve() / 'system/security/keystore2/src/vintf/vintf.cpp'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'vintf').mkdir()
    (root / 'vintf/HalManifest.h').write_text(r'''
#pragma once
#include <cstring>
#include <cstdlib>
#include <memory>
#include <set>
#include <string>
namespace android { namespace vintf {
struct Version { Version(size_t, size_t) {} };
struct HalManifest {
    std::set<std::string> getHalNames() const { return {"test.hal"}; }
    std::set<std::string> getHalNamesAndVersions() const { return {"test.hal@1.0"}; }
    std::set<std::string> getHidlInstances(const char*, Version, const char*) const { return {"hidl"}; }
    std::set<std::string> getAidlInstances(const char*, size_t, const char*) const { return {"aidl"}; }
};
}} // namespace
''')
    (root / 'vintf/VintfObject.h').write_text(r'''
#pragma once
#include "HalManifest.h"
namespace android { namespace vintf {
inline bool available = false;
struct VintfObject {
    static std::shared_ptr<HalManifest> GetDeviceHalManifest() {
        return available ? std::make_shared<HalManifest>() : nullptr;
    }
};
}}
''')
    (root / 'main.cpp').write_text(r'''
#include "vintf.hpp"
#include <vintf/VintfObject.h>
#include <cstdio>
static int failures = 0;
static void check(char** names, size_t count, const char* expected) {
    if (!names || count != (expected ? 1u : 0u) ||
            (expected && std::strcmp(names[0], expected))) ++failures;
    freeNames(names, count);
}
int main() {
    for (bool ready : {false, true, false}) {
        android::vintf::available = ready;
        size_t count = 123;
        auto names = getHalNames(&count);
        check(names, count, ready ? "test.hal" : nullptr);
        count = 123;
        names = getHalNamesAndVersions(&count);
        check(names, count, ready ? "test.hal@1.0" : nullptr);
        count = 123;
        names = getHidlInstances(&count, "test", 1, 0, "ITest");
        check(names, count, ready ? "hidl" : nullptr);
        count = 123;
        names = getAidlInstances(&count, "test", 2, "ITest");
        check(names, count, ready ? "aidl" : nullptr);
    }
    if (!failures) std::puts("PASS: 12 FFI cases, null/available/null manifests and freeNames");
    return failures ? 1 : 0;
}
''')
    compiler = os.environ.get('CXX', 'clang++')
    subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-Wno-sign-compare', '-I'+str(root), '-I'+str(source.parent),
                    str(source), str(root/'main.cpp'), '-o', str(root/'test')], check=True)
    subprocess.run([str(root/'test')], check=True)
