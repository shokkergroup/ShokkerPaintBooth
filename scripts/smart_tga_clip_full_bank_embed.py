"""Encode every existing exact Smart TGA candidate with frozen D4 CLIP vision.

This is an owner-neutral research cache.  It preserves paint/candidate trace but
does not consume semantic labels, cast ownership votes, or alter runtime output.
The full-bank cache lets downstream rankers normalize evidence against the real
within-paint proposal cohort instead of the much smaller reviewed subset.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np

try:
    from scripts.smart_tga_exact_candidate_utils import decode_support, normalized_patch
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import (  # type: ignore
        decode_support,
        normalized_patch,
    )


def _bank_rows(bank: dict) -> list[dict]:
    """Return a stable trace row for every candidate in bank order."""
    rows: list[dict] = []
    for record in bank["records"]:
        paint = str(record["paint"])
        for index, candidate in enumerate(record["candidates"]):
            rows.append({
                "paint": paint,
                "candidate_index": index,
                "proposal_id": str(candidate["proposal_id"]),
                "dominant_number_block": str(candidate["dominant_number_block"]),
                "palette_role": str(candidate["palette_role"]),
            })
    return rows


def _flush(
    model, pending: list[np.ndarray], rows: list[np.ndarray], device: str, encode_batch,
) -> None:
    if not pending:
        return
    values = encode_batch(model, pending, device)
    if values.shape[0] != 8 * len(pending):
        raise RuntimeError("D4 batch embedding count drift")
    rows.extend(np.split(values, len(pending), axis=0))
    pending.clear()


def main() -> None:
    try:
        from scripts.smart_tga_clip_d4_benchmark import (
            _encode_batch, _load_local_clipseg_vision,
        )
    except ModuleNotFoundError:
        from smart_tga_clip_d4_benchmark import (  # type: ignore
            _encode_batch, _load_local_clipseg_vision,
        )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-candidates", type=int, default=16)
    parser.add_argument("--cycle", type=int, default=730)
    args = parser.parse_args()
    if args.batch_candidates < 1:
        raise ValueError("batch-candidates must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    records = {str(row["paint"]): row for row in bank["records"]}
    trace = _bank_rows(bank)
    model = _load_local_clipseg_vision(args.checkpoint, args.device)
    source_cache: dict[str, np.ndarray] = {}
    exact_cache = {}
    pending: list[np.ndarray] = []
    embeddings: list[np.ndarray] = []
    try:
        for offset, row in enumerate(trace):
            paint = row["paint"]
            record = records[paint]
            if paint not in source_cache:
                bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
                if bgr is None:
                    raise FileNotFoundError(record["source_1024"])
                source_cache[paint] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                exact_cache[paint] = np.load(
                    record["exact_candidate_bank"], allow_pickle=False,
                )
            exact = exact_cache[paint]
            index = int(row["candidate_index"])
            if str(exact["proposal_ids"][index]) != row["proposal_id"]:
                raise RuntimeError(f"candidate trace drift: {paint} #{index}")
            x, y, width, height = map(int, exact["bboxes"][index])
            support = decode_support(exact, index)
            rgb = source_cache[paint][y:y + height, x:x + width]
            patches = normalized_patch(rgb, support, 224)
            silhouette = np.repeat(np.clip(patches[:, 3:4], 0.0, 1.0), 3, axis=1)
            pending.append(silhouette)
            if len(pending) >= args.batch_candidates:
                _flush(model, pending, embeddings, args.device, _encode_batch)
            if (offset + 1) % 96 == 0 or offset + 1 == len(trace):
                print(f"encoded {offset + 1}/{len(trace)} candidates", flush=True)
        _flush(model, pending, embeddings, args.device, _encode_batch)
    finally:
        for exact in exact_cache.values():
            exact.close()
    values = np.stack(embeddings).astype(np.float32)
    if values.shape[:2] != (len(trace), 8):
        raise RuntimeError(f"full-bank embedding shape drift: {values.shape}")
    np.savez_compressed(
        args.output,
        silhouette=values,
        paints=np.asarray([row["paint"] for row in trace]),
        candidate_indices=np.asarray(
            [row["candidate_index"] for row in trace], dtype=np.int64,
        ),
        proposal_ids=np.asarray([row["proposal_id"] for row in trace]),
        blocks=np.asarray([row["dominant_number_block"] for row in trace]),
        palette_roles=np.asarray([row["palette_role"] for row in trace]),
    )
    print(json.dumps({
        "schema": "smart-tga-full-bank-frozen-d4-silhouette-v1",
        "cycle": args.cycle,
        "candidate_count": len(trace),
        "paint_count": len(records),
        "embedding_shape": list(values.shape),
        "device": args.device,
        "checkpoint": str(args.checkpoint),
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "semantic_labels_consumed": False,
        "ownership_authority": False,
    }, indent=2))


if __name__ == "__main__":
    main()
