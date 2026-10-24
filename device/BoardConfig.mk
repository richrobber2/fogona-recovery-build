#
# Copyright (C) 2024 The Android Open Source Project
# Copyright (C) 2024 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

DEVICE_PATH := device/motorola/fogona

# Do not hide missing recovery/crypto dependencies.
ALLOW_MISSING_DEPENDENCIES := false

# A/B
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += \
    vendor \
    odm \
    system \
    product \
    system_ext

# Architecture
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := generic

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a9

# APEX
OVERRIDE_TARGET_FLATTEN_APEX := true

# Bootloader
TARGET_BOOTLOADER_BOARD_NAME := fogona
TARGET_NO_BOOTLOADER := true

# Display
TARGET_SCREEN_DENSITY := 280

# Header-v4 GKI, dedicated A/B recovery: recovery contains no kernel.
# Use the backed-up matching boot image for build metadata; do not rebuild boot.
BOARD_BOOT_HEADER_VERSION := 4
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_USES_GENERIC_KERNEL_IMAGE := true
BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true
TARGET_NO_KERNEL := true
BOARD_PREBUILT_BOOTIMAGE := $(DEVICE_PATH)/prebuilt/boot.img

# Partitions
BOARD_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 100663296
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 104857600
BOARD_HAS_LARGE_FILESYSTEM := true
BOARD_SYSTEMIMAGE_PARTITION_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := f2fs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_VENDOR := vendor
BOARD_SUPER_PARTITION_SIZE := 6710886400 # measured block device
BOARD_SUPER_PARTITION_GROUPS := mot_dp_group
BOARD_MOT_DP_GROUP_PARTITION_LIST := system system_ext vendor odm product
BOARD_MOT_DP_GROUP_SIZE := 6706692096 # measured active-slot group limit

# Platform
TARGET_BOARD_PLATFORM := bengal

# Recovery
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# A/B device flags
TARGET_NO_RECOVERY :=
BOARD_USES_RECOVERY_AS_BOOT :=
BOARD_BUILD_SYSTEM_ROOT_IMAGE :=

# Security patch level
VENDOR_SECURITY_PATCH := 2026-08-01

# Verified Boot
BOARD_AVB_ENABLE := true

# Match the inspected stock recovery vendor level; no future-date workaround.
# Actual AVB signing/rollback compatibility must be checked before a flash candidate.
PLATFORM_SECURITY_PATCH := 2026-08-01
PLATFORM_VERSION := 13.0.0

# TWRP Configuration
TW_THEME := portrait_hdpi
TW_EXTRA_LANGUAGES := true
TW_USE_TOOLBOX := true
TW_INCLUDE_REPACKTOOLS := true

# f2fs + fscrypt v2 wrapped keys and metadata decryption are required.
# These compile-time switches are not evidence that hardware-backed decryption works.
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_USE_FSCRYPT_POLICY := 2
TW_INCLUDE_FBE_METADATA_DECRYPT := true

# Matching vendor_boot modules are required. Module-loader selection remains
# a runtime-validation blocker; do not guess a touchscreen/crypto module list.
