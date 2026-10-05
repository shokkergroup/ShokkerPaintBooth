"""Regression guardrail — picking a base must NOT flip the zone's
``baseColorMode`` away from ``'source'`` when the base belongs to a
no-auto-color group.

## Context — painter-reported state-mutation bug, 2026-04-22

Painter's screenshot showed Pearl (Foundation) painting pearl-grey
across the zone's paintable area, overwriting the painter's picked
colors. Bockwinkel traced it to
``paint-booth-2-state-zones.js::_spbGetBaseGroup``. That function
built an inverse lookup (``_SPB_BASE_GROUP_LOOKUP[id] = groupName``)
with OVERWRITE semantics — so a base that lives in multiple groups
(e.g. ``f_metallic`` is in both ``'Foundation'`` and
``'Reference Foundations'``) ended up labelled with the LAST
iterated group because JS object keys preserve insertion order and
``'Reference Foundations'`` is declared after ``'Foundation'``.

That wrong label then escaped the ``_SPB_NO_AUTO_COLOR_GROUPS``
gate, causing ``_spbApplyPickedBaseToZone`` to set
``zone.baseColorMode = 'solid'`` and
``zone.baseColor = base.swatch`` — painting the base's display
swatch (pearl-grey, blue-grey, etc.) over the painter's paint.

The fix (2026-04-22):
  - ``_spbGetBaseGroup`` preserves the FIRST group found, not the last.
  - ``'Reference Foundations'`` added to ``_SPB_NO_AUTO_COLOR_GROUPS``
    as belt-and-suspenders.

## What this test pins

Invokes the upstream V8 harness
(``tests/_runtime_harness/base_color_mode_auto_fill.mjs``) that
simulates picking every base in every no-auto-color group and
asserts the invariant:

    after _spbApplyPickedBaseToZone(zone={baseColorMode:'source'}, bid)
        zone.baseColorMode === 'source'
        zone.baseColor === null
        zone._autoBaseColorFill !== true

for every bid in every group listed in
``_SPB_NO_AUTO_COLOR_GROUPS``.

If the harness exits non-zero, one of the no-auto-color groups is
leaking — picking a base there would clobber the painter's colors.
"""

import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "base_color_mode_auto_fill.mjs"


def test_base_pick_does_not_autofill_for_no_auto_color_groups():
    """Exercise the V8 harness: for every base in every group listed
    in ``_SPB_NO_AUTO_COLOR_GROUPS`` (Foundation, Reference Foundations,
    Enhanced Foundation, Candy & Pearl, Chrome & Mirror, etc.),
    calling ``_spbApplyPickedBaseToZone`` on a fresh-source zone must
    leave ``baseColorMode='source'`` and ``baseColor=null``.

    Failure mode this catches:
        - Someone reintroduces the overwrite bug in
          ``_spbGetBaseGroup``.
        - Someone removes a group from ``_SPB_NO_AUTO_COLOR_GROUPS``
          without painter approval.
        - Someone adds a new "Foundation"-style group to
          ``BASE_GROUPS`` without adding it to the no-auto-color set.
    """
    try:
        subprocess.run(
            ["node", "--version"], capture_output=True, check=True, timeout=10
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pytest.skip("node not available; skipping V8 harness")

    assert HARNESS.exists(), (
        f"V8 harness missing at {HARNESS} — recreate it to keep this "
        f"ratchet meaningful."
    )

    result = subprocess.run(
        ["node", str(HARNESS)],
        capture_output=True,
        timeout=60,
        cwd=str(REPO),
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    assert result.returncode == 0, (
        f"V8 harness reported auto-fill leak (exit {result.returncode}).\n"
        f"This means picking a base from a no-auto-color group is "
        f"still flipping the zone's baseColorMode and painting over "
        f"the painter's colors.\n\n"
        f"stdout:\n{stdout}\n\n"
        f"stderr:\n{stderr}"
    )

    # Sanity: harness must actually have checked something.
    assert "Checked" in stdout and "no-auto-color groups" in stdout, (
        f"V8 harness output looks malformed — did the structure of the "
        f"harness drift?\n{stdout}"
    )

    # Extract the checked-count number so the test fails loudly if the
    # coverage ever shrinks silently.
    import re
    m = re.search(r"Checked (\d+) bases across (\d+) no-auto-color groups", stdout)
    assert m, f"Could not parse coverage line:\n{stdout}"
    bases_checked = int(m.group(1))
    groups_checked = int(m.group(2))
    # Current baseline: 242 bases × 16 groups. Allow shrink down to 200
    # for catalog churn but ratchet against big silent drops.
    # 2026-09-30: Foundation (20) + Foundation EFX (46)
    assert bases_checked >= 60, (
        f"V8 harness only checked {bases_checked} bases (was 242 at "
        f"pin time). Either the catalog shrank significantly or the "
        f"harness is filtering something it shouldn't."
    )
    # 2026-09-30: only the Foundation shelves are source-only by owner law (others adopt colour, 07-08)
    assert groups_checked == 2, (
        f"V8 harness only checked {groups_checked} no-auto-color groups "
        f"(was 16). Someone may have removed groups from "
        f"_SPB_NO_AUTO_COLOR_GROUPS — review for painter impact."
    )
