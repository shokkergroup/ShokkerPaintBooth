"""Audit Smart TGA proposal localization on independently labeled number boxes.

This is offline Smart TGA tooling. It focuses on the safe ``car``/``car_num``
delta positives because those boxes were not discovered by the proposal miner
itself, so they are a cleaner signal for universal number localization.
Nothing here affects Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from smart_tga_number_candidate_miner import WORK, _box_iou, _read_rgb
from smart_tga_number_proposal_eval import (
    IOU_LEVELS,
    _as_xyxy,
    _proposal_boxes,
    _raw_xywh_to_xyxy,
    _source_bucket,
    _source_path,
)


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle74_veto085_strict_corpus_v1/manifest.json")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_safe_overlay_localization_audit")
VARIANTS = (
    "default",
    "multi",
    "multi_soft",
    "window",
    "hybrid",
    "hybrid_expand",
    "hybrid_focus",
    "hybrid_side_panel",
)


def _candidate_xyxy(candidate: dict[str, Any]) -> list[int]:
    raw = candidate.get("raw_box")
    if isinstance(raw, list) and len(raw) == 4:
        return _raw_xywh_to_xyxy(raw)
    box = candidate.get("box")
    if isinstance(box, list) and len(box) == 4:
        return [int(v) for v in box]
    return [0, 0, 0, 0]


def _candidate_family(candidate: dict[str, Any]) -> str:
    family = str(candidate.get("proposal_variant") or "").strip()
    if family:
        return family
    if candidate.get("raw_box") or candidate.get("area"):
        return "component_default"
    return "unknown"


def _candidate_digest(candidate: dict[str, Any], gt: list[int], index: int) -> dict[str, Any]:
    xyxy = _candidate_xyxy(candidate)
    digest: dict[str, Any] = {
        "proposal_index": index + 1,
        "xyxy": xyxy,
        "iou": round(float(_box_iou(gt, xyxy)), 6),
        "proposal_variant": _candidate_family(candidate),
    }
    for key in (
        "proposal_score",
        "area",
        "fill",
        "edge_density",
        "soft_edge_density",
        "sat_density",
        "aspect",
        "parent_index",
        "parent_variant",
    ):
        if candidate.get(key) is not None:
            value = candidate[key]
            digest[key] = round(float(value), 6) if isinstance(value, (float, int)) else value
    return digest


def _evaluate_candidates(gt: list[int], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    digests = [_candidate_digest(candidate, gt, idx) for idx, candidate in enumerate(candidates)]
    top = sorted(digests, key=lambda item: float(item["iou"]), reverse=True)[:8]
    best = top[0] if top else None
    family_best: dict[str, dict[str, Any]] = {}
    family_counts = Counter(str(item["proposal_variant"]) for item in digests)
    for item in digests:
        family = str(item["proposal_variant"])
        if family not in family_best or float(item["iou"]) > float(family_best[family]["iou"]):
            family_best[family] = item

    focused = family_best.get("focused_window")
    best_iou = float(best["iou"]) if best else 0.0
    focused_iou = float(focused["iou"]) if focused else 0.0
    return {
        "candidate_count": len(candidates),
        "best_iou": round(best_iou, 6),
        "best_candidate": best,
        "best_candidate_family": str(best["proposal_variant"]) if best else "none",
        "best_proposal_index": int(best["proposal_index"]) if best else None,
        "top_iou_candidates": top,
        "family_best": family_best,
        "family_counts": dict(sorted(family_counts.items())),
        "focused_window_best_iou": round(focused_iou, 6),
        "focused_window_best": focused,
        "focused_window_is_best": bool(best and focused and best["proposal_variant"] == "focused_window"),
        "focused_window_near_best": bool(focused and focused_iou >= max(0.20, best_iou - 0.05)),
    }


def _load_ranked_records(paths: list[Path]) -> dict[tuple[int, str, tuple[int, int, int, int]], list[dict[str, Any]]]:
    ranked: dict[tuple[int, str, tuple[int, int, int, int]], list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        for rec in data:
            gt = rec.get("gt_box")
            if not isinstance(gt, list) or len(gt) != 4:
                continue
            key = (
                int(rec.get("manifest_index", -1)),
                str(Path(str(rec.get("source_path", ""))).resolve()),
                tuple(int(v) for v in gt),
            )
            ranked[key].append(
                {
                    "ranked_records_file": str(path),
                    "score_sweep_key": rec.get("score_sweep_key"),
                    "best_iou": rec.get("best_iou"),
                    "best_rank": rec.get("best_rank"),
                    "best_score": rec.get("best_score"),
                    "best_candidate_family": _candidate_family(rec.get("best_candidate") or {}),
                }
            )
    return ranked


def _aggregate(rows: list[dict[str, Any]], result_key: str) -> dict[str, Any]:
    values = [float(row["results"][result_key]["best_iou"]) for row in rows]
    families = Counter(str(row["results"][result_key]["best_candidate_family"]) for row in rows)
    focused_best = sum(1 for row in rows if row["results"][result_key]["focused_window_is_best"])
    focused_near = sum(1 for row in rows if row["results"][result_key]["focused_window_near_best"])
    focused_covered = sum(1 for row in rows if float(row["results"][result_key]["focused_window_best_iou"]) >= 0.25)
    indices = [
        int(row["results"][result_key]["best_proposal_index"])
        for row in rows
        if row["results"][result_key]["best_proposal_index"] is not None
    ]
    aggregate: dict[str, Any] = {
        "samples": len(rows),
        "mean_best_iou": round(float(np.mean(values)) if values else 0.0, 6),
        "median_best_iou": round(float(np.median(values)) if values else 0.0, 6),
        "best_candidate_family_counts": dict(sorted(families.items())),
        "focused_window_best_count": focused_best,
        "focused_window_near_best_count": focused_near,
        "focused_window_covered_iou_0.25": focused_covered,
        "median_best_proposal_index": round(float(np.median(indices)) if indices else 0.0, 3),
        "p90_best_proposal_index": round(float(np.percentile(indices, 90)) if indices else 0.0, 3),
    }
    for threshold in IOU_LEVELS:
        covered = sum(1 for value in values if value >= threshold)
        aggregate[f"covered_iou_{threshold:.2f}"] = covered
        aggregate[f"recall_iou_{threshold:.2f}"] = round(covered / max(1, len(rows)), 6)
    return aggregate


def _aggregate_by_folder(rows: list[dict[str, Any]], result_key: str) -> dict[str, Any]:
    folders: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        folders[str(row.get("folder") or "unknown")].append(row)
    return {folder: _aggregate(items, result_key) for folder, items in sorted(folders.items())}


def _crop_overlay(rgb: np.ndarray, row: dict[str, Any], result: dict[str, Any]) -> Image.Image:
    gt = row["gt_box"]
    boxes = [gt]
    best = result.get("best_candidate")
    focus = result.get("focused_window_best")
    if best:
        boxes.append(best["xyxy"])
    if focus:
        boxes.append(focus["xyxy"])
    x0 = max(0, min(int(box[0]) for box in boxes) - 56)
    y0 = max(0, min(int(box[1]) for box in boxes) - 56)
    x1 = min(WORK, max(int(box[2]) for box in boxes) + 56)
    y1 = min(WORK, max(int(box[3]) for box in boxes) + 56)
    crop = Image.fromarray(rgb[y0:y1, x0:x1]).convert("RGB")
    draw = ImageDraw.Draw(crop)

    def local(box: list[int]) -> list[int]:
        return [int(box[0]) - x0, int(box[1]) - y0, int(box[2]) - x0, int(box[3]) - y0]

    draw.rectangle(local(gt), outline=(255, 70, 70), width=4)
    if best:
        draw.rectangle(local(best["xyxy"]), outline=(255, 225, 45), width=3)
    if focus:
        draw.rectangle(local(focus["xyxy"]), outline=(70, 230, 255), width=2)
    draw.text(
        (6, 6),
        f"IoU {float(result['best_iou']):.3f} {result['best_candidate_family']}",
        fill=(255, 255, 255),
    )
    return crop


def _contact_sheet(rows: list[dict[str, Any]], out_path: Path, title: str, result_key: str) -> None:
    if not rows:
        return
    cols = 4
    cell_w = 260
    cell_h = 226
    rows_count = int(np.ceil(len(rows) / cols))
    sheet = Image.new("RGB", (cols * cell_w, rows_count * cell_h), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    image_cache: dict[str, np.ndarray] = {}
    for idx, row in enumerate(rows):
        path = row["source_path"]
        if path not in image_cache:
            image_cache[path] = _read_rgb(Path(path))
        result = row["results"][result_key]
        img = _crop_overlay(image_cache[path], row, result)
        img.thumbnail((240, 166), Image.Resampling.LANCZOS)
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        sheet.paste(img, (x + 10, y + 34))
        best_rank = ""
        if row.get("ranked_hints"):
            rank = row["ranked_hints"][0].get("best_rank")
            best_rank = f" rank {rank}"
        draw.text((x + 7, y + 6), f"#{idx:02d} {float(result['best_iou']):.3f}{best_rank}", fill=(255, 230, 150))
        draw.text((x + 7, y + 204), str(row.get("folder") or "")[:36], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError("manifest must be a list")
    args.output.mkdir(parents=True, exist_ok=True)
    ranked_hints = _load_ranked_records(args.ranked_records)

    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for idx, rec in enumerate(manifest):
        if rec.get("label") != "number":
            continue
        bucket = _source_bucket(rec)
        if args.bucket != "all" and bucket != args.bucket:
            continue
        gt = _as_xyxy(rec)
        source = _source_path(rec)
        if not gt or not source:
            skipped.append({"manifest_index": idx, "reason": "missing_gt_or_source", "record": rec})
            continue
        source_resolved = str(source.resolve())
        row = {
            "manifest_index": idx,
            "source_path": source_resolved,
            "folder": rec.get("folder") or source.parent.name,
            "source_bucket": bucket,
            "gt_box": gt,
            "record_file": rec.get("file"),
            "ranked_hints": ranked_hints.get((idx, source_resolved, tuple(gt)), []),
            "results": {},
        }
        rows.append(row)

    image_cache: dict[str, np.ndarray] = {}
    candidate_cache: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        path = row["source_path"]
        if path not in image_cache:
            image_cache[path] = _read_rgb(Path(path))
        rgb = image_cache[path]
        for variant in args.variant:
            for max_boxes in args.max_boxes:
                cache_key = (path, variant, max_boxes)
                if cache_key not in candidate_cache:
                    candidate_cache[cache_key] = _proposal_boxes(rgb, max_boxes, variant)
                result_key = f"{variant}_{max_boxes}"
                row["results"][result_key] = _evaluate_candidates(row["gt_box"], candidate_cache[cache_key])

    summary: dict[str, Any] = {
        "manifest": str(args.manifest),
        "output": str(args.output.resolve()),
        "bucket": args.bucket,
        "samples": len(rows),
        "skipped": len(skipped),
        "variants": args.variant,
        "max_boxes": args.max_boxes,
        "iou_levels": list(IOU_LEVELS),
        "overall": {},
        "by_folder": {},
        "notes": [
            "Red box is ground truth. Yellow is best candidate. Cyan is best focused_window candidate when present.",
            "Safe-overlay records are independent labels, so they expose localization blind spots better than reviewed proposal crops.",
        ],
    }
    for variant in args.variant:
        for max_boxes in args.max_boxes:
            result_key = f"{variant}_{max_boxes}"
            summary["overall"][result_key] = _aggregate(rows, result_key)
            summary["by_folder"][result_key] = _aggregate_by_folder(rows, result_key)
            worst = sorted(rows, key=lambda item: float(item["results"][result_key]["best_iou"]))[: args.sheet_items]
            _contact_sheet(worst, args.output / f"worst_{result_key}.png", f"Safe-overlay worst localization: {result_key}", result_key)
            focus_near = [
                row
                for row in rows
                if row["results"][result_key]["focused_window_near_best"]
                or float(row["results"][result_key]["focused_window_best_iou"]) >= 0.20
            ][: args.sheet_items]
            _contact_sheet(
                focus_near,
                args.output / f"focused_window_near_{result_key}.png",
                f"Focused-window useful cases: {result_key}",
                result_key,
            )

    (args.output / "localization_records.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (args.output / "skipped_records.json").write_text(json.dumps(skipped, indent=2), encoding="utf-8")
    (args.output / "localization_audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--bucket", default="safe_car_num_delta")
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=None)
    parser.add_argument("--max-boxes", type=int, action="append", default=None)
    parser.add_argument("--ranked-records", type=Path, action="append", default=[])
    parser.add_argument("--sheet-items", type=int, default=40)
    args = parser.parse_args()
    args.variant = args.variant or ["hybrid", "hybrid_focus"]
    args.max_boxes = args.max_boxes or [240, 360]
    return args


def main() -> None:
    summary = audit(parse_args())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
