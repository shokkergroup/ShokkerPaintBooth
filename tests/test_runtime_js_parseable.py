"""HEENAN HARDMODE-GUARDRAIL-PARSE — every canonical JS file must parse.

The HARDMODE pass shipped a `paint-booth-0-finish-metadata.js` with a
missing trailing comma inside SEARCH_KEYWORDS:

    "frozen": [...]        <- no trailing comma, end of original entries
    "satin": [...]         <- new entry inserted by normalizer
    ...

`node --check` failed on all three 3-copy mirrors, which means the
browser would have failed to boot the metadata bootstrap on every build.
The existing test_layer_system.py only regex-scanned the file as text,
so a broken JS parse did not fail the gate.

This test runs `node --check` on every canonical `paint-booth-*.js` and
`scripts/*.js` file (and their two runtime-synced copies) so a parse
regression cannot ship silently again. Skips if node is not on PATH
(CI image may not have it; the ratchet is still valuable for local dev).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Canonical JS files + their 3-copy mirrors.
CANONICAL_DIRS = [
    REPO,
    REPO / "electron-app" / "server",
    REPO / "electron-app" / "server" / "pyserver" / "_internal",
]

PAINT_BOOTH_PATTERNS = [
    "paint-booth-0-finish-data.js",
    "paint-booth-0-finish-metadata.js",
    "paint-booth-1-*.js",
    "paint-booth-2-*.js",
    "paint-booth-3-*.js",
    "paint-booth-4-*.js",
    "paint-booth-5-*.js",
    "paint-booth-6-*.js",
]


def _gather_targets():
    targets = []
    for root in CANONICAL_DIRS:
        if not root.exists():
            continue
        for pat in PAINT_BOOTH_PATTERNS:
            for p in sorted(root.glob(pat)):
                targets.append(p)
    return targets


@pytest.fixture(scope="module")
def node_exe():
    exe = shutil.which("node")
    if exe is None:
        pytest.skip("node not on PATH")
    return exe


@pytest.mark.parametrize("js_path", _gather_targets(), ids=lambda p: str(p.relative_to(REPO)))
def test_js_parses(js_path, node_exe):
    """Every canonical paint-booth JS must pass `node --check`.

    If this fails, the browser bootstrap is broken and the Electron app
    will error on load. Fix the JS; do not skip the test.
    """
    proc = subprocess.run(
        [node_exe, "--check", str(js_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"node --check failed for {js_path.relative_to(REPO)}:\n"
            f"stderr:\n{proc.stderr}\n"
            f"stdout:\n{proc.stdout}"
        )
