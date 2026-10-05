#!/usr/bin/env python3
"""Background lifecycle supervisor for the Shokker Paint Booth server.

The public commands are intentionally small and synchronous:

    python spb_server_supervisor.py start
    python spb_server_supervisor.py refresh
    python spb_server_supervisor.py stop
    python spb_server_supervisor.py status

``run`` is the internal, detached supervisor entry point.  The supervisor owns
exactly one ``server_v5.py`` child at a time.  It restarts every unintentional
exit (including exit code zero), while a durable manual-stop marker is the only
state that tells it to remain down.

Only Python's standard library is used.  Windows-specific process inspection is
kept behind narrow helpers so the state machine remains unit-testable without
touching the live SPB port or process tree.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_PORT = 59876
STATE_SCHEMA = 1
CONTROL_DIR_NAME = ".spb_supervisor"
STATE_NAME = "state.json"
MANUAL_STOP_NAME = "manual_stop.json"
LOCK_NAME = "supervisor.lock"
REQUESTS_DIR_NAME = "requests"
ACKS_DIR_NAME = "acks"
LIFECYCLE_LOG_NAME = "lifecycle.log"
CHILD_LOG_NAME = "server_console.log"

HEARTBEAT_INTERVAL = 1.0
ACTIVE_HEARTBEAT_MAX_AGE = 30.0
# A full registry rebuild took 201.21s on 2026-09-01.  Leave enough headroom
# for a cold boot so the visible controller does not report a false failure
# while the detached supervisor is still bringing up a healthy child.
DEFAULT_COMMAND_TIMEOUT = 360.0
DEFAULT_POLL_INTERVAL = 0.20
DEFAULT_BASE_BACKOFF = 1.0
DEFAULT_MAX_BACKOFF = 30.0
DEFAULT_STABLE_WINDOW = 120.0
DEFAULT_LOG_BYTES = 2 * 1024 * 1024
DEFAULT_LOG_BACKUPS = 3

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_STOPPED = 3
EXIT_BLOCKED = 4


def _utc_stamp(now: float | None = None) -> str:
    value = time.time() if now is None else now
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(value))


def _resolved(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def _same_path(left: str | os.PathLike[str], right: str | os.PathLike[str]) -> bool:
    try:
        a = os.path.normcase(str(_resolved(left)))
        b = os.path.normcase(str(_resolved(right)))
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    return a == b


def _atomic_json_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(dict(value), handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    # Windows can briefly deny replacement while another process has the tiny
    # JSON file open for a status read (or while Defender scans the new file).
    # Keep the atomic temp+replace contract, but tolerate that transient sharing
    # window instead of letting a harmless status poll kill the supervisor.
    last_error: PermissionError | None = None
    for attempt in range(25):
        try:
            os.replace(temporary, path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(min(0.005 * (attempt + 1), 0.05))
    _safe_unlink(temporary)
    if last_error is not None:
        raise last_error


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return None


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # Do not use os.kill(pid, 0) on Windows.  Unlike POSIX, Windows signal
        # handling is TerminateProcess-based for most values; a liveness probe
        # must be strictly read-only.
        process_query_limited_information = 0x1000
        synchronize = 0x00100000
        still_active = 259
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        kernel32.GetExitCodeProcess.restype = ctypes.c_bool
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(
            process_query_limited_information | synchronize,
            False,
            int(pid),
        )
        if not handle:
            # Access denied still proves that a process currently owns the PID.
            return int(kernel32.GetLastError()) == 5
        try:
            exit_code = ctypes.c_uint32()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


@dataclass(frozen=True)
class ControlPaths:
    root: Path

    @property
    def directory(self) -> Path:
        return self.root / CONTROL_DIR_NAME

    @property
    def state(self) -> Path:
        return self.directory / STATE_NAME

    @property
    def manual_stop(self) -> Path:
        return self.directory / MANUAL_STOP_NAME

    @property
    def lock(self) -> Path:
        return self.directory / LOCK_NAME

    @property
    def requests(self) -> Path:
        return self.directory / REQUESTS_DIR_NAME

    @property
    def acks(self) -> Path:
        return self.directory / ACKS_DIR_NAME

    @property
    def lifecycle_log(self) -> Path:
        return self.directory / LIFECYCLE_LOG_NAME

    @property
    def child_log(self) -> Path:
        return self.directory / CHILD_LOG_NAME

    def ensure(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.requests.mkdir(parents=True, exist_ok=True)
        self.acks.mkdir(parents=True, exist_ok=True)


class CappedRotatingLog:
    """Append-only text log with a hard size cap and finite backups."""

    def __init__(self, path: Path, *, max_bytes: int = DEFAULT_LOG_BYTES, backups: int = DEFAULT_LOG_BACKUPS):
        if max_bytes < 128:
            raise ValueError("max_bytes must be at least 128")
        if backups < 0:
            raise ValueError("backups cannot be negative")
        self.path = path
        self.max_bytes = int(max_bytes)
        self.backups = int(backups)
        self._lock = threading.Lock()

    def write(self, message: str) -> None:
        if not isinstance(message, str):
            message = str(message)
        encoded = message.encode("utf-8", errors="replace")
        # A single pathological line must not defeat the cap.
        if len(encoded) > self.max_bytes:
            encoded = encoded[-self.max_bytes :]
            encoded = b"[...line tail...] " + encoded
            encoded = encoded[-self.max_bytes :]
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                current_size = self.path.stat().st_size
            except FileNotFoundError:
                current_size = 0
            if current_size + len(encoded) > self.max_bytes:
                # A visible viewer briefly opens each file while polling.  On
                # Windows a rename can momentarily collide with that read even
                # though the viewer closes handles immediately.  Retry the
                # bounded rotation instead of letting observability kill the
                # child-output pump.
                for attempt in range(6):
                    try:
                        self._rotate()
                        break
                    except PermissionError:
                        if attempt == 5:
                            # Preserve this line and retry rotation on the next
                            # write.  A few excess bytes are safer than losing
                            # the only crash evidence the owner can paste.
                            break
                        time.sleep(0.02 * (attempt + 1))
            with self.path.open("ab") as handle:
                handle.write(encoded)

    def line(self, message: str, *, now: float | None = None) -> None:
        self.write(f"{_utc_stamp(now)} {message.rstrip()}\n")

    def _rotate(self) -> None:
        if self.backups == 0:
            _safe_unlink(self.path)
            return
        oldest = self.path.with_name(f"{self.path.name}.{self.backups}")
        _safe_unlink(oldest)
        for index in range(self.backups - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            destination = self.path.with_name(f"{self.path.name}.{index + 1}")
            if source.exists():
                os.replace(source, destination)
        if self.path.exists():
            os.replace(self.path, self.path.with_name(f"{self.path.name}.1"))


class SingletonGuard:
    """Process-lifetime singleton guard (named mutex on Windows, flock elsewhere)."""

    ERROR_ALREADY_EXISTS = 183

    def __init__(self, root: Path):
        digest = hashlib.sha256(os.path.normcase(str(root)).encode("utf-8")).hexdigest()[:24]
        self.name = f"Local\\SPBServerSupervisor_{digest}"
        self.root = root
        self._handle: int | None = None
        self._file: Any = None

    def acquire(self) -> bool:
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            kernel32.CreateMutexW.restype = ctypes.c_void_p
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle.restype = ctypes.c_bool
            handle = kernel32.CreateMutexW(None, False, self.name)
            if not handle:
                return False
            if kernel32.GetLastError() == self.ERROR_ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                return False
            self._handle = int(handle)
            return True

        import fcntl

        lock_path = self.root / CONTROL_DIR_NAME / LOCK_NAME
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = lock_path.open("a+b")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._file.close()
            self._file = None
            return False
        return True

    def release(self) -> None:
        if os.name == "nt" and self._handle is not None:
            ctypes.windll.kernel32.CloseHandle(self._handle)  # type: ignore[attr-defined]
            self._handle = None
        elif self._file is not None:
            try:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            finally:
                self._file.close()
                self._file = None

    def __enter__(self) -> "SingletonGuard":
        if not self.acquire():
            raise RuntimeError("another supervisor instance already owns this root")
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.release()


def _singleton_is_owned(root: Path) -> bool:
    """Read-only-in-effect probe for an existing supervisor singleton.

    Acquiring and immediately releasing an unowned mutex/file lock does not
    affect a server process.  Failure to acquire is treated conservatively as
    "owned" so a controller can never downgrade a supervised child to legacy
    merely because state.json was briefly stale or unavailable.
    """

    guard = SingletonGuard(root)
    if not guard.acquire():
        return True
    guard.release()
    return False


def _http_build_check(port: int, *, timeout: float = 0.75) -> dict[str, Any] | None:
    request = Request(f"http://127.0.0.1:{int(port)}/build-check", headers={"Cache-Control": "no-cache"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read(256 * 1024).decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (OSError, URLError, UnicodeError, json.JSONDecodeError, ValueError):
        return None


def _validated_health(port: int, root: Path, expected_pid: int) -> bool:
    payload = _http_build_check(port)
    if not payload:
        return False
    try:
        payload_pid = int(payload.get("pid", -1))
        payload_port = int(payload.get("port", -1))
    except (TypeError, ValueError):
        return False
    return (
        payload_pid == int(expected_pid)
        and payload_port == int(port)
        and payload.get("status") == "running"
        and _same_path(str(payload.get("server_dir", "")), root)
    )


def _port_is_open(port: int, *, timeout: float = 0.20) -> bool:
    for family, address in (
        (socket.AF_INET, ("127.0.0.1", int(port))),
        (socket.AF_INET6, ("::1", int(port), 0, 0)),
    ):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as client:
                client.settimeout(timeout)
                if client.connect_ex(address) == 0:
                    return True
        except OSError:
            continue
    return False


def _windows_listener_pids(port: int) -> set[int] | None:
    """Return exact TCP listener PIDs from netstat, or None if inspection failed."""

    if os.name != "nt":
        return None
    try:
        result = subprocess.run(
            ["netstat.exe", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    listeners: set[int] = set()
    for raw_line in result.stdout.splitlines():
        fields = raw_line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP" or fields[3].upper() != "LISTENING":
            continue
        local = fields[1]
        match = re.search(r":(\d+)$", local)
        if not match or int(match.group(1)) != int(port):
            continue
        try:
            listeners.add(int(fields[4]))
        except ValueError:
            continue
    return listeners


def _windows_process_command_line(pid: int) -> str | None:
    if os.name != "nt" or pid <= 0:
        return None
    command = (
        "$p=Get-CimInstance Win32_Process -Filter 'ProcessId="
        + str(int(pid))
        + "'; if ($p) { [Console]::Out.Write($p.CommandLine) }"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


@dataclass(frozen=True)
class PortInspection:
    kind: str
    pid: int | None = None
    reason: str = ""


def inspect_port_owner(port: int, root: Path) -> PortInspection:
    """Classify a listener without ever mutating it.

    A legacy server is considered safe to replace only when all independent
    identity checks agree: `/build-check` canonical root and PID, netstat's sole
    listener PID, and a `server_v5.py` command line.
    """

    if not _port_is_open(port):
        return PortInspection("free")
    payload = _http_build_check(port)
    if not payload:
        return PortInspection("blocked", reason=f"port {port} is listening but is not a verifiable SPB /build-check")
    try:
        pid = int(payload.get("pid", -1))
        response_port = int(payload.get("port", -1))
    except (TypeError, ValueError):
        return PortInspection("blocked", reason="SPB identity response has an invalid PID or port")
    if pid <= 0 or response_port != int(port):
        return PortInspection("blocked", reason="SPB identity response does not match the requested port")
    if payload.get("status") != "running":
        return PortInspection("blocked", pid=pid, reason="SPB listener did not report a running server")
    reported_root = str(payload.get("server_dir", ""))
    if not _same_path(reported_root, root):
        # Owner 2026-09-07: Fresh Start appeared to load 8.0.4 after an old
        # registered shokker:// handler claimed 59876. Identify both copies;
        # never silently reuse or terminate a different installation.
        return PortInspection("blocked", pid=pid, reason=(
            f"port {port} is occupied by SPB {payload.get('version', 'unknown version')} "
            f"from {reported_root!r} (PID {pid}), not this project {str(root)!r}. "
            "Close that other SPB instance, then run SPB_FRESH_START again"
        ))
    if os.name != "nt":
        return PortInspection("blocked", pid=pid, reason="legacy listener replacement is supported only on Windows")
    listener_pids = _windows_listener_pids(port)
    if listener_pids != {pid}:
        return PortInspection(
            "blocked",
            pid=pid,
            reason=f"listener PID set {sorted(listener_pids or [])} does not exactly match /build-check PID {pid}",
        )
    command_line = _windows_process_command_line(pid)
    normalized = (command_line or "").replace("\\", "/").lower()
    if not re.search(r"(?:^|[ /\"'])server_v5\.py(?:$|[ /\"'])", normalized):
        return PortInspection("blocked", pid=pid, reason="listener process is not an exact server_v5.py command")
    return PortInspection("legacy_spb", pid=pid, reason="canonical foreground SPB server")


def _terminate_exact_pid(pid: int, *, timeout: float = 12.0) -> bool:
    """Terminate one previously verified PID; never walks or pattern-kills a tree."""

    if pid <= 0 or pid == os.getpid():
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_is_alive(pid):
            return True
        time.sleep(0.10)
    return not _pid_is_alive(pid)


def _console_python() -> Path:
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        console = executable.with_name("python.exe")
        if console.exists():
            return console
    preferred = Path(r"C:\Python313\python.exe")
    if os.name == "nt" and preferred.exists():
        return preferred
    return executable


def _windowless_python() -> Path:
    console = _console_python()
    if os.name == "nt":
        candidate = console.with_name("pythonw.exe")
        if candidate.exists():
            return candidate
    return console


def _creation_flags(*, detached: bool) -> int:
    if os.name != "nt":
        return 0
    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if detached:
        flags |= int(getattr(subprocess, "DETACHED_PROCESS", 0))
        flags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    return flags


class Supervisor:
    """Own and continuously supervise a single SPB server child."""

    def __init__(
        self,
        root: Path,
        *,
        port: int = DEFAULT_PORT,
        launch_token: str = "",
        child_command: Sequence[str] | None = None,
        popen_factory: Callable[..., Any] = subprocess.Popen,
        health_probe: Callable[[int, Path, int], bool] = _validated_health,
        wall_time: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        base_backoff: float = DEFAULT_BASE_BACKOFF,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        stable_window: float = DEFAULT_STABLE_WINDOW,
        log_bytes: int = DEFAULT_LOG_BYTES,
        log_backups: int = DEFAULT_LOG_BACKUPS,
    ):
        self.root = _resolved(root)
        self.port = int(port)
        self.launch_token = launch_token
        self.paths = ControlPaths(self.root)
        self.paths.ensure()
        self.child_command = list(child_command) if child_command is not None else [
            str(_console_python()),
            str(self.root / "server_v5.py"),
        ]
        self.popen_factory = popen_factory
        self.health_probe = health_probe
        self.wall_time = wall_time
        self.monotonic = monotonic
        self.sleep = sleep
        self.poll_interval = float(poll_interval)
        self.base_backoff = max(0.0, float(base_backoff))
        self.max_backoff = max(self.base_backoff, float(max_backoff))
        self.stable_window = max(0.0, float(stable_window))
        self.lifecycle_log = CappedRotatingLog(self.paths.lifecycle_log, max_bytes=log_bytes, backups=log_backups)
        self.child_log = CappedRotatingLog(self.paths.child_log, max_bytes=log_bytes, backups=log_backups)
        self.instance_token = uuid.uuid4().hex
        self.child: Any = None
        self.child_started_at = 0.0
        self.child_generation = 0
        self.child_ready = False
        self.restart_count = 0
        self.crash_streak = 0
        self.next_start_at = self.monotonic()
        self.phase = "initializing"
        self.last_exit_code: int | None = None
        self.last_exit_at: float | None = None
        self._last_state_write = 0.0
        self._pending: dict[str, dict[str, Any]] = {}
        self._pump_threads: list[threading.Thread] = []

    def _log(self, message: str) -> None:
        # Observability must never become the reason supervision stops.  A full,
        # locked, or briefly unavailable disk may cost a log line, but it must
        # not orphan the server child.
        try:
            self.lifecycle_log.line(f"[supervisor pid={os.getpid()}] {message}", now=self.wall_time())
        except OSError:
            pass

    def _state_payload(self) -> dict[str, Any]:
        child_pid = None
        if self.child is not None and self.child.poll() is None:
            child_pid = int(self.child.pid)
        return {
            "schema": STATE_SCHEMA,
            "root": str(self.root),
            "port": self.port,
            "supervisor_pid": os.getpid(),
            "instance_token": self.instance_token,
            "launch_token": self.launch_token,
            "heartbeat_at": self.wall_time(),
            "phase": self.phase,
            "child_pid": child_pid,
            "child_generation": self.child_generation,
            "child_ready": bool(child_pid and self.child_ready),
            "restart_count": self.restart_count,
            "crash_streak": self.crash_streak,
            "last_exit_code": self.last_exit_code,
            "last_exit_at": self.last_exit_at,
            "lifecycle_log": str(self.paths.lifecycle_log),
            "child_log": str(self.paths.child_log),
        }

    def _write_state(self, *, force: bool = False) -> bool:
        now = self.monotonic()
        if not force and now - self._last_state_write < HEARTBEAT_INTERVAL:
            return True
        try:
            _atomic_json_write(self.paths.state, self._state_payload())
        except OSError as exc:
            self._log(f"state heartbeat write failed: {exc!r}; supervision continues")
            return False
        self._last_state_write = now
        return True

    def _write_ack(self, request_id: str, action: str, *, ok: bool, message: str) -> bool:
        if not request_id:
            return True
        try:
            _atomic_json_write(
                self.paths.acks / f"{request_id}.json",
                {
                    "schema": STATE_SCHEMA,
                    "request_id": request_id,
                    "action": action,
                    "ok": bool(ok),
                    "message": message,
                    "instance_token": self.instance_token,
                    "child_generation": self.child_generation,
                    "child_pid": int(self.child.pid) if self.child is not None and self.child.poll() is None else None,
                    "completed_at": self.wall_time(),
                },
            )
        except OSError as exc:
            self._log(f"control acknowledgement {request_id} write failed: {exc!r}; supervision continues")
            return False
        return True

    def _consume_requests(self) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        try:
            candidates = sorted(self.paths.requests.glob("*.json"), key=lambda item: item.name)
        except OSError:
            return requests
        for path in candidates:
            payload = _read_json(path)
            if not payload:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    self._log(f"could not remove unreadable control request {path.name}: {exc!r}")
                continue
            request_id = str(payload.get("request_id", ""))
            action = str(payload.get("action", ""))
            target = str(payload.get("instance_token", ""))
            if not request_id:
                try:
                    path.unlink()
                except (FileNotFoundError, OSError):
                    pass
                continue
            # Delete before execution.  If antivirus or filesystem contention
            # prevents deletion, defer the request rather than executing the
            # same Refresh repeatedly on every supervisor tick.
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError as exc:
                self._log(f"control request {request_id} could not be claimed: {exc!r}; retrying later")
                continue
            if target and target != self.instance_token:
                self._write_ack(request_id, action, ok=False, message="request targeted a stale supervisor instance")
                continue
            requests.append(payload)
        return requests

    def _pump_child_output(self, process: Any, generation: int) -> None:
        stream = getattr(process, "stdout", None)
        if stream is None:
            return
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                try:
                    self.child_log.line(
                        f"[child gen={generation} pid={process.pid}] {line.rstrip()}",
                        now=self.wall_time(),
                    )
                except OSError:
                    # A transient viewer/rotation collision or disk hiccup may
                    # cost one line; it must never permanently end log capture.
                    continue
        except (OSError, ValueError):
            pass
        finally:
            try:
                stream.close()
            except (OSError, ValueError):
                pass

    def _launch_child(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "SHOKKER_PORT": str(self.port),
                "PYTHONHASHSEED": "0",
                "PYTHONUNBUFFERED": "1",
                "SPB_SUPERVISOR_INSTANCE": self.instance_token,
            }
        )
        # Owner 2026-10-02: don't silently disable persistent picker repair.
        # Preserve an explicit parent opt-out; the current baker skips unchanged
        # content and uses an OS lock, so restarts cannot launch competing bakes.
        self.child_generation += 1
        self.phase = "starting"
        self.child_ready = False
        self.child = self.popen_factory(
            self.child_command,
            cwd=str(self.root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=_creation_flags(detached=False),
        )
        self.child_started_at = self.monotonic()
        self._log(
            f"started child generation {self.child_generation} PID {self.child.pid} on port {self.port}; "
            f"command={self.child_command!r}"
        )
        pump = threading.Thread(
            target=self._pump_child_output,
            args=(self.child, self.child_generation),
            name=f"spb-child-log-{self.child_generation}",
            daemon=True,
        )
        pump.start()
        self._pump_threads.append(pump)

    def _terminate_child(self, reason: str) -> bool:
        process = self.child
        if process is None:
            return True
        if process.poll() is not None:
            self.child = None
            self.child_ready = False
            return True
        self._log(f"terminating owned child PID {process.pid}: {reason}")
        try:
            process.terminate()
            process.wait(timeout=12.0)
        except subprocess.TimeoutExpired:
            self._log(f"owned child PID {process.pid} did not stop in 12s; killing that exact child")
            try:
                process.kill()
                process.wait(timeout=5.0)
            except (OSError, subprocess.SubprocessError) as exc:
                self._log(f"exact-child kill failed for PID {process.pid}: {exc!r}")
        except (OSError, subprocess.SubprocessError) as exc:
            self._log(f"exact-child terminate failed for PID {process.pid}: {exc!r}")
            if process.poll() is None:
                try:
                    process.kill()
                    process.wait(timeout=5.0)
                except (OSError, subprocess.SubprocessError) as kill_exc:
                    self._log(f"exact-child fallback kill failed for PID {process.pid}: {kill_exc!r}")
        if process.poll() is None:
            # Never discard ownership of a process that Windows still reports
            # alive.  Forgetting it could make Stop lie or Refresh launch a
            # duplicate server beside the original.
            self._log(f"owned child PID {process.pid} is still alive; retaining ownership")
            return False
        self.child = None
        self.child_ready = False
        return True

    def _complete_ready_requests(self) -> None:
        completed: list[str] = []
        for request_id, pending in self._pending.items():
            if self.child_ready and self.child_generation >= int(pending["target_generation"]):
                action = str(pending["action"])
                wrote = self._write_ack(
                    request_id,
                    action,
                    ok=True,
                    message=f"server ready at generation {self.child_generation}, PID {self.child.pid}",
                )
                if wrote:
                    completed.append(request_id)
        for request_id in completed:
            self._pending.pop(request_id, None)

    def _handle_request(self, payload: Mapping[str, Any]) -> bool:
        request_id = str(payload.get("request_id", ""))
        action = str(payload.get("action", ""))
        if action == "stop":
            if not self.paths.manual_stop.exists():
                try:
                    _atomic_json_write(
                        self.paths.manual_stop,
                        {
                            "schema": STATE_SCHEMA,
                            "root": str(self.root),
                            "port": self.port,
                            "request_id": request_id,
                            "requested_at": self.wall_time(),
                            "reason": "manual stop request",
                        },
                    )
                except OSError as exc:
                    self._write_ack(
                        request_id,
                        action,
                        ok=False,
                        message="durable manual-stop intent could not be written; server was not stopped",
                    )
                    self._log(f"manual-stop request {request_id} rejected because its marker write failed: {exc!r}")
                    return False
            return True
        if action == "refresh":
            try:
                _safe_unlink(self.paths.manual_stop)
            except OSError as exc:
                self._write_ack(
                    request_id,
                    action,
                    ok=False,
                    message="manual-stop marker could not be cleared; refresh was not attempted",
                )
                self._log(f"refresh request {request_id} rejected because stop intent could not be cleared: {exc!r}")
                return False
            target_generation = self.child_generation + 1
            if not self._terminate_child("manual refresh"):
                self.phase = "running" if self.child_ready else "refresh_failed"
                self._write_state(force=True)
                self._write_ack(
                    request_id,
                    action,
                    ok=False,
                    message=f"owned server PID {self.child.pid} could not be stopped; refresh aborted",
                )
                self._log(f"refresh request {request_id} aborted because the owned child remained alive")
                return False
            self._pending[request_id] = {"action": action, "target_generation": target_generation}
            self.crash_streak = 0
            self.next_start_at = self.monotonic()
            self.phase = "refreshing"
            self._log(f"accepted refresh request {request_id}; target generation {target_generation}")
            return False
        if action in {"start", "ensure_started"}:
            target_generation = self.child_generation if self.child is not None else self.child_generation + 1
            self._pending[request_id] = {"action": action, "target_generation": target_generation}
            self.next_start_at = min(self.next_start_at, self.monotonic())
            return False
        self._write_ack(request_id, action, ok=False, message=f"unknown action: {action!r}")
        return False

    def _stop_from_marker(self) -> bool:
        marker = _read_json(self.paths.manual_stop) or {}
        request_id = str(marker.get("request_id", ""))
        self.phase = "stopping"
        self._write_state(force=True)
        if not self._terminate_child("durable manual-stop intent"):
            self.phase = "stop_failed"
            self._write_state(force=True)
            if request_id:
                self._write_ack(
                    request_id,
                    "stop",
                    ok=False,
                    message=f"owned server PID {self.child.pid} is still alive; supervisor retained ownership and will retry",
                )
            self._log("manual-stop attempt could not terminate the owned child; retaining ownership and retrying")
            return False
        self.phase = "stopped"
        self._write_state(force=True)
        if request_id:
            self._write_ack(request_id, "stop", ok=True, message="supervisor and owned server stopped by manual intent")
        self._log("manual-stop intent honored; supervisor exiting without restart")
        return True

    def run_forever(self, *, acquire_singleton: bool = True) -> int:
        guard = SingletonGuard(self.root) if acquire_singleton else None
        if guard is not None and not guard.acquire():
            self._log("duplicate run command refused because the singleton is already owned")
            return EXIT_BLOCKED
        try:
            if self.paths.manual_stop.exists():
                self._log("run command found durable manual-stop intent; remaining stopped")
            self._log(f"supervisor instance {self.instance_token} started for {self.root}")
            self.phase = "starting"
            self._write_state(force=True)
            while True:
                if self.paths.manual_stop.exists():
                    if self._stop_from_marker():
                        return EXIT_OK
                    self.sleep(max(self.poll_interval, 0.25))
                    continue

                stop_requested = False
                for request in self._consume_requests():
                    stop_requested = self._handle_request(request) or stop_requested
                if stop_requested or self.paths.manual_stop.exists():
                    if self._stop_from_marker():
                        return EXIT_OK
                    self.sleep(max(self.poll_interval, 0.25))
                    continue

                now = self.monotonic()
                if self.child is not None:
                    return_code = self.child.poll()
                    if return_code is not None:
                        uptime = max(0.0, now - self.child_started_at)
                        self.last_exit_code = int(return_code)
                        self.last_exit_at = self.wall_time()
                        self.child = None
                        self.child_ready = False
                        self.restart_count += 1
                        if uptime >= self.stable_window:
                            self.crash_streak = 0
                        else:
                            self.crash_streak += 1
                        exponent = min(max(self.crash_streak - 1, 0), 30)
                        delay = min(self.max_backoff, self.base_backoff * (2**exponent))
                        self.next_start_at = now + delay
                        self.phase = "waiting_to_restart"
                        self._log(
                            f"child exited unintentionally with code {return_code} after {uptime:.2f}s; "
                            f"restart #{self.restart_count} in {delay:.2f}s (no give-up limit)"
                        )

                if self.child is None and now >= self.next_start_at:
                    try:
                        self._launch_child()
                    except (OSError, subprocess.SubprocessError) as exc:
                        self.restart_count += 1
                        self.crash_streak += 1
                        exponent = min(max(self.crash_streak - 1, 0), 30)
                        delay = min(self.max_backoff, self.base_backoff * (2**exponent))
                        self.next_start_at = now + delay
                        self.phase = "waiting_to_restart"
                        self._log(f"child launch failed: {exc!r}; retrying in {delay:.2f}s (no give-up limit)")

                if self.child is not None and self.child.poll() is None:
                    if not self.child_ready:
                        try:
                            self.child_ready = bool(self.health_probe(self.port, self.root, int(self.child.pid)))
                        except Exception as exc:  # probe failures must never kill the supervisor
                            self._log(f"health probe raised {exc!r}; treating child as not ready")
                            self.child_ready = False
                        if self.child_ready:
                            self.phase = "running"
                            self._log(
                                f"child generation {self.child_generation} PID {self.child.pid} is ready and supervised"
                            )
                    self._complete_ready_requests()

                self._write_state()
                self.sleep(self.poll_interval)
        except KeyboardInterrupt:
            # A console Ctrl+C is an explicit manual stop only for a direct `run`.
            _atomic_json_write(
                self.paths.manual_stop,
                {
                    "schema": STATE_SCHEMA,
                    "root": str(self.root),
                    "port": self.port,
                    "requested_at": self.wall_time(),
                    "reason": "supervisor KeyboardInterrupt",
                },
            )
            while not self._stop_from_marker():
                self.sleep(max(self.poll_interval, 0.25))
            return EXIT_OK
        except BaseException as exc:
            self._log(f"FATAL supervisor exception: {exc!r}")
            raise
        finally:
            if guard is not None:
                guard.release()


class SupervisorController:
    """Synchronous CLI-facing controller for one project root."""

    def __init__(
        self,
        root: Path,
        *,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_COMMAND_TIMEOUT,
        popen_factory: Callable[..., Any] = subprocess.Popen,
        wall_time: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        port_inspector: Callable[[int, Path], PortInspection] = inspect_port_owner,
        pid_terminator: Callable[..., bool] = _terminate_exact_pid,
        singleton_probe: Callable[[Path], bool] = _singleton_is_owned,
    ):
        self.root = _resolved(root)
        self.port = int(port)
        self.timeout = float(timeout)
        self.paths = ControlPaths(self.root)
        self.paths.ensure()
        self.popen_factory = popen_factory
        self.wall_time = wall_time
        self.monotonic = monotonic
        self.sleep = sleep
        self.port_inspector = port_inspector
        self.pid_terminator = pid_terminator
        self.singleton_probe = singleton_probe

    def _valid_state(self) -> dict[str, Any] | None:
        state = _read_json(self.paths.state)
        if not state or state.get("schema") != STATE_SCHEMA:
            return None
        if not _same_path(str(state.get("root", "")), self.root):
            return None
        try:
            if int(state.get("port", -1)) != self.port:
                return None
            pid = int(state.get("supervisor_pid", -1))
            heartbeat = float(state.get("heartbeat_at", 0.0))
        except (TypeError, ValueError):
            return None
        if state.get("phase") == "stopped":
            return None
        if self.wall_time() - heartbeat > ACTIVE_HEARTBEAT_MAX_AGE:
            return None
        if heartbeat - self.wall_time() > 30.0:
            return None
        if not _pid_is_alive(pid):
            return None
        if not str(state.get("instance_token", "")):
            return None
        return state

    def _clear_manual_stop(self) -> None:
        _safe_unlink(self.paths.manual_stop)

    def _wait_valid_state(self, timeout: float) -> dict[str, Any] | None:
        deadline = self.monotonic() + max(0.0, timeout)
        while True:
            state = self._valid_state()
            if state is not None:
                return state
            if self.monotonic() >= deadline:
                return None
            self.sleep(0.10)

    def _write_request(self, action: str, instance_token: str, *, request_id: str | None = None) -> str:
        value = request_id or uuid.uuid4().hex
        _safe_unlink(self.paths.acks / f"{value}.json")
        _atomic_json_write(
            self.paths.requests / f"{value}.json",
            {
                "schema": STATE_SCHEMA,
                "request_id": value,
                "action": action,
                "instance_token": instance_token,
                "created_at": self.wall_time(),
                "controller_pid": os.getpid(),
            },
        )
        return value

    def _wait_ack(self, request_id: str, *, timeout: float | None = None) -> dict[str, Any] | None:
        deadline = self.monotonic() + (self.timeout if timeout is None else timeout)
        path = self.paths.acks / f"{request_id}.json"
        while self.monotonic() < deadline:
            ack = _read_json(path)
            if ack and str(ack.get("request_id", "")) == request_id:
                _safe_unlink(path)
                return ack
            self.sleep(0.10)
        return None

    def _replace_verified_legacy(self) -> tuple[bool, str]:
        if self.singleton_probe(self.root):
            return (
                False,
                "the SPB supervisor singleton is active; refusing to treat its child as a legacy server",
            )
        inspection = self.port_inspector(self.port, self.root)
        if inspection.kind == "free":
            return True, "port is free"
        if inspection.kind != "legacy_spb" or not inspection.pid:
            return False, inspection.reason or f"port {self.port} is owned by an unrelated process"
        # Revalidate immediately before the one exact PID mutation to reduce the
        # already-small PID-reuse race.  Never fall back to name/pattern killing.
        confirmation = self.port_inspector(self.port, self.root)
        if confirmation.kind != "legacy_spb" or confirmation.pid != inspection.pid:
            return False, "listener identity changed during validation; refusing to stop anything"
        if self.singleton_probe(self.root):
            return False, "the SPB supervisor became active during validation; refusing to stop its child"
        try:
            stopped = bool(self.pid_terminator(int(inspection.pid), timeout=12.0))
        except TypeError:
            stopped = bool(self.pid_terminator(int(inspection.pid)))
        if not stopped:
            return False, f"verified legacy SPB PID {inspection.pid} could not be stopped"
        deadline = self.monotonic() + 12.0
        while self.monotonic() < deadline:
            if not _port_is_open(self.port):
                return True, f"replaced verified legacy SPB PID {inspection.pid}"
            self.sleep(0.10)
        return False, f"verified legacy SPB PID {inspection.pid} stopped but port {self.port} stayed occupied"

    def _wait_port_free(self, timeout: float) -> bool:
        """Wait read-only for a listener that is already shutting down."""

        deadline = self.monotonic() + max(0.0, timeout)
        while True:
            if not _port_is_open(self.port):
                return True
            if self.monotonic() >= deadline:
                return False
            self.sleep(0.10)

    def _wait_supervisor_released_and_port_free(self, timeout: float) -> bool:
        """Prove both lifecycle owner and listener are gone after a Stop."""

        deadline = self.monotonic() + max(0.0, timeout)
        while True:
            if not self.singleton_probe(self.root) and not _port_is_open(self.port):
                return True
            if self.monotonic() >= deadline:
                return False
            self.sleep(0.10)

    def _launch_supervisor(self, launch_token: str) -> None:
        pythonw = _windowless_python()
        command = [
            str(pythonw),
            str(Path(__file__).resolve()),
            "run",
            "--root",
            str(self.root),
            "--port",
            str(self.port),
            "--launch-token",
            launch_token,
        ]
        kwargs: dict[str, Any] = {
            "cwd": str(self.root),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
            "creationflags": _creation_flags(detached=True),
        }
        if os.name != "nt":
            kwargs["start_new_session"] = True
        self.popen_factory(command, **kwargs)

    def _wait_new_ready(self, launch_token: str) -> dict[str, Any] | None:
        deadline = self.monotonic() + self.timeout
        while self.monotonic() < deadline:
            state = _read_json(self.paths.state)
            if state and state.get("launch_token") == launch_token and self._valid_state() is not None:
                if state.get("child_ready") and state.get("phase") == "running":
                    return state
            self.sleep(0.15)
        return None

    def start(self, *, refresh: bool = False) -> tuple[int, str]:
        self._clear_manual_stop()
        state = self._valid_state()
        if state is None and self.singleton_probe(self.root):
            # state.json is advisory and can be briefly stale/locked.  The
            # process-lifetime singleton is the higher-authority ownership
            # signal: while it is held, this listener is never a legacy target.
            state = self._wait_valid_state(min(self.timeout, 20.0))
            if state is None:
                return (
                    EXIT_BLOCKED,
                    "SPB supervisor is active, but its state heartbeat did not recover in time. "
                    f"No listener was stopped. See {self.paths.lifecycle_log}",
                )
        if state:
            action = "refresh" if refresh else "ensure_started"
            request_id = self._write_request(action, str(state["instance_token"]))
            ack = self._wait_ack(request_id)
            if not ack:
                return EXIT_ERROR, f"Timed out waiting for supervisor to {action} the server. See {self.paths.lifecycle_log}"
            if not ack.get("ok"):
                return EXIT_ERROR, str(ack.get("message", f"Supervisor rejected {action}"))
            label = "refreshed" if refresh else "running"
            return EXIT_OK, f"SPB server {label} in background: {ack.get('message')}."

        safe, detail = self._replace_verified_legacy()
        if not safe:
            return EXIT_BLOCKED, f"Cannot start supervisor safely: {detail}. Nothing was stopped."

        launch_token = uuid.uuid4().hex
        try:
            self._launch_supervisor(launch_token)
        except OSError as exc:
            return EXIT_ERROR, f"Could not launch background supervisor: {exc}"
        ready = self._wait_new_ready(launch_token)
        if not ready:
            state = _read_json(self.paths.state) or {}
            return (
                EXIT_ERROR,
                f"Background supervisor did not report a ready server within {self.timeout:.0f}s "
                f"(phase={state.get('phase', 'unknown')}). See {self.paths.lifecycle_log}",
            )
        verb = "refreshed" if refresh else "started"
        return (
            EXIT_OK,
            f"SPB server {verb} in background and is supervised (supervisor PID {ready.get('supervisor_pid')}, "
            f"server PID {ready.get('child_pid')}, port {self.port}).",
        )

    def stop(self) -> tuple[int, str]:
        state = self._valid_state()
        request_id = uuid.uuid4().hex
        # This durable intent is deliberately committed before any request or
        # process termination.  If the controller dies now, the supervisor still
        # observes the marker and remains down.
        _atomic_json_write(
            self.paths.manual_stop,
            {
                "schema": STATE_SCHEMA,
                "root": str(self.root),
                "port": self.port,
                "request_id": request_id,
                "requested_at": self.wall_time(),
                "reason": "manual stop command",
                "controller_pid": os.getpid(),
            },
        )
        if state:
            self._write_request("stop", str(state["instance_token"]), request_id=request_id)
            ack = self._wait_ack(request_id, timeout=min(self.timeout, 30.0))
            if not ack:
                return EXIT_ERROR, f"Manual stop is set, but supervisor did not acknowledge in time. See {self.paths.lifecycle_log}"
            if not ack.get("ok"):
                return EXIT_ERROR, f"Manual stop is set; supervisor response: {ack.get('message')}"
            deadline = self.monotonic() + 8.0
            while self.monotonic() < deadline and self._valid_state() is not None:
                self.sleep(0.10)
            return EXIT_OK, "SPB server stopped manually. Automatic restart remains disabled until Start or Refresh."

        if self.singleton_probe(self.root):
            # The durable marker already contains the request id.  A supervisor
            # whose state file was transiently stale can honor and acknowledge
            # it without the controller touching its child.
            ack = self._wait_ack(request_id, timeout=min(self.timeout, 30.0))
            if ack:
                if ack.get("ok"):
                    return EXIT_OK, "SPB server stopped manually. Automatic restart remains disabled until Start or Refresh."
                return EXIT_ERROR, f"Manual stop is set; supervisor response: {ack.get('message')}"
            # A free port alone is not proof: a stubborn owned child may still
            # be booting.  Success without an ACK requires both the singleton
            # owner and its listener to be gone.
            if self._wait_supervisor_released_and_port_free(min(self.timeout, 12.0)):
                return EXIT_OK, "SPB server stopped manually. Automatic restart remains disabled until Start or Refresh."
            return (
                EXIT_ERROR,
                f"Manual stop is set, but the active supervisor did not finish shutdown in time. See {self.paths.lifecycle_log}",
            )

        inspection = self.port_inspector(self.port, self.root)
        if inspection.kind == "legacy_spb" and inspection.pid:
            confirmation = self.port_inspector(self.port, self.root)
            if confirmation.kind != "legacy_spb" or confirmation.pid != inspection.pid:
                return EXIT_BLOCKED, "Manual stop is set, but listener identity changed; nothing was terminated."
            try:
                stopped = bool(self.pid_terminator(int(inspection.pid), timeout=12.0))
            except TypeError:
                stopped = bool(self.pid_terminator(int(inspection.pid)))
            if not stopped:
                return EXIT_ERROR, f"Manual stop is set, but verified legacy SPB PID {inspection.pid} could not be stopped."
            return EXIT_OK, f"Verified legacy SPB PID {inspection.pid} stopped. Automatic restart remains disabled."
        if inspection.kind == "blocked":
            # The supervisor can commit phase=stopped and close `/build-check`
            # just before Windows releases its listening socket.  In that small
            # interval the read-only identity probe correctly says "blocked",
            # even though the durable stop is succeeding.  Let socket teardown
            # settle before classifying a persistent listener as unrelated.
            if self._wait_port_free(min(self.timeout, 12.0)):
                return (
                    EXIT_OK,
                    "SPB server stopped manually. Automatic restart remains disabled until Start or Refresh.",
                )
            return EXIT_BLOCKED, f"Manual stop is set. {inspection.reason}; unrelated listener was not touched."
        return EXIT_OK, "SPB server is stopped. Automatic restart remains disabled until Start or Refresh."

    def status(self) -> tuple[int, str]:
        state = self._valid_state()
        if state:
            ready = "READY" if state.get("child_ready") else "STARTING"
            return (
                EXIT_OK,
                f"{ready}: supervisor PID {state.get('supervisor_pid')}, server PID {state.get('child_pid')}, "
                f"phase={state.get('phase')}, restarts={state.get('restart_count')}, port={self.port}. "
                f"Logs: {self.paths.lifecycle_log} and {self.paths.child_log}",
            )
        if self.paths.manual_stop.exists():
            return EXIT_STOPPED, "STOPPED MANUALLY: automatic restart is disabled until Start or Refresh."
        inspection = self.port_inspector(self.port, self.root)
        if inspection.kind == "legacy_spb":
            return EXIT_STOPPED, f"RUNNING UNSUPERVISED: verified SPB server PID {inspection.pid} is on port {self.port}."
        if inspection.kind == "blocked":
            return EXIT_BLOCKED, f"BLOCKED: {inspection.reason}. No process was touched."
        return EXIT_STOPPED, "STOPPED: no SPB supervisor or listener is running."


@dataclass
class _LogCursor:
    identity: tuple[int, int, int] | None = None
    offset: int = 0
    partial: bytes = b""
    initialized: bool = False


class SupervisorLogViewer:
    """Read-only, rotation-aware follower for supervisor and child logs."""

    def __init__(
        self,
        paths: ControlPaths,
        *,
        emit: Callable[[str], None] = print,
        tail_lines: int = 50,
        tail_bytes: int = 64 * 1024,
        max_follow_bytes: int = 256 * 1024,
    ):
        self.paths = paths
        self.emit = emit
        self.tail_lines = max(0, int(tail_lines))
        self.tail_bytes = max(1024, int(tail_bytes))
        self.max_follow_bytes = max(4096, int(max_follow_bytes))
        self.sources = (
            ("SUPERVISOR", self.paths.lifecycle_log),
            ("SERVER", self.paths.child_log),
        )
        self.cursors = {label: _LogCursor() for label, _path in self.sources}
        self._state_signature: tuple[Any, ...] | None = None
        self._warned: set[tuple[str, str]] = set()

    @staticmethod
    def _file_identity(stat_result: os.stat_result) -> tuple[int, int, int]:
        inode = int(getattr(stat_result, "st_ino", 0))
        # Windows exposes a stable file index as st_ino.  Keep creation time as
        # a fallback for filesystems that report zero so replacement is still
        # distinguishable from append.
        fallback = 0 if inode else int(getattr(stat_result, "st_ctime_ns", 0))
        return int(stat_result.st_dev), inode, fallback

    @staticmethod
    def _candidate_paths(active: Path) -> list[Path]:
        # Oldest retained backup through the active file.  CappedRotatingLog
        # currently keeps three; harmless missing paths are skipped.
        return [active.with_name(f"{active.name}.{index}") for index in (3, 2, 1)] + [active]

    def _snapshots(self, active: Path) -> list[tuple[Path, tuple[int, int, int], int]]:
        snapshots: list[tuple[Path, tuple[int, int, int], int]] = []
        for path in self._candidate_paths(active):
            try:
                with path.open("rb") as handle:
                    stat_result = os.fstat(handle.fileno())
            except (FileNotFoundError, PermissionError, OSError):
                continue
            snapshots.append((path, self._file_identity(stat_result), int(stat_result.st_size)))
        return snapshots

    def _emit_line(self, label: str, raw: bytes) -> None:
        line = raw.rstrip(b"\r").decode("utf-8", errors="replace")
        self.emit(f"[{label}] {line}")

    def _consume(self, label: str, cursor: _LogCursor, data: bytes) -> None:
        chunks = (cursor.partial + data).split(b"\n")
        cursor.partial = chunks.pop()
        for raw in chunks:
            self._emit_line(label, raw)

    def _read_exact(
        self,
        path: Path,
        identity: tuple[int, int, int],
        offset: int,
        *,
        label: str,
    ) -> tuple[bytes, int] | None:
        try:
            with path.open("rb") as handle:
                stat_result = os.fstat(handle.fileno())
                if self._file_identity(stat_result) != identity:
                    return None
                size = int(stat_result.st_size)
                start = max(0, min(int(offset), size))
                if size - start > self.max_follow_bytes:
                    self.emit(
                        f"[VIEWER] {label} produced more than {self.max_follow_bytes} unread bytes; "
                        "showing the newest bounded portion."
                    )
                    start = max(0, size - self.max_follow_bytes)
                handle.seek(start)
                data = handle.read(self.max_follow_bytes)
                end = handle.tell()
        except (FileNotFoundError, PermissionError, OSError):
            return None
        if start > offset and b"\n" in data:
            data = data.split(b"\n", 1)[1]
        return data, end

    def _prime_source(self, label: str, active: Path, cursor: _LogCursor) -> None:
        snapshots = self._snapshots(active)
        if not snapshots:
            return
        path, identity, size = snapshots[-1]
        start = max(0, size - self.tail_bytes)
        result = self._read_exact(path, identity, start, label=label)
        if result is None:
            return
        data, end = result
        if start > 0 and b"\n" in data:
            data = data.split(b"\n", 1)[1]
        parts = data.split(b"\n")
        partial = parts.pop()
        for raw in parts[-self.tail_lines :]:
            self._emit_line(label, raw)
        cursor.identity = identity
        cursor.offset = end
        cursor.partial = partial
        cursor.initialized = True

    def _poll_source(self, label: str, active: Path, cursor: _LogCursor) -> None:
        snapshots = self._snapshots(active)
        if not snapshots:
            return
        if not cursor.initialized or cursor.identity is None:
            self._prime_source(label, active, cursor)
            return

        match_index = next(
            (index for index, (_path, identity, _size) in enumerate(snapshots) if identity == cursor.identity),
            None,
        )
        if match_index is None:
            warning = (label, "rotation_gap")
            if warning not in self._warned:
                self.emit(f"[VIEWER] {label} rotations outran the reader; resuming from bounded recent history.")
                self._warned.add(warning)
            cursor.identity = None
            cursor.offset = 0
            cursor.partial = b""
            cursor.initialized = False
            self._prime_source(label, active, cursor)
            return

        self._warned.discard((label, "rotation_gap"))
        for index in range(match_index, len(snapshots)):
            path, identity, size = snapshots[index]
            start = cursor.offset if index == match_index else 0
            if index == match_index and size < start:
                self.emit(f"[VIEWER] {label} log was truncated; following again from byte zero.")
                start = 0
                cursor.partial = b""
            result = self._read_exact(path, identity, start, label=label)
            if result is None:
                return
            data, end = result
            self._consume(label, cursor, data)
            cursor.identity = identity
            cursor.offset = end

    def _poll_state(self) -> None:
        state = _read_json(self.paths.state)
        if not state:
            signature: tuple[Any, ...] = ("unavailable",)
            message = "[STATE] Supervisor state is not currently available; log following continues."
        else:
            signature = (
                state.get("phase"),
                state.get("supervisor_pid"),
                state.get("child_pid"),
                state.get("child_generation"),
                state.get("restart_count"),
                state.get("last_exit_code"),
            )
            message = (
                f"[STATE] phase={state.get('phase')} supervisor={state.get('supervisor_pid')} "
                f"server={state.get('child_pid')} generation={state.get('child_generation')} "
                f"restarts={state.get('restart_count')} last_exit={state.get('last_exit_code')}"
            )
        if signature != self._state_signature:
            self.emit(message)
            self._state_signature = signature

    def prime(self) -> None:
        self._poll_state()
        for label, path in self.sources:
            self._prime_source(label, path, self.cursors[label])

    def poll_once(self) -> None:
        self._poll_state()
        for label, path in self.sources:
            self._poll_source(label, path, self.cursors[label])

    def run(self, stop_event: threading.Event, *, interval: float = 0.20, prime: bool = True) -> None:
        if prime:
            self.prime()
        while not stop_event.wait(max(0.05, float(interval))):
            self.poll_once()


def _configure_console_output() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except (AttributeError, OSError):
        pass


def _print_viewer_banner(paths: ControlPaths) -> None:
    print("=" * 68)
    print("SPB LIVE SERVER CONSOLE")
    print(f"Supervisor events: {paths.lifecycle_log}")
    print(f"Server output:     {paths.child_log}")
    print("Close this window or press Ctrl+C to detach the viewer.")
    print("The supervised SPB server keeps running after this viewer closes.")
    print("Use SPB_STOP_SERVER.bat only when you want the server to stay down.")
    print("=" * 68)


def _follow_logs_only(paths: ControlPaths) -> int:
    _configure_console_output()
    _print_viewer_banner(paths)
    stop_event = threading.Event()
    viewer = SupervisorLogViewer(paths)
    try:
        viewer.run(stop_event)
    except KeyboardInterrupt:
        print("\n[VIEWER] Detached. SPB remains supervised in the background.")
    finally:
        stop_event.set()
    return EXIT_OK


def _run_control_with_logs(controller: SupervisorController, *, refresh: bool) -> int:
    _configure_console_output()
    _print_viewer_banner(controller.paths)
    stop_event = threading.Event()
    viewer = SupervisorLogViewer(controller.paths)
    # Establish exact EOFs before Refresh can rotate/append either log, so the
    # same terminal visibly captures the entire startup transition.
    viewer.prime()
    pump = threading.Thread(
        target=viewer.run,
        args=(stop_event,),
        kwargs={"prime": False},
        name="spb-visible-log-viewer",
        daemon=True,
    )
    pump.start()
    code = EXIT_OK
    try:
        try:
            code, message = controller.start(refresh=refresh)
            prefix = "CONTROL OK" if code == EXIT_OK else "CONTROL ERROR"
            print(f"\n[{prefix}] {message}")
        except Exception:
            code = EXIT_ERROR
            print("\n[CONTROL ERROR] Unexpected controller exception:")
            traceback.print_exc()
        print("[VIEWER] Live logs will remain here until you close this window or press Ctrl+C.")
        while True:
            time.sleep(3600.0)
    except KeyboardInterrupt:
        print("\n[VIEWER] Detached. SPB remains supervised in the background.")
    finally:
        stop_event.set()
        pump.join(timeout=2.0)
    return code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shokker Paint Booth background server supervisor")
    parser.add_argument("command", choices=("start", "refresh", "stop", "status", "logs", "run"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=argparse.SUPPRESS)
    parser.add_argument("--launch-token", default="", help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_COMMAND_TIMEOUT, help=argparse.SUPPRESS)
    parser.add_argument("--follow", action="store_true", help="keep this terminal open and stream SPB logs")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    root = _resolved(args.root)
    if args.command == "run":
        return Supervisor(root, port=args.port, launch_token=args.launch_token).run_forever()
    controller = SupervisorController(root, port=args.port, timeout=args.timeout)
    if args.command == "logs":
        return _follow_logs_only(controller.paths)
    if args.follow and args.command in {"start", "refresh"}:
        return _run_control_with_logs(controller, refresh=args.command == "refresh")
    if args.command == "start":
        code, message = controller.start(refresh=False)
    elif args.command == "refresh":
        code, message = controller.start(refresh=True)
    elif args.command == "stop":
        code, message = controller.stop()
    else:
        code, message = controller.status()
    print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
