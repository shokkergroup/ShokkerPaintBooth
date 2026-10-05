from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from _forge_dlm_front_assembly_polarity import REQUIRED_CLAIMS, run_audit


ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "_forge_out/codex_full_uv_recovery/run_99_official_uv_landmark_atlas/OFFICIAL_DLM_UV_LANDMARK_ATLAS.json"
CALIBRATION = ROOT / "_forge_out/codex_full_uv_recovery/run_101_known_flat_calibration/known_flat_calibration_report.json"
LEDGER = ROOT / "_forge_out/codex_full_uv_recovery/run_104_active_official_landmark_pairing/ACTIVE_OFFICIAL_LANDMARK_PAIRING_LEDGER.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _job(tmp_path: Path) -> Path:
    path = tmp_path / "job.json"
    path.write_text(
        json.dumps(
            {
                "$schema": "shokk-forge.front-assembly-polarity-job/v1",
                "claims": REQUIRED_CLAIMS,
                "allow_evidence_overrides": False,
                "evidence_overrides": {},
                "official_landmark_atlas": {"path": ATLAS.as_posix(), "sha256": _sha(ATLAS)},
                "known_flat_calibration": {"path": CALIBRATION.as_posix(), "sha256": _sha(CALIBRATION)},
                "active_official_ledger": {"path": LEDGER.as_posix(), "sha256": _sha(LEDGER)},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def report(tmp_path: Path) -> dict:
    return run_audit(_job(tmp_path), tmp_path / "output")


def _surface(report: dict, name: str) -> dict:
    return next(row for row in report["surfaces"] if row["surface"] == name)


def test_current_front_truth_abstains_all_four_surfaces(report: dict) -> None:
    assert report["status"] == "PASS"
    assert report["front_assembly_status"] == "ABSTAIN"
    assert report["front_assembly_polarity_ready"] is False
    assert report["surface_status_counts"] == {"ABSTAIN": 4}
    assert report["metrics"]["surface_ready_count"] == 0


def test_hood_keeps_only_real_positive_train_pieces(report: dict) -> None:
    hood = _surface(report, "hood")
    assert hood["official_atlas"]["landmark_count"] == 6
    assert hood["official_atlas"]["all_points_topology_contained"] is True
    assert hood["variant_evidence"]["v13"]["positive_local_piece_count"] == 2
    assert hood["variant_evidence"]["v13"]["positive_determinants"] == [0.293954223, 0.369342731]
    assert hood["variant_evidence"]["v19"]["positive_local_piece_count"] == 0
    assert hood["variant_evidence"]["v20"]["positive_local_piece_count"] == 0
    assert "v19_positive_local_piece_missing" in hood["blockers"]
    assert "v20_positive_local_piece_missing" in hood["blockers"]


def test_nose_and_fenders_fail_closed_on_missing_direct_truth(report: dict) -> None:
    nose = _surface(report, "nose")
    left = _surface(report, "left_front_fender")
    right = _surface(report, "right_front_fender")
    assert nose["official_atlas"]["landmark_count"] == 6
    assert nose["active_official_ledger"]["abstain_pair_count"] == 22
    assert nose["active_official_ledger"]["unique_pair_count"] == 0
    assert left["official_atlas"]["landmark_count"] == 0
    assert right["official_atlas"]["landmark_count"] == 0
    assert left["official_atlas"]["explicit_abstention_ids"] == ["left_front_fender.seam_pair"]
    assert right["official_atlas"]["explicit_abstention_ids"] == ["right_front_fender.seam_pair"]
    assert all(
        row["variant_evidence"][variant]["positive_local_piece_count"] == 0
        for row in (nose, left, right)
        for variant in ("v13", "v19", "v20")
    )


def test_exact_capture_contract_is_surface_and_variant_specific(report: dict) -> None:
    hood_ids = {item["capture_id"] for item in _surface(report, "hood")["additional_capture_required"]}
    nose_ids = {item["capture_id"] for item in _surface(report, "nose")["additional_capture_required"]}
    left_ids = {item["capture_id"] for item in _surface(report, "left_front_fender")["additional_capture_required"]}
    assert "hood.v13.known_flat_pair" not in hood_ids
    assert {"hood.v19.known_flat_pair", "hood.v20.known_flat_pair", "hood.official_physical_polarity"} <= hood_ids
    assert {"nose.v13.known_flat_pair", "nose.v19.known_flat_pair", "nose.v20.known_flat_pair", "nose.official_physical_polarity"} <= nose_ids
    assert {"left_front_fender.v13.known_flat_pair", "left_front_fender.v19.known_flat_pair", "left_front_fender.v20.known_flat_pair", "left_front_fender.official_physical_polarity"} <= left_ids


def test_one_physical_object_split_passes_and_repetition_rejects(report: dict) -> None:
    law = report["duplicate_front_law"]
    valid = law["valid_split"]
    repeated = law["whole_master_repetition"]
    assert law["status"] == "PASS"
    assert valid["status"] == "PASS"
    assert valid["fragment_surfaces"] == ["hood", "nose"]
    assert valid["object_overlap_pixels"] == 0
    assert valid["object_missing_pixels"] == 0
    assert valid["surface_adjacency"] is True
    assert repeated["status"] == "REJECT"
    assert repeated["fragment_surfaces"] == ["hood", "nose"]
    assert repeated["object_overlap_pixels"] == 960


def test_claims_and_reusable_source_remain_livery_neutral(report: dict) -> None:
    assert report["claims"] == REQUIRED_CLAIMS
    assert all(report["claims"][key] is False for key in ("livery_ready", "psd_ready", "app_ready", "delivery_ready"))
    source = (ROOT / "_forge_dlm_front_assembly_polarity.py").read_text(encoding="utf-8").lower()
    for identity in ("waffle", "domino", "crystal_lake", "sex_wax", "miller", "mountain_dew", "spider"):
        assert identity not in source
    for forbidden in ("imageops.mirror", "fliplr", "cv2.flip", "estimateaffine2d", "lstsq"):
        assert forbidden not in source


def test_contact_and_embedded_path_hashes_resolve(report: dict) -> None:
    contact = Path(report["contact"]["path"])
    assert contact.is_file()
    assert _sha(contact) == report["contact"]["sha256"]
    assert contact.stat().st_size > 50_000
    for case in report["duplicate_front_law"].values():
        if not isinstance(case, dict) or "report" not in case:
            continue
        for key in ("report", "qa_visual"):
            path = Path(case[key]["path"])
            assert path.is_file()
            assert _sha(path) == case[key]["sha256"]


def test_source_hash_mismatch_rejects_before_audit(tmp_path: Path) -> None:
    job_path = _job(tmp_path)
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["active_official_ledger"]["sha256"] = "0" * 64
    job_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="active_official_ledger_sha256_mismatch"):
        run_audit(job_path, tmp_path / "bad")
