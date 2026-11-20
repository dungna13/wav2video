#!/usr/bin/env bash
# Runner script tiện lợi: Tự động dùng đúng môi trường Python venv của dự án
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$SCRIPT_DIR/../.venv/bin:$PATH"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
PYTHON_BIN="$SCRIPT_DIR/../.venv/bin/python"

if [ -f "$PYTHON_BIN" ]; then
    exec "$PYTHON_BIN" "$SCRIPT_DIR/main.py" "$@"
else
    exec python3 "$SCRIPT_DIR/main.py" "$@"
fi

