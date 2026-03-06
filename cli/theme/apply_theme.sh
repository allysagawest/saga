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
SDDM_THEME_ROOT="/usr/share/sddm/themes"
SDDM_THEME_CONF_DIR="/etc/sddm.conf.d"
SDDM_THEME_CONF_FILE="$SDDM_THEME_CONF_DIR/20-saga-theme.conf"

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

# Best-effort SDDM theme hook:
# - Theme assets are stored under themes/<theme>/sddm in the repo.
# - System install is attempted only when non-interactive sudo (or root) is available.
SOURCE_SDDM_THEME_DIR="$SOURCE_THEME_DIR/sddm"
if [ -d "$SOURCE_SDDM_THEME_DIR" ]; then
  echo "Found SDDM theme assets for: $RESOLVED_THEME_NAME"
  if [ "$(id -u)" -eq 0 ]; then
    mkdir -p "$SDDM_THEME_ROOT" "$SDDM_THEME_CONF_DIR"
    rm -rf "$SDDM_THEME_ROOT/$RESOLVED_THEME_NAME"
    cp -a "$SOURCE_SDDM_THEME_DIR" "$SDDM_THEME_ROOT/$RESOLVED_THEME_NAME"
    cat > "$SDDM_THEME_CONF_FILE" <<EOF
[Theme]
Current=$RESOLVED_THEME_NAME
EOF
    echo "Applied SDDM theme: $RESOLVED_THEME_NAME"
  elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    sudo mkdir -p "$SDDM_THEME_ROOT" "$SDDM_THEME_CONF_DIR"
    sudo rm -rf "$SDDM_THEME_ROOT/$RESOLVED_THEME_NAME"
    sudo cp -a "$SOURCE_SDDM_THEME_DIR" "$SDDM_THEME_ROOT/$RESOLVED_THEME_NAME"
    sudo tee "$SDDM_THEME_CONF_FILE" >/dev/null <<EOF
[Theme]
Current=$RESOLVED_THEME_NAME
EOF
    echo "Applied SDDM theme: $RESOLVED_THEME_NAME"
  else
    echo "[WARN] Skipping system SDDM theme apply (requires sudo)."
    echo "[INFO] Run 'sudo -v && ./cli/saga theme $THEME_NAME' to apply login theme now."
  fi
fi
