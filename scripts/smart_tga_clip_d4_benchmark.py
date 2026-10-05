"""Benchmark frozen CLIP D4 evidence on exact reviewed Smart TGA masks.

This is a representation-only probe.  Review labels define the paint-disjoint
evaluation pairs after encoding; they never alter CLIP weights or pixels.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import cv2
import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
import torch
from torch.nn import functional as F

import open_clip

try:
    from scripts.smart_tga_local_masked_patch_train import (
        CONTROL_PAINTS,
        _decode_support,
        _load_data,
        _normalized_patch,
        _orbit_scores,
        _pair_sets,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_local_masked_patch_train import (  # type: ignore
        CONTROL_PAINTS,
        _decode_support,
        _load_data,
        _normalized_patch,
        _orbit_scores,
        _pair_sets,
    )


CLIP_MEAN = torch.tensor((0.48145466, 0.4578275, 0.40821073)).view(1, 3, 1, 1)
CLIP_STD = torch.tensor((0.26862954, 0.26130258, 0.27577711)).view(1, 3, 1, 1)
REPRESENTATIONS = ("appearance", "silhouette", "appearance_silhouette_equal")


def _load_local_clipseg_vision(checkpoint: Path, device: str) -> torch.nn.Module:
    """Map a local HF CLIPSeg ViT-B/16 CLIP model into open_clip.

    The workspace intentionally does not depend on ``transformers``.  CLIPSeg
    stores an ordinary CLIP ViT-B/16 model, so its frozen vision and text
    weights can be mapped losslessly into the installed open_clip implementation.
    """
    from safetensors import safe_open

    model = open_clip.create_model("ViT-B-16", pretrained=None, device=device).eval()
    mapped: dict[str, torch.Tensor] = {}
    text_mapped: dict[str, torch.Tensor] = {}
    with safe_open(checkpoint, framework="pt", device="cpu") as values:
        def take(target: str, source: str, *, transpose: bool = False) -> None:
            tensor = values.get_tensor(source)
            mapped[target] = tensor.t() if transpose else tensor

        prefix = "clip.vision_model"
        take("class_embedding", f"{prefix}.embeddings.class_embedding")
        take("positional_embedding", f"{prefix}.embeddings.position_embedding.weight")
        take("conv1.weight", f"{prefix}.embeddings.patch_embedding.weight")
        take("ln_pre.weight", f"{prefix}.pre_layrnorm.weight")
        take("ln_pre.bias", f"{prefix}.pre_layrnorm.bias")
        take("ln_post.weight", f"{prefix}.post_layernorm.weight")
        take("ln_post.bias", f"{prefix}.post_layernorm.bias")
        take("proj", "clip.visual_projection.weight", transpose=True)
        for layer in range(12):
            source = f"{prefix}.encoder.layers.{layer}"
            target = f"transformer.resblocks.{layer}"
            take(f"{target}.ln_1.weight", f"{source}.layer_norm1.weight")
            take(f"{target}.ln_1.bias", f"{source}.layer_norm1.bias")
            take(f"{target}.ln_2.weight", f"{source}.layer_norm2.weight")
            take(f"{target}.ln_2.bias", f"{source}.layer_norm2.bias")
            mapped[f"{target}.attn.in_proj_weight"] = torch.cat([
                values.get_tensor(f"{source}.self_attn.{name}_proj.weight")
                for name in ("q", "k", "v")
            ])
            mapped[f"{target}.attn.in_proj_bias"] = torch.cat([
                values.get_tensor(f"{source}.self_attn.{name}_proj.bias")
                for name in ("q", "k", "v")
            ])
            take(f"{target}.attn.out_proj.weight", f"{source}.self_attn.out_proj.weight")
            take(f"{target}.attn.out_proj.bias", f"{source}.self_attn.out_proj.bias")
            take(f"{target}.mlp.c_fc.weight", f"{source}.mlp.fc1.weight")
            take(f"{target}.mlp.c_fc.bias", f"{source}.mlp.fc1.bias")
            take(f"{target}.mlp.c_proj.weight", f"{source}.mlp.fc2.weight")
            take(f"{target}.mlp.c_proj.bias", f"{source}.mlp.fc2.bias")
        text_prefix = "clip.text_model"

        def take_text(target: str, source: str, *, transpose: bool = False) -> None:
            tensor = values.get_tensor(source)
            text_mapped[target] = tensor.t() if transpose else tensor

        take_text("positional_embedding", f"{text_prefix}.embeddings.position_embedding.weight")
        take_text("token_embedding.weight", f"{text_prefix}.embeddings.token_embedding.weight")
        take_text("ln_final.weight", f"{text_prefix}.final_layer_norm.weight")
        take_text("ln_final.bias", f"{text_prefix}.final_layer_norm.bias")
        take_text("text_projection", "clip.text_projection.weight", transpose=True)
        take_text("logit_scale", "clip.logit_scale")
        for layer in range(12):
            source = f"{text_prefix}.encoder.layers.{layer}"
            target = f"transformer.resblocks.{layer}"
            take_text(f"{target}.ln_1.weight", f"{source}.layer_norm1.weight")
            take_text(f"{target}.ln_1.bias", f"{source}.layer_norm1.bias")
            take_text(f"{target}.ln_2.weight", f"{source}.layer_norm2.weight")
            take_text(f"{target}.ln_2.bias", f"{source}.layer_norm2.bias")
            text_mapped[f"{target}.attn.in_proj_weight"] = torch.cat([
                values.get_tensor(f"{source}.self_attn.{name}_proj.weight")
                for name in ("q", "k", "v")
            ])
            text_mapped[f"{target}.attn.in_proj_bias"] = torch.cat([
                values.get_tensor(f"{source}.self_attn.{name}_proj.bias")
                for name in ("q", "k", "v")
            ])
            take_text(f"{target}.attn.out_proj.weight", f"{source}.self_attn.out_proj.weight")
            take_text(f"{target}.attn.out_proj.bias", f"{source}.self_attn.out_proj.bias")
            take_text(f"{target}.mlp.c_fc.weight", f"{source}.mlp.fc1.weight")
            take_text(f"{target}.mlp.c_fc.bias", f"{source}.mlp.fc1.bias")
            take_text(f"{target}.mlp.c_proj.weight", f"{source}.mlp.fc2.weight")
            take_text(f"{target}.mlp.c_proj.bias", f"{source}.mlp.fc2.bias")
    model.visual.load_state_dict(mapped, strict=True)
    result = model.load_state_dict(text_mapped, strict=False)
    if result.unexpected_keys or any(not key.startswith("visual.") for key in result.missing_keys):
        raise RuntimeError(
            f"CLIPSeg text mapping drift: missing={result.missing_keys}, "
            f"unexpected={result.unexpected_keys}"
        )
    return model


def _clip_inputs(patches: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return neutral-background appearance and binary silhouette D4 views."""
    if patches.shape[0:2] != (8, 6):
        raise ValueError("patches must have shape (8, 6, height, width)")
    mask = np.clip(patches[:, 3:4], 0.0, 1.0)
    appearance = np.clip(patches[:, :3], 0.0, 1.0) * mask + 0.5 * (1.0 - mask)
    silhouette = np.repeat(mask, 3, axis=1)
    return appearance.astype(np.float32), silhouette.astype(np.float32)


def _equal_fusion(appearance: np.ndarray, silhouette: np.ndarray) -> np.ndarray:
    fused = np.concatenate((appearance, silhouette), axis=2)
    fused /= np.maximum(np.linalg.norm(fused, axis=2, keepdims=True), 1e-8)
    return fused.astype(np.float32)


def _encode_batch(
    model: torch.nn.Module, images: list[np.ndarray], device: torch.device | str = "cpu",
) -> np.ndarray:
    tensor = torch.from_numpy(np.concatenate(images, axis=0))
    tensor = ((tensor - CLIP_MEAN) / CLIP_STD).to(device)
    with torch.inference_mode():
        encoded = F.normalize(model.encode_image(tensor), dim=1)
    return encoded.cpu().numpy().astype(np.float32)


def _build_embeddings(
    bank_path: Path,
    labels_path: Path,
    output_path: Path,
    *,
    batch_candidates: int,
    model_name: str = "ViT-B-32",
    pretrained: str = "laion2b_s34b_b79k",
    device: str = "cpu",
    clipseg_checkpoint: Path | None = None,
    include_silhouette: bool = True,
) -> dict:
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
    records = {row["paint"]: row for row in bank["records"]}
    model = (
        _load_local_clipseg_vision(clipseg_checkpoint, device)
        if clipseg_checkpoint is not None
        else open_clip.create_model(model_name, pretrained=pretrained, device=device).eval()
    )
    source_cache: dict[str, np.ndarray] = {}
    exact_cache = {}
    appearance_rows, silhouette_rows, trace = [], [], []
    pending: list[np.ndarray] = []
    pending_kinds: list[tuple[str, int]] = []

    def flush() -> None:
        if not pending:
            return
        result = _encode_batch(model, pending, device)
        cursor = 0
        for kind, count in pending_kinds:
            values = result[cursor:cursor + count]
            cursor += count
            (appearance_rows if kind == "appearance" else silhouette_rows).append(values)
        pending.clear()
        pending_kinds.clear()

    for offset, row in enumerate(labels):
        paint, index = row["paint"], int(row["candidate_index"])
        record = records[paint]
        if paint not in source_cache:
            bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
            if bgr is None:
                raise FileNotFoundError(record["source_1024"])
            source_cache[paint] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            exact_cache[paint] = np.load(record["exact_candidate_bank"], allow_pickle=False)
        exact = exact_cache[paint]
        proposal_id = str(exact["proposal_ids"][index])
        if proposal_id != row["proposal_id"]:
            raise RuntimeError(f"candidate ID drift at {row['review_code']}")
        x, y, width, height = map(int, exact["bboxes"][index])
        support = _decode_support(exact, index)
        rgb = source_cache[paint][y:y + height, x:x + width]
        appearance, silhouette = _clip_inputs(_normalized_patch(rgb, support, 224))
        pending.append(appearance)
        pending_kinds.append(("appearance", 8))
        if include_silhouette:
            pending.append(silhouette)
            pending_kinds.append(("silhouette", 8))
        trace.append((row["review_code"], paint, index, proposal_id))
        if (offset + 1) % batch_candidates == 0:
            flush()
            print(f"encoded {offset + 1}/{len(labels)} exact candidates", flush=True)
    flush()
    for values in exact_cache.values():
        values.close()
    appearance = np.stack(appearance_rows).astype(np.float32)
    silhouette = (
        np.stack(silhouette_rows).astype(np.float32) if include_silhouette else None
    )
    if appearance.shape[:2] != (len(labels), 8):
        raise RuntimeError(f"appearance embedding shape drift: {appearance.shape}")
    if include_silhouette and silhouette.shape != appearance.shape:
        raise RuntimeError(f"silhouette embedding shape drift: {silhouette.shape}")
    payload = dict(
        appearance=appearance,
        review_codes=np.asarray([row[0] for row in trace]),
        paints=np.asarray([row[1] for row in trace]),
        candidate_indices=np.asarray([row[2] for row in trace], dtype=np.int64),
        proposal_ids=np.asarray([row[3] for row in trace]),
    )
    if include_silhouette:
        payload["silhouette"] = silhouette
    np.savez_compressed(output_path, **payload)
    return {
        "cached": False, "candidate_count": len(labels),
        "embedding_dim": appearance.shape[2], "model_name": model_name,
        "pretrained": pretrained, "device": device,
        "clipseg_checkpoint": str(clipseg_checkpoint) if clipseg_checkpoint else None,
        "include_silhouette": include_silhouette,
    }


def _load_or_build_embeddings(args) -> tuple[dict[str, np.ndarray], dict]:
    output_path = args.output / args.embedding_file
    if output_path.exists():
        cache = np.load(output_path, allow_pickle=False)
        return {
            "appearance": cache["appearance"].astype(np.float32),
            "silhouette": cache["silhouette"].astype(np.float32),
        }, {"cached": True, "candidate_count": len(cache["appearance"]), "embedding_dim": cache["appearance"].shape[2]}
    build = _build_embeddings(
        args.bank, args.labels, output_path, batch_candidates=args.batch_candidates,
        model_name=args.model_name, pretrained=args.pretrained, device=args.device,
        clipseg_checkpoint=args.clipseg_checkpoint,
    )
    cache = np.load(output_path, allow_pickle=False)
    return {
        "appearance": cache["appearance"].astype(np.float32),
        "silhouette": cache["silhouette"].astype(np.float32),
    }, build


def _evaluate(data: dict, embeddings: dict[str, np.ndarray]) -> dict:
    candidate_count = len(data["groups"])
    if any(len(values) != candidate_count for values in embeddings.values()):
        raise RuntimeError("CLIP/label candidate count drift")
    views = {
        "appearance": embeddings["appearance"],
        "silhouette": embeddings["silhouette"],
        "appearance_silhouette_equal": _equal_fusion(
            embeddings["appearance"], embeddings["silhouette"],
        ),
    }
    family_scores = {name: [] for name in (*REPRESENTATIONS, "efficientnet")}
    operational_scores = {name: [] for name in (*REPRESENTATIONS, "efficientnet")}
    family_truths: list[bool] = []
    operational_truths: list[bool] = []
    folds = []
    indices = np.arange(candidate_count, dtype=np.int64)
    for fold, (_, test) in enumerate(GroupKFold(n_splits=5).split(indices, groups=data["groups"])):
        positive, family_negative, semantic_negative = _pair_sets(test, data, local=True)
        family_truth = np.concatenate((
            np.ones(len(positive), dtype=bool),
            np.zeros(len(family_negative), dtype=bool),
        ))
        operational_truth = np.concatenate((
            np.ones(len(positive), dtype=bool),
            np.zeros(len(semantic_negative), dtype=bool),
        ))
        family_truths.extend(family_truth.tolist())
        operational_truths.extend(operational_truth.tolist())
        for name in REPRESENTATIONS:
            fold_views = views[name][test]
            family_scores[name].extend(np.concatenate((
                _orbit_scores(fold_views, positive),
                _orbit_scores(fold_views, family_negative),
            )).tolist())
            operational_scores[name].extend(np.concatenate((
                _orbit_scores(fold_views, positive),
                _orbit_scores(fold_views, semantic_negative),
            )).tolist())
        baseline = data["baseline_views"][test]
        family_scores["efficientnet"].extend(np.concatenate((
            _orbit_scores(baseline, positive),
            _orbit_scores(baseline, family_negative),
        )).tolist())
        operational_scores["efficientnet"].extend(np.concatenate((
            _orbit_scores(baseline, positive),
            _orbit_scores(baseline, semantic_negative),
        )).tolist())
        folds.append({
            "fold": fold,
            "test_paints": sorted(set(data["groups"][test])),
            "positive_pairs": len(positive),
            "cross_paint_number_family_negatives": len(family_negative),
            "within_paint_number_nonnumber_negatives": len(semantic_negative),
        })
    family_average_precision = {
        name: float(average_precision_score(family_truths, values))
        for name, values in family_scores.items()
    }
    operational_average_precision = {
        name: float(average_precision_score(operational_truths, values))
        for name, values in operational_scores.items()
    }
    return {
        "family_diagnostic": {
            "pair_count": len(family_truths),
            "positive_pair_count": int(np.count_nonzero(family_truths)),
            "prevalence": float(np.mean(family_truths)),
            "average_precision": family_average_precision,
        },
        "operational_anchor_extension": {
            "pair_count": len(operational_truths),
            "positive_pair_count": int(np.count_nonzero(operational_truths)),
            "prevalence": float(np.mean(operational_truths)),
            "average_precision": operational_average_precision,
        },
        "folds": folds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--baseline-embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-candidates", type=int, default=2)
    parser.add_argument("--model-name", default="ViT-B-32")
    parser.add_argument("--pretrained", default="laion2b_s34b_b79k")
    parser.add_argument("--embedding-file", default="clip_d4_embeddings.npz")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--clipseg-checkpoint", type=Path)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--cycle", type=int, default=727)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(max(1, args.threads))
    embeddings, cache = _load_or_build_embeddings(args)
    metadata = _load_data(
        args.bank, args.labels, args.baseline_embeddings, size=64,
    )
    evaluation = _evaluate(metadata, embeddings)
    operational = evaluation["operational_anchor_extension"]
    diagnostic = evaluation["family_diagnostic"]
    baseline = operational["average_precision"]["efficientnet"]
    best_name = max(REPRESENTATIONS, key=operational["average_precision"].get)
    best_ap = operational["average_precision"][best_name]
    prevalence = operational["prevalence"]
    if abs(diagnostic["average_precision"]["efficientnet"] - 0.493040) > 5e-6:
        raise RuntimeError("EfficientNet diagnostic baseline drift")
    representation_gate = best_ap > baseline and best_ap >= prevalence + 0.10
    targets = sorted(set(metadata["groups"]) - CONTROL_PAINTS)
    controls = sorted(set(metadata["groups"]) & CONTROL_PAINTS)
    ledger = {
        "schema": "smart-tga-frozen-clip-d4-representation-benchmark-v1",
        "cycle": args.cycle,
        "baseline": {
            "frozen_efficientnet_operational_anchor_extension_ap": round(baseline, 6),
            "operational_prevalence": round(prevalence, 6),
        },
        "after": {
            "encoder": (
                "local CLIPSeg CLIP ViT-B/16 vision tower mapped to open_clip (frozen)"
                if args.clipseg_checkpoint else
                f"open_clip {args.model_name} {args.pretrained} (frozen)"
            ),
            "candidate_count": len(metadata["groups"]),
            "paint_count": len(set(metadata["groups"])),
            "operational_pair_count": operational["pair_count"],
            "positive_pair_count": operational["positive_pair_count"],
            "operational_prevalence": round(prevalence, 6),
            "appearance_operational_ap": round(operational["average_precision"]["appearance"], 6),
            "silhouette_operational_ap": round(operational["average_precision"]["silhouette"], 6),
            "fixed_equal_fusion_operational_ap": round(operational["average_precision"]["appearance_silhouette_equal"], 6),
            "best_predeclared_representation": best_name,
            "best_operational_clip_ap": round(best_ap, 6),
            "best_clip_gain_over_prevalence": round(best_ap - prevalence, 6),
            "best_clip_gain_over_efficientnet": round(best_ap - baseline, 6),
        },
        "non_authoritative_cross_paint_diagnostic": {
            "reason": "Cross-paint identity does not prove different decal identity; exact duplicate Number candidates were found across two chassis. These pairs are diagnostic only and cannot gate acceptance.",
            "pair_count": diagnostic["pair_count"],
            "prevalence": round(diagnostic["prevalence"], 6),
            "efficientnet_ap": round(diagnostic["average_precision"]["efficientnet"], 6),
            "clip_appearance_ap": round(diagnostic["average_precision"]["appearance"], 6),
            "clip_silhouette_ap": round(diagnostic["average_precision"]["silhouette"], 6),
        },
        "gates": {
            "representation_gate_passed": representation_gate,
            "requires_gain_over_efficientnet": True,
            "requires_gain_over_prevalence": 0.10,
            "supervised_head_allowed_next": representation_gate,
            "holdout_opened": False,
            "runtime_integrated": False,
        },
        "targets": targets,
        "hard_negative_controls": controls,
        "folds": evaluation["folds"],
        "embedding_cache": cache,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "model_weights_frozen": True,
            "labels_used_for_feature_learning": False,
            "casts_votes": False,
            "ownership_authority": False,
            "apply_locked": True,
            "holdout_consumed": False,
            "filename_or_car_features": False,
            "reviewed_bbox_inference_feature": False,
            "exact_reconstruction_affected": False,
        },
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": ledger["baseline"],
        "after": ledger["after"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
