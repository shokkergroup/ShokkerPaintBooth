"""Build weak DLM number masks and paint-group validate a one-pass segmenter."""

from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_object_segmentation import (
        MODEL_SIZE,
        build_tiny_unet,
        component_mask,
        image_feature_tensor,
        pooled_boxes,
        pooled_supervision,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_object_segmentation import (  # type: ignore
        MODEL_SIZE,
        build_tiny_unet,
        component_mask,
        image_feature_tensor,
        pooled_boxes,
        pooled_supervision,
    )


@dataclass
class PaintSupervision:
    cycle: int
    paint_label: str
    source_path: Path
    features: np.ndarray
    target: np.ndarray
    known: np.ndarray
    weak_boxes: np.ndarray
    components: list[dict[str, Any]]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _cycle(path: Path) -> int:
    match = re.search(r"cycle(\d+)", path.name)
    if not match:
        raise ValueError(f"cannot determine cycle from {path}")
    return int(match.group(1))


def _inspection_index(path: Path, cache: dict[Path, dict[str, Any]]) -> dict[str, Any]:
    if path not in cache:
        payload = _read(path)
        cache[path] = {str(item["paint_label"]): item for item in payload}
    return cache[path]


def _missed_boxes(labels_dir: Path, cycles: set[int]) -> dict[tuple[int, str], list[list[int]]]:
    output: dict[tuple[int, str], list[list[int]]] = {}
    for path in labels_dir.glob("cycle*_missed_number_instances_v1.json"):
        cycle = _cycle(path)
        if cycle not in cycles:
            continue
        for item in _read(path).get("instances", []):
            output.setdefault((cycle, str(item["paint_label"])), []).append([int(v) for v in item["bbox"]])
    return output


def build_supervision(labels_dir: Path, cycles: Sequence[int]) -> tuple[list[PaintSupervision], dict[str, Any]]:
    selected_cycles = set(int(value) for value in cycles)
    label_paths = [
        path for path in labels_dir.glob("cycle*_numbers_v1.json")
        if _cycle(path) in selected_cycles
    ]
    missing = _missed_boxes(labels_dir, selected_cycles)
    inspection_cache: dict[Path, dict[str, Any]] = {}
    records: list[PaintSupervision] = []
    manifest_paints = []

    for label_path in sorted(label_paths, key=lambda item: (_cycle(item), item.name)):
        review = _read(label_path)
        cycle = _cycle(label_path)
        paint_label = str(review["paint_label"])
        inspection_path = Path(review["inspection_records"])
        inspection = _inspection_index(inspection_path, inspection_cache).get(paint_label)
        if inspection is None:
            raise KeyError(f"{paint_label} not found in {inspection_path}")
        source_path = Path(inspection["source_1024"])
        parent = source_path.parent
        rgb = np.asarray(Image.open(source_path).convert("RGB"))
        component_records = {
            (str(item["layer"]), int(item["component_index"])): item
            for item in _read(parent / "component_records.json")
        }
        layer_masks = {
            path.stem: np.asarray(Image.open(path).convert("L")) > 0
            for path in (parent / "masks").glob("*.png")
        }
        positive = np.zeros(rgb.shape[:2], bool)
        negative = np.zeros(rgb.shape[:2], bool)
        components = []
        for item in review.get("component_labels", []):
            layer = str(item["layer"])
            index = int(item["component_index"])
            meta = component_records[(layer, index)]
            expected_bbox = [int(value) for value in item["expected_bbox"]]
            if [int(value) for value in meta["bbox"]] != expected_bbox:
                raise AssertionError(f"bbox drift for {paint_label} {layer}:{index}")
            exact = component_mask(layer_masks[layer], expected_bbox, int(meta["area_px"]))
            is_number = str(item["target_layer"]).lower() == "numbers"
            (positive if is_number else negative).__ior__(exact)
            small = cv2.resize(exact.astype(np.float32), (MODEL_SIZE, MODEL_SIZE), interpolation=cv2.INTER_AREA) > 0
            components.append({
                "layer": layer, "component_index": index, "is_number": is_number,
                "class": str(item["target_layer"]), "label": str(item["label"]),
                "bbox": expected_bbox, "mask": small,
            })
        target, known = pooled_supervision(positive, negative)
        weak = pooled_boxes(missing.get((cycle, paint_label), []), rgb.shape[:2])
        records.append(PaintSupervision(
            cycle=cycle, paint_label=paint_label, source_path=source_path,
            features=image_feature_tensor(rgb), target=target, known=known,
            weak_boxes=weak, components=components,
        ))
        manifest_paints.append({
            "cycle": cycle, "paint_label": paint_label,
            "source_1024": str(source_path).replace("\\", "/"),
            "positive_components": sum(item["is_number"] for item in components),
            "negative_components": sum(not item["is_number"] for item in components),
            "positive_pixels_1024": int(np.count_nonzero(positive)),
            "negative_pixels_1024": int(np.count_nonzero(negative)),
            "weak_number_boxes": len(missing.get((cycle, paint_label), [])),
        })
    manifest = {
        "schema": "smart-tga-number-object-supervision-v1",
        "cycles": sorted(selected_cycles), "paint_count": len(records),
        "positive_components": sum(item["positive_components"] for item in manifest_paints),
        "negative_components": sum(item["negative_components"] for item in manifest_paints),
        "weak_number_boxes": sum(item["weak_number_boxes"] for item in manifest_paints),
        "unknown_pixels_are_negative": False,
        "weak_boxes_are_filled_positive": False,
        "paints": manifest_paints,
    }
    return records, manifest


def _augment(features, target, known, weak, rng: np.random.Generator):
    turns = int(rng.integers(0, 4))
    values = [np.rot90(item, turns, axes=(-2, -1)).copy() for item in (features, target, known, weak)]
    flipped = bool(rng.random() < 0.5)
    if flipped:
        values = [np.flip(item, axis=-1).copy() for item in values]
    return (*values, turns, flipped)


def _transform_mask(mask: np.ndarray, turns: int, flipped: bool) -> np.ndarray:
    output = np.rot90(mask, turns, axes=(-2, -1)).copy()
    return np.flip(output, axis=-1).copy() if flipped else output


def _fit(records: Sequence[PaintSupervision], epochs: int, seed: int):
    import torch
    import torch.nn.functional as functional

    torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
    model = build_tiny_unet()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1.5e-3, weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    model.train()
    history = []
    for epoch in range(epochs):
        order = rng.permutation(len(records))
        losses = []
        for start in range(0, len(order), 4):
            batch = [records[int(index)] for index in order[start:start + 4]]
            augmented = [_augment(item.features, item.target, item.known, item.weak_boxes, rng) for item in batch]
            features = torch.from_numpy(np.stack([item[0] for item in augmented])).float()
            target = torch.from_numpy(np.stack([item[1] for item in augmented])[:, None]).float()
            known = torch.from_numpy(np.stack([item[2] for item in augmented])[:, None]).float()
            weak = torch.from_numpy(np.stack([item[3] for item in augmented])[:, None]).bool()
            logits = model(features)
            weights = torch.where(target > 0.5, 3.0, 1.0)
            supervised = functional.binary_cross_entropy_with_logits(logits, target, reduction="none")
            supervised = (supervised * known * weights).sum() / (known * weights).sum().clamp_min(1.0)
            probabilities = torch.sigmoid(logits)
            weak_losses = []
            for row in range(len(batch)):
                candidates = probabilities[row][weak[row] & (known[row] < 0.5)]
                if candidates.numel():
                    count = max(1, min(64, candidates.numel() // 20))
                    weak_losses.append(-torch.log(torch.topk(candidates, count).values.mean().clamp_min(1e-6)))
            weak_loss = torch.stack(weak_losses).mean() if weak_losses else logits.sum() * 0.0
            component_losses = []
            for row, (paint, transformed) in enumerate(zip(batch, augmented)):
                turns, flipped = int(transformed[4]), bool(transformed[5])
                for component in paint.components:
                    mask = torch.from_numpy(_transform_mask(component["mask"], turns, flipped)).bool()
                    values = probabilities[row, 0][mask]
                    if not values.numel():
                        continue
                    count = max(1, values.numel() // 4)
                    object_score = torch.topk(values, count).values.mean().clamp(1e-5, 1.0 - 1e-5)
                    truth = torch.as_tensor(float(component["is_number"]))
                    semantic = functional.binary_cross_entropy(object_score, truth)
                    component_losses.append(semantic * (1.5 if component["is_number"] else 1.0))
            component_loss = torch.stack(component_losses).mean() if component_losses else logits.sum() * 0.0
            unknown = (known < 0.5) & ~weak
            sparsity = probabilities[unknown].mean() if unknown.any() else logits.sum() * 0.0
            loss = supervised + 0.65 * component_loss + 0.06 * weak_loss + 0.015 * sparsity
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        history.append(round(float(np.mean(losses)), 6))
    return model.eval(), history


def _predict(model, records: Sequence[PaintSupervision]) -> dict[str, np.ndarray]:
    import torch
    output = {}
    with torch.no_grad():
        for item in records:
            value = torch.from_numpy(item.features[None]).float()
            output[item.paint_label] = torch.sigmoid(model(value))[0, 0].numpy()
    return output


def _component_score(probability: np.ndarray, mask: np.ndarray) -> float:
    values = probability[mask]
    if not len(values):
        return 0.0
    count = max(1, len(values) // 4)
    return float(np.mean(np.partition(values, len(values) - count)[-count:]))


def _summarize(records: Sequence[PaintSupervision], predictions: dict[str, np.ndarray], threshold: float) -> dict[str, Any]:
    scores = []
    positive_paints = set()
    hit_paints = set()
    for paint in records:
        probability = predictions[paint.paint_label]
        for component in paint.components:
            score = _component_score(probability, component["mask"])
            accepted = score >= threshold
            if component["is_number"]:
                positive_paints.add(paint.paint_label)
                if accepted:
                    hit_paints.add(paint.paint_label)
            scores.append({
                "paint_label": paint.paint_label, "cycle": paint.cycle,
                "source_layer": component["layer"],
                "component_index": component["component_index"], "class": component["class"],
                "is_number": component["is_number"], "score": round(score, 6), "accepted": accepted,
            })
    true_positive = sum(item["accepted"] and item["is_number"] for item in scores)
    false_positive = sum(item["accepted"] and not item["is_number"] for item in scores)
    positives = sum(item["is_number"] for item in scores)
    weak_total = weak_hits = 0
    for paint in records:
        if paint.weak_boxes.any():
            count, labels = cv2.connectedComponents(paint.weak_boxes.astype(np.uint8), 8)
            for label in range(1, count):
                weak_total += 1
                values = predictions[paint.paint_label][labels == label]
                weak_hits += bool(len(values) and float(np.max(values)) >= threshold)
    return {
        "paint_number_coverage": f"{len(hit_paints)}/{len(positive_paints)}",
        "number_component_hits": f"{true_positive}/{positives}",
        "accepted_controls": false_positive,
        "component_precision": round(true_positive / max(1, true_positive + false_positive), 6),
        "component_recall": round(true_positive / max(1, positives), 6),
        "weak_box_hits": f"{weak_hits}/{weak_total}", "scores": scores,
    }


def run(labels_dir: Path, cycles: Sequence[int], output_dir: Path, epochs: int, folds: int) -> dict[str, Any]:
    import torch
    from sklearn.model_selection import GroupKFold

    records, manifest = build_supervision(labels_dir, cycles)
    groups = np.asarray([item.paint_label for item in records], object)
    cross_predictions: dict[str, np.ndarray] = {}
    fold_history = []
    splitter = GroupKFold(n_splits=min(folds, len(records)))
    dummy = np.zeros(len(records))
    for fold, (train_indexes, test_indexes) in enumerate(splitter.split(dummy, dummy, groups), 1):
        train = [records[int(index)] for index in train_indexes]
        test = [records[int(index)] for index in test_indexes]
        model, history = _fit(train, epochs, 7100 + fold)
        cross_predictions.update(_predict(model, test))
        fold_history.append({"fold": fold, "train_paints": len(train), "test_paints": len(test), "loss": history})
    control_scores = []
    for paint in records:
        probability = cross_predictions[paint.paint_label]
        control_scores.extend(
            _component_score(probability, item["mask"])
            for item in paint.components if not item["is_number"]
        )
    zero_control_threshold = min(1.0, max(control_scores, default=0.5) + 1e-6)
    zero_control = _summarize(records, cross_predictions, zero_control_threshold)

    # Also report the best threshold that keeps precision at or above Cycle708's 0.833333.
    candidates = sorted({
        _component_score(cross_predictions[paint.paint_label], item["mask"])
        for paint in records for item in paint.components
    }, reverse=True)
    best_threshold = zero_control_threshold
    best_summary = zero_control
    for threshold in candidates:
        summary = _summarize(records, cross_predictions, threshold)
        if summary["component_precision"] >= 0.833333 and summary["component_recall"] > best_summary["component_recall"]:
            best_threshold, best_summary = threshold, summary

    final_model, final_history = _fit(records, epochs, 7199)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "number_object_segmenter_cycle710_semantic_v2.pt"
    torch.save({
        "state_dict": final_model.state_dict(), "model_size": MODEL_SIZE,
        "base_channels": 12, "threshold": float(best_threshold),
        "cycles": list(sorted(set(cycles))), "ownership_authority": False,
    }, model_path)
    (output_dir / "supervision_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result = {
        "schema": "smart-tga-number-object-segmentation-train-v2",
        "validation": f"{fold}-fold paint-disjoint cross-fitting; each prediction came from a model that never saw that paint",
        "paint_count": len(records), "reviewed_components": manifest["positive_components"] + manifest["negative_components"],
        "positive_components": manifest["positive_components"], "negative_components": manifest["negative_components"],
        "weak_number_boxes": manifest["weak_number_boxes"],
        "cycle708_reference": {"component_precision": 0.833333, "component_recall": 0.5},
        "cross_fitted_zero_control": {"threshold": zero_control_threshold, **zero_control},
        "cross_fitted_precision_floor": {"threshold": float(best_threshold), **best_summary},
        "fold_training": fold_history, "final_training_loss": final_history,
        "model_output": str(model_path).replace("\\", "/"),
        "runtime_integrated": False, "ownership_authority": False,
    }
    (output_dir / "training_metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--cycles", nargs="+", type=int, default=list(range(681, 691)) + [693, 695])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=18)
    parser.add_argument("--folds", type=int, default=3)
    args = parser.parse_args()
    result = run(args.labels_dir, args.cycles, args.output_dir, args.epochs, args.folds)
    compact = {key: value for key, value in result.items() if key not in {"fold_training"}}
    for section in ("cross_fitted_zero_control", "cross_fitted_precision_floor"):
        compact[section] = {key: value for key, value in result[section].items() if key != "scores"}
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
