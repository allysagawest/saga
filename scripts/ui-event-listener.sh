#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if command -v saga >/dev/null 2>&1; then
  SAGA_CMD=(saga)
else
  SAGA_CMD=("$REPO_ROOT/saga")
fi

"${SAGA_CMD[@]}" subscribe theme_reload | while IFS=$'\t' read -r _ev _raw; do
  if command -v pkill >/dev/null 2>&1; then
    pkill -SIGUSR2 waybar >/dev/null 2>&1 || true
  fi
  if command -v eww >/dev/null 2>&1; then
    eww reload >/dev/null 2>&1 || true
  fi
  if command -v hyprctl >/dev/null 2>&1; then
    hyprctl reload >/dev/null 2>&1 || true
  fi
done
