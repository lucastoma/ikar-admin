ikar-admin — minimal admin panel for Ikaros

What it is
- FastAPI service exposing simple controls and status for local services.
- Lives under path prefix /ikaros and listens on 127.0.0.1:8602 by default.
- Tiny HTML UI for quick start/stop/status + logs.

Endpoints
- GET /ikaros           – HTML dashboard
- GET /ikaros/health    – JSON health (disk, ports)
- GET /ikaros/status    – JSON services status
- GET /ikaros/events?n=200 – Tail central action log (ik ar-admin-events.log)
- GET /ikaros/logs/{svc}?n=200 – Tail service log (legacy)
- POST /ikaros/start/{svc}
- POST /ikaros/stop/{svc}

Status legend
- `UP` (green) – service detected as running.
- `DOWN` (red) – installed but not active.
- `MISSING` (gray) – binary/config missing; start/stop buttons are disabled and API returns `ok: false` with `"Service not installed"`.

Services covered
- comfyui (port 18188, log: /workspace/comfyui.log)
- code (code-server on port 8445, log: /workspace/code-server.log)
- filebrowser (optional, if binary exists; default port 8085)
- tailscale (daemon only; start may require sudo NOPASSWD)

Run locally
1) Install deps (inside ikaros):
   pip install -r /workspace/ikar_apps/ikar-admin/requirements.txt
2) Start:
   bash /workspace/ikar_apps/ikar-admin/run.sh
3) Open: http://127.0.0.1:8602/ikaros

Optional: CLI helper
- A small wrapper is installed at /workspace/bin/podctl to call the API:
  podctl status | start <svc> | stop <svc> | logs <svc> [N]

Tests
- Script creates a venv and runs pytest:
  bash /workspace/ikar_apps/ikar-admin/run_tests.sh
- What’s covered:
  - HTML dashboard renders with services and controls
  - /status JSON shape
  - start/stop endpoints return JSON (with `ok`) and 303 redirect for HTML flows
  - /events returns tail of central log
  - health JSON shape
  - missing service path returns disabled buttons + `Service not installed`

Notes
- For code-server, the panel will look for a local binary under /workspace/code-server or in PATH.
- Tailscale start uses userspace networking with state at /workspace/tailscale.state.
- To expose UI at http://localhost/ikaros (port 80), configure an Nginx reverse proxy to 127.0.0.1:8602.
