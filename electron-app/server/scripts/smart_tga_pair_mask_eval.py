"""Score Smart TGA Number masks against conservatively audited car/car_num deltas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def _mask(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")) > 127


def _key(path: str) -> str:
    return str(Path(path).resolve()).lower()


def score_masks(predicted: np.ndarray, expected: np.ndarray) -> dict[str, float | int]:
    if predicted.shape != expected.shape:
        expected = np.asarray(
            Image.fromarray(expected.astype(np.uint8) * 255).resize(
                (predicted.shape[1], predicted.shape[0]), Image.Resampling.NEAREST
            )
        ) > 127
    tp = int(np.count_nonzero(predicted & expected))
    fp = int(np.count_nonzero(predicted & ~expected))
    fn = int(np.count_nonzero(~predicted & expected))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    iou = tp / max(1, tp + fp + fn)
    return {
        "true_positive_pixels": tp,
        "false_positive_pixels": fp,
        "false_negative_pixels": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "iou": round(iou, 6),
    }


def evaluate(pair_manifest: Path, inspection_files: list[Path]) -> dict:
    expected_records = json.loads(pair_manifest.read_text(encoding="utf-8"))
    expected_by_paint = {_key(record["car_num"]): record for record in expected_records}
    route_by_paint: dict[str, dict] = {}
    for inspection_file in inspection_files:
        for record in json.loads(inspection_file.read_text(encoding="utf-8")):
            if record.get("success"):
                route_by_paint[_key(record["paint"])] = record
    records: list[dict] = []
    for paint_key, expected_record in expected_by_paint.items():
        route = route_by_paint.get(paint_key)
        if route is None:
            continue
        metrics = score_masks(
            _mask(Path(route["mask_paths"]["numbers"])),
            _mask(Path(expected_record["expected_numbers_mask"])),
        )
        records.append({
            "paint_label": route["paint_label"],
            "paint": route["paint"],
            **metrics,
        })
    tp = sum(record["true_positive_pixels"] for record in records)
    fp = sum(record["false_positive_pixels"] for record in records)
    fn = sum(record["false_negative_pixels"] for record in records)
    aggregate = score_masks(
        np.concatenate((np.ones(tp, bool), np.ones(fp, bool), np.zeros(fn, bool))),
        np.concatenate((np.ones(tp, bool), np.zeros(fp, bool), np.ones(fn, bool))),
    ) if records else score_masks(np.zeros(1, bool), np.zeros(1, bool))
    return {
        "schema": "spb-smart-tga-paired-number-mask-eval-v1",
        "evaluated": len(records),
        "aggregate": aggregate,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-manifest", type=Path, required=True)
    parser.add_argument("--inspection", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.pair_manifest, args.inspection)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
