#!/usr/bin/env bash
set -euo pipefail

mode="${1:-app}"

if ! command -v walker >/dev/null 2>&1; then
  echo "error: walker is not installed" >&2
  exit 1
fi

case "$mode" in
  app)
    walker
    ;;
  files)
    walker --placeholder "Search files..." --query "~/"
    ;;
  commands)
    walker --placeholder "Run command..." --query ":"
    ;;
  *)
    walker
    ;;
esac
