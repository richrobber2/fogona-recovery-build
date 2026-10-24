#!/system/bin/sh
# Restore only the verified recovery_a backup from this recovery project.
# Default is read-only. No reboot, slot change, service or userdata operation.
set -eu
umask 077
sandbox=0
base=/data/data/com.termux/files/home/downloads/device-assistant/recovery
image="$base/backups/recovery_a.img"
target=/dev/block/by-name/recovery_a
expected=a9d231743e9bb8e3d418a31e1964b8e07280530bc7e81c528efd780adf54b81a
size=104857600
if [ "${1:-}" = --sandbox ]; then
 [ "$(id -u)" != 0 ] || { echo 'Sandbox requires an unprivileged test process' >&2; exit 2; }
 shift
 [ "$#" -ge 1 ] || exit 2
 sandbox_root=$(CDPATH= cd -P -- "$1" && pwd)
 case "$sandbox_root" in "$base"/tests/restore-fixtures.*) ;; *) echo 'Not an isolated restore fixture' >&2; exit 2;; esac
 [ -f "$sandbox_root/.restore-fixture" ] && [ ! -L "$sandbox_root/.restore-fixture" ] || exit 2
 shift
 sandbox=1
 image="$sandbox_root/original.img"
 target="$sandbox_root/partition.img"
 expected=$(cat "$sandbox_root/expected.sha256")
 size=$(cat "$sandbox_root/expected.bytes")
else
 PATH=/system/bin:/system/xbin
 export PATH
 [ "$(id -u)" = 0 ] || { echo 'Local root required' >&2; exit 2; }
 [ "$(getprop ro.product.vendor.device)" = fogona ] || { echo 'Device is not fogona' >&2; exit 2; }
 [ "$(getprop ro.boot.slot_suffix)" = _a ] || { echo 'Active slot is not the backed-up slot_a' >&2; exit 2; }
 [ "$(getprop sys.boot_completed)" = 1 ] || { echo 'Normal Android must finish booting before restoration' >&2; exit 2; }
 [ -b "$target" ] || { echo 'Recovery target is not a block device' >&2; exit 2; }
fi
case "${1:---check}" in --check|--restore) action=${1:---check};; *) echo 'Use --check (default) or --restore' >&2; exit 2;; esac
[ "$#" -le 1 ] || exit 2
[ -f "$image" ] && [ ! -L "$image" ] || { echo 'Backup must be a regular non-symlink file' >&2; exit 2; }
if [ "$sandbox" = 1 ]; then
 [ -f "$target" ] && [ ! -L "$target" ] || { echo 'Fixture target must be a regular non-symlink file' >&2; exit 2; }
 target_size=$(stat -c%s "$target")
else
 target_size=$(blockdev --getsize64 "$target")
fi
[ "$(stat -c%s "$image")" = "$size" ] && [ "$target_size" = "$size" ] || { echo 'Backup/partition size mismatch' >&2; exit 2; }
actual=$(sha256sum "$image"); actual=${actual%% *}
[ "$actual" = "$expected" ] || { echo 'Backup SHA256 mismatch' >&2; exit 2; }
echo "Verified backup and target: recovery_a ($size bytes)."
if [ "$action" = --check ]; then
 current=$(sha256sum "$target"); current=${current%% *}
 echo "Read-only check. Target SHA256: $current"
 exit 0
fi
# Explicit --restore is the only write path; all checks above precede it.
dd if="$image" of="$target" bs=1048576 conv=fsync
readback=$(sha256sum "$target"); readback=${readback%% *}
[ "$readback" = "$expected" ] || { echo 'Restore readback failed; remain in Android and investigate before rebooting' >&2; exit 3; }
echo 'Original recovery_a restored and complete partition readback verified. No reboot performed.'
