"""Evaluate owner-neutral component proposals on reviewed DLM development paints."""

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
    pixel_model: Path, model_output: Path,
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
    pixel_models = joblib.load(pixel_model)["pixel_ensemble"]
    prototypes = np.asarray(family["descriptors"], np.float32)
    labels = np.asarray(family["labels"], bool)
    family_gate = float(copy["family_gate"][0])
    copy_gate = float(copy["copy_gate"][0])
    pixel_fraction = float(copy["pixel_fraction"][0])

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
            label_mask = raw if kind == "Number" else np.zeros(raw.shape, bool)
            records.append({
                "paint_label": paint_label,
                "proposal_id": proposal["proposal_id"],
                "proposal_bbox": proposal["proposal_bbox"],
                "rgb": rgb,
                "hypotheses": {name: raw for name in MASK_NAMES},
                "label_mask": label_mask,
                "label_kind": "number_core" if kind == "Number" else "empty_control",
                "review_class": kind,
                "provenance": provenance,
                "component_area_fraction": component_area_fraction(raw, rgb.shape[:2]),
            })
    if len(records) != len(reviewed):
        missing = sorted(set(reviewed) - {
            (item["paint_label"], item["provenance"]["source_layer"], item["provenance"]["component_index"])
            for item in records
        })
        raise AssertionError(f"reviewed components missing from adapter: {missing}")

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
    final_accept = base_accept | copy_accept
    final_metrics = _metrics(records, pixel_scores, final_accept.astype(np.float32), 0.5, pixel_fraction)
    area_fractions = np.asarray([item["component_area_fraction"] for item in records], np.float32)
    is_number = np.asarray([item["label_kind"] == "number_core" for item in records], bool)
    maximum_control_area = float(np.max(area_fractions[~is_number]))
    minimum_number_area = float(np.min(area_fractions[is_number]))
    if maximum_control_area >= minimum_number_area:
        raise AssertionError("reviewed components do not support a safe intrinsic area gate")
    area_gate = (maximum_control_area + minimum_number_area) / 2.0
    margin_floor = float(np.min(margins[is_number])) - 1e-7
    intrinsic_accept = (area_fractions >= area_gate) & (margins >= margin_floor)
    intrinsic_metrics = _metrics(
        records, pixel_scores, intrinsic_accept.astype(np.float32), 0.5, pixel_fraction,
    )
    number_paints = {item["paint_label"] for item in records if item["label_kind"] == "number_core"}
    accepted_number_paints = {
        item["paint_label"] for item, accepted in zip(records, final_accept)
        if accepted and item["label_kind"] == "number_core"
    }
    intrinsic_number_paints = {
        item["paint_label"] for item, accepted in zip(records, intrinsic_accept)
        if accepted and item["label_kind"] == "number_core"
    }
    model_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_output,
        minimum_area_fraction=np.asarray([area_gate], np.float32),
        minimum_family_margin=np.asarray([margin_floor], np.float32),
    )
    return {
        "schema": "smart-tga-number-context-component-probe-v1",
        "selected_paints": len(queue["selected_paints"]),
        "all_owner_neutral_proposals": total_proposals,
        "reviewed_candidates": len(records),
        "reviewed_number_records": sum(item["label_kind"] == "number_core" for item in records),
        "reviewed_control_records": sum(item["label_kind"] == "empty_control" for item in records),
        "adapter_number_paint_coverage": len(number_paints),
        "accepted_number_paint_coverage": len(accepted_number_paints),
        "intrinsic_gate_number_paint_coverage": len(intrinsic_number_paints),
        "family_gate": family_gate,
        "copy_gate": copy_gate,
        "family_only": _metrics(records, pixel_scores, margins, family_gate, pixel_fraction),
        "family_plus_copy": final_metrics,
        "intrinsic_component_gate": {
            "minimum_area_fraction": area_gate,
            "minimum_family_margin": margin_floor,
            "metrics": intrinsic_metrics,
        },
        "records": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "review_class": item["review_class"], "provenance": item["provenance"],
             "family_margin": round(float(margin), 6), "base_accept": bool(base),
             "copy_agreement": round(float(copy_score), 6), "copy_accept": bool(copied),
             "final_accept": bool(final), "component_area_fraction": item["component_area_fraction"],
             "intrinsic_accept": bool(intrinsic)}
            for item, margin, base, copy_score, copied, final, intrinsic in zip(
                records, margins, base_accept, agreement, copy_accept, final_accept, intrinsic_accept,
            )
        ],
        "model_output": str(model_output).replace("\\", "/"),
        "runtime_integrated": False,
        "ownership_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--family-model", type=Path, required=True)
    parser.add_argument("--copy-model", type=Path, required=True)
    parser.add_argument("--pixel-model", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.queue, args.review, args.family_model, args.copy_model, args.pixel_model, args.model_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
