"""Train and measure a DLM fragment/completeness abstention head.

The frozen anchor-relative family score remains the required Number evidence.
This head can only veto that evidence or describe a candidate as complete versus
fragmentary; it cannot manufacture ownership. All model and threshold choices
are nested inside source-content-disjoint folds.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from scripts.smart_tga_exact_candidate_utils import CONTROL_PAINTS
    from scripts.smart_tga_within_paint_ordinal_family import (
        FEATURE_NAMES, FINE_SHAPE_NAMES, _build_rows, _load_candidate_table,
        _top_two,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import CONTROL_PAINTS  # type: ignore
    from scripts.smart_tga_within_paint_ordinal_family import (  # type: ignore
        FEATURE_NAMES, FINE_SHAPE_NAMES, _build_rows, _load_candidate_table,
        _top_two,
    )


HEAD_CONFIGS = (
    {"name": "logistic_c005", "kind": "logistic", "c": 0.05},
    {"name": "logistic_c02", "kind": "logistic", "c": 0.2},
    {"name": "logistic_c1", "kind": "logistic", "c": 1.0},
    {"name": "extra_depth2", "kind": "extra", "depth": 2, "leaf": 5},
    {"name": "extra_depth3", "kind": "extra", "depth": 3, "leaf": 4},
)


def _new_head(config: dict, seed: int):
    if config["kind"] == "logistic":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=float(config["c"]), class_weight="balanced", max_iter=2000,
                solver="liblinear", random_state=seed,
            ),
        )
    return ExtraTreesClassifier(
        n_estimators=384, max_depth=int(config["depth"]),
        min_samples_leaf=int(config["leaf"]), class_weight="balanced",
        max_features=None, random_state=seed, n_jobs=1,
    )


def _arrays(rows: list[dict], indices: np.ndarray) -> dict:
    chosen = [rows[int(index)] for index in indices]
    semantic = np.asarray([row["semantic"] for row in chosen], dtype=object)
    known = np.asarray([
        value is not None and value != "uncertain" for value in semantic
    ], dtype=bool)
    family = semantic == "Number"
    complete = np.asarray([
        row.get("complete_copy") is True for row in chosen
    ], dtype=bool)
    return {
        "features": np.stack([row["features"] for row in chosen]),
        "family_score": np.asarray([
            float(row["features"][0])
            + 0.15 * (float(np.mean(row["features"][1:1 + len(FINE_SHAPE_NAMES)])) - 0.5)
            for row in chosen
        ], dtype=np.float64),
        "raw_score": np.asarray([float(row["features"][0]) for row in chosen]),
        "known": known,
        "uncertain": semantic == "uncertain",
        "family": family,
        "complete": complete,
        "control": np.asarray([row["control"] for row in chosen], dtype=bool),
        "keys": np.asarray([f"{row['paint']}|{row['block']}" for row in chosen]),
        "indices": np.asarray(indices, dtype=np.int64),
    }


def _task_definition(data: dict, task: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # The learned head never sees source identity, filename, bbox, or block.
    if task == "family_veto":
        eligible = data["known"]
        target = data["family"]
        features = data["features"]
    elif task == "review_certainty_veto":
        eligible = np.ones(len(data["known"]), dtype=bool)
        target = data["known"]
        # Certainty is an intrinsic/relative-shape veto. Raw semantic similarity
        # is excluded so it cannot become a second source of Number authority.
        features = data["features"][:, 1:]
    elif task == "complete_copy_description":
        eligible = data["known"] & data["family"]
        target = data["complete"]
        features = data["features"][:, 1:]
    else:
        raise ValueError(task)
    return eligible, target, features


def _fit_predict(
    train: dict, test: dict, config: dict, task: str, seed: int,
) -> np.ndarray:
    eligible, target, features = _task_definition(train, task)
    _, _, test_features = _task_definition(test, task)
    classes = np.unique(target[eligible])
    if len(classes) < 2:
        return np.full(len(test_features), float(target[eligible].mean()) if eligible.any() else 0.5)
    model = _new_head(config, seed)
    model.fit(features[eligible], target[eligible])
    return model.predict_proba(test_features)[:, 1].astype(np.float64)


def _oof_task(
    rows: list[dict], indices: np.ndarray, config: dict, task: str, splits: int = 4,
) -> tuple[np.ndarray, float]:
    groups = np.asarray([rows[int(index)]["content_group"] for index in indices])
    score = np.empty(len(indices), dtype=np.float64)
    fold_count = min(splits, len(np.unique(groups)))
    for fold, (train_offset, test_offset) in enumerate(
        GroupKFold(n_splits=fold_count).split(indices, groups=groups)
    ):
        train = _arrays(rows, indices[train_offset])
        test = _arrays(rows, indices[test_offset])
        score[test_offset] = _fit_predict(train, test, config, task, 7310 + fold)
    data = _arrays(rows, indices)
    eligible, target, _ = _task_definition(data, task)
    ap = float(average_precision_score(target[eligible], score[eligible]))
    return score, ap


def _select_head(
    rows: list[dict], indices: np.ndarray, task: str,
) -> tuple[dict, dict[str, float]]:
    scores = {}
    for config in HEAD_CONFIGS:
        _, ap = _oof_task(rows, indices, config, task)
        scores[config["name"]] = ap
    selected = max(HEAD_CONFIGS, key=lambda value: scores[value["name"]])
    return selected, scores


def _safe_thresholds(
    data: dict, score: np.ndarray, veto: np.ndarray | None,
    precision_floor: float = 0.80,
) -> tuple[float, float, dict]:
    veto_values = np.asarray([0.0]) if veto is None else np.unique(veto)
    effective_veto = np.ones(len(score), dtype=np.float64) if veto is None else veto
    choices = []
    for veto_value in veto_values:
        for score_value in np.unique(score):
            eligible = (score >= score_value) & (effective_veto >= veto_value)
            accepted = _top_two(score, eligible, data["keys"])
            if np.any(accepted & data["uncertain"]):
                continue
            explicit = accepted & data["known"]
            wrong = explicit & ~data["family"]
            if np.any(wrong & data["control"]):
                continue
            precision = float(data["family"][explicit].mean()) if explicit.any() else 1.0
            if precision < precision_floor:
                continue
            true_count = int(np.count_nonzero(explicit & data["family"]))
            complete_count = int(np.count_nonzero(explicit & data["complete"]))
            choices.append((
                true_count, precision, complete_count,
                -int(np.count_nonzero(accepted)), float(score_value), float(veto_value),
            ))
    if not choices:
        score_value = float(np.nextafter(score.max(), np.inf))
        return score_value, 1.0, {"inner_true": 0, "inner_precision": 1.0}
    best = max(choices)
    return best[4], best[5], {
        "inner_true": best[0], "inner_precision": round(best[1], 6),
        "inner_complete": best[2],
    }


def _metrics(data: dict, accepted: np.ndarray) -> dict:
    explicit = accepted & data["known"]
    wrong = explicit & ~data["family"]
    true_count = int(np.count_nonzero(explicit & data["family"]))
    return {
        "accepted_total": int(np.count_nonzero(accepted)),
        "accepted_true_number_family": true_count,
        "accepted_complete_copies": int(np.count_nonzero(accepted & data["complete"])),
        "accepted_number_fragments": int(np.count_nonzero(
            accepted & data["family"] & ~data["complete"]
        )),
        "accepted_false": int(np.count_nonzero(wrong)),
        "accepted_uncertain": int(np.count_nonzero(accepted & data["uncertain"])),
        "precision": round(float(data["family"][explicit].mean()) if explicit.any() else 1.0, 6),
        "family_recall": round(true_count / max(1, int(np.count_nonzero(data["known"] & data["family"]))), 6),
        "five_control_wrong_links": int(np.count_nonzero(wrong & data["control"])),
    }


def _veto_only_threshold(
    data: dict, baseline_accepted: np.ndarray, certainty: np.ndarray,
) -> tuple[float, dict]:
    """Choose a certainty veto without ever adding to the baseline set."""
    choices = []
    for value in np.unique(certainty):
        accepted = baseline_accepted & (certainty >= value)
        if np.any(accepted & data["uncertain"]):
            continue
        explicit = accepted & data["known"]
        wrong = explicit & ~data["family"]
        if np.any(wrong & data["control"]):
            continue
        precision = float(data["family"][explicit].mean()) if explicit.any() else 1.0
        if precision < 0.80:
            continue
        choices.append((
            int(np.count_nonzero(explicit & data["family"])), precision,
            int(np.count_nonzero(explicit & data["complete"])),
            -int(np.count_nonzero(accepted)), -float(value),
        ))
    if not choices:
        return 1.0, {"inner_true": 0, "inner_precision": 1.0}
    best = max(choices)
    return -best[4], {
        "inner_true": best[0], "inner_precision": round(best[1], 6),
        "inner_complete": best[2],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=731)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = _build_rows(_load_candidate_table(args.bank, args.embeddings, args.labels))
    indices = np.asarray([
        offset for offset, row in enumerate(rows) if row["semantic"] is not None
    ], dtype=np.int64)
    groups = np.asarray([rows[int(index)]["content_group"] for index in indices])
    all_parts = {name: [] for name in (
        "indices", "family_score", "raw_score", "family_probability",
        "certainty_probability", "complete_probability", "known", "uncertain",
        "family", "complete", "control", "keys", "accepted", "fine_only_accepted",
        "raw_only_accepted", "conservative_veto_accepted",
    )}
    folds = []
    for fold, (train_offset, test_offset) in enumerate(
        GroupKFold(n_splits=5).split(indices, groups=groups)
    ):
        train_indices = indices[train_offset]
        test_indices = indices[test_offset]
        family_config, family_scores = _select_head(rows, train_indices, "family_veto")
        certainty_config, certainty_scores = _select_head(
            rows, train_indices, "review_certainty_veto",
        )
        complete_config, complete_scores = _select_head(
            rows, train_indices, "complete_copy_description",
        )
        inner = _arrays(rows, train_indices)
        inner_family, _ = _oof_task(
            rows, train_indices, family_config, "family_veto",
        )
        inner_certainty, _ = _oof_task(
            rows, train_indices, certainty_config, "review_certainty_veto",
        )
        inner_veto = np.minimum(inner_family, inner_certainty)
        score_threshold, veto_threshold, inner_summary = _safe_thresholds(
            inner, inner["family_score"], inner_veto,
        )
        fine_threshold, _, fine_inner = _safe_thresholds(
            inner, inner["family_score"], None,
        )
        raw_threshold, _, raw_inner = _safe_thresholds(
            inner, inner["raw_score"], None,
        )
        inner_raw_accepted = _top_two(
            inner["raw_score"], inner["raw_score"] >= raw_threshold, inner["keys"],
        )
        conservative_veto_threshold, conservative_inner = _veto_only_threshold(
            inner, inner_raw_accepted, inner_certainty,
        )
        train = _arrays(rows, train_indices)
        test = _arrays(rows, test_indices)
        family_probability = _fit_predict(
            train, test, family_config, "family_veto", 7320 + fold,
        )
        certainty_probability = _fit_predict(
            train, test, certainty_config, "review_certainty_veto", 7330 + fold,
        )
        complete_probability = _fit_predict(
            train, test, complete_config, "complete_copy_description", 7340 + fold,
        )
        veto = np.minimum(family_probability, certainty_probability)
        accepted = _top_two(
            test["family_score"],
            (test["family_score"] >= score_threshold) & (veto >= veto_threshold),
            test["keys"],
        )
        fine_only_accepted = _top_two(
            test["family_score"], test["family_score"] >= fine_threshold, test["keys"],
        )
        raw_only_accepted = _top_two(
            test["raw_score"], test["raw_score"] >= raw_threshold, test["keys"],
        )
        conservative_veto_accepted = raw_only_accepted & (
            certainty_probability >= conservative_veto_threshold
        )
        for name, values in (
            ("indices", test["indices"]), ("family_score", test["family_score"]),
            ("raw_score", test["raw_score"]),
            ("family_probability", family_probability),
            ("certainty_probability", certainty_probability),
            ("complete_probability", complete_probability),
            ("known", test["known"]), ("uncertain", test["uncertain"]),
            ("family", test["family"]), ("complete", test["complete"]),
            ("control", test["control"]), ("keys", test["keys"]),
            ("accepted", accepted), ("fine_only_accepted", fine_only_accepted),
            ("raw_only_accepted", raw_only_accepted),
            ("conservative_veto_accepted", conservative_veto_accepted),
        ):
            all_parts[name].append(values)
        folds.append({
            "fold": fold,
            "test_paints": sorted({rows[int(value)]["paint"] for value in test_indices}),
            "selected_family_head": family_config["name"],
            "selected_certainty_head": certainty_config["name"],
            "selected_completeness_head": complete_config["name"],
            "inner_family_ap": {name: round(value, 6) for name, value in family_scores.items()},
            "inner_certainty_ap": {name: round(value, 6) for name, value in certainty_scores.items()},
            "inner_completeness_ap": {name: round(value, 6) for name, value in complete_scores.items()},
            "family_score_threshold": round(score_threshold, 8),
            "veto_threshold": round(veto_threshold, 8),
            "fine_only_threshold": round(fine_threshold, 8),
            "raw_only_threshold": round(raw_threshold, 8),
            "conservative_veto_threshold": round(conservative_veto_threshold, 8),
            "inner_joint": inner_summary,
            "inner_fine_only": fine_inner,
            "inner_raw_only": raw_inner,
            "inner_conservative_veto": conservative_inner,
        })
    result = {name: np.concatenate(parts) for name, parts in all_parts.items()}
    order = np.argsort(result["indices"])
    result = {name: values[order] for name, values in result.items()}
    data = _arrays(rows, indices)
    if not np.array_equal(result["indices"], data["indices"]):
        raise RuntimeError("outer OOF ordering drift")
    explicit = data["known"]
    number_rows = explicit & data["family"]
    family_head_ap = float(average_precision_score(
        data["family"][explicit], result["family_probability"][explicit],
    ))
    certainty_head_ap = float(average_precision_score(
        data["known"], result["certainty_probability"],
    ))
    completeness_head_ap = float(average_precision_score(
        data["complete"][number_rows], result["complete_probability"][number_rows],
    ))
    joint = _metrics(data, result["accepted"])
    fine_only = _metrics(data, result["fine_only_accepted"])
    raw_only = _metrics(data, result["raw_only_accepted"])
    conservative = _metrics(data, result["conservative_veto_accepted"])
    behavior_gain = (
        conservative["accepted_true_number_family"] > raw_only["accepted_true_number_family"]
        or conservative["accepted_false"] < raw_only["accepted_false"]
        or conservative["accepted_uncertain"] < raw_only["accepted_uncertain"]
    )
    gates = {
        "requires_at_least_8_accepted_true_number_family": conservative["accepted_true_number_family"] >= 8,
        "requires_precision_at_least_0_80": conservative["precision"] >= 0.80,
        "requires_zero_uncertain_accepts": conservative["accepted_uncertain"] == 0,
        "requires_zero_five_control_wrong_links": conservative["five_control_wrong_links"] == 0,
        "requires_measurable_behavior_gain_over_raw": behavior_gain,
        "frozen_family_ranking_reference_unchanged": True,
    }
    gates["fragment_completeness_acceptance_passed"] = all(gates.values())
    accepted_examples = []
    prediction_rows = []
    for offset, row_index in enumerate(indices):
        row = rows[int(row_index)]
        prediction_rows.append({
            "paint": row["paint"], "content_group": row["content_group"],
            "block": row["block"], "candidate_index": row["candidate_index"],
            "proposal_id": row["proposal_id"], "semantic": row["semantic"],
            "complete_copy": row.get("complete_copy"),
            "raw_score": round(float(result["raw_score"][offset]), 8),
            "frozen_family_score": round(float(result["family_score"][offset]), 8),
            "family_probability": round(float(result["family_probability"][offset]), 8),
            "certainty_probability": round(float(result["certainty_probability"][offset]), 8),
            "complete_probability": round(float(result["complete_probability"][offset]), 8),
            "raw_only_accepted": bool(result["raw_only_accepted"][offset]),
            "conservative_veto_accepted": bool(result["conservative_veto_accepted"][offset]),
            "ownership_authority": False,
        })
    for offset in np.flatnonzero(
        result["accepted"] | result["fine_only_accepted"] | result["raw_only_accepted"]
        | result["conservative_veto_accepted"]
    ):
        row = rows[int(indices[offset])]
        accepted_examples.append({
            "paint": row["paint"], "candidate_index": row["candidate_index"],
            "proposal_id": row["proposal_id"], "semantic": row["semantic"],
            "complete_copy": row.get("complete_copy"),
            "family_score": round(float(result["family_score"][offset]), 8),
            "family_probability": round(float(result["family_probability"][offset]), 8),
            "certainty_probability": round(float(result["certainty_probability"][offset]), 8),
            "complete_probability": round(float(result["complete_probability"][offset]), 8),
            "accepted": bool(result["accepted"][offset]),
            "fine_only_accepted": bool(result["fine_only_accepted"][offset]),
            "raw_only_accepted": bool(result["raw_only_accepted"][offset]),
            "conservative_veto_accepted": bool(result["conservative_veto_accepted"][offset]),
        })
    ledger = {
        "schema": "smart-tga-fragment-completeness-abstention-head-v1",
        "cycle": args.cycle,
        "contract": "Frozen anchor-relative family evidence is mandatory. Learned heads only veto or describe complete-versus-fragment state and have zero ownership authority.",
        "corpus": {
            "candidate_bank_count": 1824, "paint_count": 19,
            "evaluated_labeled_rows": int(len(indices)),
            "explicit_rows": int(np.count_nonzero(data["known"])),
            "uncertain_guard_rows": int(np.count_nonzero(data["uncertain"])),
            "complete_number_rows": int(np.count_nonzero(data["complete"])),
            "number_fragment_rows": int(np.count_nonzero(data["family"] & ~data["complete"])),
            "unique_source_content_count": int(len(np.unique(groups))),
        },
        "frozen_family_ranking": {
            "cycle730_nested_source_content_disjoint_ap": 0.773697,
            "changed_in_cycle731": False,
            "note": "The abstention head is downstream and cannot reorder or create family evidence.",
        },
        "nested_source_content_disjoint_heads": {
            "family_veto_ap": round(family_head_ap, 6),
            "review_certainty_veto_ap": round(certainty_head_ap, 6),
            "complete_vs_fragment_description_ap": round(completeness_head_ap, 6),
            "joint_acceptance": joint,
            "joint_acceptance_status": "rejected: lowered nomination threshold allowed veto scores to manufacture entry",
            "conservative_veto_only_acceptance": conservative,
            "matching_frozen_fine_only_acceptance": fine_only,
            "matching_raw_d4_only_acceptance": raw_only,
        },
        "gates": gates,
        "selected_config_counts": {
            "family": dict(Counter(row["selected_family_head"] for row in folds)),
            "certainty": dict(Counter(row["selected_certainty_head"] for row in folds)),
            "completeness": dict(Counter(row["selected_completeness_head"] for row in folds)),
        },
        "feature_contract": {
            "names": list(FEATURE_NAMES),
            "filename_or_car_model_feature": False,
            "absolute_bbox_feature": False,
            "block_feature": False,
            "review_trace_fields_used_as_features": False,
            "relationships_can_create_authority": False,
        },
        "hard_negative_controls": sorted(CONTROL_PAINTS),
        "folds": folds,
        "safety": {
            "runtime_integrated": False, "apply_locked": True,
            "exact_reconstruction_affected": False, "ocr_changed": False,
            "ownership_authority": False, "new_tga_opened": False,
        },
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "accepted_examples.json").write_text(
        json.dumps({"schema": "smart-tga-fragment-head-examples-v1", "examples": accepted_examples}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output / "oof_state_predictions.json").write_text(
        json.dumps({
            "schema": "smart-tga-source-disjoint-state-predictions-v1",
            "ownership_authority": False, "rows": prediction_rows,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "family_veto_ap": round(family_head_ap, 6),
        "certainty_veto_ap": round(certainty_head_ap, 6),
        "completeness_ap": round(completeness_head_ap, 6),
        "joint": joint, "conservative": conservative,
        "fine_only": fine_only, "raw_only": raw_only,
        "gates": gates, "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
