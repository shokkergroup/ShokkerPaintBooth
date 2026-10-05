"""Audit Smart TGA `car_decal_*` companion sponsor/contingency overlays.

This is offline Smart TGA tooling. It scans a local iRacing paint tree for
`car_decal_<id>.tga` files, classifies available `car_<id>.tga` and
`car_num_<id>.tga` sources with the same conservative gates used by the live
Smart Separate companion-decal path, and can export expected Sponsor masks.
It does not affect Auto-build Layers.
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
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_decal_companion_audit")
WORK = 1024


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:100] or "sample"


def _read_rgb(path: Path, size: int = WORK) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS))


def _read_decal(path: Path, size: int = WORK) -> Image.Image:
    return Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.NEAREST)


def _clamped(value: Any, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


def _find_decal_sources(paint_root: Path, source_mode: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for folder in sorted([p for p in paint_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        for decal in sorted(folder.glob("car_decal_*.tga"), key=lambda p: p.name.lower()):
            car_id = decal.stem[len("car_decal_") :]
            source_candidates = [
                ("car", folder / f"car_{car_id}.tga"),
                ("car_num", folder / f"car_num_{car_id}.tga"),
            ]
            existing = [(kind, path) for kind, path in source_candidates if path.is_file()]
            if source_mode == "prefer-car-num":
                existing = sorted(existing, key=lambda item: 0 if item[0] == "car_num" else 1)[:1]
            elif source_mode == "prefer-car":
                existing = sorted(existing, key=lambda item: 0 if item[0] == "car" else 1)[:1]

            if not existing:
                rows.append({
                    "folder": folder.name,
                    "id": car_id,
                    "source_kind": None,
                    "source": None,
                    "decal": str(decal),
                    "status": "rejected",
                    "reason": "missing_source",
                })
                continue
            for source_kind, source_path in existing:
                rows.append({
                    "folder": folder.name,
                    "id": car_id,
                    "source_kind": source_kind,
                    "source": str(source_path),
                    "decal": str(decal),
                })
    return rows


def _source_diff_fraction(source_rgb: np.ndarray, current_rgb: np.ndarray) -> float:
    diff = np.max(np.abs(current_rgb.astype(np.int16) - source_rgb.astype(np.int16)), axis=2) > 18
    return float(diff.mean())


def _rgb_opaque_foreground_mask(rgb_decal: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    hsv = cv2.cvtColor(rgb_decal, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    bg_dark = (val < 12) & (sat < 45)
    bg_white = (val > 245) & (sat < 20)
    rgb_mask = (~(bg_dark | bg_white)) & ((sat > 35) | (val > 35))
    rgb_clean = cv2.morphologyEx(rgb_mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    n_rgb, labels_rgb, stats_rgb, _cent_rgb = cv2.connectedComponentsWithStats(rgb_clean.astype(np.uint8), 8)
    keep_rgb = [idx for idx in range(1, n_rgb) if int(stats_rgb[idx, cv2.CC_STAT_AREA]) >= 24]
    rgb_comp_fracs = [float(stats_rgb[idx, cv2.CC_STAT_AREA]) / float(WORK * WORK) for idx in keep_rgb]
    rgb_frac = float(rgb_clean.mean())
    rgb_largest = max(rgb_comp_fracs or [0.0])
    candidate = np.isin(labels_rgb, keep_rgb) if keep_rgb else np.zeros_like(rgb_clean, dtype=bool)
    info = {
        "rgb_frac": round(rgb_frac, 6),
        "rgb_components": len(rgb_comp_fracs),
        "rgb_largest_component": round(rgb_largest, 6),
    }
    return candidate, info


def _bbox_stats(mask: np.ndarray) -> dict[str, Any]:
    ys, xs = np.where(mask)
    total = max(1, int(mask.sum()))
    if len(xs) == 0:
        return {
            "bbox_w": 0.0,
            "bbox_h": 0.0,
            "left_frac": 0.0,
            "right_frac": 0.0,
            "centroid_x": 0.0,
            "centroid_y": 0.0,
        }
    return {
        "bbox_w": round((int(xs.max()) - int(xs.min()) + 1) / float(WORK), 4),
        "bbox_h": round((int(ys.max()) - int(ys.min()) + 1) / float(WORK), 4),
        "left_frac": round(float(mask[:, : WORK // 2].sum()) / total, 4),
        "right_frac": round(float(mask[:, WORK // 2 :].sum()) / total, 4),
        "centroid_x": round(float(xs.mean()) / float(WORK), 4),
        "centroid_y": round(float(ys.mean()) / float(WORK), 4),
    }


def _component_mask(mask: np.ndarray, min_area: int = 24) -> tuple[np.ndarray, list[float]]:
    n, labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    keep = [idx for idx in range(1, n) if int(stats[idx, cv2.CC_STAT_AREA]) >= min_area]
    comp_fracs = [float(stats[idx, cv2.CC_STAT_AREA]) / float(WORK * WORK) for idx in keep]
    if not keep:
        return np.zeros_like(mask, dtype=bool), comp_fracs
    return np.isin(labels, keep), comp_fracs


def _classify_row(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not row.get("source"):
        return dict(row)

    source_path = Path(str(row["source"]))
    decal_path = Path(str(row["decal"]))
    record = dict(row)
    source_limit = _clamped(args.source_max, 0.16, 0.08, 0.35)
    alpha_min = _clamped(args.alpha_min, 0.00025, 0.00005, 0.005)
    alpha_max = _clamped(args.alpha_max, 0.12, 0.02, 0.25)

    source_rgb = _read_rgb(source_path)
    current_rgb = source_rgb
    source_diff = _source_diff_fraction(source_rgb, current_rgb)
    record.update({
        "source_diff": round(source_diff, 6),
        "source_limit": round(source_limit, 6),
        "alpha_min": round(alpha_min, 6),
        "alpha_max": round(alpha_max, 6),
    })
    if source_diff > source_limit:
        record.update({"status": "rejected", "reason": "source_mismatch"})
        return record

    decal = _read_decal(decal_path)
    alpha = np.asarray(decal.getchannel("A"), dtype=np.uint8)
    mask = alpha > 8
    alpha_frac_raw = float(mask.mean())
    record["alpha_frac_raw"] = round(alpha_frac_raw, 6)
    mask_source = "alpha"

    if alpha_frac_raw < alpha_min or alpha_frac_raw > alpha_max:
        if args.rgb_fallback and alpha_frac_raw > 0.98:
            rgb_decal = np.asarray(decal.convert("RGB"), dtype=np.uint8)
            rgb_candidate, rgb_info = _rgb_opaque_foreground_mask(rgb_decal)
            record.update(rgb_info)
            bbox = _bbox_stats(rgb_candidate)
            rgb_ok = (
                0.001 <= float(record["rgb_frac"]) <= 0.025
                and 1 <= int(record["rgb_components"]) <= 48
                and float(record["rgb_largest_component"]) <= 0.012
                and not (bbox["bbox_w"] > 0.92 and bbox["bbox_h"] > 0.92)
            )
            if not rgb_ok:
                record.update({
                    "status": "rejected",
                    "reason": "alpha_area_rejected",
                    "alpha_frac": round(alpha_frac_raw, 6),
                })
                record.update(bbox)
                return record
            mask = rgb_candidate
            mask_source = "rgb_opaque_fallback"
        else:
            record.update({
                "status": "rejected",
                "reason": "alpha_area_rejected",
                "alpha_frac": round(alpha_frac_raw, 6),
            })
            return record

    clean, comp_fracs = _component_mask(mask)
    if not comp_fracs:
        record.update({
            "status": "rejected",
            "reason": "empty_after_cleanup",
            "alpha_frac": round(float(mask.mean()), 6),
            "mask_source": mask_source,
        })
        return record
    if len(comp_fracs) > 160 or max(comp_fracs) > 0.08:
        record.update({
            "status": "rejected",
            "reason": "component_shape_rejected",
            "alpha_frac": round(float(mask.mean()), 6),
            "mask_source": mask_source,
            "components": len(comp_fracs),
            "largest_component": round(max(comp_fracs or [0.0]), 6),
        })
        return record

    bbox = _bbox_stats(clean)
    if bbox["bbox_w"] > 0.92 and bbox["bbox_h"] > 0.92:
        record.update({
            "status": "rejected",
            "reason": "whole_canvas_bbox",
            "alpha_frac": round(float(clean.mean()), 6),
            "mask_source": mask_source,
            "components": len(comp_fracs),
            "largest_component": round(max(comp_fracs), 6),
        })
        record.update(bbox)
        return record

    record.update({
        "status": "applied",
        "reason": None,
        "mask_source": mask_source,
        "alpha_frac": round(float(clean.mean()), 6),
        "components": len(comp_fracs),
        "largest_component": round(max(comp_fracs), 6),
    })
    record.update(bbox)
    return record


def _final_mask(record: dict[str, Any]) -> np.ndarray:
    if record.get("status") != "applied" or not record.get("decal"):
        return np.zeros((WORK, WORK), dtype=np.uint8)
    decal = _read_decal(Path(str(record["decal"])))
    if record.get("mask_source") == "rgb_opaque_fallback":
        rgb_decal = np.asarray(decal.convert("RGB"), dtype=np.uint8)
        mask, _info = _rgb_opaque_foreground_mask(rgb_decal)
    else:
        alpha = np.asarray(decal.getchannel("A"), dtype=np.uint8)
        mask = alpha > 8
    clean, _comp_fracs = _component_mask(mask)
    return clean.astype(np.uint8) * 255


def _decal_preview(record: dict[str, Any], size: int = 384) -> Image.Image:
    decal = Image.open(record["decal"]).convert("RGBA").resize((size, size), Image.Resampling.NEAREST)
    bg = Image.new("RGBA", decal.size, (22, 22, 22, 255))
    bg.alpha_composite(decal)
    return bg.convert("RGB")


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str, applied: bool) -> None:
    if not records:
        return
    cols = 5
    cell = 230
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (25, 25, 25))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        if applied and rec.get("source"):
            source = Image.fromarray(_read_rgb(Path(str(rec["source"])), 384)).convert("RGBA")
            mask = Image.fromarray(_final_mask(rec), "L").resize(source.size, Image.Resampling.NEAREST)
            tint = Image.new("RGBA", source.size, (255, 60, 190, 135))
            source.alpha_composite(Image.composite(tint, Image.new("RGBA", source.size, (0, 0, 0, 0)), mask))
            img = source.convert("RGB").resize((172, 172), Image.Resampling.LANCZOS)
        else:
            img = _decal_preview(rec, 384).resize((172, 172), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 28, y + 27))
        label = f"{rec.get('status')} {rec.get('mask_source') or rec.get('reason') or ''}"
        detail = f"a={rec.get('alpha_frac', rec.get('alpha_frac_raw', 0))} c={rec.get('components', '')}"
        draw.text((x + 7, y + 5), label[:34], fill=(255, 230, 160))
        draw.text((x + 7, y + 201), f"{rec['folder']} {rec['id']} {rec.get('source_kind') or ''}"[:34], fill=(220, 220, 220))
        draw.text((x + 7, y + 215), detail[:34], fill=(190, 210, 255))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _export_applied_masks(records: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    exported: list[dict[str, Any]] = []
    mask_dir = out_dir / "applied_masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        stem = _safe_name(f"{rec['folder']}_{rec['id']}_{rec.get('source_kind')}_{rec.get('mask_source')}")
        sample_dir = mask_dir / stem
        sample_dir.mkdir(parents=True, exist_ok=True)
        source = Image.fromarray(_read_rgb(Path(str(rec["source"])))).convert("RGB")
        decal_preview = _decal_preview(rec, WORK)
        mask = Image.fromarray(_final_mask(rec), "L")
        overlay = source.convert("RGBA")
        tint = Image.new("RGBA", overlay.size, (255, 60, 190, 135))
        overlay.alpha_composite(Image.composite(tint, Image.new("RGBA", overlay.size, (0, 0, 0, 0)), mask))
        source_path = sample_dir / "source_1024.png"
        decal_path = sample_dir / "decal_visual_1024.png"
        mask_path = sample_dir / "expected_sponsor_decal_mask.png"
        overlay_path = sample_dir / "expected_sponsor_decal_overlay.png"
        source.save(source_path)
        decal_preview.save(decal_path)
        mask.save(mask_path)
        overlay.convert("RGB").save(overlay_path)
        entry = dict(rec)
        entry.update({
            "source_1024": str(source_path.resolve()),
            "decal_visual_1024": str(decal_path.resolve()),
            "expected_sponsor_decal_mask": str(mask_path.resolve()),
            "expected_sponsor_decal_overlay": str(overlay_path.resolve()),
        })
        exported.append(entry)
    manifest_path = mask_dir / "manifest.json"
    manifest_path.write_text(json.dumps(exported, indent=2), encoding="utf-8")
    return {
        "exported_applied_masks": len(exported),
        "applied_mask_manifest": str(manifest_path.resolve()),
        "applied_mask_dir": str(mask_dir.resolve()),
    }


def audit_decals(args: argparse.Namespace) -> dict[str, Any]:
    rows = _find_decal_sources(args.paint_root, args.source_mode)
    if args.limit:
        rows = rows[: args.limit]
    records = [_classify_row(row, args) for row in rows]
    args.output.mkdir(parents=True, exist_ok=True)
    all_records_path = args.output / "all_records.json"
    all_records_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    applied = [rec for rec in records if rec.get("status") == "applied"]
    rejected = [rec for rec in records if rec.get("status") != "applied"]
    _contact_sheet(applied, args.output / "applied_contact_sheet.png", "Applied companion decal Sponsor masks", True)
    _contact_sheet(rejected[:50], args.output / "rejected_contact_sheet.png", "Rejected companion decals", False)

    unique_decals = {str(rec.get("decal")) for rec in records if rec.get("decal")}
    applied_unique_decals = {str(rec.get("decal")) for rec in applied if rec.get("decal")}
    summary = {
        "paint_root": str(args.paint_root),
        "source_mode": args.source_mode,
        "decals": len(unique_decals),
        "source_rows": len(records),
        "applied_rows": len(applied),
        "rejected_rows": len(rejected),
        "applied_unique_decals": len(applied_unique_decals),
        "mask_sources": dict(Counter(str(rec.get("mask_source") or "none") for rec in applied)),
        "reasons": dict(Counter(str(rec.get("reason") or "applied") for rec in records)),
        "folders_with_applied": sorted({str(rec["folder"]) for rec in applied}),
        "all_records": str(all_records_path.resolve()),
        "applied_contact_sheet": str((args.output / "applied_contact_sheet.png").resolve()) if applied else None,
        "rejected_contact_sheet": str((args.output / "rejected_contact_sheet.png").resolve()) if rejected else None,
    }
    if args.export_applied_masks:
        summary.update(_export_applied_masks(applied, args.output))
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paint-root", type=Path, default=DEFAULT_PAINT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--source-mode",
        choices=("all", "prefer-car-num", "prefer-car"),
        default="all",
        help="Audit every available source row, or one preferred source per decal.",
    )
    parser.add_argument("--source-max", type=float, default=0.16)
    parser.add_argument("--alpha-min", type=float, default=0.00025)
    parser.add_argument("--alpha-max", type=float, default=0.12)
    parser.add_argument("--disable-rgb-fallback", dest="rgb_fallback", action="store_false")
    parser.add_argument(
        "--export-applied-masks",
        action="store_true",
        help="For applied decals, write source/decal PNGs, cleaned expected Sponsor masks, and a manifest.",
    )
    parser.set_defaults(rgb_fallback=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(audit_decals(parse_args()), indent=2))


if __name__ == "__main__":
    main()
