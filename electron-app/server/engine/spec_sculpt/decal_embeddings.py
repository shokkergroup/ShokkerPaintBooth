"""Transformation-invariant reviewed decal-family embeddings for Smart TGA.

The library is corroborating shadow evidence only.  It never assigns ownership,
never mutates masks, and deliberately abstains unless a family has repeated
reviewed support, strong visual similarity, and a clear runner-up margin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - shipped runtime includes OpenCV
    cv2 = None


def _readonly(array: np.ndarray) -> np.ndarray:
    out = np.ascontiguousarray(array, np.float32)
    out.setflags(write=False)
    return out


@dataclass(frozen=True)
class DecalVisualEmbedding:
    """One or more intrinsic variants, each with eight transformed views."""

    views: np.ndarray = field(repr=False, compare=False)
    descriptor_side: int
    source_shape: tuple[int, int]

    def __post_init__(self) -> None:
        views = _readonly(self.views)
        if views.ndim != 2 or views.shape[0] < 8 or views.shape[0] % 8 or views.shape[1] <= 0:
            raise ValueError("decal embedding must contain complete eight-view variants")
        norms = np.linalg.norm(views, axis=1)
        if not np.allclose(norms, 1.0, atol=1e-4):
            raise ValueError("decal embedding views must be L2 normalized")
        object.__setattr__(self, "views", views)

    @property
    def variant_count(self) -> int:
        return int(self.views.shape[0] // 8)


@dataclass(frozen=True)
class EmbeddingReference:
    reference_id: str
    family_id: str
    reviewed_owner: str
    review_label: str
    source: str
    bbox: tuple[int, int, int, int]
    embedding: DecalVisualEmbedding = field(repr=False, compare=False)


@dataclass(frozen=True)
class EmbeddingQueryResult:
    status: str
    family_id: str | None
    reviewed_owner: str | None
    similarity: float
    runner_up_similarity: float
    margin: float
    supporting_references: int
    matched_reference_ids: tuple[str, ...]
    reason: str
    casts_votes: bool = False
    ownership_authority: bool = False


def _coerce_rgb(rgb: np.ndarray) -> np.ndarray:
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("rgb must have shape HxWx3+")
    if image.dtype == np.uint8:
        return np.ascontiguousarray(image[:, :, :3])
    values = np.asarray(image[:, :, :3], np.float32)
    if values.size and float(np.nanmax(values)) <= 1.5:
        values *= 255.0
    return np.clip(values, 0.0, 255.0).astype(np.uint8)


def _tight_crop(rgb: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    binary = np.asarray(mask) > 0
    if binary.shape != rgb.shape[:2] or not binary.any():
        raise ValueError("embedding mask must match rgb and contain pixels")
    ys, xs = np.where(binary)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    return rgb[y0:y1, x0:x1], binary[y0:y1, x0:x1]


def _descriptor(rgb: np.ndarray, mask: np.ndarray, side: int) -> np.ndarray:
    if cv2 is None:
        raise RuntimeError("OpenCV is required for decal embeddings")
    resized_rgb = cv2.resize(rgb, (side, side), interpolation=cv2.INTER_AREA)
    resized_mask = cv2.resize(mask.astype(np.uint8), (side, side), interpolation=cv2.INTER_NEAREST) > 0
    gray = cv2.cvtColor(resized_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    values = gray[resized_mask]
    mean = float(values.mean()) if len(values) else 0.0
    std = float(values.std()) if len(values) else 0.0
    normalized = np.zeros_like(gray, np.float32)
    normalized[resized_mask] = np.clip((gray[resized_mask] - mean) / max(12.0, std), -2.5, 2.5) / 2.5
    edges = cv2.Canny(gray.astype(np.uint8), 55, 135).astype(np.float32) / 255.0
    edges *= resized_mask
    silhouette = resized_mask.astype(np.float32)
    vector = np.concatenate((silhouette.ravel(), edges.ravel(), normalized.ravel()))
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-8:
        vector[0] = 1.0
        norm = 1.0
    return vector / norm


def embed_decal(
    rgb: np.ndarray,
    mask: np.ndarray | None = None,
    *,
    descriptor_side: int = 12,
    include_palette_roles: bool = False,
    include_foreground_subinstances: bool = False,
) -> DecalVisualEmbedding:
    """Embed a crop/mask with rotation, reflection, scale, and recolor tolerance."""
    image = _coerce_rgb(rgb)
    binary = np.ones(image.shape[:2], bool) if mask is None else np.asarray(mask) > 0
    image, binary = _tight_crop(image, binary)
    side = max(8, int(descriptor_side))
    variants = [binary]
    if include_palette_roles:
        from engine.spec_sculpt.decal_palette_roles import derive_palette_role_masks
        variants.extend(item.local_mask for item in derive_palette_role_masks(image, binary))
    if include_foreground_subinstances:
        from engine.spec_sculpt.decal_subinstances import derive_intrinsic_subinstances
        # Individual color components are intentionally excluded from generic
        # family embedding: isolated rectangles/strokes collapse unrelated
        # logos to identical silhouettes. Only assembled multi-component
        # hypotheses are eligible, and even these remain opt-in/shadow-only.
        variants.extend(
            item.local_mask
            for item in derive_intrinsic_subinstances(image, binary)
            if item.component_count >= 2
        )
    unique_variants = []
    seen_variants = set()
    for variant_mask in variants:
        fingerprint = np.packbits(np.asarray(variant_mask, bool).reshape(-1)).tobytes()
        if fingerprint in seen_variants:
            continue
        seen_variants.add(fingerprint)
        unique_variants.append(variant_mask)
    views = []
    for variant_mask in unique_variants:
        for turns in range(4):
            rotated_rgb = np.rot90(image, turns)
            rotated_mask = np.rot90(variant_mask, turns)
            for mirrored in (False, True):
                view_rgb = np.fliplr(rotated_rgb) if mirrored else rotated_rgb
                view_mask = np.fliplr(rotated_mask) if mirrored else rotated_mask
                views.append(_descriptor(view_rgb, view_mask, side))
    return DecalVisualEmbedding(
        views=np.stack(views),
        descriptor_side=side,
        source_shape=tuple(int(value) for value in image.shape[:2]),
    )


def embedding_similarity(
    left: DecalVisualEmbedding,
    right: DecalVisualEmbedding,
) -> tuple[float, int, int]:
    if left.views.shape[1] != right.views.shape[1]:
        raise ValueError("embedding descriptor dimensions differ")
    scores = left.views @ right.views.T
    flat_index = int(np.argmax(scores))
    left_view, right_view = np.unravel_index(flat_index, scores.shape)
    return round(float(scores[left_view, right_view]), 6), int(left_view), int(right_view)


def query_embedding_library(
    query: DecalVisualEmbedding,
    references: Sequence[EmbeddingReference],
    *,
    min_similarity: float = 0.84,
    ambiguity_margin: float = 0.04,
    min_family_support: int = 2,
) -> EmbeddingQueryResult:
    families: dict[str, list[tuple[float, EmbeddingReference]]] = {}
    for reference in references:
        similarity, _left_view, _right_view = embedding_similarity(query, reference.embedding)
        families.setdefault(reference.family_id, []).append((similarity, reference))
    ranked = []
    for family_id, matches in families.items():
        matches.sort(key=lambda item: (-item[0], item[1].reference_id))
        if len(matches) < max(1, int(min_family_support)):
            continue
        support = matches[:max(1, int(min_family_support))]
        # Repeated support is required: score by the weakest required example,
        # preventing one excellent coincidence from laundering a family.
        score = min(item[0] for item in support)
        owners = {item[1].reviewed_owner for item in support}
        if len(owners) != 1:
            continue
        ranked.append((score, family_id, next(iter(owners)), matches))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return EmbeddingQueryResult(
            status="abstained", family_id=None, reviewed_owner=None,
            similarity=0.0, runner_up_similarity=0.0, margin=0.0,
            supporting_references=0, matched_reference_ids=(),
            reason="insufficient_reviewed_family_support",
        )
    best = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
    margin = best[0] - runner_up
    support_matches = tuple(item[1].reference_id for item in best[3] if item[0] >= min_similarity)
    if best[0] < float(min_similarity):
        status, reason = "abstained", "below_similarity_threshold"
        family_id = owner = None
    elif len(ranked) > 1 and margin < float(ambiguity_margin):
        status, reason = "abstained", "ambiguous_family_margin"
        family_id = owner = None
    else:
        status, reason = "corroborated", "repeated_reviewed_family_match"
        family_id, owner = best[1], best[2]
    return EmbeddingQueryResult(
        status=status,
        family_id=family_id,
        reviewed_owner=owner,
        similarity=round(best[0], 6),
        runner_up_similarity=round(runner_up, 6),
        margin=round(margin, 6),
        supporting_references=len(support_matches),
        matched_reference_ids=support_matches,
        reason=reason,
    )


__all__ = [
    "DecalVisualEmbedding",
    "EmbeddingQueryResult",
    "EmbeddingReference",
    "embed_decal",
    "embedding_similarity",
    "query_embedding_library",
]
