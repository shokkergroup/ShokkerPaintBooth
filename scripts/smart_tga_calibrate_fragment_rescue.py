"""Calibrate a completeness-based rescue for purity-vetoed raw candidates.

The selected paint is active-learning calibration, not evaluation.  Rescue may
only protect an existing raw nomination from the purity brake; it cannot add a
candidate that the raw baseline did not already nominate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from scripts.smart_tga_assess_frozen_holdout import _outcome_map
    from scripts.smart_tga_baseline_purity_veto import _calibrate_threshold
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_assess_frozen_holdout import _outcome_map  # type: ignore
    from scripts.smart_tga_baseline_purity_veto import _calibrate_threshold  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=737)
    args = parser.parse_args()
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    outcomes_payload = json.loads(args.outcomes.read_text(encoding="utf-8"))
    outcomes = _outcome_map(outcomes_payload)
    required = int(predictions["committee"]["votes_required"])
    removed = [
        row for row in predictions["decisions"]
        if int(row["baseline_votes"]) >= required
        and int(row["baseline_purity_retained_votes"]) < required
    ]
    true_scores = np.asarray([
        float(row["median_complete_probability"])
        for row in removed
        if outcomes[int(row["candidate_index"])] ["semantic"] == "Number"
    ], dtype=np.float64)
    false_scores = np.asarray([
        float(row["median_complete_probability"])
        for row in removed
        if outcomes[int(row["candidate_index"])] ["semantic"]
        not in ("Number", "uncertain")
    ], dtype=np.float64)
    if not len(true_scores) or not len(false_scores):
        raise RuntimeError("fragment rescue calibration needs removed true and false rows")
    threshold, separation = _calibrate_threshold(true_scores, false_scores)
    candidates = []
    for row in removed:
        index = int(row["candidate_index"])
        semantic = outcomes[index]["semantic"]
        score = float(row["median_complete_probability"])
        candidates.append({
            "candidate_index": index,
            "proposal_id": str(row["proposal_id"]),
            "semantic_for_calibration_only": semantic,
            "median_complete_probability": round(score, 8),
            "rescue": score >= threshold,
        })
    rescued_true = sum(
        row["rescue"] and row["semantic_for_calibration_only"] == "Number"
        for row in candidates
    )
    rescued_false = sum(
        row["rescue"] and row["semantic_for_calibration_only"]
        not in ("Number", "uncertain")
        for row in candidates
    )
    gates = {
        "strict_true_false_separation": bool(separation["strictly_separated"]),
        "all_removed_true_fragments_rescued": rescued_true == len(true_scores),
        "zero_removed_non_number_rescued": rescued_false == 0,
        "candidate_can_only_be_restored_if_raw_nominated": True,
    }
    gates["fragment_rescue_calibration_gate_passed"] = all(gates.values())
    payload = {
        "schema": "smart-tga-baseline-fragment-rescue-v1",
        "cycle": args.cycle,
        "contract": "Frozen completeness corroboration may protect an existing raw nomination from a semantic purity veto; it cannot admit any other candidate.",
        "active_learning_calibration": {
            "paint": outcomes_payload["paint"],
            "is_evaluation_holdout": False,
            "purity_removed_candidate_count": len(removed),
            "purity_removed_true_count": len(true_scores),
            "purity_removed_false_count": len(false_scores),
            "completeness_rescue_threshold": round(float(threshold), 8),
            "threshold_calibration": separation,
            "candidates": candidates,
            "rescued_true_count": rescued_true,
            "rescued_false_count": rescued_false,
        },
        "gates": gates,
        "safety": {
            "relationships_manufacture_authority": False,
            "raw_candidates_only": True,
            "calibration_reported_as_evaluation": False,
            "runtime_integrated": False,
            "ownership_authority": False,
            "apply_locked": True,
            "exact_reconstruction_affected": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "threshold": payload["active_learning_calibration"][
            "completeness_rescue_threshold"
        ],
        "rescued_true": rescued_true,
        "rescued_false": rescued_false,
        "gates": gates,
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
