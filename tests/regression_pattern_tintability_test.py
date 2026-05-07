from __future__ import annotations

import numpy as np


def _canvas(size: int = 128):
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.zeros((size, size, 3), dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    return shape, mask, paint, bb


def test_spb4_rebuilt_direct_patterns_obey_explicit_solid_color():
    import shokker_engine_v2  # noqa: F401 - applies SPB-4 registry patches
    from engine.compose import compose_paint_mod

    shape, mask, paint, bb = _canvas()

    for pattern_id in ("aurora_bands", "julia_boundary", "skull_wings", "decade_90s_fresh_prince"):
        red = compose_paint_mod(
            "gloss",
            pattern_id,
            paint.copy(),
            shape,
            mask,
            123,
            1.0,
            bb,
            base_color_mode="solid",
            base_color=[1.0, 0.0, 0.0],
            base_color_strength=1.0,
        )
        green = compose_paint_mod(
            "gloss",
            pattern_id,
            paint.copy(),
            shape,
            mask,
            123,
            1.0,
            bb,
            base_color_mode="solid",
            base_color=[0.0, 1.0, 0.0],
            base_color_strength=1.0,
        )

        assert float(np.mean(np.abs(red - green))) > 0.20, pattern_id
        assert float(red[:, :, 0].mean()) > float(red[:, :, 1].mean()) + 0.20, pattern_id
        assert float(green[:, :, 1].mean()) > float(green[:, :, 0].mean()) + 0.20, pattern_id


def test_spb4_rebuilt_patterns_are_visible_as_base_overlay_color_masks():
    import shokker_engine_v2  # noqa: F401 - applies SPB-4 registry patches
    from engine.compose import compose_paint_mod

    shape, mask, paint, bb = _canvas()

    for pattern_id in ("aurora_bands", "birch_bark", "decade_90s_fresh_prince"):
        out = compose_paint_mod(
            "gloss",
            "none",
            paint.copy(),
            shape,
            mask,
            321,
            1.0,
            bb,
            second_base="gloss",
            second_base_color=[1.0, 0.0, 0.0],
            second_base_strength=1.0,
            second_base_blend_mode="pattern",
            second_base_pattern=pattern_id,
        )

        red_fraction = float((out[:, :, 0] > out[:, :, 1] + 0.05).mean())
        assert red_fraction > 0.18, pattern_id
        assert float(out[:, :, 0].mean()) > float(out[:, :, 1].mean()) + 0.03, pattern_id
