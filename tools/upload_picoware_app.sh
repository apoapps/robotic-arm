#!/usr/bin/env sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../picoware/apps" && pwd)"
APP_FILE="$APP_DIR/robot_arm_remote.py"

echo "Trying mpremote copy to /picoware/apps/robot_arm_remote.py"
echo "If this fails because the app lives on the SD card, copy the file manually to SD:/picoware/apps/."
mpremote fs mkdir :/picoware 2>/dev/null || true
mpremote fs mkdir :/picoware/apps 2>/dev/null || true
mpremote fs cp "$APP_FILE" :/picoware/apps/robot_arm_remote.py
mpremote reset
