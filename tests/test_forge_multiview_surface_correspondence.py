from pathlib import Path

import cv2
import numpy as np

import _forge_multiview_surface_correspondence as correspondence


def _texture(seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = rng.integers(20, 235, size=(110, 150, 3), dtype=np.uint8)
    cv2.circle(image, (35, 30), 18, (250, 220, 20), 4)
    cv2.putText(image, "77", (65, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (10, 10, 10), 4)
    return image


def test_feature_homography_recovers_non_reflecting_shared_view() -> None:
    source = _texture()
    homography = np.array([[0.92, 0.08, 28.0], [0.03, 0.88, 19.0], [0.0002, 0.0003, 1.0]], dtype=np.float64)
    target = cv2.warpPerspective(source, homography, (220, 170), borderValue=(245, 245, 245))
    config = {
        "minimum_good_matches": 6,
        "minimum_inliers": 6,
        "minimum_inlier_ratio": 0.25,
        "maximum_median_error": 4.0,
        "require_non_reflecting": True,
    }
    result = correspondence.feature_homography(source, np.full(source.shape[:2], 255, np.uint8), target, config)
    assert result["accepted"]
    assert result["non_reflecting"]
    assert result["quality"] >= 85.0
    assert result["median_reprojection_error"] < 1.0


def test_reflecting_homography_is_detected() -> None:
    reflecting = np.array([[-1.0, 0.0, 149.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    assert not correspondence.polygon_is_non_reflecting(reflecting, 150, 110)


def test_dense_inverse_map_recovers_source_coordinates() -> None:
    source_mask = np.full((20, 30), 255, np.uint8)
    homography = np.array([[1.0, 0.0, 8.0], [0.0, 1.0, 5.0], [0.0, 0.0, 1.0]])
    source_x, source_y, valid = correspondence.dense_inverse_map(homography, source_mask, (40, 50))
    assert valid[5, 8]
    assert abs(float(source_x[5, 8])) < 0.01
    assert abs(float(source_y[5, 8])) < 0.01
    assert not valid[0, 0]


def test_homography_quality_abstains_below_support() -> None:
    config = {"minimum_inliers": 8, "minimum_inlier_ratio": 0.4, "maximum_median_error": 3.0}
    assert correspondence.homography_quality(2, 0.1, 2.9, config) < 50.0
