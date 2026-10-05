"""Build label-free CLIPSeg semantic support/ring evidence for Smart TGA.

The frozen local CLIPSeg decoder is prompted with universal racing concepts on
all D4 views of each 1024 atlas. Heatmaps are inverse-mapped before exact
candidate support and immediate-ring statistics are measured. No filename,
car identity, bbox coordinate, template block or review outcome is a feature.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np

try:
    from scripts.smart_tga_exact_candidate_utils import decode_support
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_exact_candidate_utils import decode_support  # type: ignore


PROMPTS = {
    "number": (
        "a race car number made of digits",
        "large outlined racing number digits",
        "part of a race car number digit",
    ),
    "sponsor": (
        "a sponsor logo on a race car",
        "advertising text and a company logo",
        "a motorsports brand decal",
    ),
    "paint": (
        "abstract race car livery paint",
        "painted racing stripes and swooshes",
        "decorative colored body graphics",
    ),
    "template": (
        "a car body template seam or hardware",
        "vehicle body panel edge and opening",
        "car template wire and mechanical detail",
    ),
}
REDUCERS = ("d4_mean", "d4_max")
STATISTICS = ("support_mean", "support_q75", "support_q90", "support_max", "ring_mean", "support_ring_delta")
FEATURE_NAMES = tuple(
    f"{category}_{reducer}_{statistic}"
    for category in PROMPTS for reducer in REDUCERS for statistic in STATISTICS
) + tuple(
    f"number_nonnumber_{reducer}_{statistic}_margin"
    for reducer in REDUCERS
    for statistic in ("support_mean", "support_q90", "support_max", "support_ring_delta")
)


def _d4_views(rgb: np.ndarray) -> list[tuple[np.ndarray, int, bool]]:
    views = []
    for turns in range(4):
        rotated = np.rot90(rgb, turns).copy()
        views.append((rotated, turns, False))
        views.append((np.fliplr(rotated).copy(), turns, True))
    return views


def _undo_d4(values: np.ndarray, turns: int, reflected: bool) -> np.ndarray:
    restored = np.fliplr(values) if reflected else values
    return np.rot90(restored, -turns).copy()


def _semantic_maps(model, processor, rgb: np.ndarray, device: str) -> dict:
    import torch
    from PIL import Image

    prompt_rows = [
        (category, prompt) for category, prompts in PROMPTS.items() for prompt in prompts
    ]
    by_category = {category: [] for category in PROMPTS}
    for view, turns, reflected in _d4_views(rgb):
        image = Image.fromarray(view)
        inputs = processor(
            text=[prompt for _, prompt in prompt_rows],
            images=[image] * len(prompt_rows),
            padding=True, return_tensors="pt",
        )
        inputs = {name: value.to(device) for name, value in inputs.items()}
        with torch.inference_mode():
            if device.startswith("cuda"):
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    logits = model(**inputs).logits
            else:
                logits = model(**inputs).logits
        probabilities = torch.sigmoid(logits.float()).cpu().numpy()
        for offset, (category, _) in enumerate(prompt_rows):
            restored = _undo_d4(probabilities[offset], turns, reflected)
            by_category[category].append(cv2.resize(
                restored, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR,
            ))
    result = {}
    for category, values in by_category.items():
        stack = np.stack(values).astype(np.float32)
        result[(category, "d4_mean")] = stack.mean(axis=0)
        result[(category, "d4_max")] = stack.max(axis=0)
    return result


def _support_ring_statistics(
    heatmap: np.ndarray, bbox: list[int], support: np.ndarray,
) -> np.ndarray:
    x, y, width, height = map(int, bbox)
    pad = 4
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1 = min(heatmap.shape[1], x + width + pad)
    y1 = min(heatmap.shape[0], y + height + pad)
    local = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    oy, ox = y - y0, x - x0
    local[oy:oy + height, ox:ox + width] = support.astype(np.uint8)
    ring = cv2.dilate(local, np.ones((9, 9), dtype=np.uint8), iterations=1).astype(bool)
    ring &= ~local.astype(bool)
    values = heatmap[y0:y1, x0:x1][local.astype(bool)]
    ring_values = heatmap[y0:y1, x0:x1][ring]
    if not len(values):
        raise ValueError("candidate support must be non-empty")
    ring_mean = float(ring_values.mean()) if len(ring_values) else float(values.mean())
    return np.asarray((
        values.mean(), np.quantile(values, 0.75), np.quantile(values, 0.90),
        values.max(), ring_mean, values.mean() - ring_mean,
    ), dtype=np.float32)


def semantic_feature_vector(
    maps: dict, bbox: list[int], support: np.ndarray,
) -> np.ndarray:
    stats = {}
    values = []
    for category in PROMPTS:
        for reducer in REDUCERS:
            current = _support_ring_statistics(maps[(category, reducer)], bbox, support)
            stats[(category, reducer)] = current
            values.extend(current)
    for reducer in REDUCERS:
        nonnumber = np.max(np.stack([
            stats[(category, reducer)] for category in ("sponsor", "paint", "template")
        ]), axis=0)
        number = stats[("number", reducer)]
        for offset in (0, 2, 3, 5):
            values.append(float(number[offset] - nonnumber[offset]))
    result = np.asarray(values, dtype=np.float32)
    if result.shape != (len(FEATURE_NAMES),) or not np.all(np.isfinite(result)):
        raise RuntimeError("semantic mask feature schema drift")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--maximum-paints", type=int)
    parser.add_argument("--cycle", type=int, default=735)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor

    processor = CLIPSegProcessor.from_pretrained(
        args.checkpoint, local_files_only=True, use_fast=False,
    )
    model = CLIPSegForImageSegmentation.from_pretrained(
        args.checkpoint, local_files_only=True,
    ).eval().to(args.device)
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    records = bank["records"][:args.maximum_paints]
    features = []
    paints = []
    indices = []
    proposals = []
    for paint_offset, record in enumerate(records):
        bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(record["source_1024"])
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        maps = _semantic_maps(model, processor, rgb, args.device)
        exact = np.load(record["exact_candidate_bank"], allow_pickle=False)
        try:
            for index, candidate in enumerate(record["candidates"]):
                proposal = str(candidate["proposal_id"])
                if str(exact["proposal_ids"][index]) != proposal:
                    raise RuntimeError(f"candidate trace drift: {record['paint']} #{index}")
                support = decode_support(exact, index)
                features.append(semantic_feature_vector(
                    maps, list(candidate["bbox"]), support,
                ))
                paints.append(str(record["paint"]))
                indices.append(index)
                proposals.append(proposal)
        finally:
            exact.close()
        print(f"encoded semantic maps {paint_offset + 1}/{len(records)} paints")
    matrix = np.stack(features).astype(np.float32)
    np.savez_compressed(
        args.output, features=matrix, feature_names=np.asarray(FEATURE_NAMES),
        paints=np.asarray(paints), candidate_indices=np.asarray(indices, dtype=np.int32),
        proposal_ids=np.asarray(proposals),
    )
    manifest = {
        "schema": "smart-tga-frozen-clipseg-semantic-mask-bank-v1",
        "cycle": args.cycle, "paint_count": len(records),
        "candidate_count": len(features), "feature_count": len(FEATURE_NAMES),
        "prompts": PROMPTS, "d4_views": 8,
        "support_ring_width_at_1024": 4,
        "model_weights_frozen": True, "semantic_labels_consumed": False,
        "filename_car_bbox_block_feature": False,
        "ownership_authority": False, "device": args.device,
        "checkpoint": str(args.checkpoint),
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
