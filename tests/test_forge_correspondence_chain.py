from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from _forge_correspondence_chain import SCHEMA, run


def _link(tmp_path: Path, name: str, source: Path, source_crop: list[int], target: Path, target_crop: list[int], homography: list[list[float]], quality: float = 92.0) -> Path:
    manifest = {
        "$schema": "shokk-forge.multiview-surface-correspondence/v1",
        "surfaces": [{"id": f"{name}_surface", "physical_surface": "nose", "source": str(source), "crop": source_crop}],
        "views": [{"id": f"{name}_view", "source": str(target), "crop": target_crop, "surfaces": [f"{name}_surface"]}],
    }
    manifest_path = tmp_path / f"{name}_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = {
        "$schema": "shokk-forge.multiview-surface-correspondence/v1",
        "manifest": str(manifest_path),
        "valid": True,
        "correspondence_score": quality,
        "registrations": [{
            "accepted": True, "non_reflecting": True, "quality": quality,
            "median_reprojection_error": 0.5, "homography": homography,
            "surface": f"{name}_surface", "view": f"{name}_view", "physical_surface": "nose",
        }],
        "views": [{"id": f"{name}_view", "source": str(target), "crop": target_crop}],
    }
    report_path = tmp_path / f"{name}_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


def _fixture(tmp_path: Path) -> Path:
    source, middle, target = tmp_path / "source.png", tmp_path / "middle.png", tmp_path / "target.png"
    Image.new("RGB", (40, 20), "yellow").save(source)
    Image.new("RGB", (60, 30), "black").save(middle)
    Image.new("RGB", (100, 50), "white").save(target)
    first = _link(tmp_path, "first", source, [0, 0, 20, 10], middle, [5, 5, 25, 15], [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 93.0)
    second = _link(tmp_path, "second", middle, [5, 5, 25, 15], target, [0, 0, 40, 20], [[2, 0, 0], [0, 2, 0], [0, 0, 1]], 91.0)
    manifest = {
        "$schema": SCHEMA,
        "minimum_correspondence_score": 85.0,
        "links": [
            {"report": str(first), "view": "first_view", "surface": "first_surface"},
            {"report": str(second), "view": "second_view", "surface": "second_surface"},
        ],
        "output": {"view": "front", "surface": "nose_compiler_source", "physical_surface": "nose"},
    }
    path = tmp_path / "chain.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_chain_composes_exact_contiguous_nonreflecting_links(tmp_path: Path) -> None:
    report = run(_fixture(tmp_path), tmp_path / "out")
    assert report["valid"]
    assert report["correspondence_score"] == 91.0
    assert report["registrations"][0]["homography"][0][0] == 2.0
    assert len(report["registrations"][0]["chain_provenance"]) == 2


def test_chain_rejects_intermediate_crop_mismatch(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    second_report = Path(data["links"][1]["report"])
    report = json.loads(second_report.read_text(encoding="utf-8"))
    source_manifest = Path(report["manifest"])
    source_data = json.loads(source_manifest.read_text(encoding="utf-8"))
    source_data["surfaces"][0]["crop"] = [6, 5, 26, 15]
    source_manifest.write_text(json.dumps(source_data), encoding="utf-8")
    with pytest.raises(ValueError, match="exact intermediate crop provenance"):
        run(manifest, tmp_path / "bad")


def test_chain_rejects_reflecting_link(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    first_report = Path(data["links"][0]["report"])
    report = json.loads(first_report.read_text(encoding="utf-8"))
    report["registrations"][0]["non_reflecting"] = False
    first_report.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="reflecting"):
        run(manifest, tmp_path / "reflected")
