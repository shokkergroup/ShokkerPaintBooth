"""Immutable visual-instance relationships for Smart TGA decal evidence.

This module finds a transformed copy of a caller-supplied source region using
local feature geometry.  It does not classify the region and never mutates or
owns pixels; callers may use the returned polygon only as corroborating graph
evidence after establishing independent intrinsic authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, Sequence

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - shipped runtime includes OpenCV
    cv2 = None


@dataclass(frozen=True)
class VisualInstanceMatch:
    source_bbox: tuple[int, int, int, int]
    polygon: tuple[tuple[float, float], ...]
    good_match_count: int
    inlier_count: int
    inlier_ratio: float
    projected_area_ratio: float

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        points = np.asarray(self.polygon, np.float32)
        x0, y0 = np.floor(points.min(axis=0)).astype(int)
        x1, y1 = np.ceil(points.max(axis=0)).astype(int)
        return int(x0), int(y0), int(max(1, x1 - x0)), int(max(1, y1 - y0))


@dataclass(frozen=True)
class VisualFeatureIndex:
    """One immutable full-image feature pass reusable across decal seeds."""

    shape: tuple[int, int]
    gray: np.ndarray = field(repr=False, compare=False)
    keypoints: tuple[object, ...] = field(repr=False, compare=False)
    descriptors: np.ndarray = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        gray = np.ascontiguousarray(self.gray, dtype=np.uint8)
        descriptors = np.ascontiguousarray(self.descriptors, dtype=np.float32)
        gray.setflags(write=False)
        descriptors.setflags(write=False)
        if gray.shape != self.shape or len(self.keypoints) != len(descriptors):
            raise ValueError("visual feature index arrays do not match")
        object.__setattr__(self, "gray", gray)
        object.__setattr__(self, "descriptors", descriptors)


@dataclass(frozen=True)
class VisualComponentOverlap:
    """Geometric overlap between a match polygon and one immutable atom."""

    component_index: int
    matched_pixels: int
    polygon_fraction: float
    component_fraction: float


@dataclass(frozen=True)
class OwnerHypothesis:
    """One preserved detector hypothesis, never a resolved owner."""

    proposed_owner: str
    candidate_ids: tuple[str, ...]
    support_count: int
    max_confidence: float
    proposed_pixels: int


@dataclass(frozen=True)
class DecalCandidateInstance:
    """Owner-neutral union of raw proposals describing one probable decal.

    Instances are intentionally upstream of classification.  They preserve all
    detector hypotheses and exact proposal provenance; they do not expose an
    ``owner`` field and cannot be used as ownership authority.
    """

    instance_id: str
    bbox: tuple[int, int, int, int]
    area: int
    local_mask: np.ndarray = field(repr=False, compare=False)
    candidate_ids: tuple[str, ...]
    source_stages: tuple[str, ...]
    sources: tuple[str, ...]
    owner_hypotheses: tuple[OwnerHypothesis, ...]
    merge_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        x, y, width, height = self.bbox
        if min(x, y) < 0 or width <= 0 or height <= 0:
            raise ValueError("decal instance bbox must be positive and non-negative")
        local = np.ascontiguousarray(np.asarray(self.local_mask) > 0)
        if local.shape != (height, width):
            raise ValueError("decal instance local mask must match bbox")
        if int(np.count_nonzero(local)) != int(self.area):
            raise ValueError("decal instance area must match local mask")
        local.setflags(write=False)
        object.__setattr__(self, "local_mask", local)


@dataclass(frozen=True)
class DecalInstanceFeatures:
    """Intrinsic, owner-neutral measurements for one assembled decal."""

    instance_id: str
    area_fraction: float
    bbox_normalized: tuple[float, float, float, float]
    border_distance_fraction: float
    fill_ratio: float
    aspect_ratio: float
    shape_occupancy: tuple[float, ...]
    edge_density: float
    strong_gradient_fraction: float
    texture_entropy: float
    mean_rgb: tuple[float, float, float]
    std_rgb: tuple[float, float, float]
    perceptual_lightness: float
    perceptual_chroma: float
    perceptual_hue_degrees: float
    palette_role: str
    ocr_max_coverage: float
    ocr_alpha_coverage: float
    ocr_digit_coverage: float
    ocr_token_count: int
    proposed_owners: tuple[str, ...]
    proposal_conflict: bool


def encode_instance_mask_rle(mask: np.ndarray) -> dict[str, Any]:
    """Losslessly serialize one local boolean mask for gated corpus exports.

    Counts alternate background/foreground runs in row-major order and always
    begin with a background count (possibly zero).  This is transport only;
    it carries no semantic or ownership authority.
    """
    binary = np.ascontiguousarray(np.asarray(mask) > 0)
    if binary.ndim != 2 or not binary.size:
        raise ValueError("instance mask must be a non-empty 2D array")
    flat = binary.reshape(-1).astype(np.uint8, copy=False)
    changes = np.flatnonzero(flat[1:] != flat[:-1]) + 1
    boundaries = np.concatenate(([0], changes, [len(flat)]))
    counts = np.diff(boundaries).astype(np.int64).tolist()
    if bool(flat[0]):
        counts.insert(0, 0)
    return {
        "encoding": "binary-rle-row-major-v1",
        "shape": [int(binary.shape[0]), int(binary.shape[1])],
        "counts": counts,
    }


def decode_instance_mask_rle(record: Mapping[str, Any]) -> np.ndarray:
    """Decode and validate a mask created by :func:`encode_instance_mask_rle`."""
    if str(record.get("encoding")) != "binary-rle-row-major-v1":
        raise ValueError("unsupported instance mask encoding")
    shape = tuple(int(value) for value in (record.get("shape") or ()))
    if len(shape) != 2 or min(shape) <= 0:
        raise ValueError("instance mask RLE shape must contain two positive values")
    counts = np.asarray(record.get("counts") or (), dtype=np.int64)
    if counts.ndim != 1 or not len(counts) or np.any(counts < 0):
        raise ValueError("instance mask RLE counts must be non-negative")
    if int(counts.sum()) != int(shape[0] * shape[1]):
        raise ValueError("instance mask RLE pixel count does not match shape")
    values = np.arange(len(counts), dtype=np.uint8) & 1
    decoded = np.repeat(values, counts).astype(bool, copy=False).reshape(shape)
    decoded = np.ascontiguousarray(decoded)
    decoded.setflags(write=False)
    return decoded


def _shape_occupancy(local_mask: np.ndarray, side: int = 4) -> tuple[float, ...]:
    rows = np.array_split(np.asarray(local_mask, bool), max(1, int(side)), axis=0)
    values = []
    for row in rows:
        for cell in np.array_split(row, max(1, int(side)), axis=1):
            values.append(round(float(np.mean(cell)) if cell.size else 0.0, 6))
    return tuple(values)


def _ocr_instance_coverage(
    instance: DecalCandidateInstance,
    ocr_regions: Sequence[Any],
) -> tuple[float, float, float, int]:
    x, y, width, height = instance.bbox
    maximum = alpha = digit = 0.0
    tokens = 0
    for region in ocr_regions:
        if not isinstance(region, Mapping):
            try:
                region = vars(region)
            except TypeError:
                continue
        bbox = region.get("bbox")
        if not bbox or len(bbox) != 4:
            polygon = region.get("polygon") or ()
            if not polygon:
                continue
            points = np.asarray(polygon, np.float32)
            if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
                continue
            rx0, ry0 = np.floor(points.min(axis=0)).astype(int)
            rx1, ry1 = np.ceil(points.max(axis=0)).astype(int)
            bbox = (int(rx0), int(ry0), int(max(1, rx1 - rx0)), int(max(1, ry1 - ry0)))
        rx, ry, rw, rh = [int(value) for value in bbox]
        ix0, iy0 = max(x, rx), max(y, ry)
        ix1, iy1 = min(x + width, rx + rw), min(y + height, ry + rh)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        overlap = int(np.count_nonzero(
            instance.local_mask[iy0 - y:iy1 - y, ix0 - x:ix1 - x]
        ))
        coverage = overlap / float(max(1, instance.area))
        if coverage <= 0:
            continue
        text = str(region.get("text") or region.get("word_family") or "")
        tokens += 1
        maximum = max(maximum, coverage)
        if any(character.isalpha() for character in text):
            alpha = max(alpha, coverage)
        if any(character.isdigit() for character in text):
            digit = max(digit, coverage)
    return tuple(round(value, 6) for value in (maximum, alpha, digit)) + (tokens,)


def extract_candidate_instance_features(
    rgb: np.ndarray,
    instances: Sequence[DecalCandidateInstance],
    *,
    ocr_regions: Sequence[Any] = (),
) -> tuple[DecalInstanceFeatures, ...]:
    """Measure instances without consulting or resolving current ownership."""
    image = _coerce_rgb(rgb)
    image_height, image_width = image.shape[:2]
    image_area = float(max(1, image_height * image_width))
    features = []
    for instance in instances:
        x, y, width, height = instance.bbox
        crop = image[y:y + height, x:x + width]
        mask = instance.local_mask
        pixels = crop[mask]
        if not len(pixels):
            continue
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY) if cv2 is not None else np.mean(crop, axis=2).astype(np.uint8)
        if cv2 is not None:
            edges = cv2.Canny(gray, 60, 140) > 0
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            strong = np.hypot(gx, gy) >= 48.0
            lab_pixels = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)[mask].astype(np.float32)
            lightness = float(np.mean(lab_pixels[:, 0]) / 255.0)
            mean_a = float(np.mean(lab_pixels[:, 1]) - 128.0)
            mean_b = float(np.mean(lab_pixels[:, 2]) - 128.0)
            chroma = min(1.0, float(np.hypot(mean_a, mean_b) / 181.02))
            hue = (float(np.degrees(np.arctan2(mean_b, mean_a))) + 360.0) % 360.0
        else:  # pragma: no cover - shipped runtime includes OpenCV
            edges = np.zeros(mask.shape, bool)
            strong = np.zeros(mask.shape, bool)
            lightness = float(np.mean(gray[mask]) / 255.0)
            chroma = float(np.mean(np.ptp(pixels.astype(np.float32), axis=1)) / 255.0)
            hue = 0.0
        histogram = np.bincount((gray[mask] // 16).astype(np.int64), minlength=16).astype(np.float64)
        probability = histogram[histogram > 0] / float(max(1, histogram.sum()))
        entropy = float(-np.sum(probability * np.log2(probability)) / 4.0)
        if chroma >= 0.12:
            palette_role = "chromatic"
        elif lightness <= 0.24:
            palette_role = "dark_neutral"
        elif lightness >= 0.78:
            palette_role = "light_neutral"
        else:
            palette_role = "mid_neutral"
        ocr_max, ocr_alpha, ocr_digit, ocr_tokens = _ocr_instance_coverage(instance, ocr_regions)
        proposed_owners = tuple(item.proposed_owner for item in instance.owner_hypotheses)
        features.append(DecalInstanceFeatures(
            instance_id=instance.instance_id,
            area_fraction=round(instance.area / image_area, 8),
            bbox_normalized=(
                round(x / float(max(1, image_width)), 6),
                round(y / float(max(1, image_height)), 6),
                round(width / float(max(1, image_width)), 6),
                round(height / float(max(1, image_height)), 6),
            ),
            border_distance_fraction=round(
                max(0.0, min(x, y, image_width - x - width, image_height - y - height))
                / float(max(1, max(image_width, image_height))),
                6,
            ),
            fill_ratio=round(instance.area / float(max(1, width * height)), 6),
            aspect_ratio=round(width / float(max(1, height)), 6),
            shape_occupancy=_shape_occupancy(mask),
            edge_density=round(float(np.mean(edges[mask])), 6),
            strong_gradient_fraction=round(float(np.mean(strong[mask])), 6),
            texture_entropy=round(entropy, 6),
            mean_rgb=tuple(round(float(value), 4) for value in np.mean(pixels, axis=0)),
            std_rgb=tuple(round(float(value), 4) for value in np.std(pixels, axis=0)),
            perceptual_lightness=round(lightness, 6),
            perceptual_chroma=round(chroma, 6),
            perceptual_hue_degrees=round(hue, 4),
            palette_role=palette_role,
            ocr_max_coverage=ocr_max,
            ocr_alpha_coverage=ocr_alpha,
            ocr_digit_coverage=ocr_digit,
            ocr_token_count=ocr_tokens,
            proposed_owners=proposed_owners,
            proposal_conflict=len(proposed_owners) > 1,
        ))
    return tuple(features)


def _intersection_metrics(left: Any, right: Any) -> tuple[int, float, float, float]:
    lx, ly, lw, lh = left.bbox
    rx, ry, rw, rh = right.bbox
    x0, y0 = max(lx, rx), max(ly, ry)
    x1, y1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    if x1 <= x0 or y1 <= y0:
        return 0, 0.0, 0.0, 0.0
    left_local = left.local_mask[y0 - ly:y1 - ly, x0 - lx:x1 - lx]
    right_local = right.local_mask[y0 - ry:y1 - ry, x0 - rx:x1 - rx]
    mask_overlap = int(np.count_nonzero(left_local & right_local))
    overlap_min = mask_overlap / float(max(1, min(left.area, right.area)))
    intersection_area = (x1 - x0) * (y1 - y0)
    bbox_min = intersection_area / float(max(1, min(lw * lh, rw * rh)))
    bbox_ratio = min(lw * lh, rw * rh) / float(max(1, max(lw * lh, rw * rh)))
    return mask_overlap, overlap_min, bbox_min, bbox_ratio


def assemble_candidate_instances(
    snapshot: Any,
    *,
    min_mask_overlap: float = 0.30,
    min_bbox_containment: float = 0.90,
    min_bbox_area_ratio: float = 0.25,
    max_pairs: int = 100_000,
) -> tuple[DecalCandidateInstance, ...]:
    """Assemble overlapping raw proposals without deciding ownership.

    Only actual mask overlap or near-contained, similarly sized proposal boxes
    can join.  Mere proximity, palette resemblance, or repeated appearance is
    never sufficient, so relationships cannot manufacture a candidate.
    """
    if snapshot is None or not getattr(snapshot, "regions", ()):
        return ()
    regions = tuple(snapshot.regions)
    parents = list(range(len(regions)))
    reasons: dict[tuple[int, int], str] = {}

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    ordered = sorted(range(len(regions)), key=lambda i: (regions[i].bbox[0], regions[i].bbox[1], i))
    active: list[int] = []
    pair_count = 0
    for index in ordered:
        x, _y, _width, _height = regions[index].bbox
        active = [other for other in active if regions[other].bbox[0] + regions[other].bbox[2] > x]
        for other in active:
            if pair_count >= max(0, int(max_pairs)):
                break
            pair_count += 1
            mask_pixels, mask_overlap, bbox_containment, bbox_ratio = _intersection_metrics(
                regions[other], regions[index]
            )
            reason = ""
            if mask_pixels and mask_overlap >= float(min_mask_overlap) and (
                bbox_ratio >= float(min_bbox_area_ratio) or mask_overlap >= 0.85
            ):
                reason = "mask_overlap"
            elif (
                bbox_containment >= float(min_bbox_containment)
                and bbox_ratio >= float(min_bbox_area_ratio)
            ):
                reason = "bbox_containment"
            if reason:
                union(other, index)
                reasons[tuple(sorted((other, index)))] = reason
        active.append(index)

    grouped: dict[int, list[int]] = {}
    for index in range(len(regions)):
        grouped.setdefault(find(index), []).append(index)

    instances = []
    for members in grouped.values():
        member_regions = [regions[index] for index in members]
        x0 = min(item.bbox[0] for item in member_regions)
        y0 = min(item.bbox[1] for item in member_regions)
        x1 = max(item.bbox[0] + item.bbox[2] for item in member_regions)
        y1 = max(item.bbox[1] + item.bbox[3] for item in member_regions)
        local = np.zeros((y1 - y0, x1 - x0), bool)
        by_owner: dict[str, list[Any]] = {}
        for item in member_regions:
            x, y, width, height = item.bbox
            local[y - y0:y - y0 + height, x - x0:x - x0 + width] |= item.local_mask
            by_owner.setdefault(item.proposed_owner, []).append(item)
        candidate_ids = tuple(sorted(item.candidate_id for item in member_regions))
        digest = hashlib.blake2b("|".join(candidate_ids).encode("utf-8"), digest_size=8).hexdigest()
        hypotheses = tuple(
            OwnerHypothesis(
                proposed_owner=owner,
                candidate_ids=tuple(sorted(item.candidate_id for item in items)),
                support_count=len(items),
                max_confidence=max(float(item.confidence) for item in items),
                proposed_pixels=sum(int(item.area) for item in items),
            )
            for owner, items in sorted(by_owner.items())
        )
        member_set = set(members)
        merge_reasons = tuple(sorted({
            reason for pair, reason in reasons.items()
            if pair[0] in member_set and pair[1] in member_set
        }))
        instances.append(DecalCandidateInstance(
            instance_id=f"di:{digest}",
            bbox=(x0, y0, x1 - x0, y1 - y0),
            area=int(np.count_nonzero(local)),
            local_mask=local,
            candidate_ids=candidate_ids,
            source_stages=tuple(sorted({item.source_stage for item in member_regions})),
            sources=tuple(sorted({item.source for item in member_regions})),
            owner_hypotheses=hypotheses,
            merge_reasons=merge_reasons,
        ))
    return tuple(sorted(instances, key=lambda item: (item.bbox[1], item.bbox[0], item.instance_id)))


def candidate_instance_telemetry(
    snapshot: Any,
    *,
    rgb: np.ndarray | None = None,
    ocr_regions: Sequence[Any] = (),
    include_feature_records: bool = False,
    include_number_family_shadow: bool = False,
    include_number_context_shadow: bool = False,
    include_number_context_semantic_shadow: bool = False,
    include_number_context_position_shadow: bool = False,
) -> dict[str, Any]:
    """Compact shadow ledger for owner-neutral candidate assembly."""
    instances = assemble_candidate_instances(snapshot)
    conflicts = [item for item in instances if len(item.owner_hypotheses) > 1]
    telemetry = {
        "schema": "smart-tga-decal-candidate-instance-v1",
        "instance_count": len(instances),
        "merged_instance_count": sum(len(item.candidate_ids) > 1 for item in instances),
        "multi_owner_conflict_count": len(conflicts),
        "ownership_authority": False,
        "casts_votes": False,
        "samples": [
            {
                "instance_id": item.instance_id,
                "bbox": list(item.bbox),
                "area": item.area,
                "candidate_ids": list(item.candidate_ids),
                "owner_hypotheses": [hypothesis.proposed_owner for hypothesis in item.owner_hypotheses],
                "merge_reasons": list(item.merge_reasons),
            }
            for item in conflicts[:24]
        ],
        "samples_truncated": len(conflicts) > 24,
    }
    if rgb is not None:
        features = extract_candidate_instance_features(rgb, instances, ocr_regions=ocr_regions)
        feature_by_id = {item.instance_id: item for item in features}
        samples = []
        for instance in conflicts[:24]:
            item = feature_by_id.get(instance.instance_id)
            if item is None:
                continue
            samples.append({
                "instance_id": item.instance_id,
                "bbox_normalized": list(item.bbox_normalized),
                "border_distance_fraction": item.border_distance_fraction,
                "shape_occupancy": list(item.shape_occupancy),
                "fill_ratio": item.fill_ratio,
                "aspect_ratio": item.aspect_ratio,
                "edge_density": item.edge_density,
                "strong_gradient_fraction": item.strong_gradient_fraction,
                "texture_entropy": item.texture_entropy,
                "mean_rgb": list(item.mean_rgb),
                "std_rgb": list(item.std_rgb),
                "perceptual_lightness": item.perceptual_lightness,
                "perceptual_chroma": item.perceptual_chroma,
                "perceptual_hue_degrees": item.perceptual_hue_degrees,
                "palette_role": item.palette_role,
                "ocr_max_coverage": item.ocr_max_coverage,
                "ocr_alpha_coverage": item.ocr_alpha_coverage,
                "ocr_digit_coverage": item.ocr_digit_coverage,
                "ocr_token_count": item.ocr_token_count,
                "proposed_owners": list(item.proposed_owners),
                "proposal_conflict": item.proposal_conflict,
            })
        telemetry["features"] = {
            "schema": "smart-tga-decal-instance-features-v1",
            "feature_count": len(features),
            "shape_descriptor_side": 4,
            "mean_edge_density": round(float(np.mean([item.edge_density for item in features])), 6) if features else 0.0,
            "mean_texture_entropy": round(float(np.mean([item.texture_entropy for item in features])), 6) if features else 0.0,
            "ocr_supported_count": sum(item.ocr_max_coverage > 0 for item in features),
            "conflict_samples": samples,
            "samples_truncated": len(conflicts) > len(samples),
            "casts_votes": False,
            "ownership_authority": False,
        }
        from engine.spec_sculpt.decal_physical_groups import physical_decal_group_telemetry
        telemetry["physical_groups"] = physical_decal_group_telemetry(
            instances, features, image_shape=tuple(np.asarray(rgb).shape[:2]),
            include_feature_records=include_feature_records,
        )
        if include_number_family_shadow:
            from engine.spec_sculpt.number_family_shadow import number_family_shadow_telemetry
            telemetry["number_family_shadow"] = number_family_shadow_telemetry(instances, features)
        if include_number_context_shadow:
            from engine.spec_sculpt.number_context_shadow import number_context_shadow_telemetry
            telemetry["number_context_shadow"] = number_context_shadow_telemetry(
                instances, features, rgb=rgb,
                score_semantics=(
                    include_number_context_semantic_shadow
                    or include_number_context_position_shadow
                ),
                score_position=include_number_context_position_shadow,
                export_full=include_feature_records,
            )
        if include_feature_records:
            from engine.spec_sculpt.decal_semantic_objects import semantic_decal_object_telemetry
            telemetry["semantic_objects"] = semantic_decal_object_telemetry(
                instances, features, image_shape=tuple(np.asarray(rgb).shape[:2]),
                include_feature_records=True,
            )
        if include_feature_records:
            instance_by_id = {item.instance_id: item for item in instances}
            telemetry["features"]["records"] = [
                {
                    "instance_id": item.instance_id,
                    "bbox": list(instance_by_id[item.instance_id].bbox),
                    "mask_rle": encode_instance_mask_rle(
                        instance_by_id[item.instance_id].local_mask
                    ),
                    "candidate_ids": list(instance_by_id[item.instance_id].candidate_ids),
                    "source_stages": list(instance_by_id[item.instance_id].source_stages),
                    "sources": list(instance_by_id[item.instance_id].sources),
                    "merge_reasons": list(instance_by_id[item.instance_id].merge_reasons),
                    "area_fraction": item.area_fraction,
                    "bbox_normalized": list(item.bbox_normalized),
                    "border_distance_fraction": item.border_distance_fraction,
                    "fill_ratio": item.fill_ratio,
                    "aspect_ratio": item.aspect_ratio,
                    "shape_occupancy": list(item.shape_occupancy),
                    "edge_density": item.edge_density,
                    "strong_gradient_fraction": item.strong_gradient_fraction,
                    "texture_entropy": item.texture_entropy,
                    "mean_rgb": list(item.mean_rgb),
                    "std_rgb": list(item.std_rgb),
                    "perceptual_lightness": item.perceptual_lightness,
                    "perceptual_chroma": item.perceptual_chroma,
                    "perceptual_hue_degrees": item.perceptual_hue_degrees,
                    "palette_role": item.palette_role,
                    "ocr_max_coverage": item.ocr_max_coverage,
                    "ocr_alpha_coverage": item.ocr_alpha_coverage,
                    "ocr_digit_coverage": item.ocr_digit_coverage,
                    "ocr_token_count": item.ocr_token_count,
                    "proposed_owners": list(item.proposed_owners),
                    "proposal_conflict": item.proposal_conflict,
                }
                for item in features
            ]
    return telemetry


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


def build_visual_feature_index(rgb: np.ndarray) -> VisualFeatureIndex | None:
    """Compute full-image SIFT descriptors once for multiple seed queries."""
    if cv2 is None or not hasattr(cv2, "SIFT_create"):
        return None
    image = _coerce_rgb(rgb)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    detector = cv2.SIFT_create(nfeatures=5000, contrastThreshold=0.02, edgeThreshold=12)
    keypoints, descriptors = detector.detectAndCompute(gray, None)
    if descriptors is None or not keypoints:
        return None
    return VisualFeatureIndex(
        shape=gray.shape,
        gray=gray,
        keypoints=tuple(keypoints),
        descriptors=descriptors,
    )


def _bbox_overlap_min(left: Sequence[int], right: Sequence[int]) -> float:
    lx, ly, lw, lh = [int(value) for value in left]
    rx, ry, rw, rh = [int(value) for value in right]
    ix0, iy0 = max(lx, rx), max(ly, ry)
    ix1, iy1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    overlap = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    return overlap / float(max(1, min(lw * lh, rw * rh)))


def find_visual_instance_match(
    rgb: np.ndarray,
    source_bbox: Sequence[int],
    *,
    exclude_bboxes: Sequence[Sequence[int]] = (),
    ratio_test: float = 0.72,
    min_good_matches: int = 7,
    min_inliers: int = 6,
    min_inlier_ratio: float = 0.55,
    ransac_threshold: float = 4.0,
    feature_index: VisualFeatureIndex | None = None,
) -> VisualInstanceMatch | None:
    """Find one rotation/scale/perspective copy outside ``source_bbox``.

    SIFT is used because UV copies can be rotated, reflected by layout, and
    mildly rescaled.  Strict homography support and projected-area checks make
    this relationship abstain instead of returning weak descriptor coincidences.
    """
    if cv2 is None or not hasattr(cv2, "SIFT_create"):
        return None
    image = _coerce_rgb(rgb)
    height, width = image.shape[:2]
    x, y, box_width, box_height = [int(value) for value in source_bbox]
    if min(x, y) < 0 or box_width < 24 or box_height < 24:
        return None
    if x + box_width > width or y + box_height > height:
        raise ValueError("source_bbox exceeds rgb bounds")

    if feature_index is None:
        feature_index = build_visual_feature_index(image)
    if feature_index is None:
        return None
    if feature_index.shape != (height, width):
        raise ValueError("feature_index and rgb shapes differ")
    gray = feature_index.gray
    patch = gray[y:y + box_height, x:x + box_width]
    detector = cv2.SIFT_create(nfeatures=5000, contrastThreshold=0.02, edgeThreshold=12)
    source_points, source_descriptors = detector.detectAndCompute(patch, None)
    if source_descriptors is None or len(source_points) < min_good_matches:
        return None

    padding = max(8, int(round(0.04 * max(box_width, box_height))))
    exclusions = ((x, y, box_width, box_height), *exclude_bboxes)
    keep = np.ones(len(feature_index.keypoints), dtype=bool)
    for raw in exclusions:
        ex, ey, ew, eh = [int(value) for value in raw]
        ex0, ey0 = max(0, ex - padding), max(0, ey - padding)
        ex1, ey1 = min(width, ex + ew + padding), min(height, ey + eh + padding)
        for index, point in enumerate(feature_index.keypoints):
            px, py = point.pt
            if ex0 <= px < ex1 and ey0 <= py < ey1:
                keep[index] = False
    kept_indices = np.flatnonzero(keep)
    if len(kept_indices) < min_good_matches:
        return None
    target_points = [feature_index.keypoints[int(index)] for index in kept_indices]
    target_descriptors = feature_index.descriptors[kept_indices]

    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(source_descriptors, target_descriptors, k=2)
    good = [
        pair[0] for pair in pairs
        if len(pair) == 2 and pair[0].distance < float(ratio_test) * pair[1].distance
    ]
    if len(good) < int(min_good_matches):
        return None
    source_xy = np.float32([source_points[item.queryIdx].pt for item in good]).reshape(-1, 1, 2)
    target_xy = np.float32([target_points[item.trainIdx].pt for item in good]).reshape(-1, 1, 2)
    transform, inlier_mask = cv2.findHomography(
        source_xy, target_xy, cv2.RANSAC, float(ransac_threshold)
    )
    if transform is None or inlier_mask is None:
        return None
    inlier_count = int(np.count_nonzero(inlier_mask))
    inlier_ratio = inlier_count / float(max(1, len(good)))
    if inlier_count < int(min_inliers) or inlier_ratio < float(min_inlier_ratio):
        return None

    corners = np.float32(
        [[0, 0], [box_width, 0], [box_width, box_height], [0, box_height]]
    ).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(corners, transform).reshape(-1, 2)
    if not np.isfinite(projected).all() or not cv2.isContourConvex(projected.astype(np.float32)):
        return None
    projected_area = abs(float(cv2.contourArea(projected.astype(np.float32))))
    area_ratio = projected_area / float(max(1, box_width * box_height))
    if not 0.12 <= area_ratio <= 4.0:
        return None
    x0, y0 = np.floor(projected.min(axis=0)).astype(int)
    x1, y1 = np.ceil(projected.max(axis=0)).astype(int)
    match_bbox = (int(x0), int(y0), int(max(1, x1 - x0)), int(max(1, y1 - y0)))
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        return None
    if _bbox_overlap_min((x, y, box_width, box_height), match_bbox) > 0.10:
        return None

    return VisualInstanceMatch(
        source_bbox=(x, y, box_width, box_height),
        polygon=tuple((float(px), float(py)) for px, py in projected),
        good_match_count=len(good),
        inlier_count=inlier_count,
        inlier_ratio=round(inlier_ratio, 6),
        projected_area_ratio=round(area_ratio, 6),
    )


def visual_match_component_overlaps(
    match: VisualInstanceMatch,
    component_map: np.ndarray,
    *,
    min_pixels: int = 1,
) -> tuple[VisualComponentOverlap, ...]:
    """Map accepted match geometry onto immutable component indices.

    This adapter deliberately knows nothing about owners, evidence votes, or
    adjudication.  It only reports exact raster overlap so a caller can attach
    already-authorized relationship telemetry to existing graph nodes.
    """
    if cv2 is None:
        return ()
    components = np.asarray(component_map)
    if components.ndim != 2:
        raise ValueError("component_map must be two-dimensional")
    polygon = np.asarray(match.polygon, np.float32)
    if polygon.shape != (4, 2) or not np.isfinite(polygon).all():
        raise ValueError("match polygon must contain four finite points")
    polygon_mask = np.zeros(components.shape, np.uint8)
    cv2.fillConvexPoly(polygon_mask, np.rint(polygon).astype(np.int32), 1)
    polygon_pixels = int(np.count_nonzero(polygon_mask))
    if polygon_pixels <= 0:
        return ()
    inside = components[polygon_mask > 0]
    indices, counts = np.unique(inside[inside >= 0], return_counts=True)
    overlaps = []
    for raw_index, raw_count in zip(indices, counts):
        index = int(raw_index)
        count = int(raw_count)
        if count < max(1, int(min_pixels)):
            continue
        component_pixels = int(np.count_nonzero(components == index))
        overlaps.append(VisualComponentOverlap(
            component_index=index,
            matched_pixels=count,
            polygon_fraction=round(count / float(polygon_pixels), 6),
            component_fraction=round(count / float(max(1, component_pixels)), 6),
        ))
    return tuple(sorted(
        overlaps,
        key=lambda item: (-item.matched_pixels, item.component_index),
    ))


__all__ = [
    "DecalCandidateInstance",
    "DecalInstanceFeatures",
    "OwnerHypothesis",
    "VisualComponentOverlap",
    "VisualFeatureIndex",
    "VisualInstanceMatch",
    "assemble_candidate_instances",
    "build_visual_feature_index",
    "candidate_instance_telemetry",
    "decode_instance_mask_rle",
    "encode_instance_mask_rle",
    "extract_candidate_instance_features",
    "find_visual_instance_match",
    "visual_match_component_overlaps",
]
