"""Select diverse exact candidates by real masked-glyph model uncertainty."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
import torch

try:
    from engine.spec_sculpt.masked_glyph_encoder import MaskedGlyphHead
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.masked_glyph_encoder import MaskedGlyphHead  # type: ignore


def _load_head(path):
    payload = torch.load(path, map_location="cpu", weights_only=False)
    head = MaskedGlyphHead(payload["input_dim"], payload["config"]["projection_dim"])
    head.load_state_dict(payload["state_dict"])
    return head.eval()


def _predict(head, views):
    with torch.inference_mode():
        output = head(torch.from_numpy(views.astype(np.float32)))
        semantic = torch.sigmoid(output["semantic_logit"]).numpy()
        complete = torch.sigmoid(output["complete_logit"]).numpy()
        pooled = output["pooled"].numpy()
    return semantic, complete, pooled


def _entropy(probability):
    value = np.clip(probability, 1e-6, 1.0 - 1e-6)
    return -(value * np.log2(value) + (1.0 - value) * np.log2(1.0 - value))


def _family_support(pooled, candidates):
    similarity = pooled @ pooled.T
    values = np.zeros(len(candidates), dtype=np.float32)
    for index, candidate in enumerate(candidates):
        peers = [
            peer for peer in range(len(candidates))
            if peer != index and candidates[peer]["dominant_number_block"] != candidate["dominant_number_block"]
        ]
        values[index] = float(similarity[index, peers].max()) if peers else 0.0
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--image-embeddings", type=Path, required=True)
    parser.add_argument("--text-embeddings", type=Path, required=True)
    parser.add_argument("--image-head", type=Path, required=True)
    parser.add_argument("--text-head", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=96)
    parser.add_argument("--per-paint", type=int, default=5)
    args = parser.parse_args()
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    image_manifest = json.loads(args.image_embeddings.read_text(encoding="utf-8"))
    text_manifest = json.loads(args.text_embeddings.read_text(encoding="utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8"))["labels"]
    image_records = {row["paint"]: row for row in image_manifest["records"]}
    text_records = {row["paint"]: row for row in text_manifest["records"]}
    reviewed = {(row["paint"], row["proposal_id"]) for row in labels}
    positive_pair_paints = set()
    number_blocks = defaultdict(set)
    for row in labels:
        if row["semantic"] == "Number":
            number_blocks[row["paint"]].add(row["candidate_index"])
    for paint, indices in number_blocks.items():
        if len(indices) >= 2:
            positive_pair_paints.add(paint)
    image_head, text_head = _load_head(args.image_head), _load_head(args.text_head)
    rows = []
    for record in bank["records"]:
        paint, candidates = record["paint"], record["candidates"]
        with np.load(image_records[paint]["embedding_bank"], allow_pickle=False) as values:
            image_views = values["d4_embeddings"].astype(np.float32)
            image_ids = values["proposal_ids"].tolist()
        with np.load(text_records[paint]["embedding_bank"], allow_pickle=False) as values:
            text_views = values["d4_embeddings"].astype(np.float32)
            text_ids = values["proposal_ids"].tolist()
        expected = [candidate["proposal_id"] for candidate in candidates]
        if image_ids != expected or text_ids != expected:
            raise RuntimeError(f"candidate ID drift for {paint}")
        image_semantic, image_complete, _ = _predict(image_head, image_views)
        text_semantic, text_complete, text_pooled = _predict(text_head, text_views)
        support = _family_support(text_pooled, candidates)
        for index, candidate in enumerate(candidates):
            if (paint, candidate["proposal_id"]) in reviewed:
                continue
            image_accept = image_semantic[index] * image_complete[index]
            text_accept = text_semantic[index] * text_complete[index]
            entropy = float((_entropy(image_semantic[index]) + _entropy(image_complete[index])
                             + _entropy(text_semantic[index]) + _entropy(text_complete[index])) / 4.0)
            disagreement = float(abs(image_accept - text_accept))
            family = float(support[index])
            sparse_bonus = 1.0 if paint not in positive_pair_paints else 0.0
            priority = 0.45 * entropy + 0.25 * disagreement + 0.20 * family + 0.10 * sparse_bonus
            semantics = []
            if max(image_semantic[index], text_semantic[index]) >= 0.55:
                semantics.append("Number")
            if min(image_semantic[index], text_semantic[index]) <= 0.45:
                semantics.append("Sponsor")
            if not semantics:
                semantics.append("uncertain")
            rows.append({
                "paint": paint, "candidate_index": index,
                "proposal_id": candidate["proposal_id"], "bbox": candidate["bbox"],
                "dominant_number_block": candidate["dominant_number_block"],
                "palette_role": candidate["palette_role"],
                "suggested_semantics": semantics,
                "image_semantic": round(float(image_semantic[index]), 7),
                "image_complete": round(float(image_complete[index]), 7),
                "text_semantic": round(float(text_semantic[index]), 7),
                "text_complete": round(float(text_complete[index]), 7),
                "text_family_support": round(family, 7),
                "entropy": round(entropy, 7), "disagreement": round(disagreement, 7),
                "priority": round(priority, 7),
                "missing_positive_pair_paint": bool(sparse_bonus),
                "ownership_authority": False,
            })
    chosen, chosen_keys = [], set()
    by_paint = defaultdict(list)
    for row in rows:
        by_paint[row["paint"]].append(row)
    for paint in sorted(by_paint):
        candidates = sorted(by_paint[paint], key=lambda row: -row["priority"])
        diversity = set()
        for row in candidates:
            key = (row["dominant_number_block"], row["palette_role"])
            if key in diversity:
                continue
            chosen.append(row); chosen_keys.add((paint, row["proposal_id"])); diversity.add(key)
            if len([value for value in chosen if value["paint"] == paint]) >= args.per_paint:
                break
        for row in candidates:
            if len([value for value in chosen if value["paint"] == paint]) >= args.per_paint:
                break
            key = (paint, row["proposal_id"])
            if key not in chosen_keys:
                chosen.append(row); chosen_keys.add(key)
    for row in sorted(rows, key=lambda value: -value["priority"]):
        if len(chosen) >= args.count:
            break
        key = (row["paint"], row["proposal_id"])
        if key not in chosen_keys:
            chosen.append(row); chosen_keys.add(key)
    chosen = sorted(chosen[:args.count], key=lambda row: (row["paint"], -row["priority"]))
    for index, row in enumerate(chosen):
        row["review_code"] = f"A{index:03d}"
    payload = {
        "schema": "smart-tga-masked-glyph-active-review-queue-v1",
        "cycle": 725, "selection_method": "real model entropy + scorer disagreement + text-family support + block/palette diversity",
        "candidate_count_before_exclusion": len(rows),
        "excluded_existing_label_count": len(reviewed),
        "selected_count": len(chosen),
        "paint_counts": dict(Counter(row["paint"] for row in chosen)),
        "casts_votes": False, "ownership_authority": False,
        "labels": chosen,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "unlabeled_candidates": len(rows), "selected": len(chosen),
        "paints": len(payload["paint_counts"]),
        "sparse_pair_paints_selected": len({row["paint"] for row in chosen if row["missing_positive_pair_paint"]}),
    }, indent=2))


if __name__ == "__main__":
    main()
