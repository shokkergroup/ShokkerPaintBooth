from __future__ import annotations

import json
from pathlib import Path

import pytest

from _forge_dlm_calibration_completeness_gate import (
    CAPTURE_MANIFEST_SCHEMA,
    EXPECTED_COMPONENTS,
    EXPECTED_OFFICIAL_PIXELS,
    JOB_SCHEMA,
    REQUIRED_CAPTURE_ROLES,
    evaluate,
    sha256_file,
)
from _forge_dlm_full_topology_calibration_kit_v2 import build as build_full_topology


ROOT = Path(__file__).resolve().parents[1]
RUN110 = ROOT / "_forge_out/codex_full_uv_recovery/run_110_surface_id_calibration_kit"
RUN70 = ROOT / "_forge_out/codex_full_uv_recovery/run_70_v7_exact_topology"
RUN02 = ROOT / "_forge_out/codex_full_uv_recovery/run_02_official_template_authority"
RUN113_JOB = ROOT / "_forge_data/dlm_full_topology_calibration_kit_v2/run113_job.json"
CAPTURE_MANIFEST = ROOT / "_forge_data/dlm_calibration_completeness_gate/physical_capture_role_manifest.json"


def _ref(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": sha256_file(path)}


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _job_for_bundle(bundle: Path, job_path: Path, capture: Path = CAPTURE_MANIFEST) -> Path:
    job = {
        "$schema": JOB_SCHEMA,
        "job_id": "test-full-topology",
        "workspace_root": str(ROOT),
        "bundle": {
            "report": _ref(bundle / "FULL_TOPOLOGY_CALIBRATION_KIT_V2_REPORT.json"),
            "decoder": _ref(bundle / "FULL_TOPOLOGY_COMPONENT_DECODER_V2.json"),
            "inventory": _ref(RUN70 / "dlm_exact_topology_inventory.json"),
            "labels": _ref(RUN70 / "dlm_exact_topology_labels.png"),
            "alpha": _ref(bundle / "DLM_FULL_TOPOLOGY_CALIBRATION_ALPHA_V2.png"),
            "official_mask": _ref(RUN02 / "official_coverage_mask.png"),
        },
        "capture_manifest": _ref(capture),
    }
    return _write_json(job_path, job)


@pytest.fixture(scope="module")
def full_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("run113_full_topology")
    build_full_topology(RUN113_JOB, output)
    return output


def test_run110_partial_bundle_is_rejected_with_exact_observed_metrics(tmp_path: Path) -> None:
    job = {
        "$schema": JOB_SCHEMA,
        "job_id": "test-run110-partial",
        "workspace_root": str(ROOT),
        "bundle": {
            "report": _ref(RUN110 / "SURFACE_ID_CALIBRATION_KIT_REPORT.json"),
            "decoder": _ref(RUN110 / "COMPONENT_DECODER.json"),
            "inventory": _ref(RUN70 / "dlm_exact_topology_inventory.json"),
            "labels": _ref(RUN70 / "dlm_exact_topology_labels.png"),
            "alpha": _ref(RUN110 / "DLM_SURFACE_ID_CALIBRATION_ALPHA.png"),
            "official_mask": _ref(RUN02 / "official_coverage_mask.png"),
        },
        "capture_manifest": _ref(CAPTURE_MANIFEST),
    }
    report = evaluate(_write_json(tmp_path / "job.json", job), tmp_path / "out")

    assert report["decision"] == "REJECT_TOPOLOGY_INCOMPLETE"
    assert report["topology"]["complete"] is False
    metrics = report["topology"]["metrics"]
    assert metrics["alpha_pixels"] == 733_220
    assert metrics["decoder_component_count"] == 289
    assert metrics["expected_official_pixels"] == EXPECTED_OFFICIAL_PIXELS
    assert metrics["expected_component_count"] == EXPECTED_COMPONENTS
    assert "alpha_official_coverage_incomplete" in report["topology"]["failures"]
    assert "decoder_component_count_not_565" in report["topology"]["failures"]


def test_full_topology_passes_but_remains_not_captured_and_not_delivery(
    full_bundle: Path, tmp_path: Path
) -> None:
    report = evaluate(
        _job_for_bundle(full_bundle, tmp_path / "job.json"), tmp_path / "out"
    )

    assert report["decision"] == "PASS_TOPOLOGY_COMPLETE_NOT_CAPTURED_NOT_DELIVERY"
    assert report["topology"]["status"] == "PASS"
    assert report["capture"]["status"] == "NOT_CAPTURED"
    assert report["delivery_status"] == "NOT_DELIVERY"
    metrics = report["topology"]["metrics"]
    assert metrics["official_pixels"] == EXPECTED_OFFICIAL_PIXELS
    assert metrics["alpha_pixels"] == EXPECTED_OFFICIAL_PIXELS
    assert metrics["inventory_component_count"] == EXPECTED_COMPONENTS
    assert metrics["decoder_component_count"] == EXPECTED_COMPONENTS
    assert metrics["unique_decoder_token_count"] == EXPECTED_COMPONENTS
    assert metrics["token_mismatch_count"] == 0
    assert metrics["duplicate_token_count"] == 0
    assert report["claims"]["projector"] is False
    assert report["claims"]["delivery"] is False


def test_full_capture_role_manifest_requires_all_independent_wire_pairs() -> None:
    manifest = json.loads(CAPTURE_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["$schema"] == CAPTURE_MANIFEST_SCHEMA
    roles = {item["role_id"]: item for item in manifest["roles"]}
    assert set(roles) == set(REQUIRED_CAPTURE_ROLES)
    assert len(roles) == 13
    for role in roles.values():
        assert set(role["states"]) == {"wire_off", "wire_on"}
        assert role["states"]["wire_off"] == {"path": None, "sha256": None}
        assert role["states"]["wire_on"] == {"path": None, "sha256": None}


def test_decoder_physical_surface_truth_is_rejected(
    full_bundle: Path, tmp_path: Path
) -> None:
    decoder = json.loads(
        (full_bundle / "FULL_TOPOLOGY_COMPONENT_DECODER_V2.json").read_text(
            encoding="utf-8"
        )
    )
    decoder["components"][0]["physical_surface"] = "left_side"
    contaminated = _write_json(tmp_path / "decoder.json", decoder)
    job_path = _job_for_bundle(full_bundle, tmp_path / "job.json")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job["bundle"]["decoder"] = _ref(contaminated)
    _write_json(job_path, job)

    report = evaluate(job_path, tmp_path / "out")

    assert report["decision"] == "REJECT_TOPOLOGY_INCOMPLETE"
    assert "decoder_contains_physical_or_delivery_truth" in report["topology"]["failures"]
    assert report["topology"]["forbidden_decoder_truths"] == [
        "components[0].physical_surface"
    ]


def test_duplicate_capture_hash_is_detected_without_promoting_delivery(
    full_bundle: Path, tmp_path: Path
) -> None:
    frame = tmp_path / "same-frame.png"
    frame.write_bytes(b"not-a-real-capture-but-hash-bound")
    manifest = json.loads(CAPTURE_MANIFEST.read_text(encoding="utf-8"))
    for role in manifest["roles"]:
        for state in role["states"].values():
            state.update(_ref(frame))
    capture = _write_json(tmp_path / "capture.json", manifest)

    report = evaluate(
        _job_for_bundle(full_bundle, tmp_path / "job.json", capture),
        tmp_path / "out",
    )

    assert report["topology"]["status"] == "PASS"
    assert report["capture"]["captured"] is False
    assert report["capture"]["metrics"]["supplied_frame_count"] == 26
    assert report["capture"]["metrics"]["duplicate_frame_hash_count"] == 25
    assert "duplicate_capture_frame_hash" in report["capture"]["failures"]
    assert report["delivery_status"] == "NOT_DELIVERY"


def test_proof_hash_is_deterministic_for_identical_bound_inputs(
    full_bundle: Path, tmp_path: Path
) -> None:
    job_path = _job_for_bundle(full_bundle, tmp_path / "job.json")
    first = evaluate(job_path, tmp_path / "out-a")
    second = evaluate(job_path, tmp_path / "out-b")
    assert first["proof_sha256"] == second["proof_sha256"]

