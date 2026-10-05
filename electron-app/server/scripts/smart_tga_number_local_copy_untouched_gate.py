"""Run the frozen local-copy shadow on untouched paints and build review sheets.

This evaluator never supplies labels, filenames, car identities, or bounding
boxes to inference.  It records every local candidate for later human review,
verifies that input masks remain byte-identical, and keeps all output authority
disabled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

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


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


def _fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    result = Image.new("RGB", size, (28, 30, 35))
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    result.paste(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return result


def _review_sheet(source: Image.Image, candidates: list[dict], output: Path) -> None:
    card_width, card_height = 380, 260
    columns = 3
    rows = max(1, math.ceil(len(candidates) / columns))
    sheet = Image.new("RGB", (columns * card_width, rows * card_height), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)
    for index, candidate in enumerate(candidates):
        x, y, width, height = map(int, candidate["bbox"])
        padding = max(12, int(round(max(width, height) * 0.35)))
        x0, y0 = max(0, x - padding), max(0, y - padding)
        x1 = min(source.width, x + width + padding)
        y1 = min(source.height, y + height + padding)
        context = source.crop((x0, y0, x1, y1))
        context_draw = ImageDraw.Draw(context)
        color = (50, 230, 120) if candidate["accepted"] else (255, 190, 45)
        context_draw.rectangle((x - x0, y - y0, x + width - x0, y + height - y0), outline=color, width=3)
        card = _fit(context, (card_width - 12, card_height - 66))
        left = (index % columns) * card_width + 6
        top = (index // columns) * card_height + 60
        sheet.paste(card, (left, top))
        label = (
            f"#{index:02d} {'ACCEPT' if candidate['accepted'] else 'reject'} "
            f"p={candidate['probability']:.3f} margin={candidate['clip_digit_minus_all_negative_margin']:.3f}\n"
            f"bbox={x},{y},{width},{height}  panel={candidate['template_number_evidence']:.3f}"
        )
        draw.multiline_text((left, (index // columns) * card_height + 8), label, fill=(235, 238, 244), spacing=4)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def run(
    inspection_paths: list[Path], output: Path, *,
    include_visual_embeddings: bool = False,
    paint_labels: tuple[str, ...] = (),
) -> dict:
    inspection = [record for path in inspection_paths for record in _read(path)]
    if paint_labels:
        selected = set(paint_labels)
        inspection = [record for record in inspection if record["paint_label"] in selected]
        missing = sorted(selected - {record["paint_label"] for record in inspection})
        if missing:
            raise ValueError(f"requested paint labels absent from inspections: {missing}")
    labels = [record["paint_label"] for record in inspection]
    if len(labels) != len(set(labels)):
        raise ValueError("inspection inputs contain duplicate paint labels")
    records = []
    for record in inspection:
        source_path = Path(record["source_1024"])
        source = Image.open(source_path).convert("RGB")
        rgb = np.asarray(source)
        masks = {
            path.stem: np.asarray(Image.open(path).convert("L"))
            for path in (source_path.parent / "masks").glob("*.png")
        }
        before = {name: _digest(mask) for name, mask in masks.items()}
        ocr = (record.get("route_adjudicator_shadow") or {}).get("ocr_region_samples") or ()
        telemetry = number_map_family_shadow_telemetry(
            rgb, masks, ocr_regions=ocr,
            include_visual_embeddings=include_visual_embeddings,
        )
        after = {name: _digest(mask) for name, mask in masks.items()}
        if before != after:
            raise AssertionError(f"shadow mutated masks for {record['paint_label']}")
        candidates = list(telemetry.get("local_families") or ())
        sample = _safe_name(record["paint_label"])
        sheet = output.parent / sample / "local_candidate_review.png"
        _review_sheet(source, candidates, sheet)
        records.append({
            "paint_label": record["paint_label"],
            "source_1024": str(source_path),
            "review_sheet": str(sheet.resolve()),
            "global_family_count": int(telemetry["family_count"]),
            "local_family_count": len(candidates),
            "local_accepted_family_count": sum(bool(item["accepted"]) for item in candidates),
            "local_candidates": candidates,
            "masks_byte_identical": True,
            "elapsed_ms": float(telemetry["elapsed_ms"]),
        })
    payload = {
        "schema": "smart-tga-number-local-copy-untouched-gate-v1",
        "paint_count": len(records),
        "local_family_count": sum(item["local_family_count"] for item in records),
        "local_accepted_family_count": sum(item["local_accepted_family_count"] for item in records),
        "all_masks_byte_identical": all(item["masks_byte_identical"] for item in records),
        "casts_votes": False,
        "ownership_authority": False,
        "output_applied": False,
        "records": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-visual-embeddings", action="store_true")
    parser.add_argument("--paint-label", action="append", default=[])
    args = parser.parse_args()
    result = run(
        args.inspection, args.output,
        include_visual_embeddings=args.include_visual_embeddings,
        paint_labels=tuple(args.paint_label),
    )
    print(json.dumps({
        "paint_count": result["paint_count"],
        "local_family_count": result["local_family_count"],
        "local_accepted_family_count": result["local_accepted_family_count"],
        "all_masks_byte_identical": result["all_masks_byte_identical"],
    }, indent=2))


if __name__ == "__main__":
    main()
