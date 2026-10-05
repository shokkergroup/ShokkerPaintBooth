"""Regression guardrail (iter 8, 2026-04-20 / 2026-04-21 follow-up sweep) —
.shokker preset round-trip key parity.

## Context

`paint-booth-2-state-zones.js` has two distinct save/load paths:

  1. **getConfig() / loadConfigFromObj()** — the autosave + saveConfig
     path. Comprehensive: writes ~150 zone fields, reads back ~150.
     Spot-audit (this sweep) showed schema-key parity: every field
     written is read on load. No clobber risk.

  2. **exportPreset() / _applyPresetFromObject()** — the shareable
     `.shokker` file path. INTENTIONALLY a smaller subset: it omits
     `regionMask` (car-specific raster) and the entire 5-base
     overlay tower (treated as paint defaults on import, not author
     intent). This is by design.

## What this test pins

Every key the **export side** writes into the per-zone object MUST be
either:
  (a) read back on the **import side**, OR
  (b) listed in `INTENTIONALLY_DROPPED_ON_IMPORT` with a comment
      explaining WHY the painter losing this field is acceptable.

If a NEW field is added to `exportPreset` and the import side is not
updated, this test fails — preventing silent painter-data loss
across the .shokker file boundary.

## Current confirmed clobber (documented baseline)

`rotation` — exported (line 9553: `rotation: z.rotation ?? 0`) but
NOT read on import (lines 9645-9674 omit it entirely). A painter
who shares a preset with a 45° tilted carbon-fiber pattern will
have it import at 0°. Pinned here as a known-bad baseline; a
spawn_task will be filed to fix this on the import side.

## Why a structural source-level test

A behavioral JSDOM harness (see
`tests/_runtime_harness/overnight_integration_roundtrip.mjs`)
already exists and pins the specific falsy-fidelity invariants
(tolerance=0, scale=1.0, wear=0, etc.). This test catches a
DIFFERENT class of bug: a developer adds a new exported field but
forgets to add the matching import field. The behavioral test
won't fire on that, because it doesn't enumerate every field —
this one does.
"""

import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
JS_SRC = REPO / "paint-booth-2-state-zones.js"


# --- Whitelist: fields that exportPreset emits but
#     _applyPresetFromObject INTENTIONALLY does NOT read. Each entry
#     must come with a clear "why painter losing this is acceptable"
#     comment.
#
# The current state is documented here so future drift is the only
# thing that fires the test. An ENTRY in this list is a bug-baseline,
# not an endorsement.
INTENTIONALLY_DROPPED_ON_IMPORT = {
    # Comments documenting WHY each field is dropped:
    #
    # rotation: NOT INTENTIONAL — confirmed clobber as of 2026-04-21.
    #   exportPreset writes `rotation: z.rotation ?? 0` (line ~9553),
    #   but _applyPresetFromObject (lines ~9645-9674) omits it entirely.
    #   spawn_task filed; expected to be removed from this whitelist
    #   when the import side adds `rotation: z.rotation ?? 0`.
    "rotation",
}


def _extract_object_literal_keys(src: str, fn_anchor: str, expr_anchor: str) -> set:
    """Pull the keys from an object literal inside `zones.map(z => ({...}))`
    in a JS function. Returns the set of LHS keys.
    """
    fn_start = src.find(fn_anchor)
    assert fn_start >= 0, f"function not found: {fn_anchor!r}"
    expr_start = src.find(expr_anchor, fn_start)
    assert expr_start >= 0, f"anchor not found inside fn: {expr_anchor!r}"
    # Find the {...} literal opening right after the anchor (after `({`)
    open_brace = src.find("({", expr_start)
    assert open_brace >= 0
    # Walk forward, balancing braces/parens, to find the matching close.
    depth = 0
    pos = open_brace + 1   # skip '('
    obj_open = src.find("{", pos)
    assert obj_open >= 0
    pos = obj_open
    obj_close = -1
    while pos < len(src):
        c = src[pos]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                obj_close = pos
                break
        pos += 1
    assert obj_close >= 0, "unbalanced object literal"
    body = src[obj_open + 1: obj_close]
    # Strip line comments and block comments before key extraction
    body = re.sub(r"//[^\n]*", "", body)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    # Match top-level keys: <identifier> : ...
    # We avoid nested object keys by tracking brace depth as we scan
    keys = set()
    depth = 0
    line_start = 0
    for i, c in enumerate(body):
        if c == "{" or c == "[":
            depth += 1
        elif c == "}" or c == "]":
            depth -= 1
        elif c == "\n":
            if depth == 0:
                line = body[line_start:i].strip()
                # Match `key: ...`  or  `key,`  (shorthand, rare here)
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*[:,]", line)
                if m:
                    keys.add(m.group(1))
            line_start = i + 1
    # Last line if no trailing newline
    if depth == 0:
        line = body[line_start:].strip()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*[:,]", line)
        if m:
            keys.add(m.group(1))
    return keys


@pytest.fixture(scope="module")
def export_keys():
    src = JS_SRC.read_text(encoding="utf-8")
    return _extract_object_literal_keys(
        src,
        fn_anchor="function exportPreset(",
        expr_anchor="zones: zones.map(z => ({",
    )


@pytest.fixture(scope="module")
def import_keys():
    src = JS_SRC.read_text(encoding="utf-8")
    return _extract_object_literal_keys(
        src,
        fn_anchor="function _applyPresetFromObject(",
        expr_anchor="zones = preset.zones.map(z => ({",
    )


def test_export_keys_extracted_nontrivially(export_keys):
    """Sanity: the regex extraction grabbed enough keys from exportPreset
    to be a meaningful test. If the function is renamed or restructured,
    this fires before the parity assertion."""
    assert len(export_keys) >= 15, (
        f"exportPreset object-literal extraction returned only "
        f"{len(export_keys)} keys: {sorted(export_keys)!r}. The function "
        f"may have been restructured — update the anchors in this test."
    )


def test_import_keys_extracted_nontrivially(import_keys):
    """Sanity: the regex extraction grabbed enough keys from
    _applyPresetFromObject."""
    assert len(import_keys) >= 15, (
        f"_applyPresetFromObject object-literal extraction returned only "
        f"{len(import_keys)} keys: {sorted(import_keys)!r}. The function "
        f"may have been restructured — update the anchors in this test."
    )


def test_no_NEW_export_only_keys_introduced(export_keys, import_keys):
    """The bug-class this catches: a developer adds a new field to
    `exportPreset` but forgets the matching read in
    `_applyPresetFromObject`. The painter's preset round-trip
    silently loses that field.

    `INTENTIONALLY_DROPPED_ON_IMPORT` pins the CURRENT set of dropped
    fields. Any NEW drop fires this test.

    To resolve a failure here, the developer must EITHER:
      (a) add the field to `_applyPresetFromObject` so the import
          reads it, OR
      (b) add the field name to `INTENTIONALLY_DROPPED_ON_IMPORT`
          above with a comment explaining WHY losing it on import
          is acceptable.
    """
    export_only = export_keys - import_keys
    new_drops = export_only - INTENTIONALLY_DROPPED_ON_IMPORT

    assert not new_drops, (
        f"exportPreset writes the following key(s) that "
        f"_applyPresetFromObject does NOT read on import:\n"
        f"  {sorted(new_drops)!r}\n"
        f"This means a painter sharing a .shokker preset will silently "
        f"LOSE these field(s) on the recipient's import. Either add "
        f"the field(s) to _applyPresetFromObject, or document the "
        f"omission in INTENTIONALLY_DROPPED_ON_IMPORT in this test "
        f"file with a clear rationale.\n\n"
        f"Currently-known-and-pinned drops: "
        f"{sorted(INTENTIONALLY_DROPPED_ON_IMPORT)!r}"
    )


def test_known_clobber_rotation_still_present_until_fix_lands(
    export_keys, import_keys
):
    """While the rotation clobber is documented + pinned in
    `INTENTIONALLY_DROPPED_ON_IMPORT`, this assertion confirms it is
    STILL present. When the fix lands (rotation added to import), this
    test will fail and the developer should:
      (a) remove `rotation` from INTENTIONALLY_DROPPED_ON_IMPORT, AND
      (b) delete this test (it has served its purpose).
    """
    if "rotation" not in INTENTIONALLY_DROPPED_ON_IMPORT:
        pytest.skip(
            "Rotation clobber appears to have been fixed and removed "
            "from INTENTIONALLY_DROPPED_ON_IMPORT — delete this test."
        )
    assert "rotation" in export_keys, (
        "Expected 'rotation' in exportPreset key set as of 2026-04-21 "
        "audit baseline."
    )
    assert "rotation" not in import_keys, (
        "'rotation' is now read by _applyPresetFromObject — clobber "
        "fixed. Remove 'rotation' from INTENTIONALLY_DROPPED_ON_IMPORT "
        "and delete this test."
    )
