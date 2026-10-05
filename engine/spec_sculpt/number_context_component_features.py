"""Owner-neutral intrinsic features for Smart TGA component semantics.

The vector deliberately excludes filename, current owner/layer and absolute bbox
position.  It is suitable for shadow scoring only until reviewed canary gates
authorize an adjudicator to consume it.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .decal_instances import DecalCandidateInstance, extract_candidate_instance_features


FEATURE_NAMES = (
    "log_area_fraction", "fill_ratio", "log_orientation_free_aspect",
    *(f"d4_occupancy_{index}" for index in range(16)),
    "edge_density", "strong_gradient_fraction", "texture_entropy",
    "std_red", "std_green", "std_blue", "perceptual_lightness",
    "perceptual_chroma", "hue_sine", "hue_cosine", "family_margin",
    "pixel_mean", "pixel_std", "pixel_q75", "pixel_q90", "pixel_max",
    "peer_similarity", "peer_count_log1p", "peer_area_log_difference",
)


def _d4_canonical_occupancy(values: Sequence[float]) -> tuple[float, ...]:
    grid = np.asarray(values, np.float32).reshape(4, 4)
    variants = []
    for rotation in range(4):
        rotated = np.rot90(grid, rotation)
        variants.extend((rotated, np.fliplr(rotated)))
    return tuple(float(value) for value in min(
        (tuple(float(value) for value in item.ravel()) for item in variants)
    ))


def component_feature_vector(
    rgb: np.ndarray,
    bbox: Sequence[int],
    local_mask: np.ndarray,
    *,
    family_margin: float,
    pixel_score: np.ndarray | None = None,
    peer_similarity: float = 0.0,
    peer_count: int = 0,
    peer_area_log_difference: float = 8.0,
) -> np.ndarray:
    """Return one orientation/mirror-tolerant semantic feature vector."""
    x, y, width, height = (int(value) for value in bbox)
    mask = np.ascontiguousarray(np.asarray(local_mask, bool))
    instance = DecalCandidateInstance(
        instance_id="intrinsic-component",
        bbox=(x, y, width, height),
        area=int(np.count_nonzero(mask)),
        local_mask=mask,
        candidate_ids=(),
        source_stages=("component_adapter",),
        sources=(),
        owner_hypotheses=(),
    )
    feature = extract_candidate_instance_features(rgb, (instance,))[0]
    aspect = max(float(feature.aspect_ratio), 1.0 / max(1e-9, float(feature.aspect_ratio)))
    hue = np.deg2rad(float(feature.perceptual_hue_degrees))
    scores = np.asarray(pixel_score if pixel_score is not None else np.zeros(mask.shape), np.float32)
    selected = scores[mask] if scores.shape == mask.shape else np.asarray([], np.float32)
    if selected.size:
        pixel_summary = (
            float(np.mean(selected)), float(np.std(selected)),
            float(np.quantile(selected, 0.75)), float(np.quantile(selected, 0.90)),
            float(np.max(selected)),
        )
    else:
        pixel_summary = (0.0,) * 5
    vector = (
        float(np.log(max(1e-9, feature.area_fraction))),
        float(feature.fill_ratio), float(np.log(max(1.0, aspect))),
        *_d4_canonical_occupancy(feature.shape_occupancy),
        float(feature.edge_density), float(feature.strong_gradient_fraction),
        float(feature.texture_entropy),
        *(float(value) / 255.0 for value in feature.std_rgb),
        float(feature.perceptual_lightness), float(feature.perceptual_chroma),
        float(np.sin(hue)), float(np.cos(hue)), float(family_margin),
        *pixel_summary,
        float(peer_similarity), float(np.log1p(max(0, int(peer_count)))),
        float(peer_area_log_difference),
    )
    result = np.asarray(vector, np.float32)
    if result.shape != (len(FEATURE_NAMES),):
        raise AssertionError("component feature vector schema drift")
    result.setflags(write=False)
    return result


def component_probability(vector: np.ndarray, mean: np.ndarray, scale: np.ndarray, coefficient: np.ndarray, intercept: float) -> float:
    """Pure-NumPy probability for a fitted linear shadow scorer."""
    standardized = (np.asarray(vector, np.float32) - mean) / np.maximum(scale, 1e-8)
    logit = float(np.dot(standardized, coefficient) + intercept)
    return float(1.0 / (1.0 + np.exp(-np.clip(logit, -40.0, 40.0))))


__all__ = ["FEATURE_NAMES", "component_feature_vector", "component_probability"]
