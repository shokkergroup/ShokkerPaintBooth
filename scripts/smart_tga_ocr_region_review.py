"""Build and score a bounded visual review corpus for mirrored Smart TGA OCR."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw


SCHEMA = "spb-smart-tga-ocr-region-review-v1"
OWNERS = ("numbers", "sponsors", "template", "brand_graphics", "paint")
VALID_LABELS = {
    "readable_wordmark", "garbled", "already_sponsor",
    "missed_paint_template", "unsafe_overlap",
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in value)[:120]


def _mask_polygon(shape: tuple[int, int], polygon: list[list[float]]) -> np.ndarray:
    mask = np.zeros(shape, np.uint8)
    points = np.asarray(polygon, np.float32).reshape(-1, 2)
    points[:, 0] = np.clip(points[:, 0], 0, shape[1] - 1)
    points[:, 1] = np.clip(points[:, 1], 0, shape[0] - 1)
    if len(points) >= 3:
        cv2.fillPoly(mask, [np.rint(points).astype(np.int32)], 1)
    return mask > 0


def _scale_region(region: dict[str, Any], source_shape: list[int], target_shape: tuple[int, int]) -> dict[str, Any]:
    source_h, source_w = [max(1, int(v)) for v in source_shape[:2]]
    target_h, target_w = target_shape
    sx, sy = target_w / source_w, target_h / source_h
    polygon = region.get("polygon")
    if polygon:
        scaled_polygon = [[float(p[0]) * sx, float(p[1]) * sy] for p in polygon]
    else:
        x, y, width, height = [float(v) for v in region["bbox"][:4]]
        scaled_polygon = [
            [x * sx, y * sy], [(x + width) * sx, y * sy],
            [(x + width) * sx, (y + height) * sy], [x * sx, (y + height) * sy],
        ]
    xs = [p[0] for p in scaled_polygon]; ys = [p[1] for p in scaled_polygon]
    return {
        **region,
        "polygon": scaled_polygon,
        "bbox": [
            int(round(min(xs))), int(round(min(ys))),
            max(1, int(round(max(xs) - min(xs)))),
            max(1, int(round(max(ys) - min(ys)))),
        ],
    }


def _crop(source: Image.Image, polygon: list[list[float]], label: str, path: Path) -> str:
    xs = [p[0] for p in polygon]; ys = [p[1] for p in polygon]
    pad = 36
    x0, y0 = max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad)
    x1, y1 = min(source.width, int(max(xs)) + pad), min(source.height, int(max(ys)) + pad)
    crop = source.crop((x0, y0, x1, y1)).convert("RGB")
    draw = ImageDraw.Draw(crop)
    points = [(int(round(x - x0)), int(round(y - y0))) for x, y in polygon]
    draw.line(points + [points[0]], fill=(255, 60, 210), width=3)
    draw.rectangle((0, 0, min(crop.width, 430), 18), fill=(8, 12, 18))
    draw.text((3, 3), label[:68], fill=(255, 120, 225))
    path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(path)
    return str(path.resolve())


def extract(run_paths: Iterable[Path], cache_root: Path, output: Path) -> list[dict[str, Any]]:
    reviews = []
    seen = set()
    for run_path in run_paths:
        for record in _read(run_path / "inspection_records.json"):
            if not record.get("success"):
                continue
            source = Image.open(record["source_1024"]).convert("RGB")
            shape = (source.height, source.width)
            cache_key = str((record.get("route_gpu_cache") or {}).get("cache_key") or "")
            sidecar = cache_root / cache_key / "ocr_regions.json"
            if not sidecar.is_file():
                continue
            payload = _read(sidecar)
            owner_masks = {}
            for owner in OWNERS:
                path = (record.get("mask_paths") or {}).get(owner)
                if path and Path(path).is_file():
                    owner_masks[owner] = np.asarray(Image.open(path).convert("L")) > 127
            for raw in payload.get("regions") or []:
                if not raw.get("mirrored"):
                    continue
                region = _scale_region(dict(raw), payload.get("shape") or list(shape), shape)
                review_id = f"{record['paint_label']}::{region.get('id')}::{region.get('text')}"
                if review_id in seen:
                    continue
                seen.add(review_id)
                mask = _mask_polygon(shape, region["polygon"])
                area = int(mask.sum())
                owner_pixels = {
                    owner: int(np.count_nonzero(mask & owner_mask))
                    for owner, owner_mask in owner_masks.items()
                    if np.any(mask & owner_mask)
                }
                dominant_owner = max(owner_pixels, key=owner_pixels.get) if owner_pixels else "unknown"
                item = {
                    "id": review_id,
                    "paint_label": record["paint_label"],
                    "region_id": region.get("id"),
                    "text": str(region.get("text") or ""),
                    "confidence": round(float(region.get("confidence") or 0), 6),
                    "quality_basis": str(region.get("quality_basis") or "legacy_mirror"),
                    "cross_view_exact": bool(region.get("cross_view_exact")),
                    "repeated_mirror_family": bool(region.get("repeated_mirror_family")),
                    "bbox": region["bbox"],
                    "polygon": region["polygon"],
                    "polygon_area": area,
                    "owner_pixels": owner_pixels,
                    "dominant_owner": dominant_owner,
                    "label": "",
                    "notes": "",
                }
                label = f"{len(reviews):02d} {item['confidence']:.2f} {item['text']} {dominant_owner}"
                item["crop"] = _crop(
                    source, region["polygon"], label,
                    output / "crops" / f"{len(reviews):03d}_{_safe(record['paint_label'])}_{_safe(str(region.get('id')))}.png",
                )
                reviews.append(item)
    return reviews


def _metrics(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = [item for item in reviews if item.get("label") in VALID_LABELS]
    readable = [item for item in reviewed if item["label"] in {"readable_wordmark", "already_sponsor", "missed_paint_template"}]
    by_basis = {}
    for basis in sorted({str(item.get("quality_basis")) for item in reviews}):
        entries = [item for item in reviews if item.get("quality_basis") == basis]
        done = [item for item in entries if item.get("label") in VALID_LABELS]
        good = [item for item in done if item["label"] in {"readable_wordmark", "already_sponsor", "missed_paint_template"}]
        by_basis[basis] = {
            "predictions": len(entries), "reviewed": len(done), "readable": len(good),
            "readable_precision": len(good) / max(1, len(done)),
        }
    owner_predictions = Counter(str(item.get("dominant_owner")) for item in reviews)
    return {
        "prediction_count": len(reviews),
        "reviewed_count": len(reviewed),
        "all_predictions_reviewed": len(reviewed) == len(reviews),
        "readable_count": len(readable),
        "readable_precision": len(readable) / max(1, len(reviewed)),
        "unsafe_overlap_count": sum(item.get("label") == "unsafe_overlap" for item in reviewed),
        "unsafe_overlap_rate": sum(item.get("label") == "unsafe_overlap" for item in reviewed) / max(1, len(reviewed)),
        "labels": dict(Counter(str(item.get("label")) for item in reviewed)),
        "dominant_owner_predictions": dict(sorted(owner_predictions.items())),
        "by_quality_basis": by_basis,
    }


def _contact_sheet(reviews: list[dict[str, Any]], path: Path) -> str:
    cell_w, cell_h, columns = 320, 220, 4
    rows = (len(reviews) + columns - 1) // columns
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), (12, 16, 22))
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(reviews):
        crop = Image.open(item["crop"]).convert("RGB")
        crop.thumbnail((cell_w - 8, cell_h - 54), Image.Resampling.LANCZOS)
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        sheet.paste(crop, (x + 4, y + 4))
        draw.text((x + 4, y + cell_h - 47), f"{index:02d} {item['text'][:22]} {item['confidence']:.2f}", fill=(255, 140, 225))
        draw.text((x + 4, y + cell_h - 31), f"{item['dominant_owner']} | {item.get('label') or 'UNREVIEWED'}", fill=(205, 220, 235))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.resolve())


def build(run_paths: list[Path], cache_root: Path, manifest_path: Path, output: Path) -> dict[str, Any]:
    existing = _read(manifest_path) if manifest_path.is_file() else {"reviews": []}
    labels = {item["id"]: item for item in existing.get("reviews") or []}
    reviews = extract(run_paths, cache_root, output)
    for item in reviews:
        prior = labels.get(item["id"])
        if prior:
            item["label"] = str(prior.get("label") or "")
            item["notes"] = str(prior.get("notes") or "")
    # Keep the committed reviewer authority compact. Reconstructed polygons,
    # owner pixels, and crop paths belong to the generated output, not source.
    decisions = {
        "schema": SCHEMA,
        "reviews": [
            {
                "id": item["id"], "label": item.get("label") or "", "notes": item.get("notes") or "",
                "quality_basis": item.get("quality_basis") or "untyped",
                "dominant_owner": item.get("dominant_owner") or "unknown",
            }
            for item in reviews
        ],
    }
    manifest_path.write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    metrics = _metrics(reviews)
    contact = _contact_sheet(reviews, output / "contact_sheet.png")
    summary = {"schema": SCHEMA, "manifest": str(manifest_path.resolve()), "metrics": metrics, "contact_sheet": contact, "reviews": reviews}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    rows = "".join(
        f"<tr><td>{i}</td><td>{html.escape(item['paint_label'])}</td><td>{html.escape(item['text'])}</td>"
        f"<td>{item['confidence']:.3f}</td><td>{html.escape(item['quality_basis'])}</td>"
        f"<td>{html.escape(item['dominant_owner'])}</td><td>{html.escape(item.get('label') or 'UNREVIEWED')}</td>"
        f"<td><a href='{Path(item['crop']).as_uri()}'>crop</a></td></tr>"
        for i, item in enumerate(reviews)
    )
    (output / "review.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Smart TGA OCR Region Review</title>"
        "<style>body{font:14px system-ui;background:#10151d;color:#e8edf5}table{border-collapse:collapse;width:100%}td,th{border:1px solid #354153;padding:6px}a{color:#79c8ff}</style>"
        f"<h1>Smart TGA OCR Region Review</h1><pre>{html.escape(json.dumps(metrics, indent=2))}</pre>"
        f"<p><a href='{Path(contact).as_uri()}'>contact sheet</a></p><table><tr><th>#</th><th>Paint</th><th>Text</th><th>Confidence</th><th>Basis</th><th>Owner</th><th>Label</th><th>Crop</th></tr>{rows}</table>",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, default=Path("_smart_tga_runs/gpu_cache"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = build(args.run, args.cache_root, args.manifest, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
