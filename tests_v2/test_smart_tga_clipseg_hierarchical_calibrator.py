from __future__ import annotations

import numpy as np

from scripts import smart_tga_clipseg_hierarchical_calibrator as calibrator
from scripts import smart_tga_clipseg_hierarchical_holdout as holdout


def test_features_are_owner_neutral_semantic_then_complete_margin():
    category = np.asarray([
        [0.40, 0.30, 0.20, 0.10],
        [0.25, 0.45, 0.35, 0.30],
    ])
    semantic, complete = calibrator._feature_matrices(category)
    np.testing.assert_allclose(semantic[:, 0], [0.40, 0.45])
    np.testing.assert_allclose(complete, [[0.40, 0.10], [0.25, -0.20]])


def test_lower_quartile_committee_is_conservative():
    members = [
        np.asarray([0.2, 0.8]),
        np.asarray([0.4, 0.6]),
        np.asarray([0.6, 0.4]),
        np.asarray([0.8, 0.2]),
    ]
    result = calibrator._lower_quartile_ensemble(members)
    np.testing.assert_allclose(result, [0.35, 0.35])


def test_robust_threshold_sits_one_mad_above_every_unsafe_score():
    scores = np.asarray([0.20, 0.30, 0.40, 0.70])
    truth = np.asarray([False, False, True, True])
    explicit = np.asarray([True, True, True, True])
    stress = np.asarray([False, False, False, False])
    threshold, maximum, mad = calibrator._robust_safe_threshold(
        scores, truth, explicit, stress,
    )
    assert maximum == 0.30
    assert np.isclose(mad, 0.05)
    assert np.isclose(threshold, 0.35)


def test_uncertain_and_control_scores_are_unsafe_even_when_truthy():
    scores = np.asarray([0.70, 0.80, 0.90])
    truth = np.asarray([True, True, True])
    explicit = np.asarray([True, False, True])
    stress = np.asarray([False, False, True])
    threshold, maximum, _ = calibrator._robust_safe_threshold(
        scores, truth, explicit, stress,
    )
    assert maximum == 0.90
    assert threshold >= maximum


def test_inference_features_exclude_identity_and_bbox_authority():
    source = open(calibrator.__file__, encoding="utf-8").read()
    feature_source = source[source.index("def _feature_matrices"):source.index("def _new_model")]
    for forbidden in ("filename", "candidate_index", "bbox", "paint"):
        assert forbidden not in feature_source


def test_holdout_target_overlap_requires_complete_coverage():
    target = [100, 100, 100, 100]
    assert holdout._candidate_matches_target([100, 100, 100, 100], target)
    assert holdout._candidate_matches_target([90, 90, 120, 120], target)
    assert not holdout._candidate_matches_target([100, 100, 50, 100], target)
    assert not holdout._candidate_matches_target([0, 0, 40, 40], target)


def test_holdout_inference_never_uses_metric_boxes():
    source = open(holdout.__file__, encoding="utf-8").read()
    score_source = source[source.index("def _score_locked_holdout"):source.index("def main")]
    for forbidden in ("bbox", "target", "filename", "candidate_index", "paint"):
        assert forbidden not in score_source
