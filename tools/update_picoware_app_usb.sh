#!/usr/bin/env sh
set -eu

APP_FILE="$(CDPATH= cd -- "$(dirname -- "$0")/../picoware/apps" && pwd)/robotarm.py"

REMOTE_PATH="${1:-:/picoware/apps/robotarm.py}"

echo "Updating Picoware app over USB with mpremote."
echo "Source: $APP_FILE"
echo "Target: $REMOTE_PATH"
echo ""
echo "If the app is stored on SD and Picoware does not expose SD over MicroPython,"
echo "copy it to internal flash instead and launch that copy from Picoware."

mpremote fs mkdir :/picoware 2>/dev/null || true
mpremote fs mkdir :/picoware/apps 2>/dev/null || true
mpremote fs cp "$APP_FILE" "$REMOTE_PATH"
mpremote reset
