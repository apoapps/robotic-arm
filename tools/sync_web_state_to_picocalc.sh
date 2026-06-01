#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PORT="${PORT:-/dev/cu.usbmodem11301}"
STATE_FILE="$ROOT/web/robot-control/data/state.json"

python3 -m mpremote connect "$PORT" fs cp "$STATE_FILE" :/sd/robotarm.json
echo "Synced web state to /sd/robotarm.json"
