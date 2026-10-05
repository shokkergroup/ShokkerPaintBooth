# -*- coding: utf-8 -*-
"""Native-2048 Emperor Scale I1 paint-only lamellar-avalanche study.

FROZEN REJECT (SPB-105 tick 2026-08-25): actual 2048 review reads as
oversized glowing rail spaghetti with tiny repeated pink failure decorations.
The chronology is explicit, fast and angle-reactive, but the long shelf carrier
overwhelms every attached mark. No spec maps were made.

SPB-105 / 2026-08-25 native rebuild tick. Owner verdict being answered:
recoloured copies and shared topology are wasted app space; actual 2048 canvas
controls, and fine 8-32 px structure must build the material. This renderer
uses one chronological terraced sheet whose ledges change pitch/direction,
terminate in unequal shelf collapses and carry attached root pockets,
cross-ties, microcrack hooks and interrupted polished edge runs.

Paint/A-B only until native eye. No RNG, sampled noise, grain, cells, stamps,
Voronoi, shared Wilds composer or legacy renderer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_emperor_scale"
WORK = 1024
NATIVE = 2048

ROYAL_A = np.asarray([
    (5, 3, 13), (20, 6, 45), (52, 8, 83), (91, 12, 116),
    (137, 18, 136), (182, 29, 145), (221, 49, 146), (246, 79, 139),
    (255, 119, 127), (255, 164, 113), (255, 207, 107), (239, 237, 132),
    (184, 238, 168), (103, 213, 190), (52, 145, 190),
], np.float32)
ROYAL_B = np.asarray([
    (2, 10, 18), (2, 31, 47), (2, 60, 72), (3, 94, 91),
    (6, 132, 107), (14, 169, 119), (35, 201, 127), (74, 225, 137),
    (126, 240, 153), (190, 246, 181), (239, 240, 211), (255, 207, 210),
    (246, 149, 205), (202, 93, 194), (125, 57, 168),
], np.float32)


def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix


def _schedule(index: int, modulus: int, multiplier: int, offset: int = 0) -> int:
    """Deterministic unequal chronology; this does not place a repeated stamp."""
    return (index * multiplier + index * index * 7 + offset) % modulus


def _shelf_points(index: int) -> np.ndarray:
    x = np.arange(-24, WORK + 25, 3, dtype=np.float32)
    pitch_accum = index * 12.15 + 0.052 * index * index
    slope = -0.15 + 0.31 * np.sin(index * 2.39996323)
    amp_a = 4.0 + (index * 11 % 13)
    amp_b = 2.5 + (index * 7 % 9)
    y = (
        -42.0 + pitch_accum + slope * (x - WORK * 0.5)
        + amp_a * np.sin(x / (51.0 + index % 19) + index * 0.73)
        + amp_b * np.sin(x / (17.0 + index % 11) - index * 0.37)
    )
    # Each deposition front acquired two or three one-sided collapse offsets.
    # The offsets change location, handedness and width per chronology index.
    for event in range(2 + index % 2):
        cx = 70 + _schedule(index + event * 23, 884, 41, event * 137)
        width = 8.0 + _schedule(index + event * 5, 19, 13)
        step = (5.0 + _schedule(index + event * 9, 12, 17)) * (-1 if (index + event) % 2 else 1)
        y += step * (0.5 + 0.5 * np.tanh((x - cx) / width))
    return np.rint(np.stack((x, y), axis=1)).astype(np.int32)


def _clip_piece(points: np.ndarray) -> np.ndarray:
    keep = ((points[:, 0] >= -8) & (points[:, 0] <= WORK + 8)
            & (points[:, 1] >= -8) & (points[:, 1] <= WORK + 8))
    return points[keep]


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Quiet optical substrate. Its long movement is subordinate to the visible
    # mechanical ledges; it only lets the same physical sheet flip by angle.
    chroma = np.mod(
        0.00041 * x + 0.00063 * y
        + 0.13 * np.sin((x + 0.71 * y) / 139.0)
        + 0.09 * np.sin((1.31 * x - y) / 211.0),
        1.0,
    )
    if angle_b:
        chroma = np.mod(chroma + 0.43 + 0.08 * np.sin((x - y) / 87.0), 1.0)
        stops = ROYAL_B
    else:
        stops = ROYAL_A
    image = _palette(chroma, stops)
    light = 0.33 + 0.10 * np.sin((x - 0.37 * y) / 91.0) + 0.08 * np.cos((x + y) / 173.0)
    image = np.clip(image * light[..., None], 0, 255).astype(np.uint8)

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "ledge", "undercut", "collapse", "root_pocket", "cross_tie",
        "microcrack", "polish",
    )}
    shelf_cache: list[np.ndarray] = []
    for i in range(91):
        pts = _clip_piece(_shelf_points(i))
        if len(pts) < 12:
            shelf_cache.append(pts)
            continue
        shelf_cache.append(pts)
        # Unequal chronological gaps prevent an unbroken rail or wallpaper row.
        gap_count = 2 + i % 4
        open_mask = np.ones(len(pts), dtype=bool)
        for g in range(gap_count):
            center_x = 26 + _schedule(i + g * 31, 972, 37, g * 113)
            half = 5 + _schedule(i + g * 17, 12, 29)
            open_mask &= np.abs(pts[:, 0] - center_x) > half
        starts = np.flatnonzero(open_mask & np.r_[True, ~open_mask[:-1]])
        ends = np.flatnonzero(open_mask & np.r_[~open_mask[1:], True]) + 1
        pieces = [pts[a:b] for a, b in zip(starts, ends) if b - a >= 4]
        tier = 72 + 22 * (i % 8)
        width = 2 + i % 3  # 4-8 px native edge anatomy.
        under = [piece + np.asarray((0, 3 + i % 4), np.int32) for piece in pieces]
        cv2.polylines(masks["undercut"], under, False, tier, width + 2, cv2.LINE_AA)
        cv2.polylines(masks["ledge"], pieces, False, tier, width, cv2.LINE_AA)

        under_color = (3, 2, 8) if not angle_b else (1, 7, 10)
        lip_color = (245, 185, 78) if not angle_b else (77, 231, 171)
        cv2.polylines(image, under, False, under_color, width + 2, cv2.LINE_AA)
        cv2.polylines(image, pieces, False, lip_color, width, cv2.LINE_AA)

        # Partial polish histories occupy short 8-30 px native packets, not the
        # whole shelf. Different packets light under angle B.
        for p_index, piece in enumerate(pieces):
            if len(piece) < 8:
                continue
            start = _schedule(i + p_index * 19, max(1, len(piece) - 6), 23)
            run = 4 + _schedule(i + p_index * 11, 11, 31)
            packet = piece[start:min(len(piece), start + run)]
            if len(packet) >= 3 and ((i + p_index + int(angle_b)) % 3 != 0):
                cv2.polylines(masks["polish"], [packet], False, 96 + 20 * (i % 8), 2, cv2.LINE_AA)
                cv2.polylines(image, [packet], False,
                              (255, 238, 161) if not angle_b else (230, 172, 233), 1, cv2.LINE_AA)

    # Collapse anatomy belongs to the gaps in selected ledges. Each event uses
    # an unequal open wedge, a root pocket, cross-ties and a hooked microcrack.
    for event in range(37):
        i = 4 + _schedule(event, 82, 47)
        pts = shelf_cache[i]
        if len(pts) < 20:
            continue
        k = 7 + _schedule(event, len(pts) - 14, 43)
        p = pts[k].astype(np.float32)
        q = pts[min(k + 3, len(pts) - 1)].astype(np.float32)
        tangent = q - p
        tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        side = -1.0 if event % 2 else 1.0
        length = 6 + _schedule(event, 10, 17)
        depth = 5 + _schedule(event, 9, 23)
        wedge = np.rint(np.asarray([
            p - tangent * length,
            p + tangent * (length + 2),
            p + tangent * (length // 3) + normal * side * depth,
            p - tangent * (length // 2) + normal * side * (depth + 3),
        ])).astype(np.int32)
        tier = 78 + 23 * (event % 8)
        cv2.fillConvexPoly(masks["collapse"], wedge, tier, cv2.LINE_AA)
        cv2.fillConvexPoly(image, wedge, (10, 5, 18) if not angle_b else (3, 19, 21), cv2.LINE_AA)

        # Open root pocket: a bent failure lip, deliberately not a closed eye.
        root = np.rint(np.asarray([
            p - tangent * 5,
            p + normal * side * 4,
            p + tangent * 4 + normal * side * 7,
            p + tangent * 8 + normal * side * 3,
        ])).astype(np.int32)
        cv2.polylines(masks["root_pocket"], [root], False, tier, 3, cv2.LINE_AA)
        cv2.polylines(image, [root], False,
                      (238, 94, 146) if not angle_b else (123, 106, 231), 2, cv2.LINE_AA)

        for tie_index in range(1 + event % 3):
            anchor = p + tangent * (tie_index * 5 - 4)
            tie = np.rint(np.asarray([
                anchor - normal * side * (2 + tie_index),
                anchor + normal * side * (5 + event % 5),
            ])).astype(np.int32)
            cv2.polylines(masks["cross_tie"], [tie], False, 86 + 21 * ((event + tie_index) % 8), 2, cv2.LINE_AA)
            cv2.polylines(image, [tie], False,
                          (244, 211, 109) if not angle_b else (111, 227, 203), 1, cv2.LINE_AA)

        crack = np.rint(np.asarray([
            p + normal * side * depth,
            p + normal * side * (depth + 4) + tangent * 3,
            p + normal * side * (depth + 7) - tangent * 2,
            p + normal * side * (depth + 10) + tangent * (2 + event % 4),
        ])).astype(np.int32)
        cv2.polylines(masks["microcrack"], [crack], False, tier, 2, cv2.LINE_AA)
        cv2.polylines(image, [crack], False, (2, 2, 5), 1, cv2.LINE_AA)

    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    return image, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "emperor_lamellar_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage = _paint(False)
    b, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint = output / f"{ID}_paint_2048.png"
    _write(paint, native_a)
    shutil.copyfile(paint, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-emperor-lamellar-i1/1",
        "status": "REJECT-OVERSIZED-GLOWING-SHELF-RAILS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "chronological terraced lamellar avalanche with unequal attached failures",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit unequal shelf histories; no RNG/noise/grain/cells/stamps/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
