from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import uuid

import pytest

import _forge_dlm_precompile_readiness_firewall as firewall
import _forge_four_psd_delivery as flat_delivery
import _forge_reference_psd_compiler as reference_compiler


ROOT = Path(__file__).resolve().parents[1]
CURRENT_REPORT = (
    ROOT
    / "_forge_out/codex_full_uv_recovery/run_112_precompile_readiness_firewall"
    / "case_01_legacy_reference_psd_compiler_compile_case/precompile_readiness_report.json"
)


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _reference(path: Path) -> dict[str, str]:
    return {"path": path.resolve().as_posix(), "sha256": firewall.sha256_file(path)}


def _ready_payloads(candidate_id: str, candidate_sha: str) -> dict[str, dict]:
    surfaces = [
        {
            "surface_id": f"surface_{index:02d}",
            "status": "READY",
            "ready": True,
            "passed_check_count": 10,
            "required_check_count": 10,
        }
        for index in range(12)
    ]
    taxonomy_rows = {
        f"surface_{index:02d}": {"status": "READY", "ready": True}
        for index in range(13)
    }
    return {
        "surface_maturity": {
            "$schema": firewall.MATURITY_SCHEMA,
            "surface_count": 12,
            "ready_surface_count": 12,
            "surfaces": surfaces,
        },
        "side_polarity": {
            "$schema": firewall.SIDE_POLARITY_SCHEMA,
            "promotion_status": "READY",
            "claims": {
                "side_polarity_contradiction_detected": False,
                "promoted_sparse_official_side_map": True,
            },
            "metrics": {
                "target_side_unique_uv_pixel_count": 400,
                "opposite_side_unique_uv_pixel_count": 0,
            },
        },
        "front_assembly": {
            "$schema": firewall.FRONT_ASSEMBLY_SCHEMA,
            "front_assembly_polarity_ready": True,
            "front_assembly_status": "READY",
            "surface_status_counts": {"READY": 4},
        },
        "surface_taxonomy": {
            "$schema": firewall.TAXONOMY_SCHEMA,
            "readiness": {
                "ready_surface_count": 13,
                "split_child_ready_count": 2,
                "taxonomy_runtime_ready": True,
            },
            "surfaces": taxonomy_rows,
        },
        "semantic_compiler_boundary": {
            "$schema": firewall.SEMANTIC_BOUNDARY_SCHEMA,
            "status": "PASS",
            "compiler_boundary_ready": True,
            "blockers": [],
            "candidate_binding": {
                "candidate_id": candidate_id,
                "candidate_manifest_sha256": candidate_sha,
            },
        },
    }


def _build_ready_case(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, Path]]:
    source = tmp_path / "synthetic_compiler.py"
    source.write_text("def compile():\n    return None\n", encoding="utf-8")
    candidate = _write(
        tmp_path / "candidate.json",
        {"$schema": "synthetic-candidate/v1", "candidate_id": "candidate-a"},
    )
    candidate_sha = firewall.sha256_file(candidate)
    payloads = _ready_payloads("candidate-a", candidate_sha)
    evidence_paths: dict[str, Path] = {}
    for role in (
        "surface_maturity",
        "side_polarity",
        "front_assembly",
        "surface_taxonomy",
        "semantic_compiler_boundary",
    ):
        evidence_paths[role] = _write(tmp_path / f"{role}.json", payloads[role])
    taxonomy_sha = firewall.sha256_file(evidence_paths["surface_taxonomy"])
    evidence_paths["surface_taxonomy_validation"] = _write(
        tmp_path / "surface_taxonomy_validation.json",
        {
            "$schema": firewall.TAXONOMY_VALIDATION_SCHEMA,
            "status": "PASS",
            "valid": True,
            "manifest": {"sha256": taxonomy_sha},
        },
    )
    registry = _write(
        tmp_path / "registry.json",
        {
            "$schema": firewall.REGISTRY_SCHEMA,
            "entrypoint_count": 1,
            "public_compile_entrypoint_count": 1,
            "entrypoints": [
                {
                    "entrypoint_id": "synthetic.compiler.compile",
                    "module_path": source.resolve().as_posix(),
                    "source_sha256": firewall.sha256_file(source),
                    "source_present": True,
                    "symbol": "compile",
                    "kind": "PSD_WRITER",
                    "classification": "GATED_PUBLIC",
                    "public_compile_allowed": True,
                    "firewall_enforced_in_source": True,
                    "release_contract_schema": firewall.RELEASE_SCHEMA,
                }
            ],
        },
    )
    job = _write(
        tmp_path / "job.json",
        {
            "$schema": firewall.JOB_SCHEMA,
            "entrypoint_id": "synthetic.compiler.compile",
            "registry": _reference(registry),
            "candidate": {
                "candidate_id": "candidate-a",
                "manifest": _reference(candidate),
            },
            "release_contract_schema": firewall.RELEASE_SCHEMA,
            "evidence": {role: _reference(path) for role, path in evidence_paths.items()},
        },
    )
    return job, source, candidate, evidence_paths


def test_registry_classifies_known_write_and_promotion_surfaces_without_public_compiler(tmp_path: Path) -> None:
    registry = firewall.build_entrypoint_registry(ROOT, tmp_path / "registry.json")
    rows = {row["entrypoint_id"]: row for row in registry["entrypoints"]}
    assert registry["public_compile_entrypoint_count"] == 0
    assert rows["legacy.flat_delivery.compile_delivery"]["classification"] == "RETIRED"
    assert rows["legacy.reference_psd_compiler.compile_case"]["firewall_enforced_in_source"] is True
    assert rows["primitive.layer_writer.write_grouped_layered"]["classification"] == "PRIMITIVE_ONLY"
    assert rows["gate.release.evaluate_release_job"]["classification"] == "GATE_ONLY"
    assert rows["planned.universal_dlm_psd_compiler.compile"]["classification"] == "NOT_IMPLEMENTED"


def test_reusable_firewall_contains_no_livery_identity_literals() -> None:
    source = inspect.getsource(firewall).lower()
    for forbidden in ("waffle", "domino", "sex wax", "crystal lake", "miller", "mountain dew"):
        assert forbidden not in source


def test_complete_hash_bound_synthetic_contract_can_accept(tmp_path: Path) -> None:
    job, source, _candidate, _evidence = _build_ready_case(tmp_path)
    report_path = tmp_path / "report.json"
    report = firewall.evaluate_precompile_readiness(job, report_path)
    assert report["decision"] == "ACCEPT"
    assert report["precompile_ready"] is True
    assert not report["blockers"]
    firewall.assert_precompile_ready(
        report_path,
        expected_entrypoint_id="synthetic.compiler.compile",
        expected_source_path=source,
    )


def test_hand_edited_accept_report_is_recomputed_and_rejected(tmp_path: Path) -> None:
    job, source, _candidate, _evidence = _build_ready_case(tmp_path)
    report_path = tmp_path / "tampered_report.json"
    firewall.evaluate_precompile_readiness(job, report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["claims"]["app_ready"] = True
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with pytest.raises(firewall.PrecompileReadinessBlocked, match="report_drift"):
        firewall.assert_precompile_ready(
            report_path,
            expected_entrypoint_id="synthetic.compiler.compile",
            expected_source_path=source,
        )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("evidence_only", "evidence_only_forbidden"),
        ("revoked", "revoked"),
        ("false_readiness", "surface_maturity:not_ready"),
        ("side_contradiction", "side_polarity:contradiction"),
        ("missing", "front_assembly:missing"),
        ("hash_mismatch", "front_assembly:sha256_mismatch"),
        ("release_v1", "release_contract:v1_or_missing_forbidden"),
    ],
)
def test_fail_closed_mutations_never_accept(tmp_path: Path, mutation: str, expected: str) -> None:
    job_path, _source, _candidate, evidence_paths = _build_ready_case(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if mutation == "evidence_only":
        payload = json.loads(evidence_paths["front_assembly"].read_text(encoding="utf-8"))
        payload["evidence_only"] = True
        _write(evidence_paths["front_assembly"], payload)
        job["evidence"]["front_assembly"] = _reference(evidence_paths["front_assembly"])
    elif mutation == "revoked":
        payload = json.loads(evidence_paths["front_assembly"].read_text(encoding="utf-8"))
        payload["revoked"] = True
        _write(evidence_paths["front_assembly"], payload)
        job["evidence"]["front_assembly"] = _reference(evidence_paths["front_assembly"])
    elif mutation == "false_readiness":
        payload = json.loads(evidence_paths["surface_maturity"].read_text(encoding="utf-8"))
        payload["ready_surface_count"] = 0
        payload["surfaces"][0]["ready"] = False
        payload["surfaces"][0]["status"] = "LIMITED"
        _write(evidence_paths["surface_maturity"], payload)
        job["evidence"]["surface_maturity"] = _reference(evidence_paths["surface_maturity"])
    elif mutation == "side_contradiction":
        payload = json.loads(evidence_paths["side_polarity"].read_text(encoding="utf-8"))
        payload["claims"]["side_polarity_contradiction_detected"] = True
        payload["metrics"]["opposite_side_unique_uv_pixel_count"] = 50
        _write(evidence_paths["side_polarity"], payload)
        job["evidence"]["side_polarity"] = _reference(evidence_paths["side_polarity"])
    elif mutation == "missing":
        job["evidence"].pop("front_assembly")
    elif mutation == "hash_mismatch":
        job["evidence"]["front_assembly"]["sha256"] = "0" * 64
    elif mutation == "release_v1":
        job["release_contract_schema"] = "shokk-forge.dlm-release-report/v1"
    _write(job_path, job)
    report = firewall.evaluate_precompile_readiness(job_path, tmp_path / "report.json")
    assert report["decision"] != "ACCEPT"
    assert report["precompile_ready"] is False
    assert any(expected in blocker for blocker in report["blockers"])


def test_stale_evidence_after_accept_cannot_bypass_assertion(tmp_path: Path) -> None:
    job, source, _candidate, evidence = _build_ready_case(tmp_path)
    report_path = tmp_path / "report.json"
    assert firewall.evaluate_precompile_readiness(job, report_path)["decision"] == "ACCEPT"
    payload = json.loads(evidence["front_assembly"].read_text(encoding="utf-8"))
    payload["note"] = "changed after acceptance"
    _write(evidence["front_assembly"], payload)
    with pytest.raises(firewall.PrecompileReadinessBlocked, match="sha256_mismatch"):
        firewall.assert_precompile_ready(
            report_path,
            expected_entrypoint_id="synthetic.compiler.compile",
            expected_source_path=source,
        )


def test_current_hash_bound_evidence_rejects_or_abstains_without_claim(tmp_path: Path) -> None:
    audit = firewall.build_current_audit(ROOT, tmp_path / "run112")
    assert audit["current_compile_ready"] is False
    assert audit["current_decision_counts"]["ACCEPT"] == 0
    assert "side_polarity:contradiction" in audit["blockers"]
    assert "surface_maturity:not_ready:0/12" in audit["blockers"]
    assert "front_assembly:not_ready" in audit["blockers"]
    assert "surface_taxonomy:not_runtime_ready:0/13" in audit["blockers"]
    assert audit["claims"]["livery_ready"] is False
    assert audit["claims"]["psd_ready"] is False


def test_retired_flat_delivery_blocks_before_output_mutation(tmp_path: Path) -> None:
    output = tmp_path / f"run112_flat_must_not_exist_{uuid.uuid4().hex}"
    with pytest.raises(firewall.PrecompileReadinessBlocked):
        flat_delivery.compile_delivery(
            ROOT / "not_loaded.json",
            output,
            ROOT,
            snapshot_label="blocked-regression",
            precompile_readiness_report=CURRENT_REPORT,
        )
    assert not output.exists()


def test_retired_reference_compiler_blocks_before_output_mutation(tmp_path: Path) -> None:
    output = tmp_path / f"run112_reference_must_not_exist_{uuid.uuid4().hex}"
    with pytest.raises(firewall.PrecompileReadinessBlocked):
        reference_compiler.compile_case(
            "blocked-regression",
            tmp_path / "case-not-read",
            tmp_path / "guides-not-read",
            output,
            CURRENT_REPORT,
        )
    assert not output.exists()


def test_missing_report_blocks_both_legacy_writers_before_output_mutation(tmp_path: Path) -> None:
    first = tmp_path / f"run112_missing_first_{uuid.uuid4().hex}"
    second = tmp_path / f"run112_missing_second_{uuid.uuid4().hex}"
    with pytest.raises(firewall.PrecompileReadinessBlocked, match="required"):
        flat_delivery.compile_delivery(
            ROOT / "not_loaded.json",
            first,
            ROOT,
            snapshot_label="blocked-regression",
        )
    with pytest.raises(firewall.PrecompileReadinessBlocked, match="required"):
        reference_compiler.compile_case("blocked", tmp_path, tmp_path, second)
    assert not first.exists()
    assert not second.exists()
