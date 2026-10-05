"""HEENAN HCOUNT — finish/pattern/monolithic/spec count baselines.

Smoke-test ratchets: catch accidental deletions / refactor regressions
that would silently shrink the catalog. The 4 registries (BASES, PATTERNS,
MONOLITHICS, SPEC_PATTERNS) and the FINISH_METADATA catalog all have
known sizes. Bounds are generous (don't fight the catalog cull mechanism)
but tight enough to catch a 100+ entry deletion.

Baselines as of 2026-04-19 (post 4-hour autonomous run + bonus run):
- BASES:         ~358
- PATTERNS:      ~319
- MONOLITHICS:   ~628 (audit-runtime view)
- SPEC_PATTERNS: ~285
- FINISH_METADATA: ~1,432 (1424 generated + 13 hand-added aliases)

If the catalog grows past upper bound, intentional content addition;
update bound.
If shrinks past lower bound, investigate before bumping bound.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "registry_collisions.mjs"


def _run_collision_harness():
    """The collision harness already loads each registry into V8 — reuse it
    for the count snapshot. Avoids parsing 466KB of source by hand."""
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"collision harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def sizes():
    return _run_collision_harness()["sizes"]


def test_count_BASES_within_baseline(sizes):
    """BASES is the foundation tier — most-used finish registry."""
    n = sizes["BASES"]
    assert 320 <= n <= 450, (
        f"BASES count {n} outside baseline 320-450. "
        f"Either intentional content change (bump bound) or refactor regression (investigate)."
    )


def test_count_PATTERNS_within_baseline(sizes):
    n = sizes["PATTERNS"]
    assert 280 <= n <= 400, f"PATTERNS count {n} outside baseline 280-400"


def test_count_MONOLITHICS_within_baseline(sizes):
    n = sizes["MONOLITHICS"]
    # 2026-05-29: grew to 942 via intentional daily content additions (+192
    # since the 2026-04-19 baseline; harness reports zero intra-registry dupes).
    assert 580 <= n <= 1050, f"MONOLITHICS count {n} outside baseline 580-1050"


def test_count_SPEC_PATTERNS_within_baseline(sizes):
    n = sizes["SPEC_PATTERNS"]
    assert 250 <= n <= 350, f"SPEC_PATTERNS count {n} outside baseline 250-350"


def test_count_total_finish_universe_within_baseline(sizes):
    """Catalog-wide sanity: total visible-to-painter finishes shouldn't
    drift more than ±15% from current baseline without intent."""
    total = sum(sizes.values())
    # 2026-05-29: total is 1977, driven mostly by the MONOLITHICS +192 growth
    # (see test_count_MONOLITHICS_within_baseline). Bump the ceiling to match.
    assert 1500 <= total <= 2200, (
        f"Total catalog count {total} outside baseline 1500-2200"
    )


def test_count_metadata_baseline():
    """FINISH_METADATA covers most catalog entries. Should track close to
    catalog total but with the hand-added aliases (HP-METADATA + 4-HOUR).
    Currently ~1,432 entries."""
    src = (REPO / "paint-booth-0-finish-metadata.js").read_text(encoding="utf-8")
    # Count top-level entries by counting `"id": {` patterns inside the
    # FINISH_METADATA constant. Simple proxy: count `"<id>":\s*{` at indent 2.
    import re
    n = len(re.findall(r'^  "[a-zA-Z0-9_]+": \{', src, re.MULTILINE))
    assert 1300 <= n <= 1600, f"FINISH_METADATA count {n} outside baseline 1300-1600"
