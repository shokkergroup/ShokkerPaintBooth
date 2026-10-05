"""Export reviewed Smart TGA component-number rows as evaluator holdouts.

This is offline Smart TGA tooling. Reviewed component feature banks use bbox
coordinates as x/y/w/h component boxes; the multiclass proposal evaluator expects
taxonomy-style x0/y0/x1/y1 records. This converter makes true-number component
holdouts reusable without changing Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


IRACING_PAINT_ROOT = Path(r"C:\Users\Ricky's PC\Documents\iRacing\paint")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:96] or "sample"


def _source_from_paint_label(paint_label: str) -> Path:
    return IRACING_PAINT_ROOT / Path(paint_label)


def _xywh_to_xyxy(box: list[Any]) -> list[int]:
    if len(box) != 4:
        raise ValueError(f"expected xywh bbox with 4 values, got {box!r}")
    x, y, w, h = [int(round(float(v))) for v in box]
    return [x, y, x + max(1, w), y + max(1, h)]


def _crop_source(source: Path, box: list[int], pad: int) -> Image.Image | None:
    if not source.is_file():
        return None
    img = Image.open(source).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
    x0, y0, x1, y1 = box
    x0 = max(0, min(1023, x0 - pad))
    y0 = max(0, min(1023, y0 - pad))
    x1 = max(x0 + 1, min(1024, x1 + pad))
    y1 = max(y0 + 1, min(1024, y1 + pad))
    return img.crop((x0, y0, x1, y1))


def _write_contact_sheet(records: list[dict[str, Any]], output: Path, items: int) -> None:
    thumbs: list[tuple[Image.Image, dict[str, Any]]] = []
    for rec in records[:items]:
        crop = _crop_source(Path(str(rec["source_path"])), rec["analyzed_box"], 12)
        if crop is None:
            continue
        crop.thumbnail((128, 128), Image.Resampling.LANCZOS)
        thumbs.append((crop.copy(), rec))
    if not thumbs:
        return
    cols = 5
    cell_w, cell_h = 190, 172
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for idx, (crop, rec) in enumerate(thumbs):
        col = idx % cols
        row = idx // cols
        x = col * cell_w
        y = row * cell_h
        sheet.paste(crop, (x, y + 28))
        title = f"{idx:02d} number"
        source = Path(str(rec["source_path"]))
        draw.text((x + 4, y + 4), title, fill=(255, 230, 90))
        draw.text((x + 4, y + 138), source.parent.name[:24], fill=(230, 230, 230))
        draw.text((x + 4, y + 154), source.name[:28], fill=(190, 190, 190))
    sheet.save(output)


def build_holdout(feature_banks: list[Path], output: Path, sheet_items: int) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[int, int, int, int]]] = set()
    for bank_path in feature_banks:
        rows = _read_json(bank_path)
        if not isinstance(rows, list):
            raise ValueError(f"expected list in {bank_path}")
        for idx, rec in enumerate(rows):
            if str(rec.get("target_layer")) != "numbers":
                continue
            if str(rec.get("label")) != "true_number":
                continue
            paint_label = str(rec.get("paint_label") or "")
            source = _source_from_paint_label(paint_label)
            box = _xywh_to_xyxy(list(rec.get("bbox") or []))
            key = (str(source).lower(), tuple(box))
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "truth": "number",
                "subtype": "number",
                "folder": source.parent.name,
                "source": str(source),
                "source_path": str(source),
                "paint_label": paint_label,
                "analyzed_box": box,
                "component_bbox_xywh": rec.get("bbox"),
                "component_index": rec.get("component_index"),
                "source_layer": rec.get("layer"),
                "label": "true_number",
                "origin": str(bank_path),
                "origin_index": idx,
            })
    records.sort(key=lambda rec: (str(rec["folder"]), str(rec["source"]), tuple(rec["analyzed_box"])))
    records_path = output / "number_holdout_taxonomy.json"
    records_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    sheet_path = output / "number_holdout_contact_sheet.png"
    _write_contact_sheet(records, sheet_path, sheet_items)
    summary = {
        "feature_banks": [str(path) for path in feature_banks],
        "records": len(records),
        "folders": sorted({str(rec["folder"]) for rec in records}),
        "taxonomy": str(records_path),
        "contact_sheet": str(sheet_path) if sheet_path.is_file() else None,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-bank", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sheet-items", type=int, default=80)
    args = parser.parse_args()
    summary = build_holdout(args.feature_bank, args.output, args.sheet_items)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
