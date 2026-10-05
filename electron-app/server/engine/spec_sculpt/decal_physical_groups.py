"""Immutable physical-decal groups assembled from owner-neutral instances.

Smart TGA detectors often split one printed decal into disjoint fill, outline,
shadow, and wordmark proposals.  This module records strongly supported spatial
groups while preserving every member mask exactly.  Groups do not classify,
fill gaps, cast votes, or own pixels; they are observations for later semantic
adjudication after independent authority exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Mapping, Sequence

import numpy as np

from engine.spec_sculpt.decal_instances import DecalCandidateInstance, DecalInstanceFeatures


@dataclass(frozen=True)
class PhysicalDecalGroup:
    group_id: str
    instance_ids: tuple[str, ...]
    bbox: tuple[int, int, int, int]
    area: int
    local_mask: np.ndarray = field(repr=False, compare=False)
    edge_reasons: tuple[str, ...]
    cross_owner: bool

    def __post_init__(self) -> None:
        x, y, width, height = self.bbox
        mask = np.ascontiguousarray(np.asarray(self.local_mask) > 0)
        if min(x, y) < 0 or width <= 0 or height <= 0 or mask.shape != (height, width):
            raise ValueError("physical decal group bbox/mask mismatch")
        if len(self.instance_ids) < 2 or int(np.count_nonzero(mask)) != int(self.area):
            raise ValueError("physical decal group must contain exact pixels from multiple instances")
        mask.setflags(write=False)
        object.__setattr__(self, "local_mask", mask)


@dataclass(frozen=True)
class PhysicalDecalGroupFeatures:
    """Intrinsic aggregate measurements; contains no semantic class."""

    group_id: str
    member_count: int
    area_fraction: float
    bbox_fraction: float
    fill_ratio: float
    largest_member_fraction: float
    smallest_member_fraction: float
    mean_edge_density: float
    max_edge_density: float
    mean_texture_entropy: float
    max_texture_entropy: float
    max_ocr_coverage: float
    max_digit_coverage: float
    palette_role_count: int
    palette_role_entropy: float
    lightness_span: float
    chroma_span: float
    proposed_owner_count: int
    number_member_fraction: float
    sponsor_member_fraction: float
    template_member_fraction: float
    brand_graphics_member_fraction: float
    proposal_conflict_fraction: float
    cross_owner: bool


def _hue_distance(left: float, right: float) -> float:
    difference = abs(float(left) - float(right)) % 360.0
    return min(difference, 360.0 - difference)


def _palette_compatible(left: DecalInstanceFeatures, right: DecalInstanceFeatures) -> bool:
    neutral = {"dark_neutral", "mid_neutral", "light_neutral"}
    roles_match = left.palette_role == right.palette_role or (
        left.palette_role in neutral and right.palette_role in neutral
    )
    lightness_close = abs(left.perceptual_lightness - right.perceptual_lightness) <= 0.24
    chroma_close = abs(left.perceptual_chroma - right.perceptual_chroma) <= 0.22
    if left.perceptual_chroma > 0.08 and right.perceptual_chroma > 0.08:
        hue_close = _hue_distance(left.perceptual_hue_degrees, right.perceptual_hue_degrees) <= 52.0
    else:
        hue_close = True
    return bool(lightness_close and chroma_close and hue_close and (roles_match or chroma_close))


def _pair_reasons(
    left: DecalCandidateInstance,
    right: DecalCandidateInstance,
    left_features: DecalInstanceFeatures,
    right_features: DecalInstanceFeatures,
) -> tuple[str, ...]:
    lx, ly, lw, lh = left.bbox
    rx, ry, rw, rh = right.bbox
    x_overlap = max(0, min(lx + lw, rx + rw) - max(lx, rx))
    y_overlap = max(0, min(ly + lh, ry + rh) - max(ly, ry))
    intersection = x_overlap * y_overlap
    bbox_overlap = intersection / float(max(1, min(lw * lh, rw * rh)))
    x_gap = max(0, max(lx, rx) - min(lx + lw, rx + rw))
    y_gap = max(0, max(ly, ry) - min(ly + lh, ry + rh))
    horizontal_line = (
        y_overlap / float(max(1, min(lh, rh))) >= 0.48
        and x_gap <= max(5.0, 0.55 * max(lh, rh))
        and min(lh, rh) / float(max(lh, rh)) >= 0.28
    )
    vertical_line = (
        x_overlap / float(max(1, min(lw, rw))) >= 0.48
        and y_gap <= max(5.0, 0.55 * max(lw, rw))
        and min(lw, rw) / float(max(lw, rw)) >= 0.28
    )
    left_owners = {item.proposed_owner for item in left.owner_hypotheses}
    right_owners = {item.proposed_owner for item in right.owner_hypotheses}
    shared_proposal = bool(left_owners & right_owners)
    palette = _palette_compatible(left_features, right_features)
    detail = max(
        left_features.edge_density, right_features.edge_density,
        left_features.texture_entropy, right_features.texture_entropy,
        left_features.ocr_max_coverage, right_features.ocr_max_coverage,
    ) >= 0.045

    reasons = []
    # Overlapping boxes with disjoint masks commonly represent fill/outline or
    # shadow layers.  Require proposal or palette corroboration; geometry alone
    # never creates a group.
    if bbox_overlap >= 0.08 and (shared_proposal or palette) and detail:
        reasons.append("disjoint_bbox_overlap")
    # Neighbouring glyphs/letters require all three independent signals.
    if (horizontal_line or vertical_line) and shared_proposal and palette and detail:
        reasons.append("intrinsic_aligned_palette_line")
    return tuple(reasons)


def derive_physical_decal_groups(
    instances: Sequence[DecalCandidateInstance],
    features: Sequence[DecalInstanceFeatures],
    *,
    image_shape: tuple[int, int] | None = None,
    max_bbox_fraction: float = 0.08,
    max_pairs: int = 100_000,
    max_members: int = 12,
) -> tuple[PhysicalDecalGroup, ...]:
    """Return exact-mask groups; never infer semantics or add pixels."""
    items = tuple(instances)
    feature_by_id = {item.instance_id: item for item in features}
    parents = list(range(len(items)))
    pair_reasons: dict[tuple[int, int], tuple[str, ...]] = {}

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    ordered = sorted(range(len(items)), key=lambda index: (items[index].bbox[0], items[index].bbox[1], index))
    active: list[int] = []
    pair_count = 0
    for index in ordered:
        x, _y, width, height = items[index].bbox
        reach = max(5, int(round(0.55 * max(width, height))))
        active = [
            other for other in active
            if items[other].bbox[0] + items[other].bbox[2] + max(
                reach, int(round(0.55 * max(items[other].bbox[2:])))
            ) >= x
        ]
        for other in active:
            if pair_count >= max(0, int(max_pairs)):
                break
            pair_count += 1
            left_features = feature_by_id.get(items[other].instance_id)
            right_features = feature_by_id.get(items[index].instance_id)
            if left_features is None or right_features is None:
                continue
            reasons = _pair_reasons(items[other], items[index], left_features, right_features)
            if reasons:
                pair_reasons[(other, index)] = reasons
                union(other, index)
        active.append(index)

    grouped: dict[int, list[int]] = {}
    for index in range(len(items)):
        grouped.setdefault(find(index), []).append(index)
    results = []
    for members in grouped.values():
        if len(members) < 2 or len(members) > max(2, int(max_members)):
            continue
        selected = [items[index] for index in members]
        x0 = min(item.bbox[0] for item in selected)
        y0 = min(item.bbox[1] for item in selected)
        x1 = max(item.bbox[0] + item.bbox[2] for item in selected)
        y1 = max(item.bbox[1] + item.bbox[3] for item in selected)
        if image_shape is not None:
            image_height, image_width = [int(value) for value in image_shape]
            if min(image_height, image_width) <= 0:
                raise ValueError("physical decal image shape must be positive")
            bbox_fraction = ((x1 - x0) * (y1 - y0)) / float(image_height * image_width)
            if bbox_fraction > float(max_bbox_fraction):
                continue
        union_mask = np.zeros((y1 - y0, x1 - x0), bool)
        owners = set()
        for item in selected:
            x, y, width, height = item.bbox
            union_mask[y - y0:y - y0 + height, x - x0:x - x0 + width] |= item.local_mask
            owners.update(hypothesis.proposed_owner for hypothesis in item.owner_hypotheses)
        instance_ids = tuple(sorted(item.instance_id for item in selected))
        digest = hashlib.blake2b("|".join(instance_ids).encode("utf-8"), digest_size=8).hexdigest()
        member_set = set(members)
        reasons = tuple(sorted({
            reason
            for pair, values in pair_reasons.items()
            if pair[0] in member_set and pair[1] in member_set
            for reason in values
        }))
        results.append(PhysicalDecalGroup(
            group_id=f"pdg:{digest}",
            instance_ids=instance_ids,
            bbox=(x0, y0, x1 - x0, y1 - y0),
            area=int(np.count_nonzero(union_mask)),
            local_mask=union_mask,
            edge_reasons=reasons,
            cross_owner=len(owners) > 1,
        ))
    return tuple(sorted(results, key=lambda item: (item.bbox[1], item.bbox[0], item.group_id)))


def extract_physical_decal_group_features(
    groups: Sequence[PhysicalDecalGroup],
    instances: Sequence[DecalCandidateInstance],
    features: Sequence[DecalInstanceFeatures],
    *,
    image_shape: tuple[int, int],
) -> tuple[PhysicalDecalGroupFeatures, ...]:
    """Aggregate immutable member evidence without selecting a class."""
    image_height, image_width = [int(value) for value in image_shape]
    if min(image_height, image_width) <= 0:
        raise ValueError("group feature image shape must be positive")
    instance_by_id = {item.instance_id: item for item in instances}
    feature_by_id = {item.instance_id: item for item in features}
    output = []
    for group in groups:
        member_instances = [instance_by_id[item] for item in group.instance_ids]
        member_features = [feature_by_id[item] for item in group.instance_ids]
        member_areas = np.asarray([item.area for item in member_instances], np.float64)
        total_member_area = float(max(1.0, member_areas.sum()))
        role_counts: dict[str, int] = {}
        owners = set()
        for item in member_features:
            role_counts[item.palette_role] = role_counts.get(item.palette_role, 0) + 1
            owners.update(item.proposed_owners)
        probabilities = np.asarray(list(role_counts.values()), np.float64) / float(len(member_features))
        entropy = float(-np.sum(probabilities * np.log2(np.maximum(probabilities, 1e-12))))
        max_entropy = float(np.log2(max(2, len(role_counts))))
        x, y, width, height = group.bbox

        def owner_fraction(owner: str) -> float:
            return sum(owner in item.proposed_owners for item in member_features) / float(len(member_features))

        output.append(PhysicalDecalGroupFeatures(
            group_id=group.group_id,
            member_count=len(member_features),
            area_fraction=round(group.area / float(image_height * image_width), 8),
            bbox_fraction=round((width * height) / float(image_height * image_width), 8),
            fill_ratio=round(group.area / float(max(1, width * height)), 6),
            largest_member_fraction=round(float(member_areas.max() / total_member_area), 6),
            smallest_member_fraction=round(float(member_areas.min() / total_member_area), 6),
            mean_edge_density=round(float(np.mean([item.edge_density for item in member_features])), 6),
            max_edge_density=round(float(np.max([item.edge_density for item in member_features])), 6),
            mean_texture_entropy=round(float(np.mean([item.texture_entropy for item in member_features])), 6),
            max_texture_entropy=round(float(np.max([item.texture_entropy for item in member_features])), 6),
            max_ocr_coverage=round(float(np.max([item.ocr_max_coverage for item in member_features])), 6),
            max_digit_coverage=round(float(np.max([item.ocr_digit_coverage for item in member_features])), 6),
            palette_role_count=len(role_counts),
            palette_role_entropy=round(entropy / max_entropy if max_entropy else 0.0, 6),
            lightness_span=round(float(np.ptp([item.perceptual_lightness for item in member_features])), 6),
            chroma_span=round(float(np.ptp([item.perceptual_chroma for item in member_features])), 6),
            proposed_owner_count=len(owners),
            number_member_fraction=round(owner_fraction("numbers"), 6),
            sponsor_member_fraction=round(owner_fraction("sponsors"), 6),
            template_member_fraction=round(owner_fraction("template"), 6),
            brand_graphics_member_fraction=round(owner_fraction("brand_graphics"), 6),
            proposal_conflict_fraction=round(sum(item.proposal_conflict for item in member_features) / float(len(member_features)), 6),
            cross_owner=group.cross_owner,
        ))
    return tuple(output)


def physical_decal_group_telemetry(
    instances: Sequence[DecalCandidateInstance],
    features: Sequence[DecalInstanceFeatures],
    *,
    image_shape: tuple[int, int] | None = None,
    include_feature_records: bool = False,
    max_samples: int = 40,
) -> Mapping[str, object]:
    groups = derive_physical_decal_groups(instances, features, image_shape=image_shape)
    reason_counts: dict[str, int] = {}
    for group in groups:
        for reason in group.edge_reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    telemetry: dict[str, object] = {
        "schema": "smart-tga-physical-decal-groups-v1",
        "group_count": len(groups),
        "grouped_instance_count": sum(len(item.instance_ids) for item in groups),
        "cross_owner_group_count": sum(item.cross_owner for item in groups),
        "reason_counts": dict(sorted(reason_counts.items())),
        "samples": [
            {
                "group_id": item.group_id,
                "instance_ids": list(item.instance_ids),
                "bbox": list(item.bbox),
                "area": item.area,
                "member_count": len(item.instance_ids),
                "edge_reasons": list(item.edge_reasons),
                "cross_owner": item.cross_owner,
            }
            for item in groups[:max(0, int(max_samples))]
        ],
        "samples_truncated": len(groups) > max(0, int(max_samples)),
        "adds_pixels": False,
        "casts_votes": False,
        "ownership_authority": False,
    }
    if image_shape is not None:
        group_features = extract_physical_decal_group_features(
            groups, instances, features, image_shape=image_shape,
        )
        telemetry["features"] = {
            "schema": "smart-tga-physical-decal-group-features-v1",
            "feature_count": len(group_features),
            "mean_fill_ratio": round(float(np.mean([item.fill_ratio for item in group_features])), 6) if group_features else 0.0,
            "mean_palette_role_entropy": round(float(np.mean([item.palette_role_entropy for item in group_features])), 6) if group_features else 0.0,
            "casts_votes": False,
            "ownership_authority": False,
        }
        if include_feature_records:
            telemetry["features"]["records"] = [
                {
                    field_name: getattr(item, field_name)
                    for field_name in PhysicalDecalGroupFeatures.__dataclass_fields__
                }
                for item in group_features
            ]
    return telemetry


__all__ = [
    "PhysicalDecalGroup",
    "PhysicalDecalGroupFeatures",
    "derive_physical_decal_groups",
    "extract_physical_decal_group_features",
    "physical_decal_group_telemetry",
]
