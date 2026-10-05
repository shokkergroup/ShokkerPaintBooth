"""Evaluate frozen number-object scorers on reviewed, paint-disjoint holdout labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from engine.spec_sculpt.number_object_segmentation import build_tiny_unet, image_feature_tensor
    from scripts.smart_tga_number_context_component_corpus_probe import _cycle, _paint_records, _summary
    from scripts.smart_tga_number_object_active_pool import _foundation_probability, _linear_probability
    from scripts.smart_tga_number_object_segmentation_train import _component_score, build_supervision
    from scripts.smart_tga_number_object_transfer_probe import _extract
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_object_segmentation import build_tiny_unet, image_feature_tensor  # type: ignore
    from scripts.smart_tga_number_context_component_corpus_probe import _cycle, _paint_records, _summary  # type: ignore
    from scripts.smart_tga_number_object_active_pool import _foundation_probability, _linear_probability  # type: ignore
    from scripts.smart_tga_number_object_segmentation_train import _component_score, build_supervision  # type: ignore
    from scripts.smart_tga_number_object_transfer_probe import _extract  # type: ignore


def _identity(paint, layer, index):
    return str(paint), str(layer), int(index)


def run(label_root: Path, cycles, segment_model: Path, baseline_model: Path, foundation_model: Path, output: Path):
    # Load sklearn/pandas native extensions before Torch/OpenMP on Windows.
    import sklearn  # noqa: F401
    import joblib

    model_root = Path("engine/spec_sculpt/models")
    family = np.load(model_root / "smart_tga_number_context_family_cycle704_v1.npz")
    prototypes = np.asarray(family["descriptors"], np.float32)
    prototype_labels = np.asarray(family["labels"], bool)
    pixel_models = joblib.load(model_root / "smart_tga_number_context_conformal_cycle703_v1.joblib")["pixel_ensemble"]
    import torch

    selected_cycles = set(map(int, cycles))
    label_paths = [
        path for path in sorted(label_root.glob("cycle*_numbers_v1.json"))
        if _cycle(path) in selected_cycles
    ]
    records = []
    for path in label_paths:
        records.extend(_paint_records(Path.cwd(), path, prototypes, prototype_labels, pixel_models))

    supervision, manifest = build_supervision(label_root, selected_cycles)
    transfer_metadata, embeddings, weight_url = _extract(supervision)
    embedding_map = {
        _identity(item["paint_label"], item["source_layer"], item["component_index"]): vector
        for item, vector in zip(transfer_metadata, embeddings)
    }

    blob = torch.load(segment_model, map_location="cpu", weights_only=True)
    segmenter = build_tiny_unet(int(blob["base_channels"]))
    segmenter.load_state_dict(blob["state_dict"])
    segmenter.eval()
    segment_scores = {}
    with torch.no_grad():
        for paint in supervision:
            from PIL import Image
            rgb = np.asarray(Image.open(paint.source_path).convert("RGB"))
            probability = torch.sigmoid(segmenter(torch.from_numpy(image_feature_tensor(rgb)[None])))[0, 0].numpy()
            for component in paint.components:
                segment_scores[_identity(paint.paint_label, component["layer"], component["component_index"])] = _component_score(
                    probability, component["mask"],
                )

    baseline = np.load(baseline_model)
    foundation = np.load(foundation_model)
    scores = []
    baseline_accept = []
    foundation_accept = []
    for item in records:
        key = _identity(item["paint_label"], item["source_layer"], item["component_index"])
        segment_score = segment_scores[key]
        base = np.concatenate((item["vector"], np.asarray([segment_score], np.float32)))
        old_probability = _linear_probability(baseline, base)
        new_probability = _foundation_probability(foundation, base, embedding_map[key])
        old_keep = old_probability >= float(baseline["threshold"][0])
        new_keep = new_probability >= float(foundation["threshold"][0])
        baseline_accept.append(old_keep)
        foundation_accept.append(new_keep)
        scores.append({
            "paint_label": item["paint_label"], "source_layer": item["source_layer"],
            "component_index": item["component_index"], "review_label": item["review_label"],
            "is_number": item["is_number"], "baseline_probability": round(old_probability, 6),
            "foundation_probability": round(new_probability, 6),
            "baseline_accepted": old_keep, "foundation_accepted": new_keep,
        })

    missed = []
    for path in sorted(label_root.glob("cycle*_missed_number_instances_v1.json")):
        if _cycle(path) in selected_cycles:
            missed.extend(json.loads(path.read_text(encoding="utf-8")).get("instances", []))
    payload = {
        "schema": "smart-tga-number-object-fresh-holdout-eval-v1",
        "validation": "frozen models and thresholds; labels from paints absent from fitting and threshold selection",
        "proposal_identity": "paint_label + source_layer + component_index",
        "cycles": sorted(selected_cycles), "paint_count": len(supervision),
        "reviewed_components": len(records), "missing_raw_number_instances": len(missed),
        "baseline": {"threshold": float(baseline["threshold"][0]), **_summary(records, np.asarray(baseline_accept, bool))},
        "foundation": {"threshold": float(foundation["threshold"][0]), **_summary(records, np.asarray(foundation_accept, bool))},
        "scores": scores, "missed_instances": missed, "teacher_weight_url": weight_url,
        "casts_votes": False, "ownership_authority": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label-root", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--cycles", nargs="+", type=int, required=True)
    parser.add_argument("--segment-model", type=Path, required=True)
    parser.add_argument("--baseline-model", type=Path, required=True)
    parser.add_argument("--foundation-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.label_root, args.cycles, args.segment_model, args.baseline_model, args.foundation_model, args.output)
    print(json.dumps({key: value for key, value in result.items() if key not in {"scores", "missed_instances"}}, indent=2))


if __name__ == "__main__":
    main()
