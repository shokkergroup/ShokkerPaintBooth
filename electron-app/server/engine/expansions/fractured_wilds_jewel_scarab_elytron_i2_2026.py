# -*- coding: utf-8 -*-
"""Isolated native-2048 Jewel Scarab close-cropped elytron study.

SPB-105 / Wilds attempt 85 / 2026-08-25.  The recent scarab-cascade math is
used only as fine cuticle microrelief inside one explicit off-centre 3D elytron;
it never owns the palette or becomes a raw texture finish.  Surface normals,
one curved shell margin and attached abrasion windows, puncture throats,
phase-slip lips, hinge wedges, mineral caps and fracture stops form the visible
material history.  Local marks remain 8--32 px at 2048.  No RNG, noise floor,
repeated beetle stamp, bilateral circuit, rib wallpaper or shared composer.

Native-2048 verdict: REJECTED.  The recent scarab-cascade relief overwhelms the
authored shell and becomes homogeneous green diagonal crosshatch/static. Four
soft brown abrasion windows and one margin merely decorate that carrier; the
3D elytron, punctures, slips, wedges, caps and stops do not form readable
hierarchy. Frozen before spec/M7/runtime. No cascade, relief, normal, palette,
window, seam, anatomy, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np

from . import gradient_math_wave_2026 as gradient_math


ID = "fmo_jewel_scarab"
ATTEMPT = 85
WORK = 768
NATIVE = 2048

PALETTE_A = np.asarray([
    (2, 5, 16), (4, 14, 38), (4, 32, 63), (4, 57, 82),
    (4, 86, 92), (8, 117, 91), (20, 148, 83), (42, 178, 70),
    (72, 203, 61), (109, 222, 61), (151, 231, 74), (191, 229, 98),
    (222, 211, 131), (239, 177, 171), (228, 133, 218),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (18, 2, 24), (43, 3, 48), (72, 5, 67), (103, 8, 78),
    (135, 14, 83), (166, 24, 83), (194, 39, 79), (218, 59, 72),
    (236, 84, 67), (247, 114, 69), (249, 148, 79), (240, 183, 101),
    (216, 212, 134), (178, 230, 173), (128, 229, 209),
], np.float32) / 255.0


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _edge(mask, radius=1):
    src = np.uint8(mask > .5)
    k = np.ones((radius * 2 + 1, radius * 2 + 1), np.uint8)
    return (cv2.dilate(src, k) - cv2.erode(src, k)).astype(np.float32) / 255.0


def _surface():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    cx, cy, rx, ry = 302.0, 421.0, 812.0, 746.0
    x, y = (xx - cx) / rx, (yy - cy) / ry
    rr = x * x + y * y
    dome = np.sqrt(np.clip(1.0 - rr, .012, 1.0))

    # Existing new math supplies only shallow physical relief.  The close crop,
    # lighting and every named failure event are authored here.
    relief = gradient_math._scarab_cascade(WORK, WORK, 0x51CA8AB)
    relief = cv2.GaussianBlur(np.asarray(relief, np.float32), (0, 0), .62)
    height = dome + (relief - .5) * .036 * (0.34 + .66 * dome)
    gy, gx = np.gradient(height)

    margin_x = 662.0 + 34.0 * np.sin(yy / 91.0) + 13.0 * np.sin(yy / 37.0)
    margin_dist = xx - margin_x
    margin = np.clip((5.0 - np.abs(margin_dist)) / 5.0, 0, 1)

    abrasion = np.zeros((WORK, WORK), np.float32)
    windows = ((142, 154, 74, 43, -.24), (478, 276, 92, 52, .31),
               (330, 587, 61, 86, -.61), (626, 535, 47, 69, .17))
    for ax, ay, arx, ary, rot in windows:
        cr, sr = np.cos(rot), np.sin(rot)
        dx, dy = xx - ax, yy - ay
        u, v = dx * cr + dy * sr, -dx * sr + dy * cr
        q = (u / arx) ** 2 + (v / ary) ** 2
        abrasion = np.maximum(abrasion, np.clip((1.0 - q) / .24, 0, 1))
    abrasion_rim = _edge(abrasion > .18, 2)

    # Puncture throats are extrema of the attached cuticle relief, not an
    # independent point cloud. Their area is intentionally subordinate.
    minima = relief <= cv2.erode(relief, np.ones((7, 7), np.uint8))
    selector = np.cos(xx * .083 + yy * .117 + relief * 9.0) > .955
    puncture = np.uint8(minima & selector & (abrasion < .12))
    puncture = cv2.dilate(puncture, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 3))).astype(np.float32)

    phase_slip = np.clip(np.abs(cv2.Laplacian(relief, cv2.CV_32F, ksize=3)) - .08, 0, .18) / .18
    phase_slip *= np.clip((dome - .18) / .82, 0, 1)
    mineral_caps = np.clip((relief - .79) / .21, 0, 1) * (abrasion < .12)

    hinge_wedges = np.zeros((WORK, WORK), np.uint8)
    fracture_stops = np.zeros((WORK, WORK), np.uint8)
    for j, sy in enumerate((66, 141, 229, 326, 431, 544, 655, 734)):
        sx = int(662 + 34 * np.sin(sy / 91.0) + 13 * np.sin(sy / 37.0))
        side = -1 if j % 3 else 1
        pts = np.asarray(((sx - 3, sy - 7), (sx + side * (7 + j % 4), sy),
                          (sx - 2, sy + 7)), np.int32)
        cv2.fillConvexPoly(hinge_wedges, pts, 255, cv2.LINE_AA)
        cv2.ellipse(fracture_stops, (sx - 12 * side, sy + 11), (5 + j % 3, 3),
                    17 * j, 25, 250, 255, 2, cv2.LINE_AA)

    return height, gx, gy, relief, {
        "elytron_mass": np.ones((WORK, WORK), np.float32),
        "curved_margin": margin.astype(np.float32),
        "abrasion_windows": abrasion,
        "abrasion_rims": abrasion_rim,
        "puncture_throats": puncture,
        "phase_slip_lips": phase_slip.astype(np.float32),
        "hinge_wedges": hinge_wedges.astype(np.float32) / 255.0,
        "mineral_caps": mineral_caps.astype(np.float32),
        "fracture_stops": fracture_stops.astype(np.float32) / 255.0,
    }


def _render(angle_b=False):
    height, gx, gy, relief, masks = _surface()
    nz0 = np.full_like(height, .011)
    length = np.sqrt(gx * gx + gy * gy + nz0 * nz0)
    nx, ny, nz = -gx / length, -gy / length, nz0 / length
    if angle_b:
        light = np.clip(-.52 * nx + .32 * ny + .79 * nz, 0, 1)
        travel = (np.arctan2(ny, nx) / (2 * np.pi) + .5
                  + .31 * nx - .24 * ny + .18 * relief + .23) % 1.0
        palette = PALETTE_B
    else:
        light = np.clip(.47 * nx - .39 * ny + .80 * nz, 0, 1)
        travel = (np.arctan2(ny, nx) / (2 * np.pi) + .5
                  - .27 * nx + .29 * ny + .18 * relief) % 1.0
        palette = PALETTE_A
    paint = _ramp(travel, palette) * (.17 + .94 * light[..., None])
    accents = (
        ("curved_margin", (.006, .008, .017), (.020, .004, .026), .86),
        ("abrasion_windows", (.08, .045, .035), (.035, .075, .090), .62),
        ("abrasion_rims", (.94, .78, .47), (.51, .94, .80), .54),
        ("puncture_throats", (.003, .005, .011), (.010, .003, .016), .86),
        ("phase_slip_lips", (.82, .59, .30), (.40, .83, .70), .29),
        ("hinge_wedges", (.95, .90, .68), (.68, .96, .88), .68),
        ("mineral_caps", (.97, .88, .60), (.62, .98, .88), .31),
        ("fracture_stops", (.12, .04, .05), (.04, .12, .18), .76),
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
    out = Path("_wilds_fullres_progress_20260824/jewel_scarab_elytron_i2")
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
    return "fractured-wilds-jewel-scarab-elytron-i2: fail-closed pending native review"


if __name__ == "__main__":
    main()
