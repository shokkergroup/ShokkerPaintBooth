# -*- coding: utf-8 -*-
"""Isolated native-2048 kinematic carapace topology study.

SPB-WILDS-STAG-I1 / SPB-105, 2026-08-24. Native verdict: REJECT. Forty-seven
mechanically continuous chains still become long rail paths decorated by tiny
repeated colored plates, with huge empty basins between them. Hinge pins,
slots, teeth, ribs, lips and fracture stops do not overcome the failed carrier.
No density, lane, palette, plate, director or spec repair is authorized.
Installer remains fail-closed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


ID = "fmo_stag_carapace"
WORK = 512
PALETTE = np.asarray([
    (0.025, 0.040, 0.055), (0.055, 0.090, 0.105),
    (0.080, 0.180, 0.165), (0.110, 0.310, 0.245),
    (0.180, 0.480, 0.330), (0.340, 0.650, 0.390),
    (0.620, 0.780, 0.300), (0.850, 0.690, 0.210),
    (0.950, 0.430, 0.140), (0.840, 0.180, 0.190),
    (0.610, 0.100, 0.300), (0.390, 0.100, 0.410),
    (0.180, 0.170, 0.430), (0.080, 0.360, 0.560),
], np.float32)


def _fract(x: float) -> float:
    return x - np.floor(x)


def _q(index: int, salt: float) -> float:
    """Low-discrepancy causal selector, not sampled random noise."""
    return _fract((index + 1) * 0.61803398875 + salt * 0.41421356237)


def _director(x: float, y: float, lane: int) -> float:
    u = x / WORK - 0.5
    v = y / WORK - 0.5
    bend = 0.44 * np.sin(5.1 * u - 3.7 * v + lane * 0.17)
    bend += 0.28 * np.sin(3.2 * u + 4.6 * v - lane * 0.11)
    for cx, cy, charge in ((0.19, 0.23, 0.42), (0.73, 0.31, -0.36),
                           (0.42, 0.76, 0.31), (0.86, 0.82, -0.27)):
        dx = x / WORK - cx
        dy = y / WORK - cy
        bend += charge * np.exp(-(dx * dx + dy * dy) / 0.075) * np.arctan2(dy, dx)
    return float(bend)


def _poly(center: np.ndarray, tangent: np.ndarray, normal: np.ndarray,
          length: float, width: float, skew: float) -> np.ndarray:
    a = center - tangent * length * 0.53
    b = center + tangent * length * 0.47
    return np.rint(np.asarray([
        a + normal * width * (0.50 + skew),
        b + normal * width * 0.38,
        b - normal * width * 0.48,
        center - tangent * length * 0.62 - normal * width * (0.42 - skew),
    ])).astype(np.int32)


def _line(canvas: np.ndarray, p0: Iterable[float], p1: Iterable[float],
          color: tuple[float, float, float], width: int = 1) -> None:
    cv2.line(canvas, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
             color, width, cv2.LINE_AA)


def build_paint() -> tuple[np.ndarray, dict]:
    paint = np.empty((WORK, WORK, 3), np.float32)
    paint[:] = PALETTE[0]
    occupancy = np.zeros((WORK, WORK), np.uint8)
    counts = {name: 0 for name in (
        "sclerite_plates", "hinge_pins", "flexure_slots", "locking_teeth",
        "compression_ribs", "wear_lips", "fracture_stops", "collision_scars",
    )}

    for lane in range(47):
        edge = lane % 4
        t = (lane + 0.5) / 47.0
        if edge == 0:
            pos = np.asarray((-12.0, t * WORK), np.float32); base = 0.0
        elif edge == 1:
            pos = np.asarray((WORK + 12.0, (1.0 - t) * WORK), np.float32); base = np.pi
        elif edge == 2:
            pos = np.asarray((t * WORK, -12.0), np.float32); base = np.pi * 0.5
        else:
            pos = np.asarray(((1.0 - t) * WORK, WORK + 12.0), np.float32); base = -np.pi * 0.5

        previous = pos.copy()
        collision_run = 0
        for step in range(84):
            theta = base + _director(float(pos[0]), float(pos[1]), lane)
            theta += (_q(step + lane * 89, 1.7) - 0.5) * 0.18
            tangent = np.asarray((np.cos(theta), np.sin(theta)), np.float32)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            length = 5.2 + 3.6 * _q(step + lane * 97, 2.9)
            width = 4.1 + 3.0 * _q(step + lane * 101, 4.3)
            center = pos + tangent * length * 0.44

            ix = int(np.clip(round(center[0]), 0, WORK - 1))
            iy = int(np.clip(round(center[1]), 0, WORK - 1))
            crowded = occupancy[iy, ix] > 165
            collision_run = collision_run + 1 if crowded else max(0, collision_run - 1)
            if collision_run >= 3:
                base += (0.72 if lane % 2 else -0.64)
                collision_run = 0
                counts["collision_scars"] += 1

            skew = (_q(step + lane * 103, 6.1) - 0.5) * 0.28
            polygon = _poly(center, tangent, normal, length, width, skew)
            phase = (lane * 5 + step * 3 + int(7 * _q(lane, 8.2))) % (len(PALETTE) - 2) + 2
            fill = tuple(float(v) for v in PALETTE[phase])
            outline = tuple(float(v) for v in PALETTE[(phase + 10) % len(PALETTE)] * 0.56)
            cv2.fillConvexPoly(paint, polygon, fill, cv2.LINE_AA)
            cv2.polylines(paint, [polygon], True, outline, 1, cv2.LINE_AA)
            cv2.fillConvexPoly(occupancy, polygon, min(255, 72 + lane * 3), cv2.LINE_8)
            counts["sclerite_plates"] += 1

            hinge = center - tangent * length * 0.42
            radius = 1 + ((lane + step) % 2)
            cv2.circle(paint, tuple(np.rint(hinge).astype(int)), radius,
                       tuple(float(v) for v in PALETTE[(phase + 4) % len(PALETTE)]),
                       -1, cv2.LINE_AA)
            counts["hinge_pins"] += 1

            slot_center = center + tangent * length * 0.08
            _line(paint, slot_center - normal * width * 0.24,
                  slot_center + normal * width * 0.24,
                  tuple(float(v) for v in PALETTE[1]), 1)
            counts["flexure_slots"] += 1

            for tooth in (-0.26, 0.03, 0.30):
                root = center + tangent * length * 0.42 + normal * width * tooth
                tip = root + tangent * (1.2 + 0.8 * _q(step, tooth + lane))
                _line(paint, root, tip,
                      tuple(float(v) for v in PALETTE[(phase + 2) % len(PALETTE)]), 1)
                counts["locking_teeth"] += 1

            if (lane + step) % 3 == 0:
                rib_center = center - tangent * length * 0.12
                _line(paint, rib_center - normal * width * 0.34,
                      rib_center + normal * width * 0.34,
                      tuple(float(v) for v in PALETTE[(phase + 6) % len(PALETTE)]), 1)
                counts["compression_ribs"] += 1

            lip_a = center + tangent * length * 0.39 - normal * width * 0.36
            lip_b = center + tangent * length * 0.39 + normal * width * 0.31
            _line(paint, lip_a, lip_b,
                  tuple(float(v) for v in PALETTE[(phase + 1) % len(PALETTE)]), 1)
            counts["wear_lips"] += 1

            if (lane * 7 + step * 11) % 29 == 0:
                q0 = center - tangent * length * 0.08 - normal * width * 0.34
                q1 = center + tangent * length * 0.18 + normal * width * 0.30
                _line(paint, q0, q1, tuple(float(v) for v in PALETTE[13]), 2)
                counts["fracture_stops"] += 1

            previous = pos
            pos = pos + tangent * (length * 0.74)
            if pos[0] < -24 or pos[0] > WORK + 24 or pos[1] < -24 or pos[1] > WORK + 24:
                if step > 8:
                    break

    return np.clip(paint, 0.0, 1.0), counts


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    u8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "stag_kinematic_i1"
    output.mkdir(parents=True, exist_ok=True)
    paint, counts = build_paint()
    native = cv2.resize(paint, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    _write_rgb(output / f"{ID}_paint_2048.png", native)
    _write_rgb(output / f"{ID}_detail_1to1_1024.png", native[512:1536, 512:1536])
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-stag-kinematic-i1/1",
        "status": "REJECT-RAIL-CHAIN-MICROPLATES-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "causal_mark_counts": counts,
        "determinism": "analytic director plus low-discrepancy chain chronology; no RNG/noise/grain/grid",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
