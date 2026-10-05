"""Live, zero-authority shadow adapter for the frozen Cycle714 map-family scorer.

This module deliberately rebuilds the same owner-neutral probability proposals,
foundation features, immutable nested families, CLIP evidence and corroborative
owner/template features used by the paint-disjoint evaluator.  It only returns
telemetry; no object in this module can vote, own pixels, or mutate a layer.
"""

from __future__ import annotations

from functools import lru_cache
import json
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

from .number_context_component_features import component_feature_vector
from .number_context_component_proposals import component_proposal_candidates
from .number_context_family_similarity import (
    d4_cosine_similarity, normalized_visual_descriptor, prototype_margin,
)
from .number_context_relative_pixels import relative_pixel_feature_cube
from .number_map_family_features import (
    FAMILY_OCR_FEATURE_NAMES,
    FAMILY_OWNER_CORROBORATION_FEATURE_NAMES,
    FAMILY_RELATIONSHIP_FEATURE_NAMES,
    FAMILY_TEMPLATE_POSITION_FEATURE_NAMES,
    map_family_feature_vector,
    map_family_ocr_features,
    map_family_owner_corroboration_features,
    map_family_relationship_features,
    map_family_template_position_features,
    map_proposal_feature_vector,
)
from .number_map_family_model import (
    SCALAR_FEATURE_NAMES, clip_text_feature_vector, frozen_candidate_inference,
)
from .number_local_copy_proposals import palette_panel_local_copy_proposals
from .number_object_assembly import assemble_nested_proposal_families
from .number_object_segmentation import (
    build_tiny_unet, image_feature_tensor, probability_region_proposals,
    project_local_support,
)
from .number_object_transfer import isolated_object_views


MODEL_ROOT = Path(__file__).with_name("models")
DEFAULT_CANDIDATE_MODEL = MODEL_ROOT / "smart_tga_number_map_family_cycle714_v1.npz"
DEFAULT_FOUNDATION_MODEL = MODEL_ROOT / "smart_tga_number_object_foundation_fusion_cycle712_v1.npz"
DEFAULT_SEGMENT_MODEL = MODEL_ROOT / "smart_tga_number_object_segmenter_cycle712_v1.pt"
DEFAULT_PANEL_MAP = MODEL_ROOT / "smart_tga_dlm_panel_map_cycle660_v1.json"
DEFAULT_FAMILY_MODEL = MODEL_ROOT / "smart_tga_number_context_family_cycle704_v1.npz"
DEFAULT_PIXEL_MODEL = MODEL_ROOT / "smart_tga_number_context_conformal_cycle703_v1.joblib"
LOCAL_COPY_DIGIT_AMBIGUITY_TOLERANCE = 0.02
LOCAL_COPY_MAX_ORIENTATION_FREE_ASPECT = 4.0
LOCAL_COPY_MAX_LOG_ORIENTATION_FREE_ASPECT = float(
    np.log(LOCAL_COPY_MAX_ORIENTATION_FREE_ASPECT)
)
LOCAL_COPY_OCR_LONG_SIDE = 600
LOCAL_COPY_WORDMARK_MIN_CONFIDENCE = 0.75
LOCAL_COPY_WORDMARK_MIN_ALPHA_CHARS = 4

_MASK_NAMES = (
    "raw_instance_union", "seed_palette", "border_contrast",
    "hybrid_evidence", "seeded_graphcut",
)


def _bbox_intersection(first: Sequence[int], second: Sequence[int]) -> int:
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by),
    )


def _sigmoid(value: float | np.ndarray) -> float | np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0)))


def _foundation_probability(model: Mapping[str, np.ndarray], base: np.ndarray, embedding: np.ndarray) -> float:
    reduced = (embedding - model["pca_mean"]) @ model["pca_components"].T
    vector = np.concatenate((base, reduced))
    normalized = (vector - model["mean"]) / np.maximum(model["scale"], 1e-8)
    return float(_sigmoid(normalized @ model["coefficient"] + model["intercept"][0]))


def _connected_component_records(masks: Mapping[str, np.ndarray]) -> list[dict[str, Any]]:
    """Recreate the inspector's component ledger from final immutable masks."""
    records: list[dict[str, Any]] = []
    for layer in ("numbers", "sponsors", "template", "brand_graphics", "paint"):
        mask = masks.get(layer)
        if mask is None:
            continue
        count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
            (np.asarray(mask) > 0).astype(np.uint8), 8,
        )
        for component_index in range(1, count):
            x, y, width, height, area = (int(value) for value in stats[component_index])
            records.append({
                "layer": layer,
                "component_index": component_index - 1,
                "area_px": area,
                "bbox": [x, y, width, height],
            })
    return records


def _pixel_score(model: Any, record: Mapping[str, Any]) -> np.ndarray:
    cube = relative_pixel_feature_cube(
        record["rgb"], record["proposal_bbox"], record["hypotheses"],
    )
    return model.predict_proba(cube.reshape(-1, cube.shape[2]))[:, 1].reshape(cube.shape[:2])


def _build_efficientnet_teacher():
    import torch
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

    network = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT).eval()
    mean = torch.tensor([0.485, 0.456, 0.406])[None, :, None, None]
    std = torch.tensor([0.229, 0.224, 0.225])[None, :, None, None]

    def embed(view_sets):
        output = []
        with torch.no_grad():
            for start in range(0, len(view_sets), 8):
                chunk = view_sets[start:start + 8]
                tensor = torch.from_numpy(np.concatenate(chunk))
                feature = network.avgpool(network.features((tensor - mean) / std)).flatten(1).numpy()
                feature = feature.reshape(len(chunk), 2, 8, -1).mean(axis=2)
                feature /= np.linalg.norm(feature, axis=2, keepdims=True).clip(1e-8)
                output.extend(feature.reshape(len(chunk), -1))
        return output

    return embed


def _build_clip_teacher():
    import open_clip
    import torch
    from PIL import Image as PilImage

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _train, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k",
    )
    model = model.eval().to(device)
    prompts = (
        "Arabic numerals", "a group of large digits", "a two digit race car number",
        "large stylized racing numbers", "large stylized alphabetic letters",
        "an alphabetic acronym logo", "a word made of letters",
        "a company name wordmark", "a sponsor name", "a paint livery graphic",
        "an abstract logo symbol", "a racing team emblem",
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    with torch.no_grad():
        text = model.encode_text(tokenizer(prompts).to(device)).float()
        text = text / text.norm(dim=1, keepdim=True).clamp_min(1e-8)
    text_prototypes = text.cpu().numpy().astype(np.float32)

    def embed(view_sets):
        flat = [view for views in view_sets for view in views]
        if not flat:
            return np.zeros((0, 1024), np.float32)
        output = []
        with torch.no_grad():
            for start in range(0, len(flat), 64):
                images = [
                    preprocess(PilImage.fromarray(
                        (np.transpose(view, (1, 2, 0)).clip(0, 1) * 255).astype(np.uint8)
                    ))
                    for view in flat[start:start + 64]
                ]
                feature = model.encode_image(torch.stack(images).to(device)).float()
                feature = feature / feature.norm(dim=1, keepdim=True).clamp_min(1e-8)
                output.append(feature.cpu().numpy())
        matrix = np.concatenate(output).reshape(len(view_sets), 16, -1)
        appearance, silhouette = matrix[:, :8].mean(axis=1), matrix[:, 8:].mean(axis=1)
        appearance /= np.linalg.norm(appearance, axis=1, keepdims=True).clip(1e-8)
        silhouette /= np.linalg.norm(silhouette, axis=1, keepdims=True).clip(1e-8)
        return np.column_stack((appearance, silhouette)).astype(np.float32)

    return embed, text_prototypes


@lru_cache(maxsize=1)
def _runtime_assets():
    # Load sklearn before Torch/OpenMP. This order avoids a known Windows heap
    # corruption in the conformal-model unpickler.
    import sklearn  # noqa: F401
    import joblib
    import torch

    family = np.load(DEFAULT_FAMILY_MODEL, allow_pickle=False)
    segment_blob = torch.load(DEFAULT_SEGMENT_MODEL, map_location="cpu", weights_only=True)
    segment = build_tiny_unet(int(segment_blob["base_channels"]))
    segment.load_state_dict(segment_blob["state_dict"])
    segment.eval()
    return {
        "candidate": np.load(DEFAULT_CANDIDATE_MODEL, allow_pickle=False),
        "foundation": np.load(DEFAULT_FOUNDATION_MODEL, allow_pickle=False),
        "segment": segment,
        "prototypes": np.asarray(family["descriptors"], np.float32),
        "prototype_labels": np.asarray(family["labels"], bool),
        "pixel_models": joblib.load(DEFAULT_PIXEL_MODEL)["pixel_ensemble"],
        "panel_map": json.loads(DEFAULT_PANEL_MAP.read_text(encoding="utf-8")),
        "efficientnet": _build_efficientnet_teacher(),
        "clip": _build_clip_teacher(),
    }


def _proposal_records(
    rgb: np.ndarray,
    masks: Mapping[str, np.ndarray],
    segment_probability: np.ndarray,
    assets: Mapping[str, Any],
    map_proposals: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    components = _connected_component_records(masks)
    component_proposals = list(component_proposal_candidates(
        rgb.shape[:2], masks, components, min_pixels=400,
    ))
    selected_map_proposals = list(
        probability_region_proposals(segment_probability, rgb.shape[:2])
        if map_proposals is None else map_proposals
    )
    all_proposals = component_proposals + selected_map_proposals
    prepared = []
    for proposal in all_proposals:
        raw = proposal["raw_support"]
        record = {
            "proposal_bbox": proposal["proposal_bbox"], "rgb": rgb,
            "hypotheses": {name: raw for name in _MASK_NAMES},
        }
        descriptor = normalized_visual_descriptor(rgb, raw)
        prepared.append((proposal, record, descriptor))

    prototypes = assets["prototypes"]
    labels = assets["prototype_labels"]
    rgb_small = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_AREA)
    records = []
    views = []
    context_views = []
    bases = []
    for proposal, record, descriptor in prepared[len(component_proposals):]:
        raw = proposal["raw_support"]
        provenance = proposal["provenance"]
        margin = prototype_margin(descriptor, prototypes[labels], prototypes[~labels])
        score = np.mean([_pixel_score(model, record) for model in assets["pixel_models"]], axis=0)
        area = int(provenance.get("component_pixels", np.count_nonzero(raw)))
        peers = []
        for other, _other_record, other_descriptor in prepared[:len(component_proposals)]:
            other_area = int(other["provenance"].get("component_pixels", np.count_nonzero(other["raw_support"])))
            difference = abs(float(np.log(max(1, area) / max(1, other_area))))
            if difference <= 1.05:
                peers.append((d4_cosine_similarity(descriptor, other_descriptor), difference))
        peer_similarity, peer_difference = max(peers, default=(0.0, 8.0), key=lambda pair: pair[0])
        peer_count = sum(similarity >= 0.82 for similarity, _difference in peers)
        intrinsic = component_feature_vector(
            rgb, proposal["proposal_bbox"], raw,
            family_margin=float(margin), pixel_score=score,
            peer_similarity=float(peer_similarity), peer_count=peer_count,
            peer_area_log_difference=float(peer_difference),
        )
        small_mask = project_local_support(raw, proposal["proposal_bbox"], rgb.shape[:2], 256)
        values = segment_probability[small_mask]
        count = max(1, len(values) // 4)
        segment_score = float(np.mean(np.partition(values, len(values) - count)[-count:]))
        bases.append(np.concatenate((intrinsic, np.asarray([segment_score], np.float32))))
        if provenance.get("source_stage") == "number_object_local_palette_subinstance":
            x, y, width, height = map(int, proposal["proposal_bbox"])
            candidate_views = isolated_object_views(
                rgb[y:y + height, x:x + width], raw,
            )
            parent = provenance.get("parent_bbox") or proposal["proposal_bbox"]
            px, py, pwidth, pheight = map(int, parent)
            parent_crop = rgb[py:py + pheight, px:px + pwidth]
            parent_support = np.ones((pheight, pwidth), bool)
            context_views.append(isolated_object_views(parent_crop, parent_support))
            views.append(candidate_views)
        else:
            candidate_views = isolated_object_views(rgb_small, small_mask)
            views.append(candidate_views)
            context_views.append(candidate_views)
        records.append({
            "proposal_id": proposal["proposal_id"],
            "proposal_bbox": proposal["proposal_bbox"],
            "provenance": provenance,
            "raw_support": raw,
        })

    foundation_embeddings = assets["efficientnet"](views)
    clip_embed, _text_prototypes = assets["clip"]
    combined_clip_embeddings = clip_embed(views + context_views)
    clip_embeddings = combined_clip_embeddings[:len(views)]
    context_embeddings = combined_clip_embeddings[len(views):]
    probability_canvas = cv2.resize(
        segment_probability, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR,
    )
    for index, item in enumerate(records):
        foundation = _foundation_probability(assets["foundation"], bases[index], foundation_embeddings[index])
        item["foundation_probability"] = foundation
        item["vector"] = map_proposal_feature_vector(
            rgb, item["proposal_bbox"], item["raw_support"], probability_canvas,
            item["provenance"], foundation,
        )
        item["transfer_embedding"] = np.asarray(clip_embeddings[index], np.float32)
        item["context_embedding"] = np.asarray(context_embeddings[index], np.float32)
    return records


def _family_records(
    proposals: Sequence[Mapping[str, Any]],
    image: np.ndarray,
    layer_masks: Mapping[str, np.ndarray],
    ocr_regions: Sequence[Mapping[str, Any]],
    panel_map: Mapping,
) -> list[dict[str, Any]]:
    by_id = {item["proposal_id"]: item for item in proposals}
    families = []
    for family in assemble_nested_proposal_families(proposals):
        members = [by_id[item] for item in family["member_ids"]]
        embedding = np.mean([item["transfer_embedding"] for item in members], axis=0)
        embedding /= np.linalg.norm(embedding).clip(1e-8)
        context_embedding = np.mean([item["context_embedding"] for item in members], axis=0)
        context_embedding /= np.linalg.norm(context_embedding).clip(1e-8)
        outer = max(
            members,
            key=lambda item: int(item["proposal_bbox"][2]) * int(item["proposal_bbox"][3]),
        )
        families.append({
            "family_id": family["family_id"],
            "family_bbox": family["family_bbox"],
            "member_ids": list(family["member_ids"]),
            "vector": map_family_feature_vector(members),
            "ocr_features": map_family_ocr_features(family["family_bbox"], ocr_regions),
            "owner_features": map_family_owner_corroboration_features(
                outer["proposal_bbox"], outer["raw_support"], layer_masks,
            ),
            "position_features": map_family_template_position_features(
                outer["proposal_bbox"], outer["raw_support"], image.shape[:2], panel_map,
            ),
            "transfer_embedding": embedding.astype(np.float32),
            "context_embedding": context_embedding.astype(np.float32),
            # Retained only to derive owner-neutral shadow purity evidence.
            # It cannot cast a pixel-ownership vote and is never serialized.
            "raw_support": np.asarray(outer["raw_support"], bool),
        })
    return families


def _support_purity_features(raw_support: np.ndarray) -> dict[str, float]:
    """Describe visual fragmentation inside one immutable proposal support."""
    support = np.asarray(raw_support, bool)
    foreground = int(np.count_nonzero(support))
    if not foreground:
        return {
            "support_log_component_count": 0.0,
            "support_largest_component_fraction": 0.0,
            "support_component_area_entropy": 0.0,
        }
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        support.astype(np.uint8), connectivity=8,
    )
    minimum = max(4, int(round(foreground * 0.001)))
    areas = np.asarray([
        int(stats[index, cv2.CC_STAT_AREA])
        for index in range(1, count)
        if int(stats[index, cv2.CC_STAT_AREA]) >= minimum
    ], np.float64)
    if not len(areas):
        areas = np.asarray([foreground], np.float64)
    shares = areas / max(1.0, float(np.sum(areas)))
    entropy = -float(np.sum(shares * np.log(shares.clip(1e-12))))
    entropy /= float(np.log(max(2, len(shares))))
    return {
        "support_log_component_count": float(np.log1p(len(areas))),
        "support_largest_component_fraction": float(np.max(areas) / foreground),
        "support_component_area_entropy": entropy,
    }


def _proposal_conflict_features(
    families: Sequence[Mapping[str, Any]], index: int,
) -> dict[str, float]:
    """Measure normalized overlap with smaller sibling proposals.

    A mixed number-plus-wordmark panel often contains a cleaner, smaller
    proposal for the number itself.  This relationship is corroborative,
    position-neutral evidence of impurity; it never creates ownership.
    """
    x, y, width, height = map(int, families[index]["family_bbox"])
    area = max(1, width * height)
    best_containment = 0.0
    best_area_ratio = 0.0
    conflict_count = 0
    for peer_index, peer in enumerate(families):
        if peer_index == index:
            continue
        px, py, pwidth, pheight = map(int, peer["family_bbox"])
        peer_area = max(1, pwidth * pheight)
        ix0, iy0 = max(x, px), max(y, py)
        ix1, iy1 = min(x + width, px + pwidth), min(y + height, py + pheight)
        intersection = max(0, ix1 - ix0) * max(0, iy1 - iy0)
        if intersection / min(area, peer_area) >= 0.10:
            conflict_count += 1
        if peer_area >= area * 0.98:
            continue
        containment = intersection / peer_area
        if containment > best_containment:
            best_containment = containment
            best_area_ratio = peer_area / area
    return {
        "proposal_smaller_peer_containment": float(best_containment),
        "proposal_smaller_peer_area_ratio": float(best_area_ratio),
        "proposal_overlap_count_log": float(np.log1p(conflict_count)),
    }


def _score_family_records(
    families: Sequence[Mapping[str, Any]],
    assets: Mapping[str, Any],
    *,
    relationship_context: Sequence[Mapping[str, Any]] = (),
    include_visual_embeddings: bool = False,
) -> list[dict[str, Any]]:
    if not families:
        return []
    context = list(relationship_context) + list(families)
    context_embeddings = np.asarray(
        [item["transfer_embedding"] for item in context], np.float32,
    )
    context_areas = [
        max(1, int(item["family_bbox"][2]) * int(item["family_bbox"][3]))
        for item in context
    ]
    relationship = map_family_relationship_features(context_embeddings, context_areas)[
        len(relationship_context):
    ]
    embeddings = np.asarray([item["transfer_embedding"] for item in families], np.float32)
    _clip_embed, text_prototypes = assets["clip"]
    clip_text = np.asarray([
        clip_text_feature_vector(item["transfer_embedding"], text_prototypes)
        for item in families
    ], np.float32)
    context_clip_text = np.asarray([
        clip_text_feature_vector(item["context_embedding"], text_prototypes)
        for item in families
    ], np.float32)
    scalar = np.column_stack((
        np.asarray([item["vector"] for item in families], np.float32),
        relationship,
        np.asarray([item["ocr_features"] for item in families], np.float32),
        clip_text,
        np.asarray([item["owner_features"] for item in families], np.float32),
        np.asarray([item["position_features"] for item in families], np.float32),
    ))
    probability, accepted = frozen_candidate_inference(scalar, embeddings, assets["candidate"])
    digit_index = SCALAR_FEATURE_NAMES.index("clip_digit_similarity_max")
    alpha_index = SCALAR_FEATURE_NAMES.index("clip_alpha_similarity_max")
    graphic_index = SCALAR_FEATURE_NAMES.index("clip_graphic_similarity_max")
    digit_alpha_margin_index = SCALAR_FEATURE_NAMES.index("clip_digit_minus_alpha_margin")
    digit_negative_margin_index = SCALAR_FEATURE_NAMES.index("clip_digit_minus_all_negative_margin")
    peer_d4_index = SCALAR_FEATURE_NAMES.index("peer_d4_similarity_max")
    fill_ratio_index = SCALAR_FEATURE_NAMES.index("fill_ratio")
    aspect_index = SCALAR_FEATURE_NAMES.index("log_orientation_free_aspect")
    purity_scalar_names = (
        "edge_density", "strong_gradient_fraction", "texture_entropy",
        "family_log_member_count", "family_shape_instability",
        "family_texture_instability", "family_palette_instability",
    )
    purity_scalar_indices = tuple(
        SCALAR_FEATURE_NAMES.index(name) for name in purity_scalar_names
    )
    support_purity = [
        _support_purity_features(item["raw_support"]) for item in families
    ]
    proposal_conflict = [
        _proposal_conflict_features(families, index)
        for index in range(len(families))
    ]
    ocr_alpha_index = SCALAR_FEATURE_NAMES.index("ocr_alpha_family_coverage")
    ocr_digit_index = SCALAR_FEATURE_NAMES.index("ocr_digit_family_coverage")
    owner_index = SCALAR_FEATURE_NAMES.index("legacy_number_overlap")
    owner_sponsor_index = SCALAR_FEATURE_NAMES.index("legacy_sponsor_overlap")
    position_index = SCALAR_FEATURE_NAMES.index("template_number_fraction")
    position_sponsor_index = SCALAR_FEATURE_NAMES.index("template_sponsor_fraction")
    return [{
        "family_id": item["family_id"],
        "bbox": list(map(int, item["family_bbox"])),
        "member_ids": item["member_ids"],
        "probability": round(float(probability[index]), 6),
        "accepted": bool(accepted[index]),
        "clip_digit_evidence": round(float(scalar[index, digit_index]), 6),
        "clip_alpha_evidence": round(float(scalar[index, alpha_index]), 6),
        "clip_graphic_evidence": round(float(scalar[index, graphic_index]), 6),
        "clip_digit_minus_alpha_margin": round(
            float(scalar[index, digit_alpha_margin_index]), 6,
        ),
        "clip_digit_minus_all_negative_margin": round(
            float(scalar[index, digit_negative_margin_index]), 6,
        ),
        "peer_d4_similarity": round(float(scalar[index, peer_d4_index]), 6),
        "intrinsic_fill_ratio": round(float(scalar[index, fill_ratio_index]), 6),
        "intrinsic_log_orientation_free_aspect": round(
            float(scalar[index, aspect_index]), 6,
        ),
        "intrinsic_purity_features": {
            **{
                name: round(float(scalar[index, feature_index]), 6)
                for name, feature_index in zip(purity_scalar_names, purity_scalar_indices)
            },
            **{
                name: round(float(value), 6)
                for name, value in support_purity[index].items()
            },
            **{
                name: round(float(value), 6)
                for name, value in proposal_conflict[index].items()
            },
        },
        "ocr_alpha_family_coverage": round(float(scalar[index, ocr_alpha_index]), 6),
        "ocr_digit_family_coverage": round(float(scalar[index, ocr_digit_index]), 6),
        "legacy_number_overlap": round(float(scalar[index, owner_index]), 6),
        "legacy_sponsor_overlap": round(float(scalar[index, owner_sponsor_index]), 6),
        "template_number_evidence": round(float(scalar[index, position_index]), 6),
        "template_sponsor_evidence": round(float(scalar[index, position_sponsor_index]), 6),
        "context_clip_digit_evidence": round(float(context_clip_text[index, 0]), 6),
        "context_clip_alpha_evidence": round(float(context_clip_text[index, 2]), 6),
        "context_clip_graphic_evidence": round(float(context_clip_text[index, 4]), 6),
        "context_clip_digit_minus_all_negative_margin": round(
            float(context_clip_text[index, 7]), 6,
        ),
        **({
            "visual_embedding": [
                round(float(value), 7)
                for value in np.asarray(item["transfer_embedding"]).reshape(-1)
            ],
        } if include_visual_embeddings else {}),
    } for index, item in enumerate(families)]


def _apply_local_copy_adjudication(rows: Sequence[dict[str, Any]]) -> None:
    """Require local-copy digit evidence to be at least semantically ambiguous.

    CLIP's compact glyph crops can score a true outlined digit fractionally
    closer to the generic alpha prompt.  A 0.02 cosine near-tie preserves that
    ambiguity while rejecting locally prominent graphic crests.  Intrinsic
    orientation-free support shape also rejects stripe-like livery proposals
    whose major/minor aspect exceeds 4:1.  These are only corroboration gates
    on the new local branch; they cannot create an acceptance and never change
    global-map or OCR behavior.
    """
    for row in rows:
        frozen_accepted = bool(row["accepted"])
        digit_corroborated = (
            float(row["clip_digit_minus_all_negative_margin"])
            >= -LOCAL_COPY_DIGIT_AMBIGUITY_TOLERANCE
        )
        wordmark_veto = bool(row.get("local_wordmark_veto", False))
        shape_corroborated = (
            float(row.get("intrinsic_log_orientation_free_aspect", 0.0))
            <= LOCAL_COPY_MAX_LOG_ORIENTATION_FREE_ASPECT
        )
        row["frozen_scorer_accepted"] = frozen_accepted
        row["local_digit_corroborated"] = digit_corroborated
        row["local_shape_corroborated"] = shape_corroborated
        row["accepted"] = (
            frozen_accepted and digit_corroborated and shape_corroborated
            and not wordmark_veto
        )


def _annotate_local_wordmark_evidence(
    image: np.ndarray,
    families: Sequence[Mapping[str, Any]],
    rows: Sequence[dict[str, Any]],
    *,
    reader: Any | None = None,
) -> None:
    """Read locally scaled candidate crops and record strong alphabetic words.

    Full-texture OCR can miss small or diagonally laid-out sponsor words after
    the entire 1024px map is downscaled.  The local proposal branch already
    knows the immutable candidate box, so this evidence pass enlarges only
    frozen-scorer candidates that also pass the intrinsic digit ambiguity
    gate.  It can veto a local acceptance, but cannot create one or affect the
    global OCR route.
    """
    if len(families) != len(rows):
        raise ValueError("local family/score alignment mismatch")
    if reader is None:
        from .smart_separate import _reader
        reader = _reader()
    for family, row in zip(families, rows):
        row["local_ocr_evaluated"] = False
        row["local_ocr_tokens"] = []
        row["local_ocr_max_alpha_confidence"] = 0.0
        row["local_wordmark_veto"] = False
        if reader is None or not bool(row["accepted"]):
            continue
        if float(row["clip_digit_minus_all_negative_margin"]) < (
            -LOCAL_COPY_DIGIT_AMBIGUITY_TOLERANCE
        ):
            continue
        x, y, width, height = map(int, family["family_bbox"])
        crop = np.asarray(image)[y:y + height, x:x + width]
        if crop.size == 0:
            continue
        scale = max(1.0, LOCAL_COPY_OCR_LONG_SIDE / float(max(crop.shape[:2])))
        if scale > 1.0:
            crop = cv2.resize(
                crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC,
            )
        try:
            detections = reader.readtext(
                np.ascontiguousarray(crop), detail=1, paragraph=False,
            )
        except Exception:
            detections = ()
        tokens: list[dict[str, Any]] = []
        strongest = 0.0
        for _box, text, confidence in detections:
            clean = re.sub(r"[^0-9A-Za-z]", "", str(text or ""))
            if not clean:
                continue
            alpha_count = sum(character.isalpha() for character in clean)
            value = float(confidence)
            tokens.append({
                "text": clean,
                "confidence": round(value, 6),
                "alpha_characters": int(alpha_count),
            })
            if alpha_count >= LOCAL_COPY_WORDMARK_MIN_ALPHA_CHARS:
                strongest = max(strongest, value)
        row["local_ocr_evaluated"] = True
        row["local_ocr_tokens"] = tokens
        row["local_ocr_max_alpha_confidence"] = round(strongest, 6)
        row["local_wordmark_veto"] = (
            strongest >= LOCAL_COPY_WORDMARK_MIN_CONFIDENCE
        )


def _accepted_global_family_boxes(
    families: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]],
) -> tuple[Sequence[int], ...]:
    """Return only boxes whose frozen global decision already succeeded."""
    if len(families) != len(rows):
        raise ValueError("global family/score alignment mismatch")
    return tuple(
        family["family_bbox"]
        for family, row in zip(families, rows)
        if bool(row["accepted"])
    )


def number_map_family_shadow_telemetry(
    rgb: np.ndarray,
    masks: Mapping[str, np.ndarray],
    *,
    ocr_regions: Sequence[Mapping[str, Any]] = (),
    include_local_copy_proposals: bool = True,
    include_visual_embeddings: bool = False,
) -> dict[str, Any]:
    """Score all live probability-map families with no ownership authority."""
    import torch

    started = time.perf_counter()
    image = np.asarray(rgb, np.uint8)
    layer_masks = {
        name: np.asarray(masks.get(name, np.zeros(image.shape[:2], np.uint8))) > 0
        for name in ("numbers", "sponsors", "template", "paint", "brand_graphics")
    }
    assets = _runtime_assets()
    with torch.no_grad():
        segment_probability = torch.sigmoid(
            assets["segment"](torch.from_numpy(image_feature_tensor(image)[None]))
        )[0, 0].numpy()
    proposals = _proposal_records(image, layer_masks, segment_probability, assets)
    families = _family_records(
        proposals, image, layer_masks, ocr_regions, assets["panel_map"],
    )
    baseline_rows = _score_family_records(families, assets)
    for row in baseline_rows:
        row["proposal_branch"] = "global_probability_map"

    local_raw = (
        palette_panel_local_copy_proposals(image, segment_probability, assets["panel_map"])
        if include_local_copy_proposals else ()
    )
    # A rejected global family must not suppress a locally normalized,
    # full-resolution retry.  Deduplicate only evidence the frozen scorer has
    # already accepted; otherwise the local branch is starved on the exact
    # weak/compact copies it exists to recover.
    baseline_boxes = _accepted_global_family_boxes(families, baseline_rows)
    local_raw = tuple(
        proposal for proposal in local_raw
        if not any(
            _bbox_intersection(proposal["proposal_bbox"], bbox) / min(
                max(1, int(proposal["proposal_bbox"][2]) * int(proposal["proposal_bbox"][3])),
                max(1, int(bbox[2]) * int(bbox[3])),
            ) >= 0.72
            for bbox in baseline_boxes
        )
    )
    local_proposals = _proposal_records(
        image, layer_masks, segment_probability, assets, map_proposals=local_raw,
    ) if local_raw else []
    local_families = _family_records(
        local_proposals, image, layer_masks, ocr_regions, assets["panel_map"],
    )
    local_rows = _score_family_records(
        local_families, assets, relationship_context=families,
        include_visual_embeddings=include_visual_embeddings,
    )
    _annotate_local_wordmark_evidence(image, local_families, local_rows)
    _apply_local_copy_adjudication(local_rows)
    for row in local_rows:
        row["proposal_branch"] = "local_palette_panel"
    rows = baseline_rows + local_rows
    accepted_rows = [item for item in rows if item["accepted"]]
    rejected_rows = [item for item in rows if not item["accepted"]]
    candidate = assets["candidate"]
    return {
        "schema": "smart-tga-number-map-family-shadow-v1",
        "status": "shadow_only",
        "model_version": "cycle714_template_constrained_clip_v1",
        "local_proposal_adapter": "cycle717_local_palette_panel_v1",
        "local_digit_ambiguity_tolerance": LOCAL_COPY_DIGIT_AMBIGUITY_TOLERANCE,
        "local_max_orientation_free_aspect": LOCAL_COPY_MAX_ORIENTATION_FREE_ASPECT,
        "local_wordmark_min_confidence": LOCAL_COPY_WORDMARK_MIN_CONFIDENCE,
        "local_wordmark_min_alpha_chars": LOCAL_COPY_WORDMARK_MIN_ALPHA_CHARS,
        "proposal_count": len(proposals),
        "family_count": len(families),
        "local_proposal_count": len(local_proposals),
        "local_family_count": len(local_families),
        "local_accepted_family_count": sum(item["accepted"] for item in local_rows),
        "local_families": local_rows,
        "total_family_count": len(families) + len(local_families),
        "accepted_family_count": len(accepted_rows),
        "accepted_families": sorted(
            accepted_rows, key=lambda item: item["probability"], reverse=True,
        )[:24],
        "nearest_rejected": sorted(
            rejected_rows, key=lambda item: item["probability"], reverse=True,
        )[:24],
        "thresholds": {
            "probability": round(float(candidate["threshold"][0]), 6),
            "clip_digit": round(float(candidate["digit_threshold"][0]), 6),
            "legacy_number_overlap": round(float(candidate["number_overlap_threshold"][0]), 6),
            "template_number": round(float(candidate["template_number_threshold"][0]), 6),
        },
        "frozen": True,
        "fit_or_threshold_selection": False,
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
        "output_applied": False,
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


__all__ = [
    "DEFAULT_CANDIDATE_MODEL",
    "number_map_family_shadow_telemetry",
]
