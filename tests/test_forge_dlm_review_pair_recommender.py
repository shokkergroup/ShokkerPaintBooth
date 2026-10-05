from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import _forge_dlm_review_pair_recommender as recommender


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_review_pair_recommender" / "run128_job.json"


def _thresholds() -> dict[str, object]:
    return json.loads(JOB.read_text(encoding="utf-8"))["thresholds"]


def _scene(path: Path, *, shift_x: int = 0, wire: bool = False, blank: bool = False) -> Path:
    image = np.full((360, 640, 3), (229, 226, 226), np.uint8)
    if blank:
        image[:] = 0
        cv2.circle(image, (320, 180), 16, (60, 60, 60), 3)
    else:
        points = np.array(
            [
                [120 + shift_x, 245],
                [160 + shift_x, 150],
                [390 + shift_x, 125],
                [510 + shift_x, 205],
                [500 + shift_x, 260],
                [145 + shift_x, 270],
            ],
            np.int32,
        )
        cv2.fillPoly(image, [points], (28, 122, 205))
        cv2.polylines(image, [points], True, (20, 20, 25), 5, cv2.LINE_AA)
        cv2.rectangle(image, (245 + shift_x, 150), (385 + shift_x, 235), (35, 35, 38), -1)
        cv2.putText(image, "77", (260 + shift_x, 218), cv2.FONT_HERSHEY_DUPLEX, 1.8, (245, 245, 245), 4, cv2.LINE_AA)
        for x in (185, 440):
            cv2.circle(image, (x + shift_x, 255), 44, (28, 28, 30), -1)
            cv2.circle(image, (x + shift_x, 255), 20, (180, 180, 180), 4)
        rng = np.random.default_rng(128)
        for x, y in rng.integers([155 + shift_x, 140], [475 + shift_x, 245], size=(70, 2)):
            cv2.circle(image, (int(x), int(y)), 2, (230, 205, 40), -1)
        if wire:
            for x in range(150 + shift_x, 491 + shift_x, 28):
                cv2.line(image, (x, 145), (x, 255), (45, 235, 80), 1, cv2.LINE_AA)
            for y in range(155, 251, 18):
                cv2.line(image, (145 + shift_x, y), (500 + shift_x, y), (45, 235, 80), 1, cv2.LINE_AA)
    assert cv2.imwrite(str(path), image)
    return path


def test_run128_fixed_census_rejects_background_false_matches(tmp_path: Path) -> None:
    report = recommender.build(JOB, tmp_path / "out")
    counts = report["counts"]
    assert report["status"] == "PASS_REVIEW_PAIR_RECOMMENDER_NOT_CALIBRATION_AUTHORITY"
    assert counts == {
        "cohort_count": 5,
        "frame_count": 42,
        "usable_frame_count": 41,
        "unusable_frame_count": 1,
        "pair_count": 271,
        "camera_lock_candidate_count": 0,
        "review_pair_count": 231,
        "core4_concept_pair_count": 40,
    }
    assert [row["camera_lock_candidate_count"] for row in report["cohort_summary"]] == [0, 0, 0, 0, 0]
    assert all(value is False for value in report["claims"].values())
    content_hash = report.pop("report_content_sha256")
    assert recommender.canonical_sha256(report) == content_hash


def test_exact_car_supported_wire_overlay_is_recommended_not_authorized(tmp_path: Path) -> None:
    off = _scene(tmp_path / "off.png")
    on = _scene(tmp_path / "on.png", wire=True)
    left = recommender.image_signature(off, _thresholds())
    right = recommender.image_signature(on, _thresholds())
    metrics = recommender.pair_metrics(left, right, _thresholds())
    assert left["usable_review_frame"] is True
    assert right["usable_review_frame"] is True
    assert metrics["camera_lock_candidate"] is True
    assert metrics["reasons"] == []
    assert metrics["silhouette_iou"] >= _thresholds()["minimum_silhouette_iou"]


def test_moved_car_rejects_even_on_identical_studio_background(tmp_path: Path) -> None:
    left_path = _scene(tmp_path / "left.png")
    right_path = _scene(tmp_path / "right.png", shift_x=55, wire=True)
    left = recommender.image_signature(left_path, _thresholds())
    right = recommender.image_signature(right_path, _thresholds())
    metrics = recommender.pair_metrics(left, right, _thresholds())
    assert metrics["camera_lock_candidate"] is False
    assert "SILHOUETTE_CHANGED" in metrics["reasons"]
    assert "FOREGROUND_BOX_MOVED" in metrics["reasons"]


def test_loading_spinner_is_unusable_and_cannot_pair(tmp_path: Path) -> None:
    blank_path = _scene(tmp_path / "blank.png", blank=True)
    car_path = _scene(tmp_path / "car.png")
    blank = recommender.image_signature(blank_path, _thresholds())
    car = recommender.image_signature(car_path, _thresholds())
    metrics = recommender.pair_metrics(blank, car, _thresholds())
    assert blank["usable_review_frame"] is False
    assert metrics["camera_lock_candidate"] is False
    assert metrics["reasons"] == ["UNUSABLE_OR_BLANK_FRAME"]


def test_bound_report_hash_tamper_fails_before_pair_scan(tmp_path: Path) -> None:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for record in job["sources"].values():
        record["path"] = str((JOB.parent / record["path"]).resolve())
    job["sources"]["run127_report"]["sha256"] = "0" * 64
    altered = tmp_path / "tampered.json"
    altered.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(recommender.ReviewPairError, match="run127_report_sha256_mismatch"):
        recommender.build(altered, tmp_path / "out")
