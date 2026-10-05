"""Midnight Candy — broad violet candy folds with cyan/magenta angle flip."""
from __future__ import annotations

import numpy as np

from .core import FinishResult, WORK, begin, blur, coords, finish, normal_light, pack_physical, resize_result, ridge, smooth, unit


FINISH_ID = "neon2_frequency_fault"
DISPLAY_NAME = "Midnight Candy"
DEFAULT_SEED = 0xC4AD9

# SPB-105 / NU-V4-MC-1 / 2026-08-27 — owner verdict: v3 lacked Oil
# Slick mechanics, real neon, and Tokyo Drift identity.  Broad candy body
# folds drive the angle flip; fine pearl anatomy does not become wallpaper.
# NU-V4 whole-car correction: deterministic flake-flow now traverses every
# candy depth while remaining subordinate to the cyan/magenta fold shoulders.


def _mix(paint: np.ndarray, color: tuple[float, float, float], amount: np.ndarray) -> np.ndarray:
    a = np.clip(amount, 0.0, 1.0)[..., None]
    c = np.asarray(color, np.float32)
    return paint * (1.0 - a) + c * a


def build(seed: int = DEFAULT_SEED, size: int = WORK) -> FinishResult:
    started = begin()
    size = int(size)
    if size < 256:
        raise ValueError("Midnight Candy requires size >= 256")
    if size > WORK:
        source = build(seed=seed, size=WORK)
        paint_a, paint_b, spec = resize_result(source, size)
        return finish(started, FINISH_ID, DISPLAY_NAME, paint_a, paint_b, spec, source.carrier, source.material_story)
    x, y = coords(size)

    # One smooth candy-lacquer relief supplies broad, asymmetric body folds.
    phase = (
        2.30 * x
        + 1.12 * y
        + 0.38 * np.sin(1.75 * y + 0.18 * np.sin(2.2 * x))
        + 0.16 * np.sin(3.05 * x - 0.72 * y)
    ).astype(np.float32)
    sheet = (0.50 + 0.35 * np.sin(phase) + 0.12 * np.sin(1.72 * phase + 0.65 * x)).astype(np.float32)
    relief = unit(sheet)
    bay = smooth(0.28, 0.72, relief)
    fold_a = np.exp(-(((relief - 0.43) / 0.085) ** 2)).astype(np.float32)
    fold_b = np.exp(-(((relief - 0.67) / 0.090) ** 2)).astype(np.float32)
    shoulders = np.clip(0.78 * fold_a + 0.72 * fold_b, 0.0, 1.0)
    deep_bays = smooth(0.62, 0.86, relief)

    # Six attached native-fine histories follow one candy-flow axis. Random
    # mica particles, fake scratches, and dust nibs are deliberately absent.
    flow_axis = x + 0.10 * np.sin(2.6 * y) - 0.13 * y + 0.020 * np.sin(5.1 * y)
    flow_phase = 49.0 * flow_axis + 1.10 * relief
    flake_flow = ridge(flow_phase, 0.16) * (0.36 + 0.64 * bay)
    flake_rims = np.maximum(ridge(flow_phase - 0.29, 0.11),
                            ridge(flow_phase + 0.29, 0.11))
    flake_rims *= 0.30 + 0.70 * bay
    pearl_strokes = ridge(61.0 * flow_axis + 0.72 * relief, 0.085) * shoulders
    pinstripes = ridge(42.0 * flow_axis + 0.45 * relief + 0.20, 0.080) * fold_a
    mica_lamellae = ridge(57.0 * flow_axis + 0.72 * relief + 0.33, 0.10) * shoulders
    clear_pulls = ridge(53.0 * flow_axis + 0.38 * relief + 0.61, 0.080) * fold_b
    resin_shear = ridge(39.0 * flow_axis + 0.58 * relief + 0.21, 0.14)
    resin_shear *= 0.30 + 0.70 * (1.0 - shoulders)

    height = blur(0.72 * relief + 0.46 * shoulders
                  + 0.08 * pearl_strokes + 0.10 * clear_pulls, 1.55)
    light_a = smooth(-0.16, 0.74, normal_light(height, (0.65, -0.27, 0.71)))
    light_b = smooth(-0.16, 0.74, normal_light(height, (-0.59, 0.40, 0.70)))
    turn_a = np.clip(shoulders * light_a + 0.42 * fold_a * (1.0 - light_b), 0.0, 1.0)
    turn_b = np.clip(shoulders * light_b + 0.42 * fold_b * (1.0 - light_a), 0.0, 1.0)

    ground = np.empty((size, size, 3), np.float32)
    ground[:] = (0.025, 0.004, 0.075)
    violet_depth = np.clip(0.20 + 0.58 * bay + 0.18 * deep_bays, 0.0, 0.82)
    depth_veil = np.clip(0.50 + 0.28 * np.sin(2.15 * phase + 0.35)
                         + 0.18 * np.sin(4.4 * phase - 0.55 * y), 0.0, 1.0)
    ground_a = _mix(ground, (0.10, 0.015, 0.34), 0.16 * depth_veil * (1.0 - bay))
    ground_b = _mix(ground, (0.20, 0.012, 0.30), 0.16 * (1.0 - depth_veil) * (1.0 - bay))
    paint_a = _mix(ground_a, (0.30, 0.025, 0.70), violet_depth)
    paint_b = _mix(ground_b, (0.30, 0.025, 0.70), violet_depth)

    # The alternate state changes which physical shoulders are exposed.  The
    # cyan/magenta flip is therefore spatial optical travel, not a global tint.
    paint_a = _mix(paint_a, (0.02, 0.92, 1.00), turn_a)
    paint_a = _mix(paint_a, (1.00, 0.035, 0.72), 0.48 * turn_b)
    b_magenta_owner = np.clip(
        0.92 * fold_b * smooth(0.18, 0.78, light_b)
        + 0.66 * shoulders * (1.0 - light_a)
        + 0.28 * deep_bays * light_b,
        0.0,
        1.0,
    )
    b_blue_owner = np.clip(
        0.74 * fold_a * (1.0 - light_b)
        + 0.58 * clear_pulls
        + 0.34 * pearl_strokes * light_b,
        0.0,
        1.0,
    )
    paint_b = _mix(paint_b, (1.00, 0.025, 0.82), b_magenta_owner)
    paint_b = _mix(paint_b, (0.06, 0.70, 1.00), 0.72 * b_blue_owner)
    hot_a = np.clip(0.58 * pearl_strokes + 0.68 * mica_lamellae
                    + 0.38 * pinstripes + 0.34 * clear_pulls, 0.0, 1.0)
    hot_b = np.clip(0.58 * clear_pulls + 0.68 * mica_lamellae
                    + 0.38 * pinstripes + 0.34 * pearl_strokes, 0.0, 1.0)
    paint_a = _mix(paint_a, (0.92, 0.96, 1.00), 0.68 * hot_a * (0.36 + 0.64 * light_a))
    paint_b = _mix(paint_b, (1.00, 0.86, 0.98), 0.84 * hot_b * smooth(0.14, 0.78, light_b))
    candy_flow = np.clip(0.52 * flake_flow + 0.44 * flake_rims
                         + 0.36 * resin_shear, 0.0, 1.0)
    paint_a = _mix(paint_a, (0.28, 0.62, 0.86),
                   0.14 * candy_flow * (0.28 + 0.72 * light_a))
    paint_b = _mix(paint_b, (0.72, 0.24, 0.82),
                   0.15 * candy_flow * (0.28 + 0.72 * light_b))

    metal = unit(0.04 + 0.48 * mica_lamellae + 0.42 * pearl_strokes
                 + 0.38 * flake_rims + 0.30 * pinstripes
                 + 0.18 * shoulders + 0.12 * relief)
    rough = unit(0.07 + 0.52 * resin_shear + 0.40 * clear_pulls
                 + 0.30 * flake_flow + 0.20 * (1.0 - bay) - 0.22 * flake_rims)
    coat = unit(0.12 + 0.70 * bay + 0.54 * shoulders + 0.32 * deep_bays
                + 0.24 * depth_veil - 0.34 * resin_shear
                - 0.28 * clear_pulls - 0.22 * pinstripes)
    spec = pack_physical(
        metal,
        rough,
        coat,
        m_cuts=(0.05, 0.10, 0.18, 0.28, 0.40, 0.53, 0.67, 0.81, 0.93),
        r_cuts=(0.07, 0.14, 0.23, 0.33, 0.44, 0.56, 0.69, 0.82, 0.93),
        c_cuts=(0.055, 0.12, 0.21, 0.32, 0.44, 0.57, 0.70, 0.83, 0.94),
    )
    return finish(
        started,
        FINISH_ID,
        DISPLAY_NAME,
        paint_a,
        paint_b,
        spec,
        "deep violet candy lacquer folded into broad unequal body shoulders that exchange cyan and magenta under opposing light",
        {
            "M": "mica lamellae, pearl strokes, flake rims, pinstripe lips, and fold shoulders expose conductive flake",
            "R": "continuous resin shear, flake flow, clear pulls, and unfilled troughs tune the candy surface",
            "Cc": "broad candy bays, depth veils, and optical shoulders retain deep clear across the whole body",
        },
    )
