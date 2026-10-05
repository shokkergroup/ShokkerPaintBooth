# -*- coding: utf-8 -*-
"""Native-2048 Black Pearl I1 continuous deposition study.

One deterministic anisotropic phase-separation history produces merged mantle
deposition islands, saddle seams, trapped inclusions, pearl ridges, polished
windows, healed necks and age skins. Paint/A-B only until native review. No
RNG/noise/circle placement/Voronoi/ring stamps/shared composer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_black_pearl"
RES = 512
WORK = 1024
NATIVE = 2048

COLORS_A = np.asarray((
    (3, 5, 10), (7, 12, 22), (10, 25, 39), (10, 46, 57),
    (9, 76, 80), (14, 111, 106), (31, 151, 133), (67, 188, 157),
    (124, 215, 180), (205, 232, 204), (215, 188, 169), (184, 120, 169),
    (125, 77, 166), (71, 67, 151), (36, 92, 150),
), np.float32)
COLORS_B = np.asarray((
    (7, 3, 13), (19, 6, 31), (42, 10, 60), (77, 14, 91),
    (119, 20, 119), (165, 28, 130), (211, 44, 120), (245, 78, 92),
    (255, 127, 64), (250, 182, 65), (213, 222, 88), (133, 221, 119),
    (54, 196, 161), (31, 151, 194), (55, 100, 211),
), np.float32)


def _norm(field: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(field, (1.0, 99.0))
    return np.clip((field - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0).astype(np.float32)


def _lap(field: np.ndarray) -> np.ndarray:
    return (np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0)
            + np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
            - 4.0 * field)


def _topology() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:RES, 0:RES].astype(np.float32)
    # Incommensurate analytic modes seed mantle chemistry without sampled or
    # pseudorandom noise. Frequencies retain 8-32 px detail at native output.
    u = (
        0.24 * np.sin(1.13 * xx + 0.37 * yy)
        + 0.21 * np.sin(-0.56 * xx + 1.47 * yy + 0.7)
        + 0.17 * np.sin(1.91 * xx + 0.29 * yy + 1.4)
        + 0.15 * np.cos(0.34 * xx - 2.17 * yy + 0.2)
        + 0.12 * np.sin(2.43 * xx + 1.21 * yy + 2.0)
    ).astype(np.float32)
    # A weak off-axis mantle bias makes histories directional but never creates
    # a giant basin or centered pearl icon.
    u += (0.055 * np.sin(0.021 * xx + 0.034 * yy)
          - 0.045 * np.cos(0.027 * xx - 0.018 * yy)).astype(np.float32)
    u = np.clip(u, -0.82, 0.82)
    snapshots: list[np.ndarray] = []
    # Anisotropic Allen-Cahn coarsening. Every visible boundary descends from
    # the same chronological field; no dots, cells or contours are placed.
    for step in range(54):
        lap = _lap(u)
        shear = np.roll(u, -1, axis=1) - np.roll(u, 1, axis=1)
        drift = np.roll(u, -1, axis=0) - np.roll(u, 1, axis=0)
        u += 0.115 * (0.58 * lap + u - u * u * u) + 0.006 * shear - 0.004 * drift
        u = np.clip(u, -1.25, 1.25)
        if step in (12, 24, 38, 53):
            snapshots.append(u.copy())

    age0, age1, age2, final = snapshots
    gx = cv2.Sobel(final, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(final, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx * gx + gy * gy)
    gxx = cv2.Sobel(final, cv2.CV_32F, 2, 0, ksize=3)
    gyy = cv2.Sobel(final, cv2.CV_32F, 0, 2, ksize=3)
    gxy = cv2.Sobel(final, cv2.CV_32F, 1, 1, ksize=3)
    determinant = gxx * gyy - gxy * gxy
    chronology = np.abs(final - age0) + 0.8 * np.abs(final - age1) + 0.55 * np.abs(final - age2)
    # Distinct physical observables retained for later causal material work if
    # and only if the paint survives native review.
    fields = {
        "phase": _norm(final),
        "age": _norm(chronology),
        "ridge": _norm(grad),
        "saddle": _norm(np.maximum(-determinant, 0.0)),
        "inclusion": _norm(np.maximum(-final - 0.38, 0.0) * np.maximum(0.55 - grad, 0.0)),
        "window": _norm(np.maximum(final - 0.26, 0.0) * np.maximum(0.62 - grad, 0.0)),
        "neck": _norm(np.maximum(determinant, 0.0) * np.maximum(grad - 0.18, 0.0)),
    }
    return {name: cv2.resize(value, (WORK, WORK), interpolation=cv2.INTER_CUBIC)
            for name, value in fields.items()}


def _paint(fields: dict[str, np.ndarray], angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    palette = COLORS_B if angle_b else COLORS_A
    phase = fields["phase"]
    age = fields["age"]
    ridge = fields["ridge"]
    saddle = fields["saddle"]
    inclusion = fields["inclusion"]
    window = fields["window"]
    neck = fields["neck"]
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    optical = np.mod(7.2 * phase + 4.3 * age + 1.6 * ridge
                     + 0.0025 * xx - 0.0018 * yy
                     + (6.0 if angle_b else 0.0), len(palette))
    i0 = np.floor(optical).astype(np.int32)
    i1 = (i0 + 1) % len(palette)
    t = (optical - i0)[..., None]
    image = palette[i0] * (1.0 - t) + palette[i1] * t
    # Old merged deposits are deep and luminous; inclusions remain genuinely
    # black while polished windows catch different angle families.
    shade = (0.24 + 0.52 * phase + 0.20 * age + 0.18 * ridge)[..., None]
    image = image * shade + np.asarray((2, 3, 6), np.float32)
    image *= (1.0 - 0.82 * inclusion[..., None])
    window_color = np.asarray((225, 241, 232) if not angle_b else (243, 218, 249), np.float32)
    image = image * (1.0 - 0.42 * window[..., None]) + window_color * (0.42 * window[..., None])
    # Saddle mergers receive narrow mineral seams and healed necks receive a
    # different hue. Both are field-derived, not thresholded outline copies.
    seam_color = np.asarray((207, 112, 166) if not angle_b else (91, 221, 161), np.float32)
    image = image * (1.0 - 0.32 * saddle[..., None]) + seam_color * (0.32 * saddle[..., None])
    neck_color = np.asarray((92, 205, 190) if not angle_b else (248, 137, 70), np.float32)
    image = image * (1.0 - 0.27 * neck[..., None]) + neck_color * (0.27 * neck[..., None])
    image = np.clip(image, 0, 255).astype(np.uint8)
    coverage = {
        "deposition_island_coverage": round(float(np.mean(phase > 0.54)), 6),
        "age_skin_coverage": round(float(np.mean(age > 0.58)), 6),
        "pearl_ridge_coverage": round(float(np.mean(ridge > 0.62)), 6),
        "saddle_seam_coverage": round(float(np.mean(saddle > 0.62)), 6),
        "trapped_inclusion_coverage": round(float(np.mean(inclusion > 0.60)), 6),
        "polished_window_coverage": round(float(np.mean(window > 0.60)), 6),
        "healed_neck_coverage": round(float(np.mean(neck > 0.62)), 6),
    }
    return image, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "black_pearl_phase_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    fields = _topology()
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
        "schema": "spb-wilds-black-pearl-phase-i1/1",
        "status": "REJECT-DIAGONAL-CHECKER-CHEVRON-PAVER-WITH-MICRORIBS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "continuous anisotropic mantle phase-separation history",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic modes plus chronological PDE; no RNG/noise/circles/Voronoi/ring stamps",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
