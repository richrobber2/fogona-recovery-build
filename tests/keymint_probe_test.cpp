// SPDX-License-Identifier: Apache-2.0
// Linker wrappers test the real registration probe without Android Binder.
#include <cassert>
#include <cstring>
#include <cstdio>
struct AIBinder {};
int fogona_probe_main();
static int scenario, checks, references, releases, closes;
static AIBinder binder;
static AIBinder* check(const char* name) {
    assert(std::strcmp(name,"android.hardware.security.keymint.IKeyMintDevice/default")==0);
    ++checks;
    if(scenario==2) {++references;return &binder;}
    return nullptr;
}
static void release(AIBinder* object) {
    assert(object==&binder && references==1);
    --references;++releases;
}
extern "C" void* __wrap_dlopen(const char* name,int) {
    assert(std::strcmp(name,"/system/lib64/libbinder_ndk.so")==0);
    return scenario==0 ? nullptr : reinterpret_cast<void*>(1);
}
extern "C" char* __wrap_dlerror() {return const_cast<char*>("fixture: unavailable");}
extern "C" void* __wrap_dlsym(void*,const char* name) {
    if(scenario==1)return nullptr;
    if(std::strcmp(name,"AServiceManager_checkService")==0)return reinterpret_cast<void*>(check);
    if(std::strcmp(name,"AIBinder_decStrong")==0)return reinterpret_cast<void*>(release);
    assert(false);return nullptr;
}
extern "C" int __wrap_dlclose(void*) {
    assert(references==0);++closes;return 0;
}
int main() {
    for(scenario=0;scenario<4;++scenario) {
        checks=references=releases=closes=0;
        const int result=fogona_probe_main();
        assert(result==(scenario<2 ? 2 : scenario==2 ? 0 : 1));
        assert(references==0 && closes==(scenario==0 ? 0 : 1));
        if(scenario==2)assert(checks==1 && releases==1);
        if(scenario==3)assert(checks>1 && releases==0);
    }
    std::puts("PASS: absent library/API, registered/released Binder, unavailable-service timeout");
}
