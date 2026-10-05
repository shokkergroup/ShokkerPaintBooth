from pathlib import Path

import numpy as np
from PIL import Image

import _forge_positioned_projection as positioned


def _profile(nose_direction: str = "image-left") -> dict:
    return {
        "nose_direction": nose_direction,
        "wheels": [
            {"role": "rear_wheel", "x": 80.0, "y": 70.0},
            {"role": "front_wheel", "x": 20.0 if nose_direction == "image-left" else 140.0, "y": 70.0},
        ],
        "rocker": {"y_pixels": 90.0},
        "silhouette": {"car_space": {"x_min": -0.25, "x_max": 1.25, "y_bottom": -0.1, "y_top": 0.5}},
    }


def test_localization_homography_restores_trim_offsets() -> None:
    localization = {
        "accepted": True,
        "homography": np.eye(3).tolist(),
        "source_trim_box": [10, 20, 50, 60],
        "target_trim_box": [30, 40, 70, 80],
    }
    transform = positioned.localization_homography(localization)
    point = transform @ np.array([10.0, 20.0, 1.0])
    assert np.allclose(point[:2] / point[2], [30.0, 40.0])


def test_left_profile_owner_rotation_is_not_a_reflection() -> None:
    transform = positioned.profile_to_uv_homography(_profile(), [0, 0, 300, 120], 180)
    assert np.linalg.det(transform[:2, :2]) > 0.0
    first = transform @ np.array([20.0, 70.0, 1.0])
    second = transform @ np.array([80.0, 70.0, 1.0])
    assert first[0] > second[0]


def test_warp_clips_mandatory_pixels_and_preserves_no_mirror(tmp_path: Path) -> None:
    source = np.zeros((12, 12, 4), dtype=np.uint8)
    source[2:10, 2:10] = (255, 30, 20, 255)
    path = tmp_path / "source.png"
    Image.fromarray(source, "RGBA").save(path)
    car_surface = np.ones((40, 40), dtype=bool)
    mandatory = np.zeros((40, 40), dtype=bool)
    mandatory[12:18, 12:18] = True
    transform = np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 10.0], [0.0, 0.0, 1.0]])
    record = positioned.warp_positioned_layer(path, transform, [0, 0, 40, 40], car_surface, mandatory, tmp_path / "projected.png")
    assert record["mandatory_clipped_pixels"] > 0
    assert record["mandatory_overlap_after_clip"] == 0
    assert not record["mirror_applied"]


def test_primary_underlay_and_isolated_overlay_routing() -> None:
    rows = [
        {
            "source_component_id": "small",
            "direct_resolution": {"accepted": True, "profile_role": "left_profile"},
            "profile_scores": [{"profile_role": "left_profile", "localization": {"selected_fraction": 0.2}}],
        },
        {
            "source_component_id": "large",
            "direct_resolution": {"accepted": True, "profile_role": "left_profile"},
            "profile_scores": [{"profile_role": "left_profile", "localization": {"selected_fraction": 0.7}}],
        },
    ]
    assert positioned.select_primary_source(rows) == "large"
    remainder = {"kind": "paint_remainder", "semantic": {"role": {"value": None}}}
    decal = {"kind": "isolated_object", "semantic": {"role": {"value": "decal"}}}
    assert not positioned.layer_candidate_route(remainder, "small", "large")["visible"]
    assert positioned.layer_candidate_route(decal, "small", "large") == {
        "visible": True,
        "group": "40 SPONSORS & BRAND MARKS",
        "basis": "verified isolated semantic overlay",
    }


def test_inferred_base_color_uses_dominant_visible_cluster(tmp_path: Path) -> None:
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)
    rgba[:8] = (247, 249, 250, 255)
    rgba[8:] = (10, 80, 20, 255)
    path = tmp_path / "art.png"
    Image.fromarray(rgba, "RGBA").save(path)
    assert positioned.infer_base_color(path) == [247, 249, 250]


def test_alpha_placement_delta_reports_real_translation(tmp_path: Path) -> None:
    old = np.zeros((20, 30, 4), dtype=np.uint8)
    new = np.zeros_like(old)
    old[5:10, 3:8] = (255, 0, 0, 255)
    new[5:10, 13:18] = (255, 0, 0, 255)
    old_path, new_path = tmp_path / "old.png", tmp_path / "new.png"
    Image.fromarray(old, "RGBA").save(old_path)
    Image.fromarray(new, "RGBA").save(new_path)
    result = positioned.alpha_placement_delta([new_path], old_path)
    assert result["centroid_shift_pixels"] == 10.0
    assert result["alpha_iou"] == 0.0
