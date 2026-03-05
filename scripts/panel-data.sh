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
  echo "error: panel-data metric required" >&2
  exit 1
fi

query_metric() {
  local m="$1"
  "${SAGA_CMD[@]}" query "$m" | jq -r --arg m "$m" '.[$m] // .value // .status // "n/a"'
}

case "$metric" in
  cpu|ram|disk|net|wifi|bluetooth|volume|brightness)
    query_metric "$metric"
    ;;
  wifi-scan)
    query_metric "wifi_scan"
    ;;
  bt-list)
    query_metric "bluetooth_devices"
    ;;
  audio-outputs)
    query_metric "audio_outputs"
    ;;
  *)
    echo "error: unknown panel-data metric '$metric'" >&2
    exit 1
    ;;
esac
