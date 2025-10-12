from fastapi.testclient import TestClient
from app.main import app


def test_index_html(client, monkeypatch):
    from app import service_manager
    monkeypatch.setattr(service_manager, "_cmdline_matches", lambda p: p == "running_svc_pattern")

    r = client.get("/ikaros")
    assert r.status_code == 200
    html = r.text
    # All services from test_config.yaml are rendered
    assert "running_svc" in html
    assert "stopped_svc" in html
    assert "missing_svc" in html
    # Check statuses
    assert "status-up" in html.lower()
    assert "status-down" in html.lower()
    assert "status-missing" in html.lower()
    # No start/stop buttons
    assert "Start</button>" not in html
    assert "Stop</button>" not in html


def test_terminal_page(client):
    r = client.get("/ikaros/terminal")
    assert r.status_code == 200
    assert "xterm.min.js" in r.text
    assert "terminal-container" in r.text


def test_logs_page(client):
    r = client.get("/ikaros/logs")
    assert r.status_code == 200
    assert "log-source" in r.text
    assert "log-output" in r.text


def test_status_json(client, monkeypatch):
    from app import service_manager
    monkeypatch.setattr(service_manager, "_cmdline_matches", lambda p: p == "running_svc_pattern")

    r = client.get("/ikaros/status")
    assert r.status_code == 200
    data = r.json()
    assert data == {
        "running_svc": True,
        "stopped_svc": False,
        "missing_svc": False,
    }


def test_start_service_ok(client, monkeypatch):
    from app import service_manager
    monkeypatch.setattr(service_manager, "_run", lambda cmd: type("obj", (object,), {"returncode": 0, "stdout": "ok"})())
    # Make it appear stopped initially
    monkeypatch.setattr(service_manager, "_cmdline_matches", lambda p: False)

    r = client.post("/ikaros/start/stopped_svc")
    assert r.status_code == 200
    # The _wait_for will eventually time out, but the initial command was ok
    assert r.json()["ok"] is True


def test_start_missing_service_api(client):
    r = client.post("/ikaros/start/missing_svc")
    data = r.json()
    assert r.status_code == 200 # The endpoint itself doesn't 404
    assert data["ok"] is False
    assert data["message"] == "Service not installed"


def test_unknown_service_errors(client):
    r = client.post("/ikaros/start/unknown_svc")
    assert r.status_code == 404