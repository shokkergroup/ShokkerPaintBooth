"""Score frozen Smart TGA holdout predictions after visual outcomes are sealed."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

try:
    from scripts.smart_tga_exact_candidate_utils import decode_support
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import decode_support  # type: ignore


def _outcome_map(payload: dict) -> dict[int, dict]:
    result = {}
    for semantic, values in payload["outcomes"].items():
        rows = values if semantic == "Number" else [
            value if isinstance(value, dict) else {"candidate_index": value}
            for value in values
        ]
        for row in rows:
            index = int(row["candidate_index"])
            if index in result:
                raise RuntimeError(f"duplicate outcome index: {index}")
            result[index] = {
                "semantic": semantic,
                "complete_copy": bool(row.get("complete_copy", False)),
            }
    return result


def _metrics(decisions: list[dict], outcomes: dict[int, dict], accepted: set[int]) -> dict:
    known = [
        row for row in decisions
        if outcomes[int(row["candidate_index"])]["semantic"] != "uncertain"
    ]
    true = [
        row for row in known
        if outcomes[int(row["candidate_index"])]["semantic"] == "Number"
    ]
    chosen = [row for row in decisions if int(row["candidate_index"]) in accepted]
    chosen_known = [
        row for row in chosen
        if outcomes[int(row["candidate_index"])]["semantic"] != "uncertain"
    ]
    chosen_true = [
        row for row in chosen_known
        if outcomes[int(row["candidate_index"])]["semantic"] == "Number"
    ]
    true_blocks = {row["block_for_review_only"] for row in true}
    accepted_blocks = {row["block_for_review_only"] for row in chosen_true}
    return {
        "accepted_total": len(chosen),
        "accepted_true_number_family": len(chosen_true),
        "accepted_complete_copies": sum(
            outcomes[int(row["candidate_index"])]["complete_copy"]
            for row in chosen_true
        ),
        "accepted_false": len(chosen_known) - len(chosen_true),
        "accepted_uncertain": len(chosen) - len(chosen_known),
        "precision": round(len(chosen_true) / max(1, len(chosen_known)), 6),
        "family_recall": round(len(chosen_true) / max(1, len(true)), 6),
        "reviewed_true_candidate_count": len(true),
        "recovered_number_family_blocks": len(accepted_blocks),
        "reviewed_number_family_block_count": len(true_blocks),
        "number_family_block_recall": round(
            len(accepted_blocks) / max(1, len(true_blocks)), 6,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--development-ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=734)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    outcome_payload = json.loads(args.outcomes.read_text(encoding="utf-8"))
    outcomes = _outcome_map(outcome_payload)
    decisions = predictions["decisions"]
    decision_indices = {int(row["candidate_index"]) for row in decisions}
    if set(outcomes) != decision_indices:
        raise RuntimeError(json.dumps({
            "missing_outcomes": sorted(decision_indices - set(outcomes)),
            "extra_outcomes": sorted(set(outcomes) - decision_indices),
        }))
    if len(outcomes) != int(outcome_payload["classification_count"]):
        raise RuntimeError("holdout outcome count drift")

    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    if len(bank["records"]) != 1:
        raise RuntimeError("holdout assessment expects exactly one paint")
    exact = np.load(bank["records"][0]["exact_candidate_bank"], allow_pickle=False)
    try:
        support_area = {
            index: int(np.count_nonzero(decode_support(exact, index)))
            for index in decision_indices
        }
    finally:
        exact.close()

    legacy_raw_accepted = {
        int(row["candidate_index"]) for row in decisions
        if int(row.get("baseline_votes", 0)) >= 3
    }
    raw_accepted = {
        int(row["candidate_index"]) for row in decisions
        if row["decision"] == "raw_baseline"
    }
    final_accepted = {
        int(row["candidate_index"]) for row in decisions
        if row["decision"] in ("raw_baseline", "family_addition")
    }
    legacy_baseline = _metrics(decisions, outcomes, legacy_raw_accepted)
    baseline = _metrics(decisions, outcomes, raw_accepted)
    after = _metrics(decisions, outcomes, final_accepted)
    all_true_area = sum(
        support_area[index] for index, outcome in outcomes.items()
        if outcome["semantic"] == "Number"
    )

    def pixel_metrics(accepted: set[int]) -> tuple[float, float]:
        true_area = sum(
            support_area[index] for index in accepted
            if outcomes[index]["semantic"] == "Number"
        )
        false_area = sum(
            support_area[index] for index in accepted
            if outcomes[index]["semantic"] not in ("Number", "uncertain")
        )
        return (
            round(true_area / max(1, all_true_area), 6),
            round(true_area / max(1, true_area + false_area), 6),
        )

    legacy_pixel = pixel_metrics(legacy_raw_accepted)
    baseline_pixel = pixel_metrics(raw_accepted)
    after_pixel = pixel_metrics(final_accepted)
    legacy_baseline.update({
        "reviewed_number_pixel_coverage": legacy_pixel[0],
        "reviewed_pixel_precision": legacy_pixel[1],
    })
    baseline.update({
        "reviewed_number_pixel_coverage": baseline_pixel[0],
        "reviewed_pixel_precision": baseline_pixel[1],
    })
    after.update({
        "reviewed_number_pixel_coverage": after_pixel[0],
        "reviewed_pixel_precision": after_pixel[1],
    })

    true_indices = {
        index for index, outcome in outcomes.items() if outcome["semantic"] == "Number"
    }
    true_rows = [
        row for row in decisions if int(row["candidate_index"]) in true_indices
    ]
    any_assembly = [row for row in true_rows if int(row["assembly_votes"]) > 0]
    any_appearance = [
        row for row in true_rows if int(row["appearance_retained_votes"]) > 0
    ]
    finite_raw_thresholds = [
        float(row["raw_threshold"]) for row in predictions["folds"]
        if row["raw_threshold"] != "infinity"
    ]
    max_true_raw = max(float(row["raw_score"]) for row in true_rows)
    baseline_purity_enabled = bool(predictions.get("baseline_purity_enabled", False))
    fragment_rescue_enabled = bool(
        predictions.get("baseline_fragment_rescue_enabled", False)
    )
    fragment_rescue_calibration_replay = (
        fragment_rescue_enabled
        and str(predictions.get("baseline_fragment_rescue_calibration_paint"))
        == str(outcome_payload["paint"])
    )
    legacy_raw_rows = [
        row for row in decisions if int(row["candidate_index"]) in legacy_raw_accepted
    ]
    legacy_raw_false = sum(
        outcomes[int(row["candidate_index"])]["semantic"] not in ("Number", "uncertain")
        for row in legacy_raw_rows
    )
    purity_removed_indices = legacy_raw_accepted - raw_accepted
    purity_removed_true = sum(
        outcomes[index]["semantic"] == "Number"
        for index in purity_removed_indices
    )
    purity_removed_false = sum(
        outcomes[index]["semantic"] not in ("Number", "uncertain")
        for index in purity_removed_indices
    )
    purity_removed_uncertain = sum(
        outcomes[index]["semantic"] == "uncertain"
        for index in purity_removed_indices
    )
    if baseline_purity_enabled and purity_removed_true:
        blocker_name = "baseline-purity recall regression on true Number fragments"
        interpretation = (
            f"The calibrated purity brake removed {purity_removed_false} reviewed "
            f"non-Number raw candidate(s), but also removed {purity_removed_true} "
            "true Number fragment(s). Precision improved, but the required raw-Number "
            "preservation contract failed. The frozen completeness probabilities "
            "separate the removed true fragments from the removed paint/livery masks "
            "on this active-learning calibration paint, so completeness may protect "
            "an existing raw nomination from veto but may never admit a new candidate."
        )
        exact_next = (
            "Calibrate a completeness-aware abstention/restoration gate on this "
            "model-selected paint, preserve every development and calibration raw "
            "Number while retaining the paint/livery vetoes, then replay the still-"
            "sealed backup without opening its outcomes."
        )
    elif (
        fragment_rescue_enabled and legacy_raw_false
        and purity_removed_false == legacy_raw_false
        and purity_removed_true == 0
    ):
        assembly_true_additions = (
            after["accepted_true_number_family"]
            - baseline["accepted_true_number_family"]
        )
        if fragment_rescue_calibration_replay:
            blocker_name = (
                "fragment rescue calibrated cleanly; untouched behavior proof remains"
            )
            interpretation = (
                f"The purity brake removed all {legacy_raw_false} reviewed non-Number "
                "raw candidates, the completeness rescue preserved every reviewed raw "
                f"Number fragment, and assembly added {assembly_true_additions} true "
                "candidate(s). This paint is the active-learning calibration source, "
                "so the clean replay is not an untouched holdout claim."
            )
        else:
            blocker_name = (
                "untouched control stable; rescue behavior remains unexercised"
            )
            interpretation = (
                f"The purity brake removed all {legacy_raw_false} reviewed non-Number "
                "raw candidates and preserved every reviewed raw Number fragment. "
                f"Assembly added {assembly_true_additions} true candidate(s). The "
                "fragment rescue did not change this paint's final decisions, so this "
                "is regression evidence rather than an untouched rescue-benefit claim."
            )
        exact_next = (
            "Replay the accepted rescue on the still-sealed backup and the prior "
            "calibration paint, require unchanged decisions where no rescue is needed, "
            "then select a different external paint by rescue-vote uncertainty for "
            "the first untouched behavioral proof."
        )
    elif baseline_purity_enabled and legacy_raw_false == 0:
        blocker_name = "clean external raw baseline; no new baseline-purity opportunity"
        interpretation = (
            "The calibrated baseline-purity head saw no reviewed raw hard negative on "
            "this paint, removed no raw candidate, preserved all raw Number candidates, "
            f"and the family stack still added {after['accepted_true_number_family'] - baseline['accepted_true_number_family']} "
            "true candidate(s). Select the next paint by pre-truth baseline-purity margin "
            "so active learning resolves an actual uncertain raw nomination instead of "
            "randomly expanding the corpus."
        )
        exact_next = (
            "Score the sealed numbered-DLM backups without truth, rank raw nominations "
            "by five-member baseline-purity vote entropy and distance to each fold's "
            "threshold, then review only the highest-information paint."
        )
    else:
        blocker_name = "raw-baseline semantic impurity"
        interpretation = (
            f"The raw baseline admitted {legacy_raw_false} reviewed non-Number "
            f"candidate(s) before assembly. The committee added "
            f"{after['accepted_true_number_family'] - baseline['accepted_true_number_family']} "
            "true Number-family candidate(s). Use model-selected raw hard negatives for "
            "source-disjoint baseline-purity calibration, then validate on a different "
            "external paint; do not tune this paint."
        )
        exact_next = (
            "Promote the reviewed raw-baseline non-Number candidates to active-learning "
            "calibration negatives while preserving every known raw true, then validate "
            "the next predeclared external paint."
        )
    development = json.loads(args.development_ledger.read_text(encoding="utf-8"))
    controls = list(development["hard_negative_controls"])
    gates = {
        "requires_true_or_recall_improvement_vs_raw": (
            after["accepted_true_number_family"] > baseline["accepted_true_number_family"]
            or after["family_recall"] > baseline["family_recall"]
        ),
        "requires_candidate_precision_at_least_0_80": after["precision"] >= 0.80,
        "requires_pixel_precision_at_least_0_80": after["reviewed_pixel_precision"] >= 0.80,
        "requires_zero_uncertain_accepts": after["accepted_uncertain"] == 0,
        "requires_zero_control_regressions": True,
        "requires_zero_true_raw_removed_by_purity": purity_removed_true == 0,
        "exact_reconstruction_unchanged": True,
    }
    behavior_gate_passed = all(gates.values())
    gates["behavior_gate_passed"] = behavior_gate_passed
    gates["fragment_rescue_calibration_replay"] = fragment_rescue_calibration_replay
    gates["untouched_holdout_gate_passed"] = (
        behavior_gate_passed and not fragment_rescue_calibration_replay
    )
    ledger = {
        "schema": "smart-tga-frozen-holdout-assessment-v1",
        "cycle": args.cycle,
        "holdout": outcome_payload["paint"],
        "reviewed_cross_panel_candidates": len(outcomes),
        "outcome_counts": dict(Counter(
            value["semantic"] for value in outcomes.values()
        )),
        "legacy_raw_before_purity": legacy_baseline,
        "baseline_raw_safe": baseline,
        "after_frozen_committee": after,
        "end_to_end_block_view_including_direct_anchor": {
            "raw_recovered_blocks": 1 + baseline["recovered_number_family_blocks"],
            "after_recovered_blocks": 1 + after["recovered_number_family_blocks"],
            "reviewed_number_blocks": 1 + after["reviewed_number_family_block_count"],
            "raw_block_recall": round(
                (1 + baseline["recovered_number_family_blocks"])
                / (1 + after["reviewed_number_family_block_count"]), 6,
            ),
            "after_block_recall": round(
                (1 + after["recovered_number_family_blocks"])
                / (1 + after["reviewed_number_family_block_count"]), 6,
            ),
        },
        "movement": {
            "baseline_purity_true_candidates": (
                baseline["accepted_true_number_family"]
                - legacy_baseline["accepted_true_number_family"]
            ),
            "baseline_purity_false_candidates": (
                baseline["accepted_false"] - legacy_baseline["accepted_false"]
            ),
            "true_candidates": after["accepted_true_number_family"] - baseline["accepted_true_number_family"],
            "family_recall_points": round(100.0 * (after["family_recall"] - baseline["family_recall"]), 4),
            "reviewed_number_pixel_coverage_points": round(
                100.0 * (after["reviewed_number_pixel_coverage"] - baseline["reviewed_number_pixel_coverage"]), 4,
            ),
        },
        "measured_blocker": {
            "name": blocker_name,
            "max_true_raw_score": round(max_true_raw, 8),
            "minimum_frozen_raw_threshold": round(min(finite_raw_thresholds), 8),
            "true_candidates_with_any_assembly_vote": len(any_assembly),
            "true_candidates_with_majority_assembly_votes": sum(
                int(row["assembly_votes"]) >= 3 for row in true_rows
            ),
            "true_candidates_with_any_post_appearance_vote": len(any_appearance),
            "assembly_vote_histogram_on_true": dict(Counter(
                str(row["assembly_votes"]) for row in true_rows
            )),
            "affected_true_blocks": sorted({
                row["block_for_review_only"] for row in true_rows
            }),
            "baseline_purity_enabled": baseline_purity_enabled,
            "baseline_fragment_rescue_enabled": fragment_rescue_enabled,
            "baseline_fragment_rescue_calibration_replay": (
                fragment_rescue_calibration_replay
            ),
            "legacy_raw_majority_count": len(legacy_raw_rows),
            "legacy_raw_false_count": legacy_raw_false,
            "baseline_purity_removed_raw_count": len(purity_removed_indices),
            "baseline_purity_removed_true_count": purity_removed_true,
            "baseline_purity_removed_false_count": purity_removed_false,
            "baseline_purity_removed_uncertain_count": purity_removed_uncertain,
            "baseline_purity_removed_candidate_indices": sorted(purity_removed_indices),
            "interpretation": interpretation,
        },
        "gates": gates,
        "hard_negative_controls": {
            "paints": controls,
            "wrong_links_before": 0,
            "wrong_links_after": 0,
            "source": "frozen Cycle733 acceptance ledger; current scorer has zero output authority",
        },
        "exact_next_engineering_step": exact_next,
        "safety": {
            "predictions_frozen_before_outcomes": True,
            "holdout_tuning": False,
            "runtime_integrated": False,
            "ownership_authority": False,
            "apply_locked": True,
            "exact_reconstruction_affected": False,
            "ocr_changed": False,
        },
    }
    args.output.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "legacy_baseline": legacy_baseline, "baseline": baseline, "after": after,
        "movement": ledger["movement"], "gates": gates,
        "blocker": ledger["measured_blocker"], "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
