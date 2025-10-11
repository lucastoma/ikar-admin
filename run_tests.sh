#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

VENV=${IKAR_ADMIN_TEST_VENV:-/workspace/.venv/ikar-admin-tests}
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
python -m pip install -U pip wheel setuptools >/dev/null
python -m pip install -r requirements.txt >/dev/null
python -m pip install pytest >/dev/null

pytest -q

