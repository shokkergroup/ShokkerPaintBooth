from __future__ import annotations

import json
from pathlib import Path

import pytest

from _forge_dlm_surface_evidence_maturity import (
    REQUIRED_CHECKS,
    REQUIRED_CLAIMS,
    aggregate_vote_cohorts,
    collect_active_view_evidence,
    gate_surface,
    reject_readiness_overrides,
    sha256_file,
    verify_source,
)


def _checks(*, passed: set[str] | None = None) -> list[dict[str, object]]:
    passed = passed or set()
    return [
        {
            "check_id": check_id,
            "pass": check_id in passed,
            "status": "PASS" if check_id in passed else "FAIL",
            "reason": "fixture",
            "evidence": {},
        }
        for check_id in REQUIRED_CHECKS
    ]


def test_ready_requires_every_independent_check() -> None:
    result = gate_surface(_checks(passed=set(REQUIRED_CHECKS)))
    assert result["status"] == "READY"
    assert result["ready"] is True
    assert result["passed_check_count"] == 10


def test_single_failure_cannot_be_ready() -> None:
    result = gate_surface(_checks(passed=set(REQUIRED_CHECKS[:-1])))
    assert result["status"] == "LIMITED"
    assert result["ready"] is False
    assert result["passed_check_count"] == 9


def test_no_checks_and_no_support_abstains() -> None:
    result = gate_surface(_checks(), supporting_evidence_count=0)
    assert result["status"] == "ABSTAIN"
    assert result["ready"] is False


def test_diagnostic_support_is_limited_not_ready() -> None:
    result = gate_surface(_checks(), supporting_evidence_count=1)
    assert result["status"] == "LIMITED"
    assert result["ready"] is False


@pytest.mark.parametrize(
    "rows,error",
    [
        (_checks()[:-1], "readiness_checks_incomplete"),
        (_checks() + [_checks()[0]], "duplicate_readiness_check"),
    ],
)
def test_gate_rejects_incomplete_or_duplicate_checks(rows: list[dict[str, object]], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        gate_surface(rows)


def test_vote_cohorts_are_independent_by_split() -> None:
    result = aggregate_vote_cohorts(
        [
            {"surface_id": "side", "split": "TRAIN_CONTROL", "cohort_id": "a"},
            {"surface_id": "side", "split": "TRAIN_CONTROL", "cohort_id": "a"},
            {"surface_id": "side", "split": "TRAIN_CONTROL", "cohort_id": "b"},
            {"surface_id": "side", "split": "WITHHELD", "cohort_id": "w"},
        ]
    )
    assert result["side"]["TRAIN_CONTROL"] == {
        "cohorts": ["a", "b"],
        "cohort_count": 2,
        "match_count": 3,
    }
    assert result["side"]["WITHHELD"]["cohorts"] == ["w"]


def test_active_view_binding_uses_hints_landmarks_and_physical_side() -> None:
    views = [
        {
            "source_index": 1,
            "camera_role": "left_side",
            "physical_side": "left",
            "surface_interiors": [{"surface_hint": "side_main"}],
            "landmarks": [{"type": "wheel_arch_extremum"}],
        },
        {
            "source_index": 2,
            "camera_role": "right_side",
            "physical_side": "right",
            "surface_interiors": [{"surface_hint": "side_main"}],
            "landmarks": [{"type": "wheel_arch_extremum"}],
        },
    ]
    bindings = {
        "left_side": {
            "surface_hints": ["side_main"],
            "landmark_types": [],
            "physical_sides": ["left"],
        },
        "right_fender": {
            "surface_hints": [],
            "landmark_types": ["wheel_arch_extremum"],
            "physical_sides": ["right"],
        },
        "unbound": {"surface_hints": [], "landmark_types": [], "physical_sides": []},
    }
    result = collect_active_view_evidence(views, bindings)
    assert result["left_side"]["view_count"] == 1
    assert result["left_side"]["views"][0]["source_index"] == 1
    assert result["right_fender"]["view_count"] == 1
    assert result["right_fender"]["views"][0]["source_index"] == 2
    assert result["unbound"]["view_count"] == 0


def test_readiness_overrides_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="readiness_overrides_not_disabled"):
        reject_readiness_overrides({"allow_readiness_overrides": True, "readiness_overrides": {}})
    with pytest.raises(ValueError, match="readiness_override_present"):
        reject_readiness_overrides(
            {"allow_readiness_overrides": False, "readiness_overrides": {"side": "READY"}}
        )
    reject_readiness_overrides({"allow_readiness_overrides": False, "readiness_overrides": {}})


def test_source_verification_rejects_hash_drift(tmp_path: Path) -> None:
    owner = tmp_path / "job.json"
    owner.write_text("{}\n", encoding="utf-8")
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"$schema": "fixture"}) + "\n", encoding="utf-8")
    record = {"path": "source.json", "sha256": sha256_file(source)}
    assert verify_source(owner, record, "fixture") == source.resolve()
    source.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fixture_sha256_mismatch"):
        verify_source(owner, record, "fixture")


def test_claims_are_explicitly_false_for_downstream_readiness() -> None:
    assert REQUIRED_CLAIMS == {
        "surface_maturity_ledger_only": True,
        "universal_livery_reconstruction_ready": False,
        "livery_ready": False,
        "psd_ready": False,
        "app_ready": False,
        "delivery_ready": False,
    }
