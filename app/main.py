from fastapi import FastAPI, APIRouter, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from .service_manager import build_services, tail_file, EVENT_LOG_PATH
import os
import shutil
import json
import time
import socket
import shutil as _shutil


app = FastAPI(title="ikar-admin", docs_url=None, redoc_url=None)
router = APIRouter(prefix="/ikaros")


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
    services = build_services()
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
    services = build_services()
    return JSONResponse({k: v.is_running() for k, v in services.items()})


@router.get("/logs/{svc}")
def logs(svc: str, n: int = 200):
    services = build_services()
    s = services.get(svc)
    if not s:
        return PlainTextResponse("unknown service", status_code=404)
    out = tail_file(s.log_path, n)
    return PlainTextResponse(out)


@router.get("/events")
def events(n: int = 200):
    return PlainTextResponse(tail_file(EVENT_LOG_PATH, n))


@router.post("/start/{svc}")
def start(request: Request, svc: str, redirect: int = 0):
    services = build_services()
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
    services = build_services()
    s = services.get(svc)
    if not s:
        return JSONResponse({"ok": False, "error": "unknown service"}, status_code=404)
    success, msg = s.stop()
    want_redirect = redirect or ("text/html" in request.headers.get("accept", ""))
    if want_redirect:
        return RedirectResponse(url="/ikaros", status_code=303)
    return JSONResponse({"ok": success, "message": msg, "running": s.is_running()})


@router.get("/")
def index():
    services = build_services()
    rows = []
    for name, svc in services.items():
        running = svc.is_running()
        status_label = "UP" if running else ("MISSING" if not svc.available else "DOWN")
        status_color = "green" if running else ("#666" if not svc.available else "red")
        disabled_attr = " disabled" if not svc.available else ""
        open_link = ""
        if svc.available:
            if name == "comfyui":
                port = int(os.environ.get("COMFYUI_PORT", "18188"))
                open_link = f"<a href='http://localhost:{port}/' target='_blank'>Open</a>"
            elif name == "code":
                port = int(os.environ.get("CODE_SERVER_PORT", "8445"))
                open_link = f"<a href='http://localhost:{port}/' target='_blank'>Open</a>"
            elif name == "filebrowser":
                port = int(os.environ.get("FILEBROWSER_PORT", "8085"))
                open_link = f"<a href='http://localhost:{port}/' target='_blank'>Open</a>"
        rows.append(
            f"<tr id='row-{name}'><td><b>{name}</b></td>"
            f"<td id='status-{name}' data-status='{status_label}' data-available='{str(svc.available).lower()}' class='status-"
            f"{'up' if running else ('missing' if not svc.available else 'down')}'>{status_label}</td>"
            f"<td>"
            f"<form method='post' data-service='{name}' data-action='start' action='/ikaros/start/{name}?redirect=1' style='display:inline'>"
            f"<button type='submit'{disabled_attr}>Start</button></form>"
            f"<form method='post' data-service='{name}' data-action='stop' action='/ikaros/stop/{name}?redirect=1' style='display:inline;margin-left:6px'>"
            f"<button type='submit'{disabled_attr}>Stop</button></form>"
            f"<span style='margin-left:10px'>{open_link}</span>"
            f"</td>"
            f"</tr>"
        )

    html = f"""
    <html>
    <head>
        <meta charset='utf-8'/>
        <title>ikar-admin</title>
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 680px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background: #f5f5f5; text-align: left; }}
            button {{ padding: 4px 10px; }}
            .status-up {{ color: green; }}
            .status-down {{ color: red; }}
            .status-missing {{ color: #666; }}
            #toast {{ position: fixed; bottom: 20px; right: 20px; background: #333; color: #fff; padding: 8px 12px; border-radius: 4px; opacity: 0; transition: opacity 0.3s; }}
            #log-container {{ margin-top: 20px; border: 1px solid #ddd; background: #f9f9f9; padding: 10px; }}
            #log-header {{ display: flex; align-items: center; gap: 8px; font-size: 0.9em; color: #333; }}
            #log-output {{ max-height: 260px; overflow-y: auto; white-space: pre-wrap; background: #fff; border: 1px solid #ccc; padding: 8px; }}
        </style>
    </head>
    <body>
        <h2>ikar-admin</h2>
        <p>Quick status and controls for local services.</p>
        <div id='meta' style='margin:6px 0; font-size: 0.9em; color:#555;'>
          Last update: <span id='last-upd'>now</span>
          <span id='pending' style='margin-left:12px; display:none;'>Pending: <span id='pending-list'></span></span>
        </div>
        <table>
            <tr><th>Service</th><th>Status</th><th>Controls</th></tr>
            {''.join(rows)}
        </table>
        <p style='margin-top:16px'><a href='/ikaros/health' target='_blank'>Health (JSON)</a></p>
        <div id='toast'></div>
        <div id='log-container'>
          <div id='log-header'>
            <span>Logs:</span> <strong id='log-title'>events log</strong>
            <button type='button' id='log-clear'>Clear</button>
          </div>
          <pre id='log-output'>(loading…)</pre>
        </div>
        
        <script>
            const toastEl = document.getElementById('toast');
            const lastUpdEl = document.getElementById('last-upd');
            const pendingEl = document.getElementById('pending');
            const pendingListEl = document.getElementById('pending-list');
            const logTitle = document.getElementById('log-title');
            const logOutput = document.getElementById('log-output');
            const logClearBtn = document.getElementById('log-clear');

            let lastUpdAt = Date.now();
            const pendingSvcs = new Map();

            function showToast(msg) {{
                toastEl.textContent = msg;
                toastEl.style.opacity = '1';
                clearTimeout(window.__ikarToastTimer);
                window.__ikarToastTimer = setTimeout(() => {{ toastEl.style.opacity = '0'; }}, 2500);
            }}

            function refreshMeta() {{
                const sec = Math.floor((Date.now() - lastUpdAt) / 1000);
                lastUpdEl.textContent = sec === 0 ? 'now' : `${{sec}}s ago`;
                const names = Array.from(pendingSvcs.keys());
                if (names.length > 0) {{
                    pendingEl.style.display = '';
                    pendingListEl.textContent = names.join(', ');
                }} else {{
                    pendingEl.style.display = 'none';
                }}
            }}

            async function loadEvents() {{
                try {{
                    const res = await fetch('/ikaros/events?n=200');
                    if (!res.ok) throw new Error(res.status);
                    const text = await res.text();
                    logTitle.textContent = 'events log';
                    logOutput.textContent = text || '(no events yet)';
                }} catch (err) {{
                    logOutput.textContent = `Failed to load events: ${{err}}`;
                }}
            }}

            async function fetchStatus() {{
                try {{
                    const res = await fetch('/ikaros/status', {{ headers: {{ 'Accept': 'application/json' }} }});
                    if (!res.ok) return;
                    const data = await res.json();
                    Object.entries(data).forEach(([svc, running]) => {{
                        const cell = document.getElementById('status-' + svc);
                        if (!cell) return;
                        const available = cell.dataset.available !== 'false';
                        let label = available ? 'DOWN' : 'MISSING';
                        let cls = available ? 'status-down' : 'status-missing';
                        if (available && running) {{
                            label = 'UP';
                            cls = 'status-up';
                            if (pendingSvcs.has(svc)) {{
                                clearInterval(pendingSvcs.get(svc));
                                pendingSvcs.delete(svc);
                            }}
                        }}
                        cell.textContent = label;
                        cell.dataset.status = label;
                        cell.className = cls;
                    }});
                    lastUpdAt = Date.now();
                    refreshMeta();
                }} catch (err) {{
                    console.error(err);
                }}
            }}

            function schedulePendingCheck(svc, seconds = 10) {{
                if (pendingSvcs.has(svc)) {{
                    clearInterval(pendingSvcs.get(svc));
                }}
                let remaining = seconds;
                const handle = setInterval(async () => {{
                    await fetchStatus();
                    remaining -= 1;
                    if (!pendingSvcs.has(svc) || remaining <= 0) {{
                        clearInterval(handle);
                        pendingSvcs.delete(svc);
                        refreshMeta();
                    }}
                }}, 1000);
                pendingSvcs.set(svc, handle);
                refreshMeta();
            }}

            document.querySelectorAll('form[data-service]').forEach(form => {{
                form.addEventListener('submit', async ev => {{
                    if (ev.defaultPrevented) return;
                    ev.preventDefault();
                    const svc = form.dataset.service;
                    const formBtn = form.querySelector('button');
                    formBtn.disabled = true;
                    const url = new URL(form.action, window.location.origin);
                    url.searchParams.set('redirect', '0');
                    try {{
                        const res = await fetch(url.toString(), {{
                            method: 'POST',
                            headers: {{ 'Accept': 'application/json' }}
                        }});
                        if (res.ok) {{
                            const data = await res.json();
                            if (data.message) showToast(`${{svc}}: ${{data.message}}`);
                            schedulePendingCheck(svc, 10);
                        }} else {{
                            showToast(`${{svc}}: request failed (${{res.status}})`);
                        }}
                    }} catch (err) {{
                        showToast(`${{svc}}: error ${{err}}`);
                    }} finally {{
                        formBtn.disabled = false;
                        await fetchStatus();
                        await loadEvents();
                    }}
                }});
            }});

            logClearBtn.addEventListener('click', () => {{
                logOutput.textContent = '(cleared by user)';
            }});

            loadEvents();
            fetchStatus();
            setInterval(fetchStatus, 30000);
            setInterval(loadEvents, 30000);
            setInterval(refreshMeta, 1000);
        </script>

    </body>
    </html>
    """
    return HTMLResponse(html)


app.include_router(router)
