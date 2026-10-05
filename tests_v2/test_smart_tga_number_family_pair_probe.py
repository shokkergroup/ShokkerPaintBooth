import json

import numpy as np
import pytest

from scripts.smart_tga_number_family_pair_probe import (
    _mutual_top_candidates, choose_retrieval_threshold, choose_sponsor_veto,
    choose_threshold, load_banks,
)


def test_threshold_is_selected_from_precision_gate():
    truth = np.asarray([True, True, False, False])
    scores = np.asarray([0.9, 0.8, 0.7, 0.1])
    threshold, metrics = choose_threshold(truth, scores, min_precision=1.0)
    assert threshold == 0.8
    assert metrics["true_positive"] == 2
    assert metrics["false_positive"] == 0


def test_threshold_abstains_when_precision_gate_has_too_few_positives():
    truth = np.asarray([True, False])
    scores = np.asarray([0.9, 0.1])
    threshold, metrics = choose_threshold(truth, scores, min_precision=1.0)
    assert threshold == 1.0
    assert metrics["true_positive"] == 0


def test_retrieval_threshold_scores_only_one_candidate_per_anchor():
    selected = [
        ({"left_instance_id": "a"}, True, 0.9),
        ({"left_instance_id": "b"}, False, 0.6),
        ({"left_instance_id": "c"}, True, 0.7),
    ]
    threshold, metrics = choose_retrieval_threshold(selected, min_precision=1.0)
    assert threshold == 0.7
    assert metrics["true_positive"] == 2
    assert metrics["false_positive"] == 0


def test_sponsor_veto_can_remove_false_anchor_without_promoting():
    selected = [
        ({"left_instance_id": "a"}, True, 0.9),
        ({"left_instance_id": "b"}, True, 0.8),
        ({"left_instance_id": "c"}, False, 0.95),
    ]
    threshold, metrics = choose_sponsor_veto(
        selected, [-0.2, -0.1, 0.8], base_threshold=0.7,
    )
    assert threshold <= 0.8
    assert metrics["true_positive"] == 2
    assert metrics["false_positive"] == 0


def test_load_banks_preserves_rows_across_forward_cycles(tmp_path):
    feature_names = ["shape_d4_l1"]
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps({"feature_names": feature_names, "records": [{"cycle": "cycle690"}]}))
    second.write_text(json.dumps({"feature_names": feature_names, "records": [{"cycle": "cycle693"}]}))
    merged = load_banks([first, second])
    assert [row["cycle"] for row in merged["records"]] == ["cycle690", "cycle693"]
    assert merged["summary"]["ownership_authority"] is False


def test_load_banks_rejects_feature_schema_drift(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps({"feature_names": ["a"], "records": []}))
    second.write_text(json.dumps({"feature_names": ["b"], "records": []}))
    with pytest.raises(ValueError, match="schemas"):
        load_banks([first, second])


def test_mutual_top_requires_candidate_to_return_to_same_anchor():
    rows = [
        {"paint_label":"p","family_id":"f","left_instance_id":"a","right_instance_id":"b","truth_same_number_family":True},
        {"paint_label":"p","family_id":"f","left_instance_id":"a","right_instance_id":"n","truth_same_number_family":False},
        {"paint_label":"p","family_id":"f","left_instance_id":"b","right_instance_id":"a","truth_same_number_family":True},
        {"paint_label":"p","family_id":"f","left_instance_id":"b","right_instance_id":"n","truth_same_number_family":False},
    ]
    selected, diagnostics = _mutual_top_candidates(
        rows,
        np.asarray([0.8, 0.3, 0.75, 0.2]),
        np.asarray([0.75, 0.1, 0.8, 0.1]),
    )
    assert len(selected) == 2
    assert all(truth and score == pytest.approx(0.75) for _, truth, score in selected)
    assert all(item["mutual"] for item in diagnostics)
