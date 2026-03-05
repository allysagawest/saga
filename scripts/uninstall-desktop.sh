#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="$HOME/.config"
LOCAL_SHARE="$HOME/.local/share/saga"
LOCAL_BIN="$HOME/.local/bin"

safe_remove_link() {
  local path="$1"
  if [[ -L "$path" ]]; then
    rm -f "$path"
  fi
}

safe_remove_link "$CONFIG_DIR/hypr"
safe_remove_link "$CONFIG_DIR/waybar"
safe_remove_link "$CONFIG_DIR/swaync"
safe_remove_link "$CONFIG_DIR/eww"
safe_remove_link "$CONFIG_DIR/walker"

if [[ -f "$CONFIG_DIR/saga/.saga-managed" ]]; then
  rm -rf "$CONFIG_DIR/saga"
fi

if [[ -f "$LOCAL_SHARE/.saga-managed" ]]; then
  rm -rf "$LOCAL_SHARE"
fi

if [[ -L "$LOCAL_BIN/saga" ]]; then
  rm -f "$LOCAL_BIN/saga"
fi

echo "Saga desktop config and state removed."
