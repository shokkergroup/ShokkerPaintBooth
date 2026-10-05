"""Apply durable human review decisions to generated relative-pixel labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle, encode_instance_mask_rle
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle, encode_instance_mask_rle  # type: ignore


def run(dataset_path: Path, review_path: Path, output_path: Path) -> dict:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    accepted = set(review["accept_ids"])
    crops = {item["proposal_id"]: item["local_keep_box"] for item in review["crop_records"]}
    promotions = {item["proposal_id"]: item["source_mask"] for item in review.get("promote_records", [])}
    records = []
    for record in dataset["records"]:
        proposal_id = record["proposal_id"]
        if proposal_id not in accepted and proposal_id not in crops and proposal_id not in promotions:
            continue
        if proposal_id in promotions:
            full_mask = np.asarray(Image.open(promotions[proposal_id]).convert("L")) > 0
            x, y, width, height = (int(value) for value in record["proposal_bbox"])
            mask = np.ascontiguousarray(full_mask[y:y + height, x:x + width])
            if int(np.count_nonzero(mask)) < 32:
                continue
            record = {
                **record,
                "label_kind": "number_core",
                "label_mask_rle": encode_instance_mask_rle(mask),
                "number_pixels": int(np.count_nonzero(mask)),
                "review_promotion_source": promotions[proposal_id],
            }
        if proposal_id in crops and record["label_kind"] == "number_core":
            mask = decode_instance_mask_rle(record["label_mask_rle"])
            x, y, width, height = (int(value) for value in crops[proposal_id])
            keep = np.zeros(mask.shape, bool)
            keep[y:y + height, x:x + width] = True
            mask = np.ascontiguousarray(mask & keep)
            if int(np.count_nonzero(mask)) < 32:
                continue
            record = {**record, "label_mask_rle": encode_instance_mask_rle(mask),
                      "number_pixels": int(np.count_nonzero(mask)),
                      "annotation_crop_only": crops[proposal_id]}
        records.append(record)
    result = {**dataset, "schema": "smart-tga-number-context-relative-pixel-reviewed-v1",
              "review_manifest": str(review_path).replace("\\", "/"), "records": records,
              "paint_count": len({(item["cycle"], item["paint_label"]) for item in records}),
              "train_paints": sorted({item["paint_label"] for item in records if item["role"] == "train"}),
              "holdout_paints": sorted({item["paint_label"] for item in records if item["role"] == "holdout"}),
              "number_core_records": sum(item["label_kind"] == "number_core" for item in records),
              "empty_control_records": sum(item["label_kind"] == "empty_control" for item in records)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.dataset, args.review, args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
