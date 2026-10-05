"""Compute reusable D4 EfficientNet embeddings from an exact candidate bank."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import torch

try:
    from engine.spec_sculpt.tiled_visual_embeddings import (
        embed_d4_candidates,
        embed_d4_candidate_views,
        exact_masked_square,
        load_efficientnet_encoder,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.tiled_visual_embeddings import (  # type: ignore
        embed_d4_candidates,
        embed_d4_candidate_views,
        exact_masked_square,
        load_efficientnet_encoder,
    )


def _decode_all(record, image, size):
    exact = np.load(record["exact_candidate_bank"], allow_pickle=False)
    squares = []
    for index, bbox in enumerate(exact["bboxes"]):
        offset = int(exact["offsets"][index])
        length = int(exact["lengths"][index])
        height, width = map(int, exact["shapes"][index])
        support = np.unpackbits(exact["packed"][offset:offset + length])
        support = support[:height * width].reshape(height, width).astype(bool)
        squares.append(exact_masked_square(image, bbox, support, size=size))
    return exact, squares


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=112)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--persist-views", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(max(1, args.threads))
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    encoder = load_efficientnet_encoder(args.weights)
    records = []
    for record in bank["records"]:
        paint_started = time.perf_counter()
        image = np.asarray(Image.open(record["source_1024"]).convert("RGB"))
        exact, squares = _decode_all(record, image, args.size)
        if args.persist_views:
            d4_embeddings = embed_d4_candidate_views(
                encoder, squares, batch_size=args.batch_size,
            )
            embeddings = d4_embeddings.mean(axis=1)
            embeddings /= np.maximum(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-8)
        else:
            d4_embeddings = None
            embeddings = embed_d4_candidates(encoder, squares, batch_size=args.batch_size)
        path = args.output / (Path(record["exact_candidate_bank"]).stem + "_efficientnet.npz")
        arrays = {
            "embeddings": embeddings.astype(np.float16),
            "proposal_ids": exact["proposal_ids"],
            "bboxes": exact["bboxes"],
        }
        if d4_embeddings is not None:
            arrays["d4_embeddings"] = d4_embeddings.astype(np.float16)
        np.savez_compressed(path, **arrays)
        records.append({
            "paint": record["paint"],
            "embedding_bank": str(path.resolve()),
            "candidate_count": len(embeddings),
            "embedding_dimensions": embeddings.shape[1],
            "elapsed_sec": round(time.perf_counter() - paint_started, 3),
        })
        print(json.dumps(records[-1]))
    payload = {
        "schema": "smart-tga-d4-efficientnet-candidate-embeddings-v1",
        "cycle": 723,
        "weights": str(args.weights.resolve()),
        "network_access": False,
        "d4_views_averaged": 8,
        "d4_views_persisted": bool(args.persist_views),
        "input_size": args.size,
        "paint_count": len(records),
        "candidate_count": sum(row["candidate_count"] for row in records),
        "embedding_dimensions": records[0]["embedding_dimensions"] if records else 0,
        "filename_or_car_features": False,
        "ownership_authority": False,
        "records": records,
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "embedding_manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "paint_count": payload["paint_count"],
        "candidate_count": payload["candidate_count"],
        "embedding_dimensions": payload["embedding_dimensions"],
        "elapsed_sec": payload["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
