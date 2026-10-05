"""Build a cleaner Smart TGA hard-negative pack from taxonomy records.

This is offline Smart TGA tooling. It filters taxonomy/contact-sheet records
into high-confidence hard negatives plus a review-needed bucket. It is meant to
reduce weak-label noise before proposal-classifier experiments, not to wire
anything into Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


DEFAULT_TAXONOMY = [
    Path("_smart_tga_runs/cycle93_taxonomy_full_livery_stockcars2_v1/taxonomy_records.json"),
    Path("_smart_tga_runs/cycle93_taxonomy_full_livery_stock_truck_v1/taxonomy_records.json"),
]
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_taxonomy_label_pack")
SAFE_SUBTYPES = {
    "sponsor_contingency_panel",
    "sponsor_panel_or_logo_block",
    "sponsor_text_or_contingency_stack",
    "sponsor_logo_or_livery_mark",
}


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:110] or "unknown"


def _features(record: dict[str, Any]) -> dict[str, float]:
    values = record.get("features") or {}
    return {str(key): float(value) for key, value in values.items() if isinstance(value, (int, float))}


def _is_high_confidence(record: dict[str, Any], args: argparse.Namespace) -> tuple[bool, str]:
    subtype = str(record.get("subtype") or "")
    features = _features(record)
    panel = features.get("panel_score", 0.0)
    textline = features.get("textline_score", 0.0)
    graphic = features.get("graphic_score", 0.0)
    number_stroke = features.get("number_stroke_score", 0.0)
    if subtype not in SAFE_SUBTYPES:
        return False, f"subtype:{subtype or 'missing'}"
    if subtype == "sponsor_logo_or_livery_mark" and graphic < args.min_logo_graphic:
        return False, f"logo_graphic<{args.min_logo_graphic}"
    if subtype == "sponsor_text_or_contingency_stack" and textline < args.min_textline:
        return False, f"textline<{args.min_textline}"
    if subtype in {"sponsor_panel_or_logo_block", "sponsor_contingency_panel"} and panel < args.min_panel:
        return False, f"panel<{args.min_panel}"
    if number_stroke >= args.max_number_stroke and panel < args.strong_panel and textline < args.strong_textline:
        return False, f"number_stroke>={args.max_number_stroke}"
    return True, "accepted"


def _copy_crop(record: dict[str, Any], out_dir: Path, prefix: str, index: int) -> Path | None:
    src = Path(str(record.get("crop_file") or record.get("record_file") or ""))
    if not src.is_file():
        return None
    folder = _safe_name(str(record.get("folder") or Path(str(record.get("source_path", ""))).parent.name or "source"))
    dst = out_dir / f"{prefix}_{index:04d}_{folder}.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def _contact_sheet(rows: list[dict[str, Any]], out_path: Path, title: str, max_items: int) -> None:
    rows = rows[:max_items]
    if not rows:
        return
    cols = 5
    cell_w = 230
    cell_h = 210
    sheet = Image.new("RGB", (cols * cell_w, int(np.ceil(len(rows) / cols)) * cell_h), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, row in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        img = Image.open(row["pack_crop_file"]).convert("RGB")
        img.thumbnail((176, 146), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 24, y + 34))
        features = row.get("features") or {}
        draw.text((x + 6, y + 5), f"{idx:02d} {row.get('subtype', '')[:28]}", fill=(255, 225, 120))
        draw.text(
            (x + 6, y + 19),
            f"n {float(features.get('number_stroke_score', 0.0)):.2f} p {float(features.get('panel_score', 0.0)):.2f} t {float(features.get('textline_score', 0.0)):.2f}",
            fill=(170, 220, 255),
        )
        draw.text((x + 6, y + 184), str(row.get("folder") or row.get("reject_reason", ""))[:34], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def build(args: argparse.Namespace) -> dict[str, Any]:
    out = args.output
    accepted_dir = out / "accepted_hard_negative"
    review_dir = out / "needs_review"
    out.mkdir(parents=True, exist_ok=True)
    accepted: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    skipped = 0
    for path in args.taxonomy:
        records = json.loads(path.read_text(encoding="utf-8"))
        for record in records:
            keep, reason = _is_high_confidence(record, args)
            row = dict(record)
            row["source_taxonomy"] = str(path)
            row["label"] = "hard_negative" if keep else "review_needed"
            row["reject_reason"] = reason
            crop_path = _copy_crop(row, accepted_dir if keep else review_dir, "neg" if keep else "review", len(accepted) if keep else len(review))
            if crop_path is None:
                skipped += 1
                continue
            row["pack_crop_file"] = str(crop_path.resolve())
            row["file"] = row["pack_crop_file"]
            if keep:
                accepted.append(row)
            else:
                review.append(row)
    accepted_path = out / "accepted_hard_negatives.json"
    review_path = out / "needs_review.json"
    accepted_path.write_text(json.dumps(accepted, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
    _contact_sheet(accepted, out / "accepted_hard_negatives.png", "High-confidence Smart TGA hard negatives", args.sheet_items)
    _contact_sheet(review, out / "needs_review.png", "Smart TGA taxonomy records needing review", args.sheet_items)
    summary = {
        "taxonomy": [str(path) for path in args.taxonomy],
        "output": str(out.resolve()),
        "accepted": len(accepted),
        "needs_review": len(review),
        "skipped": skipped,
        "accepted_by_subtype": dict(Counter(str(row.get("subtype")) for row in accepted)),
        "review_by_reason": dict(Counter(str(row.get("reject_reason")) for row in review)),
        "accepted_records": str(accepted_path.resolve()),
        "review_records": str(review_path.resolve()),
        "accepted_sheet": str((out / "accepted_hard_negatives.png").resolve()) if accepted else None,
        "review_sheet": str((out / "needs_review.png").resolve()) if review else None,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taxonomy", type=Path, action="append", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--min-logo-graphic", type=float, default=0.64)
    parser.add_argument("--min-textline", type=float, default=0.36)
    parser.add_argument("--min-panel", type=float, default=0.52)
    parser.add_argument("--max-number-stroke", type=float, default=0.96)
    parser.add_argument("--strong-panel", type=float, default=0.62)
    parser.add_argument("--strong-textline", type=float, default=0.46)
    parser.add_argument("--sheet-items", type=int, default=160)
    args = parser.parse_args()
    args.taxonomy = args.taxonomy or DEFAULT_TAXONOMY
    print(json.dumps(build(args), indent=2))


if __name__ == "__main__":
    main()
