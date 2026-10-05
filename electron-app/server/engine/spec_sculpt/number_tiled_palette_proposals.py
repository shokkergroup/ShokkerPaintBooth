"""Probability-independent palette proposals for repeated decal instances.

The existing local-copy adapter starts from the Number segmentation map.  That
cannot recover an object the segmenter never activates.  This module instead
observes overlapping tiles across the complete texture, preserves intrinsic
palette subinstances and ranks a bounded shadow shortlist by owner-neutral D4
peer similarity.  It never casts an ownership vote or adds pixels.
"""
from __future__ import annotations

import hashlib
from typing import Sequence

import numpy as np

from .decal_subinstances import derive_intrinsic_subinstances
from .number_context_family_similarity import (
    d4_cosine_similarity,
    normalized_visual_descriptor,
)
from .number_map_family_features import map_family_template_position_features


def _intersection(first: Sequence[int], second: Sequence[int]) -> int:
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by),
    )


def _origins(length: int, tile_size: int, stride: int) -> tuple[int, ...]:
    if length <= tile_size:
        return (0,)
    values = list(range(0, length - tile_size + 1, stride))
    last = length - tile_size
    if values[-1] != last:
        values.append(last)
    return tuple(values)


def multiscale_tiled_palette_proposals(
    rgb: np.ndarray,
    *,
    tile_sizes: Sequence[int] = (192, 320),
    overlap_fraction: float = 0.5,
    min_pixels: int = 16,
    max_per_role: int = 8,
) -> tuple[dict, ...]:
    """Preserve deduplicated intrinsic palette observations from full-canvas tiles."""
    image = np.asarray(rgb, np.uint8)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("tiled palette proposals require an HxWx3 image")
    if not (0.0 <= float(overlap_fraction) < 1.0):
        raise ValueError("overlap_fraction must be in [0, 1)")

    unique: dict[tuple[tuple[int, ...], bytes], dict] = {}
    for requested_size in tile_sizes:
        size = min(int(requested_size), image.shape[0], image.shape[1])
        if size < 32:
            raise ValueError("tile sizes must be at least 32 pixels")
        stride = max(1, int(round(size * (1.0 - float(overlap_fraction)))))
        for y in _origins(image.shape[0], size, stride):
            for x in _origins(image.shape[1], size, stride):
                crop = image[y:y + size, x:x + size]
                parent = np.ones((size, size), bool)
                observations = derive_intrinsic_subinstances(
                    crop,
                    parent,
                    min_pixels=int(min_pixels),
                    min_parent_fraction=0.001,
                    max_parent_fraction=0.72,
                    max_per_role=int(max_per_role),
                )
                for observation in observations:
                    sx, sy, width, height = map(int, observation.bbox)
                    support = np.ascontiguousarray(
                        observation.local_mask[sy:sy + height, sx:sx + width],
                        dtype=bool,
                    )
                    bbox = [x + sx, y + sy, width, height]
                    fingerprint = np.packbits(support.reshape(-1)).tobytes()
                    key = (tuple(bbox), fingerprint)
                    origin = {
                        "tile_bbox": [x, y, size, size],
                        "hypothesis": observation.hypothesis,
                        "palette_role": observation.source_role,
                    }
                    if key in unique:
                        unique[key]["provenance"]["tile_origins"].append(origin)
                        continue
                    digest = hashlib.sha256()
                    digest.update(fingerprint)
                    digest.update(str(bbox).encode("ascii"))
                    support.setflags(write=False)
                    unique[key] = {
                        "proposal_id": "number-tiled-palette:" + digest.hexdigest()[:16],
                        "proposal_bbox": bbox,
                        "raw_support": support,
                        "owner_neutral": True,
                        "ownership_authority": False,
                        "provenance": {
                            "source_stage": "number_object_tiled_palette_subinstance",
                            "probability_independent": True,
                            "palette_role": observation.source_role,
                            "parent_fraction": float(observation.parent_fraction),
                            "component_count": int(observation.component_count),
                            "tile_origins": [origin],
                        },
                    }
    for proposal in unique.values():
        proposal["provenance"]["tile_origin_count"] = len(
            proposal["provenance"]["tile_origins"]
        )
    return tuple(sorted(unique.values(), key=lambda item: item["proposal_id"]))


def repeated_tiled_palette_shortlist(
    rgb: np.ndarray,
    proposals: Sequence[dict],
    *,
    maximum: int = 96,
    maximum_inputs: int = 512,
    maximum_area_ratio: float = 4.0,
    maximum_overlap: float = 0.35,
    assembled_reserve_fraction: float = 0.33,
) -> tuple[dict, ...]:
    """Rank raw observations by D4-similar non-overlapping peers without authority."""
    image = np.asarray(rgb, np.uint8)
    # The raw observer deliberately has high recall and may emit thousands of
    # overlapping palette hypotheses.  Bound the quadratic relationship pass
    # with generic stability/shape evidence only; no semantic, position,
    # filename, car or owner signal is used here.
    eligible = []
    for proposal in proposals:
        _x, _y, width, height = map(int, proposal["proposal_bbox"])
        area = max(1, int(np.count_nonzero(proposal["raw_support"])))
        aspect = max(width, height) / max(1, min(width, height))
        if min(width, height) < 3 or area < 16 or aspect > 12.0:
            continue
        provenance = proposal["provenance"]
        eligible.append((
            int(provenance.get("tile_origin_count", 1)),
            int(provenance.get("component_count", 1)),
            area,
            proposal,
        ))
    eligible.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]["proposal_id"]))
    proposals = tuple(item[3] for item in eligible[:max(0, int(maximum_inputs))])
    descriptors = []
    areas = []
    for proposal in proposals:
        x, y, width, height = map(int, proposal["proposal_bbox"])
        descriptors.append(normalized_visual_descriptor(
            image[y:y + height, x:x + width], proposal["raw_support"], size=16,
        ))
        areas.append(max(1, int(np.count_nonzero(proposal["raw_support"]))))

    ranked = []
    log_ratio = float(np.log(maximum_area_ratio))
    for index, proposal in enumerate(proposals):
        bbox = proposal["proposal_bbox"]
        box_area = max(1, int(bbox[2]) * int(bbox[3]))
        peers = []
        for peer_index, peer in enumerate(proposals):
            if peer_index == index:
                continue
            peer_bbox = peer["proposal_bbox"]
            peer_box_area = max(1, int(peer_bbox[2]) * int(peer_bbox[3]))
            if _intersection(bbox, peer_bbox) / min(box_area, peer_box_area) > maximum_overlap:
                continue
            area_difference = abs(float(np.log(areas[index] / areas[peer_index])))
            if area_difference > log_ratio:
                continue
            similarity = d4_cosine_similarity(descriptors[index], descriptors[peer_index])
            peers.append((similarity, area_difference, peer["proposal_id"]))
        best = max(peers, default=(-1.0, 8.0, ""), key=lambda item: item[0])
        repeated_count = sum(item[0] >= 0.82 for item in peers)
        enriched = {
            **proposal,
            "provenance": {
                **proposal["provenance"],
                "peer_d4_similarity": float(best[0]),
                "peer_area_log_difference": float(best[1]),
                "peer_proposal_id": best[2],
                "peer_count_at_0_82": int(repeated_count),
                "relationship_is_corroborative_only": True,
            },
        }
        component_count = int(proposal["provenance"].get("component_count", 1))
        tile_origin_count = int(proposal["provenance"].get("tile_origin_count", 1))
        ranked.append((
            float(best[0]), repeated_count, component_count,
            tile_origin_count, areas[index], enriched,
        ))
    ranked.sort(key=lambda item: (
        -item[0], -item[1], -item[2], -item[3], -item[4], item[5]["proposal_id"],
    ))

    # Stable single glyphs naturally dominate D4 peer similarity.  Preserve a
    # bounded quota of multi-component observations as *candidate hypotheses*
    # so a complete two-digit number is not discarded before semantic scoring.
    # This does not merge pixels, assign a class, or confer ownership.
    limit = max(0, int(maximum))
    reserve = min(limit, max(0, int(round(limit * assembled_reserve_fraction))))
    repeated_slots = max(0, limit - reserve)
    selected = list(ranked[:repeated_slots])
    selected_ids = {item[5]["proposal_id"] for item in selected}
    assembled = sorted(
        (item for item in ranked if item[2] >= 2 and item[5]["proposal_id"] not in selected_ids),
        key=lambda item: (-item[2], -item[3], -item[4], -item[0], item[5]["proposal_id"]),
    )
    selected.extend(assembled[:reserve])
    selected_ids = {item[5]["proposal_id"] for item in selected}
    if len(selected) < limit:
        selected.extend(item for item in ranked if item[5]["proposal_id"] not in selected_ids)
    return tuple(item[5] for item in selected[:limit])


def assemble_adjacent_tiled_palette_companions(
    proposals: Sequence[dict],
    *,
    maximum_inputs: int = 384,
    maximum: int = 192,
    maximum_area_ratio: float = 4.0,
    minimum_cross_axis_overlap: float = 0.35,
    maximum_gap_fraction: float = 0.80,
) -> tuple[dict, ...]:
    """Create immutable adjacent-component hypotheses without semantic authority.

    Stylized multi-digit numbers commonly arrive as one palette component per
    digit.  This stage preserves the original observations and adds only their
    exact pixel union when two similarly sized, aligned observations are close.
    Geometry can propose an object for later scoring; it cannot label or own it.
    """
    inputs = tuple(proposals[:max(0, int(maximum_inputs))])
    candidates = []
    seen = set()
    for first_index, first in enumerate(inputs):
        ax, ay, aw, ah = map(int, first["proposal_bbox"])
        first_area = max(1, int(np.count_nonzero(first["raw_support"])))
        first_role = first["provenance"].get("palette_role")
        for second in inputs[first_index + 1:]:
            if second["provenance"].get("palette_role") != first_role:
                continue
            bx, by, bw, bh = map(int, second["proposal_bbox"])
            second_area = max(1, int(np.count_nonzero(second["raw_support"])))
            area_ratio = max(first_area, second_area) / min(first_area, second_area)
            if area_ratio > float(maximum_area_ratio):
                continue
            first_box_area = max(1, aw * ah)
            second_box_area = max(1, bw * bh)
            if _intersection(first["proposal_bbox"], second["proposal_bbox"]) / min(
                first_box_area, second_box_area,
            ) > 0.20:
                continue

            x_overlap = max(0, min(ax + aw, bx + bw) - max(ax, bx))
            y_overlap = max(0, min(ay + ah, by + bh) - max(ay, by))
            x_gap = max(0, max(ax, bx) - min(ax + aw, bx + bw))
            y_gap = max(0, max(ay, by) - min(ay + ah, by + bh))
            horizontal = (
                y_overlap / max(1, min(ah, bh)) >= minimum_cross_axis_overlap
                and x_gap <= maximum_gap_fraction * max(ah, bh)
            )
            vertical = (
                x_overlap / max(1, min(aw, bw)) >= minimum_cross_axis_overlap
                and y_gap <= maximum_gap_fraction * max(aw, bw)
            )
            if not (horizontal or vertical):
                continue

            x0, y0 = min(ax, bx), min(ay, by)
            x1, y1 = max(ax + aw, bx + bw), max(ay + ah, by + bh)
            width, height = x1 - x0, y1 - y0
            if max(width, height) / max(1, min(width, height)) > 5.0:
                continue
            support = np.zeros((height, width), dtype=bool)
            support[ay - y0:ay - y0 + ah, ax - x0:ax - x0 + aw] |= first["raw_support"]
            support[by - y0:by - y0 + bh, bx - x0:bx - x0 + bw] |= second["raw_support"]
            fingerprint = np.packbits(support.reshape(-1)).tobytes()
            bbox = [x0, y0, width, height]
            key = (tuple(bbox), fingerprint)
            if key in seen:
                continue
            seen.add(key)
            digest = hashlib.sha256()
            digest.update(fingerprint)
            digest.update(str(sorted((first["proposal_id"], second["proposal_id"]))).encode("utf-8"))
            support.setflags(write=False)
            peer = min(
                float(first["provenance"].get("peer_d4_similarity", -1.0)),
                float(second["provenance"].get("peer_d4_similarity", -1.0)),
            )
            repeated_count = min(
                int(first["provenance"].get("peer_count_at_0_82", 0)),
                int(second["provenance"].get("peer_count_at_0_82", 0)),
            )
            cross_overlap = (
                y_overlap / max(1, min(ah, bh)) if horizontal
                else x_overlap / max(1, min(aw, bw))
            )
            gap_fraction = (
                x_gap / max(1, max(ah, bh)) if horizontal
                else y_gap / max(1, max(aw, bw))
            )
            proposal = {
                "proposal_id": "number-tiled-companion:" + digest.hexdigest()[:16],
                "proposal_bbox": bbox,
                "raw_support": support,
                "owner_neutral": True,
                "ownership_authority": False,
                "provenance": {
                    "source_stage": "number_object_tiled_palette_companion_assembly",
                    "probability_independent": True,
                    "palette_role": first_role,
                    "component_count": int(
                        first["provenance"].get("component_count", 1)
                        + second["provenance"].get("component_count", 1)
                    ),
                    "tile_origin_count": int(
                        first["provenance"].get("tile_origin_count", 1)
                        + second["provenance"].get("tile_origin_count", 1)
                    ),
                    "member_proposal_ids": sorted((first["proposal_id"], second["proposal_id"])),
                    "adjacency_axis": "horizontal" if horizontal else "vertical",
                    "cross_axis_overlap": float(cross_overlap),
                    "gap_fraction": float(gap_fraction),
                    "peer_d4_similarity": float(peer),
                    "peer_count_at_0_82": int(repeated_count),
                    "relationship_is_corroborative_only": True,
                    "assembly_creates_no_ownership": True,
                },
            }
            candidates.append((cross_overlap, -gap_fraction, peer, first_area + second_area, proposal))
    candidates.sort(key=lambda item: (
        -item[0], -item[1], -item[2], -item[3], item[4]["proposal_id"],
    ))
    return tuple(item[4] for item in candidates[:max(0, int(maximum))])


def position_ranked_tiled_shortlist(
    proposals: Sequence[dict],
    canvas_shape: Sequence[int],
    panel_map: dict,
    *,
    maximum: int = 48,
) -> tuple[dict, ...]:
    """Bound review/scoring cost with normalized position as corroboration only."""
    ranked = []
    for proposal in proposals:
        position = map_family_template_position_features(
            proposal["proposal_bbox"], proposal["raw_support"], canvas_shape, panel_map,
        )
        number_fraction = float(position[0])
        sponsor_fraction = float(position[1])
        peer = max(-1.0, float(proposal["provenance"].get("peer_d4_similarity", -1.0)))
        # This score selects which immutable observations receive expensive
        # semantic scoring. It is not an acceptance threshold or ownership vote.
        component_count = max(1, int(proposal["provenance"].get("component_count", 1)))
        assembly_support = min(1.0, float(np.log2(1.0 + component_count) / 3.0))
        rank_score = (
            0.60 * number_fraction
            + 0.30 * max(0.0, peer)
            + 0.10 * assembly_support
        )
        enriched = {
            **proposal,
            "provenance": {
                **proposal["provenance"],
                "template_number_fraction": number_fraction,
                "template_sponsor_fraction": sponsor_fraction,
                "assembly_support": assembly_support,
                "position_rank_score": float(rank_score),
                "position_is_corroborative_only": True,
            },
        }
        ranked.append((rank_score, peer, enriched))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]["proposal_id"]))
    return tuple(item[2] for item in ranked[:max(0, int(maximum))])


def corroborate_tiled_number_families(
    rgb: np.ndarray,
    proposals: Sequence[dict],
    panel_map: dict,
    *,
    minimum_peer_similarity: float = 0.82,
    maximum_area_ratio: float = 4.0,
) -> tuple[dict, ...]:
    """Attach cross-number-block visual family evidence without authority.

    A race number is normally repeated on distinct template panels.  This pass
    measures whether an immutable candidate has D4-similar peers in other
    normalized number blocks.  It never creates a candidate, changes a mask,
    labels a family, or grants ownership.
    """
    image = np.asarray(rgb, np.uint8)
    blocks = tuple(panel_map.get("number_blocks", ()))
    descriptors, block_rows, areas = [], [], []
    for proposal in proposals:
        x, y, width, height = map(int, proposal["proposal_bbox"])
        support = np.asarray(proposal["raw_support"], dtype=bool)
        descriptors.append(normalized_visual_descriptor(
            image[y:y + height, x:x + width], support, size=16,
        ))
        areas.append(max(1, int(np.count_nonzero(support))))
        fractions = []
        for block in blocks:
            bx, by, bw, bh = map(int, block["bbox"])
            ix0, iy0 = max(x, bx), max(y, by)
            ix1, iy1 = min(x + width, bx + bw), min(y + height, by + bh)
            if ix1 <= ix0 or iy1 <= iy0:
                fractions.append(0.0)
                continue
            covered = int(np.count_nonzero(
                support[iy0 - y:iy1 - y, ix0 - x:ix1 - x]
            ))
            fractions.append(covered / areas[-1])
        best_index = int(np.argmax(fractions)) if fractions else -1
        best_fraction = fractions[best_index] if best_index >= 0 else 0.0
        block_rows.append((
            str(blocks[best_index].get("name", best_index)) if best_fraction >= 0.20 else "none",
            float(best_fraction),
            tuple(float(value) for value in fractions),
        ))

    enriched = []
    maximum_log_ratio = float(np.log(maximum_area_ratio))
    for index, proposal in enumerate(proposals):
        block_name, block_fraction, block_fractions = block_rows[index]
        peers = []
        for peer_index, peer in enumerate(proposals):
            if peer_index == index or block_name == "none":
                continue
            peer_block = block_rows[peer_index][0]
            if peer_block == "none" or peer_block == block_name:
                continue
            area_difference = abs(float(np.log(areas[index] / areas[peer_index])))
            if area_difference > maximum_log_ratio:
                continue
            similarity = d4_cosine_similarity(descriptors[index], descriptors[peer_index])
            peers.append((
                float(similarity), float(area_difference), peer_block,
                proposal["provenance"].get("palette_role")
                == peer["provenance"].get("palette_role"),
                peer["proposal_id"],
            ))
        best = max(peers, default=(-1.0, 8.0, "none", False, ""), key=lambda item: item[0])
        strong = [item for item in peers if item[0] >= minimum_peer_similarity]
        distinct = len({item[2] for item in strong})
        same_palette_best = max(
            (item[0] for item in peers if item[3]), default=-1.0,
        )
        enriched.append({
            **proposal,
            "provenance": {
                **proposal["provenance"],
                "dominant_number_block": block_name,
                "dominant_number_block_fraction": block_fraction,
                "number_block_fractions": block_fractions,
                "cross_block_best_d4_similarity": float(best[0]),
                "cross_block_best_area_log_difference": float(best[1]),
                "cross_block_best_peer_id": best[4],
                "cross_block_peer_count_at_0_82": len(strong),
                "cross_block_distinct_peer_blocks": distinct,
                "cross_block_same_palette_best_similarity": float(same_palette_best),
                "family_relationship_is_corroborative_only": True,
                "family_relationship_creates_no_ownership": True,
            },
        })
    return tuple(enriched)


__all__ = [
    "assemble_adjacent_tiled_palette_companions",
    "corroborate_tiled_number_families",
    "multiscale_tiled_palette_proposals",
    "position_ranked_tiled_shortlist",
    "repeated_tiled_palette_shortlist",
]
