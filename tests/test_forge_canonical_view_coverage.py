import hashlib
import json
from pathlib import Path

from PIL import Image

from _forge_canonical_view_coverage import SCHEMA, run


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    candidate = tmp_path / "candidate.png"
    Image.new("RGB", (32, 32), (20, 30, 40)).save(candidate)
    candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
    left_ref, right_ref = tmp_path / "left.png", tmp_path / "right.png"
    Image.new("RGB", (16, 8), "yellow").save(left_ref)
    Image.new("RGB", (16, 8), "black").save(right_ref)
    visual_report = {
        "$schema": "shokk-forge.visual-fidelity-benchmark/v1",
        "views": [
            {
                "case": "car", "role": "left_profile", "surface": "left_strip",
                "reference_path": str(left_ref), "reference_sha256": hashlib.sha256(left_ref.read_bytes()).hexdigest(),
                "composite_path": str(candidate), "composite_sha256": candidate_sha,
                "metrics": {"visual_fidelity": 94.0, "evaluated_pixels": 500}, "abstentions": [],
            },
            {
                "case": "car", "role": "right_profile", "surface": "right_strip",
                "reference_path": str(right_ref), "reference_sha256": hashlib.sha256(right_ref.read_bytes()).hexdigest(),
                "composite_path": str(candidate), "composite_sha256": candidate_sha,
                "metrics": {"visual_fidelity": 93.0, "evaluated_pixels": 480}, "abstentions": [],
            },
        ],
    }
    visual_path = tmp_path / "visual.json"
    visual_path.write_text(json.dumps(visual_report), encoding="utf-8")
    roundtrip_report = {
        "$schema": "shokk-forge.candidate-surface-roundtrip/v1",
        "candidate_composite": str(candidate),
        "candidate_sha256": candidate_sha,
        "views": [
            {"view": "top", "surface": "hood", "camera_source_sha256": "a" * 64, "candidate_pixel_roundtrip_score": 96.0, "evaluated_pixels": 300, "valid": True},
            {"view": "top", "surface": "roof", "camera_source_sha256": "a" * 64, "candidate_pixel_roundtrip_score": 97.0, "evaluated_pixels": 250, "valid": True},
            {"view": "front", "surface": "hood", "camera_source_sha256": "b" * 64, "candidate_pixel_roundtrip_score": 95.0, "evaluated_pixels": 320, "valid": True},
            {"view": "front", "surface": "nose", "camera_source_sha256": "b" * 64, "candidate_pixel_roundtrip_score": 92.0, "evaluated_pixels": 240, "valid": True},
            {"view": "rear", "surface": "spoiler_outside", "camera_source_sha256": "c" * 64, "candidate_pixel_roundtrip_score": 91.0, "evaluated_pixels": 180, "valid": True},
        ],
    }
    roundtrip_path = tmp_path / "roundtrip.json"
    roundtrip_path.write_text(json.dumps(roundtrip_report), encoding="utf-8")
    manifest = {
        "$schema": SCHEMA,
        "candidate_composite": str(candidate),
        "required_roles": ["left", "right", "top", "front", "rear"],
        "minimum_score": 85.0,
        "commercial_target": 95.0,
        "cells": [
            {"role": "left", "camera_id": "left_camera", "required_surfaces": ["left_strip"], "evidence": {"type": "visual_benchmark_role", "report": str(visual_path), "case": "car", "view_role": "left_profile"}},
            {"role": "right", "camera_id": "right_camera", "required_surfaces": ["right_strip"], "evidence": {"type": "visual_benchmark_role", "report": str(visual_path), "case": "car", "view_role": "right_profile"}},
            {"role": "top", "camera_id": "top_camera", "required_surfaces": ["hood", "roof"], "evidence": {"type": "candidate_roundtrip_view", "report": str(roundtrip_path), "view": "top", "required_surfaces": ["hood", "roof"]}},
            {"role": "front", "camera_id": "front_camera", "required_surfaces": ["hood", "nose"], "evidence": {"type": "candidate_roundtrip_view", "report": str(roundtrip_path), "view": "front", "required_surfaces": ["hood", "nose"]}},
            {"role": "rear", "camera_id": "rear_camera", "required_surfaces": ["spoiler_outside"], "evidence": {"type": "candidate_roundtrip_view", "report": str(roundtrip_path), "view": "rear", "required_surfaces": ["spoiler_outside"]}},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, roundtrip_path, candidate


def test_distinct_complete_matrix_reports_conservative_minimum(tmp_path: Path) -> None:
    manifest, _roundtrip, _candidate = _fixture(tmp_path)
    report = run(manifest, tmp_path / "out")
    assert report["complete_five_view"]
    assert report["complete_cells"] == 5
    assert report["qualified_five_view_score"] == 91.0
    assert not report["forge_95_pass"]
    assert not report["duplicate_camera_sources"]


def test_missing_required_surface_is_partial_not_qualified(tmp_path: Path) -> None:
    manifest, roundtrip, _candidate = _fixture(tmp_path)
    report_data = json.loads(roundtrip.read_text(encoding="utf-8"))
    report_data["views"] = [row for row in report_data["views"] if not (row["view"] == "front" and row["surface"] == "nose")]
    roundtrip.write_text(json.dumps(report_data), encoding="utf-8")
    report = run(manifest, tmp_path / "partial")
    assert not report["complete_five_view"]
    assert report["partial_cells"] == 1
    front = next(row for row in report["cells"] if row["role"] == "front")
    assert front["status"] == "PARTIAL"
    assert front["missing_surfaces"] == ["nose"]


def test_same_camera_cannot_count_as_top_and_rear(tmp_path: Path) -> None:
    manifest, roundtrip, _candidate = _fixture(tmp_path)
    report_data = json.loads(roundtrip.read_text(encoding="utf-8"))
    for row in report_data["views"]:
        if row["view"] == "rear":
            row["camera_source_sha256"] = "a" * 64
    roundtrip.write_text(json.dumps(report_data), encoding="utf-8")
    report = run(manifest, tmp_path / "duplicate")
    assert not report["valid"]
    assert not report["complete_five_view"]
    assert report["duplicate_camera_sources"]
    assert {row["status"] for row in report["cells"] if row["role"] in {"top", "rear"}} == {"FAIL"}


def test_visual_cell_uses_all_observed_surfaces_and_weakest_score(tmp_path: Path) -> None:
    manifest, _roundtrip, _candidate = _fixture(tmp_path)
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    visual_path = Path(manifest_data["cells"][0]["evidence"]["report"])
    visual = json.loads(visual_path.read_text(encoding="utf-8"))
    left = next(row for row in visual["views"] if row["role"] == "left_profile")
    left["observed_surfaces"] = ["left_strip", "left_front_fender"]
    left["qualified_surface_score"] = 88.5
    visual_path.write_text(json.dumps(visual), encoding="utf-8")
    manifest_data["cells"][0]["required_surfaces"] = ["left_strip", "left_front_fender"]
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    report = run(manifest, tmp_path / "multi_surface")
    left_cell = next(row for row in report["cells"] if row["role"] == "left")
    assert left_cell["status"] == "PASS"
    assert left_cell["score"] == 88.5
    assert left_cell["missing_surfaces"] == []
