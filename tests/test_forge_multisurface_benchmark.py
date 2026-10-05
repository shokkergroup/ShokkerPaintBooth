import pytest

import _forge_multisurface_benchmark as benchmark


def _adapter(left: dict, right: dict) -> dict:
    return {
        "surfaces": {
            "left": {"family": "front_fender", "paintable": True, "inverse_ready": True, "car_space_extent": left},
            "right": {"family": "front_fender", "paintable": True, "inverse_ready": True, "car_space_extent": right},
            "hood": {"family": "top", "paintable": True, "inverse_ready": False},
        }
    }


def test_shared_family_extent_requires_one_cross_side_template_calibration() -> None:
    extent = {"x_min": 0.7, "x_max": 1.3, "y_bottom": 0.05, "y_top": 0.39}
    assert benchmark.shared_family_extent(_adapter(extent, dict(extent)), "front_fender") == extent


def test_shared_family_extent_rejects_per_side_drift() -> None:
    left = {"x_min": 0.7, "x_max": 1.3, "y_bottom": 0.05, "y_top": 0.39}
    right = {**left, "x_max": 1.4}
    with pytest.raises(ValueError, match="do not share"):
        benchmark.shared_family_extent(_adapter(left, right), "front_fender")
