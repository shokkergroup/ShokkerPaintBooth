"""Evaluate scored owner-neutral number-map proposals against durable reviews."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families  # type: ignore


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _intersection(first, second):
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by),
    )


def _coverage(proposal, target):
    box = target["bbox"]
    return _intersection(proposal["bbox"], box) / max(1, int(box[2]) * int(box[3]))


def run(active_pool: Path, label_root: Path, cycle: int, output: Path):
    pool = _read(active_pool)
    reviewed = []
    for path in sorted(label_root.glob(f"cycle{cycle}_*_numbers_v1.json")):
        payload = _read(path)
        for item in payload.get("component_labels", []):
            reviewed.append({
                "paint_label": payload["paint_label"], "bbox": item["expected_bbox"],
                "review_label": item["label"],
                "is_number": str(item["target_layer"]).lower() == "numbers",
            })
    missed_path = label_root / f"cycle{cycle}_missed_number_instances_v1.json"
    missed = _read(missed_path).get("instances", []) if missed_path.exists() else []
    missed = [{**item, "is_number": True} for item in missed]
    targets = reviewed + missed
    accepted = [
        item for paint in pool["ranking"] for item in paint["objects"]
        if item.get("source_layer") == "owner_neutral_map"
        and float(item["foundation_probability"]) >= float(pool["frozen_threshold"])
    ]
    classifications = []
    for proposal in accepted:
        candidates = [
            (target, _coverage(proposal, target)) for target in targets
            if target["paint_label"] == proposal["paint_label"]
        ]
        positive = max((pair for pair in candidates if pair[0]["is_number"]), key=lambda pair: pair[1], default=(None, 0.0))
        negative = max((pair for pair in candidates if not pair[0]["is_number"]), key=lambda pair: pair[1], default=(None, 0.0))
        if positive[1] >= 0.25 and positive[1] >= negative[1]:
            classification = "reviewed_number_support"
        elif negative[1] >= 0.25:
            classification = "reviewed_hard_negative"
        else:
            classification = "unreviewed_or_partial"
        classifications.append({
            "paint_label": proposal["paint_label"], "proposal_id": proposal["proposal_id"],
            "bbox": proposal["bbox"], "probability": proposal["foundation_probability"],
            "classification": classification,
            "best_positive_coverage": round(float(positive[1]), 6),
            "best_negative_coverage": round(float(negative[1]), 6),
            "best_positive_label": None if positive[0] is None else positive[0].get("review_label", positive[0].get("copy")),
            "best_negative_label": None if negative[0] is None else negative[0].get("review_label"),
        })

    classification_by_id = {item["proposal_id"]: item["classification"] for item in classifications}
    families = []
    for paint_label in sorted({item["paint_label"] for item in accepted}):
        paint_proposals = [
            {"proposal_id": item["proposal_id"], "proposal_bbox": item["bbox"],
             "provenance": item.get("proposal_provenance", {})}
            for item in accepted if item["paint_label"] == paint_label
        ]
        for family in assemble_nested_proposal_families(paint_proposals):
            member_classes = {classification_by_id[item] for item in family["member_ids"]}
            if "reviewed_hard_negative" in member_classes:
                family_class = "reviewed_hard_negative"
            elif "reviewed_number_support" in member_classes:
                family_class = "reviewed_number_support"
            else:
                family_class = "unreviewed_or_partial"
            families.append({"paint_label": paint_label, **family, "classification": family_class})

    def target_results(items):
        result = []
        for target in items:
            candidates = [
                (proposal, _coverage(proposal, target)) for proposal in accepted
                if proposal["paint_label"] == target["paint_label"]
            ]
            best = max(candidates, key=lambda pair: pair[1], default=(None, 0.0))
            result.append({
                **target, "accepted_recovered_at_25pct": best[1] >= 0.25,
                "best_accepted_coverage": round(float(best[1]), 6),
                "best_proposal_id": None if best[0] is None else best[0]["proposal_id"],
            })
        return result

    positive_results = target_results([item for item in reviewed if item["is_number"]])
    missed_results = target_results(missed)
    payload = {
        "schema": "smart-tga-number-map-scored-eval-v1", "cycle": cycle,
        "validation": "frozen scorer and threshold; paint-disjoint durable reviews",
        "accepted_map_proposals": len(accepted),
        "accepted_reviewed_number_support": sum(item["classification"] == "reviewed_number_support" for item in classifications),
        "accepted_reviewed_hard_negatives": sum(item["classification"] == "reviewed_hard_negative" for item in classifications),
        "accepted_unreviewed_or_partial": sum(item["classification"] == "unreviewed_or_partial" for item in classifications),
        "accepted_map_families": len(families),
        "reviewed_number_families": sum(item["classification"] == "reviewed_number_support" for item in families),
        "reviewed_hard_negative_families": sum(item["classification"] == "reviewed_hard_negative" for item in families),
        "unreviewed_or_partial_families": sum(item["classification"] == "unreviewed_or_partial" for item in families),
        "reviewed_positive_recovery_at_25pct": f"{sum(item['accepted_recovered_at_25pct'] for item in positive_results)}/{len(positive_results)}",
        "missing_instance_recovery_at_25pct": f"{sum(item['accepted_recovered_at_25pct'] for item in missed_results)}/{len(missed_results)}",
        "classifications": classifications, "families": families,
        "reviewed_positive_results": positive_results,
        "missing_instance_results": missed_results, "casts_votes": False,
        "ownership_authority": False, "exact_reconstruction_impact": "none",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    inspection = {item["paint_label"]: item for item in _read(Path(pool["inspection"]))}
    card_width, card_height, columns = 320, 220, 3
    sheet = Image.new(
        "RGB", (card_width * columns, card_height * max(1, math.ceil(len(classifications) / columns))),
        (18, 20, 26),
    )
    draw = ImageDraw.Draw(sheet)
    colors = {
        "reviewed_number_support": (60, 225, 120),
        "reviewed_hard_negative": (255, 75, 75),
        "unreviewed_or_partial": (255, 190, 55),
    }
    images = {}
    for position, item in enumerate(classifications):
        paint_label = item["paint_label"]
        if paint_label not in images:
            images[paint_label] = Image.open(inspection[paint_label]["source_1024"]).convert("RGB")
        source = images[paint_label]
        x, y, width, height = map(int, item["bbox"])
        margin = 8
        crop = source.crop((max(0, x - margin), max(0, y - margin), min(source.width, x + width + margin), min(source.height, y + height + margin)))
        crop.thumbnail((card_width - 20, 150), Image.Resampling.LANCZOS)
        column, row = position % columns, position // columns
        left, top = column * card_width, row * card_height
        color = colors[item["classification"]]
        draw.rectangle((left + 4, top + 4, left + card_width - 5, top + card_height - 5), outline=color, width=3)
        sheet.paste(crop, (left + (card_width - crop.width) // 2, top + 10))
        draw.text((left + 10, top + 164), f"{Path(paint_label).stem}  p={item['probability']:.3f}", fill=color)
        draw.text((left + 10, top + 180), item["classification"], fill=(225, 228, 235))
        draw.text((left + 10, top + 196), f"positive {item['best_positive_coverage']:.2f} / negative {item['best_negative_coverage']:.2f}", fill=(170, 178, 192))
    sheet.save(output.parent / "accepted_map_review_sheet.png")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-pool", type=Path, required=True)
    parser.add_argument("--label-root", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.active_pool, args.label_root, args.cycle, args.output)
    print(json.dumps({key: value for key, value in payload.items() if not isinstance(value, list)}, indent=2))


if __name__ == "__main__":
    main()
