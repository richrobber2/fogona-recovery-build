Experimental fogona recovery build

Public experimental build workspace controlled from the phone. Standard public GitHub-hosted runners are used. Device tree derived from d1g0l3b1ck/twrp_motorola_fogona at 197d653f7daf334451148aece7add1e0be6d265d with local rescue changes. See device/PORTING.txt for unresolved hardware and rollback limitations. boot.img.gz contains this phone’s matching boot partition, no userdata or init_boot/Magisk image.

Manual Actions builds only, recoveryimage target only, no flashing or releases. A successful compile does not establish boot, touch, decryption or AVB compatibility. Source revisions are recorded in the resolved manifest; branch dependencies may advance between runs. Standard runner disk/RAM may limit builds. No paid runner is requested.

Compatibility repairs are pinned by source SHA256 in patch-build.py. Obsolete recovery module names are corrected to real modules. Removed libraries are legacy relink-list entries, not linker dependencies; current libvold/keystore2 remain enabled. ALLOW_MISSING_DEPENDENCIES stays false. The global metadata checker has25 exact exclusions for unused framework/host-test edges pruned from the minimal source tree; every unlisted missing requirement remains fatal. This is a documented exception to global metadata validation, not proof of recovery runtime compatibility.

The staged ramdisk audit requires essential binaries and the rescue helper, ARM64 critical executables, executable modes, and ELF dependency name/architecture closure. It does not prove Android linker namespace, hardware HAL, decryption, AVB or boot compatibility. No image should be flashed based on compilation alone.
