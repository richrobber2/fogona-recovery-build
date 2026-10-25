#
# Copyright (C) 2024 The Android Open Source Project
# Copyright (C) 2024 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

LOCAL_PATH := device/motorola/fogona
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
