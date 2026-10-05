"""Measure number-context shadow precision/recall on the full runtime population."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _coverage(candidate: Sequence[int], review: Sequence[int]) -> tuple[float, float, float]:
    cx, cy, cw, ch = (int(value) for value in candidate)
    rx, ry, rw, rh = (int(value) for value in review)
    overlap = max(0, min(cx + cw, rx + rw) - max(cx, rx)) * max(
        0, min(cy + ch, ry + rh) - max(cy, ry)
    )
    candidate_area = max(1, cw * ch)
    review_area = max(1, rw * rh)
    return (
        overlap / review_area,
        overlap / candidate_area,
        overlap / max(1, candidate_area + review_area - overlap),
    )


def _matches(candidate: Sequence[int], review: Sequence[int]) -> bool:
    review_coverage, containment, iou = _coverage(candidate, review)
    return review_coverage >= 0.50 and containment >= 0.10 and iou >= 0.20


def evaluate_runtime_population(
    inspections: Sequence[Mapping[str, Any]], positives: Sequence[Mapping[str, Any]],
    negatives: Sequence[Mapping[str, Any]], *, threshold: float,
    score_field: str = "number_score",
    status_field: str | None = None,
    accepted_status: str | None = None,
) -> dict[str, Any]:
    proposals_by_paint: dict[str, list[Mapping[str, Any]]] = {}
    for record in inspections:
        shadow = (
            record.get("route_adjudicator_shadow", {}).get("candidate_evidence", {})
            .get("decal_instances", {}).get("number_context_shadow", {})
        )
        proposals_by_paint[str(record.get("paint_label") or "")] = [
            item for item in shadow.get("proposal_records") or ()
            if (
                item.get(status_field) == accepted_status if status_field
                else float(item.get(score_field) or 0.0) >= threshold
            )
        ]
    positives = [item for item in positives if str(item.get("paint_label") or "") in proposals_by_paint]
    negatives = [item for item in negatives if str(item.get("paint_label") or "") in proposals_by_paint]

    def hit(item: Mapping[str, Any]) -> bool:
        return any(
            _matches(proposal["bbox"], item["bbox"])
            for proposal in proposals_by_paint.get(str(item.get("paint_label") or ""), ())
        )

    positive_hits = [item for item in positives if hit(item)]
    negative_hits = [item for item in negatives if hit(item)]
    return {
        "threshold": threshold,
        "score_field": score_field,
        "status_field": status_field,
        "accepted_proposal_count": sum(len(items) for items in proposals_by_paint.values()),
        "positive_copy_hits": len(positive_hits),
        "positive_copy_total": len(positives),
        "hard_negative_hits": len(negative_hits),
        "hard_negative_total": len(negatives),
        "positive_hit_keys": [
            f"{item['paint_label']}::{item.get('copy', item.get('label', 'positive'))}"
            for item in positive_hits
        ],
        "hard_negative_hit_keys": [
            f"{item['paint_label']}::{item.get('label', item.get('semantic', 'negative'))}"
            for item in negative_hits
        ],
    }


def _labels(labels_dir: Path, cycle: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positives = list(
        (_read(labels_dir / f"cycle{cycle}_missed_number_instances_v1.json").get("instances") or ())
    )
    negatives = []
    for path in labels_dir.glob(f"cycle{cycle}_*_numbers_v1.json"):
        payload = _read(path)
        for item in payload.get("component_labels") or ():
            semantic = str(item.get("target_layer") or "").lower()
            if semantic in {"numbers", "uncertain", ""}:
                continue
            negatives.append({
                "paint_label": str(payload.get("paint_label") or ""),
                "bbox": list(item.get("expected_bbox") or ()),
                "semantic": semantic,
                "label": str(item.get("label") or semantic),
            })
    physical_path = labels_dir / f"cycle{cycle}_physical_groups_v1.json"
    if physical_path.exists():
        physical = _read(physical_path)
        audit = _read(Path(str(physical["physical_group_audit"])))
        audit_by_paint = {
            str(item.get("paint_label") or ""): item for item in audit.get("paints") or ()
        }
        for paint, targets in (physical.get("paint_group_targets") or {}).items():
            groups = (audit_by_paint.get(str(paint)) or {}).get("groups") or ()
            for index, target in enumerate(targets or ()):
                semantic = str(target or "").lower()
                if semantic in {"numbers", "uncertain", ""} or index >= len(groups):
                    continue
                negatives.append({
                    "paint_label": str(paint),
                    "bbox": list(groups[index].get("bbox") or ()),
                    "semantic": semantic,
                    "label": f"physical_group_{semantic}",
                })
    return positives, [item for item in negatives if len(item["bbox"]) == 4]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    inspections = _read(args.inspection)
    positives, negatives = _labels(args.labels_dir, args.cycle)
    shadow = (
        inspections[0]["route_adjudicator_shadow"]["candidate_evidence"]
        ["decal_instances"]["number_context_shadow"]
    )
    stage = shadow.get("position") or shadow["semantic"]
    score_field = "position_score" if shadow.get("position") else "number_score"
    status_field = "position_status" if shadow.get("position") else None
    accepted_status = "corroborated_number_candidate" if status_field else None
    threshold = float(args.threshold if args.threshold is not None else stage["decision_threshold"])
    result = {
        "schema": "smart-tga-number-context-runtime-gate-v1",
        "cycle": args.cycle,
        "inspection": str(args.inspection).replace("\\", "/"),
        "model_version": stage.get("model_version"),
        **evaluate_runtime_population(
            inspections, positives, negatives,
            threshold=threshold, score_field=score_field,
            status_field=status_field, accepted_status=accepted_status,
        ),
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
