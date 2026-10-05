"""Owner-neutral number context-envelope proposals with zero output authority."""

from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


DEFAULT_MODEL_PATH = Path(__file__).with_name("models") / "smart_tga_number_context_cycle696_v1.json"
DEFAULT_SEMANTIC_MODEL_PATH = Path(__file__).with_name("models") / "smart_tga_number_context_semantic_cycle697_v2.npz"
DEFAULT_POSITION_MODEL_PATH = Path(__file__).with_name("models") / "smart_tga_number_context_position_cycle699_v1.npz"


@lru_cache(maxsize=4)
def _load_model(path: str) -> Mapping[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != "smart-tga-number-context-prototypes-v1":
        raise ValueError("unsupported number-context prototype schema")
    return payload


def _apply_prototype(
    bbox: Sequence[int], prototype: Sequence[float], *, maximum_area_fraction: float,
    image_side: int = 1024,
) -> list[int] | None:
    x, y, width, height = (float(value) for value in bbox)
    dx, dy, log_width, log_height = (float(value) for value in prototype)
    new_width = min(float(image_side), max(4.0, width * math.exp(log_width)))
    new_height = min(float(image_side), max(4.0, height * math.exp(log_height)))
    if new_width * new_height > float(maximum_area_fraction) * image_side**2:
        return None
    center_x = x + width / 2.0 + dx * width
    center_y = y + height / 2.0 + dy * height
    x0 = max(0, min(image_side - 1, int(round(center_x - new_width / 2.0))))
    y0 = max(0, min(image_side - 1, int(round(center_y - new_height / 2.0))))
    x1 = max(x0 + 1, min(image_side, int(round(center_x + new_width / 2.0))))
    y1 = max(y0 + 1, min(image_side, int(round(center_y + new_height / 2.0))))
    return [x0, y0, x1 - x0, y1 - y0]


def number_context_shadow_telemetry(
    instances: Sequence[Any], features: Sequence[Any], *,
    rgb: np.ndarray | None = None,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    semantic_model_path: str | Path = DEFAULT_SEMANTIC_MODEL_PATH,
    position_model_path: str | Path = DEFAULT_POSITION_MODEL_PATH,
    score_semantics: bool = False,
    score_position: bool = False,
    export_full: bool = False,
) -> dict[str, Any]:
    """Generate immutable context bboxes; never classify or own their pixels."""
    model = _load_model(str(Path(model_path).resolve()))
    feature_by_id = {str(item.instance_id): item for item in features}
    seed_contract = model.get("intrinsic_seed_contract") or {}
    minimum_side = int(seed_contract.get("minimum_side", 4))
    area_min = float(seed_contract.get("area_fraction_min", 0.00005))
    area_max = float(seed_contract.get("area_fraction_max", 0.08))
    maximum_area = float((model.get("context_contract") or {}).get("maximum_area_fraction", 0.15))
    prototypes = tuple(model.get("prototypes") or ())
    proposals, seen = [], set()
    seed_records: dict[str, dict[str, Any]] = {}
    seed_count = 0
    for instance in instances:
        feature = feature_by_id.get(str(instance.instance_id))
        if feature is None:
            continue
        x, y, width, height = (int(value) for value in instance.bbox)
        area_fraction = float(feature.area_fraction)
        if width < minimum_side or height < minimum_side or not area_min <= area_fraction <= area_max:
            continue
        seed_count += 1
        seed_records[str(instance.instance_id)] = {
            "bbox": list(instance.bbox),
            "area_fraction": feature.area_fraction,
            "fill_ratio": feature.fill_ratio,
            "edge_density": feature.edge_density,
            "texture_entropy": feature.texture_entropy,
            "strong_gradient_fraction": feature.strong_gradient_fraction,
            "perceptual_lightness": feature.perceptual_lightness,
            "perceptual_chroma": feature.perceptual_chroma,
            "ocr_alpha_coverage": feature.ocr_alpha_coverage,
            "ocr_digit_coverage": feature.ocr_digit_coverage,
            "ocr_max_coverage": feature.ocr_max_coverage,
        }
        for prototype_index, prototype in enumerate(prototypes):
            bbox = _apply_prototype(
                (x, y, width, height), prototype,
                maximum_area_fraction=maximum_area,
            )
            if bbox is None:
                continue
            key = tuple(bbox)
            if key in seen:
                continue
            seen.add(key)
            digest = hashlib.sha1(
                f"{instance.instance_id}|{prototype_index}|{key}".encode("utf-8")
            ).hexdigest()[:16]
            proposals.append({
                "proposal_id": f"ncp:{digest}",
                "bbox": bbox,
                "source_crop_bbox": bbox,
                "seed_instance_id": str(instance.instance_id),
                "member_instance_ids": [str(instance.instance_id)],
                "prototype_index": prototype_index,
                "source": "number_context_envelope_shadow",
                "casts_votes": False,
                "ownership_authority": False,
                "adds_pixels": False,
            })
    semantic = None
    if score_semantics:
        if rgb is None:
            raise ValueError("rgb is required for number-context semantic shadow")
        from engine.spec_sculpt.number_context_semantics import context_feature_mapping
        from engine.spec_sculpt.number_family_shadow import PortableExtraTrees

        scorer = PortableExtraTrees(semantic_model_path)
        threshold = float(scorer.metadata["decision_threshold"])
        accepted = []
        for proposal in proposals:
            seed = seed_records[str(proposal["seed_instance_id"])]
            score = float(scorer.score(context_feature_mapping(rgb, proposal, seed)))
            proposal["number_score"] = round(score, 6)
            proposal["semantic_status"] = "accepted_number_candidate" if score >= threshold else "abstain"
            if score >= threshold:
                accepted.append(proposal)
        semantic = {
            "schema": "smart-tga-number-context-semantic-shadow-v1",
            "status": "shadow_only",
            "model_version": scorer.metadata.get("version"),
            "decision_threshold": threshold,
            "scored_proposal_count": len(proposals),
            "accepted_proposal_count": len(accepted),
            "accepted_samples": accepted[:24],
            "samples_truncated": len(accepted) > 24,
            "casts_votes": False,
            "ownership_authority": False,
            "adds_pixels": False,
        }
    position = None
    if score_position:
        if semantic is None:
            raise ValueError("semantic scoring is required before position corroboration")
        from engine.spec_sculpt.number_context_position import position_feature_mapping
        from engine.spec_sculpt.number_family_shadow import PortableExtraTrees

        scorer = PortableExtraTrees(position_model_path)
        threshold = float(scorer.metadata["decision_threshold"])
        accepted = []
        scored_count = 0
        for proposal in proposals:
            if proposal.get("semantic_status") != "accepted_number_candidate":
                proposal["position_status"] = "not_scored_semantic_abstain"
                continue
            score = float(scorer.score(position_feature_mapping(proposal)))
            scored_count += 1
            # Calibration uses a one-epsilon-above-negative threshold. Preserve
            # enough precision that telemetry serialization cannot cross it.
            proposal["position_score"] = round(score, 12)
            proposal["position_status"] = (
                "corroborated_number_candidate" if score >= threshold
                else "abstain_template_position"
            )
            if score >= threshold:
                accepted.append(proposal)
        position = {
            "schema": "smart-tga-number-context-position-shadow-v1",
            "status": "shadow_only",
            "role": "corroboration_only",
            "model_version": scorer.metadata.get("version"),
            "decision_threshold": threshold,
            "semantic_candidate_count": scored_count,
            "corroborated_candidate_count": len(accepted),
            "accepted_samples": accepted[:24],
            "samples_truncated": len(accepted) > 24,
            "casts_votes": False,
            "ownership_authority": False,
            "adds_pixels": False,
        }
    telemetry = {
        "schema": "smart-tga-number-context-shadow-v1",
        "status": "shadow_only",
        "model_version": model.get("version"),
        "seed_count": seed_count,
        "prototype_count": len(prototypes),
        "proposal_count": len(proposals),
        "proposal_growth": round(len(proposals) / max(1, len(instances)), 6),
        "proposal_samples": proposals[:24],
        "samples_truncated": len(proposals) > 24,
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }
    if semantic is not None:
        telemetry["semantic"] = semantic
    if position is not None:
        telemetry["position"] = position
    if export_full:
        telemetry["proposal_records"] = proposals
    return telemetry


__all__ = [
    "DEFAULT_MODEL_PATH", "DEFAULT_SEMANTIC_MODEL_PATH", "DEFAULT_POSITION_MODEL_PATH",
    "number_context_shadow_telemetry",
]
