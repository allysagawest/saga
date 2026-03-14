#!/usr/bin/env bash
set -euo pipefail

SAGA_INSTALL_STATE_ROOT="${SAGA_INSTALL_STATE_ROOT:-$HOME/.local/share/saga/install-state}"

ensure_install_state_root() {
  mkdir -p "$SAGA_INSTALL_STATE_ROOT"
}

state_dir_for() {
  local install_id="$1"
  printf '%s/%s\n' "$SAGA_INSTALL_STATE_ROOT" "$install_id"
}

manifest_file_for() {
  local install_id="$1"
  printf '%s/targets.tsv\n' "$(state_dir_for "$install_id")"
}

dir_manifest_file_for() {
  local install_id="$1"
  printf '%s/directories.tsv\n' "$(state_dir_for "$install_id")"
}

package_manifest_file_for() {
  local install_id="$1"
  printf '%s/packages.tsv\n' "$(state_dir_for "$install_id")"
}

meta_file_for() {
  local install_id="$1"
  printf '%s/meta.env\n' "$(state_dir_for "$install_id")"
}

ensure_install_state() {
  local install_id="$1"
  local state_dir

  ensure_install_state_root
  state_dir="$(state_dir_for "$install_id")"
  mkdir -p "$state_dir/backups"
  touch "$(manifest_file_for "$install_id")"
  touch "$(dir_manifest_file_for "$install_id")"
  touch "$(package_manifest_file_for "$install_id")"
  touch "$(meta_file_for "$install_id")"
}

has_recorded_target() {
  local install_id="$1"
  local target="$2"
  local manifest

  manifest="$(manifest_file_for "$install_id")"
  [[ -f "$manifest" ]] || return 1
  grep -Fq "${target}|" "$manifest"
}

backup_target() {
  local install_id="$1"
  local target="$2"
  local backup_path
  local digest

  ensure_install_state "$install_id"
  if has_recorded_target "$install_id" "$target"; then
    return 0
  fi

  if [[ -e "$target" || -L "$target" ]]; then
    digest="$(printf '%s' "$target" | sha256sum | awk '{print $1}')"
    backup_path="$(state_dir_for "$install_id")/backups/$digest"
    cp -a "$target" "$backup_path"
    printf '%s|1|%s\n' "$target" "$backup_path" >> "$(manifest_file_for "$install_id")"
  else
    printf '%s|0|\n' "$target" >> "$(manifest_file_for "$install_id")"
  fi
}

record_directory_state() {
  local install_id="$1"
  local directory="$2"
  local manifest
  local existed=0

  ensure_install_state "$install_id"
  manifest="$(dir_manifest_file_for "$install_id")"
  if [[ -f "$manifest" ]] && grep -Fq "${directory}|" "$manifest"; then
    return 0
  fi

  if [[ -d "$directory" ]]; then
    existed=1
  fi

  printf '%s|%s\n' "$directory" "$existed" >> "$manifest"
}

record_package_state() {
  local install_id="$1"
  local package_name="$2"
  local status="$3"
  local manifest

  ensure_install_state "$install_id"
  manifest="$(package_manifest_file_for "$install_id")"
  if grep -Eq "^${package_name}\\|" "$manifest"; then
    awk -F'|' -v pkg="$package_name" -v st="$status" '
      BEGIN { OFS="|" }
      $1 == pkg { $2 = st }
      { print }
    ' "$manifest" > "${manifest}.tmp"
    mv "${manifest}.tmp" "$manifest"
    return 0
  fi

  printf '%s|%s\n' "$package_name" "$status" >> "$manifest"
}

packages_with_status() {
  local install_id="$1"
  local status="$2"
  local manifest

  manifest="$(package_manifest_file_for "$install_id")"
  [[ -f "$manifest" ]] || return 0
  awk -F'|' -v st="$status" '$2 == st { print $1 }' "$manifest"
}

set_install_meta() {
  local install_id="$1"
  local key="$2"
  local value="$3"
  local file

  ensure_install_state "$install_id"
  file="$(meta_file_for "$install_id")"
  if grep -Eq "^${key}=" "$file"; then
    awk -F'=' -v key="$key" -v value="$value" '
      BEGIN { OFS="=" }
      $1 == key { $2 = value }
      { print }
    ' "$file" > "${file}.tmp"
    mv "${file}.tmp" "$file"
    return 0
  fi

  printf '%s=%s\n' "$key" "$value" >> "$file"
}

has_install_meta() {
  local install_id="$1"
  local key="$2"
  local file

  file="$(meta_file_for "$install_id")"
  [[ -f "$file" ]] || return 1
  grep -Eq "^${key}=" "$file"
}

restore_install_targets() {
  local install_id="$1"
  local manifest

  manifest="$(manifest_file_for "$install_id")"
  [[ -f "$manifest" ]] || return 0

  tac "$manifest" | while IFS='|' read -r target existed backup_path; do
    [[ -n "$target" ]] || continue
    if [[ "$existed" == "1" && -n "$backup_path" && -e "$backup_path" ]]; then
      rm -rf "$target"
      cp -a "$backup_path" "$target"
    else
      rm -rf "$target"
    fi
  done
}

restore_install_directories() {
  local install_id="$1"
  local manifest

  manifest="$(dir_manifest_file_for "$install_id")"
  [[ -f "$manifest" ]] || return 0

  tac "$manifest" | while IFS='|' read -r directory existed; do
    [[ -n "$directory" ]] || continue
    if [[ "$existed" == "0" ]]; then
      rm -rf "$directory"
    fi
  done
}

clear_install_state() {
  local install_id="$1"
  local state_dir

  state_dir="$(state_dir_for "$install_id")"
  [[ -d "$state_dir" ]] || return 0
  rm -rf "$state_dir"
}
