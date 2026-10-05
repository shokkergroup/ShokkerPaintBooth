"""Build paint-diverse conservative Number-core supervision from durable reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.decal_instances import encode_instance_mask_rle
    from engine.spec_sculpt.number_context_masks import number_context_mask_hypotheses
    from engine.spec_sculpt.number_family_shadow import PortableExtraTrees
    from scripts.smart_tga_number_context_member_probe import _historical_contexts
    from scripts.smart_tga_number_context_pixel_label_bootstrap import (
        _prune_annotation_components, _render,
    )
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import encode_instance_mask_rle  # type: ignore
    from engine.spec_sculpt.number_context_masks import number_context_mask_hypotheses  # type: ignore
    from engine.spec_sculpt.number_family_shadow import PortableExtraTrees  # type: ignore
    from scripts.smart_tga_number_context_member_probe import _historical_contexts  # type: ignore
    from scripts.smart_tga_number_context_pixel_label_bootstrap import (  # type: ignore
        _prune_annotation_components, _render,
    )
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches  # type: ignore


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _proposal_id(proposal: Mapping[str, Any]) -> str:
    existing = str(proposal.get("proposal_id") or "")
    if existing:
        return existing
    payload = json.dumps({
        "bbox": proposal.get("bbox"), "seed": proposal.get("seed_instance_id"),
        "members": proposal.get("member_instance_ids"),
    }, sort_keys=True).encode("utf-8")
    return "ncp:" + hashlib.sha256(payload).hexdigest()[:16]


def _raw_mask(context: Mapping[str, Any]) -> np.ndarray:
    x, y, width, height = (int(value) for value in context["proposal"]["bbox"])
    result = np.zeros((height, width), bool)
    for member in context["members"]:
        mx, my, mw, mh = (int(value) for value in member["bbox"])
        x0, y0, x1, y1 = max(x, mx), max(y, my), min(x + width, mx + mw), min(y + height, my + mh)
        if x1 <= x0 or y1 <= y0:
            continue
        result[y0 - y:y1 - y, x0 - x:x1 - x] |= np.asarray(member["local_mask"], bool)[
            y0 - my:y1 - my, x0 - mx:x1 - mx
        ]
    return result


def _positive_roi(bbox: Sequence[int], labels: Sequence[Mapping[str, Any]]) -> np.ndarray:
    x, y, width, height = (int(value) for value in bbox)
    roi = np.zeros((height, width), bool)
    for item in labels:
        lx, ly, lw, lh = (int(value) for value in item["bbox"])
        x0, y0, x1, y1 = max(x, lx), max(y, ly), min(x + width, lx + lw), min(y + height, ly + lh)
        if x1 > x0 and y1 > y0:
            roi[y0 - y:y1 - y, x0 - x:x1 - x] = True
    return roi


def run(
    queue_path: Path, labels_dir: Path, prototype_path: Path,
    semantic_path: Path, position_path: Path, output_dir: Path,
    *, all_holdout: bool = False,
) -> dict[str, Any]:
    queue_payload = _read(queue_path)
    queued = queue_payload.get("records") or [
        {"cycle": item["cycle"], "paint_label": item["paint_label"]}
        for item in queue_payload.get("selected_paints", [])
    ]
    if not queued:
        raise ValueError("queue must contain records or selected_paints")
    wanted = {(int(item["cycle"]), str(item["paint_label"])) for item in queued}
    holdouts = (
        set(wanted) if all_holdout else
        {tuple((int(queued[index]["cycle"]), str(queued[index]["paint_label"]))) for index in (0, 4, 8, 12)}
    )
    prototypes = _read(prototype_path)["prototypes"]
    contexts = _historical_contexts(
        labels_dir, sorted({cycle for cycle, _paint in wanted}), prototypes,
        PortableExtraTrees(semantic_path), PortableExtraTrees(position_path),
    )
    candidates: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
    for context in contexts:
        key = (int(context["cycle"]), str(context["paint_label"]))
        if key not in wanted:
            continue
        positives, negatives = _labels(labels_dir, key[0])
        positives = [item for item in positives if item["paint_label"] == key[1]]
        negatives = [item for item in negatives if item["paint_label"] == key[1]]
        proposal_bbox = context["proposal"]["bbox"]
        positive_match = any(_matches(proposal_bbox, item["bbox"]) for item in positives)
        negative_match = any(_matches(proposal_bbox, item["bbox"]) for item in negatives)
        if positive_match == negative_match:
            continue
        raw = _raw_mask(context)
        if positive_match:
            roi = _positive_roi(proposal_bbox, positives)
            label = _prune_annotation_components(raw & roi, roi)
            if int(np.count_nonzero(label)) < 32:
                continue
            kind = "number_core"
            rank = int(np.count_nonzero(label))
        else:
            label = np.zeros(raw.shape, bool)
            kind = "empty_control"
            rank = int(np.count_nonzero(raw))
        candidates.setdefault((key[0], key[1], kind), []).append({
            "context": context, "label": label, "rank": rank,
        })

    chosen = []
    for key, values in candidates.items():
        limit = 2 if key[2] == "number_core" else 1
        chosen.extend(sorted(values, key=lambda item: -item["rank"])[:limit])
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for index, item in enumerate(sorted(chosen, key=lambda z: (z["context"]["cycle"], z["context"]["paint_label"], _proposal_id(z["context"]["proposal"]))), 1):
        context = item["context"]
        rgb = np.asarray(Image.open(context["source_1024"]).convert("RGB"))
        hypothesis = number_context_mask_hypotheses(
            rgb, context["proposal"], context["seed"], context["members"],
        )
        label = np.ascontiguousarray(item["label"], dtype=bool)
        label.setflags(write=False)
        proposal_id = _proposal_id(context["proposal"])
        sheet = output_dir / f'{index:03d}_cycle{context["cycle"]}_{proposal_id.split(":")[-1]}.png'
        _render(Image.fromarray(rgb), context["proposal"]["bbox"], label, sheet)
        paint_key = (int(context["cycle"]), str(context["paint_label"]))
        records.append({
            "cycle": paint_key[0], "paint_label": paint_key[1],
            "role": "holdout" if paint_key in holdouts else "train",
            "source_1024": context["source_1024"],
            "proposal_id": proposal_id,
            "proposal_bbox": context["proposal"]["bbox"],
            "label_kind": "number_core" if np.any(label) else "empty_control",
            "number_pixels": int(np.count_nonzero(label)),
            "label_mask_rle": encode_instance_mask_rle(label),
            "hypothesis_masks": {
                name: encode_instance_mask_rle(mask) for name, mask in hypothesis["masks"].items()
            },
            "review_sheet": str(sheet).replace("\\", "/"),
        })
    result = {
        "schema": "smart-tga-number-context-relative-pixel-dataset-v1",
        "source_queue": str(queue_path).replace("\\", "/"),
        "paint_count": len({(item["cycle"], item["paint_label"]) for item in records}),
        "train_paints": sorted({item["paint_label"] for item in records if item["role"] == "train"}),
        "holdout_paints": sorted({item["paint_label"] for item in records if item["role"] == "holdout"}),
        "number_core_records": sum(item["label_kind"] == "number_core" for item in records),
        "empty_control_records": sum(item["label_kind"] == "empty_control" for item in records),
        "records": records,
    }
    (output_dir / "relative_pixel_dataset.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--prototype", type=Path, required=True)
    parser.add_argument("--semantic", type=Path, required=True)
    parser.add_argument("--position", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--all-holdout", action="store_true")
    args = parser.parse_args()
    result = run(
        args.queue, args.labels_dir, args.prototype, args.semantic, args.position,
        args.output_dir, all_holdout=args.all_holdout,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
