from __future__ import annotations

import itertools

import numpy as np

from engine.expansions import owner_review_signal


SIGNAL_IDS = [
    "aurora_glow",
    "bioluminescent_wave",
    "blacklight_paint",
    "cyber_punk",
    "electric_arc",
    "firefly",
    "fluorescent",
    "glow_stick",
    "laser_grid",
    "laser_show",
    "led_matrix",
    "magnesium_burn",
    "neon_glow",
    "neon_sign",
    "neon_vegas",
    "phosphorescent",
    "plasma_globe",
    "radioactive",
    "rave",
    "scorched",
    "sodium_lamp",
    "static",
    "tesla_coil",
    "tracer_round",
    "welding_arc",
]


def test_owner_review_signal_renderers_are_active_and_distinct():
    shape = (96, 96)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    paint[:, :, 0] = 0.05
    paint[:, :, 1] = 0.07
    paint[:, :, 2] = 0.11

    assert set(SIGNAL_IDS) <= set(owner_review_signal.OWNER_REVIEW_SIGNAL_MONOLITHICS)

    vectors = {}
    for signal_id in SIGNAL_IDS:
        spec_fn, paint_fn = owner_review_signal.OWNER_REVIEW_SIGNAL_MONOLITHICS[signal_id]
        spec = spec_fn(shape, mask, seed=901, sm=1.0)
        rendered = paint_fn(paint.copy(), shape, mask, seed=901, pm=1.0, bb=0.0)

        assert spec.shape == (shape[0], shape[1], 4), signal_id
        assert rendered.shape == paint.shape, signal_id
        assert spec[:, :, 3].min() == 255, signal_id
        assert float(rendered.std()) > 0.018, signal_id
        assert float(spec[:, :, 0].max() - spec[:, :, 0].min()) > 30.0, signal_id

        vec = rendered.reshape(-1)
        vectors[signal_id] = (vec - float(vec.mean())) / (float(vec.std()) + 1e-6)

    max_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(SIGNAL_IDS, 2)
    )
    assert max_corr < 0.975


def test_owner_review_signal_respects_zone_mask():
    shape = (64, 64)
    paint = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    paint[:, :, 0] = 0.22
    paint[:, :, 1] = 0.31
    paint[:, :, 2] = 0.44
    mask = np.zeros(shape, dtype=np.float32)
    mask[10:54, 14:50] = 1.0
    outside = mask < 0.5

    for signal_id, (_, paint_fn) in owner_review_signal.OWNER_REVIEW_SIGNAL_MONOLITHICS.items():
        rendered = paint_fn(paint.copy(), shape, mask, seed=503, pm=1.0, bb=0.0)
        np.testing.assert_allclose(
            rendered[outside],
            paint[outside],
            atol=1e-6,
            err_msg=f"{signal_id} changed paint outside the zone mask",
        )
