# -*- coding: utf-8 -*-
"""Isolated native-2048 White Whorl interlocked-cup study.

SPB-105 / Wilds attempt 80 / 2026-08-25. Owner verdict applied: lazy recolors
and repeated spec silhouettes waste app space.  A deterministic coupled growth
orbit lays unequal 16--32 px asymmetric gardenia cups into one overlapping
surface.  Cup bodies, shared overlap lips, fold saddles, throats, dew rims,
torn margins and compressed cushions are literal local geometry.  No RNG,
sampled noise, bubble/circle stamps, radial flower hubs or shared composer.

Native-2048 verdict: REJECTED. The coupled orbit locks into sparse repeating
caterpillar/bead chains and isolated loops over inert dark ground. Five cup
silhouettes collapse into one tiny unit, never forming a shared quilt; A/B is
also negligible. Frozen before spec/M7/runtime. No orbit, site, count, density,
shape, angle, palette, ground, scale, spec, hash, jitter or noise repair is
authorized.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fbl_white_whorl"
WORK = 1024
NATIVE = 2048
COUNT = 6800

PALETTE_A = np.asarray([
    (22, 18, 38), (43, 33, 62), (72, 58, 86), (105, 91, 117),
    (139, 126, 147), (171, 159, 174), (199, 189, 199), (221, 214, 219),
    (239, 235, 232), (250, 248, 239), (247, 244, 216), (235, 231, 186),
    (213, 218, 178), (183, 205, 187), (150, 184, 194),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (24, 20, 51), (47, 37, 83), (77, 53, 110), (111, 70, 132),
    (148, 88, 148), (185, 111, 158), (216, 139, 165), (237, 170, 177),
    (247, 201, 193), (243, 226, 211), (218, 239, 218), (181, 238, 222),
    (138, 222, 225), (100, 195, 220), (76, 157, 204),
], np.float32) / 255.0


SHAPES = (
    np.asarray(((-1.00, 0.00), (-.67, -.45), (-.18, -.62), (.40, -.47),
                (1.00, 0.00), (.34, .54), (-.22, .67), (-.72, .40)), np.float32),
    np.asarray(((-.92, -.10), (-.54, -.58), (.02, -.49), (.47, -.67),
                (1.00, -.04), (.51, .42), (.05, .59), (-.46, .66), (-1.0, .22)), np.float32),
    np.asarray(((-1.0, .05), (-.56, -.52), (-.08, -.29), (.29, -.64),
                (.95, -.08), (.54, .42), (.02, .31), (-.39, .64), (-.91, .37)), np.float32),
    np.asarray(((-.96, -.03), (-.64, -.55), (-.12, -.70), (.28, -.39),
                (.92, -.18), (.76, .29), (.22, .67), (-.31, .47), (-.82, .53)), np.float32),
    np.asarray(((-1.0, .0), (-.52, -.34), (-.17, -.65), (.39, -.57),
                (.96, -.04), (.51, .22), (.19, .65), (-.43, .58), (-.78, .27)), np.float32),
)


@lru_cache(maxsize=1)
def _cups():
    rows = []
    x, y = .137, .381
    prev_x, prev_y = x, y
    for i in range(COUNT):
        # Coupled twist map: a chronology, not independent random/hash sites.
        x = (x + .6180339887498948 + .073 * np.sin(2 * np.pi * y)
             + .019 * np.sin(6 * np.pi * prev_x)) % 1.0
        y = (y + .4142135623730950 + .061 * np.sin(2 * np.pi * x)
             - .017 * np.sin(8 * np.pi * prev_y)) % 1.0
        dx = ((x - prev_x + .5) % 1.0) - .5
        dy = ((y - prev_y + .5) % 1.0) - .5
        px, py = 8 + x * (WORK - 16), 8 + y * (WORK - 16)
        angle = np.arctan2(dy, dx) + .42 * np.sin(i * .754877666)
        length = 8.0 + (i * 7) % 9
        width = 6.0 + (i * 11) % 7
        species = (i * 3 + int(x * 11) + int(y * 13)) % len(SHAPES)
        state = (i * 7 + species * 3) % 13
        depth = (.5 + .5 * np.sin(i * 2.399963229728653 + x * 5.0 - y * 7.0))
        rows.append((depth, px, py, angle, length, width, species, state, i))
        prev_x, prev_y = x, y
    rows.sort(key=lambda row: row[0])
    return tuple(rows)


def _transform(shape, center, angle, length, width):
    ca, sa = np.cos(angle), np.sin(angle)
    x = shape[:, 0] * length * .5
    y = shape[:, 1] * width * .5
    pts = np.stack((center[0] + ca * x - sa * y,
                    center[1] + sa * x + ca * y), axis=1)
    return np.rint(pts).astype(np.int32)


def _blend_poly(image, poly, color, alpha):
    x, y, w, h = cv2.boundingRect(poly)
    x0, y0 = max(0, x - 2), max(0, y - 2)
    x1, y1 = min(WORK, x + w + 2), min(WORK, y + h + 2)
    if x0 >= x1 or y0 >= y1:
        return None
    local = poly - np.asarray((x0, y0), np.int32)
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mask, [local], 255, cv2.LINE_AA)
    area = mask > 0
    a = mask[area].astype(np.float32)[:, None] / 255.0 * alpha
    roi = image[y0:y1, x0:x1]
    roi[area] = roi[area] * (1 - a) + color * a
    return x0, x1, y0, y1, mask


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    base = .5 + .5 * np.sin(xx / 233.0 - yy / 271.0)
    ground0 = np.asarray((.045, .035, .065) if not angle_b else (.055, .027, .075), np.float32)
    ground1 = np.asarray((.15, .12, .17) if not angle_b else (.17, .10, .19), np.float32)
    paint = ground0 + (ground1 - ground0) * base[..., None] * .32
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "cup_bodies", "overlap_lips", "fold_saddles", "central_throats",
        "dew_rims", "torn_margins", "compressed_cushions")}
    depth_field = np.zeros((WORK, WORK), np.uint8)
    phase_field = np.zeros((WORK, WORK), np.uint8)

    for depth, px, py, angle, length, width, species, state, i in _cups():
        center = np.asarray((px, py), np.float32)
        shape = SHAPES[species]
        poly = _transform(shape, center, angle, length, width)
        phase = (species * 3 + state + int(depth * 9) + (5 if angle_b else 0)) % 15
        optical = .62 + .38 * abs(np.cos(angle - (.71 if angle_b else 2.24)))
        color = np.clip(palette[phase] * optical, 0, 1)
        info = _blend_poly(paint, poly, color, .86)
        if info is None:
            continue
        x0, x1, y0, y1, local = info
        masks["cup_bodies"][y0:y1, x0:x1] = np.maximum(
            masks["cup_bodies"][y0:y1, x0:x1], local)
        cv2.fillPoly(depth_field, [poly], int(depth * 255), cv2.LINE_AA)
        cv2.fillPoly(phase_field, [poly], int(phase), cv2.LINE_8)

        # The brighter overlap lip belongs to the outer two-thirds of the cup.
        ca, sa = np.cos(angle), np.sin(angle)
        u = np.asarray((ca, sa), np.float32)
        n = np.asarray((-sa, ca), np.float32)
        lip0 = center - u * length * .29 - n * width * .18
        lip1 = center + u * length * .35 + n * width * .23
        lip_color = tuple(float(v) for v in np.clip(palette[(phase + 3) % 15] * 1.18, 0, 1))
        cv2.line(paint, tuple(np.rint(lip0).astype(int)), tuple(np.rint(lip1).astype(int)),
                 lip_color, 2, cv2.LINE_AA)
        cv2.line(masks["overlap_lips"], tuple(np.rint(lip0).astype(int)),
                 tuple(np.rint(lip1).astype(int)), 255, 2, cv2.LINE_AA)

        if state in (0, 4, 8, 11):
            saddle0 = center - n * width * .34
            saddle1 = center + n * width * .34
            shadow = tuple(float(v) for v in ground0)
            cv2.line(paint, tuple(np.rint(saddle0).astype(int)),
                     tuple(np.rint(saddle1).astype(int)), shadow, 2, cv2.LINE_AA)
            cv2.line(masks["fold_saddles"], tuple(np.rint(saddle0).astype(int)),
                     tuple(np.rint(saddle1).astype(int)), 255, 2, cv2.LINE_AA)
        if state in (1, 5, 9):
            throat = center - u * length * .13
            axes = (2 + state % 2, 1 + species % 2)
            cv2.ellipse(paint, tuple(np.rint(throat).astype(int)), axes,
                        int(np.degrees(angle)), 0, 360, tuple(float(v) for v in ground0),
                        -1, cv2.LINE_AA)
            cv2.ellipse(masks["central_throats"], tuple(np.rint(throat).astype(int)), axes,
                        int(np.degrees(angle)), 0, 360, 255, -1, cv2.LINE_AA)
        if state in (2, 6, 10):
            rim = center + u * length * .30 - n * width * .12
            cv2.circle(paint, tuple(np.rint(rim).astype(int)), 2,
                       tuple(float(v) for v in np.clip(palette[(phase + 6) % 15] * 1.25, 0, 1)),
                       -1, cv2.LINE_AA)
            cv2.circle(masks["dew_rims"], tuple(np.rint(rim).astype(int)), 2,
                       255, -1, cv2.LINE_AA)
        if state in (3, 7, 12):
            tip = center + u * length * .45
            tear0, tear1 = tip - n * width * .25, tip + n * width * .13
            cv2.line(paint, tuple(np.rint(tear0).astype(int)), tuple(np.rint(tear1).astype(int)),
                     tuple(float(v) for v in ground0), 2, cv2.LINE_AA)
            cv2.line(masks["torn_margins"], tuple(np.rint(tear0).astype(int)),
                     tuple(np.rint(tear1).astype(int)), 255, 2, cv2.LINE_AA)
        if i % 17 == 0:
            cushion = _transform(shape, center - u * 2.0, angle,
                                 length * .53, width * .48)
            c = np.clip(palette[(phase + 10) % 15] * .72, 0, 1)
            _blend_poly(paint, cushion, c, .63)
            cv2.fillPoly(masks["compressed_cushions"], [cushion], 255, cv2.LINE_AA)

    return (np.clip(paint, 0, 1),
            {k: v.astype(np.float32) / 255.0 for k, v in masks.items()},
            {"depth": depth_field, "phase": phase_field})


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/white_whorl_cupquilt_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, masks, _fields = _render(False)
        repeats.append(_u8(_native(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _, _ = _render(True)
    native_a, native_b = repeats[0], _u8(_native(angle_b))
    for label, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{label}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1216, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID, "module": __name__, "attempt": 80,
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
    return "fractured-wilds-white-whorl-cupquilt-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
