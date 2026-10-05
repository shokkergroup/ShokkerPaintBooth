"""Validate and attach a visual-review overlay to exact immutable candidates."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    overlay = json.loads(args.overlay.read_text(encoding="utf-8"))
    queue_by_code = {row["review_code"]: row for row in queue["labels"]}
    overlay_by_code = {row["code"]: row for row in overlay["labels"]}
    if len(queue_by_code) != len(queue["labels"]):
        raise ValueError("duplicate review code in queue")
    if len(overlay_by_code) != len(overlay["labels"]):
        raise ValueError("duplicate review code in overlay")
    if set(queue_by_code) != set(overlay_by_code):
        raise ValueError("overlay must classify every queued exact candidate once")
    records = {row["paint"]: row for row in bank["records"]}
    labels = []
    for code in sorted(queue_by_code):
        queued, reviewed = queue_by_code[code], overlay_by_code[code]
        semantic = reviewed["semantic"]
        complete_copy = reviewed["complete_copy"]
        if semantic != "Number" and complete_copy is not None:
            raise ValueError(f"non-Number candidate cannot have completion label at {code}")
        if semantic == "Number" and not isinstance(complete_copy, bool):
            raise ValueError(f"Number candidate requires boolean completion label at {code}")
        record = records[queued["paint"]]
        index = int(queued["candidate_index"])
        exact = np.load(record["exact_candidate_bank"], allow_pickle=False)
        proposal_id = str(exact["proposal_ids"][index])
        bbox = exact["bboxes"][index].astype(int).tolist()
        if proposal_id != queued["proposal_id"] or bbox != queued["bbox"]:
            raise ValueError(f"exact candidate identity drift at {code}")
        label = {
            "review_code": code,
            "paint": queued["paint"],
            "candidate_index": index,
            "proposal_id": proposal_id,
            "bbox_for_review_trace_only": bbox,
            "semantic": semantic,
            "complete_copy": complete_copy,
            "review_status": "direct_visual_exact_mask",
            "ownership_authority": False,
        }
        if semantic == "Number":
            # These identifiers supervise grouping only.  They are paint-local,
            # are never exposed as runtime features, and cannot cast ownership.
            label["family_id"] = reviewed.get("family_id", "primary_number_family")
            label["physical_copy_id"] = reviewed.get(
                "physical_copy_id",
                queued.get("dominant_number_block", "unmapped_number_copy"),
            )
        labels.append(label)
    payload = {
        "schema": "smart-tga-direct-exact-candidate-labels-v1",
        "cycle": overlay.get("cycle", queue.get("cycle")),
        "reviewed_at": overlay["reviewed_at"],
        "review_method": overlay["review_method"],
        "label_count": len(labels),
        "semantic_counts": dict(Counter(row["semantic"] for row in labels)),
        "complete_number_count": sum(row["complete_copy"] is True for row in labels),
        "number_fragment_count": sum(
            row["semantic"] == "Number" and row["complete_copy"] is False
            for row in labels
        ),
        "labels": labels,
        "safety": {
            "exact_candidate_id_is_supervision_key": True,
            "bbox_is_runtime_authority": False,
            "filename_or_car_features": False,
            "ownership_authority": False,
        },
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "label_count": payload["label_count"],
        "semantic_counts": payload["semantic_counts"],
        "complete_number_count": payload["complete_number_count"],
        "number_fragment_count": payload["number_fragment_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
