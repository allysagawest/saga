#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if command -v saga >/dev/null 2>&1; then
  SAGA_CMD=(saga)
else
  SAGA_CMD=("$REPO_ROOT/cli/saga")
fi

if ! command -v eww >/dev/null 2>&1; then
  echo "error: eww is required" >&2
  exit 1
fi

update_metric() {
  local metric="$1"
  local var="$2"
  local value
  value="$("${SAGA_CMD[@]}" query "$metric" 2>/dev/null | jq -r --arg m "$metric" '.[$m] // .value // .status // "n/a"' || echo 'n/a')"
  eww update "$var=$value" >/dev/null 2>&1 || true
}

refresh_all() {
  update_metric cpu saga_cpu
  update_metric ram saga_ram
  update_metric disk saga_disk
  update_metric net saga_net
  update_metric wifi saga_wifi
  update_metric bluetooth saga_bt
  update_metric volume saga_volume
  update_metric brightness saga_brightness
}

watch_event() {
  local event="$1"
  local metric="$2"
  local var="$3"

  "${SAGA_CMD[@]}" subscribe "$event" | while IFS=$'\t' read -r _ev raw; do
    local value="$raw"
    if [[ "$raw" == "{"* ]]; then
      value="$(echo "$raw" | jq -r --arg m "$metric" '.[$m] // .value // .status // "n/a"' 2>/dev/null || echo 'n/a')"
    fi
    eww update "$var=$value" >/dev/null 2>&1 || true
  done
}

watch_theme() {
  "${SAGA_CMD[@]}" subscribe theme_reload | while IFS=$'\t' read -r _ev _raw; do
    eww reload >/dev/null 2>&1 || true
  done
}

refresh_all
watch_event cpu_update cpu saga_cpu &
watch_event ram_update ram saga_ram &
watch_event disk_update disk saga_disk &
watch_event net_update net saga_net &
watch_event wifi_update wifi saga_wifi &
watch_event bluetooth_update bluetooth saga_bt &
watch_event audio_update volume saga_volume &
watch_event brightness_update brightness saga_brightness &
watch_theme &

wait
