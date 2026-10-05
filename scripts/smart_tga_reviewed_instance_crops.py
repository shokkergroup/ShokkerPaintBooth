"""Export exact reviewed Smart TGA instance crops for a local family library.

The input route must use ``SPB_SMART_TGA_INSTANCE_FEATURE_EXPORT=1`` and carry
lossless ``mask_rle`` records.  Output is corpus material only: it never casts
votes, assigns ownership, or changes production masks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
from scripts.smart_tga_instance_feature_bank import attach_review_links, build_feature_bank


SCHEMA = "smart-tga-reviewed-instance-crops-v1"


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_") or "unknown"


def export_reviewed_instance_crops(
    inspection_records: Sequence[dict[str, Any]],
    label_documents: Sequence[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    bank = attach_review_links(build_feature_bank(inspection_records), label_documents)
    records = {
        (str(item["paint_label"]), str(item["instance_id"])): item
        for item in bank.get("records", ())
    }
    sources = {
        str(item.get("paint_label") or item.get("paint") or ""): Path(str(item["source_1024"]))
        for item in inspection_records
        if item.get("source_1024")
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    skipped = {"not_matched": 0, "missing_family": 0, "unsupported_owner": 0, "missing_mask": 0}
    seen = set()
    for link in bank.get("review_links", ()):
        if link.get("status") != "matched_for_review" or not link.get("instance_id"):
            skipped["not_matched"] += 1
            continue
        family_id = str(link.get("review_family_id") or "")
        if not family_id:
            skipped["missing_family"] += 1
            continue
        owner = str(link.get("review_target_layer") or "")
        if owner not in {"numbers", "sponsors"}:
            skipped["unsupported_owner"] += 1
            continue
        key = (str(link["paint_label"]), str(link["instance_id"]), family_id)
        if key in seen:
            continue
        seen.add(key)
        record = records.get(key[:2])
        if record is None or not record.get("mask_rle"):
            skipped["missing_mask"] += 1
            continue
        x, y, width, height = [int(value) for value in record["bbox"]]
        mask = decode_instance_mask_rle(record["mask_rle"])
        if mask.shape != (height, width):
            raise ValueError(f"instance mask/bbox mismatch for {key[:2]}")
        source_path = sources.get(key[0])
        if source_path is None:
            raise ValueError(f"source image missing for {key[0]}")
        image = np.asarray(Image.open(source_path).convert("RGB"))
        crop = image[y:y + height, x:x + width]
        if crop.shape[:2] != mask.shape:
            raise ValueError(f"source crop/bbox mismatch for {key[:2]}")
        stem = _safe_name(f"{key[0]}_{key[1]}_{family_id}")
        crop_path = output_dir / f"{stem}.png"
        mask_path = output_dir / f"{stem}.mask.png"
        Image.fromarray(crop).save(crop_path)
        Image.fromarray(mask.astype(np.uint8) * 255).save(mask_path)
        entries.append({
            "id": stem,
            "role": "reference",
            "family_id": family_id,
            "reviewed_owner": owner,
            "review_label": link.get("review_label"),
            "paint_label": key[0],
            "instance_id": key[1],
            "source_image": str(crop_path.resolve()),
            "mask_image": str(mask_path.resolve()),
            "bbox": [0, 0, width, height],
            "intrinsic_evidence": {
                "ocr_alpha_coverage": record.get("ocr_alpha_coverage", 0.0),
                "ocr_digit_coverage": record.get("ocr_digit_coverage", 0.0),
                "ocr_token_count": record.get("ocr_token_count", 0),
                "proposed_owners": list(record.get("proposed_owners") or ()),
                "proposal_conflict": bool(record.get("proposal_conflict")),
            },
        })
    manifest = {
        "schema": SCHEMA,
        "reference_count": len(entries),
        "family_counts": {
            family: sum(item["family_id"] == family for item in entries)
            for family in sorted({item["family_id"] for item in entries})
        },
        "review_link_counts": bank.get("review_link_counts", {}),
        "skipped_counts": skipped,
        "casts_votes": False,
        "ownership_authority": False,
        "entries": entries,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--labels-dir", required=True, type=Path)
    parser.add_argument("--label-prefix", default="")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    inspections = json.loads(args.inspection.read_text(encoding="utf-8"))
    labels = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.labels_dir.glob(f"{args.label_prefix}*.json"))
    ]
    manifest = export_reviewed_instance_crops(inspections, labels, args.output)
    print(json.dumps({key: manifest[key] for key in (
        "schema", "reference_count", "family_counts", "review_link_counts",
        "skipped_counts", "casts_votes", "ownership_authority"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
