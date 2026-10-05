"""Learn owner-neutral context-envelope proposals for fragmented number copies.

Reviewed boxes supervise relative context transforms offline. Runtime-facing
proposals contain only a bbox, seed instance id, and prototype id; they do not
contain review coordinates, cast votes, own masks, or add pixels. Model size is
selected with paint-grouped OOF recall before validation/canary evaluation.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


IMAGE_SIDE = 1024
K_CANDIDATES = (4, 8, 12, 16, 24)
MAX_CONTEXT_AREA_FRACTION = 0.15
MIN_CONTEXT_IOU = 0.20


def _read(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def _candidate_records(inspections: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result = {}
    for inspection in inspections:
        paint = str(inspection.get("paint_label") or "")
        records = (
            (inspection.get("route_adjudicator_shadow") or {})
            .get("candidate_evidence", {}).get("decal_instances", {})
            .get("features", {}).get("records", ())
        )
        result[paint] = [dict(record) for record in records if record.get("bbox")]
    return result


def _load_cycle(labels_dir: Path, cycle: int) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    annotation_path = labels_dir / f"cycle{cycle}_missed_number_instances_v1.json"
    annotations = _read(annotation_path)
    inspection_path = Path(str(annotations["inspection_records"]))
    inspections = _read(inspection_path)
    instances = [dict(item, cycle=cycle) for item in annotations.get("instances") or ()]
    return instances, _candidate_records(inspections)


def _relative_transform(candidate: Sequence[int], review: Sequence[int]) -> np.ndarray:
    cx, cy, cw, ch = (float(value) for value in candidate)
    rx, ry, rw, rh = (float(value) for value in review)
    return np.asarray([
        (rx + rw / 2.0 - (cx + cw / 2.0)) / max(cw, 1.0),
        (ry + rh / 2.0 - (cy + ch / 2.0)) / max(ch, 1.0),
        math.log(max(rw, 1.0) / max(cw, 1.0)),
        math.log(max(rh, 1.0) / max(ch, 1.0)),
    ], dtype=np.float64)


def _transform_samples(
    annotations: Sequence[Mapping[str, Any]], candidates_by_paint: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[np.ndarray, np.ndarray]:
    rows, groups = [], []
    for annotation in annotations:
        paint = str(annotation["paint_label"])
        review = annotation["bbox"]
        ranked = []
        for candidate in candidates_by_paint.get(paint, ()):
            review_coverage, containment, _ = _coverage(candidate["bbox"], review)
            if review_coverage >= 0.02 and containment >= 0.55:
                ranked.append((review_coverage, candidate))
        for _, candidate in sorted(ranked, key=lambda item: item[0], reverse=True)[:3]:
            rows.append(_relative_transform(candidate["bbox"], review))
            groups.append(paint)
    if not rows:
        return np.empty((0, 4), dtype=np.float64), np.empty((0,), dtype=object)
    return np.stack(rows), np.asarray(groups, dtype=object)


def _fit_prototypes(rows: np.ndarray, k: int) -> list[list[float]]:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    if rows.shape[0] == 0:
        return []
    count = min(int(k), int(rows.shape[0]))
    scaler = StandardScaler().fit(rows)
    model = KMeans(n_clusters=count, random_state=694, n_init=20).fit(scaler.transform(rows))
    centers = scaler.inverse_transform(model.cluster_centers_)
    return [[round(float(value), 8) for value in center] for center in centers]


def _intrinsic_seed(candidate: Mapping[str, Any]) -> bool:
    bbox = candidate.get("bbox") or ()
    if len(bbox) != 4:
        return False
    _, _, width, height = (int(value) for value in bbox)
    area_fraction = float(candidate.get("area_fraction") or (width * height / IMAGE_SIDE**2))
    return width >= 4 and height >= 4 and 0.00005 <= area_fraction <= 0.08


def _apply_prototype(bbox: Sequence[int], prototype: Sequence[float]) -> list[int] | None:
    x, y, width, height = (float(value) for value in bbox)
    dx, dy, log_width, log_height = (float(value) for value in prototype)
    new_width = min(float(IMAGE_SIDE), max(4.0, width * math.exp(log_width)))
    new_height = min(float(IMAGE_SIDE), max(4.0, height * math.exp(log_height)))
    if new_width * new_height > MAX_CONTEXT_AREA_FRACTION * IMAGE_SIDE**2:
        return None
    center_x = x + width / 2.0 + dx * width
    center_y = y + height / 2.0 + dy * height
    x0 = max(0, min(IMAGE_SIDE - 1, int(round(center_x - new_width / 2.0))))
    y0 = max(0, min(IMAGE_SIDE - 1, int(round(center_y - new_height / 2.0))))
    x1 = max(x0 + 1, min(IMAGE_SIDE, int(round(center_x + new_width / 2.0))))
    y1 = max(y0 + 1, min(IMAGE_SIDE, int(round(center_y + new_height / 2.0))))
    return [x0, y0, x1 - x0, y1 - y0]


def generate_context_proposals(
    candidates: Sequence[Mapping[str, Any]], prototypes: Sequence[Sequence[float]],
) -> list[dict[str, Any]]:
    proposals, seen = [], set()
    for candidate in candidates:
        if not _intrinsic_seed(candidate):
            continue
        for prototype_index, prototype in enumerate(prototypes):
            bbox = _apply_prototype(candidate["bbox"], prototype)
            if bbox is None:
                continue
            key = tuple(bbox)
            if key in seen:
                continue
            seen.add(key)
            proposals.append({
                "bbox": bbox,
                "seed_instance_id": str(candidate.get("instance_id") or ""),
                "prototype_index": prototype_index,
                "source": "number_context_envelope_shadow",
                "casts_votes": False,
                "ownership_authority": False,
                "adds_pixels": False,
            })
    return proposals


def _evaluate(
    annotations: Sequence[Mapping[str, Any]], candidates_by_paint: Mapping[str, Sequence[Mapping[str, Any]]],
    prototypes: Sequence[Sequence[float]],
) -> dict[str, Any]:
    proposal_cache = {
        paint: generate_context_proposals(candidates, prototypes)
        for paint, candidates in candidates_by_paint.items()
    }
    records = []
    for annotation in annotations:
        paint = str(annotation["paint_label"])
        review = annotation["bbox"]
        raw = candidates_by_paint.get(paint, ())
        proposals = proposal_cache.get(paint, ())
        raw_ranked = sorted(
            ((_coverage(candidate["bbox"], review), candidate) for candidate in raw),
            key=lambda item: (item[0][0], item[0][2]), reverse=True,
        )
        proposal_ranked = sorted(
            ((_coverage(proposal["bbox"], review), proposal) for proposal in proposals),
            key=lambda item: (item[0][2], item[0][0]), reverse=True,
        )
        raw_best = raw_ranked[0] if raw_ranked else ((0.0, 0.0, 0.0), {})
        proposal_best = proposal_ranked[0] if proposal_ranked else ((0.0, 0.0, 0.0), {})
        raw_complete = raw_best[0][0] >= 0.50 and raw_best[0][1] >= 0.10
        proposal_complete = (
            proposal_best[0][0] >= 0.50
            and proposal_best[0][1] >= 0.10
            and proposal_best[0][2] >= MIN_CONTEXT_IOU
        )
        records.append({
            "paint_label": paint,
            "family_id": annotation.get("family_id"),
            "copy": annotation.get("copy"),
            "raw_complete": raw_complete,
            "context_complete": proposal_complete,
            "raw_best_review_coverage": round(float(raw_best[0][0]), 6),
            "context_best_review_coverage": round(float(proposal_best[0][0]), 6),
            "context_best_candidate_containment": round(float(proposal_best[0][1]), 6),
            "context_best_iou": round(float(proposal_best[0][2]), 6),
            "best_context_proposal": proposal_best[1],
        })
    paints = sorted({str(item["paint_label"]) for item in annotations})
    raw_complete = sum(bool(item["raw_complete"]) for item in records)
    context_complete = sum(bool(item["context_complete"]) for item in records)
    counts = [len(proposal_cache.get(paint, ())) for paint in paints]
    raw_counts = [len(candidates_by_paint.get(paint, ())) for paint in paints]
    return {
        "reviewed_copy_count": len(records),
        "raw_complete_copy_count": raw_complete,
        "context_complete_copy_count": context_complete,
        "raw_complete_recall": round(raw_complete / max(1, len(records)), 6),
        "context_complete_recall": round(context_complete / max(1, len(records)), 6),
        "paint_count": len(paints),
        "mean_raw_candidate_count": round(float(np.mean(raw_counts)), 3) if raw_counts else 0.0,
        "mean_context_proposal_count": round(float(np.mean(counts)), 3) if counts else 0.0,
        "mean_proposal_growth": round(
            float(np.mean([count / max(1, raw) for count, raw in zip(counts, raw_counts)])), 3
        ) if counts else 0.0,
        "records": records,
    }


def _merge_cycles(
    labels_dir: Path, cycles: Sequence[int],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    annotations, candidates = [], {}
    for cycle in cycles:
        cycle_annotations, cycle_candidates = _load_cycle(labels_dir, cycle)
        annotations.extend(cycle_annotations)
        candidates.update(cycle_candidates)
    return annotations, candidates


def _false_number_controls(labels_dir: Path, cycles: Sequence[int]) -> list[dict[str, Any]]:
    controls = []
    for cycle in cycles:
        for path in sorted(labels_dir.glob(f"cycle{cycle}_*_numbers_v1.json")):
            payload = _read(path)
            paint = str(payload.get("paint_label") or "")
            for item in payload.get("component_labels") or ():
                if str(item.get("target_layer") or "").lower() == "numbers":
                    continue
                controls.append({
                    "paint_label": paint,
                    "bbox": list(item.get("expected_bbox") or ()),
                    "target_layer": item.get("target_layer"),
                    "label": item.get("label"),
                })
    return [item for item in controls if len(item["bbox"]) == 4]


def _evaluate_false_number_controls(
    controls: Sequence[Mapping[str, Any]],
    candidates_by_paint: Mapping[str, Sequence[Mapping[str, Any]]],
    prototypes: Sequence[Sequence[float]],
) -> dict[str, Any]:
    proposal_cache = {
        paint: generate_context_proposals(candidates, prototypes)
        for paint, candidates in candidates_by_paint.items()
    }
    records = []
    for control in controls:
        proposals = proposal_cache.get(str(control["paint_label"]), ())
        ranked = sorted(
            ((_coverage(proposal["bbox"], control["bbox"]), proposal) for proposal in proposals),
            key=lambda item: (item[0][0], item[0][2]), reverse=True,
        )
        best = ranked[0] if ranked else ((0.0, 0.0, 0.0), {})
        collision = best[0][0] >= 0.50 and best[0][1] >= 0.10
        records.append({
            **dict(control),
            "proposal_collision": collision,
            "best_review_coverage": round(float(best[0][0]), 6),
            "best_candidate_containment": round(float(best[0][1]), 6),
            "best_iou": round(float(best[0][2]), 6),
        })
    collisions = sum(bool(item["proposal_collision"]) for item in records)
    return {
        "reviewed_false_number_count": len(records),
        "proposal_collision_count": collisions,
        "proposal_collision_rate": round(collisions / max(1, len(records)), 6),
        "interpretation": "proposal-only coverage; never an ownership false positive",
        "records": records,
    }


def run(
    labels_dir: Path, train_cycles: Sequence[int], validation_cycles: Sequence[int],
    canary_cycles: Sequence[int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    from sklearn.model_selection import KFold

    train_annotations, train_candidates = _merge_cycles(labels_dir, train_cycles)
    validation_annotations, validation_candidates = _merge_cycles(labels_dir, validation_cycles)
    canary_annotations, canary_candidates = _merge_cycles(labels_dir, canary_cycles)
    rows, groups = _transform_samples(train_annotations, train_candidates)
    unique_paints = sorted({str(item["paint_label"]) for item in train_annotations})
    folds = min(5, len(unique_paints))
    if folds < 2:
        raise ValueError("at least two training paints are required")
    selection = []
    splitter = KFold(n_splits=folds, shuffle=True, random_state=694)
    for k in K_CANDIDATES:
        fold_records = []
        for train_index, test_index in splitter.split(unique_paints):
            train_paints = {unique_paints[index] for index in train_index}
            held_paints = {unique_paints[index] for index in test_index}
            row_mask = np.asarray([paint in train_paints for paint in groups], dtype=bool)
            prototypes = _fit_prototypes(rows[row_mask], k)
            held_annotations = [
                item for item in train_annotations if str(item["paint_label"]) in held_paints
            ]
            held_candidates = {
                paint: train_candidates[paint] for paint in held_paints if paint in train_candidates
            }
            fold_records.append(_evaluate(held_annotations, held_candidates, prototypes))
        copies = sum(item["reviewed_copy_count"] for item in fold_records)
        complete = sum(item["context_complete_copy_count"] for item in fold_records)
        selection.append({
            "prototype_count": k,
            "oof_reviewed_copy_count": copies,
            "oof_context_complete_copy_count": complete,
            "oof_context_complete_recall": round(complete / max(1, copies), 6),
            "oof_mean_proposal_growth": round(float(np.mean([
                item["mean_proposal_growth"] for item in fold_records
            ])), 3),
        })
    # Proposal recall is the goal, but raw candidate fan-out is a real runtime
    # cost. Choose the lowest-growth model within 1.1 percentage points of the
    # best paint-disjoint OOF recall; validation/canary never select capacity.
    best_oof_recall = max(item["oof_context_complete_recall"] for item in selection)
    near_best = [
        item for item in selection
        if item["oof_context_complete_recall"] >= best_oof_recall - 0.011
    ]
    selected = min(near_best, key=lambda item: (
        item["oof_mean_proposal_growth"], item["prototype_count"],
    ))
    prototypes = _fit_prototypes(rows, int(selected["prototype_count"]))
    validation_controls = _false_number_controls(labels_dir, validation_cycles)
    canary_controls = _false_number_controls(labels_dir, canary_cycles)
    report = {
        "schema": "smart-tga-number-context-proposal-probe-v1",
        "train_cycles": list(train_cycles),
        "validation_cycles": list(validation_cycles),
        "canary_cycles": list(canary_cycles),
        "transform_sample_count": int(rows.shape[0]),
        "train_paint_count": len(unique_paints),
        "paint_grouped_oof_selection": selection,
        "selection_policy": "lowest proposal growth within 0.011 recall of best grouped-OOF result",
        "selected_prototype_count": int(selected["prototype_count"]),
        "selected_oof": selected,
        "train_refit": _evaluate(train_annotations, train_candidates, prototypes),
        "validation": _evaluate(validation_annotations, validation_candidates, prototypes),
        "canary": _evaluate(canary_annotations, canary_candidates, prototypes),
        "validation_false_number_controls": _evaluate_false_number_controls(
            validation_controls, validation_candidates, prototypes,
        ),
        "canary_false_number_controls": _evaluate_false_number_controls(
            canary_controls, canary_candidates, prototypes,
        ),
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }
    portable = {
        "schema": "smart-tga-number-context-prototypes-v1",
        "version": "cycle696-dlm-context-envelope-v1",
        "feature_order": ["center_dx_per_seed_width", "center_dy_per_seed_height", "log_width_ratio", "log_height_ratio"],
        "prototypes": prototypes,
        "intrinsic_seed_contract": {"minimum_side": 4, "area_fraction_min": 0.00005, "area_fraction_max": 0.08},
        "context_contract": {"maximum_area_fraction": MAX_CONTEXT_AREA_FRACTION, "minimum_evaluation_iou": MIN_CONTEXT_IOU},
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }
    return report, portable


def _cycles(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-dir", default="smart_tga_review_labels")
    parser.add_argument("--train-cycles", default="683,684,685,686,687,688,689,690")
    parser.add_argument("--validation-cycles", default="693")
    parser.add_argument("--canary-cycles", default="695")
    parser.add_argument("--output", required=True)
    parser.add_argument("--prototypes-output", required=True)
    args = parser.parse_args()
    report, portable = run(
        Path(args.labels_dir), _cycles(args.train_cycles),
        _cycles(args.validation_cycles), _cycles(args.canary_cycles),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    prototype_output = Path(args.prototypes_output)
    prototype_output.parent.mkdir(parents=True, exist_ok=True)
    prototype_output.write_text(json.dumps(portable, indent=2) + "\n", encoding="utf-8")
    compact = {key: value for key, value in report.items() if key not in {
        "train_refit", "validation", "canary", "validation_false_number_controls",
        "canary_false_number_controls",
    }}
    compact["validation"] = {key: value for key, value in report["validation"].items() if key != "records"}
    compact["canary"] = {key: value for key, value in report["canary"].items() if key != "records"}
    compact["validation_false_number_controls"] = {
        key: value for key, value in report["validation_false_number_controls"].items()
        if key != "records"
    }
    compact["canary_false_number_controls"] = {
        key: value for key, value in report["canary_false_number_controls"].items()
        if key != "records"
    }
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
