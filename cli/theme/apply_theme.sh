#!/usr/bin/env bash
set -e

REPO_ROOT="${1:-}"
THEME_NAME="${2:-}"

if [ -z "$REPO_ROOT" ] || [ -z "$THEME_NAME" ]; then
  echo "Usage: apply_theme.sh <repo_root> <theme_name>"
  exit 1
fi

SAGA_CONFIG_DIR="$HOME/.config/saga"
THEMES_DIR="$SAGA_CONFIG_DIR/themes"
WIDGETS_DIR="$SAGA_CONFIG_DIR/widgets"
FUTURE_RENDERER_DIR="$WIDGETS_DIR/saga-ui"

# Theme lookup: exact name first, then saga-<name> fallback.
SOURCE_THEME_DIR="$REPO_ROOT/themes/$THEME_NAME"
if [ ! -d "$SOURCE_THEME_DIR" ]; then
  SOURCE_THEME_DIR="$REPO_ROOT/themes/saga-$THEME_NAME"
fi

if [ ! -d "$SOURCE_THEME_DIR" ]; then
  echo "[ERROR] Theme not found: $THEME_NAME"
  exit 1
fi

TARGET_THEME_DIR="$THEMES_DIR/$THEME_NAME"
RESOLVED_THEME_NAME="$(basename "$SOURCE_THEME_DIR")"
TARGET_THEME_DIR="$THEMES_DIR/$RESOLVED_THEME_NAME"

echo "Applying theme: $RESOLVED_THEME_NAME"
mkdir -p "$THEMES_DIR" "$WIDGETS_DIR" "$FUTURE_RENDERER_DIR" "$SAGA_CONFIG_DIR"

rm -rf "$TARGET_THEME_DIR"
cp -a "$SOURCE_THEME_DIR" "$TARGET_THEME_DIR"

echo "Installed theme: $TARGET_THEME_DIR"
echo "Renderer widgets are currently disabled"

echo "$RESOLVED_THEME_NAME" > "$SAGA_CONFIG_DIR/active-theme"
