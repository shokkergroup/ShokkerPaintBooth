from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_historical_surface_vote_fuser import (
    DEFAULT_POLICY,
    HashDriftError,
    canonical_hash,
    classify_point_in_polygon,
    classify_render_surface,
    feature_to_original,
    fuse_vote_documents,
    locked_path,
)


PAINT_HASH = "b" * 64


def _polygon(surface: str, left=0.2, top=0.2, right=0.8, bottom=0.8):
    return {
        "surface_id": surface,
        "points": [[left, top], [right, top], [right, bottom], [left, bottom]],
        "confidence": 0.95,
    }


def _seed(render_hash: str, surface="left_side", *, polygons=None, render_id=None):
    return {
        "render_id": render_id or f"render_{render_hash[0]}",
        "source": {"path": "render.png", "sha256": render_hash, "size": [100, 100]},
        "paired_paint": {"path": "paint.tga", "sha256": PAINT_HASH},
        "polygons": polygons or [_polygon(surface)],
    }


def _match(*, uv=(6, 8), render=(50, 50), accepted=True):
    return {
        "accepted": accepted,
        "flat_xy": [uv[0] * 0.5, uv[1] * 0.5],
        "render_xy": [render[0] * 0.5, render[1] * 0.5],
        "cluster_id": "cell_0_model_0",
    }


def _pair(cohort: str, split: str, render_hash: str, matches, *, status="SPARSE_EVIDENCE"):
    return {
        "cohort_id": cohort,
        "split": split,
        "status": status,
        "paint": {"path": "paint.tga", "sha256": PAINT_HASH, "size": [16, 16], "feature_scale": 0.5},
        "render": {"path": "render.png", "sha256": render_hash, "size": [100, 100], "feature_scale": 0.5},
        "matches": list(matches),
    }


def _documents(pairs, seeds):
    labels = np.zeros((16, 16), dtype=np.uint16)
    labels[8, 6] = 7
    labels[10, 10] = 8
    official = np.ones((16, 16), dtype=bool)
    run91 = {"pairs": list(pairs)}
    run94 = {"coordinate_space": "source_image_normalized_xy", "renders": list(seeds)}
    return run91, run94, labels, official


def _policy(**changes):
    return {**DEFAULT_POLICY, **changes}


def test_both_uv_and_render_feature_coordinates_scale_back_to_original_images():
    uv = feature_to_original([700, 350], 1400 / 2048, [2048, 2048])
    render = feature_to_original([450, 225], 0.5, [1800, 900])
    assert uv == (1024.0, 512.0, 1024, 512)
    assert render == (900.0, 450.0, 900, 450)

    digest = "a" * 64
    run91, run94, labels, official = _documents(
        [_pair("alpha", "TRAIN_CONTROL", digest, [_match()])], [_seed(digest)]
    )
    result = fuse_vote_documents(run91, run94, labels, official, policy=_policy(minimum_matches=1, minimum_train_cohorts=1, minimum_withheld_cohorts=0))
    accepted = result["accepted_matches"][0]
    assert accepted["uv_original_xy"] == [6.0, 8.0]
    assert accepted["render_original_xy"] == [50.0, 50.0]
    assert accepted["render_normalized_xy"] == [0.5, 0.5]


def test_polygon_boundary_is_never_inside():
    square = _polygon("left_side")["points"]
    assert classify_point_in_polygon((0.2, 0.5), square) == "boundary"
    surface, reason = classify_render_surface((0.2, 0.5), [_polygon("left_side")])
    assert surface is None and reason == "polygon_boundary"

    digest = "a" * 64
    run91, run94, labels, official = _documents(
        [_pair("alpha", "TRAIN_CONTROL", digest, [_match(render=(20, 50))])], [_seed(digest)]
    )
    result = fuse_vote_documents(run91, run94, labels, official)
    assert result["accepted_vote_match_count"] == 0
    assert result["rejection_reasons"] == {"polygon_boundary": 1}


def test_polygon_overlap_rejects_even_when_both_are_known_surfaces():
    polygons = [_polygon("left_side", 0.1, 0.1, 0.7, 0.7), _polygon("hood_nose", 0.3, 0.3, 0.9, 0.9)]
    surface, reason = classify_render_surface((0.5, 0.5), polygons)
    assert surface is None and reason == "overlapping_surface_polygons"

    digest = "a" * 64
    run91, run94, labels, official = _documents(
        [_pair("alpha", "TRAIN_CONTROL", digest, [_match()])], [_seed(digest, polygons=polygons)]
    )
    result = fuse_vote_documents(run91, run94, labels, official)
    assert result["accepted_vote_match_count"] == 0
    assert result["rejection_reasons"] == {"overlapping_surface_polygons": 1}


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("outside_polygon", "outside_surface_polygons"),
        ("outside_official", "outside_official"),
        ("unknown_component", "unknown_component"),
        ("rejected_match", "rejected_match"),
        ("rejected_pair", "rejected_pair"),
    ],
)
def test_outside_unknown_and_rejected_evidence_fail_closed(mutation, reason):
    digest = "a" * 64
    match = _match(render=(95, 95) if mutation == "outside_polygon" else (50, 50), accepted=mutation != "rejected_match")
    pair = _pair("alpha", "TRAIN_CONTROL", digest, [match], status="ABSTAIN" if mutation == "rejected_pair" else "SPARSE_EVIDENCE")
    run91, run94, labels, official = _documents([pair], [_seed(digest)])
    if mutation == "outside_official":
        official[8, 6] = False
    if mutation == "unknown_component":
        labels[8, 6] = 0
    result = fuse_vote_documents(run91, run94, labels, official)
    assert result["accepted_vote_match_count"] == 0
    assert result["rejection_reasons"] == {reason: 1}


def test_surface_contradiction_abstains_without_majority_override():
    left_hash, hood_hash = "a" * 64, "c" * 64
    pairs = [
        _pair("alpha", "TRAIN_CONTROL", left_hash, [_match(), _match()]),
        _pair("beta", "TRAIN_CONTROL", left_hash, [_match()]),
        _pair("gamma", "WITHHELD", hood_hash, [_match()]),
    ]
    seeds = [_seed(left_hash, "left_side"), _seed(hood_hash, "hood_nose")]
    run91, run94, labels, official = _documents(pairs, seeds)
    result = fuse_vote_documents(run91, run94, labels, official)
    decision = next(item for item in result["component_decisions"] if item["component_label"] == 7)
    assert decision["status"] == "ABSTAIN"
    assert decision["reason"] == "surface_contradiction"
    assert decision["candidate_surface_id"] is None
    assert {vote["surface_id"] for vote in decision["surface_votes"]} == {"left_side", "hood_nose"}


def test_candidate_requires_locked_matches_two_train_cohorts_and_withheld_support():
    digest = "a" * 64
    pairs = [
        _pair("alpha", "TRAIN_CONTROL", digest, [_match(), _match()]),
        _pair("beta", "TRAIN_CONTROL", digest, [_match()]),
        _pair("holdout", "WITHHELD", digest, [_match()]),
    ]
    run91, run94, labels, official = _documents(pairs, [_seed(digest)])
    result = fuse_vote_documents(run91, run94, labels, official)
    decision = next(item for item in result["component_decisions"] if item["component_label"] == 7)
    assert decision["status"] == "COMPONENT_VOTE_EVIDENCE"
    assert decision["candidate_surface_id"] == "left_side"
    vote = decision["surface_votes"][0]
    assert vote["match_count"] == 4
    assert vote["train_control"]["cohorts"] == ["alpha", "beta"]
    assert vote["withheld"]["cohorts"] == ["holdout"]
    assert result["candidate_component_count"] == 1


def test_many_matches_from_one_train_cohort_do_not_fake_cohort_diversity():
    digest = "a" * 64
    pairs = [
        _pair("alpha", "TRAIN_CONTROL", digest, [_match(), _match(), _match(), _match()]),
        _pair("holdout", "WITHHELD", digest, [_match()]),
    ]
    run91, run94, labels, official = _documents(pairs, [_seed(digest)])
    result = fuse_vote_documents(run91, run94, labels, official)
    decision = next(item for item in result["component_decisions"] if item["component_label"] == 7)
    assert decision["status"] == "LIMITED"
    assert decision["reason"] == "insufficient_train_cohorts"


def test_two_train_cohorts_without_withheld_support_stay_limited():
    digest = "a" * 64
    pairs = [
        _pair("alpha", "TRAIN_CONTROL", digest, [_match(), _match()]),
        _pair("beta", "TRAIN_CONTROL", digest, [_match(), _match()]),
    ]
    run91, run94, labels, official = _documents(pairs, [_seed(digest)])
    result = fuse_vote_documents(run91, run94, labels, official)
    decision = next(item for item in result["component_decisions"] if item["component_label"] == 7)
    assert decision["status"] == "LIMITED"
    assert decision["reason"] == "missing_withheld_support"


def test_hash_tamper_fails_closed(tmp_path: Path):
    source = tmp_path / "evidence.json"
    source.write_text("{}", encoding="utf-8")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    source.write_text('{"tampered":true}', encoding="utf-8")
    with pytest.raises(HashDriftError):
        locked_path({"path": str(source), "sha256": expected}, "synthetic")


def test_fusion_is_deterministic_and_all_expansive_claims_remain_false():
    digest = "a" * 64
    pairs = [
        _pair("alpha", "TRAIN_CONTROL", digest, [_match(), _match()]),
        _pair("beta", "TRAIN_CONTROL", digest, [_match()]),
        _pair("holdout", "WITHHELD", digest, [_match()]),
    ]
    run91, run94, labels, official = _documents(pairs, [_seed(digest)])
    first = fuse_vote_documents(run91, run94, labels, official)
    second = fuse_vote_documents(run91, run94, labels, official)
    assert first == second
    bare = {key: value for key, value in first.items() if key != "deterministic_hash"}
    assert first["deterministic_hash"] == canonical_hash(bare)
    assert first["claims"]["component_vote_evidence_only"] is True
    assert not any(value for key, value in first["claims"].items() if key != "component_vote_evidence_only")
