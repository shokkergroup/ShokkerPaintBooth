"""Rank truth-free DLM holdouts by calibrated raw-purity uncertainty.

Only frozen committee outputs are consumed.  Candidate outcomes, filenames,
absolute positions and reviewed non-anchor semantics never affect the ranking.
Vote entropy among folds that actually nominated the raw candidate is primary;
proximity to the fitted purity boundary breaks ties.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def _binary_vote_entropy(retained_votes: int, committee_size: int) -> float:
    if committee_size < 1 or not 0 <= retained_votes <= committee_size:
        raise ValueError("invalid committee vote count")
    probability = retained_votes / committee_size
    if probability in (0.0, 1.0):
        return 0.0
    return float(-probability * math.log2(probability) - (
        1.0 - probability
    ) * math.log2(1.0 - probability))


def _summarize_prediction(payload: dict) -> dict:
    if not payload.get("baseline_purity_enabled"):
        raise ValueError("active-learning ranking requires baseline purity")
    required = int(payload["committee"]["votes_required"])
    thresholds = [float(row["baseline_purity_threshold"]) for row in payload["folds"]]
    median_threshold = float(np.median(thresholds))
    raw = []
    for row in payload["decisions"]:
        baseline_votes = int(row["baseline_votes"])
        if baseline_votes < required:
            continue
        retained_votes = int(row["baseline_purity_retained_votes"])
        probability = float(row["median_baseline_purity_probability"])
        raw.append({
            "candidate_index": int(row["candidate_index"]),
            "proposal_id": str(row["proposal_id"]),
            "baseline_votes": baseline_votes,
            "baseline_purity_retained_votes": retained_votes,
            "vote_entropy_bits": round(
                _binary_vote_entropy(retained_votes, baseline_votes), 8,
            ),
            "median_purity_probability": round(probability, 8),
            "distance_to_median_threshold": round(
                abs(probability - median_threshold), 8,
            ),
            "purity_vetoed": retained_votes < required,
        })
    if not raw:
        raise RuntimeError("paint has no majority raw nominations")
    return {
        "paint": str(payload["holdout_paint"]),
        "raw_nomination_count": len(raw),
        "purity_vetoed_raw_count": sum(row["purity_vetoed"] for row in raw),
        "max_vote_entropy_bits": max(row["vote_entropy_bits"] for row in raw),
        "mean_vote_entropy_bits": round(float(np.mean([
            row["vote_entropy_bits"] for row in raw
        ])), 8),
        "minimum_distance_to_median_threshold": min(
            row["distance_to_median_threshold"] for row in raw
        ),
        "median_fitted_purity_threshold": round(median_threshold, 8),
        "raw_candidates": raw,
    }


def _ranking_key(row: dict) -> tuple:
    return (
        -float(row["max_vote_entropy_bits"]),
        float(row["minimum_distance_to_median_threshold"]),
        -int(row["purity_vetoed_raw_count"]),
        str(row["paint"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=737)
    args = parser.parse_args()
    rows = [
        _summarize_prediction(json.loads(path.read_text(encoding="utf-8")))
        for path in args.predictions
    ]
    rows.sort(key=_ranking_key)
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
        row["selected_for_review"] = rank == 1
    payload = {
        "schema": "smart-tga-purity-active-learning-rank-v1",
        "cycle": args.cycle,
        "contract": "Truth-free frozen predictions only; conditional purity-vote entropy among raw-nominating folds first, fitted-threshold proximity second, veto opportunity third.",
        "selected_paint": rows[0]["paint"],
        "ranking": rows,
        "safety": {
            "candidate_outcomes_consumed": False,
            "non_anchor_semantic_truth_consumed": False,
            "filename_car_or_bbox_model_feature": False,
            "ownership_authority": False,
            "runtime_integrated": False,
            "apply_locked": True,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selected_paint": payload["selected_paint"],
        "ranking": [{
            "paint": row["paint"],
            "max_vote_entropy_bits": row["max_vote_entropy_bits"],
            "minimum_distance_to_median_threshold": row[
                "minimum_distance_to_median_threshold"
            ],
            "purity_vetoed_raw_count": row["purity_vetoed_raw_count"],
        } for row in rows],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
