# -*- coding: utf-8 -*-
"""Isolated native-2048 Lime Diatom close-cropped pennate-valve study.

SPB-105 / Wilds attempt 87 / 2026-08-25. One oblique off-canvas frustule valve
owns the sheet: a dimensional silica hull carries a curved raphe, unequal
costae/striae, central and terminal nodules, areola slots, girdle bands, chipped
margins and repair bridges. Local line/slot thickness is 8--32 px at native.
This replaces repeated boat/capsule carpets with one causal shell hierarchy;
there is no RNG, noise floor, valve stamp field, paver or shared composer.

Native-2048 verdict: REJECTED. Full contact is a regimented lime comb/zipper
of parallel striae split by one central rail. The 3D hull, nodules, areolae,
girdle bands, chips and bridges remain tiny decorations and do not create
fractured silica hierarchy. Frozen before spec/M7/runtime. No valve, stria,
spacing, curvature, palette, raphe, event, scale, spec or noise repair is
authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_lime_diatom"
ATTEMPT = 87
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (3, 7, 16), (5, 20, 35), (6, 40, 54), (8, 65, 68),
    (11, 93, 75), (19, 123, 75), (34, 153, 68), (56, 181, 59),
    (85, 204, 54), (120, 220, 59), (159, 230, 75), (196, 229, 99),
    (224, 214, 133), (240, 184, 172), (228, 143, 216),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (17, 3, 24), (40, 4, 47), (68, 6, 65), (98, 10, 76),
    (128, 17, 81), (158, 29, 82), (187, 45, 78), (212, 65, 72),
    (232, 89, 69), (244, 119, 72), (246, 153, 84), (235, 186, 106),
    (211, 214, 136), (174, 230, 172), (125, 228, 205),
], np.float32) / 255.0


def _coords():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    cx, cy, angle = 478.0, 536.0, -.39
    cr, sr = np.cos(angle), np.sin(angle)
    dx, dy = xx - cx, yy - cy
    u, v = dx * cr + dy * sr, -dx * sr + dy * cr
    rx, ry, p = 1090.0, 468.0, 2.35
    q = (np.abs(u / rx) ** p + np.abs(v / ry) ** p) ** (1.0 / p)
    return xx, yy, u, v, q, (cx, cy, angle, cr, sr, rx, ry, p)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    xx, yy, u, v, q, params = _coords()
    cx, cy, angle, cr, sr, rx, ry, p = params
    inside = q < 1.0
    depth = np.sqrt(np.clip(1.0 - q * q, 0, 1))
    gy, gx = np.gradient(depth)
    nz0 = np.full_like(depth, .018)
    length = np.sqrt(gx * gx + gy * gy + nz0 * nz0)
    nx, ny, nz = -gx / length, -gy / length, nz0 / length
    if angle_b:
        light = np.clip(-.49 * nx + .35 * ny + .80 * nz, 0, 1)
        travel = (u / (2 * rx) + .5 + .27 * nx - .23 * ny + .21) % 1.0
        bg = np.asarray((.012, .002, .019), np.float32)
    else:
        light = np.clip(.52 * nx - .31 * ny + .79 * nz, 0, 1)
        travel = (u / (2 * rx) + .5 - .24 * nx + .29 * ny) % 1.0
        bg = np.asarray((.002, .006, .014), np.float32)
    pu = travel * 14
    pi = np.minimum(pu.astype(np.int32), 13)
    pf = (pu - pi)[..., None]
    paint = np.zeros((WORK, WORK, 3), np.float32) + bg
    body = (palette[pi] * (1 - pf) + palette[pi + 1] * pf) * (.18 + .92 * light[..., None])
    paint[inside] = body[inside]

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "silica_hull", "curved_raphe", "costae_striae", "central_nodule",
        "terminal_nodules", "areola_slots", "girdle_bands", "chipped_margins",
        "repair_bridges")}
    masks["silica_hull"][inside] = 255

    def world(points):
        points = np.asarray(points, np.float32)
        x = cx + points[:, 0] * cr - points[:, 1] * sr
        y = cy + points[:, 0] * sr + points[:, 1] * cr
        return np.rint(np.stack((x, y), axis=1)).astype(np.int32)

    # Unequal transverse anatomy follows the actual superellipse width at each
    # longitudinal position; no repeated valve placement exists.
    for j, su in enumerate(np.linspace(-1000, 1000, 174)):
        span = ry * max(0.0, 1.0 - abs(su / rx) ** p) ** (1.0 / p)
        if span < 9:
            continue
        bend = 7.0 * np.sin(su / 83.0) + 4.0 * np.sin(su / 31.0)
        raphe = 9.0 * np.sin(su / 141.0) + 3.0 * np.sin(su / 47.0)
        gap = 10.0 + (j * 7) % 8
        color = tuple(float(x) for x in np.clip(palette[(j * 5 + (4 if angle_b else 0)) % 15] * 1.13, 0, 1))
        width = 2 + (j % 3)
        for side in (-1, 1):
            end = side * (span - 5)
            pts = world(((su, raphe + side * gap),
                         (su + bend * .28, side * span * .46 + raphe),
                         (su + bend, end)))
            cv2.polylines(paint, [pts], False, color, width, cv2.LINE_AA)
            cv2.polylines(masks["costae_striae"], [pts], False, 255, width, cv2.LINE_AA)
            if j % 4 == 0:
                for frac in (.31, .56, .79):
                    pv = raphe + side * (gap + (abs(end) - gap) * frac)
                    pp = world(((su + bend * frac, pv),))[0]
                    axes = (2 + j % 3, 1 + (j // 3) % 2)
                    cv2.ellipse(paint, tuple(pp), axes, int(np.degrees(angle)), 0, 360,
                                tuple(float(x) for x in bg), -1, cv2.LINE_AA)
                    cv2.ellipse(masks["areola_slots"], tuple(pp), axes,
                                int(np.degrees(angle)), 0, 360, 255, -1, cv2.LINE_AA)

    raphe_pts = world([(su, 9 * np.sin(su / 141.0) + 3 * np.sin(su / 47.0))
                       for su in np.linspace(-1070, 1070, 300)])
    cv2.polylines(paint, [raphe_pts], False, tuple(float(x) for x in bg), 8, cv2.LINE_AA)
    cv2.polylines(paint, [raphe_pts], False,
                  tuple(float(x) for x in np.clip(palette[12] * 1.15, 0, 1)), 2, cv2.LINE_AA)
    cv2.polylines(masks["curved_raphe"], [raphe_pts], False, 255, 8, cv2.LINE_AA)

    edge1 = np.uint8(np.abs(q - .965) < .005) * 255
    edge2 = np.uint8(np.abs(q - .925) < .004) * 255
    bands = np.maximum(edge1, edge2)
    paint[bands > 0] = np.clip(palette[11] * 1.12, 0, 1)
    masks["girdle_bands"] = bands

    for su, sv, r0, kind in ((0, 0, 13, "central"), (-930, 0, 8, "terminal"),
                              (930, 0, 8, "terminal")):
        point = tuple(world(((su, sv),))[0])
        cv2.ellipse(paint, point, (r0, max(3, r0 // 3)), int(np.degrees(angle)), 0, 360,
                    tuple(float(x) for x in np.clip(palette[13] * 1.15, 0, 1)), -1, cv2.LINE_AA)
        key = "central_nodule" if kind == "central" else "terminal_nodules"
        cv2.ellipse(masks[key], point, (r0, max(3, r0 // 3)), int(np.degrees(angle)),
                    0, 360, 255, -1, cv2.LINE_AA)

    for j, (su, side) in enumerate(((-760, -1), (-438, 1), (-112, -1),
                                     (257, 1), (536, -1), (806, 1))):
        span = ry * max(0.0, 1.0 - abs(su / rx) ** p) ** (1.0 / p)
        point = tuple(world(((su, side * (span - 5)),))[0])
        cv2.ellipse(paint, point, (7 + j % 4, 4), int(np.degrees(angle)) + j * 17,
                    0, 360, tuple(float(x) for x in bg), -1, cv2.LINE_AA)
        cv2.ellipse(masks["chipped_margins"], point, (7 + j % 4, 4),
                    int(np.degrees(angle)) + j * 17, 0, 360, 255, -1, cv2.LINE_AA)
        p0 = world(((su - 8, side * (span - 13)),))[0]
        p1 = world(((su + 8, side * (span - 13)),))[0]
        cv2.line(paint, tuple(p0), tuple(p1),
                 tuple(float(x) for x in np.clip(palette[(j + 8) % 15] * 1.18, 0, 1)),
                 3, cv2.LINE_AA)
        cv2.line(masks["repair_bridges"], tuple(p0), tuple(p1), 255, 3, cv2.LINE_AA)
    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/lime_diatom_valve_i1")
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
    report = {"id": ID, "module": __name__, "attempt": ATTEMPT,
              "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
              "timings_s": timings,
              "deterministic": bool(all(np.array_equal(repeats[0], x) for x in repeats[1:])),
              "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
              "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, .95)),
              "coverage": {k: float((v > 8).mean()) for k, v in masks.items()},
              "owner_accepted": False, "production_wired": False}
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-lime-diatom-valve-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
