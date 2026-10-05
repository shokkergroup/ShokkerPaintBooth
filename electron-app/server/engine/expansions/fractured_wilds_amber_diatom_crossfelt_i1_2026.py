# -*- coding: utf-8 -*-
"""Isolated native-2048 Amber Diatom crossfelt study.

SPB-105 / Wilds attempt 78 / 2026-08-25.  Thousands of unequal 12--32 px
silica valves form a dense deterministic crossfelt.  Five orientation schools
produce lance, wedge, sigmoid, split and clipped valve bodies.  Raphe grooves,
transverse striae, central nodules, girdle seams, broken tips and true crossed
silica welds are constructed from each valve's geometry.  No RNG, sampled
noise, scalar carrier, generic hatching, rows, stamps or shared composer.

Native-2048 verdict: REJECTED.  The low-discrepancy sites resolve into obvious
vertical columns, while the five intended valve schools collapse into one
repeated origami/leaf/confetti unit.  Raphe, striae, nodules, seams, tips and
welds decorate that unit rather than producing a crossfelt hierarchy.  Frozen
before spec/M7/runtime; no placement, valve, angle, density, palette, scale,
spec, hash, jitter or noise repair is authorized.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_amber_diatom"
NATIVE = 2048
COUNT = 9200

PALETTE_A = np.asarray([
    (8, 12, 22), (18, 31, 48), (13, 64, 79), (13, 95, 101),
    (20, 127, 116), (46, 154, 119), (92, 176, 112), (147, 193, 102),
    (199, 198, 91), (235, 183, 78), (250, 149, 67), (245, 103, 69),
    (220, 64, 92), (171, 50, 128), (102, 45, 145),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (13, 8, 29), (34, 10, 58), (62, 13, 92), (96, 17, 119),
    (135, 25, 136), (177, 39, 142), (215, 62, 136), (242, 91, 122),
    (252, 130, 103), (250, 170, 89), (226, 205, 90), (176, 226, 110),
    (111, 231, 145), (53, 211, 182), (23, 164, 198),
], np.float32) / 255.0


def _unit(angle):
    return np.asarray((np.cos(angle), np.sin(angle)), np.float32)


@lru_cache(maxsize=1)
def _geometry():
    valves = []
    for i in range(COUNT):
        # Low-discrepancy coverage has no row clock and no random source.
        x = 10 + (NATIVE - 20) * ((.173 + i * .6180339887498948) % 1.0)
        y = 10 + (NATIVE - 20) * ((.419 + i * .4142135623730950) % 1.0)
        school = i % 5
        director = (.63 * np.sin(x / 131.0 + y / 197.0)
                    + .41 * np.cos(y / 89.0 - x / 173.0))
        angle = (school * np.pi / 5.0 + director
                 + .16 * np.sin(i * 2.399963229728653)) % np.pi
        length = 13 + (i * 11 + school * 3) % 20
        width = 4 + (i * 7 + school) % 6
        state = (i * 13 + school * 7) % 11
        valves.append((x, y, angle, length, width, school, state, i))
    # Fixed order is part of the optical depth chronology.
    return tuple(valves)


def _polyline_points(cx, cy, angle, length, width, school):
    u, n = _unit(angle), _unit(angle + np.pi / 2.0)
    center = np.asarray((cx, cy), np.float32)
    half = length * .5
    if school == 0:  # lance: symmetric raphe valve
        points = [center - u * half,
                  center - u * half * .28 + n * width * .52,
                  center + n * width * .60,
                  center + u * half * .28 + n * width * .52,
                  center + u * half,
                  center + u * half * .28 - n * width * .52,
                  center - n * width * .60,
                  center - u * half * .28 - n * width * .52]
    elif school == 1:  # asymmetric wedge valve
        points = [center - u * half - n * width * .10,
                  center - u * half * .18 + n * width * .60,
                  center + u * half + n * width * .22,
                  center + u * half * .68 - n * width * .48,
                  center - u * half * .22 - n * width * .44]
    elif school == 2:  # sigmoid body, not a straight capsule
        bend = n * width * .38
        points = [center - u * half - bend,
                  center - u * half * .30 + n * width * .50,
                  center + u * half * .22 + n * width * .62,
                  center + u * half + bend,
                  center + u * half * .30 - n * width * .50,
                  center - u * half * .22 - n * width * .62]
    elif school == 3:  # clipped pennate plate
        points = [center - u * half + n * width * .22,
                  center - u * half * .74 + n * width * .52,
                  center + u * half * .70 + n * width * .58,
                  center + u * half,
                  center + u * half * .74 - n * width * .52,
                  center - u * half * .70 - n * width * .58]
    else:  # shouldered valve with a narrow centre
        points = [center - u * half,
                  center - u * half * .58 + n * width * .55,
                  center - u * half * .10 + n * width * .33,
                  center + u * half * .52 + n * width * .58,
                  center + u * half,
                  center + u * half * .52 - n * width * .58,
                  center - u * half * .10 - n * width * .33,
                  center - u * half * .58 - n * width * .55]
    return np.rint(points).astype(np.int32), center, u, n


def _blend_poly_roi(image, poly, color, alpha):
    """Alpha-fill a tiny valve ROI; never allocate one full canvas per valve."""
    x, y, w, h = cv2.boundingRect(poly)
    x0, y0 = max(0, x - 1), max(0, y - 1)
    x1, y1 = min(NATIVE, x + w + 1), min(NATIVE, y + h + 1)
    local_poly = poly - np.asarray((x0, y0), np.int32)
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillConvexPoly(mask, local_poly, 255, cv2.LINE_AA)
    area = mask > 0
    if not np.any(area):
        return x0, x1, y0, y1, mask
    a = mask[area].astype(np.float32)[:, None] / 255.0 * alpha
    roi = image[y0:y1, x0:x1]
    roi[area] = roi[area] * (1.0 - a) + color * a
    return x0, x1, y0, y1, mask


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:NATIVE, 0:NATIVE].astype(np.float32)
    # Low-amplitude matrix tint only; it never supplies visible topology.
    matrix = (.5 + .5 * np.sin(xx / 311.0 + yy / 277.0)
              * np.cos(yy / 419.0 - xx / 367.0))
    dark0 = np.asarray((.006, .012, .022) if not angle_b else (.014, .006, .025), np.float32)
    dark1 = np.asarray((.018, .045, .055) if not angle_b else (.052, .012, .061), np.float32)
    paint = dark0 + (dark1 - dark0) * matrix[..., None] * .52
    masks = {name: np.zeros((NATIVE, NATIVE), np.uint8) for name in (
        "valve_bodies", "raphe_grooves", "transverse_striae",
        "central_nodules", "girdle_seams", "broken_tips", "silica_welds")}

    for cx, cy, angle, length, width, school, state, i in _geometry():
        poly, center, u, n = _polyline_points(cx, cy, angle, length, width, school)
        optical = .66 + .34 * abs(np.cos(angle - (.44 if angle_b else 2.18)))
        body_color = np.clip(palette[(school * 3 + state + (4 if angle_b else 0)) % 15]
                             * optical, 0, 1)
        x0, x1, y0, y1, local = _blend_poly_roi(paint, poly, body_color, .78)
        masks["valve_bodies"][y0:y1, x0:x1] = np.maximum(
            masks["valve_bodies"][y0:y1, x0:x1], local)
        edge_color = tuple(float(v) for v in np.clip(
            palette[(school * 3 + state + 2) % 15] * 1.22, 0, 1))
        cv2.polylines(paint, [poly], True, edge_color, 1, cv2.LINE_AA)

        # Every valve has a raphe, but its offset and interruption vary.
        p0 = center - u * length * (.34 + .03 * (state % 3))
        p1 = center + u * length * (.34 - .02 * (state % 4))
        groove_color = tuple(float(v) for v in (
            (.01, .025, .035) if not angle_b else (.035, .008, .045)))
        cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                 groove_color, 1, cv2.LINE_AA)
        cv2.line(masks["raphe_grooves"], tuple(np.rint(p0).astype(int)),
                 tuple(np.rint(p1).astype(int)), 255, 1, cv2.LINE_AA)

        # 2--5 causal transverse striae; they terminate on the actual body.
        for k in range(2 + (state % 4)):
            t = -.28 + .56 * (k + .5) / (2 + state % 4)
            c = center + u * length * t
            span = width * (.28 + .12 * ((k + school) % 3))
            s0, s1 = c - n * span, c + n * span
            stria_color = tuple(float(v) for v in np.clip(
                palette[(state + k + 7) % 15] * 1.16, 0, 1))
            cv2.line(paint, tuple(np.rint(s0).astype(int)), tuple(np.rint(s1).astype(int)),
                     stria_color, 1, cv2.LINE_AA)
            cv2.line(masks["transverse_striae"], tuple(np.rint(s0).astype(int)),
                     tuple(np.rint(s1).astype(int)), 255, 1, cv2.LINE_AA)

        if state in (0, 4, 7, 9):
            radius = 1 + (state % 2)
            cv2.circle(paint, tuple(np.rint(center).astype(int)), radius,
                       tuple(float(v) for v in palette[(state + 10) % 15]), -1, cv2.LINE_AA)
            cv2.circle(masks["central_nodules"], tuple(np.rint(center).astype(int)),
                       radius, 255, -1, cv2.LINE_AA)
        if state in (2, 5, 8):
            offset = n * width * .31
            g0, g1 = p0 + offset, p1 + offset
            cv2.line(paint, tuple(np.rint(g0).astype(int)), tuple(np.rint(g1).astype(int)),
                     tuple(float(v) for v in palette[(state + 4) % 15]), 1, cv2.LINE_AA)
            cv2.line(masks["girdle_seams"], tuple(np.rint(g0).astype(int)),
                     tuple(np.rint(g1).astype(int)), 255, 1, cv2.LINE_AA)
        if state in (3, 6, 10):
            tip = center + u * length * .47
            c0, c1 = tip - n * width * .45, tip + n * width * .18
            cv2.line(paint, tuple(np.rint(c0).astype(int)), tuple(np.rint(c1).astype(int)),
                     groove_color, 2, cv2.LINE_AA)
            cv2.line(masks["broken_tips"], tuple(np.rint(c0).astype(int)),
                     tuple(np.rint(c1).astype(int)), 255, 2, cv2.LINE_AA)

        # Every 19th site is a true two-valve junction, not an arbitrary dot.
        if i % 19 == 0:
            other = _unit(angle + 1.07 + .13 * (i % 3))
            q0, q1 = center - other * width * .72, center + other * width * .72
            weld_color = tuple(float(v) for v in np.clip(
                palette[(state + 12) % 15] * 1.28, 0, 1))
            cv2.line(paint, tuple(np.rint(q0).astype(int)), tuple(np.rint(q1).astype(int)),
                     weld_color, 2, cv2.LINE_AA)
            cv2.line(masks["silica_welds"], tuple(np.rint(q0).astype(int)),
                     tuple(np.rint(q1).astype(int)), 255, 2, cv2.LINE_AA)

    return np.clip(paint, 0, 1), {k: v.astype(np.float32) / 255.0 for k, v in masks.items()}


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/amber_diatom_crossfelt_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, masks = _render(False)
        repeats.append(_u8(paint))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _render(True)
    native_a, native_b = repeats[0], _u8(angle_b)
    for label, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{label}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1216, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID, "module": __name__, "attempt": 78,
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
    return "fractured-wilds-amber-diatom-crossfelt-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
