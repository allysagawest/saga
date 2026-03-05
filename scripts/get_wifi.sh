#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if command -v saga >/dev/null 2>&1; then
  SAGA_CMD=(saga)
else
  SAGA_CMD=("$REPO_ROOT/saga")
fi
"${SAGA_CMD[@]}" query wifi | jq -r '.wifi // .value // "offline"'
