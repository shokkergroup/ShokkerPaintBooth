"""
tests/conftest.py — shared pytest fixtures for the SPB test suite.

Adds the project root to sys.path so tests can ``import shokker_engine_v2``
and ``import server`` directly. Also defines fixtures used by multiple
test files:

* ``app_client``     — Flask test client for hitting routes in-process.
* ``tmp_paint_file`` — temp 64x64 RGBA PNG that satisfies _validate_paint_file.
* ``sample_zones``   — minimal valid zone list for build_multi_zone calls.
* ``clean_caches``   — clears engine + server caches before/after each test.

All fixtures are deliberately tiny so they don't dominate test runtime
(target: every test < 1 second).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Make the project root importable so ``import server`` / ``import shokker_engine_v2`` work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

RUNTIME_HARNESS_DIR = os.path.join(PROJECT_ROOT, "tests", "_runtime_harness")
LOCAL_TEMP_DIR = os.path.join(RUNTIME_HARNESS_DIR, "temp_files")
os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)
os.environ["TMPDIR"] = LOCAL_TEMP_DIR
os.environ["TEMP"] = LOCAL_TEMP_DIR
os.environ["TMP"] = LOCAL_TEMP_DIR
tempfile.tempdir = LOCAL_TEMP_DIR

_ORIGINAL_MKDTEMP = tempfile.mkdtemp

_ROOT_JUNK_ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def _is_known_root_temp_junk(path: Path) -> bool:
    """Match only the accidental root-level 4-byte ``blat`` artifacts."""
    try:
        if not path.is_file() or path.suffix:
            return False
        if len(path.name) != 8:
            return False
        if any(ch not in _ROOT_JUNK_ALLOWED_CHARS for ch in path.name):
            return False
        if path.stat().st_size != 4:
            return False
        return path.read_text(encoding="utf-8") == "blat"
    except OSError:
        return False


def _cleanup_known_test_artifacts() -> None:
    root = Path(PROJECT_ROOT)
    for path in root.iterdir():
        if _is_known_root_temp_junk(path):
            try:
                path.unlink()
            except OSError:
                pass

    temp_root = Path(LOCAL_TEMP_DIR)
    if temp_root.exists():
        for child in temp_root.iterdir():
            if child.name == ".gitkeep":
                continue
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except OSError:
                pass


def _workspace_mkdtemp(suffix=None, prefix=None, dir=None):
    if dir is not None:
        return _ORIGINAL_MKDTEMP(suffix=suffix, prefix=prefix, dir=dir)
    return os.path.join(RUNTIME_HARNESS_DIR, "mkdtemp")


tempfile.mkdtemp = _workspace_mkdtemp
_cleanup_known_test_artifacts()


def pytest_sessionfinish(session, exitstatus):
    _cleanup_known_test_artifacts()

# Windows: avoid charmap errors when engine/server log Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Session-scoped engine import — heavy registries load ONCE, not per test.
# Without this, test runtime balloons by 10x.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def engine_module():
    """Imports shokker_engine_v2 once for the whole session."""
    import shokker_engine_v2 as eng
    return eng


@pytest.fixture(scope="session")
def server_module():
    """Imports server.py once for the whole session."""
    import server
    return server


@pytest.fixture()
def tmp_path():
    """Sandbox-safe tmp_path backed by a pre-existing writable directory."""
    return Path(RUNTIME_HARNESS_DIR) / "tmp_path"


@pytest.fixture()
def app_client(server_module):
    """Flask test client — fresh per test so request state never leaks."""
    server_module.app.config["TESTING"] = True
    return server_module.app.test_client()


@pytest.fixture()
def tmp_paint_file():
    """Write a 64x64 RGBA PNG to a tempfile and yield its path.

    _validate_paint_file accepts .png, so we use that for portability
    (TGA writers aren't installed everywhere).
    """
    import numpy as np
    from PIL import Image

    arr = np.zeros((64, 64, 4), dtype=np.uint8)
    arr[:, :, 0] = 200  # mostly red
    arr[:, :, 3] = 255  # opaque
    fd, path = tempfile.mkstemp(suffix=".png", prefix="spb_test_paint_")
    os.close(fd)
    Image.fromarray(arr, mode="RGBA").save(path)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture()
def sample_zones():
    """Minimal 1-zone livery — 'everything' grabs every pixel."""
    return [
        {"name": "Body", "color": "everything", "finish": "gloss", "intensity": "100"},
    ]


@pytest.fixture()
def multi_zone_sample():
    """Multi-zone livery for priority/remainder testing."""
    return [
        {"name": "Yellow", "color": "yellow", "finish": "chrome", "intensity": "100"},
        {"name": "Rest", "color": "remaining", "finish": "matte", "intensity": "100"},
    ]


@pytest.fixture()
def clean_caches(engine_module, server_module):
    """Clear engine + server caches before/after a test for hermetic runs."""
    # --- pre ---
    try:
        if hasattr(engine_module, "build_multi_zone"):
            if hasattr(engine_module.build_multi_zone, "_zone_cache"):
                engine_module.build_multi_zone._zone_cache.clear()
    except Exception:
        pass
    try:
        from engine.compose import _pattern_tex_cache
        _pattern_tex_cache.clear()
    except Exception:
        pass
    try:
        if hasattr(server_module, "_FINISH_DATA_CACHE"):
            server_module._FINISH_DATA_CACHE = None
    except Exception:
        pass
    yield
    # --- post (best-effort, mirrors pre) ---
    try:
        if hasattr(engine_module, "build_multi_zone"):
            if hasattr(engine_module.build_multi_zone, "_zone_cache"):
                engine_module.build_multi_zone._zone_cache.clear()
    except Exception:
        pass
    try:
        from engine.compose import _pattern_tex_cache
        _pattern_tex_cache.clear()
    except Exception:
        pass


@pytest.fixture()
def finish_data_js_text():
    """Read paint-booth-0-finish-data.js once per test that needs it."""
    path = os.path.join(PROJECT_ROOT, "paint-booth-0-finish-data.js")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
