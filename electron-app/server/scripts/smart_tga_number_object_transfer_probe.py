"""Extract pretrained visual object embeddings and paint-disjoint score them."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_object_transfer import isolated_object_views
    from scripts.smart_tga_number_object_segmentation_train import build_supervision
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_object_transfer import isolated_object_views  # type: ignore
    from scripts.smart_tga_number_object_segmentation_train import build_supervision  # type: ignore


def _extract(records):
    import torch
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
    weights = EfficientNet_B0_Weights.DEFAULT
    network = efficientnet_b0(weights=weights).eval()
    mean = torch.tensor([0.485, 0.456, 0.406])[None, :, None, None]
    std = torch.tensor([0.229, 0.224, 0.225])[None, :, None, None]
    objects = []
    for paint in records:
        rgb = cv2.resize(
            np.asarray(Image.open(paint.source_path).convert("RGB")),
            (256, 256), interpolation=cv2.INTER_AREA,
        )
        for component in paint.components:
            objects.append((paint, component, isolated_object_views(rgb, component["mask"])))
    embeddings = []
    with torch.no_grad():
        for start in range(0, len(objects), 8):
            chunk = objects[start:start + 8]
            tensor = torch.from_numpy(np.concatenate([item[2] for item in chunk]))
            tensor = (tensor - mean) / std
            feature = network.features(tensor)
            feature = network.avgpool(feature).flatten(1).numpy()
            feature = feature.reshape(len(chunk), 2, 8, -1).mean(axis=2)
            feature /= np.linalg.norm(feature, axis=2, keepdims=True).clip(1e-8)
            embeddings.extend(feature.reshape(len(chunk), -1))
    metadata = [{
        "cycle": paint.cycle, "paint_label": paint.paint_label,
        "source_layer": str(component["layer"]),
        "component_index": int(component["component_index"]),
        "is_number": bool(component["is_number"]), "class": component["class"],
        "label": component["label"],
    } for paint, component, _views in objects]
    return metadata, np.asarray(embeddings, np.float32), weights.url


def _probabilities(matrix, truth, groups, c_value):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    output = np.zeros(len(truth), np.float32)
    for train, test in GroupKFold(min(8, len(set(groups)))).split(matrix, truth, groups):
        model = LogisticRegression(C=c_value, class_weight="balanced", max_iter=4000, random_state=711)
        model.fit(matrix[train], truth[train])
        output[test] = model.predict_proba(matrix[test])[:, 1]
    return output


def _summary(metadata, probabilities, threshold):
    truth = np.asarray([item["is_number"] for item in metadata], bool)
    accepted = probabilities >= threshold
    true_positive = int(np.count_nonzero(accepted & truth))
    false_positive = int(np.count_nonzero(accepted & ~truth))
    positive_paints = {item["paint_label"] for item in metadata if item["is_number"]}
    hit_paints = {
        item["paint_label"] for item, keep in zip(metadata, accepted)
        if item["is_number"] and keep
    }
    return {
        "paint_number_coverage": f"{len(hit_paints)}/{len(positive_paints)}",
        "number_component_hits": f"{true_positive}/{int(np.count_nonzero(truth))}",
        "accepted_controls": false_positive,
        "component_precision": round(true_positive / max(1, true_positive + false_positive), 6),
        "component_recall": round(true_positive / max(1, int(np.count_nonzero(truth))), 6),
    }


def run(labels_dir: Path, output_dir: Path, cycles=None):
    cycles = list(cycles if cycles is not None else list(range(681, 691)) + [693, 695])
    records, _manifest = build_supervision(labels_dir, cycles)
    metadata, matrix, weight_url = _extract(records)
    truth = np.asarray([item["is_number"] for item in metadata], bool)
    groups = np.asarray([item["paint_label"] for item in metadata], object)
    candidates = []
    for c_value in (0.003, 0.01, 0.03, 0.1, 0.3, 1.0):
        probability = _probabilities(matrix, truth, groups, c_value)
        for threshold in sorted(set(float(value) for value in probability), reverse=True):
            summary = _summary(metadata, probability, threshold)
            if summary["component_precision"] >= 0.95:
                hits = int(summary["number_component_hits"].split("/")[0])
                candidates.append((hits, -summary["accepted_controls"], -c_value, threshold, c_value, probability, summary))
    if not candidates:
        raise AssertionError("no transfer operating point meets 95% precision")
    _hits, _controls, _c_order, threshold, c_value, probability, summary = max(candidates, key=lambda item: item[:3])
    control_max = float(np.max(probability[~truth]))
    zero_threshold = min(1.0, control_max + 1e-6)
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_dir / "efficientnet_b0_d4_embeddings.npz", embeddings=matrix,
        cycles=np.asarray([item["cycle"] for item in metadata]),
        paint_labels=np.asarray([item["paint_label"] for item in metadata]),
        source_layers=np.asarray([item["source_layer"] for item in metadata]),
        component_indexes=np.asarray([item["component_index"] for item in metadata]),
        labels=truth,
    )
    payload = {
        "schema": "smart-tga-number-object-transfer-probe-v1",
        "teacher": "torchvision EfficientNet-B0 DEFAULT; frozen ImageNet weights",
        "weight_url": weight_url, "embedding_dimensions": int(matrix.shape[1]),
        "validation": "8-fold paint-disjoint cross-fit; D4-averaged masked appearance plus silhouette",
        "paint_count": len(set(groups)), "component_count": len(metadata),
        "precision_floor": {"c": c_value, "threshold": threshold, **summary},
        "zero_control": {"threshold": zero_threshold, **_summary(metadata, probability, zero_threshold)},
        "scores": [{**item, "probability": round(float(score), 6), "accepted": bool(score >= threshold)}
                   for item, score in zip(metadata, probability)],
        "runtime_integrated": False, "ownership_authority": False,
    }
    (output_dir / "transfer_probe.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cycles", nargs="+", type=int, default=list(range(681, 691)) + [693, 695])
    args = parser.parse_args()
    result = run(args.labels_dir, args.output_dir, args.cycles)
    print(json.dumps({key: value for key, value in result.items() if key != "scores"}, indent=2))


if __name__ == "__main__":
    main()
