"""Cross-fitted within-paint proposal-copy corroboration for DLM Numbers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

try:
    from engine.spec_sculpt.number_context_family_similarity import (
        d4_cosine_similarity, mask_iou, normalized_score_topology,
    )
    from scripts.smart_tga_number_context_conformal_probe import _fit_pixel, _metrics, _sample, _score
    from scripts.smart_tga_number_context_family_probe import _descriptor, _leave_paint_out_margins, _paired_metrics
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records
    from scripts.smart_tga_number_context_relative_probe import _load_new
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_family_similarity import (  # type: ignore
        d4_cosine_similarity, mask_iou, normalized_score_topology,
    )
    from scripts.smart_tga_number_context_conformal_probe import _fit_pixel, _metrics, _sample, _score  # type: ignore
    from scripts.smart_tga_number_context_family_probe import _descriptor, _leave_paint_out_margins, _paired_metrics  # type: ignore
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records  # type: ignore
    from scripts.smart_tga_number_context_relative_probe import _load_new  # type: ignore


def _canvas_mask(record: dict[str, Any]) -> np.ndarray:
    """Register a local immutable mask; absolute position is never scored."""
    local = np.asarray(record["hypotheses"]["raw_instance_union"], bool)
    x, y = map(int, record["proposal_bbox"][:2])
    result = np.zeros(record["rgb"].shape[:2], bool)
    result[y:y + local.shape[0], x:x + local.shape[1]] = local
    result.setflags(write=False)
    return result


def _copy_agreement(
    records: Sequence[dict[str, Any]], pixel_scores: Sequence[np.ndarray],
    family_margins: np.ndarray, family_gate: float,
) -> np.ndarray:
    base_accept = family_margins >= family_gate
    topologies = [
        normalized_score_topology(score, item["hypotheses"]["raw_instance_union"])
        for item, score in zip(records, pixel_scores)
    ]
    canvas_masks = [_canvas_mask(item) for item in records]
    result = np.full(len(records), -1.0, np.float32)
    for index, record in enumerate(records):
        if base_accept[index]:
            continue
        corroborators = [
            other for other, item in enumerate(records)
            if other != index and base_accept[other] and item["paint_label"] == record["paint_label"]
        ]
        if corroborators:
            result[index] = max(
                mask_iou(canvas_masks[index], canvas_masks[other])
                * d4_cosine_similarity(topologies[index], topologies[other])
                for other in corroborators
            )
    return result


def run(
    train_dataset: Path, legacy_queue: Path, legacy_labels: Path,
    legacy_probes: Sequence[Path], output_model: Path,
) -> dict[str, Any]:
    from sklearn.model_selection import GroupKFold

    new_records = _load_new(train_dataset)
    legacy = _legacy_records(legacy_queue, legacy_labels, legacy_probes)
    for item in legacy:
        item["role"] = "train"
    records = [item for item in new_records if item["role"] == "train"] + [
        item for item in legacy if item["label_kind"] != "uncertain_excluded"
    ]
    rng = np.random.default_rng(705)
    samples = [_sample(item, rng) for item in records]
    matrix = np.concatenate([item[0] for item in samples])
    labels = np.concatenate([item[1] for item in samples])
    groups = np.concatenate([
        np.full(len(sample[1]), item["paint_label"], object)
        for sample, item in zip(samples, records)
    ])
    oof_scores: list[np.ndarray | None] = [None] * len(records)
    for fold, (train_index, test_index) in enumerate(GroupKFold(4).split(matrix, labels, groups), 1):
        model = _fit_pixel(matrix[train_index], labels[train_index], 705 + fold)
        test_paints = set(groups[test_index])
        for index, record in enumerate(records):
            if record["paint_label"] in test_paints:
                oof_scores[index] = _score(model, record)
    if any(item is None for item in oof_scores):
        raise AssertionError("every record must receive paint-grouped pixel scores")
    pixel_scores = [np.asarray(item) for item in oof_scores]

    descriptors = [_descriptor(item) for item in records]
    family_margins = _leave_paint_out_margins(records, descriptors)
    kinds = np.asarray([item["label_kind"] for item in records], object)
    family_gate = float(np.max(family_margins[kinds == "empty_control"])) + 1e-7
    paired = _paired_metrics(records, family_margins)
    agreement = _copy_agreement(records, pixel_scores, family_margins, family_gate)
    copy_gate = float(np.max(agreement[kinds == "empty_control"])) + 1e-7
    base_accept = family_margins >= family_gate
    copy_accept = (~base_accept) & (agreement >= copy_gate)
    final_accept = base_accept | copy_accept
    final_scores = final_accept.astype(np.float32)
    metrics = _metrics(records, pixel_scores, final_scores, 0.5, 0.65)
    after = metrics["conformal"]
    if paired["wins"] < 7 or after["control_pixels"] or after["positive_record_hits"] < 16:
        raise AssertionError(
            f"copy gate failed: pairs={paired['wins']}/{paired['pairs']} "
            f"hits={after['positive_record_hits']} controls={after['control_pixels']}"
        )

    output_model.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_model,
        family_gate=np.asarray([family_gate], np.float32),
        copy_gate=np.asarray([copy_gate], np.float32),
        pixel_fraction=np.asarray([0.65], np.float32),
    )
    return {
        "schema": "smart-tga-number-context-copy-probe-v1",
        "train_paints": len({item["paint_label"] for item in records}),
        "train_records": len(records),
        "family_gate": family_gate,
        "copy_gate": copy_gate,
        "pixel_fraction": 0.65,
        "paint_grouped_pairwise": paired,
        "before_family_only": _metrics(records, pixel_scores, family_margins, family_gate, 0.65),
        "after_copy_corroboration": metrics,
        "rescued_records": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "label_kind": item["label_kind"], "copy_agreement": round(float(score), 6)}
            for item, score, accepted in zip(records, agreement, copy_accept) if accepted
        ],
        "copy_diagnostics": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "label_kind": item["label_kind"], "base_accept": bool(base),
             "copy_agreement": round(float(score), 6)}
            for item, score, base in zip(records, agreement, base_accept)
        ],
        "consumed_holdout_reused": False,
        "runtime_integrated": False,
        "ownership_authority": False,
        "model_output": str(output_model).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--legacy-queue", type=Path, required=True)
    parser.add_argument("--legacy-labels", type=Path, required=True)
    parser.add_argument("--legacy-probes", nargs="+", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.train_dataset, args.legacy_queue, args.legacy_labels,
                 args.legacy_probes, args.model_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
