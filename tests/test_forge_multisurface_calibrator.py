from __future__ import annotations

import numpy as np
import pytest

import _forge_multisurface_calibrator as multisurface


def _profile() -> dict:
    return {
        "source_crop_size": [40, 20],
        "wheels": [
            {"role": "rear_wheel", "x": 8.0, "y": 15.0},
            {"role": "front_wheel", "x": 32.0, "y": 15.0},
        ],
        "rocker": {"y_pixels": 19.0},
    }


def test_fender_bounds_accept_physical_extent_and_reject_whole_car() -> None:
    assert multisurface.fender_vector_valid(np.array([1.1, 0.65, 0.2, 0.4]))
    assert not multisurface.fender_vector_valid(np.array([0.5, 1.8, 0.2, 0.4]))


def test_surface_family_selection_is_adapter_driven() -> None:
    adapter = {
        "surfaces": {
            "a": {"side": "left", "family": "side", "paintable": True, "inverse_ready": True},
            "b": {"side": "left", "family": "front_fender", "paintable": True, "inverse_ready": True},
        }
    }
    name, _surface = multisurface.surface_for_role(adapter, "left_profile", "front_fender")
    assert name == "b"
    with pytest.raises(ValueError, match="exactly one"):
        multisurface.surface_for_role(adapter, "right_profile", "front_fender")


def test_confidence_composition_never_blends_overlap() -> None:
    height, width = 20, 40
    blue = np.zeros((height, width, 3), dtype=np.uint8)
    blue[:] = (10, 30, 220)
    orange = np.zeros((height, width, 3), dtype=np.uint8)
    orange[:] = (240, 120, 20)
    alpha = np.full((height, width), 255, dtype=np.uint8)
    candidates = [
        {
            "family": "side",
            "rgb": blue,
            "alpha": alpha,
            "extent": {"x_min": -0.4, "x_max": 1.0, "y_bottom": -0.1, "y_top": 0.6},
        },
        {
            "family": "front_fender",
            "rgb": orange,
            "alpha": alpha,
            "extent": {"x_min": 0.75, "x_max": 1.45, "y_bottom": -0.05, "y_top": 0.5},
        },
    ]
    rgb, out_alpha, ownership, counts = multisurface.compose_by_confidence(candidates, _profile())
    assert counts["overlap_arbitrated"] > 0
    assert np.all(out_alpha == 255)
    assert set(np.unique(ownership)).issubset({1, 2})
    colors = np.unique(rgb.reshape(-1, 3), axis=0)
    assert all(tuple(color) in {(10, 30, 220), (240, 120, 20)} for color in colors)


def test_surface_confidence_is_zero_outside_alpha() -> None:
    alpha = np.zeros((5, 6), dtype=np.uint8)
    alpha[2, 3] = 255
    x = np.tile(np.linspace(0.8, 1.3, 6), (5, 1))
    y = np.tile(np.linspace(0.0, 0.4, 5)[:, None], (1, 6))
    confidence = multisurface.surface_confidence(
        alpha,
        {"x_min": 0.75, "x_max": 1.45, "y_bottom": -0.05, "y_top": 0.5},
        x,
        y,
    )
    assert np.count_nonzero(confidence) == 1


def test_profile_grid_respects_nose_direction_from_wheel_order() -> None:
    x, y = multisurface.profile_car_grid(_profile())
    assert x[10, 8] == pytest.approx(0.0)
    assert x[10, 32] == pytest.approx(1.0)
    assert y[19, 10] == pytest.approx(0.0)
