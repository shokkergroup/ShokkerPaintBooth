import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "zone9_matte_carbon_guard.mjs"


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"zone9_matte_carbon_guard harness failed (exit {proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_zone9_matte_carbon_zombie_is_stripped(harness):
    assert harness["zombie_fixed_count"] == 1
    assert harness["zombie_after"] == {
        "base": None,
        "pattern": "none",
        "finish": None,
        "color": None,
        "colorMode": "none",
    }
    assert harness["warning_count"] >= 1


def test_authored_zone9_mask_is_not_destroyed(harness):
    assert harness["authored_mask_fixed_count"] == 0
    assert harness["authored_mask_after"] == {
        "base": "matte",
        "pattern": "carbon_fiber",
    }


def test_layer_scoped_zone9_matte_carbon_is_not_destroyed(harness):
    assert harness["authored_source_layer_fixed_count"] == 0
    assert harness["authored_source_layer_after"] == {
        "base": "matte",
        "pattern": "carbon_fiber",
        "sourceLayer": "White Base",
    }


def test_non_zone9_matte_carbon_is_not_globally_deleted(harness):
    assert harness["non_zone9_fixed_count"] == 0
    assert harness["non_zone9_after"] == {
        "base": "matte",
        "pattern": "carbon_fiber",
    }
