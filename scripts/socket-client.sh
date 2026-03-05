#!/usr/bin/env bash
set -euo pipefail

mode="${1:-}"
arg="${2:-}"
SOCKET_PATH="${SAGA_SOCKET:-$HOME/.local/share/saga/saga.sock}"

if [[ -z "$mode" || -z "$arg" ]]; then
  echo "usage: socket-client.sh <query|subscribe> <metric|event>" >&2
  exit 1
fi

if [[ ! -S "$SOCKET_PATH" ]]; then
  echo "error: saga socket not found: $SOCKET_PATH" >&2
  exit 1
fi

python3 - "$mode" "$arg" "$SOCKET_PATH" <<'PY'
import json
import socket
import sys

mode = sys.argv[1]
arg = sys.argv[2]
socket_path = sys.argv[3]

client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.connect(socket_path)
reader = client.makefile("r", encoding="utf-8", newline="\n")
writer = client.makefile("w", encoding="utf-8", newline="\n")

if mode == "query":
    writer.write(json.dumps({"command": "query", "metric": arg}) + "\n")
    writer.flush()
    line = reader.readline().strip()
    print(line if line else "{}")
elif mode == "subscribe":
    writer.write(json.dumps({"command": "subscribe", "event": arg}) + "\n")
    writer.flush()
    for line in reader:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_name = payload.get("event", arg)
        value = payload.get("value")

        if isinstance(value, (dict, list)):
            print(f"{event_name}\t{json.dumps(value, separators=(',', ':'))}", flush=True)
        elif value is None:
            print(f"{event_name}\t{json.dumps(payload, separators=(',', ':'))}", flush=True)
        else:
            print(f"{event_name}\t{value}", flush=True)
else:
    print("{}")
    sys.exit(1)
PY
