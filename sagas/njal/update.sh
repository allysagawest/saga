#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-}"
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

ln -sfn "$REPO_ROOT/sagas/njal/zsh" "$HOME/.config/saga/zsh"
echo "njal updated"
