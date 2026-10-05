from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import pytest

import _forge_dlm_release_gate as gate


NOW = datetime(2026, 7, 17, 20, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(value: datetime = NOW) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _fixture(tmp_path: Path, *, mode: str = "synthetic_contract_proof") -> dict[str, Any]:
    root = tmp_path / f"release_{uuid4().hex}"
    root.mkdir(parents=True)
    artifact_dir = root / "candidate"
    report_dir = root / "evidence"
    artifact_dir.mkdir()
    report_dir.mkdir()
    artifacts: dict[str, dict[str, str]] = {}
    hashes: dict[str, str] = {}
    for index, key in enumerate(gate.REQUIRED_ARTIFACTS):
        path = artifact_dir / f"{key}.bin"
        path.write_bytes((f"synthetic-{key}-{index}\n" * (index + 1)).encode("utf-8"))
        digest = gate.sha256_file(path)
        artifacts[key] = {"path": str(path), "sha256": digest}
        hashes[key] = digest
    fingerprint = gate.candidate_fingerprint(hashes)
    candidate_id = "synthetic.release.contract"
    semantic_job_sha = "c" * 64

    reports: dict[str, dict[str, Any]] = {
        "calibrated_adapter": {
            "$schema": gate.PHYSICAL_SCHEMA,
            "livery_neutral": True,
            "threshold_profile": "production_locked",
            "physical_adapter_ready": True,
            "readiness_checks": {"coverage": True, "orientation": True, "ownership": True},
        },
        "semantic_instances": {
            "$schema": gate.SEMANTIC_SCHEMA,
            "semantic_instance_ready": True,
            "threshold_profile": "production_locked",
            "masters": [{"id": "master-1", "ready": True}],
            "instances": [{"id": "instance-1", "ready": True}],
            "job": {"path": "semantic_job.json", "sha256": semantic_job_sha},
        },
        "semantic_compiler_boundary": {
            "$schema": gate.SEMANTIC_COMPILER_SCHEMA,
            "status": "PASS",
            "compiler_boundary_ready": True,
            "semantic_instance_ready": True,
            "lineage_present": True,
            "lineage_sha256": "d" * 64,
            "lineage_blockers": [],
            "blockers": [],
            "semantic_instance_job": {"path": "semantic_job.json", "sha256": semantic_job_sha},
            "semantic_gate_report": {
                "$schema": gate.SEMANTIC_SCHEMA,
                "semantic_instance_ready": True,
                "threshold_profile": "production_locked",
            },
            "claims": {
                "semantic_compiler_boundary_only": True,
                "livery_ready": False,
                "psd_ready": False,
                "app_ready": False,
                "delivery_ready": False,
            },
        },
        "flat_visual_sanity": {
            "$schema": gate.FLAT_VISUAL_SCHEMA,
            "status": "pass",
            "valid": True,
            "candidate": {"sha256": hashes["composite"]},
            "claims": {"promotion_ready": True},
            "failures": [],
            "insufficient_evidence": [],
            "visual_review": {"valid": True, "reviewer": "named-flat-reviewer"},
        },
        "topology_completeness": {
            "$schema": gate.TOPOLOGY_SCHEMA,
            "status": "PASS",
            "topology_complete": True,
            "failures": [],
            "insufficient_evidence": [],
            "unsafe_test_mode": False,
            "thresholds": copy.deepcopy(gate.TOPOLOGY_PRODUCTION_THRESHOLDS),
            "candidate_flat": {"sha256": hashes["composite"]},
            "psd": {"sha256": hashes["psd"]},
            "official_mask": {"sha256": "a" * 64},
            "topology_labels": {"sha256": "b" * 64},
            "coverage": {
                "official_utilization": 0.99,
                "outside_official_fraction": 0.0005,
                "largest_uncovered_fraction": 0.004,
            },
            "component_summary": {"missing_major_component_count": 0},
        },
        "promotion_gate": {
            "$schema": gate.PROMOTION_SCHEMA,
            "valid": True,
            "decision": "accept",
            "blocker_count": 0,
            "candidate_id": candidate_id,
            "gates": {
                "artifacts": {
                    "files": {key: {"sha256": digest} for key, digest in hashes.items()},
                }
            },
        },
        "owner_render_gate": {
            "$schema": gate.OWNER_RENDER_SCHEMA,
            "manifest_valid": True,
            "candidate_accepted": True,
            "decision": "accept",
            "candidate_id": candidate_id,
            "errors": [],
            "missing_accept_roles": [],
            "sim_view_role_count": 5,
        },
        "psd_source_recomposition": {
            "$schema": gate.PSD_SUMMARY_SCHEMA,
            "candidate_artifact_sha256": copy.deepcopy(hashes),
            "canvas": [2048, 2048],
            "psd_valid": True,
            "recomposition_exact": True,
            "editable_recomposition_differing_pixels": 0,
            "preview_recomposition_differing_pixels": 0,
            "mandatory_contamination_pixels": 0,
            "mirrored_text_count": 0,
            "duplicate_physical_art_count": 0,
            "missing_major_object_count": 0,
            "clipped_readable_object_count": 0,
            "semantic_groups": list(gate.REQUIRED_GROUPS),
            "source_purity": {
                "valid": True,
                "enforce_delivery_source_purity": True,
                "assembled_vehicle_source_count": 0,
                "assembled_vehicle_thumbnail_count": 0,
                "issue_count": 0,
            },
        },
        "named_visual_review": {
            "$schema": gate.REVIEW_SCHEMA,
            "candidate_artifact_sha256": copy.deepcopy(hashes),
            "decision": "accept",
            "reviewer_kind": "agent_visual",
            "reviewer": "named-release-reviewer",
            "reviewed_at": _iso(),
            "checks": {key: True for key in gate.REQUIRED_REVIEW_CHECKS},
            "blockers": [],
        },
    }
    evidence: dict[str, dict[str, str]] = {}
    report_paths: dict[str, Path] = {}
    for key, payload in reports.items():
        path = report_dir / f"{key}.json"
        _write_json(path, payload)
        report_paths[key] = path
        evidence[key] = {
            "path": str(path),
            "sha256": gate.sha256_file(path),
            "candidate_fingerprint": fingerprint,
            "attested_at": _iso(),
        }
    job = {
        "$schema": gate.JOB_SCHEMA,
        "candidate_id": candidate_id,
        "candidate_fingerprint": fingerprint,
        "evidence_mode": mode,
        "artifacts": artifacts,
        "evidence": evidence,
    }
    job_path = root / "release_job.json"
    _write_json(job_path, job)
    return {
        "job": job,
        "job_path": job_path,
        "hashes": hashes,
        "fingerprint": fingerprint,
        "reports": reports,
        "report_paths": report_paths,
    }


def _rewrite_job(fixture: dict[str, Any]) -> None:
    _write_json(fixture["job_path"], fixture["job"])


def _mutate_report(
    fixture: dict[str, Any],
    key: str,
    mutate: Callable[[dict[str, Any]], None],
    *,
    refresh_attested_hash: bool = True,
) -> None:
    payload = fixture["reports"][key]
    mutate(payload)
    path = fixture["report_paths"][key]
    _write_json(path, payload)
    if refresh_attested_hash:
        fixture["job"]["evidence"][key]["sha256"] = gate.sha256_file(path)
        _rewrite_job(fixture)


def test_synthetic_contract_pass_never_makes_delivery_claims(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    report = gate.evaluate_release_job(fixture["job_path"], tmp_path / "out", now=NOW)
    assert report["contract_valid"] is True
    assert report["release_ready"] is False
    assert report["decision"] == "synthetic_contract_pass"
    assert report["blockers"] == []
    assert report["claims"] == {
        "livery_ready": False,
        "psd_ready": False,
        "delivery_ready": False,
        "owner_sim_accepted": False,
    }
    assert all(row["passed"] is True for row in report["evidence"].values())
    assert (tmp_path / "out" / "DLM_RELEASE_GATE_QA.png").is_file()
    assert (tmp_path / "out" / "dlm_release_gate.json").is_file()


def test_production_mode_maps_contract_pass_to_release(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, mode="production_candidate")
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is True
    assert report["release_ready"] is True
    assert report["decision"] == "accept"
    assert all(report["claims"].values())


@pytest.mark.parametrize(
    ("key", "mutate", "error_fragment"),
    [
        ("calibrated_adapter", lambda value: value.__setitem__("physical_adapter_ready", False), "physical_adapter_not_ready"),
        ("semantic_instances", lambda value: value["instances"][0].__setitem__("ready", False), "semantic_instance_not_ready"),
        ("semantic_compiler_boundary", lambda value: value.__setitem__("status", "REJECT"), "semantic_compiler_boundary_not_ready"),
        ("flat_visual_sanity", lambda value: value.__setitem__("status", "reject"), "actual_flat_visual_not_pass"),
        (
            "topology_completeness",
            lambda value: value["coverage"].__setitem__("official_utilization", 0.75),
            "topology_official_utilization_below_0.985",
        ),
        ("promotion_gate", lambda value: value.__setitem__("decision", "reject"), "promotion_gate_not_accept"),
        ("owner_render_gate", lambda value: value.__setitem__("sim_view_role_count", 4), "owner_render_five_direct_views_required"),
        (
            "psd_source_recomposition",
            lambda value: value["source_purity"].__setitem__("assembled_vehicle_source_count", 1),
            "source_purity_assembled_vehicle_source_count_invalid",
        ),
        (
            "named_visual_review",
            lambda value: value["checks"].__setitem__("front_single_assembly", False),
            "release_visual_checks_failed",
        ),
    ],
)
def test_each_independent_gate_fails_closed(
    tmp_path: Path,
    key: str,
    mutate: Callable[[dict[str, Any]], None],
    error_fragment: str,
) -> None:
    fixture = _fixture(tmp_path)
    _mutate_report(fixture, key, mutate)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert report["release_ready"] is False
    assert report["decision"] == "reject"
    assert report["evidence"][key]["passed"] is False
    assert any(error_fragment in error for error in report["evidence"][key]["errors"])
    assert not any(report["claims"].values())


def test_changed_candidate_artifact_rejects_hash_and_fingerprint(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    composite = Path(fixture["job"]["artifacts"]["composite"]["path"])
    composite.write_bytes(composite.read_bytes() + b"changed")
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "artifacts:composite:sha256_mismatch" in report["blockers"]
    assert "candidate_fingerprint:mismatch" in report["blockers"]


def test_changed_evidence_report_rejects_stale_attested_hash(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _mutate_report(
        fixture,
        "flat_visual_sanity",
        lambda value: value.__setitem__("unattested_change", True),
        refresh_attested_hash=False,
    )
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "report_sha256_mismatch" in report["evidence"]["flat_visual_sanity"]["errors"]


def test_evidence_candidate_fingerprint_mismatch_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["job"]["evidence"]["semantic_instances"]["candidate_fingerprint"] = "0" * 64
    _rewrite_job(fixture)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "attestation_candidate_fingerprint_mismatch" in report["evidence"]["semantic_instances"]["errors"]


def test_semantic_compiler_must_bind_same_semantic_job(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _mutate_report(
        fixture,
        "semantic_compiler_boundary",
        lambda value: value["semantic_instance_job"].__setitem__("sha256", "e" * 64),
    )
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "semantic_compiler_cross_report_job_sha256_mismatch" in report["evidence"]["semantic_compiler_boundary"]["errors"]


def test_stale_attestation_and_stale_named_review_reject(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["job"]["evidence"]["promotion_gate"]["attested_at"] = _iso(
        NOW - timedelta(seconds=gate.MAX_ATTESTATION_AGE_SECONDS + 1)
    )
    _rewrite_job(fixture)
    _mutate_report(
        fixture,
        "named_visual_review",
        lambda value: value.__setitem__(
            "reviewed_at", _iso(NOW - timedelta(seconds=gate.MAX_REVIEW_AGE_SECONDS + 1))
        ),
    )
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert any("stale" in value for value in report["evidence"]["promotion_gate"]["errors"])
    assert any("stale" in value for value in report["evidence"]["named_visual_review"]["errors"])


@pytest.mark.parametrize("field", ["thresholds", "threshold_overrides"])
def test_caller_thresholds_are_forbidden(tmp_path: Path, field: str) -> None:
    fixture = _fixture(tmp_path)
    fixture["job"][field] = {"minimum": -999}
    _rewrite_job(fixture)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "job:caller_thresholds_forbidden" in report["blockers"]


def test_missing_evidence_exact_set_rejects(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    del fixture["job"]["evidence"]["owner_render_gate"]
    _rewrite_job(fixture)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "evidence:exact_required_set" in report["blockers"]


def test_flat_and_promotion_internal_candidate_hashes_are_bound(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _mutate_report(
        fixture,
        "flat_visual_sanity",
        lambda value: value["candidate"].__setitem__("sha256", "1" * 64),
    )
    _mutate_report(
        fixture,
        "promotion_gate",
        lambda value: value["gates"]["artifacts"]["files"]["psd"].__setitem__("sha256", "2" * 64),
    )
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "flat_visual_candidate_hash_mismatch" in report["evidence"]["flat_visual_sanity"]["errors"]
    assert "promotion_psd_hash_mismatch" in report["evidence"]["promotion_gate"]["errors"]


def test_topology_requires_locked_thresholds_bound_artifacts_and_complete_islands(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        payload["thresholds"]["minimum_official_utilization"] = 0.5
        payload["psd"]["sha256"] = "4" * 64
        payload["official_mask"]["sha256"] = ""
        payload["coverage"]["outside_official_fraction"] = 0.2
        payload["coverage"]["largest_uncovered_fraction"] = 0.2
        payload["component_summary"]["missing_major_component_count"] = 1

    _mutate_report(fixture, "topology_completeness", mutate)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    errors = report["evidence"]["topology_completeness"]["errors"]
    assert report["contract_valid"] is False
    assert "topology_thresholds_not_production_locked" in errors
    assert "topology_psd_hash_mismatch" in errors
    assert "topology_official_mask_hash_missing" in errors
    assert "topology_outside_official_fraction_above_0.001" in errors
    assert "topology_largest_uncovered_fraction_above_0.008" in errors
    assert "topology_missing_major_component_count_not_zero" in errors


def test_psd_summary_requires_exact_binding_and_zero_recomposition_drift(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def mutate(payload: dict[str, Any]) -> None:
        payload["candidate_artifact_sha256"]["tga"] = "3" * 64
        payload["editable_recomposition_differing_pixels"] = 1

    _mutate_report(fixture, "psd_source_recomposition", mutate)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    errors = report["evidence"]["psd_source_recomposition"]["errors"]
    assert report["contract_valid"] is False
    assert "psd_summary:candidate_tga_sha256_mismatch" in errors
    assert "editable_recomposition_differing_pixels_must_be_zero" in errors


def test_malformed_semantic_rows_and_unsafe_adapter_thresholds_reject(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _mutate_report(
        fixture,
        "calibrated_adapter",
        lambda value: value.__setitem__("threshold_profile", "unsafe_test_only"),
    )
    _mutate_report(
        fixture,
        "semantic_instances",
        lambda value: value.__setitem__("masters", ["not-an-object"]),
    )
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "physical_threshold_profile_not_production_locked" in report["evidence"]["calibrated_adapter"]["errors"]
    assert "semantic_master_not_ready" in report["evidence"]["semantic_instances"]["errors"]


def test_nonfinite_topology_metrics_and_boolean_psd_counts_reject(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _mutate_report(
        fixture,
        "topology_completeness",
        lambda value: value["coverage"].__setitem__("official_utilization", float("nan")),
    )

    def break_psd_types(payload: dict[str, Any]) -> None:
        payload["editable_recomposition_differing_pixels"] = False
        payload["source_purity"]["assembled_vehicle_source_count"] = False

    _mutate_report(fixture, "psd_source_recomposition", break_psd_types)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert "topology_official_utilization_below_0.985" in report["evidence"]["topology_completeness"]["errors"]
    psd_errors = report["evidence"]["psd_source_recomposition"]["errors"]
    assert "editable_recomposition_differing_pixels_must_be_zero" in psd_errors
    assert "source_purity_assembled_vehicle_source_count_invalid" in psd_errors


@pytest.mark.parametrize(
    ("key", "mutate"),
    [
        ("flat_visual_sanity", lambda value: value.__setitem__("claims", None)),
        ("semantic_compiler_boundary", lambda value: value.__setitem__("semantic_gate_report", None)),
        ("topology_completeness", lambda value: value.__setitem__("coverage", "malformed")),
        ("promotion_gate", lambda value: value.__setitem__("blocker_count", "zero")),
        ("owner_render_gate", lambda value: value.__setitem__("sim_view_role_count", "five")),
    ],
)
def test_malformed_nested_reports_reject_instead_of_crashing(
    tmp_path: Path,
    key: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    fixture = _fixture(tmp_path)
    _mutate_report(fixture, key, mutate)
    report = gate.evaluate_release_job(fixture["job_path"], now=NOW)
    assert report["contract_valid"] is False
    assert report["release_ready"] is False
    assert report["evidence"][key]["passed"] is False
    assert report["evidence"][key]["errors"]


def test_release_gate_contains_no_known_livery_identity_or_per_car_geometry_branches() -> None:
    source = Path(gate.__file__).read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal lake", "sex wax", "mountain dew", "spider-man", "miller"):
        assert forbidden not in source
    assert "per_car" not in source
    assert "bbox" not in source
