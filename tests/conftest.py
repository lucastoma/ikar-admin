import sys
from pathlib import Path
import types
import pytest


# Ensure the package root (with "app/") is importable
PKG_ROOT = Path(__file__).resolve().parents[1]
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))


class _FakeService:
    def __init__(self, name, running=False, available=True):
        self.name = name
        self._running = running
        self.log_path = None
        self.available = available

    def is_running(self):
        return self._running if self.available else False

    def start(self):
        if not self.available:
            return False, "Service not installed"
        self._running = True
        return True, "started"

    def stop(self):
        if not self.available:
            return False, "No processes matched"
        self._running = False
        return True, "stopped"


@pytest.fixture(autouse=True)
def patch_services(monkeypatch):
    # Late import after sys.path is primed
    from app import main as app_main

    services = {
        "comfyui": _FakeService("comfyui", running=False),
        "code": _FakeService("code", running=True),
        "filebrowser": _FakeService("filebrowser", running=False),
        "tailscale": _FakeService("tailscale", running=True),
    }

    monkeypatch.setattr(app_main, "build_services", lambda: services)
    monkeypatch.setattr(app_main, "tail_file", lambda path, n=200: "demo log lines")

    yield
