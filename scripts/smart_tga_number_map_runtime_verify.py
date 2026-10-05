"""Verify live number-map shadow inference against frozen offline evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_map_family_shadow import number_map_family_shadow_telemetry
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_map_family_shadow import number_map_family_shadow_telemetry  # type: ignore


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(mask: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(mask).tobytes()).hexdigest()


VERIFIED_MISSES = {
    "dirtlatemodel 350/car_num_302246.tga": [271, 916, 43, 27],
    "dirtlatemodel 358/car_num_1283575.tga": [795, 825, 170, 123],
    "dirtlatemodel 358/car_num_1288062.tga": [268, 932, 41, 10],
    "dirtlatemodel 358/car_num_1292637.tga": [271, 916, 43, 27],
}


def _match_bbox(candidate, truth):
    ax, ay, aw, ah = map(int, candidate)
    bx, by, bw, bh = map(int, truth)
    intersection = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by),
    )
    truth_area = max(1, bw * bh)
    candidate_area = max(1, aw * ah)
    coverage = intersection / truth_area
    area_ratio = candidate_area / truth_area
    return coverage >= 0.55 and area_ratio <= 6.0, coverage, area_ratio


def run(inspection_path: Path, expected_path: Path, output: Path):
    inspection = _read(inspection_path)
    expected = _read(expected_path)
    expected_by_paint = {}
    for item in expected["scores"]:
        expected_by_paint.setdefault(item["paint_label"], {})[item["family_id"]] = item
    rows = []
    for record in inspection:
        paint_label = record["paint_label"]
        source = Path(record["source_1024"])
        rgb = np.asarray(Image.open(source).convert("RGB"))
        masks = {
            path.stem: np.asarray(Image.open(path).convert("L"))
            for path in (source.parent / "masks").glob("*.png")
        }
        before = {name: _digest(mask) for name, mask in masks.items()}
        ocr = (record.get("route_adjudicator_shadow") or {}).get("ocr_region_samples") or ()
        telemetry = number_map_family_shadow_telemetry(rgb, masks, ocr_regions=ocr)
        after = {name: _digest(mask) for name, mask in masks.items()}
        actual_items = telemetry["accepted_families"] + telemetry["nearest_rejected"]
        actual = {
            item["family_id"]: item for item in actual_items
            if item.get("proposal_branch", "global_probability_map") == "global_probability_map"
        }
        local = [
            item for item in actual_items
            if item.get("proposal_branch") == "local_palette_panel"
        ]
        wanted = expected_by_paint[paint_label]
        probability_delta = max(
            (abs(float(actual[key]["probability"]) - float(wanted[key]["probability"])) for key in wanted),
            default=0.0,
        )
        acceptance_mismatches = sum(
            bool(actual[key]["accepted"]) != bool(wanted[key]["accepted"])
            for key in wanted
        )
        family_ids_match = set(actual) == set(wanted)
        masks_unchanged = before == after
        truth = VERIFIED_MISSES.get(paint_label)
        for item in local:
            matched, coverage, area_ratio = (
                _match_bbox(item["bbox"], truth) if truth is not None else (False, 0.0, 0.0)
            )
            item["verified_missing_copy_match"] = bool(matched)
            item["verified_missing_copy_coverage"] = round(float(coverage), 6)
            item["verified_missing_copy_area_ratio"] = round(float(area_ratio), 6)
        rows.append({
            "paint_label": paint_label,
            "family_count": telemetry["family_count"],
            "accepted_family_count": telemetry["accepted_family_count"],
            "family_ids_match": family_ids_match,
            "max_probability_delta": probability_delta,
            "acceptance_mismatches": acceptance_mismatches,
            "masks_byte_identical": masks_unchanged,
            "local_proposal_count": telemetry.get("local_proposal_count", 0),
            "local_family_count": telemetry.get("local_family_count", 0),
            "local_accepted_family_count": telemetry.get("local_accepted_family_count", 0),
            "local_rows": local,
            "elapsed_ms": telemetry["elapsed_ms"],
        })
        if not family_ids_match or probability_delta > 1e-6 or acceptance_mismatches or not masks_unchanged:
            raise AssertionError(f"runtime/offline drift for {paint_label}: {rows[-1]}")
    recovered_misses = {
        item["paint_label"] for item in rows
        if any(row["verified_missing_copy_match"] for row in item["local_rows"])
    }
    accepted_recovered_misses = {
        item["paint_label"] for item in rows
        if any(
            row["accepted"] and row["verified_missing_copy_match"]
            for row in item["local_rows"]
        )
    }
    local_hard_negative_accepts = sum(
        row["accepted"] and not row["verified_missing_copy_match"]
        for item in rows for row in item["local_rows"]
    )
    payload = {
        "schema": "smart-tga-number-map-family-runtime-verification-v1",
        "paint_count": len(rows),
        "family_count": sum(item["family_count"] for item in rows),
        "accepted_family_count": sum(item["accepted_family_count"] for item in rows),
        "local_proposal_count": sum(item["local_proposal_count"] for item in rows),
        "local_family_count": sum(item["local_family_count"] for item in rows),
        "local_accepted_family_count": sum(item["local_accepted_family_count"] for item in rows),
        "verified_misses_recovered": len(recovered_misses),
        "verified_misses_accepted": len(accepted_recovered_misses),
        "local_hard_negative_accepts": int(local_hard_negative_accepts),
        "proposal_recall_before": 15 / 19,
        "proposal_recall_after": (15 + len(recovered_misses)) / 19,
        "source_copy_recall_before": 12 / 19,
        "source_copy_recall_after": (12 + len(accepted_recovered_misses)) / 19,
        "family_id_parity": all(item["family_ids_match"] for item in rows),
        "max_probability_delta": max((item["max_probability_delta"] for item in rows), default=0.0),
        "acceptance_mismatches": sum(item["acceptance_mismatches"] for item in rows),
        "all_masks_byte_identical": all(item["masks_byte_identical"] for item in rows),
        "casts_votes": False,
        "ownership_authority": False,
        "output_applied": False,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inspection, args.expected, args.output)
    print(json.dumps({
        "paint_count": result["paint_count"],
        "family_count": result["family_count"],
        "accepted_family_count": result["accepted_family_count"],
        "local_family_count": result["local_family_count"],
        "verified_misses_recovered": result["verified_misses_recovered"],
        "verified_misses_accepted": result["verified_misses_accepted"],
        "local_hard_negative_accepts": result["local_hard_negative_accepts"],
        "source_copy_recall_after": result["source_copy_recall_after"],
        "max_probability_delta": result["max_probability_delta"],
        "all_masks_byte_identical": result["all_masks_byte_identical"],
    }, indent=2))


if __name__ == "__main__":
    main()
