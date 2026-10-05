"""Score Smart TGA local-copy telemetry with a frozen purity model.

This is an active-learning probe only.  It cannot alter masks, cast votes, or
apply ownership; it ranks reviewed candidates and paints for human inspection.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from smart_tga_local_purity_train import FEATURE_NAMES, _feature_row


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0))))


def main() -> None:
    args = _arguments()
    runtime = json.loads(Path(args.runtime).read_text(encoding="utf-8"))
    model = np.load(args.model, allow_pickle=False)
    selected_names = [str(name) for name in model["feature_names"].tolist()]
    indices = [FEATURE_NAMES.index(name) for name in selected_names]
    mean = np.asarray(model["mean"], np.float64)
    scale = np.asarray(model["scale"], np.float64)
    coefficient = np.asarray(model["coefficient"], np.float64)
    intercept = float(np.asarray(model["intercept"]).reshape(-1)[0])
    threshold = float(np.asarray(model["threshold"]).reshape(-1)[0])
    records = []
    for paint in runtime["records"]:
        paint_rows = []
        for row in paint["local_candidates"]:
            full = np.asarray(_feature_row(row), np.float64)
            selected = full[indices]
            probability = _sigmoid(
                float(np.dot((selected - mean) / scale, coefficient) + intercept)
            )
            current = bool(row["accepted"])
            conflict = float(
                (row.get("intrinsic_purity_features") or {}).get(
                    "proposal_smaller_peer_containment", 0.0,
                )
            )
            ocr_tokens = list(row.get("local_ocr_tokens") or ())
            short_alpha = max((
                float(token.get("confidence", 0.0))
                for token in ocr_tokens
                if 0 < int(token.get("alpha_characters", 0)) <= 3
            ), default=0.0)
            mixed_panel_risk = current and (
                conflict >= 0.15 or (len(ocr_tokens) >= 3 and short_alpha >= 0.5)
            )
            paint_rows.append({
                "family_id": row["family_id"],
                "bbox": row["bbox"],
                "current_accepted": current,
                "purity_probability": round(probability, 6),
                "purity_threshold": round(threshold, 6),
                "purity_accepted": bool(probability >= threshold),
                "final_shadow_accepted": bool(current and probability >= threshold),
                "uncertainty": round(abs(probability - threshold), 6),
                "mixed_panel_risk": mixed_panel_risk,
                "proposal_smaller_peer_containment": round(conflict, 6),
                "local_ocr_token_count": len(ocr_tokens),
                "local_ocr_short_alpha_confidence": round(short_alpha, 6),
            })
        records.append({
            "paint_label": paint["paint_label"],
            "candidate_count": len(paint_rows),
            "current_accepted_count": sum(r["current_accepted"] for r in paint_rows),
            "final_shadow_accepted_count": sum(
                r["final_shadow_accepted"] for r in paint_rows
            ),
            "mixed_panel_risk_count": sum(r["mixed_panel_risk"] for r in paint_rows),
            "minimum_accepted_uncertainty": min((
                r["uncertainty"] for r in paint_rows if r["current_accepted"]
            ), default=None),
            "candidates": paint_rows,
        })
    result = {
        "schema": "smart-tga-local-purity-active-learning-v1",
        "model": str(Path(args.model)),
        "feature_names": selected_names,
        "threshold": threshold,
        "casts_votes": False,
        "ownership_authority": False,
        "output_applied": False,
        "records": records,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "paint_count": len(records),
        "candidate_count": sum(r["candidate_count"] for r in records),
        "current_accepted_count": sum(r["current_accepted_count"] for r in records),
        "final_shadow_accepted_count": sum(
            r["final_shadow_accepted_count"] for r in records
        ),
        "mixed_panel_risk_count": sum(r["mixed_panel_risk_count"] for r in records),
    }, indent=2))


if __name__ == "__main__":
    main()
