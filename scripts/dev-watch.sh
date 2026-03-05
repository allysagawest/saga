#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-}"
THEME_NAME="${2:-saga-cyberpunk}"

if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

if ! command -v inotifywait >/dev/null 2>&1; then
  echo "error: inotifywait is required for saga dev (install inotify-tools)" >&2
  exit 1
fi

WATCH_DIR="$REPO_ROOT/themes"
echo "saga dev: watching $WATCH_DIR"
echo "saga dev: active theme $THEME_NAME"

inotifywait -mr -e modify,create,delete,move "$WATCH_DIR" | \
while read -r path action file; do
  printf '[dev] %s %s%s\n' "$action" "$path" "$file"
  "$REPO_ROOT/saga" theme apply "$THEME_NAME"
  echo "[dev] reloaded theme"
done
