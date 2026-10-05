import numpy as np
import pytest

import _forge_template_adapter as template_adapter


def _adapter() -> dict:
    surfaces = {
        "left": {
            "bbox": [0, 0, 50, 30],
            "upright_rotation_deg": 180,
            "paintable": True,
            "mask_pixels": 100,
            "inverse_ready": True,
            "projector": "wheelbase_profile",
            "car_space_extent": {"x_min": -0.5, "x_max": 1.1, "y_bottom": 0.0, "y_top": 0.3},
        },
        "roof": {
            "bbox": [50, 0, 100, 50],
            "upright_rotation_deg": 0,
            "paintable": True,
            "mask_pixels": 100,
            "inverse_ready": False,
            "projector": "top_car_space",
        },
    }
    return {
        "canvas": [100, 100],
        "surfaces": surfaces,
        "adjacency": [{"a": "left", "b": "roof"}],
        "guides": {role: {} for role in ("mandatory", "number_blocks", "sponsor_blocks", "car_mask", "wire")},
        "base_fill": {"mode": "full_canvas"},
        "placement_anchors": {},
        "policy": {"readable_art_reflection_allowed": False},
    }


def test_adapter_validation_reports_inverse_readiness() -> None:
    result = template_adapter.validate_adapter(_adapter())
    assert result["valid"]
    assert result["surface_count"] == 2
    assert result["paintable_surface_count"] == 2
    assert result["inverse_ready_surface_count"] == 1
    assert result["inverse_ready_fraction"] == 0.5
    assert result["warnings"] == ["roof: inverse projector calibration unresolved"]


def test_adapter_validation_rejects_missing_adjacency_and_reflection() -> None:
    adapter = _adapter()
    adapter["adjacency"] = [{"a": "left", "b": "missing"}]
    adapter["policy"]["readable_art_reflection_allowed"] = True
    result = template_adapter.validate_adapter(adapter)
    assert not result["valid"]
    assert any("missing surface" in error for error in result["errors"])
    assert any("reflection" in error for error in result["errors"])


def test_adapter_validation_requires_honest_seam_audit_contract() -> None:
    adapter = _adapter()
    adapter["adjacency"] = [{
        "a": "left",
        "b": "roof",
        "seam": "invalid_overlap",
        "continuity_audit": {"mode": "overlapping_car_space", "minimum_overlap_pixels": 10},
    }]
    result = template_adapter.validate_adapter(adapter)
    assert not result["valid"]
    assert any("inverse-ready surfaces" in error for error in result["errors"])
    assert any("shared projector" in error for error in result["errors"])

    adapter["adjacency"][0]["continuity_audit"] = {"mode": "abstain", "reason": "not calibrated"}
    assert template_adapter.validate_adapter(adapter)["valid"]


def test_adapter_validation_accepts_normalized_uv_edge_contract() -> None:
    adapter = _adapter()
    adapter["adjacency"] = [{
        "a": "left",
        "b": "roof",
        "seam": "stored_uv_edge_pair",
        "continuity_audit": {
            "mode": "normalized_uv_edge_profile",
            "a_edge": "right",
            "b_edge": "left",
            "reverse_a": False,
            "reverse_b": True,
            "band_pixels": 2,
            "samples": 64,
            "length_range": [0.05, 0.95],
            "minimum_valid_samples": 32,
            "pass_score": 85.0,
        },
    }]
    assert template_adapter.validate_adapter(adapter)["valid"]


def test_adapter_validation_rejects_malformed_normalized_uv_edge_contract() -> None:
    adapter = _adapter()
    adapter["adjacency"] = [{
        "a": "left",
        "b": "roof",
        "seam": "bad_stored_uv_edge_pair",
        "continuity_audit": {
            "mode": "normalized_uv_edge_profile",
            "a_edge": "diagonal",
            "b_edge": "left",
            "band_pixels": 0,
            "samples": 4,
            "length_range": [0.9, 0.1],
            "minimum_valid_samples": 0,
            "pass_score": 101.0,
        },
    }]
    result = template_adapter.validate_adapter(adapter)
    assert not result["valid"]
    assert any("valid a_edge" in error for error in result["errors"])
    assert any("samples>=8" in error for error in result["errors"])
    assert any("invalid length_range" in error for error in result["errors"])
    assert any("minimum_valid_samples" in error for error in result["errors"])
    assert any("pass_score" in error for error in result["errors"])


def test_adapter_validation_requires_complete_dense_multiview_contract() -> None:
    adapter = _adapter()
    adapter["adjacency"] = [{
        "a": "left",
        "b": "roof",
        "seam": "shared_views",
        "continuity_audit": {
            "mode": "dense_multiview_correspondence",
            "correspondence_key": "left_roof_shared_views",
            "required_physical_surfaces": ["left", "roof"],
            "minimum_views": 2,
            "pass_score": 85.0,
        },
    }]
    assert template_adapter.validate_adapter(adapter)["valid"]
    adapter["adjacency"][0]["continuity_audit"]["required_physical_surfaces"] = ["left"]
    result = template_adapter.validate_adapter(adapter)
    assert not result["valid"]
    assert any("both adjacent physical surfaces" in error for error in result["errors"])


def test_adapter_validation_requires_complete_candidate_roundtrip_contract() -> None:
    adapter = _adapter()
    adapter["adjacency"] = [{
        "a": "left",
        "b": "roof",
        "seam": "compiled_candidate_pair",
        "continuity_audit": {
            "mode": "candidate_surface_roundtrip",
            "correspondence_key": "left_roof_candidate_pixels",
            "required_physical_surfaces": ["left", "roof"],
            "minimum_views": 1,
            "pass_score": 85.0,
        },
    }]
    assert template_adapter.validate_adapter(adapter)["valid"]
    contract = adapter["adjacency"][0]["continuity_audit"]
    contract["correspondence_key"] = ""
    contract["required_physical_surfaces"] = ["left"]
    contract["minimum_views"] = 0
    contract["pass_score"] = 101.0
    result = template_adapter.validate_adapter(adapter)
    assert not result["valid"]
    assert any("requires correspondence_key" in error for error in result["errors"])
    assert any("positive minimum_views" in error for error in result["errors"])
    assert any("both adjacent physical surfaces" in error for error in result["errors"])
    assert any("pass_score" in error for error in result["errors"])


def test_surface_overlap_ownership_makes_paintable_masks_exclusive() -> None:
    masks = {
        "strip": np.array([[1, 1, 0], [1, 1, 0]], dtype=bool),
        "fender": np.array([[0, 1, 1], [0, 1, 1]], dtype=bool),
    }
    resolved, records = template_adapter.resolve_surface_overlap_ownership(
        masks,
        {"strip", "fender"},
        [{"winner": "fender", "loser": "strip", "basis": "synthetic"}],
    )
    assert int(np.count_nonzero(resolved["strip"] & resolved["fender"])) == 0
    assert records[0]["overlap_pixels_before"] == 2
    assert records[0]["overlap_pixels_after"] == 0


def test_surface_overlap_ownership_rejects_undeclared_collision() -> None:
    masks = {"a": np.ones((2, 2), dtype=bool), "b": np.ones((2, 2), dtype=bool)}
    with pytest.raises(ValueError, match="undeclared paintable surface-mask overlaps"):
        template_adapter.resolve_surface_overlap_ownership(masks, {"a", "b"}, [])


def test_adapter_validation_rejects_bad_rotation_and_empty_mask() -> None:
    adapter = _adapter()
    adapter["surfaces"]["left"]["upright_rotation_deg"] = 45
    adapter["surfaces"]["left"]["mask_pixels"] = 0
    result = template_adapter.validate_adapter(adapter)
    assert not result["valid"]
    assert any("rotation" in error for error in result["errors"])
    assert any("empty paintable mask" in error for error in result["errors"])


def test_adapter_validation_checks_inverse_car_space_extent_contract() -> None:
    adapter = _adapter()
    adapter["surfaces"]["left"]["car_space_extent"] = {
        "x_min": -0.5,
        "x_max": 1.1,
        "y_bottom": 0.0,
        "y_top": 0.3,
    }
    result = template_adapter.validate_adapter(adapter)
    assert result["valid"]
    assert not any("left: inverse-ready wheelbase surface lacks" in warning for warning in result["warnings"])

    adapter["surfaces"]["left"]["car_space_extent"]["x_max"] = -0.6
    result = template_adapter.validate_adapter(adapter)
    assert not result["valid"]
    assert any("invalid car-space extent" in error for error in result["errors"])


def test_guide_polarity_makes_official_mask_nonpaintable() -> None:
    alpha = np.array([[False, True], [True, False]])
    assert template_adapter.apply_guide_polarity(alpha, "alpha_is_nonpaintable").tolist() == [[True, False], [False, True]]
    assert template_adapter.apply_guide_polarity(alpha, "alpha_is_forbidden").tolist() == alpha.tolist()
    with pytest.raises(ValueError):
        template_adapter.apply_guide_polarity(alpha, "guess_from_filename")


def test_panel_map_anchors_scale_xywh_to_adapter_bbox() -> None:
    panel_map = {
        "space": "1024x1024",
        "number_blocks": [{"name": "door", "bbox": [10, 20, 30, 40]}],
        "sponsor_blocks": [{"name": "spoiler", "bbox": [100, 200, 50, 25]}],
        "orientation_deg": {"door": 180},
    }
    anchors = template_adapter.compile_placement_anchors(panel_map, (2048, 2048))
    assert anchors["door"]["bbox"] == [20, 40, 80, 120]
    assert anchors["door"]["orientation_deg"] == 180
    assert anchors["spoiler"]["bbox"] == [200, 400, 300, 450]


def test_placement_anchor_overrides_are_calibration_data_not_mutations() -> None:
    anchors = {
        "driver_number": {"bbox": [10, 20, 40, 80], "orientation_deg": 180},
        "outside_spoiler": {"bbox": [100, 200, 300, 240], "orientation_deg": 0},
    }
    calibrated = template_adapter.apply_placement_anchor_overrides(
        anchors,
        {
            "driver_number": {"visual_rotation_adjust_deg": 2.0},
            "outside_spoiler": {"bbox": [120, 200, 320, 240]},
        },
    )
    assert calibrated["driver_number"]["visual_rotation_adjust_deg"] == 2.0
    assert calibrated["outside_spoiler"]["bbox"] == [120, 200, 320, 240]
    assert anchors["outside_spoiler"]["bbox"] == [100, 200, 300, 240]


def test_placement_anchor_override_rejects_unknown_surface_role() -> None:
    with pytest.raises(ValueError, match="unknown anchor"):
        template_adapter.apply_placement_anchor_overrides(
            {"known": {"bbox": [0, 0, 10, 10]}}, {"typo": {"bbox": [1, 1, 9, 9]}}
        )
