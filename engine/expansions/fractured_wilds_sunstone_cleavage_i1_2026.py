# -*- coding: utf-8 -*-
"""Isolated native-2048 Sunstone aperiodic-cleavage study.

SPB-105 / Wilds attempt 72 / 2026-08-25. The frozen legacy source was bead
chains on dashed paths. I1 instead builds one edge-to-edge crystal cleavage
fabric from deterministic unequal Delaunay facets. Each 8--32 px native facet
has a distinct geometry and one of seven physical histories: hematite platelet,
pullout socket, scratch shadow, twin flash, cleavage ladder, chipped corner or
healed split. The triangulation is material structure, not sampled noise.

No RNG, sampled noise, FBM, rail/path carrier, stamp bank, shared composer or
recolor fallback.

Native-2048 verdict: REJECTED. Every facet is geometrically unique and seven
events are present, but the full sheet still reads as one dense triangle
paver/confetti field. Event types do not establish visible hierarchy. Frozen
before spec/M7/runtime. No site, triangle, color, state, edge, density, scale,
spec or noise repair is authorized.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.spatial import Delaunay


ID = "fmo_sunstone_glitter"
WORK = 1024
NATIVE = 2048
TAU = 2.0 * np.pi

PALETTE_A = np.asarray([
    (20, 7, 4), (42, 12, 5), (68, 19, 5), (96, 28, 5),
    (126, 39, 6), (157, 52, 8), (187, 68, 11), (213, 87, 16),
    (232, 111, 25), (245, 139, 40), (252, 169, 64), (255, 198, 96),
    (255, 222, 137), (250, 238, 184), (224, 244, 219),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 14, 23), (5, 27, 43), (6, 43, 64), (7, 61, 84),
    (9, 82, 102), (13, 105, 116), (22, 131, 126), (37, 158, 132),
    (60, 184, 133), (91, 207, 130), (130, 226, 132), (173, 238, 145),
    (215, 242, 169), (244, 230, 199), (250, 195, 213),
], np.float32) / 255.0


def _hash32(value):
    value = int(value) & 0xFFFFFFFF
    value = ((value ^ (value >> 16)) * 0x7FEB352D) & 0xFFFFFFFF
    value = ((value ^ (value >> 15)) * 0x846CA68B) & 0xFFFFFFFF
    return (value ^ (value >> 16)) & 0xFFFFFFFF


@lru_cache(maxsize=1)
def _geometry():
    points = []
    for i in range(5200):
        x = 3.0 + 1018.0 * ((i * .6180339887498948 + .021 * np.sin(i * .71)) % 1.0)
        y = 3.0 + 1018.0 * ((i * .7548776662466927 + .019 * np.sin(i * 1.17)) % 1.0)
        points.append((x, y))
    # A fine boundary ring prevents macro edge triangles.
    for q in range(0, WORK, 10):
        points.extend(((q, 0), (q, WORK - 1), (0, q), (WORK - 1, q)))
    pts = np.asarray(points, np.float32)
    tri = Delaunay(pts).simplices
    rows = []
    for index, ids in enumerate(tri):
        poly = pts[ids]
        ab = poly[1] - poly[0]
        ac = poly[2] - poly[0]
        area = abs(float(ab[0] * ac[1] - ab[1] * ac[0])) * .5
        if area < 5.0:
            continue
        center = poly.mean(axis=0)
        key = _hash32(index * 2654435761 + int(ids[0]) * 97 + int(ids[1]) * 193)
        state = key % 11
        height = (.52 * np.sin(center[0] / 41.0 + center[1] / 67.0)
                  + .31 * np.sin(center[0] / 23.0 - center[1] / 37.0)
                  + .17 * np.cos((center[0] + center[1]) / 19.0))
        rows.append((np.rint(poly).astype(np.int32), center, state, key, height, area))
    return rows


def _shrink(poly, center, amount):
    return np.rint(center + (poly.astype(np.float32) - center) * amount).astype(np.int32)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    paint = np.empty((WORK, WORK, 3), np.float32)
    paint[:] = palette[0] * .72
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "cleavage_facets", "hematite_platelets", "pullout_sockets",
        "scratch_shadows", "twin_flashes", "cleavage_ladders",
        "chipped_corners", "healed_splits")}

    for poly, center, state, key, height, area in _geometry():
        phase = (.41 * np.sin(center[0] / 29.0) + .37 * np.cos(center[1] / 31.0)
                 + .22 * np.sin((center[0] - center[1]) / 17.0) + height)
        color_index = int(np.floor((phase + 2.0) * 3.7 + (key % 5))) % 15
        if angle_b:
            color_index = (14 - color_index + state * 3) % 15
        shade = .58 + .34 * (.5 + .5 * np.sin(height * 3.1 + (key % 13) * .17))
        fill = tuple(float(v) for v in np.clip(palette[color_index] * shade, 0, 1))
        cv2.fillConvexPoly(paint, poly, fill, cv2.LINE_AA)
        cv2.fillConvexPoly(masks["cleavage_facets"], poly, 255, cv2.LINE_AA)
        edge = ((.04, .42, .40) if angle_b else (.23, .055, .018))
        cv2.polylines(paint, [poly], True, edge, 2 + key % 3, cv2.LINE_AA)

        inner = _shrink(poly, center, .54 + .06 * (key % 4))
        if state == 0:  # reflective platelet has a filled skew face plus rim.
            cv2.fillConvexPoly(paint, inner,
                               ((.97, .32, .70) if angle_b else (.91, .39, .11)),
                               cv2.LINE_AA)
            cv2.polylines(paint, [inner], True,
                          ((1.0, .91, .61) if angle_b else (1.0, .79, .28)),
                          2, cv2.LINE_AA)
            cv2.fillConvexPoly(masks["hematite_platelets"], inner, 255, cv2.LINE_AA)
        elif state == 1:  # material is absent, so the socket is a true dark cavity.
            cv2.fillConvexPoly(paint, inner,
                               ((.012, .028, .045) if angle_b else (.018, .007, .004)),
                               cv2.LINE_AA)
            cv2.fillConvexPoly(masks["pullout_sockets"], inner, 255, cv2.LINE_AA)
        elif state in (2, 3):  # scratch shadow crosses one facet, never a long carrier.
            longest = max(((np.linalg.norm(poly[(i + 1) % 3] - poly[i]), i)
                           for i in range(3)), key=lambda item: item[0])[1]
            a, b = poly[longest].astype(np.float32), poly[(longest + 1) % 3].astype(np.float32)
            p0 = center + (a - center) * .58
            p1 = center + (b - center) * .58
            cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                     ((.015, .06, .08) if angle_b else (.13, .02, .008)),
                     3 + key % 3, cv2.LINE_AA)
            cv2.line(masks["scratch_shadows"], tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)), 255, 3 + key % 3, cv2.LINE_AA)
        elif state == 4:  # a twin flash is one half-facet, not a dash.
            flash = np.asarray([poly[0], poly[1], np.rint(center).astype(np.int32)])
            cv2.fillConvexPoly(paint, flash,
                               ((.91, .19, .72) if angle_b else (1.0, .82, .35)),
                               cv2.LINE_AA)
            cv2.fillConvexPoly(masks["twin_flashes"], flash, 255, cv2.LINE_AA)
        elif state == 5:  # three attached rungs reveal the cleavage plane.
            axis = poly[1].astype(np.float32) - poly[0].astype(np.float32)
            length = max(1.0, float(np.linalg.norm(axis)))
            axis /= length
            normal = np.asarray([-axis[1], axis[0]], np.float32)
            for rung in (-1, 0, 1):
                c = center + axis * rung * min(4.0, length * .16)
                span = min(7.0, max(3.0, np.sqrt(area) * .25))
                p0, p1 = c - normal * span, c + normal * span
                cv2.line(paint, tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)),
                         ((.83, .94, .42) if angle_b else (.99, .68, .18)),
                         2, cv2.LINE_AA)
                cv2.line(masks["cleavage_ladders"], tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)), 255, 2, cv2.LINE_AA)
        elif state == 6:  # a chipped vertex removes one local triangular bite.
            vertex = poly[key % 3].astype(np.float32)
            chip = np.rint([vertex,
                            vertex + (center - vertex) * .38,
                            vertex + (poly[(key + 1) % 3] - vertex) * .31]).astype(np.int32)
            cv2.fillConvexPoly(paint, chip,
                               ((.02, .055, .07) if angle_b else (.07, .012, .006)),
                               cv2.LINE_AA)
            cv2.fillConvexPoly(masks["chipped_corners"], chip, 255, cv2.LINE_AA)
        elif state in (7, 8):  # healed split is bright fill between two fault lips.
            p0 = center + (poly[0] - center) * .62
            p1 = center + (poly[2] - center) * .62
            cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                     ((.95, .78, .27) if angle_b else (1.0, .93, .62)),
                     3 + key % 2, cv2.LINE_AA)
            cv2.line(masks["healed_splits"], tuple(np.rint(p0).astype(int)),
                     tuple(np.rint(p1).astype(int)), 255, 3 + key % 2, cv2.LINE_AA)

    return np.clip(paint, 0, 1), {name: mask.astype(np.float32) / 255.0
                                  for name, mask in masks.items()}


def _up(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/sunstone_cleavage_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    masks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, masks = _render(False)
        repeats.append(_u8(_up(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _render(True)
    native_a, native_b = repeats[0], _u8(_up(angle_b))
    cv2.imwrite(str(out / f"{ID}_paint_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_a_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_b_2048.png"), cv2.cvtColor(native_b, cv2.COLOR_RGB2BGR))
    crop = native_a[672:1184, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID,
        "module": __name__,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 72,
        "triangle_count": len(_geometry()),
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
