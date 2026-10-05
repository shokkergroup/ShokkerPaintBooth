"""Train on durable DLM component reviews and score a paint-disjoint cycle."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_context_component_features import FEATURE_NAMES, component_feature_vector
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates
    from engine.spec_sculpt.number_context_family_similarity import d4_cosine_similarity, prototype_margin
    from scripts.smart_tga_number_context_conformal_probe import _score
    from scripts.smart_tga_number_context_family_probe import _descriptor
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_component_features import FEATURE_NAMES, component_feature_vector  # type: ignore
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates  # type: ignore
    from engine.spec_sculpt.number_context_family_similarity import d4_cosine_similarity, prototype_margin  # type: ignore
    from scripts.smart_tga_number_context_conformal_probe import _score  # type: ignore
    from scripts.smart_tga_number_context_family_probe import _descriptor  # type: ignore


MASK_NAMES = ("raw_instance_union", "seed_palette", "border_contrast", "hybrid_evidence", "seeded_graphcut")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _cycle(path: Path) -> int:
    match = re.match(r"cycle(\d{3})_", path.name)
    if not match:
        raise ValueError(f"unrecognized review label: {path.name}")
    return int(match.group(1))


def _source_path(root: Path, review: dict) -> Path:
    run = root / Path(str(review["inspection_records"]).replace("/", "\\")).parent
    slug = review["paint_label"].replace("/", "_").replace(" ", "_").removesuffix(".tga")
    source = run / slug / "source_1024.png"
    if not source.exists():
        raise FileNotFoundError(source)
    return source


def _paint_records(root: Path, label_path: Path, prototypes, prototype_labels, pixel_models) -> list[dict]:
    review = _read(label_path)
    source = _source_path(root, review)
    parent = source.parent
    rgb = np.asarray(Image.open(source).convert("RGB"))
    components = _read(parent / "component_records.json")
    layer_masks = {
        path.stem: np.asarray(Image.open(path).convert("L")) > 0
        for path in (parent / "masks").glob("*.png")
    }
    labels = {
        (item["layer"], int(item["component_index"])): item
        for item in review["component_labels"]
    }
    proposals = component_proposal_candidates(rgb.shape[:2], layer_masks, components, min_pixels=400)
    prepared = []
    for proposal in proposals:
        raw = proposal["raw_support"]
        record = {
            "paint_label": review["paint_label"], "proposal_id": proposal["proposal_id"],
            "proposal_bbox": proposal["proposal_bbox"], "rgb": rgb,
            "hypotheses": {name: raw for name in MASK_NAMES},
        }
        prepared.append((proposal, record, _descriptor(record)))
    result = []
    for proposal, record, descriptor in prepared:
        provenance = proposal["provenance"]
        key = (provenance["source_layer"], provenance["component_index"])
        if key not in labels:
            continue
        item = labels[key]
        raw = proposal["raw_support"]
        margin = prototype_margin(descriptor, prototypes[prototype_labels], prototypes[~prototype_labels])
        pixel_score = np.mean([_score(model, record) for model in pixel_models], axis=0)
        area = int(provenance["component_pixels"])
        peers = []
        for other, _other_record, other_descriptor in prepared:
            if other["proposal_id"] == proposal["proposal_id"]:
                continue
            other_area = int(other["provenance"]["component_pixels"])
            difference = abs(float(np.log(max(1, area) / max(1, other_area))))
            if difference <= 1.05:
                peers.append((d4_cosine_similarity(descriptor, other_descriptor), difference))
        peer_similarity, peer_difference = max(peers, default=(0.0, 8.0), key=lambda pair: pair[0])
        peer_count = sum(similarity >= 0.82 for similarity, _difference in peers)
        is_number = str(item.get("target_layer")) == "numbers"
        result.append({
            "cycle": _cycle(label_path), "paint_label": review["paint_label"],
            "proposal_id": proposal["proposal_id"], "review_label": item["label"],
            "source_layer": str(provenance["source_layer"]),
            "component_index": int(provenance["component_index"]),
            "is_number": is_number, "family_margin": float(margin),
            "area_fraction": area / float(rgb.shape[0] * rgb.shape[1]),
            "vector": component_feature_vector(
                rgb, proposal["proposal_bbox"], raw, family_margin=float(margin),
                pixel_score=pixel_score, peer_similarity=float(peer_similarity),
                peer_count=peer_count, peer_area_log_difference=float(peer_difference),
            ),
        })
    missing = sorted(set(labels) - {
        (proposal["provenance"]["source_layer"], proposal["provenance"]["component_index"])
        for proposal, _record, _descriptor_value in prepared
    })
    # Tiny reviewed fragments below the adapter's 400px contract are intentionally absent.
    # A few historically reviewed paints contain only sub-400px fragments.
    # They correctly contribute no records to this adapter-specific corpus.
    return result


def _summary(records, accepted) -> dict:
    number_paints = {item["paint_label"] for item in records if item["is_number"]}
    hit_paints = {item["paint_label"] for item, keep in zip(records, accepted) if keep and item["is_number"]}
    tp = sum(bool(keep) and item["is_number"] for item, keep in zip(records, accepted))
    fp = sum(bool(keep) and not item["is_number"] for item, keep in zip(records, accepted))
    positives = sum(item["is_number"] for item in records)
    return {
        "paint_number_coverage": f"{len(hit_paints)}/{len(number_paints)}",
        "number_record_hits": f"{tp}/{positives}", "accepted_controls": fp,
        "component_precision": round(tp / max(1, tp + fp), 6),
        "component_recall": round(tp / max(1, positives), 6),
    }


def _cross_fitted_probabilities(matrix, truth, groups, c_value):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler
    probabilities = np.zeros(len(truth), np.float32)
    folds = min(8, len(set(groups)))
    for train, test in GroupKFold(folds).split(matrix, truth, groups):
        scaler = StandardScaler().fit(matrix[train])
        model = LogisticRegression(C=c_value, class_weight="balanced", max_iter=4000, random_state=708)
        model.fit(scaler.transform(matrix[train]), truth[train])
        probabilities[test] = model.predict_proba(scaler.transform(matrix[test]))[:, 1]
    return probabilities


def run(root: Path, label_root: Path, family_model: Path, pixel_model: Path, old_model: Path,
        train_min: int, train_max: int, holdout_cycle: int, model_output: Path) -> dict:
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    family = np.load(family_model)
    prototypes = np.asarray(family["descriptors"], np.float32)
    prototype_labels = np.asarray(family["labels"], bool)
    pixel_models = joblib.load(pixel_model)["pixel_ensemble"]
    paths = sorted(label_root.glob("cycle*_numbers_v1.json"))
    selected = [path for path in paths if train_min <= _cycle(path) <= holdout_cycle]
    records = []
    for path in selected:
        records.extend(_paint_records(root, path, prototypes, prototype_labels, pixel_models))
    train = [item for item in records if train_min <= item["cycle"] <= train_max]
    holdout = [item for item in records if item["cycle"] == holdout_cycle]
    if not train or not holdout:
        raise AssertionError("train and holdout records are required")
    matrix = np.asarray([item["vector"] for item in train], np.float32)
    truth = np.asarray([item["is_number"] for item in train], bool)
    groups = np.asarray([item["paint_label"] for item in train], object)
    candidates = []
    minimum_training_precision = 0.95
    for c_value in (0.03, 0.10, 0.35, 1.0):
        probability = _cross_fitted_probabilities(matrix, truth, groups, c_value)
        operating_points = []
        for threshold in sorted(set(float(value) for value in probability), reverse=True):
            accepted = probability >= threshold
            summary = _summary(train, accepted)
            if summary["component_precision"] >= minimum_training_precision:
                hits = int(summary["number_record_hits"].split("/")[0])
                operating_points.append((hits, -summary["accepted_controls"], threshold, summary))
        if not operating_points:
            continue
        hits, negative_controls, threshold, summary = max(operating_points)
        candidates.append((hits, negative_controls, c_value, threshold, probability, summary))
    if not candidates:
        raise AssertionError("no cross-fitted operating point satisfies the precision floor")
    _hits, _negative_controls, c_value, threshold, oof_probability, oof_summary = max(
        candidates, key=lambda item: (item[0], item[1], -item[2])
    )
    scaler = StandardScaler().fit(matrix)
    model = LogisticRegression(C=c_value, class_weight="balanced", max_iter=4000, random_state=708)
    model.fit(scaler.transform(matrix), truth)
    holdout_matrix = np.asarray([item["vector"] for item in holdout], np.float32)
    holdout_probability = model.predict_proba(scaler.transform(holdout_matrix))[:, 1]
    holdout_accept = holdout_probability >= threshold
    old = np.load(old_model)
    area_gate, margin_gate = float(old["minimum_area_fraction"][0]), float(old["minimum_family_margin"][0])
    old_holdout_accept = np.asarray([
        item["area_fraction"] >= area_gate and item["family_margin"] >= margin_gate for item in holdout
    ], bool)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_output, feature_names=np.asarray(FEATURE_NAMES), mean=scaler.mean_.astype(np.float32),
        scale=scaler.scale_.astype(np.float32), coefficient=model.coef_[0].astype(np.float32),
        intercept=np.asarray([model.intercept_[0]], np.float32), threshold=np.asarray([threshold], np.float32),
    )
    return {
        "schema": "smart-tga-number-context-component-corpus-probe-v1",
        "train_cycles": f"{train_min}-{train_max}", "holdout_cycle": holdout_cycle,
        "train_paints": len({item["paint_label"] for item in train}), "train_records": len(train),
        "holdout_paints": len({item["paint_label"] for item in holdout}), "holdout_records": len(holdout),
        "selected_c": c_value, "cross_fitted_minimum_precision": minimum_training_precision,
        "cross_fitted_threshold": threshold,
        "cross_fitted_train": oof_summary,
        "paint_disjoint_holdout_baseline_cycle707_gate": _summary(holdout, old_holdout_accept),
        "paint_disjoint_holdout_trained_scorer": _summary(holdout, holdout_accept),
        "holdout_scores": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "review_label": item["review_label"], "is_number": item["is_number"],
             "probability": round(float(score), 6), "accepted": bool(keep)}
            for item, score, keep in zip(holdout, holdout_probability, holdout_accept)
        ],
        "model_output": str(model_output).replace("\\", "/"),
        "runtime_integrated": False, "ownership_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--label-root", type=Path, required=True)
    parser.add_argument("--family-model", type=Path, required=True)
    parser.add_argument("--pixel-model", type=Path, required=True)
    parser.add_argument("--old-component-model", type=Path, required=True)
    parser.add_argument("--train-min", type=int, default=680)
    parser.add_argument("--train-max", type=int, default=689)
    parser.add_argument("--holdout-cycle", type=int, default=690)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.label_root, args.family_model, args.pixel_model, args.old_component_model,
                 args.train_min, args.train_max, args.holdout_cycle, args.model_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
