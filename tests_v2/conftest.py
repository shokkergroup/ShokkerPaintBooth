"""
tests_v2 — Shokker Paint Booth's ground-up, current, all-green test suite.

Design (read tests_v2/README.md for the full rationale):
- We test STABLE CONTRACTS, not churning catalog data. The finish/base/pattern
  catalog is under active rebuild (Codex), so exact counts / exact IDs / exact
  pixel values are intentionally NOT asserted here — they would flap daily.
  Instead we assert invariants that must hold no matter what the catalog is:
  "every registered finish renders without crashing", "spec output is iron-safe",
  "the bugs we fixed stay fixed", "registries load and are internally consistent".
- Every test in this suite must PASS against the current app. No red tests.
- Engine import is session-scoped (it is slow, ~10-25s) and stdout-suppressed
  (the engine is extremely chatty at import).

Run it:
    python -m pytest tests_v2/ -o addopts= -o filterwarnings= -p no:cacheprovider -q
(the -o overrides neutralize the repo-global pyproject addopts/filterwarnings so
this suite runs clean and standalone.)
"""
import io
import sys
import pathlib
import contextlib

import numpy as np
import pytest

# Repo root on sys.path so `import shokker_engine_v2` works (mirrors tests/conftest.py).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

REPO_ROOT = _ROOT
SMALL = 64          # contract-render size: fast, and exercises the small-size path that crashed before
SEED = 7


@pytest.fixture(scope="session")
def engine():
    """The imported shokker_engine_v2 module (stdout suppressed during import)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import shokker_engine_v2 as s  # noqa: E402
    return s


@pytest.fixture(scope="session")
def registries(engine):
    """Dict of the four primary registries, whatever is currently loaded."""
    return {
        "BASE": getattr(engine, "BASE_REGISTRY", {}) or {},
        "FINISH": getattr(engine, "FINISH_REGISTRY", {}) or {},
        "PATTERN": getattr(engine, "PATTERN_REGISTRY", {}) or {},
        "MONOLITHIC": getattr(engine, "MONOLITHIC_REGISTRY", {}) or {},
    }


def is_valid_spec(arr):
    """A spec result is contract-valid if it is a finite ndarray (H,W) or (H,W,C>=3)."""
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim not in (2, 3):
        return False
    if a.ndim == 3 and a.shape[2] < 3:
        return False
    return bool(np.isfinite(a).all())


def suppress_stdout():
    """Context manager to silence the chatty engine during a render call."""
    return contextlib.redirect_stdout(io.StringIO())
