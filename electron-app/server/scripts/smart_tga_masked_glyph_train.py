"""Nested paint-disjoint training for the Smart TGA masked-glyph head."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import time

import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
import torch

try:
    from engine.spec_sculpt.masked_glyph_encoder import MaskedGlyphHead, masked_glyph_loss
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.masked_glyph_encoder import MaskedGlyphHead, masked_glyph_loss  # type: ignore


CONTROL_PAINTS = {
    "dirtlatemodel 350/car_num_1006305.tga",
    "dirtlatemodel 350/car_num_1007631.tga",
    "dirtlatemodel 358/car_num_1008515.tga",
    "dirtlatemodel 358/car_num_1328151.tga",
    "dirtlatemodel 358/car_num_247671.tga",
}

CONFIGS = (
    {"projection_dim": 24, "pair_weight": 0.5, "learning_rate": 0.003},
    {"projection_dim": 32, "pair_weight": 1.0, "learning_rate": 0.003},
    {"projection_dim": 48, "pair_weight": 1.5, "learning_rate": 0.002},
    {"projection_dim": 64, "pair_weight": 2.0, "learning_rate": 0.002},
)

PAIR_SCORE_MODES = (
    "orbit_cosine", "cosine", "min_intrinsic", "product_intrinsic",
    "blend_intrinsic_cosine",
)


def _load_dataset(
    bank_path: Path,
    embedding_path: Path,
    labels_path: Path,
    secondary_embedding_path: Path | None = None,
):
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    embedding_paths = [embedding_path]
    if secondary_embedding_path is not None:
        embedding_paths.append(secondary_embedding_path)
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in embedding_paths]
    labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
    bank_records = {row["paint"]: row for row in bank["records"]}
    embedding_records = [
        {row["paint"]: row for row in manifest["records"]}
        for manifest in manifests
    ]
    cache = {}
    for paint in {row["paint"] for row in labels}:
        view_banks, proposal_ids = [], None
        for records in embedding_records:
            with np.load(records[paint]["embedding_bank"], allow_pickle=False) as values:
                ids = values["proposal_ids"].tolist()
                if proposal_ids is None:
                    proposal_ids = ids
                elif ids != proposal_ids:
                    raise RuntimeError(f"embedding candidate ID drift for {paint}")
                view_banks.append(values["d4_embeddings"].astype(np.float32))
        if len({views.shape[:2] for views in view_banks}) != 1:
            raise RuntimeError(f"embedding D4 shape drift for {paint}")
        cache[paint] = {
            "views": np.concatenate(view_banks, axis=2),
            "ids": proposal_ids,
        }
    views, semantic, complete, groups, blocks, stress = [], [], [], [], [], []
    trace = []
    for row in labels:
        paint, index = row["paint"], int(row["candidate_index"])
        candidate = bank_records[paint]["candidates"][index]
        if cache[paint]["ids"][index] != row["proposal_id"]:
            raise RuntimeError(f"candidate ID drift at {row['review_code']}")
        if row["semantic"] == "uncertain":
            semantic_target = complete_target = -1
        else:
            semantic_target = int(row["semantic"] == "Number")
            complete_target = int(row["semantic"] == "Number" and row.get("complete_copy") is True)
        views.append(cache[paint]["views"][index])
        semantic.append(semantic_target)
        complete.append(complete_target)
        groups.append(paint)
        blocks.append(candidate["dominant_number_block"])
        stress.append(paint in CONTROL_PAINTS and complete_target != 1)
        trace.append({
            "review_code": row["review_code"], "paint": paint,
            "candidate_index": index, "proposal_id": row["proposal_id"],
        })
    return {
        "views": np.asarray(views, dtype=np.float32),
        "semantic": np.asarray(semantic, dtype=np.int64),
        "complete": np.asarray(complete, dtype=np.int64),
        "groups": np.asarray(groups),
        "blocks": np.asarray(blocks),
        "stress": np.asarray(stress, dtype=bool),
        "trace": trace,
    }


def _pairs(indices, data, *, local=False):
    indices = np.asarray(indices, dtype=np.int64)
    remap = {int(value): offset for offset, value in enumerate(indices)}
    positive, negative = [], []
    grouped = defaultdict(list)
    for index in indices:
        grouped[data["groups"][index]].append(int(index))
    for paint_indices in grouped.values():
        for offset, first in enumerate(paint_indices):
            first_semantic = data["semantic"][first]
            if first_semantic < 0:
                continue
            for second in paint_indices[offset + 1:]:
                second_semantic = data["semantic"][second]
                if second_semantic < 0 or data["blocks"][first] == data["blocks"][second]:
                    continue
                if first_semantic == 1 and second_semantic == 1:
                    destination = positive
                elif first_semantic == 1 or second_semantic == 1:
                    destination = negative
                else:
                    continue
                destination.append([
                    remap[first] if local else first,
                    remap[second] if local else second,
                ])
    # A true family representation must distinguish two valid race numbers
    # from different paints.  Without these cross-paint Number/Number
    # negatives, the pair metric can be gamed by generic Number confidence and
    # does not measure decal-family identity at all.  Paint identity is used
    # only to construct supervision here; it is never an inference feature.
    number_indices = [int(index) for index in indices if data["semantic"][index] == 1]
    for offset, first in enumerate(number_indices):
        for second in number_indices[offset + 1:]:
            if data["groups"][first] == data["groups"][second]:
                continue
            negative.append([
                remap[first] if local else first,
                remap[second] if local else second,
            ])
    return np.asarray(positive, dtype=np.int64).reshape(-1, 2), np.asarray(negative, dtype=np.int64).reshape(-1, 2)


def _train(data, indices, config, seed, epochs):
    torch.manual_seed(seed)
    np.random.seed(seed)
    input_dim = int(data["views"].shape[2])
    head = MaskedGlyphHead(input_dim, config["projection_dim"])
    optimizer = torch.optim.AdamW(
        head.parameters(), lr=config["learning_rate"], weight_decay=0.002,
    )
    index_values = np.asarray(indices, dtype=np.int64)
    views = torch.from_numpy(data["views"][index_values])
    semantic = torch.from_numpy(data["semantic"][index_values])
    complete = torch.from_numpy(data["complete"][index_values])
    positive, negative = _pairs(index_values, data, local=True)
    positive = torch.from_numpy(positive)
    negative = torch.from_numpy(negative)
    head.train()
    final_parts = None
    for epoch in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        # Tiny feature jitter prevents memorizing exact cached vectors while all
        # eight D4 views remain explicit training observations.
        jittered = views + torch.randn_like(views) * 0.006 if epoch else views
        outputs = head(jittered)
        loss, parts = masked_glyph_loss(
            outputs, semantic, complete, positive, negative,
            pair_weight=config["pair_weight"], consistency_weight=0.10,
        )
        loss.backward()
        torch.nn.utils.clip_grad_norm_(head.parameters(), 5.0)
        optimizer.step()
        final_parts = {name: float(value.detach()) for name, value in parts.items()}
    return head.eval(), final_parts, {"positive": len(positive), "negative": len(negative)}


def _predict(head, data, indices):
    with torch.inference_mode():
        output = head(torch.from_numpy(data["views"][indices]))
        semantic = torch.sigmoid(output["semantic_logit"])
        complete = torch.sigmoid(output["complete_logit"])
        probability = (semantic * complete).cpu().numpy()
        pooled = output["pooled"].cpu().numpy()
        projected_views = output["views"].cpu().numpy()
    return probability, pooled, projected_views


def _pair_scores(
    indices, pooled, data, probability=None, projected_views=None, *, mode="cosine",
):
    positive, negative = _pairs(indices, data, local=True)
    scores, labels = [], []
    for pairs, value in ((positive, True), (negative, False)):
        if len(pairs):
            cosine = np.sum(pooled[pairs[:, 0]] * pooled[pairs[:, 1]], axis=1)
            if mode == "orbit_cosine":
                if projected_views is None:
                    raise ValueError("orbit_cosine requires projected D4 views")
                pair_score = np.einsum(
                    "nvd,nwd->nvw",
                    projected_views[pairs[:, 0]],
                    projected_views[pairs[:, 1]],
                ).max(axis=(1, 2))
            elif mode == "cosine":
                pair_score = cosine
            else:
                if probability is None:
                    raise ValueError(f"{mode} requires intrinsic candidate probabilities")
                first = probability[pairs[:, 0]]
                second = probability[pairs[:, 1]]
                if mode == "min_intrinsic":
                    pair_score = np.minimum(first, second)
                elif mode == "product_intrinsic":
                    pair_score = first * second
                elif mode == "blend_intrinsic_cosine":
                    pair_score = 0.70 * np.minimum(first, second) + 0.30 * ((cosine + 1.0) * 0.5)
                else:
                    raise ValueError(f"unknown pair score mode: {mode}")
            scores.extend(pair_score.tolist())
            labels.extend([value] * len(pairs))
    return scores, labels


def _evaluate_config(data, indices, config, seed, epochs):
    index_values = np.asarray(indices, dtype=np.int64)
    groups = data["groups"][index_values]
    splitter = GroupKFold(n_splits=min(3, len(set(groups))))
    probabilities, truths, pair_truths = [], [], []
    pair_scores_by_mode = {mode: [] for mode in PAIR_SCORE_MODES}
    for fold, (train_local, test_local) in enumerate(splitter.split(index_values, groups=groups)):
        train = index_values[train_local]
        test = index_values[test_local]
        head, _, _ = _train(data, train, config, seed + fold, epochs)
        predicted, pooled, projected_views = _predict(head, data, test)
        probabilities.extend(predicted.tolist())
        truths.extend((data["complete"][test] == 1).tolist())
        fold_pair_truths = None
        for mode in PAIR_SCORE_MODES:
            scores, labels = _pair_scores(
                test, pooled, data, predicted, projected_views, mode=mode,
            )
            pair_scores_by_mode[mode].extend(scores)
            if fold_pair_truths is None:
                pair_truths.extend(labels)
                fold_pair_truths = labels
            elif labels != fold_pair_truths:
                raise RuntimeError("pair truth order drift across score modes")
    candidate_ap = float(average_precision_score(truths, probabilities))
    pair_prevalence = float(np.mean(pair_truths)) if pair_truths else 0.0
    mode_metrics = {}
    for mode, pair_scores in pair_scores_by_mode.items():
        mode_metrics[mode] = float(average_precision_score(pair_truths, pair_scores)) if pair_truths else 0.0
    selected_pair_score_mode, pair_ap = max(
        mode_metrics.items(), key=lambda item: (item[1] - pair_prevalence, item[1], item[0]),
    )
    objective = candidate_ap + max(0.0, pair_ap - pair_prevalence)
    return {
        "objective": objective, "candidate_ap": candidate_ap,
        "pair_ap": pair_ap, "pair_prevalence": pair_prevalence,
        "selected_pair_score_mode": selected_pair_score_mode,
        "pair_ap_by_mode": mode_metrics,
    }


def _threshold(truth, probability, stress):
    choices = []
    for value in np.unique(probability):
        accepted = probability >= value
        if np.any(accepted & stress):
            continue
        precision = float(truth[accepted].mean()) if accepted.any() else 1.0
        if precision < 0.80:
            continue
        true_positive = int(np.count_nonzero(accepted & truth))
        false_positive = int(np.count_nonzero(accepted & ~truth))
        choices.append((true_positive, precision, -false_positive, float(value)))
    return max(choices)[3] if choices else float(np.nextafter(probability.max(), np.inf))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--secondary-embeddings", type=Path)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=724)
    parser.add_argument("--inner-epochs", type=int, default=90)
    parser.add_argument("--outer-epochs", type=int, default=140)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(8)
    torch.use_deterministic_algorithms(True)
    data = _load_dataset(
        args.bank, args.embeddings, args.labels, args.secondary_embeddings,
    )
    count = len(data["views"])
    indices = np.arange(count)
    outer = GroupKFold(n_splits=5)
    oof_probability = np.zeros(count, dtype=np.float64)
    oof_pair_scores, oof_pair_truths = [], []
    selected, selected_pair_modes, fold_records = [], [], []
    for fold, (train, test) in enumerate(outer.split(indices, groups=data["groups"])):
        choices = []
        for config_index, config in enumerate(CONFIGS):
            metrics = _evaluate_config(
                data, train, config, 72300 + fold * 100 + config_index * 10,
                args.inner_epochs,
            )
            choices.append((metrics["objective"], metrics["candidate_ap"],
                            metrics["pair_ap"] - metrics["pair_prevalence"],
                            -config["projection_dim"], config_index, metrics))
        _, _, _, _, config_index, inner_metrics = max(choices)
        config = CONFIGS[config_index]
        selected.append(config_index)
        pair_score_mode = inner_metrics["selected_pair_score_mode"]
        selected_pair_modes.append(pair_score_mode)
        head, final_loss, pair_counts = _train(
            data, train, config, 72400 + fold, args.outer_epochs,
        )
        probability, pooled, projected_views = _predict(head, data, test)
        oof_probability[test] = probability
        scores, labels = _pair_scores(
            test, pooled, data, probability, projected_views, mode=pair_score_mode,
        )
        oof_pair_scores.extend(scores)
        oof_pair_truths.extend(labels)
        fold_records.append({
            "fold": fold, "train_paints": len(set(data["groups"][train])),
            "test_paints": sorted(set(data["groups"][test])),
            "selected_config": config, "inner_metrics": inner_metrics,
            "selected_pair_score_mode": pair_score_mode,
            "training_pair_counts": pair_counts, "final_loss": final_loss,
        })

    truth = data["complete"] == 1
    comparable_ap = float(average_precision_score(truth, oof_probability))
    explicit = data["complete"] >= 0
    explicit_ap = float(average_precision_score(truth[explicit], oof_probability[explicit]))
    pair_prevalence = float(np.mean(oof_pair_truths))
    pair_ap = float(average_precision_score(oof_pair_truths, oof_pair_scores))
    threshold = _threshold(truth, oof_probability, data["stress"])
    accepted = oof_probability >= threshold
    precision = float(truth[accepted].mean()) if accepted.any() else 1.0
    recall = float(np.count_nonzero(accepted & truth) / max(1, truth.sum()))
    control_wrong = int(np.count_nonzero(accepted & data["stress"]))
    development_gate = (
        pair_ap >= pair_prevalence + 0.10
        and comparable_ap > 0.527382
        and precision >= 0.80
        and control_wrong == 0
    )

    final_config_index = Counter(selected).most_common(1)[0][0]
    final_config = CONFIGS[final_config_index]
    final_pair_score_mode = Counter(selected_pair_modes).most_common(1)[0][0]
    final_head, final_loss, pair_counts = _train(
        data, indices, final_config, 72500, args.outer_epochs,
    )
    torch.save({
        "schema": "smart-tga-masked-glyph-head-v1", "cycle": args.cycle,
        "config": final_config, "input_dim": int(data["views"].shape[2]),
        "pair_score_mode": final_pair_score_mode,
        "state_dict": final_head.state_dict(),
        "acceptance_threshold": threshold,
        "ownership_authority": False, "casts_votes": False,
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
    ledger = {
        "schema": "smart-tga-masked-glyph-development-v1",
        "cycle": args.cycle,
        "baseline": {
            "legacy_complete_number_average_precision": 0.527382,
            "cycle724_text_complete_number_average_precision": 0.235528,
            "cycle724_text_pair_average_precision": 0.659840,
            "cycle724_text_pair_prevalence": 0.605263,
            "locked_holdout_recall": "5/16",
            "locked_holdout_precision": 0.75,
        },
        "embedding_sources": [
            str(path) for path in (args.embeddings, args.secondary_embeddings) if path is not None
        ],
        "after_nested_paint_disjoint": {
            "paint_count": len(set(data["groups"])),
            "candidate_count": count,
            "complete_number_count": int(truth.sum()),
            "complete_number_average_precision_comparable": round(comparable_ap, 6),
            "complete_number_average_precision_explicit_only": round(explicit_ap, 6),
            "pair_count": len(oof_pair_truths),
            "pair_definition": "same-paint cross-copy Number positives vs within-paint Number/non-Number and cross-paint Number/Number family negatives",
            "positive_pair_count": int(np.count_nonzero(oof_pair_truths)),
            "pair_prevalence": round(pair_prevalence, 6),
            "pair_average_precision": round(pair_ap, 6),
            "pair_ap_gain_over_prevalence": round(pair_ap - pair_prevalence, 6),
            "acceptance_threshold": round(threshold, 8),
            "accepted_count": int(accepted.sum()),
            "accepted_true_positive_count": int(np.count_nonzero(accepted & truth)),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "five_control_hard_negative_count": int(data["stress"].sum()),
            "five_control_wrong_accepts": control_wrong,
            "outer_selected_config_counts": dict(Counter(map(str, selected))),
            "outer_selected_pair_score_mode_counts": dict(Counter(selected_pair_modes)),
            "final_research_config": final_config,
            "final_pair_score_mode": final_pair_score_mode,
        },
        "development_gate": {
            "pair_ap_gain_required": 0.10,
            "complete_ap_must_exceed": 0.527382,
            "precision_required": 0.80,
            "control_wrong_accepts_required": 0,
            "passed": development_gate,
            "holdout_opened": False,
            "runtime_integrated": False,
        },
        "folds": fold_records,
        "final_training": {"pair_counts": pair_counts, "loss": final_loss},
        "safety": {
            "casts_votes": False, "ownership_authority": False,
            "output_applied": False, "apply_locked": True,
            "filename_or_car_features": False,
            "paint_identity_inference_feature": False,
            "reviewed_bbox_feature": False,
            "exact_reconstruction_affected": False,
        },
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "after": ledger["after_nested_paint_disjoint"],
        "gate": ledger["development_gate"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
