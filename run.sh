#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

mkdir -p /workspace
chmod 777 /workspace

export PYTHONUNBUFFERED=1
export IKAR_ADMIN_PORT=${IKAR_ADMIN_PORT:-8602}
VENV_DIR=${IKAR_ADMIN_VENV:-/workspace/.venv/ikar-admin}

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install -U pip wheel setuptools >/dev/null
python -m pip install -r "$BASE_DIR/requirements.txt" >/dev/null

exec "$VENV_DIR/bin/python" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port "$IKAR_ADMIN_PORT"
