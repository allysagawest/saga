#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-}"
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

CONFIG_DIR="$HOME/.config"
LOCAL_SHARE="$HOME/.local/share/saga"
LOCAL_BIN="$HOME/.local/bin"
STATE_FILE="$LOCAL_SHARE/state.json"

read -r DISTRO PKG_MGR < <("$REPO_ROOT/scripts/detect-distro.sh")
if [[ "$DISTRO" == "ubuntu" ]]; then
  PKG_FILE="$REPO_ROOT/packages/debian.txt"
else
  PKG_FILE="$REPO_ROOT/packages/${DISTRO}.txt"
fi

if [[ ! -f "$PKG_FILE" ]]; then
  echo "error: package list not found: $PKG_FILE" >&2
  exit 1
fi

install_pkg() {
  local pkg="$1"
  case "$PKG_MGR" in
    pacman)
      sudo pacman -S --needed --noconfirm "$pkg"
      ;;
    dnf)
      sudo dnf install -y "$pkg"
      ;;
    apt)
      sudo apt install -y "$pkg"
      ;;
    *)
      echo "error: unsupported package manager '$PKG_MGR'" >&2
      return 1
      ;;
  esac
}

if [[ "$PKG_MGR" == "apt" ]]; then
  sudo apt update
fi

echo "distro: $DISTRO"
echo "package manager: $PKG_MGR"

to_check_installed() {
  local command_csv="$1"
  local cmd
  IFS=',' read -ra cmds <<< "$command_csv"
  for cmd in "${cmds[@]}"; do
    cmd="$(echo "$cmd" | xargs)"
    [[ -n "$cmd" ]] || continue
    if command -v "$cmd" >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

install_from_candidates() {
  local pkg_csv="$1"
  local pkg
  IFS=',' read -ra pkgs <<< "$pkg_csv"
  for pkg in "${pkgs[@]}"; do
    pkg="$(echo "$pkg" | xargs)"
    [[ -n "$pkg" ]] || continue
    if install_pkg "$pkg"; then
      return 0
    fi
  done
  return 1
}

while IFS='|' read -r command_csv package_csv; do
  [[ -n "${command_csv// }" ]] || continue
  [[ "${command_csv:0:1}" == "#" ]] && continue
  [[ "$command_csv" == njal:* ]] && continue

  if to_check_installed "$command_csv"; then
    echo "ok: $command_csv"
  else
    echo "installing: $package_csv"
    if ! install_from_candidates "$package_csv"; then
      echo "warning: failed to install any candidate for '$command_csv' ($package_csv)" >&2
    fi
  fi
done < "$PKG_FILE"

mkdir -p "$CONFIG_DIR" "$LOCAL_SHARE" "$LOCAL_BIN" "$CONFIG_DIR/saga"
touch "$CONFIG_DIR/saga/.saga-managed"
touch "$LOCAL_SHARE/.saga-managed"

ln -sfn "$REPO_ROOT/desktop/hypr" "$CONFIG_DIR/hypr"
ln -sfn "$REPO_ROOT/desktop/waybar" "$CONFIG_DIR/waybar"
ln -sfn "$REPO_ROOT/desktop/swaync" "$CONFIG_DIR/swaync"
ln -sfn "$REPO_ROOT/desktop/eww" "$CONFIG_DIR/eww"
ln -sfn "$REPO_ROOT/desktop/wofi" "$CONFIG_DIR/wofi"

if [[ ! -f "$STATE_FILE" ]]; then
  cat > "$STATE_FILE" <<JSON
{
  "saga_version": "$(cat "$REPO_ROOT/VERSION")",
  "installed_modules": {}
}
JSON
fi

echo "desktop install done"
