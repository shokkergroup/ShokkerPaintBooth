"""Train and paint-disjoint evaluate the zero-authority tiled semantic scorer."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

try:
    from engine.spec_sculpt.number_tiled_palette_proposals import (
        assemble_adjacent_tiled_palette_companions,
        corroborate_tiled_number_families,
        multiscale_tiled_palette_proposals,
        position_ranked_tiled_shortlist,
        repeated_tiled_palette_shortlist,
    )
    from engine.spec_sculpt.tiled_palette_semantics import feature_matrix
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_tiled_palette_proposals import (  # type: ignore
        assemble_adjacent_tiled_palette_companions,
        corroborate_tiled_number_families,
        multiscale_tiled_palette_proposals,
        position_ranked_tiled_shortlist,
        repeated_tiled_palette_shortlist,
    )
    from engine.spec_sculpt.tiled_palette_semantics import feature_matrix  # type: ignore


DEFAULT_REVIEWS = (
    "smart_tga_review_labels/cycle718_dlm_local_copy_untouched_v1.json",
    "smart_tga_review_labels/cycle718_dlm_shape_generalization_v1.json",
    "smart_tga_review_labels/cycle719_dlm_purity_active_learning_v1.json",
    "smart_tga_review_labels/cycle720_dlm_visual_prototype_untouched_v1.json",
    "smart_tga_review_labels/cycle685_dirtlatemodel_350_car_num_1000912_numbers_v1.json",
    "smart_tga_review_labels/cycle685_dirtlatemodel_350_car_num_1006305_numbers_v1.json",
    "smart_tga_review_labels/cycle685_dirtlatemodel_358_car_num_1003732_numbers_v1.json",
    "smart_tga_review_labels/cycle686_dirtlatemodel_350_car_num_1007631_numbers_v1.json",
    "smart_tga_review_labels/cycle686_dirtlatemodel_350_car_num_1008063_numbers_v1.json",
    "smart_tga_review_labels/cycle686_dirtlatemodel_358_car_num_1008515_numbers_v1.json",
)
CONTROL_PAINTS = {
    "dirtlatemodel 350/car_num_1006305.tga",
    "dirtlatemodel 350/car_num_1007631.tga",
    "dirtlatemodel 358/car_num_1008515.tga",
    "dirtlatemodel 358/car_num_1328151.tga",
    "dirtlatemodel 358/car_num_247671.tga",
}
CLASSES = ("Number", "Sponsor", "Template/hardware", "Paint/livery", "uncertain")


def _intersection(first, second):
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by)
    )


def _union(boxes):
    x0 = min(box[0] for box in boxes)
    y0 = min(box[1] for box in boxes)
    x1 = max(box[0] + box[2] for box in boxes)
    y1 = max(box[1] + box[3] for box in boxes)
    return [x0, y0, x1 - x0, y1 - y0]


def _semantic(value):
    value = str(value).lower()
    if value == "number" or value == "numbers":
        return "Number"
    if "sponsor" in value:
        return "Sponsor"
    if "template" in value or "hardware" in value:
        return "Template/hardware"
    if "paint" in value or "livery" in value:
        return "Paint/livery"
    return "uncertain"


def _orientation(label):
    for value in ("upper", "lower", "deck", "roof", "rear"):
        if value in label:
            return value
    return "ungrouped"


def load_review_references(paths):
    references = defaultdict(lambda: {"positive": [], "negative": []})
    for path in paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for row in payload.get("candidate_labels", []):
            paint = row["paint"]
            semantic = _semantic(row.get("semantic"))
            entry = {
                "bbox": list(map(int, row["bbox"])),
                "semantic": semantic,
                "source": str(path),
                "physical_copy": row.get("physical_copy"),
            }
            if semantic == "Number" and row.get("complete_copy"):
                references[paint]["positive"].append(entry)
            elif semantic != "Number":
                references[paint]["negative"].append(entry)

        paint = payload.get("paint_label")
        if not paint:
            continue
        number_groups = defaultdict(list)
        for row in payload.get("component_labels", []):
            label = str(row.get("label", "")).lower()
            target = _semantic(row.get("target_layer"))
            entry = {
                "bbox": list(map(int, row["expected_bbox"])),
                "semantic": target,
                "source": str(path),
                "physical_copy": None,
            }
            if target != "Number" or "false_number" in label:
                references[paint]["negative"].append(entry)
                continue
            if "mixed" in label:
                continue
            orientation = _orientation(label)
            number_groups[orientation].append((label, entry["bbox"]))
            if not any(token in label for token in ("fragment", "digit", "companion")):
                references[paint]["positive"].append(entry)
        for orientation, members in number_groups.items():
            labels = [item[0] for item in members]
            # Separate digits and companion colors are incomplete alone but a
            # reviewed group union is a valid offline complete-copy target.
            if len(members) >= 2 and any(
                token in label for label in labels for token in ("digit", "companion")
            ):
                references[paint]["positive"].append({
                    "bbox": _union([item[1] for item in members]),
                    "semantic": "Number",
                    "source": str(path),
                    "physical_copy": f"component-union:{orientation}",
                })
    return references


def load_probe_sources(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {row["paint_label"]: row["source_1024"] for row in payload["records"]}


def build_candidates(image, panel_map, maximum=96):
    raw = multiscale_tiled_palette_proposals(image)
    repeated = repeated_tiled_palette_shortlist(image, raw, maximum=max(maximum * 4, 192))
    companions = assemble_adjacent_tiled_palette_companions(repeated)
    shortlist = position_ranked_tiled_shortlist(
        (*repeated, *companions), image.shape[:2], panel_map, maximum=maximum,
    )
    shortlist = corroborate_tiled_number_families(image, shortlist, panel_map)
    matrix, names, rows = feature_matrix(image, shortlist)
    return shortlist, matrix, names, rows, len(raw), len(companions)


def label_candidate(bbox, references):
    area = max(1, int(bbox[2]) * int(bbox[3]))
    positive_matches = []
    for ref in references["positive"]:
        ref_area = max(1, ref["bbox"][2] * ref["bbox"][3])
        overlap = _intersection(bbox, ref["bbox"])
        coverage, purity = overlap / ref_area, overlap / area
        if coverage >= 0.70 and (purity >= 0.55 or area / ref_area <= 1.65):
            positive_matches.append((coverage, purity, ref))
    negative_matches = []
    for ref in references["negative"]:
        ref_area = max(1, ref["bbox"][2] * ref["bbox"][3])
        overlap = _intersection(bbox, ref["bbox"])
        coverage, purity = overlap / ref_area, overlap / area
        iou = overlap / max(1, area + ref_area - overlap)
        if purity >= 0.65 or iou >= 0.35:
            negative_matches.append((max(purity, iou), ref))
    if positive_matches and negative_matches:
        return "uncertain", "mixed-reviewed-regions"
    if positive_matches:
        best = max(positive_matches, key=lambda item: (item[0], item[1]))
        # Broader proposals containing a complete number plus panel content are
        # supervised as uncertain, not rewarded as clean Number instances.
        if best[1] < 0.55:
            return "uncertain", "number-plus-panel"
        return "Number", best[2].get("physical_copy") or "reviewed-complete-copy"
    if negative_matches:
        best = max(negative_matches, key=lambda item: item[0])
        return best[1]["semantic"], "reviewed-hard-negative"
    return None, None


def _fit(X, y, c_value):
    scaler = StandardScaler().fit(X)
    classifier = LogisticRegression(
        C=c_value, class_weight="balanced", max_iter=4000, random_state=722,
    ).fit(scaler.transform(X), y)
    return scaler, classifier


def _aligned_probabilities(classifier, values):
    raw = classifier.predict_proba(values)
    aligned = np.zeros((len(values), len(CLASSES)), dtype=np.float64)
    for source, name in enumerate(classifier.classes_):
        aligned[:, CLASSES.index(str(name))] = raw[:, source]
    return aligned


def grouped_oof(X, y, groups, c_value):
    output = np.zeros((len(y), len(CLASSES)), dtype=np.float64)
    splitter = GroupKFold(n_splits=min(5, len(set(groups))))
    for train, test in splitter.split(X, y, groups):
        scaler, classifier = _fit(X[train], y[train], c_value)
        output[test] = _aligned_probabilities(classifier, scaler.transform(X[test]))
    return output


def _fit_number_forest(X, y, *, max_depth, min_samples_leaf, estimators=160):
    classifier = RandomForestClassifier(
        n_estimators=estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=722,
        n_jobs=-1,
    ).fit(X, np.asarray(y) == "Number")
    return classifier


def grouped_oof_number_forest(X, y, groups, *, max_depth, min_samples_leaf):
    output = np.zeros(len(y), dtype=np.float64)
    splitter = GroupKFold(n_splits=min(5, len(set(groups))))
    for train, test in splitter.split(X, y, groups):
        classifier = _fit_number_forest(
            X[train], y[train], max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
        )
        number_index = list(classifier.classes_).index(True)
        output[test] = classifier.predict_proba(X[test])[:, number_index]
    return output


def _serialize_number_forest(classifier, feature_names):
    number_index = list(classifier.classes_).index(True)
    trees = []
    for estimator in classifier.estimators_:
        tree = estimator.tree_
        probabilities = []
        for value in tree.value[:, 0, :]:
            total = float(value.sum())
            probabilities.append(float(value[number_index] / total) if total else 0.0)
        trees.append({
            "feature": tree.feature.astype(int).tolist(),
            "threshold": tree.threshold.round(10).tolist(),
            "left": tree.children_left.astype(int).tolist(),
            "right": tree.children_right.astype(int).tolist(),
            "number_probability": np.round(probabilities, 10).tolist(),
        })
    return {
        "schema": "smart-tga-tiled-number-forest-v1",
        "feature_names": list(feature_names),
        "trees": trees,
        "ownership_authority": False,
    }


def _metrics(y, probabilities, threshold):
    number_index = CLASSES.index("Number")
    number_true = np.asarray(y) == "Number"
    number_accept = probabilities[:, number_index] >= threshold
    precision, recall, f1, _ = precision_recall_fscore_support(
        number_true, number_accept, average="binary", zero_division=0,
    )
    return {
        "number_average_precision": round(float(average_precision_score(number_true, probabilities[:, number_index])), 6),
        "number_precision": round(float(precision), 6),
        "number_recall": round(float(recall), 6),
        "number_f1": round(float(f1), 6),
        "accepted": int(number_accept.sum()),
    }


def _target_groups(payload):
    grouped = defaultdict(list)
    for row in payload["representative_labels"]:
        if row.get("semantic") == "Number" and row.get("physical_copy"):
            grouped[(row["paint"], row["physical_copy"])].append(row["bbox"])
    return {key: _union(boxes) for key, boxes in grouped.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-probe", type=Path, required=True)
    parser.add_argument("--holdout-probe", type=Path, required=True)
    parser.add_argument("--holdout-labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review", type=Path, action="append", default=[])
    parser.add_argument(
        "--panel-map", type=Path,
        default=Path("engine/spec_sculpt/models/smart_tga_dlm_panel_map_cycle660_v1.json"),
    )
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    review_paths = args.review or [Path(path) for path in DEFAULT_REVIEWS]
    references = load_review_references(review_paths)
    development_sources = load_probe_sources(args.development_probe)
    holdout_sources = load_probe_sources(args.holdout_probe)
    panel_map = json.loads(args.panel_map.read_text(encoding="utf-8"))

    examples, feature_names = [], None
    development_cache = {}
    for paint, source in development_sources.items():
        image = np.asarray(Image.open(source).convert("RGB"))
        candidates, matrix, names, rows, raw_count, companion_count = build_candidates(image, panel_map)
        feature_names = names if feature_names is None else feature_names
        if names != feature_names:
            raise RuntimeError("feature schema drift")
        development_cache[paint] = (candidates, matrix, rows)
        for index, candidate in enumerate(candidates):
            label, reason = label_candidate(candidate["proposal_bbox"], references[paint])
            if label is not None:
                examples.append({
                    "paint": paint,
                    "candidate_index": index,
                    "bbox": list(map(int, candidate["proposal_bbox"])),
                    "label": label,
                    "reason": reason,
                    "features": matrix[index],
                    "is_stress_control": paint in CONTROL_PAINTS and label != "Number",
                })

    if len({item["label"] for item in examples}) < 3:
        raise RuntimeError("review matching produced fewer than three semantic classes")
    X = np.vstack([item["features"] for item in examples])
    y = np.asarray([item["label"] for item in examples])
    groups = np.asarray([item["paint"] for item in examples])
    np.savez_compressed(
        args.output / "development_features.npz", X=X, y=y, groups=groups,
        feature_names=np.asarray(feature_names),
    )
    (args.output / "development_examples.json").write_text(json.dumps([{
        key: value for key, value in item.items() if key != "features"
    } for item in examples], indent=2) + "\n", encoding="utf-8")
    choices = []
    for c_value in (0.03, 0.1, 0.3, 1.0):
        probabilities = grouped_oof(X, y, groups, c_value)
        average_precision = average_precision_score(y == "Number", probabilities[:, CLASSES.index("Number")])
        choices.append((float(average_precision), -c_value, c_value, probabilities))
    _, _, c_value, oof = max(choices, key=lambda item: (item[0], item[1]))

    number_index = CLASSES.index("Number")
    forest_choices = []
    for max_depth, min_leaf in ((4, 3), (6, 2), (8, 2)):
        probabilities = grouped_oof_number_forest(
            X, y, groups, max_depth=max_depth, min_samples_leaf=min_leaf,
        )
        average_precision = average_precision_score(y == "Number", probabilities)
        forest_choices.append((float(average_precision), -max_depth, max_depth, min_leaf, probabilities))
    _, _, forest_depth, forest_min_leaf, oof_number = max(
        forest_choices, key=lambda item: (item[0], item[1]),
    )
    control_mask = np.asarray([item["is_stress_control"] for item in examples], dtype=bool)
    control_max = float(oof_number[control_mask].max()) if control_mask.any() else 0.0
    all_negative = y != "Number"
    negative_q99 = float(np.quantile(oof_number[all_negative], 0.99))
    threshold = min(0.98, max(0.50, control_max + 0.02, negative_q99 + 0.01))
    forest_probability_matrix = np.zeros_like(oof)
    forest_probability_matrix[:, number_index] = oof_number
    forest_probability_matrix[:, CLASSES.index("uncertain")] = 1.0 - oof_number
    oof_metrics = _metrics(y, forest_probability_matrix, threshold)
    oof_accept = oof_number >= threshold
    oof_metrics.update({
        "paint_disjoint_folds": min(5, len(set(groups))),
        "stress_control_negative_count": int(control_mask.sum()),
        "stress_control_wrong_accepts": int(np.count_nonzero(oof_accept & control_mask)),
        "confusion_labels": list(CLASSES),
        "semantic_linear_argmax_confusion": confusion_matrix(y, np.asarray(CLASSES)[oof.argmax(axis=1)], labels=CLASSES).tolist(),
        "linear_number_average_precision": round(float(average_precision_score(y == "Number", oof[:, number_index])), 6),
        "forest_depth": forest_depth,
        "forest_min_samples_leaf": forest_min_leaf,
    })

    scaler, classifier = _fit(X, y, c_value)
    number_forest = _fit_number_forest(
        X, y, max_depth=forest_depth, min_samples_leaf=forest_min_leaf,
    )
    coefficients = np.zeros((len(CLASSES), X.shape[1]), dtype=np.float64)
    intercept = np.full(len(CLASSES), -30.0, dtype=np.float64)
    for source, name in enumerate(classifier.classes_):
        destination = CLASSES.index(str(name))
        coefficients[destination] = classifier.coef_[source]
        intercept[destination] = classifier.intercept_[source]
    model = {
        "schema": "smart-tga-tiled-semantic-linear-v1",
        "cycle": 722,
        "feature_names": list(feature_names),
        "classes": list(CLASSES),
        "mean": scaler.mean_.round(10).tolist(),
        "scale": scaler.scale_.round(10).tolist(),
        "coefficients": coefficients.round(10).tolist(),
        "intercept": intercept.round(10).tolist(),
        "number_acceptance_threshold": round(threshold, 8),
        "abstain_probability": round(max(0.55, threshold), 8),
        "abstain_margin": 0.08,
        "ownership_authority": False,
        "casts_votes": False,
        "training": {
            "paint_count": len(set(groups)),
            "example_count": len(examples),
            "class_counts": dict(Counter(y)),
            "selected_c": c_value,
            "oof": oof_metrics,
        },
        "number_forest": _serialize_number_forest(number_forest, feature_names),
    }
    (args.output / "model.json").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")

    holdout_payload = json.loads(args.holdout_labels.read_text(encoding="utf-8"))
    targets = _target_groups(holdout_payload)
    holdout_scores = []
    target_results = []
    accepted_total = 0
    accepted_target_candidates = 0
    for paint, source in holdout_sources.items():
        image = np.asarray(Image.open(source).convert("RGB"))
        candidates, matrix, names, rows, raw_count, companion_count = build_candidates(image, panel_map)
        probabilities = _aligned_probabilities(classifier, scaler.transform(matrix))
        forest_number_index = list(number_forest.classes_).index(True)
        number_scores = number_forest.predict_proba(matrix)[:, forest_number_index]
        accepted = number_scores >= threshold
        accepted_total += int(accepted.sum())
        paint_targets = {key: bbox for key, bbox in targets.items() if key[0] == paint}
        candidate_matches = defaultdict(list)
        for index, candidate in enumerate(candidates):
            bbox = candidate["proposal_bbox"]
            area = max(1, bbox[2] * bbox[3])
            for key, target in paint_targets.items():
                target_area = max(1, target[2] * target[3])
                overlap = _intersection(bbox, target)
                coverage, purity = overlap / target_area, overlap / area
                if coverage >= 0.70 and (purity >= 0.45 or area / target_area <= 2.2):
                    candidate_matches[key].append(index)
        matched_accepted = set()
        for key, target in paint_targets.items():
            indices = candidate_matches.get(key, [])
            accepted_indices = [index for index in indices if accepted[index]]
            matched_accepted.update(accepted_indices)
            order = np.argsort(-number_scores)
            ranks = {int(index): rank + 1 for rank, index in enumerate(order)}
            target_results.append({
                "paint": paint,
                "physical_copy": key[1],
                "target_bbox": target,
                "candidate_present": bool(indices),
                "accepted": bool(accepted_indices),
                "best_number_score": round(float(max((number_scores[index] for index in indices), default=0.0)), 7),
                "best_semantic_rank": min((ranks[index] for index in indices), default=None),
                "accepted_candidate_indices": accepted_indices,
            })
        accepted_target_candidates += len(matched_accepted)
        holdout_scores.append({
            "paint": paint,
            "candidate_count": len(candidates),
            "accepted_count": int(accepted.sum()),
            "accepted_indices": np.flatnonzero(accepted).tolist(),
            "number_scores": np.round(number_scores, 7).tolist(),
        })

    complete_recall_count = sum(item["accepted"] for item in target_results)
    conservative_precision = accepted_target_candidates / max(1, accepted_total)
    gate_passed = (
        complete_recall_count >= 14
        and oof_metrics["stress_control_wrong_accepts"] == 0
        and conservative_precision >= 0.80
    )
    ledger = {
        "schema": "smart-tga-cycle722-tiled-semantic-acceptance-v1",
        "cycle": 722,
        "baseline": {
            "safe_final_correct": 1,
            "safe_final_recall": 0.0625,
            "complete_candidate_recall": 0.9375,
        },
        "development": {
            "reviewed_paints": len(set(groups)),
            "labeled_candidate_examples": len(examples),
            "class_counts": dict(Counter(y)),
            "selected_regularization_c": c_value,
            "number_threshold": round(threshold, 7),
            "paint_disjoint_oof": oof_metrics,
        },
        "after_locked_holdout": {
            "visible_primary_number_copies": len(target_results),
            "accepted_complete_copies": complete_recall_count,
            "accepted_complete_copy_recall": round(complete_recall_count / max(1, len(target_results)), 6),
            "accepted_candidate_count": accepted_total,
            "accepted_candidates_matching_complete_targets": accepted_target_candidates,
            "conservative_clean_number_precision": round(conservative_precision, 6),
            "top_k_burden": max((item["best_semantic_rank"] or 0 for item in target_results), default=0),
        },
        "shadow_gate": {
            "required_complete_recall": "14/16",
            "required_stress_control_wrong_accepts": 0,
            "required_conservative_precision": 0.80,
            "passed": gate_passed,
            "integrated": False,
            "reason": "zero-authority research scorer; integration requires every gate",
        },
        "safety": {
            "casts_votes": False,
            "ownership_authority": False,
            "output_applied": False,
            "apply_locked": True,
            "filename_or_car_features": False,
            "reviewed_bboxes_runtime_authority": False,
        },
        "target_results": target_results,
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "holdout_scores.json").write_text(json.dumps(holdout_scores, indent=2) + "\n", encoding="utf-8")
    (args.output / "acceptance_ledger.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "examples": len(examples),
        "classes": dict(Counter(y)),
        "oof": oof_metrics,
        "holdout": ledger["after_locked_holdout"],
        "gate_passed": gate_passed,
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
