from scripts.smart_tga_reviewed_candidate_bank import build_bank


def test_reviewed_candidate_bank_is_deduplicated_and_non_authoritative():
    record = {
        "paint_label": "dirtlatemodel 358/car_num_x.tga", "family_id": "number:47",
        "copy": "upper", "status": "candidate_present", "best_instance_id": "di:x",
        "best_review_coverage": 0.9, "best_candidate_coverage": 0.7, "best_iou": 0.65,
        "best_proposed_owners": ["brand_graphics", "unassigned"],
        "best_source_stages": ["appearance_quantized_raw"],
        "best_sources": ["source_rgb_lab_quantized"], "best_merge_reasons": [],
        "best_instance_features": {"edge_density": 0.2, "shape_occupancy": [0.5] * 16},
    }
    probe = {"reviewed_instance_count": 1, "records": [record], "casts_votes": False,
             "ownership_authority": False, "adds_pixels": False}
    bank = build_bank([probe, probe])
    assert bank["probe_count"] == 2
    assert bank["reviewed_region_count"] == 2
    assert bank["reviewed_candidate_count"] == 1
    assert bank["class_counts"] == {"numbers": 1}
    assert bank["owner_path_counts"] == {"brand_graphics+unassigned": 1}
    assert bank["source_stage_counts"] == {"appearance_quantized_raw": 1}
    assert bank["reviewed_candidates"][0]["features"]["edge_density"] == 0.2
    assert bank["casts_votes"] is False
    assert bank["ownership_authority"] is False
    assert bank["adds_pixels"] is False


def test_reviewed_candidate_bank_rejects_authoritative_probe():
    try:
        build_bank([{"records": [], "casts_votes": True}])
    except ValueError as exc:
        assert "claimed runtime authority" in str(exc)
    else:
        raise AssertionError("authoritative probe must fail closed")
