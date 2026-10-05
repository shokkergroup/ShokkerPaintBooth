"""Score immutable Smart TGA candidate embeddings with a frozen prototype bank.

This is evaluator-only shadow evidence.  It never changes masks or supplies
ownership votes; it only annotates the candidates already emitted by the
owner-neutral proposal path.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    from smart_tga_visual_prototype_train import prototype_features
except ModuleNotFoundError:
    from scripts.smart_tga_visual_prototype_train import prototype_features


def _scalar(model: Any, name: str) -> Any:
    value = np.asarray(model[name]).reshape(-1)
    if not len(value):
        raise ValueError(f"empty model field: {name}")
    return value[0].item()


def score(runtime: dict[str, Any], model_path: Path) -> dict[str, Any]:
    with np.load(model_path, allow_pickle=False) as model:
        schema = str(_scalar(model, "schema"))
        if schema != "smart-tga-visual-prototype-bank-v1":
            raise ValueError(f"unsupported model schema: {schema}")
        bank = np.asarray(model["embedding"], np.float64)
        bank_number = np.asarray(model["is_number"], bool)
        bank_sponsor = np.asarray(model["is_sponsor"], bool)
        metric = str(_scalar(model, "metric"))
        threshold = float(_scalar(model, "threshold"))

    records = []
    for paint in runtime["records"]:
        candidates = paint.get("local_candidates") or ()
        if not candidates:
            records.append({
                "paint_label": paint["paint_label"],
                "candidate_count": 0,
                "current_accepted_count": 0,
                "prototype_accepted_count": 0,
                "final_shadow_accepted_count": 0,
                "candidates": [],
            })
            continue
        query = np.asarray([row.get("visual_embedding") for row in candidates], np.float64)
        if query.ndim != 2 or query.shape[1] != bank.shape[1] or not np.isfinite(query).all():
            raise ValueError(f"invalid visual embeddings: {paint['paint_label']}")
        query /= np.maximum(np.linalg.norm(query, axis=1, keepdims=True), 1e-12)
        features = prototype_features(bank, bank_number, bank_sponsor, query)
        scored = []
        for index, row in enumerate(candidates):
            visual_score = float(features[metric][index])
            prototype_accepted = visual_score >= threshold
            current_accepted = bool(row["accepted"])
            scored.append({
                "family_id": row["family_id"],
                "bbox": row["bbox"],
                "current_accepted": current_accepted,
                "prototype_accepted": prototype_accepted,
                "final_shadow_accepted": current_accepted and prototype_accepted,
                "visual_score": round(visual_score, 7),
                "visual_margin_to_threshold": round(visual_score - threshold, 7),
                "nearest_number_similarity": round(float(features["nearest_number_similarity"][index]), 7),
                "nearest_nonnumber_similarity": round(float(features["nearest_nonnumber_similarity"][index]), 7),
                "nearest_sponsor_similarity": round(float(features["nearest_sponsor_similarity"][index]), 7),
            })
        records.append({
            "paint_label": paint["paint_label"],
            "candidate_count": len(scored),
            "current_accepted_count": sum(item["current_accepted"] for item in scored),
            "prototype_accepted_count": sum(item["prototype_accepted"] for item in scored),
            "final_shadow_accepted_count": sum(item["final_shadow_accepted"] for item in scored),
            "candidates": scored,
        })

    return {
        "schema": "smart-tga-visual-prototype-shadow-score-v1",
        "model_path": str(model_path),
        "metric": metric,
        "threshold": threshold,
        "paint_count": len(records),
        "candidate_count": sum(item["candidate_count"] for item in records),
        "current_accepted_count": sum(item["current_accepted_count"] for item in records),
        "prototype_accepted_count": sum(item["prototype_accepted_count"] for item in records),
        "final_shadow_accepted_count": sum(item["final_shadow_accepted_count"] for item in records),
        "casts_votes": False,
        "ownership_authority": False,
        "output_applied": False,
        "records": records,
    }


def evaluate_reviewed(
    result: dict[str, Any], label_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    labels = {}
    visible_copies = 0
    for payload in label_payloads:
        visible_copies += int((payload.get("source_totals") or {}).get("visible_number_copies", 0))
        for item in payload["candidate_labels"]:
            key = (str(item["paint"]), str(item["family_id"]))
            if key in labels:
                raise ValueError(f"duplicate reviewed label: {key}")
            labels[key] = item
    rows = []
    for paint in result["records"]:
        for candidate in paint["candidates"]:
            key = (paint["paint_label"], candidate["family_id"])
            if key not in labels:
                raise ValueError(f"missing reviewed label: {key}")
            rows.append((candidate, labels.pop(key)))
    if labels:
        raise ValueError(f"{len(labels)} reviewed labels absent from scored runtime")

    number_total = sum(item[1]["semantic"] == "Number" for item in rows)
    complete_total = sum(
        item[1]["semantic"] == "Number" and bool(item[1].get("complete_copy"))
        for item in rows
    )

    def gate(name: str) -> dict[str, Any]:
        accepted = [item for item in rows if bool(item[0][name])]
        accepted_number = sum(item[1]["semantic"] == "Number" for item in accepted)
        accepted_complete = sum(
            item[1]["semantic"] == "Number" and bool(item[1].get("complete_copy"))
            for item in accepted
        )
        return {
            "accepted": len(accepted),
            "accepted_number": accepted_number,
            "accepted_negative_or_uncertain": len(accepted) - accepted_number,
            "precision": accepted_number / max(1, len(accepted)),
            "number_candidate_recall": accepted_number / max(1, number_total),
            "complete_candidate_recall": accepted_complete / max(1, complete_total),
            "visible_number_copy_recall": accepted_complete / max(1, visible_copies),
        }

    return {
        "reviewed_candidate_count": len(rows),
        "reviewed_number_candidates": number_total,
        "reviewed_complete_number_candidates": complete_total,
        "visible_number_copies": visible_copies,
        "current_gate": gate("current_accepted"),
        "prototype_only": gate("prototype_accepted"),
        "final_intersection_shadow": gate("final_shadow_accepted"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--labels", type=Path, action="append", default=[])
    args = parser.parse_args()
    runtime = json.loads(args.runtime.read_text(encoding="utf-8"))
    result = score(runtime, args.model)
    if args.labels:
        result["reviewed_metrics"] = evaluate_reviewed(
            result,
            [json.loads(path.read_text(encoding="utf-8")) for path in args.labels],
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "paint_count": result["paint_count"],
        "candidate_count": result["candidate_count"],
        "current_accepted_count": result["current_accepted_count"],
        "final_shadow_accepted_count": result["final_shadow_accepted_count"],
        "casts_votes": result["casts_votes"],
    }, indent=2))


if __name__ == "__main__":
    main()
