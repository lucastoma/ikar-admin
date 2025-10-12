import os
import shutil
import socket
import subprocess
import re
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional, List


def _run(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def _cmdline_matches(pattern: str) -> bool:
    regex = re.compile(pattern)
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
try:
    Path(EVENT_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(EVENT_LOG_PATH).touch(exist_ok=True)
except OSError:
    pass


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
    detect: List[str]
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
        if self.systemd_unit:
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
        if self.systemd_unit:
            res = _run(f"sudo -n systemctl start {self.systemd_unit}")
            ok = _wait_for(self.is_running, True)
            msg = res.stdout.strip() or "systemd start"
            success = res.returncode == 0 and ok
            _append_event(self.name, "start", msg, success)
            return success, msg
        if not self.start_cmd:
            msg = "No start command configured"
            _append_event(self.name, "start", msg, False)
            return False, msg
        _ensure_log_file(self.log_path)
        res = _run(self.start_cmd)
        success = res.returncode == 0
        output = res.stdout.strip()
        if success and not output:
            output = "Launch command executed"
        started = _wait_for(self.is_running, True)
        msg = output or "(no output)"
        final = success and started
        _append_event(self.name, "start", msg, final)
        return final, msg

    def stop(self) -> (bool, str):
        if not self.available:
            msg = "Service not installed"
            _append_event(self.name, "stop", msg, False)
            return False, msg
        if self.systemd_unit:
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


def _find_code_server_bin() -> Optional[str]:
    # First, try PATH
    path_bin = shutil.which("code-server")
    if path_bin:
        return path_bin
    # Then, search under /workspace/code-server
    for root, _, files in os.walk("/workspace/code-server"):
        for f in files:
            p = os.path.join(root, f)
            if f == "code-server" and os.access(p, os.X_OK):
                return p
    return None


def build_services() -> Dict[str, Service]:
    COMFYUI_PORT = int(os.environ.get("COMFYUI_PORT", "18188"))
    CODE_SERVER_PORT = int(os.environ.get("CODE_SERVER_PORT", "8445"))
    FILEBROWSER_PORT = int(os.environ.get("FILEBROWSER_PORT", "8085"))

    code_bin = _find_code_server_bin()
    code_log = "/workspace/code-server.log"
    code_available = bool(code_bin) or os.path.exists("/etc/systemd/system/code-server-ikar.service")
    code_cmd = None  # prefer systemd

    comfy_available = os.path.exists("/workspace/ComfyUI/main.py")
    comfy_start_cmd = None
    if comfy_available:
        comfy_start_cmd = (
            "PYTHONPATH=/home/dev/.local/lib/python3.12/site-packages:$PYTHONPATH "
            "CUDA_VISIBLE_DEVICES='' "
            "touch /workspace/comfyui.log ; "
            "nohup /usr/local/bin/python /workspace/ComfyUI/main.py "
            f"--listen 0.0.0.0 --port {COMFYUI_PORT} --cpu "
            "&> /workspace/comfyui.log &"
        )
    comfy_systemd = None
    if os.path.exists("/etc/systemd/system/comfyui-ikar.service"):
        comfy_systemd = "comfyui-ikar"

    filebrowser_bin = shutil.which("filebrowser") or "/workspace/filebrowser/filebrowser"
    filebrowser_available = os.path.exists(filebrowser_bin)
    filebrowser_start = None
    if filebrowser_available:
        filebrowser_start = (
            "touch /workspace/filebrowser.log ; "
            "nohup "
            f"{filebrowser_bin} --port {FILEBROWSER_PORT} --address 0.0.0.0 --database /workspace/filebrowser.db "
            "--root / &> /workspace/filebrowser.log &"
        )
    filebrowser_systemd = None
    if os.path.exists("/etc/systemd/system/filebrowser-ikar.service"):
        filebrowser_systemd = "filebrowser-ikar"

    tailscale_available = shutil.which("tailscaled") is not None
    tailscale_start = None
    if tailscale_available:
        tailscale_start = (
            "(sudo -n tailscaled --state=/workspace/tailscale.state --tun=userspace-networking "
            "&>> /workspace/tailscale.log &)"
        )

    services: Dict[str, Service] = {
        "comfyui": Service(
            name="comfyui",
            detect=["ComfyUI/main.py", "python .*ComfyUI/main.py"],
            start_cmd=comfy_start_cmd,
            stop_patterns=["ComfyUI/main.py"],
            log_path="/workspace/comfyui.log",
            port=COMFYUI_PORT,
            available=comfy_available,
            systemd_unit=comfy_systemd,
        ),
        "code": Service(
            name="code",
            detect=[],
            start_cmd=code_cmd,
            stop_patterns=None,
            log_path=code_log,
            port=CODE_SERVER_PORT,
            available=code_available,
            systemd_unit="code-server-ikar" if code_available else None,
        ),
        "filebrowser": Service(
            name="filebrowser",
            detect=["filebrowser"],
            start_cmd=filebrowser_start,
            stop_patterns=["filebrowser"],
            log_path="/workspace/filebrowser.log",
            port=FILEBROWSER_PORT,
            available=filebrowser_available,
            systemd_unit=filebrowser_systemd,
        ),
        "tailscale": Service(
            name="tailscale",
            detect=["tailscaled"],
            start_cmd=tailscale_start,
            stop_patterns=["tailscaled"],
            log_path="/workspace/tailscale.log",
            available=tailscale_available,
        ),
    }

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
