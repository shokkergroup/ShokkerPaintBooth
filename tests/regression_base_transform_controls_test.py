from pathlib import Path

import numpy as np


def _gradient_config(direction="diagonal_down"):
    return {
        "direction": direction,
        "stops": [
            {"pos": 0.0, "color": [0.50, 0.00, 1.00]},
            {"pos": 1.0, "color": [0.00, 1.00, 0.00]},
        ],
    }


def test_base_color_gradient_honors_base_rotation():
    from engine.compose import compose_paint_mod

    shape = (96, 96)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((shape[0], shape[1], 3), 0.10, dtype=np.float32)
    kwargs = dict(
        base_id="gloss",
        pattern_id="none",
        shape=shape,
        mask=mask,
        seed=31031,
        pm=1.0,
        bb=0.0,
        base_color_mode="gradient",
        base_color=_gradient_config("diagonal_down"),
        base_color_strength=1.0,
        monolithic_registry={},
    )

    out0 = compose_paint_mod(paint=paint.copy(), base_rotation=0.0, base_scale=1.0, **kwargs)
    out90 = compose_paint_mod(paint=paint.copy(), base_rotation=90.0, base_scale=1.0, **kwargs)

    assert float(np.mean(np.abs(out0 - out90))) > 0.04
    assert float(np.linalg.norm(out0[0, 0] - out90[0, 0])) > 0.10


def test_base_color_gradient_honors_base_scale():
    from engine.compose import compose_paint_mod

    shape = (96, 96)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((shape[0], shape[1], 3), 0.10, dtype=np.float32)
    kwargs = dict(
        base_id="gloss",
        pattern_id="none",
        shape=shape,
        mask=mask,
        seed=31032,
        pm=1.0,
        bb=0.0,
        base_color_mode="gradient",
        base_color=_gradient_config("horizontal"),
        base_color_strength=1.0,
        monolithic_registry={},
    )

    out1 = compose_paint_mod(paint=paint.copy(), base_rotation=0.0, base_scale=1.0, **kwargs)
    out2 = compose_paint_mod(paint=paint.copy(), base_rotation=0.0, base_scale=2.0, **kwargs)

    assert float(np.mean(np.abs(out1 - out2))) > 0.03
    assert float(np.linalg.norm(out1[0, 0] - out2[0, 0])) > 0.04


def test_generic_gradient_finish_honors_base_scale():
    from engine.render import render_generic_finish

    shape = (96, 96)
    mask = np.ones(shape, dtype=np.float32)
    zone = {"finish_colors": {"c1": "#8000ff", "c2": "#00ff00"}}
    paint = np.full((shape[0], shape[1], 3), 0.10, dtype=np.float32)

    _, out1 = render_generic_finish(
        "grad_neon_violet_diag",
        zone,
        paint.copy(),
        shape,
        mask,
        seed=31033,
        sm=1.0,
        pm=1.0,
        bb=0.0,
        rotation=0.0,
        base_scale=1.0,
    )
    _, out2 = render_generic_finish(
        "grad_neon_violet_diag",
        zone,
        paint.copy(),
        shape,
        mask,
        seed=31033,
        sm=1.0,
        pm=1.0,
        bb=0.0,
        rotation=0.0,
        base_scale=2.0,
    )

    assert float(np.mean(np.abs(out1 - out2))) > 0.02
    assert float(np.linalg.norm(out1[0, 0] - out2[0, 0])) > 0.04


def test_generic_gradient_finish_honors_base_flip_and_pan():
    from engine.render import render_generic_finish

    shape = (96, 96)
    mask = np.ones(shape, dtype=np.float32)
    zone = {"finish_colors": {"c1": "#8000ff", "c2": "#00ff00"}}
    paint = np.full((shape[0], shape[1], 3), 0.10, dtype=np.float32)

    _, normal = render_generic_finish(
        "grad_neon_violet_diag",
        zone,
        paint.copy(),
        shape,
        mask,
        seed=31034,
        sm=1.0,
        pm=1.0,
        bb=0.0,
        rotation=0.0,
        base_scale=1.0,
    )
    _, flipped = render_generic_finish(
        "grad_neon_violet_diag",
        zone,
        paint.copy(),
        shape,
        mask,
        seed=31034,
        sm=1.0,
        pm=1.0,
        bb=0.0,
        rotation=0.0,
        base_scale=1.0,
        base_flip_h=True,
    )
    _, panned = render_generic_finish(
        "grad_neon_violet_diag",
        zone,
        paint.copy(),
        shape,
        mask,
        seed=31034,
        sm=1.0,
        pm=1.0,
        bb=0.0,
        rotation=0.0,
        base_scale=1.0,
        base_offset_x=0.20,
        base_offset_y=0.80,
    )

    assert float(np.mean(np.abs(normal - flipped))) > 0.03
    assert float(np.mean(np.abs(normal - panned))) > 0.03


def test_monolithic_transform_helper_moves_paint_and_spec_together():
    from shokker_engine_v2 import _apply_base_transform_to_zone_output

    shape = (64, 64)
    y, x = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    xf = x / (shape[1] - 1)
    yf = y / (shape[0] - 1)
    mask = np.ones(shape, dtype=np.float32)
    before = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    after = np.dstack([xf, yf, np.full(shape, 0.25, dtype=np.float32)]).astype(np.float32)
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.float32)
    spec[:, :, 0] = xf * 255.0
    spec[:, :, 1] = yf * 255.0
    spec[:, :, 2] = 32.0
    spec[:, :, 3] = 255.0

    moved_paint, moved_spec = _apply_base_transform_to_zone_output(
        before,
        after,
        spec,
        mask,
        shape,
        scale=1.0,
        offset_x=0.5,
        offset_y=0.5,
        rotation=0.0,
        flip_h=True,
        flip_v=False,
    )

    assert float(np.mean(np.abs(after - moved_paint))) > 0.15
    assert float(np.mean(np.abs(spec[:, :, :3] - moved_spec[:, :, :3]))) > 20.0
    assert moved_paint[0, 0, 0] > moved_paint[0, -1, 0]
    assert moved_spec[0, 0, 0] > moved_spec[0, -1, 0]


def test_monolithic_transform_uses_source_safe_seed_not_template_pixels():
    from shokker_engine_v2 import (
        _apply_base_transform_to_zone_output,
        _monolithic_transform_seed_paint,
    )

    shape = (64, 64)
    y, x = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    xf = x / (shape[1] - 1)
    mask = np.zeros(shape, dtype=np.float32)
    mask[:, 32:] = 1.0
    before = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    before[4:14, 4:14, 0] = 1.0  # source artwork outside the target zone
    seed = _monolithic_transform_seed_paint(before, mask, shape)
    clean_finish = seed.copy()
    clean_finish[:, :, 1] = xf
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.float32)
    spec[:, :, 0] = xf * 255.0
    spec[:, :, 1] = 80.0
    spec[:, :, 2] = 32.0
    spec[:, :, 3] = 255.0

    moved_paint, _ = _apply_base_transform_to_zone_output(
        before,
        clean_finish,
        spec,
        mask,
        shape,
        scale=1.0,
        offset_x=0.5,
        offset_y=0.5,
        rotation=90.0,
        flip_h=False,
        flip_v=False,
    )

    assert float(seed[:, :, 0].max()) < 0.01
    assert np.allclose(moved_paint[4:14, 4:14, 0], before[4:14, 4:14, 0])
    assert float(moved_paint[:, 32:, 0].max()) < 0.01


def test_preview_and_export_preserve_base_transform_payloads():
    src = Path("server.py").read_text(encoding="utf-8", errors="ignore")
    preview = src.split("@app.route('/preview-render'", 1)[1].split("@app.route('/render'", 1)[0]
    export = src.split("@app.route('/export-psd-layers'", 1)[1]

    for field in (
        '"base_scale"',
        '"base_offset_x"',
        '"base_offset_y"',
        '"base_rotation"',
        '"base_flip_h"',
        '"base_flip_v"',
    ):
        assert field in preview
        assert field in export


def test_engine_passes_full_base_transform_to_generic_finish_renderer():
    src = Path("shokker_engine_v2.py").read_text(encoding="utf-8", errors="ignore")
    generic_calls = [line for line in src.splitlines() if "render_generic_finish(" in line]

    assert len(generic_calls) >= 6
    assert all("base_scale=zone_base_scale" in line for line in generic_calls)
    assert all("base_offset_x=" in line for line in generic_calls)
    assert all("base_offset_y=" in line for line in generic_calls)
    assert all("base_flip_h=" in line for line in generic_calls)
    assert all("base_flip_v=" in line for line in generic_calls)
