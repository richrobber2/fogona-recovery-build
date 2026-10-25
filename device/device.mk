#
# Copyright (C) 2024 The Android Open Source Project
# Copyright (C) 2024 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

LOCAL_PATH := device/motorola/fogona
# Export this namespace so Make/Ninja can invoke the host-only parser test.
PRODUCT_SOONG_NAMESPACES += $(LOCAL_PATH)
# A/B
AB_OTA_POSTINSTALL_CONFIG += \
    RUN_POSTINSTALL_system=true \
    POSTINSTALL_PATH_system=system/bin/otapreopt_script \
    FILESYSTEM_TYPE_system=ext4 \
    POSTINSTALL_OPTIONAL_system=true

# Boot control HAL
PRODUCT_PACKAGES += \
    android.hardware.boot@1.0-impl \
    android.hardware.boot@1.0-service

PRODUCT_PACKAGES += \
    bootctrl.bengal \
    libgptutils \
    libz \
    libcutils

PRODUCT_PACKAGES += \
    otapreopt_script \
    cppreopts.sh \
    update_engine \
    update_verifier \
    update_engine_sideload

# Offline rescue, invoked explicitly from the recovery terminal; never auto-runs.
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/recovery/root/system/bin/device-rescue.sh:recovery/root/system/bin/device-rescue.sh

# The branch defines normal task_profiles.json, not task_recovery_profiles.json.
PRODUCT_COPY_FILES += \
    system/core/libprocessgroup/profiles/task_profiles.json:recovery/root/system/etc/task_profiles.json

# Bounded metadata log snapshots; independent of encrypted shared storage.
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/recovery/root/system/bin/recovery-logsave.sh:recovery/root/system/bin/recovery-logsave.sh

# Recovery-only registration probe and startup policy. Matching proprietary
# VNDK files are overlaid privately on-device, never published by this build.
PRODUCT_PACKAGES += fogona-check-keymint fogona-resetprop
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/recovery/root/init.recovery.fogona-crypto.rc:recovery/root/init.recovery.fogona-crypto.rc \
    $(LOCAL_PATH)/recovery/root/system/etc/ld.config.fogona-crypto.txt:recovery/root/system/etc/ld.config.fogona-crypto.txt \
    $(LOCAL_PATH)/recovery/root/system/bin/fogona-crypto-start.sh:recovery/root/system/bin/fogona-crypto-start.sh
