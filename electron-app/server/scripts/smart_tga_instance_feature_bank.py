"""Build a durable owner-neutral Smart TGA instance feature bank.

Input inspection records must be routed with
``SPB_SMART_TGA_INSTANCE_FEATURE_EXPORT=1``.  The exporter refuses any
telemetry that claims ownership authority or casts votes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "smart-tga-instance-feature-bank-v1"


def build_feature_bank(inspection_records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    missing = []
    for inspection in inspection_records:
        paint_label = str(inspection.get("paint_label") or inspection.get("paint") or "")
        shadow = inspection.get("route_adjudicator_shadow") or {}
        instances = ((shadow.get("candidate_evidence") or {}).get("decal_instances") or {})
        features = instances.get("features") or {}
        if bool(instances.get("ownership_authority")) or bool(features.get("ownership_authority")):
            raise ValueError(f"owner-neutral feature export rejected authority for {paint_label}")
        if bool(instances.get("casts_votes")) or bool(features.get("casts_votes")):
            raise ValueError(f"owner-neutral feature export rejected votes for {paint_label}")
        records = features.get("records")
        if records is None:
            missing.append(paint_label)
            continue
        for record in records:
            rows.append({"paint_label": paint_label, **dict(record)})
    if missing:
        raise ValueError(
            "full instance features missing; reroute with "
            "SPB_SMART_TGA_INSTANCE_FEATURE_EXPORT=1: " + ", ".join(missing)
        )
    rows.sort(key=lambda item: (item["paint_label"], item["instance_id"]))
    return {
        "schema": SCHEMA,
        "paint_count": len({item["paint_label"] for item in rows}),
        "instance_count": len(rows),
        "ownership_authority": False,
        "casts_votes": False,
        "records": rows,
    }


def _bbox_overlap_min(left: Sequence[int], right: Sequence[int]) -> float:
    lx, ly, lw, lh = [int(value) for value in left]
    rx, ry, rw, rh = [int(value) for value in right]
    ix0, iy0 = max(lx, rx), max(ly, ry)
    ix1, iy1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    overlap = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    return overlap / float(max(1, min(lw * lh, rw * rh)))


def attach_review_links(
    bank: dict[str, Any],
    label_documents: Sequence[dict[str, Any]],
    *,
    min_overlap: float = 0.35,
    ambiguity_margin: float = 0.05,
) -> dict[str, Any]:
    """Link reviewed component boxes to instances without transferring authority."""
    by_paint: dict[str, list[dict[str, Any]]] = {}
    for record in bank.get("records", ()):
        by_paint.setdefault(str(record["paint_label"]), []).append(record)
    links = []
    for document in label_documents:
        paint_label = str(document.get("paint_label") or "")
        instances = by_paint.get(paint_label, ())
        for label in document.get("component_labels") or ():
            expected_bbox = label.get("expected_bbox") or ()
            ranked = sorted(
                (
                    (_bbox_overlap_min(expected_bbox, record.get("bbox") or (0, 0, 0, 0)), record)
                    for record in instances
                ),
                key=lambda item: (-item[0], item[1]["instance_id"]),
            )
            top_score = ranked[0][0] if ranked else 0.0
            second_score = ranked[1][0] if len(ranked) > 1 else 0.0
            if top_score < float(min_overlap):
                status = "unmatched"
                instance_id = None
            elif second_score >= float(min_overlap) and top_score - second_score < float(ambiguity_margin):
                status = "ambiguous"
                instance_id = None
            else:
                status = "matched_for_review"
                instance_id = ranked[0][1]["instance_id"]
            links.append({
                "paint_label": paint_label,
                "source_layer": label.get("layer"),
                "source_component_index": label.get("component_index"),
                "expected_bbox": list(expected_bbox),
                "review_target_layer": label.get("target_layer"),
                "review_label": label.get("label"),
                "review_family_id": label.get("family_id"),
                "status": status,
                "instance_id": instance_id,
                "best_overlap_min": round(top_score, 6),
                "runner_up_overlap_min": round(second_score, 6),
                "candidate_instance_ids": [item[1]["instance_id"] for item in ranked[:3]],
                "ownership_authority": False,
                "human_review_required": True,
            })
    bank = dict(bank)
    bank["review_links"] = links
    bank["review_link_counts"] = {
        status: sum(item["status"] == status for item in links)
        for status in ("matched_for_review", "ambiguous", "unmatched")
    }
    return bank


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--labels-dir", type=Path)
    parser.add_argument("--label-prefix", default="")
    args = parser.parse_args()
    inspections = json.loads(args.inspection.read_text(encoding="utf-8"))
    if not isinstance(inspections, list):
        raise ValueError("inspection_records.json must contain a list")
    bank = build_feature_bank(inspections)
    if args.labels_dir:
        documents = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(args.labels_dir.glob(f"{args.label_prefix}*.json"))
        ]
        bank = attach_review_links(bank, documents)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bank, indent=2) + "\n", encoding="utf-8")
    summary = {key: bank[key] for key in (
        "schema", "paint_count", "instance_count", "ownership_authority", "casts_votes"
    )}
    if "review_link_counts" in bank:
        summary["review_link_counts"] = bank["review_link_counts"]
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
