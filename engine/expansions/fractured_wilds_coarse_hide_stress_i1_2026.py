# -*- coding: utf-8 -*-
"""Isolated native-2048 Coarse Hide stress-dermis study.

SPB-105 / Wilds attempt 81 / 2026-08-25. Owner verdict applied: the app cannot
ship another lazy recolor or repeated spec silhouette. Four unequal off-canvas
loads create one analytic stress tensor. Fine 8--30 px wrinkles, paired pore
valves, saddle folds, abrasion crescents, scar bridges, compression zones,
shear slips and healed lips all descend from that continuous tensor/relief.
No RNG, sampled noise, cell paving, pebble scatter, scalar color territories,
line scatter or shared composer.

Native-2048 verdict: REJECTED. The analytic dermis collapses into a uniform
moiré/ripple carrier crossed by long repeated plus-sign scar rails. Saddle,
compression, pore, abrasion, slip and healed masks do not become distinct hide
anatomy. Frozen before spec/M7/runtime. No load, tensor, phase, wavelength,
palette, threshold, pore, scar, density, scale, spec or noise repair is
authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fc_coarse_hide"
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (8, 12, 18), (12, 25, 30), (15, 42, 43), (19, 62, 55),
    (29, 83, 65), (47, 105, 75), (73, 126, 83), (105, 145, 91),
    (142, 160, 101), (177, 171, 111), (207, 178, 121), (228, 176, 132),
    (234, 159, 146), (217, 133, 163), (178, 108, 178),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (18, 7, 25), (39, 10, 45), (65, 14, 65), (91, 19, 82),
    (119, 28, 96), (148, 41, 105), (177, 57, 108), (202, 77, 108),
    (220, 101, 107), (230, 130, 109), (227, 159, 116), (207, 187, 128),
    (170, 210, 146), (126, 220, 169), (82, 210, 189),
], np.float32) / 255.0


def _norm(a):
    a = np.asarray(a, np.float32)
    return (a - float(a.min())) / (float(np.ptp(a)) + 1e-7)


def _ramp(t, palette):
    palette = np.asarray(palette, np.float32)
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    index = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - index)[..., None]
    return palette[index] * (1 - f) + palette[index + 1] * f


def _edge(mask, radius=1):
    src = np.uint8(mask > .5)
    kernel = np.ones((radius * 2 + 1, radius * 2 + 1), np.uint8)
    return (cv2.dilate(src, kernel) - cv2.erode(src, kernel)).astype(np.float32)


def _surface():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x, y = (xx - WORK * .5) / WORK, (yy - WORK * .5) / WORK
    c2 = np.zeros_like(x)
    s2 = np.zeros_like(x)
    pressure = np.zeros_like(x)
    # Unequal boundary loads create a director without random seeds or cells.
    for lx, ly, gain, bias in ((-1.13, -.37, 1.0, .12), (1.21, -.61, .79, -.18),
                               (-.74, 1.24, .63, .31), (.96, 1.18, .91, -.27)):
        dx, dy = x - lx, y - ly
        r2 = dx * dx + dy * dy + .035
        phi = np.arctan2(dy, dx) + bias
        weight = gain / r2
        c2 += weight * np.cos(2 * phi)
        s2 += weight * np.sin(2 * phi)
        pressure += gain / np.sqrt(r2)
    theta = .5 * np.arctan2(s2, c2)
    order = _norm(np.hypot(c2, s2) / (pressure + 1e-5))
    compression = _norm(pressure + .32 * np.sin(5.1 * x - 3.7 * y))
    ct, st = np.cos(theta), np.sin(theta)
    u, v = x * ct + y * st, -x * st + y * ct

    # Local wavelength stays between 4 and 15 work pixels (8--30 native).
    lam = 4.8 + 9.2 * (.22 + .78 * order)
    phase = 2 * np.pi * (u * WORK / lam + .18 * np.sin(v * WORK / 37.0))
    cross_phase = 2 * np.pi * (v * WORK / (7.0 + 7.0 * (1 - order))
                               + .13 * np.sin(u * WORK / 29.0))
    wrinkle = np.sin(phase)
    cross = np.sin(cross_phase)
    height = (.105 * wrinkle + .056 * cross * compression ** 1.6
              + .027 * np.sin(phase * .47 - cross_phase * .31)
              + .018 * np.cos(phase * 1.71 + cross_phase * .23)).astype(np.float32)
    height = cv2.GaussianBlur(height, (0, 0), .62)

    gy, gx = np.gradient(height)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    gaussian = gxx * gyy - .25 * (gxy + gyx) ** 2
    theta_gx = cv2.Sobel(theta, cv2.CV_32F, 1, 0, ksize=3)
    theta_gy = cv2.Sobel(theta, cv2.CV_32F, 0, 1, ksize=3)
    shear = _norm(np.hypot(theta_gx, theta_gy))
    saddle = np.clip((-gaussian - np.quantile(-gaussian, .72)) /
                     (np.quantile(-gaussian, .98) - np.quantile(-gaussian, .72) + 1e-7), 0, 1)
    crest = np.clip((wrinkle - .52) / .48, 0, 1)
    compression_zone = np.clip((compression - .60) / .40, 0, 1)
    slip = np.clip((shear - .67) / .33, 0, 1) * np.clip((np.abs(cross) - .48) / .52, 0, 1)
    scar = np.clip((.22 - order) / .22, 0, 1) * np.clip((np.abs(wrinkle) - .35) / .65, 0, 1)
    abrasion = _edge(compression > .73, 2) * np.clip((crest - .18) / .82, 0, 1)
    healed = _edge((compression > .48) & (compression < .58), 1) * np.clip((1 - shear) * crest, 0, 1)

    # Pore valves are actual paired relief minima selected by stress phase.
    minima = height <= cv2.erode(height, np.ones((7, 7), np.uint8))
    selector = np.cos(11.0 * x + 17.0 * y + 3.0 * theta) > .93
    pore_core = np.uint8(minima & selector & (order > .24))
    pore_a = cv2.dilate(pore_core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 3)))
    pore_b = np.roll(cv2.dilate(pore_core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 3))), 4, axis=1)
    pores = np.maximum(pore_a, pore_b).astype(np.float32)
    height -= .055 * pores

    return height, theta, {
        "saddle_wrinkles": saddle.astype(np.float32),
        "paired_pore_valves": pores,
        "abrasion_crescents": abrasion.astype(np.float32),
        "scar_bridges": scar.astype(np.float32),
        "compression_zones": compression_zone.astype(np.float32),
        "shear_slips": slip.astype(np.float32),
        "healed_fold_lips": healed.astype(np.float32),
        "wrinkle_crests": crest.astype(np.float32),
    }


def _render(angle_b=False):
    height, theta, masks = _surface()
    gy, gx = np.gradient(height)
    nz = np.full_like(height, .34)
    length = np.sqrt(gx * gx + gy * gy + nz * nz)
    nx, ny, nz = -gx / length, -gy / length, nz / length
    if angle_b:
        light = np.clip(-.54 * nx + .28 * ny + .80 * nz, 0, 1)
        travel = _norm(theta / np.pi + .52 * nx - .36 * ny + .24 * height)
        palette = PALETTE_B
    else:
        light = np.clip(.46 * nx - .37 * ny + .82 * nz, 0, 1)
        travel = _norm(theta / np.pi - .41 * nx + .31 * ny + .24 * height)
        palette = PALETTE_A
    paint = _ramp(travel, palette) * (.23 + .88 * light[..., None])
    rim = np.clip((1 - nz) ** 1.3, 0, 1)
    paint += rim[..., None] * np.asarray((.17, .52, .46) if not angle_b else
                                         (.55, .16, .38), np.float32) * .34
    accents = (
        ("saddle_wrinkles", (.08, .19, .20), (.31, .07, .27), .26),
        ("paired_pore_valves", (.015, .025, .030), (.035, .010, .045), .72),
        ("abrasion_crescents", (.86, .76, .49), (.52, .89, .75), .37),
        ("scar_bridges", (.46, .23, .14), (.18, .42, .56), .34),
        ("shear_slips", (.80, .55, .28), (.45, .82, .65), .29),
        ("healed_fold_lips", (.91, .83, .62), (.72, .91, .84), .31),
    )
    for name, ca, cb, alpha in accents:
        mask = masks[name][..., None]
        color = np.asarray(cb if angle_b else ca, np.float32)
        paint = paint * (1 - mask * alpha) + color * mask * alpha
    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/coarse_hide_stress_i1")
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
    crop = native_a[704:1216, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID, "module": __name__, "attempt": 81,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {name: float((mask > .08).mean()) for name, mask in masks.items()},
        "owner_accepted": False, "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-coarse-hide-stress-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
