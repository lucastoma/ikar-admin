# Service Configuration & API Data Model

This document captures the contract between the FastAPI backend and any frontend (Nuxt/Vue or the legacy HTML templates).  
Goals:
- describe everything the UI needs without coupling to rendering logic,
- standardise execution details for starting/stopping services,
- keep backwards compatibility so existing deployments keep working.

---

## 1. Service Configuration (`config.yaml`)

Each service entry now consists of four logical blocks: **metadata**, **runtime**, **lifecycle**, and **observability**.

```yaml
services:
  <service-name>:
    meta:
      title: "Human friendly name"
      description: "Optional short summary rendered in UI tooltips."
      tags: ["category", "optional"]
      links:
        - label: "Dashboard"
          url: "http://localhost:{port}/"
          kind: "external"     # optional, defaults to external
        - label: "Docs"
          url: "https://internal/wiki"
          kind: "doc"

    runtime:
      workdir: "/workspace/project"      # optional override for cwd
      env:                                # extra environment variables
        MY_FLAG: "1"
      shell: "/usr/bin/env bash"          # interpreter used when running inline scripts

    lifecycle:
      start:
        script: |
          #!/usr/bin/env bash
          set -euo pipefail
          # script body – may assume `bash`
          nohup my-binary > "$LOG_FILE" 2>&1 &
          echo $! > "$PID_FILE"
        timeout: 12.0                    # optional float, seconds
      stop:
        pid_file: "/workspace/service.pid"
        patterns:
          - "my-binary --serve"
        timeout: 10.0

    observability:
      log_path: "/workspace/service.log"
      port: 9000
      health:
        http:
          url: "http://127.0.0.1:9000/health"
          timeout: 5

    detect:
      - "my-binary --serve"
    systemd_unit: "service-name"          # still supported
    available: "exists('/workspace/bin/my-binary')"  # same expression language
```

### Compatibility Notes
- Existing flat keys (`start_cmd`, `stop_patterns`, `log_path`, `pid_file`, `workdir`, `env`, `health`, `start_timeout`, `stop_timeout`) are still understood. Supplying the new nested blocks takes precedence.
- When `lifecycle.start.script` is present it must start with a shebang. The runner writes the script to a temporary file, marks it executable, and invokes it directly. If no `shell` override is provided the shebang decides the interpreter.
- `IKAR_SERVICE`, `SERVICE_PORT`, `IKAR_SERVICE_PORT`, `LOG_FILE`, and `PID_FILE` are injected into the start-script environment when known, on top of whatever is defined under `runtime.env`.
- If a `pid_file` is defined, the start script is responsible for writing the PID. The stop sequence first attempts graceful termination via the PID file before falling back to patterns or `systemd`.

---

## 2. JSON API Shape

### `GET /ikaros/services`

Returns metadata necessary for rendering the dashboard and action panels.

```json
{
  "services": [
    {
      "name": "comfyui",
      "title": "ComfyUI",
      "description": "Workflow UI for image generation.",
      "tags": ["ml"],
      "available": true,
      "running": true,
      "port": 18188,
      "links": [
        {"label": "Dashboard", "url": "http://localhost:18188/", "kind": "external"}
      ],
      "log_path": "/workspace/comfyui.log",
      "supports": {
        "start": true,
        "stop": true,
        "logs": true,
        "terminal": false
      }
    }
  ]
}
```

### `GET /ikaros/services/<name>`

Detailed view combining live status with static metadata.

```json
{
  "name": "comfyui",
  "meta": {
    "title": "ComfyUI",
    "description": "...",
    "tags": ["ml"],
    "links": [...]
  },
  "status": {
    "available": true,
    "running": true,
    "health": {
      "http": {
        "url": "http://127.0.0.1:18188/",
        "timeout": 5
      }
    },
    "log_path": "/workspace/comfyui.log",
    "port": 18188
  },
  "lifecycle": {
    "has_start": true,
    "has_stop": true,
    "systemd_unit": "comfyui-ikar",
    "pid_file": "/workspace/comfyui.pid",
    "start_timeout": 15.0,
    "stop_timeout": 12.0
  }
}
```

### Other Endpoints

The existing endpoints remain but their semantics are clarified for the Nuxt frontend:

| Endpoint | Purpose | Notes |
| --- | --- | --- |
| `GET /ikaros/status` | Lightweight map `{name: running}` | Used for polling. |
| `GET /ikaros/health` | Summary card data (disk usage, port checks, service states) | Unchanged payload. |
| `GET /ikaros/events?n=` | Tail of central event log | Accepts `n=1..2000`. |
| `GET /ikaros/logs/<name>?n=` | Tail of individual service log | Returns 404 if service missing. |
| `POST /ikaros/start/<name>` | Trigger start | JSON response includes `ok`, `message`, `running`. |
| `POST /ikaros/stop/<name>` | Trigger stop | As above. |
| `GET /ikaros/env.json?prefix=` | Filtered environment map | Accepts comma-separated prefixes. |
| `GET /ikaros/comfy/config/raw` | Raw YAML for Comfy mapping | Adds `Content-Type: text/plain`. |
| `GET /ikaros/comfy/config/validate` | Directory validation | Returns lists `present`/`missing`. |
| `POST /ikaros/comfy/config/install` | Rebuild symlink | Returns `{ok: bool}`. |
| `WS /ikaros/ws/pty` | Interactive shell | No change; Nuxt front embeds xterm.js. |

---

## 3. Data Needed by the Nuxt Frontend

1. **Service Catalogue** – one call to `/ikaros/services` to populate navigation and cards.  
2. **Live Status Polling** – periodic `/ikaros/status`.  
3. **Actions** – reuse `/start`, `/stop`, `/logs`, `/events` as-is.  
4. **Terminal** – continue connecting to the websocket.  
5. **Environment Browser** – use `/env.json` with user-supplied prefixes.  
6. **Comfy Config Tools** – same endpoints the current HTML uses.

This contract allows the frontend to be rewritten without touching backend logic again; any future UI can plug into the same JSON sources.
