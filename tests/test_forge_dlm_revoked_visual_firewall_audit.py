from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from _forge_dlm_revoked_visual_firewall_audit import (
    REQUIRED_CLAIMS,
    create_synthetic_known_good,
    failure_categories,
    validate_owner_pointer,
    verify_bound_file,
)
from _forge_dlm_visual_sanity_gate import evaluate_job


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_bound_file_rejects_hash_drift(tmp_path: Path) -> None:
    owner = tmp_path / "job.json"
    owner.write_text("{}\n", encoding="utf-8")
    source = tmp_path / "candidate.png"
    source.write_bytes(b"candidate")
    record = {"path": source.name, "sha256": _sha(source)}
    assert verify_bound_file(owner, record, "candidate") == source.resolve()
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="candidate_sha256_mismatch"):
        verify_bound_file(owner, record, "candidate")


def test_pointer_status_and_reason_are_fail_closed(tmp_path: Path) -> None:
    pointer = tmp_path / "pointer.json"
    pointer.write_text(
        json.dumps(
            {
                "$schema": "shokk-forge.current-best-pointer/v1",
                "status": "revoked_by_owner",
                "revoked_on": "2026-07-16",
                "revocation_reason": "visible contradiction",
            }
        ),
        encoding="utf-8",
    )
    payload = validate_owner_pointer(
        pointer, expected_status="revoked_by_owner", candidate_id="fixture"
    )
    assert payload["revocation_reason"] == "visible contradiction"
    with pytest.raises(ValueError, match="fixture_pointer_status_mismatch"):
        validate_owner_pointer(pointer, expected_status="approved", candidate_id="fixture")


def test_failure_categories_preserve_measured_and_missing_truth() -> None:
    report = {
        "failures": [
            "coverage: official utilization 0.8 below 0.9",
            "coverage: outside-official paint 0.2 exceeds 0.1",
            "coverage: largest unintended blank 0.2 exceeds 0.1",
            "visual_review: current candidate was not visually accepted",
        ],
        "insufficient_evidence": [
            "semantic_art_mask: required evidence is missing",
            "semantic_object_labels: required evidence is missing",
            "evidence.wire_qa: required evidence is missing",
        ],
    }
    assert set(failure_categories(report)) == {
        "coverage_utilization",
        "outside_official",
        "largest_blank",
        "owner_rejection_review",
        "exact_semantic_truth_missing",
        "required_visual_evidence_missing",
    }


def test_synthetic_known_good_passes_existing_production_gate(tmp_path: Path) -> None:
    job = create_synthetic_known_good(tmp_path / "inputs")
    report = evaluate_job(job, tmp_path / "proof")
    assert report["status"] == "pass"
    assert report["valid"] is True
    assert report["failures"] == []
    assert report["insufficient_evidence"] == []
    assert report["metrics"]["coverage"]["official_utilization"] == 1.0
    assert report["metrics"]["coverage"]["outside_official_paint_pixels"] == 0


def test_downstream_claims_remain_false() -> None:
    assert REQUIRED_CLAIMS == {
        "cross_candidate_visual_firewall_audit_only": True,
        "livery_ready": False,
        "psd_ready": False,
        "app_ready": False,
        "delivery_ready": False,
        "owner_holdout_passed": False,
    }


def test_reusable_module_has_no_candidate_identity_literals() -> None:
    source = (Path(__file__).resolve().parents[1] / "_forge_dlm_revoked_visual_firewall_audit.py").read_text(
        encoding="utf-8"
    ).lower()
    for forbidden in ("waffle_house", "crystal_lake", "dominos", "sex_wax"):
        assert forbidden not in source
