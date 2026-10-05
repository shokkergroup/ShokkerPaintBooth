"""Classify Smart TGA false-positive proposal pressure into rough visual subtypes.

This is offline Smart TGA tooling. It reads ranker outputs such as
``hard_negative_pressure_records.json`` or ``top_unmatched_candidates.json``,
recrops the original iRacing TGA regions, computes simple region features, and
writes subtype summaries/contact sheets. The goal is to turn "sponsors/logos are
still fooling number detection" into reusable evidence before any runtime hook.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from smart_tga_number_candidate_miner import _read_rgb
from smart_tga_number_proposal_ranker import _number_stroke_score_from_crop


DEFAULT_RECORDS = Path("_smart_tga_runs/cycle90_ranker_side_panel160_sibling_digit_gate045_v1/hard_negative_pressure_records.json")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_hard_negative_taxonomy")
WORK = 1024


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:86] or "unknown"


def _box_from_record(record: dict[str, Any], prefer: str) -> list[int] | None:
    if prefer == "best":
        candidate = record.get("best_candidate") or record.get("best_iou_candidate") or {}
        box = candidate.get("xyxy") or candidate.get("box")
        if isinstance(box, list) and len(box) == 4:
            return [int(v) for v in box]
    for key in ("xyxy", "box", "gt_box"):
        box = record.get(key)
        if isinstance(box, list) and len(box) == 4:
            return [int(v) for v in box]
    return None


def _source_from_record(record: dict[str, Any]) -> Path | None:
    for key in ("source_path", "paint", "car"):
        raw = record.get(key)
        if raw:
            path = Path(str(raw))
            if path.is_file():
                return path
    candidate = record.get("best_candidate") or record.get("best_iou_candidate") or {}
    for key in ("paint", "source_path"):
        raw = candidate.get(key)
        if raw:
            path = Path(str(raw))
            if path.is_file():
                return path
    return None


def _crop_with_context(rgb: np.ndarray, box: list[int], pad: int = 28) -> tuple[Image.Image, list[int]]:
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = [int(v) for v in box]
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    cx0 = max(0, x0 - pad)
    cy0 = max(0, y0 - pad)
    cx1 = min(width, x1 + pad)
    cy1 = min(height, y1 + pad)
    crop = Image.fromarray(rgb[cy0:cy1, cx0:cx1]).convert("RGB")
    return crop, [x0 - cx0, y0 - cy0, x1 - cx0, y1 - cy0]


def _edge_component_stats(gray: np.ndarray) -> dict[str, float]:
    edges = cv2.Canny(gray, 35, 125)
    joined = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats((joined > 0).astype(np.uint8), 8)
    small = 0
    medium = 0
    large = 0
    for idx in range(1, count):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < 8:
            continue
        if area < 70:
            small += 1
        elif area < 420:
            medium += 1
        else:
            large += 1
    return {
        "edge_density": float((edges > 0).mean()),
        "small_edge_components": float(small),
        "medium_edge_components": float(medium),
        "large_edge_components": float(large),
    }


def _border_edge_score(edges: np.ndarray) -> float:
    h, w = edges.shape[:2]
    band = max(2, int(min(h, w) * 0.10))
    top = float((edges[:band, :] > 0).mean())
    bottom = float((edges[h - band:, :] > 0).mean())
    left = float((edges[:, :band] > 0).mean())
    right = float((edges[:, w - band:] > 0).mean())
    center = float((edges[band:h - band, band:w - band] > 0).mean()) if h > band * 2 and w > band * 2 else 0.0
    return max(0.0, min(1.0, ((top + bottom + left + right) * 0.25) * 2.2 - center * 0.55))


def _features_from_crop(crop: Image.Image) -> dict[str, float]:
    arr = np.asarray(crop.convert("RGB").resize((160, 160), Image.Resampling.LANCZOS))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges = cv2.Canny(gray, 35, 125)
    comp = _edge_component_stats(gray)
    color_std = arr.reshape(-1, 3).std(axis=0)
    luma_std = float(gray.std())
    sat_density = float((sat > 70).mean())
    dark_frac = float((gray < 45).mean())
    bright_frac = float((gray > 210).mean())
    low_sat_frac = float((sat < 45).mean())
    border_score = _border_edge_score(edges)
    small_components = comp["small_edge_components"]
    medium_components = comp["medium_edge_components"]
    textline_score = min(1.0, comp["edge_density"] * 2.25 + min(1.0, (small_components + medium_components * 0.55) / 46.0) * 0.62)
    panel_score = min(1.0, border_score * 0.66 + min(1.0, (low_sat_frac + bright_frac) * 0.35) + min(1.0, comp["edge_density"] * 1.15) * 0.20)
    template_score = min(1.0, low_sat_frac * 0.34 + dark_frac * 0.28 + border_score * 0.42)
    graphic_score = min(1.0, sat_density * 0.50 + min(1.0, float(color_std.mean()) / 80.0) * 0.38 + min(1.0, luma_std / 90.0) * 0.18)
    number_detail = _number_stroke_score_from_crop(crop)
    return {
        "edge_density": round(comp["edge_density"], 6),
        "small_edge_components": small_components,
        "medium_edge_components": medium_components,
        "large_edge_components": comp["large_edge_components"],
        "sat_density": round(sat_density, 6),
        "dark_frac": round(dark_frac, 6),
        "bright_frac": round(bright_frac, 6),
        "low_sat_frac": round(low_sat_frac, 6),
        "luma_std": round(luma_std, 6),
        "color_std_mean": round(float(color_std.mean()), 6),
        "border_score": round(border_score, 6),
        "textline_score": round(textline_score, 6),
        "panel_score": round(panel_score, 6),
        "template_score": round(template_score, 6),
        "graphic_score": round(graphic_score, 6),
        "number_stroke_score": round(float(number_detail.get("score", 0.0)), 6),
    }


def _subtype_for(record: dict[str, Any], features: dict[str, float]) -> str:
    source_bucket = str(record.get("source_bucket") or record.get("source_kind") or "")
    if source_bucket == "rejected_digit_probe":
        return "ocr_digit_false_positive"
    panel = features["panel_score"]
    textline = features["textline_score"]
    template = features["template_score"]
    graphic = features["graphic_score"]
    number_stroke = features["number_stroke_score"]
    if panel >= 0.60 and textline >= 0.30:
        return "sponsor_contingency_panel"
    if template >= 0.68 and graphic < 0.55:
        return "template_or_body_part"
    if textline >= 0.42 or (textline >= 0.32 and graphic >= 0.55):
        return "sponsor_text_or_contingency_stack"
    if panel >= 0.52 and number_stroke >= 0.65:
        return "sponsor_panel_or_logo_block"
    if panel >= 0.62:
        return "sponsor_panel_or_logo_block"
    if graphic >= 0.64:
        return "sponsor_logo_or_livery_mark"
    if number_stroke >= 0.72:
        return "number_like_confuser"
    return "misc_paint_or_shape"


def _contact_sheet(rows: list[dict[str, Any]], out_path: Path, title: str, max_items: int) -> None:
    rows = rows[:max_items]
    if not rows:
        return
    cols = 5
    cell_w = 220
    cell_h = 214
    sheet = Image.new("RGB", (cols * cell_w, int(np.ceil(len(rows) / cols)) * cell_h), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, row in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        crop = Image.open(row["crop_file"]).convert("RGB")
        crop.thumbnail((190, 150), Image.Resampling.LANCZOS)
        sheet.paste(crop, (x + 12, y + 30))
        rank = row.get("best_rank")
        score = row.get("best_score", row.get("score", 0.0))
        draw.text((x + 6, y + 5), f"{idx:02d} {row['subtype'][:24]}", fill=(255, 230, 130))
        draw.text((x + 6, y + 18), f"rank {rank if rank is not None else '-'} p {float(score):.2f} num {row['features']['number_stroke_score']:.2f}", fill=(170, 220, 255))
        draw.text((x + 6, y + 188), str(row.get("folder") or Path(str(row.get("source_path", ""))).parent.name)[:32], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    records = json.loads(args.records.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"expected list in {args.records}")
    args.output.mkdir(parents=True, exist_ok=True)
    crop_dir = args.output / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)
    rgb_cache: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        if args.only_exposed and record.get("best_rank") is None:
            continue
        if args.top_k and record.get("best_rank") is not None and int(record["best_rank"]) > args.top_k:
            continue
        source = _source_from_record(record)
        box = _box_from_record(record, args.prefer_box)
        if source is None or box is None:
            skipped.append({"index": idx, "reason": "missing_source_or_box"})
            continue
        source_key = str(source.resolve())
        if source_key not in rgb_cache:
            rgb_cache[source_key] = _read_rgb(source, size=WORK)
        rgb = rgb_cache[source_key]
        crop, local_box = _crop_with_context(rgb, box, pad=args.context_pad)
        draw = ImageDraw.Draw(crop)
        draw.rectangle(local_box, outline=(255, 225, 50), width=max(2, int(min(crop.size) * 0.015)))
        crop_name = f"{idx:04d}_{_safe_name(record.get('source_bucket') or record.get('source_kind') or record.get('folder') or source.parent.name)}.png"
        crop_path = crop_dir / crop_name
        crop.save(crop_path)
        features = _features_from_crop(crop)
        subtype = _subtype_for(record, features)
        row = dict(record)
        row["analyzed_box"] = box
        row["crop_file"] = str(crop_path.resolve())
        row["features"] = features
        row["subtype"] = subtype
        rows.append(row)
    rows.sort(key=lambda r: (
        999999 if r.get("best_rank") is None else int(r["best_rank"]),
        -float(r.get("best_score", r.get("score", 0.0)) or 0.0),
    ))

    subtype_summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        subtype = row["subtype"]
        item = subtype_summary.setdefault(subtype, {"samples": 0, "top_5": 0, "top_20": 0, "top_40": 0})
        item["samples"] += 1
        rank = row.get("best_rank")
        if rank is not None:
            r = int(rank)
            if r <= 5:
                item["top_5"] += 1
            if r <= 20:
                item["top_20"] += 1
            if r <= 40:
                item["top_40"] += 1
    for subtype, item in subtype_summary.items():
        group = [r for r in rows if r["subtype"] == subtype]
        item["mean_panel_score"] = round(float(np.mean([r["features"]["panel_score"] for r in group])), 6)
        item["mean_textline_score"] = round(float(np.mean([r["features"]["textline_score"] for r in group])), 6)
        item["mean_number_stroke_score"] = round(float(np.mean([r["features"]["number_stroke_score"] for r in group])), 6)
        _contact_sheet(
            group,
            args.output / f"taxonomy_{_safe_name(subtype)}.png",
            f"{subtype} ({len(group)} records)",
            args.sheet_items,
        )
    summary = {
        "records": str(args.records),
        "output": str(args.output.resolve()),
        "prefer_box": args.prefer_box,
        "top_k": args.top_k,
        "only_exposed": args.only_exposed,
        "analyzed": len(rows),
        "skipped": len(skipped),
        "subtypes": dict(sorted(subtype_summary.items(), key=lambda item: (-item[1]["top_20"], -item[1]["samples"], item[0]))),
        "skipped_items": skipped,
    }
    _contact_sheet(rows, args.output / "taxonomy_all.png", "Smart TGA hard-negative taxonomy", args.sheet_items)
    (args.output / "taxonomy_records.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (args.output / "taxonomy_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--prefer-box", choices=["best", "record"], default="best")
    parser.add_argument("--context-pad", type=int, default=30)
    parser.add_argument("--top-k", type=int, default=40)
    parser.add_argument("--only-exposed", action="store_true")
    parser.add_argument("--sheet-items", type=int, default=80)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(analyze(parse_args()), indent=2))


if __name__ == "__main__":
    main()
