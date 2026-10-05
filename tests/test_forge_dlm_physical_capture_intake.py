from __future__ import annotations

import copy
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import _forge_dlm_physical_capture_intake as intake


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_physical_capture_intake" / "run127_job.json"
RUN126_REPORT = ROOT / "_forge_out" / "codex_full_uv_recovery" / "run_126_native_physical_calibration" / "NATIVE_PHYSICAL_CALIBRATION_REPORT.json"


def _thresholds() -> dict[str, float]:
    return json.loads(JOB.read_text(encoding="utf-8"))["camera_lock_thresholds"]


def _asset_sha(asset_id: str = "control_black") -> str:
    report = json.loads(RUN126_REPORT.read_text(encoding="utf-8"))
    return next(row["png"]["sha256"] for row in report["assets"] if row["asset_id"] == asset_id)


def _write_pair(tmp_path: Path, *, shift_x: int = 0, broad_change: bool = False) -> tuple[Path, Path]:
    rng = np.random.default_rng(127)
    base = rng.integers(30, 210, size=(192, 256), dtype=np.uint8)
    base = cv2.GaussianBlur(base, (0, 0), 1.2)
    cv2.rectangle(base, (20, 20), (235, 170), 80, 3)
    cv2.circle(base, (128, 96), 52, 175, 3)
    cv2.putText(base, "DLM", (82, 105), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 225, 2, cv2.LINE_AA)
    wire = base.copy()
    if broad_change:
        wire[:, :110] = np.clip(wire[:, :110].astype(np.int16) + 80, 0, 255).astype(np.uint8)
    else:
        for x in range(18, 250, 19):
            cv2.line(wire, (x, 12), (x, 180), 248, 1, cv2.LINE_AA)
        for y in range(16, 188, 21):
            cv2.line(wire, (8, y), (247, y), 248, 1, cv2.LINE_AA)
    if shift_x:
        wire = np.roll(wire, shift_x, axis=1)
    off = tmp_path / "wire_off.png"
    on = tmp_path / "wire_on.png"
    assert cv2.imwrite(str(off), base)
    assert cv2.imwrite(str(on), wire)
    return off, on


def _pair(off: Path, on: Path) -> dict[str, object]:
    lock = "locked_camera_01"
    return {
        "pair_id": "synthetic_pair_01",
        "capture_role_id": "physical_side_a_profile",
        "texture_asset_id": "control_black",
        "texture_asset_png_sha256": _asset_sha(),
        "camera_lock_id": lock,
        "wire_off": {
            "path": str(off),
            "sha256": intake.sha256_file(off),
            "wire_state": "wire_off",
            "camera_lock_id": lock,
        },
        "wire_on": {
            "path": str(on),
            "sha256": intake.sha256_file(on),
            "wire_state": "wire_on",
            "camera_lock_id": lock,
        },
    }


def _validate(pair: dict[str, object]) -> dict[str, object]:
    return intake.validate_capture_pair(
        pair,
        job_path=JOB,
        valid_roles={"physical_side_a_profile"},
        valid_assets={"control_black": _asset_sha()},
        thresholds=_thresholds(),
    )


def test_run127_fixed_inventory_is_fail_closed_and_complete(tmp_path: Path) -> None:
    result = intake.build(JOB, tmp_path / "out")
    report = result["report"]
    counts = report["counts"]
    assert report["status"] == "PASS_CAPTURE_INTAKE_FIREWALL_NOT_PHYSICAL_AUTHORITY"
    assert counts["core4_pack_count"] == 4
    assert counts["core4_reference_source_count"] == 41
    assert counts["core4_direct_physical_view_count"] == 20
    assert counts["review_evidence_count"] == 22
    assert counts["accepted_pair_count"] == 0
    assert counts["required_pair_count"] == 90
    assert counts["missing_frame_count"] == 180
    assert len(report["capture_matrix"]) == 10
    assert all(len(row["asset_states"]) == 9 for row in report["capture_matrix"])
    content_hash = report.pop("report_content_sha256")
    assert intake.canonical_sha256(report) == content_hash
    report["report_content_sha256"] = content_hash
    assert len(result["ledger"]["missing"]) == 90
    assert len(result["ledger"]["missing_frames"]) == 180
    assert all(row["expected_texture_png_sha256"] for row in result["ledger"]["missing_frames"])
    assert all(value is False for value in report["claims"].values())
    assert all(row["capture_pair_eligible"] is False for row in report["review_evidence"])
    assert all(row["delivery_pixels_allowed"] is False for row in report["review_evidence"])


def test_hash_binding_tamper_rejects_before_inventory(tmp_path: Path) -> None:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for record in job["sources"].values():
        record["path"] = str((JOB.parent / record["path"]).resolve())
    for record in job["review_evidence_directories"]:
        record["path"] = str((JOB.parent / record["path"]).resolve())
    job["sources"]["run126_report"]["sha256"] = "0" * 64
    altered = tmp_path / "tampered_job.json"
    altered.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(intake.CaptureIntakeError, match="run126_report_sha256_mismatch"):
        intake.build(altered, tmp_path / "out")


def test_explicit_unchanged_camera_wire_pair_is_accepted(tmp_path: Path) -> None:
    off, on = _write_pair(tmp_path)
    result = _validate(_pair(off, on))
    metrics = result["camera_lock_metrics"]
    assert result["accepted"] is True
    assert result["reasons"] == []
    assert metrics["changed_pixel_fraction"] >= _thresholds()["minimum_changed_pixel_fraction"]
    assert metrics["wire_on_edge_gain_fraction"] >= _thresholds()["minimum_wire_on_edge_gain_fraction"]
    assert metrics["shift_magnitude_px"] <= _thresholds()["maximum_shift_px"]


def test_shifted_camera_and_broad_scene_change_are_rejected(tmp_path: Path) -> None:
    shifted_dir = tmp_path / "shifted"
    shifted_dir.mkdir(exist_ok=True)
    off, on = _write_pair(shifted_dir, shift_x=7)
    shifted = _validate(_pair(off, on))
    assert shifted["accepted"] is False
    assert "CAMERA_MOVED" in shifted["reasons"]

    broad_dir = tmp_path / "broad"
    broad_dir.mkdir(exist_ok=True)
    off, on = _write_pair(broad_dir, broad_change=True)
    broad = _validate(_pair(off, on))
    assert broad["accepted"] is False
    assert "WIRE_DELTA_TOO_BROAD" in broad["reasons"] or "NON_WIRE_SCENE_CHANGED" in broad["reasons"]


def test_pair_requires_texture_hash_and_distinct_wire_states(tmp_path: Path) -> None:
    off, on = _write_pair(tmp_path)
    wrong_asset = _pair(off, on)
    wrong_asset["texture_asset_png_sha256"] = "f" * 64
    with pytest.raises(intake.CaptureIntakeError, match="texture_asset_sha256_mismatch"):
        _validate(wrong_asset)

    wrong_state = copy.deepcopy(_pair(off, on))
    wrong_state["wire_on"]["wire_state"] = "wire_off"
    with pytest.raises(intake.CaptureIntakeError, match="wire_state_mismatch"):
        _validate(wrong_state)

    same = copy.deepcopy(_pair(off, on))
    same["wire_on"] = copy.deepcopy(same["wire_off"])
    same["wire_on"]["wire_state"] = "wire_on"
    with pytest.raises(intake.CaptureIntakeError, match="not_two_distinct_frames"):
        _validate(same)
