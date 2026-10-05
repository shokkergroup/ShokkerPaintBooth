from scripts.smart_tga_semantic_holdout_probe import (
    FEATURE_SETS,
    evaluate_paint_holdout,
    number_corroboration_abstention_reason,
    summarize_number_corroboration_abstentions,
)


def test_holdout_probe_is_paint_stratified_and_non_authoritative():
    rows = []
    for paint_index in range(5):
        for class_index, owner in enumerate(("numbers", "sponsors", "template", "paint")):
            for sample in range(3):
                rows.append({
                    "paint_label": f"paint-{paint_index}", "object_id": f"{paint_index}-{owner}-{sample}",
                    "source_content_id": "src:duplicate" if paint_index in {0, 1} else f"src:{paint_index}",
                    "review_target_layer": owner, "object_kind": "singleton",
                    "member_count": 1, "area_fraction": 0.001 + class_index * 0.01,
                    "bbox_fraction": 0.002 + class_index * 0.01, "fill_ratio": 0.2 + class_index * 0.2,
                    "aspect_ratio": 0.5 + class_index, "mean_edge_density": class_index * 0.2,
                    "shape_occupancy": [class_index / 3.0] * 16,
                    "review_target_proposal_support_state": (
                        "missing" if owner == "numbers" and sample == 0 else "supported"
                    ),
                })
    report = evaluate_paint_holdout({"reviewed_objects": rows}, min_score=0.0, min_margin=0.0)
    assert report["paint_count"] == 5
    assert report["source_content_count"] == 4
    assert report["evaluated_object_count"] == 60
    assert report["skipped_folds"] == []
    assert report["casts_votes"] is False
    assert report["ownership_authority"] is False
    assert report["calibration_ready"] is False
    assert report["feature_set"] == "legacy"
    assert report["feature_names"] == list(FEATURE_SETS["legacy"])
    assert report["number_truth_proposal_support_counts"] == {
        "missing": 5, "supported": 10,
    }


def test_probe_feature_families_are_explicit_ablation_gates():
    assert set(FEATURE_SETS) == {
        "legacy", "position", "provenance", "provenance_position",
        "intrinsic", "topology", "geometry", "geometry_position",
        "geometry_provenance_position", "topology_provenance_position",
        "intrinsic_provenance_position", "intrinsic_topology_provenance_position",
        "intrinsic_topology_assembly_provenance_position",
        "intrinsic_topology_instance_origin_provenance_position",
        "intrinsic_topology_cross_copy_provenance_position",
        "intrinsic_topology_cross_copy_anchor_provenance_position",
        "intrinsic_topology_instance_origin_cross_copy_anchor_provenance_position",
        "intrinsic_topology_completion_provenance_position",
        "intrinsic_topology_dominant_member_provenance_position",
        "intrinsic_topology_group_completion_provenance_position",
        "intrinsic_topology_group_dominant_member_provenance_position",
    }
    assert "bbox_x_fraction" not in FEATURE_SETS["legacy"]
    assert "bbox_x_fraction" in FEATURE_SETS["position"]
    assert "gpu_model_member_fraction" in FEATURE_SETS["provenance"]
    assert "physical_group_indicator" not in FEATURE_SETS["provenance"]
    assert "physical_group_indicator" in FEATURE_SETS["intrinsic_topology_assembly_provenance_position"]
    assert "candidate_member_ratio" in FEATURE_SETS["intrinsic_topology_assembly_provenance_position"]
    assert "appearance_quantized_instance_fraction" not in FEATURE_SETS["intrinsic_topology_provenance_position"]
    assert "appearance_quantized_instance_fraction" in FEATURE_SETS["intrinsic_topology_instance_origin_provenance_position"]
    assert "appearance_unassigned_instance_fraction" in FEATURE_SETS["intrinsic_topology_instance_origin_provenance_position"]
    assert "cross_copy_max_similarity" not in FEATURE_SETS["intrinsic_topology_provenance_position"]
    assert "cross_copy_max_similarity" in FEATURE_SETS["intrinsic_topology_cross_copy_provenance_position"]
    assert "cross_copy_peer_count_070" in FEATURE_SETS["intrinsic_topology_cross_copy_provenance_position"]
    assert "cross_copy_number_anchor_max_similarity" not in FEATURE_SETS["intrinsic_topology_cross_copy_provenance_position"]
    assert "cross_copy_number_anchor_max_similarity" in FEATURE_SETS["intrinsic_topology_cross_copy_anchor_provenance_position"]
    combined = FEATURE_SETS["intrinsic_topology_instance_origin_cross_copy_anchor_provenance_position"]
    assert "appearance_quantized_instance_fraction" in combined
    assert "appearance_unassigned_instance_fraction" in combined
    assert "cross_copy_max_similarity" in combined
    assert "cross_copy_number_anchor_max_similarity" in combined
    assert "largest_member_fraction" not in FEATURE_SETS["intrinsic_topology_provenance_position"]
    assert "largest_member_fraction" in FEATURE_SETS["intrinsic_topology_completion_provenance_position"]
    assert "largest_member_fraction" in FEATURE_SETS["intrinsic_topology_dominant_member_provenance_position"]
    assert "member_area_balance" not in FEATURE_SETS["intrinsic_topology_dominant_member_provenance_position"]
    assert "group_largest_member_fraction" not in FEATURE_SETS["intrinsic_topology_provenance_position"]
    assert "physical_group_indicator" in FEATURE_SETS["intrinsic_topology_group_completion_provenance_position"]
    assert "group_largest_member_fraction" in FEATURE_SETS["intrinsic_topology_group_completion_provenance_position"]
    assert "largest_member_fraction" not in FEATURE_SETS["intrinsic_topology_group_completion_provenance_position"]
    assert FEATURE_SETS["intrinsic_topology_group_dominant_member_provenance_position"].count("physical_group_indicator") == 1
    assert "group_largest_member_fraction" in FEATURE_SETS["intrinsic_topology_group_dominant_member_provenance_position"]
    assert "group_member_area_balance" not in FEATURE_SETS["intrinsic_topology_group_dominant_member_provenance_position"]
    assert "mean_perceptual_chroma" in FEATURE_SETS["intrinsic"]
    assert "topology_hole_count" in FEATURE_SETS["topology"]
    assert "geometry_hu_log_1" in FEATURE_SETS["geometry"]
    assert "geometry_thickness_mean" in FEATURE_SETS["geometry"]
    assert "bbox_x_fraction" in FEATURE_SETS["geometry_position"]


def test_intrinsic_probe_rejects_a_legacy_schema_bank():
    bank = {"reviewed_objects": [{
        "paint_label": "old", "object_id": "old-1", "review_target_layer": "numbers",
    }]}
    try:
        evaluate_paint_holdout(bank, feature_set="intrinsic")
    except ValueError as exc:
        assert "holdout bank missing requested intrinsic feature schema" in str(exc)
    else:
        raise AssertionError("intrinsic ablation must reject missing training features")


def test_strict_number_corroboration_is_one_way_and_intrinsic():
    strong_number = {
        "object_kind": "singleton",
        "multi_proposal_member_fraction": 1.0,
        "area_fraction": 0.012,
        "aspect_ratio": 1.8,
        "template_member_fraction": 0.0,
    }
    assert number_corroboration_abstention_reason(
        strong_number, policy="strict_intrinsic"
    ) is None
    assert number_corroboration_abstention_reason(
        {**strong_number, "object_kind": "physical_group"}, policy="strict_intrinsic"
    ) == "not_singleton"
    assert number_corroboration_abstention_reason(
        {**strong_number, "multi_proposal_member_fraction": 0.0}, policy="strict_intrinsic"
    ) == "no_independent_proposal_corroboration"
    assert number_corroboration_abstention_reason(
        {**strong_number, "area_fraction": 0.001}, policy="strict_intrinsic"
    ) == "insufficient_decal_area"
    assert number_corroboration_abstention_reason(
        {**strong_number, "aspect_ratio": 1.0}, policy="strict_intrinsic"
    ) == "insufficient_digit_family_width"
    assert number_corroboration_abstention_reason(
        {**strong_number, "template_member_fraction": 1.0}, policy="strict_intrinsic"
    ) == "unresolved_template_contradiction"
    assert number_corroboration_abstention_reason(
        {
            **strong_number,
            "appearance_unassigned_instance_fraction": 1.0,
            "max_ocr_alpha_coverage": 0.0,
            "max_strong_gradient_fraction": 0.159,
        },
        policy="strict_intrinsic",
    ) == "smooth_owner_neutral_shape"
    assert number_corroboration_abstention_reason(
        {
            **strong_number,
            "appearance_unassigned_instance_fraction": 1.0,
            "max_ocr_alpha_coverage": 0.0,
            "max_strong_gradient_fraction": 0.161,
        },
        policy="strict_intrinsic",
    ) is None
    assert number_corroboration_abstention_reason(strong_number, policy="none") is None


def test_abstention_audit_separates_true_number_recall_from_rejected_noise():
    report = summarize_number_corroboration_abstentions([
        {
            "truth": "numbers", "abstention_reason": "not_singleton",
            "review_label": "true_custom_number", "review_labels": ["true_custom_number"],
        },
        {
            "truth": "sponsors", "abstention_reason": "not_singleton",
            "review_label": "wordmark_false_number", "review_labels": ["wordmark_false_number"],
        },
        {
            "truth": "template", "abstention_reason": "insufficient_decal_area",
            "review_label": None, "review_labels": [],
        },
        {"truth": "numbers", "abstention_reason": None},
    ])
    assert report["number_corroboration_abstention_truth_counts_by_reason"] == {
        "insufficient_decal_area": {"template": 1},
        "not_singleton": {"numbers": 1, "sponsors": 1},
    }
    assert report["number_corroboration_abstained_true_number_review_label_counts"] == {
        "true_custom_number": 1,
    }
    assert report["number_corroboration_rejected_false_number_review_label_counts"] == {
        "unlabeled": 1,
        "wordmark_false_number": 1,
    }
