"""Live preview / render parity ratchet — Item 7.

## Why this exists (2026-04-24 overnight Iter 5)

User Item 7 brief: "Look for setters that mutate zone/base/pattern/spec
fields without both renderZones() and triggerPreviewRender(). Audit
base overlay layers 2 through 5, spec overlay stacks, pattern stacks,
layer-scoped zones, and source-layer-bound zones. Add structural tests
for any missing invalidation."

Iter 5 audit (`audit/2026-04-24-overnight/probe_setter_render_parity.py`)
classified all 155 setter-shaped functions in `paint-booth-2-state-zones.js`:
  * 18 call BOTH `renderZones()` and `triggerPreviewRender()`
  * 1 calls only `renderZones()` (`setZoneTag` — name-edit input handler,
    intentional to avoid focus-steal)
  * 118 call only `triggerPreviewRender()` (slider/input setters where a
    full UI rebuild would steal focus mid-drag — this is correct UX)
  * 18 call NEITHER — investigated; most are UI-only (toggle panels,
    update badges) or thin dispatchers; the one real risk was
    `setZoneFinish` which mutated 5 fundamental zone fields without any
    invalidation.

## Fix landed

`setZoneFinish` is currently dead code (no live caller, kept as legacy
compat). Iter 5 added defensive `renderZones()` + `triggerPreviewRender()`
+ `autoSave()` invalidation at the end of the function so any future
re-wiring of this entry point cannot silently mutate zone state without
the painter seeing both the UI and preview update.

## What this file ratchets

1. The defensive invalidation calls inside `setZoneFinish` must remain.
   If a future edit removes them and a caller is later wired up, the
   silent-state-mutation bug class returns.
2. The setter parity inventory floor: at least 18 setters must call
   BOTH render paths (the canonical "fundamental zone change"
   invalidation pair like `setZoneBase`, `setZonePattern`, `setQuickColor`).
   Catches a refactor that drops one of the canonical pair calls from
   any of these key setters.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
JS_PATH = REPO / "paint-booth-2-state-zones.js"


@pytest.fixture(scope="module")
def js_text() -> str:
    return JS_PATH.read_text(encoding="utf-8")


def _extract_function_body(src: str, fn_name: str) -> str:
    """Return the body of `function <fn_name>(...) { ... }` with balanced braces."""
    pattern = re.compile(rf"^function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{", re.MULTILINE)
    m = pattern.search(src)
    if not m:
        return ""
    body_start = m.end() - 1
    depth = 0
    i = body_start
    while i < len(src):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[body_start + 1:i]
        i += 1
    return ""


def test_set_zone_finish_invokes_both_render_paths(js_text: str):
    """setZoneFinish mutates 5 fundamental zone fields. It MUST invoke
    `renderZones()` AND `triggerPreviewRender()` even though it has no
    live caller today, because:
      (a) a future migration / saved-config / plugin script could re-wire it
      (b) silent-state mutation without UI feedback is the project's
          highest-cost trust-violation bug class.
    """
    body = _extract_function_body(js_text, "setZoneFinish")
    assert body, "setZoneFinish function not found in paint-booth-2-state-zones.js"
    assert re.search(r"\brenderZones\s*\(", body), (
        "setZoneFinish no longer calls renderZones() — silent zone-list "
        "stale state if any caller is ever re-wired."
    )
    assert re.search(r"\btriggerPreviewRender\s*\(", body), (
        "setZoneFinish no longer calls triggerPreviewRender() — silent "
        "preview-stale state if any caller is ever re-wired."
    )
    # autoSave on state mutation is the project's persistence contract.
    assert re.search(r"\bautoSave\s*\(", body), (
        "setZoneFinish no longer calls autoSave() — state mutation "
        "without persistence contract violation."
    )


def test_canonical_dual_render_setters_keep_both_calls(js_text: str):
    """The 'fundamental zone state' setters that change WHAT the zone is
    (base, pattern, finish, color, intensity) must keep both invalidations.
    These are the ones the user is most sensitive to — picking a base
    or pattern is the painter's primary action and seeing the preview
    fail to update is the loudest trust violation."""
    canonical = [
        "setZoneBase",
        "setZonePattern",
        "setZoneIntensity",
        "setZoneIntensityNumeric",
        "setQuickColor",
        "setHexColor",
        "setSpecialColor",
        "setTextColor",
        "setPickerColor",
        "setPickerTolerance",
        "setTolerancePreset",
        "applyFinishToAllZones",
        "setAllZonesTolerance",
    ]
    missing = []
    for fn in canonical:
        body = _extract_function_body(js_text, fn)
        if not body:
            missing.append(f"{fn} (function not found)")
            continue
        has_render = bool(re.search(r"\brenderZones\s*\(", body))
        has_preview = bool(re.search(r"\btriggerPreviewRender\s*\(", body))
        if not (has_render and has_preview):
            missing.append(
                f"{fn} (renderZones={has_render}, triggerPreviewRender={has_preview})"
            )
    assert missing == [], (
        f"Canonical dual-render setters lost one or both invalidation "
        f"calls — fundamental zone-state changes will silent-no-op for "
        f"the painter: {missing}"
    )


def test_dual_render_setter_count_at_or_above_baseline(js_text: str):
    """Sentinel: at least 18 setters in paint-booth-2-state-zones.js must
    invoke BOTH `renderZones()` AND `triggerPreviewRender()` per Iter 5
    audit baseline. Catches mass deletion or wholesale refactor that
    accidentally drops the canonical pair from many setters at once."""
    fn_decl_re = re.compile(
        r"^function\s+(set[A-Z]\w+|apply[A-Z]\w+|toggleZone\w+|update[A-Z]\w+)\s*\([^)]*\)\s*\{",
        re.MULTILINE,
    )
    both_count = 0
    for m in fn_decl_re.finditer(js_text):
        body = _extract_function_body(js_text, m.group(1))
        if (
            re.search(r"\brenderZones\s*\(", body)
            and re.search(r"\btriggerPreviewRender\s*\(", body)
        ):
            both_count += 1
    assert both_count >= 18, (
        f"Setter dual-invalidation count dropped to {both_count} "
        f"(Iter 5 baseline 18). A refactor likely stripped one of the "
        f"canonical render paths from key setters."
    )
