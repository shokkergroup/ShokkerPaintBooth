"""HEENAN HP1-HP4 + HB2 ratchet — cross-registry collisions and intra-registry
duplicates in paint-booth-0-finish-data.js.

This shift's Pillman audit found 5 cross-registry collisions that the in-source
validateFinishData() did not catch (it only validates per-registry shape):
  - acid_rain in BASES + MONOLITHICS                    → fixed (HP1)
  - carbon_weave in BASES + PATTERNS + SPEC_PATTERNS    → SPEC entry fixed (HP2)
  - diffraction_grating in PATTERNS + SPEC_PATTERNS     → SPEC entry fixed (HP3)
  - mystichrome × 2 in MONOLITHICS                      → fixed (HP4 intra-dup)
  - shokk_cipher in BASES + PATTERNS                    → PATTERN entry fixed (HB2)

The runtime detector found 8 ADDITIONAL legacy collisions that pre-date this
shift. Renaming them risks breaking user-saved zone configs that reference
those ids. They are TOLERATED for now (documented below) and the ratchet
asserts that the count does not grow.

Tolerated legacy collisions (DO NOT add new ones):
  base × pattern   = ['carbon_weave', 'dragonfly_wing']
  pattern × mono   = ['crystal_lattice']
  spec × mono      = ['oil_slick', 'gravity_well',
                      'sparkle_constellation', 'sparkle_firefly',
                      'sparkle_champagne']

Intra-registry duplicates: must be ZERO across all 4 registries.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "registry_collisions.mjs"

TOLERATED_LEGACY_COLLISIONS = {
    # 2026-04-19 4-HOUR RUN H4HR-1..H4HR-8 — all 8 legacy collisions resolved
    # behind HP-MIGRATE backward-compat layer. Tolerated set is now empty;
    # any cross-registry collision the harness reports is a real regression.
    "base_x_mono":     set(),
    "base_x_pattern":  set(),
    "base_x_spec":     set(),
    "pattern_x_spec":  set(),
    "pattern_x_mono":  set(),
    "spec_x_mono":     set(),
}


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    if not HARNESS.exists():
        pytest.fail(f"missing: {HARNESS}")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"registry_collisions harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_HP_no_intra_registry_duplicate_ids(harness):
    """Each registry (BASES / PATTERNS / MONOLITHICS / SPEC_PATTERNS) must
    have zero duplicate ids. JS object lookup tables (BASES_BY_ID etc.)
    silently overwrite duplicates — the surviving entry is the one that
    .set() last; the other tile renders but routes to the survivor. HP4
    found `mystichrome` × 2 in MONOLITHICS and renamed the second."""
    dupes = harness["intra_registry_duplicates"]
    for registry, ids in dupes.items():
        assert ids == [], (
            f"Intra-registry duplicate ids in {registry}: {ids}. "
            f"BY_ID lookup tables will silently overwrite — rename one."
        )


def test_HP1_HP4_HB2_no_new_cross_registry_collisions(harness):
    """The 5 collisions Pillman + Bockwinkel found this shift are fixed.
    8 legacy collisions remain TOLERATED (renaming them risks breaking
    user-saved zone configs). This ratchet asserts that the tolerated set
    does NOT grow — any NEW cross-registry collision is treated as a
    regression and the test fails with a clear message."""
    crosses = harness["cross_registry_collisions"]
    new_offenders = {}
    for klass, ids in crosses.items():
        actual = set(ids)
        tolerated = TOLERATED_LEGACY_COLLISIONS.get(klass, set())
        new = actual - tolerated
        if new:
            new_offenders[klass] = sorted(new)
    assert not new_offenders, (
        "NEW cross-registry id collision detected. The id appears in two "
        "registries — BY_ID lookup is non-deterministic and the picker "
        "shows two tiles for the same finish. Either rename one or add "
        "the id to TOLERATED_LEGACY_COLLISIONS in this test (only if "
        "the rename would break saved configs).\n"
        f"Offenders: {new_offenders}"
    )
