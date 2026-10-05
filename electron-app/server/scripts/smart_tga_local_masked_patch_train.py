"""Train and measure a local exact-mask Smart TGA family encoder paint-disjoint."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import time

import cv2
import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
import torch

try:
    from engine.spec_sculpt.local_masked_patch_encoder import LocalMaskedPatchHead, orbit_similarity
    from engine.spec_sculpt.masked_glyph_encoder import masked_glyph_loss
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.local_masked_patch_encoder import LocalMaskedPatchHead, orbit_similarity  # type: ignore
    from engine.spec_sculpt.masked_glyph_encoder import masked_glyph_loss  # type: ignore


CONTROL_PAINTS = {
    "dirtlatemodel 350/car_num_1006305.tga",
    "dirtlatemodel 350/car_num_1007631.tga",
    "dirtlatemodel 358/car_num_1008515.tga",
    "dirtlatemodel 358/car_num_1328151.tga",
    "dirtlatemodel 358/car_num_247671.tga",
}

CONFIG = {
    "patch_size": 64,
    "projection_dim": 64,
    "learning_rate": 0.0015,
    "weight_decay": 0.003,
    "pair_weight": 1.25,
    "consistency_weight": 0.04,
}


def _decode_support(exact, index: int) -> np.ndarray:
    offset = int(exact["offsets"][index])
    length = int(exact["lengths"][index])
    height, width = map(int, exact["shapes"][index])
    return np.unpackbits(exact["packed"][offset:offset + length])[:height * width].reshape(height, width).astype(bool)


def _normalized_patch(rgb: np.ndarray, support: np.ndarray, size: int) -> np.ndarray:
    if rgb.shape[:2] != support.shape:
        raise ValueError(f"source/mask shape mismatch: {rgb.shape[:2]} vs {support.shape}")
    height, width = support.shape
    scale = float(size - 8) / max(height, width)
    target_h = max(1, min(size, int(round(height * scale))))
    target_w = max(1, min(size, int(round(width * scale))))
    mask_u8 = support.astype(np.uint8)
    masked_rgb = rgb.astype(np.float32) / 255.0
    masked_rgb *= support[:, :, None]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.magnitude(grad_x, grad_y) * support
    if edge.max() > 0:
        edge /= edge.max()
    distance = cv2.distanceTransform(mask_u8, cv2.DIST_L2, 3)
    if distance.max() > 0:
        distance /= distance.max()
    channels = np.dstack((masked_rgb, support.astype(np.float32), edge, distance))
    # OpenCV resize supports at most four channels. Keep the RGB and intrinsic
    # mask/edge/distance evidence aligned by resizing the two 3-channel groups
    # independently, then reassemble the exact six-channel tensor.
    resized = np.concatenate(
        [
            cv2.resize(channels[:, :, :3], (target_w, target_h), interpolation=cv2.INTER_AREA),
            cv2.resize(channels[:, :, 3:], (target_w, target_h), interpolation=cv2.INTER_AREA),
        ],
        axis=2,
    )
    canvas = np.zeros((size, size, channels.shape[2]), dtype=np.float32)
    top, left = (size - target_h) // 2, (size - target_w) // 2
    canvas[top:top + target_h, left:left + target_w] = resized
    views = []
    for turns in range(4):
        rotated = np.rot90(canvas, turns, axes=(0, 1))
        views.extend((rotated, np.fliplr(rotated)))
    return np.ascontiguousarray(np.stack(views).transpose(0, 3, 1, 2), dtype=np.float32)


def _load_data(bank_path: Path, labels_path: Path, baseline_manifest_path: Path, size: int):
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
    manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    records = {row["paint"]: row for row in bank["records"]}
    embedding_records = {row["paint"]: row for row in manifest["records"]}
    source_cache, exact_cache, embedding_cache = {}, {}, {}
    patches, semantics, complete, groups, blocks, stress, baseline_views, trace = [], [], [], [], [], [], [], []
    for row in labels:
        paint, index = row["paint"], int(row["candidate_index"])
        record = records[paint]
        if paint not in source_cache:
            bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
            if bgr is None:
                raise FileNotFoundError(record["source_1024"])
            source_cache[paint] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            exact_cache[paint] = np.load(record["exact_candidate_bank"], allow_pickle=False)
            embedding_cache[paint] = np.load(
                embedding_records[paint]["embedding_bank"], allow_pickle=False,
            )
        exact = exact_cache[paint]
        proposal_id = str(exact["proposal_ids"][index])
        if proposal_id != row["proposal_id"]:
            raise RuntimeError(f"candidate ID drift at {row['review_code']}")
        x, y, width, height = map(int, exact["bboxes"][index])
        support = _decode_support(exact, index)
        rgb = source_cache[paint][y:y + height, x:x + width]
        patches.append(_normalized_patch(rgb, support, size))
        baseline_ids = embedding_cache[paint]["proposal_ids"].tolist()
        if baseline_ids[index] != proposal_id:
            raise RuntimeError(f"baseline embedding ID drift at {row['review_code']}")
        embedded = embedding_cache[paint]["d4_embeddings"][index].astype(np.float32)
        embedded /= np.maximum(np.linalg.norm(embedded, axis=1, keepdims=True), 1e-8)
        baseline_views.append(embedded)
        if row["semantic"] == "uncertain":
            semantic_target = complete_target = -1
        else:
            semantic_target = int(row["semantic"] == "Number")
            complete_target = int(row["semantic"] == "Number" and row.get("complete_copy") is True)
        semantics.append(semantic_target)
        complete.append(complete_target)
        groups.append(paint)
        blocks.append(record["candidates"][index]["dominant_number_block"])
        stress.append(paint in CONTROL_PAINTS and complete_target != 1)
        trace.append({
            "review_code": row["review_code"], "paint": paint,
            "candidate_index": index, "proposal_id": proposal_id,
        })
    for values in exact_cache.values():
        values.close()
    for values in embedding_cache.values():
        values.close()
    return {
        "patches": np.asarray(patches, dtype=np.float32),
        "baseline_views": np.asarray(baseline_views, dtype=np.float32),
        "semantic": np.asarray(semantics, dtype=np.int64),
        "complete": np.asarray(complete, dtype=np.int64),
        "groups": np.asarray(groups),
        "blocks": np.asarray(blocks),
        "stress": np.asarray(stress, dtype=bool),
        "trace": trace,
    }


def _pair_sets(indices, data, *, local: bool):
    indices = np.asarray(indices, dtype=np.int64)
    remap = {int(value): offset for offset, value in enumerate(indices)}
    grouped = defaultdict(list)
    for index in indices:
        grouped[data["groups"][index]].append(int(index))
    positive, family_negative, semantic_negative = [], [], []
    for paint_indices in grouped.values():
        for offset, first in enumerate(paint_indices):
            if data["semantic"][first] < 0:
                continue
            for second in paint_indices[offset + 1:]:
                if data["semantic"][second] < 0 or data["blocks"][first] == data["blocks"][second]:
                    continue
                first_number = data["semantic"][first] == 1
                second_number = data["semantic"][second] == 1
                if first_number and second_number:
                    positive.append((first, second))
                elif first_number or second_number:
                    semantic_negative.append((first, second))
    number_indices = [int(index) for index in indices if data["semantic"][index] == 1]
    for offset, first in enumerate(number_indices):
        for second in number_indices[offset + 1:]:
            if data["groups"][first] != data["groups"][second]:
                family_negative.append((first, second))

    def convert(values):
        return np.asarray([
            (remap[first], remap[second]) if local else (first, second)
            for first, second in values
        ], dtype=np.int64).reshape(-1, 2)

    return convert(positive), convert(family_negative), convert(semantic_negative)


def _jitter_patches(patches: torch.Tensor) -> torch.Tensor:
    result = patches.clone()
    candidate_count = len(result)
    gain = 0.82 + torch.rand((candidate_count, 1, 3, 1, 1), device=result.device) * 0.36
    bias = (torch.rand((candidate_count, 1, 1, 1, 1), device=result.device) - 0.5) * 0.10
    mask = result[:, :, 3:4]
    noise = torch.randn_like(result[:, :, :3]) * 0.012
    result[:, :, :3] = (result[:, :, :3] * gain + bias + noise * mask).clamp(0.0, 1.0) * mask
    return result


def _train(data, indices, *, epochs: int, seed: int, device: torch.device):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = LocalMaskedPatchHead(
        input_channels=int(data["patches"].shape[2]),
        projection_dim=CONFIG["projection_dim"],
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=CONFIG["learning_rate"], weight_decay=CONFIG["weight_decay"],
    )
    index_values = np.asarray(indices, dtype=np.int64)
    patches = torch.from_numpy(data["patches"][index_values]).to(device)
    semantic = torch.from_numpy(data["semantic"][index_values]).to(device)
    complete = torch.from_numpy(data["complete"][index_values]).to(device)
    positive, family_negative, semantic_negative = _pair_sets(index_values, data, local=True)
    negative = np.concatenate((family_negative, semantic_negative), axis=0)
    positive_t = torch.from_numpy(positive).to(device)
    negative_t = torch.from_numpy(negative).to(device)
    final_parts = None
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        outputs = model(_jitter_patches(patches) if epoch else patches)
        loss, parts = masked_glyph_loss(
            outputs, semantic, complete, positive_t, negative_t,
            pair_weight=CONFIG["pair_weight"],
            consistency_weight=CONFIG["consistency_weight"],
            negative_margin=0.30,
        )
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        final_parts = {name: float(value.detach().cpu()) for name, value in parts.items()}
    return model.eval(), final_parts, {
        "positive": len(positive),
        "family_negative": len(family_negative),
        "semantic_negative": len(semantic_negative),
    }


def _predict(model, data, indices, device):
    with torch.inference_mode():
        outputs = model(torch.from_numpy(data["patches"][indices]).to(device))
        semantic = torch.sigmoid(outputs["semantic_logit"])
        complete = torch.sigmoid(outputs["complete_logit"])
        probability = (semantic * complete).cpu().numpy()
        views = outputs["views"].cpu().numpy()
    return probability, views


def _orbit_scores(views: np.ndarray, pairs: np.ndarray) -> np.ndarray:
    if not len(pairs):
        return np.empty((0,), dtype=np.float32)
    return np.einsum(
        "nvd,nwd->nvw", views[pairs[:, 0]], views[pairs[:, 1]],
    ).max(axis=(1, 2))


def _safe_threshold(truth, probability, stress):
    choices = []
    for value in np.unique(probability):
        accepted = probability >= value
        if np.any(accepted & stress):
            continue
        precision = float(truth[accepted].mean()) if accepted.any() else 1.0
        if precision < 0.80:
            continue
        choices.append((
            int(np.count_nonzero(accepted & truth)), precision,
            -int(np.count_nonzero(accepted & ~truth)), float(value),
        ))
    return max(choices)[3] if choices else float(np.nextafter(probability.max(), np.inf))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--baseline-embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=90)
    parser.add_argument("--cycle", type=int, default=726)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(72600)
    torch.set_num_threads(8)
    if device.type == "cuda":
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    data = _load_data(args.bank, args.labels, args.baseline_embeddings, CONFIG["patch_size"])
    np.savez_compressed(
        args.output / "local_patch_bank.npz",
        patches=data["patches"], semantic=data["semantic"], complete=data["complete"],
    )
    indices = np.arange(len(data["patches"]), dtype=np.int64)
    splitter = GroupKFold(n_splits=5)
    oof_probability = np.zeros(len(indices), dtype=np.float64)
    family_scores, family_truths, baseline_scores = [], [], []
    fold_records = []
    for fold, (train, test) in enumerate(splitter.split(indices, groups=data["groups"])):
        model, loss_parts, pair_counts = _train(
            data, train, epochs=args.epochs, seed=72610 + fold, device=device,
        )
        probability, views = _predict(model, data, test, device)
        oof_probability[test] = probability
        positive, family_negative, _ = _pair_sets(test, data, local=True)
        scores = np.concatenate((_orbit_scores(views, positive), _orbit_scores(views, family_negative)))
        truths = np.concatenate((np.ones(len(positive), dtype=bool), np.zeros(len(family_negative), dtype=bool)))
        base_views = data["baseline_views"][test]
        base = np.concatenate((_orbit_scores(base_views, positive), _orbit_scores(base_views, family_negative)))
        family_scores.extend(scores.tolist())
        family_truths.extend(truths.tolist())
        baseline_scores.extend(base.tolist())
        fold_records.append({
            "fold": fold,
            "train_paints": len(set(data["groups"][train])),
            "test_paints": sorted(set(data["groups"][test])),
            "test_positive_pairs": len(positive),
            "test_cross_paint_family_negatives": len(family_negative),
            "training_pair_counts": pair_counts,
            "final_loss": loss_parts,
        })
    truth = data["complete"] == 1
    explicit = data["complete"] >= 0
    family_prevalence = float(np.mean(family_truths))
    family_ap = float(average_precision_score(family_truths, family_scores))
    baseline_family_ap = float(average_precision_score(family_truths, baseline_scores))
    complete_ap = float(average_precision_score(truth, oof_probability))
    explicit_ap = float(average_precision_score(truth[explicit], oof_probability[explicit]))
    threshold = _safe_threshold(truth, oof_probability, data["stress"])
    accepted = oof_probability >= threshold
    precision = float(truth[accepted].mean()) if accepted.any() else 1.0
    recall = float(np.count_nonzero(accepted & truth) / max(1, truth.sum()))
    control_wrong = int(np.count_nonzero(accepted & data["stress"]))
    family_gate = family_ap >= family_prevalence + 0.10 and family_ap > baseline_family_ap
    complete_gate = complete_ap > 0.489735 and precision >= 0.80 and control_wrong == 0

    final_model, final_loss, final_pairs = _train(
        data, indices, epochs=args.epochs, seed=72699, device=device,
    )
    torch.save({
        "schema": "smart-tga-local-masked-patch-head-v1",
        "cycle": args.cycle,
        "config": CONFIG,
        "input_channels": int(data["patches"].shape[2]),
        "state_dict": {key: value.detach().cpu() for key, value in final_model.state_dict().items()},
        "acceptance_threshold": threshold,
        "casts_votes": False,
        "ownership_authority": False,
    }, args.output / "research_head.pt")
    examples = []
    for index, trace in enumerate(data["trace"]):
        examples.append({
            **trace,
            "complete_number": bool(truth[index]),
            "semantic_target": int(data["semantic"][index]),
            "oof_probability": round(float(oof_probability[index]), 7),
            "oof_accepted": bool(accepted[index]),
            "five_control_hard_negative": bool(data["stress"][index]),
        })
    (args.output / "oof_examples.json").write_text(
        json.dumps(examples, indent=2) + "\n", encoding="utf-8",
    )
    targets = sorted(set(data["groups"]) - CONTROL_PAINTS)
    controls = sorted(set(data["groups"]) & CONTROL_PAINTS)
    ledger = {
        "schema": "smart-tga-local-masked-patch-development-v1",
        "cycle": args.cycle,
        "baseline": {
            "same_corpus_complete_number_average_precision": 0.489735,
            "same_folds_frozen_d4_family_average_precision": round(baseline_family_ap, 6),
            "family_prevalence": round(family_prevalence, 6),
        },
        "after_nested_paint_disjoint": {
            "device": str(device),
            "config": CONFIG,
            "paint_count": len(set(data["groups"])),
            "candidate_count": len(indices),
            "complete_number_count": int(truth.sum()),
            "complete_number_average_precision": round(complete_ap, 6),
            "explicit_only_average_precision": round(explicit_ap, 6),
            "family_pair_count": len(family_truths),
            "family_positive_pair_count": int(np.count_nonzero(family_truths)),
            "family_prevalence": round(family_prevalence, 6),
            "true_family_average_precision": round(family_ap, 6),
            "family_ap_gain_over_prevalence": round(family_ap - family_prevalence, 6),
            "family_ap_gain_over_frozen_d4": round(family_ap - baseline_family_ap, 6),
            "acceptance_threshold": round(threshold, 8),
            "accepted_count": int(accepted.sum()),
            "accepted_true_positive_count": int(np.count_nonzero(accepted & truth)),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "five_control_hard_negative_count": int(data["stress"].sum()),
            "five_control_wrong_accepts": control_wrong,
        },
        "gates": {
            "family_ap_gain_required": 0.10,
            "family_gate_passed": family_gate,
            "complete_ap_must_exceed": 0.489735,
            "complete_gate_passed": complete_gate,
            "joint_gate_passed": family_gate and complete_gate,
            "holdout_opened": False,
            "runtime_integrated": False,
        },
        "targets": targets,
        "hard_negative_controls": controls,
        "folds": fold_records,
        "final_training": {"pair_counts": final_pairs, "loss": final_loss},
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "casts_votes": False,
            "ownership_authority": False,
            "output_applied": False,
            "apply_locked": True,
            "filename_or_car_features": False,
            "paint_identity_inference_feature": False,
            "reviewed_bbox_feature": False,
            "exact_reconstruction_affected": False,
        },
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": ledger["baseline"],
        "after": ledger["after_nested_paint_disjoint"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
