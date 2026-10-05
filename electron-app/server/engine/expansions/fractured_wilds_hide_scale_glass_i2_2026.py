# -*- coding: utf-8 -*-
"""Native-2048 Hide Scale Glass I2 continuous refractive-dermis study.

FROZEN REJECT (SPB-105 tick 2026-08-25): actual 2048 review resolves the
analytic sheet into thousands of near-identical dark loop glyphs riding broad
diagonal colour bands. The mechanism is deterministic and fast, but visual
repetition still violates the owner finish doctrine. No spec maps were made.

SPB-105 / 2026-08-25 native rebuild tick. I1 is frozen as over-budget
vertical bead curtains of repeated capsules. I2 replaces both its point carrier
and discrete lens glyph with one analytic non-invertible glass mapping. Fine
caustic folds, bevel ridges, inverted occlusion pockets, focal cusps and stress
veins are separate differential observables. Paint/A-B only until native eye.

No RNG, sampled noise, grain, points, cells, stamps or shared composer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fc_hide_scale_glass"
WORK = 1024
NATIVE = 2048

GLASS_A = np.asarray([
    (5, 4, 13), (20, 8, 40), (49, 12, 76), (89, 17, 107),
    (135, 24, 129), (183, 36, 144), (224, 57, 153), (250, 88, 158),
    (255, 130, 164), (255, 177, 178), (252, 218, 201), (205, 237, 218),
    (127, 226, 221), (65, 184, 222), (67, 106, 199),
], np.float32)
GLASS_B = np.asarray([
    (3, 8, 18), (3, 25, 45), (3, 51, 72), (4, 84, 94),
    (6, 119, 110), (13, 156, 125), (30, 193, 141), (61, 222, 158),
    (109, 239, 181), (170, 246, 207), (227, 240, 230), (220, 198, 239),
    (176, 147, 232), (123, 96, 211), (67, 57, 166),
], np.float32)


def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix


def _norm(value: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(value)), float(np.max(value))
    return (value - lo) / max(hi - lo, 1e-7)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Coupled fine folds keep local widths in the 8-32 px native range. Slower
    # modulation bends the sheet but never becomes a standalone color field.
    u = (
        x
        + 9.4 * np.sin(y / 5.7 + 0.31 * np.sin(x / 43.0))
        + 5.8 * np.sin((x + 1.37 * y) / 9.1)
        + 3.7 * np.sin((1.91 * x - y) / 13.7)
    )
    v = (
        y
        + 8.7 * np.sin(x / 6.3 - 0.27 * np.cos(y / 47.0))
        + 5.1 * np.sin((1.53 * x - y) / 10.7)
        + 3.9 * np.cos((x + 1.83 * y) / 14.9)
    )
    uy, ux = np.gradient(u)
    vy, vx = np.gradient(v)
    jac = ux * vy - uy * vx
    # Jacobian zeroes are focal folds; inversion is real overlap/occlusion.
    jscale = np.percentile(np.abs(jac), 65) + 1e-6
    caustic = np.exp(-((jac / (0.24 * jscale)) ** 2))
    inverted = np.clip(-jac / (1.35 * jscale), 0.0, 1.0)
    # Singular-direction split approximates lens bevel anisotropy without SVD.
    col_x = np.hypot(ux, vx)
    col_y = np.hypot(uy, vy)
    anis = np.abs(col_x - col_y) / (col_x + col_y + 1e-6)
    bevel = np.clip(_norm(np.hypot(*np.gradient(jac))) ** 0.72, 0.0, 1.0)
    lap = cv2.Laplacian(jac.astype(np.float32), cv2.CV_32F, ksize=3)
    stress = np.clip(_norm(np.abs(lap)) ** 1.9, 0.0, 1.0)
    # Cusps require a caustic fold, high anisotropy and curvature together.
    cusp = np.clip(caustic * np.clip((anis - 0.18) / 0.42, 0.0, 1.0)
                   * np.clip(stress * 1.35, 0.0, 1.0), 0.0, 1.0)
    shoulder = np.clip(caustic * (1.0 - inverted) * (0.35 + 0.65 * anis), 0.0, 1.0)

    optical = (
        0.00141 * u + 0.00193 * v
        + 0.083 * np.sin((u - 1.27 * v) / 31.0)
        + 0.061 * np.cos((1.49 * u + v) / 43.0)
        + 0.11 * shoulder
    )
    if angle_b:
        optical = optical + 0.37 + 0.12 * anis - 0.08 * inverted
        stops = GLASS_B
        flash = 0.43 + 0.49 * np.clip(np.cos(2.0 * np.pi * (optical + 0.12)), 0.0, 1.0)
    else:
        stops = GLASS_A
        flash = 0.52 + 0.45 * np.clip(np.cos(2.0 * np.pi * (optical - 0.21)), 0.0, 1.0)
    image = _palette(optical, stops)
    light = (
        0.19 + 0.27 * anis + 0.46 * shoulder * flash
        + 0.34 * bevel + 0.42 * cusp - 0.37 * inverted
    )
    image = np.clip(image * light[..., None], 0, 255)
    # Stress veins selectively desaturate/brighten the same mapped glass; they
    # are not flecks, grain or a free high-pass overlay.
    vein = stress > 0.76
    image[vein] = np.clip(image[vein] * 0.54 + 78.0, 0, 255)
    # Open inversion throats remain optically dark, separated from bright folds.
    throat = inverted > 0.72
    image[throat] *= 0.28
    masks = {
        "refractive_body": anis,
        "caustic_fold": caustic,
        "bevel_ridge": bevel,
        "occlusion_inversion": inverted,
        "focal_cusp": cusp,
        "stress_vein": vein.astype(np.float32),
        "open_throat": throat.astype(np.float32),
    }
    coverage = {name: round(float(np.mean(mask > 0.22)), 6) for name, mask in masks.items()}
    return image.astype(np.uint8), coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "hide_scale_glass_i2"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage = _paint(False)
    b, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint = output / f"{ID}_paint_2048.png"
    _write(paint, native_a)
    shutil.copyfile(paint, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-hide-scale-glass-i2/1",
        "status": "REJECT-REPEATED-LOOP-GLYPHS-ON-DIAGONAL-BANDS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "continuous non-invertible refractive dermis with differential caustics",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic mapped sheet; no RNG/noise/grain/points/cells/stamps/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
