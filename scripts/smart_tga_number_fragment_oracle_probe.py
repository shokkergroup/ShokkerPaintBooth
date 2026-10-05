"""Measure whether immutable raw fragments can jointly cover reviewed numbers.

This is an offline ceiling probe. Reviewed copy boxes select fragment members
only for evaluation and supervision; no coordinate, filename, relationship, or
oracle result is emitted as runtime authority. The result distinguishes a
learnable fragment-membership/assembly problem from missing raw proposals.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


def _intersection(left: Sequence[int], right: Sequence[int]) -> tuple[int, int, int, int] | None:
    lx, ly, lw, lh = (int(value) for value in left)
    rx, ry, rw, rh = (int(value) for value in right)
    x0, y0 = max(lx, rx), max(ly, ry)
    x1, y1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1 - x0, y1 - y0


def _coverage(candidate: Sequence[int], review: Sequence[int]) -> tuple[float, float]:
    overlap = _intersection(candidate, review)
    overlap_area = 0 if overlap is None else int(overlap[2]) * int(overlap[3])
    candidate_area = max(1, int(candidate[2]) * int(candidate[3]))
    review_area = max(1, int(review[2]) * int(review[3]))
    return overlap_area / review_area, overlap_area / candidate_area


def _greedy_oracle_members(
    candidates: Sequence[Mapping[str, Any]], review: Sequence[int],
    *, minimum_candidate_containment: float = 0.55,
    minimum_review_coverage: float = 0.005,
) -> tuple[list[Mapping[str, Any]], float]:
    rx, ry, rw, rh = (int(value) for value in review)
    covered = np.zeros((max(1, rh), max(1, rw)), dtype=bool)
    eligible = []
    for candidate in candidates:
        bbox = candidate.get("bbox")
        if not bbox:
            continue
        review_coverage, candidate_containment = _coverage(bbox, review)
        if (
            review_coverage < minimum_review_coverage
            or candidate_containment < minimum_candidate_containment
        ):
            continue
        overlap = _intersection(bbox, review)
        if overlap is None:
            continue
        eligible.append((candidate, overlap))

    selected: list[Mapping[str, Any]] = []
    while eligible:
        best_index, best_gain = -1, 0
        for index, (_, (x, y, width, height)) in enumerate(eligible):
            local = covered[y - ry:y - ry + height, x - rx:x - rx + width]
            gain = int(local.size - np.count_nonzero(local))
            if gain > best_gain:
                best_index, best_gain = index, gain
        if best_index < 0 or best_gain <= 0:
            break
        candidate, (x, y, width, height) = eligible.pop(best_index)
        covered[y - ry:y - ry + height, x - rx:x - rx + width] = True
        selected.append(candidate)
    return selected, float(np.mean(covered))


def _bounding_envelope(members: Sequence[Mapping[str, Any]]) -> list[int] | None:
    boxes = [member.get("bbox") for member in members if member.get("bbox")]
    if not boxes:
        return None
    x0 = min(int(box[0]) for box in boxes)
    y0 = min(int(box[1]) for box in boxes)
    x1 = max(int(box[0]) + int(box[2]) for box in boxes)
    y1 = max(int(box[1]) + int(box[3]) for box in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def probe(
    inspections: Sequence[Mapping[str, Any]], annotations: Mapping[str, Any],
) -> dict[str, Any]:
    by_paint = {str(item.get("paint_label") or ""): item for item in inspections}
    records = []
    for annotation in annotations.get("instances") or ():
        paint_label = str(annotation.get("paint_label") or "")
        inspection = by_paint.get(paint_label)
        if inspection is None:
            raise ValueError(f"inspection missing for {paint_label}")
        candidates = (
            (inspection.get("route_adjudicator_shadow") or {})
            .get("candidate_evidence", {}).get("decal_instances", {})
            .get("features", {}).get("records", ())
        )
        review = annotation["bbox"]
        single_coverages = [
            _coverage(candidate.get("bbox") or (0, 0, 0, 0), review)[0]
            for candidate in candidates
            if candidate.get("bbox")
        ]
        members, union_coverage = _greedy_oracle_members(candidates, review)
        envelope = _bounding_envelope(members)
        envelope_review_coverage, envelope_containment = (
            _coverage(envelope, review) if envelope else (0.0, 0.0)
        )
        member_owners = Counter(
            owner for member in members for owner in member.get("proposed_owners") or ()
        )
        records.append({
            **dict(annotation),
            "best_single_bbox_coverage": round(max(single_coverages, default=0.0), 6),
            "oracle_fragment_union_coverage": round(union_coverage, 6),
            "coverage_gain": round(union_coverage - max(single_coverages, default=0.0), 6),
            "oracle_member_count": len(members),
            "oracle_member_ids": [str(member.get("instance_id") or "") for member in members],
            "oracle_member_owner_counts": dict(sorted(member_owners.items())),
            "oracle_fragment_envelope_bbox": envelope,
            "oracle_fragment_envelope_review_coverage": round(envelope_review_coverage, 6),
            "oracle_fragment_envelope_containment": round(envelope_containment, 6),
            "single_complete": max(single_coverages, default=0.0) >= 0.50,
            "oracle_assembly_complete": union_coverage >= 0.50,
            "oracle_envelope_complete": (
                envelope_review_coverage >= 0.50 and envelope_containment >= 0.10
            ),
        })

    single_complete = sum(bool(item["single_complete"]) for item in records)
    oracle_complete = sum(bool(item["oracle_assembly_complete"]) for item in records)
    envelope_complete = sum(bool(item["oracle_envelope_complete"]) for item in records)
    return {
        "schema": "smart-tga-number-fragment-oracle-probe-v1",
        "role": "offline assembly ceiling and membership supervision only",
        "reviewed_copy_count": len(records),
        "single_complete_copy_count": single_complete,
        "oracle_assembled_complete_copy_count": oracle_complete,
        "oracle_envelope_complete_copy_count": envelope_complete,
        "single_complete_recall": round(single_complete / max(1, len(records)), 6),
        "oracle_assembled_complete_recall": round(oracle_complete / max(1, len(records)), 6),
        "oracle_envelope_complete_recall": round(envelope_complete / max(1, len(records)), 6),
        "mean_single_coverage": round(float(np.mean([item["best_single_bbox_coverage"] for item in records])), 6),
        "mean_oracle_union_coverage": round(float(np.mean([item["oracle_fragment_union_coverage"] for item in records])), 6),
        "records": records,
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inspections = json.loads(Path(args.inspection).read_text(encoding="utf-8"))
    annotations = json.loads(Path(args.annotations).read_text(encoding="utf-8"))
    result = probe(inspections, annotations)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
