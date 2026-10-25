#
# Copyright (C) 2024 The Android Open Source Project
# Copyright (C) 2024 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),fogona)
include $(call all-subdir-makefiles,$(LOCAL_PATH))

# Preserve Android's generated event tags as a registered recovery dependency.
include $(CLEAR_VARS)
LOCAL_MODULE := fogona-event-log-tags
LOCAL_MODULE_CLASS := ETC
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_STEM := event-log-tags
LOCAL_MODULE_PATH := $(TARGET_RECOVERY_ROOT_OUT)/system/etc
LOCAL_PREBUILT_MODULE_FILE := $(TARGET_OUT)/etc/event-log-tags
include $(BUILD_PREBUILT)
endif
