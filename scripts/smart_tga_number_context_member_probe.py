"""Train a paint-disjoint raw-instance selector for context mask assembly."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
    from engine.spec_sculpt.number_context_members import (
        assemble_member_mask, member_feature_mapping,
    )
    from engine.spec_sculpt.number_context_position import position_feature_mapping
    from engine.spec_sculpt.number_context_semantics import context_feature_mapping
    from engine.spec_sculpt.number_family_shadow import PortableExtraTrees
    from scripts.smart_tga_number_context_proposal_probe import generate_context_proposals
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle  # type: ignore
    from engine.spec_sculpt.number_context_members import (  # type: ignore
        assemble_member_mask, member_feature_mapping,
    )
    from engine.spec_sculpt.number_context_position import position_feature_mapping  # type: ignore
    from engine.spec_sculpt.number_context_semantics import context_feature_mapping  # type: ignore
    from engine.spec_sculpt.number_family_shadow import PortableExtraTrees  # type: ignore
    from scripts.smart_tga_number_context_proposal_probe import generate_context_proposals  # type: ignore
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches  # type: ignore


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _intersection(left: Sequence[int], right: Sequence[int]) -> int:
    lx, ly, lw, lh = (int(value) for value in left)
    rx, ry, rw, rh = (int(value) for value in right)
    return max(0, min(lx + lw, rx + rw) - max(lx, rx)) * max(
        0, min(ly + lh, ry + rh) - max(ly, ry)
    )


def _feature_records(inspection: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = (
        inspection["route_adjudicator_shadow"]["candidate_evidence"]
        ["decal_instances"]["features"]["records"]
    )
    return [
        {**item, "local_mask": decode_instance_mask_rle(item["mask_rle"])}
        for item in records
    ]


def _historical_contexts(
    labels_dir: Path, cycles: Sequence[int], prototypes: Sequence[Sequence[float]],
    semantic: PortableExtraTrees, position: PortableExtraTrees,
) -> list[dict[str, Any]]:
    contexts = []
    for cycle in cycles:
        annotation = _read(labels_dir / f"cycle{cycle}_missed_number_instances_v1.json")
        inspections = _read(Path(str(annotation["inspection_records"])))
        positives, negatives = _labels(labels_dir, cycle)
        labels_by_paint: dict[str, list[Mapping[str, Any]]] = {}
        for item in (*positives, *negatives):
            labels_by_paint.setdefault(str(item["paint_label"]), []).append(item)
        for inspection in inspections:
            paint = str(inspection.get("paint_label") or "")
            regions = labels_by_paint.get(paint, ())
            if not regions:
                continue
            rgb = np.asarray(Image.open(inspection["source_1024"]).convert("RGB"))
            instances = _feature_records(inspection)
            by_id = {str(item["instance_id"]): item for item in instances}
            proposals = generate_context_proposals(instances, prototypes)
            for proposal in proposals:
                if not any(_matches(proposal["bbox"], item["bbox"]) for item in regions):
                    continue
                seed = by_id.get(str(proposal["seed_instance_id"]))
                if seed is None:
                    continue
                semantic_score = semantic.score(context_feature_mapping(rgb, proposal, seed))
                if semantic_score < float(semantic.metadata["decision_threshold"]):
                    continue
                position_score = position.score(position_feature_mapping(proposal))
                if position_score < float(position.metadata["decision_threshold"]):
                    continue
                members = [
                    item for item in instances
                    if _intersection(item["bbox"], proposal["bbox"]) > 0
                ]
                contexts.append({
                    "cycle": cycle, "paint_label": paint, "proposal": proposal,
                    "seed": seed, "members": members,
                    "source_1024": str(inspection["source_1024"]),
                })
    return contexts


def _runtime_contexts(inspection_path: Path, cycle: int) -> list[dict[str, Any]]:
    contexts = []
    for inspection in _read(inspection_path):
        paint = str(inspection.get("paint_label") or "")
        instances = _feature_records(inspection)
        by_id = {str(item["instance_id"]): item for item in instances}
        proposals = (
            inspection["route_adjudicator_shadow"]["candidate_evidence"]
            ["decal_instances"]["number_context_shadow"]["proposal_records"]
        )
        for proposal in proposals:
            if proposal.get("position_status") != "corroborated_number_candidate":
                continue
            contexts.append({
                "cycle": cycle, "paint_label": paint, "proposal": proposal,
                "seed": by_id[str(proposal["seed_instance_id"])],
                "source_1024": str(inspection["source_1024"]),
                "members": [
                    item for item in instances
                    if _intersection(item["bbox"], proposal["bbox"]) > 0
                ],
            })
    return contexts


def _supervised_rows(
    contexts: Sequence[Mapping[str, Any]], labels_dir: Path, cycles: Sequence[int],
) -> list[dict[str, Any]]:
    labels = {cycle: _labels(labels_dir, cycle) for cycle in cycles}
    rows = []
    for context in contexts:
        positives, negatives = labels[int(context["cycle"])]
        paint = str(context["paint_label"])
        positives = [item for item in positives if item["paint_label"] == paint]
        negatives = [item for item in negatives if item["paint_label"] == paint]
        for member in context["members"]:
            area = max(1, int(member["bbox"][2]) * int(member["bbox"][3]))
            positive_overlap = max(
                [_intersection(member["bbox"], item["bbox"]) / area for item in positives] or [0.0]
            )
            negative_overlap = max(
                [_intersection(member["bbox"], item["bbox"]) / area for item in negatives] or [0.0]
            )
            label = (
                1 if positive_overlap >= 0.50 and negative_overlap < 0.20
                else 0 if negative_overlap >= 0.50 and positive_overlap < 0.20
                else None
            )
            if label is None:
                continue
            mapping = member_feature_mapping(member, context["proposal"], context["seed"])
            rows.append({
                "cycle": int(context["cycle"]), "paint_label": paint,
                "proposal_id": context["proposal"].get("proposal_id"),
                "instance_id": member["instance_id"], "label": label,
                "features": mapping,
            })
    return rows


def _tight_bbox(mask: np.ndarray, proposal_bbox: Sequence[int]) -> list[int] | None:
    rows, columns = np.nonzero(mask)
    if not len(columns):
        return None
    x, y, _width, _height = (int(value) for value in proposal_bbox)
    return [
        x + int(columns.min()), y + int(rows.min()),
        int(columns.max() - columns.min() + 1), int(rows.max() - rows.min() + 1),
    ]


def _score_contexts(model: Any, contexts: Sequence[Mapping[str, Any]]) -> None:
    for context in contexts:
        mappings = [
            member_feature_mapping(item, context["proposal"], context["seed"])
            for item in context["members"]
        ]
        context["member_scores"] = (
            model.predict_proba(np.asarray([list(item.values()) for item in mappings]))[:, 1]
            if mappings else np.zeros(0, dtype=np.float64)
        )


def _metrics(
    contexts: Sequence[Mapping[str, Any]], labels_dir: Path, cycle: int, threshold: float,
    paint_labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    positives, negatives = _labels(labels_dir, cycle)
    paints = (
        {str(item) for item in paint_labels}
        if paint_labels is not None
        else {str(item["paint_label"]) for item in contexts}
    )
    positives = [item for item in positives if item["paint_label"] in paints]
    negatives = [item for item in negatives if item["paint_label"] in paints]
    by_paint: dict[str, list[dict[str, Any]]] = {paint: [] for paint in paints}
    selected_count = 0
    mask_pixels = 0
    for context in contexts:
        mask, selected = assemble_member_mask(
            context["proposal"]["bbox"], context["members"], context["member_scores"],
            threshold=threshold,
        )
        selected_count += len(selected)
        mask_pixels += int(np.count_nonzero(mask))
        tight = _tight_bbox(mask, context["proposal"]["bbox"])
        if tight is not None:
            by_paint[str(context["paint_label"])].append({"bbox": tight})

    def hit(item: Mapping[str, Any]) -> bool:
        return any(
            _matches(candidate["bbox"], item["bbox"])
            for candidate in by_paint.get(str(item["paint_label"]), ())
        )

    return {
        "threshold": float(threshold),
        "context_count": len(contexts),
        "selected_member_count": selected_count,
        "mask_pixels": mask_pixels,
        "positive_bbox_hits": sum(hit(item) for item in positives),
        "positive_bbox_total": len(positives),
        "hard_negative_bbox_hits": sum(hit(item) for item in negatives),
        "hard_negative_bbox_total": len(negatives),
    }


def _export(model: Any, feature_names: Sequence[str], threshold: float, output: Path) -> None:
    offsets = [0]
    left: list[int] = []
    right: list[int] = []
    split_feature: list[int] = []
    split_threshold: list[float] = []
    positive: list[float] = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        base = offsets[-1]
        left.extend(int(value + base) if value >= 0 else -1 for value in tree.children_left)
        right.extend(int(value + base) if value >= 0 else -1 for value in tree.children_right)
        split_feature.extend(int(value) for value in tree.feature)
        split_threshold.extend(float(value) for value in tree.threshold)
        for values in tree.value[:, 0, :]:
            total = float(np.sum(values))
            positive.append(float(values[1] / total) if total else 0.0)
        offsets.append(base + int(tree.node_count))
    metadata = {
        "schema": "smart-tga-number-context-member-extra-trees-v1",
        "version": "cycle700-dlm-context-member-v1",
        "decision_threshold": float(threshold),
        "tree_count": len(model.estimators_),
        "train_cycles": list(range(683, 691)),
        "calibration_cycles": [693],
        "canary_cycles_excluded": [695],
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output, metadata_json=np.asarray(json.dumps(metadata), dtype=np.str_),
        feature_names=np.asarray(feature_names, dtype=np.str_),
        tree_offsets=np.asarray(offsets, dtype=np.int32),
        children_left=np.asarray(left, dtype=np.int32), children_right=np.asarray(right, dtype=np.int32),
        split_feature=np.asarray(split_feature, dtype=np.int32),
        split_threshold=np.asarray(split_threshold, dtype=np.float64),
        positive_probability=np.asarray(positive, dtype=np.float64),
    )


def run(
    labels_dir: Path, prototype_path: Path, semantic_path: Path, position_path: Path,
    calibration_inspection: Path, canary_inspection: Path, model_output: Path,
) -> dict[str, Any]:
    from sklearn.ensemble import ExtraTreesClassifier

    prototypes = _read(prototype_path)["prototypes"]
    semantic = PortableExtraTrees(semantic_path)
    position = PortableExtraTrees(position_path)
    train_contexts = _historical_contexts(
        labels_dir, list(range(683, 691)), prototypes, semantic, position,
    )
    train_rows = _supervised_rows(train_contexts, labels_dir, list(range(683, 691)))
    feature_names = list(train_rows[0]["features"])
    matrix = np.asarray([[row["features"][name] for name in feature_names] for row in train_rows])
    labels = np.asarray([row["label"] for row in train_rows], dtype=np.int8)
    model = ExtraTreesClassifier(
        n_estimators=700, min_samples_leaf=2, max_features="sqrt",
        class_weight="balanced", random_state=700, n_jobs=-1,
    ).fit(matrix, labels)

    calibration_records = _read(calibration_inspection)
    canary_records = _read(canary_inspection)
    calibration_contexts = _runtime_contexts(calibration_inspection, 693)
    canary_contexts = _runtime_contexts(canary_inspection, 695)
    _score_contexts(model, calibration_contexts)
    _score_contexts(model, canary_contexts)
    calibration_rows = _supervised_rows(calibration_contexts, labels_dir, [693])
    negative_scores = []
    score_by_key = {
        (context["paint_label"], context["proposal"]["proposal_id"], member["instance_id"]): score
        for context in calibration_contexts
        for member, score in zip(context["members"], context["member_scores"])
    }
    for row in calibration_rows:
        if row["label"] == 0:
            key = (row["paint_label"], row["proposal_id"], row["instance_id"])
            if key in score_by_key:
                negative_scores.append(float(score_by_key[key]))
    threshold = min(1.0, max(negative_scores, default=0.5) + 1e-9)
    calibration_metrics = _metrics(
        calibration_contexts, labels_dir, 693, threshold,
        [str(item.get("paint_label") or "") for item in calibration_records],
    )
    canary_metrics = _metrics(
        canary_contexts, labels_dir, 695, threshold,
        [str(item.get("paint_label") or "") for item in canary_records],
    )
    _export(model, feature_names, threshold, model_output)
    return {
        "schema": "smart-tga-number-context-member-probe-v1",
        "train_context_count": len(train_contexts),
        "train_sample_count": len(train_rows),
        "train_positive_count": int(np.count_nonzero(labels == 1)),
        "train_negative_count": int(np.count_nonzero(labels == 0)),
        "feature_count": len(feature_names),
        "threshold": threshold,
        "calibration_cycle693": calibration_metrics,
        "untouched_canary_cycle695": canary_metrics,
        "model_output": str(model_output).replace("\\", "/"),
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--prototype", type=Path, default=Path("engine/spec_sculpt/models/smart_tga_number_context_cycle696_v1.json"))
    parser.add_argument("--semantic", type=Path, default=Path("engine/spec_sculpt/models/smart_tga_number_context_semantic_cycle697_v2.npz"))
    parser.add_argument("--position", type=Path, default=Path("engine/spec_sculpt/models/smart_tga_number_context_position_cycle699_v1.npz"))
    parser.add_argument("--calibration-inspection", type=Path, required=True)
    parser.add_argument("--canary-inspection", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(
        args.labels_dir, args.prototype, args.semantic, args.position,
        args.calibration_inspection, args.canary_inspection, args.model_output,
    )
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
