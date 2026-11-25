#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/app.py" "$@"
elif [ -f "$SCRIPT_DIR/../.venv/bin/python" ]; then
    exec "$SCRIPT_DIR/../.venv/bin/python" "$SCRIPT_DIR/app.py" "$@"
elif command -v python3 &>/dev/null; then
    exec python3 "$SCRIPT_DIR/app.py" "$@"
else
    exec python "$SCRIPT_DIR/app.py" "$@"
fi

