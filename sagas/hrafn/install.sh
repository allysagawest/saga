#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_HELPER="$REPO_ROOT/scripts/install-state.sh"
INSTALL_ID="hrafn"
DRY_RUN=0

CONFIG_DIR="$HOME/.config/hrafn"
CONFIG_FILE="$CONFIG_DIR/config.toml"
DATA_DIR="$HOME/.local/share/hrafn"
VENV_DIR="$DATA_DIR/venv"
BIN_DIR="$HOME/.local/bin"
BIN_LINK="$BIN_DIR/hrafn"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SYNC_SERVICE_UNIT="$SYSTEMD_USER_DIR/hrafn-sync.service"
SYNC_TIMER_UNIT="$SYSTEMD_USER_DIR/hrafn-sync.timer"
DISTRO=""
PKG_MGR=""
PKG_FILE=""

if [[ ! -r "$STATE_HELPER" ]]; then
  echo "error: missing shared install-state helper at $STATE_HELPER" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$STATE_HELPER"

usage() {
  cat <<EOF
Hrafn installer

Installs Hrafn into user space with an isolated virtualenv and a CLI symlink in
\`~/.local/bin/hrafn\`.

Usage:
  ./install.sh                         Install Hrafn
  ./install.sh install [--dry-run]    Install or preview Hrafn
  ./install.sh uninstall [--dry-run]  Uninstall or preview Hrafn removal

What install does:
  - creates ~/.config/hrafn and ~/.local/share/hrafn
  - creates an isolated virtualenv under ~/.local/share/hrafn/venv
  - installs the hrafn Python package and dependencies into that virtualenv
  - installs khal and vdirsyncer system packages when available for your distro
  - links ~/.local/bin/hrafn to the virtualenv entrypoint
  - installs and enables a user systemd sync timer with a default 5 minute cadence
  - preserves existing Hrafn config and CLI state for rollback

Examples:
  ./install.sh
  ./install.sh --dry-run
  ./install.sh install --dry-run
  ./install.sh uninstall --dry-run
EOF
}

list_python_requirements() {
  python3 - "$SCRIPT_DIR/pyproject.toml" <<'PY'
import sys
import tomllib
from pathlib import Path

data = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for dep in data.get("project", {}).get("dependencies", []):
    print(dep)
PY
}

detect_platform() {
  read -r DISTRO PKG_MGR < <("$REPO_ROOT/scripts/detect-distro.sh")
  if [[ "$DISTRO" == "ubuntu" ]]; then
    PKG_FILE="$REPO_ROOT/packages/debian.txt"
  else
    PKG_FILE="$REPO_ROOT/packages/${DISTRO}.txt"
  fi
}

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

remove_pkg() {
  local pkg="$1"
  case "$PKG_MGR" in
    pacman)
      sudo pacman -Rns --noconfirm "$pkg"
      ;;
    dnf)
      sudo dnf remove -y "$pkg"
      ;;
    apt)
      sudo apt remove -y "$pkg"
      ;;
  esac
}

install_hrafn_packages() {
  local command_csv package_csv package_name

  detect_platform
  [[ -f "$PKG_FILE" ]] || return 0

  if [[ "$PKG_MGR" == "apt" ]]; then
    sudo apt update
  fi

  while IFS='|' read -r command_csv package_csv; do
    [[ "$command_csv" == hrafn:* ]] || continue
    command_csv="${command_csv#hrafn:}"
    package_name="${package_csv%%,*}"
    if command -v "$command_csv" >/dev/null 2>&1; then
      record_package_state "$INSTALL_ID" "$package_name" "preexisting"
      continue
    fi

    install_pkg "$package_name"
    if command -v "$command_csv" >/dev/null 2>&1; then
      record_package_state "$INSTALL_ID" "$package_name" "installed"
    else
      record_package_state "$INSTALL_ID" "$package_name" "failed"
    fi
  done < "$PKG_FILE"
}

remove_hrafn_packages() {
  local pkg

  detect_platform
  if [[ "$PKG_MGR" == "apt" ]]; then
    sudo apt update || true
  fi

  while IFS= read -r pkg; do
    [[ -n "$pkg" ]] || continue
    remove_pkg "$pkg"
  done < <(packages_with_status "$INSTALL_ID" "installed")
}

list_hrafn_system_packages() {
  local command_csv package_csv

  detect_platform
  [[ -f "$PKG_FILE" ]] || return 0
  while IFS='|' read -r command_csv package_csv; do
    [[ "$command_csv" == hrafn:* ]] || continue
    printf '%s|%s\n' "${command_csv#hrafn:}" "${package_csv%%,*}"
  done < "$PKG_FILE"
}

list_installed_venv_packages() {
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    return 0
  fi

  "$VENV_DIR/bin/python" - <<'PY'
import importlib.metadata as metadata

seen = set()
rows = []
for dist in metadata.distributions():
    name = dist.metadata["Name"]
    version = dist.version
    key = (name, version)
    if key in seen:
        continue
    seen.add(key)
    rows.append(key)

for name, version in sorted(rows, key=lambda item: item[0].lower()):
    print(f"{name}=={version}")
PY
}

update_saga_registry() {
  local action="$1"
  local state_file="$HOME/.local/share/saga/state.json"

  mkdir -p "$(dirname "$state_file")"
  python3 - "$state_file" "$action" <<'PY'
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
action = sys.argv[2]

if state_path.exists():
    data = json.loads(state_path.read_text(encoding="utf-8"))
else:
    data = {"saga_version": "unknown", "active_theme": "default", "installed_modules": {}}

modules = data.setdefault("installed_modules", {})
if action == "install":
    modules["hrafn"] = {"managed_by": "sagas/hrafn/install.sh"}
else:
    modules.pop("hrafn", None)

state_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

run_repo_python() {
  PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" python3 "$@"
}

install_sync_service() {
  backup_target "$INSTALL_ID" "$SYNC_SERVICE_UNIT"
  backup_target "$INSTALL_ID" "$SYNC_TIMER_UNIT"
  record_directory_state "$INSTALL_ID" "$SYSTEMD_USER_DIR"
  run_repo_python - <<'PY'
from cli.service import install_sync_service

install_sync_service()
PY
}

uninstall_sync_service() {
  run_repo_python - <<'PY'
from cli.service import uninstall_sync_service

uninstall_sync_service()
PY
}

install_hrafn() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required to install hrafn" >&2
    exit 1
  fi

  if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "error: python3 venv support is required to install hrafn" >&2
    exit 1
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    preview_install
    return 0
  fi
  ensure_install_state "$INSTALL_ID"
  install_hrafn_packages
  record_directory_state "$INSTALL_ID" "$CONFIG_DIR"
  record_directory_state "$INSTALL_ID" "$DATA_DIR"
  backup_target "$INSTALL_ID" "$CONFIG_FILE"
  backup_target "$INSTALL_ID" "$BIN_LINK"
  set_install_meta "$INSTALL_ID" "INSTALL_SCRIPT" "$SCRIPT_DIR/install.sh"
  set_install_meta "$INSTALL_ID" "REPO_ROOT" "$REPO_ROOT"

  mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$BIN_DIR"

  if [[ ! -f "$CONFIG_FILE" ]]; then
    run_repo_python - <<'PY'
from cli.config import default_config_text, ensure_runtime_dirs

paths = ensure_runtime_dirs()
paths.config_file.write_text(default_config_text(), encoding="utf-8")
PY
  fi

  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
  "$VENV_DIR/bin/pip" install "$SCRIPT_DIR"

  ln -sfn "$VENV_DIR/bin/hrafn" "$BIN_LINK"
  export PATH="$BIN_DIR:$PATH"

  if ! command -v hrafn >/dev/null 2>&1; then
    echo "error: hrafn was not installed into $BIN_DIR" >&2
    exit 1
  fi

  hrafn --help >/dev/null
  install_sync_service
  update_saga_registry install
  echo "hrafn installed"
}

uninstall_hrafn() {
  if [[ "$DRY_RUN" == "1" ]]; then
    preview_uninstall
    return 0
  fi
  uninstall_sync_service
  if [[ -d "$VENV_DIR" ]]; then
    rm -rf "$VENV_DIR"
  fi

  remove_hrafn_packages
  restore_install_targets "$INSTALL_ID"
  restore_install_directories "$INSTALL_ID"
  clear_install_state "$INSTALL_ID"
  update_saga_registry uninstall
  echo "hrafn removed"
}

preview_install() {
  local requirement
  local pkg_entry command_name package_name

  echo "Hrafn install dry run"
  echo
  echo "System requirements:"
  if command -v python3 >/dev/null 2>&1; then
    echo "  keep existing: python3 ($(python3 --version 2>/dev/null))"
  else
    echo "  missing:       python3"
  fi
  if python3 -m venv --help >/dev/null 2>&1; then
    echo "  keep existing: python3 venv support"
  else
    echo "  missing:       python3 venv support"
  fi
  while IFS='|' read -r command_name package_name; do
    [[ -n "$command_name" ]] || continue
    if command -v "$command_name" >/dev/null 2>&1; then
      echo "  keep existing: $command_name ($package_name)"
    else
      echo "  install:       $package_name (provides $command_name)"
    fi
  done < <(list_hrafn_system_packages)
  echo
  if [[ -d "$CONFIG_DIR" ]]; then
    echo "Config directory exists: $CONFIG_DIR"
  else
    echo "Config directory would be created: $CONFIG_DIR"
  fi
  if [[ -d "$DATA_DIR" ]]; then
    echo "Data directory exists:   $DATA_DIR"
  else
    echo "Data directory would be created: $DATA_DIR"
  fi
  if [[ -e "$CONFIG_FILE" ]]; then
    echo "Existing config file would be preserved and reused: $CONFIG_FILE"
  else
    echo "New config file would be created: $CONFIG_FILE"
  fi
  if [[ -e "$BIN_LINK" || -L "$BIN_LINK" ]]; then
    echo "Existing CLI target would be backed up then replaced: $BIN_LINK"
  else
    echo "New CLI symlink would be created: $BIN_LINK"
  fi
  echo "User systemd timer would be installed at: $SYNC_TIMER_UNIT"
  echo "Default sync cadence would be: every 5 minutes"
  echo "Isolated virtualenv would be created at: $VENV_DIR"
  echo
  echo "Python packages declared by Hrafn:"
  while IFS= read -r requirement; do
    [[ -n "$requirement" ]] || continue
    echo "  install into venv: $requirement"
  done < <(list_python_requirements)
  echo
  if [[ -d "$VENV_DIR" ]]; then
    echo "Existing virtualenv packages that would be replaced:"
    list_installed_venv_packages | sed 's/^/  /'
  else
    echo "No existing Hrafn virtualenv found."
  fi
}

preview_uninstall() {
  local manifest
  local packages_listed=0
  local pkg

  manifest="$(manifest_file_for "$INSTALL_ID")"
  echo "Hrafn uninstall dry run"
  echo
  echo "Linux packages:"
  while IFS= read -r pkg; do
    [[ -n "$pkg" ]] || continue
    packages_listed=1
    echo "  remove if Hrafn installed it: $pkg"
  done < <(packages_with_status "$INSTALL_ID" "installed")
  if [[ "$packages_listed" == "0" ]]; then
    echo "  none"
  fi
  echo
  if [[ -f "$manifest" ]] && [[ -s "$manifest" ]]; then
    awk -F'|' '
      $2 == "1" { printf "Restore previous: %s\n", $1 }
      $2 == "0" { printf "Remove created:   %s\n", $1 }
    ' "$manifest"
  else
    echo "No Hrafn-managed install state found."
  fi

  if [[ -d "$VENV_DIR" ]]; then
    echo "Remove virtualenv: $VENV_DIR"
    echo "Python packages that would be removed with that virtualenv:"
    while IFS= read -r requirement; do
      [[ -n "$requirement" ]] || continue
      packages_listed=1
      echo "  $requirement"
    done < <(list_installed_venv_packages)
    if [[ "$packages_listed" == "0" ]]; then
      echo "  none detected"
    fi
  fi
  echo "Remove user systemd units if Hrafn installed them:"
  echo "  $SYNC_SERVICE_UNIT"
  echo "  $SYNC_TIMER_UNIT"
}

main() {
  local command="${1:-install}"
  if [[ "$command" == "--dry-run" ]]; then
    command="install"
    DRY_RUN=1
  fi
  if [[ "$command" != "install" && "$command" != "uninstall" && "$command" != "-h" && "$command" != "--help" && "$command" != "help" ]]; then
    echo "error: unknown command '$command'" >&2
    usage >&2
    exit 1
  fi
  shift || true
  if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
  fi

  case "$command" in
    install)
      install_hrafn
      ;;
    uninstall)
      uninstall_hrafn
      ;;
    -h|--help|help)
      usage
      ;;
  esac
}

main "$@"
