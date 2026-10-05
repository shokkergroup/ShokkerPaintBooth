"""Regression guardrail — painter-reported 2026-04-22: a zone whose
``baseColorMode='gradient'`` with a single-stop (or otherwise
degenerate-but-truthy) stops list must NOT silently paint uniform
gray across the entire zone.

## The bug that was fixed

``engine.compose.generate_custom_gradient`` has a defensive-looking
"single-stop → duplicate to 2-stop" expansion at its line ~746-748.
That's mathematically a gradient from color X to color X — a flat
color everywhere. The caller at ``_apply_base_color_override`` line
~957 then blends with ``src = gray*0.25 + grad*0.75``, producing a
uniform gray/tinted wash across the entire mask area.

Painter symptom: "some type of gradient which I guess is failing
and causing gray to cover the entire paint preview area."

Repro (Pillman, 2026-04-22):
  _apply_base_color_override(
      paint_in=blue(64,64),
      base_color_mode='gradient',
      base_color={'stops': [{'pos': 0.5, 'color': [0.5, 0.5, 0.5]}]},
      base_color_strength=1.0,
  )
  → returned uniform gray rgb=[0.49, 0.49, 0.49] instead of leaving
    the painter's blue alone.

Fix: require ``len(base_color['stops']) >= 2`` at the dispatch
guard. A "gradient" with fewer than 2 stops is meaningless as a
gradient; it falls through as a no-op (src stays None → paint
returned unchanged). Painters who want a uniform color have
``mode='solid'`` for that.

## What this test pins

- Single-stop gradient → paint UNCHANGED (no gray fill).
- Zero-stop / empty stops → paint UNCHANGED.
- Two-stop gradient → paint CHANGED with per-pixel variance (real
  gradient rendered).
- Hex-string malformed stops → paint UNCHANGED (falls through
  try/except).
- None / hex-string base_color (not even a dict) → paint UNCHANGED.

If this ratchet fires, the painter's zone is about to get
gray-washed again by a stray single-stop gradient. Either the guard
at compose.py around line 960 was removed or the dispatch changed.
"""

import io
import contextlib

import numpy as np
import pytest


SHAPE = (64, 64)


@pytest.fixture(scope="module")
def apply_base_color_override():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.compose import _apply_base_color_override
    return _apply_base_color_override


def _fresh_paint():
    """Non-gray fingerprint paint (blue) so any gray fill is obvious."""
    return np.full((*SHAPE, 3), [0.2, 0.4, 0.8], dtype=np.float32)


def _full_mask():
    return np.ones(SHAPE, dtype=np.float32)


def _run(apply_fn, base_color):
    """Invoke _apply_base_color_override with mode='gradient' and the
    given base_color. Return (delta, per-pixel variance sum)."""
    r = apply_fn(
        _fresh_paint(), SHAPE, _full_mask(), 42,
        base_color_mode="gradient",
        base_color=base_color,
        base_color_source=None,
        base_color_strength=1.0,
        monolithic_registry=None,
    )
    arr = np.asarray(r)
    delta = float(np.abs(arr - _fresh_paint()).max())
    variance = float(arr.var(axis=(0, 1)).sum())
    return delta, variance


def test_single_stop_gradient_does_not_gray_fill(apply_base_color_override):
    """The exact painter repro: a single-stop gradient with a gray
    color must leave the painter's paint UNCHANGED, not paint uniform
    gray across the entire zone."""
    delta, _ = _run(
        apply_base_color_override,
        {"stops": [{"pos": 0.5, "color": [0.5, 0.5, 0.5]}]},
    )
    assert delta < 1e-6, (
        f"Single-stop gradient painted over painter's paint (max delta "
        f"{delta}). This is the 2026-04-22 painter-reported gray-fill "
        f"bug — the guard at compose.py's mode=='gradient' branch has "
        f"regressed. Require `len(stops) >= 2` before invoking "
        f"generate_custom_gradient."
    )


@pytest.mark.parametrize("color", [
    [0.5, 0.5, 0.5], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
    [0.3, 0.6, 0.9], [0.9, 0.8, 0.7],
])
def test_single_stop_any_color_is_noop(apply_base_color_override, color):
    """Single-stop gradients of ANY color (not just gray) must no-op.
    Catches regressions where someone "fixes" only the gray case."""
    delta, _ = _run(
        apply_base_color_override,
        {"stops": [{"pos": 0.5, "color": color}]},
    )
    assert delta < 1e-6, (
        f"Single-stop gradient with color={color} changed paint (delta "
        f"{delta}). Single-stop gradient should be a no-op regardless "
        f"of color — painters who want uniform color should use "
        f"baseColorMode='solid'."
    )


def test_empty_stops_is_noop(apply_base_color_override):
    """Zero-stop gradient must no-op (as before the fix — this test
    just pins that behavior so any regression is caught)."""
    delta, _ = _run(apply_base_color_override, {"stops": []})
    assert delta < 1e-6, f"Empty-stops gradient changed paint (delta {delta})"


def test_two_stop_gradient_actually_renders(apply_base_color_override):
    """Counter-test: a proper 2-stop gradient MUST still produce per-
    pixel variance, so the no-op guard isn't over-eager."""
    delta, variance = _run(
        apply_base_color_override,
        {"stops": [
            {"pos": 0, "color": [1.0, 0.0, 0.0]},
            {"pos": 1, "color": [0.0, 0.0, 1.0]},
        ]},
    )
    assert delta > 0.05, (
        f"Two-stop red-to-blue gradient produced max delta {delta} — "
        f"should be significant. The no-op guard may be too aggressive."
    )
    assert variance > 0.005, (
        f"Two-stop gradient produced per-pixel variance {variance} — "
        f"should be non-flat. The guard may be filtering valid cases."
    )


@pytest.mark.parametrize("bad_color", [None, "#808080", [0.5, 0.5, 0.5], 42])
def test_non_dict_base_color_with_gradient_mode_is_noop(
    apply_base_color_override, bad_color
):
    """If someone sets baseColorMode='gradient' but leaves base_color
    as a plain hex/list/None (because the dict-packaging at
    shokker_engine_v2.py path1 didn't fire for lack of gradient_stops),
    the result must no-op, not crash and not gray-fill."""
    delta, _ = _run(apply_base_color_override, bad_color)
    assert delta < 1e-6, (
        f"Non-dict base_color={bad_color!r} with mode='gradient' "
        f"changed paint by {delta} — should no-op."
    )


def test_hex_string_stops_fall_through_noop(apply_base_color_override):
    """Hex-string stop colors (`{color: '#ffffff'}`) fail inside
    generate_custom_gradient at the float conversion. The try/except
    at the dispatch catches it and paint stays unchanged. Pinned so
    a future refactor can't accidentally propagate the exception."""
    delta, _ = _run(
        apply_base_color_override,
        {"stops": [
            {"pos": 0, "color": "#000000"},
            {"pos": 1, "color": "#ffffff"},
        ]},
    )
    assert delta < 1e-6, (
        f"Hex-string stops changed paint (delta {delta}). Exception "
        f"path must keep paint unchanged."
    )
