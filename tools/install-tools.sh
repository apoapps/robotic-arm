#!/usr/bin/env sh
set -eu

python3 -m pip install --user --upgrade pip
python3 -m pip install --user -r "$(dirname "$0")/requirements.txt"

echo "Installed tools. If your shell cannot find pio or mpremote, add this to PATH:"
echo "  export PATH=\"\$HOME/Library/Python/3.9/bin:\$PATH\""
