"""Generate and validate fail-closed Smart TGA owner review records.

The route inspector already writes exact connected-component bboxes and crop
paths.  This tool turns those records into a bounded review packet, then emits
golden-corpus entry fragments only after every in-scope prediction has an
explicit true/false/mixed decision.  An empty owner also needs an explicit
``empty_confirmed`` decision.  Nothing here changes runtime masks.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


OWNERS = ("numbers", "sponsors", "template", "brand_graphics", "paint")
DEFAULT_MIN_AREA = {
    "numbers": 8,
    "sponsors": 20,
    "template": 20,
    "brand_graphics": 20,
    "paint": 20,
}
VERDICTS = frozenset(("unreviewed", "true", "false", "mixed"))


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _normalize_label(value: Any) -> str:
    return str(value or "").replace("\\", "/")


def _mask_components(path: Path, min_area: int) -> list[dict[str, Any]]:
    mask = np.asarray(Image.open(path).convert("L")) > 127
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), 8
    )
    components = []
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        components.append({
            "component_index": index - 1,
            "area_px": area,
            "bbox": [
                int(stats[index, cv2.CC_STAT_LEFT]),
                int(stats[index, cv2.CC_STAT_TOP]),
                int(stats[index, cv2.CC_STAT_WIDTH]),
                int(stats[index, cv2.CC_STAT_HEIGHT]),
            ],
        })
    return components


def _parse_owners(values: Sequence[str]) -> tuple[str, ...]:
    owners: list[str] = []
    for value in values:
        for owner in value.split(","):
            owner = owner.strip()
            if not owner:
                continue
            if owner not in OWNERS:
                raise ValueError(f"unknown owner {owner!r}")
            if owner not in owners:
                owners.append(owner)
    if not owners:
        raise ValueError("at least one owner is required")
    return tuple(owners)


def _parse_min_areas(values: Sequence[str]) -> dict[str, int]:
    result = dict(DEFAULT_MIN_AREA)
    for value in values:
        if "=" not in value:
            raise ValueError(f"min-area must be OWNER=PIXELS, got {value!r}")
        owner, pixels = value.split("=", 1)
        owner = owner.strip()
        if owner not in OWNERS:
            raise ValueError(f"unknown min-area owner {owner!r}")
        result[owner] = max(1, int(pixels))
    return result


def build_packet(
    run_dir: Path,
    *,
    owners: Sequence[str],
    min_areas: Mapping[str, int],
    paint_labels: Sequence[str] = (),
) -> dict[str, Any]:
    records_path = run_dir / "inspection_records.json"
    records = _read(records_path)
    selected = {_normalize_label(value) for value in paint_labels}
    packet_records = []
    for route_record in records:
        label = _normalize_label(route_record.get("paint_label"))
        if selected and label not in selected:
            continue
        component_path = Path(str(route_record.get("component_records") or ""))
        if not component_path.is_file():
            raise FileNotFoundError(f"component records missing for {label}: {component_path}")
        inspector_components = _read(component_path)
        metadata_by_owner_bbox = {
            (str(component.get("layer") or ""), tuple(int(value) for value in component.get("bbox") or [])): component
            for component in inspector_components
            if len(component.get("bbox") or []) == 4
        }
        mask_paths = route_record.get("mask_paths") or {}
        owner_records: dict[str, Any] = {}
        for owner in owners:
            min_area = int(min_areas[owner])
            mask_path = Path(str(mask_paths.get(owner) or ""))
            if not mask_path.is_file():
                raise FileNotFoundError(f"mask missing for {label} {owner}: {mask_path}")
            predictions = []
            for component in _mask_components(mask_path, min_area):
                index = int(component["component_index"])
                bbox = [int(value) for value in component["bbox"]]
                metadata = metadata_by_owner_bbox.get((owner, tuple(bbox)), {})
                predictions.append({
                    "key": f"{owner}:{index}:{':'.join(str(value) for value in bbox)}",
                    "component_index": index,
                    "bbox": bbox,
                    "area_px": int(component["area_px"]),
                    "role_guess": metadata.get("role_guess") or "mask_component",
                    "crop_file": metadata.get("crop_file"),
                    "verdict": "unreviewed",
                    "note": "",
                })
            owner_records[owner] = {
                "component_min_area": min_area,
                "empty_confirmed": False,
                "missing_bboxes": [],
                "predictions": predictions,
            }
        packet_records.append({
            "paint_label": label,
            "paint": route_record.get("paint"),
            "source_1024": route_record.get("source_1024"),
            "owners": owner_records,
        })
    missing = sorted(selected - {record["paint_label"] for record in packet_records})
    if missing:
        raise ValueError(f"paint labels not found in run: {missing}")
    return {
        "schema": "spb-smart-tga-full-owner-review-v1",
        "inspection_records": str(records_path.resolve()),
        "owners": list(owners),
        "records": packet_records,
    }


def validate_and_export(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    if packet.get("schema") != "spb-smart-tga-full-owner-review-v1":
        raise ValueError("unsupported full-owner review schema")
    entries = []
    failures = []
    for record in packet.get("records") or []:
        label = _normalize_label(record.get("paint_label"))
        component_reviews: dict[str, Any] = {}
        reviewed_owners = []
        for owner, owner_record in (record.get("owners") or {}).items():
            if owner not in OWNERS:
                raise ValueError(f"unknown owner {owner!r}")
            predictions = owner_record.get("predictions") or []
            if not predictions and not bool(owner_record.get("empty_confirmed")):
                failures.append(f"{label} {owner}: empty owner is not explicitly confirmed")
                continue
            buckets = {verdict: [] for verdict in ("true", "false", "mixed")}
            seen_keys = set()
            for prediction in predictions:
                key = str(prediction.get("key") or "")
                if not key or key in seen_keys:
                    failures.append(f"{label} {owner}: duplicate or empty component key {key!r}")
                    continue
                seen_keys.add(key)
                verdict = str(prediction.get("verdict") or "unreviewed")
                if verdict not in VERDICTS:
                    failures.append(f"{label} {owner} {key}: invalid verdict {verdict!r}")
                    continue
                if verdict == "unreviewed":
                    failures.append(f"{label} {owner} {key}: prediction remains unreviewed")
                    continue
                buckets[verdict].append([int(value) for value in prediction["bbox"]])
            if any(failure.startswith(f"{label} {owner}") for failure in failures):
                continue
            reviewed_owners.append(owner)
            component_reviews[owner] = {
                "component_min_area": int(owner_record.get("component_min_area") or 1),
                "iou_threshold": 0.95,
                "require_all_predictions_reviewed": True,
                "min_reviewed_precision": 0.0,
                "min_reviewed_recall": 0.0,
                "missing_iou_threshold": 0.50,
                "true_bboxes": buckets["true"],
                "false_bboxes": buckets["false"],
                "mixed_bboxes": buckets["mixed"],
                "missing_bboxes": [
                    [int(value) for value in bbox]
                    for bbox in owner_record.get("missing_bboxes") or []
                ],
            }
        entries.append({
            "id": label.lower().replace("/", "-").replace("_", "-").replace(".", "-"),
            "family": label.split("/", 1)[0],
            "paint_label": label,
            "expected_build_prefix": "smart-tga-cycle",
            "review_status": "partial",
            "reviewed_owners": reviewed_owners,
            "known_issues": [
                f"Owners not yet reviewed: {', '.join(owner for owner in OWNERS if owner not in reviewed_owners)}."
            ] if set(reviewed_owners) != set(OWNERS) else [],
            "component_reviews": component_reviews,
        })
    if failures:
        raise ValueError("review packet is incomplete:\n- " + "\n- ".join(failures))
    return entries


def apply_decisions(packet: Mapping[str, Any], decisions: Mapping[str, Any]) -> dict[str, Any]:
    """Apply a compact explicit key→verdict map without mutating the draft."""
    if decisions.get("schema") != "spb-smart-tga-full-owner-decisions-v1":
        raise ValueError("unsupported full-owner decision schema")
    out = copy.deepcopy(packet)
    decision_records = {
        _normalize_label(record.get("paint_label")): record
        for record in decisions.get("records") or []
    }
    packet_labels = {_normalize_label(record.get("paint_label")) for record in out.get("records") or []}
    unknown_labels = sorted(set(decision_records) - packet_labels)
    if unknown_labels:
        raise ValueError(f"decision labels not present in packet: {unknown_labels}")
    for record in out.get("records") or []:
        label = _normalize_label(record.get("paint_label"))
        decision_record = decision_records.get(label, {})
        for owner, owner_record in (record.get("owners") or {}).items():
            owner_decision = (decision_record.get("owners") or {}).get(owner, {})
            default_verdict = owner_decision.get("default_verdict")
            if default_verdict is not None:
                default_verdict = str(default_verdict)
                if default_verdict not in ("true", "false", "mixed"):
                    raise ValueError(
                        f"{label} {owner}: default_verdict must be true, false, or mixed"
                    )
            verdicts = {str(key): str(value) for key, value in (owner_decision.get("verdicts") or {}).items()}
            prediction_by_key = {
                str(prediction.get("key") or ""): prediction
                for prediction in owner_record.get("predictions") or []
            }
            unknown_keys = sorted(set(verdicts) - set(prediction_by_key))
            if unknown_keys:
                raise ValueError(f"{label} {owner}: unknown decision keys {unknown_keys}")
            if default_verdict is not None:
                for prediction in prediction_by_key.values():
                    prediction["verdict"] = default_verdict
            for key, verdict in verdicts.items():
                prediction_by_key[key]["verdict"] = verdict
            if "empty_confirmed" in owner_decision:
                owner_record["empty_confirmed"] = bool(owner_decision["empty_confirmed"])
            if "missing_bboxes" in owner_decision:
                owner_record["missing_bboxes"] = owner_decision["missing_bboxes"]
    return out


def write_html(packet: Mapping[str, Any], output: Path) -> None:
    sections = []
    for record in packet.get("records") or []:
        source = Path(str(record.get("source_1024") or ""))
        source_image = Image.open(source).convert("RGB") if source.is_file() else None
        owner_sections = []
        for owner, owner_record in (record.get("owners") or {}).items():
            cards = []
            for prediction in owner_record.get("predictions") or []:
                crop = Path(str(prediction.get("crop_file") or ""))
                if not crop.is_file() and source_image is not None:
                    x, y, width, height = prediction["bbox"]
                    pad = max(8, int(round(max(width, height) * 0.35)))
                    left, top = max(0, x - pad), max(0, y - pad)
                    right = min(source_image.width, x + width + pad)
                    bottom = min(source_image.height, y + height + pad)
                    crop = output.parent / "review_crops" / record["paint_label"].replace("/", "_") / f"{prediction['key'].replace(':', '_')}.png"
                    crop.parent.mkdir(parents=True, exist_ok=True)
                    source_image.crop((left, top, right, bottom)).save(crop)
                crop_uri = crop.resolve().as_uri() if crop.is_file() else ""
                cards.append(
                    "<article>"
                    f"<img src=\"{html.escape(crop_uri)}\" alt=\"component crop\">"
                    f"<b>{html.escape(prediction['key'])}</b>"
                    f"<code>{html.escape(str(prediction['bbox']))}</code>"
                    f"<span>{prediction['area_px']} px · {html.escape(str(prediction.get('role_guess') or ''))}</span>"
                    "<em>UNREVIEWED — edit review.json to true / false / mixed</em>"
                    "</article>"
                )
            owner_sections.append(
                f"<h3>{html.escape(owner)} ({len(cards)})</h3>"
                + ("".join(cards) if cards else "<p>Empty — explicit confirmation required.</p>")
            )
        source_uri = source.resolve().as_uri() if source.is_file() else ""
        sections.append(
            f"<section><h2>{html.escape(record['paint_label'])}</h2>"
            f"<img class=\"source\" src=\"{html.escape(source_uri)}\" alt=\"source paint\">"
            + "".join(owner_sections) + "</section>"
        )
    output.write_text("""<!doctype html><meta charset="utf-8"><title>Smart TGA Owner Review</title>
<style>body{font:14px system-ui;background:#111;color:#eee;margin:20px}section{border-top:2px solid #555;margin-top:28px}.source{width:512px;max-width:100%}article{display:inline-flex;vertical-align:top;flex-direction:column;width:220px;margin:6px;padding:8px;background:#222;gap:4px}article img{width:220px;height:150px;object-fit:contain;background:#000}code{color:#9cf}em{color:#ff8;font-size:12px}</style>
<h1>Smart TGA fail-closed owner review</h1><p>Every component must be true, false, or mixed in review.json. Empty owners require empty_confirmed=true. Missing decals belong in missing_bboxes.</p>""" + "".join(sections), encoding="utf-8")


def write_owner_sheets(packet: Mapping[str, Any], output_dir: Path) -> None:
    """Render mask-authoritative review sheets, including inspector omissions."""
    sheet_dir = output_dir / "review_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    columns, card_width, card_height = 4, 280, 220
    for record in packet.get("records") or []:
        source = Path(str(record.get("source_1024") or ""))
        source_image = Image.open(source).convert("RGB") if source.is_file() else None
        slug = record["paint_label"].replace("/", "_").replace(".", "_")
        for owner, owner_record in (record.get("owners") or {}).items():
            predictions = owner_record.get("predictions") or []
            rows = max(1, (len(predictions) + columns - 1) // columns)
            sheet = Image.new("RGB", (columns * card_width, rows * card_height + 36), (18, 18, 18))
            draw = ImageDraw.Draw(sheet)
            draw.text((8, 8), f"{record['paint_label']} — {owner} — {len(predictions)} authoritative components", fill=(245, 245, 245))
            for position, prediction in enumerate(predictions):
                column, row = position % columns, position // columns
                left, top = column * card_width, 36 + row * card_height
                crop = Path(str(prediction.get("crop_file") or ""))
                if not crop.is_file() and source_image is not None:
                    x, y, width, height = prediction["bbox"]
                    pad = max(8, int(round(max(width, height) * 0.35)))
                    crop = output_dir / "review_crops" / record["paint_label"].replace("/", "_") / f"{prediction['key'].replace(':', '_')}.png"
                    if not crop.is_file():
                        crop.parent.mkdir(parents=True, exist_ok=True)
                        source_image.crop((
                            max(0, x - pad), max(0, y - pad),
                            min(source_image.width, x + width + pad),
                            min(source_image.height, y + height + pad),
                        )).save(crop)
                if crop.is_file():
                    image = Image.open(crop).convert("RGB")
                    image.thumbnail((250, 150), Image.Resampling.LANCZOS)
                    framed = ImageOps.pad(image, (250, 150), color=(0, 0, 0))
                    sheet.paste(framed, (left + 15, top + 6))
                draw.rectangle((left + 14, top + 5, left + 266, top + 157), outline=(255, 60, 170), width=2)
                draw.text((left + 15, top + 164), prediction["key"], fill=(255, 220, 80))
                draw.text((left + 15, top + 180), f"bbox={prediction['bbox']} area={prediction['area_px']}", fill=(190, 220, 255))
                draw.text((left + 15, top + 196), f"verdict={prediction['verdict']}", fill=(255, 180, 180))
            sheet.save(sheet_dir / f"{slug}_{owner}.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--owner", action="append", default=[])
    parser.add_argument("--paint-label", action="append", default=[])
    parser.add_argument("--min-area", action="append", default=[])
    parser.add_argument("--review", type=Path, help="Validate an edited review.json and export manifest entries")
    parser.add_argument("--decisions", type=Path, help="Compact explicit decision map applied before validation")
    parser.add_argument(
        "--shard-output",
        type=Path,
        help="Also write a directly loadable spb-smart-tga-golden-entries-v1 shard",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    if args.review:
        packet = _read(args.review)
        if args.decisions:
            packet = apply_decisions(packet, _read(args.decisions))
        entries = validate_and_export(packet)
        _write(args.output / "manifest_entries.json", entries)
        if args.shard_output:
            _write(args.shard_output, {
                "schema": "spb-smart-tga-golden-entries-v1",
                "description": "Fail-closed five-owner component review export.",
                "entries": entries,
            })
        print(json.dumps({"status": "complete", "entry_count": len(entries), "owner_record_count": sum(len(entry["reviewed_owners"]) for entry in entries)}, indent=2))
        return 0
    if not args.run:
        parser.error("--run is required when --review is not supplied")
    owners = _parse_owners(args.owner)
    packet = build_packet(
        args.run,
        owners=owners,
        min_areas=_parse_min_areas(args.min_area),
        paint_labels=args.paint_label,
    )
    _write(args.output / "review.json", packet)
    write_html(packet, args.output / "review.html")
    write_owner_sheets(packet, args.output)
    print(json.dumps({"status": "draft", "paint_count": len(packet["records"]), "owner_record_count": sum(len(record["owners"]) for record in packet["records"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
