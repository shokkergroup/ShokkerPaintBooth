"""Evaluate the frozen CLIPSeg hierarchy once on the locked six-paint DLM holdout.

The six paints and their reviewed physical-copy targets predate the Cycle729
hierarchy.  Candidate identity and reviewed target boxes are metrics only.
Inference uses frozen pixels/prompt evidence, never filename, car, or bbox.
No holdout value selects a model, threshold, or acceptance rule.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import time

import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
import torch

try:
    from scripts.smart_tga_clip_d4_benchmark import (
        _build_embeddings,
        _load_local_clipseg_vision,
    )
    from scripts.smart_tga_clipseg_zero_shot_probe import (
        _category_scores,
        _prompt_prototypes,
    )
    from scripts.smart_tga_clipseg_hierarchical_calibrator import (
        INNER_FOLDS,
        OUTER_FOLDS,
        _feature_matrices,
        _fit_stage_models,
        _load_evidence,
        _lower_quartile_ensemble,
        _predict_stage_models,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_clip_d4_benchmark import (  # type: ignore
        _build_embeddings, _load_local_clipseg_vision,
    )
    from scripts.smart_tga_clipseg_zero_shot_probe import (  # type: ignore
        _category_scores, _prompt_prototypes,
    )
    from scripts.smart_tga_clipseg_hierarchical_calibrator import (  # type: ignore
        INNER_FOLDS, OUTER_FOLDS, _feature_matrices, _fit_stage_models,
        _load_evidence, _lower_quartile_ensemble, _predict_stage_models,
    )


def _write_candidate_trace(bank: dict, output: Path) -> list[dict]:
    labels = []
    offset = 0
    for record in bank["records"]:
        for candidate_index, candidate in enumerate(record["candidates"]):
            labels.append({
                "review_code": f"H{offset:04d}",
                "paint": record["paint"],
                "candidate_index": candidate_index,
                "proposal_id": candidate["proposal_id"],
            })
            offset += 1
    payload = {
        "schema": "smart-tga-neutral-candidate-trace-v1",
        "review_labels": False,
        "candidate_count": len(labels),
        "labels": labels,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return labels


def _intersection(first: list[int], second: list[int]) -> int:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[0] + first[2], second[0] + second[2])
    bottom = min(first[1] + first[3], second[1] + second[3])
    return max(0, right - left) * max(0, bottom - top)


def _candidate_matches_target(candidate: list[int], target: list[int]) -> bool:
    area = max(1, candidate[2] * candidate[3])
    target_area = max(1, target[2] * target[3])
    overlap = _intersection(candidate, target)
    coverage, purity = overlap / target_area, overlap / area
    return bool(coverage >= 0.70 and (purity >= 0.45 or area / target_area <= 2.2))


def _target_map(target_ledger: dict) -> dict[str, dict[str, list[int]]]:
    result: dict[str, dict[str, list[int]]] = defaultdict(dict)
    for row in target_ledger["target_results"]:
        result[row["paint"]][row["physical_copy"]] = row["target_bbox_review_metric_only"]
    return dict(result)


def _baseline_score_map(payload: list[dict]) -> dict[str, np.ndarray]:
    return {row["paint"]: np.asarray(row["scores"], dtype=np.float64) for row in payload}


def _score_locked_holdout(
    development: dict,
    category: np.ndarray,
    fold_thresholds: list[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    semantic_x, complete_x = _feature_matrices(category)
    indices = np.arange(len(development["groups"]), dtype=np.int64)
    outer_scores, outer_accepts = [], []
    outer = GroupKFold(n_splits=OUTER_FOLDS)
    for fold, (train, _) in enumerate(outer.split(indices, groups=development["groups"])):
        member_scores = []
        inner = GroupKFold(n_splits=INNER_FOLDS)
        for inner_train_offset, _ in inner.split(train, groups=development["groups"][train]):
            inner_train = train[inner_train_offset]
            semantic, complete = _predict_stage_models(
                _fit_stage_models(development, inner_train), semantic_x, complete_x,
            )
            member_scores.append(np.minimum(semantic, complete))
        committee_score = _lower_quartile_ensemble(member_scores)
        outer_scores.append(committee_score)
        outer_accepts.append(committee_score >= fold_thresholds[fold])
    stacked_scores = np.stack(outer_scores)
    stacked_accepts = np.stack(outer_accepts)
    return (
        _lower_quartile_ensemble(list(stacked_scores)),
        np.all(stacked_accepts, axis=0),
        np.sum(stacked_accepts, axis=0),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-examples", type=Path, required=True)
    parser.add_argument("--development-controls-ledger", type=Path, required=True)
    parser.add_argument("--development-calibrator-ledger", type=Path, required=True)
    parser.add_argument("--holdout-bank", type=Path, required=True)
    parser.add_argument("--holdout-target-ledger", type=Path, required=True)
    parser.add_argument("--baseline-holdout-scores", type=Path, required=True)
    parser.add_argument("--clipseg-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-candidates", type=int, default=2)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cycle", type=int, default=729)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(max(1, args.threads))
    development = _load_evidence(
        args.development_examples, args.development_controls_ledger,
    )
    dev_ledger = json.loads(args.development_calibrator_ledger.read_text(encoding="utf-8"))
    if not dev_ledger["gates"]["development_hierarchical_gate_passed"]:
        raise RuntimeError("development hierarchy did not authorize holdout opening")
    bank = json.loads(args.holdout_bank.read_text(encoding="utf-8"))
    trace_path = args.output / "candidate_trace.json"
    labels = _write_candidate_trace(bank, trace_path)
    embedding_path = args.output / "clipseg_b16_d4_embeddings.npz"
    if embedding_path.exists():
        cache = np.load(embedding_path, allow_pickle=False)
        appearance = cache["appearance"].astype(np.float32)
        embedding_cache = {"cached": True, "candidate_count": len(appearance)}
    else:
        embedding_cache = _build_embeddings(
            args.holdout_bank, trace_path, embedding_path,
            batch_candidates=args.batch_candidates,
            model_name="ViT-B-16", pretrained="local-clipseg", device=args.device,
            clipseg_checkpoint=args.clipseg_checkpoint,
            include_silhouette=False,
        )
        cache = np.load(embedding_path, allow_pickle=False)
        appearance = cache["appearance"].astype(np.float32)
    if len(appearance) != len(labels):
        raise RuntimeError("holdout embedding trace drift")
    prompt_model = _load_local_clipseg_vision(args.clipseg_checkpoint, "cpu")
    category_dict = _category_scores(appearance, _prompt_prototypes(prompt_model))
    category = np.column_stack([
        category_dict[name] for name in (
            "complete_number", "number_fragment", "sponsor", "paint",
        )
    ])
    thresholds = [
        float(row["robust_acceptance_threshold"]) for row in dev_ledger["folds"]
    ]
    score, accepted, accept_votes = _score_locked_holdout(
        development, category, thresholds,
    )
    targets = _target_map(json.loads(args.holdout_target_ledger.read_text(encoding="utf-8")))
    baseline = _baseline_score_map(json.loads(
        args.baseline_holdout_scores.read_text(encoding="utf-8")
    ))
    truth, baseline_scores = [], []
    offset = 0
    paint_results, target_results, candidate_examples = [], [], []
    accepted_target_candidates = set()
    for record in bank["records"]:
        paint = record["paint"]
        paint_truth = []
        candidate_target_names = []
        for candidate in record["candidates"]:
            matches = [
                physical_copy for physical_copy, target in targets[paint].items()
                if _candidate_matches_target(candidate["bbox"], target)
            ]
            paint_truth.append(bool(matches))
            candidate_target_names.append(matches)
        paint_truth = np.asarray(paint_truth, dtype=bool)
        count = len(paint_truth)
        paint_score = score[offset:offset + count]
        paint_accepted = accepted[offset:offset + count]
        for index, matches in enumerate(candidate_target_names):
            if paint_accepted[index] and matches:
                accepted_target_candidates.add((paint, index))
        for physical_copy, target in targets[paint].items():
            matches = [i for i, names in enumerate(candidate_target_names) if physical_copy in names]
            accepted_indices = [i for i in matches if paint_accepted[i]]
            target_results.append({
                "paint": paint,
                "physical_copy": physical_copy,
                "target_bbox_review_metric_only": target,
                "candidate_present": bool(matches),
                "accepted": bool(accepted_indices),
                "best_score": round(float(max((paint_score[i] for i in matches), default=0.0)), 8),
                "accepted_candidate_indices": accepted_indices,
            })
        truth.extend(paint_truth.tolist())
        baseline_scores.extend(baseline[paint].tolist())
        for index, candidate in enumerate(record["candidates"]):
            global_index = offset + index
            candidate_examples.append({
                "paint": paint,
                "candidate_index": index,
                "proposal_id": candidate["proposal_id"],
                "bbox_review_metric_only": candidate["bbox"],
                "complete_target_match": bool(paint_truth[index]),
                "physical_copy_matches": candidate_target_names[index],
                "hierarchical_score": round(float(paint_score[index]), 8),
                "hierarchical_accepted": bool(paint_accepted[index]),
                "outer_committee_accept_votes": int(accept_votes[global_index]),
                "cycle723_baseline_score": round(float(baseline[paint][index]), 8),
                "category_scores": {
                    name: round(float(category[global_index, category_index]), 8)
                    for category_index, name in enumerate((
                        "complete_number", "number_fragment", "sponsor", "paint",
                    ))
                },
                "ownership_authority": False,
            })
        paint_results.append({
            "paint": paint,
            "candidate_count": count,
            "complete_target_candidate_count": int(np.count_nonzero(paint_truth)),
            "cycle723_candidate_average_precision": round(float(
                average_precision_score(paint_truth, baseline[paint])
            ), 6),
            "hierarchical_candidate_average_precision": round(float(
                average_precision_score(paint_truth, paint_score)
            ), 6),
            "accepted_count": int(np.count_nonzero(paint_accepted)),
            "accepted_indices": np.flatnonzero(paint_accepted).tolist(),
            "scores": np.round(paint_score, 8).tolist(),
            "outer_committee_accept_votes": accept_votes[offset:offset + count].tolist(),
        })
        offset += count
    truth = np.asarray(truth, dtype=bool)
    baseline_scores = np.asarray(baseline_scores, dtype=np.float64)
    baseline_ap = float(average_precision_score(truth, baseline_scores))
    after_ap = float(average_precision_score(truth, score))
    accepted_count = int(np.count_nonzero(accepted))
    accepted_copies = int(sum(row["accepted"] for row in target_results))
    precision = len(accepted_target_candidates) / max(1, accepted_count)
    gate = bool(
        after_ap > baseline_ap
        and accepted_copies >= 5
        and precision >= 0.80
        and accepted_count > 0
    )
    (args.output / "holdout_scores.json").write_text(
        json.dumps(paint_results, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "holdout_examples.json").write_text(
        json.dumps(candidate_examples, indent=2) + "\n", encoding="utf-8",
    )
    ledger = {
        "schema": "smart-tga-clipseg-hierarchical-locked-holdout-v1",
        "cycle": args.cycle,
        "baseline_cycle723_same_candidates": {
            "candidate_average_precision": round(baseline_ap, 6),
            "accepted_complete_copies": 5,
            "visible_primary_number_copies": 16,
            "accepted_candidate_count": 16,
            "conservative_precision": 0.75,
        },
        "after_locked_six_paint_holdout": {
            "candidate_count": len(truth),
            "complete_target_candidate_count": int(np.count_nonzero(truth)),
            "candidate_average_precision": round(after_ap, 6),
            "accepted_complete_copies": accepted_copies,
            "visible_primary_number_copies": len(target_results),
            "accepted_candidate_count": accepted_count,
            "accepted_candidates_matching_complete_targets": len(accepted_target_candidates),
            "conservative_precision": round(precision, 6),
        },
        "gates": {
            "locked_holdout_gate_passed": gate,
            "requires_candidate_ap_greater_than_cycle723": round(baseline_ap, 6),
            "requires_accepted_complete_copies_at_least": 5,
            "requires_conservative_precision_at_least": 0.80,
            "runtime_integrated": False,
            "shadow_authority": False,
        },
        "measured_blocker": {
            "finding": (
                "Absolute CLIPSeg prompt probabilities do not transfer from the "
                "review-selected development candidates to the broad locked tiled pool."
            ),
            "next_implementation": (
                "Train source-content-disjoint within-paint ordinal family ranking: "
                "require an independent Number anchor, normalize candidate evidence "
                "inside each paint/block family, use D4 silhouette similarity for copy "
                "assembly, and retain CLIP semantics only as corroboration."
            ),
            "locked_holdout_is_consumed_and_forbidden_for_tuning": True,
        },
        "targets": sorted(targets),
        "development_hard_negative_controls": development["controls"],
        "target_results": target_results,
        "embedding_cache": embedding_cache,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "holdout_opened_once_after_development_gate": True,
            "holdout_used_for_model_or_threshold_selection": False,
            "acceptance_requires_all_outer_committees": True,
            "reviewed_bboxes_are_metrics_only": True,
            "casts_votes": False,
            "ownership_authority": False,
            "apply_locked": True,
            "filename_or_car_features": False,
            "absolute_bbox_inference_feature": False,
            "ocr_changed": False,
            "exact_reconstruction_affected": False,
        },
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": ledger["baseline_cycle723_same_candidates"],
        "after": ledger["after_locked_six_paint_holdout"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
