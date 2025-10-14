import os
import shutil
import socket
import subprocess
import re
import time
import yaml
import tempfile
import textwrap
import shlex
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any


CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_ENV_VAR_DEFAULT_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}")
_ENV_VAR_SIMPLE_RE = re.compile(r"\$(\w+)")


def _expand_env_vars(value: str, extra_env: Optional[Dict[str, str]] = None) -> str:
    """
    Expand $VAR, ${VAR}, and ${VAR:-default} constructs using os.environ merged with extra_env.
    Defaults follow POSIX shell semantics where unset/empty values fall back to the provided default.
    """
    if not isinstance(value, str):
        return value

    env: Dict[str, str] = {k: str(v) for k, v in os.environ.items()}
    if extra_env:
        env.update({str(k): str(v) for k, v in extra_env.items() if v is not None})

    def replace_with_default(match: re.Match) -> str:
        var = match.group(1)
        default = match.group(3)
        current = env.get(var)
        if current is None or current == "":
            return default or ""
        return current

    value = _ENV_VAR_DEFAULT_RE.sub(replace_with_default, value)

    def replace_simple(match: re.Match) -> str:
        var = match.group(1)
        return env.get(var, "")

    return _ENV_VAR_SIMPLE_RE.sub(replace_simple, value)


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


def _to_float(value, default: float) -> float:
    try:
        if value is None:
            raise TypeError
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: Optional[int] = None) -> Optional[int]:
    try:
        if value is None:
            raise TypeError
        return int(value)
    except (TypeError, ValueError):
        return default


class _SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


@dataclass
class Service:
    name: str
    detect: List[str] = field(default_factory=list)
    start_cmd: Optional[str] = None
    start_script: Optional[str] = None
    start_shell: Optional[str] = None
    stop_patterns: Optional[List[str]] = None
    log_path: Optional[str] = None
    port: Optional[int] = None
    available: bool = True
    systemd_unit: Optional[str] = None
    pid_file: Optional[str] = None
    workdir: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    start_timeout: float = 8.0
    stop_timeout: float = 8.0
    health: Dict = field(default_factory=dict)
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)

    def _is_pid_running(self):
        if not self.pid_file or not os.path.exists(self.pid_file):
            return False
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            return os.path.exists(f"/proc/{pid}")
        except (IOError, ValueError):
            return False

    def _expand_config_value(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        extra_env: Dict[str, str] = {}
        extra_env.update(self.env)
        extra_env.setdefault("IKAR_SERVICE", self.name)
        if self.port is not None:
            port_str = str(self.port)
            extra_env.setdefault("SERVICE_PORT", port_str)
            extra_env.setdefault("IKAR_SERVICE_PORT", port_str)
            extra_env.setdefault(f"{self.name.upper()}_PORT", port_str)

        expanded = _expand_env_vars(value, extra_env)
        try:
            expanded = expanded.format_map(_SafeFormatDict(
                port=str(self.port) if self.port is not None else "",
                name=self.name,
            ))
        except Exception:
            pass
        return expanded

    def _run_health_check(self) -> bool:
        if not self.health:
            return False

        if 'tcp' in self.health:
            tcp_conf = self.health['tcp']
            host = tcp_conf.get('host', '127.0.0.1')
            port = tcp_conf.get('port')
            if not port: return False
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(tcp_conf.get('timeout', 2))
                try:
                    s.connect((host, port))
                    return True
                except OSError:
                    return False

        if 'http' in self.health:
            http_conf = self.health['http']
            url = self._expand_config_value(http_conf.get('url'))
            if not url: return False
            try:
                import httpx
                timeout = self._expand_config_value(http_conf.get('timeout'))
                # httpx expects numeric timeout; fall back to default if conversion fails
                if isinstance(timeout, str):
                    try:
                        timeout = float(timeout)
                    except ValueError:
                        timeout = http_conf.get('timeout', 2)
                res = httpx.get(url, timeout=timeout if timeout is not None else 2)
                expect = self._expand_config_value(http_conf.get('expect', 200))
                if isinstance(expect, str):
                    try:
                        expect = int(expect)
                    except ValueError:
                        expect = 200
                return res.status_code == expect
            except (ImportError, httpx.RequestError):
                return False

        return False

    def is_running(self) -> bool:
        if not self.available:
            return False

        # 1. Systemd
        if self.systemd_unit and shutil.which("systemctl"):
            out = _run(f"sudo -n systemctl is-active {self.systemd_unit}")
            if out.returncode == 0 and out.stdout.strip() == "active":
                return True

        # 2. PID file
        if self._is_pid_running():
            return True

        # 3. Health check
        if self._run_health_check():
            return True

        # 4. Process pattern detection
        for p in self.detect:
            if _cmdline_matches(p):
                return True

        # 5. Port fallback
        if self.port is not None:
            return _is_port_open(self.port)

        return False

    def resolved_links(self) -> List[Dict[str, Any]]:
        replacements = _SafeFormatDict(
            port=str(self.port) if self.port is not None else "",
            name=self.name,
        )
        resolved = []
        for item in self.links:
            tpl = item.get("url_template") or item.get("url")
            entry = {k: v for k, v in item.items() if k != "url_template"}
            if tpl:
                try:
                    entry["url"] = tpl.format_map(replacements)
                except Exception:
                    entry["url"] = tpl
            resolved.append(entry)
        return resolved

    def supports_start(self) -> bool:
        if not self.available:
            return False
        return bool(self.systemd_unit or self.start_script or self.start_cmd)

    def supports_stop(self) -> bool:
        if not self.available:
            return False
        return bool(self.systemd_unit or self.pid_file or self.stop_patterns)

    def summary(self, running: Optional[bool] = None) -> Dict[str, Any]:
        active = self.is_running() if running is None else running
        return {
            "name": self.name,
            "title": self.display_name or self.name,
            "description": self.description,
            "tags": self.tags,
            "available": self.available,
            "running": active,
            "port": self.port,
            "log_path": self.log_path,
            "links": self.resolved_links(),
            "supports": {
                "start": self.supports_start(),
                "stop": self.supports_stop(),
                "logs": bool(self.log_path),
                "terminal": False,
            },
        }

    def detail(self, running: Optional[bool] = None) -> Dict[str, Any]:
        active = self.is_running() if running is None else running
        return {
            "name": self.name,
            "meta": {
                "title": self.display_name or self.name,
                "description": self.description,
                "tags": self.tags,
                "links": self.resolved_links(),
            },
            "status": {
                "available": self.available,
                "running": active,
                "port": self.port,
                "log_path": self.log_path,
                "health": self.health,
            },
            "lifecycle": {
                "has_start": self.supports_start(),
                "has_stop": self.supports_stop(),
                "systemd_unit": self.systemd_unit,
                "pid_file": self.pid_file,
                "start_timeout": self.start_timeout,
                "stop_timeout": self.stop_timeout,
            },
            "detect": self.detect,
        }

    def _run_start_script(self, run_env: Dict[str, str]) -> subprocess.CompletedProcess:
        script_body = textwrap.dedent(self.start_script or "").strip()
        if not script_body:
            raise ValueError("start script empty")

        if not script_body.startswith("#!"):
            interpreter = (self.start_shell or "/bin/sh").strip() or "/bin/sh"
            if interpreter.startswith("#!"):
                shebang = interpreter
            else:
                shebang = f"#!{interpreter}"
            script_body = f"{shebang}\n{script_body}"

        script_body = script_body.rstrip() + "\n"

        with tempfile.NamedTemporaryFile("w", delete=False, prefix=f"{self.name}_start_", suffix=".sh") as tmp:
            tmp.write(script_body)
            script_path = tmp.name

        os.chmod(script_path, 0o750)

        try:
            process = subprocess.run(
                [script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.workdir,
                env=run_env,
            )
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass
        return process

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
            ok = _wait_for(self.is_running, True, timeout=self.start_timeout)
            msg = res.stdout.strip() or "systemd start"
            success = res.returncode == 0 and ok
            _append_event(self.name, "start", msg, success)
            return success, msg
        if not self.start_script and not self.start_cmd:
            msg = "No start command configured"
            # Treat as no-op success (acknowledged request)
            _append_event(self.name, "start", msg, True)
            return True, msg
        _ensure_log_file(self.log_path)
        # Prepare environment
        run_env = os.environ.copy()
        run_env.update(self.env)
        run_env.setdefault("IKAR_SERVICE", self.name)
        if self.log_path and "LOG_FILE" not in run_env:
            run_env["LOG_FILE"] = self.log_path
        if self.pid_file and "PID_FILE" not in run_env:
            run_env["PID_FILE"] = self.pid_file
        if self.port and "SERVICE_PORT" not in run_env:
            run_env["SERVICE_PORT"] = str(self.port)
        run_env.setdefault("IKAR_SERVICE_PORT", run_env.get("SERVICE_PORT", ""))

        try:
            if self.start_script:
                process = self._run_start_script(run_env)
            else:
                expanded_cmd = os.path.expandvars(self.start_cmd)
                process = subprocess.run(
                    expanded_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.workdir,
                    env=run_env
                )
        except Exception as exc:
            msg = f"Start command failed: {exc}"
            _append_event(self.name, "start", msg, False)
            return False, msg

        success = process.returncode == 0
        output = process.stdout.strip()
        if success and not output:
            output = "Launch command executed"

        started = _wait_for(self.is_running, True, timeout=self.start_timeout)
        msg = output or "(no output)"

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
            ok = _wait_for(self.is_running, False, timeout=self.stop_timeout)
            msg = "Stopped" if ok else (res.stdout.strip() or "Requested stop")
            success = res.returncode == 0 and ok
            _append_event(self.name, "stop", msg, success)
            return success, msg

        # PID file stop logic
        if self.pid_file and os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, 15)  # SIGTERM
                stopped = _wait_for(lambda: not os.path.exists(f"/proc/{pid}"), True, timeout=self.stop_timeout)
                if stopped:
                    msg = f"Stopped process with PID {pid}"
                    _append_event(self.name, "stop", msg, True)
                    return True, msg
                else:
                    os.kill(pid, 9) # SIGKILL
                    stopped = _wait_for(lambda: not os.path.exists(f"/proc/{pid}"), True, timeout=2)
                    msg = f"Force-stopped process with PID {pid}"
                    _append_event(self.name, "stop", msg, stopped)
                    return stopped, msg
            except (IOError, ValueError, ProcessLookupError) as e:
                _append_event(self.name, "stop", f"Error stopping with pidfile: {e}", False)
                # Fall through to pkill

        if self.stop_patterns:
            ok = False
            for pat in self.stop_patterns:
                if _pkill(pat):
                    ok = True
            stopped = _wait_for(self.is_running, False, timeout=self.stop_timeout)
            msg = "Stopped" if ok else "No processes matched"
            success = ok and stopped
            _append_event(self.name, "stop", msg, success)
            return success, msg
        msg = "No stop patterns or pid_file configured"
        _append_event(self.name, "stop", msg, False)
        return False, msg

import warnings

def _evaluate_available(expr: any) -> bool:
    if isinstance(expr, bool):
        return expr
    if not isinstance(expr, str) or not expr.strip():
        return True

    expr = expr.strip()

    safe_functions = {
        "exists": os.path.exists,
        "which": shutil.which,
    }

    # More robust tokenizer
    token_regex = re.compile(r"""
        (?P<LPAREN>\() |
        (?P<RPAREN>\)) |
        (?P<OP>\b(and|or)\b) |
        (?P<FUNC>\b(exists|which)\b) |  # Only match known safe functions
        (?P<STR>'[^']*'|\"[^\"]*\") |
        (?P<IDENT>[a-zA-Z_][a-zA-Z0-9_]*) | # Other identifiers are invalid
        (?P<SPACE>\s+) |
        (?P<MISMATCH>.)
    """, re.VERBOSE)

    output_queue = []
    operator_stack = []

    def precedence(op):
        return {"or": 1, "and": 2}.get(op, 0)

    try:
        tokens = token_regex.finditer(expr)
        for match in tokens:
            kind = match.lastgroup
            value = match.group()

            if kind == "SPACE":
                continue

            if kind == "STR":
                output_queue.append(("ARG", value[1:-1]))
            elif kind == "FUNC":
                operator_stack.append(("FUNC", value))
            elif kind == "IDENT":
                raise ValueError(f"Unsafe or unknown identifier: {value}")
            elif kind == "OP":
                while (operator_stack and
                       operator_stack[-1][0] == "OP" and
                       precedence(operator_stack[-1][1]) >= precedence(value)):
                    output_queue.append(operator_stack.pop())
                operator_stack.append(("OP", value))
            elif kind == "LPAREN":
                operator_stack.append(("LPAREN", "("))
            elif kind == "RPAREN":
                while operator_stack and operator_stack[-1][0] != "LPAREN":
                    output_queue.append(operator_stack.pop())
                if not operator_stack or operator_stack.pop()[0] != "LPAREN":
                    raise ValueError("Mismatched parentheses")
                if operator_stack and operator_stack[-1][0] == "FUNC":
                    output_queue.append(operator_stack.pop())
            else:
                raise ValueError(f"Invalid token: {value}")

        while operator_stack:
            op_type, op_val = operator_stack.pop()
            if op_type == "LPAREN":
                raise ValueError("Mismatched parentheses")
            output_queue.append((op_type, op_val))

        # Evaluate RPN
        eval_stack = []
        for token_type, value in output_queue:
            if token_type == "ARG":
                eval_stack.append(value)
            elif token_type == "FUNC":
                if not eval_stack:
                    raise ValueError(f"Missing argument for function {value}")
                arg = eval_stack.pop()
                result = safe_functions[value](arg)
                eval_stack.append(result)
            elif token_type == "OP":
                if len(eval_stack) < 2:
                    raise ValueError(f"Missing operand for operator {value}")
                right = eval_stack.pop()
                left = eval_stack.pop()
                if value == 'and':
                    eval_stack.append(left and right)
                elif value == 'or':
                    eval_stack.append(left or right)

        if len(eval_stack) != 1:
            raise ValueError("Invalid expression structure")

        return bool(eval_stack[0])

    except ValueError as e:
        warnings.warn(f"Invalid available expression '{expr}': {e}")
        return False
    except Exception as e:
        warnings.warn(f"Error evaluating available expression '{expr}': {e}")
        return False


def load_services_from_config(path: Path) -> Dict[str, Service]:
    if not path.exists():
        return {}
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    services: Dict[str, Service] = {}
    if not config or "services" not in config:
        return {}

    for name, attrs in config["services"].items():
        attrs = attrs or {}
        meta = attrs.get("meta") or {}
        runtime = attrs.get("runtime") or {}
        lifecycle = attrs.get("lifecycle") or {}
        start_conf = lifecycle.get("start") or {}
        stop_conf = lifecycle.get("stop") or {}
        observability = attrs.get("observability") or {}

        detect = attrs.get("detect", [])
        if isinstance(detect, str):
            detect = [detect]

        stop_patterns = stop_conf.get("patterns", attrs.get("stop_patterns"))
        if isinstance(stop_patterns, str):
            stop_patterns = [stop_patterns]
        elif not stop_patterns:
            stop_patterns = []

        env_combined: Dict[str, str] = {}
        env_combined.update(attrs.get("env") or {})
        env_combined.update(runtime.get("env") or {})
        env_combined = {str(k): str(v) for k, v in env_combined.items()}

        start_timeout = _to_float(start_conf.get("timeout", attrs.get("start_timeout")), 8.0)
        stop_timeout = _to_float(stop_conf.get("timeout", attrs.get("stop_timeout")), 8.0)

        port_val = _to_int(observability.get("port", attrs.get("port")))
        log_path = observability.get("log_path", attrs.get("log_path"))
        health = observability.get("health", attrs.get("health", {})) or {}

        pid_file = stop_conf.get("pid_file", attrs.get("pid_file"))
        workdir = runtime.get("workdir", attrs.get("workdir"))
        start_shell = runtime.get("shell", start_conf.get("shell"))
        if isinstance(start_shell, str):
            start_shell = start_shell.strip()

        links = []
        for link in meta.get("links", []):
            if isinstance(link, dict):
                entry: Dict[str, Any] = {
                    "label": link.get("label") or link.get("title") or link.get("name") or "Link",
                }
                if link.get("kind"):
                    entry["kind"] = link["kind"]
                if link.get("description"):
                    entry["description"] = link["description"]
                url_template = link.get("url") or link.get("href")
                if url_template:
                    entry["url_template"] = url_template
                links.append(entry)
            elif isinstance(link, str):
                links.append({"label": link, "url_template": link})

        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        tags = [str(tag) for tag in tags]

        is_available = _evaluate_available(attrs.get("available"))

        services[name] = Service(
            name=name,
            detect=detect,
            start_cmd=attrs.get("start_cmd"),
            start_script=start_conf.get("script"),
            start_shell=start_shell,
            stop_patterns=stop_patterns,
            log_path=log_path,
            port=port_val,
            available=is_available,
            systemd_unit=attrs.get("systemd_unit"),
            pid_file=pid_file,
            workdir=workdir,
            env=env_combined,
            start_timeout=start_timeout,
            stop_timeout=stop_timeout,
            health=health,
            display_name=meta.get("title") or meta.get("name"),
            description=meta.get("description"),
            tags=tags,
            links=links,
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
