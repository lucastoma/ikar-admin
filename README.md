ikar-admin — minimal admin panel for Ikaros

What it is
- FastAPI service that wraps a catalogue of local services and exposes both a JSON API and a simple HTML dashboard.
- Lives under prefix `/ikaros` on `127.0.0.1:8610` by default (configurable via `IKAR_ADMIN_PORT`); the HTML UI remains for convenience while we prototype a Nuxt/Vue front end.
- Service metadata, lifecycle commands, and observability settings are now expressed entirely in `config.yaml`, so any UI can be rebuilt on top of the same contract.

Endpoints
- **HTML**
  - `GET /ikaros` – Dashboard (statuses, controls, quick links).
  - `GET /ikaros/terminal` – In-browser terminal backed by `/ikaros/ws/pty`.
  - `GET /ikaros/logs` – Log tailer with filtering.
  - `GET /ikaros/env` – Environment browser with prefix filters.
  - `GET /ikaros/comfy` – ComfyUI config inspector and validator.
- **JSON**
  - `GET /ikaros/services` – Service catalogue with metadata and live status.
  - `GET /ikaros/services/{name}` – Detailed view for a single service.
  - `GET /ikaros/status` – Lightweight `{name: bool}` map for polling.
  - `GET /ikaros/health` – Summary card data (disk usage + port probes).
  - `GET /ikaros/events?n=` – Tail `ikar-admin-events.log`.
  - `GET /ikaros/logs/{name}?n=` – Tail selected service log.
  - `GET /ikaros/env.json?prefix=` – Filtered environment snapshot.
  - Comfy helpers: `/ikaros/comfy/config/raw`, `/ikaros/comfy/config/validate`, `/ikaros/comfy/config/install`.
- **Mutating**
  - `POST /ikaros/start/{name}`
  - `POST /ikaros/stop/{name}`
  - `WS /ikaros/ws/pty`

Status legend
- `UP` – service detected as running.
- `DOWN` – installed but not active.
- `MISSING` – binary/config missing.

Services covered out of the box
- `comfyui` (port 18188, log `/workspace/comfyui.log`)
- `code` (code-server on port 8445, log `/workspace/code-server.log`)
- `filebrowser` (optional, default port 8085, log `/workspace/filebrowser.log`)
- `tailscale` (userspace daemon, log `/workspace/tailscale.log`)
- `my_api` (example process, port 9000)

Run locally
1) Install deps (current interpreter, no venv):
   `pip install -r /workspace/ikar_apps/ikar-admin/requirements.txt`
2) Start backend:
   `bash /workspace/ikar_apps/ikar-admin/run.sh`
   - Bootstrap deps into the interpreter: `IKAR_ADMIN_BOOTSTRAP=1 .../run.sh`
   - Allow install into externally-managed Python: add `IKAR_ADMIN_PIP_BREAK=1`
   - Force dedicated venv: `IKAR_ADMIN_USE_VENV=1 IKAR_ADMIN_BOOTSTRAP=1 .../run.sh`
   - **Development mode** (port 8621, no service conflicts): `bash /workspace/ikar_apps/ikar-admin/run_dev_8621.sh`
3) Browse to:
   - Production: `http://127.0.0.1:8610/ikaros`
   - Development: `http://127.0.0.1:8621/ikaros`

Service Management (systemd)
- Install/restart service with updated symlink: `bash /workspace/ikar_apps/ikar-admin/restart_service.sh`
- Stop service and disable autorestart: `bash /workspace/ikar_apps/ikar-admin/stop_service.sh`

Systemd Service Installation
1) Manual installation (one-time setup):
   ```bash
   sudo ln -sf /workspace/ikar_apps/ikar-admin/systemd/ikar-admin.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable ikar-admin.service
   ```

2) Or use the restart script (handles symlink creation):
   ```bash
   sudo /workspace/ikar_apps/ikar-admin/restart_service.sh
   ```

3) Check service status:
   ```bash
   sudo systemctl status ikar-admin.service
   ```

Service Configuration
- **User**: Runs as `dev` user
- **Auto-restart**: Always restarts on failure (2 second delay)
- **Working Directory**: `/workspace/ikar_apps/ikar-admin`
- **Environment**: Includes default ports for ComfyUI (18188), FileBrowser (8085), Code Server (8445)

Tests
- Quick run (reuses interpreter): `bash /workspace/ikar_apps/ikar-admin/run_tests.sh`
- Dedicated venv: `IKAR_ADMIN_TEST_USE_VENV=1 bash .../run_tests.sh`
- Bootstrap deps (pytest + pytest-mock) inside the chosen interpreter/venv:
  `IKAR_ADMIN_TEST_BOOTSTRAP=1 ...`
- Coverage:
  - HTML dashboard rendering
  - Service status map
  - Start/stop flows (JSON + redirect)
  - Event/log tail endpoints
  - Availability expression evaluator

Available Scripts
- **`run.sh`** - Main startup script with environment loading and workspace setup (port 8610)
- **`run_dev_8621.sh`** - Development mode with fixed port 8621 (no service conflicts)
- **`run_tests.sh`** - Test runner with optional venv and dependency bootstrap
- **`restart_service.sh`** - Service management with symlink refresh and status display
- **`stop_service.sh`** - Proper service shutdown with autorestart disabled
- **`stop_dev_8621.sh`** - Stop development server running on port 8621

CLI helper
- `/workspace/bin/podctl` wraps the API (`status`, `start`, `stop`, `logs`).

Environment Configuration
- The application loads environment variables from `.env` files in order of priority:
  1. `/workspace/.env` (lowest priority)
  2. `/workspace/ikar_apps/ikar-admin/.env` (medium priority)
  3. `/workspace/pod_config_ikarosopolis/.env` (highest priority - overrides others)
- Later files override variables from earlier files, allowing flexible configuration per environment.

Data layout & Comfy helpers
- `DATA_DIR` (default `/workspace/ikar_data`) stores Comfy assets (`models/`, `assets/`, `flows/`, `nodes/`).
- `pod_config_ikarosopolis/scripts/setup_data_layout.sh` prepares directories and generates `extra_model_paths.yaml`.
- `/ikaros/comfy` lets you inspect the effective YAML, validate directories, and reinstall the symlink into `ComfyUI/extra_model_paths.yaml`.

Configuration (`config.yaml`)
---
The service catalogue is fully declarative. Each entry is split into four sections:

```yaml
services:
  comfyui:
    meta:
      title: "ComfyUI"
      description: "Nodes-based workflow UI"
      tags: ["ml", "ui"]
      links:
        - label: "Open UI"
          url: "http://localhost:{port}/"
    runtime:
      workdir: "/workspace/comfyui"
      env:
        CUDA_VISIBLE_DEVICES: ""
      shell: "/usr/bin/env bash"
    lifecycle:
      start:
        script: |
          #!/usr/bin/env bash
          set -euo pipefail
          ...
          nohup /usr/local/bin/python main.py --listen 0.0.0.0 --port "${COMFYUI_PORT:-18188}" --cpu \
            >> "${LOG_FILE}" 2>&1 &
          echo $! > "${PID_FILE}"
        timeout: 15.0
      stop:
        pid_file: "/workspace/comfyui.pid"
        patterns: ["ComfyUI/main.py"]
    observability:
      log_path: "/workspace/comfyui.log"
      port: 18188
      health:
        http:
          url: "http://127.0.0.1:${COMFYUI_PORT:-18188}/"
          timeout: 5
    detect:
      - "ComfyUI/main.py"
      - "python .*ComfyUI/main.py"
    available: "exists('/workspace/comfyui/main.py')"
    systemd_unit: "comfyui-ikar"
```

Key points:
- `meta` drives UI presentation (display name, description, tags, quick links). Placeholders such as `{port}` are expanded automatically.
- `runtime` defines the execution context for lifecycle scripts (working directory, interpreter, additional env vars).
- `lifecycle.start.script` is an inline file with a shebang; it must arrange background processes and write the PID file when one is configured. `lifecycle.stop` combines PID-file shutdown and optional fallback patterns.
- `observability` collects log locations, ports, and optional health probes (`tcp` / `http`).
- Legacy keys (`start_cmd`, `stop_patterns`, `log_path`, `pid_file`, `env`, `workdir`, `health`, etc.) continue to work, but the structured form above is preferred.

The backend injects a few convenience environment variables while running start scripts:
`IKAR_SERVICE`, `SERVICE_PORT`, `IKAR_SERVICE_PORT`, `LOG_FILE`, and `PID_FILE` (when known).

For a deeper schema reference and API payload examples see `doc/service_config_schema.md`.

Additional Documentation
- **`ANALYSIS_REPORT.md`** - Comprehensive technical analysis of the application architecture, features, and security considerations

Notes
- code-server detection prefers the local binary at `/workspace/code-server` before falling back to `PATH`.
- Tailscale start uses `sudo -n tailscaled` in userspace networking mode (`/workspace/tailscale.state`).
- To expose the UI at `http://localhost/ikaros` (port 80) front it with an Nginx reverse proxy pointing to `127.0.0.1:8610`.
