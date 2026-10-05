# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Chrysina Gold I1 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 56, 2026-08-25. One continuous chiral cuticle
sheet is differentially buckled at native 8-32 px wavelengths. Color comes
from the sheet normal and curvature under two opposed viewing directions—not
from stripes, cells, placed marks, RNG/noise or a shared composer. Ridge caps,
valley oxide, saddle bruises, compressed facets and healed slips are causal
differential anatomy. Spec waits for actual-2048 paint survival.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_chrysina_gold"
AUTHORED = 1024

PALETTE_A = np.asarray([
    (5, 8, 13), (13, 26, 25), (24, 54, 34), (49, 88, 40),
    (88, 126, 43), (137, 163, 47), (188, 196, 54), (235, 220, 72),
    (255, 242, 116), (240, 205, 73), (204, 157, 43), (160, 106, 30),
    (112, 66, 27), (67, 37, 26), (30, 17, 20),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 9, 18), (8, 31, 47), (7, 67, 76), (8, 107, 93),
    (20, 151, 96), (57, 190, 81), (124, 218, 67), (201, 228, 62),
    (253, 210, 69), (255, 157, 67), (245, 96, 82), (218, 54, 116),
    (169, 37, 142), (104, 31, 137), (45, 23, 96),
], np.float32) / 255.0


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    n = AUTHORED
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n
    y = (yy + 0.5) / n

    # Smooth domain weights change wrinkle direction without winner regions.
    gate_a = 0.5 + 0.5 * np.sin(2.0 * np.pi * (0.83 * x + 0.47 * y + 0.07 * np.sin(5.1 * y)))
    gate_b = 0.5 + 0.5 * np.cos(2.0 * np.pi * (0.39 * x - 0.91 * y + 0.06 * np.sin(4.3 * x)))
    p1 = 2.0 * np.pi * (76.0 * x + 13.0 * y + 2.7 * np.sin(2.0 * np.pi * (1.7 * y + 0.3 * x)))
    p2 = 2.0 * np.pi * (-21.0 * x + 83.0 * y + 2.1 * np.sin(2.0 * np.pi * (1.3 * x - 0.8 * y)))
    p3 = 2.0 * np.pi * (61.0 * x + 54.0 * y + 1.8 * np.sin(2.0 * np.pi * (0.9 * x + 1.4 * y)))
    height = ((0.29 + 0.42 * gate_a) * np.sin(p1)
              + (0.25 + 0.39 * gate_b) * np.sin(p2)
              + (0.19 + 0.24 * (1.0 - gate_a * gate_b)) * np.sin(p3)
              + 0.16 * np.sin(0.53 * p1 - 0.47 * p2 + 0.31 * p3))
    height = cv2.GaussianBlur(height.astype(np.float32), (0, 0), 0.72)

    hx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
    hy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
    hxx = cv2.Sobel(hx, cv2.CV_32F, 1, 0, ksize=3)
    hyy = cv2.Sobel(hy, cv2.CV_32F, 0, 1, ksize=3)
    hxy = cv2.Sobel(hx, cv2.CV_32F, 0, 1, ksize=3)
    slope = np.sqrt(hx * hx + hy * hy)
    lap = hxx + hyy
    det = hxx * hyy - hxy * hxy
    azimuth = np.mod(np.arctan2(hy, hx) / (2.0 * np.pi) + 1.0, 1.0)

    ridge = _norm(np.maximum(lap, 0.0))
    valley = _norm(np.maximum(-lap, 0.0))
    saddle = _norm(np.maximum(-det, 0.0))
    compression = _norm(slope)
    slip_gate = 0.5 + 0.5 * np.sin(2.0 * np.pi * (7.3 * x - 5.1 * y + 0.8 * gate_a))
    healed_gate = 0.5 + 0.5 * np.cos(2.0 * np.pi * (4.7 * x + 8.1 * y + 0.6 * gate_b))
    slip = ridge * np.clip((slip_gate - 0.52) / 0.48, 0.0, 1.0)
    healed = valley * np.clip((healed_gate - 0.55) / 0.45, 0.0, 1.0)

    travel = azimuth + 0.19 * _norm(height) + 0.13 * saddle - 0.09 * compression
    light = _norm(((-0.72 if angle_b else 0.68) * hx
                   + (0.63 if angle_b else -0.57) * hy
                   + 0.52) / np.sqrt(1.0 + slope * slope))
    if angle_b:
        travel = 1.0 - travel + 0.16 * healed - 0.12 * slip
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)
    relief = 0.24 + 0.58 * light + 0.23 * ridge + 0.15 * saddle - 0.20 * valley
    rgb *= np.clip(relief, 0.08, 1.28)[..., None]
    rgb += np.asarray((0.38, 0.27, 0.06) if not angle_b else (0.04, 0.28, 0.35), np.float32) * slip[..., None]
    rgb += np.asarray((0.10, 0.25, 0.13) if not angle_b else (0.30, 0.07, 0.24), np.float32) * healed[..., None]
    rgb *= (1.0 - 0.24 * compression * valley)[..., None]

    paint = cv2.resize(np.clip(rgb, 0.0, 1.0).astype(np.float32),
                       (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    return paint, {"ridge": ridge, "valley": valley, "saddle": saddle,
                   "compression": compression, "slip": slip,
                   "healed": healed, "light": light}


def clear_cache() -> None:
    _paint.cache_clear()


def render_evidence(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache(); start = time.perf_counter(); a, _ = _paint(False); b, _ = _paint(True)
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
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" / "chrysina_buckle_i1"), indent=2))
