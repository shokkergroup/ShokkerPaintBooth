from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest

import _forge_dlm_physical_capture_session as session


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_physical_capture_session" / "run129_job.json"


def _portable_job(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path = tmp_path / uuid4().hex
    tmp_path.mkdir(parents=True, exist_ok=True)
    payload = json.loads(JOB.read_text(encoding="utf-8"))
    for record in payload["sources"].values():
        record["path"] = str((JOB.parent / record["path"]).resolve())
    capture_root = tmp_path / "captures"
    payload["capture_root"] = str(capture_root)
    job = tmp_path / "job.json"
    job.write_text(json.dumps(payload), encoding="utf-8")
    return job, capture_root


def _write_good_pair(capture_root: Path, off_name: str, on_name: str) -> tuple[Path, Path]:
    capture_root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(129)
    base = rng.integers(30, 210, size=(192, 256), dtype=np.uint8)
    base = cv2.GaussianBlur(base, (0, 0), 1.2)
    cv2.rectangle(base, (20, 20), (235, 170), 80, 3)
    cv2.circle(base, (128, 96), 52, 175, 3)
    cv2.putText(base, "UV", (92, 107), cv2.FONT_HERSHEY_SIMPLEX, 1.1, 225, 2, cv2.LINE_AA)
    wire = base.copy()
    for x in range(18, 250, 19):
        cv2.line(wire, (x, 12), (x, 180), 248, 1, cv2.LINE_AA)
    for y in range(16, 188, 21):
        cv2.line(wire, (8, y), (247, y), 248, 1, cv2.LINE_AA)
    off = capture_root / off_name
    on = capture_root / on_name
    assert cv2.imwrite(str(off), base)
    assert cv2.imwrite(str(on), wire)
    return off, on


def _first_names(result: dict[str, object]) -> tuple[str, str]:
    pair = result["manifest"]["schedule"][0]
    return pair["frames"]["wire_off"]["canonical_filename"], pair["frames"]["wire_on"]["canonical_filename"]


def test_empty_realistic_session_is_exact_180_frame_debt(tmp_path: Path) -> None:
    job, capture_root = _portable_job(tmp_path)
    result = session.build(job, tmp_path / "out")
    counts = result["report"]["counts"]
    assert capture_root.is_dir()
    assert len(result["manifest"]["schedule"]) == 90
    assert counts["expected_frame_count"] == 180
    assert counts["routed_frame_count"] == 0
    assert counts["missing_frame_count"] == 180
    assert counts["complete_pair_count"] == 0
    assert counts["accepted_candidate_pair_count"] == 0
    assert result["patch"]["candidate_pairs"] == []
    assert all(value is False for value in result["report"]["claims"].values())


def test_single_wire_off_frame_is_resumable_but_not_a_pair(tmp_path: Path) -> None:
    job, capture_root = _portable_job(tmp_path)
    empty = session.build(job, tmp_path / "empty")
    off_name, _ = _first_names(empty)
    capture_root.mkdir(parents=True, exist_ok=True)
    image = np.full((96, 128), 100, dtype=np.uint8)
    assert cv2.imwrite(str(capture_root / off_name), image)
    result = session.build(job, tmp_path / "partial")
    counts = result["report"]["counts"]
    assert counts["routed_frame_count"] == 1
    assert counts["missing_frame_count"] == 179
    assert counts["complete_pair_count"] == 0
    assert result["report"]["pair_rows"][0]["reasons"] == ["PAIR_INCOMPLETE"]


def test_complete_unchanged_camera_pair_becomes_run127_candidate(tmp_path: Path) -> None:
    job, capture_root = _portable_job(tmp_path)
    empty = session.build(job, tmp_path / "empty")
    off_name, on_name = _first_names(empty)
    _write_good_pair(capture_root, off_name, on_name)
    result = session.build(job, tmp_path / "complete")
    counts = result["report"]["counts"]
    assert counts["routed_frame_count"] == 2
    assert counts["complete_pair_count"] == 1
    assert counts["accepted_candidate_pair_count"] == 1
    assert result["report"]["pair_rows"][0]["accepted"] is True
    assert result["patch"]["candidate_pair_count"] == 1
    assert result["patch"]["claims"]["physical_authority"] is False


def test_identical_pixels_and_canvas_change_fail_closed(tmp_path: Path) -> None:
    duplicate_job, duplicate_root = _portable_job(tmp_path / "duplicate")
    duplicate_empty = session.build(duplicate_job, tmp_path / "duplicate_empty")
    off_name, on_name = _first_names(duplicate_empty)
    duplicate_root.mkdir(parents=True, exist_ok=True)
    identical = np.full((100, 140), 125, dtype=np.uint8)
    assert cv2.imwrite(str(duplicate_root / off_name), identical)
    assert cv2.imwrite(str(duplicate_root / on_name), identical)
    duplicate = session.build(duplicate_job, tmp_path / "duplicate_out")
    assert duplicate["report"]["counts"]["accepted_candidate_pair_count"] == 0
    assert "PAIR_REUSES_PIXELS_ACROSS_SCHEDULE" in duplicate["report"]["pair_rows"][0]["reasons"]

    canvas_job, canvas_root = _portable_job(tmp_path / "canvas")
    canvas_empty = session.build(canvas_job, tmp_path / "canvas_empty")
    off_name, on_name = _first_names(canvas_empty)
    canvas_root.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(canvas_root / off_name), np.full((100, 140), 80, dtype=np.uint8))
    assert cv2.imwrite(str(canvas_root / on_name), np.full((110, 140), 190, dtype=np.uint8))
    canvas = session.build(canvas_job, tmp_path / "canvas_out")
    assert canvas["report"]["counts"]["complete_pair_count"] == 1
    assert canvas["report"]["counts"]["accepted_candidate_pair_count"] == 0
    assert "CAMERA_CANVAS_CHANGED" in canvas["report"]["pair_rows"][0]["reasons"]


def test_orphan_is_reported_and_source_hash_tamper_rejects(tmp_path: Path) -> None:
    job, capture_root = _portable_job(tmp_path)
    capture_root.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(capture_root / "mystery.png"), np.full((24, 24), 30, dtype=np.uint8))
    result = session.build(job, tmp_path / "out")
    assert result["report"]["counts"]["orphan_frame_count"] == 1
    assert result["report"]["orphans"][0]["reason"] == "FILENAME_NOT_IN_BOUND_SCHEDULE"

    payload = json.loads(job.read_text(encoding="utf-8"))
    payload["sources"]["run127_ledger"]["sha256"] = "0" * 64
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(session.CaptureSessionError, match="run127_ledger_sha256_mismatch"):
        session.build(tampered, tmp_path / "tampered_out")


def test_reusable_source_has_no_livery_identity_branches() -> None:
    source = (ROOT / "_forge_dlm_physical_capture_session.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor", "car_name"):
        assert forbidden not in source
