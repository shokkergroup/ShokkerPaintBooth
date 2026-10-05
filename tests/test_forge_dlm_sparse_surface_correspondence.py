from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from _forge_dlm_sparse_surface_correspondence import (
    HashDriftError,
    canonical_hash,
    feature_to_original,
    fuse_sparse_documents,
    locked_path,
)


def _match(x, y, *, accepted=True):
    return {"accepted": accepted, "flat_xy": [x, y], "render_xy": [20, 30], "cluster_id": "local"}


def _pair(cohort, split, matches, *, status="SPARSE_EVIDENCE", scale=0.5):
    return {
        "cohort_id": cohort,
        "split": split,
        "status": status,
        "paint": {"feature_scale": scale, "size": [16, 16]},
        "render": {"path": "render.png", "sha256": "0" * 64},
        "matches": matches,
    }


def _docs(pairs, assignment=None):
    labels = np.zeros((16, 16), np.uint16)
    official = np.ones((16, 16), bool)
    labels[8, 6] = 7
    labels[10, 10] = 8
    run92 = {"component_assignments": assignment or {"7": {"status": "SEED", "surface_id": "left_side"}, "8": {"status": "PROPAGATED", "surface_id": "hood_nose"}}}
    return {"pairs": pairs}, run92, labels, official


def test_feature_coordinates_scale_back_to_original_2048_space():
    x, y, px, py = feature_to_original([700, 350], 1400 / 2048, [2048, 2048])
    assert (px, py) == (1024, 512)
    assert abs(x - 1024) < 1e-9 and abs(y - 512) < 1e-9


def test_cross_cohort_train_and_withheld_promotes_sparse_surface_only():
    pairs = [_pair("alpha", "TRAIN_CONTROL", [_match(3, 4)]), _pair("beta", "WITHHELD", [_match(3, 4)])]
    run91, run92, labels, official = _docs(pairs)
    result = fuse_sparse_documents(run91, run92, labels, official)
    assert result["accepted_sparse_correspondence_count"] == 2
    assert result["cross_cohort_sparse_surface_count"] == 1
    assert result["surfaces"][0]["status"] == "SPARSE_EVIDENCED"
    assert result["surfaces"][0]["train_control"]["match_count"] == 1
    assert result["surfaces"][0]["withheld"]["match_count"] == 1
    assert result["claims"]["sparse_surface_evidence_only"] is True
    assert not any(value for key, value in result["claims"].items() if key != "sparse_surface_evidence_only")


def test_train_only_stays_limited_and_withheld_is_not_leaked():
    pairs = [_pair("alpha", "TRAIN_CONTROL", [_match(3, 4)]), _pair("gamma", "TRAIN_CONTROL", [_match(3, 4)])]
    run91, run92, labels, official = _docs(pairs)
    result = fuse_sparse_documents(run91, run92, labels, official)
    assert result["surfaces"][0]["cohort_count"] == 2
    assert result["surfaces"][0]["withheld"]["match_count"] == 0
    assert result["surfaces"][0]["status"] == "LIMITED_SPARSE_EVIDENCE"


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("outside", "outside_official"),
        ("unknown", "unknown_component"),
        ("conflict", "conflicted_component"),
        ("unowned", "unowned_component"),
    ],
)
def test_outside_unknown_conflict_and_unowned_reject(mutation, reason):
    run91, run92, labels, official = _docs([_pair("alpha", "TRAIN_CONTROL", [_match(3, 4)])])
    if mutation == "outside":
        official[8, 6] = False
    elif mutation == "unknown":
        labels[8, 6] = 0
    elif mutation == "conflict":
        run92["component_assignments"]["7"] = {"status": "ABSTAIN", "reason": "seed_surface_conflict"}
    else:
        run92["component_assignments"].pop("7")
    result = fuse_sparse_documents(run91, run92, labels, official)
    assert result["accepted_sparse_correspondence_count"] == 0
    assert result["rejection_reasons"] == {reason: 1}


def test_rejected_match_and_rejected_pair_never_assign():
    pairs = [_pair("alpha", "TRAIN_CONTROL", [_match(3, 4, accepted=False)]), _pair("beta", "WITHHELD", [_match(3, 4)], status="ABSTAIN")]
    run91, run92, labels, official = _docs(pairs)
    result = fuse_sparse_documents(run91, run92, labels, official)
    assert result["accepted_sparse_correspondence_count"] == 0
    assert result["rejection_reasons"] == {"rejected_match": 1, "rejected_pair": 1}


def test_hash_tamper_fails_closed(tmp_path: Path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text("{}", encoding="utf-8")
    expected = hashlib.sha256(evidence.read_bytes()).hexdigest()
    evidence.write_text('{"tampered":true}', encoding="utf-8")
    with pytest.raises(HashDriftError):
        locked_path({"path": str(evidence), "sha256": expected}, "synthetic")


def test_deterministic_payload_hash():
    pairs = [_pair("alpha", "TRAIN_CONTROL", [_match(3, 4)]), _pair("beta", "WITHHELD", [_match(3, 4)])]
    run91, run92, labels, official = _docs(pairs)
    first = fuse_sparse_documents(run91, run92, labels, official)
    second = fuse_sparse_documents(run91, run92, labels, official)
    assert first == second
    bare = {key: value for key, value in first.items() if key != "deterministic_hash"}
    assert first["deterministic_hash"] == canonical_hash(bare)
