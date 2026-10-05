from __future__ import annotations

import numpy as np
import pytest

import _forge_reference_uv_splatter as splatter


def _profile() -> dict:
    return {
        "source_crop_size": [120, 48],
        "nose_direction": "image-right",
        "wheels": [
            {"role": "rear_wheel", "x": 25.0, "y": 37.0, "radius": 7.0},
            {"role": "front_wheel", "x": 92.0, "y": 37.0, "radius": 7.0},
        ],
        "rocker": {"y_pixels": 45},
        "silhouette": {
            "bbox_pixels": [2, 2, 118, 47],
            "car_space": {"x_min": -0.3, "x_max": 1.35, "y_bottom": -0.03, "y_top": 0.55},
        },
        "window": {"bbox_pixels": [46, 5, 74, 16]},
    }


def test_common_observation_mask_is_strict_intersection() -> None:
    first = np.array([[1, 1], [0, 1]], dtype=bool)
    second = np.array([[1, 0], [1, 1]], dtype=bool)
    assert np.array_equal(splatter.common_observation_mask([first, second]), [[1, 0], [0, 1]])


def test_common_observation_mask_rejects_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="different sizes"):
        splatter.common_observation_mask([np.ones((2, 2), bool), np.ones((3, 2), bool)])


def test_reference_splat_respects_template_mask_and_has_no_reflection_flag() -> None:
    reference = np.full((48, 120, 3), (25, 145, 65), dtype=np.uint8)
    reference[15:28, 45:75] = (230, 30, 25)
    template_mask = np.zeros((64, 128), dtype=np.uint8)
    template_mask[8:58, 5:123] = 255
    surface = {
        "bbox": [5, 8, 123, 58],
        "upright_rotation_deg": 0,
        "car_space_extent": {"x_min": -0.3, "x_max": 1.35, "y_bottom": -0.03, "y_top": 0.55},
    }
    result = splatter.splat_reference_to_surface(reference, _profile(), surface, template_mask, (128, 64))
    assert result["uv_observed_pixels"] > 500
    assert not np.any(result["observed"] & (template_mask == 0))
    assert result["rgb"][result["observed"]].mean() > 20
    assert np.asarray(result["profile_to_uv_homography"]).shape == (3, 3)


def test_reference_valid_mask_excludes_wheels_and_window() -> None:
    reference = np.full((48, 120, 3), (30, 120, 50), dtype=np.uint8)
    mask = splatter.reference_valid_mask(reference, _profile())
    assert not mask[37, 25]
    assert not mask[10, 55]
    assert mask[25, 95]
