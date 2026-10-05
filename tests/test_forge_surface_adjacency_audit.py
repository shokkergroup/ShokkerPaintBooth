import json
import hashlib
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_surface_adjacency_audit import run, sample_uv_edge_profile, score_overlap, score_uv_edge_profiles


def test_seam_overlap_scores_identical_continuation_high() -> None:
    image = np.zeros((80, 120, 3), dtype=np.uint8)
    image[:, :60] = (245, 190, 15)
    image[:, 60:] = (15, 20, 25)
    mask = np.ones((80, 120), dtype=bool)
    metrics, _edges = score_overlap(image, image.copy(), mask)
    assert metrics["visual_fidelity"] >= 99.9
    assert metrics["mean_lab_delta_8bit"] == 0.0


def test_seam_overlap_rejects_broken_color_and_edge_continuation() -> None:
    a = np.zeros((80, 120, 3), dtype=np.uint8)
    a[:, :60] = (245, 190, 15)
    b = np.zeros_like(a)
    b[:40] = (20, 120, 220)
    mask = np.ones((80, 120), dtype=bool)
    metrics, _edges = score_overlap(a, b, mask)
    assert metrics["visual_fidelity"] < 80.0
    assert metrics["mean_lab_delta_8bit"] > 20.0


def test_seam_overlap_rejects_mismatched_canvas() -> None:
    a = np.zeros((8, 8, 3), dtype=np.uint8)
    try:
        score_overlap(a, np.zeros((7, 8, 3), dtype=np.uint8), np.ones((8, 8), dtype=bool))
    except ValueError as error:
        assert "share one canvas" in str(error)
    else:
        raise AssertionError("mismatched seam canvases were accepted")


def test_normalized_uv_edge_profile_honors_declared_reversal() -> None:
    width = 80
    gradient = np.zeros((40, width, 3), dtype=np.uint8)
    gradient[:, :, 0] = np.linspace(10, 240, width, dtype=np.uint8)
    gradient[:, :, 1] = np.linspace(220, 20, width, dtype=np.uint8)
    mask = np.ones((40, width), dtype=bool)
    forward = sample_uv_edge_profile(gradient, mask, [0, 0, width, 40], "top", 8, 64)
    reversed_source = gradient[:, ::-1].copy()
    wrong = sample_uv_edge_profile(reversed_source, mask, [0, 0, width, 40], "top", 8, 64)
    corrected = sample_uv_edge_profile(
        reversed_source, mask, [0, 0, width, 40], "top", 8, 64, reverse=True
    )
    correct_metrics, _ = score_uv_edge_profiles(forward, corrected)
    wrong_metrics, _ = score_uv_edge_profiles(forward, wrong)
    assert correct_metrics["visual_fidelity"] > 99.0
    assert wrong_metrics["visual_fidelity"] < correct_metrics["visual_fidelity"] - 20.0


def test_normalized_uv_edge_profile_rejects_bad_contract() -> None:
    rgb = np.zeros((20, 20, 3), dtype=np.uint8)
    mask = np.ones((20, 20), dtype=bool)
    with pytest.raises(ValueError, match="unsupported UV edge"):
        sample_uv_edge_profile(rgb, mask, [0, 0, 20, 20], "diagonal", 4, 16)
    with pytest.raises(ValueError, match="length_range"):
        sample_uv_edge_profile(rgb, mask, [0, 0, 20, 20], "top", 4, 16, (0.8, 0.2))


def test_dense_multiview_correspondence_passes_only_indexed_case(tmp_path: Path) -> None:
    for name, color in (("front_ref.png", "yellow"), ("front_reproject.png", "orange"), ("top_ref.png", "black"), ("top_reproject.png", "gold")):
        Image.new("RGB", (32, 24), color).save(tmp_path / name)
    correspondence_report = {
        "valid": True,
        "score_meaning": "geometric correspondence confidence; not livery visual fidelity",
        "correspondence_score": 92.5,
        "registrations": [
            {"accepted": True, "view": view, "physical_surface": surface, "non_reflecting": True}
            for view in ("front", "top") for surface in ("hood", "nose")
        ],
        "views": [
            {"id": "front", "dense_pixels": 100, "reference_image": "front_ref.png", "reprojection_image": "front_reproject.png"},
            {"id": "top", "dense_pixels": 80, "reference_image": "top_ref.png", "reprojection_image": "top_reproject.png"},
        ],
    }
    (tmp_path / "report.json").write_text(json.dumps(correspondence_report), encoding="utf-8")
    index = {
        "$schema": "shokk-forge.surface-correspondence-index/v1",
        "cases": {"case": {"hood_nose": {"report": "report.json"}}},
    }
    (tmp_path / "index.json").write_text(json.dumps(index), encoding="utf-8")
    adapter = {
        "surfaces": {"hood": {}, "nose": {}},
        "adjacency": [{
            "a": "hood", "b": "nose", "seam": "hood_to_nose",
            "continuity_audit": {
                "mode": "dense_multiview_correspondence",
                "correspondence_key": "hood_nose",
                "required_physical_surfaces": ["hood", "nose"],
                "minimum_views": 2,
                "pass_score": 85.0,
            },
        }],
    }
    (tmp_path / "adapter.json").write_text(json.dumps(adapter), encoding="utf-8")
    (tmp_path / "profiles.json").write_text(json.dumps({"packs": [{"name": "case", "profiles": []}]}), encoding="utf-8")
    Image.new("RGB", (8, 8), "black").save(tmp_path / "candidate.png")
    result = run(
        tmp_path / "adapter.json",
        tmp_path / "profiles.json",
        [("case", tmp_path / "candidate.png")],
        tmp_path / "out",
        tmp_path / "index.json",
    )
    assert result["valid"]
    assert result["weighted_continuity_score"] == 92.5
    assert result["rows"][0]["correspondence"]["accepted_views"] == ["front", "top"]


def _candidate_roundtrip_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    candidate = Image.new("RGB", (64, 64), (18, 20, 24))
    pixels = np.asarray(candidate, dtype=np.uint8).copy()
    pixels[4:60, 3:31] = (242, 190, 12)
    pixels[8:56, 33:61] = (12, 18, 24)
    pixels[20:44, 40:56] = (230, 230, 224)
    candidate_path = tmp_path / "candidate.png"
    Image.fromarray(pixels, "RGB").save(candidate_path)
    left_mask = np.zeros((64, 64), dtype=np.uint8)
    left_mask[4:60, 3:31] = 255
    right_mask = np.zeros((64, 64), dtype=np.uint8)
    right_mask[8:56, 33:61] = 255
    Image.fromarray(left_mask, "L").save(tmp_path / "hood.png")
    Image.fromarray(right_mask, "L").save(tmp_path / "nose.png")
    adapter = {
        "surfaces": {
            "hood": {"bbox": [3, 4, 31, 60], "mask_path": "hood.png"},
            "nose": {"bbox": [33, 8, 61, 56], "mask_path": "nose.png"},
        },
        "adjacency": [{
            "a": "hood",
            "b": "nose",
            "seam": "hood_to_nose",
            "continuity_audit": {
                "mode": "candidate_surface_roundtrip",
                "correspondence_key": "hood_nose_candidate",
                "required_physical_surfaces": ["hood", "nose"],
                "minimum_views": 1,
                "pass_score": 85.0,
            },
        }],
    }
    adapter_path = tmp_path / "adapter.json"
    adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
    report = {
        "$schema": "shokk-forge.candidate-surface-roundtrip/v1",
        "valid": True,
        "candidate_composite": str(candidate_path.resolve()),
        "candidate_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "score_meaning": "compiled candidate pixel fidelity",
        "surfaces": [
            {"surface": "hood", "direct_uv_score": 94.0, "evaluated_pixels": 500, "valid": True},
            {"surface": "nose", "direct_uv_score": 93.0, "evaluated_pixels": 450, "valid": True},
        ],
        "views": [
            {"view": "top", "surface": "hood", "candidate_pixel_roundtrip_score": 92.0, "evaluated_pixels": 400, "valid": True},
            {"view": "top", "surface": "nose", "candidate_pixel_roundtrip_score": 91.0, "evaluated_pixels": 380, "valid": True},
        ],
        "contact_sheet": "roundtrip.png",
    }
    Image.new("RGB", (80, 60), "gold").save(tmp_path / "roundtrip.png")
    report_path = tmp_path / "candidate_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    index = {
        "$schema": "shokk-forge.surface-correspondence-index/v1",
        "cases": {"case": {"hood_nose_candidate": {"report": report_path.name}}},
    }
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(index), encoding="utf-8")
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(json.dumps({"packs": [{"name": "case", "profiles": []}]}), encoding="utf-8")
    return adapter_path, profiles_path, candidate_path, index_path


def test_candidate_roundtrip_enforces_candidate_hash_and_shared_pair_view(tmp_path: Path) -> None:
    adapter, profiles, candidate, index = _candidate_roundtrip_fixture(tmp_path)
    result = run(adapter, profiles, [("case", candidate)], tmp_path / "passing", index)
    assert result["valid"]
    assert result["weighted_continuity_score"] == 91.0
    proof = result["rows"][0]["candidate_roundtrip"]
    assert proof["candidate_hash_matches"]
    assert proof["shared_views"] == ["top"]

    changed = np.asarray(Image.open(candidate).convert("RGB"), dtype=np.uint8).copy()
    changed[10:20, 10:20] = (255, 0, 255)
    Image.fromarray(changed, "RGB").save(candidate)
    failed = run(adapter, profiles, [("case", candidate)], tmp_path / "hash_mismatch", index)
    assert not failed["valid"]
    assert not failed["rows"][0]["candidate_roundtrip"]["candidate_hash_matches"]
    assert "candidate SHA-256 does not match audited report" in failed["rows"][0]["candidate_roundtrip"]["failure_reasons"]


def test_candidate_roundtrip_rejects_failed_or_missing_surface(tmp_path: Path) -> None:
    adapter, profiles, candidate, index = _candidate_roundtrip_fixture(tmp_path)
    index_data = json.loads(index.read_text(encoding="utf-8"))
    report_path = tmp_path / index_data["cases"]["case"]["hood_nose_candidate"]["report"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["surfaces"][1]["valid"] = False
    report["surfaces"][1]["direct_uv_score"] = 42.0
    report_path.write_text(json.dumps(report), encoding="utf-8")
    failed = run(adapter, profiles, [("case", candidate)], tmp_path / "failed_surface", index)
    assert not failed["valid"]
    assert failed["rows"][0]["metrics"]["visual_fidelity"] == 42.0

    index_data["cases"]["case"] = {}
    index.write_text(json.dumps(index_data), encoding="utf-8")
    missing = run(adapter, profiles, [("case", candidate)], tmp_path / "missing", index)
    assert not missing["valid"]
    assert missing["abstention_count"] == 1
