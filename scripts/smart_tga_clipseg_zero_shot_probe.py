"""Probe universal zero-shot Smart TGA semantics with local frozen CLIPSeg.

The prompt vocabulary describes racing concepts, never a filename, car, paint,
or bounding box.  Scores are review evidence only and retain zero ownership
authority.  Thresholds and score-mode selection are source-content-disjoint.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np
import open_clip
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
import torch
from torch.nn import functional as F

try:
    from scripts.smart_tga_clip_d4_benchmark import _load_local_clipseg_vision
    from scripts.smart_tga_clip_anchor_extension_train import _load_intrinsics
    from scripts.smart_tga_local_masked_patch_train import CONTROL_PAINTS, _load_data
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_clip_d4_benchmark import _load_local_clipseg_vision  # type: ignore
    from scripts.smart_tga_clip_anchor_extension_train import _load_intrinsics  # type: ignore
    from scripts.smart_tga_local_masked_patch_train import CONTROL_PAINTS, _load_data  # type: ignore


PROMPTS = {
    "complete_number": (
        "a complete race car number decal",
        "a full racing number made of digits",
        "a complete car door number",
        "a complete roof number on a race car",
    ),
    "number_fragment": (
        "a fragment of a race car number",
        "part of a number digit",
        "an incomplete racing number decal",
        "a cropped piece of a number",
    ),
    "sponsor": (
        "a sponsor logo on a race car",
        "advertising text and a company logo",
        "a motorsports sponsor decal",
        "a brand logo decal",
    ),
    "paint": (
        "painted racing stripes",
        "abstract race car livery graphics",
        "a colored paint swoosh",
        "decorative car paint graphics",
    ),
}

SCORE_MODES = (
    "complete_raw",
    "complete_minus_fragment",
    "complete_minus_nonnumber",
    "complete_minus_all",
)


def _prompt_prototypes(model: torch.nn.Module) -> dict[str, np.ndarray]:
    tokenizer = open_clip.get_tokenizer("ViT-B-16")
    result = {}
    with torch.inference_mode():
        for name, prompts in PROMPTS.items():
            encoded = F.normalize(model.encode_text(tokenizer(list(prompts))), dim=1)
            result[name] = F.normalize(encoded.mean(dim=0), dim=0).cpu().numpy().astype(np.float32)
    return result


def _category_scores(
    appearance_views: np.ndarray, prototypes: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    return {
        name: np.einsum("nvd,d->nv", appearance_views, prototype).max(axis=1)
        for name, prototype in prototypes.items()
    }


def _score_modes(category: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    complete = category["complete_number"]
    fragment = category["number_fragment"]
    nonnumber = np.maximum(category["sponsor"], category["paint"])
    return {
        "complete_raw": complete,
        "complete_minus_fragment": complete - fragment,
        "complete_minus_nonnumber": complete - nonnumber,
        "complete_minus_all": complete - np.maximum(fragment, nonnumber),
    }


def _safe_threshold(
    truth: np.ndarray,
    explicit: np.ndarray,
    score: np.ndarray,
    control_stress: np.ndarray,
    *,
    precision_floor: float = 0.80,
) -> float:
    """Maximize true accepts while refusing reviewed-uncertain and control errors."""
    choices = []
    for value in np.unique(score):
        accepted = score >= value
        if np.any(accepted & ~explicit) or np.any(accepted & control_stress):
            continue
        explicit_accepted = accepted & explicit
        precision = (
            float(truth[explicit_accepted].mean()) if explicit_accepted.any() else 1.0
        )
        if precision < precision_floor:
            continue
        choices.append((
            int(np.count_nonzero(accepted & truth)), precision,
            -int(np.count_nonzero(explicit_accepted & ~truth)), -float(value),
        ))
    return -max(choices)[3] if choices else float(np.nextafter(score.max(), np.inf))


def _select_mode(
    indices: np.ndarray, modes: dict[str, np.ndarray], truth: np.ndarray, explicit: np.ndarray,
) -> str:
    ranked = []
    for order, name in enumerate(SCORE_MODES):
        selected = indices[explicit[indices]]
        ap = float(average_precision_score(truth[selected], modes[name][selected]))
        ranked.append((ap, -order, name))
    return max(ranked)[2]


def _metrics(truth, explicit, accepted, stress) -> dict:
    explicit_accepted = accepted & explicit
    false = explicit_accepted & ~truth
    return {
        "accepted_count": int(np.count_nonzero(accepted)),
        "accepted_true_positive_count": int(np.count_nonzero(accepted & truth)),
        "accepted_explicit_false_positive_count": int(np.count_nonzero(false)),
        "accepted_review_uncertain_count": int(np.count_nonzero(accepted & ~explicit)),
        "precision_on_explicit": round(
            float(truth[explicit_accepted].mean()) if explicit_accepted.any() else 1.0, 6,
        ),
        "recall": round(
            float(np.count_nonzero(accepted & truth) / max(1, np.count_nonzero(truth))), 6,
        ),
        "five_control_wrong_accepts": int(np.count_nonzero(accepted & stress)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--baseline-embeddings", type=Path, required=True)
    parser.add_argument("--clip-embeddings", type=Path, required=True)
    parser.add_argument("--clipseg-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=728)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    data = _load_data(args.bank, args.labels, args.baseline_embeddings, size=64)
    intrinsics = _load_intrinsics(args.bank, args.labels, data["trace"])
    clip = np.load(args.clip_embeddings, allow_pickle=False)
    appearance = clip["appearance"].astype(np.float32)
    model = _load_local_clipseg_vision(args.clipseg_checkpoint, "cpu")
    prototypes = _prompt_prototypes(model)
    category = _category_scores(appearance, prototypes)
    modes = _score_modes(category)
    indices = np.arange(len(data["groups"]), dtype=np.int64)
    content_groups = intrinsics["content_groups"]
    truth = data["complete"] == 1
    explicit = data["complete"] >= 0
    semantic_truth = data["semantic"] == 1
    semantic_explicit = data["semantic"] >= 0
    probability = np.zeros(len(indices), dtype=np.float64)
    accepted = np.zeros(len(indices), dtype=bool)
    folds = []
    for fold, (train, test) in enumerate(
        GroupKFold(n_splits=5).split(indices, groups=content_groups)
    ):
        selected = _select_mode(train, modes, truth, explicit)
        threshold = _safe_threshold(
            truth[train], explicit[train], modes[selected][train], data["stress"][train],
        )
        probability[test] = modes[selected][test]
        accepted[test] = modes[selected][test] >= threshold
        folds.append({
            "fold": fold,
            "test_paints": sorted(set(data["groups"][test])),
            "test_source_content_groups": len(set(content_groups[test])),
            "selected_score_mode": selected,
            "safe_train_threshold": round(threshold, 8),
            "test_accepted_count": int(np.count_nonzero(accepted[test])),
        })
    valid_explicit_ap = float(average_precision_score(truth[explicit], probability[explicit]))
    legacy_comparable_ap = float(average_precision_score(truth, probability))
    number_raw = np.maximum(category["complete_number"], category["number_fragment"])
    semantic_ap = float(average_precision_score(
        semantic_truth[semantic_explicit], number_raw[semantic_explicit],
    ))
    within_number_ap = float(average_precision_score(
        truth[semantic_truth],
        (category["complete_number"] - category["number_fragment"])[semantic_truth],
    ))
    acceptance = _metrics(truth, explicit, accepted, data["stress"])
    complete_gate = bool(
        legacy_comparable_ap > 0.489735
        and valid_explicit_ap > 0.489735
        and acceptance["precision_on_explicit"] >= 0.80
        and acceptance["five_control_wrong_accepts"] == 0
        and acceptance["accepted_review_uncertain_count"] == 0
        and acceptance["accepted_true_positive_count"] > 0
    )
    examples = [{
        **trace,
        "semantic": int(data["semantic"][index]),
        "complete": int(data["complete"][index]),
        "source_content_group": str(content_groups[index]),
        "oof_score": round(float(probability[index]), 8),
        "oof_accepted": bool(accepted[index]),
        "category_scores": {
            name: round(float(values[index]), 8) for name, values in category.items()
        },
        "ownership_authority": False,
    } for index, trace in enumerate(data["trace"])]
    (args.output / "oof_examples.json").write_text(
        json.dumps(examples, indent=2) + "\n", encoding="utf-8",
    )
    ledger = {
        "schema": "smart-tga-clipseg-zero-shot-semantic-probe-v1",
        "cycle": args.cycle,
        "baseline": {
            "legacy_complete_number_average_precision": 0.489735,
            "frozen_clip_b32_silhouette_anchor_extension_ap": 0.672250,
        },
        "after_source_content_disjoint": {
            "semantic_number_zero_shot_explicit_ap_diagnostic": round(semantic_ap, 6),
            "complete_number_legacy_comparable_ap": round(legacy_comparable_ap, 6),
            "complete_number_valid_explicit_ap": round(valid_explicit_ap, 6),
            "within_number_complete_vs_fragment_ap_diagnostic": round(within_number_ap, 6),
            "selected_score_mode_counts": dict(Counter(
                row["selected_score_mode"] for row in folds
            )),
            **acceptance,
        },
        "gates": {
            "zero_shot_complete_gate_passed": complete_gate,
            "requires_legacy_comparable_ap_greater_than": 0.489735,
            "requires_valid_explicit_ap_greater_than": 0.489735,
            "requires_precision_at_least": 0.80,
            "requires_zero_five_control_wrong_accepts": True,
            "requires_zero_review_uncertain_accepts": True,
            "runtime_integrated": False,
            "holdout_opened": False,
        },
        "prompt_ensembles": {name: list(values) for name, values in PROMPTS.items()},
        "targets": sorted(set(data["groups"]) - CONTROL_PAINTS),
        "hard_negative_controls": sorted(set(data["groups"]) & CONTROL_PAINTS),
        "folds": folds,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "model_weights_frozen": True,
            "prompt_vocabulary_is_owner_neutral": True,
            "outer_source_content_disjoint": True,
            "score_mode_and_threshold_selected_inside_outer_training_fold": True,
            "casts_votes": False,
            "ownership_authority": False,
            "apply_locked": True,
            "holdout_consumed": False,
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
        "baseline": ledger["baseline"],
        "after": ledger["after_source_content_disjoint"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
