"""Export and measure mask hypotheses for corroborated number contexts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.decal_instances import (
        decode_instance_mask_rle, encode_instance_mask_rle,
    )
    from engine.spec_sculpt.number_context_masks import number_context_mask_hypotheses
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import (  # type: ignore
        decode_instance_mask_rle, encode_instance_mask_rle,
    )
    from engine.spec_sculpt.number_context_masks import number_context_mask_hypotheses  # type: ignore
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches  # type: ignore


METHODS = (
    "raw_instance_union", "seed_palette", "border_contrast",
    "hybrid_evidence", "seeded_graphcut",
)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tight_bbox(mask: np.ndarray, proposal_bbox: Sequence[int]) -> list[int] | None:
    rows, columns = np.nonzero(mask)
    if not len(columns):
        return None
    x, y, _width, _height = (int(value) for value in proposal_bbox)
    x0, x1 = int(columns.min()), int(columns.max()) + 1
    y0, y1 = int(rows.min()), int(rows.max()) + 1
    return [x + x0, y + y0, x1 - x0, y1 - y0]


def _negative_pixels(
    mask: np.ndarray, proposal_bbox: Sequence[int], negative_boxes: Sequence[Sequence[int]],
) -> int:
    x, y, width, height = (int(value) for value in proposal_bbox)
    total = 0
    for nx, ny, nw, nh in negative_boxes:
        x0, y0 = max(x, nx), max(y, ny)
        x1, y1 = min(x + width, nx + nw), min(y + height, ny + nh)
        if x1 > x0 and y1 > y0:
            total += int(np.count_nonzero(mask[y0 - y:y1 - y, x0 - x:x1 - x]))
    return total


def _overlay(crop: np.ndarray, mask: np.ndarray, size: tuple[int, int]) -> Image.Image:
    base = Image.fromarray(crop).convert("RGBA")
    color = np.zeros((*mask.shape, 4), np.uint8)
    color[mask] = (255, 20, 160, 180)
    base.alpha_composite(Image.fromarray(color, mode="RGBA"))
    base.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (22, 24, 30))
    canvas.paste(base.convert("RGB"), ((size[0] - base.width) // 2, (size[1] - base.height) // 2))
    return canvas


def run(inspection_path: Path, labels_dir: Path, cycle: int, output: Path) -> dict[str, Any]:
    inspections = _read(inspection_path)
    positives, negatives = _labels(labels_dir, cycle)
    paints = {str(item.get("paint_label") or "") for item in inspections}
    positives = [item for item in positives if str(item.get("paint_label") or "") in paints]
    negatives = [item for item in negatives if str(item.get("paint_label") or "") in paints]
    positives_by_paint = {
        paint: [item for item in positives if item["paint_label"] == paint] for paint in paints
    }
    negatives_by_paint = {
        paint: [item for item in negatives if item["paint_label"] == paint] for paint in paints
    }
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    sheets = []

    for inspection in inspections:
        paint = str(inspection.get("paint_label") or "")
        rgb = np.asarray(Image.open(inspection["source_1024"]).convert("RGB"))
        feature_records = (
            inspection["route_adjudicator_shadow"]["candidate_evidence"]
            ["decal_instances"]["features"]["records"]
        )
        instances = [
            {
                **item,
                "local_mask": decode_instance_mask_rle(item["mask_rle"]),
            }
            for item in feature_records
        ]
        by_id = {str(item["instance_id"]): item for item in instances}
        proposals = (
            inspection["route_adjudicator_shadow"]["candidate_evidence"]
            ["decal_instances"]["number_context_shadow"]["proposal_records"]
        )
        accepted = [
            item for item in proposals
            if item.get("position_status") == "corroborated_number_candidate"
        ]
        tiles: list[list[Image.Image]] = []
        for proposal in accepted:
            seed = by_id[str(proposal["seed_instance_id"])]
            hypotheses = number_context_mask_hypotheses(rgb, proposal, seed, instances)
            x, y, width, height = (int(value) for value in proposal["bbox"])
            crop = rgb[y:y + height, x:x + width]
            row = [_overlay(crop, np.zeros((height, width), bool), (180, 120))]
            mask_payload = {}
            tight_payload = {}
            for method in METHODS:
                mask = hypotheses["masks"][method]
                row.append(_overlay(crop, mask, (180, 120)))
                mask_payload[method] = encode_instance_mask_rle(mask)
                tight_payload[method] = _tight_bbox(mask, proposal["bbox"])
            tiles.append(row)
            records.append({
                "paint_label": paint,
                "proposal_id": proposal["proposal_id"],
                "proposal_bbox": list(proposal["bbox"]),
                "number_score": proposal.get("number_score"),
                "position_score": proposal.get("position_score"),
                "seed_instance_id": proposal["seed_instance_id"],
                "raw_member_instance_ids": hypotheses["raw_member_instance_ids"],
                "minimum_component_area": hypotheses["minimum_component_area"],
                "tight_bboxes": tight_payload,
                "mask_rle": mask_payload,
            })
        if tiles:
            headers = ("source", *METHODS)
            sheet = Image.new("RGB", (180 * len(headers), 26 + 142 * len(tiles)), (16, 18, 24))
            draw = ImageDraw.Draw(sheet)
            for index, header in enumerate(headers):
                draw.text((index * 180 + 6, 6), header, fill=(238, 238, 242))
            for row_index, row in enumerate(tiles):
                for column_index, tile in enumerate(row):
                    sheet.paste(tile, (column_index * 180, 26 + row_index * 142))
                draw.text((6, 26 + row_index * 142 + 121), accepted[row_index]["proposal_id"], fill=(220, 220, 225))
            sheet_path = output / f"review_{paint.replace('/', '_').replace('.tga', '').replace(' ', '_')}.png"
            sheet.save(sheet_path)
            sheets.append(str(sheet_path).replace("\\", "/"))

    metrics = {}
    for method in METHODS:
        by_paint: dict[str, list[Mapping[str, Any]]] = {paint: [] for paint in paints}
        pixel_count = 0
        negative_pixel_count = 0
        empty_count = 0
        for record in records:
            mask = decode_instance_mask_rle(record["mask_rle"][method])
            pixel_count += int(np.count_nonzero(mask))
            negative_pixel_count += _negative_pixels(
                mask, record["proposal_bbox"],
                [item["bbox"] for item in negatives_by_paint[record["paint_label"]]],
            )
            tight = record["tight_bboxes"][method]
            if tight is None:
                empty_count += 1
            else:
                by_paint[record["paint_label"]].append({"bbox": tight})
        positive_hits = sum(
            any(_matches(item["bbox"], positive["bbox"]) for item in by_paint[positive["paint_label"]])
            for positive in positives
        )
        negative_hits = sum(
            any(_matches(item["bbox"], negative["bbox"]) for item in by_paint[negative["paint_label"]])
            for negative in negatives
        )
        metrics[method] = {
            "positive_bbox_hits": positive_hits,
            "positive_bbox_total": len(positives),
            "hard_negative_bbox_hits": negative_hits,
            "hard_negative_bbox_total": len(negatives),
            "mask_pixels": pixel_count,
            "hard_negative_mask_pixels": negative_pixel_count,
            "empty_masks": empty_count,
        }

    payload = {
        "schema": "smart-tga-number-context-mask-probe-v1",
        "cycle": cycle,
        "inspection": str(inspection_path).replace("\\", "/"),
        "proposal_count": len(records),
        "methods": list(METHODS),
        "metrics": metrics,
        "sheets": sheets,
        "records": records,
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }
    (output / "mask_probe.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inspection, args.labels_dir, args.cycle, args.output)
    summary = {key: value for key, value in result.items() if key != "records"}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
