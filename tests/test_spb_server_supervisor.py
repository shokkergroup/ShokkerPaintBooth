from __future__ import annotations

import io
import json
import os
import threading
import time
import uuid
from pathlib import Path

import pytest

import spb_server_supervisor as supervisor_module
from spb_server_supervisor import (
    CappedRotatingLog,
    ControlPaths,
    PortInspection,
    STATE_SCHEMA,
    Supervisor,
    SupervisorController,
    SupervisorLogViewer,
    _atomic_json_write,
    _read_json,
)


@pytest.fixture
def supervisor_root(tmp_path, request):
    # conftest's Windows runtime harness uses a shared bounded base directory;
    # include a UUID so parallel agent/test processes never share state files.
    root = tmp_path / f"{request.node.name}-{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    return root


def test_foreign_installation_reports_version_folder_and_recovery_without_process_access(monkeypatch, tmp_path):
    monkeypatch.setattr(supervisor_module, '_port_is_open', lambda port: True)
    monkeypatch.setattr(supervisor_module, '_http_build_check', lambda port: {
        'status': 'running', 'pid': 46704, 'port': 59876, 'version': '8.0.4-beta',
        'server_dir': str(tmp_path / 'old-installed-app'),
    })
    monkeypatch.setattr(supervisor_module, '_windows_listener_pids',
                        lambda port: pytest.fail('A foreign root must not reach process takeover checks'))
    result = supervisor_module.inspect_port_owner(59876, tmp_path / 'current-project')
    assert result.kind == 'blocked'
    for text in ['8.0.4-beta', 'old-installed-app', 'current-project', '46704', 'SPB_FRESH_START']:
        assert text in result.reason


class FakeProcess:
    def __init__(self, pid: int, *, marker_path: Path | None = None):
        self.pid = pid
        self.returncode: int | None = None
        self.stdout = io.StringIO("fake child booted\n")
        self.terminate_calls = 0
        self.kill_calls = 0
        self.marker_path = marker_path
        self.marker_seen_at_terminate = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminate_calls += 1
        if self.marker_path is not None:
            self.marker_seen_at_terminate = self.marker_path.exists()
        self.returncode = -15

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            raise AssertionError("fake wait called before terminate/exit")
        return self.returncode

    def exit(self, code: int):
        self.returncode = code


class StubbornProcess(FakeProcess):
    """A live child that rejects both graceful and forced termination."""

    def terminate(self):
        self.terminate_calls += 1
        raise OSError("terminate refused")

    def kill(self):
        self.kill_calls += 1
        raise OSError("kill refused")


class FakePopenFactory:
    def __init__(self, marker_path: Path | None = None):
        self.marker_path = marker_path
        self.processes: list[FakeProcess] = []
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, command, **kwargs):
        process = FakeProcess(41000 + len(self.processes), marker_path=self.marker_path)
        self.processes.append(process)
        self.calls.append((list(command), dict(kwargs)))
        return process


def wait_until(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError("condition did not become true before timeout")


def test_production_command_timeout_covers_observed_cold_boot():
    # The live 2026-09-01 registry rebuild needed 201.21 seconds before both
    # listeners were ready.  Keep the production wait above that cold-boot case.
    assert supervisor_module.DEFAULT_COMMAND_TIMEOUT >= 300.0


def write_request(paths: ControlPaths, instance_token: str, action: str) -> str:
    request_id = uuid.uuid4().hex
    _atomic_json_write(
        paths.requests / f"{request_id}.json",
        {
            "schema": STATE_SCHEMA,
            "request_id": request_id,
            "action": action,
            "instance_token": instance_token,
            "created_at": time.time(),
        },
    )
    return request_id


def write_manual_stop(paths: ControlPaths, instance_token: str = "") -> str:
    request_id = uuid.uuid4().hex
    _atomic_json_write(
        paths.manual_stop,
        {
            "schema": STATE_SCHEMA,
            "root": str(paths.root),
            "port": 63001,
            "request_id": request_id,
            "instance_token": instance_token,
            "requested_at": time.time(),
            "reason": "unit test stop",
        },
    )
    return request_id


def make_supervisor(tmp_path: Path, factory: FakePopenFactory) -> Supervisor:
    # The repository's Windows runtime-harness fixture intentionally reuses one
    # bounded directory, so isolate control state explicitly between tests.
    paths = ControlPaths(tmp_path.resolve())
    paths.ensure()
    for item in (paths.manual_stop, paths.state):
        item.unlink(missing_ok=True)
    for directory in (paths.requests, paths.acks):
        for item in directory.glob("*.json"):
            item.unlink()
    (tmp_path / "server_v5.py").write_text("# fake entry point\n", encoding="utf-8")
    return Supervisor(
        tmp_path,
        port=63001,
        child_command=["fake-python", str(tmp_path / "server_v5.py")],
        popen_factory=factory,
        health_probe=lambda port, root, pid: True,
        poll_interval=0.01,
        base_backoff=0.01,
        max_backoff=0.04,
        stable_window=1.0,
        log_bytes=4096,
        log_backups=2,
    )


def start_in_thread(supervisor: Supervisor):
    result: list[int] = []
    thread = threading.Thread(
        target=lambda: result.append(supervisor.run_forever(acquire_singleton=False)),
        name="supervisor-unit-test",
        daemon=True,
    )
    thread.start()
    wait_until(lambda: len(getattr(supervisor.popen_factory, "processes", [])) >= 1)
    wait_until(lambda: (_read_json(supervisor.paths.state) or {}).get("child_ready") is True)
    return thread, result


def stop_test_supervisor(supervisor: Supervisor, thread: threading.Thread):
    if thread.is_alive():
        write_manual_stop(supervisor.paths, supervisor.instance_token)
        thread.join(timeout=3.0)
    assert not thread.is_alive()


def test_unintentional_exit_code_zero_always_restarts_then_manual_stop_stays_down(supervisor_root):
    tmp_path = supervisor_root
    paths = ControlPaths(tmp_path.resolve())
    factory = FakePopenFactory(paths.manual_stop)
    supervisor = make_supervisor(tmp_path, factory)
    thread, result = start_in_thread(supervisor)
    try:
        first = factory.processes[0]
        first.exit(0)
        wait_until(lambda: len(factory.processes) == 2)
        second = factory.processes[1]
        wait_until(lambda: (_read_json(supervisor.paths.state) or {}).get("child_pid") == second.pid)

        request_id = write_manual_stop(supervisor.paths, supervisor.instance_token)
        thread.join(timeout=3.0)

        assert not thread.is_alive()
        assert result == [0]
        assert len(factory.processes) == 2
        assert second.terminate_calls == 1
        assert second.marker_seen_at_terminate is True
        ack = _read_json(supervisor.paths.acks / f"{request_id}.json")
        assert ack and ack["ok"] is True
        assert (_read_json(supervisor.paths.state) or {})["phase"] == "stopped"
    finally:
        stop_test_supervisor(supervisor, thread)


def test_refresh_replaces_exactly_one_generation_and_keeps_supervisor_alive(supervisor_root):
    tmp_path = supervisor_root
    paths = ControlPaths(tmp_path.resolve())
    factory = FakePopenFactory(paths.manual_stop)
    supervisor = make_supervisor(tmp_path, factory)
    thread, _result = start_in_thread(supervisor)
    try:
        first = factory.processes[0]
        request_id = write_request(supervisor.paths, supervisor.instance_token, "refresh")
        ack_path = supervisor.paths.acks / f"{request_id}.json"
        ack = wait_until(lambda: _read_json(ack_path))

        assert ack["ok"] is True
        assert ack["action"] == "refresh"
        assert ack["child_generation"] == 2
        assert len(factory.processes) == 2
        assert first.terminate_calls == 1
        assert factory.processes[1].poll() is None
        assert thread.is_alive()
        assert (_read_json(supervisor.paths.state) or {})["phase"] == "running"
    finally:
        stop_test_supervisor(supervisor, thread)


def test_termination_failure_retains_exact_child_ownership(supervisor_root):
    factory = FakePopenFactory()
    supervisor = make_supervisor(supervisor_root, factory)
    stubborn = StubbornProcess(47771)
    supervisor.child = stubborn
    supervisor.child_ready = True

    stopped = supervisor._terminate_child("unit-test refusal")

    assert stopped is False
    assert supervisor.child is stubborn
    assert supervisor.child_ready is True
    assert stubborn.terminate_calls == 1
    assert stubborn.kill_calls == 1


def test_refresh_failure_never_forgets_child_or_queues_duplicate(supervisor_root):
    factory = FakePopenFactory()
    supervisor = make_supervisor(supervisor_root, factory)
    stubborn = StubbornProcess(47772)
    supervisor.child = stubborn
    supervisor.child_ready = True
    supervisor.child_generation = 4
    request_id = uuid.uuid4().hex

    stop_requested = supervisor._handle_request(
        {
            "request_id": request_id,
            "action": "refresh",
            "instance_token": supervisor.instance_token,
        }
    )

    ack = _read_json(supervisor.paths.acks / f"{request_id}.json")
    assert stop_requested is False
    assert ack and ack["ok"] is False
    assert "refresh aborted" in ack["message"]
    assert supervisor.child is stubborn
    assert supervisor.child_generation == 4
    assert request_id not in supervisor._pending
    assert factory.processes == []
    assert supervisor.phase == "running"


def test_manual_stop_failure_stays_supervised_and_does_not_ack_success(supervisor_root):
    factory = FakePopenFactory()
    supervisor = make_supervisor(supervisor_root, factory)
    stubborn = StubbornProcess(47773)
    supervisor.child = stubborn
    supervisor.child_ready = True
    request_id = write_manual_stop(supervisor.paths, supervisor.instance_token)

    stopped = supervisor._stop_from_marker()

    ack = _read_json(supervisor.paths.acks / f"{request_id}.json")
    assert stopped is False
    assert ack and ack["ok"] is False
    assert "still alive" in ack["message"]
    assert supervisor.child is stubborn
    assert supervisor.paths.manual_stop.exists()
    assert supervisor.phase == "stop_failed"


def test_control_file_io_failure_does_not_raise_or_drop_child(supervisor_root, monkeypatch):
    factory = FakePopenFactory()
    supervisor = make_supervisor(supervisor_root, factory)
    child = FakeProcess(47774)
    supervisor.child = child
    supervisor.child_ready = True
    monkeypatch.setattr(
        supervisor_module,
        "_atomic_json_write",
        lambda path, value: (_ for _ in ()).throw(OSError("disk temporarily unavailable")),
    )

    assert supervisor._write_state(force=True) is False
    assert supervisor._write_ack("io-failure", "status", ok=True, message="test") is False
    assert supervisor.child is child
    assert child.poll() is None


def test_controller_refresh_and_stop_round_trip_against_fake_supervisor(supervisor_root):
    tmp_path = supervisor_root
    paths = ControlPaths(tmp_path.resolve())
    factory = FakePopenFactory(paths.manual_stop)
    supervisor = make_supervisor(tmp_path, factory)
    thread, _result = start_in_thread(supervisor)
    controller = SupervisorController(
        tmp_path,
        port=63001,
        timeout=2.0,
        singleton_probe=lambda root: True,
        port_inspector=lambda port, root: pytest.fail("active controller must not inspect or mutate the port"),
        pid_terminator=lambda pid, timeout=0: pytest.fail("active controller must not terminate by PID"),
    )
    try:
        refresh_code, refresh_message = controller.start(refresh=True)
        assert refresh_code == supervisor_module.EXIT_OK
        assert "refreshed" in refresh_message
        assert len(factory.processes) == 2

        stop_code, stop_message = controller.stop()
        assert stop_code == supervisor_module.EXIT_OK
        assert "stopped manually" in stop_message
        thread.join(timeout=3.0)
        assert not thread.is_alive()
        assert factory.processes[1].marker_seen_at_terminate is True
    finally:
        stop_test_supervisor(supervisor, thread)


def test_stop_marker_is_committed_before_owned_child_termination(supervisor_root):
    tmp_path = supervisor_root
    paths = ControlPaths(tmp_path.resolve())
    factory = FakePopenFactory(paths.manual_stop)
    supervisor = make_supervisor(tmp_path, factory)
    thread, _result = start_in_thread(supervisor)
    try:
        request_id = write_manual_stop(supervisor.paths, supervisor.instance_token)
        # The stop request may be created after the durable marker; the marker's
        # request id is sufficient for acknowledgement even across that race.
        write_request(supervisor.paths, supervisor.instance_token, "stop")
        thread.join(timeout=3.0)

        assert not thread.is_alive()
        assert factory.processes[0].marker_seen_at_terminate is True
        assert (_read_json(supervisor.paths.acks / f"{request_id}.json") or {})["ok"] is True
    finally:
        stop_test_supervisor(supervisor, thread)


@pytest.mark.parametrize('warm_opt_out', [None, '0', '1'])
def test_child_environment_and_working_directory_are_explicit(supervisor_root, monkeypatch, warm_opt_out):
    if warm_opt_out is None:
        monkeypatch.delenv('SPB_NO_BOOT_SWATCH_WARM', raising=False)
    else:
        monkeypatch.setenv('SPB_NO_BOOT_SWATCH_WARM', warm_opt_out)
    tmp_path = supervisor_root
    paths = ControlPaths(tmp_path.resolve())
    factory = FakePopenFactory(paths.manual_stop)
    supervisor = make_supervisor(tmp_path, factory)
    thread, _result = start_in_thread(supervisor)
    try:
        command, kwargs = factory.calls[0]
        assert command[-1] == str(tmp_path / "server_v5.py")
        assert Path(kwargs["cwd"]) == tmp_path.resolve()
        assert kwargs["env"]["SHOKKER_PORT"] == "63001"
        assert kwargs["env"]["PYTHONHASHSEED"] == "0"
        assert kwargs["env"].get("SPB_NO_BOOT_SWATCH_WARM") == warm_opt_out
        assert kwargs["env"]["PYTHONUNBUFFERED"] == "1"
        assert kwargs["env"]["SPB_SUPERVISOR_INSTANCE"] == supervisor.instance_token
    finally:
        stop_test_supervisor(supervisor, thread)


def test_crash_loop_backoff_is_bounded_and_never_gives_up(supervisor_root):
    tmp_path = supervisor_root
    paths = ControlPaths(tmp_path.resolve())
    factory = FakePopenFactory(paths.manual_stop)
    supervisor = make_supervisor(tmp_path, factory)
    thread, _result = start_in_thread(supervisor)
    try:
        for expected_count in range(2, 7):
            factory.processes[-1].exit(17)
            wait_until(lambda: len(factory.processes) >= expected_count, timeout=3.0)
        assert len(factory.processes) == 6
        assert supervisor.restart_count >= 5
        assert supervisor.crash_streak >= 1
        assert thread.is_alive()
    finally:
        stop_test_supervisor(supervisor, thread)


def test_rotating_logs_remain_hard_capped(supervisor_root):
    tmp_path = supervisor_root
    path = tmp_path / "bounded.log"
    log = CappedRotatingLog(path, max_bytes=160, backups=2)
    for index in range(30):
        log.line(f"entry {index}: " + ("x" * 65), now=1_788_300_000 + index)

    files = sorted(tmp_path.glob("bounded.log*"))
    assert 1 <= len(files) <= 3
    assert all(item.stat().st_size <= 160 for item in files)
    assert path.exists()


def test_log_rotation_retries_transient_viewer_collision(supervisor_root, monkeypatch):
    path = supervisor_root / "collision.log"
    log = CappedRotatingLog(path, max_bytes=160, backups=2)
    log.line("x" * 100, now=1_788_300_000)
    original_rotate = log._rotate
    attempts = 0

    def flaky_rotate():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("viewer held a short read")
        original_rotate()

    monkeypatch.setattr(log, "_rotate", flaky_rotate)
    log.line("y" * 100, now=1_788_300_001)

    assert attempts == 2
    assert path.exists()
    assert path.with_name("collision.log.1").exists()


def test_visible_log_viewer_primes_and_follows_both_logs_once(supervisor_root):
    paths = ControlPaths(supervisor_root.resolve())
    paths.ensure()
    paths.lifecycle_log.write_text("old lifecycle\n", encoding="utf-8")
    paths.child_log.write_text("old server\n", encoding="utf-8")
    emitted: list[str] = []
    viewer = SupervisorLogViewer(paths, emit=emitted.append, tail_lines=10)

    viewer.prime()
    with paths.lifecycle_log.open("ab") as handle:
        handle.write(b"new lifecycle\n")
    with paths.child_log.open("ab") as handle:
        handle.write(b"new server\n")
    viewer.poll_once()
    viewer.poll_once()

    assert emitted.count("[SUPERVISOR] old lifecycle") == 1
    assert emitted.count("[SERVER] old server") == 1
    assert emitted.count("[SUPERVISOR] new lifecycle") == 1
    assert emitted.count("[SERVER] new server") == 1


def test_visible_log_viewer_discovers_files_created_after_attach(supervisor_root):
    paths = ControlPaths(supervisor_root.resolve())
    paths.ensure()
    emitted: list[str] = []
    viewer = SupervisorLogViewer(paths, emit=emitted.append, tail_lines=10)

    viewer.prime()
    paths.child_log.write_text("late server line\n", encoding="utf-8")
    viewer.poll_once()

    assert "[SERVER] late server line" in emitted


def test_visible_log_viewer_drains_rotated_file_then_new_active_in_order(supervisor_root):
    paths = ControlPaths(supervisor_root.resolve())
    paths.ensure()
    paths.lifecycle_log.write_text("already shown\n", encoding="utf-8")
    emitted: list[str] = []
    viewer = SupervisorLogViewer(paths, emit=emitted.append, tail_lines=10)
    viewer.prime()
    emitted.clear()

    with paths.lifecycle_log.open("ab") as handle:
        handle.write(b"unread before rotate\n")
    os.replace(paths.lifecycle_log, paths.lifecycle_log.with_name("lifecycle.log.1"))
    paths.lifecycle_log.write_text("new active\n", encoding="utf-8")
    viewer.poll_once()
    viewer.poll_once()

    lines = [line for line in emitted if line.startswith("[SUPERVISOR]")]
    assert lines == ["[SUPERVISOR] unread before rotate", "[SUPERVISOR] new active"]


def test_visible_log_viewer_reassembles_split_utf8_line(supervisor_root):
    paths = ControlPaths(supervisor_root.resolve())
    paths.ensure()
    paths.child_log.write_bytes(b"")
    emitted: list[str] = []
    viewer = SupervisorLogViewer(paths, emit=emitted.append, tail_lines=10)
    viewer.prime()

    encoded = "split euro: €".encode("utf-8")
    with paths.child_log.open("ab") as handle:
        handle.write(encoded[:-1])
    viewer.poll_once()
    assert not any("split euro" in line for line in emitted)
    with paths.child_log.open("ab") as handle:
        handle.write(encoded[-1:] + b"\n")
    viewer.poll_once()

    assert "[SERVER] split euro: €" in emitted
    assert not paths.manual_stop.exists()
    assert list(paths.requests.glob("*.json")) == []


def test_follow_banner_and_controller_error_are_visible_before_wait(supervisor_root, monkeypatch, capsys):
    paths = ControlPaths(supervisor_root.resolve())
    paths.ensure()
    observed: dict[str, str] = {}

    class ImmediateViewer:
        def __init__(self, _paths):
            pass

        def prime(self):
            pass

        def run(self, _stop_event, *, prime=True):
            pass

    class FailingController:
        def __init__(self):
            self.paths = paths

        def start(self, *, refresh=False):
            observed["before_start"] = capsys.readouterr().out
            raise RuntimeError("synthetic controller failure")

    def interrupt_wait(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(supervisor_module, "SupervisorLogViewer", ImmediateViewer)
    monkeypatch.setattr(supervisor_module.time, "sleep", interrupt_wait)

    code = supervisor_module._run_control_with_logs(FailingController(), refresh=True)
    captured = capsys.readouterr()

    assert "SPB LIVE SERVER CONSOLE" in observed["before_start"]
    assert "[CONTROL ERROR] Unexpected controller exception:" in captured.out
    assert "Live logs will remain here" in captured.out
    assert "Detached. SPB remains supervised" in captured.out
    assert "synthetic controller failure" in captured.err
    assert code == supervisor_module.EXIT_ERROR
    assert not paths.manual_stop.exists()


def test_controller_revalidates_exact_legacy_pid_before_termination(supervisor_root):
    tmp_path = supervisor_root
    inspections = iter(
        [
            PortInspection("legacy_spb", pid=1234, reason="verified"),
            PortInspection("blocked", pid=5678, reason="identity changed"),
        ]
    )
    terminated: list[int] = []
    controller = SupervisorController(
        tmp_path,
        port=63001,
        timeout=0.2,
        port_inspector=lambda port, root: next(inspections),
        pid_terminator=lambda pid, timeout=0: terminated.append(pid) or True,
    )

    safe, message = controller._replace_verified_legacy()

    assert safe is False
    assert "identity changed" in message
    assert terminated == []


def test_controller_never_terminates_a_blocked_unrelated_owner(supervisor_root):
    tmp_path = supervisor_root
    terminated: list[int] = []
    controller = SupervisorController(
        tmp_path,
        port=63001,
        timeout=0.2,
        port_inspector=lambda port, root: PortInspection("blocked", pid=9999, reason="different project root"),
        pid_terminator=lambda pid, timeout=0: terminated.append(pid) or True,
    )

    code, message = controller.start(refresh=True)

    assert code == supervisor_module.EXIT_BLOCKED
    assert "Nothing was stopped" in message
    assert terminated == []


def test_refresh_never_downgrades_a_mutex_owned_child_to_legacy(supervisor_root):
    tmp_path = supervisor_root
    inspected: list[int] = []
    terminated: list[int] = []
    controller = SupervisorController(
        tmp_path,
        port=63001,
        timeout=0.02,
        sleep=lambda seconds: time.sleep(0.001),
        singleton_probe=lambda root: True,
        port_inspector=lambda port, root: inspected.append(port) or PortInspection(
            "legacy_spb",
            pid=79088,
            reason="would be unsafe to downgrade",
        ),
        pid_terminator=lambda pid, timeout=0: terminated.append(pid) or True,
    )

    code, message = controller.start(refresh=True)

    assert code == supervisor_module.EXIT_BLOCKED
    assert "supervisor is active" in message
    assert "No listener was stopped" in message
    assert inspected == []
    assert terminated == []


def test_stop_waits_for_transient_socket_teardown_before_reporting_success(supervisor_root, monkeypatch):
    tmp_path = supervisor_root
    probes = iter((True, True, False))
    terminated: list[int] = []
    monkeypatch.setattr(supervisor_module, "_port_is_open", lambda port: next(probes, False))
    controller = SupervisorController(
        tmp_path,
        port=63001,
        timeout=1.0,
        sleep=lambda seconds: None,
        port_inspector=lambda port, root: PortInspection(
            "blocked",
            reason="listener is closing and /build-check has already stopped",
        ),
        pid_terminator=lambda pid, timeout=0: terminated.append(pid) or True,
    )

    code, message = controller.stop()

    assert code == supervisor_module.EXIT_OK
    assert "stopped manually" in message
    assert controller.paths.manual_stop.exists()
    assert terminated == []


def test_stale_state_stop_propagates_negative_supervisor_ack(supervisor_root, monkeypatch):
    monkeypatch.setattr(supervisor_module, "_port_is_open", lambda port: False)
    controller = SupervisorController(
        supervisor_root,
        port=63001,
        timeout=0.02,
        singleton_probe=lambda root: True,
        sleep=lambda seconds: None,
    )
    monkeypatch.setattr(
        controller,
        "_wait_ack",
        lambda request_id, timeout=None: {
            "request_id": request_id,
            "ok": False,
            "message": "owned child is still alive",
        },
    )

    code, message = controller.stop()

    assert code == supervisor_module.EXIT_ERROR
    assert "still alive" in message
    assert controller.paths.manual_stop.exists()


def test_stale_state_stop_needs_singleton_release_even_when_port_is_free(supervisor_root, monkeypatch):
    monkeypatch.setattr(supervisor_module, "_port_is_open", lambda port: False)
    controller = SupervisorController(
        supervisor_root,
        port=63001,
        timeout=0.01,
        singleton_probe=lambda root: True,
        sleep=lambda seconds: time.sleep(0.001),
    )
    monkeypatch.setattr(controller, "_wait_ack", lambda request_id, timeout=None: None)

    code, message = controller.stop()

    assert code == supervisor_module.EXIT_ERROR
    assert "did not finish shutdown" in message
    assert controller.paths.manual_stop.exists()


def test_stale_or_foreign_state_is_not_treated_as_an_active_supervisor(supervisor_root):
    tmp_path = supervisor_root
    controller = SupervisorController(tmp_path, port=63001, timeout=0.2)
    _atomic_json_write(
        controller.paths.state,
        {
            "schema": STATE_SCHEMA,
            "root": str(tmp_path / "different-root"),
            "port": 63001,
            "supervisor_pid": os.getpid(),
            "heartbeat_at": time.time(),
            "instance_token": "foreign",
            "phase": "running",
        },
    )
    assert controller._valid_state() is None

    _atomic_json_write(
        controller.paths.state,
        {
            "schema": STATE_SCHEMA,
            "root": str(tmp_path.resolve()),
            "port": 63001,
            "supervisor_pid": os.getpid(),
            "heartbeat_at": time.time() - 60,
            "instance_token": "stale",
            "phase": "running",
        },
    )
    assert controller._valid_state() is None


def test_start_server_launcher_uses_background_supervisor_only():
    root = Path(__file__).resolve().parents[1]
    text = (root / "START_SERVER.bat").read_text(encoding="utf-8").lower()
    assert "spb_server_supervisor.py\" start --follow" in text or "spb_server_supervisor.py start --follow" in text
    assert "server_v5.py" not in text
    assert "timeout /t 5" not in text
    assert "window stays open" in text
    assert "closing this window detaches logs only" in text
    assert "[error] spb server control failed" in text
    assert "pause" in text


def test_fresh_start_is_narrow_refresh_without_process_pattern_kills():
    root = Path(__file__).resolve().parents[1]
    text = (root / "SPB_FRESH_START.bat").read_text(encoding="utf-8").lower()
    assert "spb_server_supervisor.py\" refresh" in text or "spb_server_supervisor.py refresh" in text
    for forbidden in ("taskkill", "get-ciminstance", "win32_process", "server(_v5)?", "killtree"):
        assert forbidden not in text
    assert "refresh --follow" in text
    assert '"%spb_python%" -u' in text
    assert "running canonical file: %~f0" in text
    assert "timeout /t 5" not in text
    assert "window remains open" in text
    assert "pause" in text


def test_logs_launcher_is_read_only_and_persistent():
    root = Path(__file__).resolve().parents[1]
    text = (root / "SPB_SERVER_LOGS.bat").read_text(encoding="utf-8").lower()
    assert "spb_server_supervisor.py\" logs" in text or "spb_server_supervisor.py logs" in text
    for forbidden in ("server_v5.py", "taskkill", " stop", " refresh", "timeout /t 5"):
        assert forbidden not in text


@pytest.mark.parametrize(
    ("filename", "command"),
    [
        ("SPB_STOP_SERVER.bat", "stop"),
        ("SPB_REFRESH_SERVER.bat", "refresh"),
        ("SPB_SERVER_STATUS.bat", "status"),
    ],
)
def test_dedicated_control_launchers_map_to_one_supervisor_command(filename, command):
    root = Path(__file__).resolve().parents[1]
    text = (root / filename).read_text(encoding="utf-8").lower()
    assert f"spb_server_supervisor.py\" {command}" in text or f"spb_server_supervisor.py {command}" in text
    assert "server_v5.py" not in text
    assert "taskkill" not in text
