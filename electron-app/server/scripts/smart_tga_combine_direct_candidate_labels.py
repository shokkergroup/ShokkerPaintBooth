"""Combine durable exact-candidate review files without changing candidate identity."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, required=True)
    args = parser.parse_args()

    combined = []
    seen = set()
    sources = []
    for path in args.labels:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources.append({"path": str(path), "cycle": payload.get("cycle"), "count": len(payload["labels"])})
        for row in payload["labels"]:
            key = (row["paint"], row["proposal_id"])
            if key in seen:
                raise ValueError(f"duplicate exact candidate label: {key}")
            seen.add(key)
            combined.append(row)

    combined.sort(key=lambda row: (row["paint"], int(row["candidate_index"]), row["proposal_id"]))
    payload = {
        "schema": "smart-tga-direct-exact-candidate-labels-v2",
        "cycle": args.cycle,
        "sources": sources,
        "label_count": len(combined),
        "paint_count": len({row["paint"] for row in combined}),
        "semantic_counts": dict(Counter(row["semantic"] for row in combined)),
        "complete_number_count": sum(row["complete_copy"] is True for row in combined),
        "number_fragment_count": sum(
            row["semantic"] == "Number" and row["complete_copy"] is False for row in combined
        ),
        "labels": combined,
        "safety": {
            "exact_candidate_id_is_supervision_key": True,
            "paint_identity_is_split_and_grouping_only": True,
            "bbox_is_runtime_authority": False,
            "filename_or_car_features": False,
            "ownership_authority": False,
        },
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "label_count", "paint_count", "semantic_counts", "complete_number_count", "number_fragment_count"
    )}, indent=2))


if __name__ == "__main__":
    main()
