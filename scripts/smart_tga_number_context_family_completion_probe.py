"""Score immutable family-completion proposals on untouched DLM paints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_context_component_features import component_feature_vector, component_probability
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates
    from engine.spec_sculpt.number_context_family_completion import family_completion_candidates
    from engine.spec_sculpt.number_context_family_similarity import d4_cosine_similarity, prototype_margin
    from scripts.smart_tga_number_context_conformal_probe import _score
    from scripts.smart_tga_number_context_family_probe import _descriptor
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_component_features import component_feature_vector, component_probability  # type: ignore
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates  # type: ignore
    from engine.spec_sculpt.number_context_family_completion import family_completion_candidates  # type: ignore
    from engine.spec_sculpt.number_context_family_similarity import d4_cosine_similarity, prototype_margin  # type: ignore
    from scripts.smart_tga_number_context_conformal_probe import _score  # type: ignore
    from scripts.smart_tga_number_context_family_probe import _descriptor  # type: ignore


MASK_NAMES = ("raw_instance_union", "seed_palette", "border_contrast", "hybrid_evidence", "seeded_graphcut")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _source(root: Path, component_review: dict) -> Path:
    run = root / Path(str(component_review["inspection_records"]).replace("/", "\\")).parent
    slug = component_review["paint_label"].replace("/", "_").replace(" ", "_").removesuffix(".tga")
    return run / slug / "source_1024.png"


def _bbox_match(candidate, target) -> bool:
    x, y, width, height = (int(value) for value in candidate)
    tx, ty, tw, th = (int(value) for value in target)
    x0, y0, x1, y1 = max(x, tx), max(y, ty), min(x + width, tx + tw), min(y + height, ty + th)
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    cx, cy = x + width / 2.0, y + height / 2.0
    return (
        intersection / float(max(1, width * height)) >= 0.55
        and intersection / float(max(1, tw * th)) >= 0.04
        and tx <= cx <= tx + tw and ty <= cy <= ty + th
    )


def _score_paint(rgb, layer_masks, components, family, pixel_models, semantic_model):
    prototypes = np.asarray(family["descriptors"], np.float32)
    prototype_labels = np.asarray(family["labels"], bool)
    atom_proposals = component_proposal_candidates(rgb.shape[:2], layer_masks, components, min_pixels=20)
    baseline_ids = {
        item["proposal_id"] for item in component_proposal_candidates(rgb.shape[:2], layer_masks, components, min_pixels=400)
    }
    completed = family_completion_candidates(
        rgb.shape[:2], layer_masks, components, min_atom_pixels=20, min_group_pixels=400, max_members=3,
    )
    atom_records, atom_scores, atom_descriptors = {}, {}, {}
    for proposal in atom_proposals:
        raw = proposal["raw_support"]
        record = {"rgb": rgb, "proposal_bbox": proposal["proposal_bbox"],
                  "hypotheses": {name: raw for name in MASK_NAMES}}
        key = (proposal["provenance"]["source_layer"], proposal["provenance"]["component_index"])
        atom_records[key] = proposal
        atom_scores[key] = np.mean([_score(model, record) for model in pixel_models], axis=0)
        atom_descriptors[key] = _descriptor(record)

    candidates = []
    for proposal in tuple(atom_proposals) + tuple(completed):
        if proposal["proposal_id"].startswith("ncc:") and proposal["proposal_id"] not in baseline_ids:
            continue
        raw = proposal["raw_support"]
        bbox = proposal["proposal_bbox"]
        if "provenance" in proposal:
            member_keys = ((proposal["provenance"]["source_layer"], proposal["provenance"]["component_index"]),)
            pixel_score = atom_scores[member_keys[0]]
        else:
            member_keys = tuple(
                (item["source_layer"], item["component_index"]) for item in proposal["member_provenance"]
            )
            x, y, width, height = bbox
            pixel_score = np.zeros((height, width), np.float32)
            for key in member_keys:
                atom = atom_records[key]
                ax, ay, aw, ah = atom["proposal_bbox"]
                pixel_score[ay - y:ay - y + ah, ax - x:ax - x + aw] = np.maximum(
                    pixel_score[ay - y:ay - y + ah, ax - x:ax - x + aw], atom_scores[key],
                )
        record = {"rgb": rgb, "proposal_bbox": bbox, "hypotheses": {name: raw for name in MASK_NAMES}}
        descriptor = _descriptor(record)
        margin = prototype_margin(descriptor, prototypes[prototype_labels], prototypes[~prototype_labels])
        peers = []
        own = set(member_keys)
        area = int(np.count_nonzero(raw))
        for key, other_descriptor in atom_descriptors.items():
            if key in own:
                continue
            other_area = int(atom_records[key]["provenance"]["component_pixels"])
            difference = abs(float(np.log(max(1, area) / max(1, other_area))))
            if difference <= 1.05:
                peers.append((d4_cosine_similarity(descriptor, other_descriptor), difference))
        peer_similarity, peer_difference = max(peers, default=(0.0, 8.0), key=lambda pair: pair[0])
        peer_count = sum(similarity >= 0.82 for similarity, _difference in peers)
        vector = component_feature_vector(
            rgb, bbox, raw, family_margin=float(margin), pixel_score=pixel_score,
            peer_similarity=float(peer_similarity), peer_count=peer_count,
            peer_area_log_difference=float(peer_difference),
        )
        probability = component_probability(
            vector, semantic_model["mean"], semantic_model["scale"], semantic_model["coefficient"],
            float(semantic_model["intercept"][0]),
        )
        candidates.append({
            "proposal_id": proposal["proposal_id"], "bbox": bbox,
            "member_keys": member_keys, "probability": probability,
            "accepted": probability >= float(semantic_model["threshold"][0]),
            "completed": proposal["proposal_id"].startswith("ncf:"),
        })
    return candidates, len(atom_proposals), len(completed)


def _metrics(rows):
    paints = {row["paint_label"] for row in rows}
    hit_paints = {row["paint_label"] for row in rows if row["positive_hits"]}
    copies = sum(row["truth_copies"] for row in rows)
    copy_hits = sum(row["positive_hits"] for row in rows)
    controls = sum(row["accepted_controls"] for row in rows)
    return {"paint_coverage": f"{len(hit_paints)}/{len(paints)}", "copy_hits": f"{copy_hits}/{copies}",
            "accepted_reviewed_controls": controls}


def run(root: Path, label_root: Path, cycles, family_model: Path, pixel_model: Path, semantic_model: Path):
    import joblib
    family = np.load(family_model)
    pixel_models = joblib.load(pixel_model)["pixel_ensemble"]
    semantic = np.load(semantic_model)
    all_rows = []
    totals = {"atom_proposals": 0, "completion_proposals": 0}
    for cycle in cycles:
        missed_path = label_root / f"cycle{cycle}_missed_number_instances_v1.json"
        missed = _read(missed_path)
        by_paint = {}
        for item in missed["instances"]:
            by_paint.setdefault(item["paint_label"], []).append(item)
        for component_path in sorted(label_root.glob(f"cycle{cycle}_*_numbers_v1.json")):
            review = _read(component_path)
            paint_label = review["paint_label"]
            if paint_label not in by_paint:
                continue
            source = _source(root, review)
            parent = source.parent
            rgb = np.asarray(Image.open(source).convert("RGB"))
            components = _read(parent / "component_records.json")
            layer_masks = {path.stem: np.asarray(Image.open(path).convert("L")) > 0
                           for path in (parent / "masks").glob("*.png")}
            candidates, atom_count, completion_count = _score_paint(
                rgb, layer_masks, components, family, pixel_models, semantic,
            )
            totals["atom_proposals"] += atom_count
            totals["completion_proposals"] += completion_count
            truth = by_paint[paint_label]
            false_keys = {
                (item["layer"], int(item["component_index"]))
                for item in review["component_labels"] if item.get("target_layer") != "numbers"
            }
            for mode, eligible in (
                ("baseline_components", [item for item in candidates if not item["completed"]]),
                ("with_family_completion", candidates),
            ):
                accepted = [item for item in eligible if item["accepted"]]
                positive_hits = sum(any(_bbox_match(item["bbox"], target["bbox"]) for item in accepted) for target in truth)
                controls = {
                    key for item in accepted
                    if not any(_bbox_match(item["bbox"], target["bbox"]) for target in truth)
                    for key in item["member_keys"] if key in false_keys
                }
                all_rows.append({"mode": mode, "paint_label": paint_label, "truth_copies": len(truth),
                                 "positive_hits": positive_hits, "accepted_controls": len(controls),
                                 "accepted_candidates": len(accepted)})
    baseline = [item for item in all_rows if item["mode"] == "baseline_components"]
    completed = [item for item in all_rows if item["mode"] == "with_family_completion"]
    return {
        "schema": "smart-tga-number-context-family-completion-probe-v1",
        "evaluated_once": True, "calibrated_on_holdout": False, "holdout_cycles": list(cycles),
        **totals, "baseline": _metrics(baseline), "with_family_completion": _metrics(completed),
        "paint_records": all_rows, "runtime_integrated": False, "ownership_authority": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--label-root", type=Path, required=True)
    parser.add_argument("--cycles", nargs="+", type=int, required=True)
    parser.add_argument("--family-model", type=Path, required=True)
    parser.add_argument("--pixel-model", type=Path, required=True)
    parser.add_argument("--semantic-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.label_root, args.cycles, args.family_model, args.pixel_model, args.semantic_model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
