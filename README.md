ikar-admin — minimal admin panel for Ikaros

What it is
- FastAPI service exposing simple controls and status for local services.
- Lives under path prefix /ikaros and listens on 127.0.0.1:8602 by default.
- Tiny HTML UI for quick start/stop/status + logs.

Endpoints
- GET /ikaros           – Connect page with service statuses.
- GET /ikaros/terminal    – Web terminal.
- GET /ikaros/logs        – Page for viewing logs.
- GET /ikaros/health    – JSON health (disk, ports)
- GET /ikaros/status    – JSON services status
- GET /ikaros/events?n=200 – Tail central action log (ik ar-admin-events.log)
- GET /ikaros/logs/{svc}?n=200 – Tail service log (legacy)
- POST /ikaros/start/{svc} - (API only)
- POST /ikaros/stop/{svc} - (API only)
- WS /ikaros/ws/pty     - WebSocket for the web terminal.

Status legend
- `UP` – service detected as running.
- `DOWN` – installed but not active.
- `MISSING` – binary/config missing.

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

Configuration (`config.yaml`)
---
Services are defined in `config.yaml`. Each service has the following attributes:

- `detect`: A list of patterns to detect if the service is running.
- `start_cmd`: The command to start the service.
- `stop_patterns`: A list of patterns to use with `pkill` to stop the service.
- `log_path`: The path to the service's log file.
- `port`: The port the service runs on.
- `available`: A safe boolean expression to check for availability. Supports `exists('/path/to/file')` and `which('binary')`, combined with `and` and `or`.
- `systemd_unit`: The name of the systemd unit for the service. If provided, `systemctl` will be used to start, stop, and check the status of the service.
- `pid_file`: Path to a file containing the process ID of the service. Used for more reliable stopping of the service.
- `workdir`: The working directory to run the `start_cmd` in.
- `env`: A dictionary of environment variables to set for the `start_cmd`.
- `start_timeout`: Timeout in seconds for waiting for the service to start (default: 8.0).
- `stop_timeout`: Timeout in seconds for waiting for the service to stop (default: 8.0).
- `health`: A dictionary defining a health check for the service.
  - `tcp`: Check if a TCP port is open.
    - `host`: The host to check (default: `127.0.0.1`).
    - `port`: The port to check.
    - `timeout`: The timeout in seconds (default: 2).
  - `http`: Check if an HTTP endpoint returns a successful response.
    - `url`: The URL to check.
    - `expect`: The expected HTTP status code (default: 200).
    - `timeout`: The timeout in seconds (default: 2).
