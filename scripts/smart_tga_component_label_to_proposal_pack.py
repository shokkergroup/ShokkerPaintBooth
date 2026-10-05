"""Convert reviewed Smart TGA component labels into proposal-training packs.

This is offline Smart TGA tooling. It bridges the reviewed component-label
workflow into the older number-proposal evaluator by exporting true race-number
components as a number manifest and sponsor/paint/template confusers as a
hard-negative/taxonomy pack. It does not affect Auto-build Layers runtime.
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


REPO_ROOT = Path(__file__).resolve().parents[1]
WORK = 1024


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:110] or "unknown"


def _xywh_to_xyxy(box: list[int]) -> list[int]:
    x, y, w, h = [int(v) for v in box]
    return [x, y, x + w, y + h]


def _clip_xyxy(box: list[int], width: int, height: int) -> list[int]:
    x0, y0, x1, y1 = [int(v) for v in box]
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    return [x0, y0, x1, y1]


def _bbox_ok(actual: list[int], expected: list[int] | None) -> bool:
    if not expected:
        return True
    return all(abs(int(a) - int(e)) <= 1 for a, e in zip(actual, expected))


def _find_inspection(records_path: Path, paint_label: str) -> dict[str, Any]:
    records = _read_json(records_path)
    for record in records:
        if record.get("paint_label") == paint_label:
            return record
    raise ValueError(f"paint_label {paint_label!r} not found in {records_path}")


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str, max_items: int) -> None:
    rows = records[:max_items]
    if not rows:
        return
    cols = 5
    cell_w = 245
    cell_h = 230
    sheet = Image.new("RGB", (cols * cell_w, int(np.ceil(len(rows) / cols)) * cell_h), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 6), title, fill=(255, 255, 255))
    for idx, rec in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        src = Path(str(rec.get("file") or ""))
        if src.is_file():
            img = Image.open(src).convert("RGB")
            img.thumbnail((190, 150), Image.Resampling.LANCZOS)
            sheet.paste(img, (x + 27, y + 42))
        draw.text((x + 6, y + 22), f"{idx:02d} {rec.get('label', '?')}", fill=(255, 230, 130))
        draw.text((x + 6, y + 184), str(rec.get("subtype") or "")[:38], fill=(170, 220, 255))
        draw.text((x + 6, y + 202), str(rec.get("group") or "")[:38], fill=(220, 220, 220))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _copy_crop(source_image: Image.Image, box: list[int], out_path: Path) -> str:
    width, height = source_image.size
    x0, y0, x1, y1 = _clip_xyxy(box, width, height)
    crop = source_image.crop((x0, y0, x1, y1)).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out_path)
    return str(out_path.resolve())


def _record_for_label(
    label_row: dict[str, Any],
    component: dict[str, Any],
    inspection: dict[str, Any],
    source_image: Image.Image,
    out_dir: Path,
    ordinal: int,
) -> dict[str, Any]:
    target = str(label_row.get("target_layer") or component.get("layer") or "")
    is_number = target == "numbers"
    source_layer = str(label_row.get("layer") or component.get("layer") or "")
    comp_idx = int(label_row.get("component_index", component.get("component_index", -1)))
    bbox_xywh = label_row.get("review_bbox") or component.get("bbox")
    if not (isinstance(bbox_xywh, list) and len(bbox_xywh) == 4):
        raise ValueError(f"missing bbox for {source_layer} component {comp_idx}")
    bbox_xywh = [int(v) for v in bbox_xywh]
    expected = label_row.get("expected_bbox")
    if not label_row.get("review_bbox") and not _bbox_ok([int(v) for v in component.get("bbox", [])], expected):
        raise ValueError(
            f"bbox mismatch for {source_layer} component {comp_idx}: "
            f"{component.get('bbox')} != {expected}"
        )

    analyzed_box = _xywh_to_xyxy(bbox_xywh)
    label = "number" if is_number else "hard_negative"
    subtype = "number" if is_number else str(label_row.get("label") or target or "reviewed_hard_negative")
    folder = Path(str(inspection.get("paint") or "")).parent.name or str(inspection.get("paint_label") or "source")
    stem = Path(str(inspection.get("paint") or inspection.get("paint_label") or "paint")).stem
    file_name = f"{label}_{ordinal:04d}_{_safe_name(source_layer)}_{comp_idx:03d}_{_safe_name(subtype)}.png"
    crop_file = _copy_crop(source_image, analyzed_box, out_dir / ("number" if is_number else "hard_negative") / file_name)
    rec = {
        "source_kind": "reviewed_component_label",
        "folder": folder,
        "paint": inspection.get("paint"),
        "source": inspection.get("paint"),
        "source_path": inspection.get("paint"),
        "paint_label": inspection.get("paint_label"),
        "group": f"{folder}/{stem}",
        "component_layer": source_layer,
        "component_index": comp_idx,
        "target_layer": target,
        "component_label": label_row.get("label"),
        "note": label_row.get("note"),
        "subtype": subtype,
        "label": label,
        "truth": "number" if is_number else "non_number",
        "file": crop_file,
        "crop_file": crop_file,
        "box": analyzed_box,
        "analyzed_box": analyzed_box,
        "bbox_xywh": bbox_xywh,
        "component_area": component.get("area_px"),
        "component_role_guess": component.get("role_guess"),
        "features": {
            key: component.get(key)
            for key in (
                "area_frac",
                "aspect",
                "fill",
                "mean_saturation",
                "mean_value",
                "edge_density",
                "color_std",
            )
            if component.get(key) is not None
        },
    }
    return rec


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    labels_path = _repo_path(args.labels)
    labels_doc = _read_json(labels_path)
    paint_label = str(labels_doc["paint_label"])
    inspection_path = _repo_path(labels_doc["inspection_records"])
    inspection = _find_inspection(inspection_path, paint_label)
    components_path = Path(str(inspection["component_records"]))
    components = _read_json(components_path)
    component_map = {
        (str(row.get("layer")), int(row.get("component_index", -1))): row
        for row in components
    }
    source_image = Image.open(str(inspection["source_1024"])).convert("RGB")
    out_dir = _repo_path(args.output)
    if out_dir.exists() and args.clean:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    number_records: list[dict[str, Any]] = []
    hard_negative_records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    excluded_layers = {str(layer).lower() for layer in args.exclude_source_layer}
    excluded_labels = {str(label).lower() for label in args.exclude_label}
    for label_row in labels_doc.get("component_labels", []):
        source_layer = str(label_row.get("layer") or "").lower()
        label_name = str(label_row.get("label") or "").lower()
        if source_layer in excluded_layers or label_name in excluded_labels:
            skipped.append({
                "key": [label_row.get("layer"), label_row.get("component_index")],
                "reason": "excluded_by_filter",
                "source_layer": label_row.get("layer"),
                "label": label_row.get("label"),
            })
            continue
        key = (str(label_row.get("layer")), int(label_row.get("component_index", -1)))
        component = component_map.get(key)
        if component is None:
            skipped.append({"key": key, "reason": "component_not_found"})
            continue
        ordinal = len(number_records) if label_row.get("target_layer") == "numbers" else len(hard_negative_records)
        rec = _record_for_label(label_row, component, inspection, source_image, out_dir, ordinal)
        if rec["label"] == "number":
            number_records.append(rec)
        else:
            hard_negative_records.append(rec)

    number_path = out_dir / "number_manifest.json"
    hard_negative_path = out_dir / "hard_negative_manifest.json"
    taxonomy_path = out_dir / "taxonomy_records.json"
    all_path = out_dir / "manifest.json"
    number_path.write_text(json.dumps(number_records, indent=2), encoding="utf-8")
    hard_negative_path.write_text(json.dumps(hard_negative_records, indent=2), encoding="utf-8")
    taxonomy_path.write_text(json.dumps(hard_negative_records, indent=2), encoding="utf-8")
    all_path.write_text(json.dumps(number_records + hard_negative_records, indent=2), encoding="utf-8")

    _contact_sheet(number_records, out_dir / "number_components.png", "Reviewed true number components", args.sheet_items)
    _contact_sheet(
        hard_negative_records,
        out_dir / "hard_negative_components.png",
        "Reviewed non-number component confusers",
        args.sheet_items,
    )
    _contact_sheet(
        number_records + hard_negative_records,
        out_dir / "all_reviewed_components.png",
        "Reviewed component proposal pack",
        args.sheet_items,
    )

    summary = {
        "labels": str(labels_path.resolve()),
        "inspection_records": str(inspection_path.resolve()),
        "component_records": str(components_path.resolve()),
        "paint_label": paint_label,
        "output": str(out_dir.resolve()),
        "number_records": len(number_records),
        "hard_negative_records": len(hard_negative_records),
        "skipped": skipped,
        "by_subtype": dict(Counter(str(rec.get("subtype")) for rec in hard_negative_records)),
        "by_source_layer": dict(Counter(str(rec.get("component_layer")) for rec in number_records + hard_negative_records)),
        "number_manifest": str(number_path.resolve()),
        "hard_negative_manifest": str(hard_negative_path.resolve()),
        "taxonomy_records": str(taxonomy_path.resolve()),
        "manifest": str(all_path.resolve()),
        "number_sheet": str((out_dir / "number_components.png").resolve()) if number_records else None,
        "hard_negative_sheet": str((out_dir / "hard_negative_components.png").resolve()) if hard_negative_records else None,
        "all_sheet": str((out_dir / "all_reviewed_components.png").resolve()) if number_records or hard_negative_records else None,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, help="Reviewed component label JSON")
    parser.add_argument("--output", required=True, help="Output pack directory")
    parser.add_argument("--sheet-items", type=int, default=120)
    parser.add_argument("--clean", action="store_true", help="Remove an existing output directory first")
    parser.add_argument(
        "--exclude-source-layer",
        action="append",
        default=[],
        help="Skip reviewed rows from this original source layer, e.g. paint.",
    )
    parser.add_argument(
        "--exclude-label",
        action="append",
        default=[],
        help="Skip reviewed rows with this label.",
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(build_pack(parse_args()), indent=2))


if __name__ == "__main__":
    main()
