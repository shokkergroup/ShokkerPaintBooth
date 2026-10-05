"""Frozen, portable inference contract for Smart TGA number-map families.

The model consumes immutable owner-neutral family features.  It returns scores
and shadow decisions only; it cannot create evidence votes or mutate a layer.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np

from .number_map_family_features import (
    FAMILY_FEATURE_NAMES,
    FAMILY_OCR_FEATURE_NAMES,
    FAMILY_OWNER_CORROBORATION_FEATURE_NAMES,
    FAMILY_RELATIONSHIP_FEATURE_NAMES,
    FAMILY_TEMPLATE_POSITION_FEATURE_NAMES,
)


CLIP_TEXT_FEATURE_NAMES = (
    "clip_digit_similarity_max", "clip_digit_similarity_mean",
    "clip_alpha_similarity_max", "clip_alpha_similarity_mean",
    "clip_graphic_similarity_max", "clip_graphic_similarity_mean",
    "clip_digit_minus_alpha_margin", "clip_digit_minus_all_negative_margin",
)

SCALAR_FEATURE_NAMES = (
    *FAMILY_FEATURE_NAMES,
    *FAMILY_RELATIONSHIP_FEATURE_NAMES,
    *FAMILY_OCR_FEATURE_NAMES,
    *CLIP_TEXT_FEATURE_NAMES,
    *FAMILY_OWNER_CORROBORATION_FEATURE_NAMES,
    *FAMILY_TEMPLATE_POSITION_FEATURE_NAMES,
)


def clip_text_feature_vector(
    embedding: np.ndarray, text_prototypes: np.ndarray,
) -> np.ndarray:
    half = len(embedding) // 2
    appearance = np.asarray(embedding[:half], np.float32)
    appearance /= np.linalg.norm(appearance).clip(1e-8)
    similarity = np.asarray(text_prototypes, np.float32) @ appearance
    digit, alpha, graphic = similarity[:4], similarity[4:9], similarity[9:]
    result = np.asarray((
        np.max(digit), np.mean(digit), np.max(alpha), np.mean(alpha),
        np.max(graphic), np.mean(graphic),
        np.max(digit) - np.max(alpha),
        np.max(digit) - max(np.max(alpha), np.max(graphic)),
    ), np.float32)
    if result.shape != (len(CLIP_TEXT_FEATURE_NAMES),):
        raise AssertionError("CLIP text feature schema drift")
    result.setflags(write=False)
    return result


def frozen_candidate_inference(
    scalar_features: np.ndarray,
    embeddings: np.ndarray,
    candidate: Mapping[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Apply one serialized scorer without fitting or selecting a threshold."""
    scalar = np.asarray(scalar_features, np.float32)
    embedding = np.asarray(embeddings, np.float32)
    expected_names = tuple(str(value) for value in candidate["feature_names"].tolist())
    if expected_names != SCALAR_FEATURE_NAMES:
        raise AssertionError("frozen candidate scalar feature contract drift")
    reduced = (embedding - candidate["pca_mean"]) @ candidate["pca_components"].T
    matrix = np.column_stack((scalar, reduced))
    if matrix.shape[1] != len(candidate["mean"]):
        raise AssertionError("frozen candidate matrix width drift")
    scaled = (matrix - candidate["mean"]) / np.maximum(candidate["scale"], 1e-8)
    logit = scaled @ candidate["coefficient"] + float(candidate["intercept"][0])
    probability = 1.0 / (1.0 + np.exp(-np.clip(logit, -40.0, 40.0)))
    digit = scalar[:, SCALAR_FEATURE_NAMES.index("clip_digit_similarity_max")]
    legacy_number = scalar[:, SCALAR_FEATURE_NAMES.index("legacy_number_overlap")]
    template_number = scalar[:, SCALAR_FEATURE_NAMES.index("template_number_fraction")]
    corroborated = (
        (
            (digit >= float(candidate["digit_threshold"][0]))
            & (template_number >= float(candidate["template_number_threshold"][0]))
        )
        | (legacy_number >= float(candidate["number_overlap_threshold"][0]))
    )
    accepted = (probability >= float(candidate["threshold"][0])) & corroborated
    return probability.astype(np.float32), accepted


__all__ = [
    "CLIP_TEXT_FEATURE_NAMES",
    "SCALAR_FEATURE_NAMES",
    "clip_text_feature_vector",
    "frozen_candidate_inference",
]
