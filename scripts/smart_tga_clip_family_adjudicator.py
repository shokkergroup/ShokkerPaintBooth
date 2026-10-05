"""Train a constrained CLIP family-link scorer with zero ownership authority."""
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
    from scripts.smart_tga_local_masked_patch_train import (
        CONTROL_PAINTS,
        _load_data,
        _orbit_scores,
        _pair_sets,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_local_masked_patch_train import (  # type: ignore
        CONTROL_PAINTS,
        _load_data,
        _orbit_scores,
        _pair_sets,
    )


PAIR_POSITIVE = 1
PAIR_CROSS_PAINT_NUMBER = 2
PAIR_WITHIN_PAINT_NONNUMBER = 3


def _features_for_pairs(
    pairs: np.ndarray,
    appearance: np.ndarray,
    silhouette: np.ndarray,
    efficientnet: np.ndarray,
) -> np.ndarray:
    if not len(pairs):
        return np.empty((0, 3), dtype=np.float32)
    return np.column_stack((
        _orbit_scores(appearance, pairs),
        _orbit_scores(silhouette, pairs),
        _orbit_scores(efficientnet, pairs),
    )).astype(np.float32)


def _pair_dataset(indices, data, appearance, silhouette):
    positive, family_negative, semantic_negative = _pair_sets(indices, data, local=False)
    pairs = np.concatenate((positive, family_negative, semantic_negative), axis=0)
    truth = np.concatenate((
        np.ones(len(positive), dtype=bool),
        np.zeros(len(family_negative) + len(semantic_negative), dtype=bool),
    ))
    kind = np.concatenate((
        np.full(len(positive), PAIR_POSITIVE, dtype=np.int8),
        np.full(len(family_negative), PAIR_CROSS_PAINT_NUMBER, dtype=np.int8),
        np.full(len(semantic_negative), PAIR_WITHIN_PAINT_NONNUMBER, dtype=np.int8),
    ))
    features = _features_for_pairs(
        pairs, appearance, silhouette, data["baseline_views"],
    )
    return pairs, features, truth, kind


def _fit(features: np.ndarray, truth: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        solver="liblinear",
        random_state=727,
    )
    model.fit(features, truth)
    return model


def _zero_error_threshold(truth: np.ndarray, probability: np.ndarray) -> float:
    choices = []
    for value in np.unique(probability):
        accepted = probability >= value
        false_positive = int(np.count_nonzero(accepted & ~truth))
        if false_positive:
            continue
        choices.append((int(np.count_nonzero(accepted & truth)), -float(value)))
    return -max(choices)[1] if choices else float(np.nextafter(probability.max(), np.inf))


def _inner_threshold(train_indices, data, appearance, silhouette) -> tuple[float, float]:
    train_indices = np.asarray(train_indices, dtype=np.int64)
    groups = data["groups"][train_indices]
    probability, truth = [], []
    for inner_train_offset, inner_test_offset in GroupKFold(
        n_splits=min(4, len(np.unique(groups))),
    ).split(train_indices, groups=groups):
        inner_train = train_indices[inner_train_offset]
        inner_test = train_indices[inner_test_offset]
        _, train_features, train_truth, _ = _pair_dataset(
            inner_train, data, appearance, silhouette,
        )
        _, test_features, test_truth, _ = _pair_dataset(
            inner_test, data, appearance, silhouette,
        )
        model = _fit(train_features, train_truth)
        probability.extend(model.predict_proba(test_features)[:, 1].tolist())
        truth.extend(test_truth.tolist())
    probability = np.asarray(probability, dtype=np.float64)
    truth = np.asarray(truth, dtype=bool)
    return _zero_error_threshold(truth, probability), float(average_precision_score(truth, probability))


def _subset_ap(truth, probability, kind, allowed) -> float:
    selected = np.isin(kind, allowed)
    return float(average_precision_score(truth[selected], probability[selected]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--baseline-embeddings", type=Path, required=True)
    parser.add_argument("--clip-embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=727)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    data = _load_data(args.bank, args.labels, args.baseline_embeddings, size=64)
    clip = np.load(args.clip_embeddings, allow_pickle=False)
    appearance = clip["appearance"].astype(np.float32)
    silhouette = clip["silhouette"].astype(np.float32)
    indices = np.arange(len(data["groups"]), dtype=np.int64)
    all_probability, all_raw, all_truth, all_kind, all_pairs = [], [], [], [], []
    all_accepted, all_raw_accepted = [], []
    folds = []
    for fold, (train, test) in enumerate(GroupKFold(n_splits=5).split(indices, groups=data["groups"])):
        threshold, inner_ap = _inner_threshold(train, data, appearance, silhouette)
        _, train_features, train_truth, _ = _pair_dataset(train, data, appearance, silhouette)
        test_pairs, test_features, test_truth, test_kind = _pair_dataset(
            test, data, appearance, silhouette,
        )
        model = _fit(train_features, train_truth)
        probability = model.predict_proba(test_features)[:, 1]
        accepted = probability >= threshold
        raw_threshold = _zero_error_threshold(train_truth, train_features[:, 0])
        raw_accepted = test_features[:, 0] >= raw_threshold
        all_probability.extend(probability.tolist())
        all_raw.extend(test_features[:, 0].tolist())
        all_truth.extend(test_truth.tolist())
        all_kind.extend(test_kind.tolist())
        all_pairs.extend(test_pairs.tolist())
        all_accepted.extend(accepted.tolist())
        all_raw_accepted.extend(raw_accepted.tolist())
        folds.append({
            "fold": fold,
            "test_paints": sorted(set(data["groups"][test])),
            "inner_oof_combined_ap": round(inner_ap, 6),
            "zero_error_inner_threshold": round(threshold, 8),
            "frozen_clip_zero_error_train_threshold": round(raw_threshold, 8),
            "test_pair_count": len(test_truth),
            "test_accepted_count": int(np.count_nonzero(accepted)),
            "frozen_clip_test_accepted_count": int(np.count_nonzero(raw_accepted)),
        })
    probability = np.asarray(all_probability)
    raw = np.asarray(all_raw)
    truth = np.asarray(all_truth, dtype=bool)
    kind = np.asarray(all_kind, dtype=np.int8)
    pairs = np.asarray(all_pairs, dtype=np.int64)
    accepted = np.asarray(all_accepted, dtype=bool)
    raw_accepted = np.asarray(all_raw_accepted, dtype=bool)
    family_kinds = (PAIR_POSITIVE, PAIR_CROSS_PAINT_NUMBER)
    operational_kinds = (PAIR_POSITIVE, PAIR_WITHIN_PAINT_NONNUMBER)
    raw_metrics = {
        "combined_ap": float(average_precision_score(truth, raw)),
        "family_ap": _subset_ap(truth, raw, kind, family_kinds),
        "operational_anchor_extension_ap": _subset_ap(truth, raw, kind, operational_kinds),
    }
    after_metrics = {
        "combined_ap": float(average_precision_score(truth, probability)),
        "family_ap": _subset_ap(truth, probability, kind, family_kinds),
        "operational_anchor_extension_ap": _subset_ap(truth, probability, kind, operational_kinds),
    }
    precision = float(truth[accepted].mean()) if accepted.any() else 1.0
    recall = float(np.count_nonzero(accepted & truth) / max(1, np.count_nonzero(truth)))
    negative_accepted = accepted & ~truth
    control_pair = np.asarray([
        data["groups"][first] in CONTROL_PAINTS or data["groups"][second] in CONTROL_PAINTS
        for first, second in pairs
    ])
    control_wrong = int(np.count_nonzero(negative_accepted & control_pair))
    raw_negative_accepted = raw_accepted & ~truth
    raw_precision = float(truth[raw_accepted].mean()) if raw_accepted.any() else 1.0
    raw_recall = float(np.count_nonzero(raw_accepted & truth) / max(1, np.count_nonzero(truth)))
    raw_control_wrong = int(np.count_nonzero(raw_negative_accepted & control_pair))
    raw_link_gate = bool(
        raw_precision >= 0.90
        and raw_control_wrong == 0
        and np.any(raw_accepted & truth)
    )
    gate = (
        after_metrics["combined_ap"] > raw_metrics["combined_ap"]
        and after_metrics["family_ap"] >= raw_metrics["family_ap"] - 0.02
        and after_metrics["operational_anchor_extension_ap"] > raw_metrics["operational_anchor_extension_ap"]
        and precision >= 0.90
        and control_wrong == 0
    )
    ledger = {
        "schema": "smart-tga-constrained-clip-family-link-v1",
        "cycle": args.cycle,
        "contract": "A family link may corroborate an existing Number anchor; it never creates semantic or ownership authority.",
        "baseline_frozen_clip_appearance": {
            key: round(value, 6) for key, value in raw_metrics.items()
        },
        "after_nested_paint_disjoint": {
            **{key: round(value, 6) for key, value in after_metrics.items()},
            "pair_count": len(truth),
            "positive_pair_count": int(np.count_nonzero(truth)),
            "accepted_count": int(np.count_nonzero(accepted)),
            "accepted_true_positive_count": int(np.count_nonzero(accepted & truth)),
            "accepted_false_positive_count": int(np.count_nonzero(negative_accepted)),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "accepted_cross_paint_number_family_negatives": int(np.count_nonzero(
                negative_accepted & (kind == PAIR_CROSS_PAINT_NUMBER)
            )),
            "accepted_within_paint_nonnumber_links": int(np.count_nonzero(
                negative_accepted & (kind == PAIR_WITHIN_PAINT_NONNUMBER)
            )),
            "five_control_wrong_links": control_wrong,
        },
        "frozen_clip_calibrated_link": {
            "accepted_count": int(np.count_nonzero(raw_accepted)),
            "accepted_true_positive_count": int(np.count_nonzero(raw_accepted & truth)),
            "accepted_false_positive_count": int(np.count_nonzero(raw_negative_accepted)),
            "precision": round(raw_precision, 6),
            "recall": round(raw_recall, 6),
            "accepted_cross_paint_number_family_negatives": int(np.count_nonzero(
                raw_negative_accepted & (kind == PAIR_CROSS_PAINT_NUMBER)
            )),
            "accepted_within_paint_nonnumber_links": int(np.count_nonzero(
                raw_negative_accepted & (kind == PAIR_WITHIN_PAINT_NONNUMBER)
            )),
            "five_control_wrong_links": raw_control_wrong,
        },
        "gates": {
            "constrained_family_link_gate_passed": gate,
            "frozen_clip_calibrated_link_gate_passed": raw_link_gate,
            "requires_existing_number_anchor": True,
            "casts_ownership_vote": False,
            "holdout_opened": False,
            "runtime_integrated": False,
        },
        "targets": sorted(set(data["groups"]) - CONTROL_PAINTS),
        "hard_negative_controls": sorted(set(data["groups"]) & CONTROL_PAINTS),
        "folds": folds,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "clip_weights_frozen": True,
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
        "baseline": ledger["baseline_frozen_clip_appearance"],
        "after": ledger["after_nested_paint_disjoint"],
        "frozen_clip_calibrated": ledger["frozen_clip_calibrated_link"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
