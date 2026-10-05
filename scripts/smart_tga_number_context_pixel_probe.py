"""Train/evaluate a paint-disjoint proposal-local Number-core pixel scorer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
    from engine.spec_sculpt.number_context_pixels import FEATURE_NAMES, pixel_feature_cube
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle  # type: ignore
    from engine.spec_sculpt.number_context_pixels import FEATURE_NAMES, pixel_feature_cube  # type: ignore


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _records(queue_path: Path, label_path: Path, probes: Sequence[Path]) -> list[dict[str, Any]]:
    queue = {
        (int(item["cycle"]), item["paint_label"], item["proposal_id"]): item
        for item in _read(queue_path)["queue"]
    }
    masks = {
        (int(probe["cycle"]), item["paint_label"], item["proposal_id"]): {
            name: decode_instance_mask_rle(rle) for name, rle in item["mask_rle"].items()
        }
        for probe in (_read(path) for path in probes)
        for item in probe["records"]
    }
    records = []
    for label in _read(label_path)["records"]:
        key = (int(label["cycle"]), label["paint_label"], label["proposal_id"])
        item = queue[key]
        rgb = np.asarray(Image.open(item["source_1024"]).convert("RGB"))
        records.append({
            **label, "source_1024": item["source_1024"], "rgb": rgb,
            "hypotheses": masks[key],
            "label_mask": decode_instance_mask_rle(label["mask_rle"]),
        })
    return records


def _sample(record: Mapping[str, Any], rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cube = pixel_feature_cube(record["rgb"], record["proposal_bbox"], record["hypotheses"])
    label = np.asarray(record["label_mask"], bool)
    union = np.logical_or.reduce(list(record["hypotheses"].values()))
    positive = np.flatnonzero(label.ravel())
    negative = np.flatnonzero((union & ~label).ravel())
    background = np.flatnonzero((~union & ~label).ravel())
    def take(values: np.ndarray, count: int) -> np.ndarray:
        return rng.choice(values, min(count, len(values)), replace=False) if len(values) else values
    indexes = np.concatenate([take(positive, 12000), take(negative, 16000), take(background, 3000)])
    flags = np.concatenate([
        np.zeros(min(12000, len(positive)), np.uint8),
        np.ones(min(16000, len(negative)), np.uint8),
        np.ones(min(3000, len(background)), np.uint8),
    ])
    return cube.reshape(-1, cube.shape[2])[indexes], label.ravel()[indexes].astype(np.uint8), flags


def _fit(matrix: np.ndarray, labels: np.ndarray, seed: int) -> Any:
    from sklearn.ensemble import ExtraTreesClassifier
    return ExtraTreesClassifier(
        n_estimators=500, min_samples_leaf=3, max_features="sqrt",
        class_weight="balanced", random_state=seed, n_jobs=-1,
    ).fit(matrix, labels)


def _evaluate(model: Any, records: Sequence[Mapping[str, Any]], threshold: float) -> dict[str, Any]:
    result = {"positive_pixels": 0, "predicted_pixels": 0, "true_positive_pixels": 0,
              "hard_negative_pixels": 0, "positive_records": 0, "positive_record_hits": 0}
    baseline = {key: 0 for key in result}
    for record in records:
        if record["label_kind"] == "uncertain_excluded":
            continue
        cube = pixel_feature_cube(record["rgb"], record["proposal_bbox"], record["hypotheses"])
        scores = model.predict_proba(cube.reshape(-1, cube.shape[2]))[:, 1].reshape(cube.shape[:2])
        predicted = scores >= threshold
        raw = np.asarray(record["hypotheses"]["raw_instance_union"], bool)
        label = np.asarray(record["label_mask"], bool)
        for target, mask in ((result, predicted), (baseline, raw)):
            target["positive_pixels"] += int(np.count_nonzero(label))
            target["predicted_pixels"] += int(np.count_nonzero(mask))
            target["true_positive_pixels"] += int(np.count_nonzero(mask & label))
            if record["label_kind"] == "empty_control":
                target["hard_negative_pixels"] += int(np.count_nonzero(mask))
            elif record["label_kind"] == "number_core":
                target["positive_records"] += 1
                target["positive_record_hits"] += int(np.count_nonzero(mask & label) >= 32)
    def finish(values: dict[str, Any]) -> dict[str, Any]:
        values["pixel_precision"] = round(values["true_positive_pixels"] / max(1, values["predicted_pixels"]), 6)
        values["pixel_recall"] = round(values["true_positive_pixels"] / max(1, values["positive_pixels"]), 6)
        return values
    return {"raw_union_baseline": finish(baseline), "pixel_scorer": finish(result)}


def run(queue: Path, labels: Path, probes: Sequence[Path], model_output: Path) -> dict[str, Any]:
    from sklearn.model_selection import GroupKFold
    records = _records(queue, labels, probes)
    train_records = [item for item in records if item["cycle"] == 693 and item["label_kind"] != "uncertain_excluded"]
    canary_records = [item for item in records if item["cycle"] == 695]
    rng = np.random.default_rng(701)
    samples = [_sample(item, rng) for item in train_records]
    matrix = np.concatenate([item[0] for item in samples])
    targets = np.concatenate([item[1] for item in samples])
    control_flags = np.concatenate([
        np.full(len(item[1]), record["label_kind"] == "empty_control", bool)
        for item, record in zip(samples, train_records)
    ])
    groups = np.concatenate([
        np.full(len(item[1]), record["paint_label"], object)
        for item, record in zip(samples, train_records)
    ])
    heldout = np.zeros(len(targets), np.float32)
    splitter = GroupKFold(n_splits=len(set(groups)))
    for fold, (train_index, test_index) in enumerate(splitter.split(matrix, targets, groups), 1):
        heldout[test_index] = _fit(matrix[train_index], targets[train_index], 701 + fold).predict_proba(matrix[test_index])[:, 1]
    control_scores = heldout[control_flags & (targets == 0)]
    threshold = min(1.0, float(np.max(control_scores, initial=0.5)) + 1e-7)
    model = _fit(matrix, targets, 701)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES, "threshold": threshold}, model_output)
    return {
        "schema": "smart-tga-number-context-pixel-probe-v1",
        "train_paints": sorted(set(groups)), "train_samples": len(targets),
        "train_positive_samples": int(np.count_nonzero(targets)),
        "feature_count": len(FEATURE_NAMES), "cv_control_calibrated_threshold": threshold,
        "cycle693_fit_metrics": _evaluate(model, train_records, threshold),
        "untouched_cycle695": _evaluate(model, canary_records, threshold),
        "model_output": str(model_output).replace("\\", "/"),
        "runtime_integrated": False, "ownership_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--probes", nargs="+", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.queue, args.labels, args.probes, args.model_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
