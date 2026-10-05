"""Apply one frozen Smart TGA map-family candidate to an untouched holdout.

This evaluator never fits, calibrates, or changes a threshold.  It rebuilds the
same immutable family features as training, applies the serialized Cycle714
candidate, and emits reviewable shadow decisions with zero output authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from engine.spec_sculpt.number_map_family_features import map_family_relationship_features
    from engine.spec_sculpt.number_map_family_model import (
        SCALAR_FEATURE_NAMES, clip_text_feature_vector, frozen_candidate_inference,
    )
    from scripts.smart_tga_number_map_family_probe import (
        _build_clip_teacher, _family_records, _summary,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_map_family_features import map_family_relationship_features  # type: ignore
    from engine.spec_sculpt.number_map_family_model import (  # type: ignore
        SCALAR_FEATURE_NAMES, clip_text_feature_vector, frozen_candidate_inference,
    )
    from scripts.smart_tga_number_map_family_probe import (  # type: ignore
        _build_clip_teacher, _family_records, _summary,
    )


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    inspection: Path, active_pool: Path, segment_model: Path, panel_map_path: Path,
    candidate_model: Path, output: Path, reviews: Path | None = None,
):
    teacher, text_prototypes = _build_clip_teacher()
    panel_map = _read(panel_map_path)
    families = _family_records(
        inspection, active_pool, reviews, segment_model, teacher, panel_map,
    )
    base = np.asarray([item["vector"] for item in families], np.float32)
    embedding = np.asarray([item["transfer_embedding"] for item in families], np.float32)
    groups = np.asarray([item["paint_label"] for item in families], object)
    relationship = np.zeros((len(families), len(FAMILY_RELATIONSHIP_FEATURE_NAMES)), np.float32)
    for paint_label in sorted(set(groups)):
        indexes = np.flatnonzero(groups == paint_label)
        areas = [
            max(1, int(families[index]["family_bbox"][2]) * int(families[index]["family_bbox"][3]))
            for index in indexes
        ]
        relationship[indexes] = map_family_relationship_features(embedding[indexes], areas)
    ocr = np.asarray([item["ocr_features"] for item in families], np.float32)
    owner = np.asarray([item["owner_features"] for item in families], np.float32)
    position = np.asarray([item["position_features"] for item in families], np.float32)
    clip_text = np.asarray([
        clip_text_feature_vector(item["transfer_embedding"], text_prototypes)
        for item in families
    ], np.float32)
    scalar = np.column_stack((base, relationship, ocr, clip_text, owner, position))
    candidate = np.load(candidate_model, allow_pickle=False)
    probability, accepted = frozen_candidate_inference(scalar, embedding, candidate)
    digit_index = SCALAR_FEATURE_NAMES.index("clip_digit_similarity_max")
    owner_index = SCALAR_FEATURE_NAMES.index("legacy_number_overlap")
    position_index = SCALAR_FEATURE_NAMES.index("template_number_fraction")
    scores = [
        {
            "paint_label": item["paint_label"], "family_id": item["family_id"],
            "family_bbox": list(map(int, item["family_bbox"])),
            "member_ids": list(item["member_ids"]), "member_labels": item["member_labels"],
            "is_number": item["is_number"], "probability": round(float(score), 6),
            "accepted": bool(decision),
            "clip_digit_evidence": round(float(scalar[index, digit_index]), 6),
            "legacy_number_overlap": round(float(scalar[index, owner_index]), 6),
            "template_number_evidence": round(float(scalar[index, position_index]), 6),
        }
        for index, (item, score, decision) in enumerate(zip(families, probability, accepted))
    ]
    payload = {
        "schema": "smart-tga-number-map-family-frozen-holdout-v1",
        "candidate_model": str(candidate_model).replace("\\", "/"),
        "candidate_thresholds": {
            "probability": round(float(candidate["threshold"][0]), 6),
            "clip_digit": round(float(candidate["digit_threshold"][0]), 6),
            "legacy_number_overlap": round(float(candidate["number_overlap_threshold"][0]), 6),
            "template_number": round(float(candidate["template_number_threshold"][0]), 6),
        },
        "holdout_family_count": len(families),
        "holdout_paint_count": len(set(groups)),
        "accepted_family_count": int(np.count_nonzero(accepted)),
        "metrics": (
            _summary(np.asarray([item["is_number"] for item in families], bool), accepted)
            if reviews is not None else None
        ),
        "scores": scores,
        "frozen": True, "fit_or_threshold_selection": False,
        "casts_votes": False, "ownership_authority": False,
        "default_runtime_changed": False, "exact_reconstruction_impact": "none",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--active-pool", type=Path, required=True)
    parser.add_argument("--segment-model", type=Path, required=True)
    parser.add_argument("--panel-map", type=Path, required=True)
    parser.add_argument("--candidate-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    payload = run(
        args.inspection, args.active_pool, args.segment_model, args.panel_map,
        args.candidate_model, args.output, args.reviews,
    )
    print(json.dumps({
        "holdout_family_count": payload["holdout_family_count"],
        "accepted_family_count": payload["accepted_family_count"],
        "metrics": payload["metrics"],
    }, indent=2))


if __name__ == "__main__":
    main()
