"""Rank truth-free DLM paints by actual fragment-rescue opportunity.

Only frozen committee predictions and the accepted rescue threshold are read.
Current candidate outcomes never participate.  A paint is reviewable only when
at least one already-raw candidate receives a majority of rescue votes.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path


def _vote_entropy(votes: int, opportunities: int) -> float:
    if opportunities < 1 or not 0 <= votes <= opportunities:
        raise ValueError("invalid conditional rescue vote count")
    probability = votes / opportunities
    if probability in (0.0, 1.0):
        return 0.0
    return float(-probability * math.log2(probability) - (
        1.0 - probability
    ) * math.log2(1.0 - probability))


def _summaries(payload: dict, rescue_threshold: float) -> list[dict]:
    if not payload.get("baseline_fragment_rescue_enabled"):
        raise ValueError("ranking requires the accepted fragment rescue")
    required = int(payload["committee"]["votes_required"])
    by_paint: dict[str, list[dict]] = defaultdict(list)
    for row in payload["decisions"]:
        by_paint[str(row["paint"])].append(row)
    result = []
    for paint, decisions in sorted(by_paint.items()):
        raw = [
            row for row in decisions
            if int(row["baseline_votes"]) >= required
        ]
        opportunities = []
        for row in raw:
            baseline_votes = int(row["baseline_votes"])
            rescue_votes = int(row["baseline_fragment_rescue_votes"])
            if rescue_votes < 1:
                continue
            completeness = float(row["median_complete_probability"])
            opportunities.append({
                "candidate_index": int(row["candidate_index"]),
                "proposal_id": str(row["proposal_id"]),
                "baseline_votes": baseline_votes,
                "rescue_votes": rescue_votes,
                "majority_rescue": rescue_votes >= required,
                "conditional_vote_entropy_bits": round(
                    _vote_entropy(rescue_votes, baseline_votes), 8,
                ),
                "median_complete_probability": round(completeness, 8),
                "distance_to_rescue_threshold": round(
                    abs(completeness - rescue_threshold), 8,
                ),
            })
        majority = [row for row in opportunities if row["majority_rescue"]]
        result.append({
            "paint": paint,
            "decision_count": len(decisions),
            "raw_nomination_count": len(raw),
            "any_rescue_vote_candidate_count": len(opportunities),
            "majority_rescue_candidate_count": len(majority),
            "max_conditional_vote_entropy_bits": max(
                (row["conditional_vote_entropy_bits"] for row in opportunities),
                default=0.0,
            ),
            "minimum_distance_to_rescue_threshold": min(
                (row["distance_to_rescue_threshold"] for row in opportunities),
                default=None,
            ),
            "rescue_candidates": opportunities,
        })
    return result


def _ranking_key(row: dict) -> tuple:
    distance = row["minimum_distance_to_rescue_threshold"]
    return (
        -int(row["majority_rescue_candidate_count"] > 0),
        -int(row["majority_rescue_candidate_count"]),
        -float(row["max_conditional_vote_entropy_bits"]),
        math.inf if distance is None else float(distance),
        str(row["paint"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, action="append", required=True)
    parser.add_argument("--fragment-rescue-ledger", type=Path, required=True)
    parser.add_argument("--anchor-availability", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=738)
    args = parser.parse_args()
    rescue = json.loads(args.fragment_rescue_ledger.read_text(encoding="utf-8"))
    threshold = float(
        rescue["active_learning_calibration"]["completeness_rescue_threshold"]
    )
    rows = []
    for path in args.predictions:
        rows.extend(_summaries(json.loads(path.read_text(encoding="utf-8")), threshold))
    if len({row["paint"] for row in rows}) != len(rows):
        raise RuntimeError("duplicate paint predictions")
    rows.sort(key=_ranking_key)
    reviewable = [
        row for row in rows if row["majority_rescue_candidate_count"] > 0
    ]
    selected = reviewable[0]["paint"] if reviewable else None
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
        row["selected_for_review"] = row["paint"] == selected
    anchors = json.loads(args.anchor_availability.read_text(encoding="utf-8"))
    unavailable = {
        paint: value for paint, value in anchors["anchor_availability"].items()
        if not value["available"]
    }
    payload = {
        "schema": "smart-tga-fragment-rescue-active-learning-rank-v1",
        "cycle": args.cycle,
        "contract": "Majority rescue occurrence first, conditional rescue-vote entropy second, frozen completeness-threshold distance third. Current outcomes are sealed.",
        "frozen_rescue_threshold": threshold,
        "selected_paint": selected,
        "review_allowed": selected is not None,
        "measured_blocker": (
            None if selected is not None else
            "No anchorable paint contains a majority rescue opportunity. Opening candidate outcomes would not measure the new rescue and is disallowed."
        ),
        "ranking": rows,
        "unanchorable_paints": unavailable,
        "safety": {
            "candidate_outcomes_consumed": False,
            "non_anchor_semantic_truth_consumed": False,
            "filename_car_or_bbox_model_feature": False,
            "relationships_manufacture_authority": False,
            "ownership_authority": False,
            "runtime_integrated": False,
            "apply_locked": True,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selected_paint": selected,
        "review_allowed": payload["review_allowed"],
        "ranking": [{
            "paint": row["paint"],
            "raw": row["raw_nomination_count"],
            "any_rescue": row["any_rescue_vote_candidate_count"],
            "majority_rescue": row["majority_rescue_candidate_count"],
        } for row in rows],
        "unanchorable_paint_count": len(unavailable),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
