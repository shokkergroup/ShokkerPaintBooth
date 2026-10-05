"""Rotation/scale-tolerant local feature evidence for reviewed decals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


@dataclass(frozen=True)
class LocalFeatureSignature:
    points: np.ndarray = field(repr=False, compare=False)
    descriptors: np.ndarray = field(repr=False, compare=False)
    source_shape: tuple[int, int]

    def __post_init__(self) -> None:
        points = np.ascontiguousarray(self.points, np.float32)
        descriptors = np.ascontiguousarray(self.descriptors, np.float32)
        if points.ndim != 2 or points.shape[1:] != (2,) or descriptors.ndim != 2:
            raise ValueError("invalid local feature arrays")
        if len(points) != len(descriptors):
            raise ValueError("local feature point/descriptor count mismatch")
        points.setflags(write=False)
        descriptors.setflags(write=False)
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "descriptors", descriptors)


@dataclass(frozen=True)
class LocalFeatureReference:
    reference_id: str
    family_id: str
    reviewed_owner: str
    signature: LocalFeatureSignature = field(repr=False, compare=False)


@dataclass(frozen=True)
class LocalFeatureSimilarity:
    score: float
    good_matches: int
    match_fraction: float
    inlier_count: int
    inlier_ratio: float


@dataclass(frozen=True)
class LocalFeatureQueryResult:
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


def extract_local_feature_signature(
    rgb: np.ndarray,
    mask: np.ndarray | None = None,
) -> LocalFeatureSignature:
    if cv2 is None or not hasattr(cv2, "SIFT_create"):
        raise RuntimeError("OpenCV SIFT is required for local decal features")
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("local decal RGB must be HxWx3+")
    image = np.clip(image[:, :, :3], 0, 255).astype(np.uint8)
    binary = np.ones(image.shape[:2], bool) if mask is None else np.asarray(mask) > 0
    if binary.shape != image.shape[:2] or not binary.any():
        raise ValueError("local decal mask must match RGB and contain pixels")
    ys, xs = np.where(binary)
    image = image[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()
    binary = binary[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    median = np.median(image[binary], axis=0).astype(np.uint8)
    image[~binary] = median
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    detector = cv2.SIFT_create(nfeatures=1200, contrastThreshold=0.01, edgeThreshold=15)
    keypoints, descriptors = detector.detectAndCompute(gray, None)
    if descriptors is None or not keypoints:
        return LocalFeatureSignature(
            points=np.empty((0, 2), np.float32),
            descriptors=np.empty((0, 128), np.float32),
            source_shape=gray.shape,
        )
    points = np.asarray([item.pt for item in keypoints], np.float32)
    return LocalFeatureSignature(points=points, descriptors=descriptors, source_shape=gray.shape)


def local_feature_similarity(
    left: LocalFeatureSignature,
    right: LocalFeatureSignature,
    *,
    ratio_threshold: float = 0.78,
) -> LocalFeatureSimilarity:
    if cv2 is None or len(left.descriptors) < 2 or len(right.descriptors) < 2:
        return LocalFeatureSimilarity(0.0, 0, 0.0, 0, 0.0)
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(left.descriptors, right.descriptors, k=2)
    good = [first for first, second in pairs if first.distance < float(ratio_threshold) * second.distance]
    # ``knnMatch`` emits at most one accepted match per descriptor in the
    # left/query signature.  Normalizing by the smaller descriptor bank can
    # therefore exceed 1.0 whenever the query has more features than the
    # reference.  Use the actual query count so this remains a calibrated,
    # bounded evidence value (and never acquires accidental extra authority).
    fraction = len(good) / float(max(1, len(pairs)))
    inliers = 0
    inlier_ratio = 0.0
    if len(good) >= 6:
        source = np.float32([left.points[item.queryIdx] for item in good])
        target = np.float32([right.points[item.trainIdx] for item in good])
        _transform, inlier_mask = cv2.findHomography(source, target, cv2.RANSAC, 4.0)
        if inlier_mask is not None:
            inliers = int(np.count_nonzero(inlier_mask))
            inlier_ratio = inliers / float(len(good))
    score = fraction * (0.55 + 0.45 * inlier_ratio) if len(good) >= 6 else 0.0
    return LocalFeatureSimilarity(
        score=round(float(score), 6),
        good_matches=len(good),
        match_fraction=round(float(fraction), 6),
        inlier_count=inliers,
        inlier_ratio=round(float(inlier_ratio), 6),
    )


def query_local_feature_library(
    query: LocalFeatureSignature,
    references: Sequence[LocalFeatureReference],
    *,
    min_similarity: float = 0.20,
    ambiguity_margin: float = 0.035,
    min_family_support: int = 2,
    min_good_matches: int = 8,
) -> LocalFeatureQueryResult:
    families: dict[str, list[tuple[LocalFeatureSimilarity, LocalFeatureReference]]] = {}
    for reference in references:
        result = local_feature_similarity(query, reference.signature)
        families.setdefault(reference.family_id, []).append((result, reference))
    ranked = []
    required = max(1, int(min_family_support))
    for family, matches in families.items():
        matches.sort(key=lambda item: (-item[0].score, item[1].reference_id))
        if len(matches) < required:
            continue
        support = matches[:required]
        if any(item[0].good_matches < int(min_good_matches) for item in support):
            continue
        owners = {item[1].reviewed_owner for item in support}
        if len(owners) != 1:
            continue
        ranked.append((min(item[0].score for item in support), family, next(iter(owners)), support))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return LocalFeatureQueryResult("abstained", None, None, 0.0, 0.0, 0.0, 0, (), "insufficient_geometric_support")
    best = ranked[0]
    runner = ranked[1][0] if len(ranked) > 1 else 0.0
    margin = best[0] - runner
    if best[0] < float(min_similarity):
        status, reason, family, owner = "abstained", "below_similarity_threshold", None, None
    elif len(ranked) > 1 and margin < float(ambiguity_margin):
        status, reason, family, owner = "abstained", "ambiguous_family_margin", None, None
    else:
        status, reason, family, owner = "corroborated", "repeated_geometric_family_match", best[1], best[2]
    return LocalFeatureQueryResult(
        status, family, owner, round(best[0], 6), round(runner, 6), round(margin, 6),
        len(best[3]), tuple(item[1].reference_id for item in best[3]), reason,
    )


__all__ = [
    "LocalFeatureQueryResult", "LocalFeatureReference", "LocalFeatureSignature",
    "LocalFeatureSimilarity", "extract_local_feature_signature",
    "local_feature_similarity", "query_local_feature_library",
]
