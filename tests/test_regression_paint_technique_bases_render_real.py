"""Behavioral ratchet — Paint Technique bases must produce real paint+spec output.

## Why this exists (2026-04-24 overnight Iter 2)

User Item 5 brief flagged the 6 Paint Technique bases as "doing nothing":
  paint_brush_stroke, paint_drip_gravity, paint_roller_streak,
  paint_splatter_loose, paint_sponge_stipple, paint_spray_fade

Iter 2 behavioral probe found they actually DO render correctly:
  * Each paint_fn lives in `engine.paint_v2.paint_technique` (unique fns)
  * Each produces visible paint variation (std 0.019–0.083)
  * Each produces distinct paint output (no cross-base hash collision)
  * Each spec_fn produces meaningful (M, R, CC) tuples with std 9–45

The user's "doing nothing" report was almost certainly the auto-color-fill
bug fixed 2026-04-24 (`_SPB_NO_AUTO_COLOR_GROUPS` now includes "Paint
Technique" — see `tests/test_regression_special_base_no_auto_color_fill.py`).
Pre-fix: picking these triggered the JS swatch-to-solid auto-fill which
clobbered painter's view of the actual paint_fn output. Post-fix:
the distinctive paint variation is visible.

This file pins the working renderer state. If any of these silently
regress to flat output, generic fallback, or shared paint_fn (the
"doing nothing" symptom in disguise), this ratchet fires.

## What this proves

1. Each Paint Technique base is in BASE_REGISTRY with its own paint_fn
   and base_spec_fn (no shared-generic regression).
2. paint_fn outputs measurably distinct, non-flat paint when given mid-grey
   input (proves the base actually contributes visible paint character).
3. base_spec_fn returns a 3-tuple (M, R, CC) with substantial variance
   on every channel (proves the spec contribution is real, not flat-fill).
4. No two Paint Technique bases share a paint_fn output hash (proves
   they're individually rendered, not all wired to the same generic).

If this fires, painters will see Paint Technique bases render flat OR
all-identical OR not at all — the same painter-trust regression class
the project has been hunting since the 2026-04-21 Codex thread doctrine.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest


PAINT_TECHNIQUE_IDS = [
    "paint_brush_stroke",
    "paint_drip_gravity",
    "paint_roller_streak",
    "paint_splatter_loose",
    "paint_sponge_stipple",
    "paint_spray_fade",
]


@pytest.fixture(scope="module")
def engine():
    import shokker_engine_v2 as eng
    eng._ensure_expansions_loaded()
    return eng


@pytest.fixture(scope="module")
def probe_inputs():
    H, W = 256, 256
    return {
        "shape": (H, W),
        "mask": np.ones((H, W), dtype=np.float32),
        "mid_grey_paint": np.full((H, W, 3), 0.45, dtype=np.float32),
        "bb_2d": np.zeros((H, W), dtype=np.float32),
        "seed": 42,
        "pm": 1.0,
    }


@pytest.mark.parametrize("base_id", PAINT_TECHNIQUE_IDS)
def test_paint_technique_base_registered(engine, base_id):
    """Every Paint Technique base must be in BASE_REGISTRY with both paint_fn
    and base_spec_fn callable."""
    assert base_id in engine.BASE_REGISTRY, (
        f"{base_id} missing from BASE_REGISTRY — picker exposes it but engine "
        f"won't render anything. Item 5 'doing nothing' regression."
    )
    entry = engine.BASE_REGISTRY[base_id]
    assert callable(entry.get("paint_fn")), f"{base_id}.paint_fn missing or not callable"
    assert callable(entry.get("base_spec_fn")), f"{base_id}.base_spec_fn missing or not callable"


@pytest.mark.parametrize("base_id", PAINT_TECHNIQUE_IDS)
def test_paint_technique_paint_fn_produces_visible_variation(engine, probe_inputs, base_id):
    """paint_fn called on mid-grey input must produce measurable variation
    AND modify the input meaningfully (max abs delta > 0.05). A flat output
    or near-zero delta means the painter sees nothing happen when they apply
    this base — exact 'doing nothing' bug."""
    entry = engine.BASE_REGISTRY[base_id]
    paint_fn = entry["paint_fn"]
    out = paint_fn(
        probe_inputs["mid_grey_paint"].copy(),
        probe_inputs["shape"],
        probe_inputs["mask"],
        probe_inputs["seed"],
        probe_inputs["pm"],
        probe_inputs["bb_2d"],
    )
    arr = np.asarray(out, dtype=np.float32)
    assert arr.shape == probe_inputs["mid_grey_paint"].shape, (
        f"{base_id} paint_fn returned shape {arr.shape}, expected "
        f"{probe_inputs['mid_grey_paint'].shape}"
    )
    std = float(arr.std())
    delta = float(np.abs(arr - probe_inputs["mid_grey_paint"]).max())
    assert std > 0.005, (
        f"{base_id} paint_fn output is essentially flat (std={std:.4f}). "
        f"Painter would see no character from this base."
    )
    assert delta > 0.05, (
        f"{base_id} paint_fn barely modifies input (max abs delta {delta:.4f}). "
        f"Painter would experience this as 'doing nothing'."
    )


@pytest.mark.parametrize("base_id", PAINT_TECHNIQUE_IDS)
def test_paint_technique_spec_fn_returns_real_tuple_with_variance(engine, probe_inputs, base_id):
    """base_spec_fn must accept the engine's 5-arg signature
    (shape, seed, sm, base_M, base_R) — see compose.py:1298 — and return
    a 3-tuple of (M, R, CC) arrays. Each channel must show measurable
    variance (std > 1.0 on uint8-scale 0–255). Flat spec means painter
    sees no shading character from the base."""
    entry = engine.BASE_REGISTRY[base_id]
    spec_fn = entry["base_spec_fn"]
    base_m = entry.get("M", 100)
    base_r = entry.get("R", 50)
    result = spec_fn(probe_inputs["shape"], probe_inputs["seed"], 1.0, base_m, base_r)
    assert isinstance(result, tuple) and len(result) == 3, (
        f"{base_id} spec_fn must return (M, R, CC) tuple, got {type(result).__name__}"
    )
    for ch_name, ch_arr in zip(("M", "R", "CC"), result):
        arr = np.asarray(ch_arr, dtype=np.float32)
        std = float(arr.std())
        assert std > 1.0, (
            f"{base_id} spec_fn {ch_name} channel essentially flat (std={std:.3f}). "
            f"Painter sees no shading character from this base's spec contribution."
        )


def test_no_paint_technique_pair_shares_paint_fn_output(engine, probe_inputs):
    """If two Paint Technique bases produce byte-identical paint_fn output
    when given the same input/seed/mask, they're functionally the same finish
    rendered under different names — painter sees identical results from
    different picker selections. Catches regression to a shared generic."""
    hashes = {}
    for base_id in PAINT_TECHNIQUE_IDS:
        entry = engine.BASE_REGISTRY[base_id]
        paint_fn = entry["paint_fn"]
        out = paint_fn(
            probe_inputs["mid_grey_paint"].copy(),
            probe_inputs["shape"],
            probe_inputs["mask"],
            probe_inputs["seed"],
            probe_inputs["pm"],
            probe_inputs["bb_2d"],
        )
        arr = np.asarray(out, dtype=np.float32)
        h = hashlib.sha256(arr.tobytes()).hexdigest()[:16]
        hashes.setdefault(h, []).append(base_id)
    collisions = {h: ids for h, ids in hashes.items() if len(ids) > 1}
    assert collisions == {}, (
        f"Paint Technique bases share paint_fn output (silent-no-op symptom): "
        f"{collisions}. Painter selecting different bases sees identical paint."
    )


def test_paint_technique_paint_fns_are_unique_callables(engine):
    """The paint_fn objects themselves must differ across all 6 bases.
    Catches the case where every base entry was wired to a single shared
    fn (which would also fail the output-collision test, but this catches
    it at the wiring layer)."""
    fns = {}
    for base_id in PAINT_TECHNIQUE_IDS:
        entry = engine.BASE_REGISTRY[base_id]
        paint_fn = entry["paint_fn"]
        fns[base_id] = id(paint_fn)
    unique_fn_ids = set(fns.values())
    assert len(unique_fn_ids) == len(PAINT_TECHNIQUE_IDS), (
        f"Paint Technique paint_fn objects collide — wired to shared fn: {fns}"
    )
