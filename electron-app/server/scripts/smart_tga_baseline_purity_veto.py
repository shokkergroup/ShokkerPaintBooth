"""Calibrate a removal-only semantic veto for Smart TGA raw nominations.

The frozen raw baseline is intentionally high precision, but Cycle735 found two
Sponsor strips that crossed it on a new DLM paint.  This module learns from that
active-learning paint without calling it evaluation: every outer development
fold is still source-content-disjoint, while the reviewed calibration paint is
present only as an additional training source.  The resulting head can remove
raw nominations; it can never add a candidate or own output pixels.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

try:
    from scripts.smart_tga_exact_candidate_utils import CONTROL_PAINTS
    from scripts.smart_tga_fragment_completeness_head import _arrays
    from scripts.smart_tga_fragment_purity_veto import (
        _appearance_matrix, _candidate_key, _fit_predict, _load_appearance,
        _load_pretrained_appearance, _select_model,
    )
    from scripts.smart_tga_number_family_set_assembler import _set_metrics
    from scripts.smart_tga_within_paint_ordinal_family import (
        _build_rows, _load_candidate_table, _top_two,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import CONTROL_PAINTS  # type: ignore
    from scripts.smart_tga_fragment_completeness_head import _arrays  # type: ignore
    from scripts.smart_tga_fragment_purity_veto import (  # type: ignore
        _appearance_matrix, _candidate_key, _fit_predict, _load_appearance,
        _load_pretrained_appearance, _select_model,
    )
    from scripts.smart_tga_number_family_set_assembler import _set_metrics  # type: ignore
    from scripts.smart_tga_within_paint_ordinal_family import (  # type: ignore
        _build_rows, _load_candidate_table, _top_two,
    )


FEATURE_MODE = "pretrained-anchor-relative-semantic"


def _candidate_records(path: Path, paint: str) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    matches = [record for record in payload["records"] if record["paint"] == paint]
    if len(matches) != 1:
        raise RuntimeError(f"expected one candidate record for {paint}, found {len(matches)}")
    return matches[0]["candidates"]


def _outcome_labels(path: Path) -> dict[int, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    outcomes = payload["outcomes"]
    result: dict[int, str] = {}
    for item in outcomes["Number"]:
        result[int(item["candidate_index"])] = "Number"
    for semantic in ("Sponsor", "Template", "Paint"):
        for candidate_index in outcomes[semantic]:
            index = int(candidate_index)
            if index in result:
                raise RuntimeError(f"duplicate calibration outcome for candidate {index}")
            result[index] = semantic
    if outcomes.get("uncertain"):
        raise RuntimeError("baseline calibration source must have zero uncertain outcomes")
    return result


def _relative_feature_vector(
    key: tuple[str, int, str], anchor_key: tuple[str, int, str],
    pretrained: dict[tuple[str, int, str], np.ndarray],
    semantic: dict[tuple[str, int, str], np.ndarray],
) -> np.ndarray:
    """Match fragment_purity_veto's frozen combined visual representation."""
    candidate_orbit = pretrained[key]
    anchor_orbit = pretrained[anchor_key]
    candidate_mean = candidate_orbit.mean(axis=0)
    candidate_mean /= max(float(np.linalg.norm(candidate_mean)), 1e-8)
    anchor_mean = anchor_orbit.mean(axis=0)
    anchor_mean /= max(float(np.linalg.norm(anchor_mean)), 1e-8)
    similarity = candidate_orbit @ anchor_orbit.T
    appearance = np.concatenate((
        np.abs(candidate_mean - anchor_mean),
        np.asarray((
            similarity.max(), similarity.mean(), similarity.std(),
            np.median(similarity), np.quantile(similarity, 0.90),
        ), dtype=np.float32),
    ))
    candidate_semantic = semantic[key]
    anchor_semantic = semantic[anchor_key]
    return np.concatenate((
        appearance, candidate_semantic,
        np.abs(candidate_semantic - anchor_semantic),
    )).astype(np.float32)


def _calibration_dataset(
    bank_path: Path, outcomes_path: Path, paint: str, anchor_index: int,
    pretrained: dict[tuple[str, int, str], np.ndarray],
    semantic: dict[tuple[str, int, str], np.ndarray],
) -> tuple[np.ndarray, np.ndarray, list[int], list[tuple[str, int, str]]]:
    candidates = _candidate_records(bank_path, paint)
    labels = _outcome_labels(outcomes_path)
    indices = sorted(labels)
    if not 0 <= anchor_index < len(candidates):
        raise RuntimeError("calibration anchor index is outside the candidate bank")
    anchor_key = (paint, anchor_index, str(candidates[anchor_index]["proposal_id"]))
    keys = [
        (paint, index, str(candidates[index]["proposal_id"])) for index in indices
    ]
    features = np.stack([
        _relative_feature_vector(key, anchor_key, pretrained, semantic) for key in keys
    ])
    target = np.asarray([labels[index] == "Number" for index in indices], dtype=np.int8)
    return features, target, indices, keys


def _calibrate_threshold(true_scores: np.ndarray, false_scores: np.ndarray) -> tuple[float, dict]:
    """Place the veto boundary strictly between known raw false and true scores."""
    if len(true_scores) == 0 or len(false_scores) == 0:
        raise RuntimeError("baseline calibration requires raw true and raw false examples")
    false_ceiling = float(np.max(false_scores))
    true_floor = float(np.min(true_scores))
    separated = false_ceiling < true_floor
    threshold = (false_ceiling + true_floor) / 2.0 if separated else true_floor
    return threshold, {
        "raw_false_score_ceiling": round(false_ceiling, 8),
        "raw_true_score_floor": round(true_floor, 8),
        "strictly_separated": separated,
        "margin": round(true_floor - false_ceiling, 8),
    }


def _raw_baseline(
    rows: list[dict], indices: np.ndarray, groups: np.ndarray, frozen_ledger: dict,
) -> tuple[np.ndarray, list[tuple[np.ndarray, np.ndarray]]]:
    folds = list(GroupKFold(n_splits=5).split(indices, groups=groups))
    if len(folds) != len(frozen_ledger["folds"]):
        raise RuntimeError("frozen outer-fold count drift")
    baseline = np.zeros(len(indices), dtype=bool)
    for fold, (_, test_offset) in enumerate(folds):
        test = _arrays(rows, indices[test_offset])
        threshold = float(frozen_ledger["folds"][fold]["raw_safe_threshold"])
        baseline[test_offset] = _top_two(
            test["raw_score"], test["raw_score"] >= threshold, test["keys"],
        )
    return baseline, folds


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--semantic-appearance", type=Path, required=True)
    parser.add_argument("--pretrained-appearance", type=Path, required=True)
    parser.add_argument("--frozen-ledger", type=Path, required=True)
    parser.add_argument("--calibration-bank", type=Path, required=True)
    parser.add_argument("--calibration-outcomes", type=Path, required=True)
    parser.add_argument("--calibration-paint", required=True)
    parser.add_argument("--calibration-anchor", type=int, required=True)
    parser.add_argument("--calibration-raw", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=736)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)

    frozen_ledger = json.loads(args.frozen_ledger.read_text(encoding="utf-8"))
    table = _load_candidate_table(args.bank, args.embeddings, args.labels)
    rows = _build_rows(table)
    indices = np.asarray([
        offset for offset, row in enumerate(rows) if row["semantic"] is not None
    ], dtype=np.int64)
    data = _arrays(rows, indices)
    groups = np.asarray([rows[int(index)]["content_group"] for index in indices])
    semantic, semantic_names = _load_appearance(args.semantic_appearance)
    pretrained = _load_pretrained_appearance(args.pretrained_appearance)
    development_features, feature_names = _appearance_matrix(
        rows, indices, table, semantic, semantic_names, FEATURE_MODE,
        pretrained, semantic, semantic_names,
    )
    calibration_features, calibration_target, calibration_indices, calibration_keys = (
        _calibration_dataset(
            args.calibration_bank, args.calibration_outcomes,
            args.calibration_paint, args.calibration_anchor, pretrained, semantic,
        )
    )
    calibration_offset = {
        candidate_index: offset
        for offset, candidate_index in enumerate(calibration_indices)
    }
    missing_raw = sorted(set(args.calibration_raw) - set(calibration_offset))
    if missing_raw:
        raise RuntimeError(f"calibration raw candidates lack outcomes: {missing_raw}")
    calibration_raw = np.asarray([
        calibration_offset[index] for index in args.calibration_raw
    ], dtype=np.int64)
    calibration_raw_true = calibration_raw[
        calibration_target[calibration_raw].astype(bool)
    ]
    calibration_raw_false = calibration_raw[
        ~calibration_target[calibration_raw].astype(bool)
    ]

    baseline, folds = _raw_baseline(rows, indices, groups, frozen_ledger)
    baseline_before = _set_metrics(rows, indices, data, baseline)
    if baseline_before != frozen_ledger["baseline_raw_safe"]:
        raise RuntimeError("Cycle732 raw baseline replay drift")

    development_scores = np.empty(len(indices), dtype=np.float64)
    retained_baseline = np.zeros(len(indices), dtype=bool)
    calibration_votes = np.zeros(len(calibration_indices), dtype=np.int16)
    fold_ledgers = []
    for fold, (train_offset, test_offset) in enumerate(folds):
        train_data = _arrays(rows, indices[train_offset])
        selected, model_scores, _ = _select_model(
            development_features[train_offset], train_data["family"],
            train_data["known"], groups[train_offset], feature_names,
            7360 + fold * 100,
        )
        fit_features = np.concatenate((
            development_features[train_offset], calibration_features,
        ))
        fit_target = np.concatenate((train_data["family"], calibration_target))
        fit_known = np.concatenate((
            train_data["known"], np.ones(len(calibration_target), dtype=bool),
        ))
        seed = 7460 + fold
        test_score = _fit_predict(
            fit_features, fit_target, fit_known, development_features[test_offset],
            selected, feature_names, seed,
        )
        train_score = _fit_predict(
            fit_features, fit_target, fit_known, development_features[train_offset],
            selected, feature_names, seed,
        )
        calibration_score = _fit_predict(
            fit_features, fit_target, fit_known, calibration_features,
            selected, feature_names, seed,
        )
        development_raw_true = (
            baseline[train_offset] & train_data["known"] & train_data["family"]
        )
        true_scores = np.concatenate((
            train_score[development_raw_true],
            calibration_score[calibration_raw_true],
        ))
        false_scores = calibration_score[calibration_raw_false]
        threshold, threshold_summary = _calibrate_threshold(true_scores, false_scores)
        development_scores[test_offset] = test_score
        retained_baseline[test_offset] = (
            baseline[test_offset] & (test_score >= threshold)
        )
        calibration_votes += (calibration_score >= threshold).astype(np.int16)
        fold_ledgers.append({
            "fold": fold,
            "test_paints": sorted({
                rows[int(indices[value])]["paint"] for value in test_offset
            }),
            "source_content_overlap": bool(
                set(groups[train_offset]).intersection(set(groups[test_offset]))
            ),
            "calibration_paint_in_test": args.calibration_paint in {
                rows[int(indices[value])]["paint"] for value in test_offset
            },
            "selected_baseline_purity_head": selected["name"],
            "inner_development_ap": {
                name: round(value, 6) for name, value in model_scores.items()
            },
            "baseline_purity_threshold": round(float(threshold), 8),
            "threshold_calibration": threshold_summary,
            "outer_raw_nominated": int(np.count_nonzero(baseline[test_offset])),
            "outer_raw_retained": int(np.count_nonzero(retained_baseline[test_offset])),
            "calibration_raw_scores": [
                {
                    "candidate_index": int(calibration_indices[offset]),
                    "semantic_for_calibration_only": (
                        "Number" if calibration_target[offset] else "not_Number"
                    ),
                    "purity": round(float(calibration_score[offset]), 8),
                    "retain": bool(calibration_score[offset] >= threshold),
                }
                for offset in calibration_raw
            ],
        })

    baseline_after = _set_metrics(rows, indices, data, retained_baseline)
    explicit_ap = float(average_precision_score(
        data["family"][data["known"]], development_scores[data["known"]],
    ))
    calibration_retained = calibration_votes >= 3
    raw_calibration_retained = calibration_retained[calibration_raw]
    raw_calibration_target = calibration_target[calibration_raw].astype(bool)
    raw_true_before = int(np.count_nonzero(raw_calibration_target))
    raw_false_before = int(np.count_nonzero(~raw_calibration_target))
    raw_true_after = int(np.count_nonzero(
        raw_calibration_retained & raw_calibration_target
    ))
    raw_false_after = int(np.count_nonzero(
        raw_calibration_retained & ~raw_calibration_target
    ))
    calibration_before_precision = raw_true_before / max(len(calibration_raw), 1)
    calibration_after_precision = raw_true_after / max(
        raw_true_after + raw_false_after, 1
    )
    gates = {
        "all_development_raw_true_preserved": (
            baseline_after["accepted_true_number_family"]
            == baseline_before["accepted_true_number_family"]
        ),
        "development_candidate_precision_at_least_0_80": (
            baseline_after["precision"] >= 0.80
        ),
        "development_pixel_precision_at_least_0_80": (
            baseline_after["reviewed_pixel_precision"] >= 0.80
        ),
        "zero_development_uncertain_accepts": baseline_after["accepted_uncertain"] == 0,
        "zero_five_control_wrong_links": baseline_after["five_control_wrong_links"] == 0,
        "all_calibration_raw_true_preserved": raw_true_after == raw_true_before,
        "all_calibration_raw_false_removed": raw_false_after == 0,
        "all_folds_strictly_separate_calibration_raw": all(
            item["threshold_calibration"]["strictly_separated"]
            for item in fold_ledgers
        ),
        "zero_source_content_overlap": not any(
            item["source_content_overlap"] for item in fold_ledgers
        ),
    }
    gates["baseline_purity_calibration_gate_passed"] = all(gates.values())
    ledger = {
        "schema": "smart-tga-baseline-purity-veto-v1",
        "cycle": args.cycle,
        "contract": (
            "Frozen pretrained D4 appearance plus candidate-resolution prompt semantics "
            "form a removal-only raw-baseline purity corroborator. The reviewed active-"
            "learning paint is calibration, never evaluation; output authority is zero."
        ),
        "feature_mode": FEATURE_MODE,
        "feature_count": len(feature_names),
        "development": {
            "reviewed_rows": len(indices),
            "unique_source_content_count": len(np.unique(groups)),
            "baseline_number_purity_ap": round(explicit_ap, 6),
            "before_raw_baseline": baseline_before,
            "after_baseline_purity_veto": baseline_after,
        },
        "active_learning_calibration": {
            "paint": args.calibration_paint,
            "anchor_candidate_index": args.calibration_anchor,
            "reviewed_candidate_count": len(calibration_indices),
            "reviewed_number_count": int(calibration_target.sum()),
            "raw_candidate_indices": [int(value) for value in args.calibration_raw],
            "before": {
                "true": raw_true_before, "false": raw_false_before,
                "precision": round(calibration_before_precision, 6),
            },
            "after_majority_committee": {
                "true": raw_true_after, "false": raw_false_after,
                "precision": round(calibration_after_precision, 6),
            },
            "candidate_votes": [
                {
                    "candidate_index": int(calibration_indices[offset]),
                    "proposal_id": calibration_keys[offset][2],
                    "semantic_for_calibration_only": (
                        "Number" if calibration_target[offset] else "not_Number"
                    ),
                    "retain_votes": int(calibration_votes[offset]),
                    "decision": "retain" if calibration_retained[offset] else "veto",
                }
                for offset in calibration_raw
            ],
            "is_evaluation_holdout": False,
        },
        "gates": gates,
        "selected_head_counts": dict(Counter(
            item["selected_baseline_purity_head"] for item in fold_ledgers
        )),
        "folds": fold_ledgers,
        "hard_negative_controls": sorted(CONTROL_PAINTS),
        "safety": {
            "raw_candidates_can_only_be_removed": True,
            "candidate_can_be_admitted": False,
            "filename_or_car_model_feature": False,
            "absolute_bbox_model_feature": False,
            "template_position_model_feature": False,
            "calibration_labels_are_features": False,
            "calibration_paint_reported_as_holdout": False,
            "pretrained_model_weights_frozen": True,
            "semantic_decoder_weights_frozen": True,
            "runtime_integrated": False,
            "ownership_authority": False,
            "apply_locked": True,
            "exact_reconstruction_affected": False,
            "ocr_changed": False,
            "new_tga_opened": False,
        },
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "development_before": baseline_before,
        "development_after": baseline_after,
        "calibration_before": ledger["active_learning_calibration"]["before"],
        "calibration_after": ledger["active_learning_calibration"]["after_majority_committee"],
        "gates": gates,
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
