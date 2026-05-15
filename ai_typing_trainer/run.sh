#!/bin/bash
DIR="$(dirname "$(realpath "$0")")"
VENV_DIR="$(dirname "$DIR")/.venv"
wezterm start -- bash -c "source '$VENV_DIR/bin/activate' && python3 '$DIR/src/main.py'; exec bash"
