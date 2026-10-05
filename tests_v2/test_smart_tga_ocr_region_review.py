import json
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.smart_tga_ocr_region_review import SCHEMA, build
from scripts.smart_tga_golden_corpus_gate import _ocr_region_review_report


def test_ocr_region_review_extracts_distinct_polygon_owner_metrics(tmp_path: Path):
    run = tmp_path / "run"
    sample = run / "sample"
    masks = sample / "masks"
    cache = tmp_path / "cache" / "abc"
    output = tmp_path / "review"
    masks.mkdir(parents=True)
    cache.mkdir(parents=True)
    rgb = np.zeros((32, 32, 3), np.uint8)
    rgb[:, :] = [24, 32, 40]
    source = sample / "source.png"
    Image.fromarray(rgb, "RGB").save(source)
    paths = {}
    for owner in ("numbers", "sponsors", "template", "brand_graphics", "paint"):
        mask = np.zeros((32, 32), np.uint8)
        if owner == "sponsors":
            mask[8:16, 8:20] = 255
        elif owner == "paint":
            mask[:, :] = 255
            mask[8:16, 8:20] = 0
        path = masks / f"{owner}.png"
        Image.fromarray(mask, "L").save(path)
        paths[owner] = str(path)
    (cache / "ocr_regions.json").write_text(json.dumps({
        "shape": [32, 32],
        "regions": [{
            "id": "gpu-mirror-word-0", "mirrored": True, "text": "MOTUL",
            "confidence": 0.91, "quality_basis": "cross_view_exact",
            "cross_view_exact": True,
            "polygon": [[8, 8], [20, 8], [20, 16], [8, 16]],
        }],
    }), encoding="utf-8")
    (run / "inspection_records.json").write_text(json.dumps([{
        "success": True, "paint_label": "fixture/car.tga", "source_1024": str(source),
        "route_gpu_cache": {"cache_key": "abc"}, "mask_paths": paths,
    }]), encoding="utf-8")
    manifest = tmp_path / "reviews.json"
    first = build([run], tmp_path / "cache", manifest, output)
    assert first["schema"] == SCHEMA
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(payload["reviews"]) == 1
    review = first["reviews"][0]
    assert review["dominant_owner"] == "sponsors"
    assert review["owner_pixels"]["sponsors"] > 0
    payload["reviews"][0]["label"] = "readable_wordmark"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    second = build([run], tmp_path / "cache", manifest, output)
    assert second["metrics"]["all_predictions_reviewed"] is True
    assert second["metrics"]["readable_precision"] == 1.0
    assert second["metrics"]["by_quality_basis"]["cross_view_exact"]["readable"] == 1
    assert Path(second["contact_sheet"]).is_file()


def test_golden_gate_requires_complete_ocr_region_review_coverage(tmp_path: Path):
    review_path = tmp_path / "ocr_reviews.json"
    reviews = [
        {
            "id": f"r{i}", "label": "garbled", "notes": "reviewed",
            "quality_basis": "legacy_mirror", "dominant_owner": "paint",
        }
        for i in range(10)
    ]
    review_path.write_text(json.dumps({"schema": SCHEMA, "reviews": reviews}), encoding="utf-8")
    manifest_path = tmp_path / "golden.json"
    manifest = {"ocr_region_review_manifest": review_path.name}
    report = _ocr_region_review_report(manifest, manifest_path)
    assert report["passed"] is True
    assert report["all_predictions_reviewed"] is True
    assert report["reviewed_count"] == 10
    assert report["readable_precision"] == 0.0
    reviews[0]["label"] = ""
    review_path.write_text(json.dumps({"schema": SCHEMA, "reviews": reviews}), encoding="utf-8")
    assert _ocr_region_review_report(manifest, manifest_path)["passed"] is False
