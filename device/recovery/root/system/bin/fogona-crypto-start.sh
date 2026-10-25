#!/system/bin/sh
# One bounded recovery-only attempt. Never touch keys, format or reboot.
PATH=/system/bin:/sbin
export PATH
umask 077
mount_table=/proc/self/mounts
runtime=/system/lib64/fogona-vndk33
vendor_manifest=/vendor/etc/vintf/manifest.xml
system_device=/dev/block/bootdevice/by-name/system
system_mount=/tmp/fogona-system

vendor_is_ro() {
    awk '$2=="/vendor" && $3=="erofs" {if (index("," $4 ",",",ro,")) found=1} END {exit !found}' "$mount_table"
}
runtime_complete() {
    for library in libc++.so libxml2.so libdmabufheap.so libutils.so libcutils.so libbase.so libion.so \
        android.hardware.security.sharedsecret-V1-ndk.so libbinder.so \
        android.hardware.security.secureclock-V1-ndk.so android.hardware.security.keymint-V2-ndk.so \
        libcrypto.so libhidlbase.so libhardware.so; do
        [ -s "$runtime/$library" ] || return 1
    done
}
# Only read the active system image; do not replay its ext4 journal or execute
# anything from it. KeyMint must see the installed OS values, not recovery's
# independently built release/patch defaults. No guessed or future values.
system_is_block() { [ -b "$system_device" ]; }
system_is_expected_ro() {
    info=$(awk -v target="$system_mount" '$2==target {print $1 " " $3 " " $4; exit}' "$mount_table")
    [ -n "$info" ] || return 1
    set -- $info
    [ "$2" = ext4 ] && [ "$(readlink -f "$1")" = "$(readlink -f "$system_device")" ] || return 1
    case ",$3," in *,ro,*) return 0;; *) return 1;; esac
}
align_os_properties() {
    system_is_block && [ ! -L "$system_mount" ] || return 1
    mounted_here=0
    if ! system_is_expected_ro; then
        [ -z "$(awk -v target="$system_mount" '$2==target {print $1}' "$mount_table")" ] || return 1
        mkdir -p "$system_mount" || return 1
        mount -t ext4 -o ro,noload,nosuid,nodev,noexec "$system_device" "$system_mount" || return 1
        mounted_here=1
    fi
    os_release=
    os_patch=
    if system_is_expected_ro; then
        for propfile in "$system_mount/system/build.prop" "$system_mount/build.prop"; do
            [ -f "$propfile" ] && [ ! -L "$propfile" ] || continue
            os_release=$(awk -F= '$1=="ro.build.version.release" {print substr($0,index($0,"=")+1);exit}' "$propfile")
            os_patch=$(awk -F= '$1=="ro.build.version.security_patch" {print substr($0,index($0,"=")+1);exit}' "$propfile")
            [ -n "$os_release" ] && [ -n "$os_patch" ] && break
        done
    fi
    if [ "$mounted_here" = 1 ]; then
        umount "$system_mount" || return 1
    fi
    printf '%s\n' "$os_release" | grep -Eq '^[0-9]+(\.[0-9]+){0,2}$' || return 1
    printf '%s\n' "$os_patch" | grep -Eq '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$' || return 1
    fogona-resetprop -n ro.build.version.release "$os_release" || return 1
    fogona-resetprop -n ro.build.version.security_patch "$os_patch" || return 1
    [ "$(getprop ro.build.version.release)" = "$os_release" ] &&
        [ "$(getprop ro.build.version.security_patch)" = "$os_patch" ] || return 1
    echo "Crypto OS configuration copied from installed system: release=$os_release patch=$os_patch"
}
start_crypto() {
    [ "$(id -u)" = 0 ] && [ "$(getprop ro.bootmode)" = recovery ] &&
        [ "$(getprop ro.twrp.boot)" = 1 ] &&
        [ "$(getprop ro.product.vendor.device)" = fogona ] &&
        [ "$(getprop sys.boot_completed)" != 1 ] || return 2
    vendor_is_ro && runtime_complete || return 3
    [ -r "$vendor_manifest" ] || return 3
    align_os_properties || return 6
    setprop ctl.start fogona-qseecomd || return 4
    setprop ctl.start fogona-keymint || return 4
    # Outer process deadline also bounds a stuck Binder registration query.
    if timeout -s KILL 3 fogona-check-keymint; then
        setprop fogona.crypto.keymint.ready 1 || return 4
        return 0
    fi
    setprop ctl.stop fogona-keymint || :
    setprop ctl.stop fogona-qseecomd || :
    return 5
}
[ "${1:-}" != --library ] || return 0
exec > /tmp/fogona-crypto-startup.log 2>&1
start_crypto
result=$?
echo "crypto_startup_exit=$result"
setprop fogona.crypto.startup.exit "$result" || :
exit "$result"
