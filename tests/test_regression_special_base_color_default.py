"""Special/monolithic base picks must visibly own their default color.

Ordinary base materials should keep ``Use source paint`` by default. Shipping
specials and monolithics should default Base Color to ``From special`` using the
same finish ID, so picking COLORSHOXX Inferno Flip does not appear inert.
"""

import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "special_base_color_default.mjs"


def test_special_base_defaults_to_same_special_color_source():
    try:
        subprocess.run(
            ["node", "--version"], capture_output=True, check=True, timeout=10
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("node not available; skipping V8 harness")

    result = subprocess.run(
        ["node", str(HARNESS)],
        capture_output=True,
        timeout=60,
        cwd=str(REPO),
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    assert result.returncode == 0, (
        "Special base color default harness failed.\n\n"
        f"stdout:\n{stdout}\n\nstderr:\n{stderr}"
    )
    assert "specials default to From special" in stdout
