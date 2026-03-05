#!/usr/bin/env bash
set -euo pipefail

mode="${1:-app}"

if ! command -v wofi >/dev/null 2>&1; then
  echo "error: wofi is not installed" >&2
  exit 1
fi

case "$mode" in
  app)
    wofi --show drun
    ;;
  files)
    echo "info: file search mode is not enabled for wofi yet" >&2
    exit 1
    ;;
  commands)
    wofi --show run
    ;;
  *)
    wofi --show drun
    ;;
esac
