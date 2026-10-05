import json
from pathlib import Path

import numpy as np

from scripts.smart_tga_visual_prototype_score import evaluate_reviewed, score


def test_frozen_prototype_score_is_shadow_only(tmp_path: Path):
    model_path = tmp_path / "model.npz"
    np.savez_compressed(
        model_path,
        schema=np.asarray(["smart-tga-visual-prototype-bank-v1"]),
        embedding=np.asarray([[1.0, 0.0], [0.0, 1.0]], np.float32),
        is_number=np.asarray([True, False]),
        is_sponsor=np.asarray([False, True]),
        metric=np.asarray(["number_minus_nonnumber_top1"]),
        threshold=np.asarray([0.2], np.float32),
    )
    runtime = {
        "records": [{
            "paint_label": "holdout",
            "local_candidates": [
                {"family_id": "n", "bbox": [0, 0, 1, 1], "accepted": True, "visual_embedding": [1.0, 0.0]},
                {"family_id": "s", "bbox": [0, 0, 1, 1], "accepted": True, "visual_embedding": [0.0, 1.0]},
            ],
        }],
    }
    result = score(runtime, model_path)
    assert result["current_accepted_count"] == 2
    assert result["final_shadow_accepted_count"] == 1
    assert result["casts_votes"] is False
    assert result["ownership_authority"] is False
    assert result["output_applied"] is False
    assert [item["final_shadow_accepted"] for item in result["records"][0]["candidates"]] == [True, False]

    labels = [{
        "source_totals": {"visible_number_copies": 2},
        "candidate_labels": [
            {"paint": "holdout", "family_id": "n", "semantic": "Number", "complete_copy": True},
            {"paint": "holdout", "family_id": "s", "semantic": "Sponsor", "complete_copy": False},
        ],
    }]
    metrics = evaluate_reviewed(result, labels)
    assert metrics["current_gate"]["accepted_negative_or_uncertain"] == 1
    assert metrics["final_intersection_shadow"]["accepted_negative_or_uncertain"] == 0
    assert metrics["final_intersection_shadow"]["visible_number_copy_recall"] == 0.5
