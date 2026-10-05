# -*- coding: utf-8 -*-
"""Isolated native-2048 Black Opal asymmetric Newton-basin study.

SPB-105 / Wilds attempt 95 / 2026-08-25. Seven unequal complex roots form one
deterministic silica-domain field. Basin plates, convergence terraces, critical
filaments, order-switch seams, black potch, crazing hooks, inclusion windows,
dislocation wedges and repair bridges are literal observables of the Newton
history. There is no sampled noise, dot/pinfire scatter, hex/cell paver,
periodic phase carrier, recolour fallback or shared composer. The solved field
is deliberately smoothed so native features land at 8--32 px rather than pixel
static. Fractured A/B changes optical order while preserving exact geometry.

Native-2048 verdict: REJECTED. The asymmetric solve becomes giant green
eye/bullseye basins. Basin seams become repeated thick lacy loops, and hooks,
windows, wedges and bridges read as scattered symbols. New math is not a
uniqueness pass. Frozen before spec/M7/runtime. No root, affine, iteration,
smoothing, palette, seam, accessory, scale, spec or noise repair is authorized;
a successor must replace both basin and seam contact topology.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_black_opal"
ATTEMPT = 95
WORK = 768
NATIVE = 2048
ITERATIONS = 34

ROOTS = np.asarray([
    -1.13 - .22j, -.71 + .94j, .09 + 1.21j, .91 + .78j,
    1.17 - .31j, .43 - 1.08j, -.57 - .91j,
], np.complex64)

PALETTE_A = np.asarray([
    (2, 4, 13), (5, 12, 31), (8, 27, 53), (10, 49, 72), (11, 75, 84),
    (14, 103, 88), (22, 132, 85), (37, 160, 76), (58, 187, 65),
    (86, 208, 59), (119, 224, 68), (157, 232, 87), (195, 229, 116),
    (224, 214, 151), (241, 192, 195),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (20, 2, 27), (48, 3, 52), (78, 5, 72), (109, 8, 86), (140, 13, 93),
    (171, 21, 95), (199, 33, 91), (223, 49, 85), (239, 70, 80),
    (248, 96, 80), (249, 126, 89), (244, 158, 107), (232, 188, 133),
    (211, 214, 165), (179, 232, 204),
], np.float32) / 255.0


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _solve():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx / (WORK - 1) - .5) * 3.46
    y = (yy / (WORK - 1) - .5) * 3.31
    # Fixed affine skew removes textbook radial symmetry without introducing
    # any stochastic warp or hiding the basin topology.
    z = ((x + .17 * y + .09 * np.sin(y * 1.7))
         + 1j * (y - .11 * x + .07 * np.sin(x * 2.1))).astype(np.complex64)
    first_converged = np.full((WORK, WORK), ITERATIONS, np.float32)
    residual = np.zeros((WORK, WORK), np.float32)
    for iteration in range(ITERATIONS):
        denom = np.zeros_like(z)
        for root in ROOTS:
            denom += 1.0 / (z - root + np.complex64(1e-6 + 1e-6j))
        step = 1.0 / (denom + np.complex64(1e-6 + 1e-6j))
        z -= step
        residual = np.abs(step).astype(np.float32)
        newly = (first_converged == ITERATIONS) & (residual < 2.5e-4)
        first_converged[newly] = iteration
    distances = np.stack([np.abs(z - root) for root in ROOTS], axis=0)
    basin = np.argmin(distances, axis=0).astype(np.uint8)
    nearest = np.min(distances, axis=0).astype(np.float32)
    return basin, first_converged, residual, nearest


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    basin, convergence, residual, nearest = _solve()
    conv = np.clip(convergence / (ITERATIONS - 1), 0, 1)
    # Smooth only optical observables; discrete basin ownership remains exact.
    conv_s = cv2.GaussianBlur(conv, (0, 0), 3.2)
    basin_order = np.asarray((.04, .21, .39, .58, .76, .91, .67), np.float32)[basin]
    basin_order = cv2.GaussianBlur(basin_order, (0, 0), 2.7)
    terrace = .5 + .5 * np.cos(2 * np.pi * (convergence / 4.7 + nearest * 3.2))
    terrace = cv2.GaussianBlur(terrace.astype(np.float32), (0, 0), 2.2)
    gy, gx = np.gradient(conv_s)

    travel = (basin_order * .56 + conv_s * .37 + terrace * .18
              + gx * .21 - gy * .15 + (.41 if angle_b else 0.0)) % 1.0
    shade = np.clip(.22 + .47 * (1 - conv_s) + .29 * terrace + .16 * gx - .11 * gy,
                    .07, 1.06)
    paint = _ramp(travel, palette) * shade[..., None]

    # Exact discrete boundaries expose root-domain terminations; no Voronoi or
    # arbitrary crack graph is generated.
    seam = np.zeros((WORK, WORK), np.uint8)
    seam[:, 1:] |= (basin[:, 1:] != basin[:, :-1]).astype(np.uint8) * 255
    seam[1:, :] |= (basin[1:, :] != basin[:-1, :]).astype(np.uint8) * 255
    seam = cv2.dilate(seam, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    critical = ((conv_s > .55) & (terrace > .46)).astype(np.uint8) * 255
    critical = cv2.morphologyEx(critical, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    potch = ((convergence >= ITERATIONS - 3) | (nearest > .055)).astype(np.uint8) * 255
    potch = cv2.morphologyEx(potch, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    paint[seam > 8] = np.clip(paint[seam > 8] * .31 + palette[13] * .61, 0, 1)
    paint[potch > 8] *= .09

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "silica_domain_plates", "convergence_terraces", "critical_filaments",
        "order_switch_seams", "black_potch", "crazing_hooks",
        "inclusion_windows", "dislocation_wedges", "repair_bridges")}
    masks["silica_domain_plates"][:] = 255
    masks["convergence_terraces"][terrace > .61] = 255
    masks["critical_filaments"] = critical
    masks["order_switch_seams"] = seam
    masks["black_potch"] = potch

    # Curvature-selected seam anatomy. Event locations come from seam geometry
    # sampled at fixed arc order, never RNG or arbitrary dot placement.
    contours, _ = cv2.findContours(seam, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    contours = sorted((c for c in contours if len(c) >= 19), key=lambda c: len(c), reverse=True)[:23]
    for contour_index, contour in enumerate(contours):
        pts = contour[:, 0, :]
        stride = max(17, len(pts) // (4 + contour_index % 5))
        for event, p in enumerate(pts[stride // 2::stride]):
            x, y = int(p[0]), int(p[1])
            if not (10 <= x < WORK - 10 and 10 <= y < WORK - 10):
                continue
            q0 = pts[(event * stride - 4) % len(pts)].astype(np.float32)
            q1 = pts[(event * stride + 4) % len(pts)].astype(np.float32)
            tangent = q1 - q0
            tangent /= np.linalg.norm(tangent) + 1e-6
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            centre = np.asarray((x, y), np.float32)
            family = (contour_index * 7 + event * 3) % 4
            color = tuple(float(v) for v in np.clip(palette[(contour_index * 3 + event + 11) % 15] * 1.2, 0, 1))
            if family == 0:
                hook = np.asarray((centre - tangent * 7,
                                   centre + normal * 7,
                                   centre + tangent * 8 + normal * 2), np.int32)
                cv2.polylines(paint, [hook], False, color, 3, cv2.LINE_AA)
                cv2.polylines(masks["crazing_hooks"], [hook], False, 255, 3, cv2.LINE_AA)
            elif family == 1:
                axes = (5 + event % 5, 3 + contour_index % 3)
                cv2.ellipse(paint, (x, y), axes, int(np.degrees(np.arctan2(tangent[1], tangent[0]))),
                            0, 360, (0.002, .003, .007), 3, cv2.LINE_AA)
                cv2.ellipse(masks["inclusion_windows"], (x, y), axes, 0, 0, 360, 255, 3, cv2.LINE_AA)
            elif family == 2:
                tri = np.asarray((centre - tangent * 6,
                                  centre + tangent * 7 - normal * 6,
                                  centre + tangent * 4 + normal * 7), np.int32)
                cv2.polylines(paint, [tri], True, color, 3, cv2.LINE_AA)
                cv2.fillPoly(masks["dislocation_wedges"], [tri], 255, cv2.LINE_AA)
            else:
                a, b = centre - normal * 7, centre + normal * 8
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), color, 3, cv2.LINE_AA)
                cv2.line(masks["repair_bridges"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/black_opal_newton_basins_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, masks = _render(False)
        repeats.append(_u8(_native(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _render(True)
    native_a, native_b = repeats[0], _u8(_native(angle_b))
    for label, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{label}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(native_a[704:1344, 704:1344], cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {"id": ID, "module": __name__, "attempt": ATTEMPT,
              "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED", "timings_s": timings,
              "deterministic": bool(all(np.array_equal(repeats[0], x) for x in repeats[1:])),
              "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95)),
              "coverage": {k: float((v > 8).mean()) for k, v in masks.items()},
              "owner_accepted": False, "production_wired": False}
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-black-opal-newton-basins-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
