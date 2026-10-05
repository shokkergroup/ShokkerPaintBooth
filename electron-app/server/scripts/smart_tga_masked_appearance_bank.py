"""Build label-free, candidate-only masked appearance evidence for Smart TGA.

The bank deliberately excludes filename, car identity, absolute position, bbox
dimensions, template block, semantic review and ownership outcomes.  Bounding
boxes are used only to recover the exact source pixels under each immutable
candidate mask.  All emitted values describe masked pixels or their immediate
ring and are invariant to rotations/reflections up to resize interpolation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np

try:
    from scripts.smart_tga_clip_full_bank_embed import _bank_rows
    from scripts.smart_tga_exact_candidate_utils import decode_support
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_clip_full_bank_embed import _bank_rows  # type: ignore
    from scripts.smart_tga_exact_candidate_utils import decode_support  # type: ignore


STAT_CHANNELS = (
    "lightness", "lab_a", "lab_b", "chroma", "saturation", "value",
    "gray", "edge", "texture",
)
SPATIAL_CHANNELS = (
    "lightness", "lab_a", "lab_b", "chroma", "saturation", "value",
    "edge", "texture",
)
STAT_NAMES = ("mean", "std", "q10", "median", "q90")
HIST_BINS = 6
GRID_CELLS = 4


def _channel_maps(rgb: np.ndarray) -> dict[str, np.ndarray]:
    value = rgb.astype(np.float32) / 255.0
    lab = cv2.cvtColor(value, cv2.COLOR_RGB2LAB)
    hsv = cv2.cvtColor(value, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(value, cv2.COLOR_RGB2GRAY)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = np.clip(cv2.magnitude(grad_x, grad_y) / 4.0, 0.0, 1.0)
    mean = cv2.GaussianBlur(gray, (0, 0), 1.25)
    square_mean = cv2.GaussianBlur(gray * gray, (0, 0), 1.25)
    texture = np.sqrt(np.maximum(square_mean - mean * mean, 0.0))
    lab_a = lab[:, :, 1] / 128.0
    lab_b = lab[:, :, 2] / 128.0
    return {
        "lightness": lab[:, :, 0] / 100.0,
        "lab_a": lab_a,
        "lab_b": lab_b,
        "chroma": np.clip(np.sqrt(lab_a * lab_a + lab_b * lab_b), 0.0, 1.5),
        "saturation": hsv[:, :, 1],
        "value": hsv[:, :, 2],
        "gray": gray,
        "edge": edge,
        "texture": np.clip(texture, 0.0, 1.0),
        "hue": hsv[:, :, 0] * (np.pi / 180.0),
    }


def _entropy(histogram: np.ndarray) -> float:
    probability = histogram / max(float(histogram.sum()), 1.0)
    return -float(np.sum(probability * np.log(np.maximum(probability, 1e-8))))


def _normalized_canvas(
    values: np.ndarray, support: np.ndarray, size: int = 40,
) -> tuple[np.ndarray, np.ndarray]:
    height, width = support.shape
    scale = float(size - 8) / max(height, width)
    target_h = max(1, min(size, int(round(height * scale))))
    target_w = max(1, min(size, int(round(width * scale))))
    resized_mask = cv2.resize(
        support.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA,
    )
    resized_values = cv2.resize(
        values.astype(np.float32), (target_w, target_h), interpolation=cv2.INTER_AREA,
    )
    canvas = np.zeros((size, size), dtype=np.float32)
    mask_canvas = np.zeros((size, size), dtype=np.float32)
    top, left = (size - target_h) // 2, (size - target_w) // 2
    canvas[top:top + target_h, left:left + target_w] = resized_values * resized_mask
    mask_canvas[top:top + target_h, left:left + target_w] = resized_mask
    return canvas, mask_canvas


def _sorted_grid_embedding(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    """Return D4-invariant masked cell values without encoding bbox dimensions."""
    canvas, mask = _normalized_canvas(values, support)
    cells = []
    for row in np.array_split(np.arange(canvas.shape[0]), GRID_CELLS):
        for column in np.array_split(np.arange(canvas.shape[1]), GRID_CELLS):
            local_mask = mask[np.ix_(row, column)]
            weight = float(local_mask.sum())
            if weight <= 1e-6:
                cells.append(-2.0)
            else:
                cells.append(float((canvas[np.ix_(row, column)]).sum() / weight))
    return np.sort(np.asarray(cells, dtype=np.float32))


def appearance_feature_names() -> tuple[str, ...]:
    names: list[str] = []
    for channel in STAT_CHANNELS:
        names.extend(f"summary_{channel}_{name}" for name in STAT_NAMES)
        names.extend(f"hist_{channel}_{offset}" for offset in range(HIST_BINS))
        names.append(f"hist_{channel}_entropy")
    names.extend((
        "summary_hue_sin", "summary_hue_cos", "summary_hue_resultant",
        "summary_hue_entropy", "summary_dark_fraction", "summary_bright_fraction",
        "summary_saturated_fraction", "summary_grayscale_fraction",
        "summary_high_chroma_fraction", "ring_present",
    ))
    names.extend(f"ring_{channel}_mean_difference" for channel in STAT_CHANNELS)
    for channel in SPATIAL_CHANNELS:
        names.extend(
            f"spatial_{channel}_order_{offset}" for offset in range(GRID_CELLS ** 2)
        )
    return tuple(names)


FEATURE_NAMES = appearance_feature_names()


def appearance_features(rgb: np.ndarray, support: np.ndarray) -> np.ndarray:
    """Describe exact masked appearance and its local ring, never its identity."""
    if rgb.shape[:2] != support.shape:
        raise ValueError(f"source/mask shape mismatch: {rgb.shape[:2]} vs {support.shape}")
    if not np.any(support):
        raise ValueError("candidate support must be non-empty")
    channels = _channel_maps(rgb)
    mask = support.astype(bool)
    ring = cv2.dilate(mask.astype(np.uint8), np.ones((7, 7), np.uint8), iterations=1)
    ring = ring.astype(bool) & ~mask
    values: list[float] = []
    ranges = {
        "lab_a": (-1.0, 1.0), "lab_b": (-1.0, 1.0), "chroma": (0.0, 1.5),
    }
    for name in STAT_CHANNELS:
        selected = channels[name][mask].astype(np.float64)
        values.extend((
            float(selected.mean()), float(selected.std()),
            float(np.quantile(selected, 0.10)), float(np.median(selected)),
            float(np.quantile(selected, 0.90)),
        ))
        low, high = ranges.get(name, (0.0, 1.0))
        histogram = np.histogram(selected, bins=HIST_BINS, range=(low, high))[0]
        values.extend((histogram / max(1, int(histogram.sum()))).tolist())
        values.append(_entropy(histogram))
    hue = channels["hue"][mask].astype(np.float64)
    sin_mean, cos_mean = float(np.sin(hue).mean()), float(np.cos(hue).mean())
    hue_histogram = np.histogram(hue, bins=HIST_BINS, range=(0.0, 2.0 * np.pi))[0]
    lightness = channels["lightness"][mask]
    saturation = channels["saturation"][mask]
    chroma = channels["chroma"][mask]
    values.extend((
        sin_mean, cos_mean, float(np.hypot(sin_mean, cos_mean)),
        _entropy(hue_histogram), float(np.mean(lightness < 0.20)),
        float(np.mean(lightness > 0.80)), float(np.mean(saturation > 0.40)),
        float(np.mean(saturation < 0.12)), float(np.mean(chroma > 0.25)),
        float(np.any(ring)),
    ))
    for name in STAT_CHANNELS:
        difference = 0.0 if not np.any(ring) else float(
            channels[name][mask].mean() - channels[name][ring].mean()
        )
        values.append(difference)
    for name in SPATIAL_CHANNELS:
        values.extend(_sorted_grid_embedding(channels[name], mask).tolist())
    result = np.asarray(values, dtype=np.float32)
    if result.shape != (len(FEATURE_NAMES),) or not np.all(np.isfinite(result)):
        raise RuntimeError(
            f"masked appearance feature drift: {result.shape} vs {len(FEATURE_NAMES)}"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=733)
    parser.add_argument("--ring-padding", type=int, default=5)
    args = parser.parse_args()
    started = time.perf_counter()
    if args.ring_padding < 3:
        raise ValueError("ring-padding must be at least 3 pixels")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    trace = _bank_rows(bank)
    features = np.empty((len(trace), len(FEATURE_NAMES)), dtype=np.float32)
    cursor = 0
    for record in bank["records"]:
        bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(record["source_1024"])
        source = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        exact = np.load(record["exact_candidate_bank"], allow_pickle=False)
        try:
            for index, candidate in enumerate(record["candidates"]):
                if str(exact["proposal_ids"][index]) != str(candidate["proposal_id"]):
                    raise RuntimeError(f"candidate trace drift: {record['paint']} #{index}")
                x, y, width, height = map(int, exact["bboxes"][index])
                support = decode_support(exact, index)
                if support.shape != (height, width):
                    raise RuntimeError("candidate bbox/support shape drift")
                pad = args.ring_padding
                x0, y0 = max(0, x - pad), max(0, y - pad)
                x1, y1 = min(source.shape[1], x + width + pad), min(
                    source.shape[0], y + height + pad,
                )
                local_support = np.zeros((y1 - y0, x1 - x0), dtype=bool)
                local_support[y - y0:y - y0 + height, x - x0:x - x0 + width] = support
                features[cursor] = appearance_features(source[y0:y1, x0:x1], local_support)
                cursor += 1
        finally:
            exact.close()
    if cursor != len(trace):
        raise RuntimeError("full-bank appearance traversal drift")
    np.savez_compressed(
        args.output,
        paints=np.asarray([row["paint"] for row in trace]),
        candidate_indices=np.asarray([row["candidate_index"] for row in trace], dtype=np.int32),
        proposal_ids=np.asarray([row["proposal_id"] for row in trace]),
        features=features,
        feature_names=np.asarray(FEATURE_NAMES),
    )
    manifest = {
        "schema": "smart-tga-masked-appearance-bank-v1", "cycle": args.cycle,
        "candidate_count": len(trace), "feature_count": len(FEATURE_NAMES),
        "feature_groups": {
            "masked_summary_histogram": int(sum(not name.startswith("spatial_") and not name.startswith("ring_") for name in FEATURE_NAMES)),
            "masked_ring_contrast": int(sum(name.startswith("ring_") for name in FEATURE_NAMES)),
            "d4_invariant_masked_spatial_embedding": int(sum(name.startswith("spatial_") for name in FEATURE_NAMES)),
        },
        "label_free": True, "ownership_authority": False,
        "forbidden_features": {
            "filename_or_car_identity": False, "absolute_bbox_or_position": False,
            "bbox_dimensions": False, "template_block": False,
            "semantic_review_or_outcome": False,
        },
        "output": str(args.output),
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
