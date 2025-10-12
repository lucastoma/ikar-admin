import pytest
from app.service_manager import Service, _run
import os
import signal

def test_start_with_workdir_and_env(mocker):
    mocker.patch("app.service_manager._run", return_value=type("obj", (object,), {"returncode": 0, "stdout": "ok"})())
    mocker.patch("app.service_manager._wait_for", return_value=True)
    mock_subprocess_run = mocker.patch("subprocess.run")

    svc = Service(
        name="test_svc",
        start_cmd="my_command",
        workdir="/test/dir",
        env={"MY_VAR": "my_value"}
    )

    svc.start()

    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    assert kwargs["cwd"] == "/test/dir"
    assert "MY_VAR" in kwargs["env"]
    assert kwargs["env"]["MY_VAR"] == "my_value"

def test_stop_with_pid_file(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data="12345"))
    mock_kill = mocker.patch("os.kill")
    mock_wait_for = mocker.patch("app.service_manager._wait_for", return_value=True)

    svc = Service(name="test_svc", pid_file="/tmp/test.pid")

    success, msg = svc.stop()

    assert success is True
    assert "PID 12345" in msg
    mock_kill.assert_called_once_with(12345, signal.SIGTERM)
    mock_wait_for.assert_called_once()

def test_stop_with_pid_file_force_kill(mocker):
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data="12345"))
    mock_kill = mocker.patch("os.kill")
    # Simulate SIGTERM failing
    mocker.patch("app.service_manager._wait_for", side_effect=[False, True])

    svc = Service(name="test_svc", pid_file="/tmp/test.pid", stop_timeout=0.1)

    success, msg = svc.stop()

    assert success is True
    assert "Force-stopped" in msg
    assert mock_kill.call_count == 2
    mock_kill.assert_any_call(12345, signal.SIGTERM)
    mock_kill.assert_any_call(12345, signal.SIGKILL)

def test_stop_fallback_to_pkill(mocker):
    # pid file doesn't exist
    mocker.patch("os.path.exists", return_value=False)
    mock_pkill = mocker.patch("app.service_manager._pkill", return_value=True)
    mocker.patch("app.service_manager._wait_for", return_value=True)

    svc = Service(name="test_svc", pid_file="/tmp/test.pid", stop_patterns=["my_pattern"])

    svc.stop()

    mock_pkill.assert_called_once_with("my_pattern")

def test_is_running_with_pid_file(mocker):
    mocker.patch("app.service_manager.Service._is_pid_running", return_value=True)
    svc = Service(name="test_svc", pid_file="/tmp/test.pid")
    assert svc.is_running() is True

def test_health_check_tcp_success(mocker):
    mock_socket = mocker.patch("socket.socket")
    mock_socket.return_value.__enter__.return_value.connect.return_value = None

    svc = Service(name="test_svc", health={"tcp": {"port": 1234}})
    assert svc._run_health_check() is True

def test_health_check_tcp_failure(mocker):
    mock_socket = mocker.patch("socket.socket")
    mock_socket.return_value.__enter__.return_value.connect.side_effect = OSError

    svc = Service(name="test_svc", health={"tcp": {"port": 1234}})
    assert svc._run_health_check() is False

def test_health_check_http_success(mocker):
    mock_get = mocker.patch("httpx.get", return_value=type("obj", (object,), {"status_code": 200})())

    svc = Service(name="test_svc", health={"http": {"url": "http://test.com"}})
    assert svc._run_health_check() is True
    mock_get.assert_called_once_with("http://test.com", timeout=2)

def test_health_check_http_failure(mocker):
    mocker.patch("httpx.get", return_value=type("obj", (object,), {"status_code": 500})())

    svc = Service(name="test_svc", health={"http": {"url": "http://test.com", "expect": 201}})
    assert svc._run_health_check() is False