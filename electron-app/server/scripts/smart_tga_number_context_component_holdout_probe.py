"""One-shot evaluation of the frozen Cycle707 component gate on a fresh DLM holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_context_component_proposals import component_area_fraction, component_proposal_candidates
    from engine.spec_sculpt.number_context_family_similarity import prototype_margin
    from scripts.smart_tga_number_context_conformal_probe import _metrics, _score
    from scripts.smart_tga_number_context_copy_probe import _copy_agreement
    from scripts.smart_tga_number_context_family_probe import _descriptor
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_component_proposals import component_area_fraction, component_proposal_candidates  # type: ignore
    from engine.spec_sculpt.number_context_family_similarity import prototype_margin  # type: ignore
    from scripts.smart_tga_number_context_conformal_probe import _metrics, _score  # type: ignore
    from scripts.smart_tga_number_context_copy_probe import _copy_agreement  # type: ignore
    from scripts.smart_tga_number_context_family_probe import _descriptor  # type: ignore


MASK_NAMES = ("raw_instance_union", "seed_palette", "border_contrast", "hybrid_evidence", "seeded_graphcut")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    queue_path: Path, review_path: Path, family_model: Path, copy_model: Path,
    component_model: Path, pixel_model: Path,
) -> dict:
    import joblib

    queue = _read(queue_path)
    review = _read(review_path)
    reviewed = {
        (item["paint_label"], item["layer"], int(item["component_index"])): item["class"]
        for item in review["records"]
    }
    family = np.load(family_model)
    copy = np.load(copy_model)
    component = np.load(component_model)
    pixel_models = joblib.load(pixel_model)["pixel_ensemble"]
    prototypes = np.asarray(family["descriptors"], np.float32)
    labels = np.asarray(family["labels"], bool)
    family_gate = float(copy["family_gate"][0])
    copy_gate = float(copy["copy_gate"][0])
    pixel_fraction = float(copy["pixel_fraction"][0])
    area_gate = float(component["minimum_area_fraction"][0])
    margin_floor = float(component["minimum_family_margin"][0])

    records = []
    total_proposals = 0
    for paint in queue["selected_paints"]:
        paint_label = paint["paint_label"]
        source_path = Path(paint["source_1024"])
        parent = source_path.parent
        rgb = np.asarray(Image.open(source_path).convert("RGB"))
        components = _read(parent / "component_records.json")
        layer_masks = {
            path.stem: np.asarray(Image.open(path).convert("L")) > 0
            for path in (parent / "masks").glob("*.png")
        }
        proposals = component_proposal_candidates(rgb.shape[:2], layer_masks, components, min_pixels=400)
        total_proposals += len(proposals)
        for proposal in proposals:
            provenance = proposal["provenance"]
            key = (paint_label, provenance["source_layer"], provenance["component_index"])
            if key not in reviewed:
                continue
            raw = proposal["raw_support"]
            kind = reviewed[key]
            records.append({
                "paint_label": paint_label,
                "proposal_id": proposal["proposal_id"],
                "proposal_bbox": proposal["proposal_bbox"],
                "rgb": rgb,
                "hypotheses": {name: raw for name in MASK_NAMES},
                "label_mask": raw if kind == "Number" else np.zeros(raw.shape, bool),
                "label_kind": "number_core" if kind == "Number" else "empty_control",
                "review_class": kind,
                "provenance": provenance,
                "component_area_fraction": component_area_fraction(raw, rgb.shape[:2]),
            })
    found = {
        (item["paint_label"], item["provenance"]["source_layer"], item["provenance"]["component_index"])
        for item in records
    }
    if len(records) != len(reviewed):
        raise AssertionError(f"reviewed components missing from adapter: {sorted(set(reviewed) - found)}")

    pixel_scores = [
        np.mean([_score(model, record) for model in pixel_models], axis=0)
        for record in records
    ]
    descriptors = [_descriptor(record) for record in records]
    margins = np.asarray([
        prototype_margin(descriptor, prototypes[labels], prototypes[~labels])
        for descriptor in descriptors
    ], np.float32)
    base_accept = margins >= family_gate
    agreement = _copy_agreement(records, pixel_scores, margins, family_gate)
    copy_accept = (~base_accept) & (agreement >= copy_gate)
    legacy_accept = base_accept | copy_accept
    area_fractions = np.asarray([item["component_area_fraction"] for item in records], np.float32)
    intrinsic_accept = (area_fractions >= area_gate) & (margins >= margin_floor)
    metrics = _metrics(records, pixel_scores, intrinsic_accept.astype(np.float32), 0.5, pixel_fraction)

    number_paints = {item["paint_label"] for item in records if item["label_kind"] == "number_core"}
    accepted_number_paints = {
        item["paint_label"] for item, accepted in zip(records, intrinsic_accept)
        if accepted and item["label_kind"] == "number_core"
    }
    accepted_controls = sum(
        bool(accepted) and item["label_kind"] == "empty_control"
        for item, accepted in zip(records, intrinsic_accept)
    )
    return {
        "schema": "smart-tga-number-context-component-holdout-v1",
        "evaluated_once": True,
        "calibrated_on_holdout": False,
        "selected_paints": len(queue["selected_paints"]),
        "all_owner_neutral_proposals": total_proposals,
        "reviewed_candidates": len(records),
        "reviewed_number_records": sum(item["label_kind"] == "number_core" for item in records),
        "reviewed_control_records": sum(item["label_kind"] == "empty_control" for item in records),
        "adapter_number_paint_coverage": len(number_paints),
        "intrinsic_gate_number_paint_coverage": len(accepted_number_paints),
        "accepted_controls": accepted_controls,
        "frozen_thresholds": {
            "minimum_area_fraction": area_gate,
            "minimum_family_margin": margin_floor,
            "family_gate": family_gate,
            "copy_gate": copy_gate,
            "pixel_fraction": pixel_fraction,
        },
        "legacy_family_plus_copy": _metrics(
            records, pixel_scores, legacy_accept.astype(np.float32), 0.5, pixel_fraction,
        ),
        "intrinsic_component_gate": metrics,
        "acceptance_pass": len(accepted_number_paints) == len(queue["selected_paints"]) and accepted_controls == 0,
        "records": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "review_class": item["review_class"], "provenance": item["provenance"],
             "family_margin": round(float(margin), 6),
             "component_area_fraction": item["component_area_fraction"],
             "legacy_accept": bool(old), "intrinsic_accept": bool(new)}
            for item, margin, old, new in zip(records, margins, legacy_accept, intrinsic_accept)
        ],
        "runtime_integrated": False,
        "ownership_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--family-model", type=Path, required=True)
    parser.add_argument("--copy-model", type=Path, required=True)
    parser.add_argument("--component-model", type=Path, required=True)
    parser.add_argument("--pixel-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.queue, args.review, args.family_model, args.copy_model,
        args.component_model, args.pixel_model,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
