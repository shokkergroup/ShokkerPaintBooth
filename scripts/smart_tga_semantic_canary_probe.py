"""Fixed-train, independent-canary probe for reviewed Smart TGA objects.

The canary bank is never used for fitting. Scores are offline diagnostics only;
this script casts no votes and has no runtime ownership authority.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from scripts.smart_tga_semantic_holdout_probe import (
        CLASSES, FEATURE_SETS, _vector, assert_feature_set_complete,
    )
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from smart_tga_semantic_holdout_probe import (
        CLASSES, FEATURE_SETS, _vector, assert_feature_set_complete,
    )


def evaluate_independent_canary(
    train_bank: dict, canary_bank: dict, *, feature_set: str = "legacy",
    min_score: float = 0.80, min_margin: float = 0.25,
) -> dict:
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"unknown semantic feature set: {feature_set}")
    train = [x for x in train_bank.get("reviewed_objects") or () if x.get("review_target_layer") in CLASSES]
    canary = [x for x in canary_bank.get("reviewed_objects") or () if x.get("review_target_layer") in CLASSES]
    assert_feature_set_complete(train, feature_set=feature_set, bank_role="training")
    assert_feature_set_complete(canary, feature_set=feature_set, bank_role="canary")
    train_paints = {str(x["paint_label"]) for x in train}
    canary_paints = {str(x["paint_label"]) for x in canary}
    overlap = sorted(train_paints & canary_paints)
    if overlap:
        raise ValueError(f"canary paint leakage: {overlap}")
    missing = sorted(set(CLASSES) - {str(x["review_target_layer"]) for x in train})
    if missing:
        raise ValueError(f"training bank missing classes: {missing}")
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0),
    )
    model.fit(
        np.asarray([_vector(x, feature_set=feature_set) for x in train]),
        [x["review_target_layer"] for x in train],
    )
    probabilities = model.predict_proba(
        np.asarray([_vector(x, feature_set=feature_set) for x in canary])
    )
    predictions = []
    for item, scores in zip(canary, probabilities):
        order = np.argsort(scores)[::-1]
        best, second = int(order[0]), int(order[1])
        score, margin = float(scores[best]), float(scores[best] - scores[second])
        emitted = score >= min_score and margin >= min_margin
        prediction = str(model.classes_[best]) if emitted else "abstain"
        predictions.append({
            "paint_label": item["paint_label"], "object_id": item["object_id"],
            "truth": item["review_target_layer"], "prediction": prediction,
            "top_class": str(model.classes_[best]), "top_score": round(score, 6),
            "margin": round(margin, 6), "emitted": emitted,
        })
    emitted = [x for x in predictions if x["emitted"]]
    correct = [x for x in emitted if x["prediction"] == x["truth"]]
    number_false_positives = sum(x["prediction"] == "numbers" and x["truth"] != "numbers" for x in emitted)
    precision = len(correct) / len(emitted) if emitted else 0.0
    coverage = len(emitted) / len(predictions) if predictions else 0.0
    acceptance_ready = bool(
        len(canary_paints) >= 8 and len(emitted) >= 20 and precision >= 0.98
        and number_false_positives == 0
    )
    return {
        "schema": "smart-tga-semantic-independent-canary-v1",
        "feature_set": feature_set, "feature_names": list(FEATURE_SETS[feature_set]),
        "train_paint_count": len(train_paints), "canary_paint_count": len(canary_paints),
        "train_object_count": len(train), "canary_object_count": len(canary),
        "emitted_count": len(emitted), "correct_count": len(correct),
        "precision": round(precision, 6), "coverage": round(coverage, 6),
        "number_false_positive_count": number_false_positives,
        "train_class_counts": dict(Counter(str(x["review_target_layer"]) for x in train)),
        "canary_class_counts": dict(Counter(str(x["review_target_layer"]) for x in canary)),
        "paint_leakage_count": 0, "independent_canary": True,
        "acceptance_ready": acceptance_ready, "calibration_ready": False,
        "calibration_blockers": ([] if acceptance_ready else ["independent_canary_precision_gate"])
            + ["scores_not_probability_calibrated"],
        "casts_votes": False, "ownership_authority": False,
        "predictions": predictions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-bank", required=True)
    parser.add_argument("--canary-bank", required=True)
    parser.add_argument("--feature-set", choices=sorted(FEATURE_SETS), default="legacy")
    parser.add_argument("--min-score", type=float, default=0.80)
    parser.add_argument("--min-margin", type=float, default=0.25)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = evaluate_independent_canary(
        json.loads(Path(args.train_bank).read_text(encoding="utf-8")),
        json.loads(Path(args.canary_bank).read_text(encoding="utf-8")),
        feature_set=args.feature_set, min_score=args.min_score, min_margin=args.min_margin,
    )
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "predictions"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
