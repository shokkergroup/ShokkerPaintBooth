"""Behavioral ratchet — Metallic Standard bases render real paint+spec
WITHOUT crashing at swatch shapes.

## Why this exists (2026-04-25 overnight Iter 7)

User Item 5 brief specifically called out:
  "Metallic Standard: regular Metallic, Copper, Satan's Apple crash"

Iter 7 audit:
  * "Satan's Apple" is `candy_apple` — confirmed the only entry whose
    display name matches /satan|apple/.
  * `candy_apple`, `metallic`, `copper` all render cleanly at 256x256.
    paint stds 0.026–0.249, max abs delta 0.212–0.526; spec channels
    all show variance.
  * No crashes at small shapes either ({32, 48, 64, 96}^2 for paint and
    spec). The user-reported crash on Satan's Apple is HISTORIC —
    no longer present in the current renderer.
  * All 22 Metallic Standard bases produce unique paint and spec output
    (no hash collisions across the category).

This file pins the working state. The explicit `candy_apple` no-crash-
at-swatch-shape test guards against the historic crash returning.

## Surfaces protected

1. Each Metallic Standard base in BASE_REGISTRY with callable paint_fn
   and base_spec_fn.
2. `candy_apple` (Satan's Apple) renders without crashing at every
   swatch shape the server can request — directly addresses the user's
   "Satan's Apple crash" report.
3. `metallic` and `copper` (the other 2 user-flagged Metallic Standard
   bases) produce visible paint variation.
4. No two Metallic Standard bases share paint output (no shared-
   generic regression in this category).
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest


METALLIC_STANDARD_IDS = [
    "candy", "candy_apple", "champagne", "copper", "gunmetal", "gunmetal_satin",
    "metal_flake_base", "original_metal_flake", "champagne_flake",
    "fine_silver_flake", "blue_ice_flake", "bronze_flake", "gunmetal_flake",
    "green_flake", "fire_flake", "metallic", "midnight_pearl", "pearl",
    "pearlescent_white", "pewter", "satin_metal", "alubeam",
]

USER_FLAGGED_IDS = ["candy_apple", "metallic", "copper"]

# Server.py serves swatches from SWATCH_SIZE_MIN=32 up. Every Metallic
# Standard base must survive every swatch shape without crashing.
SWATCH_SHAPES = [(32, 32), (48, 48), (64, 64), (96, 96), (128, 128), (256, 256)]


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


@pytest.mark.parametrize("base_id", METALLIC_STANDARD_IDS)
def test_metallic_standard_base_registered(engine, base_id):
    """Every Metallic Standard picker id must be in BASE_REGISTRY with
    callable paint_fn and base_spec_fn."""
    assert base_id in engine.BASE_REGISTRY, (
        f"{base_id} missing from BASE_REGISTRY — picker exposes it but "
        f"engine won't render anything. Item 5 'doing nothing' regression."
    )
    e = engine.BASE_REGISTRY[base_id]
    assert callable(e.get("paint_fn")), f"{base_id}.paint_fn missing/invalid"
    assert callable(e.get("base_spec_fn")), f"{base_id}.base_spec_fn missing/invalid"


@pytest.mark.parametrize("base_id", METALLIC_STANDARD_IDS)
def test_metallic_standard_paint_produces_visible_variation(engine, probe_inputs, base_id):
    """paint_fn called on mid-grey input must produce measurable
    variation AND modify the input meaningfully."""
    e = engine.BASE_REGISTRY[base_id]
    out = e["paint_fn"](
        probe_inputs["mid_grey"].copy(), probe_inputs["shape"],
        probe_inputs["mask"], probe_inputs["seed"], 1.0, probe_inputs["bb_2d"],
    )
    arr = np.asarray(out, dtype=np.float32)
    std = float(arr.std())
    delta = float(np.abs(arr - probe_inputs["mid_grey"]).max())
    assert std > 0.005, f"{base_id} paint output flat (std={std:.4f})"
    assert delta > 0.05, f"{base_id} paint barely modifies input (delta={delta:.4f})"


@pytest.mark.parametrize("base_id", METALLIC_STANDARD_IDS)
def test_metallic_standard_spec_returns_real_tuple_with_variance(engine, probe_inputs, base_id):
    """base_spec_fn must accept the engine's 5-arg signature and return
    a 3-tuple where at least one channel has measurable variance."""
    e = engine.BASE_REGISTRY[base_id]
    bm = e.get("M", 100); br = e.get("R", 50)
    r = e["base_spec_fn"](probe_inputs["shape"], probe_inputs["seed"], 1.0, bm, br)
    assert isinstance(r, tuple) and len(r) == 3, (
        f"{base_id} spec_fn must return (M,R,CC) tuple"
    )
    stds = [float(np.asarray(c, dtype=np.float32).std()) for c in r]
    assert max(stds) > 1.0, (
        f"{base_id} spec channels all flat (stds={stds})"
    )


@pytest.mark.parametrize("base_id", METALLIC_STANDARD_IDS)
@pytest.mark.parametrize("shape", SWATCH_SHAPES)
def test_metallic_standard_no_crash_at_swatch_shape(engine, base_id, shape):
    """Every Metallic Standard base must render without crashing at
    every server-requestable swatch shape (32, 48, 64, 96, 128, 256).

    DIRECTLY GUARDS THE USER-REPORTED 'Satan's Apple crash' — `candy_apple`
    (Satan's Apple) appears in this parametrize and must not crash.
    """
    e = engine.BASE_REGISTRY[base_id]
    H, W = shape
    mask = np.ones((H, W), dtype=np.float32)
    paint_in = np.full((H, W, 3), 0.45, dtype=np.float32)
    bb = np.zeros((H, W), dtype=np.float32)
    seed = 42
    bm = e.get("M", 100); br = e.get("R", 50)
    # paint_fn at this shape must not raise
    e["paint_fn"](paint_in.copy(), shape, mask, seed, 1.0, bb)
    # spec_fn at this shape must not raise
    e["base_spec_fn"](shape, seed, 1.0, bm, br)


def test_metallic_standard_no_paint_collisions(engine, probe_inputs):
    """No two Metallic Standard bases should produce byte-identical
    paint output — catches regression to a shared generic renderer."""
    hashes = {}
    for fid in METALLIC_STANDARD_IDS:
        e = engine.BASE_REGISTRY[fid]
        out = e["paint_fn"](
            probe_inputs["mid_grey"].copy(), probe_inputs["shape"],
            probe_inputs["mask"], probe_inputs["seed"], 1.0, probe_inputs["bb_2d"],
        )
        h = hashlib.sha256(np.asarray(out, dtype=np.float32).tobytes()).hexdigest()[:16]
        hashes.setdefault(h, []).append(fid)
    collisions = {h: ids for h, ids in hashes.items() if len(ids) > 1}
    assert collisions == {}, (
        f"Metallic Standard bases share paint output: {collisions}"
    )


def test_satan_apple_renders_at_all_swatch_shapes(engine):
    """Tighter pin specifically for 'Satan's Apple' (candy_apple) per the
    user's Item 5 'Satan's Apple crash' report. Iter 7 confirmed the
    historic crash is no longer present; this test makes its return
    fail loudly with a message tying back to the user report."""
    e = engine.BASE_REGISTRY["candy_apple"]
    bm = e.get("M", 100); br = e.get("R", 50)
    for shape in SWATCH_SHAPES:
        H, W = shape
        mask = np.ones((H, W), dtype=np.float32)
        paint_in = np.full((H, W, 3), 0.45, dtype=np.float32)
        bb = np.zeros((H, W), dtype=np.float32)
        try:
            e["paint_fn"](paint_in.copy(), shape, mask, 42, 1.0, bb)
            e["base_spec_fn"](shape, 42, 1.0, bm, br)
        except Exception as exc:
            pytest.fail(
                f"'Satan's Apple' (candy_apple) crashed at swatch shape {shape}: "
                f"{type(exc).__name__}: {exc}. The historic crash class the user "
                f"reported in Item 5 has returned. Investigate "
                f"engine/paint_v2/metallic_standard.py and the candy_apple entry "
                f"in engine/base_registry_data.py."
            )
