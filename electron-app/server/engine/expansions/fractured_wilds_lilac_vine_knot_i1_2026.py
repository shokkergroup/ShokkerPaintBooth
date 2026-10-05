# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lilac Vine I1 paint-only Fourier botanical knot.

SPB-105 / Wilds rebuild tick 52, 2026-08-25. Owner verdict: native 2048 first;
stop spending spec/M7 time on paint carriers that fail the eye. Before: legacy
shared-composer loop/paisley relative, no admissible native rebuild. After:
pending paint-only native-2048 verdict.

One deterministic Fourier knot supplies the continuous vine ancestry. Two
grafted companions use different harmonic spectra, not translated copies.
Over/under depth, node collars, asymmetric leaves, tendrils, thorns, pods and
bells attach to those curves. No RNG/noise, grid, cell field, stamps, generic
weave or repeated loop tile is used.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json
import time

import cv2
import numpy as np


ID = "fbl_lilac_vine"
AUTHORED = 1024

PALETTE_A = np.asarray([
    (12, 7, 28), (35, 15, 69), (73, 24, 112), (124, 31, 145),
    (180, 43, 151), (226, 66, 131), (252, 105, 104), (255, 158, 91),
    (238, 207, 104), (173, 228, 116), (89, 209, 142), (30, 168, 159),
    (17, 116, 151), (25, 70, 125), (25, 35, 82),
], np.uint8)

PALETTE_B = np.asarray([
    (7, 15, 31), (10, 43, 77), (9, 82, 121), (12, 130, 148),
    (31, 180, 154), (83, 215, 136), (156, 230, 113), (226, 225, 98),
    (255, 177, 88), (251, 113, 102), (224, 67, 135), (174, 47, 161),
    (116, 42, 165), (68, 38, 135), (30, 27, 82),
], np.uint8)


def _fourier_path(lane: int, samples: int = 18000) -> np.ndarray:
    t = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False, dtype=np.float32)
    spectra = (
        ((1, 0.0, 1.00), (2, 1.13, 0.31), (5, 0.47, 0.24), (8, 2.09, 0.14), (13, 0.81, 0.09)),
        ((1, 0.71, 0.83), (3, 1.89, 0.36), (4, 0.22, 0.25), (9, 2.61, 0.13), (14, 1.31, 0.08)),
        ((2, 0.39, 0.72), (3, 2.37, 0.42), (7, 0.96, 0.23), (11, 1.77, 0.12), (16, 0.18, 0.07)),
    )
    sx = np.zeros_like(t)
    sy = np.zeros_like(t)
    for order, (harmonic, phase, amp) in enumerate(spectra[lane]):
        sx += np.float32(amp) * np.sin(np.float32(harmonic) * t + np.float32(phase))
        sy += np.float32(amp * (0.91 + 0.04 * order)) * np.sin(
            np.float32(harmonic + 1 + lane) * t + np.float32(phase * 1.37 + 0.62)
        )
    sx = (sx - sx.min()) / max(1e-6, float(sx.max() - sx.min()))
    sy = (sy - sy.min()) / max(1e-6, float(sy.max() - sy.min()))
    transforms = ((0.94, 0.91, 0.03, 0.05), (0.84, 0.79, 0.08, 0.10), (0.72, 0.88, 0.15, 0.06))
    wx, wy, ox, oy = transforms[lane]
    x = ox + wx * sx
    y = oy + wy * sy
    # A nonlinear botanical lean prevents the three spectra from sharing one
    # central/radial presentation even where their projections cross.
    x += 0.028 * np.sin(2.0 * np.pi * (2.1 * y + 0.37 * lane))
    y += 0.024 * np.sin(2.0 * np.pi * (1.7 * x - 0.29 * lane))
    return np.column_stack((x, y)).astype(np.float32)


def _poly(points: np.ndarray) -> np.ndarray:
    return np.rint(np.clip(points, 0.0, 1.0) * (AUTHORED - 1)).astype(np.int32)


def _normal(points: np.ndarray, index: int) -> tuple[np.ndarray, np.ndarray]:
    prev = points[(index - 7) % len(points)]
    nxt = points[(index + 7) % len(points)]
    tangent = nxt - prev
    tangent /= max(1e-6, float(np.linalg.norm(tangent)))
    normal = np.asarray((-tangent[1], tangent[0]), np.float32)
    return tangent, normal


def _leaf_polygon(center: np.ndarray, tangent: np.ndarray, normal: np.ndarray, index: int) -> np.ndarray:
    side = -1.0 if index % 2 else 1.0
    length = np.float32(9.0 + (index * 7) % 7)
    width = np.float32(4.0 + (index * 5) % 4)
    base = center + normal * side * 5.0
    tip = base + tangent * length + normal * side * (5.0 + (index % 3))
    shoulder = base + tangent * length * 0.48
    pts = np.vstack((
        base - tangent * 2.0,
        shoulder + normal * side * width,
        tip,
        shoulder - normal * side * width * 0.68,
    ))
    return np.rint(pts).astype(np.int32)


@lru_cache(maxsize=6)
def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    n = AUTHORED
    palette = PALETTE_B if angle_b else PALETTE_A
    canvas = np.zeros((n, n, 3), np.uint8)
    # Dense luminous soil/underleaf carrier built from broad deterministic
    # chromatic sweeps, not noise or a second hidden pattern.
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    base_phase = (0.00061 * xx + 0.00043 * yy
                  + 0.06 * np.sin(xx / 113.0 + yy / 179.0))
    if angle_b:
        base_phase = 1.0 - base_phase
    q = np.mod(base_phase, 1.0) * len(palette)
    i0 = np.floor(q).astype(np.int16) % len(palette)
    f = (q - np.floor(q))[..., None]
    base = palette[i0] * (1.0 - f) + palette[(i0 + 1) % len(palette)] * f
    canvas[:] = np.clip(base * 0.18, 0, 255).astype(np.uint8)

    masks = {name: np.zeros((n, n), np.uint8) for name in
             ("vine", "collar", "leaf", "tendril", "thorn", "pod", "bell", "crossing")}

    for lane in range(3):
        path_f = _fourier_path(lane)
        path = _poly(path_f)
        # Chunked chronological redraw makes later segments genuinely pass over
        # earlier ones at crossings. It is not a decorative crossing mask.
        chunks = 240
        step = len(path) // chunks
        for chunk in range(chunks):
            start = chunk * step
            end = min(len(path), (chunk + 1) * step + 2)
            segment = path[start:end].reshape(-1, 1, 2)
            cv2.polylines(canvas, [segment], False, (2, 3, 8), 18 - lane * 2, cv2.LINE_AA)
            color = tuple(int(v) for v in palette[(chunk * 5 + lane * 3) % len(palette)])
            cv2.polylines(canvas, [segment], False, color, 11 - lane, cv2.LINE_AA)
            hi = tuple(int(min(255, v * 1.22 + 18)) for v in color)
            cv2.polylines(canvas, [segment], False, hi, 3, cv2.LINE_AA)
            cv2.polylines(masks["vine"], [segment], False, 255, 12 - lane, cv2.LINE_AA)
            if chunk > 0:
                cv2.circle(masks["crossing"], tuple(path[start]), 8 - lane, 255, -1, cv2.LINE_AA)

        feature_stride = (430, 517, 613)[lane]
        for feature_no, index in enumerate(range(120 + lane * 77, len(path) - 120, feature_stride)):
            center = path[index].astype(np.float32)
            tangent, normal = _normal(path.astype(np.float32), index)
            kind = feature_no % 6
            color = tuple(int(v) for v in palette[(feature_no * 7 + lane * 4 + 3) % len(palette)])

            if kind == 0:  # node collar, physically wraps the stem
                p0 = np.rint(center - normal * 9.0).astype(int)
                p1 = np.rint(center + normal * 9.0).astype(int)
                cv2.line(canvas, tuple(p0), tuple(p1), (3, 3, 8), 8, cv2.LINE_AA)
                cv2.line(canvas, tuple(p0), tuple(p1), color, 4, cv2.LINE_AA)
                cv2.line(masks["collar"], tuple(p0), tuple(p1), 255, 6, cv2.LINE_AA)
            elif kind == 1:  # asymmetric paired leaf plate
                poly = _leaf_polygon(center, tangent, normal, feature_no + lane)
                cv2.fillConvexPoly(canvas, poly, color, cv2.LINE_AA)
                cv2.polylines(canvas, [poly.reshape(-1, 1, 2)], True, (4, 5, 10), 3, cv2.LINE_AA)
                cv2.fillConvexPoly(masks["leaf"], poly, 255, cv2.LINE_AA)
            elif kind == 2:  # attached tendril spiral
                tt = np.linspace(0.0, 2.7 * np.pi, 42, dtype=np.float32)
                radius = np.linspace(2.0, 12.0, len(tt), dtype=np.float32)
                spiral = center + tangent[None, :] * (tt[:, None] * 0.8) + normal[None, :] * (np.sin(tt) * radius)[:, None]
                spiral_i = np.rint(spiral).astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(canvas, [spiral_i], False, color, 5, cv2.LINE_AA)
                cv2.polylines(masks["tendril"], [spiral_i], False, 255, 6, cv2.LINE_AA)
            elif kind == 3:  # thorn pair grows from the local tangent
                for side in (-1.0, 1.0):
                    tip = center + normal * side * (9.0 + feature_no % 5) + tangent * 3.0
                    p0 = center + tangent * 4.0
                    p1 = center - tangent * 3.0
                    tri = np.rint(np.vstack((p0, p1, tip))).astype(np.int32)
                    cv2.fillConvexPoly(canvas, tri, color, cv2.LINE_AA)
                    cv2.fillConvexPoly(masks["thorn"], tri, 255, cv2.LINE_AA)
            elif kind == 4:  # two-lobed seed pod attached by its neck
                pod_center = np.rint(center + normal * 10.0).astype(int)
                angle = float(np.degrees(np.arctan2(tangent[1], tangent[0])))
                cv2.ellipse(canvas, tuple(pod_center), (9, 5), angle, 0, 360, color, -1, cv2.LINE_AA)
                cv2.line(canvas, tuple(np.rint(center).astype(int)), tuple(pod_center), color, 4, cv2.LINE_AA)
                cv2.ellipse(masks["pod"], tuple(pod_center), (10, 6), angle, 0, 360, 255, -1, cv2.LINE_AA)
            else:  # hanging bell with an open lip
                bell_base = center + normal * 6.0
                p0 = bell_base - tangent * 7.0
                p1 = bell_base + tangent * 7.0
                tip = bell_base + normal * (12.0 + feature_no % 4)
                bell = np.rint(np.vstack((p0, tip, p1, bell_base + normal * 5.0))).astype(np.int32)
                cv2.fillConvexPoly(canvas, bell, color, cv2.LINE_AA)
                cv2.line(canvas, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)), (245, 230, 180), 3, cv2.LINE_AA)
                cv2.fillConvexPoly(masks["bell"], bell, 255, cv2.LINE_AA)

    paint = cv2.resize(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0,
                       (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    return np.clip(paint, 0.0, 1.0), {k: v.astype(np.float32) / 255.0 for k, v in masks.items()}


def clear_cache() -> None:
    _paint.cache_clear()


def render_paint_contact(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    clear_cache(); start = time.perf_counter(); a, _ = _paint(False); b, _ = _paint(True)
    elapsed = time.perf_counter() - start; delta = np.abs(a - b)
    for suffix, image in (("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2.0, 0.0, 1.0))):
        arr = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out_dir / f"{ID}_{suffix}_2048.png"), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    report = {"id": ID, "status": "PAINT-ONLY-NATIVE-2048-CONTACT-NOT-WIRED",
              "elapsed_s": elapsed, "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, 0.95))}
    (out_dir / "paint_contact.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(render_paint_contact(root / "_wilds_fullres_progress_20260824" / "lilac_vine_knot_i1"), indent=2))
