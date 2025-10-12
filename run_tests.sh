#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# Defaults: use current Python; no new venv by default
PY_BIN=${IKAR_ADMIN_PY:-python3}
TEST_USE_VENV=${IKAR_ADMIN_TEST_USE_VENV:-0}     # set to 1 to use a dedicated venv
TEST_BOOTSTRAP=${IKAR_ADMIN_TEST_BOOTSTRAP:-0}   # set to 1 to install deps into selected interpreter

if [ "${TEST_USE_VENV}" = "1" ]; then
  VENV=${IKAR_ADMIN_TEST_VENV:-/workspace/.venv/ikar-admin-tests}
  if [ ! -d "$VENV" ]; then
    "$PY_BIN" -m venv "$VENV"
  fi
  PY_BIN="$VENV/bin/python"
fi

if [ "${TEST_BOOTSTRAP}" = "1" ]; then
  "$PY_BIN" -m pip install -U pip wheel setuptools >/dev/null
  "$PY_BIN" -m pip install -r requirements.txt >/dev/null
  "$PY_BIN" -m pip install pytest >/dev/null
fi

"$PY_BIN" -m pytest -q
