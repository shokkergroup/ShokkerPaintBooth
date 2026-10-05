"""Probe route outputs for sponsor components that match hard-negative retainers.

This is offline Smart TGA tooling. It scans ``component_records.json`` files
emitted by ``smart_tga_route_layer_inspector.py`` and writes a compact candidate
sheet for Sponsor components shaped like known number-confusing sponsor decals.
It does not change runtime masks.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _shape_rules(record: dict[str, Any]) -> list[str]:
    bbox = record.get("bbox") or [0, 0, 0, 0]
    width = int(bbox[2] or 0)
    height = int(bbox[3] or 0)
    center_y = float(record.get("centroid_y") or ((float(bbox[1] or 0) + height / 2.0) / 1024.0))
    area_px = float(record.get("area_px") or 0.0)
    aspect = float(record.get("aspect") or 0.0)
    fill = float(record.get("fill") or 0.0)
    mean_saturation = float(record.get("mean_saturation") or 0.0)
    mean_value = float(record.get("mean_value") or 0.0)
    edge_density = float(record.get("edge_density") or 0.0)
    color_std = float(record.get("color_std") or 0.0)

    hits: list[str] = []
    if (
        600 <= area_px <= 1000
        and 4.50 <= aspect <= 7.00
        and 0.50 <= fill <= 0.75
        and 0.55 <= mean_saturation <= 0.80
        and 0.45 <= mean_value <= 0.65
        and 0.32 <= edge_density <= 0.42
        and 0.30 <= color_std <= 0.42
        and 70 <= width <= 100
        and 10 <= height <= 22
    ):
        hits.append("thin_sponsor_textline_on_number_panel")

    if (
        2800 <= area_px <= 4200
        and 0.90 <= aspect <= 1.30
        and 0.24 <= fill <= 0.38
        and 0.12 <= mean_saturation <= 0.32
        and 0.30 <= mean_value <= 0.45
        and 0.22 <= edge_density <= 0.31
        and 0.36 <= color_std <= 0.46
        and 85 <= width <= 140
        and 75 <= height <= 125
    ):
        hits.append("high_variance_sponsor_logo_graphic")

    if (
        2500 <= area_px <= 3800
        and 2.20 <= aspect <= 3.00
        and 0.68 <= fill <= 0.86
        and 0.42 <= mean_saturation <= 0.64
        and 0.52 <= mean_value <= 0.72
        and 0.29 <= edge_density <= 0.39
        and 0.30 <= color_std <= 0.39
        and 85 <= width <= 130
        and 30 <= height <= 55
    ):
        hits.append("high_variance_sponsor_text_panel")

    if (
        2000 <= area_px <= 8500
        and 1.85 <= aspect <= 4.25
        and 0.74 <= fill <= 0.94
        and 0.14 <= mean_saturation <= 0.42
        and 0.54 <= mean_value <= 0.70
        and 0.29 <= edge_density <= 0.41
        and 0.34 <= color_std <= 0.42
        and 95 <= width <= 175
        and 24 <= height <= 75
    ):
        hits.append("large_low_sat_sponsor_wordmark")

    if (
        4800 <= area_px <= 60000
        and (
            (2.45 <= aspect <= 4.05 and width >= 120 and height >= 45)
            or (0.38 <= aspect <= 0.66 and width >= 120 and height >= 90)
        )
        and 0.50 <= fill <= 0.86
        and 0.58 <= mean_saturation <= 0.98
        and 0.58 <= mean_value <= 0.92
        and 0.075 <= edge_density <= 0.17
        and 0.16 <= color_std <= 0.38
    ):
        hits.append("large_saturated_stockcar_sponsor_panel")

    if (
        30 <= area_px <= 900
        and 0.80 <= aspect <= 3.35
        and 0.50 <= fill <= 0.95
        and mean_saturation <= 0.28
        and 0.40 <= mean_value <= 0.58
        and 0.30 <= edge_density <= 0.47
        and 0.29 <= color_std <= 0.44
        and 0.20 <= center_y <= 0.95
        and width <= 55
        and height <= 25
    ):
        hits.append("small_neutral_contingency_fragment")

    if (
        500 <= area_px <= 6500
        and 0.14 <= aspect <= 0.42
        and 0.62 <= fill <= 0.94
        and mean_saturation <= 0.40
        and 0.50 <= mean_value <= 0.72
        and 0.24 <= edge_density <= 0.38
        and 0.30 <= color_std <= 0.47
        and 16 <= width <= 40
        and 45 <= height <= 210
    ):
        hits.append("vertical_sponsor_wordmark")

    return hits


def _rules(record: dict[str, Any]) -> list[str]:
    if str(record.get("layer")) != "sponsors":
        return []
    return _shape_rules(record)


def _load_records(paths: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for value in paths:
        path = _repo_path(value)
        if path.is_dir():
            files = sorted(path.rglob("component_records.json"))
        else:
            files = [path]
        for file_path in files:
            for row in _read_json(file_path):
                item = dict(row)
                item["component_records_path"] = str(file_path.resolve())
                records.append(item)
    return records


def _write_contact_sheet(candidates: list[dict[str, Any]], path: Path, max_items: int) -> str | None:
    if not candidates:
        return None

    font = ImageFont.load_default()
    thumb_w, thumb_h = 190, 155
    cols = 4
    rows = min((len(candidates[:max_items]) + cols - 1) // cols, 16)
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "white")
    draw = ImageDraw.Draw(sheet)

    for idx, candidate in enumerate(candidates[: rows * cols]):
        crop_file = candidate.get("crop_file")
        x0 = (idx % cols) * thumb_w
        y0 = (idx // cols) * thumb_h
        try:
            crop = Image.open(str(crop_file)).convert("RGB")
        except Exception:
            crop = Image.new("RGB", (thumb_w, thumb_h - 45), (245, 245, 245))
        crop.thumbnail((thumb_w - 10, thumb_h - 48), Image.LANCZOS)
        sheet.paste(crop, (x0 + 5, y0 + 5))
        text = f"{idx:02d} {candidate['rule']}\n{candidate.get('paint_label')}\n{candidate.get('component_index')} {candidate.get('bbox')}"
        draw.multiline_text((x0 + 5, y0 + thumb_h - 42), text[:130], fill=(0, 0, 0), font=font)

    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.resolve())


def _sum_area_px(items: list[dict[str, Any]]) -> int:
    return int(sum(float(item.get("area_px") or 0) for item in items))


def run(args: argparse.Namespace) -> dict[str, Any]:
    records = _load_records(args.records)
    candidates: list[dict[str, Any]] = []
    for record in records:
        for rule in _rules(record):
            item = {
                "rule": rule,
                "paint_label": record.get("paint_label"),
                "paint": record.get("paint"),
                "layer": record.get("layer"),
                "component_index": record.get("component_index"),
                "role_guess": record.get("role_guess"),
                "bbox": record.get("bbox"),
                "area_px": record.get("area_px"),
                "area_frac": record.get("area_frac"),
                "aspect": record.get("aspect"),
                "fill": record.get("fill"),
                "mean_saturation": record.get("mean_saturation"),
                "mean_value": record.get("mean_value"),
                "edge_density": record.get("edge_density"),
                "color_std": record.get("color_std"),
                "crop_file": record.get("crop_file"),
                "component_records_path": record.get("component_records_path"),
            }
            candidates.append(item)

    all_layer_hits: list[dict[str, Any]] = []
    if args.audit_all_layers:
        for record in records:
            for rule in _shape_rules(record):
                all_layer_hits.append({
                    "rule": rule,
                    "paint_label": record.get("paint_label"),
                    "paint": record.get("paint"),
                    "layer": record.get("layer"),
                    "component_index": record.get("component_index"),
                    "role_guess": record.get("role_guess"),
                    "bbox": record.get("bbox"),
                    "area_px": record.get("area_px"),
                    "area_frac": record.get("area_frac"),
                    "aspect": record.get("aspect"),
                    "fill": record.get("fill"),
                    "mean_saturation": record.get("mean_saturation"),
                    "mean_value": record.get("mean_value"),
                    "edge_density": record.get("edge_density"),
                    "color_std": record.get("color_std"),
                    "crop_file": record.get("crop_file"),
                    "component_records_path": record.get("component_records_path"),
                    "risk": "expected_sponsor_layer" if str(record.get("layer")) == "sponsors" else "non_sponsor_collision",
                })

    out_dir = _repo_path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = out_dir / "sponsor_retainer_candidates.json"
    candidates_path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    sheet_path = _write_contact_sheet(candidates, out_dir / "sponsor_retainer_candidates.png", args.max_sheet_items)
    all_layer_hits_path = out_dir / "sponsor_retainer_all_layer_hits.json"
    all_layer_sheet_path: str | None = None
    risk_hits = [item for item in all_layer_hits if item["risk"] == "non_sponsor_collision"]
    if args.audit_all_layers:
        all_layer_hits_path.write_text(json.dumps(all_layer_hits, indent=2), encoding="utf-8")
        all_layer_sheet_path = _write_contact_sheet(
            risk_hits,
            out_dir / "sponsor_retainer_non_sponsor_risk_hits.png",
            args.max_sheet_items,
        )
    summary = {
        "records_scanned": len(records),
        "candidates": len(candidates),
        "by_rule": dict(Counter(item["rule"] for item in candidates)),
        "by_paint_label": dict(Counter(str(item.get("paint_label")) for item in candidates)),
        "candidates_path": str(candidates_path.resolve()),
        "contact_sheet": sheet_path,
        "audit_all_layers": bool(args.audit_all_layers),
    }
    if args.audit_all_layers:
        summary.update({
            "all_layer_hits": len(all_layer_hits),
            "non_sponsor_risk_hits": len(risk_hits),
            "already_sponsor_hits": len(all_layer_hits) - len(risk_hits),
            "non_sponsor_risk_area_px": _sum_area_px(risk_hits),
            "already_sponsor_area_px": _sum_area_px([item for item in all_layer_hits if item["risk"] == "expected_sponsor_layer"]),
            "non_sponsor_risk_by_layer": dict(Counter(str(item.get("layer")) for item in risk_hits)),
            "non_sponsor_risk_by_rule": dict(Counter(item["rule"] for item in risk_hits)),
            "non_sponsor_risk_by_paint_label": dict(Counter(str(item.get("paint_label")) for item in risk_hits)),
            "all_layer_hits_path": str(all_layer_hits_path.resolve()),
            "non_sponsor_risk_sheet": all_layer_sheet_path,
            "runtime_delta_recommendation": (
                "do_not_wire_runtime_yet_no_non_sponsor_hits"
                if candidates and not risk_hits
                else "inspect_non_sponsor_collisions_before_runtime"
                if risk_hits
                else "no_sponsor_retainer_shape_hits"
            ),
        })
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", nargs="+", required=True, help="component_records.json files or directories")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--max-sheet-items", type=int, default=64)
    parser.add_argument(
        "--audit-all-layers",
        action="store_true",
        help="Also report same-shape hits outside Sponsors as a runtime-promotion risk audit.",
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
