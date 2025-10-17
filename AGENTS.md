# Repository Guidelines

## Project Structure & Module Organization
- `app/` — FastAPI backend (`main.py`, `service_manager.py`), static assets in `app/static/`.
- `frontend/` — Nuxt 3 + TypeScript UI (`pages/`, `composables/`, `types/`). Build output at `.output/public` (symlinked as `frontend/dist`).
- `tests/` — Pytest suite (`test_*.py`).
- `config.yaml` — service and UI configuration; supports env var expansion.
- `nginx/`, `systemd/` — deployment configs. Additional notes in `doc/` and `README.md`.

## Build, Test, and Development Commands
- Backend run (default port 8610): `./run.sh`
- Backend dev (port 8621): `./run_dev_8621.sh` (stop with `./stop_dev_8621.sh`)
- Install backend deps: `pip install -r requirements.txt`
- Run tests: `bash run_tests.sh` (or `pytest -q`)
- Frontend dev: `cd frontend && npm ci && npm run dev`
- Frontend build/preview: `cd frontend && npm run build && npm run preview`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent, `snake_case` for functions/vars, `PascalCase` for classes, add type hints where practical. Keep side effects out of module import time.
- FastAPI: Prefer explicit routes and clear response models; keep handlers small and delegate logic to `service_manager.py`.
- Nuxt/Vue: Composition API with `<script setup>`. Pages in `frontend/pages/` use lowercase filenames (e.g., `logs.vue`); composables are `useX` (e.g., `useServices.ts`). Components use `PascalCase`.
- Linters/formatters: No enforced tool in repo; ensure consistent formatting and small, focused functions.

## Testing Guidelines
- Framework: Pytest. Place tests in `tests/` named `test_*.py`.
- Scope: Cover service control, status endpoints, config evaluation, and error paths (see `tests/test_app.py`, `tests/test_service_logic.py`).
- Run locally: `bash run_tests.sh`. Add tests for new endpoints or config semantics. See `TESTING.md` for manual checks.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:` (matches current history).
- PRs: clear description, link issues, include screenshots/GIFs for UI changes, and test outcomes. Update `README.md`/`TESTING.md` and `nginx/` or `systemd/` docs when behavior/config changes.

## Security & Configuration Tips
- Do not commit secrets. Prefer `.env` files; `run.sh` auto-loads from `/workspace/.env`, `/workspace/ikar_apps/ikar-admin/.env`, and `/workspace/pod_config_ikarosopolis/.env`.
- Respect `IKAR_ADMIN_PORT` and related `IKAR_ADMIN_*` env vars. Review `nginx/ikaros.conf` and `systemd/ikar-admin.service` when changing ports or paths.

