# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Black Opal I3 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 58, 2026-08-25. I1 checker/chevron phase and
I2 Bragg static/moire are frozen. I3 uses one nonperiodic rational-orbit sheet:
every pixel follows the same deterministic complex recurrence, while escape
age, pole approach, derivative strain, capture age and orbit angle expose five
causal anatomies. No RNG/noise, periodic substrate, placed marks, cells, tiles,
stamps or shared composer. Work at 512 and smooth before 2048 so visible
anatomy stays in the 8-32 px native band.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_black_opal"
WORK = 512

PALETTE_A = np.asarray([
    (2, 3, 8), (7, 7, 24), (18, 10, 48), (42, 12, 78),
    (79, 15, 105), (125, 22, 121), (172, 36, 116), (216, 58, 96),
    (246, 91, 72), (255, 137, 55), (246, 189, 54), (181, 220, 73),
    (87, 206, 102), (28, 158, 126), (17, 91, 128),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (2, 4, 11), (5, 18, 40), (6, 48, 81), (5, 88, 111),
    (9, 133, 119), (32, 177, 102), (83, 207, 82), (151, 224, 70),
    (220, 219, 67), (255, 180, 69), (254, 122, 82), (231, 72, 113),
    (185, 45, 142), (122, 34, 146), (56, 25, 109),
], np.float32) / 255.0


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.nan_to_num(np.asarray(a, np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / max(hi - lo, 1e-6)


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    n = WORK
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    z0 = ((xx + 0.5) / n * 2.52 - 1.36
          + 1j * ((yy + 0.5) / n * 2.18 - 1.09)).astype(np.complex64)
    z = z0.copy()
    derivative = np.ones_like(z)
    escape_age = np.zeros((n, n), np.float32)
    capture_age = np.zeros((n, n), np.float32)
    pole_trap = np.full((n, n), 6.0, np.float32)
    strain_peak = np.zeros((n, n), np.float32)
    active = np.ones((n, n), bool)
    c = np.complex64(-0.417 + 0.596j)
    pole = np.complex64(0.238 - 0.173j)
    strength = np.complex64(0.094 + 0.052j)

    for iteration in range(52):
        safe = z - pole + np.complex64(0.006 + 0.004j)
        local_derivative = np.complex64(2.0) * z - strength / (safe * safe)
        derivative = derivative * local_derivative
        z = z * z + c + strength / safe
        mag = np.abs(z).astype(np.float32)
        pole_trap = np.minimum(pole_trap, np.abs(safe).astype(np.float32))
        strain_peak = np.maximum(strain_peak, np.log1p(np.abs(derivative)).astype(np.float32))
        newly_escaped = active & (mag > 5.0)
        escape_age[newly_escaped] = iteration + 1.0 - np.log2(np.maximum(np.log2(mag[newly_escaped]), 1e-4))
        active &= ~newly_escaped
        newly_captured = active & (mag < 0.075) & (capture_age == 0.0)
        capture_age[newly_captured] = float(iteration + 1)
        # Keep inactive values bounded while retaining their recorded anatomy.
        z[~active] = np.complex64(5.0 + 0.0j)
        derivative[~active] = np.complex64(1.0 + 0.0j)

    interior = active.astype(np.float32)
    escape = _norm(escape_age)
    capture = _norm(capture_age)
    pole_approach = 1.0 - _norm(np.log1p(pole_trap))
    strain = _norm(strain_peak)
    orbit_angle = np.mod(np.angle(z) / (2.0 * np.pi) + 1.0, 1.0).astype(np.float32)
    # Suppress sub-pixel orbit residue before 4x upscale. Derivative edges then
    # land around 8-24 px at native 2048.
    escape = cv2.GaussianBlur(escape, (0, 0), 1.25)
    pole_approach = cv2.GaussianBlur(pole_approach, (0, 0), 1.15)
    strain = cv2.GaussianBlur(strain, (0, 0), 1.35)
    capture = cv2.GaussianBlur(capture, (0, 0), 1.45)
    filament = _norm(cv2.magnitude(
        cv2.Sobel(escape, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(escape, cv2.CV_32F, 0, 1, ksize=3)))
    refractory = _norm(interior * (1.0 - pole_approach) * (0.3 + 0.7 * strain))
    healed = _norm(capture * (1.0 - filament))
    return {"escape": escape, "capture": capture, "pole": pole_approach,
            "strain": strain, "angle": orbit_angle, "filament": filament,
            "refractory": refractory, "healed": healed,
            "interior": interior}


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> np.ndarray:
    f = _fields()
    travel = (0.39 * f["escape"] + 0.28 * f["angle"]
              + 0.23 * f["pole"] + 0.16 * f["strain"]
              + 0.11 * f["capture"])
    if angle_b:
        travel = 1.0 - travel + 0.19 * f["healed"] - 0.14 * f["refractory"]
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)
    relief = (0.19 + 0.48 * f["filament"] + 0.29 * f["pole"]
              + 0.22 * f["strain"] + 0.18 * f["healed"]
              - 0.27 * f["refractory"])
    rgb *= np.clip(relief, 0.055, 1.30)[..., None]
    rgb += np.asarray((0.32, 0.08, 0.28) if not angle_b else (0.04, 0.28, 0.31), np.float32) * f["pole"][..., None]
    rgb += np.asarray((0.34, 0.21, 0.045) if not angle_b else (0.27, 0.06, 0.24), np.float32) * f["filament"][..., None]
    rgb += np.asarray((0.06, 0.25, 0.16) if not angle_b else (0.29, 0.10, 0.04), np.float32) * f["healed"][..., None]
    rgb *= (1.0 - 0.47 * f["refractory"])[..., None]
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
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" / "black_opal_orbit_i3"), indent=2))
