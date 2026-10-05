"""Regression guardrail — ``_apply_base_color_override`` solid-mode
must accept BOTH hex strings ("#RRGGBB", "#RGB") and [R, G, B]
float arrays without crashing.

## Context (Iter 5, ship-readiness audit, 2026-04-22)

Pre-hardening: solid-mode tried ``float(clr[0])`` where ``clr`` was
the raw ``base_color`` value. A hex string like ``"#ff3366"`` would
crash at ``float('#')`` → ValueError.

The live render payload builder at
``paint-booth-3-canvas.js:5612`` converts hex → RGB array before
sending, so painters don't hit the crash in the main render flow.
But export paths (fleet / season-shared / PSD export) and any
direct API call can pass the hex string straight through. A future
catalog change that added a gradient-swatch base to the picker
group WITHOUT adding it to ``_SPB_NO_AUTO_COLOR_GROUPS`` would
also push a CSS-gradient string into ``zone.baseColor``, which
would then crash the engine.

## Fix (Iter 5)

Solid-mode now:
  1. Detects string input and parses as "#RRGGBB" or "#RGB" hex.
  2. Falls back to [R, G, B] array acceptance (the pre-existing path).
  3. Any unparseable input (CSS gradient string, dict, int, short
     array, empty string, invalid hex chars) falls back to the
     white sentinel ``[1.0, 1.0, 1.0]`` — same as passing
     ``base_color=None``.
  4. NEVER crashes.

## What this test pins

  - Every standard hex format produces a valid tint (non-crash).
  - Every weird/malformed input produces a valid no-op / sentinel
    (non-crash).
  - Array inputs still work.
  - The crash-proof behavior is pinned so nobody re-regresses
    to ``float(base_color[0])`` direct.
"""

import io
import contextlib

import numpy as np
import pytest


SHAPE = (32, 32)


@pytest.fixture(scope="module")
def apply_fn():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.compose import _apply_base_color_override
    return _apply_base_color_override


def _run(apply_fn, base_color):
    paint = np.full((*SHAPE, 3), [0.2, 0.4, 0.8], dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)
    return apply_fn(
        paint, SHAPE, mask, 42,
        base_color_mode="solid",
        base_color=base_color,
        base_color_source=None,
        base_color_strength=1.0,
        monolithic_registry=None,
    )


@pytest.mark.parametrize("hex_str", [
    "#000000", "#ffffff", "#ff3366", "#00ff00", "#0000ff",
    "#FF3366",  # uppercase
    "#abcdef",
])
def test_solid_mode_accepts_6char_hex(apply_fn, hex_str):
    """Every standard 6-char hex must parse and produce a non-null
    result without crashing."""
    r = _run(apply_fn, hex_str)
    assert isinstance(r, np.ndarray) and r.shape == (*SHAPE, 3), (
        f"Solid-mode with hex={hex_str!r} returned unexpected "
        f"shape/type {getattr(r, 'shape', type(r))}"
    )


@pytest.mark.parametrize("hex_str", ["#f36", "#FF3", "#000", "#abc"])
def test_solid_mode_accepts_3char_hex(apply_fn, hex_str):
    """Short-form hex (`#RGB`) expands to `#RRGGBB` and works."""
    r = _run(apply_fn, hex_str)
    assert isinstance(r, np.ndarray) and r.shape == (*SHAPE, 3)


@pytest.mark.parametrize("bad", [
    "linear-gradient(135deg, #ff3366 0%, #3366ff 100%)",
    "conic-gradient(#AA4444, #AA8833, #66AA44)",
    "#zz3366",   # invalid hex chars
    "#gg",       # too short + invalid
    "#",         # just the hash
    "",          # empty string
    "not a color",
    None,
    42,
    3.14,
    [0.5],       # too-short array
    {"foo": "bar"},
    # 2026-04-22 Codex P2: dict-with-3+-keys reproducer. Pre-patch,
    # the `len >= 3` check accepted mappings and then crashed at
    # `clr[0]` → KeyError: 0. These all must no-op now.
    {"r": 1, "g": 0, "b": 0},
    {"r": 1.0, "g": 0.5, "b": 0.0},
    {"a": 1, "b": 2, "c": 3},
    {"r": 1, "g": 0, "b": 0, "alpha": 1},
    {},          # empty dict
    {0: 1, 1: 2, 2: 3},  # int-keyed dict (len>=3, but still wrong shape)
    set([1, 2, 3]),      # set of 3 (len>=3 but not indexable)
    frozenset([1, 2, 3]),
])
def test_solid_mode_never_crashes_on_bad_input(apply_fn, bad):
    """Any unparseable input must fall back to the white sentinel
    without raising. Pre-hardening these ALL crashed (strings with
    float('#'), dicts with KeyError: 0, sets with TypeError)."""
    r = _run(apply_fn, bad)
    assert isinstance(r, np.ndarray) and r.shape == (*SHAPE, 3)


@pytest.mark.parametrize("dct", [
    {"r": 1, "g": 0, "b": 0},
    {"r": 1.0, "g": 0.5, "b": 0.0},
    {"a": 1, "b": 2, "c": 3},
    {"r": 1, "g": 0, "b": 0, "alpha": 1},
])
def test_solid_mode_dict_input_matches_white_fallback(apply_fn, dct):
    """Dict-like RGB payloads (which some legacy API callers send)
    must specifically fall back to the white sentinel — same output
    as None. Pre-2026-04-22 Codex P2 they crashed with KeyError: 0."""
    r_dict = _run(apply_fn, dct)
    r_none = _run(apply_fn, None)
    assert np.allclose(r_dict, r_none, atol=1e-5), (
        f"Dict input {dct!r} should fall back to the same white "
        f"sentinel as None, but produced different output."
    )


@pytest.mark.parametrize("arr", [
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [0.5, 0.5, 0.5],
    [255, 0, 0],    # int-range (gets floated)
    [1, 1, 1],
    (0.5, 0.5, 0.5),  # tuple
])
def test_solid_mode_accepts_rgb_array(apply_fn, arr):
    """Pre-existing array behavior still works."""
    r = _run(apply_fn, arr)
    assert isinstance(r, np.ndarray) and r.shape == (*SHAPE, 3)


def test_hex_and_array_produce_matching_output(apply_fn):
    """Hex "#ff0000" and array [1.0, 0.0, 0.0] must tint the same
    way — otherwise hex parsing has a bug."""
    r_hex = _run(apply_fn, "#ff0000")
    r_arr = _run(apply_fn, [1.0, 0.0, 0.0])
    assert np.allclose(r_hex, r_arr, atol=1e-5), (
        f"Hex '#ff0000' and array [1,0,0] produced different tints. "
        f"Max diff: {float(np.abs(r_hex - r_arr).max())}"
    )


def test_invalid_input_matches_none_fallback(apply_fn):
    """Unparseable input and None must produce the same output
    (both default to white)."""
    r_none = _run(apply_fn, None)
    r_bad = _run(apply_fn, "linear-gradient(135deg, #f00, #00f)")
    assert np.allclose(r_none, r_bad, atol=1e-5), (
        f"None and unparseable input should both fall back to white "
        f"sentinel, but produced different outputs."
    )
