"""Train and freeze an exact-mask D4 number-family ranker.

All semantic supervision attaches to immutable candidate IDs.  Paint identity,
filenames, and reviewed bboxes are excluded from model features.  Cross-panel
relationships are corroborative evidence only; this offline scorer has zero
ownership authority and cannot alter Smart TGA output.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from engine.spec_sculpt.tiled_visual_embeddings import d4_orbit_similarity
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.tiled_visual_embeddings import d4_orbit_similarity  # type: ignore


CONTROL_PAINTS = {
    "dirtlatemodel 350/car_num_1006305.tga",
    "dirtlatemodel 350/car_num_1007631.tga",
    "dirtlatemodel 358/car_num_1008515.tga",
    "dirtlatemodel 358/car_num_1328151.tga",
    "dirtlatemodel 358/car_num_247671.tga",
}

FEATURE_NAMES = (
    "cross_panel_similarity_max",
    "cross_panel_similarity_top3_mean",
    "cross_panel_similarity_top8_mean",
    "cross_panel_peer_count_0_65",
    "cross_panel_peer_count_0_75",
    "cross_panel_peer_count_0_82",
    "cross_panel_peer_count_0_90",
    "distinct_block_similarity_max",
    "distinct_block_similarity_top3_mean",
    "distinct_block_count_0_75",
    "distinct_block_count_0_82",
    "distinct_block_count_0_90",
    "proposal_cross_block_d4_similarity",
    "template_number_block_fraction",
    "component_count_log1p",
    "support_bbox_area_log1p",
    "support_bbox_aspect_log",
)


def _load_bundle(bank_path: Path, embeddings_path: Path):
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    manifest = json.loads(embeddings_path.read_text(encoding="utf-8"))
    embedding_records = {row["paint"]: row for row in manifest["records"]}
    bundle = {}
    for row in bank["records"]:
        paint = row["paint"]
        with np.load(embedding_records[paint]["embedding_bank"], allow_pickle=False) as values:
            proposal_ids = values["proposal_ids"].tolist()
            expected = [candidate["proposal_id"] for candidate in row["candidates"]]
            if proposal_ids != expected:
                raise RuntimeError(f"candidate ID drift for {paint}")
            if "d4_embeddings" not in values:
                raise RuntimeError(f"persisted D4 views missing for {paint}")
            bundle[paint] = {
                "candidates": row["candidates"],
                "embeddings": values["embeddings"].astype(np.float32),
                "views": values["d4_embeddings"].astype(np.float32),
            }
    return bundle


def _family_features(record, representation: str):
    candidates = record["candidates"]
    if representation == "d4_orbit":
        similarities = d4_orbit_similarity(record["views"]).copy()
    elif representation == "averaged":
        embeddings = record["embeddings"]
        similarities = embeddings @ embeddings.T
    else:
        raise ValueError(representation)
    np.fill_diagonal(similarities, -1.0)
    rows = []
    for index, candidate in enumerate(candidates):
        block = candidate["dominant_number_block"]
        peers, blocks = [], {}
        for peer_index, peer in enumerate(candidates):
            if peer_index == index or peer["dominant_number_block"] == block:
                continue
            similarity = float(similarities[index, peer_index])
            peers.append(similarity)
            peer_block = peer["dominant_number_block"]
            blocks[peer_block] = max(blocks.get(peer_block, -1.0), similarity)
        peers.sort(reverse=True)
        block_scores = sorted(blocks.values(), reverse=True)
        _, _, width, height = map(int, candidate["bbox"])
        rows.append([
            max(peers, default=0.0),
            float(np.mean(peers[:3])) if peers else 0.0,
            float(np.mean(peers[:8])) if peers else 0.0,
            sum(value >= 0.65 for value in peers),
            sum(value >= 0.75 for value in peers),
            sum(value >= 0.82 for value in peers),
            sum(value >= 0.90 for value in peers),
            max(block_scores, default=0.0),
            float(np.mean(block_scores[:3])) if block_scores else 0.0,
            sum(value >= 0.75 for value in block_scores),
            sum(value >= 0.82 for value in block_scores),
            sum(value >= 0.90 for value in block_scores),
            float(candidate["cross_block_best_d4_similarity"]),
            float(candidate["number_block_fraction"]),
            float(np.log1p(candidate["component_count"])),
            float(np.log1p(width * height)),
            float(np.log((width + 1.0) / (height + 1.0))),
        ])
    return np.asarray(rows, dtype=np.float64)


def _classifier(c_value: float):
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=c_value, class_weight="balanced", solver="liblinear",
            max_iter=4000, random_state=723,
        ),
    )


def _grouped_oof(matrix, labels, groups, c_value):
    probabilities = np.zeros(len(labels), dtype=np.float64)
    splitter = GroupKFold(n_splits=min(5, len(set(groups))))
    for train, test in splitter.split(matrix, labels, groups):
        model = _classifier(c_value)
        model.fit(matrix[train], labels[train])
        probabilities[test] = model.predict_proba(matrix[test])[:, 1]
    return probabilities


def _select_threshold(labels, probabilities, stress_controls):
    choices = []
    for threshold in np.unique(probabilities):
        accepted = probabilities >= threshold
        if np.any(accepted & stress_controls):
            continue
        count = int(accepted.sum())
        precision = float(labels[accepted].mean()) if count else 1.0
        if precision < 0.80:
            continue
        true_positive = int(np.count_nonzero(accepted & labels))
        false_positive = int(np.count_nonzero(accepted & ~labels))
        choices.append((true_positive, precision, -false_positive, float(threshold)))
    if not choices:
        return float(np.nextafter(probabilities.max(), np.inf))
    return max(choices)[3]


def _intersection(first, second):
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[0] + first[2], second[0] + second[2])
    bottom = min(first[1] + first[3], second[1] + second[3])
    return max(0, right - left) * max(0, bottom - top)


def _union(boxes):
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = max(box[0] + box[2] for box in boxes)
    bottom = max(box[1] + box[3] for box in boxes)
    return [left, top, right - left, bottom - top]


def _targets(payload):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in payload["representative_labels"]:
        if row.get("semantic") == "Number" and row.get("physical_copy"):
            grouped[row["paint"]][row["physical_copy"]].append(row["bbox"])
    return {
        paint: {physical_copy: _union(boxes) for physical_copy, boxes in copies.items()}
        for paint, copies in grouped.items()
    }


def _pair_probe(bundle, direct_labels):
    by_paint = defaultdict(dict)
    for row in direct_labels:
        by_paint[row["paint"]][int(row["candidate_index"])] = row
    features, labels, groups = [], [], []
    for paint, paint_labels in by_paint.items():
        record = bundle[paint]
        orbit = d4_orbit_similarity(record["views"])
        averaged = record["embeddings"] @ record["embeddings"].T
        indices = sorted(paint_labels)
        for offset, first in enumerate(indices):
            first_label = paint_labels[first]
            if first_label["semantic"] == "uncertain":
                continue
            first_number = first_label["semantic"] == "Number"
            for second in indices[offset + 1:]:
                second_label = paint_labels[second]
                second_number = second_label["semantic"] == "Number"
                if second_label["semantic"] == "uncertain" or not (first_number or second_number):
                    continue
                first_candidate = record["candidates"][first]
                second_candidate = record["candidates"][second]
                if first_candidate["dominant_number_block"] == second_candidate["dominant_number_block"]:
                    continue
                features.append([
                    averaged[first, second], orbit[first, second],
                    float(first_candidate["palette_role"] == second_candidate["palette_role"]),
                ])
                labels.append(first_number and second_number)
                groups.append(paint)
    matrix = np.asarray(features, dtype=np.float64)
    y = np.asarray(labels, dtype=bool)
    group_values = np.asarray(groups)
    prevalence = float(y.mean())
    choices = []
    for c_value in (0.01, 0.1, 1.0, 10.0):
        probabilities = _grouped_oof(matrix, y, group_values, c_value)
        choices.append((float(average_precision_score(y, probabilities)), -c_value, c_value))
    average_precision, _, selected_c = max(choices)
    return {
        "pair_count": len(y),
        "positive_pair_count": int(y.sum()),
        "paint_count": len(set(groups)),
        "positive_prevalence": round(prevalence, 6),
        "best_paint_disjoint_average_precision": round(average_precision, 6),
        "selected_c": selected_c,
        "beats_prevalence_baseline": bool(average_precision > prevalence),
        "used_for_acceptance": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-bank", type=Path, required=True)
    parser.add_argument("--development-embeddings", type=Path, required=True)
    parser.add_argument("--direct-labels", type=Path, required=True)
    parser.add_argument("--holdout-bank", type=Path, required=True)
    parser.add_argument("--holdout-embeddings", type=Path, required=True)
    parser.add_argument("--holdout-labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    development = _load_bundle(args.development_bank, args.development_embeddings)
    holdout = _load_bundle(args.holdout_bank, args.holdout_embeddings)
    direct_payload = json.loads(args.direct_labels.read_text(encoding="utf-8"))
    direct_labels = direct_payload["labels"]

    feature_cache = {
        representation: {
            paint: _family_features(record, representation)
            for paint, record in development.items()
        }
        for representation in ("averaged", "d4_orbit")
    }
    y, groups, stress, indices = [], [], [], []
    for row in direct_labels:
        complete_number = row["semantic"] == "Number" and row.get("complete_copy") is True
        y.append(complete_number)
        groups.append(row["paint"])
        stress.append(row["paint"] in CONTROL_PAINTS and not complete_number)
        indices.append((row["paint"], int(row["candidate_index"])))
    y = np.asarray(y, dtype=bool)
    groups = np.asarray(groups)
    stress = np.asarray(stress, dtype=bool)

    model_choices = []
    for representation, matrices in feature_cache.items():
        matrix = np.vstack([matrices[paint][index] for paint, index in indices])
        for c_value in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0):
            probabilities = _grouped_oof(matrix, y, groups, c_value)
            average_precision = float(average_precision_score(y, probabilities))
            model_choices.append((average_precision, representation == "d4_orbit", -c_value,
                                  representation, c_value, matrix, probabilities))
    representation_best_ap = {
        name: max(choice[0] for choice in model_choices if choice[3] == name)
        for name in feature_cache
    }
    average_precision, _, _, representation, c_value, matrix, oof = max(model_choices)
    threshold = _select_threshold(y, oof, stress)
    oof_accept = oof >= threshold
    oof_precision = float(y[oof_accept].mean()) if oof_accept.any() else 1.0
    oof_recall = float(np.count_nonzero(oof_accept & y) / max(1, y.sum()))
    pair_probe = _pair_probe(development, direct_labels)

    model = _classifier(c_value)
    model.fit(matrix, y)
    scaler = model.named_steps["standardscaler"]
    classifier = model.named_steps["logisticregression"]
    model_payload = {
        "schema": "smart-tga-d4-family-linear-v1",
        "cycle": 723,
        "representation": representation,
        "feature_names": list(FEATURE_NAMES),
        "mean": scaler.mean_.round(10).tolist(),
        "scale": scaler.scale_.round(10).tolist(),
        "coefficients": classifier.coef_[0].round(10).tolist(),
        "intercept": round(float(classifier.intercept_[0]), 10),
        "acceptance_threshold": round(threshold, 10),
        "selected_c": c_value,
        "ownership_authority": False,
        "casts_votes": False,
        "filename_or_car_features": False,
        "reviewed_bbox_features": False,
    }
    (args.output / "model.json").write_text(json.dumps(model_payload, indent=2) + "\n", encoding="utf-8")

    target_map = _targets(json.loads(args.holdout_labels.read_text(encoding="utf-8")))
    target_results, paint_scores = [], []
    accepted_total, accepted_target_candidates = 0, 0
    for paint, record in holdout.items():
        holdout_matrix = _family_features(record, representation)
        scores = model.predict_proba(holdout_matrix)[:, 1]
        accepted = scores >= threshold
        accepted_total += int(accepted.sum())
        candidate_matches = defaultdict(list)
        for candidate_index, candidate in enumerate(record["candidates"]):
            bbox = candidate["bbox"]
            area = max(1, bbox[2] * bbox[3])
            for physical_copy, target in target_map[paint].items():
                target_area = max(1, target[2] * target[3])
                overlap = _intersection(bbox, target)
                coverage, purity = overlap / target_area, overlap / area
                if coverage >= 0.70 and (purity >= 0.45 or area / target_area <= 2.2):
                    candidate_matches[physical_copy].append(candidate_index)
        matched_accepted = set()
        order = np.argsort(-scores)
        ranks = {int(index): rank + 1 for rank, index in enumerate(order)}
        for physical_copy, target in target_map[paint].items():
            candidates = candidate_matches.get(physical_copy, [])
            accepted_indices = [index for index in candidates if accepted[index]]
            matched_accepted.update(accepted_indices)
            target_results.append({
                "paint": paint,
                "physical_copy": physical_copy,
                "target_bbox_review_metric_only": target,
                "candidate_present": bool(candidates),
                "accepted": bool(accepted_indices),
                "best_score": round(float(max((scores[index] for index in candidates), default=0.0)), 7),
                "best_rank": min((ranks[index] for index in candidates), default=None),
                "accepted_candidate_indices": accepted_indices,
            })
        accepted_target_candidates += len(matched_accepted)
        paint_scores.append({
            "paint": paint,
            "accepted_count": int(accepted.sum()),
            "accepted_indices": np.flatnonzero(accepted).tolist(),
            "scores": np.round(scores, 7).tolist(),
        })

    accepted_copies = sum(row["accepted"] for row in target_results)
    precision = accepted_target_candidates / max(1, accepted_total)
    stress_wrong = int(np.count_nonzero(oof_accept & stress))
    gate_passed = accepted_copies >= 14 and precision >= 0.80 and stress_wrong == 0
    development_examples = []
    for source, row in enumerate(direct_labels):
        development_examples.append({
            "review_code": row["review_code"],
            "paint": row["paint"],
            "candidate_index": row["candidate_index"],
            "complete_number": bool(y[source]),
            "oof_score": round(float(oof[source]), 7),
            "oof_accepted": bool(oof_accept[source]),
            "stress_control_negative": bool(stress[source]),
        })
    (args.output / "development_examples.json").write_text(
        json.dumps(development_examples, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "holdout_scores.json").write_text(
        json.dumps(paint_scores, indent=2) + "\n", encoding="utf-8",
    )
    ledger = {
        "schema": "smart-tga-cycle723-d4-family-acceptance-v1",
        "cycle": 723,
        "baseline_cycle722_best": {
            "accepted_complete_copies": 3,
            "visible_primary_number_copies": 16,
            "accepted_candidate_count": 8,
            "conservative_precision": 0.875,
        },
        "development": {
            "reviewed_paints": len(set(groups)),
            "direct_exact_candidate_labels": len(y),
            "complete_number_count": int(y.sum()),
            "other_count": int((~y).sum()),
            "representation": representation,
            "selected_c": c_value,
            "paint_disjoint_folds": min(5, len(set(groups))),
            "average_precision": round(average_precision, 6),
            "representation_best_average_precision": {
                name: round(value, 6) for name, value in representation_best_ap.items()
            },
            "threshold": round(threshold, 8),
            "accepted_count": int(oof_accept.sum()),
            "accepted_true_positive_count": int(np.count_nonzero(oof_accept & y)),
            "precision": round(oof_precision, 6),
            "recall": round(oof_recall, 6),
            "five_control_negative_count": int(stress.sum()),
            "five_control_wrong_accepts": stress_wrong,
            "pairwise_family_probe": pair_probe,
        },
        "after_locked_holdout": {
            "visible_primary_number_copies": len(target_results),
            "accepted_complete_copies": accepted_copies,
            "accepted_complete_copy_recall": round(accepted_copies / max(1, len(target_results)), 6),
            "accepted_candidate_count": accepted_total,
            "accepted_candidates_matching_complete_targets": accepted_target_candidates,
            "conservative_precision": round(precision, 6),
            "top_k_burden": max((row["best_rank"] or 0 for row in target_results), default=0),
        },
        "shadow_gate": {
            "required_complete_recall": "14/16",
            "required_five_control_wrong_accepts": 0,
            "required_conservative_precision": 0.80,
            "passed": gate_passed,
            "integrated": False,
        },
        "measured_blocker": None if gate_passed else {
            "finding": "generic ImageNet D4 embeddings do not separate race-number family pairs paint-disjoint",
            "pair_average_precision": pair_probe["best_paint_disjoint_average_precision"],
            "pair_prevalence_baseline": pair_probe["positive_prevalence"],
            "next_implementation": "train a masked-glyph representation with supervised contrastive family/copy loss and paint-disjoint validation; retain this exact candidate bank and labels",
        },
        "safety": {
            "casts_votes": False,
            "ownership_authority": False,
            "output_applied": False,
            "apply_locked": True,
            "exact_reconstruction_affected": False,
            "filename_or_car_features": False,
            "reviewed_bboxes_runtime_authority": False,
        },
        "target_results": target_results,
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "development": ledger["development"],
        "holdout": ledger["after_locked_holdout"],
        "gate_passed": gate_passed,
        "measured_blocker": ledger["measured_blocker"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
