#!/usr/bin/env sh
set -eu

UF2_NAME="${1:-}"
BOOT_VOLUME="${2:-}"

if [ -z "$UF2_NAME" ]; then
  echo "Usage: $0 <uf2-name> [boot-volume]"
  echo ""
  echo "Known PicoCalc MicroPython UF2 names:"
  echo "  Picoware-PicoCalcPico.uf2"
  echo "  Picoware-PicoCalcPicoW.uf2"
  echo "  Picoware-PicoCalcPico2.uf2"
  echo "  Picoware-PicoCalcPico2W.uf2"
  exit 2
fi

if [ -z "$BOOT_VOLUME" ]; then
  if [ -d /Volumes/RPI-RP2 ]; then
    BOOT_VOLUME="/Volumes/RPI-RP2"
  elif [ -d /Volumes/RP2350 ]; then
    BOOT_VOLUME="/Volumes/RP2350"
  else
    echo "No Pico BOOTSEL volume found. Hold BOOTSEL while connecting USB."
    echo "Refusing to flash /Volumes/NO NAME because that is usually an SD card."
    exit 1
  fi
fi

if [ ! -d "$BOOT_VOLUME" ]; then
  echo "Boot volume does not exist: $BOOT_VOLUME"
  exit 1
fi

if [ ! -f "$BOOT_VOLUME/INFO_UF2.TXT" ] && [ ! -f "$BOOT_VOLUME/INDEX.HTM" ] && [ ! -f "$BOOT_VOLUME/CURRENT.UF2" ]; then
  echo "Refusing to flash: $BOOT_VOLUME does not look like a Pico BOOTSEL UF2 volume."
  exit 1
fi

TAG="$(python3 - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("https://api.github.com/repos/jblanked/Picoware/releases/latest", timeout=20) as response:
    print(json.load(response)["tag_name"])
PY
)"

URL="https://raw.githubusercontent.com/jblanked/Picoware/${TAG}/builds/MicroPython/${UF2_NAME}"
TMP_FILE="${TMPDIR:-/tmp}/${UF2_NAME}"

echo "Downloading Picoware ${TAG}: ${UF2_NAME}"
curl -L --fail "$URL" -o "$TMP_FILE"

echo "Flashing to $BOOT_VOLUME"
cp "$TMP_FILE" "$BOOT_VOLUME/"
sync
echo "Done. The board should reboot after the UF2 copy completes."
