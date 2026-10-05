from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_historical_surface_vote_fuser import HashDriftError, locked_path
from _forge_dlm_seam_constrained_subcomponents import (
    DEFAULT_POLICY,
    EvidenceError,
    evaluate_subregions,
    partition_component,
    partition_vote_components,
    scale_wire_barrier,
)


def _vote(x, y, surface, cohort, split):
    return {
        "uv_sample_xy": [x, y],
        "surface_id": surface,
        "cohort_id": cohort,
        "split": split,
        "component_label": 7,
    }


def _vertical_split(size=9, x=4):
    component = np.ones((size, size), dtype=bool)
    barrier = np.zeros_like(component)
    barrier[:, x] = True
    regions, boundary, metrics = partition_component(component, barrier, boundary_radius=0)
    return component, barrier, regions, boundary, metrics


def test_wire_alpha_scales_nearest_without_interpolated_geometry():
    alpha = np.array([[0, 100], [200, 255]], dtype=np.uint8)
    barrier = scale_wire_barrier(alpha, (4, 4), 128)
    expected = np.array(
        [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
        ],
        dtype=bool,
    )
    assert np.array_equal(barrier, expected)


def test_proved_wire_barrier_creates_disjoint_geodesic_regions_and_boundary_band():
    component, _, regions, boundary, metrics = _vertical_split()
    assert metrics["subregion_count"] == 2
    assert metrics["overlap_pixel_count"] == 0
    assert metrics["containment_violation_pixel_count"] == 0
    assert np.count_nonzero(boundary) == 9
    assert not np.any((regions > 0) & boundary)
    assert not np.any((regions > 0) & ~component)
    assert set(np.unique(regions)) == {0, 1, 2}


def test_abstention_band_expands_only_inside_exact_component():
    component = np.zeros((11, 11), dtype=bool)
    component[1:10, 1:10] = True
    barrier = np.zeros_like(component)
    barrier[1:10, 5] = True
    regions, boundary, metrics = partition_component(component, barrier, boundary_radius=1)
    assert metrics["subregion_count"] == 2
    assert np.all(boundary <= component)
    assert not np.any((regions > 0) & boundary)
    assert metrics["traversable_pixel_count"] + metrics["abstention_boundary_pixel_count"] == metrics["component_pixel_count"]


def test_locked_train_diversity_and_withheld_support_promote_one_subregion_only():
    component, _, regions, boundary, _ = _vertical_split()
    votes = [
        _vote(1, 2, "left_side", "alpha", "TRAIN_CONTROL"),
        _vote(2, 3, "left_side", "alpha", "TRAIN_CONTROL"),
        _vote(1, 5, "left_side", "beta", "TRAIN_CONTROL"),
        _vote(2, 6, "left_side", "holdout", "WITHHELD"),
    ]
    result = evaluate_subregions(regions, component, boundary, votes)
    promoted = [item for item in result["decisions"] if item["status"] == "SUBREGION_VOTE_EVIDENCE"]
    assert len(promoted) == 1
    assert promoted[0]["surface_id"] == "left_side"
    assert result["promoted_subregion_count"] == 1


def test_surface_contradiction_abstains_even_with_large_majority():
    component, _, regions, boundary, _ = _vertical_split()
    votes = [
        *[_vote(1, 2, "left_side", f"train_{index}", "TRAIN_CONTROL") for index in range(8)],
        _vote(2, 6, "rear_deck_lid", "holdout", "WITHHELD"),
    ]
    result = evaluate_subregions(regions, component, boundary, votes)
    left = next(item for item in result["decisions"] if item["surface_votes"])
    assert left["status"] == "ABSTAIN"
    assert left["reason"] == "surface_contradiction"
    assert left["surface_id"] is None


def test_no_wire_barrier_means_conflicted_connected_region_stays_abstain():
    component = np.ones((9, 9), dtype=bool)
    barrier = np.zeros_like(component)
    regions, boundary, metrics = partition_component(component, barrier, boundary_radius=1)
    votes = [
        _vote(1, 2, "left_side", "alpha", "TRAIN_CONTROL"),
        _vote(7, 6, "rear_deck_lid", "holdout", "WITHHELD"),
    ]
    result = evaluate_subregions(regions, component, boundary, votes)
    assert metrics["subregion_count"] == 1
    assert result["decisions"][0]["reason"] == "surface_contradiction"


def test_vote_on_reserved_boundary_never_enters_a_subregion():
    component, _, regions, boundary, _ = _vertical_split()
    result = evaluate_subregions(
        regions,
        component,
        boundary,
        [_vote(4, 4, "left_side", "holdout", "WITHHELD")],
    )
    assert result["accepted_region_vote_count"] == 0
    assert result["vote_rejection_reasons"] == {"vote_in_abstention_boundary": 1}


def test_two_train_cohorts_without_withheld_support_remain_limited():
    component, _, regions, boundary, _ = _vertical_split()
    votes = [
        _vote(1, 1, "left_side", "alpha", "TRAIN_CONTROL"),
        _vote(2, 2, "left_side", "alpha", "TRAIN_CONTROL"),
        _vote(1, 5, "left_side", "beta", "TRAIN_CONTROL"),
        _vote(2, 6, "left_side", "beta", "TRAIN_CONTROL"),
    ]
    result = evaluate_subregions(regions, component, boundary, votes)
    voted = next(item for item in result["decisions"] if item["surface_votes"])
    assert voted["status"] == "LIMITED"
    assert voted["reason"] == "missing_withheld_support"


def test_exact_official_containment_is_required_before_partition():
    labels = np.zeros((9, 9), dtype=np.uint16)
    labels[1:8, 1:8] = 7
    official = np.ones((9, 9), dtype=bool)
    official[2, 2] = False
    wire = np.zeros((9, 9), dtype=bool)
    with pytest.raises(EvidenceError, match="escapes exact official mask"):
        partition_vote_components(labels, official, wire, {"accepted_matches": []}, [7])


def test_hash_tamper_fails_closed(tmp_path: Path):
    source = tmp_path / "wire.png"
    source.write_bytes(b"wire")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    source.write_bytes(b"tampered")
    with pytest.raises(HashDriftError):
        locked_path({"path": str(source), "sha256": expected}, "wire")


def test_partition_and_decisions_are_deterministic():
    labels = np.zeros((9, 9), dtype=np.uint16)
    labels[:, :] = 7
    official = np.ones((9, 9), dtype=bool)
    wire = np.zeros((9, 9), dtype=bool)
    wire[:, 4] = True
    votes = [
        _vote(1, 2, "left_side", "alpha", "TRAIN_CONTROL"),
        _vote(2, 3, "left_side", "alpha", "TRAIN_CONTROL"),
        _vote(1, 5, "left_side", "beta", "TRAIN_CONTROL"),
        _vote(2, 6, "left_side", "holdout", "WITHHELD"),
    ]
    run95 = {"accepted_matches": votes}
    first, first_maps, first_boundaries = partition_vote_components(labels, official, wire, run95, [7], policy=DEFAULT_POLICY)
    second, second_maps, second_boundaries = partition_vote_components(labels, official, wire, run95, [7], policy=DEFAULT_POLICY)
    assert first == second
    assert np.array_equal(first_maps[7], second_maps[7])
    assert np.array_equal(first_boundaries[7], second_boundaries[7])
    assert first["claims"]["seam_constrained_subregion_vote_evidence_only"] is True
    assert not any(value for key, value in first["claims"].items() if key != "seam_constrained_subregion_vote_evidence_only")
