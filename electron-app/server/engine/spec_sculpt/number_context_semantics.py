"""Shared intrinsic feature extraction for Smart TGA number context crops."""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
from PIL import Image


SCALAR_SEED_FIELDS = (
    "area_fraction", "fill_ratio", "edge_density", "texture_entropy",
    "strong_gradient_fraction", "perceptual_lightness", "perceptual_chroma",
    "ocr_alpha_coverage", "ocr_digit_coverage", "ocr_max_coverage",
)


def canonical_d4(grid: np.ndarray) -> np.ndarray:
    variants = []
    for turns in range(4):
        rotated = np.rot90(grid, turns)
        variants.extend((rotated, np.fliplr(rotated)))
    return min(variants, key=lambda item: tuple(np.round(item.ravel(), 4))).ravel()


def _resize_grid(array: np.ndarray, side: int = 8) -> np.ndarray:
    image = Image.fromarray(np.clip(array * 255.0, 0, 255).astype(np.uint8), mode="L")
    return np.asarray(image.resize((side, side), Image.Resampling.BILINEAR), dtype=np.float64) / 255.0


def context_feature_mapping(
    image: np.ndarray, proposal: Mapping[str, Any], seed: Mapping[str, Any],
) -> dict[str, float]:
    x, y, width, height = (int(value) for value in proposal["bbox"])
    crop = np.asarray(image[y:y + height, x:x + width], dtype=np.float64) / 255.0
    if crop.size == 0:
        crop = np.zeros((1, 1, 3), dtype=np.float64)
    gray = 0.2126 * crop[..., 0] + 0.7152 * crop[..., 1] + 0.0722 * crop[..., 2]
    maximum = np.max(crop, axis=2)
    minimum = np.min(crop, axis=2)
    saturation = (maximum - minimum) / np.maximum(maximum, 1e-6)
    # High-recall proposal generation intentionally keeps one-pixel fragments.
    # np.gradient requires at least two samples on every requested axis, so
    # compute each axis independently and treat a singleton axis as flat.
    gy = np.gradient(gray, axis=0) if gray.shape[0] > 1 else np.zeros_like(gray)
    gx = np.gradient(gray, axis=1) if gray.shape[1] > 1 else np.zeros_like(gray)
    magnitude = np.hypot(gx, gy)
    border = np.concatenate((gray[0], gray[-1], gray[:, 0], gray[:, -1]))
    border_median = float(np.median(border))
    foreground = np.maximum(np.abs(gray - border_median), saturation) > 0.14
    foreground_grid = canonical_d4(_resize_grid(foreground.astype(np.float64)))
    edge_scale = max(float(np.percentile(magnitude, 95)), 1e-6)
    edge_grid = canonical_d4(_resize_grid(np.clip(magnitude / edge_scale, 0, 1)))
    gray_hist = np.histogram(gray, bins=8, range=(0.0, 1.0))[0].astype(np.float64)
    gray_hist /= max(1.0, float(np.sum(gray_hist)))
    sat_hist = np.histogram(saturation, bins=6, range=(0.0, 1.0))[0].astype(np.float64)
    sat_hist /= max(1.0, float(np.sum(sat_hist)))
    seed_bbox = seed.get("bbox") or (x, y, width, height)
    seed_area = max(1, int(seed_bbox[2]) * int(seed_bbox[3]))
    proposal_area = max(1, width * height)
    result = {
        "proposal_area_fraction": proposal_area / 1024.0**2,
        "proposal_aspect_log": math.log(max(width, 1) / max(height, 1)),
        "proposal_border_distance": min(x, y, 1024 - x - width, 1024 - y - height) / 1024.0,
        "seed_to_proposal_area_ratio": seed_area / proposal_area,
        "seed_to_proposal_width_ratio": float(seed_bbox[2]) / max(1, width),
        "seed_to_proposal_height_ratio": float(seed_bbox[3]) / max(1, height),
        "crop_gray_mean": float(np.mean(gray)),
        "crop_gray_std": float(np.std(gray)),
        "crop_gray_p10": float(np.percentile(gray, 10)),
        "crop_gray_p50": float(np.percentile(gray, 50)),
        "crop_gray_p90": float(np.percentile(gray, 90)),
        "crop_saturation_mean": float(np.mean(saturation)),
        "crop_saturation_std": float(np.std(saturation)),
        "crop_edge_mean": float(np.mean(magnitude)),
        "crop_edge_p90": float(np.percentile(magnitude, 90)),
        "crop_foreground_fraction": float(np.mean(foreground)),
        "crop_border_median": border_median,
    }
    for field in SCALAR_SEED_FIELDS:
        result[f"seed_{field}"] = float(seed.get(field) or 0.0)
    for index, value in enumerate(gray_hist):
        result[f"gray_hist_{index}"] = float(value)
    for index, value in enumerate(sat_hist):
        result[f"sat_hist_{index}"] = float(value)
    for prefix, grid in (("foreground_d4", foreground_grid), ("edge_d4", edge_grid)):
        for index, value in enumerate(grid):
            result[f"{prefix}_{index}"] = float(value)
    for index in range(8):
        result[f"prototype_{index}"] = float(int(proposal.get("prototype_index", -1)) == index)
    return result


__all__ = ["SCALAR_SEED_FIELDS", "canonical_d4", "context_feature_mapping"]
