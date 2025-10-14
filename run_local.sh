#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# Use a local directory instead of /workspace
mkdir -p ./local_workspace
chmod 777 ./local_workspace
export DATA_DIR=./local_workspace

export PYTHONUNBUFFERED=1
export IKAR_ADMIN_PORT=${IKAR_ADMIN_PORT:-8602}

# Configuration (no nested venv by default)
PY_BIN=${IKAR_ADMIN_PY:-python3}
USE_VENV=${IKAR_ADMIN_USE_VENV:-0}
BOOTSTRAP=${IKAR_ADMIN_BOOTSTRAP:-0}

if [ "${USE_VENV}" = "1" ]; then
  VENV_DIR=./.venv/ikar-admin
  if [ ! -d "$VENV_DIR" ]; then
    "$PY_BIN" -m venv "$VENV_DIR"
  fi
  PY_BIN="$VENV_DIR/bin/python"
fi

if [ "${BOOTSTRAP}" = "1" ]; then
  "$PY_BIN" -m pip install -r "$BASE_DIR/requirements.txt" >/dev/null
fi

exec "$PY_BIN" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port "$IKAR_ADMIN_PORT"