"""Calibrate frozen CLIPSeg evidence as Number -> complete/fragment hierarchy.

The scorer is deliberately low dimensional.  Stage one sees only the maximum
of the owner-neutral complete-Number and Number-fragment prompt similarities.
Stage two, trained only on reviewed Number candidates, sees complete similarity
and the complete-minus-fragment margin.  Their minimum is the final score: a
candidate cannot rank highly unless both stages agree.

All reported predictions are source-content-disjoint.  Each outer test fold is
scored by a four-member inner committee and uses its lower quartile, while the
acceptance threshold is the largest unsafe inner-OOF score plus one robust MAD
margin.  This is research evidence only; it never casts ownership votes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold


CATEGORY_NAMES = ("complete_number", "number_fragment", "sponsor", "paint")
MODEL_C = 100.0
OUTER_FOLDS = 5
INNER_FOLDS = 4
ENSEMBLE_QUANTILE = 0.25


def _load_evidence(examples_path: Path, controls_path: Path) -> dict[str, np.ndarray | list]:
    examples = json.loads(examples_path.read_text(encoding="utf-8"))
    control_ledger = json.loads(controls_path.read_text(encoding="utf-8"))
    controls = set(control_ledger["hard_negative_controls"])
    category = np.asarray([
        [float(row["category_scores"][name]) for name in CATEGORY_NAMES]
        for row in examples
    ], dtype=np.float64)
    return {
        "examples": examples,
        "category": category,
        "semantic_truth": np.asarray([row["semantic"] == 1 for row in examples]),
        "semantic_explicit": np.asarray([row["semantic"] >= 0 for row in examples]),
        "complete_truth": np.asarray([row["complete"] == 1 for row in examples]),
        "complete_explicit": np.asarray([row["complete"] >= 0 for row in examples]),
        "groups": np.asarray([row["source_content_group"] for row in examples]),
        "paints": np.asarray([row["paint"] for row in examples]),
        "stress": np.asarray([row["paint"] in controls for row in examples]),
        "controls": sorted(controls),
    }


def _feature_matrices(category: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return owner-neutral semantic and conditional-completeness evidence."""
    complete = category[:, 0]
    fragment = category[:, 1]
    semantic = np.maximum(complete, fragment)[:, None]
    completeness = np.column_stack((complete, complete - fragment))
    return semantic.astype(np.float64), completeness.astype(np.float64)


def _new_model() -> LogisticRegression:
    # CLIP cosine similarities occupy a narrow range; the fixed C is part of
    # this development architecture and receives no holdout tuning.
    return LogisticRegression(
        C=MODEL_C,
        class_weight="balanced",
        max_iter=2000,
        solver="liblinear",
        random_state=729,
    )


def _fit_stage_models(data: dict, train: np.ndarray) -> tuple[LogisticRegression, LogisticRegression]:
    semantic_x, complete_x = _feature_matrices(data["category"])
    semantic_train = train[data["semantic_explicit"][train]]
    complete_train = train[
        data["semantic_truth"][train] & data["complete_explicit"][train]
    ]
    semantic_model = _new_model().fit(
        semantic_x[semantic_train], data["semantic_truth"][semantic_train],
    )
    complete_model = _new_model().fit(
        complete_x[complete_train], data["complete_truth"][complete_train],
    )
    return semantic_model, complete_model


def _predict_stage_models(
    models: tuple[LogisticRegression, LogisticRegression],
    semantic_x: np.ndarray,
    complete_x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    semantic_model, complete_model = models
    return (
        semantic_model.predict_proba(semantic_x)[:, 1],
        complete_model.predict_proba(complete_x)[:, 1],
    )


def _fit_predict(data: dict, train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    semantic_x, complete_x = _feature_matrices(data["category"])
    return _predict_stage_models(
        _fit_stage_models(data, train), semantic_x[test], complete_x[test],
    )


def _lower_quartile_ensemble(values: list[np.ndarray]) -> np.ndarray:
    if not values:
        raise ValueError("committee cannot be empty")
    return np.quantile(np.stack(values), ENSEMBLE_QUANTILE, axis=0)


def _robust_safe_threshold(
    score: np.ndarray,
    truth: np.ndarray,
    explicit: np.ndarray,
    stress: np.ndarray,
) -> tuple[float, float, float]:
    """Put the threshold one MAD beyond every known unsafe score."""
    unsafe = (~explicit) | stress | (explicit & ~truth)
    unsafe_scores = score[unsafe]
    if not len(unsafe_scores):
        raise ValueError("safe calibration requires explicit unsafe examples")
    median = float(np.median(unsafe_scores))
    mad = float(np.median(np.abs(unsafe_scores - median)))
    maximum = float(np.max(unsafe_scores))
    return maximum + mad, maximum, mad


def _nested_source_disjoint(data: dict) -> dict:
    count = len(data["groups"])
    indices = np.arange(count, dtype=np.int64)
    semantic_probability = np.zeros(count, dtype=np.float64)
    complete_probability = np.zeros(count, dtype=np.float64)
    joint_score = np.zeros(count, dtype=np.float64)
    accepted = np.zeros(count, dtype=bool)
    folds = []
    outer = GroupKFold(n_splits=OUTER_FOLDS)
    for fold, (train, test) in enumerate(outer.split(indices, groups=data["groups"])):
        inner = list(GroupKFold(n_splits=INNER_FOLDS).split(
            train, groups=data["groups"][train],
        ))
        inner_oof = np.zeros(len(train), dtype=np.float64)
        semantic_committee, complete_committee = [], []
        for inner_train_offset, inner_test_offset in inner:
            inner_train = train[inner_train_offset]
            inner_test = train[inner_test_offset]
            semantic, complete = _fit_predict(data, inner_train, inner_test)
            inner_oof[inner_test_offset] = np.minimum(semantic, complete)
            semantic, complete = _fit_predict(data, inner_train, test)
            semantic_committee.append(semantic)
            complete_committee.append(complete)
        semantic_probability[test] = _lower_quartile_ensemble(semantic_committee)
        complete_probability[test] = _lower_quartile_ensemble(complete_committee)
        joint_score[test] = np.minimum(
            semantic_probability[test], complete_probability[test],
        )
        threshold, unsafe_max, mad = _robust_safe_threshold(
            inner_oof,
            data["complete_truth"][train],
            data["complete_explicit"][train],
            data["stress"][train],
        )
        accepted[test] = joint_score[test] >= threshold
        folds.append({
            "fold": fold,
            "test_paints": sorted(set(data["paints"][test])),
            "test_source_content_groups": len(set(data["groups"][test])),
            "inner_unsafe_max": round(unsafe_max, 8),
            "inner_unsafe_mad": round(mad, 8),
            "robust_acceptance_threshold": round(threshold, 8),
            "test_accepted_count": int(np.count_nonzero(accepted[test])),
        })
    return {
        "semantic_probability": semantic_probability,
        "complete_probability": complete_probability,
        "joint_score": joint_score,
        "accepted": accepted,
        "folds": folds,
    }


def _acceptance_metrics(data: dict, accepted: np.ndarray) -> dict:
    truth = data["complete_truth"]
    explicit = data["complete_explicit"]
    explicit_accepted = accepted & explicit
    return {
        "accepted_count": int(np.count_nonzero(accepted)),
        "accepted_true_positive_count": int(np.count_nonzero(accepted & truth)),
        "accepted_explicit_false_positive_count": int(np.count_nonzero(
            explicit_accepted & ~truth,
        )),
        "accepted_review_uncertain_count": int(np.count_nonzero(accepted & ~explicit)),
        "precision_on_explicit": round(
            float(truth[explicit_accepted].mean()) if explicit_accepted.any() else 1.0, 6,
        ),
        "recall": round(
            float(np.count_nonzero(accepted & truth) / max(1, np.count_nonzero(truth))), 6,
        ),
        "five_control_wrong_accepts": int(np.count_nonzero(accepted & data["stress"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--controls-ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=729)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    data = _load_evidence(args.examples, args.controls_ledger)
    result = _nested_source_disjoint(data)
    truth = data["complete_truth"]
    explicit = data["complete_explicit"]
    score = result["joint_score"]
    comparable_ap = float(average_precision_score(truth, score))
    explicit_ap = float(average_precision_score(truth[explicit], score[explicit]))
    acceptance = _acceptance_metrics(data, result["accepted"])
    gate = bool(
        comparable_ap > 0.489735
        and explicit_ap >= 0.669527
        and acceptance["precision_on_explicit"] >= 0.80
        and acceptance["five_control_wrong_accepts"] == 0
        and acceptance["accepted_review_uncertain_count"] == 0
        and acceptance["accepted_true_positive_count"] > 0
    )
    rows = []
    for index, example in enumerate(data["examples"]):
        rows.append({
            **example,
            "hierarchical_semantic_probability": round(
                float(result["semantic_probability"][index]), 8,
            ),
            "hierarchical_complete_probability": round(
                float(result["complete_probability"][index]), 8,
            ),
            "hierarchical_joint_score": round(float(score[index]), 8),
            "hierarchical_accepted": bool(result["accepted"][index]),
            "ownership_authority": False,
        })
    (args.output / "development_examples.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8",
    )
    ledger = {
        "schema": "smart-tga-clipseg-hierarchical-calibrator-v1",
        "cycle": args.cycle,
        "contract": (
            "Frozen owner-neutral semantic Number evidence gates a conditional "
            "complete-versus-fragment stage; the lower score wins."
        ),
        "baseline": {
            "legacy_complete_number_average_precision": 0.489735,
            "zero_shot_complete_valid_explicit_average_precision": 0.669527,
            "zero_shot_safe_accepted_true_positive_count": 2,
            "zero_shot_safe_explicit_false_positive_count": 1,
        },
        "after_nested_source_content_disjoint": {
            "candidate_count": len(truth),
            "paint_count": len(set(data["paints"])),
            "source_content_group_count": len(set(data["groups"])),
            "complete_number_count": int(np.count_nonzero(truth)),
            "comparable_average_precision": round(comparable_ap, 6),
            "valid_explicit_average_precision": round(explicit_ap, 6),
            **acceptance,
        },
        "architecture": {
            "semantic_features": ["max(complete_number, number_fragment)"],
            "conditional_complete_features": [
                "complete_number", "complete_number_minus_number_fragment",
            ],
            "joint_operator": "minimum_stage_probability",
            "model": f"balanced_logistic_C{MODEL_C:g}",
            "outer_folds": OUTER_FOLDS,
            "inner_committee_folds": INNER_FOLDS,
            "test_ensemble_quantile": ENSEMBLE_QUANTILE,
            "threshold": "max_inner_unsafe_oof_plus_unsafe_mad",
            "anchor_relationships_used": False,
        },
        "gates": {
            "development_hierarchical_gate_passed": gate,
            "requires_comparable_ap_greater_than": 0.489735,
            "requires_valid_explicit_ap_at_least": 0.669527,
            "requires_precision_at_least": 0.80,
            "requires_zero_five_control_wrong_accepts": True,
            "requires_zero_review_uncertain_accepts": True,
            "requires_nonzero_recall": True,
            "untouched_holdout_allowed_next": gate,
            "untouched_holdout_opened": False,
            "runtime_integrated": False,
        },
        "targets": sorted(set(data["paints"]) - set(data["controls"])),
        "hard_negative_controls": data["controls"],
        "folds": result["folds"],
        "selected_model_counts": dict(Counter(
            f"balanced_logistic_C{MODEL_C:g}" for _ in result["folds"]
        )),
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "frozen_clipseg_evidence": True,
            "outer_source_content_disjoint": True,
            "threshold_calibrated_inside_outer_training_only": True,
            "hyperparameters_receive_no_holdout_tuning": True,
            "casts_votes": False,
            "ownership_authority": False,
            "apply_locked": True,
            "filename_or_car_features": False,
            "absolute_bbox_inference_feature": False,
            "ocr_changed": False,
            "exact_reconstruction_affected": False,
        },
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": ledger["baseline"],
        "after": ledger["after_nested_source_content_disjoint"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
