"""Render bounded Neon Underground v4 A/B/material contacts and diagnostics.

This is an owner-eye aid, not an acceptance oracle. SPB-105 / NU-V4.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.neon_underground_v4.catalog import CATALOG, ORDER, module_name  # noqa: E402


def _rgb8(image: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(image, np.float32) * 255.0, 0, 255).astype(np.uint8)


def _tile(image: np.ndarray, title: str, width: int = 300, height: int = 220) -> np.ndarray:
    rgb = cv2.resize(_rgb8(image), (width, height), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((height + 38, width, 3), np.uint8)
    canvas[:height] = rgb
    cv2.putText(canvas, title, (9, height + 25), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (235, 235, 235), 1, cv2.LINE_AA)
    return canvas


def _spec_tile(spec: np.ndarray, title: str, width: int = 300, height: int = 220) -> np.ndarray:
    # M/R/Cc become cyan/magenta/yellow so causal disagreement stays visible.
    s = cv2.resize(spec, (width, height), interpolation=cv2.INTER_NEAREST).astype(np.float32) / 255.0
    rgb = np.stack((0.70 * s[..., 1] + 0.72 * s[..., 2],
                    0.82 * s[..., 0] + 0.68 * s[..., 2],
                    0.86 * s[..., 0] + 0.58 * s[..., 1]), axis=2)
    rgb = np.clip(rgb, 0.0, 1.0)
    canvas = np.zeros((height + 38, width, 3), np.uint8)
    canvas[:height] = _rgb8(rgb)
    cv2.putText(canvas, title + "  M/R/Cc", (9, height + 25), cv2.FONT_HERSHEY_SIMPLEX,
                0.52, (235, 235, 235), 1, cv2.LINE_AA)
    return canvas


def _contact(tiles: list[np.ndarray], columns: int) -> np.ndarray:
    if not tiles:
        raise ValueError("no tiles")
    blank = np.zeros_like(tiles[0])
    rows = []
    for start in range(0, len(tiles), columns):
        row = tiles[start:start + columns]
        row += [blank] * (columns - len(row))
        rows.append(np.concatenate(row, axis=1))
    return np.concatenate(rows, axis=0)


def _write_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise OSError(path)


def _broad_structure(image: np.ndarray) -> float:
    lum = np.mean(image, axis=2).astype(np.float32)
    broad = cv2.GaussianBlur(lum, (0, 0), 30.0)
    return float(np.std(broad) / max(float(np.std(lum)), 1e-6))


def _structure_thumb(image: np.ndarray) -> np.ndarray:
    lum = cv2.cvtColor(_rgb8(image), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    thumb = cv2.resize(lum, (48, 48), interpolation=cv2.INTER_AREA)
    thumb -= thumb.mean()
    norm = np.linalg.norm(thumb)
    return (thumb / max(float(norm), 1e-7)).ravel()


def _whole_canvas_utilization(image: np.ndarray) -> dict[str, float]:
    """Measure deliberate local anatomy, not brightness or random variation.

    A 64px WORK tile represents 128px at delivery. It is active only when it
    contains both local structure and fine/edge energy. This catches poster-like
    hero art surrounded by dead pixels without rewarding a flat bright wash.
    """
    lum = np.mean(np.asarray(image, np.float32), axis=2)
    fine = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 3.0))
    gy, gx = np.gradient(lum)
    gradient = np.sqrt(gx * gx + gy * gy)
    block = max(16, int(round(min(lum.shape) / 16.0)))
    rows = []
    for top in range(0, lum.shape[0], block):
        row = []
        for left in range(0, lum.shape[1], block):
            region = np.s_[top:min(top + block, lum.shape[0]), left:min(left + block, lum.shape[1])]
            structured = float(np.std(lum[region])) > 0.006
            detailed = (float(np.mean(fine[region])) > 0.0015
                        or float(np.mean(gradient[region])) > 0.0035)
            row.append(bool(structured and detailed))
        rows.append(row)
    active = np.asarray(rows, np.uint8)
    inactive = 1 - active
    components, _labels, stats, _centroids = cv2.connectedComponentsWithStats(inactive, 8)
    largest = int(stats[1:, cv2.CC_STAT_AREA].max()) if components > 1 else 0
    return {
        "active_block_fraction": round(float(np.mean(active)), 4),
        "largest_inactive_region_fraction": round(float(largest / active.size), 4),
    }


def _tile_readability(image: np.ndarray, side: int) -> dict[str, float]:
    """Measure whether the actual delivered tile keeps a material hierarchy.

    This deliberately samples the final downscaled pixel grid.  It is a
    diagnostic, not a way to win with noise: a good score needs tonal mass,
    chroma/light separation and structured local energy in most of the card.
    SPB-105 / NU-V4-TILE-1, 2026-08-28: owner says the live Neon cards lose
    their impact when tiled down, unlike the strongest Fractured Wilds work.
    """
    thumb = cv2.resize(np.asarray(image, np.float32), (side, side), interpolation=cv2.INTER_AREA)
    lum = np.mean(thumb, axis=2)
    sat = np.max(thumb, axis=2) - np.min(thumb, axis=2)
    gy, gx = np.gradient(lum)
    gradient = np.sqrt(gx * gx + gy * gy)
    cells = []
    cell = max(4, side // 4)
    for top in range(0, side, cell):
        for left in range(0, side, cell):
            sl = np.s_[top:top + cell, left:left + cell]
            cells.append(
                float(np.std(lum[sl])) > 0.018
                and float(np.mean(gradient[sl])) > 0.008
            )
    return {
        "luminance_std": round(float(np.std(lum)), 4),
        "structured_cell_fraction": round(float(np.mean(cells)), 4),
        "chroma_light_fraction": round(float(np.mean((sat > 0.20) & (lum > 0.12))), 4),
        "edge_energy": round(float(np.mean(gradient)), 5),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys", nargs="*", default=None)
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--output", default=str(ROOT / "_neon_v4_work"))
    args = parser.parse_args()
    keys = tuple(args.keys) if args.keys else ORDER
    unknown = [key for key in keys if key not in CATALOG]
    if unknown:
        raise SystemExit(f"unknown keys: {unknown}")

    out = Path(args.output)
    paint_tiles: list[np.ndarray] = []
    angle_tiles: list[np.ndarray] = []
    spec_tiles: list[np.ndarray] = []
    metrics: dict[str, object] = {}
    structures: dict[str, np.ndarray] = {}
    renders: dict[str, np.ndarray] = {}
    for key in keys:
        result = importlib.import_module(module_name(key)).build()
        renders[key] = result.paint
        name = CATALOG[key][1]
        paint_tiles.append(_tile(result.paint, name))
        angle_tiles.append(_tile(result.paint_b, name + " / B"))
        spec_tiles.append(_spec_tile(result.spec, name))
        lum = np.mean(result.paint, axis=2)
        sat = np.max(result.paint, axis=2) - np.min(result.paint, axis=2)
        val = np.max(result.paint, axis=2)
        delta = np.mean(np.abs(result.paint - result.paint_b), axis=2)
        per_channel = []
        for channel in range(3):
            values = result.spec[..., channel]
            per_channel.append({
                "std": round(float(np.std(values)), 4),
                "range": [int(values.min()), int(values.max())],
                "tiers": int(len(np.unique(values))),
            })
        metrics[key] = {
            "name": name,
            "carrier": result.carrier,
            "elapsed_seconds": round(float(result.elapsed_seconds), 4),
            "dark_fraction": round(float(np.mean(lum < 0.08)), 4),
            "neon_fraction": round(float(np.mean((sat > 0.45) & (val > 0.35))), 4),
            "broad_structure": round(_broad_structure(result.paint), 4),
            "angle_delta_mean": round(float(delta.mean()), 4),
            "angle_delta_p95": round(float(np.percentile(delta, 95)), 4),
            "whole_canvas": _whole_canvas_utilization(result.paint),
            "tile_readability": {
                "128": _tile_readability(result.paint, 128),
                "64": _tile_readability(result.paint, 64),
            },
            "spec": per_channel,
        }
        structures[key] = _structure_thumb(result.paint)

    pairwise = []
    for i, key_a in enumerate(keys):
        for key_b in keys[i + 1:]:
            corr = float(np.dot(structures[key_a], structures[key_b]))
            pairwise.append({"a": key_a, "b": key_b, "structure_correlation": round(corr, 4)})
    pairwise.sort(key=lambda row: row["structure_correlation"], reverse=True)
    payload = {"schema": "spb-neon-v4-review/1", "keys": list(keys),
               "metrics": metrics, "nearest_structure_pairs": pairwise[:25]}
    out.mkdir(parents=True, exist_ok=True)
    (out / "review.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_rgb(out / "paint_contact.png", _contact(paint_tiles, args.columns))
    _write_rgb(
        out / "picker_128_contact.png",
        _contact([_tile(renders[key], CATALOG[key][1], 128, 128)
                  for key in keys], args.columns),
    )
    _write_rgb(
        out / "micro_64_contact.png",
        _contact([_tile(renders[key], CATALOG[key][1], 64, 64)
                  for key in keys], args.columns),
    )
    _write_rgb(out / "angle_b_contact.png", _contact(angle_tiles, args.columns))
    _write_rgb(out / "spec_contact.png", _contact(spec_tiles, args.columns))
    print(json.dumps({"output": str(out), "count": len(keys),
                      "paint_contact": str(out / "paint_contact.png"),
                      "review": str(out / "review.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
