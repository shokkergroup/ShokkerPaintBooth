"""Nested paint-disjoint completeness calibration over frozen exact-mask CLIP."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

try:
    from scripts.smart_tga_local_masked_patch_train import CONTROL_PAINTS, _load_data
    from scripts.smart_tga_clip_anchor_extension_train import _load_intrinsics
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_local_masked_patch_train import CONTROL_PAINTS, _load_data  # type: ignore
    from scripts.smart_tga_clip_anchor_extension_train import _load_intrinsics  # type: ignore


C_VALUES = (0.001, 0.01, 0.1, 1.0)
REPRESENTATIONS = ("appearance", "appearance_silhouette_equal")


def _normalize(values: np.ndarray) -> np.ndarray:
    return values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1e-8)


def _candidate_features(appearance: np.ndarray, silhouette: np.ndarray) -> dict[str, np.ndarray]:
    appearance_pooled = _normalize(appearance.mean(axis=1))
    silhouette_pooled = _normalize(silhouette.mean(axis=1))
    fused = _normalize(np.concatenate((appearance_pooled, silhouette_pooled), axis=1))
    return {
        "appearance": appearance_pooled.astype(np.float32),
        "appearance_silhouette_equal": fused.astype(np.float32),
    }


def _fit_probability(features: np.ndarray, truth: np.ndarray, c_value: float) -> LogisticRegression:
    model = LogisticRegression(
        C=c_value,
        class_weight="balanced",
        max_iter=2000,
        solver="liblinear",
        random_state=727,
    )
    model.fit(features, truth)
    return model


def _safe_threshold(truth: np.ndarray, probability: np.ndarray, stress: np.ndarray) -> float:
    choices = []
    for value in np.unique(probability):
        accepted = probability >= value
        if np.any(accepted & stress):
            continue
        precision = float(truth[accepted].mean()) if accepted.any() else 1.0
        if precision < 0.80:
            continue
        choices.append((
            int(np.count_nonzero(accepted & truth)),
            precision,
            -int(np.count_nonzero(accepted & ~truth)),
            -float(value),
        ))
    return -max(choices)[3] if choices else float(np.nextafter(probability.max(), np.inf))


def _inner_select(
    features: dict[str, np.ndarray],
    indices: np.ndarray,
    complete: np.ndarray,
    groups: np.ndarray,
    stress: np.ndarray,
) -> tuple[str, float, float, float]:
    explicit = indices[complete[indices] >= 0]
    unique_groups = np.unique(groups[explicit])
    splitter = GroupKFold(n_splits=min(4, len(unique_groups)))
    best = None
    for representation_index, representation in enumerate(REPRESENTATIONS):
        for c_index, c_value in enumerate(C_VALUES):
            probability = np.zeros(len(explicit), dtype=np.float64)
            for inner_train_offset, inner_test_offset in splitter.split(
                explicit, groups=groups[explicit],
            ):
                inner_train = explicit[inner_train_offset]
                inner_test = explicit[inner_test_offset]
                model = _fit_probability(
                    features[representation][inner_train],
                    complete[inner_train],
                    c_value,
                )
                probability[inner_test_offset] = model.predict_proba(
                    features[representation][inner_test],
                )[:, 1]
            ap = float(average_precision_score(complete[explicit], probability))
            candidate = (ap, -c_index, -representation_index, representation, c_value, probability, explicit)
            if best is None or candidate[:3] > best[:3]:
                best = candidate
    _, _, _, representation, c_value, inner_probability, explicit = best
    threshold = _safe_threshold(
        complete[explicit] == 1,
        inner_probability,
        stress[explicit],
    )
    return representation, c_value, float(best[0]), threshold


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--baseline-embeddings", type=Path, required=True)
    parser.add_argument("--clip-embeddings", type=Path, required=True)
    parser.add_argument("--family-ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=727)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    data = _load_data(args.bank, args.labels, args.baseline_embeddings, size=64)
    content_groups = _load_intrinsics(
        args.bank, args.labels, data["trace"],
    )["content_groups"]
    clip = np.load(args.clip_embeddings, allow_pickle=False)
    features = _candidate_features(
        clip["appearance"].astype(np.float32), clip["silhouette"].astype(np.float32),
    )
    family = json.loads(args.family_ledger.read_text(encoding="utf-8"))
    indices = np.arange(len(data["groups"]), dtype=np.int64)
    probability = np.zeros(len(indices), dtype=np.float64)
    accepted = np.zeros(len(indices), dtype=bool)
    fold_records = []
    for fold, (train, test) in enumerate(GroupKFold(n_splits=5).split(indices, groups=content_groups)):
        representation, c_value, inner_ap, threshold = _inner_select(
            features, train, data["complete"], content_groups, data["stress"],
        )
        explicit_train = train[data["complete"][train] >= 0]
        model = _fit_probability(
            features[representation][explicit_train],
            data["complete"][explicit_train],
            c_value,
        )
        fold_probability = model.predict_proba(features[representation][test])[:, 1]
        probability[test] = fold_probability
        accepted[test] = fold_probability >= threshold
        fold_records.append({
            "fold": fold,
            "test_paints": sorted(set(data["groups"][test])),
            "test_source_content_groups": len(set(content_groups[test])),
            "selected_representation": representation,
            "selected_c": c_value,
            "inner_oof_average_precision": round(inner_ap, 6),
            "inner_oof_safe_threshold": round(threshold, 8),
            "outer_accepted_count": int(np.count_nonzero(accepted[test])),
        })
    truth = data["complete"] == 1
    explicit = data["complete"] >= 0
    complete_ap = float(average_precision_score(truth, probability))
    explicit_ap = float(average_precision_score(truth[explicit], probability[explicit]))
    precision = float(truth[accepted].mean()) if accepted.any() else 1.0
    recall = float(np.count_nonzero(accepted & truth) / max(1, truth.sum()))
    false_positive = int(np.count_nonzero(accepted & ~truth))
    control_wrong = int(np.count_nonzero(accepted & data["stress"]))
    family_passed = bool(family["gates"]["representation_gate_passed"])
    complete_passed = complete_ap > 0.489735 and precision >= 0.80 and control_wrong == 0
    examples = [
        {
            **trace,
            "complete_number": bool(truth[index]),
            "explicit_label": bool(explicit[index]),
            "oof_probability": round(float(probability[index]), 7),
            "oof_accepted": bool(accepted[index]),
            "five_control_hard_negative": bool(data["stress"][index]),
        }
        for index, trace in enumerate(data["trace"])
    ]
    (args.output / "oof_examples.json").write_text(
        json.dumps(examples, indent=2) + "\n", encoding="utf-8",
    )
    targets = sorted(set(data["groups"]) - CONTROL_PAINTS)
    controls = sorted(set(data["groups"]) & CONTROL_PAINTS)
    ledger = {
        "schema": "smart-tga-frozen-clip-nested-completeness-v1",
        "cycle": args.cycle,
        "baseline": {
            "complete_number_average_precision": 0.489735,
            "frozen_efficientnet_operational_anchor_extension_ap": family["baseline"]["frozen_efficientnet_operational_anchor_extension_ap"],
        },
        "after_nested_paint_disjoint": {
            "frozen_clip_operational_anchor_extension_ap": family["after"]["best_operational_clip_ap"],
            "operational_ap_gain_over_efficientnet": family["after"]["best_clip_gain_over_efficientnet"],
            "complete_number_average_precision": round(complete_ap, 6),
            "explicit_only_average_precision": round(explicit_ap, 6),
            "accepted_count": int(np.count_nonzero(accepted)),
            "accepted_true_positive_count": int(np.count_nonzero(accepted & truth)),
            "accepted_false_positive_count": false_positive,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "five_control_hard_negative_count": int(np.count_nonzero(data["stress"])),
            "five_control_wrong_accepts": control_wrong,
        },
        "content_split_audit": {
            "paint_count": len(set(data["groups"])),
            "unique_source_content_count": len(set(content_groups)),
            "source_hash_used_as_model_feature": False,
        },
        "gates": {
            "family_representation_gate_passed": family_passed,
            "complete_gate_passed": complete_passed,
            "joint_development_gate_passed": family_passed and complete_passed,
            "untouched_holdout_opened": False,
            "runtime_integrated": False,
        },
        "targets": targets,
        "hard_negative_controls": controls,
        "folds": fold_records,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "clip_weights_frozen": True,
            "outer_and_inner_source_content_disjoint": True,
            "hyperparameters_selected_inside_outer_training_folds": True,
            "thresholds_selected_inside_outer_training_folds": True,
            "casts_votes": False,
            "ownership_authority": False,
            "apply_locked": True,
            "holdout_consumed": False,
            "filename_or_car_features": False,
            "reviewed_bbox_inference_feature": False,
            "exact_reconstruction_affected": False,
        },
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": ledger["baseline"],
        "after": ledger["after_nested_paint_disjoint"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
