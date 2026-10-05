from __future__ import annotations

import numpy as np

import _forge_surface_extent_calibrator as calibrator
from _forge_positioned_projection import profile_to_uv_homography


def _profile() -> dict:
    return {
        "nose_direction": "image-right",
        "wheels": [
            {"role": "rear_wheel", "x": 20.0, "y": 70.0},
            {"role": "front_wheel", "x": 80.0, "y": 70.0},
        ],
        "rocker": {"y_pixels": 90.0},
        "silhouette": {"car_space": {"x_min": -0.3, "x_max": 1.4, "y_bottom": -0.05, "y_top": 0.55}},
    }


def test_extent_vector_round_trip() -> None:
    extent = {"x_min": -0.45, "x_max": 1.25, "y_bottom": -0.04, "y_top": 0.46}
    assert calibrator.vector_to_extent(calibrator.extent_to_vector(extent)) == extent


def test_coordinate_descent_improves_shared_objective() -> None:
    target = np.array([0.34, 1.72, 0.20, 0.48])

    def objective(vector: np.ndarray) -> float:
        return -float(np.sum((vector - target) ** 2))

    initial = np.array([0.52, 1.90, 0.26, 0.60])
    fitted, score, trace = calibrator.coordinate_descent(
        objective, initial, np.array([0.12, 0.14, 0.04, 0.05]), rounds=5
    )
    assert score > objective(initial)
    assert np.linalg.norm(fitted - target) < np.linalg.norm(initial - target)
    assert any(item["accepted"] for item in trace[1:])


def test_optional_surface_extent_changes_profile_mapping_without_reflection() -> None:
    bbox = [0, 0, 200, 80]
    historical = profile_to_uv_homography(_profile(), bbox, 0)
    calibrated = profile_to_uv_homography(
        _profile(),
        bbox,
        0,
        {"x_min": -0.5, "x_max": 1.2, "y_bottom": -0.05, "y_top": 0.55},
    )
    point = np.array([50.0, 40.0, 1.0])
    old_xy = historical @ point
    new_xy = calibrated @ point
    old_xy /= old_xy[2]
    new_xy /= new_xy[2]
    assert not np.allclose(old_xy, new_xy)
    assert np.linalg.det(historical[:2, :2]) * np.linalg.det(calibrated[:2, :2]) > 0


def test_vector_bounds_reject_degenerate_extent() -> None:
    assert calibrator.valid_vector(np.array([0.4, 1.7, 0.2, 0.5]))
    assert not calibrator.valid_vector(np.array([0.4, 0.1, 0.2, 0.5]))
