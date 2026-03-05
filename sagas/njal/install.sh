#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-}"
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

read -r DISTRO PKG_MGR < <("$REPO_ROOT/scripts/detect-distro.sh")
if [[ "$DISTRO" == "ubuntu" ]]; then
  PKG_FILE="$REPO_ROOT/packages/debian.txt"
else
  PKG_FILE="$REPO_ROOT/packages/${DISTRO}.txt"
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
  esac
}

if [[ "$PKG_MGR" == "apt" ]]; then
  sudo apt update
fi

while IFS='|' read -r command_csv package_csv; do
  [[ "$command_csv" == njal:* ]] || continue
  command_csv="${command_csv#njal:}"

  if ! command -v "$command_csv" >/dev/null 2>&1; then
    install_pkg "$package_csv" || echo "warning: could not install $package_csv" >&2
  fi
done < "$PKG_FILE"

mkdir -p "$HOME/.config/saga"
ln -sfn "$REPO_ROOT/sagas/njal/zsh" "$HOME/.config/saga/zsh"

echo "njal installed"
