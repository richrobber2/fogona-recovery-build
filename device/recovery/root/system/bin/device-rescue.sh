#!/system/bin/sh
# Offline recovery utility. No daemon, network, partition writes, mounts or wipes.
set -eu
umask 077
sandbox=0
if [ "${1:-}" = --sandbox ]; then
 [ "$(id -u)" != 0 ] || { echo 'Sandbox requires an unprivileged test process' >&2; exit 2; }
 shift
 [ "$#" -ge 2 ] || exit 2
 root=$(CDPATH= cd -P -- "$1" && pwd)
 case "$root" in /data/data/com.termux/files/home/downloads/device-assistant/recovery/tests/fixtures.*) ;; *) echo 'Not an isolated test fixture' >&2; exit 2;; esac
 shift
 sandbox=1
else
 root=
 [ "$(id -u)" = 0 ] || { echo 'Recovery root required' >&2; exit 2; }
fi
modules="$root/data/adb/modules"
command=${1:-menu}
valid_id() {
 case "$1" in ''|.*|*[!a-zA-Z0-9._-]*) return 1;; esac
}
check_data() {
 [ -d "$modules" ] && [ ! -L "$modules" ] || {
  echo 'Module directory unavailable. Mount/decrypt data using recovery first; do not format it.' >&2
  exit 3
 }
}
check_recovery() {
 [ "$sandbox" = 1 ] && return
 mode=$(getprop ro.bootmode 2>/dev/null || true)
 twrp=$(getprop ro.twrp.boot 2>/dev/null || true)
 [ "$mode" = recovery ] || [ "$twrp" = 1 ] || {
  echo 'Writes refused outside recovery' >&2; exit 2
 }
 device=$(getprop ro.product.vendor.device 2>/dev/null || true)
 [ "$device" = fogona ] || device=$(getprop ro.product.device 2>/dev/null || true)
 [ "$device" = fogona ] || { echo 'This bundle is scoped to fogona' >&2; exit 2; }
}
status() {
 echo 'Offline rescue: module status (no module scripts executed)'
 check_data
 count=0
 for directory in "$modules"/*; do
  [ -d "$directory" ] && [ ! -L "$directory" ] || continue
  name=${directory##*/}
  valid_id "$name" || continue
  if [ -L "$directory/disable" ]; then state=unsafe-symlink
  elif [ -e "$directory/disable" ]; then state=disabled
  else state=enabled
  fi
  printf '%s: %s\n' "$name" "$state"
  count=$((count+1))
 done
 printf 'Modules found: %s\n' "$count"
}
check_module() {
 valid_id "$1" || { echo 'Invalid module ID' >&2; exit 2; }
 directory="$modules/$1"
 [ -d "$directory" ] && [ ! -L "$directory" ] || { echo 'Module missing or symlinked' >&2; exit 3; }
 [ ! -L "$directory/disable" ] || { echo 'Disable marker is a symlink; refusing' >&2; exit 3; }
 [ ! -e "$directory/disable" ] || [ -f "$directory/disable" ] || { echo 'Non-file disable marker; refusing' >&2; exit 3; }
}
disable_one() {
 check_module "$1"
 directory="$modules/$1"
 if [ -f "$directory/disable" ]; then
  printf '%s: already disabled\n' "$1"
 else
  # noclobber refuses a competing existing file/link rather than following it.
  (set -C; : > "$directory/disable")
  printf '%s: disabled (reversible marker only)\n' "$1"
 fi
}
disable_all() {
 check_recovery
 check_data
 # Preflight every entry before changing any markers.
 for directory in "$modules"/*; do
  [ -e "$directory" ] || [ -L "$directory" ] || continue
  check_module "${directory##*/}"
 done
 for directory in "$modules"/*; do
  [ -d "$directory" ] || continue
  disable_one "${directory##*/}"
 done
 sync
}
boot_summary() {
 echo 'Boot summary (selected fields; no personal files)'
 if [ "$sandbox" = 0 ]; then
  for key in ro.bootmode ro.boot.bootreason sys.boot.reason ro.boot.slot_suffix sys.boot_completed; do
   printf '%s=%s\n' "$key" "$(getprop "$key" 2>/dev/null || true)"
  done
 fi
 if [ -r "$root/proc/uptime" ]; then
  IFS=' ' read -r uptime unused < "$root/proc/uptime" || true
  printf 'uptime_seconds=%s\n' "${uptime:-unavailable}"
 fi
 for log in "$root"/sys/fs/pstore/*; do
  [ -f "$log" ] && [ ! -L "$log" ] || continue
  printf 'pstore_file=%s\n' "${log##*/}"
  grep -iE 'Kernel panic|watchdog|Oops|BUG:|Call trace:' "$log" || true
 done
}
case "$command" in
 status) status;;
 boot-summary) boot_summary;;
 disable-module)
  [ "$#" = 2 ] || { echo 'Usage: device-rescue.sh disable-module ID' >&2; exit 2; }
  check_recovery; check_data; disable_one "$2"; sync;;
 disable-all-modules)
  [ "$#" = 1 ] || exit 2
  disable_all;;
 menu)
  while :; do
   printf '\n1) Module status\n2) Disable modules for next Android boot\n3) Boot summary\n4) Exit\nSelection: '
   IFS= read -r choice || exit 0
   case "$choice" in
    1) status;;
    2) printf 'Type DISABLE to confirm reversible module disable: '; IFS= read -r answer || exit 0
       [ "$answer" != DISABLE ] || disable_all;;
    3) boot_summary;;
    4) exit 0;;
    *) echo 'Select 1, 2, 3 or 4';;
   esac
  done;;
 *) echo 'Commands: status, boot-summary, disable-module ID, disable-all-modules, menu' >&2; exit 2;;
esac
