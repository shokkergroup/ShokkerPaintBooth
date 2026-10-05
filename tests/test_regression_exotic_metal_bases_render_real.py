"""Behavioral ratchet — Exotic Metal bases must produce real paint+spec output.

## Why this exists (2026-04-24 overnight Iter 6)

User Item 5 brief flagged 5 Exotic Metal bases as needing review:
  brushed_aluminum, titanium_raw, organic_metal (Biomech Flesh),
  xirallic (Crystal Flake), chromaflair (Light Shift).

Iter 6 behavioral probe (`audit/2026-04-24-overnight/probe_exotic_metal_bases.py`)
classified all 16 Exotic Metal bases:

  Every base has a unique paint_fn and produces visible variation
  (paint std 0.026–0.161, max abs delta vs mid-grey 0.117–0.489).

  Every base's base_spec_fn returns a 3-tuple with non-trivial channel
  variance (max channel std 6.5–27.4 on uint8 0–255).

  No paint output hash collisions across 16 → each renders distinctly.
  No spec output hash collisions either.

The user's "doing nothing" report on the 5 flagged finishes was almost
certainly either (a) the auto-color-fill bug fixed 2026-04-24 (Exotic
Metal is in `_SPB_NO_AUTO_COLOR_GROUPS`), or (b) a UI selection issue
that didn't actually reach the renderer.

This file pins the working state. If any Exotic Metal base silently
regresses to flat output, generic fallback, or shared paint_fn (the
"doing nothing" symptom), this ratchet fires.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest


EXOTIC_METAL_IDS = [
    "anodized",
    "brushed_aluminum",
    "brushed_titanium",
    "cobalt_metal",
    "diamond_coat",
    "frozen",
    "liquid_titanium",
    "platinum",
    "raw_aluminum",
    "rose_gold",
    "titanium_raw",
    "tungsten",
    "organic_metal",
    "anodized_exotic",
    "xirallic",
    "chromaflair",
]

# The 5 the user explicitly flagged as "doing nothing"
USER_FLAGGED_IDS = [
    "brushed_aluminum",
    "titanium_raw",
    "organic_metal",
    "xirallic",
    "chromaflair",
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
        "mid_grey": np.full((H, W, 3), 0.45, dtype=np.float32),
        "bb_2d": np.zeros((H, W), dtype=np.float32),
        "seed": 42,
    }


@pytest.mark.parametrize("base_id", EXOTIC_METAL_IDS)
def test_exotic_metal_base_registered(engine, base_id):
    """Every Exotic Metal picker id must be in BASE_REGISTRY with both
    paint_fn and base_spec_fn callable."""
    assert base_id in engine.BASE_REGISTRY, (
        f"{base_id} missing from BASE_REGISTRY — picker exposes it but engine "
        f"won't render anything. Item 5 'doing nothing' regression."
    )
    e = engine.BASE_REGISTRY[base_id]
    assert callable(e.get("paint_fn")), f"{base_id}.paint_fn missing or not callable"
    assert callable(e.get("base_spec_fn")), f"{base_id}.base_spec_fn missing or not callable"


@pytest.mark.parametrize("base_id", EXOTIC_METAL_IDS)
def test_exotic_metal_paint_fn_produces_visible_variation(engine, probe_inputs, base_id):
    """paint_fn called on mid-grey input must produce measurable variation
    AND modify the input (max abs delta > 0.05). Catches the case where
    a future regression points the base at a no-op or flat-fill renderer."""
    e = engine.BASE_REGISTRY[base_id]
    out = e["paint_fn"](
        probe_inputs["mid_grey"].copy(),
        probe_inputs["shape"],
        probe_inputs["mask"],
        probe_inputs["seed"],
        1.0,
        probe_inputs["bb_2d"],
    )
    arr = np.asarray(out, dtype=np.float32)
    assert arr.shape == probe_inputs["mid_grey"].shape
    std = float(arr.std())
    delta = float(np.abs(arr - probe_inputs["mid_grey"]).max())
    assert std > 0.005, (
        f"{base_id} paint_fn output essentially flat (std={std:.4f}). "
        f"Painter would see no character from this base."
    )
    assert delta > 0.05, (
        f"{base_id} paint_fn barely modifies input (max abs delta {delta:.4f}). "
        f"Painter would experience this as 'doing nothing'."
    )


@pytest.mark.parametrize("base_id", EXOTIC_METAL_IDS)
def test_exotic_metal_spec_fn_returns_real_tuple_with_variance(engine, probe_inputs, base_id):
    """base_spec_fn must accept the engine's 5-arg signature
    (shape, seed, sm, base_M, base_R) per `engine/compose.py:1298` and
    return a 3-tuple of (M, R, CC) arrays. At LEAST ONE channel must
    show measurable variance (max ch std > 1.0 on uint8 0–255).

    Allowing flat-on-some-channels matches the design of color-shift
    bases like chromaflair where the iridescent character lives on
    M while CC stays low and steady — but TOTALLY flat across all 3
    means the base contributes no shading character at all."""
    e = engine.BASE_REGISTRY[base_id]
    bm = e.get("M", 100)
    br = e.get("R", 50)
    result = e["base_spec_fn"](probe_inputs["shape"], probe_inputs["seed"], 1.0, bm, br)
    assert isinstance(result, tuple) and len(result) == 3, (
        f"{base_id} spec_fn must return (M, R, CC) tuple, got {type(result).__name__}"
    )
    stds = [float(np.asarray(c, dtype=np.float32).std()) for c in result]
    assert max(stds) > 1.0, (
        f"{base_id} spec_fn channels all flat (per-channel stds={stds}). "
        f"Painter sees no shading character from this base's spec."
    )


def test_exotic_metal_no_paint_output_collisions(engine, probe_inputs):
    """If any two Exotic Metal bases produce byte-identical paint_fn
    output for the same input, they're functionally identical finishes
    rendered under different names — painter sees the same thing from
    different picker selections. Catches mass regression to a shared
    generic renderer."""
    hashes = {}
    for base_id in EXOTIC_METAL_IDS:
        e = engine.BASE_REGISTRY[base_id]
        out = e["paint_fn"](
            probe_inputs["mid_grey"].copy(),
            probe_inputs["shape"],
            probe_inputs["mask"],
            probe_inputs["seed"],
            1.0,
            probe_inputs["bb_2d"],
        )
        arr = np.asarray(out, dtype=np.float32)
        h = hashlib.sha256(arr.tobytes()).hexdigest()[:16]
        hashes.setdefault(h, []).append(base_id)
    collisions = {h: ids for h, ids in hashes.items() if len(ids) > 1}
    assert collisions == {}, (
        f"Exotic Metal bases share paint_fn output: {collisions}. "
        f"Different picker selections render identically — painter trust violation."
    )


def test_user_flagged_exotic_metals_are_specifically_pinned(engine, probe_inputs):
    """The 5 specifically flagged 'doing nothing' Exotic Metal bases
    (brushed_aluminum, titanium_raw, organic_metal, xirallic, chromaflair)
    must all produce visible paint variation. Pinning them by name so
    a future regression specifically affecting one of these is caught
    with a clear failure message tying back to the user's report."""
    for base_id in USER_FLAGGED_IDS:
        e = engine.BASE_REGISTRY[base_id]
        out = e["paint_fn"](
            probe_inputs["mid_grey"].copy(),
            probe_inputs["shape"],
            probe_inputs["mask"],
            probe_inputs["seed"],
            1.0,
            probe_inputs["bb_2d"],
        )
        arr = np.asarray(out, dtype=np.float32)
        delta = float(np.abs(arr - probe_inputs["mid_grey"]).max())
        assert delta > 0.05, (
            f"{base_id} (user-flagged 'doing nothing' candidate from Item 5) "
            f"renders effectively flat — max abs delta {delta:.4f}. The "
            f"original painter complaint has now actually become a real bug; "
            f"investigate the renderer in engine/paint_v2/exotic_metal.py "
            f"or the registry entry in engine/base_registry_data.py."
        )
