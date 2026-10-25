#!/system/bin/sh
# One bounded recovery-only attempt. Never touch keys, format or reboot.
PATH=/system/bin:/sbin
export PATH
umask 077
mount_table=/proc/self/mounts
runtime=/system/lib64/fogona-vndk33
vendor_manifest=/vendor/etc/vintf/manifest.xml

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
start_crypto() {
    [ "$(id -u)" = 0 ] && [ "$(getprop ro.bootmode)" = recovery ] &&
        [ "$(getprop ro.twrp.boot)" = 1 ] &&
        [ "$(getprop ro.product.vendor.device)" = fogona ] &&
        [ "$(getprop sys.boot_completed)" != 1 ] || return 2
    vendor_is_ro && runtime_complete || return 3
    [ -r "$vendor_manifest" ] || return 3
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
