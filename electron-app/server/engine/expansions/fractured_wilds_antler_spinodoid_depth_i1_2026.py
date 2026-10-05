# -*- coding: utf-8 -*-
"""Isolated native-2048 Antler Bone anisotropic-spinodoid depth study.

SPB-105 / Wilds attempt 83 / 2026-08-25.  A deterministic seven-wave 3D
spinodoid is ray-cast through sixty-four depth slices.  This tests continuous
load-remodelled trabecular solid rather than a 2D branch, stroke swarm, ring
scatter, paver, sampled-noise texture or recoloured scalar map.  Depth and
surface differential geometry causally expose trabecular plates, rod necks,
marrow windows, remodeling terraces, osteocyte lacunae, mineral rims,
microcrack lips and healed bridges.  Contact scale is 8--32 px at 2048.

Native-2048 verdict: REJECTED.  The ray-cast volume is source-distinct but the
visible contact collapses into a homogeneous carpet of repeated loop/squiggle
islands with no load-bearing hierarchy; it reads as foam/static instead of
dimensional bone.  Exact cold paint also misses budget at `3.014-3.220 s`.
Frozen before spec/M7/runtime.  No wave, depth, threshold, frequency, palette,
lighting, anatomy, performance, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fc_antler_bone"
ATTEMPT = 83
WORK = 768
NATIVE = 2048
DEPTH_STEPS = 64

PALETTE_A = np.asarray([
    (5, 8, 15), (13, 18, 29), (27, 31, 45), (48, 47, 61),
    (74, 65, 77), (102, 85, 92), (131, 106, 104), (158, 129, 114),
    (181, 153, 123), (201, 177, 134), (217, 199, 150), (229, 218, 173),
    (236, 231, 200), (223, 238, 224), (185, 233, 229),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 8, 20), (6, 19, 42), (7, 36, 65), (8, 59, 85),
    (9, 86, 99), (14, 115, 106), (28, 145, 105), (52, 174, 101),
    (87, 199, 98), (128, 218, 103), (171, 229, 118), (210, 229, 143),
    (238, 213, 172), (247, 178, 203), (228, 134, 232),
], np.float32) / 255.0

# Incommensurate directions and z-rates; explicit constants are a material
# recipe, not a random seed.  Shorter transverse wavelengths form rods while
# slower load-axis waves keep them connected into plates.
WAVES = (
    (.214, .071, .193, 1.00, .13),
    (-.083, .246, .171, .91, 1.07),
    (.169, -.192, .227, .84, 2.11),
    (.298, .117, -.149, .71, .67),
    (-.224, -.137, .263, .66, 1.59),
    (.119, .319, .183, .58, 2.73),
    (-.311, .056, .209, .52, 2.29),
)


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _raycast():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Slowly varying explicit load warp bends the volume without making a 2D
    # carrier.  Every visible point still comes from the first solid crossing.
    wx = xx + 13.0 * np.sin(yy / 91.0) + 5.0 * np.sin((xx + yy) / 143.0)
    wy = yy + 11.0 * np.sin(xx / 117.0) - 6.0 * np.cos((xx - yy) / 157.0)
    bases = []
    for kx, ky, _kz, _gain, phase in WAVES:
        a = kx * wx + ky * wy + phase
        bases.append((np.sin(a).astype(np.float32), np.cos(a).astype(np.float32)))

    hit = np.zeros((WORK, WORK), bool)
    depth = np.full((WORK, WORK), DEPTH_STEPS - 1, np.float32)
    surface_value = np.zeros((WORK, WORK), np.float32)
    previous = np.zeros((WORK, WORK), np.float32)
    crossings = np.zeros((WORK, WORK), np.uint8)
    for zi in range(DEPTH_STEPS):
        z = zi * 1.17
        field = np.zeros((WORK, WORK), np.float32)
        for (sx, cx), (_kx, _ky, kz, gain, _phase) in zip(bases, WAVES):
            az = kz * z
            field += gain * (sx * np.cos(az) + cx * np.sin(az))
        # A second helicoidal invariant joins narrow rods into load-bearing
        # plates without a separate texture or noise floor.
        field += .46 * np.sin(.113 * wx - .087 * wy + .271 * z
                              + .51 * np.sin(.043 * wx + .052 * wy - .119 * z))
        threshold = .73 + .16 * np.sin((wx - .37 * wy) / 131.0)
        solid = field > threshold
        crossings += np.uint8((field > threshold) != (previous > threshold))
        new = (~hit) & solid
        depth[new] = zi
        surface_value[new] = field[new] - threshold[new]
        hit |= new
        previous = field
    return depth, hit, surface_value, crossings


def _surface_anatomy(depth, hit, excess, crossings):
    smooth = cv2.GaussianBlur(depth, (0, 0), .72)
    gy, gx = np.gradient(smooth)
    lap = cv2.Laplacian(smooth, cv2.CV_32F, ksize=3)
    slope = np.hypot(gx, gy)
    void = (~hit).astype(np.float32)
    # Literal depth-derived material anatomy; none is an independent scatter.
    terraces = (np.abs(np.sin(depth * np.pi / 3.7)) > .86).astype(np.float32) * hit
    necks = np.clip((slope - 1.7) / 5.3, 0, 1) * hit
    rims = cv2.dilate(np.uint8(void), np.ones((5, 5), np.uint8)).astype(np.float32) * hit
    lacunae = ((crossings >= 7) & (excess < .22) & hit).astype(np.uint8)
    lacunae = cv2.morphologyEx(lacunae, cv2.MORPH_OPEN,
                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))).astype(np.float32)
    cracks = np.clip((np.abs(lap) - 7.0) / 18.0, 0, 1) * hit
    bridges = ((crossings >= 10) & (slope < 1.35) & hit).astype(np.float32)
    scallops = np.clip((-lap - 4.0) / 15.0, 0, 1) * hit
    return gx, gy, {
        "trabecular_plates": hit.astype(np.float32),
        "rod_necks": necks.astype(np.float32),
        "marrow_windows": void,
        "remodeling_terraces": terraces,
        "osteocyte_lacunae": lacunae,
        "mineral_rims": rims,
        "microcrack_lips": cracks.astype(np.float32),
        "healed_bridges": bridges,
        "resorption_scallops": scallops.astype(np.float32),
    }


def _render(angle_b=False):
    depth, hit, excess, crossings = _raycast()
    gx, gy, masks = _surface_anatomy(depth, hit, excess, crossings)
    nz0 = np.full_like(depth, 2.4)
    length = np.sqrt(gx * gx + gy * gy + nz0 * nz0)
    nx, ny, nz = -gx / length, -gy / length, nz0 / length
    if angle_b:
        light = np.clip(-.48 * nx + .39 * ny + .78 * nz, 0, 1)
        travel = (depth / (DEPTH_STEPS - 1) + .23 * nx - .31 * ny + .17) % 1.0
        palette = PALETTE_B
        marrow = np.asarray((.004, .010, .025), np.float32)
    else:
        light = np.clip(.53 * nx - .31 * ny + .79 * nz, 0, 1)
        travel = (depth / (DEPTH_STEPS - 1) - .28 * nx + .21 * ny) % 1.0
        palette = PALETTE_A
        marrow = np.asarray((.009, .006, .013), np.float32)
    paint = _ramp(travel, palette) * (.18 + .93 * light[..., None])
    paint[~hit] = marrow
    accents = (
        ("remodeling_terraces", (.92, .80, .57), (.54, .92, .77), .34),
        ("osteocyte_lacunae", (.02, .01, .02), (.01, .03, .05), .78),
        ("mineral_rims", (.96, .92, .78), (.70, .98, .91), .52),
        ("microcrack_lips", (.20, .07, .08), (.07, .18, .26), .58),
        ("healed_bridges", (.76, .51, .27), (.34, .76, .65), .31),
        ("resorption_scallops", (.38, .18, .14), (.14, .36, .45), .26),
    )
    for name, ca, cb, alpha in accents:
        m = masks[name][..., None]
        c = np.asarray(cb if angle_b else ca, np.float32)
        paint = paint * (1 - m * alpha) + c * m * alpha
    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/antler_spinodoid_depth_i1")
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
    crop = native_a[704:1344, 704:1344]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID, "module": __name__, "attempt": ATTEMPT,
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
    return "fractured-wilds-antler-spinodoid-depth-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
