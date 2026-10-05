"""Build a review queue from Smart TGA ranker unmatched candidates.

This is offline Smart TGA tooling. It converts one or more
``top_unmatched_candidates.json`` files from the proposal ranker into the same
review queue format consumed by ``smart_tga_review_queue_to_corpus.py``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from smart_tga_number_candidate_miner import _box_iou, _crop_square, _read_rgb, _safe_name


DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_ranker_unmatched_review_queue")


def _xyxy(rec: dict[str, Any]) -> list[int]:
    box = rec.get("xyxy") or rec.get("box") or [0, 0, 0, 0]
    return [int(v) for v in box]


def _load_candidates(paths: list[Path], dedupe_iou: float) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_by_source: dict[str, list[list[int]]] = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"expected list in {path}")
        ranker_name = path.parent.name
        for rec in data:
            source_path = str(rec.get("source_path") or "")
            if not source_path:
                continue
            xyxy = _xyxy(rec)
            prior = seen_by_source.setdefault(source_path, [])
            if any(_box_iou(xyxy, old) >= dedupe_iou for old in prior):
                continue
            prior.append(xyxy)
            out = dict(rec)
            out["ranker_source"] = ranker_name
            out["ranker_json"] = str(path)
            out["xyxy"] = xyxy
            records.append(out)
    records.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)
    return records


def _write_queue(records: list[dict[str, Any]], out_dir: Path, limit: int) -> list[dict[str, Any]]:
    crop_dir = out_dir / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)
    rgb_cache: dict[str, np.ndarray] = {}
    queue: list[dict[str, Any]] = []
    for rec in records[:limit]:
        source = Path(str(rec["source_path"]))
        if not source.is_file():
            continue
        source_key = str(source.resolve())
        if source_key not in rgb_cache:
            rgb_cache[source_key] = _read_rgb(source)
        crop_box = rec.get("box") or rec["xyxy"]
        crop_name = (
            f"{len(queue):03d}_{_safe_name(source.parent.name)}_{_safe_name(source.stem)}_"
            f"rank{int(rec.get('rank', 0)):03d}_p{float(rec.get('score', 0.0)):.3f}.png"
        )
        crop_path = crop_dir / crop_name
        _crop_square(rgb_cache[source_key], tuple(int(v) for v in crop_box)).save(crop_path)
        item = {
            "review_label": "",
            "review_notes": "",
            "review_source": "ranker_top_unmatched",
            "suggested_labels": ["number", "hard_negative", "skip"],
            "review_index": len(queue),
            "paint": source_key,
            "folder": source.parent.name,
            "label": f"{source.parent.name}/{source.name}",
            "crop_file": str(crop_path.resolve()),
            "prediction": 1,
            "raw_score": round(float(rec.get("score", 0.0)), 6),
            "ranker_score": round(float(rec.get("score", 0.0)), 6),
            "image_score": rec.get("image_score"),
            "meta_score": rec.get("meta_score"),
            "meta_vetoed": rec.get("meta_vetoed"),
            "ranker_rank": rec.get("rank"),
            "ranker_source": rec.get("ranker_source"),
            "ranker_json": rec.get("ranker_json"),
            "proposal_index": rec.get("proposal_index"),
            "proposal_variant": rec.get("proposal_variant"),
            "proposal_score": rec.get("proposal_score"),
            "area": rec.get("area"),
            "fill": rec.get("fill"),
            "edge_density": rec.get("edge_density"),
            "soft_edge_density": rec.get("soft_edge_density"),
            "sat_density": rec.get("sat_density"),
            "aspect": rec.get("aspect"),
            "raw_box": rec.get("raw_box"),
            "box": rec.get("box") or rec["xyxy"],
            "xyxy": rec["xyxy"],
        }
        queue.append(item)
    return queue


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 6
    cell = 210
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        img = Image.open(rec["crop_file"]).convert("RGB").resize((166, 166), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 22, y + 25))
        draw.text(
            (x + 6, y + 5),
            f"#{rec['review_index']:02d} p {float(rec['ranker_score']):.3f} r {rec.get('ranker_rank')}",
            fill=(255, 230, 150),
        )
        draw.text((x + 6, y + 192), rec["folder"][:31], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def build_queue(args: argparse.Namespace) -> dict[str, Any]:
    args.output.mkdir(parents=True, exist_ok=True)
    candidates = _load_candidates(args.unmatched_json, args.dedupe_iou)
    queue = _write_queue(candidates, args.output, args.limit)
    (args.output / "review_queue.json").write_text(json.dumps(queue, indent=2), encoding="utf-8")
    (args.output / "candidates.json").write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    for start in range(0, len(queue), args.sheet_page_size):
        page = queue[start:start + args.sheet_page_size]
        suffix = start // args.sheet_page_size
        _contact_sheet(page, args.output / f"review_queue_sheet_{suffix:02d}.png", f"Ranker unmatched review queue {suffix:02d}")
    if queue:
        _contact_sheet(queue[: args.sheet_page_size], args.output / "review_queue_sheet.png", "Ranker unmatched review queue")
    summary = {
        "inputs": [str(p) for p in args.unmatched_json],
        "output": str(args.output.resolve()),
        "dedupe_iou": args.dedupe_iou,
        "loaded_candidates_after_dedupe": len(candidates),
        "review_queue": len(queue),
        "review_queue_json": str((args.output / "review_queue.json").resolve()),
        "sheet_page_size": args.sheet_page_size,
        "sheet_pages": int(np.ceil(len(queue) / max(1, args.sheet_page_size))),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unmatched-json", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=96)
    parser.add_argument("--dedupe-iou", type=float, default=0.82)
    parser.add_argument("--sheet-page-size", type=int, default=48)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(build_queue(parse_args()), indent=2))


if __name__ == "__main__":
    main()
