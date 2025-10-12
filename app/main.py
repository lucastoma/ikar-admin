from fastapi import FastAPI, APIRouter, Response, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
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


app = FastAPI(title="ikar-admin", docs_url=None, redoc_url=None)
router = APIRouter(prefix="/ikaros")


@router.websocket("/ws/pty")
async def websocket_pty(ws: WebSocket):
    await ws.accept()

    # Check origin for basic security
    origin = ws.headers.get("origin", "").split("://")[-1]
    host = ws.headers.get("host", "")
    if origin != host:
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
            # This part is tricky to get feedback from, but we try
            os._exit(127)

    # Set master PTY to non-blocking
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    try:
        while True:
            # Wait for data from WebSocket or PTY
            readable, _, _ = await asyncio.to_thread(
                lambda: select.select([ws._stream_reader._transport.get_extra_info("socket"), fd], [], [], 0.1)
            )

            if ws._stream_reader._transport.get_extra_info("socket") in readable:
                try:
                    data = await ws.receive_text()
                    try:
                        msg = json.loads(data)
                        if msg.get("type") == "resize":
                            import termios
                            import struct
                            winsize = struct.pack("HHHH", msg["rows"], msg["cols"], 0, 0)
                            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
                    except json.JSONDecodeError:
                        os.write(fd, data.encode())
                except WebSocketDisconnect:
                    break

            if fd in readable:
                try:
                    output = os.read(fd, 1024)
                    if output:
                        await ws.send_text(output.decode("utf-8", "ignore"))
                except OSError:
                    break # PTY closed

    except Exception as e:
        sm._append_event("terminal", "error", str(e), False)
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.close(fd)
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
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css">
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
        <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.9.0/lib/xterm-addon-fit.min.js"></script>
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
        open_link = ""
        if svc.available and svc.port:
            open_link = f"<a href='http://localhost:{svc.port}/' target='_blank'>Open</a>"

        rows.append(
            f"<tr><td><b>{name}</b></td>"
            f"<td><span class='status-badge {status_class}'>{status_label}</span></td>"
            f"<td>{open_link}</td></tr>"
        )

    content = f"""
        <h2>Connect</h2>
        <p>Service connection status and quick links.</p>
        <table>
            <thead><tr><th>Service</th><th>Status</th><th>Link</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    """
    return _render_page("Connect", content, str(request.url.path), services)


@router.get("/terminal")
def terminal(request: Request):
    content = """
        <h2>Web Terminal</h2>
        <div id="terminal-container"></div>
        <script>
            const term = new Terminal({
                cursorBlink: true,
                theme: {
                    background: '#0d1117',
                    foreground: '#c9d1d9',
                }
            });
            const fitAddon = new FitAddon.FitAddon();
            term.loadAddon(fitAddon);
            term.open(document.getElementById('terminal-container'));
            fitAddon.fit();

            const wsProtocol = location.protocol === 'https:' ? 'wss' : 'ws';
            const wsUrl = `${wsProtocol}://${location.host}/ikaros/ws/pty`;
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                term.focus();
            };

            ws.onmessage = (event) => {
                term.write(event.data);
            };

            ws.onclose = () => {
                term.write('\\r\\n\\nConnection closed.\\r\\n');
            };

            term.onData((data) => {
                ws.send(data);
            });

            window.addEventListener('resize', () => {
                fitAddon.fit();
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


app.include_router(router)
