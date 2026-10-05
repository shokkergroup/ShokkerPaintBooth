"""Lossless semantic-object partition for Smart TGA learning.

Physical groups describe split decals well, but many real racing numbers are
already one complete instance.  This module partitions immutable instances
into either one corroborated physical group or one singleton object so a later
semantic learner sees every candidate exactly once.  Objects do not classify,
cast votes, add pixels, or own output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Mapping, Sequence

import numpy as np

from engine.spec_sculpt.decal_instances import (
    DecalCandidateInstance,
    DecalInstanceFeatures,
    encode_instance_mask_rle,
)
from engine.spec_sculpt.decal_physical_groups import (
    derive_physical_decal_groups,
    extract_physical_decal_group_features,
)


@dataclass(frozen=True)
class SemanticDecalObject:
    object_id: str
    object_kind: str
    instance_ids: tuple[str, ...]
    bbox: tuple[int, int, int, int]
    area: int
    local_mask: np.ndarray = field(repr=False, compare=False)
    physical_group_id: str | None = None

    def __post_init__(self) -> None:
        if self.object_kind not in {"physical_group", "singleton"}:
            raise ValueError("unknown semantic decal object kind")
        x, y, width, height = self.bbox
        mask = np.ascontiguousarray(np.asarray(self.local_mask) > 0)
        if min(x, y) < 0 or width <= 0 or height <= 0 or mask.shape != (height, width):
            raise ValueError("semantic decal object bbox/mask mismatch")
        if int(np.count_nonzero(mask)) != int(self.area) or not self.instance_ids:
            raise ValueError("semantic decal object must preserve exact instance pixels")
        if self.object_kind == "singleton" and len(self.instance_ids) != 1:
            raise ValueError("singleton semantic object must contain one instance")
        mask.setflags(write=False)
        object.__setattr__(self, "local_mask", mask)


@dataclass(frozen=True)
class SemanticDecalObjectFeatures:
    object_id: str
    object_kind: str
    member_count: int
    area_fraction: float
    bbox_fraction: float
    fill_ratio: float
    aspect_ratio: float
    bbox_x_fraction: float
    bbox_y_fraction: float
    bbox_width_fraction: float
    bbox_height_fraction: float
    border_distance_fraction: float
    shape_occupancy: tuple[float, ...]
    mean_edge_density: float
    max_edge_density: float
    mean_strong_gradient_fraction: float
    max_strong_gradient_fraction: float
    mean_texture_entropy: float
    max_texture_entropy: float
    max_ocr_coverage: float
    max_ocr_alpha_coverage: float
    max_digit_coverage: float
    max_ocr_token_count: int
    mean_perceptual_lightness: float
    mean_perceptual_chroma: float
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
    candidate_count: int
    source_stage_count: int
    source_count: int
    merge_reason_count: int
    gpu_model_member_fraction: float
    template_raw_member_fraction: float
    multi_proposal_member_fraction: float
    cross_owner: bool


def _object_id(instance_ids: Sequence[str]) -> str:
    digest = hashlib.blake2b("|".join(sorted(instance_ids)).encode("utf-8"), digest_size=8).hexdigest()
    return f"sdo:{digest}"


def _occupancy(mask: np.ndarray, grid: int = 4) -> tuple[float, ...]:
    height, width = mask.shape
    values = []
    for row in range(grid):
        y0, y1 = round(row * height / grid), round((row + 1) * height / grid)
        for col in range(grid):
            x0, x1 = round(col * width / grid), round((col + 1) * width / grid)
            cell = mask[y0:y1, x0:x1]
            values.append(round(float(np.mean(cell)) if cell.size else 0.0, 6))
    return tuple(values)


def derive_semantic_decal_objects(
    instances: Sequence[DecalCandidateInstance],
    features: Sequence[DecalInstanceFeatures],
    *,
    image_shape: tuple[int, int],
) -> tuple[SemanticDecalObject, ...]:
    """Partition every instance into one group or singleton; never add pixels."""
    groups = derive_physical_decal_groups(instances, features, image_shape=image_shape)
    grouped_ids = {instance_id for group in groups for instance_id in group.instance_ids}
    objects = [
        SemanticDecalObject(
            object_id=_object_id(group.instance_ids),
            object_kind="physical_group",
            instance_ids=group.instance_ids,
            bbox=group.bbox,
            area=group.area,
            local_mask=group.local_mask,
            physical_group_id=group.group_id,
        )
        for group in groups
    ]
    objects.extend(
        SemanticDecalObject(
            object_id=_object_id((instance.instance_id,)),
            object_kind="singleton",
            instance_ids=(instance.instance_id,),
            bbox=instance.bbox,
            area=instance.area,
            local_mask=instance.local_mask,
        )
        for instance in instances
        if instance.instance_id not in grouped_ids
    )
    return tuple(sorted(objects, key=lambda item: (item.bbox[1], item.bbox[0], item.object_id)))


def extract_semantic_decal_object_features(
    objects: Sequence[SemanticDecalObject],
    instances: Sequence[DecalCandidateInstance],
    features: Sequence[DecalInstanceFeatures],
    *,
    image_shape: tuple[int, int],
) -> tuple[SemanticDecalObjectFeatures, ...]:
    image_height, image_width = [int(value) for value in image_shape]
    instance_by_id = {item.instance_id: item for item in instances}
    feature_by_id = {item.instance_id: item for item in features}
    groups = derive_physical_decal_groups(instances, features, image_shape=image_shape)
    group_feature_by_id = {
        item.group_id: item for item in extract_physical_decal_group_features(
            groups, instances, features, image_shape=image_shape,
        )
    }
    output = []
    for obj in objects:
        x, y, width, height = obj.bbox
        members = [instance_by_id[instance_id] for instance_id in obj.instance_ids]
        member_features = [feature_by_id[instance_id] for instance_id in obj.instance_ids]
        candidate_ids = {value for member in members for value in member.candidate_ids}
        source_stages = {value for member in members for value in member.source_stages}
        sources = {value for member in members for value in member.sources}
        merge_reasons = {value for member in members for value in member.merge_reasons}
        member_count = float(max(1, len(members)))
        provenance = dict(
            candidate_count=len(candidate_ids),
            source_stage_count=len(source_stages),
            source_count=len(sources),
            merge_reason_count=len(merge_reasons),
            gpu_model_member_fraction=round(
                sum("gpu_model_raw" in member.source_stages for member in members) / member_count, 6,
            ),
            template_raw_member_fraction=round(
                sum("template_raw" in member.source_stages for member in members) / member_count, 6,
            ),
            multi_proposal_member_fraction=round(
                sum(len(member.candidate_ids) > 1 for member in members) / member_count, 6,
            ),
        )
        intrinsic = dict(
            mean_strong_gradient_fraction=round(float(np.mean([
                value.strong_gradient_fraction for value in member_features
            ])), 6),
            max_strong_gradient_fraction=round(float(np.max([
                value.strong_gradient_fraction for value in member_features
            ])), 6),
            max_ocr_alpha_coverage=round(float(np.max([
                value.ocr_alpha_coverage for value in member_features
            ])), 6),
            max_ocr_token_count=int(max(value.ocr_token_count for value in member_features)),
            mean_perceptual_lightness=round(float(np.mean([
                value.perceptual_lightness for value in member_features
            ])), 6),
            mean_perceptual_chroma=round(float(np.mean([
                value.perceptual_chroma for value in member_features
            ])), 6),
        )
        if obj.object_kind == "physical_group":
            item = group_feature_by_id[str(obj.physical_group_id)]
            values = dict(
                member_count=item.member_count,
                area_fraction=item.area_fraction,
                bbox_fraction=item.bbox_fraction,
                fill_ratio=item.fill_ratio,
                mean_edge_density=item.mean_edge_density,
                max_edge_density=item.max_edge_density,
                mean_texture_entropy=item.mean_texture_entropy,
                max_texture_entropy=item.max_texture_entropy,
                max_ocr_coverage=item.max_ocr_coverage,
                max_digit_coverage=item.max_digit_coverage,
                palette_role_count=item.palette_role_count,
                palette_role_entropy=item.palette_role_entropy,
                lightness_span=item.lightness_span,
                chroma_span=item.chroma_span,
                proposed_owner_count=item.proposed_owner_count,
                number_member_fraction=item.number_member_fraction,
                sponsor_member_fraction=item.sponsor_member_fraction,
                template_member_fraction=item.template_member_fraction,
                brand_graphics_member_fraction=item.brand_graphics_member_fraction,
                proposal_conflict_fraction=item.proposal_conflict_fraction,
                cross_owner=item.cross_owner,
            )
        else:
            instance = instance_by_id[obj.instance_ids[0]]
            item = feature_by_id[instance.instance_id]
            owners = set(item.proposed_owners)
            values = dict(
                member_count=1,
                area_fraction=item.area_fraction,
                bbox_fraction=round((width * height) / float(image_height * image_width), 8),
                fill_ratio=item.fill_ratio,
                mean_edge_density=item.edge_density,
                max_edge_density=item.edge_density,
                mean_texture_entropy=item.texture_entropy,
                max_texture_entropy=item.texture_entropy,
                max_ocr_coverage=item.ocr_max_coverage,
                max_digit_coverage=item.ocr_digit_coverage,
                palette_role_count=1,
                palette_role_entropy=0.0,
                lightness_span=0.0,
                chroma_span=0.0,
                proposed_owner_count=len(owners),
                number_member_fraction=float("numbers" in owners),
                sponsor_member_fraction=float("sponsors" in owners),
                template_member_fraction=float("template" in owners),
                brand_graphics_member_fraction=float("brand_graphics" in owners),
                proposal_conflict_fraction=float(item.proposal_conflict),
                cross_owner=len(owners) > 1,
            )
        output.append(SemanticDecalObjectFeatures(
            object_id=obj.object_id,
            object_kind=obj.object_kind,
            aspect_ratio=round(width / float(max(1, height)), 6),
            bbox_x_fraction=round(x / float(max(1, image_width)), 6),
            bbox_y_fraction=round(y / float(max(1, image_height)), 6),
            bbox_width_fraction=round(width / float(max(1, image_width)), 6),
            bbox_height_fraction=round(height / float(max(1, image_height)), 6),
            border_distance_fraction=round(
                max(0.0, min(x, y, image_width - x - width, image_height - y - height))
                / float(max(1, max(image_width, image_height))),
                6,
            ),
            shape_occupancy=_occupancy(obj.local_mask),
            **provenance,
            **intrinsic,
            **values,
        ))
    return tuple(output)


def semantic_decal_object_telemetry(
    instances: Sequence[DecalCandidateInstance],
    features: Sequence[DecalInstanceFeatures],
    *,
    image_shape: tuple[int, int],
    include_feature_records: bool = False,
) -> Mapping[str, object]:
    objects = derive_semantic_decal_objects(instances, features, image_shape=image_shape)
    records = extract_semantic_decal_object_features(
        objects, instances, features, image_shape=image_shape,
    )
    telemetry: dict[str, object] = {
        "schema": "smart-tga-semantic-decal-objects-v3",
        "object_count": len(objects),
        "physical_group_object_count": sum(item.object_kind == "physical_group" for item in objects),
        "singleton_object_count": sum(item.object_kind == "singleton" for item in objects),
        "partitioned_instance_count": sum(len(item.instance_ids) for item in objects),
        "partitions_instances": True,
        "adds_pixels": False,
        "casts_votes": False,
        "ownership_authority": False,
    }
    if include_feature_records:
        object_by_id = {item.object_id: item for item in objects}
        telemetry["records"] = [
            {
                **{name: getattr(item, name) for name in SemanticDecalObjectFeatures.__dataclass_fields__},
                "instance_ids": list(object_by_id[item.object_id].instance_ids),
                "physical_group_id": object_by_id[item.object_id].physical_group_id,
                "bbox": list(object_by_id[item.object_id].bbox),
                "area": object_by_id[item.object_id].area,
                "mask_rle": encode_instance_mask_rle(object_by_id[item.object_id].local_mask),
            }
            for item in records
        ]
    return telemetry


__all__ = [
    "SemanticDecalObject", "SemanticDecalObjectFeatures",
    "derive_semantic_decal_objects", "extract_semantic_decal_object_features",
    "semantic_decal_object_telemetry",
]
