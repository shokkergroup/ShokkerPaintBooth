"""Merge direct boundary states into durable exact-candidate supervision.

The resulting labels are training evidence only. They never grant ownership,
and review-trace bbox/block fields are deliberately excluded from features.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


STATE_TO_TARGET = {
    "complete_number_copy": ("Number", True),
    "number_fragment": ("Number", False),
    "sponsor_glyph": ("Sponsor", False),
    "paint_or_template": ("Paint/livery", False),
    "ambiguous_crop": ("uncertain", None),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = json.loads(args.base.read_text(encoding="utf-8"))
    boundary = json.loads(args.boundary.read_text(encoding="utf-8"))
    labels = list(base["labels"])
    keys = {(str(row["paint"]), int(row["candidate_index"])) for row in labels}
    additions = []
    for review in boundary["reviews"]:
        state = str(review["direct_state"])
        if state not in STATE_TO_TARGET:
            raise ValueError(f"unsupported boundary state: {state}")
        key = (str(review["paint"]), int(review["candidate_index"]))
        if key in keys:
            raise ValueError(f"duplicate reviewed candidate: {key}")
        semantic, complete = STATE_TO_TARGET[state]
        row = {
            "review_code": str(review["review_code"]),
            "paint": key[0],
            "candidate_index": key[1],
            "proposal_id": str(review["proposal_id"]),
            "bbox_for_review_trace_only": review["bbox_for_review_trace_only"],
            "semantic": semantic,
            "complete_copy": complete,
            "boundary_state": state,
            "review_status": "direct_visual_exact_mask_and_context",
            "ownership_authority": False,
        }
        additions.append(row)
        keys.add(key)
    output = {
        "schema": "smart-tga-direct-exact-candidate-labels-v3",
        "created": boundary.get("created"),
        "purpose": "Durable exact-mask semantics plus direct completeness/fragment states for source-content-disjoint learning.",
        "base_labels": args.base.as_posix(),
        "boundary_reviews": args.boundary.as_posix(),
        "ownership_authority": False,
        "label_count": len(labels) + len(additions),
        "boundary_state_counts": {
            state: sum(row["boundary_state"] == state for row in additions)
            for state in STATE_TO_TARGET
        },
        "labels": labels + additions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output), "base": len(labels),
        "added": len(additions), "total": output["label_count"],
        "boundary_state_counts": output["boundary_state_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
