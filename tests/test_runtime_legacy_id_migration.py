"""HEENAN HP-MIGRATE runtime ratchet — Codex hotfix.

The HP1-HP4 + HB2 cross-registry rename pass changed raw IDs that the app
persists to disk (autosaves, project files, presets). Without a migration
layer, painters' prior work would silently orphan on load: the engine
would receive IDs that no longer exist in the registry and render an
invisible finish where the painter expected their work.

The fix introduces `_SPB_LEGACY_ID_MIGRATIONS` + `_migrateZoneFinishIds`
in state-zones.js and calls them from BOTH:
  - loadConfigFromObj()  — fires at config-load time (immediate)
  - repairZoneData()     — fires on init (2-second timer safety net)

This ratchet executes the migration helper in real V8 against a
zone-shaped object that uses every legacy id we expect to migrate, and
asserts that:
  - finish/pattern/specPatternStack ids get rewritten to canonical ids
  - patternStack and overlay-spec stacks (1, 5) also get rewritten
  - unrelated ids are NOT touched
  - a clean zone produces zero changes
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "legacy_id_migration.mjs"


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
            f"legacy_id_migration harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_HP_MIGRATE_pre_rename_zone_finish_field(harness):
    """RUNTIME: z.finish='acid_rain' (HP1 legacy MONOLITHIC) → 'acid_rain_drip'."""
    after = harness["preRename_zone_after"]
    assert after["finish"] == "acid_rain_drip", (
        f"HP1 monolithic migration broke: finish={after['finish']!r}"
    )


def test_HP_MIGRATE_pre_rename_zone_pattern_field(harness):
    """RUNTIME: z.pattern='shokk_cipher' (HB2 legacy PATTERN) → 'shokk_cipher_pattern'."""
    after = harness["preRename_zone_after"]
    assert after["pattern"] == "shokk_cipher_pattern", (
        f"HB2 pattern migration broke: pattern={after['pattern']!r}"
    )


def test_HP_MIGRATE_pattern_stack_entries_rewritten(harness):
    """RUNTIME: patternStack[].id legacy entries get rewritten while
    unrelated entries are left untouched. Updated fixture covers HB2 +
    H4HR-1 + H4HR-2 + 1 unrelated entry."""
    after = harness["preRename_zone_after"]
    stack = after["patternStack"]
    ids = [e["id"] for e in stack]
    # Last entry must remain unrelated (not migrated)
    assert "carbon_fiber" in ids, "unrelated carbon_fiber removed"
    # No legacy ids should remain anywhere in the stack
    assert "shokk_cipher" not in ids, "HB2 stale id in stack"
    assert "dragonfly_wing" not in ids, "H4HR-1 stale id in stack"
    assert "carbon_weave" not in ids, "H4HR-2 stale id in stack"
    # All renamed targets must appear
    assert "shokk_cipher_pattern" in ids, "HB2 migration not in stack"
    assert "dragonfly_wing_pattern" in ids, "H4HR-1 migration not in stack"
    assert "carbon_weave_pattern" in ids, "H4HR-2 migration not in stack"


def test_HP_MIGRATE_spec_pattern_stack_rewritten(harness):
    """RUNTIME: specPatternStack[].id rewrites for HP2 + HP3 + H4HR-4..H4HR-8.
    Unrelated `spec_kevlar_weave` untouched."""
    after = harness["preRename_zone_after"]
    sps = after["specPatternStack"]
    ids = [e["id"] for e in sps]
    expected_present = {
        "spec_carbon_weave",                 # HP2
        "spec_diffraction_grating_cd",       # HP3
        "spec_oil_slick",                    # H4HR-4
        "spec_gravity_well",                 # H4HR-5
        "spec_sparkle_constellation",        # H4HR-6
        "spec_sparkle_firefly",              # H4HR-7
        "spec_sparkle_champagne",            # H4HR-8
        "spec_kevlar_weave",                 # unrelated
    }
    assert set(ids) == expected_present, (
        f"spec pattern stack mismatch: {set(ids) - expected_present!r} extra, "
        f"{expected_present - set(ids)!r} missing"
    )


def test_HP_MIGRATE_overlay_stacks_also_rewritten(harness):
    """RUNTIME: overlaySpecPatternStack and fifthOverlaySpecPatternStack
    are migrated alongside the main spec pattern stack — painter who used
    multi-overlay layers gets full migration coverage."""
    after = harness["preRename_zone_after"]
    overlay = after["overlaySpecPatternStack"]
    fifth = after["fifthOverlaySpecPatternStack"]
    assert overlay[0]["id"] == "spec_carbon_weave", "overlay stack not migrated"
    assert fifth[0]["id"] == "spec_diffraction_grating_cd", "fifth-overlay stack not migrated"


def test_HP_MIGRATE_change_count_correct(harness):
    """RUNTIME: helper returns count of mutations. 14 expected for the
    expanded test zone covering HP1-HP4 + HB2 + H4HR-1..H4HR-8:
    finish (HP1) + pattern (HB2) +
    3 patternStack entries (HB2 + H4HR-1 + H4HR-2) +
    7 specPatternStack entries (HP2 + HP3 + H4HR-4..H4HR-8) +
    1 overlay entry (HP2) + 1 fifth-overlay entry (HP3) = 14."""
    assert harness["preRename_changed_count"] == 14, (
        f"expected 14 migrations, got {harness['preRename_changed_count']}"
    )


def test_HP_MIGRATE_h4hr1_h4hr2_pattern_stack(harness):
    """RUNTIME (H4HR-1 + H4HR-2): patternStack[].id legacy entries get
    rewritten — dragonfly_wing → dragonfly_wing_pattern, carbon_weave
    → carbon_weave_pattern."""
    after = harness["preRename_zone_after"]
    stack_ids = [e["id"] for e in after["patternStack"]]
    assert "dragonfly_wing_pattern" in stack_ids, "H4HR-1 dragonfly migration broke"
    assert "carbon_weave_pattern" in stack_ids, "H4HR-2 carbon_weave migration broke"
    assert "dragonfly_wing" not in stack_ids, "stale dragonfly_wing left in stack"
    assert "carbon_weave" not in stack_ids, "stale carbon_weave left in stack"


def test_HP_MIGRATE_h4hr4_h4hr5_h4hr6_h4hr7_h4hr8_spec_stack(harness):
    """RUNTIME (H4HR-4..H4HR-8): specPatternStack[].id rewrites for the 5
    SPEC × MONOLITHIC collisions. All renames go to `spec_*` namespace."""
    after = harness["preRename_zone_after"]
    sps_ids = set(e["id"] for e in after["specPatternStack"])
    expected_new = {
        "spec_oil_slick", "spec_gravity_well",
        "spec_sparkle_constellation", "spec_sparkle_firefly",
        "spec_sparkle_champagne",
    }
    assert expected_new.issubset(sps_ids), (
        f"H4HR-4..H4HR-8 spec migrations incomplete. Got: {sps_ids}"
    )
    # And the legacy ids must NOT remain
    legacy = {"oil_slick", "gravity_well", "sparkle_constellation",
              "sparkle_firefly", "sparkle_champagne"}
    assert legacy.isdisjoint(sps_ids), (
        f"stale legacy ids left in spec stack: {sps_ids & legacy}"
    )


def test_HP_MIGRATE_h4hr3_monolithic_finish(harness):
    """RUNTIME (H4HR-3): z.finish = 'crystal_lattice' (legacy MONO id) gets
    rewritten to 'crystal_lattice_mono'. PATTERN tier kept the canonical
    id so painters who used it as a pattern still see their work."""
    assert harness["h4hr3_zone2_changed"] == 1, (
        f"H4HR-3 migration count wrong: {harness['h4hr3_zone2_changed']}"
    )
    assert harness["h4hr3_zone2_finish"] == "crystal_lattice_mono", (
        f"H4HR-3 finish migration broke: {harness['h4hr3_zone2_finish']}"
    )


def test_HP_MIGRATE_full_map_covers_13_legacy_ids(harness):
    """RUNTIME: the migration map must hold all 13 legacy IDs documented
    by HP1-HP4 + HB2 + H4HR-1..H4HR-8. Asserting on the keys catches a
    refactor that drops an entry without noticing."""
    m = harness["migration_map_full"]
    mono_keys = set(m["monolithic"].keys())
    pat_keys = set(m["pattern"].keys())
    spec_keys = set(m["specPattern"].keys())
    assert "acid_rain" in mono_keys, "HP1 missing"
    assert "crystal_lattice" in mono_keys, "H4HR-3 missing"
    assert "shokk_cipher" in pat_keys, "HB2 missing"
    assert "dragonfly_wing" in pat_keys, "H4HR-1 missing"
    assert "carbon_weave" in pat_keys, "H4HR-2 missing"
    assert "carbon_weave" in spec_keys, "HP2 missing"
    assert "diffraction_grating" in spec_keys, "HP3 missing"
    for sid in ("oil_slick", "gravity_well", "sparkle_constellation",
                "sparkle_firefly", "sparkle_champagne"):
        assert sid in spec_keys, f"H4HR-* {sid} missing"


def test_HP_MIGRATE_clean_zone_unchanged(harness):
    """RUNTIME: a zone with NO legacy ids returns zero changes and is
    bit-for-bit untouched. The migration must not introduce new state for
    painters who started after the rename."""
    assert harness["clean_zone_changed"] == 0, (
        f"clean zone got {harness['clean_zone_changed']} unexpected migrations"
    )
    assert harness["clean_zone_unchanged"] is True


def test_HP_MIGRATE_helper_exposes_migration_keys(harness):
    """RUNTIME: the migration map is structured by field-type so future
    additions can extend the right scope. Must expose monolithic/pattern/
    specPattern keys at minimum."""
    keys = set(harness["migrations_visible"])
    assert {"monolithic", "pattern", "specPattern"}.issubset(keys), (
        f"migration map missing field-type scopes: {keys}"
    )
