from __future__ import annotations

import json

import numpy as np

from scripts.smart_tga_fragment_purity_veto import (
    _appearance_matrix, _frozen_added_keys, _select_veto_threshold,
)
from scripts.smart_tga_extend_pretrained_appearance_cache import _bank_trace_rows
from scripts.smart_tga_masked_appearance_bank import (
    FEATURE_NAMES, appearance_features,
)
from scripts.smart_tga_frozen_holdout_committee import (
    _apply_fragment_rescue, _majority_top_two,
)
from scripts.smart_tga_assess_frozen_holdout import _outcome_map
from scripts.smart_tga_clipseg_semantic_mask_bank import (
    FEATURE_NAMES as SEMANTIC_FEATURE_NAMES, _d4_views, _undo_d4,
    semantic_feature_vector,
)
from scripts.smart_tga_clip_prompt_feature_bank import (
    FEATURE_NAMES as PROMPT_FEATURE_NAMES, prompt_feature_matrix,
)
from scripts.smart_tga_baseline_purity_veto import (
    _calibrate_threshold, _relative_feature_vector,
)
from scripts.smart_tga_rank_purity_active_learning import (
    _binary_vote_entropy, _ranking_key, _summarize_prediction,
)
from scripts.smart_tga_rank_fragment_rescue_active_learning import (
    _ranking_key as _rescue_ranking_key,
    _summaries as _rescue_summaries,
    _vote_entropy as _rescue_vote_entropy,
)


def test_masked_appearance_is_finite_and_d4_stable():
    rng = np.random.default_rng(733)
    rgb = rng.integers(0, 256, size=(31, 47, 3), dtype=np.uint8)
    support = np.zeros((31, 47), dtype=bool)
    support[4:26, 8:39] = True
    support[10:18, 18:28] = False
    baseline = appearance_features(rgb, support)
    assert baseline.shape == (len(FEATURE_NAMES),)
    assert np.all(np.isfinite(baseline))
    for turns in range(4):
        rotated = appearance_features(np.rot90(rgb, turns), np.rot90(support, turns))
        assert np.allclose(baseline, rotated, atol=0.03)
        reflected = appearance_features(
            np.fliplr(np.rot90(rgb, turns)), np.fliplr(np.rot90(support, turns)),
        )
        assert np.allclose(baseline, reflected, atol=0.03)


def test_appearance_feature_contract_excludes_identity_and_location():
    forbidden = ("filename", "car_identity", "bbox", "position", "block", "review")
    assert len(FEATURE_NAMES) > 100
    assert any(name.startswith("ring_") for name in FEATURE_NAMES)
    assert any(name.startswith("spatial_") for name in FEATURE_NAMES)
    assert not any(any(token in name for token in forbidden) for name in FEATURE_NAMES)


def test_veto_threshold_can_remove_false_addition_but_never_add():
    rows = [
        {
            "paint": "p0", "block": "b0", "placement_fingerprint_for_instance_dedupe": "a",
            "support_area_for_metrics_only": 100,
        },
        {
            "paint": "p1", "block": "b1", "placement_fingerprint_for_instance_dedupe": "b",
            "support_area_for_metrics_only": 80,
        },
        {
            "paint": "p2", "block": "b2", "placement_fingerprint_for_instance_dedupe": "c",
            "support_area_for_metrics_only": 60,
        },
    ]
    indices = np.arange(3, dtype=np.int64)
    data = {
        "known": np.ones(3, dtype=bool), "uncertain": np.zeros(3, dtype=bool),
        "family": np.asarray([True, True, False]),
        "complete": np.asarray([True, False, False]),
        "control": np.zeros(3, dtype=bool),
        "keys": np.asarray(["p0|b0", "p1|b1", "p2|b2"]),
    }
    baseline = np.asarray([True, False, False])
    added = np.asarray([False, True, True])
    score = np.asarray([0.5, 0.9, 0.1])
    threshold, summary = _select_veto_threshold(
        rows, indices, data, baseline, added, score,
    )
    retained = added & (score >= threshold)
    assert summary["safe_choice_found"] is True
    assert retained.tolist() == [False, True, False]
    assert np.all(~retained | added)


def test_frozen_set_parser_preserves_exact_candidate_trace(tmp_path):
    path = tmp_path / "sets.json"
    path.write_text(json.dumps({
        "sets": [{
            "paint": "dirtlatemodel 350/car_num_1.tga",
            "members": [{"candidate_index": 7, "proposal_id": "proposal:abc"}],
        }],
    }), encoding="utf-8")
    assert _frozen_added_keys(path) == {
        ("dirtlatemodel 350/car_num_1.tga", 7, "proposal:abc")
    }


def test_pretrained_anchor_relative_features_are_veto_only_d4_evidence():
    rows = [{
        "paint": "paint", "candidate_index": 2, "proposal_id": "candidate",
        "anchor": 0,
    }]
    table = {"trace": [{"candidate_index": 1, "proposal_id": "anchor"}]}
    candidate = np.eye(8, 8, dtype=np.float32)
    anchor = np.roll(candidate, 1, axis=0)
    pretrained = {
        ("paint", 2, "candidate"): candidate,
        ("paint", 1, "anchor"): anchor,
    }
    matrix, names = _appearance_matrix(
        rows, np.asarray([0]), table, {}, [],
        "pretrained-anchor-relative", pretrained,
    )
    assert matrix.shape == (1, 13)
    assert names[-5:] == [
        "pretrained_orbit_max", "pretrained_orbit_mean", "pretrained_orbit_std",
        "pretrained_orbit_median", "pretrained_orbit_q90",
    ]
    assert matrix[0, -5] == 1.0


def test_semantic_mask_evidence_appends_candidate_and_anchor_relative_values():
    rows = [{
        "paint": "paint", "candidate_index": 2, "proposal_id": "candidate",
        "anchor": 0,
    }]
    table = {"trace": [{"candidate_index": 1, "proposal_id": "anchor"}]}
    orbit = np.eye(8, 8, dtype=np.float32)
    pretrained = {
        ("paint", 2, "candidate"): orbit,
        ("paint", 1, "anchor"): orbit,
    }
    semantic = {
        ("paint", 2, "candidate"): np.asarray([0.8, -0.1], dtype=np.float32),
        ("paint", 1, "anchor"): np.asarray([0.5, 0.2], dtype=np.float32),
    }
    matrix, names = _appearance_matrix(
        rows, np.asarray([0]), table, {}, [],
        "pretrained-anchor-relative-semantic", pretrained,
        semantic, ["number_margin", "paint_margin"],
    )
    assert matrix.shape == (1, 17)
    np.testing.assert_allclose(matrix[0, -4:], [0.8, -0.1, 0.3, 0.3])
    assert names[-4:] == [
        "semantic_candidate_number_margin", "semantic_candidate_paint_margin",
        "semantic_relative_number_margin", "semantic_relative_paint_margin",
    ]


def test_label_free_holdout_trace_expansion_preserves_bank_order():
    bank = {"records": [
        {"paint": "p0", "candidates": [
            {"proposal_id": "a"}, {"proposal_id": "b"},
        ]},
        {"paint": "p1", "candidates": [{"proposal_id": "c"}]},
    ]}
    assert _bank_trace_rows(bank) == [
        {"paint": "p0", "candidate_index": 0, "proposal_id": "a"},
        {"paint": "p0", "candidate_index": 1, "proposal_id": "b"},
        {"paint": "p1", "candidate_index": 0, "proposal_id": "c"},
    ]


def test_holdout_committee_requires_majority_and_preserves_top_two_per_block():
    votes = np.asarray([
        [1, 1, 1, 0], [1, 1, 1, 0], [1, 1, 1, 1],
        [0, 0, 1, 1], [0, 0, 0, 0],
    ], dtype=bool)
    score = np.asarray([0.70, 0.90, 0.80, 0.99])
    keys = np.asarray(["p|b", "p|b", "p|b", "p|b"])
    # First three clear 3/5, but only the two highest scores survive. The last
    # candidate has the best score yet only 2/5 votes and remains rejected.
    assert _majority_top_two(votes, score, keys).tolist() == [False, True, True, False]


def test_holdout_outcome_map_rejects_duplicate_candidate_classification():
    payload = {"outcomes": {
        "Number": [{"candidate_index": 7, "complete_copy": True}],
        "Paint": [8], "Sponsor": [], "Template": [], "uncertain": [9],
    }}
    assert _outcome_map(payload) == {
        7: {"semantic": "Number", "complete_copy": True},
        8: {"semantic": "Paint", "complete_copy": False},
        9: {"semantic": "uncertain", "complete_copy": False},
    }


def test_clipseg_semantic_mask_features_are_finite_and_location_free():
    height, width = 17, 23
    support = np.zeros((7, 9), dtype=bool)
    support[1:6, 2:8] = True
    yy, xx = np.mgrid[:height, :width]
    maps = {}
    for category_offset, category in enumerate(("number", "sponsor", "paint", "template")):
        for reducer_offset, reducer in enumerate(("d4_mean", "d4_max")):
            maps[(category, reducer)] = (
                0.02 * xx + 0.01 * yy + 0.1 * category_offset + 0.03 * reducer_offset
            ).astype(np.float32)
    result = semantic_feature_vector(maps, [5, 4, 9, 7], support)
    assert result.shape == (len(SEMANTIC_FEATURE_NAMES),)
    assert np.all(np.isfinite(result))
    assert not any(
        token in name for name in SEMANTIC_FEATURE_NAMES
        for token in ("filename", "car", "bbox", "position", "block", "review")
    )


def test_clipseg_d4_inverse_restores_square_source_coordinates():
    source = np.arange(36, dtype=np.float32).reshape(6, 6)
    for view, turns, reflected in _d4_views(source):
        np.testing.assert_array_equal(_undo_d4(view, turns, reflected), source)


def test_candidate_resolution_prompt_features_are_d4_summaries_only():
    appearance = np.zeros((2, 8, 3), dtype=np.float32)
    appearance[0, :, 0] = 1.0
    appearance[1, :, 1] = 1.0
    prototypes = {
        "complete_number": np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
        "number_fragment": np.asarray([0.8, 0.0, 0.0], dtype=np.float32),
        "sponsor": np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
        "paint": np.asarray([0.0, 0.0, 1.0], dtype=np.float32),
    }
    result = prompt_feature_matrix(appearance, prototypes)
    assert result.shape == (2, len(PROMPT_FEATURE_NAMES))
    assert np.all(np.isfinite(result))
    margin = PROMPT_FEATURE_NAMES.index("prompt_number_minus_nonnumber_mean")
    assert result[0, margin] == 1.0
    assert result[1, margin] == -1.0


def test_baseline_purity_threshold_sits_between_raw_false_and_true_scores():
    threshold, summary = _calibrate_threshold(
        np.asarray([0.74, 0.82, 0.91]), np.asarray([0.19, 0.41]),
    )
    assert 0.41 < threshold < 0.74
    assert summary["strictly_separated"] is True
    assert summary["margin"] == 0.33


def test_baseline_purity_threshold_reports_overlap_instead_of_hiding_it():
    threshold, summary = _calibrate_threshold(
        np.asarray([0.44, 0.80]), np.asarray([0.52, 0.18]),
    )
    assert threshold == 0.44
    assert summary["strictly_separated"] is False
    assert summary["margin"] == -0.08


def test_baseline_purity_combines_d4_appearance_and_prompt_deltas():
    candidate_key = ("paint", 2, "candidate")
    anchor_key = ("paint", 1, "anchor")
    candidate = np.tile(np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32), (8, 1))
    anchor = np.tile(np.asarray([[0.0, 1.0, 0.0]], dtype=np.float32), (8, 1))
    result = _relative_feature_vector(
        candidate_key, anchor_key,
        {candidate_key: candidate, anchor_key: anchor},
        {
            candidate_key: np.asarray([0.8, -0.1], dtype=np.float32),
            anchor_key: np.asarray([0.5, 0.2], dtype=np.float32),
        },
    )
    assert result.shape == (12,)
    assert np.all(np.isfinite(result))
    np.testing.assert_allclose(result[-4:], [0.8, -0.1, 0.3, 0.3])


def test_active_learning_vote_entropy_is_normalized_and_deterministic():
    assert _binary_vote_entropy(0, 5) == 0.0
    assert _binary_vote_entropy(5, 5) == 0.0
    assert _binary_vote_entropy(2, 4) == 1.0


def test_active_learning_uses_threshold_distance_when_vote_entropy_ties():
    def payload(paint, probability, retained_votes):
        return {
            "baseline_purity_enabled": True,
            "holdout_paint": paint,
            "committee": {"size": 5, "votes_required": 3},
            "folds": [{"baseline_purity_threshold": value} for value in (
                0.49, 0.50, 0.51, 0.52, 0.53,
            )],
            "decisions": [{
                "candidate_index": 7,
                "proposal_id": f"proposal:{paint}",
                "baseline_votes": 5,
                "baseline_purity_retained_votes": retained_votes,
                "median_baseline_purity_probability": probability,
            }],
        }

    farther = _summarize_prediction(payload("farther", 0.90, 5))
    nearer = _summarize_prediction(payload("nearer", 0.56, 5))
    assert sorted((farther, nearer), key=_ranking_key)[0]["paint"] == "nearer"


def test_fragment_rescue_only_protects_existing_raw_candidates():
    baseline = np.asarray([True, True, False, False])
    purity = np.asarray([False, True, False, False])
    complete = np.asarray([0.8, 0.9, 0.95, 0.1])
    retained, rescued = _apply_fragment_rescue(
        baseline, purity, complete, threshold=0.7,
    )
    np.testing.assert_array_equal(retained, [True, True, False, False])
    np.testing.assert_array_equal(rescued, [True, False, False, False])


def test_fragment_rescue_active_learning_requires_majority_behavior():
    payload = {
        "baseline_fragment_rescue_enabled": True,
        "committee": {"votes_required": 3},
        "decisions": [
            {
                "paint": "no-majority",
                "candidate_index": 1,
                "proposal_id": "one",
                "baseline_votes": 5,
                "baseline_fragment_rescue_votes": 2,
                "median_complete_probability": 0.51,
            },
            {
                "paint": "majority",
                "candidate_index": 2,
                "proposal_id": "two",
                "baseline_votes": 4,
                "baseline_fragment_rescue_votes": 3,
                "median_complete_probability": 0.52,
            },
        ],
    }
    rows = _rescue_summaries(payload, rescue_threshold=0.49)
    ranked = sorted(rows, key=_rescue_ranking_key)
    assert ranked[0]["paint"] == "majority"
    assert ranked[0]["majority_rescue_candidate_count"] == 1
    assert ranked[1]["majority_rescue_candidate_count"] == 0
    assert _rescue_vote_entropy(2, 4) == 1.0


def test_fragment_rescue_active_learning_ignores_non_raw_candidates():
    payload = {
        "baseline_fragment_rescue_enabled": True,
        "committee": {"votes_required": 3},
        "decisions": [{
            "paint": "paint",
            "candidate_index": 9,
            "proposal_id": "not-raw",
            "baseline_votes": 2,
            "baseline_fragment_rescue_votes": 2,
            "median_complete_probability": 0.9,
        }],
    }
    row = _rescue_summaries(payload, rescue_threshold=0.49)[0]
    assert row["raw_nomination_count"] == 0
    assert row["any_rescue_vote_candidate_count"] == 0
    assert row["majority_rescue_candidate_count"] == 0
