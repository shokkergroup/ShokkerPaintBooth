"""Join lossless semantic-object features to durable human review labels.

This is offline corpus tooling.  It never casts votes or supplies runtime
ownership.  Exact physical-group reviews are joined by group id; indexed final
component reviews are conservatively linked by bbox overlap so clean atomic
numbers are represented alongside split decal groups.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import cv2
import numpy as np

OWNERS = {"numbers", "sponsors", "template", "paint", "uncertain"}


def _decode_mask_rle(record: dict[str, Any]) -> np.ndarray:
    if str(record.get("encoding")) != "binary-rle-row-major-v1":
        raise ValueError("unsupported semantic object mask encoding")
    shape = tuple(int(value) for value in (record.get("shape") or ()))
    counts = np.asarray(record.get("counts") or (), dtype=np.int64)
    if len(shape) != 2 or min(shape) <= 0 or counts.ndim != 1 or not len(counts) or np.any(counts < 0):
        raise ValueError("invalid semantic object mask RLE")
    if int(counts.sum()) != int(shape[0] * shape[1]):
        raise ValueError("semantic object mask RLE pixel count mismatch")
    decoded = np.repeat(np.arange(len(counts), dtype=np.uint8) & 1, counts).astype(bool).reshape(shape)
    decoded = np.ascontiguousarray(decoded)
    decoded.setflags(write=False)
    return decoded


def _mask_topology_features(record: dict[str, Any]) -> dict[str, float | int]:
    """Measure exact object shape without assigning a semantic owner."""
    mask = _decode_mask_rle(record)
    binary = np.ascontiguousarray(mask, dtype=np.uint8)
    area = int(np.count_nonzero(binary))
    if area <= 0:
        raise ValueError("semantic object topology requires non-empty mask")
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, 8)
    component_areas = stats[1:, cv2.CC_STAT_AREA].astype(np.int64)
    rectangular_area = 0
    for index in range(1, count):
        width = int(stats[index, cv2.CC_STAT_WIDTH])
        height = int(stats[index, cv2.CC_STAT_HEIGHT])
        component_area = int(stats[index, cv2.CC_STAT_AREA])
        if component_area / float(max(1, width * height)) >= 0.90:
            rectangular_area += component_area
    inverse = np.ascontiguousarray(~mask, dtype=np.uint8)
    background_count, background_labels = cv2.connectedComponents(inverse, 8)
    border_ids = set(np.unique(background_labels[0])) | set(np.unique(background_labels[-1]))
    border_ids |= set(np.unique(background_labels[:, 0])) | set(np.unique(background_labels[:, -1]))
    hole_count = sum(index not in border_ids for index in range(1, background_count))
    eroded = cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=1)
    boundary_area = int(np.count_nonzero(binary & (1 - eroded)))
    return {
        "topology_component_count": int(max(0, count - 1)),
        "topology_largest_component_fraction": round(float(component_areas.max()) / area, 6),
        "topology_hole_count": int(hole_count),
        "topology_boundary_fraction": round(boundary_area / float(area), 6),
        "topology_full_row_fraction": round(float(np.mean(np.mean(mask, axis=1) >= 0.90)), 6),
        "topology_full_column_fraction": round(float(np.mean(np.mean(mask, axis=0) >= 0.90)), 6),
        "topology_rectangular_component_fraction": round(rectangular_area / float(area), 6),
    }


def _mask_geometry_features(record: dict[str, Any]) -> dict[str, float]:
    """Describe exact mask geometry without encoding a class decision.

    These compact descriptors complement the coarse 4x4 occupancy grid.  They
    are translation independent, size normalized where appropriate, and remain
    offline evidence only.  In particular, they do not recognize a number or
    logo and cannot manufacture ownership authority.
    """
    mask = _decode_mask_rle(record)
    binary = np.ascontiguousarray(mask, dtype=np.uint8)
    area = float(np.count_nonzero(binary))
    if area <= 0:
        raise ValueError("semantic object geometry requires non-empty mask")
    contours, _hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    perimeter = float(sum(cv2.arcLength(contour, True) for contour in contours))
    hull_area = float(sum(max(1.0, cv2.contourArea(cv2.convexHull(contour))) for contour in contours))
    hu = cv2.HuMoments(cv2.moments(binary)).reshape(-1)
    # A cropped mask may be entirely foreground (especially a 1px proposal).
    # OpenCV then has no background seed and can return float32 maxima.  A
    # synthetic zero border makes the metric finite without changing the mask.
    padded = np.pad(binary, 1, mode="constant", constant_values=0)
    distance = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1]
    inside_distance = distance[mask]
    thickness_scale = float(max(1, min(mask.shape)))
    horizontal_union = np.logical_or(mask, mask[:, ::-1])
    vertical_union = np.logical_or(mask, mask[::-1, :])
    values = {
        "geometry_solidity": area / max(area, hull_area),
        "geometry_perimeter_sqrt_area": perimeter / max(1.0, float(np.sqrt(area))),
        "geometry_compactness": min(
            1.0, (4.0 * float(np.pi) * area) / max(1.0, perimeter * perimeter)
        ),
        "geometry_horizontal_symmetry": (
            float(np.count_nonzero(mask & mask[:, ::-1]))
            / float(max(1, np.count_nonzero(horizontal_union)))
        ),
        "geometry_vertical_symmetry": (
            float(np.count_nonzero(mask & mask[::-1, :]))
            / float(max(1, np.count_nonzero(vertical_union)))
        ),
        "geometry_thickness_mean": float(np.mean(inside_distance)) / thickness_scale,
        "geometry_thickness_max": float(np.max(inside_distance)) / thickness_scale,
    }
    for index, moment in enumerate(hu, start=1):
        values[f"geometry_hu_log_{index}"] = float(
            -np.sign(moment) * np.log10(abs(float(moment)) + 1e-30)
        )
    return {name: round(value, 6) for name, value in values.items()}


def _iter_group_labels(document: dict[str, Any]):
    yield from document.get("group_labels") or ()
    target_sets = document.get("paint_group_targets") or {}
    if not target_sets:
        return
    audit_path = str(document.get("physical_group_audit") or "")
    if not audit_path:
        raise ValueError("compact group review requires physical_group_audit")
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    paints = {str(item["paint_label"]): item for item in audit.get("paints") or ()}
    for paint_label, decisions in target_sets.items():
        groups = list((paints.get(str(paint_label)) or {}).get("groups") or ())
        if len(groups) != len(decisions):
            raise ValueError(
                f"compact group review count mismatch for {paint_label}: "
                f"{len(decisions)} decisions for {len(groups)} groups"
            )
        for group, decision in zip(groups, decisions):
            values = {"target_layer": decision} if isinstance(decision, str) else dict(decision)
            target = str(values.get("target_layer") or "")
            if target not in OWNERS:
                raise ValueError(f"unknown compact group target {target!r} for {paint_label}")
            yield {"paint_label": paint_label, "group_id": group["group_id"], **values}


def _bbox_overlap_min(left: Sequence[int], right: Sequence[int]) -> float:
    lx, ly, lw, lh = [int(value) for value in left]
    rx, ry, rw, rh = [int(value) for value in right]
    ix0, iy0 = max(lx, rx), max(ly, ry)
    ix1, iy1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    overlap = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    return overlap / float(max(1, min(lw * lh, rw * rh)))


def _mask_overlap_min(
    left_bbox: Sequence[int], left_mask: np.ndarray,
    right_bbox: Sequence[int], right_mask: np.ndarray,
) -> float:
    lx, ly, lw, lh = [int(value) for value in left_bbox]
    rx, ry, rw, rh = [int(value) for value in right_bbox]
    if np.asarray(left_mask).shape != (lh, lw) or np.asarray(right_mask).shape != (rh, rw):
        raise ValueError("semantic review mask/bbox mismatch")
    ix0, iy0 = max(lx, rx), max(ly, ry)
    ix1, iy1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    if ix0 >= ix1 or iy0 >= iy1:
        return 0.0
    left = np.asarray(left_mask, dtype=bool)[iy0 - ly:iy1 - ly, ix0 - lx:ix1 - lx]
    right = np.asarray(right_mask, dtype=bool)[iy0 - ry:iy1 - ry, ix0 - rx:ix1 - rx]
    overlap = int(np.count_nonzero(left & right))
    denominator = min(int(np.count_nonzero(left_mask)), int(np.count_nonzero(right_mask)))
    return overlap / float(max(1, denominator))


def _review_component_mask(mask_path: str, bbox: Sequence[int]) -> np.ndarray | None:
    source = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if source is None:
        return None
    binary = np.ascontiguousarray(source > 0, dtype=np.uint8)
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    expected = tuple(int(value) for value in bbox)
    for index in range(1, count):
        actual = tuple(int(value) for value in stats[index, :4])
        if actual == expected:
            x, y, width, height = expected
            component = np.ascontiguousarray(_labels[y:y + height, x:x + width] == index)
            component.setflags(write=False)
            return component
    return None


def _attach_cross_copy_similarity_features(rows: list[dict[str, Any]]) -> None:
    """Measure immutable within-paint visual siblings without assigning an owner."""
    rows_by_paint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_paint[str(row.get("paint_label") or "")].append(row)
    defaults = {
        "cross_copy_max_similarity": 0.0,
        "cross_copy_shape_similarity": 0.0,
        "cross_copy_palette_similarity": 0.0,
        "cross_copy_peer_count_070": 0.0,
        "cross_copy_mean_top3_similarity": 0.0,
        "cross_copy_number_anchor_max_similarity": 0.0,
        "cross_copy_number_anchor_peer_count_070": 0.0,
        "cross_copy_sponsor_anchor_max_similarity": 0.0,
        "cross_copy_sponsor_anchor_peer_count_070": 0.0,
        "cross_copy_template_anchor_max_similarity": 0.0,
        "cross_copy_template_anchor_peer_count_070": 0.0,
    }
    for paint_rows in rows_by_paint.values():
        for row in paint_rows:
            row.update(defaults)
        if len(paint_rows) < 2:
            continue
        grids = np.zeros((len(paint_rows), 4, 4), dtype=np.float32)
        valid = np.zeros(len(paint_rows), dtype=bool)
        for index, row in enumerate(paint_rows):
            occupancy = np.asarray(row.get("shape_occupancy") or (), dtype=np.float32)
            if occupancy.size == 16 and np.all(np.isfinite(occupancy)) and np.any(occupancy > 0):
                grids[index] = occupancy.reshape(4, 4)
                valid[index] = True
        flat = grids.reshape(len(paint_rows), -1)
        norms = np.linalg.norm(flat, axis=1)
        normalized = np.divide(
            flat, norms[:, None], out=np.zeros_like(flat), where=norms[:, None] > 1e-8,
        )
        shape_similarity = np.zeros((len(paint_rows), len(paint_rows)), dtype=np.float32)
        # Compare all rotations and reflections because UV-mapped number copies
        # may be upside-down or mirrored on the source texture.
        for turns in range(4):
            rotated = np.rot90(grids, turns, axes=(1, 2))
            for variant in (rotated, np.flip(rotated, axis=2)):
                variant_flat = variant.reshape(len(paint_rows), -1)
                variant_norms = np.linalg.norm(variant_flat, axis=1)
                variant_normalized = np.divide(
                    variant_flat, variant_norms[:, None], out=np.zeros_like(variant_flat),
                    where=variant_norms[:, None] > 1e-8,
                )
                shape_similarity = np.maximum(shape_similarity, normalized @ variant_normalized.T)
        shape_similarity[~valid, :] = 0.0
        shape_similarity[:, ~valid] = 0.0
        area = np.maximum(1e-9, np.asarray([
            float(row.get("area_fraction") or row.get("bbox_fraction") or 0.0)
            for row in paint_rows
        ], dtype=np.float32))
        area_similarity = np.minimum(area[:, None], area[None, :]) / np.maximum(area[:, None], area[None, :])
        aspect = np.maximum(1e-6, np.asarray([
            float(row.get("aspect_ratio") or 1.0) for row in paint_rows
        ], dtype=np.float32))
        aspect = np.minimum(aspect, 1.0 / aspect)
        aspect_similarity = np.minimum(aspect[:, None], aspect[None, :]) / np.maximum(aspect[:, None], aspect[None, :])
        palette = np.asarray([[
            float(row.get("mean_perceptual_lightness") or 0.0),
            float(row.get("mean_perceptual_chroma") or 0.0),
            float(row.get("lightness_span") or 0.0),
            float(row.get("chroma_span") or 0.0),
        ] for row in paint_rows], dtype=np.float32)
        palette_similarity = np.clip(
            1.0 - np.mean(np.abs(palette[:, None, :] - palette[None, :, :]), axis=2), 0.0, 1.0,
        )
        combined = shape_similarity * (0.4 + 0.6 * palette_similarity)
        combined *= np.sqrt(area_similarity * aspect_similarity)
        np.fill_diagonal(combined, -1.0)
        proposal_anchor_masks = {
            "number": np.asarray([
                float(row.get("number_member_fraction") or 0.0) > 0.0 for row in paint_rows
            ], dtype=bool),
            "sponsor": np.asarray([
                float(row.get("sponsor_member_fraction") or 0.0) > 0.0 for row in paint_rows
            ], dtype=bool),
            "template": np.asarray([
                float(row.get("template_member_fraction") or 0.0) > 0.0 for row in paint_rows
            ], dtype=bool),
        }
        for index, row in enumerate(paint_rows):
            best = int(np.argmax(combined[index]))
            positive = np.sort(combined[index][combined[index] >= 0.0])
            top = positive[-3:] if positive.size else np.asarray([0.0], dtype=np.float32)
            row["cross_copy_max_similarity"] = round(max(0.0, float(combined[index, best])), 6)
            row["cross_copy_shape_similarity"] = round(float(shape_similarity[index, best]), 6)
            row["cross_copy_palette_similarity"] = round(float(palette_similarity[index, best]), 6)
            row["cross_copy_peer_count_070"] = float(np.count_nonzero(combined[index] >= 0.70))
            row["cross_copy_mean_top3_similarity"] = round(float(np.mean(top)), 6)
            for owner, anchor_mask in proposal_anchor_masks.items():
                eligible = anchor_mask.copy()
                eligible[index] = False
                values = combined[index, eligible]
                row[f"cross_copy_{owner}_anchor_max_similarity"] = round(
                    max(0.0, float(values.max())) if values.size else 0.0, 6
                )
                row[f"cross_copy_{owner}_anchor_peer_count_070"] = float(
                    np.count_nonzero(values >= 0.70)
                )


def build_bank(inspections: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    mask_paths_by_paint = {}
    for inspection in inspections:
        paint_label = str(inspection.get("paint_label") or "")
        source_path = Path(str(inspection.get("source_1024") or ""))
        source_content_id = (
            "src:" + hashlib.blake2b(source_path.read_bytes(), digest_size=16).hexdigest()
            if source_path.is_file()
            else "paint:" + paint_label
        )
        mask_paths_by_paint[paint_label] = dict(inspection.get("mask_paths") or {})
        objects = (
            (inspection.get("route_adjudicator_shadow") or {})
            .get("candidate_evidence", {}).get("decal_instances", {})
            .get("semantic_objects", {})
        )
        group_feature_records = (
            (inspection.get("route_adjudicator_shadow") or {})
            .get("candidate_evidence", {}).get("decal_instances", {})
            .get("physical_groups", {}).get("features", {}).get("records", ())
        )
        group_features = {
            str(item.get("group_id") or ""): item for item in group_feature_records
            if item.get("group_id")
        }
        instance_feature_records = (
            (inspection.get("route_adjudicator_shadow") or {})
            .get("candidate_evidence", {}).get("decal_instances", {})
            .get("features", {}).get("records", ())
        )
        instance_features = {
            str(item.get("instance_id") or ""): item for item in instance_feature_records
            if item.get("instance_id")
        }
        if objects.get("casts_votes") or objects.get("ownership_authority") or objects.get("adds_pixels"):
            raise ValueError(f"semantic object export claimed authority for {paint_label}")
        records = objects.get("records")
        if records is None:
            raise ValueError(f"semantic object records missing for {paint_label}")
        for item in records:
            row = {
                "paint_label": paint_label,
                "source_content_id": source_content_id,
                **dict(item),
            }
            member_count = max(1.0, float(row.get("member_count") or 1.0))
            candidate_count = float(row.get("candidate_count") or member_count)
            object_instances = [
                instance_features[str(instance_id)]
                for instance_id in row.get("instance_ids") or ()
                if str(instance_id) in instance_features
            ]
            origin_denominator = float(max(1, len(object_instances)))
            row["instance_origin_feature_available"] = float(bool(object_instances))
            row["appearance_quantized_instance_fraction"] = round(sum(
                "appearance_quantized_raw" in set(item.get("source_stages") or ())
                for item in object_instances
            ) / origin_denominator, 6)
            row["unassigned_instance_fraction"] = round(sum(
                "unassigned" in set(item.get("proposed_owners") or ())
                for item in object_instances
            ) / origin_denominator, 6)
            row["appearance_unassigned_instance_fraction"] = round(sum(
                "appearance_quantized_raw" in set(item.get("source_stages") or ())
                and "unassigned" in set(item.get("proposed_owners") or ())
                for item in object_instances
            ) / origin_denominator, 6)
            # Owner-neutral assembly provenance. These facts describe how the
            # immutable object was formed; they do not inspect its review label
            # and therefore remain safe model inputs rather than target leaks.
            row["physical_group_indicator"] = float(
                str(row.get("object_kind") or "") == "physical_group"
            )
            row["candidate_member_ratio"] = round(candidate_count / member_count, 6)
            row["candidate_member_excess"] = max(0.0, candidate_count - member_count)
            # Immutable object-completion evidence. A singleton is exactly one
            # complete member. Physical groups use exported member-area shares
            # to distinguish one dominant decal plus crumbs from a fragmented
            # many-part assembly. Missing exports are explicit, never guessed.
            if str(row.get("object_kind") or "") == "singleton":
                largest_member_fraction = smallest_member_fraction = 1.0
                completion_available = 1.0
            else:
                group = group_features.get(str(row.get("physical_group_id") or ""))
                completion_available = float(group is not None)
                largest_member_fraction = float((group or {}).get("largest_member_fraction") or 0.0)
                smallest_member_fraction = float((group or {}).get("smallest_member_fraction") or 0.0)
            row["completion_feature_available"] = completion_available
            row["largest_member_fraction"] = round(largest_member_fraction, 6)
            row["smallest_member_fraction"] = round(smallest_member_fraction, 6)
            row["member_area_balance"] = round(
                smallest_member_fraction / largest_member_fraction
                if largest_member_fraction > 0.0 else 0.0, 6
            )
            row["member_fragmentation"] = round(max(0.0, 1.0 - largest_member_fraction), 6)
            # Missingness-aware completion evidence. The first completion
            # experiment represented every singleton as 100% dominant, which
            # lets a model confuse object kind with assembly quality. Keep the
            # original ablation reproducible, but also export a group-only
            # family where singleton values are explicitly not applicable.
            is_physical_group = str(row.get("object_kind") or "") == "physical_group"
            group_completion_available = float(is_physical_group and completion_available > 0.0)
            row["group_completion_feature_available"] = group_completion_available
            row["group_largest_member_fraction"] = round(
                largest_member_fraction if group_completion_available else 0.0, 6
            )
            row["group_smallest_member_fraction"] = round(
                smallest_member_fraction if group_completion_available else 0.0, 6
            )
            row["group_member_area_balance"] = round(
                row["member_area_balance"] if group_completion_available else 0.0, 6
            )
            row["group_member_fragmentation"] = round(
                row["member_fragmentation"] if group_completion_available else 0.0, 6
            )
            if row.get("mask_rle"):
                row.update(_mask_topology_features(row["mask_rle"]))
                row.update(_mask_geometry_features(row["mask_rle"]))
            rows.append(row)
    _attach_cross_copy_similarity_features(rows)
    return {
        "schema": "smart-tga-semantic-object-bank-v3",
        "paint_count": len({item["paint_label"] for item in rows}),
        "source_content_count": len({item["source_content_id"] for item in rows}),
        "object_count": len(rows),
        "casts_votes": False,
        "ownership_authority": False,
        "mask_paths_by_paint": mask_paths_by_paint,
        "records": rows,
    }


def attach_reviews(
    bank: dict[str, Any],
    component_documents: Sequence[dict[str, Any]],
    group_documents: Sequence[dict[str, Any]],
    *,
    min_overlap: float = 0.55,
    ambiguity_margin: float = 0.08,
) -> dict[str, Any]:
    by_paint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in bank.get("records") or ():
        by_paint[str(record["paint_label"])].append(record)
    evidence: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    links = []
    component_mask_cache: dict[tuple[str, str, tuple[int, ...]], np.ndarray | None] = {}

    for document in group_documents:
        for label in _iter_group_labels(document):
            paint_label = str(label.get("paint_label") or "")
            group_id = str(label.get("group_id") or "")
            matches = [item for item in by_paint.get(paint_label, ()) if item.get("physical_group_id") == group_id]
            object_id = matches[0]["object_id"] if len(matches) == 1 else None
            status = "matched_for_review" if object_id else "unmatched"
            link = {
                "paint_label": paint_label, "source": "physical_group", "group_id": group_id,
                "target_layer": label.get("target_layer"), "family_id": label.get("family_id"),
                "label": label.get("label"), "object_id": object_id, "status": status,
            }
            links.append(link)
            if object_id:
                evidence[(paint_label, str(object_id))].append(link)

    for document in component_documents:
        # Some reviews are already tied to an immutable instance id.  Preserve
        # that exact human link instead of degrading it back to bbox matching.
        # Semantic objects partition instances, so a reviewed singleton or
        # grouped member must resolve to exactly one object or abstain.
        for label in document.get("instance_labels") or ():
            paint_label = str(label.get("paint_label") or document.get("paint_label") or "")
            instance_id = str(label.get("instance_id") or "")
            matches = [
                item for item in by_paint.get(paint_label, ())
                if instance_id and instance_id in {str(value) for value in item.get("instance_ids") or ()}
            ]
            if len(matches) == 1:
                expected_bbox = label.get("bbox") or ()
                bbox_ok = not expected_bbox or list(matches[0].get("bbox") or ()) == list(expected_bbox)
                object_id = matches[0]["object_id"] if bbox_ok else None
                status = "matched_for_review" if bbox_ok else "bbox_mismatch"
            else:
                object_id = None
                status = "ambiguous" if len(matches) > 1 else "unmatched"
            link = {
                "paint_label": paint_label, "source": "reviewed_instance",
                "instance_id": instance_id, "expected_bbox": list(label.get("bbox") or ()),
                "target_layer": label.get("target_layer"), "family_id": label.get("family_id"),
                "label": label.get("label"), "object_id": object_id, "status": status,
                "match_method": "exact_instance_id",
            }
            links.append(link)
            if object_id and label.get("target_layer") in OWNERS:
                evidence[(paint_label, str(object_id))].append(link)

        paint_label = str(document.get("paint_label") or "")
        objects = by_paint.get(paint_label, ())
        for label in document.get("component_labels") or ():
            # Indexed final components are exact reviews. Candidate/freehand
            # boxes remain useful ledger context but do not train objects.
            if label.get("component_index") is None or label.get("target_layer") not in OWNERS:
                continue
            bbox = label.get("expected_bbox") or ()
            layer = str(label.get("layer") or "")
            mask_path = str((bank.get("mask_paths_by_paint") or {}).get(paint_label, {}).get(layer) or "")
            cache_key = (paint_label, layer, tuple(int(value) for value in bbox))
            if cache_key not in component_mask_cache:
                component_mask_cache[cache_key] = _review_component_mask(mask_path, bbox) if mask_path else None
            component_mask = component_mask_cache[cache_key]
            exact_masks = component_mask is not None and all(item.get("mask_rle") for item in objects)
            ranked = sorted(
                ((
                    _mask_overlap_min(
                        bbox, component_mask,
                        item.get("bbox") or (0, 0, 0, 0), _decode_mask_rle(item["mask_rle"]),
                    ) if exact_masks else _bbox_overlap_min(bbox, item.get("bbox") or (0, 0, 0, 0)),
                    item,
                ) for item in objects),
                key=lambda pair: (-pair[0], pair[1]["object_id"]),
            )
            top = ranked[0][0] if ranked else 0.0
            second = ranked[1][0] if len(ranked) > 1 else 0.0
            if top < min_overlap:
                status, object_id = "unmatched", None
            elif second >= min_overlap and top - second < ambiguity_margin:
                status, object_id = "ambiguous", None
            else:
                status, object_id = "matched_for_review", ranked[0][1]["object_id"]
            link = {
                "paint_label": paint_label, "source": "indexed_component",
                "source_layer": label.get("layer"), "component_index": label.get("component_index"),
                "expected_bbox": list(bbox), "target_layer": label.get("target_layer"),
                "family_id": label.get("family_id"), "label": label.get("label"),
                "object_id": object_id, "status": status,
                "best_overlap_min": round(top, 6), "runner_up_overlap_min": round(second, 6),
                "match_method": "exact_pixel_overlap" if exact_masks else "bbox_overlap_fallback",
            }
            links.append(link)
            if object_id:
                evidence[(paint_label, str(object_id))].append(link)

    reviewed = []
    for record in bank.get("records") or ():
        key = (str(record["paint_label"]), str(record["object_id"]))
        votes = evidence.get(key, ())
        targets = {str(item.get("target_layer")) for item in votes}
        families = {str(item.get("family_id")) for item in votes if item.get("family_id")}
        labels = {str(item.get("label")) for item in votes if item.get("label")}
        if not votes:
            continue
        target = next(iter(targets)) if len(targets) == 1 else "uncertain"
        proposal_fraction_fields = {
            "numbers": "number_member_fraction",
            "sponsors": "sponsor_member_fraction",
            "template": "template_member_fraction",
        }
        proposal_field = proposal_fraction_fields.get(target)
        proposal_fraction = (
            float(record[proposal_field])
            if proposal_field and record.get(proposal_field) is not None
            else None
        )
        proposal_support_state = (
            "supported" if proposal_fraction is not None and proposal_fraction > 0.0
            else "missing" if proposal_fraction is not None
            else "unknown"
        )
        reviewed.append({
            **record,
            "review_target_layer": target,
            "review_family_id": next(iter(families)) if len(families) == 1 else None,
            # Preserve the reviewer's semantic failure family instead of
            # flattening every hard negative into only its final owner.  These
            # labels remain immutable corpus evidence and have no runtime vote.
            "review_label": next(iter(labels)) if len(labels) == 1 else None,
            "review_labels": sorted(labels),
            "review_evidence_count": len(votes),
            "review_conflict": len(targets) > 1,
            "review_label_conflict": len(labels) > 1,
            # Audit-only failure-stage evidence. This exposes whether the
            # reviewed owner was ever proposed, but is intentionally excluded
            # from every model feature set to avoid target leakage.
            "review_target_proposal_fraction": proposal_fraction,
            "review_target_proposal_support_state": proposal_support_state,
        })

    counts = Counter(str(item["review_target_layer"]) for item in reviewed)
    paints: dict[str, set[str]] = defaultdict(set)
    for item in reviewed:
        paints[str(item["review_target_layer"])].add(str(item["paint_label"]))
    minimum = sorted(
        owner for owner in ("numbers", "sponsors", "template", "paint")
        if counts[owner] >= 12 and len(paints[owner]) >= 3
    )
    output = dict(bank)
    output["review_links"] = links
    output["reviewed_objects"] = reviewed
    output["summary"] = {
        "review_link_counts": dict(Counter(item["status"] for item in links)),
        "review_match_method_counts": dict(Counter(
            str(item.get("match_method")) for item in links if item.get("match_method")
        )),
        "reviewed_object_count": len(reviewed),
        "class_counts": dict(sorted(counts.items())),
        "class_paint_counts": {key: len(value) for key, value in sorted(paints.items())},
        "review_label_counts": dict(sorted(Counter(
            label for item in reviewed for label in item.get("review_labels") or ()
        ).items())),
        "review_target_proposal_support_counts": dict(sorted(Counter(
            str(item["review_target_proposal_support_state"]) for item in reviewed
        ).items())),
        "review_target_proposal_support_by_class": {
            owner: dict(sorted(Counter(
                str(item["review_target_proposal_support_state"])
                for item in reviewed if item["review_target_layer"] == owner
            ).items()))
            for owner in ("numbers", "sponsors", "template", "paint", "uncertain")
            if any(item["review_target_layer"] == owner for item in reviewed)
        },
        "minimum_coverage_classes": minimum,
        "training_coverage_ready": len(minimum) == 4,
        "calibration_ready": False,
        "calibration_blockers": (
            [f"minimum_review_coverage:{owner}" for owner in ("numbers", "sponsors", "template", "paint") if owner not in minimum]
            + ["no_paint_stratified_holdout_model"]
        ),
        "casts_votes": False,
        "ownership_authority": False,
    }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", action="append", required=True)
    parser.add_argument("--component-labels", action="append", default=[])
    parser.add_argument("--group-labels", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inspections = [item for path in args.inspection for item in json.loads(Path(path).read_text(encoding="utf-8"))]
    components = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.component_labels]
    groups = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.group_labels]
    bank = attach_reviews(build_bank(inspections), components, groups)
    Path(args.output).write_text(json.dumps(bank, indent=2), encoding="utf-8")
    print(json.dumps(bank["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
