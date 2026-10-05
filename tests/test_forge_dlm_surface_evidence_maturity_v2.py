from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from _forge_dlm_surface_evidence_maturity_v2 import (
    CLAIMS,
    LOCKED_FALSE_CLAIMS,
    REQUIRED_CHECKS,
    create_job,
    evaluate_maturity_v2,
    read_json,
    validate_ledger_v2,
    verify_source,
)


SURFACES = [
    "hood_nose",
    "left_front_fender",
    "left_side",
    "rear_deck_lid",
    "right_front_fender",
    "right_side",
    "roof",
    "spoiler_inside",
    "spoiler_left_endplate",
    "spoiler_outside",
    "spoiler_right_endplate",
    "tub",
]


def _baseline(pass_by_surface: dict[str, set[str]] | None = None) -> dict:
    pass_by_surface = pass_by_surface or {}
    surfaces = []
    for surface in SURFACES:
        checks = []
        for check_id in REQUIRED_CHECKS:
            passed = check_id in pass_by_surface.get(surface, set())
            checks.append(
                {
                    "check_id": check_id,
                    "pass": passed,
                    "status": "PASS" if passed else "FAIL",
                    "reason": f"baseline {check_id}",
                    "evidence": {"baseline": True},
                }
            )
        passed_count = sum(item["pass"] for item in checks)
        surfaces.append(
            {
                "surface_id": surface,
                "status": "LIMITED" if passed_count else "ABSTAIN",
                "ready": passed_count == 10,
                "passed_check_count": passed_count,
                "required_check_count": 10,
                "supporting_evidence_count": 0,
                "checks": checks,
            }
        )
    return {
        "$schema": "shokk-forge.dlm-surface-evidence-maturity-ledger/v1",
        "policy": {
            "required_checks": list(REQUIRED_CHECKS),
            "ready_requires_all_checks": True,
            "readiness_overrides_allowed": False,
        },
        "surfaces": surfaces,
    }


def _run98() -> dict:
    return {
        "$schema": "shokk-forge.dlm-seam-constrained-subcomponents/v1",
        "claims": {"whole_surface_ownership": False},
        "containment_violation_pixel_count": 0,
        "overlap_pixel_count": 0,
        "components": [
            {
                "component_label": 10,
                "decisions": [
                    {
                        "status": "SUBREGION_VOTE_EVIDENCE",
                        "surface_id": "left_side",
                        "subregion_id": 76,
                        "pixel_count": 6787,
                    }
                ],
            }
        ],
    }


def _run99() -> dict:
    return {
        "$schema": "shokk-forge.dlm-official-uv-landmark-atlas/v1",
        "landmarks": [
            {"id": "official.left.rear_top", "physical_surface": "left_side"},
            {"id": "official.right.rear_top", "physical_surface": "right_side"},
        ],
        "abstentions": [
            {"id": "official.left.front_left", "physical_surface": "left_side"}
        ],
    }


def _policy() -> dict:
    return {
        "minimum_train_variants": 2,
        "minimum_heldout_variants": 1,
        "minimum_train_correspondences": 6,
        "minimum_heldout_correspondences": 2,
        "maximum_train_median_residual_px": 3.5,
        "maximum_heldout_median_residual_px": 5.0,
        "maximum_heldout_p95_residual_px": 9.0,
        "minimum_ransac_inliers": 8,
        "minimum_inlier_ratio": 0.5,
        "minimum_determinant": 0.00001,
        "maximum_condition_number": 10000.0,
    }


def _piece(side: str, map_id: str, variant: str, role: str) -> dict:
    return {
        "map_id": map_id,
        "surface_hint": "side_main",
        "physical_side": side,
        "variant_id": variant,
        "variant_role": role,
        "fit_status": "LOCAL_NONREFLECTING_AFFINE_EVIDENCE",
        "cross_version_status": "PROMOTED_SPARSE_CALIBRATION_PIECE",
        "reflection": False,
        "fold_count": 0,
        "determinant": 0.5,
        "condition_number": 1.2,
        "ransac_inlier_count": 12,
        "ransac_inlier_ratio": 0.75,
        "train_residual": {"count": 12, "median_px": 1.0, "p95_px": 2.0},
        "heldout_residual": {"count": 4, "median_px": 2.0, "p95_px": 3.0},
    }


def _run101() -> dict:
    pieces = []
    groups = []
    for side in ("left", "right"):
        ids = [f"{side}_v13", f"{side}_v19", f"{side}_v20"]
        side_pieces = [
            _piece(side, ids[0], "v13", "TRAIN_VARIANT"),
            _piece(side, ids[1], "v19", "TRAIN_VARIANT"),
            _piece(side, ids[2], "v20", "HELDOUT_VARIANT"),
        ]
        pieces.extend(side_pieces)
        groups.append(
            {
                "surface_hint": "side_main",
                "physical_side": side,
                "status": "CROSS_VERSION_SPARSE_CALIBRATION_EVIDENCE",
                "map_ids": ids,
                "train_variants": ["v13", "v19"],
                "heldout_variants": ["v20"],
            }
        )
    return {
        "$schema": "shokk-forge.dlm-known-flat-calibration/v1",
        "policy": _policy(),
        "cross_version_groups": groups,
        "views": [{"piece_maps": pieces}],
    }


def _run104() -> dict:
    return {
        "$schema": "shokk-forge.active-official-landmark-pairing-ledger/v1",
        "records": [
            {
                "status": "unique",
                "compatible_official_candidates": [
                    {"official_id": "official.left.rear_top", "physical_surface": "left_side"}
                ],
                "expected_physical_surfaces": ["left_side"],
            },
            {
                "status": "abstain",
                "compatible_official_candidates": [],
                "expected_physical_surfaces": ["left_side"],
            },
        ],
    }


def _evaluate(baseline: dict | None = None, run101: dict | None = None) -> dict:
    return evaluate_maturity_v2(
        baseline or _baseline(),
        _run98(),
        _run99(),
        run101 or _run101(),
        _run104(),
    )


def _surface(ledger: dict, surface_id: str) -> dict:
    return next(item for item in ledger["surfaces"] if item["surface_id"] == surface_id)


def _check(surface: dict, check_id: str) -> dict:
    return next(item for item in surface["checks"] if item["check_id"] == check_id)


def test_only_left_and_right_residuals_promote() -> None:
    ledger = _evaluate()
    promoted = [
        (surface["surface_id"], check["check_id"])
        for surface in ledger["surfaces"]
        for check in surface["checks"]
        if check["delta"] == "FAIL_TO_PASS"
    ]
    assert promoted == [("left_side", "residual"), ("right_side", "residual")]
    assert ledger["check_delta_counts"]["FAIL_TO_PASS"] == 2


def test_run98_seam_cells_do_not_claim_complete_seam_mapping() -> None:
    left = _surface(_evaluate(), "left_side")
    seam = _check(left, "seam_bounded_mapping")
    assert seam["pass"] is False
    evidence = seam["supplemental_evidence"][0]
    assert evidence["promoted_seam_cell_count"] == 1
    assert evidence["complete_surface_seam_mapping_proved"] is False


def test_sparse_landmarks_do_not_promote_ownership_orientation_coverage_or_ambiguity() -> None:
    left = _surface(_evaluate(), "left_side")
    for check_id in ("exact_uv_ownership", "stored_readable_orientation", "coverage", "ambiguity"):
        assert _check(left, check_id)["pass"] is False
    assert left["evidence_summary"]["run99"]["exact_official_landmark_count"] == 1
    assert left["evidence_summary"]["run104"]["unique_active_instance_count"] == 1
    assert left["evidence_summary"]["run104"]["surface_ambiguity_fully_resolved"] is False


def test_residual_threshold_failure_remains_fail_closed() -> None:
    report = _run101()
    report["views"][0]["piece_maps"][0]["heldout_residual"]["p95_px"] = 9.01
    ledger = _evaluate(run101=report)
    assert _check(_surface(ledger, "left_side"), "residual")["pass"] is False
    assert _check(_surface(ledger, "right_side"), "residual")["pass"] is True


def test_ready_requires_all_ten_checks() -> None:
    passes = {"roof": set(REQUIRED_CHECKS) - {"coverage"}}
    ledger = _evaluate(baseline=_baseline(passes))
    roof = _surface(ledger, "roof")
    assert roof["passed_check_count"] == 9
    assert roof["ready"] is False
    assert roof["status"] == "LIMITED"


def test_false_readiness_claims_are_locked() -> None:
    ledger = _evaluate()
    assert all(ledger["claims"][name] is False for name in LOCKED_FALSE_CLAIMS)
    broken = copy.deepcopy(ledger)
    broken["claims"]["psd_ready"] = True
    assert any("psd_ready" in error for error in validate_ledger_v2(broken, _baseline()))


def test_validation_rejects_delta_drift_and_check_regression() -> None:
    baseline = _baseline({"left_side": {"active_view_evidence"}})
    ledger = _evaluate(baseline=baseline)
    broken = copy.deepcopy(ledger)
    check = _check(_surface(broken, "left_side"), "active_view_evidence")
    check["pass"] = False
    assert any("regression" in error for error in validate_ledger_v2(broken, baseline))
    broken = copy.deepcopy(ledger)
    _check(_surface(broken, "left_side"), "residual")["delta"] = "UNCHANGED_FAIL"
    assert any("delta mismatch" in error for error in validate_ledger_v2(broken, baseline))


def test_exact_twelve_surface_set_is_required() -> None:
    baseline = _baseline()
    baseline["surfaces"].pop()
    with pytest.raises(ValueError, match="canonical_twelve_surfaces_required"):
        _evaluate(baseline=baseline)


def test_job_source_hash_is_verified(tmp_path: Path) -> None:
    sources = {}
    payloads = {
        "run100_baseline": _baseline(),
        "run98_seam_cells": _run98(),
        "run99_official_landmarks": _run99(),
        "run101_sparse_calibration": _run101(),
        "run104_active_official_pairs": _run104(),
    }
    for label, payload in payloads.items():
        path = tmp_path / f"{label}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        sources[label] = path
    job_path = tmp_path / "job.json"
    job = create_job(sources, job_path)
    source_path = Path(job["sources"]["run98_seam_cells"]["path"])
    source_path.write_text(json.dumps({"changed": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="sha256_mismatch"):
        verify_source(job_path, job["sources"]["run98_seam_cells"], "run98_seam_cells")


def test_optional_run106_forbidden_ready_claim_fails_closed() -> None:
    report = {
        "$schema": "shokk-forge.dlm-sparse-official-side-correspondence/v1",
        "claims": {"dense_mapping": True},
        "surface_results": [],
    }
    with pytest.raises(ValueError, match="run106_forbidden_claim_true"):
        evaluate_maturity_v2(_baseline(), _run98(), _run99(), _run101(), _run104(), report)


def test_run106_side_polarity_contradiction_revokes_run101_residual_promotion() -> None:
    report = {
        "$schema": "shokk-forge.sparse-official-side-correspondence-report/v1",
        "promotion_status": "ABSTAIN_SIDE_POLARITY_CONTRADICTION",
        "claims": {
            "dense_mapping": False,
            "side_polarity_contradiction_detected": True,
        },
        "metrics": {
            "target_side_unique_uv_pixel_count": 0,
            "opposite_side_unique_uv_pixel_count": 344,
        },
        "additional_evidence_required": ["surface-ID-coded matched-side renders"],
        "surface_results": [],
    }
    ledger = evaluate_maturity_v2(_baseline(), _run98(), _run99(), _run101(), _run104(), report)
    assert _check(_surface(ledger, "left_side"), "residual")["pass"] is False
    assert _check(_surface(ledger, "right_side"), "residual")["pass"] is False
    assert ledger["check_delta_counts"]["FAIL_TO_PASS"] == 0
    assert _surface(ledger, "hood_nose")["evidence_summary"]["run106"]["promotion_status"] == "OUT_OF_SCOPE"


def test_real_bound_inputs_promote_exactly_two_side_residual_checks() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = {
        "baseline": root / "_forge_out/codex_full_uv_recovery/run_100_surface_evidence_maturity/DLM_SURFACE_EVIDENCE_MATURITY_LEDGER.json",
        "run98": root / "_forge_out/codex_full_uv_recovery/run_98_seam_constrained_subcomponents/seam_constrained_subcomponent_report.json",
        "run99": root / "_forge_out/codex_full_uv_recovery/run_99_official_uv_landmark_atlas/OFFICIAL_DLM_UV_LANDMARK_ATLAS.json",
        "run101": root / "_forge_out/codex_full_uv_recovery/run_101_known_flat_calibration/known_flat_calibration_report.json",
        "run104": root / "_forge_out/codex_full_uv_recovery/run_104_active_official_landmark_pairing/ACTIVE_OFFICIAL_LANDMARK_PAIRING_LEDGER.json",
    }
    ledger = evaluate_maturity_v2(
        read_json(paths["baseline"]), read_json(paths["run98"]), read_json(paths["run99"]),
        read_json(paths["run101"]), read_json(paths["run104"]),
    )
    assert ledger["check_delta_counts"] == {
        "FAIL_TO_PASS": 2,
        "UNCHANGED_FAIL": 108,
        "UNCHANGED_PASS": 10,
    }
    assert ledger["ready_surface_count"] == 0
    assert ledger["status_counts"] == {"ABSTAIN": 2, "LIMITED": 10}


def test_validation_accepts_clean_ledger() -> None:
    baseline = _baseline()
    ledger = _evaluate(baseline=baseline)
    assert validate_ledger_v2(ledger, baseline) == []
    assert ledger["claims"] == CLAIMS

