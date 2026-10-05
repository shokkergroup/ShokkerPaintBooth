from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import _forge_dense_pair_registration as dense


def test_endpoint_signature_distinguishes_nose_and_tail() -> None:
    mask = np.zeros((20, 100), dtype=bool)
    mask[8:12, :10] = True
    mask[2:18, -10:] = True
    assert dense.endpoint_signature(mask) == [0.25, 1.0]
    reflected = np.fliplr(mask)
    assert dense.endpoint_compatibility(mask, reflected)["score"] == 0.25


def test_dense_registration_recovers_non_reflecting_translation(tmp_path: Path) -> None:
    source = np.zeros((32, 120, 4), dtype=np.uint8)
    cv2.rectangle(source, (0, 12), (119, 31), (25, 25, 210, 255), -1)
    cv2.rectangle(source, (0, 5), (119, 11), (40, 165, 205, 255), -1)
    source_path = tmp_path / "source.png"
    Image.fromarray(cv2.cvtColor(source, cv2.COLOR_BGRA2RGBA), "RGBA").save(source_path)
    target = np.full((100, 180, 3), 245, dtype=np.uint8)
    target[58:90, 30:150] = source[:, :, :3]
    target_path = tmp_path / "target.png"
    cv2.imwrite(str(target_path), target)
    profile = {
        "role": "left_profile",
        "source_crop_path": str(target_path),
        "silhouette": {"bbox_pixels": [20, 10, 160, 95]},
        "wheelbase_pixels": 120,
        "rocker": {"y_pixels": 92},
    }
    result = dense.dense_register(source_path, profile)
    assert result["mirror_applied"] is False
    assert result["affine_determinant"] > 0
    assert abs(result["translation"][0] - 30) <= 10
    assert abs(result["translation"][1] - 58) <= 8


def test_dense_registration_learns_blue_green_palette(tmp_path: Path) -> None:
    source = np.zeros((30, 120, 4), dtype=np.uint8)
    cv2.rectangle(source, (0, 12), (119, 29), (210, 55, 20, 255), -1)
    cv2.rectangle(source, (0, 4), (119, 11), (45, 185, 45, 255), -1)
    source_path = tmp_path / "blue_green.png"
    Image.fromarray(cv2.cvtColor(source, cv2.COLOR_BGRA2RGBA), "RGBA").save(source_path)
    target = np.full((100, 180, 3), 245, dtype=np.uint8)
    target[60:90, 30:150] = source[:, :, :3]
    target_path = tmp_path / "target.png"
    cv2.imwrite(str(target_path), target)
    profile = {
        "role": "right_profile",
        "source_crop_path": str(target_path),
        "silhouette": {"bbox_pixels": [20, 10, 160, 95]},
        "wheelbase_pixels": 120,
        "rocker": {"y_pixels": 92},
    }
    result = dense.dense_register(source_path, profile)
    assert result["method"] == "masked-multiscale-adaptive-palette-chroma-edge"
    assert len(result["palette"]["centers"]) >= 2
    assert abs(result["translation"][0] - 30) <= 10


def _row(source: str, profile: str, score: float, endpoint: float, coverage: float = 0.9) -> dict:
    return {
        "source_id": source,
        "profile_role": profile,
        "dense_score": score,
        "endpoint_score": endpoint,
        "longitudinal_coverage": coverage,
        "affine_determinant": 1.0,
        "mirror_applied": False,
    }


def test_joint_assignment_accepts_distinct_supported_sides() -> None:
    rows = [_row("a", "left", 0.8, 0.9), _row("a", "right", 0.3, 0.3), _row("b", "left", 0.25, 0.3), _row("b", "right", 0.78, 0.92)]
    result = dense.select_joint_assignment(rows)
    assert result["accepted"]
    assert result["mapping"] == {"a": "left", "b": "right"}


def test_joint_assignment_abstains_when_both_sources_prefer_one_side() -> None:
    rows = [_row("a", "left", 0.75, 0.91), _row("a", "right", 0.28, 0.3), _row("b", "left", 0.72, 0.9), _row("b", "right", 0.3, 0.31)]
    result = dense.select_joint_assignment(rows)
    assert not result["accepted"]
    assert "distinct_independent_winners" in result["abstention"]
    assert "endpoint_orientation" in result["abstention"]


def test_joint_assignment_rejects_reflecting_transform() -> None:
    rows = [_row("a", "left", 0.8, 0.9), _row("a", "right", 0.2, 0.2), _row("b", "left", 0.2, 0.2), _row("b", "right", 0.8, 0.9)]
    rows[-1]["affine_determinant"] = -1.0
    rows[-1]["mirror_applied"] = True
    result = dense.select_joint_assignment(rows)
    assert not result["accepted"]
    assert "non_reflecting" in result["abstention"]
