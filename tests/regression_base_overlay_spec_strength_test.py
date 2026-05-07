from __future__ import annotations

import numpy as np

from engine.overlay import blend_dual_base_spec, get_base_overlay_alpha


def _solid_spec(metallic: int, roughness: int, clearcoat: int, shape=(8, 8)) -> np.ndarray:
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:, :, 0] = metallic
    spec[:, :, 1] = roughness
    spec[:, :, 2] = clearcoat
    spec[:, :, 3] = 255
    return spec


def test_base_overlay_spec_strength_is_linear_for_full_pattern_mask():
    primary = _solid_spec(40, 80, 32)
    secondary = _solid_spec(200, 140, 192)
    pattern = np.ones(primary.shape[:2], dtype=np.float32)

    for strength in (0.0, 0.10, 0.50, 1.0):
        blended, alpha = blend_dual_base_spec(
            primary,
            secondary,
            strength=strength,
            blend_mode="pattern",
            pattern_mask=pattern,
        )

        assert np.allclose(alpha, strength)
        expected_metallic = int(40 * (1.0 - strength) + 200 * strength)
        expected_roughness = int(80 * (1.0 - strength) + 140 * strength)
        expected_clearcoat = int(32 * (1.0 - strength) + 192 * strength)
        assert np.all(blended[:, :, 0] == expected_metallic)
        assert np.all(blended[:, :, 1] == expected_roughness)
        assert np.all(blended[:, :, 2] == expected_clearcoat)


def test_base_overlay_tint_can_fully_replace_spec_at_100_percent():
    primary = _solid_spec(40, 80, 32)
    secondary = _solid_spec(200, 140, 192)

    blended, alpha = blend_dual_base_spec(
        primary,
        secondary,
        strength=1.0,
        blend_mode="tint",
    )

    assert np.allclose(alpha, 1.0)
    assert np.all(blended[:, :, :3] == secondary[:, :, :3])


def test_base_overlay_noise_spec_has_no_low_strength_leakage():
    def flat_noise(shape, scales, weights, seed):
        return np.ones(shape, dtype=np.float32)

    alpha = get_base_overlay_alpha(
        (64, 64),
        strength=0.0,
        blend_mode="noise",
        noise_fn=flat_noise,
    )

    assert np.max(alpha) == 0.0
