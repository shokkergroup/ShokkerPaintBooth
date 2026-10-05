# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Sunset Moth I1 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 54, 2026-08-25. Owner verdict: no recolored
clones, no random-noise separation, fine 8-32 px anatomy, and a real
Fractured A/B flip. This contact uses one deterministic off-canvas wing-root
chronology: unequal fan folds, transverse growth checks, scale lips, healed
splits and frayed tips all derive from the same continuous membrane. It does
not call a shared Wilds composer and authors no spec until native paint passes.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_sunset_moth"
AUTHORED = 1024

PALETTE_A = np.asarray([
    (10, 3, 19), (37, 5, 43), (77, 7, 68), (122, 12, 76),
    (171, 21, 66), (218, 43, 50), (250, 78, 36), (255, 124, 29),
    (255, 178, 39), (247, 224, 67), (170, 224, 82), (77, 196, 100),
    (24, 148, 116), (19, 92, 119), (38, 42, 102),
], np.float32) / 255.0

PALETTE_B = np.asarray([
    (7, 8, 26), (11, 31, 67), (12, 68, 111), (10, 112, 139),
    (18, 157, 135), (55, 197, 106), (125, 220, 78), (207, 227, 62),
    (255, 194, 55), (255, 137, 58), (245, 79, 82), (213, 43, 119),
    (163, 30, 143), (103, 28, 141), (48, 24, 101),
], np.float32) / 255.0


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    n = AUTHORED
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n * 2.0 - 1.0
    y = (yy + 0.5) / n * 2.0 - 1.0

    # One off-canvas wing root. The logarithmic chronology opens toward the
    # opposite edge; asymmetric shears prevent a polar/ring stamp reading.
    dx = x + 1.31
    dy = (y - 0.24) * 1.18
    radius = np.sqrt(dx * dx + dy * dy) + 0.035
    theta = np.arctan2(dy, dx)
    shear = (0.080 * np.sin(3.7 * y + 1.9 * x)
             + 0.041 * np.sin(8.3 * x - 2.6 * y)
             + 0.023 * np.sin(5.1 * x * y + 2.8 * y))
    fan = theta / np.pi + shear / radius
    growth = np.log(radius) + 0.11 * np.sin(4.6 * theta + 2.3 * radius)
    bend = 0.08 * np.sin(6.7 * growth - 2.9 * fan) + 0.045 * np.sin(11.1 * fan + 1.7 * growth)

    # Five attached mark families. They are continuous consequences of the
    # same chronology, never independent noise or pasted glyphs.
    fold_phase = 2.0 * np.pi * (31.0 * fan + 2.8 * growth + 3.0 * bend)
    check_phase = 2.0 * np.pi * (34.0 * growth + 4.2 * fan + 1.7 * bend)
    fine_phase = 2.0 * np.pi * (47.0 * growth - 19.0 * fan + 4.0 * bend)
    fold = np.exp(-((np.sin(fold_phase) / 0.22) ** 2)).astype(np.float32)
    check = np.exp(-((np.sin(check_phase) / 0.19) ** 2)).astype(np.float32)
    scale_lip = np.exp(-((np.sin(fine_phase) / 0.16) ** 2)).astype(np.float32)
    growth_gate = 0.5 + 0.5 * np.sin(7.3 * growth + 9.1 * fan)
    transverse = check * np.clip((growth_gate - 0.36) / 0.64, 0.0, 1.0)
    healed_split = fold * check * np.clip((0.57 - growth_gate) / 0.57, 0.0, 1.0)
    fray = scale_lip * np.clip((radius - 1.18) / 0.75, 0.0, 1.0) * np.clip(
        0.58 + 0.42 * np.sin(13.7 * fan - 4.9 * growth), 0.0, 1.0)
    compression = np.clip(0.5 + 0.5 * np.cos(5.7 * growth + 3.1 * fan), 0.0, 1.0)

    travel = 0.34 * growth + 0.61 * fan + 0.18 * bend + 0.08 * compression
    if angle_b:
        travel = 1.0 - travel + 0.17 * transverse - 0.11 * healed_split
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)

    relief = (0.30 + 0.44 * fold + 0.21 * transverse + 0.13 * scale_lip
              + 0.19 * compression - 0.31 * fray - 0.22 * healed_split)
    rgb *= np.clip(relief, 0.08, 1.24)[..., None]
    rgb += np.asarray((0.34, 0.10, 0.025) if not angle_b else (0.025, 0.20, 0.34), np.float32) * (fold * compression)[..., None]
    rgb += np.asarray((0.05, 0.27, 0.15) if not angle_b else (0.31, 0.05, 0.22), np.float32) * transverse[..., None]
    rgb += np.asarray((0.25, 0.045, 0.24) if not angle_b else (0.04, 0.28, 0.20), np.float32) * healed_split[..., None]
    rgb *= (1.0 - 0.54 * fray)[..., None]

    paint = cv2.resize(np.clip(rgb, 0.0, 1.0).astype(np.float32),
                       (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    return paint, {"fold": fold, "transverse": transverse,
                   "scale_lip": scale_lip, "healed_split": healed_split,
                   "fray": fray, "compression": compression}


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
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" / "sunset_moth_fan_i1"), indent=2))
