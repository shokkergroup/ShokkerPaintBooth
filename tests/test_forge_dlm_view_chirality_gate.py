from __future__ import annotations

import json
from pathlib import Path

import pytest

from _forge_dlm_view_chirality_gate import (
    ViewChiralityError,
    analyze_mapping,
    build,
    synthetic_samples,
)

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data/dlm_view_chirality_gate/run134_job.json"
RUN133_SYNTHETIC = ROOT / "_forge_out/codex_full_uv_recovery/run_133_chiral_decode_gate/SYNTHETIC_CHIRAL_DECODE_AB_REPORT.json"
THRESHOLDS = json.loads(JOB.read_text(encoding="utf-8"))["jacobian_thresholds"]


def test_run133_exports_explicit_native_uv_to_screen_correspondences():
    report = json.loads(RUN133_SYNTHETIC.read_text(encoding="utf-8"))
    clean = report["scenarios"][0]
    rows = clean["decoded_uv_screen_samples"]
    assert len(rows) == 1024
    assert {"screen_x", "screen_y", "native_u", "native_v", "confidence", "orientation_residual_normalized"} <= set(rows[0])


def test_consistent_positive_and_negative_mappings_pass_their_witness():
    positive = analyze_mapping(synthetic_samples("valid_positive_nonlinear"), THRESHOLDS, "positive")
    negative = analyze_mapping(synthetic_samples("valid_negative_nonlinear"), THRESHOLDS, "negative")
    assert positive["accepted"] is True
    assert positive["dominant_orientation_sign"] == "positive"
    assert negative["accepted"] is True
    assert negative["dominant_orientation_sign"] == "negative"


def test_consistent_negative_mapping_is_not_intrinsically_invalid():
    result = analyze_mapping(synthetic_samples("valid_negative_nonlinear"), THRESHOLDS, "negative")
    assert result["valid_local_fraction"] == pytest.approx(1.0)
    assert result["dominant_orientation_fraction"] == pytest.approx(1.0)
    assert "VIEW_CHIRALITY_UNEXPECTED_REFLECTION" not in result["reasons"]


def test_declared_positive_witness_rejects_reflected_mapping():
    result = analyze_mapping(synthetic_samples("unexpected_reflection"), THRESHOLDS, "positive")
    assert result["accepted"] is False
    assert result["dominant_orientation_sign"] == "negative"
    assert "VIEW_CHIRALITY_UNEXPECTED_REFLECTION" in result["reasons"]


def test_foldover_rejects_mixed_local_jacobian_signs():
    result = analyze_mapping(synthetic_samples("foldover"), THRESHOLDS, "positive")
    assert result["accepted"] is False
    assert result["foldover_fraction"] > 0.02
    assert "VIEW_CHIRALITY_FOLDOVER_OR_MIXED_ORIENTATION" in result["reasons"]


def test_axis_collapse_rejects_before_projector():
    result = analyze_mapping(synthetic_samples("axis_collapse"), THRESHOLDS, "positive")
    assert result["accepted"] is False
    assert "VIEW_CHIRALITY_SCREEN_AXIS_COLLAPSE" in result["reasons"]
    assert "VIEW_CHIRALITY_VALID_JACOBIAN_COVERAGE_TOO_LOW" in result["reasons"]


def test_sparse_correspondence_rejects():
    result = analyze_mapping(synthetic_samples("sparse"), THRESHOLDS, "positive")
    assert result["accepted"] is False
    assert "VIEW_CHIRALITY_SAMPLE_COUNT_TOO_SMALL" in result["reasons"]


def test_consistent_mapping_without_independent_sign_witness_abstains():
    result = analyze_mapping(synthetic_samples("valid_positive_nonlinear"), THRESHOLDS, None)
    assert result["accepted"] is False
    assert result["dominant_orientation_sign"] == "positive"
    assert "VIEW_CHIRALITY_INDEPENDENT_SIGN_WITNESS_REQUIRED" in result["reasons"]


def test_live_core4_stays_fail_closed_without_run133_decode_or_witness(tmp_path: Path):
    result = build(JOB, tmp_path / "run134")
    report = result["report"]
    assert report["status"] == "VIEW_CHIRALITY_ABSTAIN"
    assert report["counts"] == {
        "role_count": 10,
        "run133_dense_decode_accepted_role_count": 0,
        "view_chirality_accepted_role_count": 0,
        "view_chirality_abstained_role_count": 10,
        "declared_orientation_witness_count": 0,
    }
    assert all(row["psd_allowed"] is False for row in report["core4_release_status"])


def test_downstream_claims_remain_false(tmp_path: Path):
    report = build(JOB, tmp_path / "claims")["report"]
    for key in (
        "physical_surface_ownership",
        "physical_side_polarity",
        "readable_direction",
        "stored_orientation",
        "projector",
        "psd",
        "delivery",
        "app",
        "fidelity_95",
    ):
        assert report["claims"][key] is False


def test_hash_bound_run133_source_rejects_tamper(tmp_path: Path):
    job = json.loads(JOB.read_text(encoding="utf-8"))
    job["sources"]["run133_report"]["sha256"] = "0" * 64
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ViewChiralityError, match="run133_report_sha256_mismatch"):
        build(tampered, tmp_path / "tampered_out")


def test_reusable_module_has_no_livery_identity_branches():
    source = (ROOT / "_forge_dlm_view_chirality_gate.py").read_text(encoding="utf-8").lower()
    forbidden = ("waffle", "domino", "crystal", "jason", "wax", "miller", "dew", "spider")
    assert not any(token in source for token in forbidden)