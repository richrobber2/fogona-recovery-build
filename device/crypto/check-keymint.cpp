// SPDX-License-Identifier: Apache-2.0
// Registration check only; no key creation, security-level RPC or HAL invocation.
// Android 12 does not expose a recovery build variant of libbinder_ndk. Load
// the matching copy already packaged for keystore rather than mixing variants.
#include "FogonaKeystoreWait.h"
#include <cstdio>
#include <dlfcn.h>
#include <memory>
#include <thread>
struct AIBinder;
int main() {
    void* library = dlopen("/system/lib64/libbinder_ndk.so", RTLD_NOW);
    if (!library) {
        std::fprintf(stderr, "Cannot load Binder NDK: %s\n", dlerror());
        return 2;
    }
    auto check = reinterpret_cast<AIBinder* (*)(const char*)>(
        dlsym(library, "AServiceManager_checkService"));
    auto release = reinterpret_cast<void (*)(AIBinder*)>(dlsym(library, "AIBinder_decStrong"));
    if (!check || !release) {
        std::fprintf(stderr, "Binder NDK registration API missing\n");
        dlclose(library);
        return 2;
    }
    auto service = fogona::WaitForKeystore(
        [check, release] {
            AIBinder* binder = check("android.hardware.security.keymint.IKeyMintDevice/default");
            return binder ? std::shared_ptr<AIBinder>(binder, release) : std::shared_ptr<AIBinder>{};
        },
        [] { return std::chrono::steady_clock::now(); },
        [](std::chrono::steady_clock::duration delay) { std::this_thread::sleep_for(delay); },
        std::chrono::milliseconds(2500), std::chrono::milliseconds(50));
    const bool ready = service.get() != nullptr;
    service.reset();
    dlclose(library);
    if (!ready) {
        std::fprintf(stderr, "KeyMint did not register within 2500ms\n");
        return 1;
    }
    std::puts("KeyMint default registered");
    return 0;
}
