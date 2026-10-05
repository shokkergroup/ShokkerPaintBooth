"""Regression guardrail — every JS payload-builder that constructs
zone payloads for the engine must emit `region_mask`, `spatial_mask`,
AND `source_layer_mask` for any zone that has them set.

## Context (Iter 6, 6h Alpha-hardening run, 2026-04-23)

The painter-facing render flows in `paint-booth-5-api-render.js` are:

  - `doRender()`             → `buildServerZonesForRender(zones)`
  - `doExportToPhotoshop()`  → `buildServerZonesForRender(zones)`
  - `doSeasonRender()`       → its own inline mapper
  - `doFleetRender()`        → its own inline mapper

Each mapper turns the JS `zones[]` array into a server payload. For
zones the painter has restricted via `regionMask` / `spatialMask` /
`sourceLayer`, the mapper is responsible for emitting the
corresponding `region_mask` / `spatial_mask` / `source_layer_mask`
payload field. If the field is missing, the engine treats the zone
as UNRESTRICTED — silently painting it across the whole car body
instead of inside the restriction.

### Pre-Iter-6 silent painter-trust violation

A 2026-04-18 audit (Bockwinkel MARATHON #27) caught `doSeasonRender`
emitting NO restriction fields. That was patched. Two years later
(this run, Iter 5 audit) the same bug class was discovered in
`doFleetRender` — never patched. Painters who restricted a zone to a
PSD layer or region mask, then hit "Fleet Render", saw every car in
the fleet rendered with the zone painted across the WHOLE car body.

### Iter 6 fix

The exact emission block from `doSeasonRender:1998-2040` was copied
verbatim into `doFleetRender:1806`, including the dangling-source
fail-closed contract (empty all-zero mask + `console.warn` +
throttled `showToast` keyed on zone name).

### Post-Iter-6 refactor (region/spatial → `_encodeZoneApplyMasks`)

The region_mask + spatial_mask emission was subsequently extracted out
of each builder's inline body into a single shared helper,
`_encodeZoneApplyMasks(zoneObj, z)` (paint-booth-5-api-render.js:33).
The helper assigns `zoneObj.region_mask` (when `regionMask` is set and
`useRegion` is on) and `zoneObj.spatial_mask` (when `spatialMask` is
set). All three inline-mapper builders (`doFleetRender`,
`doSeasonRender`, `buildServerZonesForRender`) now satisfy the
region/spatial restriction contract by DELEGATING to this helper —
they call `_encodeZoneApplyMasks(zoneObj, z)` rather than inlining
`zoneObj.region_mask = ...` / `zoneObj.spatial_mask = ...`.

`source_layer_mask` was NOT moved into the helper — it carries its own
dangling-source fail-closed contract and is still emitted inline in
each builder body. So the contract is now split:

  - region_mask / spatial_mask  → emitted by `_encodeZoneApplyMasks`
                                   (builders satisfy via delegation)
  - source_layer_mask           → still inline in each builder body

The guardrail below therefore accepts delegation (a call to the
helper) as satisfying the helper-owned fields, AND separately pins the
helper body itself so the genuine emission can't silently vanish.

### What this test pins

  1. All named JS inline-mapper builders (`doRender` via
     `buildServerZonesForRender`, `doExportToPhotoshop` ditto,
     `doSeasonRender`, `doFleetRender`) reference all 3 restriction-mask
     field names — region/spatial via delegation to
     `_encodeZoneApplyMasks`, source_layer_mask inline.
  2. The `_encodeZoneApplyMasks` helper body genuinely assigns
     `zoneObj.region_mask` and `zoneObj.spatial_mask` (the emission
     didn't disappear when it was extracted from the builders).
  3. All builders carry the dangling-source fail-closed contract
     (the `_SPB_DANGLING_SOURCE_TOASTED` toast guard or equivalent).
  4. `doFleetRender` specifically emits the source_layer_mask field and
     delegates the region/spatial fields. Pre-Iter-6 this would have
     failed on all 3.
  5. The emission counts in `doFleetRender` match the canonical
     reference (`doSeasonRender`) — i.e. the fix wasn't a partial
     copy that drifted out of parity.

If this test fires:
  - A future edit removed restriction-mask emission from the helper or
    stopped a builder from delegating to it → painters lose the
    restriction. Restore the `_encodeZoneApplyMasks(zoneObj, z)` call
    and/or the helper body.
  - A FIFTH builder was added without the emission block → add it,
    update this test's BUILDER list.
  - The dangling-source toast guard regressed → painters silently lose
    zones when their PSD layer is gone.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
JS_FILE = REPO_ROOT / "paint-booth-5-api-render.js"


@pytest.fixture(scope="module")
def js_text():
    return JS_FILE.read_text(encoding="utf-8")


def _slice_function_body(text, fn_signature_regex):
    """Extract the body of a JS function by matching its signature line
    and walking the brace count until balanced. Returns the body text
    including the outer braces. Returns None if the function isn't
    found or the brace match fails (defensive: never throws)."""
    m = re.search(fn_signature_regex, text)
    if not m:
        return None
    start = text.find("{", m.end())
    if start < 0:
        return None
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    return None


# Each entry: builder display name → regex for function signature.
BUILDERS = [
    ("doFleetRender",                r"async\s+function\s+doFleetRender\s*\("),
    ("doSeasonRender",               r"async\s+function\s+doSeasonRender\s*\("),
    ("buildServerZonesForRender",    r"function\s+buildServerZonesForRender\s*\("),
    # doExportToPhotoshop delegates to buildServerZonesForRender — its
    # own body doesn't inline the restriction-mask emission. Covered
    # transitively via the buildServerZonesForRender check.
]

REQUIRED_FIELDS = ("region_mask", "spatial_mask", "source_layer_mask")

# Post-Iter-6 refactor: region_mask + spatial_mask emission was extracted
# out of each builder's inline body into the shared `_encodeZoneApplyMasks`
# helper. Builders now satisfy these two fields by DELEGATING to the helper
# (a call to `_encodeZoneApplyMasks(zoneObj, z)`) rather than inlining the
# assignment. source_layer_mask carries its own dangling-source contract and
# is still emitted inline in each builder body.
HELPER_OWNED_FIELDS = ("region_mask", "spatial_mask")
INLINE_FIELDS = ("source_layer_mask",)
# The name of the shared helper that owns region/spatial emission and the
# call form the builders use to delegate to it.
APPLY_MASKS_HELPER = "_encodeZoneApplyMasks"
APPLY_MASKS_DELEGATION = "_encodeZoneApplyMasks(zoneObj, z)"


@pytest.mark.parametrize("builder_name,sig_regex", BUILDERS)
def test_builder_emits_all_three_restriction_fields(js_text, builder_name, sig_regex):
    """Every named JS builder must satisfy all 3 restriction-mask fields.

    Post-Iter-6 the region_mask + spatial_mask emission was extracted into
    the shared `_encodeZoneApplyMasks` helper, so a builder satisfies those
    two fields by DELEGATING to the helper (calling
    `_encodeZoneApplyMasks(zoneObj, z)`) instead of inlining the assignment.
    source_layer_mask is still emitted inline in each builder body.

    Pre-Iter-6 doFleetRender failed this for all 3 fields — that was the
    exact silent-no-op bug. The helper's own emission is pinned separately
    by test_apply_masks_helper_emits_region_and_spatial below, so accepting
    delegation here does NOT weaken the guardrail to something trivially
    true."""
    body = _slice_function_body(js_text, sig_regex)
    assert body is not None, (
        f"{builder_name}: could not locate function body in "
        f"{JS_FILE.name}. Did the function get renamed or deleted?"
    )
    # Helper-owned fields: builder must delegate to _encodeZoneApplyMasks.
    assert APPLY_MASKS_DELEGATION in body, (
        f"{builder_name} does not delegate region/spatial mask emission to "
        f"the shared helper (no `{APPLY_MASKS_DELEGATION}` call in its "
        f"body). Pre-fix bug class: zones the painter restricted via "
        f"regionMask / spatialMask will be silently UNRESTRICTED in this "
        f"builder's render path — every car/zone painted across the WHOLE "
        f"body. Restore the `{APPLY_MASKS_HELPER}` call (or inline the "
        f"region_mask + spatial_mask emission block from the helper)."
    )
    # source_layer_mask is still inline in each builder body.
    for field in INLINE_FIELDS:
        assert f"zoneObj.{field}" in body, (
            f"{builder_name} body does not assign zoneObj.{field}. "
            f"Pre-fix bug class: zones that the painter restricted via "
            f"{field.replace('_', '')} will be silently UNRESTRICTED in "
            f"this builder's render path. Restore the emission block "
            f"from doSeasonRender."
        )


def test_apply_masks_helper_emits_region_and_spatial(js_text):
    """The region_mask + spatial_mask emission that used to live inline in
    each builder was extracted into `_encodeZoneApplyMasks`. Pin the helper
    body so the genuine emission can't silently vanish when builders only
    delegate to it. This is what keeps the delegation-accepting builder
    test above meaningful rather than trivially true."""
    body = _slice_function_body(
        js_text, rf"function\s+{APPLY_MASKS_HELPER}\s*\("
    )
    assert body is not None, (
        f"{APPLY_MASKS_HELPER}: could not locate helper body in "
        f"{JS_FILE.name}. Region/spatial mask emission was extracted into "
        f"this helper — if it's gone, every builder that delegates to it "
        f"now emits no region/spatial mask and silently broadens every "
        f"restricted zone."
    )
    for field in HELPER_OWNED_FIELDS:
        assert f"zoneObj.{field}" in body, (
            f"{APPLY_MASKS_HELPER} body does not assign zoneObj.{field}. "
            f"All inline-mapper builders delegate region/spatial emission "
            f"to this helper; if it no longer assigns {field}, every zone "
            f"the painter restricted via {field.replace('_mask', 'Mask')} "
            f"is silently UNRESTRICTED across all render paths at once."
        )


@pytest.mark.parametrize("builder_name,sig_regex", BUILDERS)
def test_builder_carries_dangling_source_failclosed_contract(js_text, builder_name, sig_regex):
    """Every builder that emits source_layer_mask must also carry the
    dangling-source fail-closed contract: when the painter references
    a sourceLayer that no longer exists in _psdLayers, the builder
    must emit an EMPTY mask (so the engine paints nothing) and surface
    a warning, NOT silently fall through to no-mask (which would
    silently broaden the zone)."""
    body = _slice_function_body(js_text, sig_regex)
    assert body is not None, f"{builder_name}: function body not found"
    # The fail-closed contract is detectable by the throttled-toast
    # guard variable name. All 3 builders that emit source_layer_mask
    # use the same `_SPB_DANGLING_SOURCE_TOASTED` window key.
    assert "_SPB_DANGLING_SOURCE_TOASTED" in body, (
        f"{builder_name} does not carry the dangling-source fail-closed "
        f"contract (`_SPB_DANGLING_SOURCE_TOASTED` not present). When "
        f"the painter's PSD source layer is gone, this builder will "
        f"silently broaden the zone. Restore from doSeasonRender."
    )


def test_doFleetRender_emission_count_matches_canonical(js_text):
    """Negative-control: count the field-assignment occurrences in
    doFleetRender vs doSeasonRender (the canonical reference). If the
    fleet copy diverges, somebody applied a partial fix or the
    canonical site changed.

    Post-Iter-6 the region/spatial assignment lives in the shared
    `_encodeZoneApplyMasks` helper, so the comparable inline signal for
    those two fields is the delegation call (both builders should make
    exactly one). source_layer_mask is still inline, so its raw
    assignment count is compared directly."""
    fleet = _slice_function_body(js_text, r"async\s+function\s+doFleetRender\s*\(")
    season = _slice_function_body(js_text, r"async\s+function\s+doSeasonRender\s*\(")
    assert fleet is not None and season is not None
    # source_layer_mask: still inline — compare raw assignment counts.
    for field in INLINE_FIELDS:
        fleet_n = fleet.count(f"zoneObj.{field}")
        season_n = season.count(f"zoneObj.{field}")
        assert fleet_n == season_n, (
            f"doFleetRender emits zoneObj.{field} {fleet_n} time(s) but "
            f"doSeasonRender emits it {season_n} time(s). Fix drifted from "
            f"the canonical block."
        )
    # region/spatial: now delegated — compare the helper-call count, and
    # require both builders to actually make the call (>= 1), so the
    # parity check can't be satisfied by neither builder delegating.
    fleet_deleg = fleet.count(APPLY_MASKS_DELEGATION)
    season_deleg = season.count(APPLY_MASKS_DELEGATION)
    assert fleet_deleg >= 1 and season_deleg >= 1, (
        f"region/spatial mask delegation missing: doFleetRender makes "
        f"{fleet_deleg} `{APPLY_MASKS_DELEGATION}` call(s), doSeasonRender "
        f"{season_deleg}. Both builders must delegate to the shared helper."
    )
    assert fleet_deleg == season_deleg, (
        f"doFleetRender delegates region/spatial emission "
        f"{fleet_deleg} time(s) but doSeasonRender does so {season_deleg} "
        f"time(s). Fix drifted from the canonical block."
    )


def test_doFleetRender_uses_visible_contribution_mask_helper(js_text):
    """The dangling-source contract emits an empty mask; the
    happy-path emits via `getLayerVisibleContributionMask`. Pin both
    code paths in doFleetRender so a future edit can't accidentally
    delete the happy-path branch and leave only the empty-mask
    branch (which would BREAK every restricted zone)."""
    fleet = _slice_function_body(js_text, r"async\s+function\s+doFleetRender\s*\(")
    assert fleet is not None
    assert "getLayerVisibleContributionMask" in fleet, (
        "doFleetRender lost its happy-path mask emission "
        "(getLayerVisibleContributionMask reference missing). Every "
        "painter with a working source-layer restriction would now get "
        "an empty mask + zone painting nothing. Restore from doSeasonRender."
    )
    assert "_emptyMask" in fleet, (
        "doFleetRender lost its dangling-source empty-mask branch. "
        "Painters whose PSD source layer is missing would silently get "
        "the zone painted across the WHOLE car body. Restore from "
        "doSeasonRender."
    )


def test_no_5th_unaccounted_builder_with_partial_emission(js_text):
    """Defensive sanity: if a 5th `do*Render` function appears in this
    file with its own zone-mapping inline (i.e., not delegating to
    buildServerZonesForRender), the test list above must be updated to
    cover it. This test fires on every new builder-style function so a
    future contributor can't silently add a fleet-bug-class regression."""
    # Match every `async function do<Name>Render(` declaration in the file.
    pattern = re.compile(r"async\s+function\s+(do[A-Za-z]+Render)\s*\(")
    found = set(pattern.findall(js_text))
    # Known + accounted-for set:
    accounted = {"doFleetRender", "doSeasonRender"}
    # Builders that delegate to buildServerZonesForRender (no inline mapper):
    delegating = {"doExportToPhotoshop"} & found  # may not be present
    # Anything else triggers a hard failure.
    extra = found - accounted - delegating
    if extra:
        # Allow it ONLY if its body contains buildServerZonesForRender —
        # i.e. it delegates and doesn't need its own emission block.
        unaccounted = []
        for name in sorted(extra):
            body = _slice_function_body(js_text, rf"async\s+function\s+{name}\s*\(")
            if body and "buildServerZonesForRender" in body:
                continue  # delegates to canonical builder — safe
            unaccounted.append(name)
        assert not unaccounted, (
            f"New builder function(s) found that neither delegate to "
            f"buildServerZonesForRender nor inline the restriction-mask "
            f"emission block: {unaccounted}. Audit each for the same bug "
            f"class as doFleetRender (Iter 5 finding) and either delegate "
            f"or copy the emission block, then add to BUILDERS list above."
        )
