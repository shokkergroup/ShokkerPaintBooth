"""Build candidate-resolution frozen CLIP racing-semantic evidence.

This reuses the universal prompt vocabulary frozen in Cycle728 and existing
exact-mask D4 candidate embeddings.  Each candidate therefore receives the
full 224px vision input instead of a few pixels in a whole-atlas heatmap.
Prompt evidence is label-free, location-free and veto-only downstream.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

try:
    from scripts.smart_tga_clip_d4_benchmark import _load_local_clipseg_vision
    from scripts.smart_tga_clipseg_zero_shot_probe import PROMPTS, _prompt_prototypes
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_clip_d4_benchmark import _load_local_clipseg_vision  # type: ignore
    from scripts.smart_tga_clipseg_zero_shot_probe import (  # type: ignore
        PROMPTS, _prompt_prototypes,
    )


SUMMARY_STATS = ("mean", "max", "q90", "std")
MARGINS = (
    "number_minus_nonnumber", "complete_minus_nonnumber",
    "fragment_minus_nonnumber", "complete_minus_fragment",
)
FEATURE_NAMES = tuple(
    f"prompt_{category}_{stat}"
    for category in PROMPTS for stat in SUMMARY_STATS
) + tuple(
    f"prompt_{margin}_{stat}" for margin in MARGINS for stat in SUMMARY_STATS
)


def prompt_feature_matrix(
    appearance: np.ndarray, prototypes: dict[str, np.ndarray],
) -> np.ndarray:
    if appearance.ndim != 3 or appearance.shape[1] != 8:
        raise ValueError("expected candidate x 8 D4 views x embedding dimensions")
    category = {
        name: np.einsum("nvd,d->nv", appearance, prototype)
        for name, prototype in prototypes.items()
    }
    number = np.maximum(category["complete_number"], category["number_fragment"])
    nonnumber = np.maximum(category["sponsor"], category["paint"])
    values = []
    for name in PROMPTS:
        score = category[name]
        values.extend((
            score.mean(axis=1), score.max(axis=1),
            np.quantile(score, 0.90, axis=1), score.std(axis=1),
        ))
    margin_rows = {
        "number_minus_nonnumber": number - nonnumber,
        "complete_minus_nonnumber": category["complete_number"] - nonnumber,
        "fragment_minus_nonnumber": category["number_fragment"] - nonnumber,
        "complete_minus_fragment": (
            category["complete_number"] - category["number_fragment"]
        ),
    }
    for name in MARGINS:
        score = margin_rows[name]
        values.extend((
            score.mean(axis=1), score.max(axis=1),
            np.quantile(score, 0.90, axis=1), score.std(axis=1),
        ))
    result = np.column_stack(values).astype(np.float32)
    if result.shape != (len(appearance), len(FEATURE_NAMES)):
        raise RuntimeError("prompt feature schema drift")
    if not np.all(np.isfinite(result)):
        raise RuntimeError("non-finite prompt feature")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appearance", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cycle", type=int, default=735)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cache = np.load(args.appearance, allow_pickle=False)
    try:
        appearance = cache["appearance"].astype(np.float32)
        paints = cache["paints"].copy()
        indices = cache["candidate_indices"].copy()
        proposals = cache["proposal_ids"].copy()
    finally:
        cache.close()
    model = _load_local_clipseg_vision(args.checkpoint, args.device)
    prototypes = _prompt_prototypes(model)
    features = prompt_feature_matrix(appearance, prototypes)
    np.savez_compressed(
        args.output, features=features, feature_names=np.asarray(FEATURE_NAMES),
        paints=paints, candidate_indices=indices, proposal_ids=proposals,
    )
    manifest = {
        "schema": "smart-tga-frozen-candidate-clip-prompt-bank-v1",
        "cycle": args.cycle, "candidate_count": len(features),
        "feature_count": len(FEATURE_NAMES),
        "prompt_source": "Cycle728 frozen universal racing vocabulary",
        "prompts": PROMPTS, "d4_views": 8, "candidate_resolution": 224,
        "semantic_labels_consumed": False, "bbox_or_location_feature": False,
        "model_weights_frozen": True, "ownership_authority": False,
        "checkpoint": str(args.checkpoint), "device": args.device,
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
