# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Swallowtail Braid I1 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 59, 2026-08-25. Owner verdict being answered:
"EXACT SAME pattern just recolored" and "do NOT just put random noise in the
patterns." This isolated contact is a deterministic exchange-braid chronology:
paired costal streams open, swap neighbours, rejoin, shed tail forks, and carry
attached scale teeth, cross braces, swallow notches, vein ladders and edge
fringe. No RNG/noise, scalar contour field, cells, scatter, stamps, or shared
Wilds composer. Work-resolution 512 anatomy is 2-8 px (8-32 px at 2048).

Paint-only gate: do not add spec, register, package, or runtime-wire unless the
literal 2048 frame and 1:1 crop survive owner-eye review.
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


ID = "fmo_swallowtail"
WORK = 512

PALETTE_A = np.asarray([
    (5, 7, 15), (14, 17, 42), (18, 36, 82), (12, 72, 128),
    (9, 117, 165), (20, 163, 177), (62, 197, 162), (132, 218, 123),
    (210, 226, 89), (252, 199, 65), (252, 141, 60), (234, 78, 85),
    (185, 45, 122), (116, 35, 135), (51, 25, 97),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (6, 8, 17), (31, 16, 55), (74, 22, 100), (126, 31, 127),
    (180, 44, 131), (224, 70, 113), (250, 111, 82), (255, 164, 66),
    (236, 211, 77), (169, 222, 104), (92, 207, 137), (35, 174, 161),
    (13, 128, 159), (16, 78, 133), (22, 39, 89),
], np.float32) / 255.0


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


def _polyline(mask: np.ndarray, points: np.ndarray, value: float, width: int) -> None:
    cv2.polylines(mask, [np.rint(points).astype(np.int32)], False,
                  float(value), int(width), cv2.LINE_AA)


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    n = WORK
    primary = np.zeros((n, n), np.float32)
    underside = np.zeros_like(primary)
    fork = np.zeros_like(primary)
    brace = np.zeros_like(primary)
    teeth = np.zeros_like(primary)
    notch = np.zeros_like(primary)
    fringe = np.zeros_like(primary)
    vein = np.zeros_like(primary)
    identity = np.zeros_like(primary)

    # Eleven parents occupy the frame, but six unequal exchange windows destroy
    # a fixed row identity. Each path is analytic and deterministic.
    x = np.linspace(-24.0, n + 24.0, 760, dtype=np.float32)
    xn = x / n
    exchange_x = (0.105, 0.245, 0.395, 0.555, 0.715, 0.865)
    exchange_w = (0.047, 0.036, 0.052, 0.041, 0.057, 0.034)
    tracks: list[np.ndarray] = []
    for i in range(11):
        base = 18.0 + i * 47.2
        y = (base
             + (7.0 + (i % 4) * 2.1) * np.sin(2.0 * np.pi *
                 ((0.72 + 0.037 * i) * xn + 0.119 * i))
             + (3.2 + (i % 3)) * np.sin(2.0 * np.pi *
                 ((1.91 + 0.061 * i) * xn - 0.071 * i)))
        # Neighbour exchanges are signed S-shaped offsets, not random jitter.
        for j, (cx, cw) in enumerate(zip(exchange_x, exchange_w)):
            if i in {j % 10, j % 10 + 1, (j * 3 + 4) % 10, (j * 3 + 5) % 10}:
                sign = 1.0 if (i + j) % 2 == 0 else -1.0
                u = (xn - cx) / cw
                y += sign * (17.0 + 2.5 * (j % 3)) * np.exp(-0.5 * u * u) * np.tanh(1.8 * u)
        points = np.stack([x, y], axis=1)
        tracks.append(points)

        width = 7 + (i * 5) % 8
        _polyline(underside, points + np.asarray((0.0, 2.4), np.float32), 0.72, width + 5)
        _polyline(primary, points, 0.45 + 0.05 * (i % 6), width)
        _polyline(vein, points, 0.55 + 0.04 * (i % 7), 2 + (i % 2))
        _polyline(identity, points, (i + 1) / 12.0, width + 1)

        # Unequal local fork windows, with branches causally returning to the
        # same parent rather than becoming detached glyphs.
        starts = (62 + 19 * i, 221 + 11 * (i % 5), 365 - 7 * (i % 4))
        spans = (54 + 3 * (i % 4), 43 + 5 * ((i + 2) % 4), 58 - 2 * (i % 5))
        for k, (start, span) in enumerate(zip(starts, spans)):
            sel = (x >= start) & (x <= start + span)
            if not np.any(sel):
                continue
            local_x = x[sel]
            local_y = y[sel]
            u = (local_x - start) / span
            aperture = (5.0 + 1.4 * ((i + k) % 4)) * np.sin(np.pi * u) ** 1.35
            up = np.stack([local_x, local_y - aperture], axis=1)
            dn = np.stack([local_x, local_y + aperture], axis=1)
            _polyline(fork, up, 0.66 + 0.04 * ((i + k) % 5), 3 + ((i + k) % 3))
            _polyline(fork, dn, 0.48 + 0.05 * ((i + 2 * k) % 5), 2 + ((i + k + 1) % 3))
            # Cross-braces are anchored between the two live branch positions.
            for q in range(7 + (i + k) % 5, len(local_x) - 6, 11 + (i + 2 * k) % 5):
                p0 = (int(local_x[q]), int(local_y[q] - aperture[q]))
                p1 = (int(local_x[q]), int(local_y[q] + aperture[q]))
                cv2.line(brace, p0, p1, 0.58 + 0.06 * ((q + i) % 6), 2, cv2.LINE_AA)

        # Teeth, notches and fringe derive from path tangents and remain attached.
        stride = 17 + (i * 3) % 9
        for q in range(18 + (i * 7) % stride, len(points) - 18, stride):
            p = points[q]
            tangent = points[q + 3] - points[q - 3]
            tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            side = -1.0 if (q // stride + i) % 3 == 0 else 1.0
            length = 5.0 + float((q + 3 * i) % 5)
            half = 2.0 + float((q + i) % 3)
            root = p + side * normal * (4.0 + (i % 4))
            tri = np.asarray([root - tangent * half,
                              root + tangent * half,
                              root + side * normal * length], np.int32)
            cv2.fillConvexPoly(teeth, tri, 0.52 + 0.07 * ((q + i) % 6), cv2.LINE_AA)
            if (q // stride + 2 * i) % 7 == 0:
                tip = root - side * normal * (3.0 + (i % 3))
                cv2.line(notch, tuple(np.rint(root).astype(int)),
                         tuple(np.rint(tip).astype(int)), 0.72, 3, cv2.LINE_AA)
            if (q // stride + i) % 5 == 0:
                for s in (-1.0, 1.0):
                    tip = root + side * normal * (7.0 + (q % 4)) + tangent * s * 3.0
                    cv2.line(fringe, tuple(np.rint(root).astype(int)),
                             tuple(np.rint(tip).astype(int)),
                             0.44 + 0.08 * ((q + i) % 7), 2, cv2.LINE_AA)

    # Partner ties exist only where unequal trajectories approach; they express
    # the braid exchange rather than overlaying a generic mesh.
    for i in range(10):
        a, b = tracks[i], tracks[i + 1]
        dist = np.abs(a[:, 1] - b[:, 1])
        candidates = np.where(dist < 25.0 + 2.0 * (i % 3))[0]
        for q in candidates[::53 + 3 * (i % 4)]:
            p0 = tuple(np.rint(a[q]).astype(int))
            p1 = tuple(np.rint(b[q]).astype(int))
            cv2.line(brace, p0, p1, 0.45 + 0.05 * (i % 7), 2, cv2.LINE_AA)

    return {"primary": primary, "underside": underside, "fork": fork,
            "brace": brace, "teeth": teeth, "notch": notch,
            "fringe": fringe, "vein": vein, "identity": identity}


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> np.ndarray:
    f = _fields()
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    travel = (0.17 * xx / WORK + 0.23 * yy / WORK
              + 0.91 * f["identity"] + 0.36 * f["fork"]
              + 0.29 * f["teeth"] - 0.22 * f["notch"]
              + 0.18 * f["brace"] + 0.14 * f["fringe"])
    if angle_b:
        travel = (1.0 - travel + 0.47 * f["underside"]
                  - 0.31 * f["primary"] + 0.24 * f["brace"])
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)
    body = np.clip(0.10 + 0.70 * f["underside"] + 0.78 * f["primary"], 0.0, 1.0)
    relief = (0.22 + 0.50 * body + 0.46 * f["fork"] + 0.39 * f["teeth"]
              + 0.34 * f["brace"] + 0.28 * f["fringe"]
              + 0.37 * f["vein"] - 0.31 * f["notch"])
    rgb *= np.clip(relief, 0.07, 1.27)[..., None]
    rgb += np.asarray((0.11, 0.28, 0.38) if not angle_b else (0.34, 0.10, 0.29), np.float32) * f["fork"][..., None]
    rgb += np.asarray((0.38, 0.26, 0.05) if not angle_b else (0.07, 0.31, 0.29), np.float32) * f["teeth"][..., None]
    rgb += np.asarray((0.26, 0.07, 0.35) if not angle_b else (0.37, 0.22, 0.04), np.float32) * f["fringe"][..., None]
    return cv2.resize(np.clip(rgb, 0.0, 1.0).astype(np.float32),
                      (2048, 2048), interpolation=cv2.INTER_LANCZOS4)


def clear_cache() -> None:
    _paint.cache_clear(); _fields.cache_clear()


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
        cv2.imwrite(str(out_dir / f"{ID}_{suffix}_2048.png"),
                    cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out_dir / f"{ID}_crop_1to1.png"),
                cv2.cvtColor(np.clip(a[512:1280, 640:1408] * 255.0, 0, 255).astype(np.uint8),
                             cv2.COLOR_RGB2BGR))
    report = {"id": ID, "status": "NATIVE-2048-PAINT-CONTACT-NO-SPEC-NOT-WIRED",
              "timings_s": timings, "deterministic": len(set(digests)) == 1,
              "digest": digests[0], "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, 0.95))}
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" /
                                     "swallowtail_braid_i1"), indent=2))
