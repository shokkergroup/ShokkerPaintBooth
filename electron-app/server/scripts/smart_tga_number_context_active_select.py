"""Select untouched DLM paints by visual-family coverage and hard-negative confusion."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_context_family_similarity import (
        d4_cosine_similarity, normalized_visual_descriptor,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_family_similarity import (  # type: ignore
        d4_cosine_similarity, normalized_visual_descriptor,
    )


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _descriptor(source: np.ndarray, layer_mask: np.ndarray, bbox: Sequence[int]) -> np.ndarray:
    x, y, width, height = (int(value) for value in bbox)
    rgb = source[y:y + height, x:x + width]
    support = layer_mask[y:y + height, x:x + width]
    return normalized_visual_descriptor(rgb, support)


def _evidence(
    descriptor: np.ndarray, positives: np.ndarray, controls: np.ndarray,
) -> tuple[float, float, float]:
    positive = max(d4_cosine_similarity(descriptor, item) for item in positives)
    control = max(d4_cosine_similarity(descriptor, item) for item in controls)
    return positive, control, positive - control


def _seen_paints(
    reviewed: Sequence[Path], legacy_labels: Path, excluded_queues: Sequence[Path] = (),
) -> set[str]:
    seen = set()
    for path in reviewed:
        seen.update(str(item["paint_label"]) for item in _read(path)["records"])
    seen.update(str(item["paint_label"]) for item in _read(legacy_labels)["records"])
    for path in excluded_queues:
        payload = _read(path)
        rows = payload.get("selected_paints") or payload.get("records") or []
        seen.update(str(item["paint_label"]) for item in rows)
    return seen


def run(
    inspections: Sequence[Path], prototype_model: Path, reviewed: Sequence[Path],
    legacy_labels: Path, output: Path, paint_count: int = 6, control_count: int = 5,
    excluded_queues: Sequence[Path] = (),
) -> dict[str, Any]:
    model = np.load(prototype_model)
    descriptors = np.asarray(model["descriptors"], np.float32)
    labels = np.asarray(model["labels"], bool)
    positives, controls = descriptors[labels], descriptors[~labels]
    seen = _seen_paints(reviewed, legacy_labels, excluded_queues)
    excluded_content = {
        str(item.get("source_sha256"))
        for path in excluded_queues
        for item in (_read(path).get("selected_paints") or [])
        if item.get("source_sha256")
    }
    paint_rows = []
    for inspection_path in inspections:
        cycle = int(inspection_path.parent.name[5:8])
        for paint in _read(inspection_path):
            paint_label = str(paint["paint_label"])
            if paint_label in seen or not paint_label.startswith("dirtlatemodel "):
                continue
            components = _read(Path(paint["component_records"]))
            source = np.asarray(Image.open(paint["source_1024"]).convert("RGB"))
            layer_masks = {
                name: np.asarray(Image.open(path).convert("L")) > 0
                for name, path in paint["mask_paths"].items()
            }
            targets, negatives = [], []
            for item in components:
                if int(item.get("area_px", 0)) < 400 or item["layer"] not in layer_masks:
                    continue
                descriptor = _descriptor(source, layer_masks[item["layer"]], item["bbox"])
                positive, control, margin = _evidence(descriptor, positives, controls)
                row = {
                    "layer": item["layer"], "component_index": item["component_index"],
                    "crop_file": item["crop_file"], "area_px": item["area_px"],
                    "positive_similarity": round(positive, 6),
                    "control_similarity": round(control, 6),
                    "family_margin": round(margin, 6),
                }
                if item["layer"] == "numbers":
                    targets.append(row)
                elif item["layer"] in {"sponsors", "template", "brand_graphics", "paint"}:
                    negatives.append(row)
            if not targets:
                continue
            largest_targets = sorted(targets, key=lambda item: -item["area_px"])[:3]
            coverage = max(item["positive_similarity"] for item in largest_targets)
            paint_rows.append({
                "cycle": cycle, "paint_label": paint_label,
                "source_1024": paint["source_1024"],
                "source_sha256": hashlib.sha256(Path(paint["source_1024"]).read_bytes()).hexdigest(),
                "prototype_coverage": round(coverage, 6),
                "target_candidates": largest_targets,
                "control_candidates": sorted(negatives, key=lambda item: -item["family_margin"])[:3],
            })

    unique_rows, seen_content = [], set(excluded_content)
    for row in sorted(paint_rows, key=lambda item: (item["prototype_coverage"], item["paint_label"])):
        if row["source_sha256"] in seen_content:
            continue
        seen_content.add(row["source_sha256"])
        unique_rows.append(row)
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in unique_rows:
        family = row["paint_label"].split("/", 1)[0]
        by_family.setdefault(family, []).append(row)
    selected = []
    for family in sorted(by_family):
        selected.extend(by_family[family][:2])
    for row in unique_rows:
        if row not in selected:
            selected.append(row)
        if len(selected) >= paint_count:
            break
    selected = selected[:paint_count]
    hard_negatives = sorted(
        [item | {"paint_label": row["paint_label"]} for row in selected for item in row["control_candidates"]],
        key=lambda item: (-item["family_margin"], item["paint_label"], item["component_index"]),
    )[:control_count]
    result = {
        "schema": "smart-tga-number-context-active-selection-v1",
        "selection_basis": "lowest visual Number-prototype coverage among largest runtime Number candidates",
        "excluded_reviewed_paints": len(seen),
        "candidate_paints": len(paint_rows),
        "unique_candidate_paints": len(unique_rows),
        "selected_paints": selected,
        "hard_negative_controls": hard_negatives,
        "holdout_policy": "review before scoring; calibrate nothing on this batch; evaluate once",
        "filename_authority": False,
        "bbox_authority": False,
    }
    if len(selected) < paint_count or len(hard_negatives) < control_count:
        raise AssertionError("active selection did not produce the requested paint/control coverage")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inspections", nargs="+", type=Path)
    parser.add_argument("--prototype-model", type=Path, required=True)
    parser.add_argument("--reviewed", nargs="+", type=Path, required=True)
    parser.add_argument("--legacy-labels", type=Path, required=True)
    parser.add_argument("--exclude-queues", nargs="*", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paints", type=int, default=6)
    parser.add_argument("--controls", type=int, default=5)
    args = parser.parse_args()
    result = run(args.inspections, args.prototype_model, args.reviewed, args.legacy_labels,
                 args.output, args.paints, args.controls, args.exclude_queues)
    print(json.dumps({
        "selected_paints": [item["paint_label"] for item in result["selected_paints"]],
        "hard_negative_controls": len(result["hard_negative_controls"]),
    }, indent=2))


if __name__ == "__main__":
    main()
