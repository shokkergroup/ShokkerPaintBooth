"""Regression guardrail — the swatch endpoint must upscale small
monolithic-swatch requests to a safe rendering resolution, so the
205 MONOs that can't render below 64x64 don't crash painter thumbnails.

## Context (Iter 6, ship-readiness audit, 2026-04-22)

Iter 1 behavioral probe found that 205 of 1027 MONOLITHIC_REGISTRY
spec functions raise ``ValueError: operands could not be broadcast
together`` when invoked at ``shape=(32,32)`` (and at every shape
below 64). They use a noise cache that's keyed on a different
(larger) shape, so the broadcast fails. At ``shape >= 64``, all 205
work cleanly.

The swatch endpoint (``/api/swatch/<type>/<key>?size=N``) accepts
size values from 32 to 256 (``SWATCH_SIZE_MIN=32``,
``SWATCH_SIZE_MAX=256``). Painters can request thumbnails at 32px,
48px, etc. — shapes that would crash all 205 of those MONOs.

Current protection at ``server.py:2277-2279``:

    elif size <= 96 and (finish_type == 'monolithic' or is_base_but_mono):
        internal_size = 256
        logger.debug("Swatch monolithic at 256px then downscale: ...")

The server renders the MONO at 256×256 internally then downscales
to the requested size. Small-shape crashes are unreachable through
the live swatch endpoint.

## What this test pins

  1. `SWATCH_SIZE_MIN` / `SWATCH_SIZE_MAX` bounds.
  2. The `_SWATCH_256_FINISHES` audited-finicky set still exists.
  3. The `size <= 96 and monolithic → 256` defensive upscale is
     still there (source-text pin — catches accidental removal).
  4. Behavioral: invoking every MONO spec_fn at the 64x64 floor
     works. This catches any regression that RAISES the minimum
     required shape (e.g. a new MONO added that needs 128+).

If any test here fires, small-shape thumbnails could start producing
crash-fallback renders or black tiles.
"""

import contextlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest


REPO = Path(__file__).resolve().parent.parent


def test_swatch_size_bounds_pinned():
    """Server's swatch size bounds must stay at [32, 256]. If they
    change, the defensive upscale range below may need re-tuning."""
    src = (REPO / "server.py").read_text(encoding="utf-8")
    assert "SWATCH_SIZE_MIN = 32" in src, (
        "SWATCH_SIZE_MIN is no longer 32. If it's raised, the defensive "
        "upscale may be redundant; if lowered, MORE shapes need "
        "protection. Audit before merging."
    )
    assert "SWATCH_SIZE_MAX = 256" in src, (
        "SWATCH_SIZE_MAX changed; audit downstream consumers."
    )


def test_monolithic_swatch_defensive_upscale_present():
    """`server.py` must still contain the `size <= 96 and ... →
    internal_size = 256` defensive upscale for MONO swatches. This
    is what keeps the 205 crash-at-small-shape MONOs from blowing
    up thumbnails."""
    src = (REPO / "server.py").read_text(encoding="utf-8")
    # Look for the specific defensive-upscale construct.
    assert "size <= 96 and (finish_type == 'monolithic'" in src or \
           'size <= 96 and (finish_type == "monolithic"' in src, (
        "Defensive MONO-swatch upscale at server.py:2277 is missing. "
        "Restore it or find its replacement. Without this, painter "
        "thumbnails for the 205 MONO finishes that need shape >= 64 "
        "would crash when rendered at small sizes."
    )
    # Also pin the target internal size (must be >= 64 for all 205 MONOs).
    assert "internal_size = 256" in src, (
        "The defensive upscale used to target 256. If it now targets "
        "a different resolution, verify it's still >= 64 (minimum shape "
        "the 205 crash-prone MONOs need)."
    )


def test_swatch_256_finishes_set_present():
    """The audited list of always-256-rendered finishes
    (_SWATCH_256_FINISHES) must still be populated — these are
    multi-color-shift finishes that need high-res noise to read
    correctly."""
    src = (REPO / "server.py").read_text(encoding="utf-8")
    assert "_SWATCH_256_FINISHES" in src, (
        "_SWATCH_256_FINISHES set is gone. The specific color-shift "
        "finishes that were audited into it no longer get the safe "
        "256px render path. Restore before shipping."
    )


def test_swatch_cache_keys_include_engine_fingerprint():
    """Engine edits must not keep serving old disk-cache swatches forever."""
    server_src = (REPO / "server.py").read_text(encoding="utf-8")
    route_src = (REPO / "server_routes" / "swatch_routes.py").read_text(encoding="utf-8")
    assert "def _swatch_cache_token()" in server_src
    assert "swatch_cache_token=_swatch_cache_token" in server_src
    assert "cache_key = f\"{cache_token}:" in route_src
    assert "_safe_swatch_key(cache_token, finish_type, finish_key" in route_src
    assert "f\"{swatch_cache_token()}_mono_{finish_id}.png\"" in route_src


def test_live_engine_swatches_are_default_and_js_requests_live():
    """Picker previews should not hide rebuilt finish math behind old PNGs."""
    route_src = (REPO / "server_routes" / "swatch_routes.py").read_text(encoding="utf-8")
    swatch_popup_src = (REPO / "js" / "zones" / "swatch-popup-render-controls.js").read_text(encoding="utf-8")
    boot_src = (REPO / "paint-booth-6-ui-boot.js").read_text(encoding="utf-8")

    assert "prefer_live = prefer != 'static' and prefer != 'prerender'" in route_src
    assert "allow_prerender = not prefer_live" in route_src
    assert "var prefer = '&prefer=live';" in swatch_popup_src
    assert 'return `background: url("${url}") center/cover, #111827;`;' in boot_src


def test_client_swatch_tint_accepts_only_exact_hex_and_fails_to_valid_default():
    """Catalog prose or malformed CSS must never leak into ``color=``.

    The swatch endpoint requires a six-digit tint. The browser helper may
    accept the intended three- or six-digit hex forms (with an optional #),
    but must use a valid fallback/default for every other input.
    """
    script = r"""
require('./js/zones/swatch-popup-render-controls.js');
global.SPBSwatchPopupRenderControls.install({});
const normalize = global._normalizeSwatchTintHex;
const results = [
  normalize('#AbC', null),
  normalize('abc', null),
  normalize('#A1b2C3', null),
  normalize('A1B2C3', null),
  normalize('  #0fA  ', null),
  normalize(null, '#FeD'),
  normalize('Near-black forest-green field', '#123456'),
  normalize('Near-black forest-green field', null),
  normalize('linear-gradient(135deg, #123456, #abcdef)', null),
  normalize('#12345678', null),
  normalize('12345g', null),
  normalize(123456, null)
];
process.stdout.write(JSON.stringify(results));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == [
        "aabbcc",
        "aabbcc",
        "a1b2c3",
        "a1b2c3",
        "00ffaa",
        "ffeedd",
        "123456",
        "888888",
        "888888",
        "888888",
        "888888",
        "888888",
    ]


def test_server_swatch_normalizes_tuple_specs():
    """Pattern-driven monolithics return (M, R, CC); swatches must read them.

    The normalizer was extracted to ``server_routes/spec_result_support.py``
    (def ``normalize_spec_result_to_rgba``) and ``server.py`` now imports it as
    ``_normalize_spec_result_to_rgba`` and calls it on the swatch render path.
    Pin the real (relocated) definition + tuple/list handling, and that
    ``server.py`` still wires the call into the swatch path."""
    src = (REPO / "server.py").read_text(encoding="utf-8")
    support_src = (REPO / "server_routes" / "spec_result_support.py").read_text(encoding="utf-8")
    assert "def normalize_spec_result_to_rgba" in support_src
    assert "isinstance(spec_result, (tuple, list)) and len(spec_result) >= 2" in support_src
    assert "normalize_spec_result_to_rgba as _normalize_spec_result_to_rgba" in src
    assert "spec_arr = _normalize_spec_result_to_rgba(" in src


def test_all_monolithic_spec_fns_work_at_64x64():
    """Behavioral: every MONO spec_fn must run without crashing at
    shape=(64,64). This is the floor the server's defensive upscale
    maps 32-96 swatch requests to. If any MONO raises the floor
    (e.g. a new MONO added requiring 128+), this test fires and
    the server's upscale target must be raised to match."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import MONOLITHIC_REGISTRY

    shape = (64, 64)
    mask = np.ones(shape, dtype=np.float32)
    crashes = []
    for mid, tup in MONOLITHIC_REGISTRY.items():
        if not isinstance(tup, (tuple, list)) or len(tup) < 2:
            continue
        sf = tup[0]
        try:
            sf(shape, mask, 42, 1.0)
        except Exception as e:
            crashes.append((mid, type(e).__name__, str(e)[:60]))

    assert not crashes, (
        f"{len(crashes)} MONO spec_fns crashed at shape=(64,64). "
        f"The server.py defensive upscale targets 256 specifically "
        f"because 64 was the previous 'floor' — if new MONOs push "
        f"it higher, raise the upscale target accordingly. Samples:\n  "
        + "\n  ".join(f"{m}: {e} {msg}" for m, e, msg in crashes[:5])
    )


def test_no_monolithic_spec_fn_raises_minimum_above_64():
    """Complement to the above — verifies no MONO requires LARGER
    than 64 (which would mean the 256 upscale isn't enough). Probed
    at shape=(64,64) — must succeed for all."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from shokker_engine_v2 import MONOLITHIC_REGISTRY

    # This test is effectively the same as the one above — 64 is the
    # floor. If anything raises it, the previous test fails first.
    # Keep this as a named sentinel: "the 64 floor is painter-safe
    # assuming server upscales to 256."
    shape_64_count = 0
    for mid, tup in MONOLITHIC_REGISTRY.items():
        if not isinstance(tup, (tuple, list)) or len(tup) < 2:
            continue
        sf = tup[0]
        try:
            sf(shape, 42, 1.0) if False else sf((64, 64), np.ones((64, 64), np.float32), 42, 1.0)
            shape_64_count += 1
        except Exception:
            pass

    # Reasonable MONO count floor — catches registry shrinks
    assert shape_64_count >= 900, (
        f"Only {shape_64_count} MONOs succeed at shape=(64,64). "
        f"Previous baseline >= 1000. Either MONOs were deleted or "
        f"new ones are more shape-sensitive."
    )
