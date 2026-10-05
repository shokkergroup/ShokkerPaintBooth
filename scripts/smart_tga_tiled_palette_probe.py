"""Probe probability-independent tiled palette proposals on real Smart TGAs."""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_tiled_palette_proposals import (
        assemble_adjacent_tiled_palette_companions,
        multiscale_tiled_palette_proposals,
        position_ranked_tiled_shortlist,
        repeated_tiled_palette_shortlist,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_tiled_palette_proposals import (  # type: ignore
        assemble_adjacent_tiled_palette_companions,
        multiscale_tiled_palette_proposals,
        position_ranked_tiled_shortlist,
        repeated_tiled_palette_shortlist,
    )


def _safe(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


def _cards(image: Image.Image, rows: list[dict], output: Path, page_size: int = 24) -> list[str]:
    paths = []
    width, height, columns = 300, 220, 4
    for page, start in enumerate(range(0, len(rows), page_size)):
        subset = rows[start:start + page_size]
        canvas = Image.new("RGB", (columns * width, math.ceil(len(subset) / columns) * height), (18, 20, 24))
        draw = ImageDraw.Draw(canvas)
        for offset, row in enumerate(subset):
            x, y, w, h = row["bbox"]
            pad = max(10, int(round(max(w, h) * 0.25)))
            crop = image.crop((max(0, x - pad), max(0, y - pad), min(image.width, x + w + pad), min(image.height, y + h + pad)))
            crop_draw = ImageDraw.Draw(crop)
            crop_draw.rectangle((x - max(0, x - pad), y - max(0, y - pad), x + w - max(0, x - pad), y + h - max(0, y - pad)), outline=(80, 230, 130), width=3)
            crop.thumbnail((width - 12, height - 56), Image.Resampling.LANCZOS)
            left, top = (offset % columns) * width + 6, (offset // columns) * height + 50
            canvas.paste(crop, (left + (width - 12 - crop.width) // 2, top))
            draw.text((left, (offset // columns) * height + 6), f"#{start+offset:03d} peer={row['peer_d4_similarity']:.3f}\n{row['bbox']} {row['palette_role']}", fill=(235, 238, 244))
        path = output / f"candidates_{page:02d}.png"
        canvas.save(path)
        paths.append(str(path.resolve()))
    return paths


def _mask_cards(
    image: Image.Image, proposals: list[dict], rows: list[dict], output: Path,
    page_size: int = 24,
) -> list[str]:
    """Render only proposed pixels; nearby sponsors cannot hide in a bbox crop."""
    paths = []
    rgb = np.asarray(image)
    width, height, columns = 300, 220, 4
    for page, start in enumerate(range(0, len(rows), page_size)):
        subset = rows[start:start + page_size]
        canvas = Image.new(
            "RGB", (columns * width, math.ceil(len(subset) / columns) * height),
            (18, 20, 24),
        )
        draw = ImageDraw.Draw(canvas)
        for offset, (row, proposal) in enumerate(zip(
            subset, proposals[start:start + page_size], strict=True,
        )):
            x, y, w, h = row["bbox"]
            support = np.asarray(proposal["raw_support"], dtype=bool)
            crop = rgb[y:y + h, x:x + w].copy()
            crop[~support] = 0
            masked = Image.fromarray(crop)
            masked.thumbnail((width - 12, height - 56), Image.Resampling.NEAREST)
            left, top = (offset % columns) * width + 6, (offset // columns) * height + 50
            canvas.paste(masked, (left + (width - 12 - masked.width) // 2, top))
            draw.text(
                (left, (offset // columns) * height + 6),
                f"#{start+offset:03d} components={row['component_count']}\n{row['bbox']} {row['palette_role']}",
                fill=(235, 238, 244),
            )
        path = output / f"masks_{page:02d}.png"
        canvas.save(path)
        paths.append(str(path.resolve()))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum", type=int, default=96)
    parser.add_argument("--paint-label", action="append", default=[])
    parser.add_argument(
        "--panel-map", type=Path,
        default=Path("engine/spec_sculpt/models/smart_tga_dlm_panel_map_cycle660_v1.json"),
    )
    args = parser.parse_args()
    runtime_records = []
    for runtime_path in args.runtime:
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime_records.extend(payload["records"])
    selected = set(args.paint_label)
    panel_map = json.loads(args.panel_map.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    seen_paints = set()
    for paint in runtime_records:
        if selected and paint["paint_label"] not in selected:
            continue
        if paint["paint_label"] in seen_paints:
            continue
        seen_paints.add(paint["paint_label"])
        started = time.perf_counter()
        source = Image.open(paint["source_1024"]).convert("RGB")
        image = np.asarray(source)
        raw = multiscale_tiled_palette_proposals(image)
        repeated = repeated_tiled_palette_shortlist(
            image, raw, maximum=max(args.maximum * 4, 192),
        )
        companions = assemble_adjacent_tiled_palette_companions(repeated)
        shortlist = position_ranked_tiled_shortlist(
            (*repeated, *companions), image.shape[:2], panel_map, maximum=args.maximum,
        )
        rows = [{
            "proposal_id": item["proposal_id"],
            "bbox": list(map(int, item["proposal_bbox"])),
            "palette_role": item["provenance"]["palette_role"],
            "component_count": int(item["provenance"]["component_count"]),
            "tile_origin_count": int(item["provenance"]["tile_origin_count"]),
            "peer_d4_similarity": round(float(item["provenance"]["peer_d4_similarity"]), 7),
            "peer_count_at_0_82": int(item["provenance"]["peer_count_at_0_82"]),
            "template_number_fraction": round(float(item["provenance"]["template_number_fraction"]), 7),
            "template_sponsor_fraction": round(float(item["provenance"]["template_sponsor_fraction"]), 7),
            "position_rank_score": round(float(item["provenance"]["position_rank_score"]), 7),
            "owner_neutral": True,
            "ownership_authority": False,
        } for item in shortlist]
        paint_dir = args.output / _safe(paint["paint_label"])
        paint_dir.mkdir(parents=True, exist_ok=True)
        sheets = _cards(source, rows, paint_dir)
        mask_sheets = _mask_cards(source, list(shortlist), rows, paint_dir)
        records.append({
            "paint_label": paint["paint_label"],
            "source_1024": paint["source_1024"],
            "raw_proposal_count": len(raw),
            "companion_proposal_count": len(companions),
            "shortlist_count": len(rows),
            "review_sheets": sheets,
            "mask_review_sheets": mask_sheets,
            "candidates": rows,
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        })
        (args.output / "probe.json").write_text(json.dumps({"records": records}, indent=2) + "\n", encoding="utf-8")
    payload = {
        "schema": "smart-tga-tiled-palette-probe-v1",
        "paint_count": len(records),
        "raw_proposal_count": sum(item["raw_proposal_count"] for item in records),
        "shortlist_count": sum(item["shortlist_count"] for item in records),
        "casts_votes": False,
        "ownership_authority": False,
        "output_applied": False,
        "records": records,
    }
    (args.output / "probe.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("paint_count", "raw_proposal_count", "shortlist_count", "casts_votes")}, indent=2))


if __name__ == "__main__":
    main()
