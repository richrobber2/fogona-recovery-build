Experimental fogona recovery build

Public build workspace controlled from the phone, using standard GitHub-hosted runners. Device tree derived from d1g0l3b1ck/twrp_motorola_fogona at197d653f7daf334451148aece7add1e0be6d265d with local rescue changes. See device/PORTING.txt for hardware and rollback limitations. boot.img.gz contains this phone's matching stock boot partition, published with explicit permission; no userdata or patched init_boot/Magisk image is included.

Manual Actions builds only, recoveryimage target only. No flashing or releases. Source revisions are recorded in the resolved manifest; dependency branches may advance between runs. Source repair inputs are SHA256-pinned and any change requires review before patching.

Dependency validation follows the recovery image's build graph. Upstream deferred missing-dependency handling allows omitted, unused OS/test packages in the minimal manifest. A mandatory Make check traverses REQUIRED edges from recovery-installed modules and explicit recovery/ramdisk/relink roots; a second check follows their native-link dependency graph. Missing reachable requirements or linked modules fail. Soong also emits Ninja error rules for reachable modules with missing dependencies (android/module.go at c6c059ab28c8c67921c0838a994bb70d53594aa7, lines2207-2209). Thirteen tests exercise direct/transitive missing edges, host tools, installed roots, cycles and unused packages. No blanket metadata exception list or unused-makefile pruning is applied.

Obsolete TWRP module names and legacy relink-only entries are repaired in patch-build.py. Current libvold/keystore2 and wrapped-key decryption configuration remain enabled. FOGONA_RECOVERY_BUILD=true prevents generation of HIDL VTS-only driver/profiler/fuzzer modules whose framework is absent; normal HAL libraries remain generated. This is an offline rescue recovery, without a Wi-Fi userspace or live Codex client.

After compilation, the staged ramdisk audit requires essential binaries and the rescue helper, ARM64 critical executables, executable modes, and ELF dependency name/architecture closure. The helper must match its source. Image size and SHA256 are recorded. These checks do not prove Android linker namespace, vendor HAL, decryption, AVB acceptance, display, touch, charging or boot compatibility. The phone-only rollback path remains unverified, and no image is ready to flash based on compilation alone.

CI runs the dependency-graph tests with GNU Make before sync and Android's exact prebuilt Kati after sync. Traversal side effects run in assignment context; unexpected returned text is rejected explicitly. A local AOSP Kati build also passes the13 fixtures, but only the full remote Android graph can validate integration.

The phone-only fallback tool tools/restore-stock-recovery.sh defaults to a read-only backup/target check. Its explicit --restore action is limited to the verified stock recovery_a backup on this phone/slot and has not been executed on a physical partition. Twelve device-local fixture tests pass with both Termux tools and Android toybox; they are skipped on other environments. A real read-only check confirmed that the phone's recovery_a still matches its stock backup. The physical bootloader START path back to Android still needs confirmation before any trial; this tool cannot help while normal Android is unavailable.


Current crypto-startup investigation

The current locally stock-packaged image boots with working touch, mounts
vendor read-only and saves logs in metadata. Userdata decryption still fails.
A private isolated probe reproduced an exact mismatch: vendor manifest schema
5.0 is rejected by Android 12.1 libvintf (schema 4.0), after which keystore2's
VINTF wrapper dereferences the null manifest. Full Binder/HAL behavior has not
been reproduced by that focused probe.

support.xml now pins the complete Android 13 libvintf source project at
96bcbaf82bde249b6f5ea1dc654abfebdca9b86b. Its parser supports schema 5.0;
consumers are rebuilt from source. This is a scoped library source upgrade,
not an Android 13 migration of the entire recovery. No vendor XML versions
are edited. patch-build.py adds null guards to the four pinned keystore2 FFI
entrypoints, returning allocated empty results without inventing HAL instances.

The host-only fogona-vintf-parser-test exercises schema 4/5, KeyMint v2
compatibility with v1/v2 clients, and rejection of v3/malformed/future input.
tests/test_vintf_wrapper.py compiles the actual patched wrapper against
controlled null/available manifests and checks all four FFI paths and cleanup.
These tests do not prove Android ABI, hardware HAL startup or decryption.

The existing five-second vold deadline bounds service-registration polling
only; later Binder transactions remain unbounded. No format, key-generation
or key-deletion fallback is added. Logd/logcat and metadata diagnostics remain.

CI artifacts remain experimental. Stock packaging and the device-local matching
touch firmware/module overlay are required before any physical trial; those
private device inputs are not included in this public repository. Physical
bootloader START fallback has been tested; stock restoration from Android has
only been checked read-only. No flashing is performed by the workflow.
