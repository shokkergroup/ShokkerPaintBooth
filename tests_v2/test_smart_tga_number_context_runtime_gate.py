from scripts.smart_tga_number_context_runtime_gate import evaluate_runtime_population


def test_runtime_gate_scores_every_proposal_not_only_curated_matches():
    proposals = [
        {"bbox": [10, 10, 20, 20], "number_score": 0.8},
        {"bbox": [50, 50, 20, 20], "number_score": 0.7},
    ]
    inspections = [{
        "paint_label": "paint",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "number_context_shadow": {"proposal_records": proposals},
        }}},
    }]
    result = evaluate_runtime_population(
        inspections,
        [{"paint_label": "paint", "bbox": [10, 10, 20, 20]}],
        [{"paint_label": "paint", "bbox": [50, 50, 20, 20]}],
        threshold=0.75,
    )
    assert result["accepted_proposal_count"] == 1
    assert result["positive_copy_hits"] == 1
    assert result["hard_negative_hits"] == 0


def test_runtime_gate_can_measure_position_corroboration_stage():
    inspections = [{
        "paint_label": "paint",
        "route_adjudicator_shadow": {"candidate_evidence": {"decal_instances": {
            "number_context_shadow": {"proposal_records": [
                {"bbox": [10, 10, 20, 20], "number_score": 0.9, "position_score": 0.8},
                {"bbox": [50, 50, 20, 20], "number_score": 0.9, "position_score": 0.2},
            ]},
        }}},
    }]
    result = evaluate_runtime_population(
        inspections,
        [{"paint_label": "paint", "bbox": [10, 10, 20, 20]}],
        [{"paint_label": "paint", "bbox": [50, 50, 20, 20]}],
        threshold=0.75, score_field="position_score",
    )
    assert result["positive_copy_hits"] == 1
    assert result["hard_negative_hits"] == 0
