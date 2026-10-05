"""Measure owner-neutral probability proposal recall on verified DLM copy misses.

This is an evaluation probe only.  Reviewed boxes score proposal geometry; they
are never passed to the model or proposal generator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_map_family_shadow import (
        DEFAULT_FAMILY_MODEL, DEFAULT_PANEL_MAP, DEFAULT_SEGMENT_MODEL,
    )
    from engine.spec_sculpt.number_context_family_similarity import (
        d4_cosine_similarity, normalized_visual_descriptor, prototype_margin,
    )
    from engine.spec_sculpt.number_object_segmentation import (
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families
    from engine.spec_sculpt.number_map_family_features import map_family_template_position_features
    from engine.spec_sculpt.decal_subinstances import derive_intrinsic_subinstances
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_map_family_shadow import (  # type: ignore
        DEFAULT_FAMILY_MODEL, DEFAULT_PANEL_MAP, DEFAULT_SEGMENT_MODEL,
    )
    from engine.spec_sculpt.number_context_family_similarity import (  # type: ignore
        d4_cosine_similarity, normalized_visual_descriptor, prototype_margin,
    )
    from engine.spec_sculpt.number_object_segmentation import (  # type: ignore
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
    )
    from engine.spec_sculpt.number_object_assembly import assemble_nested_proposal_families  # type: ignore
    from engine.spec_sculpt.number_map_family_features import map_family_template_position_features  # type: ignore
    from engine.spec_sculpt.decal_subinstances import derive_intrinsic_subinstances  # type: ignore


VERIFIED_MISSES = {
    "dirtlatemodel 350/car_num_302246.tga": {
        "label": "small_spoiler_82", "bbox": [271, 916, 43, 27],
    },
    "dirtlatemodel 358/car_num_1283575.tga": {
        "label": "roof_57", "bbox": [795, 825, 170, 123],
    },
    "dirtlatemodel 358/car_num_1288062.tga": {
        "label": "small_nose_10", "bbox": [268, 932, 41, 10],
    },
    "dirtlatemodel 358/car_num_1292637.tga": {
        "label": "small_spoiler_30", "bbox": [271, 916, 43, 27],
    },
}

VARIANTS = {
    "baseline": {"quantiles": (0.90, 0.95, 0.98), "min_model_pixels": 5},
    "baseline_min1": {"quantiles": (0.90, 0.95, 0.98), "min_model_pixels": 1},
    "high_tail": {
        "quantiles": (0.90, 0.95, 0.98, 0.99, 0.995, 0.997),
        "min_model_pixels": 1,
    },
    "wide_tail": {
        "quantiles": (0.85, 0.90, 0.95, 0.98, 0.99, 0.995, 0.997),
        "min_model_pixels": 1,
    },
}

LOCAL_VARIANTS = {
    "local24_z050": {
        "window_sizes": (24,), "z_scores": (0.50,), "min_model_pixels": 2,
    },
    "local24_z075": {
        "window_sizes": (24,), "z_scores": (0.75,), "min_model_pixels": 2,
    },
    "local24_pair": {
        "window_sizes": (24,), "z_scores": (0.50, 0.75), "min_model_pixels": 2,
    },
    "local_contrast_narrow": {
        "window_sizes": (32, 64), "z_scores": (0.75, 1.0), "min_model_pixels": 2,
    },
    "local_contrast_wide": {
        "window_sizes": (24, 40, 64, 96), "z_scores": (0.50, 0.75, 1.0),
        "min_model_pixels": 2,
    },
}


def _local_contrast_proposals(
    probability, output_shape, *, window_sizes, z_scores, min_model_pixels,
):
    """Create owner-neutral components from local probability prominence."""
    values = np.asarray(probability, np.float32)
    out_height, out_width = map(int, output_shape)
    global_floor = float(np.quantile(values, 0.50))
    proposals = []
    for window_size in window_sizes:
        size = int(window_size)
        mean = cv2.boxFilter(values, cv2.CV_32F, (size, size), normalize=True)
        square = cv2.boxFilter(values * values, cv2.CV_32F, (size, size), normalize=True)
        std = np.sqrt(np.maximum(0.0, square - mean * mean))
        for z_score in z_scores:
            binary = (
                (values >= mean + float(z_score) * std)
                & (values >= global_floor)
                & ((values - mean) >= 0.01)
            ).astype(np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, 8)
            for label in range(1, count):
                x, y, width, height, area = map(int, stats[label])
                if area < int(min_model_pixels):
                    continue
                x0 = max(0, int(np.floor(x * out_width / values.shape[1])))
                y0 = max(0, int(np.floor(y * out_height / values.shape[0])))
                x1 = min(out_width, int(np.ceil((x + width) * out_width / values.shape[1])))
                y1 = min(out_height, int(np.ceil((y + height) * out_height / values.shape[0])))
                local = labels[y:y + height, x:x + width] == label
                support = cv2.resize(
                    local.astype(np.uint8), (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST,
                ) > 0
                digest = hashlib.sha256()
                digest.update(support.tobytes())
                digest.update(f"{x0},{y0},{x1-x0},{y1-y0},{size},{z_score:.3f}".encode())
                component_values = values[labels == label]
                proposals.append({
                    "proposal_id": "number-local-map:" + digest.hexdigest()[:16],
                    "proposal_bbox": [x0, y0, x1 - x0, y1 - y0],
                    "raw_support": support,
                    "owner_neutral": True,
                    "ownership_authority": False,
                    "provenance": {
                        "source_stage": "number_object_local_contrast_probability_map",
                        "window_size": size, "z_score": float(z_score),
                        "model_pixels": area,
                        "mean_probability": float(component_values.mean()),
                        "max_probability": float(component_values.max()),
                    },
                })
    return tuple(proposals)


def _intersection(first, second):
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    return max(0, x1 - x0) * max(0, y1 - y0)


def _stable_local_pairs(proposals):
    lower = [item for item in proposals if item["provenance"]["z_score"] == 0.50]
    upper = [item for item in proposals if item["provenance"]["z_score"] == 0.75]
    pairs = []
    for high in upper:
        high_box = high["proposal_bbox"]
        high_area = max(1, int(high_box[2]) * int(high_box[3]))
        candidates = []
        for low in lower:
            low_box = low["proposal_bbox"]
            low_area = max(1, int(low_box[2]) * int(low_box[3]))
            intersection = _intersection(high_box, low_box)
            containment = intersection / min(high_area, low_area)
            area_ratio = max(high_area, low_area) / min(high_area, low_area)
            if containment >= 0.50 and area_ratio <= 6.0:
                candidates.append((containment, -area_ratio, low))
        if not candidates:
            continue
        _containment, _negative_ratio, low = max(candidates, key=lambda item: item[:2])
        low_box = low["proposal_bbox"]
        x0, y0 = min(high_box[0], low_box[0]), min(high_box[1], low_box[1])
        x1 = max(high_box[0] + high_box[2], low_box[0] + low_box[2])
        y1 = max(high_box[1] + high_box[3], low_box[1] + low_box[3])
        pairs.append({
            "proposal_bbox": [x0, y0, x1 - x0, y1 - y0],
            "member_count": 2,
            "max_probability": max(
                float(high["provenance"]["max_probability"]),
                float(low["provenance"]["max_probability"]),
            ),
        })
    unique = {}
    for item in pairs:
        unique.setdefault(tuple(item["proposal_bbox"]), item)
    return tuple(unique.values())


def _match(proposal, truth):
    intersection = _intersection(proposal["proposal_bbox"], truth)
    truth_area = max(1, int(truth[2]) * int(truth[3]))
    proposal_area = max(1, int(proposal["proposal_bbox"][2]) * int(proposal["proposal_bbox"][3]))
    coverage = intersection / truth_area
    area_ratio = proposal_area / truth_area
    # Complete enough to contain the copy and not merely a huge livery panel.
    recovered = coverage >= 0.55 and area_ratio <= 6.0
    rank = (recovered, min(coverage, 1.0) / max(1.0, area_ratio), coverage, -area_ratio)
    return rank, coverage, area_ratio, recovered


def run(inspection_path: Path, output: Path, frozen_scores_path: Path | None = None):
    import torch

    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    blob = torch.load(DEFAULT_SEGMENT_MODEL, map_location="cpu", weights_only=True)
    model = build_tiny_unet(int(blob["base_channels"]))
    model.load_state_dict(blob["state_dict"])
    model.eval()
    prototype_archive = np.load(DEFAULT_FAMILY_MODEL, allow_pickle=False)
    descriptors = np.asarray(prototype_archive["descriptors"], np.float32)
    descriptor_labels = np.asarray(prototype_archive["labels"], bool)
    positive_descriptors = descriptors[descriptor_labels]
    control_descriptors = descriptors[~descriptor_labels]
    frozen_proposal_gate = float(prototype_archive["proposal_gate"][0])
    panel_map = json.loads(DEFAULT_PANEL_MAP.read_text(encoding="utf-8"))
    accepted_members_by_paint = {}
    if frozen_scores_path is not None:
        frozen_scores = json.loads(frozen_scores_path.read_text(encoding="utf-8"))
        for item in frozen_scores["scores"]:
            if item["accepted"]:
                accepted_members_by_paint.setdefault(item["paint_label"], set()).update(
                    item["member_ids"]
                )
    paints = []
    totals = {
        name: {"proposal_count": 0, "verified_misses_recovered": 0}
        for name in (*VARIANTS, *LOCAL_VARIANTS)
    }
    for record in inspection:
        paint_label = record["paint_label"]
        rgb = np.asarray(Image.open(record["source_1024"]).convert("RGB"))
        with torch.no_grad():
            probability = torch.sigmoid(
                model(torch.from_numpy(image_feature_tensor(rgb)[None]))
            )[0, 0].numpy()
        row = {"paint_label": paint_label, "variants": {}}
        miss = VERIFIED_MISSES.get(paint_label)
        if miss:
            x, y, width, height = miss["bbox"]
            x0, y0 = int(x * probability.shape[1] / rgb.shape[1]), int(y * probability.shape[0] / rgb.shape[0])
            x1 = max(x0 + 1, int(np.ceil((x + width) * probability.shape[1] / rgb.shape[1])))
            y1 = max(y0 + 1, int(np.ceil((y + height) * probability.shape[0] / rgb.shape[0])))
            values = probability[y0:y1, x0:x1]
            row["verified_miss"] = {
                **miss,
                "model_bbox": [x0, y0, x1 - x0, y1 - y0],
                "probability_mean": float(values.mean()),
                "probability_max": float(values.max()),
                "global_percentile_of_max": float(np.mean(probability <= values.max())),
            }
        for name, kwargs in VARIANTS.items():
            proposals = probability_region_proposals(probability, rgb.shape[:2], **kwargs)
            totals[name]["proposal_count"] += len(proposals)
            variant = {"proposal_count": len(proposals)}
            if miss:
                candidates = []
                for proposal in proposals:
                    rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                    candidates.append((rank, proposal, coverage, area_ratio, recovered))
                _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
                variant.update({
                    "recovered": bool(recovered),
                    "best_bbox": list(map(int, best["proposal_bbox"])),
                    "best_coverage": float(coverage),
                    "best_area_ratio": float(area_ratio),
                    "best_quantile": float(best["provenance"]["relative_quantile"]),
                    "best_model_pixels": int(best["provenance"]["model_pixels"]),
                })
                totals[name]["verified_misses_recovered"] += int(recovered)
            row["variants"][name] = variant
        for name, kwargs in LOCAL_VARIANTS.items():
            proposals = _local_contrast_proposals(probability, rgb.shape[:2], **kwargs)
            totals[name]["proposal_count"] += len(proposals)
            variant = {"proposal_count": len(proposals)}
            if miss:
                candidates = []
                for proposal in proposals:
                    rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                    candidates.append((rank, proposal, coverage, area_ratio, recovered))
                _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
                variant.update({
                    "recovered": bool(recovered),
                    "best_bbox": list(map(int, best["proposal_bbox"])),
                    "best_coverage": float(coverage),
                    "best_area_ratio": float(area_ratio),
                    "best_window_size": int(best["provenance"]["window_size"]),
                    "best_z_score": float(best["provenance"]["z_score"]),
                    "best_model_pixels": int(best["provenance"]["model_pixels"]),
                })
                totals[name]["verified_misses_recovered"] += int(recovered)
            row["variants"][name] = variant
        pair = _local_contrast_proposals(
            probability, rgb.shape[:2], **LOCAL_VARIANTS["local24_pair"],
        )
        by_id = {item["proposal_id"]: item for item in pair}
        stable_families = []
        for family in assemble_nested_proposal_families(pair):
            members = [by_id[item] for item in family["member_ids"]]
            z_scores = {float(item["provenance"]["z_score"]) for item in members}
            if len(z_scores) < 2:
                continue
            stable_families.append({
                "proposal_bbox": family["family_bbox"],
                "member_count": len(members),
                "max_probability": max(
                    float(item["provenance"]["max_probability"]) for item in members
                ),
            })
        variant = {"proposal_count": len(stable_families)}
        totals.setdefault("local24_stable_families", {
            "proposal_count": 0, "verified_misses_recovered": 0,
        })
        totals["local24_stable_families"]["proposal_count"] += len(stable_families)
        if miss:
            candidates = []
            for proposal in stable_families:
                rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                candidates.append((rank, proposal, coverage, area_ratio, recovered))
            _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
            variant.update({
                "recovered": bool(recovered),
                "best_bbox": list(map(int, best["proposal_bbox"])),
                "best_coverage": float(coverage),
                "best_area_ratio": float(area_ratio),
                "best_member_count": int(best["member_count"]),
                "best_max_probability": float(best["max_probability"]),
            })
            totals["local24_stable_families"]["verified_misses_recovered"] += int(recovered)
        row["variants"]["local24_stable_families"] = variant
        stable_pairs = _stable_local_pairs(pair)
        totals.setdefault("local24_stable_pairs", {
            "proposal_count": 0, "verified_misses_recovered": 0,
        })
        totals["local24_stable_pairs"]["proposal_count"] += len(stable_pairs)
        variant = {"proposal_count": len(stable_pairs)}
        if miss:
            candidates = []
            for proposal in stable_pairs:
                rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                candidates.append((rank, proposal, coverage, area_ratio, recovered))
            _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
            variant.update({
                "recovered": bool(recovered),
                "best_bbox": list(map(int, best["proposal_bbox"])),
                "best_coverage": float(coverage),
                "best_area_ratio": float(area_ratio),
                "best_max_probability": float(best["max_probability"]),
            })
            totals["local24_stable_pairs"]["verified_misses_recovered"] += int(recovered)
        row["variants"]["local24_stable_pairs"] = variant
        gated = []
        for proposal in pair:
            x, y, width, height = map(int, proposal["proposal_bbox"])
            descriptor = normalized_visual_descriptor(
                rgb[y:y + height, x:x + width], proposal["raw_support"],
            )
            margin = prototype_margin(
                descriptor, positive_descriptors, control_descriptors,
            )
            if margin >= frozen_proposal_gate:
                gated.append({**proposal, "prototype_margin": float(margin)})
        totals.setdefault("local24_frozen_prototype_gate", {
            "proposal_count": 0, "verified_misses_recovered": 0,
        })
        totals["local24_frozen_prototype_gate"]["proposal_count"] += len(gated)
        variant = {
            "proposal_count": len(gated), "frozen_proposal_gate": frozen_proposal_gate,
        }
        if miss:
            candidates = []
            for proposal in gated:
                rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                candidates.append((rank, proposal, coverage, area_ratio, recovered))
            _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
            ranked = sorted(gated, key=lambda item: item["prototype_margin"], reverse=True)
            variant.update({
                "recovered": bool(recovered),
                "best_bbox": list(map(int, best["proposal_bbox"])),
                "best_coverage": float(coverage),
                "best_area_ratio": float(area_ratio),
                "best_prototype_margin": float(best["prototype_margin"]),
                "best_margin_rank": ranked.index(best) + 1,
            })
            totals["local24_frozen_prototype_gate"]["verified_misses_recovered"] += int(recovered)
        row["variants"]["local24_frozen_prototype_gate"] = variant
        baseline = probability_region_proposals(
            probability, rgb.shape[:2], **VARIANTS["baseline"],
        )
        accepted_ids = accepted_members_by_paint.get(paint_label, set())
        anchors = []
        for proposal in baseline:
            if proposal["proposal_id"] not in accepted_ids:
                continue
            x, y, width, height = map(int, proposal["proposal_bbox"])
            anchors.append(normalized_visual_descriptor(
                rgb[y:y + height, x:x + width], proposal["raw_support"],
            ))
        peer_gated = []
        if anchors:
            for proposal in pair:
                x, y, width, height = map(int, proposal["proposal_bbox"])
                descriptor = normalized_visual_descriptor(
                    rgb[y:y + height, x:x + width], proposal["raw_support"],
                )
                similarity = max(d4_cosine_similarity(descriptor, anchor) for anchor in anchors)
                if similarity >= 0.82:
                    peer_gated.append({**proposal, "anchor_similarity": float(similarity)})
        totals.setdefault("local24_accepted_anchor_gate", {
            "proposal_count": 0, "verified_misses_recovered": 0,
        })
        totals["local24_accepted_anchor_gate"]["proposal_count"] += len(peer_gated)
        variant = {
            "proposal_count": len(peer_gated), "frozen_peer_similarity_gate": 0.82,
            "anchor_count": len(anchors),
        }
        if miss and peer_gated:
            candidates = []
            for proposal in peer_gated:
                rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                candidates.append((rank, proposal, coverage, area_ratio, recovered))
            _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
            variant.update({
                "recovered": bool(recovered),
                "best_bbox": list(map(int, best["proposal_bbox"])),
                "best_coverage": float(coverage),
                "best_area_ratio": float(area_ratio),
                "best_anchor_similarity": float(best["anchor_similarity"]),
            })
            totals["local24_accepted_anchor_gate"]["verified_misses_recovered"] += int(recovered)
        elif miss:
            variant["recovered"] = False
        row["variants"]["local24_accepted_anchor_gate"] = variant
        position_gated = []
        for proposal in pair:
            position = map_family_template_position_features(
                proposal["proposal_bbox"], proposal["raw_support"], rgb.shape[:2], panel_map,
            )
            if float(position[0]) >= 0.30:
                position_gated.append({
                    **proposal, "template_number_fraction": float(position[0]),
                    "template_sponsor_fraction": float(position[1]),
                })
        totals.setdefault("local24_template_corroborated", {
            "proposal_count": 0, "verified_misses_recovered": 0,
        })
        totals["local24_template_corroborated"]["proposal_count"] += len(position_gated)
        variant = {
            "proposal_count": len(position_gated), "frozen_template_number_gate": 0.30,
        }
        if miss and position_gated:
            candidates = []
            for proposal in position_gated:
                rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                candidates.append((rank, proposal, coverage, area_ratio, recovered))
            _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
            variant.update({
                "recovered": bool(recovered),
                "best_bbox": list(map(int, best["proposal_bbox"])),
                "best_coverage": float(coverage),
                "best_area_ratio": float(area_ratio),
                "best_template_number_fraction": float(best["template_number_fraction"]),
                "best_template_sponsor_fraction": float(best["template_sponsor_fraction"]),
            })
            totals["local24_template_corroborated"]["verified_misses_recovered"] += int(recovered)
        elif miss:
            variant["recovered"] = False
        row["variants"]["local24_template_corroborated"] = variant
        palette_candidates = []
        for proposal in pair:
            x, y, width, height = map(int, proposal["proposal_bbox"])
            rectangular_support = np.ones((height, width), bool)
            broad_position = map_family_template_position_features(
                proposal["proposal_bbox"], rectangular_support, rgb.shape[:2], panel_map,
            )
            if float(broad_position[0]) <= 0.0:
                continue
            crop = rgb[y:y + height, x:x + width]
            for subinstance in derive_intrinsic_subinstances(
                crop, rectangular_support, min_pixels=8, min_parent_fraction=0.003,
            ):
                sx, sy, sw, sh = subinstance.bbox
                local = subinstance.local_mask[sy:sy + sh, sx:sx + sw]
                bbox = [x + sx, y + sy, sw, sh]
                position = map_family_template_position_features(
                    bbox, local, rgb.shape[:2], panel_map,
                )
                if float(position[0]) < 0.30:
                    continue
                digest = hashlib.sha256()
                digest.update(local.tobytes())
                digest.update(f"{bbox},{subinstance.hypothesis}".encode())
                palette_candidates.append({
                    "proposal_id": "number-local-palette:" + digest.hexdigest()[:16],
                    "proposal_bbox": bbox, "raw_support": local,
                    "prototype_role": subinstance.source_role,
                    "support_pixels": int(np.count_nonzero(local)),
                    "template_number_fraction": float(position[0]),
                })
        unique_palette = {}
        for proposal in palette_candidates:
            key = (tuple(proposal["proposal_bbox"]), proposal["raw_support"].tobytes())
            unique_palette.setdefault(key, proposal)
        palette_candidates = list(unique_palette.values())
        totals.setdefault("local24_palette_template", {
            "proposal_count": 0, "verified_misses_recovered": 0,
        })
        totals["local24_palette_template"]["proposal_count"] += len(palette_candidates)
        variant = {"proposal_count": len(palette_candidates)}
        if miss and palette_candidates:
            candidates = []
            for proposal in palette_candidates:
                rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                candidates.append((rank, proposal, coverage, area_ratio, recovered))
            _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
            variant.update({
                "recovered": bool(recovered),
                "best_bbox": list(map(int, best["proposal_bbox"])),
                "best_coverage": float(coverage),
                "best_area_ratio": float(area_ratio),
                "best_role": best["prototype_role"],
                "best_template_number_fraction": best["template_number_fraction"],
            })
            totals["local24_palette_template"]["verified_misses_recovered"] += int(recovered)
        elif miss:
            variant["recovered"] = False
        row["variants"]["local24_palette_template"] = variant
        panel_ranked = []
        scaled_blocks = []
        for block in panel_map["number_blocks"]:
            bx, by, bw, bh = block["bbox"]
            scaled_blocks.append((
                block["name"], [
                    int(round(bx * rgb.shape[1] / 1024.0)),
                    int(round(by * rgb.shape[0] / 1024.0)),
                    int(round(bw * rgb.shape[1] / 1024.0)),
                    int(round(bh * rgb.shape[0] / 1024.0)),
                ],
            ))
        for block_name, block_bbox in scaled_blocks:
            candidates = []
            for proposal in palette_candidates:
                overlap = _intersection(proposal["proposal_bbox"], block_bbox)
                if not overlap:
                    continue
                score = (
                    float(proposal["template_number_fraction"])
                    * np.sqrt(max(1, int(proposal["support_pixels"])))
                )
                candidates.append((float(score), proposal))
            kept = []
            for score, proposal in sorted(candidates, key=lambda item: (-item[0], item[1]["proposal_id"])):
                bbox = proposal["proposal_bbox"]
                area = max(1, int(bbox[2]) * int(bbox[3]))
                duplicate = False
                for item in kept:
                    other = item["proposal_bbox"]
                    other_area = max(1, int(other[2]) * int(other[3]))
                    overlap = _intersection(bbox, other)
                    if overlap / min(area, other_area) >= 0.70:
                        duplicate = True
                        break
                if duplicate:
                    continue
                kept.append({**proposal, "panel_block": block_name, "rank_score": score})
                if len(kept) == 3:
                    break
            panel_ranked.extend(kept)
        unique_ranked = {}
        for proposal in panel_ranked:
            unique_ranked.setdefault(proposal["proposal_id"], proposal)
        panel_ranked = list(unique_ranked.values())
        totals.setdefault("local24_palette_panel_top3", {
            "proposal_count": 0, "verified_misses_recovered": 0,
        })
        totals["local24_palette_panel_top3"]["proposal_count"] += len(panel_ranked)
        variant = {"proposal_count": len(panel_ranked), "maximum_per_number_block": 3}
        if miss and panel_ranked:
            candidates = []
            for proposal in panel_ranked:
                rank, coverage, area_ratio, recovered = _match(proposal, miss["bbox"])
                candidates.append((rank, proposal, coverage, area_ratio, recovered))
            _rank, best, coverage, area_ratio, recovered = max(candidates, key=lambda item: item[0])
            variant.update({
                "recovered": bool(recovered),
                "best_bbox": list(map(int, best["proposal_bbox"])),
                "best_coverage": float(coverage),
                "best_area_ratio": float(area_ratio),
                "best_role": best["prototype_role"],
                "best_panel_block": best["panel_block"],
                "best_rank_score": float(best["rank_score"]),
            })
            totals["local24_palette_panel_top3"]["verified_misses_recovered"] += int(recovered)
        elif miss:
            variant["recovered"] = False
        row["variants"]["local24_palette_panel_top3"] = variant
        paints.append(row)
    payload = {
        "schema": "smart-tga-small-copy-proposal-probe-v1",
        "reviewed_truth_used_only_for_evaluation": True,
        "filename_car_bbox_inference_authority": False,
        "paint_count": len(paints),
        "verified_miss_count": len(VERIFIED_MISSES),
        "totals": totals,
        "paints": paints,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen-scores", type=Path)
    args = parser.parse_args()
    result = run(args.inspection, args.output, args.frozen_scores)
    print(json.dumps(result["totals"], indent=2))


if __name__ == "__main__":
    main()
