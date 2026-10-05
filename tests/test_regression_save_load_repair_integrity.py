"""Regression guardrails for save/load/repair persistence paths.

## Context (originally: 2026-04-20 regression loop iter 8; updated
## after HEENAN OVERNIGHT fix loop 2026-04-21 iter 1)

A painter who configured a zone deliberately (an explicit `channels="C"`
on a spec pattern whose default is "MR"; a `pickerTolerance` of
exactly 0; an explicit `muted=false`) must survive a save/load
round-trip unchanged.

Audit findings on `paint-booth-2-state-zones.js`:

- **`loadConfigFromObj` (line 9207+)** — the MAIN config-load path —
  uses `??` (nullish coalescing) for all numeric/boolean/null
  persistence fields, e.g. `pickerTolerance: z.pickerTolerance ?? 40`.
  This preserves legit falsy values (tolerance=0, strength=0,
  muted=false, wear=0). Uses `||` only for fields where empty/missing
  are equivalent by design (arrays, zone name, gradient stops,
  gradient direction). **Safe — behavioral proof in
  `tests/test_runtime_load_config_falsy_values.py`.**

- **`repairZoneData` (line 11115+)** uses defensive type-guarded
  assignments: `if (typeof z.name !== 'string' || !z.name.trim())
  z.name = 'Zone'`. Defaults ONLY on type failure — never overwrites
  a valid user value. **Safe.**

- **`_migrateZoneFinishIds` (line 11043+)** rewrites only IDs present
  in the `_SPB_LEGACY_ID_MIGRATIONS` map. Unknown IDs pass through
  untouched. **Safe.**

- **`_normalizeLegacySpecPatternChannels` (line 11080+)** contains a
  KNOWN design trade-off. For legacy saves (before the
  `channelsCustomized` tracking flag was added), if
  `channels === "MR"` and the pattern's docstring-inferred default
  is NOT "MR", the channels get REWRITTEN to the pattern default.
  Modern saves with `channelsCustomized: true` preserve user choice.
  After the 2026-04-21 overnight iter 2 fix of `engine/compose.py`,
  the server-side falls back to the same docstring-inferred default
  when `channels` is absent, so the JS-side normalization is now
  only a per-load clean-up (no longer load-bearing for render
  correctness).

## Historical pre-existing persistence bugs — NOW FIXED

**UPDATE 2026-04-21 HEENAN OVERNIGHT iter 1:** the two persistence
bugs this file originally pinned as "pre-existing, not fixed" have
been fixed. History preserved below for context:

1. **Duplicate `applyPreset` function definition** — FIXED. Replaced
   by a polymorphic `applyPreset(arg)` dispatcher that routes
   `string` input to `_applyPresetById` (gallery path) and `object`
   input to `_applyPresetFromObject` (file-import path). JS
   function-declaration hoisting no longer silently shadows either
   path. Preset gallery card clicks now work.

2. **Preset-load `||` vs `??` divergence** — FIXED. The preset
   object-form helper now uses `??` for numeric/boolean persistence
   fields (pickerTolerance, scale, wear, muted, intensity), matching
   the main `loadConfigFromObj` path. Preset-authored falsy values
   (tolerance=0, etc.) now round-trip faithfully. Behavioral proof:
   `tests/test_runtime_apply_preset_dispatch.py` drives the live
   dispatcher in V8 with a realistic falsy-value preset.

## What these tests do

Pin structural invariants so a regression of the main
`loadConfigFromObj` path (switching `??` to `||` on a numeric field
and replacing tolerance=0 with 40) is caught at test time. The
companion behavioral tests in
`tests/test_runtime_apply_preset_dispatch.py` and
`tests/test_runtime_load_config_falsy_values.py` exercise the actual
JS code paths in V8 and assert end-to-end preservation.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ZONES_JS = REPO / "paint-booth-2-state-zones.js"


def _read_js():
    return ZONES_JS.read_text(encoding="utf-8")


def _find_function_body(src: str, fn_decl: str) -> str:
    """Locate `fn_decl` (e.g. 'function loadConfigFromObj') and return
    its body by brace matching. Raises if not found or unbalanced.
    """
    start = src.find(fn_decl)
    assert start >= 0, f"{fn_decl} not found in source"
    depth = 0
    end = None
    for i, c in enumerate(src[start:], start):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    assert end is not None, f"unbalanced braces starting at {fn_decl}"
    return src[start:end]


# Fields that MUST use `??` (not `||`) because falsy values are legitimate.
# If any of these get switched to `||` in loadConfigFromObj, a painter
# who sets the value to 0 or false will have it silently replaced.
FIELDS_REQUIRING_NULLISH_COALESCE = [
    # Numeric fields where 0 is legitimate
    ("pickerTolerance", "40"),
    ("patternOpacity", "100"),
    ("patternIntensity", "'100'"),
    ("scale", "1.0"),
    ("rotation", "0"),
    ("wear", "0"),
    ("baseStrength", "1"),
    ("baseSpecStrength", "1"),
    ("patternSpecMult", "1"),
    ("baseRotation", "0"),
    ("baseScale", "1.0"),
    ("baseHueOffset", "0"),
    ("baseSaturationAdjust", "0"),
    ("baseBrightnessAdjust", "0"),
    # Boolean fields where false is legitimate
    ("muted", "false"),
    ("patternFlipH", "false"),
    ("patternFlipV", "false"),
    ("baseFlipH", "false"),
    ("baseFlipV", "false"),
]


@pytest.mark.parametrize("field,default", FIELDS_REQUIRING_NULLISH_COALESCE)
def test_load_config_preserves_falsy_values_via_nullish_coalesce(field, default):
    """loadConfigFromObj (MAIN config-load path) must use `??` not
    `||` for fields where falsy values (0, false) are legitimate
    user choices. A switch to `||` silently replaces 0 with the
    default.

    This is the 'painter saved tolerance=0 and got 40 back' class
    of regression, scoped to the main config path.

    The preset-load path (applyPreset) was historically divergent
    (`||` instead of `??`) — that divergence was eliminated in the
    2026-04-21 HEENAN OVERNIGHT iter 1 fix; it's now guarded by
    `test_preset_path_uses_nullish_coalesce` below (strict `||` →
    `??` assertion) and by behavioral tests in
    `tests/test_runtime_apply_preset_dispatch.py`.
    """
    body = _find_function_body(_read_js(), "function loadConfigFromObj")

    nullish_pattern = f"{field}: z.{field} ?? {default}"
    fallback_pattern = f"{field}: z.{field} || {default}"

    assert nullish_pattern in body, (
        f"loadConfigFromObj no longer contains `{nullish_pattern}`. "
        f"If the default value changed, update this test. If the "
        f"operator was changed from `??` to `||`, that's a regression "
        f"— falsy user-set values (0, false) will now be silently "
        f"replaced with `{default}` on load."
    )
    assert fallback_pattern not in body, (
        f"loadConfigFromObj contains `{fallback_pattern}` (using `||` "
        f"instead of `??`). This is a regression: a user who saved "
        f"`{field}` as a falsy value (0 or false) will get `{default}` "
        f"back on load. Change the operator to `??` (nullish coalesce)."
    )


def test_preset_path_uses_nullish_coalesce():
    """After the 2026-04-21 HEENAN overnight iter 1 fix, the preset
    object-form helper (`_applyPresetFromObject`) must use `??` for
    all numeric/boolean persistence fields, matching the main
    `loadConfigFromObj` path. `||` would re-introduce the bug where
    preset-authored `pickerTolerance: 0`, `scale: 0`, etc. got
    silently replaced by defaults.

    Behavioral verification of this same invariant lives in
    `tests/test_runtime_apply_preset_dispatch.py`, which runs the
    real dispatcher in a V8 sandbox with a falsy-value preset and
    confirms the values round-trip.
    """
    src = _read_js()
    helper_pos = src.find("function _applyPresetFromObject")
    assert helper_pos >= 0, (
        "_applyPresetFromObject helper not found. The preset-apply "
        "path was restructured — refresh this guardrail (and the "
        "companion runtime harness at "
        "tests/_runtime_harness/apply_preset_dispatch.mjs)."
    )
    # Extract the helper body.
    depth = 0
    end = None
    for i, c in enumerate(src[helper_pos:], helper_pos):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    body = src[helper_pos:end]

    # Critical fields must use `??` (nullish) — regression of ANY to
    # `||` re-breaks the preset-author-saved-falsy-value bug.
    for field, default in FIELDS_REQUIRING_NULLISH_COALESCE:
        fallback = f"{field}: z.{field} || {default}"
        present = (
            re.search(rf"{re.escape(field)}\s*:\s*z\.{re.escape(field)}", body)
            is not None
        )
        if not present:
            continue
        assert fallback not in body, (
            f"Preset path regressed: `{fallback}` is back. This "
            f"re-introduces the bug where preset-authored falsy "
            f"values like `{field}: 0` get silently replaced by "
            f"{default}. Switch to `??` (nullish coalesce)."
        )


def test_exactly_one_applypreset_definition():
    """After the 2026-04-21 HEENAN overnight iter 1 fix, there must
    be exactly one `function applyPreset(...)` definition — the
    polymorphic dispatcher. The two internal helpers are named
    `_applyPresetById` and `_applyPresetFromObject`.

    More than one `applyPreset` re-introduces the JS hoisting bug
    where the object-form silently shadowed the ID-form and broke
    gallery clicks.
    """
    src = _read_js()
    positions = [m.start() for m in re.finditer(r"function applyPreset\b", src)]
    count = len(positions)

    assert count == 1, (
        f"Expected exactly 1 `function applyPreset` definition "
        f"(the polymorphic dispatcher). Found {count}. Either the "
        f"duplicate has been reintroduced (regression) or the "
        f"dispatcher was renamed (refresh this guardrail)."
    )
    # And confirm the two expected internal helpers are present.
    assert "function _applyPresetById" in src, (
        "_applyPresetById helper missing — the ID-form dispatch path "
        "was removed or renamed. Gallery clicks may be broken."
    )
    assert "function _applyPresetFromObject" in src, (
        "_applyPresetFromObject helper missing — the object-form "
        "dispatch path was removed or renamed. .shokker file imports "
        "may be broken."
    )


def test_repair_zone_data_only_defaults_on_type_check_failure():
    """repairZoneData must use `if (type-check fails) { field = default }`
    guards — it must NEVER unconditionally assign a default over an
    existing valid user value.
    """
    body = _find_function_body(_read_js(), "function repairZoneData")

    # Scan the forEach body for unguarded `z.X = default` assignments.
    # An unguarded assignment is one where the full line has `z.X = ...`
    # but no leading `if (` on that same line. All defaulting inside
    # repairZoneData uses the form `if (check) { z.X = default; fixed++; }`
    # on a single line — so `if (` should appear on the same line as
    # every `z.X = ...` default assignment.
    unguarded = []
    for line in body.splitlines():
        stripped = line.strip()
        # Filter to direct zone-property defaulting: `z.X = ...;`
        # Exclude: property-read comparisons (z.X === ...), migration
        # function calls, counter increments.
        if re.match(r"z\.\w+\s*=\s*[^=]", stripped) and "if (" not in line:
            unguarded.append(stripped)

    assert not unguarded, (
        "repairZoneData contains unguarded `z.X = default` assignments:\n"
        + "\n".join(f"  {u}" for u in unguarded)
        + "\n\nEvery default must be behind an `if (type-check fails) "
        "{ ... }` guard, or repairZoneData will clobber valid user values."
    )


def test_repair_preserves_explicit_tolerance_zero():
    """The guard for pickerTolerance must be `== null || isNaN(...)`,
    NOT `!z.pickerTolerance`. The latter would treat tolerance=0
    as missing and replace it with 40.
    """
    body = _find_function_body(_read_js(), "function repairZoneData")
    # Find the pickerTolerance guard line.
    tol_lines = [l for l in body.splitlines() if "pickerTolerance" in l and "= 40" in l]
    assert tol_lines, (
        "repairZoneData no longer contains a `pickerTolerance = 40` "
        "guard line. The repair has been restructured — update this "
        "test."
    )
    guard_line = tol_lines[0]
    assert "== null" in guard_line and "isNaN" in guard_line, (
        f"repairZoneData guard is `{guard_line.strip()}`. Expected a "
        f"`== null || isNaN(...)` check. If the guard was switched to "
        f"`!z.pickerTolerance`, tolerance=0 is falsely replaced with 40."
    )


def test_normalize_spec_channels_respects_customized_flag():
    """_normalizeLegacySpecPatternChannels must check
    `entry.channelsCustomized == null` before considering a legacy
    rewrite. A modern save has `channelsCustomized: true` and MUST
    be left alone regardless of the channels value.
    """
    body = _find_function_body(
        _read_js(), "function _normalizeLegacySpecPatternChannels"
    )

    assert "channelsCustomized == null" in body, (
        "_normalizeLegacySpecPatternChannels no longer gates its legacy "
        "rewrite behind `entry.channelsCustomized == null`. Modern "
        "saves with `channelsCustomized: true` will now be silently "
        "rewritten — user-chosen channel overrides lost."
    )
    assert "defaults.channels !== 'MR'" in body, (
        "_normalizeLegacySpecPatternChannels no longer checks "
        "`defaults.channels !== 'MR'` before rewriting a legacy `MR` "
        "entry. The normalization may have been broadened in a way "
        "that rewrites more aggressively — review."
    )


def test_normalize_spec_channels_documents_preexisting_tradeoff():
    """The known design trade-off: a legacy save with an explicit
    user-chosen `channels='MR'` on a pattern whose default is NOT
    'MR' WILL be rewritten by _normalizeLegacySpecPatternChannels.
    The painter's explicit choice is lost because legacy saves have
    no way to distinguish explicit-MR from auto-MR.

    This test does NOT assert the rewrite is correct — it just
    anchors the expected behavior so a future "let's preserve all
    legacy MR" change trips this test and gets reviewed.
    """
    body = _find_function_body(
        _read_js(), "function _normalizeLegacySpecPatternChannels"
    )
    rewrite_markers = [
        "entry.channels = defaults.channels",
        "channelsCustomized = false",
    ]
    for marker in rewrite_markers:
        assert marker in body, (
            f"Expected marker `{marker}` missing from "
            f"_normalizeLegacySpecPatternChannels. The proactive "
            f"legacy-MR rewrite may have been removed. If that's "
            f"intentional, update this test AND verify whether "
            f"compose.py's `channels='MR'` default bug (see "
            f"tests/test_regression_spec_pattern_channels.py) now "
            f"affects more painter saves."
        )


def test_migrate_finish_ids_only_rewrites_known_ids():
    """_migrateZoneFinishIds must rewrite ONLY IDs present in the
    _SPB_LEGACY_ID_MIGRATIONS map. Unknown IDs must pass through
    untouched — otherwise a painter's custom-authored finish ID
    could be silently lost.
    """
    body = _find_function_body(_read_js(), "function _migrateZoneFinishIds")

    assert "M.monolithic[zone.finish]" in body, (
        "_migrateZoneFinishIds no longer looks up finish IDs in "
        "_SPB_LEGACY_ID_MIGRATIONS.monolithic. Migration coverage "
        "may have been lost."
    )
    assert "M.pattern[entry.id]" in body, (
        "_migrateZoneFinishIds no longer guards patternStack entries "
        "by the pattern-id migration map. Unknown pattern IDs may "
        "now be mutated — review."
    )
