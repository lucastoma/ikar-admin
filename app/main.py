from fastapi import FastAPI, APIRouter, Response, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from . import service_manager as sm
import os
import shutil
import json
import time
import socket
import shutil as _shutil
import asyncio
import pty
import select
import fcntl
import signal
import yaml
from pathlib import Path
from html import escape


app = FastAPI(title="ikar-admin", docs_url=None, redoc_url=None)
router = APIRouter(prefix="/ikaros")

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@router.websocket("/ws/pty")
async def websocket_pty(ws: WebSocket):
    await ws.accept()

    # Basic origin/host check: allow when same host:port or when Origin missing
    origin = ws.headers.get("origin", "")
    host = ws.headers.get("host", "")
    if origin:
        try:
            origin_host = origin.split("://", 1)[-1]
        except Exception:
            origin_host = origin
        if origin_host != host:
            await ws.close(code=1008, reason="Invalid origin")
            return

    sm._append_event("terminal", "open", f"Session opened from {ws.client.host}", True)

    try:
        pid, fd = pty.fork()
    except OSError:
        await ws.send_text("\r\nPTY not supported on this platform.\r\n")
        sm._append_event("terminal", "open", "PTY not supported", False)
        await ws.close()
        return

    if pid == 0:  # Child process
        try:
            os.environ["TERM"] = "xterm-256color"
            os.execv("/bin/bash", ["/bin/bash", "-l"])
        except Exception:
            os._exit(127)

    # Reader: WS -> PTY
    async def ws_to_pty():
        try:
            while True:
                data = await ws.receive_text()
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "resize":
                        import termios
                        import struct
                        cols = int(msg.get("cols", 80))
                        rows = int(msg.get("rows", 24))
                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
                        continue
                except json.JSONDecodeError:
                    pass
                os.write(fd, data.encode())
        except WebSocketDisconnect:
            pass

    # Writer: PTY -> WS
    async def pty_to_ws():
        try:
            while True:
                try:
                    output = await asyncio.to_thread(os.read, fd, 1024)
                except OSError:
                    break
                if output:
                    await ws.send_text(output.decode("utf-8", "ignore"))
                else:
                    await asyncio.sleep(0.05)
        except Exception:
            pass

    try:
        await asyncio.gather(ws_to_pty(), pty_to_ws())
    except Exception as e:
        sm._append_event("terminal", "error", str(e), False)
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.close(fd)
        except Exception:
            pass
        sm._append_event("terminal", "close", f"Session closed for {ws.client.host}", True)


def _disk_info(path: str):
    total, used, free = _shutil.disk_usage(path)
    return {
        "path": path,
        "total_gb": round(total / 1e9, 2),
        "used_gb": round(used / 1e9, 2),
        "free_gb": round(free / 1e9, 2),
    }


def _port_open(p: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", p), 0.2):
            return True
    except OSError:
        return False


@router.get("/health")
def health():
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    return JSONResponse(
        {
            "ok": True,
            "time": int(time.time()),
            "disk": _disk_info("/workspace"),
            "ports": {
                "comfyui": _port_open(int(os.environ.get("COMFYUI_PORT", "18188"))),
                "code": _port_open(int(os.environ.get("CODE_SERVER_PORT", "8445"))),
                "filebrowser": _port_open(int(os.environ.get("FILEBROWSER_PORT", "8085"))),
            },
            "services": {k: v.is_running() for k, v in services.items()},
        }
    )


@router.get("/status")
def status():
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    return JSONResponse({k: v.is_running() for k, v in services.items()})


@router.get("/services")
def services_catalog():
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    items = []
    for svc in services.values():
        items.append(svc.summary(running=svc.is_running()))
    return JSONResponse({"services": items})


@router.get("/services/{svc_name}")
def service_detail(svc_name: str):
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    svc = services.get(svc_name)
    if not svc:
        raise HTTPException(status_code=404, detail="unknown service")
    return JSONResponse(svc.detail(running=svc.is_running()))


@router.get("/logs/{svc}")
def logs(svc: str, n: int = 200):
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    s = services.get(svc)
    if not s:
        return PlainTextResponse("unknown service", status_code=404)
    out = sm.tail_file(s.log_path, n)
    return PlainTextResponse(out)


@router.get("/events")
def events(n: int = 200):
    return PlainTextResponse(sm.tail_file(sm.EVENT_LOG_PATH, n))


@router.post("/start/{svc}")
def start(request: Request, svc: str, redirect: int = 0):
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    s = services.get(svc)
    if not s:
        return JSONResponse({"ok": False, "error": "unknown service"}, status_code=404)
    success, msg = s.start()
    # If called from the HTML form, bounce back to dashboard
    want_redirect = redirect or ("text/html" in request.headers.get("accept", ""))
    if want_redirect:
        return RedirectResponse(url="/ikaros", status_code=303)
    return JSONResponse({"ok": success, "message": msg, "running": s.is_running()})


@router.post("/stop/{svc}")
def stop(request: Request, svc: str, redirect: int = 0):
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    s = services.get(svc)
    if not s:
        return JSONResponse({"ok": False, "error": "unknown service"}, status_code=404)
    success, msg = s.stop()
    want_redirect = redirect or ("text/html" in request.headers.get("accept", ""))
    if want_redirect:
        return RedirectResponse(url="/ikaros", status_code=303)
    return JSONResponse({"ok": success, "message": msg, "running": s.is_running()})


def _render_page(title: str, content: str, current_path: str, services: dict = None):
    nav_links = {
        "/ikaros": "Connect",
        "/ikaros/terminal": "Terminal",
        "/ikaros/logs": "Logs",
        "/ikaros/env": "Env",
        "/ikaros/comfy": "Comfy",
    }
    nav_html = "".join(
        f"<a href='{path}' class='{'active' if path == current_path else ''}'>{name}</a>"
        for path, name in nav_links.items()
    )

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{title} - ikar-admin</title>
        <link rel="stylesheet" href="/static/xterm/xterm.css">
        <script src="/static/xterm/xterm.min.js"></script>
        <style>
            :root {{
                --bg-color: #0d1117;
                --text-color: #c9d1d9;
                --border-color: #30363d;
                --accent-color: #58a6ff;
                --header-bg: #161b22;
                --status-up: #238636;
                --status-down: #da3633;
                --status-missing: #8b949e;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 960px;
                margin: 20px auto;
                padding: 0 20px;
            }}
            header {{
                background-color: var(--header-bg);
                border-bottom: 1px solid var(--border-color);
                padding: 12px 20px;
                display: flex;
                align-items: center;
                gap: 16px;
            }}
            header h1 {{
                margin: 0;
                font-size: 1.5em;
            }}
            nav a {{
                color: var(--text-color);
                text-decoration: none;
                padding: 8px 12px;
                border-radius: 6px;
            }}
            nav a.active {{
                background-color: var(--accent-color);
                color: var(--bg-color);
                font-weight: 600;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid var(--border-color);
                padding: 10px 14px;
                text-align: left;
            }}
            th {{
                background-color: var(--header-bg);
            }}
            .status-badge {{
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: 600;
                color: #fff;
            }}
            .status-up {{ background-color: var(--status-up); }}
            .status-down {{ background-color: var(--status-down); }}
            .status-missing {{ background-color: var(--status-missing); }}
            a {{ color: var(--accent-color); }}
            #terminal-container, #log-container {{
                border: 1px solid var(--border-color);
                margin-top: 20px;
                min-height: 400px;
            }}
            .log-controls {{
                display: flex;
                gap: 10px;
                align-items: center;
                padding: 10px;
                background: var(--header-bg);
                border-bottom: 1px solid var(--border-color);
            }}
            select, input[type=text], button {{
                background-color: var(--bg-color);
                color: var(--text-color);
                border: 1px solid var(--border-color);
                padding: 5px 8px;
                border-radius: 6px;
            }}
            .chip-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin: 6px 0;
            }}
            .chip {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: var(--border-color);
                color: var(--text-color);
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.85em;
            }}
            .chip button {{
                border: none;
                background: transparent;
                color: inherit;
                cursor: pointer;
                font-size: 0.9em;
            }}
            #toast {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #333;
                color: #fff;
                padding: 8px 12px;
                border-radius: 4px;
                opacity: 0;
                transition: opacity 0.3s;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>ikar-admin</h1>
            <nav>{nav_html}</nav>
        </header>
        <main class="container">
            {content}
        </main>
    </body>
    </html>
    """
    return HTMLResponse(html)

@router.get("/")
def index(request: Request):
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    rows = []
    for name, svc in services.items():
        running = svc.is_running()
        status_label = "UP" if running else ("MISSING" if not svc.available else "DOWN")
        status_class = "status-" + status_label.lower()
        display_name = svc.display_name or name
        display_html = escape(display_name)
        title_attr = f" title='{escape(svc.description)}'" if svc.description else ""
        links = svc.resolved_links()
        open_link = ""
        if links:
            primary = links[0]
            url = primary.get("url")
            label = primary.get("label", "Open")
            if url:
                open_link = f"<a href='{url}' target='_blank'>{escape(label)}</a>"
        elif svc.available and svc.port:
            open_link = f"<a href='http://localhost:{svc.port}/' target='_blank'>Open</a>"

        control_buttons = []
        if svc.supports_start():
            control_buttons.append(f"<button class='btn-start' data-svc='{name}'>Start</button>")
        if svc.supports_stop():
            control_buttons.append(f"<button class='btn-stop' data-svc='{name}' style='margin-left:6px'>Stop</button>")
        controls = " ".join(control_buttons) if control_buttons else "&mdash;"

        rows.append(
            f"<tr id='row-{name}'>"
            f"<td><b{title_attr}>{display_html}</b></td>"
            f"<td><span id='status-{name}' data-available='{str(svc.available).lower()}' class='status-badge {status_class}'>{status_label}</span></td>"
            f"<td>{open_link}</td>"
            f"<td>{controls}</td>"
            f"</tr>"
        )

    content = f"""
        <h2>Connect</h2>
        <p>Service connection status, quick links and controls.</p>
        <table>
            <thead><tr><th>Service</th><th>Status</th><th>Link</th><th>Controls</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
        <div id='toast'></div>
        <script>
            const toastEl = document.getElementById('toast');
            function showToast(msg) {{
                toastEl.textContent = msg;
                toastEl.style.opacity = '1';
                clearTimeout(window.__ikarToastTimer);
                window.__ikarToastTimer = setTimeout(() => {{ toastEl.style.opacity = '0'; }}, 2500);
            }}

            function applyStatus(name, running) {{
                const el = document.getElementById('status-' + name);
                if (!el) return;
                const available = el.dataset.available !== 'false';
                let label = available ? 'DOWN' : 'MISSING';
                let cls = available ? 'status-down' : 'status-missing';
                if (available && running) {{
                    label = 'UP';
                    cls = 'status-up';
                }}
                el.textContent = label;
                el.className = 'status-badge ' + cls;
            }}

            async function fetchStatus() {{
                try {{
                    const res = await fetch('/ikaros/status', {{ headers: {{ 'Accept': 'application/json' }} }});
                    if (!res.ok) return;
                    const data = await res.json();
                    Object.entries(data).forEach(([name, running]) => applyStatus(name, running));
                }} catch (_) {{}}
            }}

            async function callAction(name, action) {{
                try {{
                    const res = await fetch(`/ikaros/${{action}}/${{name}}`, {{ method: 'POST', headers: {{ 'Accept': 'application/json' }} }});
                    if (res.ok) {{
                        const data = await res.json();
                        if (data && typeof data.running === 'boolean') applyStatus(name, data.running);
                        if (data && data.message) showToast(`${{name}}: ${{data.message}}`);
                    }} else {{
                        showToast(`${{name}}: request failed (${{res.status}})`);
                    }}
                }} catch (err) {{
                    showToast(`${{name}}: error ${{err}}`);
                }} finally {{
                    fetchStatus();
                }}
            }}

            document.querySelectorAll('.btn-start').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    const name = e.currentTarget.dataset.svc;
                    callAction(name, 'start');
                }});
            }});

            document.querySelectorAll('.btn-stop').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    const name = e.currentTarget.dataset.svc;
                    callAction(name, 'stop');
                }});
            }});

            // Initial/periodic refresh
            fetchStatus();
            setInterval(fetchStatus, 30000);
        </script>
    """
    return _render_page("Connect", content, str(request.url.path), services)


@router.get("/terminal")
def terminal(request: Request):
    content = """
        <h2>Web Terminal</h2>
        <div id="terminal-container"></div>
        <div id="terminal-status" style="margin-top:8px;font-size:0.9em;color:#8b949e;"></div>
        <script>
            const term = new Terminal({
                cursorBlink: true,
                theme: {
                    background: '#0d1117',
                    foreground: '#c9d1d9',
                }
            });
            term.open(document.getElementById('terminal-container'));

            function fitTerminal() {
                try {
                    const dims = term._core?._renderService?.dimensions;
                    const parent = term.element?.parentElement;
                    if (!dims || !parent || !dims.actualCellWidth || !dims.actualCellHeight) return;
                    const width = parent.clientWidth - 4;
                    const height = parent.clientHeight - 4;
                    const cols = Math.max(2, Math.floor(width / dims.actualCellWidth));
                    const rows = Math.max(1, Math.floor(height / dims.actualCellHeight));
                    term.resize(cols, rows);
                } catch (err) {
                    console.debug('fit error', err);
                }
            }

            const statusEl = document.getElementById('terminal-status');
            const setStatus = (text, color = '#8b949e') => {
                statusEl.textContent = text;
                statusEl.style.color = color;
            };
            setStatus('Connecting...');
            fitTerminal();

            const wsProtocol = location.protocol === 'https:' ? 'wss' : 'ws';
            const wsUrl = `${wsProtocol}://${location.host}/ikaros/ws/pty`;
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                term.focus();
                setStatus('Connected');
                fitTerminal();
            };

            ws.onmessage = (event) => {
                term.write(event.data);
                fitTerminal();
            };

            ws.onclose = () => {
                term.write('\\r\\n\\nConnection closed.\\r\\n');
                setStatus('Connection closed', '#da3633');
            };

            ws.onerror = () => {
                setStatus('WebSocket error (check backend logs)', '#da3633');
            };

            term.onData((data) => {
                ws.send(data);
            });

            window.addEventListener('resize', () => {
                fitTerminal();
            });

            term.onResize(({ cols, rows }) => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'resize', cols, rows }));
                }
            });
        </script>
    """
    return _render_page("Terminal", content, str(request.url.path))


@router.get("/logs")
def logs(request: Request):
    services = sm.load_services_from_config(sm.CONFIG_PATH)
    service_options = "".join(f"<option value='{name}'>{name}</option>" for name in services.keys())

    content = f"""
        <h2>Logs</h2>
        <div class="log-controls">
            <select id="log-source">
                <option value="events">Events</option>
                {service_options}
            </select>
            <input type="text" id="log-filter" placeholder="Filter logs...">
            <button id="log-pause-btn">Pause</button>
        </div>
        <pre id="log-output" style="white-space: pre-wrap; word-break: break-all; background: #010409; padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);"></pre>
        
        <script>
            const logSource = document.getElementById('log-source');
            const logFilter = document.getElementById('log-filter');
            const logOutput = document.getElementById('log-output');
            const pauseBtn = document.getElementById('log-pause-btn');

            let polling = true;
            let intervalId;

            async function fetchLogs() {{
                if (!polling) return;

                const source = logSource.value;
                const url = source === 'events' ? '/ikaros/events?n=500' : `/ikaros/logs/${{source}}?n=500`;

                try {{
                    const res = await fetch(url);
                    const text = await res.text();
                    const filterValue = logFilter.value.toLowerCase();

                    if (filterValue) {{
                        const filteredLines = text.split('\\n').filter(line => line.toLowerCase().includes(filterValue));
                        logOutput.textContent = filteredLines.join('\\n');
                    }} else {{
                        logOutput.textContent = text;
                    }}
                }} catch (e) {{
                    logOutput.textContent = `Error loading logs: ${{e}}`;
                }}
            }}

            function startPolling() {{
                fetchLogs();
                intervalId = setInterval(fetchLogs, 4000);
            }}

            logSource.addEventListener('change', fetchLogs);
            logFilter.addEventListener('input', fetchLogs);
            pauseBtn.addEventListener('click', () => {{
                polling = !polling;
                pauseBtn.textContent = polling ? 'Pause' : 'Resume';
            }});

            startPolling();
        </script>
    """
    return _render_page("Logs", content, str(request.url.path))


## Router include moved to end of file after all route definitions


@router.get("/env")
def env_page(request: Request):
    content = """
        <h2>Environment</h2>
        <div style='margin:8px 0;'>
            <label>Prefixes filter:</label>
            <div class='chip-container' id='prefix-chips'></div>
            <div style='display:flex; gap:8px; align-items:center; margin-top:4px;'>
                <input type='text' id='prefix-input' placeholder='Add prefix (e.g. DATA_)' style='flex:1; min-width:220px;'>
                <button id='add-prefix'>Add</button>
                <button id='reload'>Reload</button>
            </div>
            <p style='margin-top:6px;font-size:0.85em;color:#8b949e;'>
              Leave list empty to show all variables. Prefix can also be a full key (e.g. COMFYUI_PORT).
            </p>
        </div>
        <table id='env-table'>
          <thead><tr><th>Key</th><th>Value</th></tr></thead>
          <tbody></tbody>
        </table>
        <script>
            const storageKey = 'ikar-env-prefixes';
            const defaultPrefixes = ["DATA_", "COMFYUI_", "IKAR_", "FILEBROWSER_", "CODE_SERVER_", "COMFYUI_PORT"];
            const chipsEl = document.getElementById('prefix-chips');
            const inputEl = document.getElementById('prefix-input');
            const addBtn = document.getElementById('add-prefix');
            const reloadBtn = document.getElementById('reload');
            const tableBody = document.querySelector('#env-table tbody');
            let prefixes = [];

            function loadPrefixes() {
                try {
                    const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
                    if (Array.isArray(stored) && stored.length > 0) {
                        prefixes = stored;
                    } else {
                        prefixes = [...defaultPrefixes];
                    }
                } catch (e) {
                    prefixes = [...defaultPrefixes];
                }
            }

            function savePrefixes() {
                localStorage.setItem(storageKey, JSON.stringify(prefixes));
            }

            function renderChips() {
                chipsEl.innerHTML = '';
                if (prefixes.length === 0) {
                    const span = document.createElement('span');
                    span.textContent = '(showing all variables)';
                    span.style.fontSize = '0.9em';
                    span.style.color = '#8b949e';
                    chipsEl.appendChild(span);
                    return;
                }
                prefixes.forEach((prefix, idx) => {
                    const chip = document.createElement('span');
                    chip.className = 'chip';
                    chip.innerHTML = `<span>${prefix}</span>`;
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.setAttribute('aria-label', `Remove ${prefix}`);
                    btn.textContent = '×';
                    btn.addEventListener('click', () => {
                        prefixes.splice(idx, 1);
                        savePrefixes();
                        renderChips();
                        load();
                    });
                    chip.appendChild(btn);
                    chipsEl.appendChild(chip);
                });
            }

            function addPrefix(raw) {
                const value = (raw || '').trim();
                if (!value) return;
                if (prefixes.includes(value)) return;
                prefixes.push(value);
                savePrefixes();
                renderChips();
                inputEl.value = '';
                load();
            }

            function mask(key, value) {
                const k = key.toLowerCase();
                if (k.includes('secret') || k.endsWith('key') || k.includes('token') || k.includes('password')) {
                    return '••••••';
                }
                return value;
            }

            async function load() {
                const u = new URL('/ikaros/env.json', location.origin);
                if (prefixes.length > 0) {
                    u.searchParams.set('prefix', prefixes.join(','));
                }
                const res = await fetch(u);
                const data = await res.json();
                tableBody.innerHTML = '';
                Object.entries(data).sort((a,b)=>a[0].localeCompare(b[0])).forEach(([k,v])=>{
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td style='white-space:nowrap;'>${k}</td><td style='word-break:break-all;'>${mask(k, v)}</td>`;
                    tableBody.appendChild(tr);
                });
            }

            reloadBtn.addEventListener('click', load);
            addBtn.addEventListener('click', () => addPrefix(inputEl.value));
            inputEl.addEventListener('keydown', (ev) => {
                if (ev.key === 'Enter' || ev.key === ',') {
                    ev.preventDefault();
                    addPrefix(inputEl.value);
                }
            });

            loadPrefixes();
            renderChips();
            load();
        </script>
    """
    return _render_page("Env", content, str(request.url.path))


@router.get("/env.json")
def env_json(prefix: str = ""):
    prefixes = [p.strip() for p in prefix.split(',') if p.strip()]
    prefixes_lower = [p.lower() for p in prefixes]
    def want(k: str) -> bool:
        if not prefixes:
            return True
        kl = k.lower()
        return any(kl.startswith(p) for p in prefixes_lower)
    out = {k: v for k, v in os.environ.items() if want(k)}
    return JSONResponse(out)

# ---------------- Comfy Config Panel ---------------- #

def _paths_default_models() -> dict:
    data_dir = os.environ.get("DATA_DIR", "/workspace/data")
    m = os.path.join(data_dir, "models")
    return {
        "checkpoints": [f"{m}/checkpoints"],
        "vae": [f"{m}/vae"],
        "lora": [f"{m}/loras"],
        "clip": [f"{m}/clip"],
        "clip_vision": [f"{m}/clip_vision"],
        "controlnet": [f"{m}/controlnet"],
        "upscale_models": [f"{m}/upscale"],
        "embeddings": [f"{m}/embeddings"],
        "unet": [f"{m}/unet"],
        "vae_approx": [f"{m}/vae_approx"],
        "configs": [f"{m}/configs"],
    }


def _ensure_comfy_config() -> tuple[str, dict]:
    data_dir = os.environ.get("DATA_DIR", "/workspace/data")
    config_path = os.environ.get("COMFYUI_CONFIG_FILE", f"{data_dir}/extra_model_paths.yaml")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(_paths_default_models(), fh, sort_keys=False)
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        data = {}
    # Ensure symlink into ComfyUI directory (best effort)
    comfy_link = "/workspace/ComfyUI/extra_model_paths.yaml"
    try:
        if os.path.isdir("/workspace/ComfyUI"):
            if os.path.islink(comfy_link) or os.path.exists(comfy_link):
                try:
                    os.remove(comfy_link)
                except OSError:
                    pass
            os.symlink(config_path, comfy_link)
    except OSError:
        pass
    return config_path, data


@router.get("/comfy")
def comfy_page(request: Request):
    content = """
        <h2>Comfy Config</h2>
        <div id='meta' style='font-size:0.9em;color:#8b949e;'></div>
        <div style='margin:8px 0; display:flex; gap:8px;'>
            <button id='btn-validate'>Validate</button>
            <button id='btn-install'>Install/Repair Symlink</button>
        </div>
        <div style='display:grid; grid-template-columns: 1fr; gap:10px;'>
            <div>
              <h3 style='margin:8px 0;'>Current YAML</h3>
              <pre id='cfg' style='white-space:pre-wrap; word-break:break-all; background:#010409; padding:10px; border:1px solid var(--border-color); border-radius:6px;'></pre>
            </div>
            <div>
              <h3 style='margin:8px 0;'>Validation</h3>
              <pre id='val' style='white-space:pre-wrap; word-break:break-all; background:#010409; padding:10px; border:1px solid var(--border-color); border-radius:6px;'>(not validated)</pre>
            </div>
        </div>
        <script>
            async function loadMeta() {
                const res = await fetch('/ikaros/comfy/config/raw');
                const text = await res.text();
                document.getElementById('cfg').textContent = text || '(empty)';
                const meta = `Config: ${res.headers.get('x-config-path') || ''}`;
                document.getElementById('meta').textContent = meta;
            }
            async function validate() {
                const r = await fetch('/ikaros/comfy/config/validate');
                const j = await r.json();
                const lines = [];
                lines.push('config: ' + j.config_path);
                lines.push('present: ' + j.present.length);
                lines.push(...j.present.map(p => '  \u2713 ' + p));
                lines.push('missing: ' + j.missing.length);
                lines.push(...j.missing.map(p => '  \u2717 ' + p));
                document.getElementById('val').textContent = lines.join('\n');
            }
            async function install() {
                const r = await fetch('/ikaros/comfy/config/install', {method:'POST'});
                const j = await r.json();
                await loadMeta();
                await validate();
                alert(j.ok ? 'Installed' : ('Failed: ' + (j.error||'')));
            }
            document.getElementById('btn-validate').addEventListener('click', validate);
            document.getElementById('btn-install').addEventListener('click', install);
            loadMeta();
        </script>
    """
    return _render_page("Comfy", content, str(request.url.path))


@router.get("/comfy/config/raw")
def comfy_config_raw():
    path, data = _ensure_comfy_config()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except Exception:
        text = yaml.safe_dump(data or {}, sort_keys=False)
    r = PlainTextResponse(text)
    r.headers["x-config-path"] = path
    return r


@router.get("/comfy/config/validate")
def comfy_config_validate():
    path, data = _ensure_comfy_config()
    paths = []
    try:
        for key, arr in (data or {}).items():
            if isinstance(arr, list):
                for p in arr:
                    if isinstance(p, str):
                        paths.append(os.path.expandvars(p))
    except Exception:
        pass
    present = [p for p in paths if os.path.isdir(p)]
    missing = [p for p in paths if p not in present]
    return JSONResponse({"ok": True, "config_path": path, "present": present, "missing": missing})


@router.post("/comfy/config/install")
def comfy_config_install():
    try:
        path, _ = _ensure_comfy_config()
        return JSONResponse({"ok": True, "config_path": path})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# Finally register router and explicit WS route
app.include_router(router)
app.add_api_websocket_route("/ikaros/ws/pty", websocket_pty)
