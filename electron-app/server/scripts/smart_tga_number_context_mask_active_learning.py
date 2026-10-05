"""Select exact context-mask reviews from model disagreement, never filenames.

The queue is intentionally built from already-reviewed paints.  It asks for
pixel masks only where the current immutable hypotheses disagree or expose a
reviewed hard-negative region, so another broad corpus pass is unnecessary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle  # type: ignore
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches  # type: ignore


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _intersection(left: Sequence[int], right: Sequence[int]) -> tuple[int, int, int, int] | None:
    lx, ly, lw, lh = (int(value) for value in left)
    rx, ry, rw, rh = (int(value) for value in right)
    x0, y0 = max(lx, rx), max(ly, ry)
    x1, y1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _negative_exposure(
    mask: np.ndarray, proposal_bbox: Sequence[int], negatives: Sequence[Mapping[str, Any]],
) -> int:
    px, py, _pw, _ph = (int(value) for value in proposal_bbox)
    exposed = 0
    for item in negatives:
        overlap = _intersection(proposal_bbox, item["bbox"])
        if overlap is None:
            continue
        x0, y0, x1, y1 = overlap
        exposed += int(np.count_nonzero(mask[y0 - py:y1 - py, x0 - px:x1 - px]))
    return exposed


def _analyse(probe_path: Path, labels_dir: Path) -> list[dict[str, Any]]:
    probe = _read(probe_path)
    cycle = int(probe["cycle"])
    positives, negatives = _labels(labels_dir, cycle)
    inspections = _read(Path(str(probe["inspection"])))
    source_by_paint = {
        str(item.get("paint_label") or ""): str(item.get("source_1024") or "")
        for item in inspections
    }
    rows = []
    for record in probe["records"]:
        paint = str(record["paint_label"])
        masks = {
            name: decode_instance_mask_rle(rle)
            for name, rle in record["mask_rle"].items()
        }
        stack = np.stack(list(masks.values()), axis=0)
        votes = np.count_nonzero(stack, axis=0)
        union_pixels = int(np.count_nonzero(votes))
        disagreement_pixels = int(np.count_nonzero((votes > 0) & (votes < len(masks))))
        pairwise_ious = []
        values = list(masks.values())
        for index, left in enumerate(values):
            for right in values[index + 1:]:
                union = int(np.count_nonzero(left | right))
                pairwise_ious.append(
                    int(np.count_nonzero(left & right)) / union if union else 1.0
                )
        paint_positives = [item for item in positives if item["paint_label"] == paint]
        paint_negatives = [item for item in negatives if item["paint_label"] == paint]
        target_matches = sum(
            _matches(record["proposal_bbox"], item["bbox"]) for item in paint_positives
        )
        exposures = {
            name: _negative_exposure(mask, record["proposal_bbox"], paint_negatives)
            for name, mask in masks.items()
        }
        disagreement = disagreement_pixels / max(1, union_pixels)
        mean_iou = float(np.mean(pairwise_ious)) if pairwise_ious else 1.0
        negative_exposure = max(exposures.values(), default=0)
        rows.append({
            "cycle": cycle,
            "paint_label": paint,
            "source_1024": source_by_paint.get(paint, ""),
            "proposal_id": record["proposal_id"],
            "proposal_bbox": record["proposal_bbox"],
            "number_score": record["number_score"],
            "position_score": record["position_score"],
            "target_bbox_matches": int(target_matches),
            "maximum_hard_negative_mask_pixels": negative_exposure,
            "hard_negative_pixels_by_method": exposures,
            "hypothesis_disagreement_fraction": round(disagreement, 6),
            "mean_pairwise_iou": round(mean_iou, 6),
            "uncertainty_score": round(
                disagreement + (1.0 - mean_iou) + min(1.0, negative_exposure / 5000.0), 6
            ),
            "mask_rle": record["mask_rle"],
        })
    return rows


def _select(rows: Sequence[dict[str, Any]], target_count: int, control_count: int) -> list[dict[str, Any]]:
    targets = sorted(
        (item for item in rows if item["target_bbox_matches"] > 0),
        key=lambda item: (-item["uncertainty_score"], item["proposal_id"]),
    )
    controls = sorted(
        (item for item in rows if item["target_bbox_matches"] == 0),
        key=lambda item: (
            -int(item["maximum_hard_negative_mask_pixels"] > 0),
            -item["uncertainty_score"], item["proposal_id"],
        ),
    )

    def stratified(pool: Sequence[dict[str, Any]], count: int) -> list[dict[str, Any]]:
        chosen, seen = [], set()
        for item in pool:
            if item["paint_label"] in seen:
                continue
            chosen.append(item)
            seen.add(item["paint_label"])
            if len(chosen) == count:
                return chosen
        for item in pool:
            if item not in chosen:
                chosen.append(item)
            if len(chosen) == count:
                break
        return chosen

    selected = stratified(targets, target_count) + stratified(controls, control_count)
    return sorted(selected, key=lambda item: (item["cycle"], item["paint_label"], item["proposal_id"]))


def _overlay(source: Image.Image, mask: np.ndarray) -> Image.Image:
    rgb = np.asarray(source.convert("RGB")).copy()
    tint = np.zeros_like(rgb)
    tint[..., 0], tint[..., 1], tint[..., 2] = 255, 35, 180
    rgb[mask] = (0.42 * rgb[mask] + 0.58 * tint[mask]).astype(np.uint8)
    return Image.fromarray(rgb)


def _render(item: Mapping[str, Any], output: Path) -> None:
    source = Image.open(str(item["source_1024"])).convert("RGB")
    x, y, width, height = (int(value) for value in item["proposal_bbox"])
    crop = source.crop((x, y, x + width, y + height))
    methods = list(item["mask_rle"])
    panels = [("SOURCE — draw exact Number pixels", crop)] + [
        (name.replace("_", " ").upper(), _overlay(crop, decode_instance_mask_rle(item["mask_rle"][name])))
        for name in methods
    ]
    panel_width, panel_height = 320, 210
    canvas = Image.new("RGB", (panel_width * 3, panel_height * 2 + 58), (18, 20, 25))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 8), f'{item["paint_label"]}  {item["proposal_id"]}', fill=(245, 245, 245))
    draw.text(
        (12, 28),
        f'target={item["target_bbox_matches"]}  negative-pixels={item["maximum_hard_negative_mask_pixels"]}  uncertainty={item["uncertainty_score"]}',
        fill=(185, 205, 235),
    )
    for index, (label, panel) in enumerate(panels):
        column, row = index % 3, index // 3
        panel.thumbnail((panel_width - 12, panel_height - 32), Image.Resampling.LANCZOS)
        left = column * panel_width + (panel_width - panel.width) // 2
        top = 58 + row * panel_height + 24
        canvas.paste(panel, (left, top))
        draw.text((column * panel_width + 8, 58 + row * panel_height + 5), label, fill=(245, 220, 100))
    canvas.save(output)


def run(
    probes: Sequence[Path], labels_dir: Path, output_dir: Path,
    target_count: int = 10, control_count: int = 6,
) -> dict[str, Any]:
    rows = [item for path in probes for item in _analyse(path, labels_dir)]
    selected = _select(rows, target_count, control_count)
    output_dir.mkdir(parents=True, exist_ok=True)
    queue = []
    for index, item in enumerate(selected, 1):
        sheet = output_dir / f'{index:02d}_cycle{item["cycle"]}_{item["proposal_id"].split(":")[-1]}.png'
        _render(item, sheet)
        queue.append({key: value for key, value in item.items() if key != "mask_rle"} | {
            "review_sheet": str(sheet).replace("\\", "/"),
            "requested_label": "exact Number pixel mask; empty mask means non-Number control",
        })
    result = {
        "schema": "smart-tga-number-context-mask-active-learning-v1",
        "selection_basis": "hypothesis disagreement plus reviewed hard-negative pixel exposure",
        "candidate_proposal_count": len(rows),
        "selected_proposal_count": len(queue),
        "selected_target_count": sum(item["target_bbox_matches"] > 0 for item in queue),
        "selected_control_count": sum(item["target_bbox_matches"] == 0 for item in queue),
        "queue": queue,
    }
    (output_dir / "active_learning_queue.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("probes", nargs="+", type=Path)
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--targets", type=int, default=10)
    parser.add_argument("--controls", type=int, default=6)
    args = parser.parse_args()
    print(json.dumps(run(args.probes, args.labels_dir, args.output_dir, args.targets, args.controls), indent=2))


if __name__ == "__main__":
    main()
