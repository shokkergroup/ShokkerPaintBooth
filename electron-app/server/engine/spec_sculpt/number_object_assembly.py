"""Immutable owner-neutral assembly for nested number-object hypotheses."""

from __future__ import annotations

import hashlib
from typing import Mapping, Sequence


def _intersection(first: Sequence[int], second: Sequence[int]) -> int:
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by),
    )


def assemble_nested_proposal_families(
    proposals: Sequence[Mapping], minimum_containment: float = 0.72,
) -> tuple[dict, ...]:
    """Group nested proposals while preserving every member and all provenance.

    Geometry only assembles hypotheses; it never assigns a semantic owner or
    casts an output vote.  The original proposal dictionaries are not mutated.
    """
    if not 0.0 < float(minimum_containment) <= 1.0:
        raise ValueError("minimum_containment must be in (0, 1]")
    items = list(proposals)
    parent = list(range(len(items)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        left, right = find(first), find(second)
        if left != right:
            parent[right] = left

    for first in range(len(items)):
        first_box = items[first]["proposal_bbox"]
        first_area = max(1, int(first_box[2]) * int(first_box[3]))
        for second in range(first + 1, len(items)):
            second_box = items[second]["proposal_bbox"]
            second_area = max(1, int(second_box[2]) * int(second_box[3]))
            containment = _intersection(first_box, second_box) / min(first_area, second_area)
            if containment >= float(minimum_containment):
                union(first, second)

    groups = {}
    for index in range(len(items)):
        groups.setdefault(find(index), []).append(items[index])
    families = []
    for members in groups.values():
        x0 = min(int(item["proposal_bbox"][0]) for item in members)
        y0 = min(int(item["proposal_bbox"][1]) for item in members)
        x1 = max(int(item["proposal_bbox"][0]) + int(item["proposal_bbox"][2]) for item in members)
        y1 = max(int(item["proposal_bbox"][1]) + int(item["proposal_bbox"][3]) for item in members)
        member_ids = tuple(sorted(str(item["proposal_id"]) for item in members))
        digest = hashlib.sha256("|".join(member_ids).encode("utf-8")).hexdigest()[:16]
        families.append({
            "family_id": "number-family:" + digest,
            "family_bbox": [x0, y0, x1 - x0, y1 - y0],
            "member_ids": member_ids,
            "member_bboxes": tuple(tuple(map(int, item["proposal_bbox"])) for item in members),
            "member_provenance": tuple(dict(item.get("provenance", {})) for item in members),
            "member_count": len(members), "owner_neutral": True,
            "casts_votes": False, "ownership_authority": False,
        })
    return tuple(sorted(families, key=lambda item: item["family_id"]))


__all__ = ["assemble_nested_proposal_families"]
