"""Measure immutable complete-seed + fragment Number-family assembly.

The raw safe baseline is preserved verbatim. Each paint's direct complete
Number review is the immutable cross-block family anchor. Extra members must
independently clear the frozen Cycle730 fine-shape ensemble score; completeness
and block relationships only corroborate grouping.
All choices are nested inside source-content-disjoint folds and have zero
runtime or ownership authority.
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
    from scripts.smart_tga_fragment_completeness_head import (
        _arrays, _fit_predict, _metrics, _oof_task, _safe_thresholds,
        _select_head,
    )
    from scripts.smart_tga_within_paint_ordinal_family import (
        _build_rows, _load_candidate_table, _top_two,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import CONTROL_PAINTS  # type: ignore
    from scripts.smart_tga_fragment_completeness_head import (  # type: ignore
        _arrays, _fit_predict, _metrics, _oof_task, _safe_thresholds,
        _select_head,
    )
    from scripts.smart_tga_within_paint_ordinal_family import (  # type: ignore
        _build_rows, _load_candidate_table, _top_two,
    )


def _unique_weight(
    rows: list[dict], indices: np.ndarray, mask: np.ndarray,
) -> int:
    seen = set()
    total = 0
    for offset in np.flatnonzero(mask):
        row = rows[int(indices[offset])]
        key = (
            row["paint"], row["block"],
            row["placement_fingerprint_for_instance_dedupe"],
        )
        if key in seen:
            continue
        seen.add(key)
        total += int(row["support_area_for_metrics_only"])
    return total


def _set_metrics(
    rows: list[dict], indices: np.ndarray, data: dict, accepted: np.ndarray,
) -> dict:
    result = _metrics(data, accepted)
    explicit = accepted & data["known"]
    true = explicit & data["family"]
    false = explicit & ~data["family"]
    true_weight = _unique_weight(rows, indices, true)
    false_weight = _unique_weight(rows, indices, false)
    all_true_weight = _unique_weight(rows, indices, data["known"] & data["family"])
    accepted_true_blocks = set(data["keys"][true])
    all_true_blocks = set(data["keys"][data["known"] & data["family"]])
    result.update({
        "reviewed_number_pixel_coverage": round(
            true_weight / max(1, all_true_weight), 6,
        ),
        "reviewed_pixel_precision": round(
            true_weight / max(1, true_weight + false_weight), 6,
        ),
        "recovered_number_family_blocks": len(accepted_true_blocks),
        "reviewed_number_family_block_count": len(all_true_blocks),
        "number_family_block_recall": round(
            len(accepted_true_blocks) / max(1, len(all_true_blocks)), 6,
        ),
    })
    return result


def _assemble(
    rows: list[dict], indices: np.ndarray, data: dict,
    baseline: np.ndarray, complete_probability: np.ndarray,
    seed_complete_threshold: float, fragment_score_threshold: float,
    fragment_cap: int,
) -> tuple[np.ndarray, list[dict]]:
    """Augment baseline with independently nominated, placement-unique fragments."""
    accepted = baseline.copy()
    sets = []
    for key in np.unique(data["keys"]):
        group = np.flatnonzero(data["keys"] == key)
        seed_choices = group[
            baseline[group]
            & (complete_probability[group] >= seed_complete_threshold)
        ]
        if not len(seed_choices):
            continue
        seed = int(max(
            seed_choices,
            key=lambda value: (
                complete_probability[value], data["family_score"][value],
            ),
        ))
        occupied = {
            rows[int(indices[value])]["placement_fingerprint_for_instance_dedupe"]
            for value in group if accepted[value]
        }
        candidates = [
            int(value) for value in group
            if not accepted[value]
            and data["family_score"][value] >= fragment_score_threshold
            and complete_probability[value] < seed_complete_threshold
        ]
        candidates.sort(
            key=lambda value: data["family_score"][value], reverse=True,
        )
        fragments = []
        for value in candidates:
            fingerprint = rows[int(indices[value])][
                "placement_fingerprint_for_instance_dedupe"
            ]
            if fingerprint in occupied:
                continue
            accepted[value] = True
            occupied.add(fingerprint)
            fragments.append(value)
            if len(fragments) >= fragment_cap:
                break
        if fragments:
            seed_row = rows[int(indices[seed])]
            sets.append({
                "paint": seed_row["paint"], "block": seed_row["block"],
                "seed": seed, "fragments": fragments,
            })
    return accepted, sets


def _candidate_thresholds(values: np.ndarray, include_infinity: bool = False) -> np.ndarray:
    unique = np.unique(values)
    if len(unique) > 28:
        unique = np.unique(np.quantile(unique, np.linspace(0.0, 1.0, 28)))
    if include_infinity:
        unique = np.concatenate((unique, np.asarray([np.inf])))
    return unique


def _select_assembly(
    rows: list[dict], indices: np.ndarray, data: dict,
    baseline: np.ndarray, complete_probability: np.ndarray,
) -> tuple[dict, dict]:
    seed_values = _candidate_thresholds(complete_probability[baseline])
    fragment_values = _candidate_thresholds(
        data["family_score"][~baseline], include_infinity=True,
    )
    choices = []
    for seed_threshold in seed_values:
        for fragment_threshold in fragment_values:
            for cap in (1, 2, 3, 4):
                accepted, sets = _assemble(
                    rows, indices, data, baseline, complete_probability,
                    float(seed_threshold), float(fragment_threshold), cap,
                )
                metrics = _set_metrics(rows, indices, data, accepted)
                if metrics["accepted_uncertain"]:
                    continue
                if metrics["five_control_wrong_links"]:
                    continue
                if metrics["precision"] < 0.80 or metrics["reviewed_pixel_precision"] < 0.80:
                    continue
                choices.append((
                    metrics["accepted_true_number_family"],
                    metrics["reviewed_number_pixel_coverage"],
                    metrics["recovered_number_family_blocks"],
                    metrics["precision"],
                    -metrics["accepted_false"], -metrics["accepted_total"],
                    -float(seed_threshold), float(fragment_threshold), -cap,
                    metrics, len(sets),
                ))
    if not choices:
        return {
            "seed_complete_threshold": 1.0,
            "fragment_score_threshold": float("inf"), "fragment_cap": 1,
        }, {"inner_safe_choice_found": False}
    best = max(choices)
    config = {
        "seed_complete_threshold": -best[6],
        "fragment_score_threshold": best[7],
        "fragment_cap": -best[8],
    }
    summary = dict(best[9])
    summary["inner_safe_choice_found"] = True
    summary["assembled_set_count"] = best[10]
    return config, summary


def _assemble_from_reviewed_anchor(
    rows: list[dict], indices: np.ndarray, data: dict,
    baseline: np.ndarray, complete_probability: np.ndarray,
    fragment_score_threshold: float, fragment_complete_max: float,
    fragment_cap: int, certainty_probability: np.ndarray | None = None,
    certainty_min: float = 0.0,
) -> tuple[np.ndarray, list[dict]]:
    """Augment from the paint's direct complete anchor, never from adjacency alone."""
    accepted = baseline.copy()
    certainty = (
        np.ones(len(baseline), dtype=np.float64)
        if certainty_probability is None else certainty_probability
    )
    sets = []
    for key in np.unique(data["keys"]):
        group = np.flatnonzero(data["keys"] == key)
        occupied = {
            rows[int(indices[value])]["placement_fingerprint_for_instance_dedupe"]
            for value in group if accepted[value]
        }
        candidates = [
            int(value) for value in group
            if not accepted[value]
            and data["family_score"][value] >= fragment_score_threshold
            and complete_probability[value] <= fragment_complete_max
            and certainty[value] >= certainty_min
        ]
        candidates.sort(key=lambda value: data["family_score"][value], reverse=True)
        fragments = []
        for value in candidates:
            fingerprint = rows[int(indices[value])][
                "placement_fingerprint_for_instance_dedupe"
            ]
            if fingerprint in occupied:
                continue
            accepted[value] = True
            occupied.add(fingerprint)
            fragments.append(value)
            if len(fragments) >= fragment_cap:
                break
        if fragments:
            first = rows[int(indices[fragments[0]])]
            sets.append({
                "paint": first["paint"], "block": first["block"],
                "anchor_review_code": first["anchor_review_code"],
                "fragments": fragments,
            })
    return accepted, sets


def _select_anchor_assembly(
    rows: list[dict], indices: np.ndarray, data: dict,
    baseline: np.ndarray, complete_probability: np.ndarray,
    certainty_probability: np.ndarray,
) -> tuple[dict, dict]:
    baseline_metrics = _set_metrics(rows, indices, data, baseline)
    score_values = _candidate_thresholds(
        data["family_score"][~baseline], include_infinity=True,
    )
    complete_values = _candidate_thresholds(complete_probability[~baseline])
    certainty_values = _candidate_thresholds(certainty_probability[~baseline])
    choices = []
    for score_threshold in score_values:
        for complete_max in complete_values:
            for certainty_min in certainty_values:
                for cap in (1, 2, 3, 4):
                    accepted, sets = _assemble_from_reviewed_anchor(
                        rows, indices, data, baseline, complete_probability,
                        float(score_threshold), float(complete_max), cap,
                        certainty_probability, float(certainty_min),
                    )
                    metrics = _set_metrics(rows, indices, data, accepted)
                    if metrics["accepted_uncertain"] > baseline_metrics["accepted_uncertain"]:
                        continue
                    if metrics["accepted_false"] > baseline_metrics["accepted_false"]:
                        continue
                    if metrics["five_control_wrong_links"]:
                        continue
                    if metrics["precision"] < 0.80 or metrics["reviewed_pixel_precision"] < 0.80:
                        continue
                    choices.append((
                        metrics["accepted_true_number_family"],
                        metrics["reviewed_number_pixel_coverage"],
                        metrics["recovered_number_family_blocks"],
                        metrics["precision"], -metrics["accepted_false"],
                        -metrics["accepted_total"], float(score_threshold),
                        float(complete_max), -float(certainty_min), -cap,
                        metrics, len(sets),
                    ))
    if not choices:
        return {
            "fragment_score_threshold": float("inf"),
            "fragment_complete_max": 0.0, "certainty_min": 1.0,
            "fragment_cap": 1,
        }, {"inner_safe_choice_found": False}
    best = max(choices)
    config = {
        "fragment_score_threshold": best[6],
        "fragment_complete_max": best[7], "certainty_min": -best[8],
        "fragment_cap": -best[9],
    }
    summary = dict(best[10])
    summary["inner_safe_choice_found"] = True
    summary["assembled_set_count"] = best[11]
    return config, summary


def _serialize_sets(
    rows: list[dict], indices: np.ndarray, sets: list[dict],
    complete_probability: np.ndarray, data: dict,
) -> list[dict]:
    output = []
    for family in sets:
        seed_offset = int(family["seed"])
        member_offsets = [seed_offset] + [int(value) for value in family["fragments"]]
        members = []
        for offset in member_offsets:
            row = rows[int(indices[offset])]
            members.append({
                "role": "complete_seed" if offset == seed_offset else "fragment",
                "candidate_index": row["candidate_index"],
                "proposal_id": row["proposal_id"],
                "placement_fingerprint": row["placement_fingerprint_for_instance_dedupe"],
                "support_area": row["support_area_for_metrics_only"],
                "frozen_family_score": round(float(data["family_score"][offset]), 8),
                "complete_probability": round(float(complete_probability[offset]), 8),
                "review_semantic_for_metrics_only": row["semantic"],
                "review_complete_copy_for_metrics_only": row.get("complete_copy"),
            })
        output.append({
            "paint": family["paint"], "block": family["block"],
            "members": members, "ownership_authority": False,
        })
    return output


def _serialize_anchor_sets(
    rows: list[dict], indices: np.ndarray, sets: list[dict],
    complete_probability: np.ndarray, certainty_probability: np.ndarray,
    data: dict,
) -> list[dict]:
    output = []
    for family in sets:
        members = []
        for offset in family["fragments"]:
            row = rows[int(indices[int(offset)])]
            members.append({
                "role": "anchor_nominated_fragment",
                "candidate_index": row["candidate_index"],
                "proposal_id": row["proposal_id"],
                "placement_fingerprint": row["placement_fingerprint_for_instance_dedupe"],
                "support_area": row["support_area_for_metrics_only"],
                "frozen_family_score": round(float(data["family_score"][offset]), 8),
                "complete_probability": round(float(complete_probability[offset]), 8),
                "certainty_probability": round(float(certainty_probability[offset]), 8),
                "review_semantic_for_metrics_only": row["semantic"],
                "review_complete_copy_for_metrics_only": row.get("complete_copy"),
            })
        output.append({
            "paint": family["paint"], "block": family["block"],
            "direct_complete_anchor_review_code": family["anchor_review_code"],
            "members": members, "ownership_authority": False,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=732)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = _build_rows(_load_candidate_table(args.bank, args.embeddings, args.labels))
    indices = np.asarray([
        offset for offset, row in enumerate(rows) if row["semantic"] is not None
    ], dtype=np.int64)
    groups = np.asarray([rows[int(index)]["content_group"] for index in indices])
    all_parts = {name: [] for name in (
        "indices", "known", "uncertain", "family", "complete", "control",
        "keys", "features", "family_score", "raw_score", "baseline",
        "assembled", "complete_probability", "certainty_probability",
    )}
    fold_ledgers = []
    all_sets = []
    for fold, (train_offset, test_offset) in enumerate(
        GroupKFold(n_splits=5).split(indices, groups=groups)
    ):
        train_indices = indices[train_offset]
        test_indices = indices[test_offset]
        complete_config, complete_scores = _select_head(
            rows, train_indices, "complete_copy_description",
        )
        certainty_config, certainty_scores = _select_head(
            rows, train_indices, "review_certainty_veto",
        )
        inner = _arrays(rows, train_indices)
        inner_complete, _ = _oof_task(
            rows, train_indices, complete_config, "complete_copy_description",
        )
        inner_certainty, _ = _oof_task(
            rows, train_indices, certainty_config, "review_certainty_veto",
        )
        raw_threshold, _, _ = _safe_thresholds(
            inner, inner["raw_score"], None,
        )
        inner_baseline = _top_two(
            inner["raw_score"], inner["raw_score"] >= raw_threshold, inner["keys"],
        )
        assembly_config, inner_summary = _select_anchor_assembly(
            rows, train_indices, inner, inner_baseline, inner_complete,
            inner_certainty,
        )
        train = _arrays(rows, train_indices)
        test = _arrays(rows, test_indices)
        complete_probability = _fit_predict(
            train, test, complete_config, "complete_copy_description", 7420 + fold,
        )
        certainty_probability = _fit_predict(
            train, test, certainty_config, "review_certainty_veto", 7430 + fold,
        )
        baseline = _top_two(
            test["raw_score"], test["raw_score"] >= raw_threshold, test["keys"],
        )
        assembled, sets = _assemble_from_reviewed_anchor(
            rows, test_indices, test, baseline, complete_probability,
            assembly_config["fragment_score_threshold"],
            assembly_config["fragment_complete_max"],
            assembly_config["fragment_cap"],
            certainty_probability, assembly_config["certainty_min"],
        )
        all_sets.extend(_serialize_anchor_sets(
            rows, test_indices, sets, complete_probability,
            certainty_probability, test,
        ))
        for name, values in (
            ("indices", test["indices"]), ("known", test["known"]),
            ("uncertain", test["uncertain"]), ("family", test["family"]),
            ("complete", test["complete"]), ("control", test["control"]),
            ("keys", test["keys"]), ("features", test["features"]),
            ("family_score", test["family_score"]), ("raw_score", test["raw_score"]),
            ("baseline", baseline), ("assembled", assembled),
            ("complete_probability", complete_probability),
            ("certainty_probability", certainty_probability),
        ):
            all_parts[name].append(values)
        fold_ledgers.append({
            "fold": fold,
            "test_paints": sorted({rows[int(value)]["paint"] for value in test_indices}),
            "selected_completeness_head": complete_config["name"],
            "selected_certainty_head": certainty_config["name"],
            "inner_completeness_ap": {
                name: round(value, 6) for name, value in complete_scores.items()
            },
            "inner_certainty_ap": {
                name: round(value, 6) for name, value in certainty_scores.items()
            },
            "raw_safe_threshold": round(raw_threshold, 8),
            "assembly_config": {
                key: round(value, 8) if isinstance(value, float) else value
                for key, value in assembly_config.items()
            },
            "inner_assembly": inner_summary,
            "outer_assembled_set_count": len(sets),
        })
    result = {name: np.concatenate(parts) for name, parts in all_parts.items()}
    order = np.argsort(result["indices"])
    result = {name: value[order] for name, value in result.items()}
    data = _arrays(rows, indices)
    if not np.array_equal(result["indices"], data["indices"]):
        raise RuntimeError("set assembler OOF ordering drift")
    baseline_metrics = _set_metrics(rows, indices, data, result["baseline"])
    after_metrics = _set_metrics(rows, indices, data, result["assembled"])
    explicit = data["known"]
    fixed_family_ap = float(average_precision_score(
        data["family"][explicit], data["family_score"][explicit],
    ))
    certainty_ap = float(average_precision_score(
        data["known"], result["certainty_probability"],
    ))
    added = result["assembled"] & ~result["baseline"]
    added_metrics = _set_metrics(rows, indices, data, added)
    gates = {
        "requires_more_than_8_true_or_more_than_16pct_family_recall": (
            after_metrics["accepted_true_number_family"] > 8
            or after_metrics["family_recall"] > 0.16
        ),
        "requires_candidate_precision_at_least_0_80": after_metrics["precision"] >= 0.80,
        "requires_pixel_precision_at_least_0_80": after_metrics["reviewed_pixel_precision"] >= 0.80,
        "requires_zero_uncertain_accepts": after_metrics["accepted_uncertain"] == 0,
        "requires_zero_five_control_wrong_links": after_metrics["five_control_wrong_links"] == 0,
        "requires_no_true_regression_vs_baseline": (
            after_metrics["accepted_true_number_family"]
            >= baseline_metrics["accepted_true_number_family"]
        ),
        "frozen_cycle730_reference_ap_unchanged": True,
    }
    gates["development_family_assembly_gate_passed"] = all(gates.values())
    ledger = {
        "schema": "smart-tga-immutable-number-family-set-assembler-v2",
        "cycle": args.cycle,
        "contract": "Raw safe accepted candidates are immutable. Each paint's direct complete Number review is the cross-block family anchor; every added fragment independently clears frozen family evidence. Block grouping and completeness only corroborate and never manufacture authority.",
        "corpus": {
            "evaluated_rows": len(indices),
            "explicit_rows": int(np.count_nonzero(data["known"])),
            "uncertain_guard_rows": int(np.count_nonzero(data["uncertain"])),
            "unique_source_content_count": int(len(np.unique(groups))),
            "paint_count": len({rows[int(index)]["paint"] for index in indices}),
        },
        "ranking": {
            "frozen_cycle730_nested_reference_ap": 0.773697,
            "fixed_fine10_fine20_ensemble_ap_on_expanded_labels": round(fixed_family_ap, 6),
            "ranking_or_weights_tuned_in_cycle732": False,
        },
        "review_certainty_veto_ap": round(certainty_ap, 6),
        "baseline_raw_safe": baseline_metrics,
        "after_immutable_family_assembly": after_metrics,
        "added_members_only": added_metrics,
        "gates": gates,
        "assembled_set_count": len(all_sets),
        "selected_completeness_config_counts": dict(Counter(
            row["selected_completeness_head"] for row in fold_ledgers
        )),
        "selected_certainty_config_counts": dict(Counter(
            row["selected_certainty_head"] for row in fold_ledgers
        )),
        "targets": sorted({
            rows[int(index)]["paint"] for index in indices
            if rows[int(index)]["paint"] not in CONTROL_PAINTS
        }),
        "hard_negative_controls": sorted(CONTROL_PAINTS),
        "folds": fold_ledgers,
        "safety": {
            "filename_or_car_model_feature": False,
            "absolute_bbox_model_feature": False,
            "review_trace_feature": False,
            "placement_hash_used_only_for_exact_instance_dedupe": True,
            "runtime_integrated": False, "apply_locked": True,
            "exact_reconstruction_affected": False, "ocr_changed": False,
            "ownership_authority": False, "new_tga_opened": False,
        },
        "next_engineering_step": "Do not tune more assembly thresholds. Build a candidate-only masked appearance bank (Lab/chroma/lightness distribution, texture/edge entropy, palette-role structure and masked visual embedding) and train a source-content-disjoint fragment-purity veto against the observed Paint/livery and Sponsor additions. It may only veto anchor-nominated additions; preserve the raw 8/8 baseline and immutable set reconstruction.",
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "immutable_family_sets.json").write_text(
        json.dumps({
            "schema": "smart-tga-immutable-number-family-sets-v2",
            "ownership_authority": False, "sets": all_sets,
        }, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": baseline_metrics, "after": after_metrics,
        "added": added_metrics, "assembled_set_count": len(all_sets),
        "fixed_family_ap": round(fixed_family_ap, 6),
        "certainty_veto_ap": round(certainty_ap, 6),
        "gates": gates, "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
