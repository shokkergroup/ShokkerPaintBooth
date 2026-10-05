"""Probe owner-neutral proposals made directly from a frozen number probability map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_object_segmentation import (
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_object_segmentation import (  # type: ignore
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _intersection(first, second):
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    width = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    height = max(0, min(ay + ah, by + bh) - max(ay, by))
    return width * height


def _overlay(rgb, proposals, destination):
    image = Image.fromarray(rgb).convert("RGB")
    draw = ImageDraw.Draw(image)
    colors = {0.90: (40, 220, 255), 0.95: (255, 200, 40), 0.98: (255, 70, 180)}
    for item in proposals:
        x, y, width, height = item["proposal_bbox"]
        quantile = item["provenance"]["relative_quantile"]
        draw.rectangle((x, y, x + width, y + height), outline=colors.get(quantile, (220, 220, 220)), width=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def run(inspection: Path, label_root: Path, cycle: int, model_path: Path, output_dir: Path):
    import torch

    labels = [
        _read(path) for path in sorted(label_root.glob(f"cycle{cycle}_*_numbers_v1.json"))
    ]
    paint_labels = {item["paint_label"] for item in labels}
    inspection_index = {item["paint_label"]: item for item in _read(inspection)}
    missed_path = label_root / f"cycle{cycle}_missed_number_instances_v1.json"
    missed = _read(missed_path).get("instances", []) if missed_path.exists() else []

    blob = torch.load(model_path, map_location="cpu", weights_only=True)
    model = build_tiny_unet(int(blob["base_channels"]))
    model.load_state_dict(blob["state_dict"])
    model.eval()
    paints = []
    proposal_map = {}
    with torch.no_grad():
        for paint_label in sorted(paint_labels):
            source = Path(inspection_index[paint_label]["source_1024"])
            rgb = np.asarray(Image.open(source).convert("RGB"))
            probability = torch.sigmoid(model(torch.from_numpy(image_feature_tensor(rgb)[None])))[0, 0].numpy()
            proposals = probability_region_proposals(probability, rgb.shape[:2])
            proposal_map[paint_label] = proposals
            slug = paint_label.replace("/", "_").replace(" ", "_").replace(".tga", "")
            _overlay(rgb, proposals, output_dir / f"overlay_{slug}.png")
            paints.append({
                "paint_label": paint_label, "proposal_count": len(proposals),
                "probability_quantiles": {
                    str(value): round(float(np.quantile(probability, value)), 6)
                    for value in (0.5, 0.9, 0.95, 0.98, 0.99)
                },
            })

    def score_targets(targets):
        results = []
        for target in targets:
            target_box = target["bbox"]
            target_area = max(1, int(target_box[2]) * int(target_box[3]))
            candidates = []
            for proposal in proposal_map[target["paint_label"]]:
                overlap = _intersection(target_box, proposal["proposal_bbox"])
                if overlap:
                    candidates.append({
                        "proposal_id": proposal["proposal_id"], "bbox": proposal["proposal_bbox"],
                        "relative_quantile": proposal["provenance"]["relative_quantile"],
                        "target_coverage": overlap / target_area,
                    })
            best = max(candidates, key=lambda item: item["target_coverage"], default=None)
            results.append({**target, "best_proposal": best})
        return results

    target_results = score_targets(missed)
    reviewed_targets = []
    for review in labels:
        for component in review.get("component_labels", []):
            if str(component.get("target_layer", "")).lower() == "numbers":
                reviewed_targets.append({
                    "paint_label": review["paint_label"], "copy": component["label"],
                    "bbox": component["expected_bbox"], "source_layer": component["layer"],
                    "component_index": component["component_index"],
                })
    reviewed_results = score_targets(reviewed_targets)

    payload = {
        "schema": "smart-tga-number-probability-proposal-probe-v1",
        "model": str(model_path).replace("\\", "/"), "cycle": cycle,
        "paint_count": len(paints), "proposal_count": sum(item["proposal_count"] for item in paints),
        "missing_target_recall_at_25pct_coverage": f"{sum(item['best_proposal'] is not None and item['best_proposal']['target_coverage'] >= 0.25 for item in target_results)}/{len(target_results)}",
        "reviewed_positive_recall_at_25pct_coverage": f"{sum(item['best_proposal'] is not None and item['best_proposal']['target_coverage'] >= 0.25 for item in reviewed_results)}/{len(reviewed_results)}",
        "target_results": target_results, "reviewed_positive_results": reviewed_results, "paint_controls": paints,
        "proposal_quantiles": [0.90, 0.95, 0.98], "casts_votes": False,
        "ownership_authority": False, "exact_reconstruction_impact": "none",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "proposal_probe.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--label-root", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inspection, args.label_root, args.cycle, args.model, args.output_dir)
    print(json.dumps({key: value for key, value in result.items() if key not in {"target_results", "reviewed_positive_results", "paint_controls"}}, indent=2))


if __name__ == "__main__":
    main()
