#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# Development configuration
export PYTHONUNBUFFERED=1
export IKAR_ADMIN_PORT=8621  # Stały port dla developmentu

# Load optional environment files (export all)
set +a
for ENV_FILE in \
  "/workspace/.env" \
  "/workspace/ikar_apps/ikar-admin/.env" \
  "/workspace/pod_config_ikarosopolis/.env"; do
  if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
done

# Force port override for development
export IKAR_ADMIN_PORT=8621

# Configuration (no nested venv by default)
PY_BIN=${IKAR_ADMIN_PY:-python3}
USE_VENV=${IKAR_ADMIN_USE_VENV:-0}
BOOTSTRAP=${IKAR_ADMIN_BOOTSTRAP:-0}

if [ "${USE_VENV}" = "1" ]; then
  VENV_DIR=${IKAR_ADMIN_VENV:-/workspace/.venv/ikar-admin}
  if [ ! -d "$VENV_DIR" ]; then
    "$PY_BIN" -m venv "$VENV_DIR"
  fi
  PY_BIN="$VENV_DIR/bin/python"
fi

if [ "${BOOTSTRAP}" = "1" ]; then
  PIP_BREAK=${IKAR_ADMIN_PIP_BREAK:-0}
  IN_VENV=$("$PY_BIN" -c "import sys; print('1' if sys.prefix!=getattr(sys,'base_prefix',sys.prefix) else '0')")
  if [ "$IN_VENV" = "1" ]; then
    "$PY_BIN" -m pip install -U pip wheel setuptools >/dev/null
    if [ "$PIP_BREAK" = "1" ]; then
      "$PY_BIN" -m pip install --break-system-packages -r "$BASE_DIR/requirements.txt" >/dev/null
    else
      "$PY_BIN" -m pip install -r "$BASE_DIR/requirements.txt" >/dev/null
    fi
  else
    # No venv: avoid upgrading pip/wheel; install requirements to user site
    "$PY_BIN" -m pip install --user -r "$BASE_DIR/requirements.txt" >/dev/null || {
      if [ "$PIP_BREAK" = "1" ]; then
        "$PY_BIN" -m pip install --break-system-packages -r "$BASE_DIR/requirements.txt" >/dev/null
      else
        echo "[ikar-admin] pip install failed in system env. Retry with IKAR_ADMIN_PIP_BREAK=1 or install deps manually." >&2
      fi
    }
  fi
fi

echo "🚀 Uruchamiam ikar-admin w trybie DEVELOPMENT na porcie 8621"
echo "📂 Katalog roboczy: $BASE_DIR"
echo "🌐 URL: http://127.0.0.1:8621/ikaros"
echo "⏹️  Zatrzymaj skryptem: stop_dev_8621.sh"

exec "$PY_BIN" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8621