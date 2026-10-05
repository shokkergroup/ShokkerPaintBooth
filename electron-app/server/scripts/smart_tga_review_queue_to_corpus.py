"""Merge reviewed Smart TGA number-candidate queues into a detector corpus.

This is offline Smart TGA tooling. It takes a base race-number crop manifest,
one or more candidate-miner review queues, and a small human-reviewed label map.
The output is a new manifest with copied reviewed crops and contact sheets.
It does not affect app behavior.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


PATCH = 160


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:96] or "sample"


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
        source = str(rec.get("folder") or rec.get("probe_label") or "")
        draw.text((x + 6, y + 4), f"{idx:02d} {rec['label']}", fill=(255, 255, 180))
        draw.text((x + 6, y + 178), source[:26], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected manifest list in {path}")
    return data


def _queue_key(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").lower()


def _load_label_map(path: Path) -> dict[str, dict[int, dict[str, str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    queue_maps: dict[str, dict[int, dict[str, str]]] = {}
    entries = data.get("queues", [])
    if not isinstance(entries, list):
        raise ValueError("label map must contain a 'queues' list")
    for entry in entries:
        queue_path = Path(entry["review_queue"])
        labels: dict[int, dict[str, str]] = {}
        default_subtypes = {
            "number": entry.get("default_number_subtype") or "number",
            "hard_negative": entry.get("default_hard_negative_subtype"),
            "skip": entry.get("default_skip_subtype"),
        }
        for label_name in ("number", "hard_negative", "skip"):
            for raw_index in entry.get(label_name, []):
                index = int(raw_index)
                if index in labels:
                    raise ValueError(f"duplicate review index {index} in {queue_path}")
                labels[index] = {"label": label_name}
                if default_subtypes.get(label_name):
                    labels[index]["subtype"] = str(default_subtypes[label_name])
        for raw_index, subtype in (entry.get("subtypes") or {}).items():
            index = int(raw_index)
            if index in labels:
                labels[index]["subtype"] = str(subtype)
        for raw_index, note in (entry.get("notes") or {}).items():
            index = int(raw_index)
            if index in labels:
                labels[index]["note"] = str(note)
        queue_maps[_queue_key(queue_path)] = labels
    return queue_maps


def _copy_reviewed_crop(item: dict[str, Any], out_dir: Path, label: str, sample_id: str) -> Path:
    crop_file = Path(item["crop_file"])
    if not crop_file.is_file():
        raise FileNotFoundError(crop_file)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{_safe_name(sample_id)}.png"
    # Re-save through Pillow so reviewed crops have a normalized 160x160 footprint.
    Image.open(crop_file).convert("RGB").resize((PATCH, PATCH), Image.Resampling.LANCZOS).save(out_path)
    return out_path.resolve()


def _record_from_item(
    item: dict[str, Any],
    queue_path: Path,
    label: str,
    out_root: Path,
    ordinal: int,
    subtype: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    subdir = "reviewed_number" if label == "number" else "reviewed_hard_negative"
    filename = f"{label}_{ordinal:04d}_{item.get('review_index', ordinal):02d}_{Path(item.get('paint', 'paint')).stem}"
    copied = _copy_reviewed_crop(item, out_root / subdir, label, filename)
    record = {
        "source_kind": "reviewed_candidate_queue",
        "source_queue": str(queue_path),
        "review_source": item.get("review_source"),
        "review_index": int(item.get("review_index", ordinal)),
        "folder": item.get("folder"),
        "paint": item.get("paint"),
        "candidate_label": item.get("label"),
        "candidate_prediction": item.get("prediction"),
        "candidate_raw_score": item.get("raw_score"),
        "candidate_ranker_score": item.get("ranker_score"),
        "candidate_image_score": item.get("image_score"),
        "candidate_meta_score": item.get("meta_score"),
        "candidate_meta_vetoed": item.get("meta_vetoed"),
        "candidate_ranker_rank": item.get("ranker_rank"),
        "candidate_proposal_index": item.get("proposal_index"),
        "candidate_proposal_variant": item.get("proposal_variant"),
        "candidate_proposal_score": item.get("proposal_score"),
        "candidate_area": item.get("area"),
        "candidate_fill": item.get("fill"),
        "candidate_edge_density": item.get("edge_density"),
        "candidate_soft_edge_density": item.get("soft_edge_density"),
        "candidate_sat_density": item.get("sat_density"),
        "candidate_aspect": item.get("aspect"),
        "raw_box": item.get("raw_box"),
        "label": label,
        "subtype": subtype or ("number" if label == "number" else "reviewed_hard_negative"),
        "file": str(copied),
        "box": item.get("box"),
    }
    if note:
        record["review_notes"] = note
    if label == "hard_negative":
        record["probe_label"] = f"review {item.get('folder') or Path(str(item.get('paint', 'unknown'))).stem}"
    return record


def merge_review_queues(args: argparse.Namespace) -> dict[str, Any]:
    out_root = args.output
    out_root.mkdir(parents=True, exist_ok=True)
    base_manifest = _load_manifest(args.base_manifest)
    queue_label_maps = _load_label_map(args.label_map)
    reviewed_numbers: list[dict[str, Any]] = []
    reviewed_negatives: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for queue_path in args.review_queue:
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        if not isinstance(queue, list):
            raise ValueError(f"expected queue list in {queue_path}")
        labels = queue_label_maps.get(_queue_key(queue_path), {})
        if not labels:
            raise ValueError(f"no labels found for review queue {queue_path}")
        for item in queue:
            index = int(item.get("review_index", -1))
            label_spec = labels.get(index)
            label = (label_spec or {}).get("label") or str(item.get("review_label") or "")
            if not label:
                continue
            if label == "skip":
                skipped.append({"queue": str(queue_path), "review_index": index, "reason": "label_map_skip"})
                continue
            if label not in {"number", "hard_negative"}:
                raise ValueError(f"unsupported label {label!r} for {queue_path} #{index}")
            ordinal = len(reviewed_numbers) if label == "number" else len(reviewed_negatives)
            rec = _record_from_item(
                item,
                queue_path,
                label,
                out_root,
                ordinal,
                subtype=(label_spec or {}).get("subtype"),
                note=(label_spec or {}).get("note"),
            )
            if label == "number":
                reviewed_numbers.append(rec)
            else:
                reviewed_negatives.append(rec)

    manifest = base_manifest + reviewed_numbers + reviewed_negatives
    manifest_path = out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    reviewed_only_path = out_root / "reviewed_only_manifest.json"
    reviewed_only_path.write_text(json.dumps(reviewed_numbers + reviewed_negatives, indent=2), encoding="utf-8")
    reviewed_number_path = out_root / "reviewed_number_manifest.json"
    reviewed_number_path.write_text(json.dumps(reviewed_numbers, indent=2), encoding="utf-8")
    reviewed_hard_negative_path = out_root / "reviewed_hard_negative_manifest.json"
    reviewed_hard_negative_path.write_text(json.dumps(reviewed_negatives, indent=2), encoding="utf-8")
    _contact_sheet(reviewed_numbers, out_root / "reviewed_number_contact_sheet.png", "Reviewed Smart TGA number crops")
    _contact_sheet(
        reviewed_negatives,
        out_root / "reviewed_hard_negative_contact_sheet.png",
        "Reviewed Smart TGA number confusers",
    )
    _contact_sheet(
        [r for r in manifest if r.get("label") == "number"],
        out_root / "all_number_contact_sheet.png",
        "All Smart TGA number crops",
    )
    _contact_sheet(
        [r for r in manifest if r.get("label") != "number"],
        out_root / "all_hard_negative_contact_sheet.png",
        "All Smart TGA hard negatives",
    )
    summary = {
        "base_manifest": str(args.base_manifest),
        "label_map": str(args.label_map),
        "review_queues": [str(p) for p in args.review_queue],
        "output": str(out_root.resolve()),
        "manifest": str(manifest_path.resolve()),
        "reviewed_only_manifest": str(reviewed_only_path.resolve()),
        "reviewed_number_manifest": str(reviewed_number_path.resolve()),
        "reviewed_hard_negative_manifest": str(reviewed_hard_negative_path.resolve()),
        "base_samples": len(base_manifest),
        "base_numbers": sum(1 for r in base_manifest if r.get("label") == "number"),
        "base_hard_negatives": sum(1 for r in base_manifest if r.get("label") != "number"),
        "reviewed_numbers": len(reviewed_numbers),
        "reviewed_hard_negatives": len(reviewed_negatives),
        "skipped": len(skipped),
        "samples": len(manifest),
        "positive_samples": sum(1 for r in manifest if r.get("label") == "number"),
        "hard_negative_samples": sum(1 for r in manifest if r.get("label") != "number"),
        "skipped_items": skipped,
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path, action="append", required=True)
    parser.add_argument("--label-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    summary = merge_review_queues(parse_args())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
