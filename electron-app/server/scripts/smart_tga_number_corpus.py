"""Build a small labeled Smart TGA race-number crop corpus.

This is an offline fixture tool for the Smart TGA / Smart Separate work. It
does not affect app behavior. Positives come only from companion `car_num_*`
pairs that previous audits marked safe. Hard negatives come from rejected
detector summaries, where OCR/crop heuristics confidently found digit-looking
non-number regions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


DEFAULT_SAFE_AUDIT = Path("_smart_tga_runs/cycle52_number_pair_audit_v2/all_records.json")
DEFAULT_HARD_NEGATIVE_SUMMARIES = [
    Path("_smart_tga_runs/cycle59_sam_crop_digit_word_veto_probe/summary.json"),
]
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_number_corpus_v1")
WORK = 1024
PATCH = 160


def _read_rgb(path: Path, size: int = WORK) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS))


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:80] or "sample"


def _mask_from_safe_pair(car_path: Path, car_num_path: Path) -> np.ndarray:
    base = _read_rgb(car_path).astype(np.int16)
    numbered = _read_rgb(car_num_path).astype(np.int16)
    diff = np.max(np.abs(numbered - base), axis=2)
    mask = diff > 24
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
    return mask


def _component_boxes(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    boxes: list[tuple[int, int, int, int, int]] = []
    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < 180:
            continue
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        if w < 12 or h < 12:
            continue
        boxes.append((x, y, w, h, area))
    return boxes


def _expand_box(box: tuple[int, int, int, int], pad_frac: float = 0.22) -> tuple[int, int, int, int]:
    x, y, w, h = box
    pad = int(max(w, h) * pad_frac)
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(WORK, x + w + pad)
    y1 = min(WORK, y + h + pad)
    return x0, y0, x1, y1


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


def _write_sample(
    rgb: np.ndarray,
    box: tuple[int, int, int, int],
    out_dir: Path,
    label: str,
    sample_id: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_name(sample_id)}.png"
    _crop_square(rgb, box).save(out_dir / filename)
    record = dict(meta)
    record.update({
        "label": label,
        "file": str((out_dir / filename).resolve()),
        "box": [int(v) for v in box],
    })
    return record


def _build_positive_records(records: list[dict[str, Any]], out_root: Path, limit_pairs: int | None) -> list[dict[str, Any]]:
    positives: list[dict[str, Any]] = []
    safe = [r for r in records if r.get("status") == "safe"]
    if limit_pairs:
        safe = safe[:limit_pairs]
    for pair_index, rec in enumerate(safe):
        car = Path(rec["car"])
        car_num = Path(rec["car_num"])
        if not car.is_file() or not car_num.is_file():
            continue
        rgb = _read_rgb(car_num)
        mask = _mask_from_safe_pair(car, car_num)
        boxes = _component_boxes(mask)
        for comp_index, (x, y, w, h, area) in enumerate(boxes):
            box = _expand_box((x, y, w, h))
            positives.append(_write_sample(
                rgb,
                box,
                out_root / "positive",
                "number",
                f"pos_{pair_index:03d}_{comp_index:02d}_{Path(car_num).stem}",
                {
                    "source_kind": "safe_car_num_delta",
                    "folder": rec.get("folder"),
                    "car": str(car),
                    "car_num": str(car_num),
                    "component_area": int(area),
                },
            ))
    return positives


def _build_negative_records(
    summary_paths: list[Path],
    out_root: Path,
    max_per_source: int,
    label_prefixes: list[str],
    skip_texts: set[str],
) -> list[dict[str, Any]]:
    negatives: list[dict[str, Any]] = []
    for summary_path in summary_paths:
        if not summary_path.is_file():
            continue
        entries = json.loads(summary_path.read_text(encoding="utf-8"))
        for entry in entries:
            if label_prefixes:
                label_text = str(entry.get("label") or "")
                if not any(label_text.startswith(prefix) for prefix in label_prefixes):
                    continue
            src = Path(entry.get("path", ""))
            if not src.is_file():
                continue
            rgb = _read_rgb(src)
            kept = entry.get("kept") or entry.get("accepted") or []
            # These summaries are from rejected probes. Limit per source so one
            # bad detector run cannot dominate the corpus.
            for idx, cand in enumerate(kept[:max_per_source]):
                raw_box = cand.get("bbox")
                if not raw_box or len(raw_box) != 4:
                    continue
                x, y, w, h = [int(v) for v in raw_box]
                box = _expand_box((x, y, w, h), pad_frac=0.12)
                top_ocr = (cand.get("ocr") or [{}])[0]
                ocr_text = str(top_ocr.get("text") or "").strip().upper()
                if ocr_text in skip_texts:
                    continue
                negatives.append(_write_sample(
                    rgb,
                    box,
                    out_root / "hard_negative",
                    "hard_negative",
                    f"neg_{len(negatives):04d}_{Path(src).stem}_{idx:02d}",
                    {
                        "source_kind": "rejected_digit_probe",
                        "source_summary": str(summary_path),
                        "paint": str(src),
                        "probe_label": entry.get("label"),
                        "probe_ocr": top_ocr,
                    },
                ))
    return negatives


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 8
    cell = 190
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        img = Image.open(rec["file"]).convert("RGB").resize((160, 160), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 15, y + 20))
        draw.text((x + 6, y + 4), rec["label"][:22], fill=(255, 255, 180))
        hint = Path(rec.get("paint") or rec.get("car_num") or rec.get("car") or rec["file"]).stem
        draw.text((x + 6, y + 178), hint[:26], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def build_corpus(args: argparse.Namespace) -> dict[str, Any]:
    out_root = args.output
    out_root.mkdir(parents=True, exist_ok=True)
    records = json.loads(args.safe_audit.read_text(encoding="utf-8"))
    positives = _build_positive_records(records, out_root, args.limit_pairs)
    negatives = _build_negative_records(
        args.hard_negative_summary,
        out_root,
        args.max_negatives_per_source,
        args.hard_negative_label_prefix,
        {str(v).strip().upper() for v in args.hard_negative_skip_text},
    )
    manifest = positives + negatives
    manifest_path = out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _contact_sheet(positives, out_root / "positive_contact_sheet.png", "Smart TGA number positives")
    _contact_sheet(negatives, out_root / "hard_negative_contact_sheet.png", "Smart TGA hard negatives")
    summary = {
        "output": str(out_root.resolve()),
        "safe_audit": str(args.safe_audit),
        "hard_negative_summaries": [str(p) for p in args.hard_negative_summary],
        "hard_negative_label_prefix": args.hard_negative_label_prefix,
        "hard_negative_skip_text": args.hard_negative_skip_text,
        "positive_count": len(positives),
        "hard_negative_count": len(negatives),
        "manifest": str(manifest_path.resolve()),
        "positive_contact_sheet": str((out_root / "positive_contact_sheet.png").resolve()) if positives else None,
        "hard_negative_contact_sheet": str((out_root / "hard_negative_contact_sheet.png").resolve()) if negatives else None,
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-audit", type=Path, default=DEFAULT_SAFE_AUDIT)
    parser.add_argument("--hard-negative-summary", type=Path, action="append", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit-pairs", type=int, default=None)
    parser.add_argument("--max-negatives-per-source", type=int, default=8)
    parser.add_argument(
        "--hard-negative-label-prefix",
        action="append",
        default=[],
        help="Only import hard negatives from summary entries whose label starts with this value.",
    )
    parser.add_argument(
        "--hard-negative-skip-text",
        action="append",
        default=[],
        help="Skip rejected-probe crops whose top OCR text exactly matches this value.",
    )
    args = parser.parse_args()
    if args.hard_negative_summary is None:
        args.hard_negative_summary = DEFAULT_HARD_NEGATIVE_SUMMARIES
    return args


def main() -> None:
    summary = build_corpus(parse_args())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
