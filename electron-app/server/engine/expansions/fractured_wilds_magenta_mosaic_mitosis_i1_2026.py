# -*- coding: utf-8 -*-
"""Isolated native-2048 Magenta Mosaic mitosis-sheet study.

SPB-105 / Wilds attempt 69 / 2026-08-25. The rejected exact source was a sparse
tree with stamped squares. This blank topology builds one edge-to-edge tissue
chronology from 3,240 unequal analytic cells in nine distinct physical states:
interphase, chromatin condensation, metaphase, anaphase, cytokinesis, torn
membrane, apoptotic collapse, bridged daughters and junction compression.

Cell radii and attached primitives remain 4--16 work pixels (8--32 px native).
No RNG, sampled noise, FBM, Voronoi/polygon paver, path carrier, stamp bank,
shared composer or recolor fallback.

Native-2048 verdict: REJECTED. The 3,240 objects become homogeneous
confetti/static: tiny rings, dots and sticks without readable tissue hierarchy.
Nine state names do not create nine visible causal systems. Frozen before
spec/M7/runtime. No count, spacing, size, palette, state, density, scale, spec
or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_magenta_mosaic"
WORK = 1024
NATIVE = 2048
COUNT = 3240
TAU = 2.0 * np.pi

PALETTE_A = np.asarray([
    (32, 7, 25), (55, 9, 44), (80, 12, 64), (109, 17, 82),
    (139, 22, 99), (171, 29, 115), (201, 40, 128), (226, 61, 139),
    (244, 91, 151), (252, 127, 168), (255, 164, 188), (245, 197, 214),
    (208, 224, 228), (135, 216, 213), (60, 178, 181),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (8, 22, 31), (8, 39, 52), (7, 61, 74), (6, 86, 96),
    (8, 114, 114), (15, 143, 126), (32, 172, 132), (65, 197, 128),
    (111, 217, 124), (164, 231, 128), (216, 239, 149), (247, 232, 183),
    (255, 198, 176), (244, 137, 177), (206, 79, 177),
], np.float32) / 255.0


def _cells():
    rows = []
    for i in range(COUNT):
        x = 5.0 + 1014.0 * ((i * .6180339887498948
                             + .037 * np.sin(i * .731)) % 1.0)
        y = 5.0 + 1014.0 * ((i * .7548776662466927
                             + .031 * np.sin(i * 1.117 + .4)) % 1.0)
        rx = 4.0 + ((i * 11 + i // 7) % 12)
        ry = 4.0 + ((i * 7 + i // 11) % 11)
        angle = (i * 137.50776405003785 + 23.0 * np.sin(i * .319)) % 180.0
        state = (i * 7 + i // 13 + i // 47) % 9
        phase = (i * .4142135623730950 + .13 * np.sin(i * .271)) % 1.0
        rows.append((x, y, rx, ry, angle, state, phase, i))
    # Larger cells paint first; small late states remain legible without a grid.
    rows.sort(key=lambda item: item[2] * item[3], reverse=True)
    return rows


def _shape(cx, cy, rx, ry, angle_deg, state, phase):
    angle = np.deg2rad(angle_deg)
    ca, sa = np.cos(angle), np.sin(angle)
    points = []
    for j in range(22):
        theta = TAU * j / 22.0
        deform = (1.0 + .13 * np.sin(3 * theta + phase * TAU)
                  + .08 * np.sin(5 * theta - phase * TAU * 1.7))
        if state in (3, 4, 7):
            # Division pinch creates one continuous two-lobed membrane.
            deform *= 1.0 - .26 * np.cos(2.0 * theta) ** 8
        px = rx * deform * np.cos(theta)
        py = ry * deform * np.sin(theta)
        points.append((cx + px * ca - py * sa, cy + px * sa + py * ca))
    return np.rint(points).astype(np.int32)


def _ellipse_poly(cx, cy, rx, ry, angle_deg, count=18):
    angle = np.deg2rad(angle_deg)
    ca, sa = np.cos(angle), np.sin(angle)
    out = []
    for j in range(count):
        theta = TAU * j / count
        px, py = rx * np.cos(theta), ry * np.sin(theta)
        out.append((cx + px * ca - py * sa, cy + px * sa + py * ca))
    return np.rint(out).astype(np.int32)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    paint = np.empty((WORK, WORK, 3), np.float32)
    paint[:] = palette[0] * .66
    tissue = np.zeros((WORK, WORK), np.uint8)
    membranes = np.zeros_like(tissue)
    nuclei = np.zeros_like(tissue)
    chromatin = np.zeros_like(tissue)
    furrows = np.zeros_like(tissue)
    tears = np.zeros_like(tissue)
    bridges = np.zeros_like(tissue)
    junctions = np.zeros_like(tissue)
    gaps = np.zeros_like(tissue)

    for cx, cy, rx, ry, angle, state, phase, index in _cells():
        poly = _shape(cx, cy, rx, ry, angle, state, phase)
        fill_index = (index * 7 + state * 3 + int(phase * 11)) % 15
        if angle_b:
            fill_index = (14 - fill_index + state * 2) % 15
        fill = tuple(float(value) for value in palette[fill_index])
        cv2.fillPoly(paint, [poly], fill, cv2.LINE_AA)
        cv2.fillPoly(tissue, [poly], 255, cv2.LINE_AA)
        border_color = ((.05, .85, .75) if angle_b else (.22, .025, .16))
        cv2.polylines(paint, [poly], True, border_color,
                      2 + (index + state) % 4, cv2.LINE_AA)
        cv2.polylines(membranes, [poly], True, 255,
                      2 + (index + state) % 4, cv2.LINE_AA)

        rad = np.deg2rad(angle)
        axis = np.asarray([np.cos(rad), np.sin(rad)], np.float32)
        normal = np.asarray([-axis[1], axis[0]], np.float32)
        center = np.asarray([cx, cy], np.float32)
        nucleus_center = center + axis * ((phase - .5) * rx * .43)
        nrx, nry = max(2, int(rx * .34)), max(2, int(ry * .30))

        if state in (0, 1, 2, 5):
            n_poly = _ellipse_poly(nucleus_center[0], nucleus_center[1],
                                   nrx, nry, angle + 17 * np.sin(index), 16)
            ncol = ((.96, .22, .67) if angle_b else (.18, .04, .28))
            cv2.fillPoly(paint, [n_poly], ncol, cv2.LINE_AA)
            cv2.fillPoly(nuclei, [n_poly], 255, cv2.LINE_AA)
        if state in (1, 2, 3):
            for rod in range(2 + index % 4):
                shift = (rod - 1.5) * 2.5
                p0 = nucleus_center + normal * shift - axis * (2 + rod % 3)
                p1 = nucleus_center + normal * shift + axis * (2 + (rod + index) % 4)
                cv2.line(paint, tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)),
                         ((.98, .87, .24) if angle_b else (.96, .35, .68)),
                         2 + rod % 2, cv2.LINE_AA)
                cv2.line(chromatin, tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)), 255, 2 + rod % 2,
                         cv2.LINE_AA)
        if state in (3, 4, 7):
            span = min(rx, ry) * .72
            p0, p1 = center - normal * span, center + normal * span
            cv2.line(paint, tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)),
                     ((.12, .95, .70) if angle_b else (1.0, .70, .18)),
                     3 + index % 4, cv2.LINE_AA)
            cv2.line(furrows, tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)), 255, 3 + index % 4,
                     cv2.LINE_AA)
            if state in (4, 7):
                for side in (-1, 1):
                    dc = center + axis * side * rx * .43
                    rr = 2 + (index + side) % 3
                    cv2.circle(paint, tuple(np.rint(dc).astype(int)), rr,
                               ((.92, .17, .75) if angle_b else (.16, .03, .24)),
                               -1, cv2.LINE_AA)
                    cv2.circle(nuclei, tuple(np.rint(dc).astype(int)), rr,
                               255, -1, cv2.LINE_AA)
        if state == 5:
            # A true torn edge removes a wedge and paints two ragged lips.
            tip = center + axis * rx * .82
            wedge = np.rint([tip - normal * 4, tip + axis * 6,
                             tip + normal * 4]).astype(np.int32)
            cv2.fillConvexPoly(paint, wedge,
                               tuple(float(v) for v in palette[0] * .55), cv2.LINE_AA)
            cv2.fillConvexPoly(tears, wedge, 255, cv2.LINE_AA)
            cv2.line(paint, tuple(np.rint(tip - normal * 5).astype(int)),
                     tuple(np.rint(tip + normal * 5).astype(int)),
                     ((.08, .89, .78) if angle_b else (1.0, .53, .22)),
                     3, cv2.LINE_AA)
        if state == 6:
            # Apoptotic collapse is an open crescent, not another complete cell.
            radius = 3 + index % 5
            c = tuple(np.rint(center).astype(int))
            cv2.ellipse(paint, c, (radius + 2, radius), angle,
                        38, 276, tuple(float(v) for v in palette[0] * .42),
                        3, cv2.LINE_AA)
            cv2.ellipse(gaps, c, (radius + 2, radius), angle,
                        38, 276, 255, 3, cv2.LINE_AA)
        if state == 7:
            span = 5 + index % 10
            p0, p1 = center - axis * span, center + axis * span
            cv2.line(paint, tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)),
                     ((.95, .92, .42) if angle_b else (.98, .79, .48)),
                     3 + index % 3, cv2.LINE_AA)
            cv2.line(bridges, tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)), 255, 3 + index % 3,
                     cv2.LINE_AA)
        if state == 8:
            radius = 2 + index % 4
            cv2.circle(paint, tuple(np.rint(center).astype(int)), radius,
                       ((.03, .10, .13) if angle_b else (.05, .018, .035)),
                       -1, cv2.LINE_AA)
            cv2.circle(junctions, tuple(np.rint(center).astype(int)), radius,
                       255, -1, cv2.LINE_AA)

    return np.clip(paint, 0, 1), {
        "tissue": tissue.astype(np.float32) / 255.0,
        "membranes": membranes.astype(np.float32) / 255.0,
        "nuclei": nuclei.astype(np.float32) / 255.0,
        "chromatin": chromatin.astype(np.float32) / 255.0,
        "furrows": furrows.astype(np.float32) / 255.0,
        "tears": tears.astype(np.float32) / 255.0,
        "bridges": bridges.astype(np.float32) / 255.0,
        "junctions": junctions.astype(np.float32) / 255.0,
        "gaps": gaps.astype(np.float32) / 255.0,
    }


def _up(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/magenta_mosaic_mitosis_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    marks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, marks = _render(False)
        repeats.append(_u8(_up(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _render(True)
    native_a, native_b = repeats[0], _u8(_up(angle_b))
    cv2.imwrite(str(out / f"{ID}_paint_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_a_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_b_2048.png"), cv2.cvtColor(native_b, cv2.COLOR_RGB2BGR))
    crop = native_a[512:1024, 768:1280]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID,
        "module": __name__,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 69,
        "cell_count": COUNT,
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {key: float(value.mean()) for key, value in marks.items()},
        "owner_accepted": False,
        "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
