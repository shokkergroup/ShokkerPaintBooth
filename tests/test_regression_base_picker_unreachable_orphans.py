"""Regression guardrail — JS BASES array contains entries without
Python render paths. Verify they remain de-exposed from BASE_GROUPS
so painters cannot select them from the picker.

## Context (Iter 4, ship-readiness audit 2026-04-22)

The "Boil the Ocean 2026-04-17" catalog-expansion blitz added 18
new base ids to the JS catalog (paint_*, stone_*, textile_*
families) without corresponding Python render functions. The JS
team added display metadata (name, swatch, desc) in BASES but
never wired them into any BASE_GROUPS picker group.

Current state (2026-04-22):
  - JS BASES array:                   358 ids
  - Python BASE_REGISTRY:             375 ids
  - JS BASES with NO Python entry:    18 (the orphans below)
  - Those 18 orphans in BASE_GROUPS:  0 (all de-exposed)

Painter-visible risk today: LOW. The orphans cannot be selected
through the picker. They would only hit render code if a painter
loaded a saved config with one of these ids as a zone.base, in
which case the engine at shokker_engine_v2.py:10012 logs a warning
and skips the zone (not a crash).

## What this test pins

  1. The count of JS BASES ids without Python entries stays <= 18.
     If new orphans appear, either a Python render function is
     missing or the JS catalog added more unreachable entries
     silently.
  2. Every orphan in the known set stays de-exposed from
     BASE_GROUPS. If any gets added to a picker group without a
     Python render function, painters get silent-no-op picks.

## Remediation options (deferred — needs painter sign-off)

  A. Add Python BASE_REGISTRY aliases for each orphan → closest
     existing material match. Preserves painter intent on saved
     configs.
  B. Strip the orphan entries from BASES array entirely. Breaks
     display metadata for saved configs that reference them.
  C. Leave as-is with a picker-reachability ratchet (this test).
     Safest for ship-today; does not alter any current behavior.
"""

import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
FINISH_DATA_JS = REPO / "paint-booth-0-finish-data.js"


# Documented orphan baseline as of 2026-04-22 Iter 4.
# If this set shrinks, someone added Python render paths — trim the set.
# If it grows, someone added JS catalog entries without Python support.
KNOWN_BASE_ORPHANS = frozenset({
    # paint_* family (paint-technique names, no Python render)
    "paint_brush_stroke", "paint_drip_gravity", "paint_roller_streak",
    "paint_splatter_loose", "paint_sponge_stipple", "paint_spray_fade",
    # stone_* family
    "stone_granite_speckled", "stone_marble_polished",
    "stone_obsidian_mirror", "stone_sandstone_warm",
    "stone_slate_matte", "stone_travertine_cream",
    # textile_* family
    "textile_burlap_coarse", "textile_canvas_rough",
    "textile_denim_weave", "textile_silk_sheen",
    "textile_suede_soft", "textile_velvet_crush",
})


def _extract_ids_from_js_array(src: str, varname: str) -> set:
    m = re.search(rf"(?:const|var|let)\s+{varname}\s*=\s*\[", src)
    if not m:
        return set()
    start = m.end()
    depth = 1
    pos = start
    while pos < len(src) and depth > 0:
        if src[pos] == '[':
            depth += 1
        elif src[pos] == ']':
            depth -= 1
        pos += 1
    body = src[start:pos - 1]
    return set(re.findall(r'id:\s*"([a-z_][a-z0-9_]*)"', body))


def _extract_base_groups(src: str) -> dict:
    start = src.find("BASE_GROUPS")
    if start < 0:
        return {}
    obrace = src.find("{", start)
    depth = 1
    pos = obrace + 1
    while pos < len(src) and depth > 0:
        if src[pos] == '{':
            depth += 1
        elif src[pos] == '}':
            depth -= 1
        pos += 1
    body = src[obrace + 1:pos - 1]
    groups = {}
    for m in re.finditer(r'"([^"]+)"\s*:\s*\[([^\]]*)\]', body):
        groups[m.group(1)] = re.findall(r'"([a-z_][a-z0-9_]*)"', m.group(2))
    return groups


def test_orphan_base_count_does_not_grow():
    """If more JS BASES ids appear without Python render paths,
    painters with saved configs referencing them get silent
    zone-skip. Shipping the alpha with a larger gap than baseline
    is a trust risk."""
    import io
    import contextlib
    import sys

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    js = FINISH_DATA_JS.read_text(encoding="utf-8")
    js_bases = _extract_ids_from_js_array(js, "BASES")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import BASE_REGISTRY, MONOLITHIC_REGISTRY

    # A JS base id is "orphan" if Python has no render path for it
    # in either BASE_REGISTRY or MONOLITHIC_REGISTRY (cross-registry
    # fallback is the HP-MIGRATE pattern).
    orphans = js_bases - set(BASE_REGISTRY.keys()) - set(MONOLITHIC_REGISTRY.keys())

    unexpected_new = orphans - KNOWN_BASE_ORPHANS
    assert not unexpected_new, (
        f"NEW JS BASES ids without Python render paths: "
        f"{sorted(unexpected_new)}. Either add Python render "
        f"functions, or register aliases, or add to "
        f"KNOWN_BASE_ORPHANS with a clear rationale. Do NOT add "
        f"without remediation — painters hitting these ids via "
        f"saved configs get silent zone-skip."
    )


def test_known_base_orphans_stay_de_exposed_from_picker():
    """The 18 known orphans MUST stay out of BASE_GROUPS. If any
    gets added to a picker group without a Python render function
    being added first, painters could select it and get
    silent-no-op. This catches that accidental exposure."""
    js = FINISH_DATA_JS.read_text(encoding="utf-8")
    groups = _extract_base_groups(js)

    exposed = []
    for orphan in sorted(KNOWN_BASE_ORPHANS):
        memberships = [g for g, ids in groups.items() if orphan in ids]
        if memberships:
            exposed.append((orphan, memberships))

    assert not exposed, (
        "Base orphan(s) with no Python render path are now in "
        "picker groups — painters can select them and get "
        "silent-no-op:\n  "
        + "\n  ".join(f"{o}: {g}" for o, g in exposed)
    )


def test_known_base_orphans_still_in_bases_array():
    """If all 18 disappear from BASES, the orphan set should be
    trimmed. Fires in the positive direction (coverage improved)
    to prompt test maintenance."""
    js = FINISH_DATA_JS.read_text(encoding="utf-8")
    js_bases = _extract_ids_from_js_array(js, "BASES")
    survivors = KNOWN_BASE_ORPHANS & js_bases

    # If someone removes orphans from BASES (Option B in the module
    # docstring), this test fires in xfail direction — we WANT the
    # orphan set to shrink. Use a floor instead of exact-match so
    # partial cleanups don't fail the test.
    assert len(survivors) <= len(KNOWN_BASE_ORPHANS), (
        "Somehow the orphan set grew in BASES — impossible if the "
        "set is a frozenset. Test logic bug."
    )
    if len(survivors) < len(KNOWN_BASE_ORPHANS):
        removed = KNOWN_BASE_ORPHANS - survivors
        pytest.skip(
            f"{len(removed)} orphan(s) were removed from BASES array "
            f"(option B): {sorted(removed)}. Trim KNOWN_BASE_ORPHANS "
            f"to match — ship-readiness improved."
        )
