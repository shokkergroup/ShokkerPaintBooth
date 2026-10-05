"""Mine visually similar Smart TGA proposal crops from known mistake seeds.

This is offline Smart TGA tooling. It takes mistake/seed records from the
hierarchical evaluator plus candidate-miner JSON files, computes a compact
RGB/HSV/luma/edge crop descriptor, and writes an indexed review queue of the
nearest real-TGA candidates. It does not affect Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


PATCH = 160


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:96] or "sample"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _feature(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    rgb48 = np.asarray(img.resize((48, 48), Image.Resampling.LANCZOS), np.float32) / 255.0
    rgb24 = cv2.resize(rgb48, (24, 24), interpolation=cv2.INTER_AREA)
    hsv24 = cv2.cvtColor((rgb24 * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv24[:, :, 0] /= 179.0
    hsv24[:, :, 1:] /= 255.0
    gray32 = cv2.cvtColor((cv2.resize(rgb48, (32, 32), interpolation=cv2.INTER_AREA) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    edges32 = (cv2.Canny(gray32, 40, 130).astype(np.float32) / 255.0)[:, :, None]
    gray32f = (gray32.astype(np.float32) / 255.0)[:, :, None]
    stats: list[float] = []
    for arr in (rgb48, hsv24, gray32f, edges32):
        flat = arr.reshape(-1, arr.shape[-1])
        stats.extend(np.mean(flat, axis=0).tolist())
        stats.extend(np.std(flat, axis=0).tolist())
        stats.extend(np.percentile(flat, [10, 50, 90], axis=0).reshape(-1).tolist())
    vector = np.concatenate([
        rgb48.reshape(-1),
        hsv24.reshape(-1),
        gray32f.reshape(-1),
        edges32.reshape(-1),
        np.asarray(stats, np.float32),
    ]).astype(np.float32)
    norm = float(np.linalg.norm(vector))
    if norm > 1e-6:
        vector /= norm
    return vector


def _load_seeds(paths: list[Path], only_mistakes: bool) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for path in paths:
        records = _read_json(path)
        if not isinstance(records, list):
            raise ValueError(f"expected list in {path}")
        for index, rec in enumerate(records):
            if only_mistakes:
                truth = str(rec.get("hier_truth") or rec.get("truth") or "")
                pred = str(rec.get("hier_pred") or rec.get("pred") or "")
                if not truth or not pred or truth == pred:
                    continue
            file_path = Path(str(rec.get("file") or ""))
            if not file_path.is_file():
                continue
            seed = dict(rec)
            seed["seed_source_file"] = str(path)
            seed["seed_source_index"] = index
            seed["seed_file"] = str(file_path)
            seeds.append(seed)
    return seeds


def _load_candidates(paths: list[Path], min_edge: float, min_sat: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        records = _read_json(path)
        if not isinstance(records, list):
            raise ValueError(f"expected list in {path}")
        for index, rec in enumerate(records):
            crop = Path(str(rec.get("crop_file") or rec.get("file") or ""))
            if not crop.is_file():
                continue
            edge_density = float(rec.get("edge_density") or rec.get("soft_edge_density") or 0.0)
            sat_density = float(rec.get("sat_density") or 0.0)
            if edge_density < min_edge or sat_density < min_sat:
                continue
            key = str(crop.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            row = dict(rec)
            row["candidate_source_file"] = str(path)
            row["candidate_source_index"] = index
            row["crop_file"] = str(crop)
            rows.append(row)
    return rows


def _source_key(rec: dict[str, Any]) -> str:
    raw = rec.get("paint") or rec.get("source_path") or rec.get("source") or ""
    return str(raw).replace("\\", "/").lower()


def _copy_crop(src: Path, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{_safe_name(name)}.png"
    Image.open(src).convert("RGB").resize((PATCH, PATCH), Image.Resampling.LANCZOS).save(out_path)
    return out_path.resolve()


def _write_sheet(rows: list[dict[str, Any]], out_path: Path, title: str, max_items: int) -> None:
    if not rows:
        return
    rows = rows[:max_items]
    cols = 8
    cell_w = 190
    cell_h = 210
    sheet_rows = int(math.ceil(len(rows) / cols))
    sheet = Image.new("RGB", (cols * cell_w, sheet_rows * cell_h), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        img = Image.open(rec["crop_file"]).convert("RGB").resize((160, 160), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 15, y + 24))
        seed_tag = rec.get("nearest_seed_tag") or "seed"
        dist = float(rec.get("nearest_distance", 0.0))
        draw.text((x + 6, y + 4), f"#{rec['review_index']:03d} d={dist:.3f} {seed_tag}"[:30], fill=(255, 255, 150))
        source = str(rec.get("folder") or Path(str(rec.get("paint") or rec.get("crop_file"))).parent.name)
        draw.text((x + 6, y + 188), source[:28], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def mine(args: argparse.Namespace) -> dict[str, Any]:
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    seeds = _load_seeds(args.seed_records, args.seed_only_mistakes)
    candidates = _load_candidates(args.candidate_json, args.candidate_min_edge, args.candidate_min_sat)
    if not seeds:
        raise ValueError("no usable seed records")
    if not candidates:
        raise ValueError("no usable candidates")

    seed_features = np.stack([_feature(Path(seed["seed_file"])) for seed in seeds]).astype(np.float32)
    candidate_features = np.stack([_feature(Path(cand["crop_file"])) for cand in candidates]).astype(np.float32)
    distances = 1.0 - np.clip(candidate_features @ seed_features.T, -1.0, 1.0)

    ranked: list[dict[str, Any]] = []
    used_crop: set[str] = set()
    for seed_index, seed in enumerate(seeds):
        order = np.argsort(distances[:, seed_index])
        kept = 0
        for cand_index in order:
            cand = candidates[int(cand_index)]
            if args.exclude_same_source and _source_key(seed) and _source_key(seed) == _source_key(cand):
                continue
            crop_key = str(Path(cand["crop_file"]).resolve()).lower()
            if crop_key in used_crop:
                continue
            used_crop.add(crop_key)
            row = dict(cand)
            row["nearest_seed_index"] = seed_index
            row["nearest_seed_source_index"] = seed.get("seed_source_index")
            row["nearest_seed_truth"] = seed.get("truth")
            row["nearest_seed_subtype"] = seed.get("subtype")
            row["nearest_seed_file"] = seed.get("seed_file")
            row["nearest_seed_source"] = seed.get("source_path") or seed.get("source")
            row["nearest_seed_tag"] = str(seed.get("subtype") or seed.get("truth") or f"seed{seed_index}")
            row["nearest_distance"] = round(float(distances[int(cand_index), seed_index]), 6)
            row["seed_hier_pred"] = seed.get("hier_pred")
            row["seed_hier_truth"] = seed.get("hier_truth")
            ranked.append(row)
            kept += 1
            if kept >= args.per_seed:
                break
    ranked.sort(key=lambda rec: (float(rec["nearest_distance"]), str(rec.get("paint") or ""), str(rec.get("crop_file"))))
    ranked = ranked[: args.max_results]

    crops_out = out / "crops"
    review_queue: list[dict[str, Any]] = []
    for review_index, rec in enumerate(ranked):
        copied = _copy_crop(Path(rec["crop_file"]), crops_out, f"nearest_{review_index:04d}_{Path(str(rec.get('paint') or rec.get('crop_file'))).stem}")
        row = dict(rec)
        row["review_index"] = review_index
        row["source_crop_file"] = rec["crop_file"]
        row["crop_file"] = str(copied)
        row["review_label"] = ""
        review_queue.append(row)

    queue_path = out / "review_queue.json"
    queue_path.write_text(json.dumps(review_queue, indent=2), encoding="utf-8")
    (out / "seeds.json").write_text(json.dumps(seeds, indent=2), encoding="utf-8")
    _write_sheet(review_queue, out / "review_queue_sheet.png", "Smart TGA visual-nearest review queue", args.sheet_items)
    summary = {
        "seed_records": [str(p) for p in args.seed_records],
        "candidate_json": [str(p) for p in args.candidate_json],
        "output": str(out.resolve()),
        "seeds": len(seeds),
        "candidates": len(candidates),
        "candidate_min_edge": args.candidate_min_edge,
        "candidate_min_sat": args.candidate_min_sat,
        "review_queue": len(review_queue),
        "per_seed": args.per_seed,
        "max_results": args.max_results,
        "exclude_same_source": args.exclude_same_source,
        "review_queue_json": str(queue_path.resolve()),
        "review_queue_sheet": str((out / "review_queue_sheet.png").resolve()),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-records", type=Path, action="append", required=True)
    parser.add_argument("--candidate-json", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-seed", type=int, default=30)
    parser.add_argument("--max-results", type=int, default=160)
    parser.add_argument("--sheet-items", type=int, default=160)
    parser.add_argument("--candidate-min-edge", type=float, default=0.0)
    parser.add_argument("--candidate-min-sat", type=float, default=0.0)
    parser.add_argument("--seed-only-mistakes", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--exclude-same-source", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(mine(parse_args()), indent=2))


if __name__ == "__main__":
    main()
