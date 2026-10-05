"""Regression guardrail — picking a base from a "rich paint_fn" group MUST
NOT auto-fill the zone's base color with the swatch hex (flat solid override).

## Context (2026-04-24)

`paint-booth-2-state-zones.js` defines `_SPB_NO_AUTO_COLOR_GROUPS` — the set
of BASE_GROUPS whose members should NOT trigger the swatch-as-solid-color
auto-fill on pick. Bases in OTHER groups DO auto-fill (intentional for color
swatches). The set must include every group whose members render via a
distinctive paint_fn (Foundation, Iridescent Insects, PARADIGM, Carbon
fibers, Chrome, Specials, etc.).

### Pre-2026-04-24 painter-reported bug

5 BASE_GROUPS were MISSING from `_SPB_NO_AUTO_COLOR_GROUPS`:
  - 'Iridescent Insects' (firefly_glow, beetle_jewel, butterfly_morpho, ...)
  - 'PARADIGM' (sci-fi/exotic finishes)
  - 'Textile-Inspired'
  - 'Stone & Mineral'
  - 'Paint Technique'

When a painter picked Firefly Glow (or any other ID in these groups) as the
PRIMARY base, the JS auto-set:
  zone.baseColor = '#88cc22'  (firefly swatch)
  zone.baseColorMode = 'solid'

The engine then rendered firefly_glow's distinctive paint (dark body + glow
zones) and IMMEDIATELY OVERWROTE it with a flat #88cc22 yellow-green wash via
`_apply_base_color_override(mode='solid', ...)`. Painter saw flat yellow-green,
not firefly's actual look. Symptom they reported: "Special base doesn't work."

### Fix

Add the 5 missing groups to `_SPB_NO_AUTO_COLOR_GROUPS`. Painters who actually
want a flat tint can still manually switch baseColorMode to 'solid' from the
zone-detail UI.

## What this test pins

  1. Every BASE_GROUP whose members have rich paint_fns (per the canonical
     `_SPB_NO_AUTO_COLOR_GROUPS` list) is present in the JS source.
  2. The 5 specific groups added in the 2026-04-24 fix are explicitly checked
     by name so a future contributor can't accidentally drop one.

If this test fires:
  - Someone removed a group from `_SPB_NO_AUTO_COLOR_GROUPS` → painters who
    pick from that group will lose their material's distinctive look as it
    gets silently overwritten by the swatch hex.
  - The fix is to restore the missing group name(s).
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
JS_FILE = REPO_ROOT / "paint-booth-2-state-zones.js"


@pytest.fixture(scope="module")
def js_text():
    return JS_FILE.read_text(encoding="utf-8")


# Groups that MUST appear in _SPB_NO_AUTO_COLOR_GROUPS — these are the ones
# whose members have rich paint_fns and shouldn't be flattened to the swatch.
REQUIRED_NO_AUTO_GROUPS = [
    # Foundation classes (pre-existing)
    "Foundation",
    "Foundation EFX",   # FOUNDATION ONE 2026-09-03: EFX carries its own paint
    # Material classes (pre-existing)
    "Candy & Pearl",
    "Carbon & Composite",
    "Ceramic & Glass",
    "Chrome & Mirror",
    "Exotic Metal",
    "Industrial & Tactical",
    "Metallic Standard",
    "OEM Automotive",
    "Premium Luxury",
    "Racing Heritage",
    "Satin & Wrap",
    "Weathered & Aged",
    "Extreme & Experimental",
    # 2026-04-24 painter-bug fix additions
    "Iridescent Insects",
    "PARADIGM",
    "Textile-Inspired",
    "Stone & Mineral",
    "Paint Technique",
]


def _extract_no_auto_color_groups_set(js_text):
    """Find the `const _SPB_NO_AUTO_COLOR_GROUPS = new Set([...])` declaration
    and return the list of group-name string literals inside."""
    import re
    m = re.search(
        r"const\s+_SPB_NO_AUTO_COLOR_GROUPS\s*=\s*new\s+Set\(\s*\[(.*?)\]\s*\)",
        js_text, re.DOTALL,
    )
    assert m is not None, "Could not locate `_SPB_NO_AUTO_COLOR_GROUPS = new Set([...])` declaration"
    body = m.group(1)
    # Extract every quoted-string literal (single or double quote)
    return set(re.findall(r"['\"]([^'\"]+?)['\"]", body))


def test_set_declaration_present(js_text):
    """The _SPB_NO_AUTO_COLOR_GROUPS Set declaration must exist."""
    assert "const _SPB_NO_AUTO_COLOR_GROUPS = new Set(" in js_text


@pytest.mark.parametrize("group_name", REQUIRED_NO_AUTO_GROUPS)
def test_required_group_in_no_auto_color_set(js_text, group_name):
    """Every group in the required list must be present in the Set.

    A group's absence means picking ANY base from that group will auto-fill
    the swatch hex as a flat solid color, masking the base's distinctive
    paint_fn output. Painter-reported "doesn't work" bug class."""
    groups_in_set = _extract_no_auto_color_groups_set(js_text)
    assert group_name in groups_in_set, (
        f"Group {group_name!r} is missing from `_SPB_NO_AUTO_COLOR_GROUPS`. "
        f"Painters picking bases from this group will see their material's "
        f"distinctive paint_fn output silently overwritten by a flat swatch "
        f"hex. Restore the group entry in paint-booth-2-state-zones.js."
    )


def test_no_unexpected_shrinkage(js_text):
    """The Set must contain at least 16 entries (the pre-fix baseline plus
    the 5 added in the 2026-04-24 fix). If a future edit drops below this
    count, this test fires."""
    groups_in_set = _extract_no_auto_color_groups_set(js_text)
    # 21 = 16 distinct + the 5 alternate spellings ('Candy and Pearl', etc.)
    # We pin >= 20 to allow some flexibility while catching mass deletions.
    assert len(groups_in_set) >= 20, (
        f"_SPB_NO_AUTO_COLOR_GROUPS shrunk to {len(groups_in_set)} entries "
        f"(was >= 20). Mass deletion of group entries → painters losing "
        f"distinctive material renders across many groups."
    )


def test_iridescent_insects_specifically_pinned(js_text):
    """Painter-reported regression on 2026-04-24: firefly_glow rendering
    flat-yellow-green instead of its distinctive dark+glow look. Pin
    'Iridescent Insects' specifically by name + make the test fire if
    someone removes it."""
    groups_in_set = _extract_no_auto_color_groups_set(js_text)
    assert "Iridescent Insects" in groups_in_set, (
        "'Iridescent Insects' is missing — firefly_glow / beetle_jewel / "
        "butterfly_morpho / dragonfly_wing / etc. will all auto-fill their "
        "swatch hex as a flat solid color, masking the distinctive insect "
        "paint_fn outputs. This was the 2026-04-24 painter-reported regression."
    )
