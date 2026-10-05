from __future__ import annotations

import copy

from pathlib import Path
import numpy as np
import pytest

from _forge_dlm_known_flat_calibrator import (
    DEFAULT_POLICY,
    EvidenceError,
    _locked_policy,
    cross_version_consistency,
    fit_local_affine,
    green_wire_mask,
    pairing_decision,
    surface_masks,
)


def _grid():
    uv = np.asarray([(x, y) for y in (100, 160, 220, 280) for x in (300, 380, 460, 540, 620, 700)], np.float64)
    return uv


def _positive_screen(uv):
    matrix = np.asarray([[0.62, 0.08], [-0.04, 0.51]], np.float64)
    return uv @ matrix.T + np.asarray([37.0, 81.0])


def test_pairing_accepts_only_declared_unique_winner():
    scores = {
        "candidate_a": {"unique_uv_bin_count": 44, "match_count": 51, "mean_descriptor_distance": 120.0},
        "candidate_b": {"unique_uv_bin_count": 24, "match_count": 31, "mean_descriptor_distance": 110.0},
        "candidate_c": {"unique_uv_bin_count": 7, "match_count": 8, "mean_descriptor_distance": 90.0},
    }
    result = pairing_decision(scores, "candidate_a", DEFAULT_POLICY)
    assert result["status"] == "APPEARANCE_PAIR_CANDIDATE"
    assert result["winner_variant_id"] == "candidate_a"


def test_pairing_abstains_when_timestamp_declared_variant_is_not_visual_winner():
    scores = {
        "declared": {"unique_uv_bin_count": 30, "match_count": 40, "mean_descriptor_distance": 110.0},
        "visual": {"unique_uv_bin_count": 38, "match_count": 46, "mean_descriptor_distance": 120.0},
    }
    result = pairing_decision(scores, "declared", DEFAULT_POLICY)
    assert result["status"] == "ABSTAIN"
    assert "declared_variant_not_local_appearance_winner" in result["reasons"]


def test_pairing_abstains_on_weak_candidate_margin():
    scores = {
        "declared": {"unique_uv_bin_count": 30, "match_count": 40, "mean_descriptor_distance": 110.0},
        "other": {"unique_uv_bin_count": 28, "match_count": 38, "mean_descriptor_distance": 120.0},
    }
    result = pairing_decision(scores, "declared", DEFAULT_POLICY)
    assert result["status"] == "ABSTAIN"
    assert "insufficient_candidate_margin" in result["reasons"]


def test_green_wire_mask_rejects_only_confident_green_pixels():
    image = np.zeros((8, 8, 3), np.uint8)
    image[2, 2] = (20, 180, 30)
    image[4, 4] = (220, 220, 220)
    mask = green_wire_mask(image, minimum_green=95, delta=28, dilation=0)
    assert mask[2, 2]
    assert not mask[4, 4]


def test_surface_masks_exclude_background_and_wire():
    image = np.zeros((100, 120, 3), np.uint8)
    image[50, 60] = (10, 220, 20)
    interiors = [{"id": "piece", "points_normalized": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]}]
    masks, metrics = surface_masks(image, interiors, DEFAULT_POLICY)
    assert not masks["piece"][0, 0]
    assert not masks["piece"][50, 60]
    assert metrics["eligible_screen_pixel_count"] > 0
    assert metrics["confident_green_wire_excluded_pixel_count"] > 0
    assert metrics["surface_overlap_pixel_count"] == 0


def test_surface_masks_reject_overlapping_semantic_pieces():
    image = np.zeros((100, 120, 3), np.uint8)
    interiors = [
        {"id": "a", "points_normalized": [[0.1, 0.1], [0.7, 0.1], [0.7, 0.7], [0.1, 0.7]]},
        {"id": "b", "points_normalized": [[0.4, 0.4], [0.9, 0.4], [0.9, 0.9], [0.4, 0.9]]},
    ]
    with pytest.raises(EvidenceError):
        surface_masks(image, interiors, DEFAULT_POLICY)


def test_local_affine_passes_positive_map_with_camera_match_heldout():
    uv = _grid()
    result = fit_local_affine(uv, _positive_screen(uv), DEFAULT_POLICY)
    assert result["status"] == "LOCAL_NONREFLECTING_AFFINE_EVIDENCE"
    assert result["determinant"] > 0
    assert result["fold_count"] == 0
    assert result["heldout_residual"]["count"] >= 2


def test_local_affine_rejects_reflection():
    uv = _grid()
    screen = uv @ np.asarray([[-0.6, 0.0], [0.0, 0.5]]).T + np.asarray([900.0, 40.0])
    result = fit_local_affine(uv, screen, DEFAULT_POLICY)
    assert result["status"] == "ABSTAIN"
    assert result["reflection"] is True
    assert "reflection_or_degenerate_map" in result["reasons"]


def test_local_affine_rejects_heldout_residual_regression():
    uv = _grid()
    screen = _positive_screen(uv)
    screen[:, 0] += np.sin(np.arange(len(screen))) * 0.35
    policy = {**DEFAULT_POLICY, "maximum_train_median_residual_px": 0.01, "maximum_heldout_median_residual_px": 0.01, "maximum_heldout_p95_residual_px": 0.02}
    result = fit_local_affine(uv, screen, policy)
    assert result["status"] == "ABSTAIN"
    assert any("residual" in reason for reason in result["reasons"])


def _map(variant, role, offset=0.0):
    uv = _grid() + np.asarray([offset, 0.0])
    return {
        "variant_id": variant,
        "variant_role": role,
        "consensus_uv": uv,
        "fold_count": 0,
        "reflection": False,
    }


def test_cross_version_consistency_requires_two_train_and_one_heldout_variant():
    maps = [_map("train_a", "TRAIN_VARIANT"), _map("train_b", "TRAIN_VARIANT", 5), _map("heldout", "HELDOUT_VARIANT", 10)]
    result = cross_version_consistency(maps, DEFAULT_POLICY)
    assert result["status"] == "CROSS_VERSION_SPARSE_CALIBRATION_EVIDENCE"
    assert result["heldout_uv_support_fraction"] == 1.0


def test_cross_version_consistency_abstains_without_heldout_variant():
    maps = [_map("train_a", "TRAIN_VARIANT"), _map("train_b", "TRAIN_VARIANT", 5)]
    result = cross_version_consistency(maps, DEFAULT_POLICY)
    assert result["status"] == "LIMITED"
    assert "missing_heldout_variant" in result["reasons"]


def test_forbidden_global_or_reflecting_policy_is_rejected():
    for field in ("allow_reflection", "allow_global_map", "allow_nearest_fill", "allow_livery_claim"):
        policy = copy.deepcopy(DEFAULT_POLICY)
        policy[field] = True
        with pytest.raises(EvidenceError):
            _locked_policy(policy)

def test_reusable_module_contains_no_livery_identity_literal() -> None:
    source = (Path(__file__).resolve().parents[1] / "_forge_dlm_known_flat_calibrator.py").read_text(encoding="utf-8").lower()
    for identity in ("waffle", "dominos", "crystal_lake", "sex_wax"):
        assert identity not in source

