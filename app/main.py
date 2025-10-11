from fastapi import FastAPI, APIRouter, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from .service_manager import build_services, tail_file
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
            f"<a href='/ikaros/logs/{name}' target='_blank' style='margin-left:10px'>Logs</a>"
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
        </style>
    </head>
    <body>
        <h2>ikar-admin</h2>
        <p>Quick status and controls for local services.</p>
        <table>
            <tr><th>Service</th><th>Status</th><th>Controls</th></tr>
            {''.join(rows)}
        </table>
        <p style='margin-top:16px'><a href='/ikaros/health' target='_blank'>Health (JSON)</a></p>
        <div id='toast'></div>
        <script>
            const toastEl = document.getElementById('toast');
            function showToast(msg) {{
                toastEl.textContent = msg;
                toastEl.style.opacity = '1';
                clearTimeout(window.__ikarToastTimer);
                window.__ikarToastTimer = setTimeout(() => {{ toastEl.style.opacity = '0'; }}, 2500);
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
                        }}
                        cell.textContent = label;
                        cell.dataset.status = label;
                        cell.className = cls;
                    }});
                }} catch (err) {{ console.error(err); }}
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
                            const res = await fetch(url.toString(), {{ method: 'POST', headers: {{ 'Accept': 'application/json' }} }});
                            if (res.ok) {{
                                const data = await res.json();
                                if (data.message) showToast(`${{svc}}: ${{data.message}}`);
                            }} else {{
                                showToast(`${{svc}}: request failed (${{res.status}})`);
                            }}
                        }} catch (err) {{
                            showToast(`${{svc}}: error ${{err}}`);
                        }} finally {{
                            formBtn.disabled = false;
                            await fetchStatus();
                        }}
                }});
            }});
            fetchStatus();
            setInterval(fetchStatus, 8000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


app.include_router(router)
