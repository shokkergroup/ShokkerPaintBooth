"""One-shot frozen family+copy evaluation on a reviewed active DLM holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from engine.spec_sculpt.number_context_family_similarity import prototype_margin
    from scripts.smart_tga_number_context_conformal_probe import _metrics, _score
    from scripts.smart_tga_number_context_copy_probe import _copy_agreement
    from scripts.smart_tga_number_context_family_probe import _descriptor
    from scripts.smart_tga_number_context_relative_probe import _load_new
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_family_similarity import prototype_margin  # type: ignore
    from scripts.smart_tga_number_context_conformal_probe import _metrics, _score  # type: ignore
    from scripts.smart_tga_number_context_copy_probe import _copy_agreement  # type: ignore
    from scripts.smart_tga_number_context_family_probe import _descriptor  # type: ignore
    from scripts.smart_tga_number_context_relative_probe import _load_new  # type: ignore


def run(
    dataset: Path, family_model: Path, copy_model: Path, pixel_model: Path,
    selected_paint_count: int, upstream_controls: int,
) -> dict:
    import joblib

    records = _load_new(dataset)
    family = np.load(family_model)
    copy = np.load(copy_model)
    pixels = joblib.load(pixel_model)["pixel_ensemble"]
    prototypes = np.asarray(family["descriptors"], np.float32)
    prototype_labels = np.asarray(family["labels"], bool)
    positive_prototypes = prototypes[prototype_labels]
    control_prototypes = prototypes[~prototype_labels]
    family_gate = float(copy["family_gate"][0])
    copy_gate = float(copy["copy_gate"][0])
    pixel_fraction = float(copy["pixel_fraction"][0])

    pixel_scores = [
        np.mean([_score(model, record) for model in pixels], axis=0)
        for record in records
    ]
    descriptors = [_descriptor(record) for record in records]
    family_margins = np.asarray([
        prototype_margin(descriptor, positive_prototypes, control_prototypes)
        for descriptor in descriptors
    ], np.float32)
    base_accept = family_margins >= family_gate
    agreement = _copy_agreement(records, pixel_scores, family_margins, family_gate)
    copy_accept = (~base_accept) & (agreement >= copy_gate)
    final_accept = base_accept | copy_accept
    result = {
        "schema": "smart-tga-number-context-copy-holdout-probe-v1",
        "evaluated_once": True,
        "calibrated_on_holdout": False,
        "selected_paints": selected_paint_count,
        "paints_with_proposals": len({item["paint_label"] for item in records}),
        "paint_candidate_recall": round(len({item["paint_label"] for item in records}) / max(1, selected_paint_count), 6),
        "reviewed_number_records": len(records),
        "upstream_hard_negative_rejections": upstream_controls,
        "family_gate": family_gate,
        "copy_gate": copy_gate,
        "pixel_fraction": pixel_fraction,
        "family_only": _metrics(records, pixel_scores, family_margins, family_gate, pixel_fraction),
        "family_plus_copy": _metrics(records, pixel_scores, final_accept.astype(np.float32), 0.5, pixel_fraction),
        "records": [
            {"paint_label": item["paint_label"], "proposal_id": item["proposal_id"],
             "family_margin": round(float(margin), 6), "base_accept": bool(base),
             "copy_agreement": round(float(copy_score), 6), "copy_accept": bool(copied),
             "final_accept": bool(final)}
            for item, margin, base, copy_score, copied, final in zip(
                records, family_margins, base_accept, agreement, copy_accept, final_accept,
            )
        ],
        "runtime_integrated": False,
        "ownership_authority": False,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--family-model", type=Path, required=True)
    parser.add_argument("--copy-model", type=Path, required=True)
    parser.add_argument("--pixel-model", type=Path, required=True)
    parser.add_argument("--selected-paints", type=int, required=True)
    parser.add_argument("--upstream-controls", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.dataset, args.family_model, args.copy_model, args.pixel_model,
                 args.selected_paints, args.upstream_controls)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
