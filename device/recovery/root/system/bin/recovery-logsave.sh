#!/system/bin/sh
# Bounded recovery-only snapshots; no formatting, userdata access or reboot.
PATH=/system/bin:/sbin
export PATH
umask 077
set -eu
out=/metadata/device-assistant-recovery
scratch=/tmp
recovery_source=/tmp/recovery.log
mount_source=/proc/self/mounts
module_source=/proc/modules
input_source=/proc/bus/input/devices
boot_id_source=/proc/sys/kernel/random/boot_id

mount_is_expected() {
    mount_table=$1
    expected_device=$2
    mounted=$(awk '$2=="/metadata" { print $1 " " $3 " " $4; exit }' "$mount_table")
    [ -n "$mounted" ] || return 1
    set -- $mounted
    [ "$(readlink -f "$1")" = "$(readlink -f "$expected_device")" ] || return 1
    [ "$2" = f2fs ] || return 1
    case ",$3," in *,rw,*) return 0;; *) return 1;; esac
}

save_checked() {
    source=$1
    dest=$2
    limit=$3
    [ -f "$source" ] && [ ! -L "$source" ] || return 1
    [ ! -L "$dest" ] && [ ! -L "$dest.new" ] || return 1
    tail -c "$limit" "$source" > "$dest.new" || return 1
    digest=$(sha256sum "$dest.new") || return 1
    digest=${digest%% *}
    chmod 600 "$dest.new" || return 1
    mv -f "$dest.new" "$dest" || return 1
    sync
    actual=$(sha256sum "$dest") || return 1
    [ "${actual%% *}" = "$digest" ]
}

ensure_metadata() {
    [ -b /dev/block/by-name/metadata ] && [ ! -L /metadata ] || return 1
    mkdir -p /metadata || return 1
    if ! mount_is_expected /proc/self/mounts /dev/block/by-name/metadata; then
        [ -z "$(awk '$2=="/metadata" {print $1}' /proc/self/mounts)" ] || return 1
        mount -t f2fs -o nosuid,nodev /dev/block/by-name/metadata /metadata || return 1
        mount_is_expected /proc/self/mounts /dev/block/by-name/metadata || return 1
    fi
    [ ! -L "$out" ] || return 1
    mkdir -p "$out" || return 1
    chmod 700 "$out"
}

report_status() {
    # SELinux/property policy must not prevent saving to the verified filesystem.
    setprop device.rescue.log_status "$1" >/dev/null 2>&1 || :
}

write_status() {
    state=$1
    { echo "boot_id=$(cat "$boot_id_source")"; date -u; echo "state=$state"; echo "last_stage=$stage"; } > "$scratch/device-recovery-save-status" || return 1
    save_checked "$scratch/device-recovery-save-status" "$out/status.txt" 4096
}

snapshot() {
    stage=snapshot
    ensure_metadata || return 1
    save_checked "$recovery_source" "$out/recovery.log" 2097152 || return 1
    stage=mount-table
    save_checked "$mount_source" "$out/mounts.txt" 262144 || return 1
    save_checked "$module_source" "$out/modules.txt" 262144 || return 1
    save_checked "$input_source" "$out/input-devices.txt" 262144 || return 1
    # Optional kernel snapshot; avoid marking the main log saved when it failed.
    if dmesg > "$scratch/device-recovery-dmesg.txt"; then
        save_checked "$scratch/device-recovery-dmesg.txt" "$out/dmesg.txt" 1048576 || return 1
        if [ "$first_snapshot" = 1 ]; then
            save_checked "$scratch/device-recovery-dmesg.txt" "$out/boot-dmesg.txt" 1048576 || return 1
        fi
    fi
    stage=service-state
    { getprop; } > "$scratch/device-recovery-properties.txt"
    save_checked "$scratch/device-recovery-properties.txt" "$out/properties.txt" 65536 || return 1
    ps -A > "$scratch/device-recovery-processes.txt" 2>&1 || :
    save_checked "$scratch/device-recovery-processes.txt" "$out/processes.txt" 262144 || return 1
    if command -v service >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
        timeout 3 service list > "$scratch/device-recovery-services.txt" 2>&1 || :
        save_checked "$scratch/device-recovery-services.txt" "$out/services.txt" 65536 || return 1
    fi
    if command -v logcat >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
        if timeout 3 logcat -b all -d -t 500 > "$scratch/device-recovery-logcat.txt" 2>/dev/null; then
            save_checked "$scratch/device-recovery-logcat.txt" "$out/logcat.txt" 524288 || return 1
        fi
    fi
    stage=complete
    first_snapshot=0
    write_status saved || return 1
    report_status saved
}

# Sourcing functions for isolated tests does not run device operations.
[ "${1:-}" != --library ] || return 0
case "${1:-}" in --once|--boot) action=$1;; *) echo 'Use --once or --boot' >&2; exit 2;; esac
[ "$(id -u)" = 0 ] && [ "$(getprop ro.product.vendor.device)" = fogona ] || exit 2
[ "$(getprop sys.boot_completed)" != 1 ] || { echo 'Recovery only' >&2; exit 2; }
ensure_metadata || exit 2
for name in recovery.log previous-recovery.log modules.txt input-devices.txt dmesg.txt boot-dmesg.txt mounts.txt logcat.txt properties.txt processes.txt services.txt status.txt; do
    [ ! -L "$out/$name" ] && [ ! -L "$out/$name.new" ] || exit 2
done
if [ -f "$out/recovery.log" ]; then
    cp -p "$out/recovery.log" "$out/previous-recovery.log"
fi
first_snapshot=1
stage=starting
write_status pending || exit 1
report_status pending
if [ "$action" = --once ]; then
    snapshot || { write_status failed || :; report_status failed; exit 1; }
else
    # Four bounded snapshots, then exit. No continuing watcher.
    for delay in 1 4 15 40; do
        sleep "$delay"
        if ! snapshot; then write_status failed || :; report_status failed; fi
    done
fi
