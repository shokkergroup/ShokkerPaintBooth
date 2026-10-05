import numpy as np

from engine.compose import compose_paint_mod
from shokker_engine_v2 import _apply_base_transform_to_zone_paint_only


def test_scaled_base_material_does_not_tile_template_pixels_into_zone():
    shape = (96, 96)
    paint = np.zeros((96, 96, 3), dtype=np.float32)
    paint[:] = [0.0, 0.82, 0.95]
    paint[:, 48:] = [1.0, 1.0, 1.0]
    paint[20:40, 20:76] = [0.0, 0.0, 0.0]

    mask = np.zeros((96, 96), dtype=np.float32)
    mask[16:80, 16:80] = 1.0

    out = compose_paint_mod(
        "cx_arctic",
        "none",
        paint.copy(),
        shape,
        mask,
        seed=123,
        pm=1.0,
        bb=0.0,
        base_scale=0.5,
    )

    inside = out[mask > 0.5, :3]
    outside = out[mask < 0.5, :3]

    pure_template_white_fraction = np.mean(np.all(inside > 0.93, axis=1))
    assert pure_template_white_fraction == 0.0
    assert np.max(np.abs(outside - paint[mask < 0.5, :3])) == 0.0


def test_zone_post_transform_sanitizes_out_of_mask_template_pixels():
    shape = (96, 96)
    before = np.zeros((96, 96, 3), dtype=np.float32)
    before[:] = [0.0, 0.82, 0.95]
    before[:, 48:] = [1.0, 1.0, 1.0]

    mask = np.zeros((96, 96), dtype=np.float32)
    mask[16:80, 16:80] = 1.0

    after = before.copy()
    after[mask > 0.5] = [0.2, 0.55, 0.9]

    out = _apply_base_transform_to_zone_paint_only(
        before,
        after,
        mask,
        shape,
        scale=0.5,
        offset_x=0.5,
        offset_y=0.5,
        rotation=0,
        flip_h=False,
        flip_v=False,
    )

    inside = out[mask > 0.5, :3]
    outside = out[mask < 0.5, :3]

    pure_template_white_fraction = np.mean(np.all(inside > 0.93, axis=1))
    assert pure_template_white_fraction == 0.0
    assert np.max(np.abs(outside - before[mask < 0.5, :3])) == 0.0


def test_scaled_base_color_source_uses_full_clean_material_plate():
    shape = (96, 96)
    paint = np.zeros((96, 96, 3), dtype=np.float32)
    paint[:] = [0.0, 0.82, 0.95]

    mask = np.zeros((96, 96), dtype=np.float32)
    mask[16:80, 16:80] = 1.0

    out = compose_paint_mod(
        "cx_arctic",
        "none",
        paint.copy(),
        shape,
        mask,
        seed=123,
        pm=1.0,
        bb=0.0,
        base_color_mode="from_special",
        base_color_source="cx_arctic",
        base_color_strength=1.0,
        base_scale=0.5,
    )

    inside = out[mask > 0.5, :3]
    outside = out[mask < 0.5, :3]
    neutral_seed = np.array([0.533, 0.533, 0.533], dtype=np.float32)

    neutral_seed_fraction = np.mean(np.all(np.abs(inside - neutral_seed) < 0.025, axis=1))
    assert neutral_seed_fraction == 0.0
    assert np.max(np.abs(outside - paint[mask < 0.5, :3])) == 0.0


def test_base_color_scale_is_independent_from_base_material_scale():
    shape = (96, 96)
    paint = np.zeros((96, 96, 3), dtype=np.float32)
    paint[:] = [0.0, 0.82, 0.95]

    mask = np.zeros((96, 96), dtype=np.float32)
    mask[16:80, 16:80] = 1.0

    default_color_scale = compose_paint_mod(
        "f_frozen",
        "none",
        paint.copy(),
        shape,
        mask,
        seed=123,
        pm=1.0,
        bb=0.0,
        base_color_mode="from_special",
        base_color_source="cx_arctic",
        base_color_strength=1.0,
        base_scale=1.0,
        base_color_scale=1.0,
    )
    smaller_color_scale = compose_paint_mod(
        "f_frozen",
        "none",
        paint.copy(),
        shape,
        mask,
        seed=123,
        pm=1.0,
        bb=0.0,
        base_color_mode="from_special",
        base_color_source="cx_arctic",
        base_color_strength=1.0,
        base_scale=1.0,
        base_color_scale=0.5,
    )

    inside = mask > 0.5
    outside = mask < 0.5
    mean_inside_delta = np.mean(np.abs(default_color_scale[inside, :3] - smaller_color_scale[inside, :3]))

    assert mean_inside_delta > 0.01
    assert np.max(np.abs(smaller_color_scale[outside, :3] - paint[outside, :3])) == 0.0


def test_monolithic_base_color_source_honors_color_scale():
    from shokker_engine_v2 import MONOLITHIC_REGISTRY

    shape = (96, 96)
    paint = np.zeros((96, 96, 3), dtype=np.float32)
    paint[:] = [0.0, 0.82, 0.95]

    mask = np.zeros((96, 96), dtype=np.float32)
    mask[16:80, 16:80] = 1.0

    default_color_scale = compose_paint_mod(
        "f_frozen",
        "none",
        paint.copy(),
        shape,
        mask,
        seed=123,
        pm=1.0,
        bb=0.0,
        base_color_mode="from_special",
        base_color_source="gravity_well",
        base_color_strength=1.0,
        base_scale=1.0,
        base_color_scale=1.0,
        monolithic_registry=MONOLITHIC_REGISTRY,
    )
    smaller_color_scale = compose_paint_mod(
        "f_frozen",
        "none",
        paint.copy(),
        shape,
        mask,
        seed=123,
        pm=1.0,
        bb=0.0,
        base_color_mode="from_special",
        base_color_source="gravity_well",
        base_color_strength=1.0,
        base_scale=1.0,
        base_color_scale=0.35,
        monolithic_registry=MONOLITHIC_REGISTRY,
    )

    inside = mask > 0.5
    mean_inside_delta = np.mean(np.abs(default_color_scale[inside, :3] - smaller_color_scale[inside, :3]))

    assert mean_inside_delta > 0.01
