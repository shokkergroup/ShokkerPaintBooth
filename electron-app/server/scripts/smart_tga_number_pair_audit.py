"""Audit iRacing `car_*` / `car_num_*` pairs for sparse number overlays.

This is offline Smart TGA tooling. It scans a local iRacing paint tree and
classifies exact `car_<id>.tga` + `car_num_<id>.tga` pairs with conservative
area/component/bbox gates modeled after the live companion-number supplement.
It does not affect app behavior.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


DEFAULT_PAINT_ROOT = Path(r"C:\Users\Ricky's PC\Documents\iRacing\paint")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_number_pair_audit")
WORK = 1024


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:90] or "sample"


def _read_rgb(path: Path, size: int = WORK) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS))


def _find_exact_pairs(paint_root: Path) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for folder in sorted([p for p in paint_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        cars = {
            p.stem[4:]: p
            for p in folder.glob("car_*.tga")
            if not p.stem.startswith(("car_num_", "car_team_", "car_decal_"))
        }
        nums = {p.stem[8:]: p for p in folder.glob("car_num_*.tga")}
        for car_id in sorted(set(cars) & set(nums), key=lambda v: (len(v), v)):
            pairs.append({
                "folder": folder.name,
                "id": car_id,
                "car": str(cars[car_id]),
                "car_num": str(nums[car_id]),
            })
    return pairs


def _classify_pair(pair: dict[str, Any]) -> dict[str, Any]:
    base = _read_rgb(Path(pair["car"])).astype(np.int16)
    comp = _read_rgb(Path(pair["car_num"])).astype(np.int16)
    rgb_delta = np.max(np.abs(base - comp), axis=2)
    loose = rgb_delta > 18
    mask = rgb_delta > 45
    frac = float(mask.mean())
    loose_frac = float(loose.mean())
    result = dict(pair)
    result.update({
        "delta_frac": round(frac, 6),
        "loose_delta_frac": round(loose_frac, 6),
    })
    if frac < 0.002 or frac > 0.075 or loose_frac > 0.16:
        result.update({"status": "rejected", "reason": "delta_area_rejected"})
        return _add_shape_stats(result, mask)

    clean = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    n, labels, stats, _cent = cv2.connectedComponentsWithStats(clean.astype(np.uint8), 8)
    keep = [idx for idx in range(1, n) if int(stats[idx, cv2.CC_STAT_AREA]) >= 80]
    comp_fracs = [float(stats[idx, cv2.CC_STAT_AREA]) / float(WORK * WORK) for idx in keep]
    if not keep or len(comp_fracs) > 48 or max(comp_fracs) > 0.035:
        result.update({
            "status": "rejected",
            "reason": "component_shape_rejected",
            "components": len(comp_fracs),
            "largest_component": round(max(comp_fracs or [0.0]), 6),
        })
        return _add_shape_stats(result, np.isin(labels, keep) if keep else clean)

    clean = np.isin(labels, keep)
    ys, xs = np.where(clean)
    if len(xs) == 0:
        result.update({"status": "rejected", "reason": "empty_after_cleanup"})
        return _add_shape_stats(result, clean)
    bbox_w = (int(xs.max()) - int(xs.min()) + 1) / float(WORK)
    bbox_h = (int(ys.max()) - int(ys.min()) + 1) / float(WORK)
    if bbox_w > 0.92 and bbox_h > 0.92:
        result.update({"status": "rejected", "reason": "whole_canvas_bbox"})
        return _add_shape_stats(result, clean)
    result.update({
        "status": "safe",
        "reason": None,
        "components": len(comp_fracs),
        "largest_component": round(max(comp_fracs), 6),
    })
    return _add_shape_stats(result, clean)


def _safe_pair_mask(pair: dict[str, Any]) -> np.ndarray:
    """Return the cleaned companion-number mask for a pair already classified safe."""
    base = _read_rgb(Path(pair["car"])).astype(np.int16)
    comp = _read_rgb(Path(pair["car_num"])).astype(np.int16)
    rgb_delta = np.max(np.abs(base - comp), axis=2)
    mask = rgb_delta > 45
    clean = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    n, labels, stats, _cent = cv2.connectedComponentsWithStats(clean.astype(np.uint8), 8)
    keep = [idx for idx in range(1, n) if int(stats[idx, cv2.CC_STAT_AREA]) >= 80]
    if not keep:
        return np.zeros_like(clean, dtype=np.uint8)
    return (np.isin(labels, keep).astype(np.uint8) * 255)


def _add_shape_stats(record: dict[str, Any], mask: np.ndarray) -> dict[str, Any]:
    ys, xs = np.where(mask)
    total = max(1, int(mask.sum()))
    if len(xs) == 0:
        record.update({
            "components": int(record.get("components", 0)),
            "largest_component": float(record.get("largest_component", 0.0)),
            "bbox_w": 0.0,
            "bbox_h": 0.0,
            "left_frac": 0.0,
            "right_frac": 0.0,
            "centroid_x": 0.0,
            "centroid_y": 0.0,
        })
        return record
    if "components" not in record or "largest_component" not in record:
        n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        areas = [int(stats[idx, cv2.CC_STAT_AREA]) for idx in range(1, n) if int(stats[idx, cv2.CC_STAT_AREA]) >= 80]
        record.update({
            "components": len(areas),
            "largest_component": round((max(areas) if areas else 0) / float(WORK * WORK), 6),
        })
    record.update({
        "bbox_w": round((int(xs.max()) - int(xs.min()) + 1) / float(WORK), 4),
        "bbox_h": round((int(ys.max()) - int(ys.min()) + 1) / float(WORK), 4),
        "left_frac": round(float(mask[:, : WORK // 2].sum()) / total, 4),
        "right_frac": round(float(mask[:, WORK // 2 :].sum()) / total, 4),
        "centroid_x": round(float(xs.mean()) / float(WORK), 4),
        "centroid_y": round(float(ys.mean()) / float(WORK), 4),
    })
    return record


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 5
    cell = 220
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        car = _read_rgb(Path(rec["car"]), 384).astype(np.int16)
        car_num = _read_rgb(Path(rec["car_num"]), 384).astype(np.int16)
        delta = np.max(np.abs(car - car_num), axis=2) > 45
        img = Image.fromarray(np.asarray(np.clip(car_num, 0, 255), np.uint8)).resize((168, 168), Image.Resampling.LANCZOS)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        mask_img = Image.fromarray((delta.astype(np.uint8) * 180)).resize(img.size, Image.Resampling.NEAREST)
        overlay.paste((255, 80, 80, 130), mask=mask_img)
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        sheet.paste(img, (x + 26, y + 24))
        draw.text((x + 7, y + 5), f"{rec['status']} {rec.get('reason') or ''}"[:32], fill=(255, 230, 160))
        draw.text((x + 7, y + 194), f"{rec['folder']} {rec['id']}"[:32], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _export_safe_masks(records: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    exported: list[dict[str, Any]] = []
    mask_dir = out_dir / "safe_masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        stem = _safe_name(f"{rec['folder']}_{rec['id']}")
        sample_dir = mask_dir / stem
        sample_dir.mkdir(parents=True, exist_ok=True)
        car = Image.fromarray(_read_rgb(Path(rec["car"]))).convert("RGB")
        car_num = Image.fromarray(_read_rgb(Path(rec["car_num"]))).convert("RGB")
        mask = Image.fromarray(_safe_pair_mask(rec), "L")
        overlay = car_num.convert("RGBA")
        tint = Image.new("RGBA", overlay.size, (255, 70, 70, 120))
        overlay.alpha_composite(Image.composite(tint, Image.new("RGBA", overlay.size, (0, 0, 0, 0)), mask))
        car_path = sample_dir / "source_1024.png"
        car_num_path = sample_dir / "car_num_1024.png"
        mask_path = sample_dir / "expected_numbers_mask.png"
        overlay_path = sample_dir / "expected_numbers_overlay.png"
        car.save(car_path)
        car_num.save(car_num_path)
        mask.save(mask_path)
        overlay.convert("RGB").save(overlay_path)
        entry = dict(rec)
        entry.update({
            "source_1024": str(car_path.resolve()),
            "car_num_1024": str(car_num_path.resolve()),
            "expected_numbers_mask": str(mask_path.resolve()),
            "expected_numbers_overlay": str(overlay_path.resolve()),
        })
        exported.append(entry)
    manifest_path = mask_dir / "manifest.json"
    manifest_path.write_text(json.dumps(exported, indent=2), encoding="utf-8")
    return {
        "exported_safe_masks": len(exported),
        "safe_mask_manifest": str(manifest_path.resolve()),
        "safe_mask_dir": str(mask_dir.resolve()),
    }


def audit_pairs(args: argparse.Namespace) -> dict[str, Any]:
    pairs = _find_exact_pairs(args.paint_root)
    excluded = {str(v).strip() for v in args.exclude_id if str(v).strip()}
    if excluded:
        pairs = [pair for pair in pairs if str(pair["id"]) not in excluded]
    if args.limit:
        pairs = pairs[: args.limit]
    records = [_classify_pair(pair) for pair in pairs]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "all_records.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    safe = [rec for rec in records if rec["status"] == "safe"]
    rejected = [rec for rec in records if rec["status"] != "safe"]
    _contact_sheet(safe, args.output / "safe_contact_sheet.png", "Safe sparse number overlays")
    _contact_sheet(rejected[:40], args.output / "rejected_contact_sheet.png", "Rejected car_num pairs")
    summary = {
        "paint_root": str(args.paint_root),
        "pairs": len(records),
        "safe": len(safe),
        "rejected": len(rejected),
        "reasons": dict(Counter(rec.get("reason") or "safe" for rec in records)),
        "folders_with_safe": sorted({rec["folder"] for rec in safe}),
        "all_records": str((args.output / "all_records.json").resolve()),
        "safe_contact_sheet": str((args.output / "safe_contact_sheet.png").resolve()) if safe else None,
        "rejected_contact_sheet": str((args.output / "rejected_contact_sheet.png").resolve()) if rejected else None,
    }
    if args.export_safe_masks:
        summary.update(_export_safe_masks(safe, args.output))
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paint-root", type=Path, default=DEFAULT_PAINT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--exclude-id", action="append", default=[],
                        help="Skip an exact car/car_num id. Repeatable; useful for non-owner breadth audits.")
    parser.add_argument("--export-safe-masks", action="store_true",
                        help="For safe sparse pairs, write source/car_num PNGs, cleaned expected masks, and a manifest.")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(audit_pairs(parse_args()), indent=2))


if __name__ == "__main__":
    main()
