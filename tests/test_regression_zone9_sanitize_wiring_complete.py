"""Structural ratchet — Zone 9 zombie sanitize wiring must remain in place.

## Why this exists (2026-04-24 overnight Iter 3)

The existing Zone 9 zombie defenses are:
  * `tests/test_regression_zone9_default_empty.py` — pins the source default
    literals (Zone 9 stays empty, Zone 10 is the catch-all, no "Dark / Carbon
    Areas" string survives).
  * `tests/zone9_matte_carbon_guard_test.py` + the runtime harness — pins
    that `_sanitizeZonesInPlace` actually strips a zombie zone with
    `base:matte, pattern:carbon_fiber, no regionMask` and leaves authored
    zones with a regionMask alone.

But neither test pins that EVERY load path actually CALLS the sanitizer.
A future refactor that removes the `_sanitizeZonesInPlace(...)` call from
`loadConfigFromObj` (file load), `renderZones` (the every-render safety
net), the built-in preset apply, or the imported preset apply would let
the zombie resurrect through the unprotected path and no test would fire.

This file pins the 4 call sites Iter 3 audit identified as the complete
wiring set:
  1. `renderZones` — line ~842, called on every UI render
  2. Built-in preset apply — line ~9162
  3. `loadConfigFromObj` — line ~9771, the central load path used by file
     load, drag-drop, and `autoRestore` (localStorage session restore)
  4. Imported preset apply — line ~9991

If any of these wirings disappears, this ratchet fires.

## Painter trust context

User brief Item 9 explicitly listed the surfaces to verify:
"Search all presets, default zone builders, migrations, load paths,
fallback state, SHOKK load, localStorage/session restore, and test
fixtures. Ensure Zone 9 Matte + Carbon Fiber cannot resurrect."

Iter 3 audit verified:
  * presets — built-in (9162) + imported (9991) both sanitize
  * default zone builders — init() + restoreAllZones() both ship empty
    Zone 9 (covered by `test_regression_zone9_default_empty.py`)
  * migrations — go through `loadConfigFromObj` which sanitizes
  * load paths — file open (9817), drag-drop (9934), other (10027) all
    use `loadConfigFromObj`
  * fallback state — `renderZones` sanitizes on every render as net
  * SHOKK load — `paint-booth-7-shokk.js` does not have its own zone
    load; uses standard config load (verified by repo grep)
  * localStorage / session restore — `autoRestore` (10163) calls
    `loadConfigFromObj` (10195), inheriting sanitize
  * test fixtures — no `.shokker` / `.spb` files exist; no JSON fixture
    contains the zombie pair (verified by repo grep)

This file PINS those audit findings as structural ratchets.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent
STATE_ZONES_JS = REPO / "paint-booth-2-state-zones.js"


@pytest.fixture(scope="module")
def js_text() -> str:
    return STATE_ZONES_JS.read_text(encoding="utf-8")


def test_sanitize_function_is_defined(js_text: str):
    """The sanitizer itself must exist and be exported on window for the
    runtime harness in `zone9_matte_carbon_guard_test.py` to keep working."""
    assert "function _sanitizeZonesInPlace(zoneList, source)" in js_text, (
        "_sanitizeZonesInPlace function definition disappeared. The Zone 9 "
        "runtime harness depends on this function."
    )
    assert "window._sanitizeZonesInPlace = _sanitizeZonesInPlace" in js_text, (
        "_sanitizeZonesInPlace is no longer attached to window — the runtime "
        "harness in zone9_matte_carbon_guard_test.py will fail."
    )


def test_render_zones_calls_sanitize_as_safety_net(js_text: str):
    """The `renderZones` function must invoke the sanitizer on every render.
    This is the defense-in-depth backstop: even if a load path bypasses
    sanitize, the first UI render will catch the zombie."""
    assert (
        "_sanitizeZonesInPlace(zones, 'renderZones')" in js_text
    ), (
        "renderZones() no longer sanitizes. Without this safety-net, any "
        "load path that bypasses sanitize will let the Zone 9 zombie reach "
        "the painter UI."
    )


def test_built_in_preset_apply_calls_sanitize(js_text: str):
    """Built-in preset application must sanitize — a built-in preset
    template could theoretically include a zombie-shaped Zone 9."""
    assert (
        "_sanitizeZonesInPlace(zones, 'built-in preset: '" in js_text
    ), (
        "Built-in preset apply path no longer sanitizes. A future preset "
        "template containing the zombie pair would resurrect Zone 9."
    )


def test_load_config_from_obj_calls_sanitize(js_text: str):
    """`loadConfigFromObj` is the central load path used by file open,
    drag-drop, autoRestore (localStorage), and migration. It MUST sanitize
    or every one of those entry points loses zombie protection."""
    assert (
        "_sanitizeZonesInPlace(zones, 'loaded config')" in js_text
    ), (
        "loadConfigFromObj no longer sanitizes. This is the central load "
        "path; removing sanitize here breaks zombie protection across file "
        "load, drag-drop, autoRestore (localStorage), and migration paths "
        "all at once."
    )


def test_imported_preset_calls_sanitize(js_text: str):
    """Imported presets (sharable JSON files) must sanitize. A painter-shared
    preset that was authored with the old zombie default would otherwise
    resurrect the zombie on import."""
    assert (
        "_sanitizeZonesInPlace(zones, 'imported preset: '" in js_text
    ), (
        "Imported preset apply path no longer sanitizes. A shared preset "
        "carrying the zombie pair would resurrect Zone 9 on import."
    )


def test_total_sanitize_call_sites_at_or_above_baseline(js_text: str):
    """Sentinel: count of sanitize call sites must not drop below the
    Iter 3 baseline of 4. Catches the case where someone removes a call
    we currently rely on without replacing it."""
    # Match function calls (open paren after the name), not the function
    # definition or the window export.
    pattern = re.compile(r"_sanitizeZonesInPlace\(\s*zones\b")
    matches = pattern.findall(js_text)
    assert len(matches) >= 4, (
        f"_sanitizeZonesInPlace(zones, ...) call site count dropped to "
        f"{len(matches)} — baseline is 4 (renderZones, built-in preset, "
        f"loadConfigFromObj, imported preset). A load path lost its "
        f"protection."
    )


def test_autosave_restore_routes_through_load_config_from_obj(js_text: str):
    """`autoRestore` (localStorage session restore) must call
    `loadConfigFromObj` to inherit sanitization — not parse the autosave
    JSON directly into `zones` and bypass the central path."""
    # Find the autoRestore function body
    m = re.search(
        r"function\s+autoRestore\s*\(\s*\)\s*\{(.*?)\n\}\n",
        js_text,
        re.DOTALL,
    )
    assert m is not None, (
        "autoRestore function not found — localStorage restore path may "
        "have been refactored without updating this guard test."
    )
    body = m.group(1)
    assert "loadConfigFromObj(cfg)" in body, (
        "autoRestore (localStorage session restore) no longer calls "
        "loadConfigFromObj — it must, or the autosaved zombie would "
        "resurrect on every app launch."
    )


def test_no_test_fixture_contains_the_zombie_pair():
    """Test repo must not ship a JSON fixture containing the zombie pair
    that could be loaded by accident in a future test or smoke run."""
    suspect_pairs = [
        re.compile(r'"matte"[^}]{0,200}"carbon_fiber"'),
        re.compile(r'"carbon_fiber"[^}]{0,200}"matte"'),
    ]
    json_files = list((REPO / "tests").rglob("*.json"))
    offenders = []
    for fp in json_files:
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        for pat in suspect_pairs:
            if pat.search(text):
                # Allow the legitimate engine-internal test that proves
                # NON-Zone-9 matte+carbon survives sanitization.
                if "non_zone9" in text or "Carbon Accent" in text:
                    continue
                offenders.append(str(fp.relative_to(REPO)))
                break
    assert offenders == [], (
        f"Test fixture(s) contain the zombie pair (matte + carbon_fiber): "
        f"{offenders}. Loading these in a smoke test would resurrect the "
        f"zombie if the fixture lands in a Zone 9 slot."
    )
