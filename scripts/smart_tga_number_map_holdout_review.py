"""Render per-paint visual review sheets for frozen map-family holdout scores."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_object_segmentation import (
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )
    from scripts.smart_tga_number_map_active_review import _tile
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_object_segmentation import (  # type: ignore
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )
    from scripts.smart_tga_number_map_active_review import _tile  # type: ignore


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build(inspection_path: Path, scores_path: Path, segment_model_path: Path, output_dir: Path):
    import torch

    inspection = {item["paint_label"]: item for item in _read(inspection_path)}
    score_document = _read(scores_path)
    scores = list(score_document["scores"])
    blob = torch.load(segment_model_path, map_location="cpu", weights_only=True)
    segment = build_tiny_unet(int(blob["base_channels"]))
    segment.load_state_dict(blob["state_dict"])
    segment.eval()
    output_dir.mkdir(parents=True, exist_ok=True)
    reviewed = []
    sheets = {}
    for paint_label in sorted({item["paint_label"] for item in scores}):
        records = [item for item in scores if item["paint_label"] == paint_label]
        records.sort(key=lambda item: (not item["accepted"], -float(item["probability"])))
        wanted = {proposal_id for item in records for proposal_id in item["member_ids"]}
        rgb = np.asarray(Image.open(inspection[paint_label]["source_1024"]).convert("RGB"))
        with torch.no_grad():
            probability = torch.sigmoid(
                segment(torch.from_numpy(image_feature_tensor(rgb)[None]))
            )[0, 0].numpy()
        proposals = [
            item for item in probability_region_proposals(probability, rgb.shape[:2])
            if item["proposal_id"] in wanted
        ]
        proposal_by_id = {item["proposal_id"]: item for item in proposals}
        if set(proposal_by_id) != wanted:
            raise AssertionError(f"proposal regeneration drift for {paint_label}")
        visuals = []
        for record in records:
            outer_id = max(
                record["member_ids"],
                key=lambda item: np.prod(proposal_by_id[item]["proposal_bbox"][2:]),
            )
            outer = proposal_by_id[outer_id]
            context, isolated = _tile(rgb, outer["raw_support"], outer["proposal_bbox"])
            entry = dict(record)
            entry.update({
                "outer_proposal_id": outer_id, "review_class": None,
                "review_label": None,
            })
            reviewed.append(entry)
            visuals.append((entry, context, isolated))
        tile, caption, columns = 230, 90, 3
        rows = max(1, math.ceil(len(visuals) / columns))
        canvas = Image.new("RGB", (columns * tile * 2, rows * (tile + caption)), (14, 15, 20))
        draw = ImageDraw.Draw(canvas)
        for index, (record, context, isolated) in enumerate(visuals):
            column, row = index % columns, index // columns
            x, y = column * tile * 2, row * (tile + caption)
            canvas.paste(context, (x + (tile - context.width) // 2, y + (tile - context.height) // 2))
            canvas.paste(isolated, (x + tile + (tile - isolated.width) // 2, y + (tile - isolated.height) // 2))
            draw.rectangle((x, y + tile, x + tile * 2 - 1, y + tile + caption - 1), fill=(7, 8, 12))
            decision = "ACCEPT" if record["accepted"] else "reject"
            color = (88, 238, 151) if record["accepted"] else (210, 214, 224)
            draw.text((x + 6, y + tile + 5), f"{index:02d} {decision}  p={record['probability']:.3f}", fill=color)
            draw.text((x + 6, y + tile + 24), f"digit={record['clip_digit_evidence']:.3f} panel={record['template_number_evidence']:.3f} owner={record['legacy_number_overlap']:.3f}", fill=(168, 205, 255))
            draw.text((x + 6, y + tile + 43), f"box {','.join(map(str, record['family_bbox']))} members={len(record['member_ids'])}", fill=(190, 194, 204))
            draw.text((x + 6, y + tile + 62), record["family_id"], fill=(150, 155, 168))
        destination = output_dir / f"{paint_label.replace('/', '_').replace(' ', '_').replace('.tga', '')}.png"
        canvas.save(destination)
        sheets[paint_label] = str(destination).replace("\\", "/")
    payload = {
        "schema": "smart-tga-number-map-frozen-holdout-review-v1",
        "scores": str(scores_path).replace("\\", "/"),
        "family_count": len(reviewed), "paint_count": len(sheets),
        "sheets": sheets, "families": reviewed,
        "selection": "all frozen accepted and rejected families; no sampling",
        "casts_votes": False, "ownership_authority": False,
    }
    (output_dir / "family_review.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--segment-model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.inspection, args.scores, args.segment_model, args.output_dir)
    print(json.dumps({
        "family_count": payload["family_count"], "paint_count": payload["paint_count"],
        "sheets": payload["sheets"],
    }, indent=2))


if __name__ == "__main__":
    main()
