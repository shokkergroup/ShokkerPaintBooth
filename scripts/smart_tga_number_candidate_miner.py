"""Mine review candidates for Smart TGA race-number training.

This is offline Smart TGA tooling. It trains the lightweight crop detector from
an existing labeled manifest, scans real iRacing `car_num_*.tga` files, extracts
number-like visual components, scores the crops, and writes review sheets. The
output is for human/agent review; it is not automatically added to training and
does not affect Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from smart_tga_number_detector_eval import _features, _source_group, _train_svm, _predict


DEFAULT_PAINT_ROOT = Path(r"C:\Users\Ricky's PC\Documents\iRacing\paint")
DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle62_number_corpus_v1/manifest.json")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_number_candidate_miner")
WORK = 1024
PATCH = 160
BOX_IOU_SKIP = 0.72
CAR_TGA_RE = re.compile(r"^car_\d+\.tga$", re.IGNORECASE)
CAR_NUM_TGA_RE = re.compile(r"^car_num_\d+\.tga$", re.IGNORECASE)


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:90] or "sample"


def _read_rgb(path: Path, size: int = WORK) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS))


def _crop_square(rgb: np.ndarray, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    crop = rgb[y0:y1, x0:x1]
    if crop.size == 0:
        crop = np.zeros((8, 8, 3), np.uint8)
    h, w = crop.shape[:2]
    side = max(h, w)
    canvas = np.zeros((side, side, 3), np.uint8)
    oy = (side - h) // 2
    ox = (side - w) // 2
    canvas[oy:oy + h, ox:ox + w] = crop
    return Image.fromarray(canvas).resize((PATCH, PATCH), Image.Resampling.LANCZOS)


def _candidate_boxes(rgb: np.ndarray, max_boxes: int) -> list[dict[str, Any]]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges = cv2.Canny(gray, 45, 135)
    edge_words = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)
    edge_words = cv2.morphologyEx(edge_words, cv2.MORPH_CLOSE, np.ones((13, 9), np.uint8))
    n, labels, stats, _cent = cv2.connectedComponentsWithStats((edge_words > 0).astype(np.uint8), 8)
    boxes: list[dict[str, Any]] = []
    for idx in range(1, n):
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if w < 36 or h < 24 or w > 430 or h > 340:
            continue
        aspect = w / max(1.0, float(h))
        if aspect < 0.35 or aspect > 6.5:
            continue
        fill = area / float(w * h)
        if fill < 0.06 or fill > 0.75:
            continue
        raw = (labels[y:y + h, x:x + w] == idx)
        edge_density = float((edges[y:y + h, x:x + w] > 0).mean())
        sat_density = float((sat[y:y + h, x:x + w] > 55).mean())
        if edge_density < 0.04:
            continue
        pad = int(max(w, h) * 0.18)
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(WORK, x + w + pad)
        y1 = min(WORK, y + h + pad)
        boxes.append({
            "box": [x0, y0, x1, y1],
            "raw_box": [x, y, w, h],
            "area": area,
            "fill": round(fill, 4),
            "edge_density": round(edge_density, 4),
            "sat_density": round(sat_density, 4),
            "aspect": round(aspect, 4),
            "raw_pixels": int(raw.sum()),
        })
    boxes.sort(key=lambda b: (b["edge_density"] * 2.0 + b["sat_density"] + min(3.0, b["aspect"])), reverse=True)
    return boxes[:max_boxes]


def _window_boxes(rgb: np.ndarray, max_boxes: int) -> list[dict[str, Any]]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges = cv2.Canny(gray, 30, 110)
    edge_integral = cv2.integral((edges > 0).astype(np.float32))
    sat_integral = cv2.integral((sat > 55).astype(np.float32))

    def isum(integral: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> float:
        return float(integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0])

    sizes: list[tuple[int, int]] = []
    for w, h in (
        (72, 56),
        (96, 76),
        (124, 96),
        (160, 120),
        (200, 150),
        (240, 180),
        (300, 220),
        (360, 260),
        (420, 300),
        (260, 260),
        (340, 340),
        (460, 380),
    ):
        sizes.append((w, h))
        if abs(w - h) > 20:
            sizes.append((h, w))

    boxes: list[dict[str, Any]] = []
    for w, h in sizes:
        step_x = max(20, w // 4)
        step_y = max(20, h // 4)
        for y in range(0, WORK - h + 1, step_y):
            for x in range(0, WORK - w + 1, step_x):
                area = float(w * h)
                edge_density = isum(edge_integral, x, y, x + w, y + h) / area
                if edge_density < 0.006:
                    continue
                sat_density = isum(sat_integral, x, y, x + w, y + h) / area
                aspect = w / float(h)
                aspect_bonus = 1.0 - min(1.0, abs(np.log(max(0.2, min(6.0, aspect)))) / 2.2)
                size_bonus = min(1.0, area / float(300 * 220))
                score = edge_density * 4.0 + sat_density * 0.35 + aspect_bonus * 0.12 + size_bonus * 0.20
                boxes.append({
                    "box": [x, y, x + w, y + h],
                    "raw_box": [x, y, w, h],
                    "area": int(area),
                    "fill": 1.0,
                    "edge_density": round(edge_density, 4),
                    "sat_density": round(sat_density, 4),
                    "aspect": round(aspect, 4),
                    "proposal_variant": "window",
                    "proposal_score": round(float(score), 6),
                    "raw_pixels": int(area),
                })

    boxes.sort(key=lambda b: float(b.get("proposal_score", 0.0)), reverse=True)
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        if any(_box_iou(box["box"], existing["box"]) >= 0.74 for existing in deduped):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _dedupe_ordered(boxes: list[dict[str, Any]], max_boxes: int) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        raw = box.get("raw_box")
        xyxy = _raw_to_xyxy(raw) if isinstance(raw, list) and len(raw) == 4 else box["box"]
        if any(
            _box_iou(
                xyxy,
                _raw_to_xyxy(existing["raw_box"])
                if isinstance(existing.get("raw_box"), list) and len(existing["raw_box"]) == 4
                else existing["box"],
            )
            >= 0.72
            for existing in deduped
        ):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _candidate_boxes_for_mode(rgb: np.ndarray, max_boxes: int, proposal_mode: str) -> list[dict[str, Any]]:
    if proposal_mode == "default":
        return _candidate_boxes(rgb, max_boxes)
    if proposal_mode != "hybrid":
        raise ValueError(f"unsupported proposal mode: {proposal_mode}")
    component_budget = min(max_boxes, max(14, max_boxes // 3))
    boxes = _candidate_boxes(rgb, component_budget)
    boxes.extend(_window_boxes(rgb, max_boxes))
    return _dedupe_ordered(boxes, max_boxes)


def _box_iou(a: list[int], b: list[int]) -> float:
    ax0, ay0, ax1, ay1 = [float(v) for v in a]
    bx0, by0, bx1, by1 = [float(v) for v in b]
    inter_x0 = max(ax0, bx0)
    inter_y0 = max(ay0, by0)
    inter_x1 = min(ax1, bx1)
    inter_y1 = min(ay1, by1)
    inter_w = max(0.0, inter_x1 - inter_x0)
    inter_h = max(0.0, inter_y1 - inter_y0)
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return inter / max(1.0, area_a + area_b - inter)


def _raw_to_xyxy(raw_box: list[int]) -> list[int]:
    x, y, w, h = [int(v) for v in raw_box]
    return [x, y, x + w, y + h]


def _reviewed_boxes(manifest_path: Path) -> dict[str, list[list[int]]]:
    if not manifest_path.is_file():
        return {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reviewed: dict[str, list[list[int]]] = {}
    for rec in manifest:
        paint = rec.get("paint")
        if not paint:
            continue
        box = rec.get("raw_box")
        if box and len(box) == 4:
            xyxy = _raw_to_xyxy([int(v) for v in box])
        else:
            box = rec.get("box")
            if not box or len(box) != 4:
                continue
            xyxy = [int(v) for v in box]
        reviewed.setdefault(str(Path(paint).resolve()).lower(), []).append(xyxy)
    return reviewed


def _is_previously_reviewed(path: Path, candidate: dict[str, Any], reviewed: dict[str, list[list[int]]]) -> bool:
    existing = reviewed.get(str(path.resolve()).lower())
    if not existing:
        return False
    cand_box = _raw_to_xyxy(candidate["raw_box"])
    return any(_box_iou(cand_box, box) >= BOX_IOU_SKIP for box in existing)


def _paint_globs(file_kind: str) -> list[str]:
    if file_kind == "car":
        return ["car_*.tga"]
    if file_kind == "car_num":
        return ["car_num_*.tga"]
    if file_kind == "both":
        return ["car_*.tga", "car_num_*.tga"]
    raise ValueError(f"unsupported file kind: {file_kind}")


def _is_allowed_paint_file(path: Path, file_kind: str) -> bool:
    name = path.name
    is_car = CAR_TGA_RE.match(name) is not None
    is_car_num = CAR_NUM_TGA_RE.match(name) is not None
    if file_kind == "car":
        return is_car
    if file_kind == "car_num":
        return is_car_num
    if file_kind == "both":
        return is_car or is_car_num
    return False


def _pick_files(paint_root: Path, folder_prefix: list[str], max_files: int, file_kind: str) -> list[Path]:
    files: list[Path] = []
    prefixes = [p.lower() for p in folder_prefix]
    for folder in sorted([p for p in paint_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        if prefixes and not any(folder.name.lower().startswith(prefix) for prefix in prefixes):
            continue
        seen: set[Path] = set()
        for glob in _paint_globs(file_kind):
            for path in sorted(folder.glob(glob), key=lambda p: p.name.lower()):
                if path in seen or not _is_allowed_paint_file(path, file_kind):
                    continue
                seen.add(path)
                files.append(path)
                if len(files) >= max_files:
                    return files
    return files


def _train_detector(manifest_path: Path, feature_set: str, svm_c: float) -> cv2.ml_SVM:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rec in manifest:
        rec["source_group"] = _source_group(rec)
    x = np.stack([_features(rec["file"], feature_set) for rec in manifest]).astype(np.float32)
    y = np.array([1 if rec["label"] == "number" else 0 for rec in manifest], np.int32)
    return _train_svm(x, y, "linear", svm_c, 0.01)


def _score_crop(svm: cv2.ml_SVM, crop_path: Path, feature_set: str) -> tuple[int, float]:
    x = _features(crop_path, feature_set).reshape(1, -1).astype(np.float32)
    pred = int(_predict(svm, x)[0])
    try:
        _ok, raw = svm.predict(x, flags=cv2.ml.STAT_MODEL_RAW_OUTPUT)
        score = float(raw.ravel()[0])
    except Exception:
        score = 0.0
    return pred, score


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 6
    cell = 210
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        img = Image.open(rec["crop_file"]).convert("RGB").resize((166, 166), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 22, y + 24))
        prefix = f"#{rec['review_index']:02d} " if "review_index" in rec else ""
        draw.text((x + 6, y + 5), f"{prefix}pred {rec['prediction']} raw {rec['raw_score']:.3f}", fill=(255, 230, 150))
        draw.text((x + 6, y + 192), rec["label"][:31], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _review_queue(records: list[dict[str, Any]], sheet_items: int) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    seen: set[str] = set()
    buckets = [
        ("predicted_positive", [rec for rec in records if rec["prediction"] == 1]),
        ("boundary", records),
    ]
    for source, bucket in buckets:
        ordered = sorted(bucket, key=lambda rec: (abs(rec["raw_score"]), -rec["edge_density"]))
        for rec in ordered:
            key = rec["crop_file"]
            if key in seen:
                continue
            seen.add(key)
            item = {
                "review_label": "",
                "review_notes": "",
                "review_source": source,
                "suggested_labels": ["number", "hard_negative", "skip"],
            }
            item.update(rec)
            item["review_index"] = len(queue)
            queue.append(item)
            if len(queue) >= sheet_items:
                return queue
    return queue


def mine_candidates(args: argparse.Namespace) -> dict[str, Any]:
    out = args.output
    crop_dir = out / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)
    svm = _train_detector(args.manifest, args.feature_set, args.svm_c)
    reviewed = _reviewed_boxes(args.exclude_reviewed_manifest or args.manifest) if args.skip_reviewed else {}
    files = _pick_files(args.paint_root, args.folder_prefix, args.max_files, args.file_kind)
    records: list[dict[str, Any]] = []
    skipped_reviewed = 0
    for file_index, path in enumerate(files):
        rgb = _read_rgb(path)
        candidates = _candidate_boxes_for_mode(rgb, args.max_boxes_per_file, args.proposal_mode)
        for box_index, cand in enumerate(candidates):
            if _is_previously_reviewed(path, cand, reviewed):
                skipped_reviewed += 1
                continue
            crop_name = f"{file_index:03d}_{box_index:02d}_{_safe_name(path.parent.name)}_{path.stem}.png"
            crop_path = crop_dir / crop_name
            _crop_square(rgb, tuple(cand["box"])).save(crop_path)
            pred, score = _score_crop(svm, crop_path, args.feature_set)
            rec = {
                "paint": str(path),
                "folder": path.parent.name,
                "label": f"{path.parent.name}/{path.name}",
                "crop_file": str(crop_path.resolve()),
                "prediction": pred,
                "raw_score": round(score, 6),
            }
            rec.update(cand)
            records.append(rec)
    positive = [rec for rec in records if rec["prediction"] == 1]
    negative = [rec for rec in records if rec["prediction"] == 0]
    # OpenCV SVM raw score sign is model-dependent, so review both predicted
    # positives and the closest-to-boundary candidates instead of auto-labeling.
    positive_sorted = sorted(positive, key=lambda rec: (abs(rec["raw_score"]), -rec["edge_density"]))
    uncertain_sorted = sorted(records, key=lambda rec: abs(rec["raw_score"]))
    negative_sorted = sorted(negative, key=lambda rec: (abs(rec["raw_score"]), -rec["edge_density"]))
    _contact_sheet(positive_sorted[:args.sheet_items], out / "predicted_positive_review.png", "Predicted number candidates")
    _contact_sheet(uncertain_sorted[:args.sheet_items], out / "uncertain_review.png", "Boundary candidates")
    _contact_sheet(negative_sorted[:args.sheet_items], out / "predicted_negative_review.png", "Predicted non-number candidates")
    review_queue = _review_queue(records, args.sheet_items)
    _contact_sheet(review_queue, out / "review_queue_sheet.png", "Review queue")
    (out / "candidates.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    (out / "review_queue.json").write_text(json.dumps(review_queue, indent=2), encoding="utf-8")
    summary = {
        "paint_root": str(args.paint_root),
        "manifest": str(args.manifest),
        "feature_set": args.feature_set,
        "svm_c": args.svm_c,
        "proposal_mode": args.proposal_mode,
        "file_kind": args.file_kind,
        "folder_prefix": args.folder_prefix,
        "files_scanned": len(files),
        "candidates": len(records),
        "skipped_reviewed": skipped_reviewed,
        "skip_reviewed": bool(args.skip_reviewed),
        "exclude_reviewed_manifest": str(args.exclude_reviewed_manifest or args.manifest) if args.skip_reviewed else None,
        "predicted_positive": len(positive),
        "predicted_negative": len(negative),
        "review_queue": len(review_queue),
        "candidates_json": str((out / "candidates.json").resolve()),
        "review_queue_json": str((out / "review_queue.json").resolve()),
        "review_queue_sheet": str((out / "review_queue_sheet.png").resolve()) if review_queue else None,
        "predicted_positive_review": str((out / "predicted_positive_review.png").resolve()) if positive else None,
        "uncertain_review": str((out / "uncertain_review.png").resolve()) if records else None,
        "predicted_negative_review": str((out / "predicted_negative_review.png").resolve()) if negative else None,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paint-root", type=Path, default=DEFAULT_PAINT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--folder-prefix", action="append", default=[])
    parser.add_argument("--file-kind", choices=["car", "car_num", "both"], default="car_num")
    parser.add_argument("--max-files", type=int, default=80)
    parser.add_argument("--max-boxes-per-file", type=int, default=10)
    parser.add_argument("--proposal-mode", choices=["default", "hybrid"], default="default")
    parser.add_argument("--feature-set", choices=["base", "hog"], default="hog")
    parser.add_argument("--svm-c", type=float, default=0.1)
    parser.add_argument("--sheet-items", type=int, default=36)
    parser.add_argument("--skip-reviewed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--exclude-reviewed-manifest", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(mine_candidates(parse_args()), indent=2))


if __name__ == "__main__":
    main()
