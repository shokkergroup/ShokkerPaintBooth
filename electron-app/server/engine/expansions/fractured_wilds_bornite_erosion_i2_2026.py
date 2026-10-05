# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Bornite Patina I2 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 57, 2026-08-25. I1's macro Newton basins are
frozen. I2 is a deterministic electrochemical erosion chronology: analytic ore
relief routes repeated rainfall downhill for 72 transport steps, producing
connected sulfide channels, oxide banks, dry ridges, deposition fans and healed
terraces. No RNG/noise, contours, stamps, cells, placed marks or shared Wilds
composer. Work resolution 512 gives 8-32 px native anatomy after 2048 upscale.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_bornite_patina"
WORK = 512

PALETTE_A = np.asarray([
    (5, 7, 11), (19, 17, 27), (42, 20, 45), (72, 24, 71),
    (107, 29, 94), (145, 38, 111), (185, 53, 111), (220, 77, 91),
    (244, 112, 62), (248, 158, 48), (225, 201, 55), (149, 206, 76),
    (68, 178, 99), (22, 125, 112), (16, 71, 103),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 8, 18), (8, 28, 54), (8, 61, 91), (8, 101, 117),
    (15, 144, 121), (47, 181, 99), (105, 207, 79), (177, 220, 66),
    (236, 211, 62), (255, 169, 62), (251, 112, 76), (225, 65, 109),
    (177, 41, 138), (113, 32, 139), (52, 25, 103),
], np.float32) / 255.0

OFFSETS = ((-1, -1), (-1, 0), (-1, 1), (0, -1),
           (0, 1), (1, -1), (1, 0), (1, 1))


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.roll(np.roll(a, dy, axis=0), dx, axis=1)
    if dy < 0: out[dy:, :] = out[dy - 1:dy, :]
    elif dy > 0: out[:dy, :] = out[dy:dy + 1, :]
    if dx < 0: out[:, dx:] = out[:, dx - 1:dx]
    elif dx > 0: out[:, :dx] = out[:, dx:dx + 1]
    return out


@lru_cache(maxsize=2)
def _fields() -> dict[str, np.ndarray]:
    n = WORK
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n
    y = (yy + 0.5) / n
    height = (0.46
              + 0.18 * np.sin(2.0 * np.pi * (3.1 * x + 1.7 * y))
              + 0.14 * np.cos(2.0 * np.pi * (2.3 * x - 4.1 * y))
              + 0.11 * np.sin(2.0 * np.pi * (7.1 * x + 5.3 * y))
              + 0.08 * np.cos(2.0 * np.pi * (11.3 * x - 8.7 * y))
              + 0.05 * np.sin(2.0 * np.pi * (17.9 * x + 13.1 * y)))
    height = cv2.GaussianBlur(height.astype(np.float32), (0, 0), 1.1)

    # Route by positive downhill slope. Direction weights are fixed by the ore
    # surface; iterative transport accumulates chronology without random rain.
    drops = []
    for dy, dx in OFFSETS:
        neighbour = _shift(height, -dy, -dx)
        distance = 1.41421356 if dy and dx else 1.0
        drops.append(np.maximum((height - neighbour) / distance, 0.0))
    drop = np.stack(drops, axis=0).astype(np.float32)
    total = drop.sum(axis=0) + 1e-6
    weight = drop / total[None, ...]
    rainfall = (0.65 + 0.35 * (0.5 + 0.5 * np.sin(
        2.0 * np.pi * (5.7 * x - 3.3 * y + 0.18 * np.sin(6.1 * y)))))
    flux = rainfall.astype(np.float32)
    for _ in range(72):
        routed = np.zeros_like(flux)
        for k, (dy, dx) in enumerate(OFFSETS):
            routed += _shift(flux * weight[k], dy, dx)
        flux = rainfall + 0.82 * routed
        flux = np.minimum(flux, 36.0)

    accumulation = _norm(np.log1p(flux))
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
    slope = _norm(np.sqrt(gx * gx + gy * gy))
    lap = cv2.Laplacian(height, cv2.CV_32F, ksize=3)
    channel = _norm(accumulation * (0.28 + 0.72 * slope))
    broad = cv2.GaussianBlur(channel, (0, 0), 3.2)
    oxide_bank = _norm(np.maximum(broad - 0.63 * channel, 0.0))
    dry_ridge = _norm(np.maximum(lap, 0.0) * (1.0 - accumulation))
    deposition = _norm(np.maximum(channel - cv2.GaussianBlur(channel, (0, 0), 1.1), 0.0))
    healed = _norm(np.maximum(-lap, 0.0) * oxide_bank)
    return {"height": _norm(height), "accumulation": accumulation,
            "channel": channel, "oxide_bank": oxide_bank,
            "dry_ridge": dry_ridge, "deposition": deposition,
            "healed": healed, "slope": slope}


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> np.ndarray:
    f = _fields()
    travel = (0.31 * f["height"] + 0.47 * f["accumulation"]
              + 0.19 * f["oxide_bank"] + 0.13 * f["deposition"]
              - 0.11 * f["dry_ridge"])
    if angle_b:
        travel = 1.0 - travel + 0.17 * f["healed"] - 0.14 * f["channel"]
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)
    relief = (0.25 + 0.44 * f["oxide_bank"] + 0.36 * f["deposition"]
              + 0.22 * f["dry_ridge"] + 0.14 * f["slope"]
              - 0.29 * f["channel"])
    rgb *= np.clip(relief, 0.07, 1.26)[..., None]
    rgb += np.asarray((0.24, 0.09, 0.29) if not angle_b else (0.04, 0.24, 0.29), np.float32) * f["channel"][..., None]
    rgb += np.asarray((0.32, 0.20, 0.04) if not angle_b else (0.29, 0.05, 0.20), np.float32) * f["deposition"][..., None]
    rgb += np.asarray((0.05, 0.24, 0.16) if not angle_b else (0.28, 0.09, 0.05), np.float32) * f["healed"][..., None]
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
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" / "bornite_erosion_i2"), indent=2))
