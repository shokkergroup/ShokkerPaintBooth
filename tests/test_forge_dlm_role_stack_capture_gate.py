from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest

import _forge_dlm_role_stack_capture_gate as gate


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_role_stack_capture_gate" / "run130_job.json"
RUN129_MANIFEST = ROOT / "_forge_out" / "codex_full_uv_recovery" / "run_129_physical_capture_session" / "CAPTURE_SESSION_MANIFEST.json"
RUN128_JOB = ROOT / "_forge_data" / "dlm_review_pair_recommender" / "run128_job.json"


def _thresholds() -> tuple[dict[str, object], dict[str, object]]:
    signature = json.loads(RUN128_JOB.read_text(encoding="utf-8"))["thresholds"]
    stack = json.loads(JOB.read_text(encoding="utf-8"))["role_stack_thresholds"]
    return signature, stack


def _first_role_schedule() -> list[dict[str, object]]:
    manifest = json.loads(RUN129_MANIFEST.read_text(encoding="utf-8"))
    return gate.corrected_schedule(manifest)[:9]


def _scene(path: Path, *, variant: int, shift_x: int = 0) -> Path:
    image = np.full((360, 640, 3), (214, 218, 221), np.uint8)
    points = np.array(
        [[110 + shift_x, 245], [155 + shift_x, 145], [405 + shift_x, 125], [525 + shift_x, 205], [505 + shift_x, 267], [140 + shift_x, 272]],
        np.int32,
    )
    colors = [(35, 55, 75), (245, 245, 245), (45, 160, 220), (190, 75, 45), (55, 185, 75), (175, 45, 190), (45, 190, 195), (120, 70, 210), (205, 115, 40)]
    cv2.fillPoly(image, [points], colors[variant % len(colors)])
    cv2.polylines(image, [points], True, (20, 22, 25), 5, cv2.LINE_AA)
    for x in (180, 450):
        cv2.circle(image, (x + shift_x, 256), 45, (24, 25, 27), -1)
        cv2.circle(image, (x + shift_x, 256), 21, (175, 180, 184), 4)
    cv2.rectangle(image, (245 + shift_x, 145), (390 + shift_x, 235), (32, 34, 37), 4)
    for index in range(18):
        x = 150 + shift_x + index * 19
        cv2.circle(image, (x, 137 + (index % 3) * 8), 2, (8, 8, 8), -1)
    if variant % 2:
        for x in range(145 + shift_x, 505 + shift_x, 26):
            cv2.line(image, (x, 155), (x, 242), (80, 90, 105), 2, cv2.LINE_AA)
    else:
        for y in range(155, 243, 17):
            cv2.line(image, (145 + shift_x, y), (505 + shift_x, y), (230, 185, 55), 2, cv2.LINE_AA)
    assert cv2.imwrite(str(path), image)
    return path


def _synthetic_scan(tmp_path: Path, *, accepted_pairs: int = 9, moved_asset: int | None = None) -> tuple[list[dict[str, object]], dict[str, object]]:
    root = tmp_path / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    schedule = _first_role_schedule()
    pair_rows: list[dict[str, object]] = []
    frame_rows: list[dict[str, object]] = []
    for index, pair in enumerate(schedule):
        path = _scene(root / f"off_{index}.png", variant=index, shift_x=9 if moved_asset == index else 0)
        pair_rows.append({"pair_id": pair["pair_id"], "accepted": index < accepted_pairs})
        frame_rows.append({"pair_id": pair["pair_id"], "wire_state": "wire_off", "path": str(path)})
    return schedule, {"pair_rows": pair_rows, "frame_rows": frame_rows}


def test_run130_live_session_abstains_all_ten_role_stacks(tmp_path: Path) -> None:
    result = gate.build(JOB, tmp_path / uuid4().hex)
    counts = result["report"]["counts"]
    assert counts == {
        "role_stack_count": 10,
        "expected_pair_count": 90,
        "expected_frame_count": 180,
        "accepted_pair_count": 0,
        "accepted_role_stack_count": 0,
        "abstained_role_stack_count": 10,
    }
    assert all(row["status"] == "ROLE_STACK_ABSTAIN" for row in result["report"]["role_stack_results"])
    assert result["report"]["claims"]["pair_lock_is_sufficient_for_absolute_uv"] is False
    assert result["report"]["claims"]["role_stack_camera_lock"] is False
    assert all(row["psd_allowed"] is False for row in result["report"]["core4_release_status"])


def test_corrected_schedule_uses_one_lock_per_nine_texture_role() -> None:
    manifest = json.loads(RUN129_MANIFEST.read_text(encoding="utf-8"))
    schedule = gate.corrected_schedule(manifest)
    roles = list(dict.fromkeys(row["capture_role_id"] for row in schedule))
    assert len(schedule) == 90
    assert len(roles) == 10
    for role in roles:
        rows = [row for row in schedule if row["capture_role_id"] == role]
        assert len(rows) == 9
        assert len({row["required_role_stack_lock_id"] for row in rows}) == 1
        assert len({row["legacy_pair_camera_lock_id"] for row in rows}) == 9


def test_texture_variants_at_one_pose_accept_complete_role_stack(tmp_path: Path) -> None:
    schedule, scan = _synthetic_scan(tmp_path)
    signature_thresholds, stack_thresholds = _thresholds()
    results = gate.evaluate_role_stacks(schedule, scan, signature_thresholds, stack_thresholds)
    assert len(results) == 1
    assert results[0]["accepted"] is True
    assert results[0]["accepted_pair_count"] == 9
    assert results[0]["comparison_count"] == 8
    assert results[0]["reasons"] == []
    assert min(row["metrics"]["silhouette_iou"] for row in results[0]["comparisons"]) >= stack_thresholds["minimum_stack_silhouette_iou"]


def test_one_moved_texture_rejects_entire_role_stack(tmp_path: Path) -> None:
    schedule, scan = _synthetic_scan(tmp_path, moved_asset=7)
    signature_thresholds, stack_thresholds = _thresholds()
    result = gate.evaluate_role_stacks(schedule, scan, signature_thresholds, stack_thresholds)[0]
    assert result["accepted"] is False
    assert any(reason in result["reasons"] for reason in ("ROLE_STACK_SILHOUETTE_CHANGED", "ROLE_STACK_BOX_MOVED", "ROLE_STACK_PHASE_SHIFT", "ROLE_STACK_ECC_SHIFT"))


def test_eight_valid_pairs_cannot_authorize_absolute_uv(tmp_path: Path) -> None:
    schedule, scan = _synthetic_scan(tmp_path, accepted_pairs=8)
    signature_thresholds, stack_thresholds = _thresholds()
    result = gate.evaluate_role_stacks(schedule, scan, signature_thresholds, stack_thresholds)[0]
    assert result["accepted"] is False
    assert result["accepted_pair_count"] == 8
    assert result["comparisons"] == []
    assert result["reasons"] == ["ROLE_STACK_REQUIRES_NINE_ACCEPTED_WIRE_PAIRS"]


def test_bound_session_tamper_rejects_and_source_is_livery_neutral(tmp_path: Path) -> None:
    payload = json.loads(JOB.read_text(encoding="utf-8"))
    for record in payload["sources"].values():
        record["path"] = str((JOB.parent / record["path"]).resolve())
    payload["sources"]["run129_manifest"]["sha256"] = "0" * 64
    altered = tmp_path / "tampered.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(gate.RoleStackError, match="run129_manifest_sha256_mismatch"):
        gate.build(altered, tmp_path / "out")

    source = (ROOT / "_forge_dlm_role_stack_capture_gate.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor", "car_name"):
        assert forbidden not in source
