import os
import shutil
import socket
import subprocess
import re
import time
import yaml
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Optional, List


CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _run(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def _cmdline_matches(pattern: str) -> bool:
    if not pattern:
        return False
    regex = re.compile(pattern)
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/cmdline", "rb") as f:
                    raw = f.read()
            except OSError:
                continue
            if not raw:
                continue
            cmdline = raw.replace(b"\x00", b" ").decode("utf-8", "ignore")
            if regex.search(cmdline):
                return True
    except FileNotFoundError:
        # /proc not available on all systems
        pass
    return False


def _pkill(pattern: str) -> bool:
    res = _run(f"pkill -f '{pattern}'")
    return res.returncode == 0


def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _ensure_log_file(path: Optional[str]) -> None:
    if not path:
        return
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).touch(exist_ok=True)
    except OSError:
        pass


def _wait_for(predicate, expect: bool, timeout: float = 8.0, interval: float = 0.5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate() == expect:
            return True
        time.sleep(interval)
    return predicate() == expect


EVENT_LOG_PATH = os.environ.get("IKAR_EVENT_LOG", "/workspace/ikar-admin-events.log")
_ensure_log_file(EVENT_LOG_PATH)


def _append_event(service: str, action: str, message: str, success: bool) -> None:
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "OK" if success else "FAIL"
        with open(EVENT_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"[{ts}] [{service}] [{action}] [{status}] {message}\n")
    except OSError:
        pass


@dataclass
class Service:
    name: str
    detect: List[str] = field(default_factory=list)
    start_cmd: Optional[str] = None
    stop_patterns: Optional[List[str]] = None
    log_path: Optional[str] = None
    port: Optional[int] = None
    available: bool = True
    systemd_unit: Optional[str] = None

    def is_running(self) -> bool:
        if not self.available:
            return False
        # Prefer systemd when defined
        if self.systemd_unit and shutil.which("systemctl"):
            out = _run(f"sudo -n systemctl is-active {self.systemd_unit}")
            if out.returncode == 0 and out.stdout.strip() == "active":
                return True
        # Process pattern checks
        for p in self.detect:
            if _cmdline_matches(p):
                return True
        # Port fallback
        if self.port is not None:
            return _is_port_open(self.port)
        return False

    def start(self) -> (bool, str):
        if not self.available:
            msg = "Service not installed"
            _append_event(self.name, "start", msg, False)
            return False, msg
        if self.is_running():
            msg = "Already running"
            _append_event(self.name, "start", msg, True)
            return True, msg
        if self.systemd_unit and shutil.which("systemctl"):
            res = _run(f"sudo -n systemctl start {self.systemd_unit}")
            ok = _wait_for(self.is_running, True)
            msg = res.stdout.strip() or "systemd start"
            success = res.returncode == 0 and ok
            _append_event(self.name, "start", msg, success)
            return success, msg
        if not self.start_cmd:
            msg = "No start command configured"
            # Treat as no-op success (acknowledged request)
            _append_event(self.name, "start", msg, True)
            return True, msg
        _ensure_log_file(self.log_path)
        # Substitute environment variables in start_cmd
        expanded_cmd = os.path.expandvars(self.start_cmd)
        res = _run(expanded_cmd)
        success = res.returncode == 0
        output = res.stdout.strip()
        if success and not output:
            output = "Launch command executed"
        started = _wait_for(self.is_running, True)
        msg = output or "(no output)"
        # Consider command success sufficient to report OK; also accept if process detected later
        final = success or started
        _append_event(self.name, "start", msg, final)
        return final, msg

    def stop(self) -> (bool, str):
        if not self.available:
            msg = "Service not installed"
            _append_event(self.name, "stop", msg, False)
            return False, msg
        if self.systemd_unit and shutil.which("systemctl"):
            res = _run(f"sudo -n systemctl stop {self.systemd_unit}")
            ok = _wait_for(self.is_running, False)
            msg = "Stopped" if ok else (res.stdout.strip() or "Requested stop")
            success = res.returncode == 0 and ok
            _append_event(self.name, "stop", msg, success)
            return success, msg
        if self.stop_patterns:
            ok = False
            for pat in self.stop_patterns:
                if _pkill(pat):
                    ok = True
            stopped = _wait_for(self.is_running, False)
            msg = "Stopped" if ok else "No processes matched"
            success = ok and stopped
            _append_event(self.name, "stop", msg, success)
            return success, msg
        msg = "No stop patterns configured"
        _append_event(self.name, "stop", msg, False)
        return False, msg

def load_services_from_config(path: Path) -> Dict[str, Service]:
    if not path.exists():
        return {}
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    services: Dict[str, Service] = {}
    if not config or "services" not in config:
        return {}

    for name, attrs in config["services"].items():
        # Evaluate the 'available' field as a Python expression
        is_available = True
        if "available" in attrs:
            try:
                # Provide context for eval
                eval_context = {"os": os, "shutil": shutil}
                is_available = eval(attrs["available"], eval_context)
            except Exception:
                is_available = False

        services[name] = Service(
            name=name,
            detect=attrs.get("detect", []),
            start_cmd=attrs.get("start_cmd"),
            stop_patterns=attrs.get("stop_patterns"),
            log_path=attrs.get("log_path"),
            port=attrs.get("port"),
            available=is_available,
            systemd_unit=attrs.get("systemd_unit"),
        )
    return services


def tail_file(path: str, n: int = 200) -> str:
    if not path or not os.path.exists(path):
        return "<no log file>"
    try:
        if os.path.getsize(path) == 0:
            return "<log file empty>"
        res = _run(f"tail -n {n} {path}")
        return res.stdout or "<log file empty>"
    except Exception as e:
        return f"<tail error: {e}>"
