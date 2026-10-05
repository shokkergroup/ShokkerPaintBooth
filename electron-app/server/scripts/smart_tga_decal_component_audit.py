"""Component-level audit for Smart TGA companion-decal Sponsor fixtures.

The companion-decal route now has whole-mask fixtures. This script breaks those
expected Sponsor masks into individual connected components, computes shape and
color features, and writes contact sheets for likely sponsor/logo/text islands
versus broad livery/paint-band review candidates. It is offline evidence only;
it does not affect Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle103_decal_companion_audit_export_v1/applied_masks/manifest.json")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_decal_component_audit")


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:96] or "sample"


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected manifest list in {path}")
    return data


def _read_rgb(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def _read_mask(path: str, size: tuple[int, int] | None = None) -> np.ndarray:
    img = Image.open(path).convert("L")
    if size and img.size != size:
        img = img.resize(size, Image.Resampling.NEAREST)
    return np.asarray(img) > 127


def _crop_box(x: int, y: int, w: int, h: int, width: int, height: int, pad: int = 18) -> tuple[int, int, int, int]:
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(width, x + w + pad)
    y1 = min(height, y + h + pad)
    return x0, y0, x1, y1


def _edge_density(rgb_crop: np.ndarray, mask_crop: np.ndarray) -> float:
    if not mask_crop.any():
        return 0.0
    gray = cv2.cvtColor(rgb_crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 145) > 0
    return float((edges & mask_crop).sum()) / float(max(1, mask_crop.sum()))


def _color_stats(rgb_crop: np.ndarray, mask_crop: np.ndarray) -> dict[str, Any]:
    pixels = rgb_crop[mask_crop]
    if pixels.size == 0:
        return {
            "mean_saturation": 0.0,
            "mean_value": 0.0,
            "color_clusters": 0,
            "dark_pixel_frac": 0.0,
            "light_pixel_frac": 0.0,
        }
    hsv = cv2.cvtColor(pixels.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    quant = (pixels // 32).astype(np.uint8)
    clusters = len({tuple(int(v) for v in row) for row in quant})
    return {
        "mean_saturation": round(float(hsv[:, 1].mean()) / 255.0, 4),
        "mean_value": round(float(hsv[:, 2].mean()) / 255.0, 4),
        "color_clusters": int(clusters),
        "dark_pixel_frac": round(float((hsv[:, 2] < 40).mean()), 4),
        "light_pixel_frac": round(float((hsv[:, 2] > 220).mean()), 4),
    }


def _role_guess(features: dict[str, Any]) -> str:
    area = float(features["area_frac"])
    bbox_w = float(features["bbox_w_frac"])
    bbox_h = float(features["bbox_h_frac"])
    aspect = float(features["aspect"])
    fill = float(features["fill"])
    color_clusters = int(features["color_clusters"])
    edge = float(features["edge_density"])

    if bbox_w > 0.88 and bbox_h > 0.16:
        return "wide_livery_or_panel_review"
    if bbox_w > 0.88 and bbox_h <= 0.16:
        return "full_width_text_or_stripe_review"
    if area >= 0.025 and fill > 0.28 and color_clusters >= 4:
        return "large_sponsor_graphic_or_panel"
    if aspect >= 8.0 and bbox_h <= 0.08:
        return "thin_textline_or_stripe"
    if area <= 0.0012:
        return "small_contingency_or_logo"
    if edge >= 0.12 and color_clusters >= 3:
        return "logo_or_text_island"
    return "medium_sponsor_or_graphic"


def _priority(features: dict[str, Any]) -> str:
    role = str(features["role_guess"])
    if role.endswith("_review") or role == "thin_textline_or_stripe":
        return "review"
    return "likely_sponsor"


def _component_records_for_fixture(fixture: dict[str, Any], fixture_index: int) -> list[dict[str, Any]]:
    source = _read_rgb(fixture["source_1024"])
    h, w = source.shape[:2]
    mask = _read_mask(fixture["expected_sponsor_decal_mask"], size=(w, h))
    n, labels, stats, cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    records: list[dict[str, Any]] = []
    for idx in range(1, n):
        area_px = int(stats[idx, cv2.CC_STAT_AREA])
        if area_px < 24:
            continue
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        cw = int(stats[idx, cv2.CC_STAT_WIDTH])
        ch = int(stats[idx, cv2.CC_STAT_HEIGHT])
        comp = labels == idx
        x0, y0, x1, y1 = _crop_box(x, y, cw, ch, w, h)
        rgb_crop = source[y0:y1, x0:x1]
        mask_crop = comp[y0:y1, x0:x1]
        fill = area_px / float(max(1, cw * ch))
        features: dict[str, Any] = {
            "fixture_index": fixture_index,
            "component_index": len(records),
            "folder": fixture.get("folder"),
            "id": fixture.get("id"),
            "source_kind": fixture.get("source_kind"),
            "mask_source": fixture.get("mask_source"),
            "source": fixture.get("source"),
            "decal": fixture.get("decal"),
            "area_px": area_px,
            "area_frac": round(area_px / float(w * h), 7),
            "bbox": [x, y, cw, ch],
            "bbox_w_frac": round(cw / float(w), 5),
            "bbox_h_frac": round(ch / float(h), 5),
            "aspect": round(cw / float(max(1, ch)), 4),
            "fill": round(fill, 4),
            "centroid_x": round(float(cent[idx][0]) / float(w), 4),
            "centroid_y": round(float(cent[idx][1]) / float(h), 4),
            "edge_density": round(_edge_density(rgb_crop, mask_crop), 4),
        }
        features.update(_color_stats(rgb_crop, mask_crop))
        features["role_guess"] = _role_guess(features)
        features["priority"] = _priority(features)
        records.append(features)
    return records


def _component_crop(record: dict[str, Any], out_root: Path) -> str:
    source = _read_rgb(str(record["source_1024"]))
    h, w = source.shape[:2]
    mask = _read_mask(str(record["expected_sponsor_decal_mask"]), size=(w, h))
    x, y, bw, bh = [int(v) for v in record["bbox"]]
    x0, y0, x1, y1 = _crop_box(x, y, bw, bh, w, h, pad=32)
    comp = np.zeros_like(mask, dtype=bool)
    comp[y:y + bh, x:x + bw] = mask[y:y + bh, x:x + bw]
    crop = Image.fromarray(source[y0:y1, x0:x1]).convert("RGBA")
    local_mask = Image.fromarray((comp[y0:y1, x0:x1].astype(np.uint8) * 255), "L")
    tint = Image.new("RGBA", crop.size, (255, 60, 190, 140))
    crop.alpha_composite(Image.composite(tint, Image.new("RGBA", crop.size, (0, 0, 0, 0)), local_mask))
    draw = ImageDraw.Draw(crop)
    draw.rectangle((x - x0, y - y0, x + bw - x0 - 1, y + bh - y0 - 1), outline=(255, 255, 255, 255), width=3)
    path = out_root / "component_crops" / f"{int(record['fixture_index']):03d}_{int(record['component_index']):02d}_{_safe_name(str(record['folder']) + '_' + str(record['id']) + '_' + str(record['role_guess']))}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    crop.convert("RGB").save(path)
    return str(path.resolve())


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 5
    cell = 218
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        img = Image.open(rec["crop_file"]).convert("RGB").resize((156, 156), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 31, y + 25))
        draw.text((x + 7, y + 5), str(rec["role_guess"])[:32], fill=(255, 230, 160))
        draw.text((x + 7, y + 184), f"{rec['folder']} {rec['id']}"[:32], fill=(220, 220, 220))
        detail = f"a={rec['area_frac']:.5f} bw={rec['bbox_w_frac']:.2f} ar={rec['aspect']:.1f}"
        draw.text((x + 7, y + 200), detail[:32], fill=(190, 210, 255))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def audit_components(args: argparse.Namespace) -> dict[str, Any]:
    fixtures = _load_manifest(args.manifest)
    if args.limit:
        fixtures = fixtures[: args.limit]
    args.output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for fixture_index, fixture in enumerate(fixtures):
        fixture_records = _component_records_for_fixture(fixture, fixture_index)
        for rec in fixture_records:
            rec.update({
                "source_1024": fixture["source_1024"],
                "expected_sponsor_decal_mask": fixture["expected_sponsor_decal_mask"],
                "expected_sponsor_decal_overlay": fixture["expected_sponsor_decal_overlay"],
                "crop_file": "",
            })
            records.append(rec)

    # Write crops after all records exist so contact sheets can reuse a stable file list.
    for rec in records:
        rec["crop_file"] = _component_crop(rec, args.output)

    likely = [rec for rec in records if rec["priority"] == "likely_sponsor"]
    review = [rec for rec in records if rec["priority"] == "review"]
    wide = [rec for rec in records if str(rec["role_guess"]).endswith("_review")]
    _contact_sheet(records, args.output / "all_components_contact_sheet.png", "All companion-decal components")
    _contact_sheet(likely, args.output / "likely_sponsor_components.png", "Likely Sponsor/Text/Logo components")
    _contact_sheet(review, args.output / "review_components.png", "Review: broad/stripe/panel components")
    _contact_sheet(wide, args.output / "wide_review_components.png", "Wide review components")

    records_path = args.output / "component_records.json"
    records_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    role_counts = Counter(str(rec["role_guess"]) for rec in records)
    fixture_component_counts: dict[str, int] = defaultdict(int)
    for rec in records:
        fixture_component_counts[f"{rec['folder']}|{rec['id']}|{rec['source_kind']}"] += 1
    summary = {
        "manifest": str(args.manifest),
        "fixtures": len(fixtures),
        "components": len(records),
        "likely_sponsor_components": len(likely),
        "review_components": len(review),
        "wide_review_components": len(wide),
        "role_counts": dict(sorted(role_counts.items())),
        "fixture_component_counts": dict(sorted(fixture_component_counts.items())),
        "component_records": str(records_path.resolve()),
        "all_components_contact_sheet": str((args.output / "all_components_contact_sheet.png").resolve()) if records else None,
        "likely_sponsor_components_sheet": str((args.output / "likely_sponsor_components.png").resolve()) if likely else None,
        "review_components_sheet": str((args.output / "review_components.png").resolve()) if review else None,
        "wide_review_components_sheet": str((args.output / "wide_review_components.png").resolve()) if wide else None,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(audit_components(parse_args()), indent=2))


if __name__ == "__main__":
    main()
