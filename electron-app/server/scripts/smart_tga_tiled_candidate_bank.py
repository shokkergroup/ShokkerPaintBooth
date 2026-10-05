"""Persist exact immutable tiled candidates and a bounded direct-review queue."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.number_tiled_palette_proposals import (
        assemble_adjacent_tiled_palette_companions,
        corroborate_tiled_number_families,
        multiscale_tiled_palette_proposals,
        position_ranked_tiled_shortlist,
        repeated_tiled_palette_shortlist,
    )
    from scripts.smart_tga_tiled_semantic_train import (
        DEFAULT_REVIEWS,
        _intersection,
        load_probe_sources,
        load_review_references,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_tiled_palette_proposals import (  # type: ignore
        assemble_adjacent_tiled_palette_companions,
        corroborate_tiled_number_families,
        multiscale_tiled_palette_proposals,
        position_ranked_tiled_shortlist,
        repeated_tiled_palette_shortlist,
    )
    from scripts.smart_tga_tiled_semantic_train import (  # type: ignore
        DEFAULT_REVIEWS,
        _intersection,
        load_probe_sources,
        load_review_references,
    )


def _safe(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


def _build(image, panel_map, maximum):
    raw = multiscale_tiled_palette_proposals(image)
    repeated = repeated_tiled_palette_shortlist(image, raw, maximum=max(maximum * 4, 192))
    companions = assemble_adjacent_tiled_palette_companions(repeated)
    shortlist = position_ranked_tiled_shortlist(
        (*repeated, *companions), image.shape[:2], panel_map, maximum=maximum,
    )
    shortlist = corroborate_tiled_number_families(image, shortlist, panel_map)
    return shortlist, len(raw), len(companions)


def _store_exact_candidates(output, paint, candidates):
    packed_parts, offsets, lengths, shapes, bboxes, ids = [], [], [], [], [], []
    cursor = 0
    for candidate in candidates:
        support = np.asarray(candidate["raw_support"], dtype=bool)
        packed = np.packbits(support.reshape(-1))
        packed_parts.append(packed)
        offsets.append(cursor)
        lengths.append(len(packed))
        shapes.append(support.shape)
        bboxes.append(candidate["proposal_bbox"])
        ids.append(candidate["proposal_id"])
        cursor += len(packed)
    path = output / f"{_safe(paint)}_exact_candidates.npz"
    np.savez_compressed(
        path,
        packed=np.concatenate(packed_parts) if packed_parts else np.zeros(0, np.uint8),
        offsets=np.asarray(offsets, np.int64),
        lengths=np.asarray(lengths, np.int64),
        shapes=np.asarray(shapes, np.int32),
        bboxes=np.asarray(bboxes, np.int32),
        proposal_ids=np.asarray(ids),
    )
    return str(path.resolve())


def _queue_candidates(paint, candidates, references):
    queue = {}
    for kind in ("positive", "negative"):
        for reference_index, reference in enumerate(references[kind]):
            ref = reference["bbox"]
            ref_area = max(1, ref[2] * ref[3])
            scored = []
            for candidate_index, candidate in enumerate(candidates):
                bbox = candidate["proposal_bbox"]
                area = max(1, bbox[2] * bbox[3])
                overlap = _intersection(bbox, ref)
                coverage, purity = overlap / ref_area, overlap / area
                iou = overlap / max(1, area + ref_area - overlap)
                score = (
                    0.65 * coverage + 0.35 * purity
                    if kind == "positive" else max(purity, iou)
                )
                if score > 0.25:
                    scored.append((score, coverage, purity, candidate_index, candidate))
            limit = 2 if kind == "positive" else 1
            for score, coverage, purity, candidate_index, candidate in sorted(
                scored, reverse=True, key=lambda item: (item[0], item[1], item[2]),
            )[:limit]:
                key = candidate["proposal_id"]
                suggestion = "Number" if kind == "positive" else reference["semantic"]
                row = queue.setdefault(key, {
                    "paint": paint,
                    "candidate_index": candidate_index,
                    "proposal_id": key,
                    "bbox": list(map(int, candidate["proposal_bbox"])),
                    "suggested_semantics": [],
                    "selection_evidence": [],
                    "direct_semantic": None,
                    "review_status": "pending_visual_review",
                })
                if suggestion not in row["suggested_semantics"]:
                    row["suggested_semantics"].append(suggestion)
                row["selection_evidence"].append({
                    "review_source": reference["source"],
                    "reference_index": reference_index,
                    "reference_bbox": ref,
                    "selection_score": round(float(score), 6),
                    "reference_coverage": round(float(coverage), 6),
                    "candidate_purity": round(float(purity), 6),
                    "selection_only_no_runtime_authority": True,
                })
    return list(queue.values())


def _render_review_pages(image_by_paint, candidates_by_paint, queue, output, page_size=24):
    width, height, columns = 300, 220, 4
    pages = []
    for page_index, start in enumerate(range(0, len(queue), page_size)):
        subset = queue[start:start + page_size]
        canvas = Image.new(
            "RGB", (width * columns, height * math.ceil(len(subset) / columns)),
            (18, 20, 24),
        )
        draw = ImageDraw.Draw(canvas)
        for offset, row in enumerate(subset):
            image = image_by_paint[row["paint"]]
            rgb = np.asarray(image)
            candidate = candidates_by_paint[row["paint"]][row["candidate_index"]]
            x, y, box_w, box_h = map(int, candidate["proposal_bbox"])
            support = np.asarray(candidate["raw_support"], dtype=bool)
            crop = rgb[y:y + box_h, x:x + box_w].copy()
            crop[~support] = 0
            masked = Image.fromarray(crop)
            masked.thumbnail((width - 12, height - 67), Image.Resampling.NEAREST)
            left = (offset % columns) * width + 6
            top = (offset // columns) * height
            canvas.paste(masked, (
                left + (width - 12 - masked.width) // 2,
                top + 61 + (height - 67 - masked.height) // 2,
            ))
            code = f"Q{start + offset:03d}"
            row["review_code"] = code
            short_paint = row["paint"].replace("dirtlatemodel ", "DLM")
            draw.text(
                (left, top + 5),
                f"{code} {short_paint}\nidx={row['candidate_index']} {row['bbox']}\nsuggest={'+'.join(row['suggested_semantics'])}",
                fill=(236, 239, 245),
            )
        path = output / f"direct_review_{page_index:02d}.png"
        canvas.save(path)
        pages.append(str(path.resolve()))
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review", type=Path, action="append", default=[])
    parser.add_argument("--maximum", type=int, default=96)
    parser.add_argument("--cycle", type=int, default=723)
    parser.add_argument(
        "--paint", action="append", default=[],
        help="Optional exact paint label; repeat to build a bounded subset.",
    )
    parser.add_argument(
        "--panel-map", type=Path,
        default=Path("engine/spec_sculpt/models/smart_tga_dlm_panel_map_cycle660_v1.json"),
    )
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    sources = load_probe_sources(args.probe)
    if args.paint:
        requested = set(args.paint)
        missing = sorted(requested - set(sources))
        if missing:
            raise RuntimeError(f"requested paints are absent from the probe: {missing}")
        sources = {paint: sources[paint] for paint in args.paint}
    references = load_review_references(args.review or [Path(path) for path in DEFAULT_REVIEWS])
    panel_map = json.loads(args.panel_map.read_text(encoding="utf-8"))
    images, candidates_by_paint, records, queue = {}, {}, [], []
    for paint, source in sources.items():
        pil = Image.open(source).convert("RGB")
        image = np.asarray(pil)
        candidates, raw_count, companion_count = _build(image, panel_map, args.maximum)
        images[paint] = pil
        candidates_by_paint[paint] = candidates
        exact_path = _store_exact_candidates(args.output, paint, candidates)
        rows = []
        for candidate in candidates:
            provenance = candidate["provenance"]
            rows.append({
                "proposal_id": candidate["proposal_id"],
                "bbox": list(map(int, candidate["proposal_bbox"])),
                "palette_role": provenance.get("palette_role"),
                "component_count": int(provenance.get("component_count", 1)),
                "dominant_number_block": provenance.get("dominant_number_block", "none"),
                "number_block_fraction": round(float(provenance.get("dominant_number_block_fraction", 0.0)), 7),
                "cross_block_best_d4_similarity": round(float(provenance.get("cross_block_best_d4_similarity", -1.0)), 7),
                "owner_neutral": True,
                "ownership_authority": False,
            })
        paint_queue = _queue_candidates(paint, candidates, references[paint])
        queue.extend(paint_queue)
        records.append({
            "paint": paint,
            "source_1024": source,
            "raw_proposal_count": raw_count,
            "companion_count": companion_count,
            "candidate_count": len(candidates),
            "exact_candidate_bank": exact_path,
            "candidates": rows,
            "direct_review_queue_count": len(paint_queue),
        })
    queue.sort(key=lambda row: (row["paint"], row["candidate_index"], row["proposal_id"]))
    pages = _render_review_pages(images, candidates_by_paint, queue, args.output)
    payload = {
        "schema": "smart-tga-exact-tiled-candidate-bank-v1",
        "cycle": args.cycle,
        "paint_count": len(records),
        "candidate_count": sum(row["candidate_count"] for row in records),
        "exact_masks_persisted": True,
        "reviewed_bboxes_used_for_queue_selection_only": True,
        "runtime_bbox_authority": False,
        "records": records,
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "candidate_bank.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    review_payload = {
        "schema": "smart-tga-direct-candidate-review-v1",
        "cycle": 723,
        "review_method": "visual classification of exact masked candidate pixels; legacy bboxes selected the queue only",
        "allowed_semantics": ["Number", "Sponsor", "Template/hardware", "Paint/livery", "uncertain"],
        "queue_count": len(queue),
        "review_pages": pages,
        "labels": queue,
    }
    (args.output / "direct_review_labels.json").write_text(json.dumps(review_payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "paint_count": payload["paint_count"],
        "candidate_count": payload["candidate_count"],
        "review_queue_count": len(queue),
        "review_pages": len(pages),
        "elapsed_sec": payload["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
