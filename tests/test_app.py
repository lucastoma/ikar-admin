from fastapi.testclient import TestClient
from app.main import app


def _client():
    return TestClient(app)


def test_index_html():
    c = _client()
    r = c.get("/ikaros")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    html = r.text
    for name in ["comfyui", "code", "filebrowser", "tailscale"]:
        assert name in html
    # buttons/links visible
    assert "Start" in html and "Stop" in html and "Logs" in html
    # quick access links
    assert "http://localhost:18188/" in html
    assert "http://localhost:8445/" in html
    assert "http://localhost:8085/" in html


def test_status_json():
    c = _client()
    r = c.get("/ikaros/status")
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"comfyui", "code", "filebrowser", "tailscale"}
    assert isinstance(data["comfyui"], bool)


def test_start_json_and_redirect():
    c = _client()
    # JSON default
    r = c.post("/ikaros/start/comfyui")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["running"] is True

    # Redirect flow from HTML form
    r = c.post(
        "/ikaros/stop/code?redirect=1",
        headers={"accept": "text/html"},
        follow_redirects=False,
    )
    assert r.status_code in (303, 307, 302)
    assert r.headers.get("location", "").startswith("/ikaros")


def test_logs_plaintext():
    c = _client()
    r = c.get("/ikaros/logs/comfyui?n=10")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "demo log lines" in r.text


def test_health_shape():
    c = _client()
    r = c.get("/ikaros/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "disk" in data and "ports" in data and "services" in data


def test_unknown_service_errors():
    c = _client()
    r = c.post("/ikaros/start/unknown")
    assert r.status_code == 404
    assert r.json()["error"] == "unknown service"

    r = c.post("/ikaros/stop/unknown")
    assert r.status_code == 404
    assert r.json()["error"] == "unknown service"

    r = c.get("/ikaros/logs/unknown")
    assert r.status_code == 404
    assert "unknown service" in r.text


def test_missing_service_marks_disabled(monkeypatch):
    from app import main as app_main

    class Stub:
        def __init__(self, name, running, available):
            self.name = name
            self._running = running
            self.available = available
            self.log_path = None

        def is_running(self):
            return self.available and self._running

        def start(self):
            return (self.available, "started" if self.available else "Service not installed")

        def stop(self):
            return (self.available, "stopped" if self.available else "Service not installed")

    services = {
        "comfyui": Stub("comfyui", running=True, available=True),
        "filebrowser": Stub("filebrowser", running=False, available=False),
        "tailscale": Stub("tailscale", running=True, available=True),
    }

    monkeypatch.setattr(app_main, "build_services", lambda: services)

    c = _client()
    html = c.get("/ikaros").text
    assert "MISSING" in html
    assert "filebrowser" in html
    assert "button type='submit' disabled" in html


def test_missing_service_start_via_api(monkeypatch):
    from app import main as app_main

    class Stub:
        def __init__(self):
            self.available = False
            self.log_path = None

        def is_running(self):
            return False

        def start(self):
            return False, "Service not installed"

        def stop(self):
            return False, "Service not installed"

    services = {"comfyui": Stub()}
    monkeypatch.setattr(app_main, "build_services", lambda: services)

    c = _client()
    r = c.post("/ikaros/start/comfyui")
    data = r.json()
    assert data["ok"] is False
    assert data["message"] == "Service not installed"
