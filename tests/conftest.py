import sys
from pathlib import Path
import pytest

# Ensure the package root (with "app/") is importable
PKG_ROOT = Path(__file__).resolve().parents[1]
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

@pytest.fixture(autouse=True)
def mock_low_level_deps(monkeypatch):
    """Mock low-level dependencies that interact with the OS."""
    from app import service_manager

    # Mock all OS-interacting functions to return False by default
    monkeypatch.setattr(service_manager, "_cmdline_matches", lambda pattern: False)
    monkeypatch.setattr(service_manager, "_is_port_open", lambda port: False)
    monkeypatch.setattr(service_manager.shutil, "which", lambda cmd: f"/bin/{cmd}")
    monkeypatch.setattr(service_manager.os.path, "exists", lambda path: True)

    # Mock the config path to point to a test-specific config
    test_config_path = PKG_ROOT / "tests" / "test_config.yaml"
    monkeypatch.setattr(service_manager, "CONFIG_PATH", test_config_path)