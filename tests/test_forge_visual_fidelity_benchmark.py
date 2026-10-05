from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import _forge_visual_fidelity_benchmark as benchmark


def _adapter() -> dict:
    return {
        "surfaces": {
            "left_strip": {"side": "left", "family": "side", "paintable": True, "inverse_ready": True},
            "left_fender": {"side": "left", "family": "front_fender", "paintable": True, "inverse_ready": True},
            "right_strip": {"side": "right", "family": "side", "paintable": True, "inverse_ready": True},
        }
    }


def _profile() -> dict:
    return {
        "source_crop_size": [120, 48],
        "nose_direction": "image-right",
        "wheels": [
            {"role": "rear_wheel", "x": 25.0, "y": 37.0, "radius": 8.0},
            {"role": "front_wheel", "x": 92.0, "y": 37.0, "radius": 8.0},
        ],
        "rocker": {"y_pixels": 44},
        "silhouette": {
            "bbox_pixels": [4, 4, 116, 46],
            "car_space": {"x_min": -0.3, "x_max": 1.35, "y_bottom": -0.03, "y_top": 0.55},
        },
        "window": {"bbox_pixels": [45, 5, 75, 17]},
    }


def test_primary_surface_abstains_from_ambiguous_fender() -> None:
    name, _surface, abstentions = benchmark.primary_surface_for_role(_adapter(), "left_profile")
    assert name == "left_strip"
    assert abstentions == [
        {
            "surface": "left_fender",
            "reason": "missing distinct car_space_extent; whole-profile overlap is ambiguous",
        }
    ]


def test_role_surfaces_accept_explicit_fender_extent() -> None:
    adapter = _adapter()
    adapter["surfaces"]["left_fender"].update(
        {
            "projector": "wheelbase_profile",
            "car_space_extent": {"x_min": 0.7, "x_max": 1.3, "y_bottom": 0.05, "y_top": 0.4},
        }
    )
    surfaces, abstentions = benchmark.surfaces_for_role(adapter, "left_profile")
    assert [name for name, _row in surfaces] == ["left_strip", "left_fender"]
    assert abstentions == []


def test_qualified_role_score_is_weakest_physical_surface() -> None:
    score = benchmark.conservative_surface_score(
        [
            {"surface": "left_strip", "metrics": {"visual_fidelity": 96.0}},
            {"surface": "left_fender", "metrics": {"visual_fidelity": 88.25}},
        ]
    )
    assert score == 88.25


def test_adapter_canvas_accepts_versioned_list_contract() -> None:
    assert benchmark.adapter_canvas_shape({"canvas": [2048, 2048]}) == (2048, 2048, 3)


def test_calibration_overlay_can_reuse_source_adapter_masks() -> None:
    path = benchmark.resolve_surface_mask(
        Path("calibrations/adapter.json"),
        {"mask_root": "source_adapter"},
        {"mask_path": "masks/left.png"},
    )
    assert path == Path("source_adapter/masks/left.png")


def test_primary_surface_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="unsupported benchmark role"):
        benchmark.primary_surface_for_role(_adapter(), "top")


def test_inverse_render_has_expected_shape_and_coverage() -> None:
    composite = np.zeros((64, 128, 3), dtype=np.uint8)
    composite[:, :] = (30, 170, 70)
    surface_mask = np.zeros((64, 128), dtype=np.uint8)
    surface_mask[10:55, 5:120] = 255
    surface = {"bbox": [5, 10, 120, 55], "upright_rotation_deg": 0}
    rendered, alpha = benchmark.render_surface_to_profile(composite, surface_mask, _profile(), surface)
    assert rendered.shape == (48, 120, 3)
    assert alpha.shape == (48, 120)
    assert np.count_nonzero(alpha >= 80) > 2000
    assert rendered[alpha >= 200, 1].mean() > 150


def test_scores_identical_evidence_above_changed_evidence() -> None:
    yy, xx = np.mgrid[:80, :180]
    reference = np.zeros((80, 180, 3), dtype=np.uint8)
    reference[:, :] = (18, 92, 42)
    reference[(xx > 45) & (xx < 120) & (yy > 18) & (yy < 62)] = (238, 238, 232)
    reference[(xx > 76) & (xx < 91)] = (220, 18, 24)
    mask = np.ones((80, 180), dtype=bool)
    same, _ = benchmark.score_view(reference, reference.copy(), mask)
    changed = np.roll(reference, 48, axis=1)
    changed[:, :, 0] = 30
    different, _ = benchmark.score_view(reference, changed, mask)
    assert same["visual_fidelity"] > 99.0
    assert different["visual_fidelity"] < same["visual_fidelity"] - 15.0


def test_border_background_retains_isolated_white_paint() -> None:
    image = np.full((40, 80, 3), 255, dtype=np.uint8)
    image[8:32, 12:68] = (20, 70, 35)
    image[14:26, 28:52] = 250
    background = benchmark.border_background_mask(image)
    assert background[0, 0]
    assert not background[20, 40]


def test_border_background_removes_connected_off_white_studio_field() -> None:
    image = np.full((40, 80, 3), (236, 234, 231), dtype=np.uint8)
    image[8:32, 12:68] = (225, 184, 15)
    image[14:26, 28:52] = 248
    background = benchmark.border_background_mask(image)
    assert background[0, 0]
    assert not background[20, 40]
