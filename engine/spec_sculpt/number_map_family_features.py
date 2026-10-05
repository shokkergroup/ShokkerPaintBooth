"""Owner-neutral intrinsic features for number probability-map families.

Probability-map proposals are deliberately high recall.  This module describes
their visual content and the stability of nested proposal families without using
filename, car identity, current owner, or absolute canvas position.  The features
are evidence for a calibrated shadow scorer; they never assign an output layer.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import cv2
import numpy as np

from .number_context_component_features import FEATURE_NAMES, component_feature_vector
from .decal_template_position import compute_template_position_evidence


MAP_EVIDENCE_FEATURE_NAMES = (
    "map_relative_quantile", "map_threshold", "map_mean_probability",
    "map_max_probability", "map_log_model_pixels", "foundation_probability",
)
PROPOSAL_FEATURE_NAMES = (*FEATURE_NAMES, *MAP_EVIDENCE_FEATURE_NAMES)
FAMILY_STABILITY_FEATURE_NAMES = (
    "family_log_member_count", "family_foundation_mean", "family_foundation_min",
    "family_foundation_max", "family_foundation_std", "family_quantile_min",
    "family_quantile_max", "family_quantile_range", "family_log_area_scale",
    "family_shape_instability", "family_texture_instability",
    "family_palette_instability",
)
FAMILY_FEATURE_NAMES = (*PROPOSAL_FEATURE_NAMES, *FAMILY_STABILITY_FEATURE_NAMES)
FAMILY_RELATIONSHIP_FEATURE_NAMES = (
    "peer_d4_similarity_max", "peer_d4_similarity_second",
    "peer_appearance_similarity_max", "peer_silhouette_similarity_max",
    "peer_count_ge_080_log1p", "peer_count_ge_090_log1p",
    "peer_area_log_difference_at_max",
)
FAMILY_OCR_FEATURE_NAMES = (
    "ocr_max_family_coverage", "ocr_max_region_coverage",
    "ocr_alpha_family_coverage", "ocr_digit_family_coverage",
    "ocr_alpha_token_count_log1p", "ocr_digit_token_count_log1p",
    "ocr_alpha_character_count_log1p", "ocr_digit_character_count_log1p",
    "ocr_max_confidence", "ocr_max_text_quality",
)
FAMILY_OWNER_CORROBORATION_FEATURE_NAMES = (
    "legacy_number_overlap", "legacy_sponsor_overlap", "legacy_template_overlap",
    "legacy_paint_overlap", "legacy_brand_graphics_overlap",
    "legacy_number_minus_sponsor", "legacy_number_minus_max_non_number",
)
FAMILY_TEMPLATE_POSITION_FEATURE_NAMES = (
    "template_number_fraction", "template_sponsor_fraction",
    "template_mandatory_fraction", "template_number_minus_sponsor",
    "template_number_minus_max_non_number",
)


def _local_probability(
    probability_canvas: np.ndarray, bbox: Sequence[int], expected_shape: Sequence[int],
) -> np.ndarray:
    x, y, width, height = (int(value) for value in bbox)
    values = np.asarray(probability_canvas, np.float32)
    local = values[max(0, y):max(0, y) + height, max(0, x):max(0, x) + width]
    if local.shape != tuple(map(int, expected_shape)):
        local = cv2.resize(values, (width, height), interpolation=cv2.INTER_LINEAR)
    return np.asarray(local, np.float32)


def map_proposal_feature_vector(
    rgb: np.ndarray,
    bbox: Sequence[int],
    local_mask: np.ndarray,
    probability_canvas: np.ndarray,
    provenance: Mapping,
    foundation_probability: float,
) -> np.ndarray:
    """Describe one map proposal using only intrinsic image/map evidence."""
    mask = np.asarray(local_mask, bool)
    local_probability = _local_probability(probability_canvas, bbox, mask.shape)
    intrinsic = component_feature_vector(
        rgb, bbox, mask, family_margin=0.0, pixel_score=local_probability,
    )
    evidence = np.asarray((
        float(provenance.get("relative_quantile", 0.0)),
        float(provenance.get("threshold", 0.0)),
        float(provenance.get("mean_probability", 0.0)),
        float(provenance.get("max_probability", 0.0)),
        float(np.log1p(max(0, int(provenance.get("model_pixels", 0))))),
        float(foundation_probability),
    ), np.float32)
    result = np.concatenate((intrinsic, evidence)).astype(np.float32, copy=False)
    if result.shape != (len(PROPOSAL_FEATURE_NAMES),):
        raise AssertionError("map proposal feature schema drift")
    result.setflags(write=False)
    return result


def map_family_feature_vector(members: Sequence[Mapping]) -> np.ndarray:
    """Describe a nested proposal family while preserving its outer hypothesis.

    Each member supplies ``vector``, ``proposal_bbox``, ``provenance``, and
    ``foundation_probability``.  The largest proposal represents the complete
    object hypothesis; compact stability terms describe how that hypothesis
    changes across stricter probability thresholds.
    """
    if not members:
        raise ValueError("map family must contain at least one proposal")
    vectors = np.asarray([item["vector"] for item in members], np.float32)
    if vectors.ndim != 2 or vectors.shape[1] != len(PROPOSAL_FEATURE_NAMES):
        raise ValueError("map family proposal feature schema mismatch")
    areas = np.asarray([
        max(1, int(item["proposal_bbox"][2]) * int(item["proposal_bbox"][3]))
        for item in members
    ], np.float32)
    outer = vectors[int(np.argmax(areas))]
    foundations = np.asarray([float(item["foundation_probability"]) for item in members], np.float32)
    quantiles = np.asarray([
        float(item.get("provenance", {}).get("relative_quantile", 0.0)) for item in members
    ], np.float32)
    # Summarize instability by evidence family rather than appending a large,
    # paint-fragile vector of per-feature differences.
    standard_deviation = np.std(vectors, axis=0)
    shape_stop = 3 + 16
    texture_stop = shape_stop + 3
    palette_stop = texture_stop + 7
    stability = np.asarray((
        np.log1p(len(members)),
        np.mean(foundations), np.min(foundations), np.max(foundations), np.std(foundations),
        np.min(quantiles), np.max(quantiles), np.ptp(quantiles),
        np.log(max(areas) / max(1.0, float(np.min(areas)))),
        np.mean(standard_deviation[:shape_stop]),
        np.mean(standard_deviation[shape_stop:texture_stop]),
        np.mean(standard_deviation[texture_stop:palette_stop]),
    ), np.float32)
    result = np.concatenate((outer, stability)).astype(np.float32, copy=False)
    if result.shape != (len(FAMILY_FEATURE_NAMES),):
        raise AssertionError("map family feature schema drift")
    result.setflags(write=False)
    return result


def map_family_relationship_features(
    embeddings: np.ndarray, areas: Sequence[float],
) -> np.ndarray:
    """Return owner-neutral within-paint D4 copy-similarity corroboration.

    The result describes repeated visual families but never assigns semantics or
    casts a vote.  Appearance and silhouette halves are measured separately so a
    repeated palette cannot disguise a different object shape.
    """
    values = np.asarray(embeddings, np.float32)
    if values.ndim != 2 or values.shape[1] < 2 or values.shape[1] % 2:
        raise ValueError("D4 embeddings must be an Nx(2K) matrix")
    area_values = np.asarray(areas, np.float32)
    if area_values.shape != (len(values),):
        raise ValueError("family area count must match embeddings")
    half = values.shape[1] // 2

    def normalized(matrix):
        return matrix / np.linalg.norm(matrix, axis=1, keepdims=True).clip(1e-8)

    appearance = normalized(values[:, :half])
    silhouette = normalized(values[:, half:])
    combined = (appearance @ appearance.T + silhouette @ silhouette.T) * 0.5
    appearance_similarity = appearance @ appearance.T
    silhouette_similarity = silhouette @ silhouette.T
    output = []
    for index in range(len(values)):
        peers = [peer for peer in range(len(values)) if peer != index]
        if not peers:
            output.append((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.0))
            continue
        ranked = sorted(peers, key=lambda peer: float(combined[index, peer]), reverse=True)
        best = ranked[0]
        scores = np.asarray([combined[index, peer] for peer in peers], np.float32)
        output.append((
            float(combined[index, best]),
            float(combined[index, ranked[1]]) if len(ranked) > 1 else 0.0,
            float(appearance_similarity[index, best]),
            float(silhouette_similarity[index, best]),
            float(np.log1p(np.count_nonzero(scores >= 0.80))),
            float(np.log1p(np.count_nonzero(scores >= 0.90))),
            float(abs(np.log(max(1.0, float(area_values[index])) / max(1.0, float(area_values[best]))))),
        ))
    result = np.asarray(output, np.float32)
    if result.shape != (len(values), len(FAMILY_RELATIONSHIP_FEATURE_NAMES)):
        raise AssertionError("map family relationship feature schema drift")
    result.setflags(write=False)
    return result


def map_family_ocr_features(
    family_bbox: Sequence[int], ocr_regions: Sequence[Mapping],
) -> np.ndarray:
    """Summarize immutable OCR overlap as corroborative semantic evidence."""
    x, y, width, height = (int(value) for value in family_bbox)
    family_area = max(1, width * height)
    maximum_family = maximum_region = alpha_coverage = digit_coverage = 0.0
    alpha_tokens = digit_tokens = alpha_characters = digit_characters = 0
    maximum_confidence = maximum_quality = 0.0
    for region in ocr_regions:
        box = region.get("bbox") or ()
        if len(box) != 4:
            continue
        rx, ry, rw, rh = (int(value) for value in box)
        intersection = max(0, min(x + width, rx + rw) - max(x, rx)) * max(
            0, min(y + height, ry + rh) - max(y, ry),
        )
        if not intersection:
            continue
        family_coverage = intersection / family_area
        region_coverage = intersection / max(1, rw * rh)
        text = str(region.get("text") or "")
        alpha_count = sum(character.isalpha() for character in text)
        digit_count = sum(character.isdigit() for character in text)
        maximum_family = max(maximum_family, family_coverage)
        maximum_region = max(maximum_region, region_coverage)
        if alpha_count:
            alpha_coverage = max(alpha_coverage, family_coverage)
            alpha_tokens += 1
            alpha_characters += alpha_count
        if digit_count:
            digit_coverage = max(digit_coverage, family_coverage)
            digit_tokens += 1
            digit_characters += digit_count
        maximum_confidence = max(maximum_confidence, float(region.get("confidence") or 0.0))
        maximum_quality = max(maximum_quality, float(region.get("text_quality") or 0.0))
    result = np.asarray((
        maximum_family, maximum_region, alpha_coverage, digit_coverage,
        np.log1p(alpha_tokens), np.log1p(digit_tokens),
        np.log1p(alpha_characters), np.log1p(digit_characters),
        maximum_confidence, maximum_quality,
    ), np.float32)
    if result.shape != (len(FAMILY_OCR_FEATURE_NAMES),):
        raise AssertionError("map family OCR feature schema drift")
    result.setflags(write=False)
    return result


def map_family_owner_corroboration_features(
    family_bbox: Sequence[int], local_mask: np.ndarray, layer_masks: Mapping[str, np.ndarray],
) -> np.ndarray:
    """Summarize exact-mask legacy ownership as non-authoritative corroboration."""
    x, y, width, height = (int(value) for value in family_bbox)
    support = np.asarray(local_mask, bool)
    if support.shape != (height, width):
        support = cv2.resize(
            support.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST,
        ) > 0
    denominator = max(1, int(np.count_nonzero(support)))
    overlaps = []
    for name in ("numbers", "sponsors", "template", "paint", "brand_graphics"):
        canvas = np.asarray(layer_masks.get(name, np.zeros((y + height, x + width), bool)), bool)
        local = canvas[y:y + height, x:x + width]
        if local.shape != support.shape:
            padded = np.zeros(support.shape, bool)
            padded[:local.shape[0], :local.shape[1]] = local
            local = padded
        overlaps.append(float(np.count_nonzero(support & local)) / denominator)
    numbers, sponsors, template, paint, brand = overlaps
    result = np.asarray((
        numbers, sponsors, template, paint, brand,
        numbers - sponsors, numbers - max(sponsors, template, paint, brand),
    ), np.float32)
    if result.shape != (len(FAMILY_OWNER_CORROBORATION_FEATURE_NAMES),):
        raise AssertionError("map family owner corroboration feature schema drift")
    result.setflags(write=False)
    return result


def map_family_template_position_features(
    family_bbox: Sequence[int], local_mask: np.ndarray,
    canvas_shape: Sequence[int], panel_map: Mapping,
) -> np.ndarray:
    """Summarize normalized template-block overlap without assigning ownership.

    Panel maps are supplied by the caller and scaled to the current canvas by
    :func:`compute_template_position_evidence`.  These values may corroborate a
    visual classifier, but they never create a Number vote on their own.
    """
    evidence = compute_template_position_evidence(
        family_bbox, local_mask, canvas_shape, panel_map,
    )
    number = float(evidence.best_number_fraction)
    sponsor = float(evidence.best_sponsor_fraction)
    mandatory = float(evidence.best_mandatory_fraction)
    result = np.asarray((
        number, sponsor, mandatory, number - sponsor,
        number - max(sponsor, mandatory),
    ), np.float32)
    if result.shape != (len(FAMILY_TEMPLATE_POSITION_FEATURE_NAMES),):
        raise AssertionError("map family template-position feature schema drift")
    result.setflags(write=False)
    return result


__all__ = [
    "FAMILY_FEATURE_NAMES", "FAMILY_OCR_FEATURE_NAMES",
    "FAMILY_OWNER_CORROBORATION_FEATURE_NAMES", "FAMILY_RELATIONSHIP_FEATURE_NAMES",
    "FAMILY_TEMPLATE_POSITION_FEATURE_NAMES",
    "MAP_EVIDENCE_FEATURE_NAMES", "PROPOSAL_FEATURE_NAMES",
    "map_family_feature_vector", "map_family_ocr_features",
    "map_family_owner_corroboration_features", "map_family_relationship_features",
    "map_family_template_position_features",
    "map_proposal_feature_vector",
]
