# -*- coding: utf-8 -*-
"""Isolated native-2048 Coral Cluster heterogeneous-accretion study.

SPB-105 / Wilds attempt 73 / 2026-08-25. Three failed carriers (calice paver,
tree with polyp stamps, analytic micro-maze) are discarded. I4 is one connected
reef chronology whose overlapping neighborhoods visibly change morphology:
branching growth, plate shelves, brain folds, cup fields, sponge pores, lace
fans, healed rubble and encrusting ridges. No one unit covers the whole sheet.

All drawn widths/radii are 4--16 work pixels (8--32 px native). No RNG, sampled
noise, FBM, shared composer, global paver, single rail family or recolor
fallback.

Native-2048 verdict: REJECTED. Distinct neighborhoods exist, but they read as
pasted macro icons/specimens over an unrelated striped background, not one
continuous material. Frozen before spec/M7/runtime. No neighborhood, generator,
placement, density, palette, background, scale, spec or noise repair is
authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fbl_coral_cluster"
WORK = 1024
NATIVE = 2048
TAU = 2.0 * np.pi

COLORS_A = np.asarray([
    (23, 5, 13), (55, 8, 20), (91, 13, 29), (129, 21, 38),
    (166, 32, 48), (199, 47, 60), (226, 67, 75), (244, 91, 92),
    (253, 120, 111), (255, 153, 135), (255, 186, 160), (247, 215, 188),
    (215, 234, 211), (159, 229, 220), (88, 205, 207),
], np.float32) / 255.0
COLORS_B = np.asarray([
    (4, 17, 28), (4, 34, 48), (4, 55, 68), (5, 80, 86),
    (8, 108, 101), (16, 137, 112), (31, 165, 119), (53, 191, 122),
    (84, 214, 124), (124, 231, 133), (169, 241, 151), (211, 243, 177),
    (244, 233, 204), (254, 200, 209), (241, 153, 218),
], np.float32) / 255.0

CENTERS = (
    (84, 111, 0), (345, 85, 1), (690, 112, 2), (938, 198, 3),
    (159, 432, 4), (493, 366, 5), (786, 453, 6),
    (84, 742, 7), (375, 713, 2), (680, 752, 0), (948, 688, 4),
    (218, 987, 6), (541, 947, 3), (835, 963, 1),
)


def _new_masks():
    return {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "branching_growth", "plate_shelves", "brain_folds", "cup_fields",
        "sponge_pores", "lace_fans", "healed_rubble", "encrusting_ridges")}


def _polyline(mask, points, width):
    cv2.polylines(mask, [np.rint(points).astype(np.int32)], False, 255,
                  int(width), cv2.LINE_AA)


def _branching(mask, cx, cy, index):
    base_angle = -.8 + (index % 4) * .57
    for stem in range(37 + index % 9):
        angle = base_angle + (stem - 18) * .031 + .12 * np.sin(stem * .71 + index)
        length = 55 + (stem * 17 + index * 11) % 145
        points = []
        for step in range(17):
            t = step / 16.0
            bend = angle + .24 * np.sin(t * TAU * (1 + stem % 3) + stem * .19)
            x = cx + np.cos(bend) * length * t + 14 * np.sin(t * np.pi) * np.sin(stem)
            y = cy + np.sin(bend) * length * t + 11 * np.sin(t * TAU + index)
            points.append((x, y))
        _polyline(mask, points, 4 + stem % 7)
        for node in (6, 10, 13):
            if (stem + node + index) % 3:
                p = np.asarray(points[node])
                q = p + np.asarray([np.cos(angle + 1.07), np.sin(angle + 1.07)]) * (9 + node % 7)
                cv2.line(mask, tuple(np.rint(p).astype(int)), tuple(np.rint(q).astype(int)),
                         255, 4 + node % 4, cv2.LINE_AA)


def _shelves(mask, cx, cy, index):
    for shelf in range(39):
        radius = 9 + shelf * 3.7
        start = 17 + (shelf * 29 + index * 13) % 87
        sweep = 112 + (shelf * 17) % 143
        axes = (int(radius * (1.08 + .18 * np.sin(shelf))),
                int(max(5, radius * (.38 + .12 * np.cos(shelf * .7)))))
        center = (int(cx + 21 * np.sin(shelf * .43)),
                  int(cy + 17 * np.cos(shelf * .31)))
        cv2.ellipse(mask, center, axes, (index * 31 + shelf * 7) % 180,
                    start, start + sweep, 255, 4 + shelf % 6, cv2.LINE_AA)


def _brain(mask, cx, cy, index):
    for fold in range(52):
        radius = 7 + fold * 2.9
        points = []
        for sample in range(96):
            t = TAU * sample / 95.0
            r = radius * (1 + .11 * np.sin(3 * t + fold * .37)
                          + .07 * np.sin(5 * t - index))
            x = cx + r * np.cos(t) + 13 * np.sin(2 * t + fold * .11)
            y = cy + r * .71 * np.sin(t) + 11 * np.sin(3 * t - fold * .17)
            points.append((x, y))
        _polyline(mask, points, 4 + fold % 5)


def _cups(mask, cx, cy, index):
    for cup in range(96):
        angle = cup * 2.399963229728653 + index * .31
        radius = 10 + (cup * 17 + index * 13) % 155
        x = cx + np.cos(angle) * radius
        y = cy + np.sin(angle) * radius * .72
        rx = 5 + (cup * 7) % 11
        ry = 4 + (cup * 11) % 9
        start = 22 + (cup * 19) % 73
        cv2.ellipse(mask, (int(x), int(y)), (rx, ry),
                    (cup * 137 + index * 23) % 180, start, 318 - start // 2,
                    255, 4 + cup % 4, cv2.LINE_AA)


def _pores(mask, cx, cy, index):
    for pore in range(185):
        angle = pore * 2.399963229728653 + index * .13
        radius = 7 + (pore * 31 + index * 17) % 177
        x = cx + np.cos(angle) * radius
        y = cy + np.sin(angle) * radius * .75
        rx = 4 + (pore * 7) % 9
        ry = 4 + (pore * 5) % 8
        cv2.ellipse(mask, (int(x), int(y)), (rx, ry),
                    (pore * 83) % 180, 0, 360, 255, 4 + pore % 3, cv2.LINE_AA)


def _fans(mask, cx, cy, index):
    for vane in range(61):
        angle = -1.37 + vane * .045 + index * .19
        length = 52 + (vane * 23 + index * 9) % 144
        p0 = np.asarray([cx, cy], np.float32)
        p1 = p0 + np.asarray([np.cos(angle), np.sin(angle)]) * length
        bow = np.asarray([-np.sin(angle), np.cos(angle)]) * (13 * np.sin(vane * .43))
        points = []
        for sample in range(15):
            t = sample / 14.0
            points.append((1 - t) * p0 + t * p1 + bow * np.sin(np.pi * t))
        _polyline(mask, points, 4 + vane % 5)
        for rung in range(3, 13, 3):
            p = np.asarray(points[rung])
            normal = np.asarray([-np.sin(angle), np.cos(angle)])
            cv2.line(mask, tuple(np.rint(p - normal * 6).astype(int)),
                     tuple(np.rint(p + normal * 6).astype(int)), 255,
                     3 + rung % 3, cv2.LINE_AA)


def _rubble(mask, cx, cy, index):
    for chip in range(143):
        angle = chip * 2.399963229728653 + index * .23
        radius = 8 + (chip * 29 + index * 19) % 164
        center = np.asarray([cx + np.cos(angle) * radius,
                             cy + np.sin(angle) * radius * .78])
        size = 4 + (chip * 7) % 12
        theta = angle + chip * .37
        points = []
        for vertex in range(3 + chip % 3):
            q = theta + TAU * vertex / (3 + chip % 3)
            r = size * (.72 + .23 * np.sin(chip + vertex * 1.7))
            points.append(center + np.asarray([np.cos(q), np.sin(q)]) * r)
        cv2.polylines(mask, [np.rint(points).astype(np.int32)], True, 255,
                      4 + chip % 4, cv2.LINE_AA)


def _ridges(mask, cx, cy, index):
    for ridge in range(47):
        angle = -.74 + ridge * .033 + index * .17
        length = 70 + (ridge * 19) % 139
        origin = np.asarray([cx - 90 + (ridge * 23) % 180,
                             cy - 80 + (ridge * 31) % 160], np.float32)
        direction = np.asarray([np.cos(angle), np.sin(angle)])
        points = [origin + direction * (length * t / 14.0)
                  + np.asarray([-direction[1], direction[0]]) *
                  (8 * np.sin(t * .93 + ridge)) for t in range(15)]
        _polyline(mask, points, 4 + ridge % 6)


def _masks():
    masks = _new_masks()
    funcs = (_branching, _shelves, _brain, _cups, _pores, _fans, _rubble, _ridges)
    names = tuple(masks)
    for index, (cx, cy, kind) in enumerate(CENTERS):
        funcs[kind](masks[names[kind]], cx, cy, index)
        # Every episode heals into the next morphology through a short local
        # overlap, never a long common carrier.
        next_kind = (kind + 3 + index % 4) % 8
        funcs[next_kind](masks[names[next_kind]],
                         cx + 37 * np.sin(index * .9),
                         cy + 31 * np.cos(index * .7), index + 19)
    return {name: mask.astype(np.float32) / 255.0 for name, mask in masks.items()}


def _paint(angle_b=False):
    masks = _masks()
    palette = COLORS_B if angle_b else COLORS_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    phase = np.mod(.013 * xx + .017 * yy +
                   .21 * np.sin(xx / 37.0) - .17 * np.cos(yy / 43.0), 1.0)
    idx = np.clip(np.floor(phase * 15).astype(np.int32), 0, 14)
    paint = palette[idx] * .18
    order = tuple(masks)
    for layer, name in enumerate(order):
        mask = masks[name]
        color_index = (layer * 2 + (7 if angle_b else 0)) % 15
        color = palette[color_index]
        # Each morphology owns a different brightness/tint and remains visible
        # at overlaps instead of being composited through one shared rule.
        alpha = .72 + .035 * layer
        a = np.clip(mask * alpha, 0, 1)[..., None]
        paint = paint * (1 - a) + color * a
        halo = cv2.GaussianBlur(mask, (0, 0), 2.1 + layer * .13)
        rim = np.clip(halo - mask * .58, 0, 1)[..., None]
        rim_color = palette[(color_index + 5 + layer) % 15]
        paint = paint * (1 - rim * .51) + rim_color * (rim * .51)
    return np.clip(paint, 0, 1), masks


def _up(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_LINEAR)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/coral_accretion_i4")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, masks = _paint(False)
        repeats.append(_u8(_up(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _paint(True)
    native_a, native_b = repeats[0], _u8(_up(angle_b))
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
        "attempt": 73,
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
