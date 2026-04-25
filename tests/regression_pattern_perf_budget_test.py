from __future__ import annotations

import time

import numpy as np


def test_spec_overlay_small_scale_uses_canvas_sized_generation():
    from engine.compose import _scale_down_spec_pattern

    calls = []

    def fake_spec(shape, seed=0, sm=1.0, **kwargs):
        calls.append(tuple(shape))
        return np.full(shape[:2], 0.5, dtype=np.float32)

    out = _scale_down_spec_pattern(fake_spec, 0.30, (512, 512), 123, 1.0, {})

    assert out.shape == (512, 512)
    assert calls == [(512, 512)]


def test_regular_pattern_rebuilds_are_allowlisted_not_family_broad():
    import shokker_engine_v2 as eng

    bespoke = eng._SPB_BESPOKE_PATTERN_REBUILD_IDS
    candidates = eng._SPB_PATTERN_REBUILD_MODES

    assert len(bespoke) < 80
    assert len(bespoke) < len(candidates)
    assert "zigzag_bands" not in bespoke
    assert "fiber_optic" in bespoke
    assert "flame_inferno_wall" in bespoke


def test_regular_pattern_hot_paths_stay_under_budget():
    import shokker_engine_v2  # noqa: F401 - applies registry patches
    from engine.registry import PATTERN_REGISTRY

    shape = (512, 512)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((shape[0], shape[1], 3), 0.45, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    hot_ids = (
        "fiber_optic",
        "graphene_hex",
        "hex_mandala",
        "shokk_fracture",
        "shokk_waveform",
        "shokk_plasma_storm",
        "shokk_tesseract",
        "flame_inferno_wall",
        "flame_blue_propane",
        "flame_ember_field",
    )
    worst = 0.0
    start = time.perf_counter()
    for pid in hot_ids:
        entry = PATTERN_REGISTRY[pid]
        tex_fn = entry.get("texture_fn")
        paint_fn = entry.get("paint_fn")
        if tex_fn is not None:
            t0 = time.perf_counter()
            tex_fn(shape, mask, 123, 1.0)
            worst = max(worst, time.perf_counter() - t0)
        if paint_fn is not None:
            t0 = time.perf_counter()
            paint_fn(paint, shape, mask, 123, 1.0, bb)
            worst = max(worst, time.perf_counter() - t0)

    assert worst < 1.25
    assert time.perf_counter() - start < 12.0


def test_spec_pattern_hot_paths_stay_under_budget():
    from engine.spec_patterns import PATTERN_CATALOG

    shape = (512, 512)
    hot_ids = (
        "sparkle_comet",
        "spec_electroplated_chrome",
        "spec_xirallic_crystal",
        "spec_pvd_coating",
        "quantum_noise",
        "brake_dust_buildup",
        "spec_subsurface_depth",
        "gold_leaf_torn",
        "spec_iridescent_film",
        "sparkle_nebula",
    )
    worst = 0.0
    start = time.perf_counter()
    for pid in hot_ids:
        t0 = time.perf_counter()
        out = PATTERN_CATALOG[pid](shape, seed=123, sm=1.0)
        worst = max(worst, time.perf_counter() - t0)
        assert out.shape == shape

    assert worst < 0.90
    assert time.perf_counter() - start < 8.0
