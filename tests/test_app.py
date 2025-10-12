from fastapi.testclient import TestClient
from app.main import app


def _client():
    return TestClient(app)


def test_index_html(monkeypatch):
    from app import service_manager
    monkeypatch.setattr(service_manager, "_cmdline_matches", lambda p: p == "running_svc_pattern")

    c = _client()
    r = c.get("/ikaros")
    assert r.status_code == 200
    html = r.text
    # All services from test_config.yaml are rendered
    assert "running_svc" in html
    assert "stopped_svc" in html
    assert "missing_svc" in html
    # Check statuses
    assert "<td id='status-running_svc' data-status='UP'" in html
    assert "<td id='status-stopped_svc' data-status='DOWN'" in html
    assert "<td id='status-missing_svc' data-status='MISSING'" in html
    # Check disabled attribute for missing service
    assert "<tr id='row-missing_svc'>" in html
    assert "<button type='submit' disabled>Start</button>" in html


def test_status_json(monkeypatch):
    from app import service_manager
    monkeypatch.setattr(service_manager, "_cmdline_matches", lambda p: p == "running_svc_pattern")

    c = _client()
    r = c.get("/ikaros/status")
    assert r.status_code == 200
    data = r.json()
    assert data == {
        "running_svc": True,
        "stopped_svc": False,
        "missing_svc": False,
    }


def test_start_service_ok(monkeypatch):
    from app import service_manager
    monkeypatch.setattr(service_manager, "_run", lambda cmd: type("obj", (object,), {"returncode": 0, "stdout": "ok"})())
    # Make it appear stopped initially
    monkeypatch.setattr(service_manager, "_cmdline_matches", lambda p: False)

    c = _client()
    r = c.post("/ikaros/start/stopped_svc")
    assert r.status_code == 200
    # The _wait_for will eventually time out, but the initial command was ok
    assert r.json()["ok"] is True


def test_start_missing_service_api():
    c = _client()
    r = c.post("/ikaros/start/missing_svc")
    data = r.json()
    assert r.status_code == 200 # The endpoint itself doesn't 404
    assert data["ok"] is False
    assert data["message"] == "Service not installed"


def test_unknown_service_errors():
    c = _client()
    r = c.post("/ikaros/start/unknown_svc")
    assert r.status_code == 404