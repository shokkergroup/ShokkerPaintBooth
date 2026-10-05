"""Train and paint-group validate the intrinsic DLM component scorer."""

from __future__ import annotations

import argparse
import json
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


def _records(queue_path: Path, review_path: Path, prototypes: np.ndarray, labels: np.ndarray, pixel_models) -> list[dict]:
    queue, review = _read(queue_path), _read(review_path)
    reviewed = {
        (item["paint_label"], item["layer"], int(item["component_index"])): item["class"]
        for item in review["records"]
    }
    records = []
    for paint in queue["selected_paints"]:
        paint_label = paint["paint_label"]
        source = Path(paint["source_1024"])
        parent = source.parent
        rgb = np.asarray(Image.open(source).convert("RGB"))
        components = _read(parent / "component_records.json")
        layer_masks = {
            path.stem: np.asarray(Image.open(path).convert("L")) > 0
            for path in (parent / "masks").glob("*.png")
        }
        proposals = component_proposal_candidates(rgb.shape[:2], layer_masks, components, min_pixels=400)
        proposal_records = []
        for proposal in proposals:
            raw = proposal["raw_support"]
            base_record = {
                "paint_label": paint_label,
                "proposal_id": proposal["proposal_id"],
                "proposal_bbox": proposal["proposal_bbox"],
                "rgb": rgb,
                "hypotheses": {name: raw for name in MASK_NAMES},
            }
            proposal_records.append((proposal, base_record, _descriptor(base_record)))
        for proposal, record, descriptor in proposal_records:
            provenance = proposal["provenance"]
            key = (paint_label, provenance["source_layer"], provenance["component_index"])
            if key not in reviewed:
                continue
            raw = proposal["raw_support"]
            pixel_score = np.mean([_score(model, record) for model in pixel_models], axis=0)
            margin = prototype_margin(descriptor, prototypes[labels], prototypes[~labels])
            area = int(provenance["component_pixels"])
            peers = []
            for other_proposal, _other_record, other_descriptor in proposal_records:
                if other_proposal["proposal_id"] == proposal["proposal_id"]:
                    continue
                other_area = int(other_proposal["provenance"]["component_pixels"])
                log_difference = abs(float(np.log(max(1, area) / max(1, other_area))))
                if log_difference > 1.05:
                    continue
                peers.append((d4_cosine_similarity(descriptor, other_descriptor), log_difference))
            peer_similarity, peer_area_difference = max(peers, default=(0.0, 8.0), key=lambda item: item[0])
            peer_count = sum(similarity >= 0.82 for similarity, _difference in peers)
            records.append({
                "paint_label": paint_label,
                "proposal_id": proposal["proposal_id"],
                "review_class": reviewed[key],
                "is_number": reviewed[key] == "Number",
                "family_margin": float(margin),
                "area_fraction": provenance["component_pixels"] / float(rgb.shape[0] * rgb.shape[1]),
                "vector": component_feature_vector(
                    rgb, proposal["proposal_bbox"], raw,
                    family_margin=float(margin), pixel_score=pixel_score,
                    peer_similarity=float(peer_similarity), peer_count=peer_count,
                    peer_area_log_difference=float(peer_area_difference),
                ),
            })
    if len(records) != len(reviewed):
        raise AssertionError(f"expected {len(reviewed)} reviewed components, found {len(records)}")
    return records


def _summary(records, accepted) -> dict:
    number_paints = {item["paint_label"] for item in records if item["is_number"]}
    accepted_number_paints = {
        item["paint_label"] for item, keep in zip(records, accepted) if keep and item["is_number"]
    }
    true_positive = sum(bool(keep) and item["is_number"] for item, keep in zip(records, accepted))
    false_positive = sum(bool(keep) and not item["is_number"] for item, keep in zip(records, accepted))
    positives = sum(item["is_number"] for item in records)
    return {
        "paint_number_coverage": f"{len(accepted_number_paints)}/{len(number_paints)}",
        "number_record_hits": f"{true_positive}/{positives}",
        "accepted_controls": false_positive,
        "component_precision": round(true_positive / max(1, true_positive + false_positive), 6),
        "component_recall": round(true_positive / max(1, positives), 6),
    }


def run(queue_reviews, family_model: Path, pixel_model: Path, old_component_model: Path, model_output: Path) -> dict:
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import LeaveOneGroupOut
    from sklearn.preprocessing import StandardScaler

    family = np.load(family_model)
    prototypes = np.asarray(family["descriptors"], np.float32)
    labels = np.asarray(family["labels"], bool)
    pixel_models = joblib.load(pixel_model)["pixel_ensemble"]
    records = []
    for queue, review in queue_reviews:
        records.extend(_records(queue, review, prototypes, labels, pixel_models))
    matrix = np.asarray([item["vector"] for item in records], np.float32)
    truth = np.asarray([item["is_number"] for item in records], bool)
    groups = np.asarray([item["paint_label"] for item in records], object)
    probabilities = np.zeros(len(records), np.float32)
    for train, test in LeaveOneGroupOut().split(matrix, truth, groups):
        scaler = StandardScaler().fit(matrix[train])
        model = LogisticRegression(C=0.35, class_weight="balanced", max_iter=4000, random_state=708)
        model.fit(scaler.transform(matrix[train]), truth[train])
        probabilities[test] = model.predict_proba(scaler.transform(matrix[test]))[:, 1]
    control_max = float(np.max(probabilities[~truth]))
    threshold = min(1.0, control_max + 1e-7)
    learned_accept = probabilities >= threshold

    old = np.load(old_component_model)
    area_gate = float(old["minimum_area_fraction"][0])
    margin_gate = float(old["minimum_family_margin"][0])
    old_accept = np.asarray([
        item["area_fraction"] >= area_gate and item["family_margin"] >= margin_gate for item in records
    ], bool)

    scaler = StandardScaler().fit(matrix)
    model = LogisticRegression(C=0.35, class_weight="balanced", max_iter=4000, random_state=708)
    model.fit(scaler.transform(matrix), truth)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_output,
        feature_names=np.asarray(FEATURE_NAMES), mean=scaler.mean_.astype(np.float32),
        scale=scaler.scale_.astype(np.float32), coefficient=model.coef_[0].astype(np.float32),
        intercept=np.asarray([model.intercept_[0]], np.float32), threshold=np.asarray([threshold], np.float32),
    )
    return {
        "schema": "smart-tga-number-context-component-train-probe-v1",
        "train_paints": len(set(groups)), "reviewed_records": len(records),
        "number_records": int(np.count_nonzero(truth)), "control_records": int(np.count_nonzero(~truth)),
        "validation": "leave-one-paint-out; every score comes from a model that did not see that paint",
        "baseline_frozen_cycle707_gate": _summary(records, old_accept),
        "cross_fitted_intrinsic_scorer": _summary(records, learned_accept),
        "cross_fitted_zero_control_threshold": threshold,
        "cross_fitted_control_probability_max": control_max,
        "scores": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "review_class": item["review_class"], "probability": round(float(score), 6),
             "accepted": bool(keep)}
            for item, score, keep in zip(records, probabilities, learned_accept)
        ],
        "model_output": str(model_output).replace("\\", "/"),
        "runtime_integrated": False, "ownership_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-review", nargs=2, action="append", metavar=("QUEUE", "REVIEW"), required=True)
    parser.add_argument("--family-model", type=Path, required=True)
    parser.add_argument("--pixel-model", type=Path, required=True)
    parser.add_argument("--old-component-model", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        [(Path(queue), Path(review)) for queue, review in args.queue_review],
        args.family_model, args.pixel_model, args.old_component_model, args.model_output,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
