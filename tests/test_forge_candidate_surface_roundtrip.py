import json
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from _forge_candidate_surface_roundtrip import SCHEMA, forward_surface_reference, run
from _forge_panel_pack_reconstructor import extract_asset_with_origin


def _write_fixture(root: Path) -> tuple[Path, Path, dict]:
    source = Image.new("RGB", (80, 60), "white")
    draw = ImageDraw.Draw(source)
    draw.polygon([(8, 8), (70, 12), (62, 53), (12, 48)], fill=(245, 198, 8))
    draw.rectangle((12, 15, 37, 42), fill=(9, 12, 15))
    draw.ellipse((45, 17, 67, 39), fill=(205, 35, 28))
    draw.rectangle((18, 22, 27, 34), fill=(236, 236, 230))
    source_path = root / "source.png"
    source.save(source_path)

    mask = np.zeros((128, 128), dtype=np.uint8)
    mask[18:112, 20:108] = 255
    mask_path = root / "surface_mask.png"
    Image.fromarray(mask, "L").save(mask_path)
    adapter = {
        "$schema": "shokk-forge.template-adapter/v1",
        "canvas": [128, 128],
        "surfaces": {"panel": {"bbox": [20, 18, 108, 112], "mask_path": mask_path.name}},
    }
    adapter_path = root / "adapter.json"
    adapter_path.write_text(json.dumps(adapter), encoding="utf-8")

    row = {
        "surface": "panel",
        "correspondence_surface": "panel_source",
        "source": str(source_path),
        "crop": [0, 0, 80, 60],
        "background_tolerance": 24,
        "rotate": 90,
        "fit": "stretch",
        "views": ["camera"],
    }
    extracted, _origin = extract_asset_with_origin(source_path, row["crop"], 24)
    expected = forward_surface_reference(extracted, row, adapter["surfaces"]["panel"], mask, (128, 128))
    candidate_path = root / "candidate.png"
    Image.fromarray(expected[:, :, :3], "RGB").save(candidate_path)

    correspondence = {
        "$schema": "shokk-forge.multiview-surface-correspondence/v1",
        "valid": True,
        "correspondence_score": 100.0,
        "registrations": [{
            "accepted": True,
            "view": "camera",
            "surface": "panel_source",
            "quality": 100.0,
            "homography": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        }],
        "views": [{"id": "camera", "crop": [0, 0, 80, 60]}],
    }
    report_path = root / "correspondence.json"
    report_path.write_text(json.dumps(correspondence), encoding="utf-8")
    manifest = {
        "$schema": SCHEMA,
        "template_adapter": str(adapter_path),
        "candidate_composite": str(candidate_path),
        "correspondence_reports": [str(report_path)],
        "minimum_surface_score": 85.0,
        "minimum_view_score": 85.0,
        "minimum_discrimination_margin": 5.0,
        "surfaces": [row],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, candidate_path, adapter


def test_extraction_retains_trim_origin(tmp_path: Path) -> None:
    source = Image.new("RGB", (40, 30), "white")
    ImageDraw.Draw(source).rectangle((7, 5, 31, 24), fill=(10, 70, 190))
    path = tmp_path / "source.png"
    source.save(path)
    extracted, origin = extract_asset_with_origin(path, [0, 0, 40, 30], 24)
    assert origin == (7, 5)
    assert extracted.size == (25, 20)


def test_exact_candidate_pixels_roundtrip_through_camera(tmp_path: Path) -> None:
    manifest_path, _candidate_path, _adapter = _write_fixture(tmp_path)
    report = run(manifest_path, tmp_path / "output")
    assert report["valid"] is True
    assert report["candidate_sha256"] == hashlib.sha256(_candidate_path.read_bytes()).hexdigest()
    assert report["surfaces"][0]["direct_uv_score"] >= 99.0
    assert report["views"][0]["candidate_pixel_roundtrip_score"] >= 90.0
    assert report["stress_tests"]["minimum_discrimination_margin"] >= 5.0


def test_reflected_compiled_candidate_is_rejected(tmp_path: Path) -> None:
    manifest_path, candidate_path, adapter = _write_fixture(tmp_path)
    candidate = np.asarray(Image.open(candidate_path).convert("RGB"), dtype=np.uint8).copy()
    x0, y0, x1, y1 = adapter["surfaces"]["panel"]["bbox"]
    candidate[y0:y1, x0:x1] = candidate[y0:y1, x0:x1][:, ::-1]
    reflected_path = tmp_path / "reflected.png"
    Image.fromarray(candidate, "RGB").save(reflected_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_composite"] = str(reflected_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = run(manifest_path, tmp_path / "reflected_output")
    assert report["valid"] is False
    assert report["surfaces"][0]["discrimination_margin"] < 0.0
