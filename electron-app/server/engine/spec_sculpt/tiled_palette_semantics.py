"""Intrinsic semantic evidence for immutable tiled-palette candidates.

The feature extractor deliberately has no filename, car-id, or reviewed-bbox
inputs.  Reviewed boxes belong in offline supervision only; runtime candidates
are described by their pixels, mask geometry, proposal provenance, conflicts,
and normalized template evidence.  Scores produced from these features are
advisory until a separate acceptance gate grants output authority.
"""
from __future__ import annotations

from collections.abc import Sequence
import math

import cv2
import numpy as np


PALETTE_ROLES = (
    "light_ink",
    "dark_ink",
    "chromatic_ink",
    "minority_contrast",
    "light_neutral",
    "dark_neutral",
)


def _bbox_intersection(first: Sequence[int], second: Sequence[int]) -> int:
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by)
    )


def _canonical_d4_grid(mask: np.ndarray, size: int = 32, cells: int = 4) -> np.ndarray:
    """Return a deterministic mirror/rotation-invariant shape descriptor.

    Seven absolute Hu moments preserve global glyph structure.  Eight
    quantiles of the unordered row/column projection multiset preserve stroke
    density without selecting an orientation.  Fill contributes the sixteenth
    value.  The result is exactly invariant to every D4 transform apart from
    floating point round-off.
    """
    binary = mask.astype(np.uint8)
    hu = cv2.HuMoments(cv2.moments(binary)).reshape(-1)
    hu = -np.log10(np.maximum(np.abs(hu), 1e-30))
    row_projection = binary.mean(axis=1)
    column_projection = binary.mean(axis=0)
    projections = np.sort(np.concatenate((row_projection, column_projection)))
    quantiles = np.quantile(projections, np.linspace(0.0, 1.0, 8))
    return np.concatenate((hu, quantiles, [binary.mean()])).astype(np.float64)


def _mask_geometry(mask: np.ndarray) -> dict[str, float]:
    binary = mask.astype(np.uint8)
    area = max(1, int(np.count_nonzero(binary)))
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    perimeter = float(sum(cv2.arcLength(contour, True) for contour in contours))
    holes = 0
    hole_area = 0.0
    if hierarchy is not None:
        for contour, record in zip(contours, hierarchy[0], strict=True):
            if int(record[3]) >= 0:
                holes += 1
                hole_area += abs(float(cv2.contourArea(contour)))
    return {
        "support_pixels": float(area),
        "fill_ratio": float(area / max(1, mask.size)),
        "hole_count_log": float(math.log1p(holes)),
        "hole_area_fraction": float(hole_area / area),
        "perimeter_area_ratio": float(perimeter / math.sqrt(area)),
    }


def _pixel_features(rgb: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    pixels = rgb[mask]
    if not len(pixels):
        pixels = np.zeros((1, 3), dtype=np.uint8)
    lab = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    hsv = cv2.cvtColor(pixels.reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3).astype(np.float32)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = np.sqrt(gx * gx + gy * gy)[mask]
    luminance = lab[:, 0] / 255.0
    saturation = hsv[:, 1] / 255.0
    return {
        "light_mean": float(luminance.mean()),
        "light_std": float(luminance.std()),
        "light_q10": float(np.quantile(luminance, 0.10)),
        "light_q90": float(np.quantile(luminance, 0.90)),
        "saturation_mean": float(saturation.mean()),
        "saturation_std": float(saturation.std()),
        "chroma_mean": float(np.linalg.norm(lab[:, 1:3] - 128.0, axis=1).mean() / 181.0),
        "gradient_mean": float(gradient.mean()) if len(gradient) else 0.0,
        "gradient_std": float(gradient.std()) if len(gradient) else 0.0,
    }


def tiled_candidate_features(
    image_rgb: np.ndarray,
    candidate: dict,
    peers: Sequence[dict] = (),
) -> dict[str, float]:
    """Extract owner-neutral intrinsic features from one immutable candidate."""
    image = np.asarray(image_rgb, dtype=np.uint8)
    x, y, width, height = map(int, candidate["proposal_bbox"])
    support = np.asarray(candidate["raw_support"], dtype=bool)
    if support.shape != (height, width):
        raise ValueError("candidate raw_support does not match proposal_bbox")
    crop = image[y:y + height, x:x + width]
    if crop.shape[:2] != support.shape:
        raise ValueError("candidate bbox falls outside image")
    canvas_h, canvas_w = image.shape[:2]
    geometry = _mask_geometry(support)
    provenance = candidate.get("provenance", {})

    maximum_iou = 0.0
    maximum_containment = 0.0
    nested_count = 0
    candidate_area = max(1, width * height)
    for peer in peers:
        if peer is candidate or peer.get("proposal_id") == candidate.get("proposal_id"):
            continue
        intersection = _bbox_intersection(candidate["proposal_bbox"], peer["proposal_bbox"])
        if not intersection:
            continue
        px, py, pw, ph = map(int, peer["proposal_bbox"])
        peer_area = max(1, pw * ph)
        maximum_iou = max(maximum_iou, intersection / (candidate_area + peer_area - intersection))
        containment = intersection / min(candidate_area, peer_area)
        maximum_containment = max(maximum_containment, containment)
        if containment >= 0.90:
            nested_count += 1

    features = {
        "bbox_area_fraction_log": float(math.log1p(candidate_area) - math.log1p(canvas_h * canvas_w)),
        "support_area_fraction_log": float(math.log1p(geometry["support_pixels"]) - math.log1p(canvas_h * canvas_w)),
        "aspect_magnitude_log": float(abs(math.log(max(width, 1) / max(height, 1)))),
        "fill_ratio": geometry["fill_ratio"],
        "hole_count_log": geometry["hole_count_log"],
        "hole_area_fraction": geometry["hole_area_fraction"],
        "perimeter_area_ratio": geometry["perimeter_area_ratio"],
        "component_count_log": float(math.log1p(max(0, int(provenance.get("component_count", 1))))),
        "tile_origin_count_log": float(math.log1p(max(0, int(provenance.get("tile_origin_count", 1))))),
        "peer_d4_similarity": float(provenance.get("peer_d4_similarity", -1.0)),
        "peer_count_log": float(math.log1p(max(0, int(provenance.get("peer_count_at_0_82", 0))))),
        "template_number_fraction": float(provenance.get("template_number_fraction", 0.0)),
        "template_sponsor_fraction": float(provenance.get("template_sponsor_fraction", 0.0)),
        "assembly_support": float(provenance.get("assembly_support", 0.0)),
        "adjacency_cross_overlap": float(provenance.get("cross_axis_overlap", 0.0)),
        "adjacency_gap_fraction": float(provenance.get("gap_fraction", 1.0)),
        "conflict_max_iou": float(maximum_iou),
        "conflict_max_containment": float(maximum_containment),
        "conflict_nested_count_log": float(math.log1p(nested_count)),
        "number_block_fraction": float(provenance.get("dominant_number_block_fraction", 0.0)),
        "cross_block_best_d4_similarity": float(provenance.get("cross_block_best_d4_similarity", -1.0)),
        "cross_block_best_area_log_difference": float(provenance.get("cross_block_best_area_log_difference", 8.0)),
        "cross_block_peer_count_log": float(math.log1p(max(0, int(provenance.get("cross_block_peer_count_at_0_82", 0))))),
        "cross_block_distinct_peer_blocks": float(provenance.get("cross_block_distinct_peer_blocks", 0)),
        "cross_block_same_palette_best_similarity": float(provenance.get("cross_block_same_palette_best_similarity", -1.0)),
        # OCR remains unchanged/unavailable in this proposal stage.  Explicit
        # missingness prevents a zero from being mistaken for negative OCR.
        "ocr_coverage": 0.0,
        "ocr_available": 0.0,
    }
    features.update(_pixel_features(crop, support))
    for index, value in enumerate(_canonical_d4_grid(support)):
        features[f"shape_d4_{index:02d}"] = float(value)
    role = str(provenance.get("palette_role", ""))
    for known_role in PALETTE_ROLES:
        features[f"palette_{known_role}"] = float(role == known_role)
    features["palette_other"] = float(role not in PALETTE_ROLES)
    return features


def feature_matrix(
    image_rgb: np.ndarray,
    candidates: Sequence[dict],
    feature_names: Sequence[str] | None = None,
) -> tuple[np.ndarray, tuple[str, ...], tuple[dict[str, float], ...]]:
    """Return a stable dense matrix and the underlying immutable feature rows."""
    rows = tuple(tiled_candidate_features(image_rgb, item, candidates) for item in candidates)
    names = tuple(feature_names) if feature_names is not None else tuple(sorted({key for row in rows for key in row}))
    matrix = np.asarray([[float(row.get(name, 0.0)) for name in names] for row in rows], dtype=np.float64)
    matrix.setflags(write=False)
    return matrix, names, rows


def linear_semantic_scores(features: dict[str, float], model: dict) -> dict:
    """Apply a serialized multinomial linear scorer with explicit abstention."""
    names = tuple(model["feature_names"])
    values = np.asarray([float(features.get(name, 0.0)) for name in names], dtype=np.float64)
    mean = np.asarray(model["mean"], dtype=np.float64)
    scale = np.asarray(model["scale"], dtype=np.float64)
    coefficients = np.asarray(model["coefficients"], dtype=np.float64)
    intercept = np.asarray(model["intercept"], dtype=np.float64)
    logits = coefficients @ ((values - mean) / np.where(scale == 0.0, 1.0, scale)) + intercept
    logits -= logits.max()
    probabilities = np.exp(logits)
    probabilities /= probabilities.sum()
    classes = tuple(model["classes"])
    scores = {name: float(value) for name, value in zip(classes, probabilities, strict=True)}
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    threshold = float(model.get("abstain_probability", 0.60))
    margin = float(model.get("abstain_margin", 0.10))
    abstain = ordered[0][1] < threshold or ordered[0][1] - ordered[1][1] < margin
    return {
        "scores": scores,
        "predicted_semantic": "uncertain" if abstain else ordered[0][0],
        "abstained": bool(abstain),
        "ownership_authority": False,
    }


def forest_number_score(features: dict[str, float], model: dict) -> float:
    """Evaluate a serialized shallow forest without an sklearn dependency."""
    names = tuple(model["feature_names"])
    values = np.asarray([float(features.get(name, 0.0)) for name in names], dtype=np.float64)
    scores = []
    for tree in model["trees"]:
        node = 0
        while int(tree["feature"][node]) >= 0:
            feature_index = int(tree["feature"][node])
            node = (
                int(tree["left"][node])
                if values[feature_index] <= float(tree["threshold"][node])
                else int(tree["right"][node])
            )
        scores.append(float(tree["number_probability"][node]))
    return float(np.mean(scores)) if scores else 0.0


__all__ = [
    "feature_matrix", "forest_number_score", "linear_semantic_scores",
    "tiled_candidate_features",
]
