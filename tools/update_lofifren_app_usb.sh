#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PORT="${PORT:-/dev/cu.usbmodem11301}"
LOFIFREN_ROOT="${LOFIFREN_ROOT:-/Volumes/ApoSSD/Documents/PicoCalc-LofiFren}"
PY_RUN_SRC="$LOFIFREN_ROOT/MicroPython/modules/py_run.py"
TMP_PY_RUN="/tmp/py_run_robotarm.py"

python3 -m mpremote connect "$PORT" fs cp "$ROOT/picocalc-lofifren/robotarm.py" :/sd/py_scripts/robotarm.py

if [ -f "$PY_RUN_SRC" ]; then
  cp "$PY_RUN_SRC" "$TMP_PY_RUN"
  python3 - "$TMP_PY_RUN" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
text = text.replace('def find_py_files(base_path="/sd"):', 'def find_py_files(base_path="/sd/py_scripts"):')
text = text.replace('relative_path = full_path[len("/sd/"):-3]', 'relative_path = full_path[len("/sd/py_scripts/"):-3]')
text = text.replace('def run_script(script_path, base_path="/sd"):', 'def run_script(script_path, base_path="/sd/py_scripts"):')
old = """                    _w(f'{name} exited.\\n\\n')
                    _rst()
                    input("Press Enter for menu...")"""
new = """                    _w(f'{name} exited.\\n')
                    _rst()
                    utime.sleep_ms(500)"""
text = text.replace(old, new)
path.write_text(text)
PY
  python3 -m mpremote connect "$PORT" fs cp "$TMP_PY_RUN" :/modules/py_run.py
else
  echo "Skipped py_run.py patch: $PY_RUN_SRC not found" >&2
fi

python3 -m mpremote connect "$PORT" reset
