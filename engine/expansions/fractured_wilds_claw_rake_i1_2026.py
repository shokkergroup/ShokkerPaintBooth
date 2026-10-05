# -*- coding: utf-8 -*-
"""Isolated native-2048 Claw Rake pressure-fracture ledger.

SPB-WILDS-CLAW-I1 / SPB-105, 2026-08-24. Explicit chronological strike paths
produce fine gouge cores, displaced lips, taper tails, terminal punctures,
crushed wedges, stress arcs, abrasion chips and older/later crosscuts. Local
widths target 8-32 px at native 2048.

Paint/A-B review only. No RNG, sampled noise, grain, slash scatter, repeated
claw stamp, shared Wilds composer or material maps. Fail closed until native
owner-eye review.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fc_claw_rake"
WORK = 1024
NATIVE = 2048

PALETTE_A = [
    (16, 205, 226), (33, 239, 164), (168, 247, 58), (252, 211, 49),
    (255, 115, 35), (240, 45, 90), (187, 45, 217), (92, 64, 238),
]
PALETTE_B = [
    (242, 52, 177), (255, 72, 80), (255, 143, 35), (249, 222, 55),
    (108, 238, 90), (35, 217, 195), (31, 148, 239), (104, 70, 235),
]


def _curve(points: list[tuple[float, float]], samples: int = 160) -> np.ndarray:
    p = np.asarray(points, np.float32)
    t = np.linspace(0.0, 1.0, samples, dtype=np.float32)[:, None]
    q = ((1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1]
         + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3])
    return np.rint(q).astype(np.int32)


def _offset_controls(controls: list[tuple[float, float]], offset: float,
                     bend: float) -> list[tuple[float, float]]:
    p = np.asarray(controls, np.float32)
    tangent = p[-1] - p[0]
    normal = np.asarray([-tangent[1], tangent[0]], np.float32)
    normal /= max(float(np.linalg.norm(normal)), 1e-6)
    weights = np.asarray([1.0, 0.62 + bend, 0.62 - bend, 0.18], np.float32)[:, None]
    return [tuple(v) for v in (p + offset * weights * normal)]


def _base(angle_b: bool) -> np.ndarray:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x, y = xx / WORK, yy / WORK
    polish = 0.5 + 0.5 * np.sin(13.0 * x + 9.0 * y + 0.7 * np.sin(5.0 * x - 3.0 * y))
    cross = 0.5 + 0.5 * np.sin(17.0 * x - 12.0 * y)
    if angle_b:
        rgb = np.stack((11 + 8 * polish, 8 + 5 * cross, 20 + 13 * polish), axis=2)
    else:
        rgb = np.stack((7 + 5 * cross, 15 + 10 * polish, 19 + 12 * cross), axis=2)
    return np.clip(rgb, 0, 255).astype(np.uint8)


STRIKES = [
    [(-90, 150), (180, 55), (470, 250), (765, 195)],
    [(90, -60), (210, 190), (410, 365), (690, 535)],
    [(1085, 45), (825, 175), (760, 420), (535, 605)],
    [(-75, 455), (210, 370), (550, 520), (1035, 485)],
    [(170, 1080), (230, 795), (485, 690), (620, 405)],
    [(1060, 820), (785, 725), (620, 900), (300, 805)],
    [(-80, 860), (160, 720), (350, 850), (545, 690)],
    [(760, 1080), (690, 850), (930, 650), (1045, 360)],
    [(380, -65), (455, 155), (300, 340), (390, 600)],
    [(1080, 980), (830, 900), (770, 695), (570, 560)],
]


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    palette = PALETTE_B if angle_b else PALETTE_A
    image = _base(angle_b)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "core", "lip", "puncture", "wedge", "stress", "chip", "crosscut")}
    track_count = 0

    for strike_index, controls in enumerate(STRIKES):
        count = 3 + (strike_index * 5) % 5
        spread = 9 + (strike_index * 7) % 12
        color = palette[strike_index % len(palette)]
        lip_color = palette[(strike_index + 3) % len(palette)]
        strike_paths = []
        for lane in range(count):
            centered = lane - 0.5 * (count - 1)
            bend = 0.14 * np.sin(0.9 * strike_index + 1.7 * lane)
            path = _curve(_offset_controls(controls, centered * spread, bend), 190)
            strike_paths.append(path)
            width = 4 + (strike_index + 2 * lane) % 6
            # Earlier strikes stay visible beneath later chronology; the lip is
            # laid after its dark core and only on the pressure side.
            cv2.polylines(image, [path], False, (3, 4, 7), width + 3, cv2.LINE_AA)
            cv2.polylines(masks["core"], [path], False, 255, width + 2, cv2.LINE_AA)
            lip = path.copy()
            lip[:, 0] += 2 + (strike_index % 3)
            lip[:, 1] -= 1 + (lane % 2)
            cv2.polylines(image, [lip], False, color, max(2, width // 2), cv2.LINE_AA)
            cv2.polylines(masks["lip"], [lip], False, 80 + 25 * (lane % 7), max(2, width // 2), cv2.LINE_AA)

            # Tapered last quarter is redrawn in decreasing widths rather than
            # ending as a blunt macro slash.
            tail = path[int(len(path) * 0.74):]
            chunks = np.array_split(tail, 4)
            for k, chunk in enumerate(chunks):
                if len(chunk) < 2:
                    continue
                cv2.polylines(image, [chunk], False, lip_color, max(1, width - k - 2), cv2.LINE_AA)

            ex, ey = map(int, path[-1])
            radius = 4 + (lane + strike_index) % 5
            cv2.circle(image, (ex, ey), radius + 2, (3, 4, 7), -1, cv2.LINE_AA)
            cv2.circle(image, (ex, ey), radius, lip_color, 2, cv2.LINE_AA)
            cv2.circle(masks["puncture"], (ex, ey), radius + 1,
                       95 + 22 * ((lane + strike_index) % 7), -1, cv2.LINE_AA)

            # Unequal crushed wedges share the terminal load direction.
            if (lane + strike_index) % 2 == 0:
                dx = 7 + (3 * lane) % 9
                dy = -5 + (5 * strike_index) % 11
                wedge = np.asarray([(ex, ey), (ex + dx, ey + dy),
                                    (ex + dx + 8, ey + dy + 3),
                                    (ex + 3, ey + 6)], np.int32)
                cv2.fillConvexPoly(image, wedge, color, cv2.LINE_AA)
                cv2.fillConvexPoly(masks["wedge"], wedge,
                                   105 + 20 * ((lane + 2 * strike_index) % 7), cv2.LINE_AA)
            track_count += 1

        # A stress arc links only the two outer terminal punctures of each event.
        a = tuple(map(int, strike_paths[0][-1]))
        b = tuple(map(int, strike_paths[-1][-1]))
        center = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
        axes = (12 + spread * count // 3, 7 + spread * count // 5)
        angle = int(np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0])))
        cv2.ellipse(image, center, axes, angle, 195, 342, color, 2, cv2.LINE_AA)
        cv2.ellipse(masks["stress"], center, axes, angle, 195, 342,
                    85 + 17 * (strike_index % 8), 3, cv2.LINE_AA)

        # Abrasion chips attach to alternating lips; they are short point clusters,
        # not loose noise or a full-frame fleck field.
        anchor_path = strike_paths[(strike_index * 3) % len(strike_paths)]
        for chip_index, pos in enumerate((0.22, 0.39, 0.57, 0.69)):
            px, py = map(int, anchor_path[int(pos * (len(anchor_path) - 1))])
            r = 2 + (strike_index + chip_index) % 4
            cv2.circle(image, (px, py), r, lip_color, -1, cv2.LINE_AA)
            cv2.circle(masks["chip"], (px, py), r, 90 + 30 * (chip_index % 6), -1, cv2.LINE_AA)

    # Crosscut mask is derived after chronology from locations where independent
    # cores overlap; it is not another drawn carrier.
    core_binary = (masks["core"] > 0).astype(np.uint8)
    overlap = cv2.boxFilter(core_binary, cv2.CV_16U, (13, 13), normalize=False)
    masks["crosscut"] = np.where(overlap > 58, 220, 0).astype(np.uint8)
    cross_edge = cv2.morphologyEx(masks["crosscut"], cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    image[cross_edge > 0] = palette[6 if angle_b else 2]

    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    coverage["tracks"] = float(track_count)
    return image, masks, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "claw_rake_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, _, coverage = _paint(False)
    b, _, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    _write(output / f"{ID}_paint_2048.png", native_a)
    _write(output / f"{ID}_angle_a_2048.png", native_a)
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-claw-rake-i1/1",
        "status": "REJECT-NEON-CABLE-ROADS-CIRCULAR-TERMINALS-DO-NOT-WIRE",
        "owner_accepted": False, "production_wired": False,
        "finish_id": ID, "native_size": [2048, 2048],
        "topology": "chronological pressure-fracture strike ledger",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit strike raster; no RNG/noise/grain/slash scatter/stamps",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
