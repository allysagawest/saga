#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-}"
action="${2:-}"
panel="${3:-}"

if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

if ! command -v eww >/dev/null 2>&1; then
  echo "error: eww is required for panels" >&2
  exit 1
fi

refresh_vars() {
  local cpu ram disk net wifi bt vol bright
  cpu="$("$REPO_ROOT/scripts/panel-data.sh" cpu 2>/dev/null || echo 'n/a')"
  ram="$("$REPO_ROOT/scripts/panel-data.sh" ram 2>/dev/null || echo 'n/a')"
  disk="$("$REPO_ROOT/scripts/panel-data.sh" disk 2>/dev/null || echo 'n/a')"
  net="$("$REPO_ROOT/scripts/panel-data.sh" net 2>/dev/null || echo 'offline')"
  wifi="$("$REPO_ROOT/scripts/panel-data.sh" wifi 2>/dev/null || echo 'off')"
  bt="$("$REPO_ROOT/scripts/panel-data.sh" bluetooth 2>/dev/null || echo 'off')"
  vol="$("$REPO_ROOT/scripts/panel-data.sh" volume 2>/dev/null || echo '0')"
  bright="$("$REPO_ROOT/scripts/panel-data.sh" brightness 2>/dev/null || echo '50')"

  eww update saga_cpu="$cpu" saga_ram="$ram" saga_disk="$disk" saga_net="$net" saga_wifi="$wifi" saga_bt="$bt" saga_volume="$vol" saga_brightness="$bright"
  eww update saga_wifi_scan="$($REPO_ROOT/scripts/panel-data.sh wifi-scan 2>/dev/null | sed 's/"//g' | paste -sd ' | ' - || echo 'No WiFi scan data')"
  eww update saga_bt_list="$($REPO_ROOT/scripts/panel-data.sh bt-list 2>/dev/null | sed 's/"//g' | paste -sd ' | ' - || echo 'No paired devices')"
  eww update saga_audio_outputs="$($REPO_ROOT/scripts/panel-data.sh audio-outputs 2>/dev/null | sed 's/"//g' | tr '\n' '|' || echo 'No audio outputs')"
}

set_volume() {
  local value="$1"
  wpctl set-volume @DEFAULT_AUDIO_SINK@ "$value%" >/dev/null 2>&1 || true
  refresh_vars
}

set_brightness() {
  local value="$1"
  brightnessctl set "$value%" >/dev/null 2>&1 || true
  refresh_vars
}

if [[ "$action" == "set-volume" ]]; then
  set_volume "${panel:-50}"
  exit 0
fi

if [[ "$action" == "set-brightness" ]]; then
  set_brightness "${panel:-50}"
  exit 0
fi

if [[ "$action" == "refresh" ]]; then
  refresh_vars
  exit 0
fi

if [[ -z "$panel" ]]; then
  echo "error: panel name required" >&2
  exit 1
fi

refresh_vars

case "$action" in
  open)
    eww open "$panel"
    ;;
  close)
    eww close "$panel"
    ;;
  toggle)
    eww open --toggle "$panel"
    ;;
  *)
    echo "error: unknown panel action '$action'" >&2
    exit 1
    ;;
esac
