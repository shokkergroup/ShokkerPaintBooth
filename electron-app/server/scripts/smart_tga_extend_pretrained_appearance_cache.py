"""Extend a frozen D4 masked-appearance cache for exact candidates.

Existing embeddings are preserved byte-for-byte. Only exact candidate traces
missing from the cache are encoded with the same frozen local CLIPSeg vision
tower and neutral-background masking used by Cycle728. Semantic label values
are never read. A review file may supply a trace list, or an untouched holdout
may explicitly request every owner-neutral bank candidate without fabricating
placeholder semantic labels.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np

try:
    from scripts.smart_tga_clip_d4_benchmark import (
        _clip_inputs, _encode_batch, _load_local_clipseg_vision,
    )
    from scripts.smart_tga_exact_candidate_utils import decode_support, normalized_patch
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_clip_d4_benchmark import (  # type: ignore
        _clip_inputs, _encode_batch, _load_local_clipseg_vision,
    )
    from scripts.smart_tga_exact_candidate_utils import (  # type: ignore
        decode_support, normalized_patch,
    )


def _trace_key(paint, candidate_index, proposal_id) -> tuple[str, int, str]:
    return str(paint), int(candidate_index), str(proposal_id)


def _bank_trace_rows(bank: dict) -> list[dict]:
    """Return label-free exact traces in stable bank order."""
    rows = []
    for record in bank["records"]:
        paint = str(record["paint"])
        for index, candidate in enumerate(record["candidates"]):
            rows.append({
                "paint": paint,
                "candidate_index": index,
                "proposal_id": str(candidate["proposal_id"]),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--labels", type=Path)
    source.add_argument(
        "--all-bank-candidates", action="store_true",
        help="encode every exact candidate trace in the bank without labels",
    )
    parser.add_argument("--existing", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--cycle", type=int, default=733)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    records = {str(row["paint"]): row for row in bank["records"]}
    traces = (
        _bank_trace_rows(bank) if args.all_bank_candidates
        else json.loads(args.labels.read_text(encoding="utf-8"))["labels"]
    )
    existing = np.load(args.existing, allow_pickle=False)
    try:
        appearances = [value.copy() for value in existing["appearance"]]
        paints = [str(value) for value in existing["paints"]]
        indices = [int(value) for value in existing["candidate_indices"]]
        proposal_ids = [str(value) for value in existing["proposal_ids"]]
    finally:
        existing.close()
    known = {
        _trace_key(paint, index, proposal)
        for paint, index, proposal in zip(paints, indices, proposal_ids)
    }
    missing = [
        row for row in traces
        if _trace_key(row["paint"], row["candidate_index"], row["proposal_id"])
        not in known
    ]
    model = _load_local_clipseg_vision(args.checkpoint, args.device)
    source_cache: dict[str, np.ndarray] = {}
    exact_cache = {}
    pending: list[np.ndarray] = []
    pending_trace: list[tuple[str, int, str]] = []

    def flush() -> None:
        if not pending:
            return
        encoded = _encode_batch(model, pending, args.device)
        if encoded.shape[0] != 8 * len(pending):
            raise RuntimeError("D4 masked appearance embedding count drift")
        for trace, values in zip(pending_trace, np.split(encoded, len(pending), axis=0)):
            paint, index, proposal = trace
            appearances.append(values.astype(np.float32))
            paints.append(paint)
            indices.append(index)
            proposal_ids.append(proposal)
        pending.clear()
        pending_trace.clear()

    try:
        for row in missing:
            paint, index, proposal = _trace_key(
                row["paint"], row["candidate_index"], row["proposal_id"],
            )
            record = records[paint]
            if paint not in source_cache:
                bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
                if bgr is None:
                    raise FileNotFoundError(record["source_1024"])
                source_cache[paint] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                exact_cache[paint] = np.load(record["exact_candidate_bank"], allow_pickle=False)
            exact = exact_cache[paint]
            if str(exact["proposal_ids"][index]) != proposal:
                raise RuntimeError(f"candidate trace drift: {paint} #{index}")
            x, y, width, height = map(int, exact["bboxes"][index])
            support = decode_support(exact, index)
            rgb = source_cache[paint][y:y + height, x:x + width]
            appearance, _ = _clip_inputs(normalized_patch(rgb, support, 224))
            pending.append(appearance)
            pending_trace.append((paint, index, proposal))
        flush()
    finally:
        for exact in exact_cache.values():
            exact.close()
    np.savez_compressed(
        args.output, appearance=np.stack(appearances).astype(np.float32),
        paints=np.asarray(paints), candidate_indices=np.asarray(indices, dtype=np.int32),
        proposal_ids=np.asarray(proposal_ids),
    )
    manifest = {
        "schema": "smart-tga-frozen-d4-masked-appearance-cache-v2",
        "cycle": args.cycle, "preserved_candidate_count": len(known),
        "newly_encoded_candidate_count": len(missing),
        "candidate_count": len(appearances), "embedding_shape": list(np.stack(appearances).shape),
        "model_weights_frozen": True, "semantic_label_values_consumed": False,
        "trace_list_only": not args.all_bank_candidates,
        "all_bank_candidates_label_free": bool(args.all_bank_candidates),
        "ownership_authority": False,
        "checkpoint": str(args.checkpoint), "device": args.device,
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
