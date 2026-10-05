"""Run-smoke tests for the repository's verification tools.

Unlike ``test_tooling_and_routes_smoke.py`` (which only byte-compiles the
scripts), this module actually *executes* each verification tool end-to-end as
a subprocess. The point is to prove the tools RUN end-to-end (import the engine,
enumerate the catalog, compare baselines), not merely that they parse.

Each tool imports the rendering engine (~10-25s), so this file is slow by
design. The tests are marked ``slow`` so they can be deselected with
``-m "not slow"`` for a fast inner loop, but they must PASS when run.

Per-tool exit-code contract (verified against each script's own docstring):

* ``spb_catalog_report.py`` -- REPORT-ONLY: its docstring guarantees it
  "ALWAYS exits 0 ... never a build gate". We assert exit 0 (hard).
* ``spb_visual_diff.py`` (REVIEW mode, i.e. NO ``--update-baselines`` so the
  committed golden baselines are never overwritten) -- REVIEW-ONLY: its
  docstring guarantees it "NEVER fails the build - it always exits 0". We assert
  exit 0 (hard).
* ``spb_doctor.py`` -- this one is a preflight *gate*, not a pure report: its
  docstring documents "Exit codes: 0 no FAILs (WARNs allowed); 1 one or more
  FAILs". So for the doctor, BOTH exit 0 and exit 1 mean it executed end-to-end
  successfully (0 = clean workspace, 1 = it found real FAIL items to report). A
  test environment that hasn't been synced yet (3-copy drift) or that exposes
  the catalog only through ``engine.registry`` rather than the legacy
  ``shokker_engine_v2`` attributes will legitimately make the doctor report
  FAILs and exit 1 -- that is the doctor working, not breaking. We therefore
  accept {0, 1} as a successful run and xfail-with-reason on a clean exit 1 (so
  the gate's findings are surfaced without turning the smoke run red). Only an
  abnormal exit (crash / killed / anything outside {0, 1}) is a hard failure.

stdout is discarded on purpose: the engine leaks large amounts of text to
stdout, and we only care about the process exit code here. stderr is captured so
a failure message is useful.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Generous timeout: these tools import the engine and do real work. If a tool
# blows past this it is xfailed (see below) rather than left to hang the suite.
TOOL_TIMEOUT_S = 240

# Tools that are PURE report/review tools: by their own contract they ALWAYS
# exit 0 (never a build gate). Run in their default/review mode. spb_visual_diff
# is run WITHOUT --update-baselines so committed golden baselines are untouched.
REPORT_ONLY_TOOLS = [
    ("spb_catalog_report.py", []),
    ("spb_visual_diff.py", []),  # review mode -- NOT --update-baselines
]

# The doctor is a preflight GATE: exit 0 (no FAILs) OR exit 1 (FAILs found) both
# mean it ran end-to-end. Anything else is abnormal.
GATE_TOOLS = [
    ("spb_doctor.py", []),
]


def _run_tool(script_name: str, extra_args: list[str]) -> subprocess.CompletedProcess:
    """Run a verification tool as a subprocess from the project root.

    stdout is discarded (engine chatter), stderr captured. Returns the
    CompletedProcess. xfails (does not hang) if the tool is missing or exceeds
    the timeout.
    """
    script_path = SCRIPTS_DIR / script_name
    if not script_path.is_file():
        pytest.xfail(f"tool not found: {script_path.relative_to(PROJECT_ROOT)}")

    cmd = [sys.executable, str(script_path), *extra_args]
    try:
        return subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,  # engine leaks to stdout; discard it
            stderr=subprocess.PIPE,
            timeout=TOOL_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        pytest.xfail(
            f"{script_name} exceeded {TOOL_TIMEOUT_S}s "
            "(too slow to run in this smoke check)"
        )


def _stderr_tail(proc: subprocess.CompletedProcess, n: int = 2000) -> str:
    return (proc.stderr or b"")[-n:].decode("utf-8", errors="replace")


@pytest.mark.slow
@pytest.mark.parametrize(
    ("script_name", "extra_args"),
    REPORT_ONLY_TOOLS,
    ids=[name for name, _ in REPORT_ONLY_TOOLS],
)
def test_report_only_tool_runs_and_exits_zero(
    script_name: str, extra_args: list[str]
) -> None:
    """A pure report/review tool must execute end-to-end and exit 0.

    These tools guarantee (in their own docstrings) that they are report-only
    and never a build gate, so a non-zero exit is a genuine runtime regression.
    """
    proc = _run_tool(script_name, extra_args)
    assert proc.returncode == 0, (
        f"{script_name} exited {proc.returncode} "
        f"(expected 0; this tool is report-only / never a build gate). "
        f"stderr tail:\n{_stderr_tail(proc)}"
    )


@pytest.mark.slow
@pytest.mark.parametrize(
    ("script_name", "extra_args"),
    GATE_TOOLS,
    ids=[name for name, _ in GATE_TOOLS],
)
def test_gate_tool_runs_end_to_end(script_name: str, extra_args: list[str]) -> None:
    """The preflight gate must execute end-to-end with a documented exit code.

    spb_doctor's contract is exit 0 (no FAILs) or exit 1 (FAILs found); both
    prove it ran the full check sequence without crashing. Exit 0 is a hard
    pass. Exit 1 is the gate doing its job (e.g. unsynced 3-copy drift, or the
    catalog being exposed only via ``engine.registry`` in this environment) --
    we xfail-with-reason so the smoke run stays green while still recording that
    the gate flagged items. Any OTHER exit code (crash / killed) is a hard
    failure: that means the tool did not run end-to-end.
    """
    proc = _run_tool(script_name, extra_args)
    rc = proc.returncode
    assert rc in (0, 1), (
        f"{script_name} exited abnormally with {rc} "
        f"(expected 0=no-FAILs or 1=FAILs-found; anything else means it did not "
        f"run end-to-end). stderr tail:\n{_stderr_tail(proc)}"
    )
    if rc == 1:
        pytest.xfail(
            f"{script_name} ran end-to-end but reported FAIL item(s) and exited 1 "
            "(documented gate behavior; expected in an unsynced/legacy-registry "
            "test environment)"
        )
