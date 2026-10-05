# -*- coding: utf-8 -*-
"""Isolated native-2048 Lime Mold fruiting-mat study.

SPB-105 / Wilds attempt 94 / 2026-08-25. Deterministic edge-fed hyphal
genealogies anastomose into one continuous fruiting sheet. Branch-age tissue,
fusion saddles, active margins, rupture lanes, spore-head ridges, attached
conidia chains, septa, dead zones, repair lips and terminal fans remain causal.
No sampled noise, loose tree/web skeleton, reaction texture, particle scatter,
round colony stamps, recolour fallback or shared composer is used. Visible
primitive widths are 8--32 px native; sheet mass must dominate at full size.

Native-2048 verdict: REJECTED. The genealogies remain disconnected edge lobes
around a huge black center; soft lime bulb masses and repeated C-shaped fruiting
glyphs dominate. Three straight rupture rails further expose the construction.
It is neither continuous nor materially fungal at car scale. Frozen before
spec/M7/runtime. No growth, dilation, root, crop, fruit, rupture, palette,
density, scale, spec or noise repair is authorized; replace the carrier.
"""
from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_lime_mold"
ATTEMPT = 94
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (3, 8, 9), (5, 24, 14), (7, 43, 20), (10, 65, 26), (14, 89, 31),
    (21, 115, 34), (31, 142, 36), (46, 169, 38), (66, 194, 42),
    (91, 215, 51), (122, 229, 68), (157, 235, 91), (192, 232, 121),
    (220, 220, 155), (237, 199, 195),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (18, 3, 24), (44, 4, 45), (72, 6, 63), (101, 9, 75), (131, 14, 81),
    (160, 23, 82), (188, 35, 79), (212, 52, 74), (231, 74, 70),
    (243, 100, 72), (248, 130, 82), (245, 161, 100), (233, 190, 127),
    (212, 215, 161), (183, 231, 201),
], np.float32) / 255.0


def _child_value(lineage, generation, salt):
    n = (lineage * 1664525 + generation * 1013904223 + salt * 2246822519) & 0xFFFFFFFF
    n ^= n >> 15
    n = (n * 3266489917) & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFFFFFF) / float(0xFFFFFF)


def _grow_masks():
    hypha = np.zeros((WORK, WORK), np.uint8)
    age = np.zeros((WORK, WORK), np.uint8)
    order = np.zeros((WORK, WORK), np.uint8)
    forks = np.zeros((WORK, WORK), np.uint8)
    septa = np.zeros((WORK, WORK), np.uint8)
    tips = []
    roots = ((-18, 148, .16, 101), (-20, 423, -.11, 211), (-16, 741, .09, 307),
             (180, -18, 1.28, 401), (504, -19, 1.77, 503), (818, -16, 1.93, 601),
             (1041, 288, 3.02, 701), (1040, 686, 3.31, 809),
             (719, 1042, 4.57, 907), (311, 1041, 4.88, 1009))
    queue = deque((np.asarray((x, y), np.float32), angle, 0, lineage, 0)
                  for x, y, angle, lineage in roots)
    while queue:
        point, angle, generation, lineage, branch_order = queue.popleft()
        if generation >= 10:
            tips.append((point.copy(), angle, lineage, branch_order))
            continue
        v1 = _child_value(lineage, generation, 3)
        v2 = _child_value(lineage, generation, 7)
        length = 18.0 - generation * .78 + v1 * 13.0
        # Deterministic chemotactic steering bends toward three nutrient basins,
        # then lineage torsion prevents a generic symmetric tree.
        attractors = np.asarray(((264, 285), (746, 448), (431, 792)), np.float32)
        attractor = attractors[(lineage + generation) % 3]
        desired = np.arctan2(attractor[1] - point[1], attractor[0] - point[0])
        delta = np.arctan2(np.sin(desired - angle), np.cos(desired - angle))
        next_angle = angle + .18 * delta + (v2 - .5) * .43
        endpoint = point + np.asarray((np.cos(next_angle), np.sin(next_angle)), np.float32) * length
        width = max(2, 6 - generation // 2)
        p0, p1 = tuple(np.rint(point).astype(int)), tuple(np.rint(endpoint).astype(int))
        cv2.line(hypha, p0, p1, 255, width, cv2.LINE_AA)
        cv2.line(age, p0, p1, min(255, 24 + generation * 21), width + 2, cv2.LINE_AA)
        cv2.line(order, p0, p1, min(255, 37 + branch_order * 29), width + 1, cv2.LINE_AA)
        if generation in (3, 6, 8):
            cv2.circle(forks, p1, 4 + generation % 3, 255, 2, cv2.LINE_AA)
        if generation >= 4 and (lineage + generation) % 3 == 0:
            tangent = np.asarray((np.cos(next_angle), np.sin(next_angle)), np.float32)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            a, b = endpoint - normal * 5, endpoint + normal * 5
            cv2.line(septa, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 2, cv2.LINE_AA)

        if -80 < endpoint[0] < 1104 and -80 < endpoint[1] < 1104:
            # The primary child always continues.
            queue.append((endpoint, next_angle, generation + 1,
                          lineage * 2 + 1, branch_order))
            # Branching schedule creates unequal genealogy without random draws.
            if generation < 8 and ((lineage + generation * 3) % 5 != 0):
                side = -1 if (lineage + generation) % 2 else 1
                split = .39 + .31 * _child_value(lineage, generation, 11)
                queue.append((endpoint, next_angle + side * split, generation + 1,
                              lineage * 2 + 2, branch_order + 1))
            if generation in (4, 7) and lineage % 4 == 1:
                queue.append((endpoint, next_angle - .58, generation + 1,
                              lineage * 2 + 3, branch_order + 2))
        else:
            tips.append((point.copy(), next_angle, lineage, branch_order))
    return hypha, age, order, forks, septa, tips


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    hypha, age, order, forks, septa, tips = _grow_masks()
    # Anastomosing sheet grows from actual hyphae; two physical dilation scales
    # produce tissue and active-margin observables, not a scalar noise field.
    tissue = cv2.dilate(hypha, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (23, 23)))
    tissue = cv2.morphologyEx(tissue, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)))
    outer = cv2.dilate(tissue, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    active_margin = cv2.subtract(outer, tissue)
    inner_distance = cv2.distanceTransform(tissue, cv2.DIST_L2, 3)
    inner_distance = np.clip(inner_distance / 19.0, 0, 1)
    age_f = cv2.GaussianBlur(age.astype(np.float32) / 255.0, (0, 0), 4.0)
    order_f = cv2.GaussianBlur(order.astype(np.float32) / 255.0, (0, 0), 2.0)
    gy, gx = np.gradient(inner_distance)
    travel = (age_f * .43 + order_f * .27 + inner_distance * .31
              + gx * .13 - gy * .17 + (.40 if angle_b else 0.0)) % 1.0
    shade = np.clip(.20 + .66 * inner_distance + .15 * gx - .10 * gy, .06, 1.06)
    paint = _ramp(travel, palette) * shade[..., None]
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    substrate = _ramp((xx * .00029 + yy * .00017 + (.19 if angle_b else 0)) % 1, palette)
    paint[tissue < 8] = substrate[tissue < 8] * .055

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "anastomosed_sheet", "branch_age_tissue", "fusion_saddles", "active_margins",
        "rupture_lanes", "spore_head_ridges", "attached_conidia_chains", "septa",
        "dead_zones", "repair_lips", "terminal_fans")}
    masks["anastomosed_sheet"] = tissue
    masks["branch_age_tissue"] = age
    masks["active_margins"] = active_margin
    masks["septa"] = septa

    # Fusion saddles occur only where local tissue is thick and multiple fork
    # histories overlap. They are not generic cells.
    fork_field = cv2.dilate(forks, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    fusion = cv2.bitwise_and(fork_field, tissue)
    masks["fusion_saddles"] = fusion
    paint[fusion > 8] = np.clip(paint[fusion > 8] * .52 + palette[12] * .52, 0, 1)

    # A small number of chronology-owned rupture lanes interrupt sheet mass.
    rupture_controls = (
        ((72, 357), (242, 381), (389, 348), (536, 399)),
        ((514, 690), (653, 647), (802, 675), (966, 619)),
        ((337, 94), (402, 234), (455, 373), (429, 532)),
    )
    for j, control in enumerate(rupture_controls):
        curve = np.asarray(control, np.int32)
        cv2.polylines(paint, [curve], False, (0.002, .004, .003), 8 + j * 2, cv2.LINE_AA)
        cv2.polylines(masks["rupture_lanes"], [curve], False, 255, 8 + j * 2, cv2.LINE_AA)
        cv2.polylines(paint, [curve], False,
                      tuple(float(v) for v in np.clip(palette[(j * 4 + 10) % 15] * 1.15, 0, 1)), 2, cv2.LINE_AA)
        cv2.polylines(masks["repair_lips"], [curve], False, 255, 2, cv2.LINE_AA)

    # Fruiting anatomy is attached only to terminal genealogy points.
    for event, (point, angle, lineage, branch_order) in enumerate(tips[::max(1, len(tips) // 137)]):
        x, y = np.rint(point).astype(int)
        if not (10 <= x < WORK - 10 and 10 <= y < WORK - 10):
            continue
        tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        radius = 4 + (lineage + event) % 5
        # Open ridge, not a repeated round spore stamp.
        cv2.ellipse(paint, (x, y), (radius + 3, radius), int(np.degrees(angle)),
                    28, 307, tuple(float(v) for v in np.clip(palette[(event * 5 + 11) % 15] * 1.18, 0, 1)), 3, cv2.LINE_AA)
        cv2.ellipse(masks["spore_head_ridges"], (x, y), (radius + 3, radius),
                    int(np.degrees(angle)), 28, 307, 255, 3, cv2.LINE_AA)
        for k in range(1, 4 + event % 3):
            c = point + tangent * (5 + k * 5) + normal * np.sin(k * 1.7 + event) * 3
            cv2.circle(paint, tuple(np.rint(c).astype(int)), 2 + k % 2,
                       tuple(float(v) for v in np.clip(palette[(event + k + 12) % 15] * 1.2, 0, 1)), 2, cv2.LINE_AA)
            cv2.circle(masks["attached_conidia_chains"], tuple(np.rint(c).astype(int)), 2 + k % 2, 255, 2, cv2.LINE_AA)
        for side in (-1, 1):
            a = point - tangent * 3
            b = point + tangent * 8 + normal * side * (6 + branch_order % 4)
            cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                     tuple(float(v) for v in np.clip(palette[(event * 3 + side + 9) % 15] * 1.16, 0, 1)), 2, cv2.LINE_AA)
            cv2.line(masks["terminal_fans"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 2, cv2.LINE_AA)

    # Dead zones are exact sheet interiors starved by rupture adjacency.
    rupture_dilate = cv2.dilate(masks["rupture_lanes"], cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    dead = cv2.bitwise_and(rupture_dilate, tissue)
    dead = cv2.bitwise_and(dead, cv2.bitwise_not(masks["repair_lips"]))
    masks["dead_zones"] = dead
    paint[dead > 8] *= .23
    return np.clip(paint, 0, 1), masks


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/lime_mold_fruiting_mat_i1")
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
    return "fractured-wilds-lime-mold-fruiting-mat-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
