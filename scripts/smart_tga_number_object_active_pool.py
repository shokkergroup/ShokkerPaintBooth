"""Score and rank a fresh DLM inspection pool with frozen number-object models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_context_component_features import component_feature_vector
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates
    from engine.spec_sculpt.number_context_family_similarity import d4_cosine_similarity, prototype_margin
    from engine.spec_sculpt.number_object_segmentation import (
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
        project_local_support,
    )
    from engine.spec_sculpt.number_object_transfer import isolated_object_views
    from scripts.smart_tga_number_context_conformal_probe import _score
    from scripts.smart_tga_number_context_family_probe import _descriptor
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_component_features import component_feature_vector  # type: ignore
    from engine.spec_sculpt.number_context_component_proposals import component_proposal_candidates  # type: ignore
    from engine.spec_sculpt.number_context_family_similarity import d4_cosine_similarity, prototype_margin  # type: ignore
    from engine.spec_sculpt.number_object_segmentation import (  # type: ignore
        build_tiny_unet, image_feature_tensor, probability_region_proposals,
        project_local_support,
    )
    from engine.spec_sculpt.number_object_transfer import isolated_object_views  # type: ignore
    from scripts.smart_tga_number_context_conformal_probe import _score  # type: ignore
    from scripts.smart_tga_number_context_family_probe import _descriptor  # type: ignore


MASK_NAMES = ("raw_instance_union", "seed_palette", "border_contrast", "hybrid_evidence", "seeded_graphcut")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sigmoid(value):
    return 1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0)))


def _linear_probability(model, vector):
    normalized = (vector - model["mean"]) / np.maximum(model["scale"], 1e-8)
    return float(_sigmoid(np.dot(normalized, model["coefficient"]) + model["intercept"][0]))


def _foundation_probability(model, base, embedding):
    reduced = np.dot(embedding - model["pca_mean"], model["pca_components"].T)
    return _linear_probability(model, np.concatenate((base, reduced)))


def _build_transfer_teacher():
    import torch
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0
    network = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT).eval()
    mean = torch.tensor([0.485, 0.456, 0.406])[None, :, None, None]
    std = torch.tensor([0.229, 0.224, 0.225])[None, :, None, None]

    def embed(views):
        output = []
        with torch.no_grad():
            for start in range(0, len(views), 8):
                chunk = views[start:start + 8]
                tensor = torch.from_numpy(np.concatenate(chunk))
                feature = network.avgpool(network.features((tensor - mean) / std)).flatten(1).numpy()
                feature = feature.reshape(len(chunk), 2, 8, -1).mean(axis=2)
                feature /= np.linalg.norm(feature, axis=2, keepdims=True).clip(1e-8)
                output.extend(feature.reshape(len(chunk), -1))
        return output

    return embed


def _overlay(rgb, records, destination):
    image = Image.fromarray(rgb).convert("RGB")
    draw = ImageDraw.Draw(image)
    for item in records:
        x, y, width, height = item["bbox"]
        accepted = item["foundation_probability"] >= item["foundation_threshold"]
        color = (30, 245, 100) if accepted else ((255, 180, 30) if item["uncertainty"] < 0.10 else (120, 180, 255))
        draw.rectangle((x, y, x + width, y + height), outline=color, width=3)
        text = f"{item['component_index']} {item['source_layer'][:1].upper()} old {item['cycle710_probability']:.2f} new {item['foundation_probability']:.2f}"
        draw.rectangle((x, max(0, y - 16), min(image.width, x + 245), y), fill=(8, 8, 12))
        draw.text((x + 2, max(0, y - 15)), text, fill=color)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


def run(
    inspection: Path, output_dir: Path,
    baseline_model: Path | None = None,
    foundation_model: Path | None = None,
    segment_model: Path | None = None,
    paint_labels: set[str] | None = None,
    include_probability_proposals: bool = False,
):
    # Import sklearn's native stack before Torch/OpenMP.  Reversing this order can
    # trigger a Windows heap-corruption exit while unpickling the conformal model.
    import sklearn  # noqa: F401
    import joblib
    import torch
    from PIL import Image

    model_root = Path("engine/spec_sculpt/models")
    baseline_model = baseline_model or model_root / "smart_tga_number_object_fusion_cycle710_v1.npz"
    foundation_model = foundation_model or model_root / "smart_tga_number_object_foundation_fusion_cycle711_v1.npz"
    segment_model = segment_model or model_root / "smart_tga_number_object_segmenter_cycle710_v1.pt"
    family = np.load(model_root / "smart_tga_number_context_family_cycle704_v1.npz")
    prototypes = np.asarray(family["descriptors"], np.float32)
    prototype_labels = np.asarray(family["labels"], bool)
    pixel_models = joblib.load(model_root / "smart_tga_number_context_conformal_cycle703_v1.joblib")["pixel_ensemble"]
    old_fusion = np.load(baseline_model)
    foundation = np.load(foundation_model)
    segment_blob = torch.load(segment_model, map_location="cpu", weights_only=True)
    segment = build_tiny_unet(int(segment_blob["base_channels"]))
    segment.load_state_dict(segment_blob["state_dict"])
    segment.eval()
    transfer_teacher = _build_transfer_teacher()

    paints = []
    objects = []
    for inspection_record in _read(inspection):
        paint_label = str(inspection_record["paint_label"])
        if paint_labels is not None and paint_label not in paint_labels:
            continue
        source = Path(inspection_record["source_1024"])
        parent = source.parent
        rgb = np.asarray(Image.open(source).convert("RGB"))
        components = _read(parent / "component_records.json")
        layer_masks = {path.stem: np.asarray(Image.open(path).convert("L")) > 0 for path in (parent / "masks").glob("*.png")}
        proposals = list(component_proposal_candidates(rgb.shape[:2], layer_masks, components, min_pixels=400))
        with torch.no_grad():
            segment_probability = torch.sigmoid(segment(torch.from_numpy(image_feature_tensor(rgb)[None])))[0, 0].numpy()
        if include_probability_proposals:
            proposals.extend(probability_region_proposals(segment_probability, rgb.shape[:2]))
        prepared = []
        for proposal in proposals:
            raw = proposal["raw_support"]
            record = {"paint_label": paint_label, "proposal_id": proposal["proposal_id"],
                      "proposal_bbox": proposal["proposal_bbox"], "rgb": rgb,
                      "hypotheses": {name: raw for name in MASK_NAMES}}
            prepared.append((proposal, record, _descriptor(record)))
        paint_objects = []
        paint_views = []
        rgb_small = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_AREA)
        for proposal, record, descriptor in prepared:
            raw = proposal["raw_support"]
            provenance = proposal["provenance"]
            margin = prototype_margin(descriptor, prototypes[prototype_labels], prototypes[~prototype_labels])
            pixel_score = np.mean([_score(model, record) for model in pixel_models], axis=0)
            area = int(provenance.get("component_pixels", np.asarray(raw, bool).sum()))
            peers = []
            for other, _other_record, other_descriptor in prepared:
                if other["proposal_id"] == proposal["proposal_id"]:
                    continue
                if other["provenance"].get("source_stage") == "number_object_probability_map":
                    continue
                other_area = int(other["provenance"].get("component_pixels", np.asarray(other["raw_support"], bool).sum()))
                difference = abs(float(np.log(max(1, area) / max(1, other_area))))
                if difference <= 1.05:
                    peers.append((d4_cosine_similarity(descriptor, other_descriptor), difference))
            peer_similarity, peer_difference = max(peers, default=(0.0, 8.0), key=lambda pair: pair[0])
            peer_count = sum(similarity >= 0.82 for similarity, _difference in peers)
            intrinsic = component_feature_vector(
                rgb, proposal["proposal_bbox"], raw, family_margin=float(margin), pixel_score=pixel_score,
                peer_similarity=float(peer_similarity), peer_count=peer_count,
                peer_area_log_difference=float(peer_difference),
            )
            small_mask = project_local_support(raw, proposal["proposal_bbox"], rgb.shape[:2], 256)
            values = segment_probability[small_mask]
            count = max(1, len(values) // 4)
            segment_score = float(np.mean(np.partition(values, len(values) - count)[-count:]))
            base = np.concatenate((intrinsic, np.asarray([segment_score], np.float32)))
            item = {
                "paint_label": paint_label, "proposal_id": proposal["proposal_id"],
                "component_index": int(provenance.get("component_index", -1)),
                "source_layer": provenance.get("source_layer", "owner_neutral_map"),
                "proposal_source": provenance.get("source_stage", "assembled_component"),
                "proposal_provenance": provenance,
                "bbox": [int(value) for value in proposal["proposal_bbox"]], "base": base,
                "segment_score": segment_score, "cycle710_probability": _linear_probability(old_fusion, base),
                "foundation_threshold": float(foundation["threshold"][0]),
            }
            paint_objects.append(item)
            objects.append(item)
            paint_views.append(isolated_object_views(rgb_small, small_mask))
        # Bound peak memory to one paint.  A real DLM route can expose hundreds
        # of proposals; retaining every 16-view tensor scales into tens of GB.
        for item, embedding in zip(paint_objects, transfer_teacher(paint_views)):
            probability = _foundation_probability(foundation, item.pop("base"), embedding)
            item["foundation_probability"] = probability
            item["delta"] = probability - item["cycle710_probability"]
            item["uncertainty"] = abs(probability - item["foundation_threshold"])
        paints.append({"paint_label": paint_label, "rgb": rgb, "objects": paint_objects, "parent": parent})
        print(f"scored {paint_label}: {len(paint_objects)} owner-neutral proposals", flush=True)

    ranking = []
    for paint in paints:
        records = paint["objects"]
        entry = {
            "paint_label": paint["paint_label"],
            "proposal_count": len(records),
            "accepted_count": sum(item["foundation_probability"] >= item["foundation_threshold"] for item in records),
            "max_recovery_delta": max((item["delta"] for item in records), default=0.0),
            "max_disagreement": max((abs(item["delta"]) for item in records), default=0.0),
            "minimum_uncertainty": min((item["uncertainty"] for item in records), default=1.0),
            "objects": records,
        }
        ranking.append(entry)
        _overlay(paint["rgb"], records, output_dir / f"overlay_{paint['parent'].name}.png")
    recovery = sorted(ranking, key=lambda item: item["max_recovery_delta"], reverse=True)
    disagreement = sorted(ranking, key=lambda item: item["max_disagreement"], reverse=True)
    uncertainty = sorted(ranking, key=lambda item: item["minimum_uncertainty"])
    selected = []
    for bucket, reason in ((recovery, "recovery"), (disagreement, "disagreement"), (uncertainty, "uncertainty")):
        for item in bucket:
            if item["paint_label"] not in {entry["paint_label"] for entry in selected}:
                selected.append({"paint_label": item["paint_label"], "reason": reason})
                break
    for family in ("dirtlatemodel 350/", "dirtlatemodel 358/"):
        while sum(item["paint_label"].startswith(family) for item in selected) < 3:
            candidate = next(item for item in recovery if item["paint_label"].startswith(family) and item["paint_label"] not in {entry["paint_label"] for entry in selected})
            selected.append({"paint_label": candidate["paint_label"], "reason": "family_recovery_control"})
    payload = {
        "schema": "smart-tga-number-object-active-pool-v1", "inspection": str(inspection).replace("\\", "/"),
        "paint_count": len(ranking), "proposal_count": len(objects), "frozen_threshold": float(foundation["threshold"][0]),
        "selected_paints": selected, "ranking": ranking,
        "casts_votes": False, "ownership_authority": False,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "active_pool.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-model", type=Path)
    parser.add_argument("--foundation-model", type=Path)
    parser.add_argument("--segment-model", type=Path)
    parser.add_argument("--paint-label", action="append", dest="paint_labels")
    parser.add_argument("--include-probability-proposals", action="store_true")
    args = parser.parse_args()
    payload = run(
        args.inspection, args.output_dir, args.baseline_model,
        args.foundation_model, args.segment_model,
        set(args.paint_labels) if args.paint_labels else None,
        args.include_probability_proposals,
    )
    print(json.dumps({"paint_count": payload["paint_count"], "proposal_count": payload["proposal_count"],
                      "frozen_threshold": payload["frozen_threshold"], "selected_paints": payload["selected_paints"]}, indent=2))


if __name__ == "__main__":
    main()
