import pytest

from scripts.smart_tga_group_canary_probe import CLASSES, evaluate_canary


def _row(paint, group_id, owner, value):
    return {
        "paint_label": paint, "group_id": group_id, "reviewed": True,
        "review_target_layer": owner, "fill_ratio": value,
        "area_fraction": value / 10, "bbox_fraction": value / 8,
        "largest_member_fraction": value, "smallest_member_fraction": value / 2,
        "mean_edge_density": value / 3, "max_edge_density": value / 2,
        "mean_texture_entropy": value / 4, "max_texture_entropy": value / 3,
        "max_ocr_coverage": value if owner == "sponsors" else 0,
        "max_digit_coverage": value if owner == "numbers" else 0,
        "palette_role_count": int(value * 10), "palette_role_entropy": value / 5,
        "lightness_span": value / 6, "chroma_span": value / 7,
        "proposal_conflict_fraction": 0,
        "shape_occupancy_mean": value,
        "shape_occupancy_std": value / 2,
        "shape_horizontal_symmetry": value,
        "shape_vertical_symmetry": value,
        "shape_center_edge_delta": value / 3,
        "shape_adjacent_transition": value / 4,
    }


def _bank(prefix, paint_count):
    rows = []
    centers = {"numbers": 0.9, "sponsors": 0.65, "template": 0.35, "paint": 0.1}
    for paint_index in range(paint_count):
        for owner in CLASSES:
            for repeat in range(3):
                value = centers[owner] + (paint_index % 3 - 1) * 0.005 + repeat * 0.002
                rows.append(_row(f"{prefix}_{paint_index}", f"{owner}_{repeat}", owner, value))
    return {"records": rows, "summary": {"casts_votes": False, "ownership_authority": False}}


def test_group_canary_is_paint_disjoint_calibrated_and_non_authoritative():
    report = evaluate_canary(_bank("train", 12), _bank("canary", 4), min_score=0.55, min_margin=0.10)
    assert report["train_paint_count"] == 12
    assert report["canary_paint_count"] == 4
    assert report["calibration"]["method"] == "sigmoid"
    assert report["number_false_positive_count"] == 0
    assert report["casts_votes"] is False
    assert report["ownership_authority"] is False
    assert report["adds_pixels"] is False


def test_group_canary_rejects_paint_overlap():
    bank = _bank("same", 12)
    with pytest.raises(ValueError, match="paint overlap"):
        evaluate_canary(bank, bank)


def test_group_canary_reports_shape_topology_features():
    report = evaluate_canary(
        _bank("train_shape", 12), _bank("canary_shape", 4),
        min_score=0.55, min_margin=0.10, feature_set="shape",
    )
    assert "shape_occupancy_mean" in report["feature_names"]
    assert "shape_adjacent_transition" in report["feature_names"]

    baseline = evaluate_canary(
        _bank("train_baseline", 12), _bank("canary_baseline", 4),
        min_score=0.55, min_margin=0.10, feature_set="baseline",
    )
    assert baseline["feature_set"] == "baseline"
    assert "shape_occupancy_mean" not in baseline["feature_names"]
