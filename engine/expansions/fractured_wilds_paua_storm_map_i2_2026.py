# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Paua Storm Map I2 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 62, 2026-08-25. I1's cyclic-state macro
territories are frozen. I2 advects fifteen authored mineral bands through seven
unequal area-preserving standard-map folds. Continuous band transport produces
fine nacre filaments; Jacobian stretch, fold curvature, trapped islands, fold
collisions and healed wakes are causal observables of that same transport. No
RNG/noise, placed marks, contour overlay, cells, stamps, or shared Wilds
composer. Work resolution 512 targets 8-32 px native filament anatomy.

Paint-only gate: no spec/registry/package/runtime work unless literal 2048 and
the 1:1 crop survive owner-eye review.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_paua_storm"
WORK = 512
TAU = np.float32(2.0 * np.pi)

PALETTE_A = np.asarray([
    (3, 8, 18), (8, 27, 59), (6, 58, 104), (2, 96, 139),
    (4, 137, 151), (20, 174, 146), (62, 202, 127), (124, 220, 102),
    (193, 229, 80), (241, 207, 67), (255, 158, 70), (247, 103, 91),
    (217, 62, 126), (158, 39, 145), (86, 28, 125),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 7, 17), (28, 15, 55), (69, 21, 100), (119, 30, 130),
    (174, 44, 137), (220, 67, 119), (248, 107, 88), (255, 158, 66),
    (241, 207, 65), (185, 225, 80), (113, 219, 108), (52, 196, 140),
    (16, 158, 158), (6, 111, 153), (14, 62, 116),
], np.float32) / 255.0


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(np.quantile(a, 0.01)), float(np.quantile(a, 0.99))
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


def _wrapped_delta(a: np.ndarray, axis: int) -> np.ndarray:
    d = np.roll(a, -1, axis=axis) - np.roll(a, 1, axis=axis)
    return (np.mod(d + 0.5, 1.0) - 0.5) * 0.5


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    n = WORK
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n
    p = (yy + 0.5) / n
    x0, p0 = x.copy(), p.copy()

    # Inverse unequal standard-map chronology. Each pass is area-preserving;
    # there is no sampled displacement texture hiding underneath the folds.
    strengths = (0.84, -0.57, 0.71, -0.46, 0.63, -0.39, 0.52)
    offsets = (0.03, 0.19, 0.41, 0.08, 0.32, 0.57, 0.23)
    for k, off in zip(strengths, offsets):
        p0 = np.mod(p0 - np.float32(k / (2.0 * np.pi)) *
                    np.sin(TAU * (x0 + np.float32(off))), 1.0)
        x0 = np.mod(x0 - p0 - np.float32(0.071 * off), 1.0)
        # Unequal orthogonal fold makes no pass a simple repetition/rotation.
        x0 = np.mod(x0 - np.float32(0.19 * k / (2.0 * np.pi)) *
                    np.sin(TAU * (p0 * np.float32(1.0 + 0.13 * off))), 1.0)

    dx_x = _wrapped_delta(x0, 1) * n
    dx_y = _wrapped_delta(x0, 0) * n
    dp_x = _wrapped_delta(p0, 1) * n
    dp_y = _wrapped_delta(p0, 0) * n
    stretch = _norm(np.sqrt(dx_x * dx_x + dx_y * dx_y +
                            dp_x * dp_x + dp_y * dp_y))
    det = dx_x * dp_y - dx_y * dp_x
    compression = _norm(np.abs(det - np.median(det)))
    lap_x = cv2.Laplacian(x0.astype(np.float32), cv2.CV_32F, ksize=3)
    lap_p = cv2.Laplacian(p0.astype(np.float32), cv2.CV_32F, ksize=3)
    fold = _norm(np.abs(lap_x) + 0.73 * np.abs(lap_p))
    band_phase = np.mod(15.0 * x0, 1.0)
    seam = np.exp(-np.minimum(band_phase, 1.0 - band_phase) / 0.055).astype(np.float32)
    island = np.clip((0.34 - stretch) / 0.34, 0.0, 1.0)
    collision = _norm(fold * (0.25 + 0.75 * compression))
    healed = _norm(cv2.GaussianBlur(seam, (0, 0), 2.2) * (1.0 - seam) * stretch)
    wake = _norm(np.abs(_wrapped_delta(stretch, 1)) + np.abs(_wrapped_delta(stretch, 0)))
    return {"x0": x0, "p0": p0, "stretch": stretch,
            "compression": compression, "fold": fold, "seam": seam,
            "island": island, "collision": collision,
            "healed": healed, "wake": wake}


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> np.ndarray:
    f = _fields()
    travel = (f["x0"] + 0.13 * f["p0"] + 0.09 * f["stretch"]
              + 0.07 * f["collision"] - 0.05 * f["island"])
    if angle_b:
        travel = (1.0 - f["x0"] + 0.37 * f["p0"]
                  - 0.18 * f["stretch"] + 0.14 * f["healed"])
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)
    relief = (0.31 + 0.38 * f["stretch"] + 0.42 * f["seam"]
              + 0.34 * f["fold"] + 0.40 * f["collision"]
              + 0.28 * f["healed"] + 0.24 * f["wake"]
              - 0.19 * f["island"])
    rgb *= np.clip(relief, 0.08, 1.28)[..., None]
    rgb += np.asarray((0.05, 0.31, 0.37) if not angle_b else (0.36, 0.07, 0.29), np.float32) * f["seam"][..., None]
    rgb += np.asarray((0.39, 0.23, 0.04) if not angle_b else (0.05, 0.32, 0.30), np.float32) * f["collision"][..., None]
    rgb += np.asarray((0.26, 0.06, 0.34) if not angle_b else (0.38, 0.24, 0.04), np.float32) * f["healed"][..., None]
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
                                     "paua_storm_map_i2"), indent=2))
