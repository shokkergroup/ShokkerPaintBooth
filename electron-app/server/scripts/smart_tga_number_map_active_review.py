"""Build family-level visual review evidence for owner-neutral number-map proposals."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families
    from engine.spec_sculpt.number_object_segmentation import (
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families  # type: ignore
    from engine.spec_sculpt.number_object_segmentation import (  # type: ignore
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _tile(rgb, support, bbox, size=230):
    x, y, width, height = map(int, bbox)
    margin = max(12, int(round(max(width, height) * 0.25)))
    x0, y0 = max(0, x - margin), max(0, y - margin)
    x1, y1 = min(rgb.shape[1], x + width + margin), min(rgb.shape[0], y + height + margin)
    context = Image.fromarray(rgb[y0:y1, x0:x1]).convert("RGB")
    context.thumbnail((size, size), Image.Resampling.LANCZOS)
    isolated = np.full_like(rgb[y0:y1, x0:x1], 127)
    crop_support = np.zeros((y1 - y0, x1 - x0), bool)
    local = np.asarray(support, bool)
    target = crop_support[y - y0:y - y0 + local.shape[0], x - x0:x - x0 + local.shape[1]]
    target[:] = local[:target.shape[0], :target.shape[1]]
    isolated[crop_support] = rgb[y0:y1, x0:x1][crop_support]
    isolated_image = Image.fromarray(isolated).convert("RGB")
    isolated_image.thumbnail((size, size), Image.Resampling.LANCZOS)
    return context, isolated_image


def build(inspection_path, active_pool_path, segment_model_path, output, rejected_per_paint=2):
    import torch

    pool = _read(active_pool_path)
    threshold = float(pool["frozen_threshold"])
    inspection = {item["paint_label"]: item for item in _read(inspection_path)}
    blob = torch.load(segment_model_path, map_location="cpu", weights_only=True)
    segment = build_tiny_unet(int(blob["base_channels"]))
    segment.load_state_dict(blob["state_dict"])
    segment.eval()
    families = []
    visuals = []
    for paint in pool["ranking"]:
        paint_label = paint["paint_label"]
        maps = [item for item in paint["objects"] if item.get("source_layer") == "owner_neutral_map"]
        accepted = [item for item in maps if float(item["foundation_probability"]) >= threshold]
        rejected = sorted(
            (item for item in maps if float(item["foundation_probability"]) < threshold),
            key=lambda item: item["uncertainty"],
        )[:int(rejected_per_paint)]
        chosen = accepted + rejected
        chosen_by_id = {item["proposal_id"]: item for item in chosen}
        rgb = np.asarray(Image.open(inspection[paint_label]["source_1024"]).convert("RGB"))
        with torch.no_grad():
            probability = torch.sigmoid(
                segment(torch.from_numpy(image_feature_tensor(rgb)[None]))
            )[0, 0].numpy()
        proposals = [
            item for item in probability_region_proposals(probability, rgb.shape[:2])
            if item["proposal_id"] in chosen_by_id
        ]
        if {item["proposal_id"] for item in proposals} != set(chosen_by_id):
            raise AssertionError(f"proposal regeneration drift for {paint_label}")
        proposal_by_id = {item["proposal_id"]: item for item in proposals}
        for family in assemble_nested_proposal_families(proposals):
            members = [chosen_by_id[item] for item in family["member_ids"]]
            outer_id = max(
                family["member_ids"],
                key=lambda item: np.prod(proposal_by_id[item]["proposal_bbox"][2:]),
            )
            outer = proposal_by_id[outer_id]
            context, isolated = _tile(rgb, outer["raw_support"], outer["proposal_bbox"])
            probabilities = [float(item["foundation_probability"]) for item in members]
            record = {
                "paint_label": paint_label, "family_id": family["family_id"],
                "family_bbox": family["family_bbox"], "outer_proposal_id": outer_id,
                "member_ids": list(family["member_ids"]),
                "member_count": len(members),
                "accepted_member_count": sum(value >= threshold for value in probabilities),
                "probability_min": round(min(probabilities), 6),
                "probability_max": round(max(probabilities), 6),
                "review_class": None, "review_label": None,
            }
            families.append(record)
            visuals.append((record, context, isolated))

    tile, caption, columns = 230, 72, 3
    rows = max(1, math.ceil(len(visuals) / columns))
    canvas = Image.new("RGB", (columns * tile * 2, rows * (tile + caption)), (14, 15, 20))
    draw = ImageDraw.Draw(canvas)
    for index, (record, context, isolated) in enumerate(visuals):
        column, row = index % columns, index // columns
        x, y = column * tile * 2, row * (tile + caption)
        canvas.paste(context, (x + (tile - context.width) // 2, y + (tile - context.height) // 2))
        canvas.paste(isolated, (x + tile + (tile - isolated.width) // 2, y + (tile - isolated.height) // 2))
        draw.rectangle((x, y + tile, x + tile * 2 - 1, y + tile + caption - 1), fill=(7, 8, 12))
        paint = Path(record["paint_label"]).stem.replace("car_num_", "")
        draw.text((x + 6, y + tile + 5), f"{index:02d}  {paint}  members {record['member_count']} accepted {record['accepted_member_count']}", fill=(240, 242, 246))
        draw.text((x + 6, y + tile + 24), f"p {record['probability_min']:.3f}-{record['probability_max']:.3f}  box {','.join(map(str, record['family_bbox']))}", fill=(168, 205, 255))
        draw.text((x + 6, y + tile + 43), record["family_id"], fill=(170, 175, 188))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    payload = {
        "schema": "smart-tga-number-map-active-review-v1",
        "active_pool": str(active_pool_path).replace("\\", "/"),
        "family_count": len(families), "frozen_threshold": threshold,
        "selection": f"all accepted plus {rejected_per_paint} nearest rejected per paint",
        "families": families, "casts_votes": False, "ownership_authority": False,
    }
    output.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--active-pool", type=Path, required=True)
    parser.add_argument("--segment-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rejected-per-paint", type=int, default=2)
    args = parser.parse_args()
    payload = build(
        args.inspection, args.active_pool, args.segment_model, args.output,
        args.rejected_per_paint,
    )
    print(json.dumps({"family_count": payload["family_count"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
