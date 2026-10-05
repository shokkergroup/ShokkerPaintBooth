"""Calibrated, paint-disjoint canary probe for reviewed physical groups.

The model is fitted and calibrated only on the training bank.  The canary bank
must contain different paint labels.  Scores are offline diagnostics: this
tool never casts votes, adds pixels, or grants ownership authority.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


CLASSES = ("numbers", "sponsors", "template", "paint")
BASE_INTRINSIC_FEATURES = (
    "member_count", "area_fraction", "bbox_fraction", "fill_ratio",
    "largest_member_fraction", "smallest_member_fraction",
    "mean_edge_density", "max_edge_density", "mean_texture_entropy",
    "max_texture_entropy", "max_ocr_coverage", "max_digit_coverage",
    "palette_role_count", "palette_role_entropy", "lightness_span",
    "chroma_span", "proposal_conflict_fraction",
)
SHAPE_FEATURES = (
    "shape_occupancy_mean",
    "shape_occupancy_std", "shape_horizontal_symmetry",
    "shape_vertical_symmetry", "shape_center_edge_delta",
    "shape_adjacent_transition",
)
INTRINSIC_FEATURES = BASE_INTRINSIC_FEATURES + SHAPE_FEATURES


def _reviewed(bank: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = bank.get("summary") or {}
    if summary.get("casts_votes") or summary.get("ownership_authority"):
        raise ValueError("group feature bank claimed runtime authority")
    return [
        dict(row) for row in bank.get("records") or ()
        if row.get("reviewed") and row.get("review_target_layer") in CLASSES
    ]


def _matrix(
    rows: Sequence[Mapping[str, Any]], feature_names: Sequence[str],
) -> np.ndarray:
    return np.asarray([
        [float(row.get(name) or 0.0) for name in feature_names]
        for row in rows
    ], dtype=np.float64)


def evaluate_canary(
    train_bank: Mapping[str, Any], canary_bank: Mapping[str, Any],
    *, min_score: float = 0.80, min_margin: float = 0.25,
    feature_set: str = "baseline",
) -> dict[str, Any]:
    if feature_set not in {"baseline", "shape"}:
        raise ValueError(f"unknown feature set: {feature_set}")
    feature_names = (
        BASE_INTRINSIC_FEATURES if feature_set == "baseline"
        else INTRINSIC_FEATURES
    )
    train = _reviewed(train_bank)
    canary = _reviewed(canary_bank)
    train_paints = {str(row["paint_label"]) for row in train}
    canary_paints = {str(row["paint_label"]) for row in canary}
    overlap = sorted(train_paints & canary_paints)
    if overlap:
        raise ValueError(f"train/canary paint overlap: {overlap[:5]}")
    train_counts = Counter(str(row["review_target_layer"]) for row in train)
    missing = [owner for owner in CLASSES if train_counts[owner] < 12]
    if missing:
        raise ValueError(f"training classes below 12 reviews: {missing}")
    if len(train_paints) < 6:
        raise ValueError("at least six training paints are required")

    x_train = _matrix(train, feature_names)
    y_train = np.asarray([str(row["review_target_layer"]) for row in train])
    groups = np.asarray([str(row["paint_label"]) for row in train])
    fold_count = min(5, len(train_paints))
    splits = list(GroupKFold(n_splits=fold_count).split(x_train, y_train, groups))
    for fit, _ in splits:
        if set(y_train[fit]) != set(CLASSES):
            raise ValueError("paint calibration fold lacks a semantic class")
    estimator = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2500, class_weight="balanced", random_state=0),
    )
    model = CalibratedClassifierCV(estimator=estimator, method="sigmoid", cv=splits)
    model.fit(x_train, y_train)

    x_canary = _matrix(canary, feature_names)
    truth = np.asarray([str(row["review_target_layer"]) for row in canary])
    probabilities = model.predict_proba(x_canary)
    class_names = [str(value) for value in model.classes_]
    predictions = []
    emitted = Counter()
    correct = Counter()
    truth_counts = Counter(truth)
    false_numbers = []
    for row, actual, scores in zip(canary, truth, probabilities):
        order = np.argsort(scores)[::-1]
        top_index, second_index = int(order[0]), int(order[1])
        top_class = class_names[top_index]
        top_score = float(scores[top_index])
        margin = top_score - float(scores[second_index])
        accepted = top_score >= min_score and margin >= min_margin
        prediction = top_class if accepted else "abstain"
        if accepted:
            emitted[top_class] += 1
            if top_class == actual:
                correct[top_class] += 1
            elif top_class == "numbers":
                false_numbers.append({
                    "paint_label": row["paint_label"], "group_id": row["group_id"],
                    "truth": actual, "score": round(top_score, 6),
                    "margin": round(margin, 6),
                })
        predictions.append({
            "paint_label": row["paint_label"], "group_id": row["group_id"],
            "truth": actual, "prediction": prediction, "top_class": top_class,
            "top_score": round(top_score, 6), "margin": round(margin, 6),
            "scores": {
                owner: round(float(scores[class_names.index(owner)]), 6)
                for owner in class_names
            },
        })

    per_class = {}
    for owner in CLASSES:
        per_class[owner] = {
            "truth": truth_counts[owner], "emitted": emitted[owner],
            "correct": correct[owner],
            "precision": round(correct[owner] / emitted[owner], 6) if emitted[owner] else None,
            "recall_at_threshold": round(correct[owner] / truth_counts[owner], 6) if truth_counts[owner] else None,
        }
    encoded = np.zeros_like(probabilities)
    for index, actual in enumerate(truth):
        encoded[index, class_names.index(str(actual))] = 1.0
    number_truth_paints = {
        str(row["paint_label"]) for row in canary
        if row["review_target_layer"] == "numbers"
    }
    blockers = []
    if false_numbers:
        blockers.append("number_false_positive")
    if truth_counts["numbers"] < 12 or len(number_truth_paints) < 3:
        blockers.append("insufficient_independent_number_canary_coverage")
    return {
        "schema": "smart-tga-group-canary-probe-v1",
        "feature_set": feature_set,
        "feature_names": list(feature_names),
        "train_paint_count": len(train_paints), "train_group_count": len(train),
        "canary_paint_count": len(canary_paints), "canary_group_count": len(canary),
        "train_class_counts": dict(sorted(train_counts.items())),
        "canary_class_counts": dict(sorted(truth_counts.items())),
        "calibration": {
            "method": "sigmoid", "paint_group_folds": fold_count,
            "multiclass_log_loss": round(float(log_loss(truth, probabilities, labels=class_names)), 6),
            "multiclass_brier": round(float(np.mean(np.sum((probabilities - encoded) ** 2, axis=1))), 6),
        },
        "min_score": min_score, "min_margin": min_margin,
        "per_class": per_class,
        "number_false_positive_count": len(false_numbers),
        "number_false_positives": false_numbers,
        "acceptance_ready": not blockers,
        "acceptance_blockers": blockers,
        "predictions": predictions,
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-bank", required=True)
    parser.add_argument("--canary-bank", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-score", type=float, default=0.80)
    parser.add_argument("--min-margin", type=float, default=0.25)
    parser.add_argument("--feature-set", choices=("baseline", "shape"), default="baseline")
    args = parser.parse_args()
    train = json.loads(Path(args.train_bank).read_text(encoding="utf-8"))
    canary = json.loads(Path(args.canary_bank).read_text(encoding="utf-8"))
    report = evaluate_canary(
        train, canary, min_score=args.min_score, min_margin=args.min_margin,
        feature_set=args.feature_set,
    )
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "predictions"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
