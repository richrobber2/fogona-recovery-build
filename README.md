Experimental fogona recovery build

Public build workspace controlled from the phone, using standard GitHub-hosted runners. Device tree derived from d1g0l3b1ck/twrp_motorola_fogona at197d653f7daf334451148aece7add1e0be6d265d with local rescue changes. See device/PORTING.txt for hardware and rollback limitations. boot.img.gz contains this phone's matching stock boot partition, published with explicit permission; no userdata or patched init_boot/Magisk image is included.

Manual Actions builds only, recoveryimage target only. No flashing or releases. Source revisions are recorded in the resolved manifest; dependency branches may advance between runs. Source repair inputs are SHA256-pinned and any change requires review before patching.

Dependency validation follows the recovery image's build graph. Upstream deferred missing-dependency handling allows omitted, unused OS/test packages in the minimal manifest. A mandatory Make check traverses REQUIRED edges from recovery-installed modules and explicit recovery/ramdisk/relink roots; a second check follows their native-link dependency graph. Missing reachable requirements or linked modules fail. Soong also emits Ninja error rules for reachable modules with missing dependencies (android/module.go at c6c059ab28c8c67921c0838a994bb70d53594aa7, lines2207-2209). Thirteen tests exercise direct/transitive missing edges, host tools, installed roots, cycles and unused packages. No blanket metadata exception list or unused-makefile pruning is applied.

Obsolete TWRP module names and legacy relink-only entries are repaired in patch-build.py. Current libvold/keystore2 and wrapped-key decryption configuration remain enabled. FOGONA_RECOVERY_BUILD=true prevents generation of HIDL VTS-only driver/profiler/fuzzer modules whose framework is absent; normal HAL libraries remain generated. This is an offline rescue recovery, without a Wi-Fi userspace or live Codex client.

After compilation, the staged ramdisk audit requires essential binaries and the rescue helper, ARM64 critical executables, executable modes, and ELF dependency name/architecture closure. The helper must match its source. Image size and SHA256 are recorded. These checks do not prove Android linker namespace, vendor HAL, decryption, AVB acceptance, display, touch, charging or boot compatibility. The phone-only rollback path remains unverified, and no image is ready to flash based on compilation alone.

CI runs the dependency-graph tests with GNU Make before sync and Android's exact prebuilt Kati after sync. Traversal side effects run in assignment context; unexpected returned text is rejected explicitly. A local AOSP Kati build also passes the13 fixtures, but only the full remote Android graph can validate integration.

The phone-only fallback tool tools/restore-stock-recovery.sh defaults to a read-only backup/target check. Its explicit --restore action is limited to the verified stock recovery_a backup on this phone/slot and has not been executed on a physical partition. Twelve device-local fixture tests pass with both Termux tools and Android toybox; they are skipped on other environments. A real read-only check confirmed that the phone's recovery_a still matches its stock backup. The physical bootloader START path back to Android still needs confirmation before any trial; this tool cannot help while normal Android is unavailable.


Current crypto-startup investigation

A stock-packaged local image has booted with working touch and persistent
metadata logs. A later storage correction mounted vendor successfully but
stalled entering metadata decryption; the device was restored to that tested
image. The cause has not yet been proven from service logs.

This branch adds a five-second service-registration polling deadline in vold's
Keymaster constructor. It does not bound later Binder transactions or guarantee
hardware-backed decryption. Keystore2 is explicitly started by the recovery
init configuration; missing registration now returns an unavailable wrapper
instead of waiting indefinitely. Ready services still follow the original
crypto path. No format, key-generation or key-deletion fallback is added.

Logd/logcat are built from matching sources and required by the staged audit.
The metadata snapshot helper records mounts, init properties and processes,
retains early kernel output, and replaces stale status on partial failure.
The header uses injected clock/check functions for focused native tests; full
Android compilation and device runtime verification are still required.

CI artifacts remain experimental. Stock packaging and the device-local matching
touch firmware/module overlay are required before any physical trial; those
private device inputs are not included in this public repository.
