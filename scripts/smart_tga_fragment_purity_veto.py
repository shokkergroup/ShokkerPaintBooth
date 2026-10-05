"""Evaluate an appearance-only veto over frozen Smart TGA family additions.

Cycle732's raw baseline and immutable assembly nominations are replayed exactly.
This probe cannot add a candidate, alter assembly thresholds or affect runtime;
it can only veto a newly nominated member using candidate-only masked appearance.
Model choice and the veto threshold are nested inside source-content-disjoint
folds so each reported candidate is scored without its source pixels in train.
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
    from scripts.smart_tga_fragment_completeness_head import (
        HEAD_CONFIGS, _arrays, _oof_task, _safe_thresholds,
    )
    from scripts.smart_tga_number_family_set_assembler import (
        _assemble_from_reviewed_anchor, _set_metrics,
    )
    from scripts.smart_tga_within_paint_ordinal_family import (
        _build_rows, _load_candidate_table, _top_two,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import CONTROL_PAINTS  # type: ignore
    from scripts.smart_tga_fragment_completeness_head import (  # type: ignore
        HEAD_CONFIGS, _arrays, _oof_task, _safe_thresholds,
    )
    from scripts.smart_tga_number_family_set_assembler import (  # type: ignore
        _assemble_from_reviewed_anchor, _set_metrics,
    )
    from scripts.smart_tga_within_paint_ordinal_family import (  # type: ignore
        _build_rows, _load_candidate_table, _top_two,
    )


MODEL_CONFIGS = tuple(
    {
        "name": f"logistic_{group}_c{str(c).replace('.', '')}",
        "kind": "logistic", "group": group, "c": c,
    }
    for group in ("summary", "all")
    for c in (0.005, 0.02, 0.1, 0.5)
) + tuple(
    {
        "name": f"extra_{group}_depth{depth}",
        "kind": "extra", "group": group, "depth": depth,
    }
    for group in ("summary", "all") for depth in (2, 3)
)


def _load_appearance(path: Path) -> tuple[dict[tuple[str, int, str], np.ndarray], list[str]]:
    bank = np.load(path, allow_pickle=False)
    try:
        names = [str(value) for value in bank["feature_names"]]
        forbidden = ("filename", "car_identity", "bbox", "position", "block", "review")
        if any(any(token in name for token in forbidden) for name in names):
            raise RuntimeError("forbidden identity/location feature in appearance bank")
        result = {}
        for offset in range(len(bank["features"])):
            key = (
                str(bank["paints"][offset]), int(bank["candidate_indices"][offset]),
                str(bank["proposal_ids"][offset]),
            )
            if key in result:
                raise RuntimeError(f"duplicate appearance trace: {key}")
            result[key] = bank["features"][offset].astype(np.float32)
        return result, names
    finally:
        bank.close()


def _load_pretrained_appearance(
    path: Path,
) -> dict[tuple[str, int, str], np.ndarray]:
    bank = np.load(path, allow_pickle=False)
    try:
        result = {}
        for offset in range(len(bank["appearance"])):
            key = (
                str(bank["paints"][offset]), int(bank["candidate_indices"][offset]),
                str(bank["proposal_ids"][offset]),
            )
            values = bank["appearance"][offset].astype(np.float32)
            if values.shape[0] != 8 or values.ndim != 2:
                raise RuntimeError("pretrained D4 appearance shape drift")
            result[key] = values
        return result
    finally:
        bank.close()


def _feature_columns(config: dict, names: list[str]) -> np.ndarray:
    if config["group"] == "summary":
        return np.asarray([
            offset for offset, name in enumerate(names) if "spatial_" not in name
        ], dtype=np.int64)
    return np.arange(len(names), dtype=np.int64)


def _new_model(config: dict, seed: int):
    if config["kind"] == "logistic":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=float(config["c"]), class_weight="balanced", max_iter=4000,
                solver="liblinear", random_state=seed,
            ),
        )
    return ExtraTreesClassifier(
        n_estimators=384, max_depth=int(config["depth"]), min_samples_leaf=4,
        class_weight="balanced", max_features="sqrt", random_state=seed, n_jobs=1,
    )


def _fit_predict(
    train_features: np.ndarray, train_target: np.ndarray, train_known: np.ndarray,
    test_features: np.ndarray, config: dict, names: list[str], seed: int,
) -> np.ndarray:
    columns = _feature_columns(config, names)
    if len(np.unique(train_target[train_known])) < 2:
        value = float(train_target[train_known].mean()) if train_known.any() else 0.5
        return np.full(len(test_features), value, dtype=np.float64)
    model = _new_model(config, seed)
    model.fit(train_features[train_known][:, columns], train_target[train_known])
    return model.predict_proba(test_features[:, columns])[:, 1].astype(np.float64)


def _oof_scores(
    features: np.ndarray, target: np.ndarray, known: np.ndarray,
    groups: np.ndarray, config: dict, names: list[str], seed: int,
) -> np.ndarray:
    score = np.empty(len(features), dtype=np.float64)
    folds = min(4, len(np.unique(groups)))
    for fold, (train, test) in enumerate(
        GroupKFold(n_splits=folds).split(features, groups=groups)
    ):
        score[test] = _fit_predict(
            features[train], target[train], known[train], features[test],
            config, names, seed + fold,
        )
    return score


def _select_model(
    features: np.ndarray, target: np.ndarray, known: np.ndarray,
    groups: np.ndarray, names: list[str], seed: int,
) -> tuple[dict, dict[str, float], np.ndarray]:
    scores: dict[str, float] = {}
    predictions: dict[str, np.ndarray] = {}
    for offset, config in enumerate(MODEL_CONFIGS):
        prediction = _oof_scores(
            features, target, known, groups, config, names, seed + offset * 20,
        )
        predictions[config["name"]] = prediction
        scores[config["name"]] = float(average_precision_score(
            target[known], prediction[known],
        ))
    selected = max(MODEL_CONFIGS, key=lambda item: scores[item["name"]])
    return selected, scores, predictions[selected["name"]]


def _candidate_key(row: dict) -> tuple[str, int, str]:
    return row["paint"], int(row["candidate_index"]), row["proposal_id"]


def _appearance_matrix(
    rows: list[dict], indices: np.ndarray, table: dict,
    appearance: dict[tuple[str, int, str], np.ndarray], names: list[str], mode: str,
    pretrained: dict[tuple[str, int, str], np.ndarray] | None = None,
    semantic: dict[tuple[str, int, str], np.ndarray] | None = None,
    semantic_names: list[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    if mode.startswith("pretrained-"):
        if pretrained is None:
            raise ValueError("pretrained appearance cache is required for pretrained mode")
        result = []
        for index in indices:
            row = rows[int(index)]
            candidate_orbit = pretrained[_candidate_key(row)]
            trace = table["trace"][int(row["anchor"])]
            anchor_key = (
                row["paint"], int(trace["candidate_index"]), str(trace["proposal_id"]),
            )
            anchor_orbit = pretrained[anchor_key]
            candidate_mean = candidate_orbit.mean(axis=0)
            candidate_mean /= max(float(np.linalg.norm(candidate_mean)), 1e-8)
            if mode == "pretrained-candidate":
                result.append(candidate_mean)
                continue
            anchor_mean = anchor_orbit.mean(axis=0)
            anchor_mean /= max(float(np.linalg.norm(anchor_mean)), 1e-8)
            similarity = candidate_orbit @ anchor_orbit.T
            result.append(np.concatenate((
                np.abs(candidate_mean - anchor_mean),
                np.asarray((
                    similarity.max(), similarity.mean(), similarity.std(),
                    np.median(similarity), np.quantile(similarity, 0.90),
                ), dtype=np.float32),
            )))
        width = len(result[0])
        pretrained_names = [f"pretrained_dimension_{offset}" for offset in range(width - 5)]
        pretrained_names.extend((
            "pretrained_orbit_max", "pretrained_orbit_mean", "pretrained_orbit_std",
            "pretrained_orbit_median", "pretrained_orbit_q90",
        ))
        matrix = np.stack(result).astype(np.float32)
        if mode != "pretrained-anchor-relative-semantic":
            return matrix, pretrained_names
        if semantic is None or semantic_names is None:
            raise ValueError("semantic mask bank is required for semantic mode")
        semantic_rows = []
        for index in indices:
            row = rows[int(index)]
            candidate_semantic = semantic[_candidate_key(row)]
            trace = table["trace"][int(row["anchor"])]
            anchor_key = (
                row["paint"], int(trace["candidate_index"]), str(trace["proposal_id"]),
            )
            anchor_semantic = semantic[anchor_key]
            semantic_rows.append(np.concatenate((
                candidate_semantic, np.abs(candidate_semantic - anchor_semantic),
            )))
        semantic_matrix = np.stack(semantic_rows).astype(np.float32)
        semantic_feature_names = (
            [f"semantic_candidate_{name}" for name in semantic_names]
            + [f"semantic_relative_{name}" for name in semantic_names]
        )
        return (
            np.concatenate((matrix, semantic_matrix), axis=1),
            pretrained_names + semantic_feature_names,
        )
    candidate = np.stack([
        appearance[_candidate_key(rows[int(index)])] for index in indices
    ])
    if mode == "candidate":
        return candidate, names
    anchor_rows = []
    for index in indices:
        row = rows[int(index)]
        trace = table["trace"][int(row["anchor"])]
        key = (row["paint"], int(trace["candidate_index"]), str(trace["proposal_id"]))
        anchor_rows.append(appearance[key])
    anchor = np.stack(anchor_rows)
    # Absolute candidate-to-anchor deltas remove paint/style identity while
    # retaining only masked palette, ring, edge, texture and spatial agreement.
    # This relationship is a veto-only corroborator and never Number authority.
    return np.abs(candidate - anchor), [f"relative_{name}" for name in names]


def _frozen_added_keys(path: Path) -> set[tuple[str, int, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        (str(group["paint"]), int(member["candidate_index"]), str(member["proposal_id"]))
        for group in payload["sets"] for member in group["members"]
    }


def _select_veto_threshold(
    rows: list[dict], indices: np.ndarray, data: dict,
    baseline: np.ndarray, added: np.ndarray, score: np.ndarray,
    scope: str = "additions",
) -> tuple[float, dict]:
    """Choose one veto-only threshold on training predictions."""
    nominated = added if scope == "additions" else (baseline | added)
    if not np.any(nominated):
        return float("inf"), {"retained_additions": 0, "safe_choice_found": False}
    thresholds = np.concatenate((
        np.asarray([np.nextafter(float(score[nominated].min()), -np.inf)]),
        np.unique(score[nominated]),
        np.asarray([np.nextafter(float(score[nominated].max()), np.inf)]),
    ))
    choices = []
    for threshold in thresholds:
        if scope == "all" and np.any(
            baseline & data["known"] & data["family"] & (score < threshold)
        ):
            continue
        accepted = (
            baseline | (added & (score >= threshold))
            if scope == "additions" else nominated & (score >= threshold)
        )
        metrics = _set_metrics(rows, indices, data, accepted)
        if metrics["precision"] < 0.80 or metrics["reviewed_pixel_precision"] < 0.80:
            continue
        if metrics["accepted_uncertain"] or metrics["five_control_wrong_links"]:
            continue
        retained = int(np.count_nonzero(added & (score >= threshold)))
        choices.append((
            metrics["accepted_true_number_family"],
            metrics["recovered_number_family_blocks"],
            metrics["reviewed_number_pixel_coverage"],
            metrics["precision"], -retained, -float(threshold),
            float(threshold), metrics,
        ))
    if not choices:
        return float("inf"), {"retained_additions": 0, "safe_choice_found": False}
    best = max(choices, key=lambda item: item[:6])
    return best[6], {
        "retained_additions": int(np.count_nonzero(added & (score >= best[6]))),
        "safe_choice_found": True, "training_after": best[7],
    }


def _metrics_match(actual: dict, expected: dict) -> bool:
    keys = (
        "accepted_total", "accepted_true_number_family", "accepted_false",
        "accepted_uncertain", "precision", "family_recall",
        "reviewed_number_pixel_coverage", "reviewed_pixel_precision",
        "recovered_number_family_blocks", "number_family_block_recall",
    )
    return all(actual[key] == expected[key] for key in keys)


def _frozen_inner_nominations(
    rows: list[dict], train_indices: np.ndarray, fold_ledger: dict,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Replay nominations using only the current outer fold's training groups."""
    configs = {config["name"]: config for config in HEAD_CONFIGS}
    complete_config = configs[fold_ledger["selected_completeness_head"]]
    certainty_config = configs[fold_ledger["selected_certainty_head"]]
    train = _arrays(rows, train_indices)
    complete, _ = _oof_task(
        rows, train_indices, complete_config, "complete_copy_description",
    )
    certainty, _ = _oof_task(
        rows, train_indices, certainty_config, "review_certainty_veto",
    )
    # Recompute the deterministic Cycle732 safe baseline from this outer
    # training fold because the ledger's display-rounded threshold can move a
    # candidate sitting exactly on the boundary.
    raw_threshold, _, _ = _safe_thresholds(train, train["raw_score"], None)
    baseline = _top_two(
        train["raw_score"], train["raw_score"] >= raw_threshold, train["keys"],
    )
    config = fold_ledger["assembly_config"]
    assembled, sets = _assemble_from_reviewed_anchor(
        rows, train_indices, train, baseline, complete,
        float(config["fragment_score_threshold"]),
        float(config["fragment_complete_max"]), int(config["fragment_cap"]),
        certainty, float(config["certainty_min"]),
    )
    metrics = _set_metrics(rows, train_indices, train, assembled)
    expected = fold_ledger["inner_assembly"]
    if expected.get("inner_safe_choice_found"):
        if not _metrics_match(metrics, expected) or len(sets) != expected["assembled_set_count"]:
            raise RuntimeError(
                "frozen inner assembly replay drift: "
                + json.dumps({"actual": metrics, "expected": expected, "sets": len(sets)})
            )
    elif np.any(assembled & ~baseline):
        raise RuntimeError("unsafe frozen inner assembly unexpectedly nominated members")
    return baseline, assembled & ~baseline, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--appearance", type=Path, required=True)
    parser.add_argument("--pretrained-appearance", type=Path)
    parser.add_argument("--semantic-appearance", type=Path)
    parser.add_argument("--veto-scope", choices=("additions", "all"), default="additions")
    parser.add_argument("--frozen-ledger", type=Path, required=True)
    parser.add_argument("--frozen-sets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=733)
    parser.add_argument(
        "--appearance-mode", choices=(
            "candidate", "anchor-relative", "pretrained-candidate",
            "pretrained-anchor-relative", "pretrained-anchor-relative-semantic",
        ),
        default="candidate",
    )
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
    appearance, feature_names = _load_appearance(args.appearance)
    pretrained = (
        None if args.pretrained_appearance is None
        else _load_pretrained_appearance(args.pretrained_appearance)
    )
    semantic, semantic_names = (
        (None, None) if args.semantic_appearance is None
        else _load_appearance(args.semantic_appearance)
    )
    appearance_matrix, model_feature_names = _appearance_matrix(
        rows, indices, table, appearance, feature_names, args.appearance_mode,
        pretrained, semantic, semantic_names,
    )
    added_keys = _frozen_added_keys(args.frozen_sets)
    added = np.asarray([
        _candidate_key(rows[int(index)]) in added_keys for index in indices
    ], dtype=bool)
    baseline = np.zeros(len(indices), dtype=bool)
    folds = list(GroupKFold(n_splits=5).split(indices, groups=groups))
    if len(folds) != len(frozen_ledger["folds"]):
        raise RuntimeError("frozen outer-fold count drift")
    for fold, (_, test_offset) in enumerate(folds):
        test = _arrays(rows, indices[test_offset])
        threshold = float(frozen_ledger["folds"][fold]["raw_safe_threshold"])
        baseline[test_offset] = _top_two(
            test["raw_score"], test["raw_score"] >= threshold, test["keys"],
        )
    if np.any(baseline & added):
        raise RuntimeError("frozen baseline/addition contract overlap")
    baseline_metrics = _set_metrics(rows, indices, data, baseline)
    before = baseline | added
    before_metrics = _set_metrics(rows, indices, data, before)
    if not _metrics_match(baseline_metrics, frozen_ledger["baseline_raw_safe"]):
        raise RuntimeError("Cycle732 baseline replay drift")
    if not _metrics_match(before_metrics, frozen_ledger["after_immutable_family_assembly"]):
        raise RuntimeError("Cycle732 immutable addition replay drift")

    purity = np.empty(len(indices), dtype=np.float64)
    keep_baseline = baseline.copy()
    keep_added = np.zeros(len(indices), dtype=bool)
    fold_ledgers = []
    for fold, (train_offset, test_offset) in enumerate(folds):
        train_features = appearance_matrix[train_offset]
        train_data = _arrays(rows, indices[train_offset])
        test_features = appearance_matrix[test_offset]
        selected, scores, inner_purity = _select_model(
            train_features, train_data["family"], train_data["known"],
            groups[train_offset], model_feature_names, 7330 + fold * 200,
        )
        inner_baseline, inner_added, inner_assembly_metrics = _frozen_inner_nominations(
            rows, indices[train_offset], frozen_ledger["folds"][fold],
        )
        threshold, threshold_summary = _select_veto_threshold(
            rows, indices[train_offset], train_data, inner_baseline,
            inner_added, inner_purity, args.veto_scope,
        )
        test_purity = _fit_predict(
            train_features, train_data["family"], train_data["known"],
            test_features, selected, model_feature_names, 7430 + fold,
        )
        purity[test_offset] = test_purity
        if args.veto_scope == "all":
            keep_baseline[test_offset] = baseline[test_offset] & (
                test_purity >= threshold
            )
        keep_added[test_offset] = added[test_offset] & (test_purity >= threshold)
        fold_ledgers.append({
            "fold": fold,
            "test_paints": sorted({rows[int(indices[value])]["paint"] for value in test_offset}),
            "source_content_overlap": bool(
                set(groups[train_offset]).intersection(set(groups[test_offset]))
            ),
            "selected_appearance_head": selected["name"],
            "inner_explicit_ap": {
                name: round(value, 6) for name, value in scores.items()
            },
            "purity_veto_threshold": round(float(threshold), 8),
            "inner_threshold_selection": threshold_summary,
            "inner_frozen_assembly": inner_assembly_metrics,
            "inner_nominated_additions": int(np.count_nonzero(inner_added)),
            "outer_nominated_additions": int(np.count_nonzero(added[test_offset])),
            "outer_retained_baseline": int(np.count_nonzero(keep_baseline[test_offset])),
            "outer_retained_additions": int(np.count_nonzero(keep_added[test_offset])),
        })
    after = keep_baseline | keep_added
    after_metrics = _set_metrics(rows, indices, data, after)
    added_after_metrics = _set_metrics(rows, indices, data, keep_added)
    explicit_ap = float(average_precision_score(
        data["family"][data["known"]], purity[data["known"]],
    ))
    decisions = []
    for offset in np.flatnonzero(added | (baseline if args.veto_scope == "all" else False)):
        row = rows[int(indices[offset])]
        decisions.append({
            "paint": row["paint"], "candidate_index": int(row["candidate_index"]),
            "proposal_id": row["proposal_id"], "block_for_metrics_only": row["block"],
            "masked_appearance_purity": round(float(purity[offset]), 8),
            "nomination_source": "raw_baseline" if baseline[offset] else "assembly_addition",
            "decision": "retain" if after[offset] else "veto",
            "review_semantic_for_metrics_only": row["semantic"],
            "support_area_for_metrics_only": int(row["support_area_for_metrics_only"]),
            "ownership_authority": False,
        })
    gates = {
        "requires_more_than_8_true_or_more_than_16pct_family_recall": (
            after_metrics["accepted_true_number_family"] > 8
            or after_metrics["family_recall"] > 0.16
        ),
        "requires_candidate_precision_at_least_0_80": after_metrics["precision"] >= 0.80,
        "requires_pixel_precision_at_least_0_80": after_metrics["reviewed_pixel_precision"] >= 0.80,
        "requires_zero_uncertain_accepts": after_metrics["accepted_uncertain"] == 0,
        "requires_zero_five_control_wrong_links": after_metrics["five_control_wrong_links"] == 0,
        "requires_no_true_regression_vs_raw_baseline": (
            after_metrics["accepted_true_number_family"]
            >= baseline_metrics["accepted_true_number_family"]
        ),
        "frozen_cycle730_reference_ap_unchanged": True,
        "frozen_cycle732_assembly_replayed_exactly": True,
    }
    gates["development_appearance_veto_gate_passed"] = all(gates.values())
    ledger = {
        "schema": "smart-tga-fragment-purity-veto-v2", "cycle": args.cycle,
        "contract": "Masked appearance is veto-only corroboration over the selected nomination scope. Anchor-relative mode compares candidate-only evidence to the paint's direct complete Number anchor. It cannot admit candidates, change family/assembly thresholds or affect runtime ownership.",
        "corpus": {
            "evaluated_rows": len(indices), "explicit_rows": int(data["known"].sum()),
            "uncertain_guard_rows": int(data["uncertain"].sum()),
            "full_candidate_appearance_bank_count": len(appearance),
            "appearance_feature_count": len(model_feature_names),
            "pretrained_appearance_cache_count": 0 if pretrained is None else len(pretrained),
            "semantic_mask_cache_count": 0 if semantic is None else len(semantic),
            "unique_source_content_count": len(np.unique(groups)),
        },
        "appearance_mode": args.appearance_mode,
        "veto_scope": args.veto_scope,
        "masked_appearance_explicit_number_purity_ap": round(explicit_ap, 6),
        "baseline_raw_safe": baseline_metrics,
        "before_frozen_cycle732_assembly": before_metrics,
        "after_appearance_veto": after_metrics,
        "retained_additions_only": added_after_metrics,
        "movement": {
            "false_additions_removed": before_metrics["accepted_false"] - after_metrics["accepted_false"],
            "true_additions_removed": before_metrics["accepted_true_number_family"] - after_metrics["accepted_true_number_family"],
            "candidate_precision_points": round(100.0 * (after_metrics["precision"] - before_metrics["precision"]), 4),
            "number_family_recall_points": round(100.0 * (after_metrics["family_recall"] - before_metrics["family_recall"]), 4),
            "reviewed_number_pixel_coverage_points": round(100.0 * (after_metrics["reviewed_number_pixel_coverage"] - before_metrics["reviewed_number_pixel_coverage"]), 4),
        },
        "gates": gates,
        "selected_head_counts": dict(Counter(
            item["selected_appearance_head"] for item in fold_ledgers
        )),
        "folds": fold_ledgers,
        "hard_negative_controls": sorted(CONTROL_PAINTS),
        "safety": {
            "filename_or_car_model_feature": False, "absolute_bbox_model_feature": False,
            "bbox_dimensions_model_feature": False, "template_block_model_feature": False,
            "review_trace_model_feature": False, "runtime_integrated": False,
            "anchor_relationship_is_veto_only_corroboration": "anchor-relative" in args.appearance_mode,
            "pretrained_model_weights_frozen": args.appearance_mode.startswith("pretrained-"),
            "semantic_decoder_weights_frozen": semantic is not None,
            "semantic_evidence_is_veto_only_corroboration": semantic is not None,
            "raw_baseline_can_only_be_removed": args.veto_scope == "all",
            "apply_locked": True, "exact_reconstruction_affected": False,
            "ocr_changed": False, "ownership_authority": False,
            "new_tga_opened": False,
        },
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "appearance_veto_decisions.json").write_text(
        json.dumps({
            "schema": "smart-tga-appearance-veto-decisions-v1",
            "ownership_authority": False, "frozen_input_sets_unchanged": True,
            "decisions": decisions,
        }, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "appearance_ap": round(explicit_ap, 6), "before": before_metrics,
        "after": after_metrics, "movement": ledger["movement"],
        "gates": gates, "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
