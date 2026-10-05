"""Regression coverage for Easy By Color scaling on monolithic finishes.

The selected finish and the borrowed authored-color source are independent
materials.  Changing ``base_color_scale`` must transform only the borrowed
paint texture; it must not alter the selected finish's spec map.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import numpy as np
from PIL import Image


def test_build_multi_zone_scales_monolithic_color_source_without_changing_spec(
    tmp_path, monkeypatch
):
    import shokker_engine_v2 as engine

    height = width = 64
    source = np.full((height, width, 3), 96, dtype=np.uint8)
    source_path = tmp_path / "source.png"
    Image.fromarray(source, mode="RGB").save(source_path)

    zone_mask = np.zeros((height, width), dtype=np.float32)
    zone_mask[8:56, 8:56] = 1.0

    def selected_spec(shape, mask, seed, spec_mult):
        h, w = shape
        out = np.zeros((h, w, 4), dtype=np.uint8)
        out[:, :, 0] = np.where(mask > 0.5, 173, 0).astype(np.uint8)
        out[:, :, 1] = np.where(mask > 0.5, 91, 0).astype(np.uint8)
        out[:, :, 2] = np.where(mask > 0.5, 207, 0).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    def selected_paint(paint, shape, mask, seed, paint_mult, brightness_boost):
        out = np.asarray(paint, dtype=np.float32)[:, :, :3].copy()
        out[:, :, :] = (0.18, 0.22, 0.28)
        return out

    def patterned_color_source(paint, shape, mask, seed, paint_mult, brightness_boost):
        h, w = shape
        yy, xx = np.indices((h, w))
        cells = ((xx // 7) + (yy // 5)) % 2
        out = np.empty((h, w, 3), dtype=np.float32)
        out[cells == 0] = (0.95, 0.12, 0.04)
        out[cells == 1] = (0.04, 0.78, 0.92)
        return out

    monkeypatch.setitem(
        engine.MONOLITHIC_REGISTRY,
        "synthetic_selected_material",
        (selected_spec, selected_paint),
    )
    monkeypatch.setitem(
        engine.MONOLITHIC_REGISTRY,
        "synthetic_patterned_color",
        (selected_spec, patterned_color_source),
    )

    def render(color_scale):
        zone = {
            "name": "Easy By Color synthetic zone",
            "color": "everything",
            "region_mask": zone_mask,
            "finish": "synthetic_selected_material",
            "intensity": "100",
            "base_scale": 1.0,
            "base_color_mode": "from_special",
            "base_color_source": "mono:synthetic_patterned_color",
            "base_color_strength": 1.0,
            "base_color_scale": color_scale,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            paint, spec = engine.build_multi_zone(
                str(source_path),
                str(tmp_path / f"out_{color_scale}"),
                [zone],
                seed=20260721,
                preview_mode=True,
            )
        return np.asarray(paint, dtype=np.float32), np.asarray(spec)

    paint_original_scale, spec_original_scale = render(1.0)
    paint_finer_scale, spec_finer_scale = render(0.4)

    inside = zone_mask > 0.5
    outside = ~inside
    inside_delta = np.mean(
        np.abs(paint_original_scale[inside, :3] - paint_finer_scale[inside, :3])
    )

    assert inside_delta > 1.0, (
        "base_color_scale did not visibly transform the borrowed monolithic "
        f"paint texture (mean in-zone delta={inside_delta:.4f})"
    )
    assert np.array_equal(spec_original_scale, spec_finer_scale), (
        "base_color_scale changed spec output; it must scale authored paint color only"
    )
    assert np.array_equal(
        paint_original_scale[outside, :3], paint_finer_scale[outside, :3]
    ), "the color-source scale escaped the selected zone"


def test_car_helmet_and_suit_monolithic_overrides_share_the_scale_helper():
    import shokker_engine_v2 as engine

    source = Path(engine.__file__).read_text(encoding="utf-8")
    call = "base_scale=_zone_monolithic_color_source_scale(zone, _base_ctrl)"

    assert source.count(call) == 3, (
        "car, helmet, and suit monolithic color overrides must all compose "
        "base_scale with base_color_scale through the shared helper"
    )
