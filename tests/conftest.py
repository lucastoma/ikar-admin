import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app
from app import service_manager

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(service_manager, "CONFIG_PATH", Path(__file__).parent / "test_config.yaml")
    with TestClient(app) as c:
        yield c