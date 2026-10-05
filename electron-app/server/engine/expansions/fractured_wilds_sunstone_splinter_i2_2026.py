# -*- coding: utf-8 -*-
"""Isolated native-2048 Sunstone suspended-splinter study.

SPB-105 / Wilds attempt 76 / 2026-08-25. Legacy bead chains and I1's dense
triangle paver are discarded. I2 uses a 15-color continuous optical field with
six deterministic crystallographic schools of overlapping translucent
splinters. Each unequal 8--32 px shard carries depth/shadow/glare plus one
attached history: hematite platelet, pullout socket, scratch, twin split,
cleavage ladder, chipped tip or reflection wake.

No RNG, sampled noise, FBM, tessellation, glitter dots, path carrier, shared
composer or recolor fallback.

Native-2048 verdict: REJECTED. The source reference's hierarchy depends on real
optical microflake and photographic depth; the procedural translation becomes
flat shard/confetti scatter over a broad gradient, with event icons. Frozen
before spec/M7/runtime. No count, shard, alpha, glow, palette, school, density,
scale, spec or noise repair is authorized.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_sunstone_glitter"
WORK = 1024
NATIVE = 2048
COUNT = 2650
TAU = 2.0 * np.pi

PALETTE_A = np.asarray([
    (5, 8, 25), (8, 19, 52), (9, 36, 82), (8, 60, 108),
    (7, 88, 126), (8, 119, 133), (15, 150, 132), (34, 179, 124),
    (67, 205, 115), (111, 225, 111), (161, 238, 120), (208, 242, 144),
    (244, 229, 177), (255, 194, 191), (242, 147, 216),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (22, 4, 23), (46, 5, 45), (75, 7, 66), (106, 10, 83),
    (138, 16, 96), (170, 25, 105), (199, 39, 110), (224, 57, 112),
    (242, 80, 115), (253, 108, 123), (255, 140, 139), (255, 174, 162),
    (248, 207, 191), (223, 231, 215), (172, 239, 229),
], np.float32) / 255.0


def _ramp(t, palette):
    q = np.clip(t, 0, 1) * (len(palette) - 1)
    lo = np.floor(q).astype(np.int32)
    hi = np.minimum(lo + 1, len(palette) - 1)
    f = (q - lo)[..., None]
    return palette[lo] * (1 - f) + palette[hi] * f


@lru_cache(maxsize=1)
def _shards():
    rows = []
    for i in range(COUNT):
        x = 7 + 1010 * ((i * .6180339887498948 + .027 * np.sin(i * .73)) % 1.0)
        y = 7 + 1010 * ((i * .7548776662466927 + .023 * np.sin(i * 1.11)) % 1.0)
        school = (i * 7 + i // 23) % 6
        director = (.24 + school * .49 + .38 * np.sin(x / 97.0 + y / 131.0)
                    + .17 * np.sin((x - y) / 61.0))
        length = 8 + (i * 11 + i // 17) % 9
        width = 4 + (i * 7 + i // 29) % 5
        skew = ((i * .4142135623730950) % 1.0 - .5) * .78
        axis = np.asarray([np.cos(director), np.sin(director)], np.float32)
        normal = np.asarray([-axis[1], axis[0]], np.float32)
        c = np.asarray([x, y], np.float32)
        poly = np.asarray([
            c - axis * length * .57,
            c - normal * width * .55 + axis * length * skew * .16,
            c + axis * length * .57,
            c + normal * width * .55 - axis * length * skew * .12,
        ], np.float32)
        state = (i * 13 + i // 31 + school * 3) % 11
        depth = ((i * .5698402909980532 + school * .13) % 1.0)
        rows.append((depth, np.rint(poly).astype(np.int32), c, axis, normal,
                     state, school, i, length, width))
    rows.sort(key=lambda item: item[0])
    return rows


def _blend_poly(image, poly, color, alpha):
    x, y, w, h = cv2.boundingRect(poly)
    x0, y0 = max(0, x - 2), max(0, y - 2)
    x1, y1 = min(WORK, x + w + 2), min(WORK, y + h + 2)
    if x1 <= x0 or y1 <= y0:
        return
    local = poly - np.asarray([x0, y0], np.int32)
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillConvexPoly(mask, local, 255, cv2.LINE_AA)
    a = (mask.astype(np.float32) / 255.0 * alpha)[..., None]
    roi = image[y0:y1, x0:x1]
    roi[:] = roi * (1 - a) + np.asarray(color, np.float32) * a


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    t = (.47 * xx / WORK + .36 * yy / WORK
         + .16 * np.sin(xx / 183.0 + yy / 227.0)
         + .11 * np.sin((xx - 1.4 * yy) / 149.0))
    t = (t - t.min()) / (float(np.ptp(t)) + 1e-7)
    paint = _ramp(t, palette) * (.49 + .26 * (1 - np.abs(t - .5) * 2)[..., None])
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "splinter_bodies", "hematite_platelets", "pullout_sockets",
        "scratch_shadows", "twin_flashes", "cleavage_ladders",
        "chipped_tips", "reflection_wakes")}
    glow = np.zeros((WORK, WORK), np.float32)

    for depth, poly, center, axis, normal, state, school, index, length, width in _shards():
        shadow_poly = np.rint(poly.astype(np.float32) + normal * (2.0 + depth * 2.1)).astype(np.int32)
        _blend_poly(paint, shadow_poly,
                    ((.006, .015, .025) if angle_b else (.012, .007, .012)),
                    .34 + .31 * depth)
        base_index = (school * 2 + index % 5 + (5 if angle_b else 0)) % 15
        body_color = palette[base_index] * (.76 + .28 * depth)
        _blend_poly(paint, poly, np.clip(body_color, 0, 1), .42 + .38 * depth)
        cv2.fillConvexPoly(masks["splinter_bodies"], poly, 255, cv2.LINE_AA)
        edge_color = ((.76, .97, .94) if angle_b else (.96, .89, .69))
        cv2.polylines(paint, [poly], True, edge_color, 1 + (index % 2), cv2.LINE_AA)
        spine0 = center - axis * length * .38
        spine1 = center + axis * length * .38
        cv2.line(paint, tuple(np.rint(spine0).astype(int)),
                 tuple(np.rint(spine1).astype(int)),
                 ((.91, .45, .83) if angle_b else (.64, .89, .93)),
                 1 + index % 2, cv2.LINE_AA)

        if state == 0:
            inner = np.rint(center + (poly.astype(np.float32) - center) * .55).astype(np.int32)
            _blend_poly(paint, inner,
                        ((.96, .25, .68) if angle_b else (.94, .54, .17)), .88)
            cv2.fillConvexPoly(masks["hematite_platelets"], inner, 255, cv2.LINE_AA)
        elif state == 1:
            inner = np.rint(center + (poly.astype(np.float32) - center) * .49).astype(np.int32)
            _blend_poly(paint, inner,
                        ((.008, .025, .04) if angle_b else (.018, .008, .006)), .97)
            cv2.fillConvexPoly(masks["pullout_sockets"], inner, 255, cv2.LINE_AA)
        elif state in (2, 3):
            span = max(4, min(8, width + 2))
            p0, p1 = center - normal * span, center + normal * span
            cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                     ((.02, .06, .08) if angle_b else (.13, .025, .01)),
                     2 + state % 2, cv2.LINE_AA)
            cv2.line(masks["scratch_shadows"], tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)), 255, 2 + state % 2, cv2.LINE_AA)
        elif state == 4:
            half = np.asarray([poly[0], poly[1], np.rint(center).astype(np.int32)])
            _blend_poly(paint, half,
                        ((.98, .82, .30) if angle_b else (.92, .20, .64)), .91)
            cv2.fillConvexPoly(masks["twin_flashes"], half, 255, cv2.LINE_AA)
        elif state == 5:
            for rung in (-3, 0, 3):
                c = center + axis * rung
                p0, p1 = c - normal * min(6, width), c + normal * min(6, width)
                cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                         ((.91, .96, .41) if angle_b else (1.0, .77, .29)), 2, cv2.LINE_AA)
                cv2.line(masks["cleavage_ladders"], tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)), 255, 2, cv2.LINE_AA)
        elif state == 6:
            tip = poly[2].astype(np.float32)
            chip = np.rint([tip, tip + (center - tip) * .54,
                            tip + normal * min(5, width)]).astype(np.int32)
            _blend_poly(paint, chip,
                        ((.01, .035, .05) if angle_b else (.05, .012, .007)), .98)
            cv2.fillConvexPoly(masks["chipped_tips"], chip, 255, cv2.LINE_AA)
        elif state in (7, 8):
            wake0 = center - axis * length * .2 + normal * width * .52
            wake1 = center + axis * length * .45 + normal * width * .52
            cv2.line(glow, tuple(np.rint(wake0).astype(int)),
                     tuple(np.rint(wake1).astype(int)), .55 + .35 * depth,
                     2 + index % 3, cv2.LINE_AA)
            cv2.line(masks["reflection_wakes"], tuple(np.rint(wake0).astype(int)),
                     tuple(np.rint(wake1).astype(int)), 255, 2 + index % 3, cv2.LINE_AA)

    bloom = cv2.GaussianBlur(glow, (0, 0), 3.1)
    bloom_color = np.asarray((.61, .94, .94) if angle_b else (1.0, .71, .42), np.float32)
    paint = np.clip(paint + bloom[..., None] * bloom_color * .68, 0, 1)
    return paint, {name: mask.astype(np.float32) / 255.0 for name, mask in masks.items()}


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_LINEAR)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/sunstone_splinter_i2")
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
    cv2.imwrite(str(out / f"{ID}_paint_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_a_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_b_2048.png"), cv2.cvtColor(native_b, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1216, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID,
        "module": __name__,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 76,
        "source_mechanism_contact": "assets/reference_textures/colorshoxx/teal_gold_texture.png",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {name: float(mask.mean()) for name, mask in masks.items()},
        "owner_accepted": False,
        "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
