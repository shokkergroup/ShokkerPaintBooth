"""Paint-grouped DLM Number-family similarity and ranked-pixel probe."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

import numpy as np

try:
    from engine.spec_sculpt.number_context_family_similarity import normalized_visual_descriptor, prototype_margin
    from scripts.smart_tga_number_context_conformal_probe import _fit_pixel, _metrics, _sample, _score
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records
    from scripts.smart_tga_number_context_relative_probe import _load_new
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_family_similarity import normalized_visual_descriptor, prototype_margin  # type: ignore
    from scripts.smart_tga_number_context_conformal_probe import _fit_pixel, _metrics, _sample, _score  # type: ignore
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records  # type: ignore
    from scripts.smart_tga_number_context_relative_probe import _load_new  # type: ignore


def _descriptor(record: dict[str, Any]) -> np.ndarray:
    return normalized_visual_descriptor(record["rgb"], record["hypotheses"]["raw_instance_union"])


def _leave_paint_out_margins(records: Sequence[dict[str, Any]], descriptors: Sequence[np.ndarray]) -> np.ndarray:
    result = []
    for index, record in enumerate(records):
        eligible = [i for i, item in enumerate(records) if item["paint_label"] != record["paint_label"]]
        positives = [descriptors[i] for i in eligible if records[i]["label_kind"] == "number_core"]
        controls = [descriptors[i] for i in eligible if records[i]["label_kind"] == "empty_control"]
        result.append(prototype_margin(descriptors[index], positives, controls))
    return np.asarray(result, np.float32)


def _paired_metrics(records: Sequence[dict[str, Any]], margins: np.ndarray) -> dict[str, Any]:
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for record, score in zip(records, margins):
        grouped[record["paint_label"]].append((record["label_kind"], float(score)))
    rows = []
    for paint, values in sorted(grouped.items()):
        positives = [score for kind, score in values if kind == "number_core"]
        controls = [score for kind, score in values if kind == "empty_control"]
        if positives and controls:
            rows.append({"paint_label": paint, "margin": round(max(positives) - max(controls), 6)})
    return {"wins": sum(item["margin"] > 0 for item in rows), "pairs": len(rows), "records": rows}


def run(
    train_dataset: Path, holdout_dataset: Path, legacy_queue: Path,
    legacy_labels: Path, legacy_probes: Sequence[Path], model_output: Path,
) -> dict[str, Any]:
    from sklearn.model_selection import GroupKFold

    new_records = _load_new(train_dataset)
    legacy = _legacy_records(legacy_queue, legacy_labels, legacy_probes)
    for item in legacy:
        item["role"] = "train"
    train = [item for item in new_records if item["role"] == "train"] + [
        item for item in legacy if item["label_kind"] != "uncertain_excluded"
    ]
    holdout = _load_new(holdout_dataset)

    rng = np.random.default_rng(704)
    samples = [_sample(item, rng) for item in train]
    matrix = np.concatenate([item[0] for item in samples])
    labels = np.concatenate([item[1] for item in samples])
    sample_groups = np.concatenate([
        np.full(len(sample[1]), item["paint_label"], object)
        for sample, item in zip(samples, train)
    ])
    pixel_models = []
    oof_scores: list[np.ndarray | None] = [None] * len(train)
    for fold, (train_index, test_index) in enumerate(GroupKFold(4).split(matrix, labels, sample_groups), 1):
        model = _fit_pixel(matrix[train_index], labels[train_index], 704 + fold)
        pixel_models.append(model)
        test_paints = set(sample_groups[test_index])
        for index, record in enumerate(train):
            if record["paint_label"] in test_paints:
                oof_scores[index] = _score(model, record)
    if any(item is None for item in oof_scores):
        raise AssertionError("every training record must receive cross-fitted pixel scores")
    train_pixel_scores = [np.asarray(item) for item in oof_scores]

    train_descriptors = [_descriptor(item) for item in train]
    train_margins = _leave_paint_out_margins(train, train_descriptors)
    paired = _paired_metrics(train, train_margins)
    if paired["wins"] < 6 or paired["pairs"] < 7:
        raise AssertionError(f"family evidence gate failed: {paired['wins']}/{paired['pairs']}")
    kinds = np.asarray([item["label_kind"] for item in train], object)
    gate = float(np.max(train_margins[kinds == "empty_control"])) + 1e-7

    best_fraction, best_f1 = 0.0, -1.0
    for fraction in np.linspace(0.10, 1.0, 19):
        metric = _metrics(train, train_pixel_scores, train_margins, gate, float(fraction))["conformal"]
        if metric["control_pixels"]:
            continue
        precision, recall = metric["pixel_precision"], metric["pixel_recall"]
        f1 = 2 * precision * recall / max(1e-9, precision + recall)
        if f1 > best_f1:
            best_fraction, best_f1 = float(fraction), f1

    positives = [descriptor for descriptor, kind in zip(train_descriptors, kinds) if kind == "number_core"]
    controls = [descriptor for descriptor, kind in zip(train_descriptors, kinds) if kind == "empty_control"]
    holdout_descriptors = [_descriptor(item) for item in holdout]
    holdout_margins = np.asarray([
        prototype_margin(descriptor, positives, controls) for descriptor in holdout_descriptors
    ], np.float32)
    holdout_pixel_scores = [
        np.mean([_score(model, record) for model in pixel_models], axis=0)
        for record in holdout
    ]
    model_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_output,
        descriptors=np.asarray(train_descriptors, np.float32),
        labels=(kinds == "number_core").astype(np.uint8),
        proposal_gate=np.asarray([gate], np.float32),
        pixel_fraction=np.asarray([best_fraction], np.float32),
    )
    return {
        "schema": "smart-tga-number-context-family-probe-v1",
        "train_paints": len({item["paint_label"] for item in train}),
        "train_records": len(train),
        "proposal_gate": gate,
        "pixel_fraction": best_fraction,
        "paint_grouped_pairwise": paired,
        "cross_fitted_train": _metrics(train, train_pixel_scores, train_margins, gate, best_fraction),
        "cross_fitted_scores": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "label_kind": item["label_kind"], "family_margin": round(float(score), 6)}
            for item, score in zip(train, train_margins)
        ],
        "paint_disjoint_holdout_paints": sorted({item["paint_label"] for item in holdout}),
        "paint_disjoint_holdout": _metrics(holdout, holdout_pixel_scores, holdout_margins, gate, best_fraction),
        "holdout_family_margins": [round(float(value), 6) for value in holdout_margins],
        "runtime_integrated": False,
        "ownership_authority": False,
        "model_output": str(model_output).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--holdout-dataset", type=Path, required=True)
    parser.add_argument("--legacy-queue", type=Path, required=True)
    parser.add_argument("--legacy-labels", type=Path, required=True)
    parser.add_argument("--legacy-probes", nargs="+", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.train_dataset, args.holdout_dataset, args.legacy_queue, args.legacy_labels,
                 args.legacy_probes, args.model_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
