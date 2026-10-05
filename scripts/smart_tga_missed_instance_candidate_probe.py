"""Measure owner-neutral raw-instance coverage for reviewed missed decals.

Review bboxes are evaluation truth only.  This probe never changes masks,
casts ownership votes, or turns filenames/coordinates into runtime authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


INSTANCE_FEATURE_FIELDS = (
    "area_fraction", "aspect_ratio", "bbox_normalized", "border_distance_fraction",
    "edge_density", "fill_ratio", "mean_rgb", "std_rgb", "ocr_alpha_coverage",
    "ocr_digit_coverage", "ocr_max_coverage", "ocr_token_count", "palette_role",
    "perceptual_chroma", "perceptual_hue_degrees", "perceptual_lightness",
    "proposal_conflict", "shape_occupancy", "strong_gradient_fraction",
    "texture_entropy",
)


def _intersection(left: Sequence[int], right: Sequence[int]) -> int:
    lx, ly, lw, lh = (int(value) for value in left)
    rx, ry, rw, rh = (int(value) for value in right)
    return max(0, min(lx + lw, rx + rw) - max(lx, rx)) * max(
        0, min(ly + lh, ry + rh) - max(ly, ry)
    )


def _coverage(candidate: Sequence[int], review: Sequence[int]) -> tuple[float, float, float]:
    overlap = _intersection(candidate, review)
    candidate_area = max(1, int(candidate[2]) * int(candidate[3]))
    review_area = max(1, int(review[2]) * int(review[3]))
    union = max(1, candidate_area + review_area - overlap)
    return overlap / review_area, overlap / candidate_area, overlap / union


def probe(
    inspections: Sequence[Mapping[str, Any]], annotations: Mapping[str, Any],
) -> dict[str, Any]:
    by_paint = {str(item.get("paint_label") or ""): item for item in inspections}
    results = []
    status_counts: dict[str, int] = {}
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
        ranked = []
        for candidate in candidates:
            bbox = candidate.get("bbox")
            if not bbox:
                continue
            review_coverage, candidate_coverage, iou = _coverage(bbox, annotation["bbox"])
            if review_coverage <= 0.0:
                continue
            ranked.append((review_coverage, iou, candidate_coverage, candidate))
        ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        best = ranked[0] if ranked else (0.0, 0.0, 0.0, {})
        # A huge unrelated panel can fully contain a tiny reviewed decal and
        # otherwise look like perfect recall.  Candidate coverage separates
        # that containment accident from a coherent decal proposal.
        if best[0] >= 0.50 and best[2] < 0.10:
            status = "candidate_overbroad"
        elif best[0] >= 0.50:
            status = "candidate_present"
        elif best[0] >= 0.10:
            status = "candidate_fragment_only"
        else:
            status = "candidate_absent"
        status_counts[status] = status_counts.get(status, 0) + 1
        candidate = best[3]
        area_ratio = float(best[0]) / max(float(best[2]), 1e-9) if best[0] else 0.0
        feature_snapshot = {
            name: candidate.get(name) for name in INSTANCE_FEATURE_FIELDS if name in candidate
        }
        results.append({
            **dict(annotation),
            "status": status,
            "overlap_candidate_count": len(ranked),
            "candidate_count_ge_025": sum(item[0] >= 0.25 for item in ranked),
            "candidate_count_ge_050": sum(item[0] >= 0.50 for item in ranked),
            "best_review_coverage": round(float(best[0]), 6),
            "best_candidate_coverage": round(float(best[2]), 6),
            "best_iou": round(float(best[1]), 6),
            "best_candidate_to_review_area_ratio": round(area_ratio, 6),
            "best_instance_id": candidate.get("instance_id"),
            "best_proposed_owners": list(candidate.get("proposed_owners") or ()),
            "best_source_stages": list(candidate.get("source_stages") or ()),
            "best_sources": list(candidate.get("sources") or ()),
            "best_merge_reasons": list(candidate.get("merge_reasons") or ()),
            # Immutable raw-instance features make reviewed misses reusable by
            # future candidate-recall models.  Review bboxes select the audit
            # match but are never copied into this feature vector or runtime.
            "best_instance_features": feature_snapshot,
        })
    owner_paths = Counter(
        "+".join(sorted(item["best_proposed_owners"])) or "none" for item in results
    )
    source_stages = Counter(
        stage for item in results for stage in item["best_source_stages"]
    )
    # Preserve copy-level review truth as family-level completion supervision.
    # This is deliberately offline: it describes where upper/lower/deck copies
    # have raw candidates, but it cannot create candidates or ownership votes.
    family_members: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        family_id = str(item.get("family_id") or "")
        if family_id:
            family_members[(str(item["paint_label"]), family_id)].append(item)
    family_records = []
    for (paint_label, family_id), members in sorted(family_members.items()):
        counts = Counter(str(item["status"]) for item in members)
        candidate_ids = {
            str(item["best_instance_id"]) for item in members if item.get("best_instance_id")
        }
        absent = counts["candidate_absent"]
        overbroad = counts["candidate_overbroad"]
        supervision_ready = (
            len(members) >= 2 and absent == 0 and overbroad == 0
            and all(item.get("best_instance_id") for item in members)
        )
        family_records.append({
            "paint_label": paint_label,
            "family_id": family_id,
            "reviewed_copy_count": len(members),
            "copies": [str(item.get("copy") or item.get("review_id") or "") for item in members],
            "status_counts": dict(sorted(counts.items())),
            "unique_candidate_instance_count": len(candidate_ids),
            "complete_candidate_copy_count": counts["candidate_present"],
            "fragment_candidate_copy_count": counts["candidate_fragment_only"],
            "absent_candidate_copy_count": absent,
            "overbroad_candidate_copy_count": overbroad,
            "completion_supervision_ready": supervision_ready,
        })
    return {
        "schema": "smart-tga-missed-instance-candidate-probe-v3",
        "reviewed_instance_count": len(results),
        "status_counts": status_counts,
        "trainable_candidate_count": sum(bool(item["best_instance_id"]) for item in results),
        "best_proposed_owner_path_counts": dict(sorted(owner_paths.items())),
        "best_source_stage_counts": dict(sorted(source_stages.items())),
        "reviewed_family_count": len(family_records),
        "multi_copy_family_count": sum(
            item["reviewed_copy_count"] >= 2 for item in family_records
        ),
        "completion_supervision_ready_family_count": sum(
            item["completion_supervision_ready"] for item in family_records
        ),
        "family_records": family_records,
        "instance_feature_fields": list(INSTANCE_FEATURE_FIELDS),
        "records": results,
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
    report = probe(inspections, annotations)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
