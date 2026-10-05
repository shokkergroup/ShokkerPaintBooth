# -*- coding: utf-8 -*-
"""Native-2048 Oil Beetle I1 differential cuticle study.

A single deterministic quasiperiodic Monge surface generates connected wet
blisters, negative-curvature throats, drainage rivulets, wrinkle collars, dry
gaps, pinhole critical points and travelling interference rims. Paint/A-B only
until native review. No RNG/noise/cells/circle placement/shared composer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_oil_beetle"
WORK = 1024
NATIVE = 2048

COLORS_A = np.asarray((
    (2, 5, 9), (3, 15, 23), (4, 38, 48), (5, 74, 75),
    (10, 121, 105), (30, 169, 130), (70, 208, 152), (141, 229, 166),
    (227, 230, 155), (250, 181, 92), (244, 109, 77), (215, 57, 113),
    (157, 43, 157), (88, 52, 171), (49, 96, 184),
), np.float32)
COLORS_B = np.asarray((
    (7, 3, 14), (23, 6, 39), (53, 10, 75), (92, 15, 106),
    (140, 24, 123), (191, 37, 122), (232, 61, 101), (252, 105, 70),
    (250, 164, 54), (218, 215, 63), (148, 226, 85), (68, 211, 132),
    (30, 178, 180), (36, 126, 213), (76, 77, 219),
), np.float32)


def _norm(field: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> np.ndarray:
    a, b = np.percentile(field, (lo, hi))
    return np.clip((field - a) / max(float(b - a), 1e-6), 0.0, 1.0).astype(np.float32)


def _surface() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Locally varying coordinates remove a repeating lattice while keeping all
    # primitive wavelengths within roughly 8-32 native pixels.
    wx = xx + 8.0 * np.sin(0.017 * yy + 0.9 * np.sin(0.006 * xx))
    wy = yy + 7.0 * np.sin(0.019 * xx - 0.8 * np.sin(0.008 * yy))
    phi1 = 0.47 * wx + 0.18 * wy + 1.4 * np.sin(0.021 * wy)
    phi2 = -0.23 * wx + 0.59 * wy + 1.1 * np.sin(0.017 * wx + 0.5)
    phi3 = 0.41 * wx - 0.52 * wy + 0.9 * np.sin(0.013 * (wx + wy))
    phi4 = 0.71 * wx + 0.11 * wy + 0.65 * np.sin(0.029 * (wx - wy))
    z = (0.78 * np.sin(phi1) + 0.66 * np.sin(phi2)
         + 0.48 * np.sin(phi3) + 0.31 * np.cos(phi4)
         + 0.17 * np.sin(phi1 + phi2 - 0.6 * phi3)).astype(np.float32)
    z = cv2.GaussianBlur(z, (0, 0), 0.65)
    zx = cv2.Sobel(z, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    zy = cv2.Sobel(z, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    zxx = cv2.Sobel(z, cv2.CV_32F, 2, 0, ksize=3) / 4.0
    zyy = cv2.Sobel(z, cv2.CV_32F, 0, 2, ksize=3) / 4.0
    zxy = cv2.Sobel(z, cv2.CV_32F, 1, 1, ksize=3) / 4.0
    denom = np.maximum((1.0 + zx * zx + zy * zy) ** 2, 1e-5)
    gaussian = (zxx * zyy - zxy * zxy) / denom
    mean = ((1.0 + zy * zy) * zxx - 2.0 * zx * zy * zxy
            + (1.0 + zx * zx) * zyy) / np.maximum(
                2.0 * (1.0 + zx * zx + zy * zy) ** 1.5, 1e-5)
    slope = np.sqrt(zx * zx + zy * zy)
    blister = _norm(np.maximum(gaussian, 0.0) * (0.65 + 0.35 * _norm(z)))
    throat = _norm(np.maximum(-gaussian, 0.0) * (0.55 + 0.45 * _norm(slope)))
    collar = _norm(np.sqrt(
        cv2.Sobel(blister, cv2.CV_32F, 1, 0, ksize=3) ** 2
        + cv2.Sobel(blister, cv2.CV_32F, 0, 1, ksize=3) ** 2))
    # Gravity-projected slope selects actual draining faces; it is not a line
    # texture or independent overlay.
    drainage = _norm(np.maximum(0.72 * zy + 0.31 * zx, 0.0) * np.maximum(slope - 0.08, 0.0))
    dry = _norm(np.maximum(-z - 0.45, 0.0) * np.maximum(0.42 - slope, 0.0))
    critical = _norm(np.maximum(0.19 - slope, 0.0) * np.maximum(np.abs(gaussian) - 0.012, 0.0))
    rim = _norm(np.abs(mean) * (0.55 + 0.45 * blister))
    orientation = np.mod(np.arctan2(zy, zx) / (2.0 * np.pi) + 1.0, 1.0).astype(np.float32)
    return {
        "height": _norm(z), "blister": blister, "throat": throat,
        "collar": collar, "drainage": drainage, "dry": dry,
        "critical": critical, "rim": rim, "orientation": orientation,
    }


def _paint(fields: dict[str, np.ndarray], angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    palette = COLORS_B if angle_b else COLORS_A
    height = fields["height"]
    blister = fields["blister"]
    throat = fields["throat"]
    collar = fields["collar"]
    drainage = fields["drainage"]
    dry = fields["dry"]
    critical = fields["critical"]
    rim = fields["rim"]
    orientation = fields["orientation"]
    optical = np.mod(5.5 * height + 4.1 * orientation + 3.4 * rim
                     + 1.7 * blister + (6.2 if angle_b else 0.0), len(palette))
    i0 = np.floor(optical).astype(np.int32)
    i1 = (i0 + 1) % len(palette)
    t = (optical - i0)[..., None]
    image = palette[i0] * (1.0 - t) + palette[i1] * t
    shade = (0.17 + 0.34 * height + 0.31 * blister + 0.22 * rim)[..., None]
    image = image * shade + np.asarray((1, 3, 5), np.float32)
    # Each causal family receives its own optical response. Thresholds never
    # add dots or random grain; they expose differential-surface events.
    throat_color = np.asarray((3, 8, 13), np.float32)
    image = image * (1.0 - 0.66 * throat[..., None]) + throat_color * (0.66 * throat[..., None])
    drain_color = np.asarray((41, 193, 176) if not angle_b else (246, 117, 74), np.float32)
    image = image * (1.0 - 0.24 * drainage[..., None]) + drain_color * (0.24 * drainage[..., None])
    collar_color = np.asarray((225, 232, 176) if not angle_b else (177, 231, 105), np.float32)
    image = image * (1.0 - 0.27 * collar[..., None]) + collar_color * (0.27 * collar[..., None])
    image *= (1.0 - 0.48 * dry[..., None])
    pin_color = np.asarray((234, 110, 166) if not angle_b else (70, 207, 195), np.float32)
    image = image * (1.0 - 0.25 * critical[..., None]) + pin_color * (0.25 * critical[..., None])
    image = np.clip(image, 0, 255).astype(np.uint8)
    coverage = {
        "wet_blister_coverage": round(float(np.mean(blister > 0.60)), 6),
        "throat_coverage": round(float(np.mean(throat > 0.62)), 6),
        "wrinkle_collar_coverage": round(float(np.mean(collar > 0.64)), 6),
        "drainage_coverage": round(float(np.mean(drainage > 0.62)), 6),
        "dry_gap_coverage": round(float(np.mean(dry > 0.62)), 6),
        "pinhole_critical_coverage": round(float(np.mean(critical > 0.65)), 6),
        "interference_rim_coverage": round(float(np.mean(rim > 0.62)), 6),
    }
    return image, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "oil_beetle_surface_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    fields = _surface()
    a, coverage = _paint(fields, False)
    b, _ = _paint(fields, True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint_path = output / f"{ID}_paint_2048.png"
    _write(paint_path, native_a)
    shutil.copyfile(paint_path, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-oil-beetle-surface-i1/1",
        "status": "REJECT-HOMOGENEOUS-MICROPORE-PEBBLE-WALLPAPER-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "continuous quasiperiodic differential wet-cuticle surface",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic Monge surface; no RNG/noise/cells/circles/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
