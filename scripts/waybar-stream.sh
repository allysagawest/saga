#!/usr/bin/env bash
set -euo pipefail

metric="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if command -v saga >/dev/null 2>&1; then
  SAGA_CMD=(saga)
else
  SAGA_CMD=("$REPO_ROOT/cli/saga")
fi

if [[ -z "$metric" ]]; then
  echo '{"text":"n/a"}'
  exit 1
fi

format_json() {
  local m="$1"
  local val="$2"
  case "$m" in
    cpu)
      printf '{"text":" %s%%","tooltip":"CPU %s%%","class":"cpu"}\n' "$val" "$val"
      ;;
    wifi)
      printf '{"text":" %s","tooltip":"WiFi %s","class":"wifi"}\n' "$val" "$val"
      ;;
    volume)
      printf '{"text":" %s%%","tooltip":"Volume %s%%","class":"volume"}\n' "$val" "$val"
      ;;
    bluetooth)
      printf '{"text":" %s","tooltip":"Bluetooth %s","class":"bluetooth"}\n' "$val" "$val"
      ;;
    *)
      printf '{"text":"%s"}\n' "$val"
      ;;
  esac
}

extract_value() {
  local m="$1"
  local json="$2"
  echo "$json" | jq -r --arg m "$m" '.[$m] // .value // .status // "n/a"'
}

event_for_metric() {
  case "$1" in
    cpu) echo "cpu_update" ;;
    wifi) echo "wifi_update" ;;
    volume) echo "audio_update" ;;
    bluetooth) echo "bluetooth_update" ;;
    *) echo "${1}_update" ;;
  esac
}

initial="$("${SAGA_CMD[@]}" query "$metric" 2>/dev/null || echo '{}')"
value="$(extract_value "$metric" "$initial" 2>/dev/null || echo 'n/a')"
format_json "$metric" "$value"

event_name="$(event_for_metric "$metric")"
"${SAGA_CMD[@]}" subscribe "$event_name" | while IFS=$'\t' read -r _ev raw; do
  val="$raw"
  if [[ "$raw" == "{"* ]]; then
    val="$(echo "$raw" | jq -r --arg m "$metric" '.[$m] // .value // .status // "n/a"' 2>/dev/null || echo 'n/a')"
  fi
  format_json "$metric" "$val"
done
