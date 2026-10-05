from __future__ import annotations

import json
import uuid
from pathlib import Path

import cv2
import numpy as np
import pytest

import _forge_dlm_bookend_capture_gate as gate


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_bookend_capture_gate" / "run131_job.json"


def _thresholds() -> dict[str, float]:
    return json.loads(JOB.read_text(encoding="utf-8"))["bookend_thresholds"]


def _scene(seed: int = 17) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = rng.integers(30, 220, (192, 256), dtype=np.uint8)
    image = cv2.GaussianBlur(image, (0, 0), 1.2)
    cv2.rectangle(image, (23, 31), (214, 159), 185, 4)
    cv2.circle(image, (91, 103), 31, 55, 5)
    cv2.putText(image, "UV", (133, 118), cv2.FONT_HERSHEY_SIMPLEX, 1.25, 240, 3, cv2.LINE_AA)
    return image


def _write(path: Path, image: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), image)
    return path


def _isolated_job(tmp_path: Path) -> Path:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for record in job["sources"].values():
        record["path"] = str((JOB.parent / record["path"]).resolve())
    job["capture_root"] = str(tmp_path / f"capture_{uuid.uuid4().hex}")
    path = tmp_path / f"run131_{uuid.uuid4().hex}.json"
    path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    return path


def test_live_build_is_220_frame_fail_closed_matrix(tmp_path: Path) -> None:
    result = gate.build(_isolated_job(tmp_path), tmp_path / f"out_{uuid.uuid4().hex}")
    assert len(result["schedule"]["schedule"]) == 110
    assert result["report"]["counts"] == {
        "role_count": 10,
        "expected_pair_count": 110,
        "expected_frame_count": 220,
        "routed_frame_count": 0,
        "missing_frame_count": 220,
        "accepted_pair_count": 0,
        "accepted_bookend_role_count": 0,
        "abstained_bookend_role_count": 10,
    }
    assert result["patch"]["candidate_pair_count"] == 0
    assert result["report"]["claims"]["psd"] is False
    assert all(row["psd_allowed"] is False for row in result["report"]["core4_release_status"])


def test_schedule_has_one_lock_and_start_end_controls_per_role() -> None:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    source_path = (JOB.parent / job["sources"]["run130_schedule"]["path"]).resolve()
    schedule = gate.bookended_schedule(json.loads(source_path.read_text(encoding="utf-8")))
    roles = list(dict.fromkeys(row["capture_role_id"] for row in schedule))
    assert len(roles) == 10
    assert len(schedule) == 110
    assert len({row["frames"]["wire_off"]["canonical_filename"] for row in schedule}) == 110
    for role in roles:
        rows = [row for row in schedule if row["capture_role_id"] == role]
        assert len(rows) == 11
        assert len({row["camera_lock_id"] for row in rows}) == 1
        assert [(row["texture_asset_id"], row["bookend_position"]) for row in rows[:2]] == [
            ("control_black", "start"),
            ("control_white", "start"),
        ]
        assert [(row["texture_asset_id"], row["bookend_position"]) for row in rows[-2:]] == [
            ("control_black", "end"),
            ("control_white", "end"),
        ]


def test_bookend_metric_accepts_distinct_stable_recapture(tmp_path: Path) -> None:
    first = _scene()
    last = first.copy()
    last[7, 11] = np.uint8((int(last[7, 11]) + 1) % 255)
    metrics = gate.bookend_metrics(_write(tmp_path / "start.png", first), _write(tmp_path / "end.png", last), _thresholds())
    assert metrics["accepted"] is True
    assert metrics["shift_magnitude_px"] <= 0.75
    assert metrics["mean_luma_delta"] <= 0.015


def test_bookend_metric_rejects_lighting_drift(tmp_path: Path) -> None:
    first = _scene()
    last = np.clip(first.astype(np.int16) + 35, 0, 255).astype(np.uint8)
    metrics = gate.bookend_metrics(_write(tmp_path / "start.png", first), _write(tmp_path / "bright.png", last), _thresholds())
    assert metrics["accepted"] is False
    assert "BOOKEND_MEAN_LUMA_DRIFT" in metrics["reasons"]
    assert "BOOKEND_LOW_FREQUENCY_DRIFT" in metrics["reasons"]


def test_bookend_metric_rejects_camera_shift(tmp_path: Path) -> None:
    first = _scene()
    last = np.roll(first, 5, axis=1)
    metrics = gate.bookend_metrics(_write(tmp_path / "start.png", first), _write(tmp_path / "shift.png", last), _thresholds())
    assert metrics["accepted"] is False
    assert "BOOKEND_CAMERA_MOVED" in metrics["reasons"]


def test_complete_role_requires_four_stable_control_comparisons(tmp_path: Path) -> None:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    source_path = (JOB.parent / job["sources"]["run130_schedule"]["path"]).resolve()
    schedule = gate.bookended_schedule(json.loads(source_path.read_text(encoding="utf-8")))[:11]
    pair_rows = [{"pair_id": row["pair_id"], "accepted": True} for row in schedule]
    frame_rows: list[dict[str, object]] = []
    controls: dict[tuple[str, str, str], Path] = {}
    for asset_index, asset in enumerate(gate.CONTROL_ASSETS):
        for state_index, state in enumerate(("wire_off", "wire_on")):
            first = _scene(20 + asset_index * 3 + state_index)
            last = first.copy()
            last[4 + asset_index, 8 + state_index] = np.uint8((int(last[4 + asset_index, 8 + state_index]) + 1) % 255)
            controls[(asset, "start", state)] = _write(tmp_path / f"{asset}_start_{state}.png", first)
            controls[(asset, "end", state)] = _write(tmp_path / f"{asset}_end_{state}.png", last)
    for row in schedule:
        for state in ("wire_off", "wire_on"):
            path = controls.get((row["texture_asset_id"], row["bookend_position"], state))
            frame_rows.append({"pair_id": row["pair_id"], "wire_state": state, "path": str(path) if path else None})
    results = gate.evaluate_bookends(schedule, {"pair_rows": pair_rows, "frame_rows": frame_rows}, _thresholds())
    assert len(results) == 1
    assert results[0]["accepted"] is True
    assert results[0]["comparison_count"] == 4
    pair_rows[-1]["accepted"] = False
    rejected = gate.evaluate_bookends(schedule, {"pair_rows": pair_rows, "frame_rows": frame_rows}, _thresholds())
    assert rejected[0]["accepted"] is False
    assert "BOOKEND_ROLE_REQUIRES_ELEVEN_ACCEPTED_WIRE_PAIRS" in rejected[0]["reasons"]


def test_source_binding_tamper_and_identity_branching_fail_closed() -> None:
    record = json.loads(JOB.read_text(encoding="utf-8"))["sources"]["run130_schedule"].copy()
    record["sha256"] = "0" * 64
    with pytest.raises(gate.BookendCaptureError, match="run130_schedule_sha256_mismatch"):
        gate._load_bound(JOB, record, "run130_schedule")
    source = (ROOT / "_forge_dlm_bookend_capture_gate.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor", "car_name"):
        assert forbidden not in source
