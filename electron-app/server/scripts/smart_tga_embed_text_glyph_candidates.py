"""Embed every exact candidate with the locally cached EasyOCR glyph encoder."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import easyocr
import numpy as np
from PIL import Image
import torch

try:
    from engine.spec_sculpt.text_glyph_embeddings import encode_text_glyph_views
    from engine.spec_sculpt.tiled_visual_embeddings import exact_masked_square
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.text_glyph_embeddings import encode_text_glyph_views  # type: ignore
    from engine.spec_sculpt.tiled_visual_embeddings import exact_masked_square  # type: ignore


def _squares(record, size):
    image = np.asarray(Image.open(record["source_1024"]).convert("RGB"))
    exact = np.load(record["exact_candidate_bank"], allow_pickle=False)
    values = []
    for index, bbox in enumerate(exact["bboxes"]):
        offset = int(exact["offsets"][index])
        length = int(exact["lengths"][index])
        height, width = map(int, exact["shapes"][index])
        support = np.unpackbits(exact["packed"][offset:offset + length])
        support = support[:height * width].reshape(height, width).astype(bool)
        values.append(exact_masked_square(image, bbox, support, size=size))
    return exact, values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=112)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(max(1, args.threads))
    reader = easyocr.Reader(["en"], gpu=False, download_enabled=False, verbose=False)
    recognizer = reader.recognizer
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    records = []
    for record in bank["records"]:
        paint_started = time.perf_counter()
        exact, squares = _squares(record, args.size)
        embeddings = encode_text_glyph_views(
            recognizer, squares, batch_size=args.batch_size,
        )
        path = args.output / (Path(record["exact_candidate_bank"]).stem + "_text_glyph.npz")
        np.savez_compressed(
            path, d4_embeddings=embeddings.astype(np.float16),
            embeddings=embeddings.mean(axis=1).astype(np.float16),
            proposal_ids=exact["proposal_ids"], bboxes=exact["bboxes"],
        )
        records.append({
            "paint": record["paint"], "embedding_bank": str(path.resolve()),
            "candidate_count": len(embeddings),
            "embedding_dimensions": embeddings.shape[2],
            "elapsed_sec": round(time.perf_counter() - paint_started, 3),
        })
        print(json.dumps(records[-1]))
    payload = {
        "schema": "smart-tga-easyocr-contextual-glyph-embeddings-v1",
        "cycle": 724,
        "network_access": False,
        "decoded_text_used": False,
        "cached_model_required": True,
        "d4_views_persisted": 8,
        "paint_count": len(records),
        "candidate_count": sum(row["candidate_count"] for row in records),
        "embedding_dimensions": records[0]["embedding_dimensions"] if records else 0,
        "filename_or_car_features": False,
        "ownership_authority": False,
        "records": records,
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "embedding_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({key: payload[key] for key in (
        "paint_count", "candidate_count", "embedding_dimensions", "elapsed_sec",
    )}, indent=2))


if __name__ == "__main__":
    main()
