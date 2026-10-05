# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Sunbird Throat I1 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 55, 2026-08-25. This is an explicit fine-mark
plume, not another scalar contour sheet: 10,800 deterministic marks ride one
continuous throat-flow chronology. Five separate mark anatomies (barb, fork,
crescent, platelet and broken glint) vary in length, bend, color and shade at
8-32 px native scale. No RNG/noise/shared composer; spec waits for owner-eye
survival at the actual 2048 canvas.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math
import time

import cv2
import numpy as np


ID = "fmo_sunbird_throat"
AUTHORED = 1024

PALETTE_A = np.asarray([
    (4, 9, 18), (7, 28, 48), (5, 62, 77), (5, 102, 96),
    (14, 148, 102), (51, 190, 89), (117, 219, 75), (195, 231, 66),
    (252, 207, 55), (255, 150, 45), (250, 92, 55), (226, 48, 87),
    (180, 31, 127), (115, 28, 145), (48, 23, 104),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (8, 4, 23), (29, 7, 54), (65, 8, 83), (111, 12, 101),
    (163, 25, 103), (212, 47, 87), (246, 82, 64), (255, 127, 48),
    (255, 181, 44), (238, 222, 66), (160, 226, 83), (74, 197, 106),
    (23, 151, 124), (15, 96, 128), (24, 48, 104),
], np.float32) / 255.0


def _color(t: float, palette: np.ndarray) -> tuple[int, int, int]:
    q = (t % 1.0) * len(palette)
    i = int(math.floor(q)) % len(palette)
    f = q - math.floor(q)
    rgb = palette[i] * (1.0 - f) + palette[(i + 1) % len(palette)] * f
    return tuple(int(v) for v in np.clip(rgb * 255.0, 0, 255))


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> np.ndarray:
    n = AUTHORED
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n
    y = (yy + 0.5) / n
    flow = (0.57 * x + 0.31 * y
            + 0.095 * np.sin(2.0 * np.pi * (1.7 * x - 0.8 * y))
            + 0.047 * np.sin(2.0 * np.pi * (3.1 * y + 0.6 * x)))
    relief = (0.22 + 0.18 * (0.5 + 0.5 * np.sin(2.0 * np.pi * (5.3 * flow + y)))
              + 0.12 * (0.5 + 0.5 * np.cos(2.0 * np.pi * (8.1 * x - 3.7 * y))))
    base = np.empty((n, n, 3), np.float32)
    palette = PALETTE_B if angle_b else PALETTE_A
    q = np.mod((1.0 - flow if angle_b else flow), 1.0) * len(palette)
    i0 = np.floor(q).astype(np.int16) % len(palette)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    base[:] = palette[i0] * (1.0 - f) + palette[(i0 + 1) % len(palette)] * f
    base *= relief[..., None]
    canvas = np.clip(base * 255.0, 0, 255).astype(np.uint8)

    # Deterministic continuous plume coordinates. Marks remain discrete and
    # short; the source streamlines are never drawn as rails.
    rows, cols = 120, 90
    for i in range(rows):
        v = (i + 0.5) / rows
        phase = 0.37 * i + 0.19 * math.sin(i * 0.61)
        for j in range(cols):
            u = (j + 0.5) / cols
            pxn = u + 0.028 * math.sin(2.0 * math.pi * (1.8 * v + 0.7 * u))
            pyn = (v + 0.070 * math.sin(2.0 * math.pi * (0.63 * u + 1.9 * v))
                   + 0.026 * math.sin(2.0 * math.pi * (2.7 * u - 0.8 * v)))
            px, py = int(pxn * n), int(pyn * n)
            if px < 8 or px >= n - 8 or py < 8 or py >= n - 8:
                continue
            slope = (0.070 * 2.0 * math.pi * 0.63 * math.cos(2.0 * math.pi * (0.63 * u + 1.9 * v))
                     + 0.026 * 2.0 * math.pi * 2.7 * math.cos(2.0 * math.pi * (2.7 * u - 0.8 * v)))
            angle = math.atan2(slope, 1.0) + 0.18 * math.sin(phase + j * 0.23)
            length = 4.2 + 7.4 * (0.5 + 0.5 * math.sin(i * 0.73 + j * 1.17))
            width = 1 + ((i * 3 + j * 5) % 3)
            dx, dy = math.cos(angle), math.sin(angle)
            travel = 0.61 * u + 0.39 * v + 0.12 * math.sin(phase + j * 0.31)
            if angle_b:
                travel = 1.0 - travel + 0.16 * math.sin(i * 0.17 - j * 0.29)
            color = _color(travel, palette)
            shade = 0.48 + 0.52 * (0.5 + 0.5 * math.sin(i * 1.13 + j * 0.83))
            c = tuple(int(ch * shade) for ch in color)
            bright = tuple(min(255, int(ch * 1.28 + 12)) for ch in color)
            kind = (i * 7 + j * 11) % 5
            p0 = (int(px - dx * length * 0.5), int(py - dy * length * 0.5))
            p1 = (int(px + dx * length * 0.5), int(py + dy * length * 0.5))
            if kind == 0:  # tapered barb
                cv2.line(canvas, p0, p1, c, width, cv2.LINE_AA)
                cv2.circle(canvas, p1, 1, bright, -1, cv2.LINE_AA)
            elif kind == 1:  # split fork
                cv2.line(canvas, p0, (px, py), c, width, cv2.LINE_AA)
                for turn in (-0.52, 0.52):
                    ax, ay = math.cos(angle + turn), math.sin(angle + turn)
                    cv2.line(canvas, (px, py), (int(px + ax * length * 0.55), int(py + ay * length * 0.55)), bright, 1, cv2.LINE_AA)
            elif kind == 2:  # unequal crescent
                axes = (max(2, int(length * 0.55)), max(1, int(length * 0.24)))
                cv2.ellipse(canvas, (px, py), axes, math.degrees(angle), 18, 238, c, width, cv2.LINE_AA)
            elif kind == 3:  # skew platelet
                nx, ny = -dy, dx
                pts = np.asarray([
                    (px - dx * length * 0.55, py - dy * length * 0.55),
                    (px + dx * length * 0.38 + nx * width, py + dy * length * 0.38 + ny * width),
                    (px + dx * length * 0.55 - nx * width, py + dy * length * 0.55 - ny * width),
                    (px - dx * length * 0.35 - nx * width, py - dy * length * 0.35 - ny * width),
                ], np.int32)
                cv2.fillConvexPoly(canvas, pts, c, cv2.LINE_AA)
                cv2.line(canvas, p0, p1, bright, 1, cv2.LINE_AA)
            else:  # broken glint
                gap = length * 0.13
                cv2.line(canvas, p0, (int(px - dx * gap), int(py - dy * gap)), c, width, cv2.LINE_AA)
                cv2.line(canvas, (int(px + dx * gap), int(py + dy * gap)), p1, bright, 1, cv2.LINE_AA)

    return cv2.resize(canvas.astype(np.float32) / 255.0, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)


def clear_cache() -> None:
    _paint.cache_clear()


def render_evidence(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache(); start = time.perf_counter(); a = _paint(False); b = _paint(True)
        timings.append(time.perf_counter() - start)
        blob = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes()
        digests.append(hashlib.sha256(blob).hexdigest()); last = a, b
    a, b = last; delta = np.abs(a - b)
    for suffix, image in (("paint", a), ("angle_a", a), ("angle_b", b),
                          ("angle_delta_x2", np.clip(delta * 2.0, 0.0, 1.0))):
        arr = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out_dir / f"{ID}_{suffix}_2048.png"), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out_dir / f"{ID}_crop_1to1.png"),
                cv2.cvtColor(np.clip(a[512:1280, 640:1408] * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    report = {"id": ID, "status": "NATIVE-2048-PAINT-CONTACT-NO-SPEC-NOT-WIRED",
              "timings_s": timings, "deterministic": len(set(digests)) == 1,
              "digest": digests[0], "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, 0.95))}
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" / "sunbird_plume_i1"), indent=2))
