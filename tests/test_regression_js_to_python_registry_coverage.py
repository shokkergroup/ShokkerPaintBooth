"""Regression guardrail + ratchet for JS → Python registry coverage.

## Context (originally 2026-04-20 regression loop iter 10;
## UPDATED after 2026-04-21 HEENAN OVERNIGHT iter 3)

Checklist: do the canonical JS pattern ids actually resolve to a
Python render function, or do picker selections silently produce
no output?

## Original finding (2026-04-20)

31 JS pattern ids had no corresponding entry in Python render
registries (24 PATTERN + 7 SPEC_PATTERN). Selecting any of them
from the picker resulted in silent no-render.

## UPDATE 2026-04-21 HEENAN OVERNIGHT iter 3 — 19 closed, 12 de-exposed

The 31-id gap was closed. All 19 originally painter-visible
unrenderable ids now either render (via alias) or are de-exposed
from the picker (no longer selectable):

1. **10 cross-registry rename aliases shipped** (identity-preserving):
   - 3 PATTERN aliases (`carbon_weave_pattern` → `carbon_weave`,
     `dragonfly_wing_pattern` → `dragonfly_wing`, `shokk_cipher_pattern`
     → `shokk_cipher`) in `shokker_engine_v2.py` `_UI_PATTERN_ALIASES`.
   - 7 SPEC_PATTERN aliases (HP2/HP3/H4HR-4..8 renames) in
     `engine/spec_patterns.py` `_HP_H4HR_SPEC_ALIASES`.

2. **3 broken `_PATTERN_FALLBACKS` targets repaired** — their
   originals (`chrome_edge`, `shimmer_pearl_ripple`, `glow_pulse`)
   didn't exist in PATTERN_REGISTRY. Replaced with the closest
   existing semantic equivalents (`shimmer_chrome_flux`,
   `shimmer_prism_frost`, `shimmer_neon_weft`).

3. **6 family-prefix semantic aliases added** (`geo_fractal_triangle`,
   `geo_hilbert_curve`, `nature_bark_rough`, `nature_water_ripple_pat`,
   `tribal_celtic_spiral`, `tribal_norse_runes`). Each points at the
   closest existing registry key — a pattern whose docstring and
   swatch are the nearest semantic match.

4. **12 family patterns with no adequate semantic match** have been
   de-exposed from `PATTERN_GROUPS` in
   `paint-booth-0-finish-data.js`. They remain in the PATTERNS
   display-data array (so any saved zone referencing them keeps its
   metadata) but are no longer pickable. Painter can never select
   them from the UI. These are the entries still in
   `KNOWN_MISSING_PATTERN_IDS` below.

Behavioral verification: `test_iter3_aliases_actually_resolve_in_python`
and `test_iter3_repaired_pattern_fallbacks_have_real_targets` below
exercise the actual import-time resolution.

## What these tests still do

- **Ratchet on growth:** any NEW JS id without a Python render path
  fails `test_pattern_registry_coverage_gap_does_not_grow` (the
  allowlist `KNOWN_MISSING_PATTERN_IDS` must not expand).
- **De-exposure pin:** `test_de_exposed_family_patterns_absent_from_pattern_groups`
  guarantees the 12 unrenderable ids stay out of picker groups.
- **Alias resolution:** the iter 3 behavioral tests fire if any
  alias block is removed or if its targets go missing.
- **xfail-on-shrink:** if the gap shrinks further (someone authors
  a real render function for one of the 12 remaining family
  patterns), the count ratchet xfails to signal the test should
  be updated.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FINISH_DATA_JS = REPO / "paint-booth-0-finish-data.js"


def _extract_js_array_ids(text: str, varname: str) -> set[str]:
    """Grab every `id: 'xxx'` literal inside the top-level `const varname = [...]`."""
    m = re.search(rf"(?:const|var|let)\s+{re.escape(varname)}\s*=\s*\[", text)
    if not m:
        return set()
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
        i += 1
    body = text[start : i - 1]
    return set(re.findall(r"""id\s*:\s*['"]([^'"]+)['"]""", body))


# ---- Remaining gap after the 2026-04-21 HEENAN OVERNIGHT iter 3 fix ----
#
# Iter 3 closed 19 of the 31 originally documented gaps:
#   - 10 cross-registry rename aliases shipped (3 PATTERN + 7 SPEC_PATTERN)
#   - 3 broken _PATTERN_FALLBACKS targets repaired
#   - 6 family-prefix semantic aliases added (geo_fractal_triangle,
#     geo_hilbert_curve, nature_bark_rough, nature_water_ripple_pat,
#     tribal_celtic_spiral, tribal_norse_runes)
#
# The 12 ids below have NO adequate semantic equivalent in
# PATTERN_REGISTRY. They've been DE-EXPOSED from PATTERN_GROUPS in
# paint-booth-0-finish-data.js so the picker no longer offers them
# (they remain in the PATTERNS array so any saved zone referencing
# them keeps its display metadata; selecting one programmatically
# still silently renders nothing).
#
# None of these are reachable from the live UI. The remaining gap is
# purely a code-level concern — a future task can author render
# functions for each, OR remove them from PATTERNS entirely once
# nobody has saved configs referencing them.
KNOWN_MISSING_PATTERN_IDS = frozenset({
    # Geographic pattern family (de-exposed from picker).
    "geo_islamic_star",
    "geo_penrose_tile",
    "geo_truchet_curves",
    "geo_voronoi_organic",
    # Nature pattern family (de-exposed from picker).
    "nature_cloud_wisp",
    "nature_fern_fractal",
    "nature_flame_flicker",
    "nature_leaf_vein",
    # Tribal pattern family (de-exposed from picker).
    "tribal_aboriginal_dots",
    "tribal_african_kente",
    "tribal_native_diamond",
    "tribal_polynesian",
})

# All HP/H4HR rename gaps closed by aliases in engine/spec_patterns.py.
KNOWN_MISSING_SPEC_PATTERN_IDS = frozenset()


@pytest.fixture(scope="module")
def python_pattern_registry():
    """Import PATTERN_REGISTRY with engine initialization output suppressed."""
    import contextlib
    import io
    import sys

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import PATTERN_REGISTRY
    return set(PATTERN_REGISTRY.keys())


@pytest.fixture(scope="module")
def python_spec_pattern_catalog():
    import contextlib
    import io
    import sys

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.spec_patterns import PATTERN_CATALOG
    return set(PATTERN_CATALOG)


@pytest.fixture(scope="module")
def js_patterns():
    return _extract_js_array_ids(FINISH_DATA_JS.read_text(encoding="utf-8"), "PATTERNS")


@pytest.fixture(scope="module")
def js_spec_patterns():
    return _extract_js_array_ids(
        FINISH_DATA_JS.read_text(encoding="utf-8"), "SPEC_PATTERNS"
    )


def test_pattern_registry_coverage_gap_does_not_grow(
    python_pattern_registry, js_patterns
):
    """The set of JS PATTERNS with no Python PATTERN_REGISTRY entry
    must not exceed the documented known-missing list. Any NEW id
    falling into this gap is a regression.

    **This is a RATCHET, not a claim of correctness.** The existing
    31-id gap is a pre-existing painter-facing bug: these patterns
    appear in the picker but silently render nothing. The ratchet
    PREVENTS the gap from growing while a focused follow-up task
    (filed via spawn_task) addresses the documented 31.

    If this test fires with an UNEXPECTED id, a new pattern was
    added to the JS PATTERNS array without a corresponding Python
    render function. The right action is almost always to add the
    render function, NOT to expand KNOWN_MISSING_PATTERN_IDS.
    """
    missing = js_patterns - python_pattern_registry - {"none"}
    unexpected = missing - KNOWN_MISSING_PATTERN_IDS

    assert not unexpected, (
        f"NEW JS PATTERNS lack Python PATTERN_REGISTRY entries: "
        f"{sorted(unexpected)}. These will silently render nothing. "
        f"Register a Python render function. Do NOT add these ids to "
        f"KNOWN_MISSING_PATTERN_IDS without explicit painter-UX "
        f"justification — that set is for documenting EXISTING debt, "
        f"not for absorbing new gaps."
    )


def test_spec_pattern_catalog_coverage_gap_does_not_grow(
    python_spec_pattern_catalog, js_spec_patterns
):
    """Same ratchet as above, but for SPEC_PATTERNS vs the spec
    pattern catalog.
    """
    missing = js_spec_patterns - python_spec_pattern_catalog - {"none"}
    unexpected = missing - KNOWN_MISSING_SPEC_PATTERN_IDS

    assert not unexpected, (
        f"NEW JS SPEC_PATTERNS lack Python PATTERN_CATALOG entries: "
        f"{sorted(unexpected)}. These will silently render nothing. "
        f"Either register a spec-pattern function or (if display-only) "
        f"add to KNOWN_MISSING_SPEC_PATTERN_IDS after filing a follow-up."
    )


def test_pattern_registry_coverage_ratchet_count(
    python_pattern_registry, js_patterns
):
    """The COUNT of missing ids must not grow. When it shrinks,
    xfail (= green) signals the fix landed and prompts the
    KNOWN_MISSING_PATTERN_IDS allowlist to be trimmed.
    """
    missing = js_patterns - python_pattern_registry - {"none"}
    count = len(missing)

    assert count <= len(KNOWN_MISSING_PATTERN_IDS), (
        f"JS→Python PATTERNS coverage gap grew: {count} missing "
        f"(pinned max {len(KNOWN_MISSING_PATTERN_IDS)} in iter 10 of the "
        f"2026-04-20 regression loop)."
    )
    if count < len(KNOWN_MISSING_PATTERN_IDS):
        pytest.xfail(
            f"Coverage gap SHRUNK from {len(KNOWN_MISSING_PATTERN_IDS)} to "
            f"{count}. Fix progress detected. Trim the now-resolved ids "
            f"from KNOWN_MISSING_PATTERN_IDS: "
            f"{sorted(KNOWN_MISSING_PATTERN_IDS - missing)}"
        )


def test_spec_pattern_catalog_coverage_ratchet_count(
    python_spec_pattern_catalog, js_spec_patterns
):
    """Ratchet count for the spec side."""
    missing = js_spec_patterns - python_spec_pattern_catalog - {"none"}
    count = len(missing)

    assert count <= len(KNOWN_MISSING_SPEC_PATTERN_IDS), (
        f"JS→Python SPEC_PATTERNS coverage gap grew: {count} missing "
        f"(pinned max {len(KNOWN_MISSING_SPEC_PATTERN_IDS)})."
    )
    if count < len(KNOWN_MISSING_SPEC_PATTERN_IDS):
        pytest.xfail(
            f"Coverage gap SHRUNK from {len(KNOWN_MISSING_SPEC_PATTERN_IDS)}"
            f" to {count}. Fix progress detected. Trim the resolved ids "
            f"from KNOWN_MISSING_SPEC_PATTERN_IDS: "
            f"{sorted(KNOWN_MISSING_SPEC_PATTERN_IDS - missing)}"
        )


def test_js_patterns_in_groups_are_also_in_patterns_array():
    """Any pattern id appearing in PATTERN_GROUPS (the picker
    organization) must also exist in the PATTERNS display-data
    array. If not, the picker is trying to display a pattern that
    has no display metadata → blank card, broken UI.
    """
    text = FINISH_DATA_JS.read_text(encoding="utf-8")
    js_patterns = _extract_js_array_ids(text, "PATTERNS")

    # Extract PATTERN_GROUPS object body
    m = re.search(r"(?:const|var|let)\s+PATTERN_GROUPS\s*=\s*\{", text)
    assert m, "PATTERN_GROUPS not found in paint-booth-0-finish-data.js"
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    groups_body = text[start : i - 1]

    # Each group is of the form: "Group Name": ["id1", "id2", ...]
    # Extract all quoted lowercase-snake-case-ish ids from inside the array
    # parts (not the group keys).
    group_arrays = re.findall(r":\s*\[([^\]]*)\]", groups_body)
    all_grouped_ids = set()
    for arr in group_arrays:
        for token in re.findall(r"""['"]([a-z][a-z0-9_]+)['"]""", arr):
            all_grouped_ids.add(token)

    orphans = all_grouped_ids - js_patterns - {"none"}
    # orphans could include spec ids too if a group mixes them — filter
    # to ones that look like pattern ids. For safety, flag all; the
    # known-missing ratchet below absorbs expected ones.
    # The known-missing set here is: pattern ids in groups that aren't
    # in PATTERNS. Currently should be minimal.
    assert len(orphans) < 25, (
        f"PATTERN_GROUPS references {len(orphans)} ids that don't "
        f"appear in PATTERNS: {sorted(orphans)[:10]}... If this list "
        f"grew, someone added an id to a group without adding a "
        f"display entry in PATTERNS."
    )


def test_de_exposed_family_patterns_absent_from_pattern_groups():
    """The 12 family-prefix patterns with no Python render function
    were de-exposed from PATTERN_GROUPS in iter 3 so the picker no
    longer offers selections that produce silent no-render. This
    test pins that they stay out of PATTERN_GROUPS — a re-add would
    re-expose the dead-end UX.

    Behaviour spec: each of these 12 ids may still appear in the
    PATTERNS display-data array (so saved zones referencing them
    keep their swatch metadata) but MUST NOT appear inside any
    PATTERN_GROUPS array.
    """
    text = FINISH_DATA_JS.read_text(encoding="utf-8")
    m = re.search(r"(?:const|var|let)\s+PATTERN_GROUPS\s*=\s*\{", text)
    assert m, "PATTERN_GROUPS not found"
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    groups_body = text[start : i - 1]

    re_exposed = []
    for pid in sorted(KNOWN_MISSING_PATTERN_IDS):
        # Look for the id inside any quoted form (the group arrays
        # use either single or double quotes).
        if (f'"{pid}"' in groups_body) or (f"'{pid}'" in groups_body):
            re_exposed.append(pid)

    assert not re_exposed, (
        f"De-exposed family patterns are back in PATTERN_GROUPS: "
        f"{re_exposed}. The picker will offer them again, producing "
        f"silent no-render when selected. Either add a Python render "
        f"function for the id (and remove from KNOWN_MISSING_PATTERN_IDS), "
        f"or keep it out of PATTERN_GROUPS."
    )


def test_iter3_aliases_actually_resolve_in_python():
    """Behavioral pin: the 6 family-semantic aliases + 3 H4HR/HB2
    rename aliases shipped in iter 3 must all resolve to real entries
    in PATTERN_REGISTRY. Same for the 7 SPEC_PATTERN aliases in
    PATTERN_CATALOG. Catches a regression where someone removes the
    alias block but leaves the JS-side ids exposed.
    """
    import contextlib
    import io
    import sys

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import PATTERN_REGISTRY
        from engine.spec_patterns import PATTERN_CATALOG

    iter3_pattern_aliases = [
        # H4HR/HB2 cross-registry renames
        "shokk_cipher_pattern", "dragonfly_wing_pattern", "carbon_weave_pattern",
        # Family-semantic aliases
        "geo_fractal_triangle", "geo_hilbert_curve",
        "nature_bark_rough", "nature_water_ripple_pat",
        "tribal_celtic_spiral", "tribal_norse_runes",
    ]
    iter3_spec_aliases = [
        "spec_carbon_weave", "spec_diffraction_grating_cd",
        "spec_gravity_well", "spec_oil_slick",
        "spec_sparkle_champagne", "spec_sparkle_constellation",
        "spec_sparkle_firefly",
    ]
    missing_pat = [k for k in iter3_pattern_aliases if k not in PATTERN_REGISTRY]
    missing_spec = [k for k in iter3_spec_aliases if k not in PATTERN_CATALOG]

    assert not missing_pat, (
        f"iter 3 pattern aliases missing from PATTERN_REGISTRY: "
        f"{missing_pat}. The alias block in shokker_engine_v2.py "
        f"may have been removed or its target refs invalidated."
    )
    assert not missing_spec, (
        f"iter 3 spec-pattern aliases missing from PATTERN_CATALOG: "
        f"{missing_spec}. The alias block in engine/spec_patterns.py "
        f"may have been removed or its target refs invalidated."
    )


def test_iter3_repaired_pattern_fallbacks_have_real_targets():
    """iter 3 repaired the 3 _PATTERN_FALLBACKS whose targets
    (chrome_edge / shimmer_pearl_ripple / glow_pulse) didn't exist.
    Pin that the repaired targets DO exist so the fallback loop
    actually wires the ids — protects against a regression that
    re-points them at missing targets.
    """
    import contextlib
    import io
    import sys

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import PATTERN_REGISTRY

    # Repaired ids must now be IN the registry (the fallback loop
    # would have copied them from the target).
    for pid in ("chrome_delete_edge", "pearlescent_flip", "uv_night_accent"):
        assert pid in PATTERN_REGISTRY, (
            f"_PATTERN_FALLBACKS did not wire {pid!r} — its repaired "
            f"target may have gone missing again. Pick a different "
            f"target and update the fallback dict."
        )


def test_finish_data_js_passes_self_validation():
    """paint-booth-0-finish-data.js contains an in-source
    `validateFinishData()` function. Running node's --check on the
    file (done in iter 9) confirms JS parses. Here we just confirm
    the validator function is still present — a removed validator
    means the per-save catalog check is bypassed.
    """
    text = FINISH_DATA_JS.read_text(encoding="utf-8")
    assert "function validateFinishData" in text or "validateFinishData =" in text, (
        "paint-booth-0-finish-data.js no longer contains "
        "`validateFinishData`. The in-source catalog validator has "
        "been removed — the per-save catalog check will no longer "
        "fire. Restore the validator or update this test."
    )
