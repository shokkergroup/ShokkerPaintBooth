# -*- coding: utf-8 -*-
"""Isolated native-2048 Leaf Whorl braided-canopy paint study.

SPB-105 / Wilds attempt 97 / 2026-08-25. Twenty-three unequal botanical
chronologies cross as one close-cropped canopy. The construction deliberately
mixes pinnate blades, dichotomous forks, serrated fans, curled tendrils, torn
windows, node bands and over/under scars. All visible primitives are 8--32 px
at native size. There is no RNG, sampled noise, leaf stamp, radial rosette,
generic chevron/paver, parallel herringbone or shared composer. Fractured A/B
changes optical faces while retaining exact geometry.

Native-2048 verdict: REJECTED. The botanical braid collapses into colored
dash/confetti anatomy and tiny glyphs over broad color fields. Frozen with no
density/palette/mark/curve/scale/spec/noise repair authorized.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fbl_leaf_whorl"
ATTEMPT = 97
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (5, 18, 25), (8, 40, 42), (10, 70, 54), (13, 104, 59),
    (24, 139, 61), (54, 170, 63), (96, 196, 66), (151, 213, 71),
    (207, 222, 85), (238, 201, 99), (244, 157, 105), (225, 103, 118),
    (185, 65, 133), (124, 48, 131), (59, 35, 92),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (24, 7, 39), (54, 10, 68), (91, 15, 91), (132, 23, 103),
    (175, 36, 102), (212, 57, 91), (239, 88, 77), (251, 128, 65),
    (247, 173, 64), (222, 210, 75), (164, 225, 92), (91, 213, 116),
    (38, 178, 133), (20, 124, 130), (22, 68, 100),
], np.float32) / 255.0


def _bezier(p0, p1, p2, p3, count=180):
    t = np.linspace(0.0, 1.0, count, dtype=np.float32)
    u = 1.0 - t
    pts = (u[:, None] ** 3 * p0 + 3.0 * u[:, None] ** 2 * t[:, None] * p1
           + 3.0 * u[:, None] * t[:, None] ** 2 * p2 + t[:, None] ** 3 * p3)
    derivative = np.gradient(pts, axis=0)
    derivative /= np.maximum(np.linalg.norm(derivative, axis=1, keepdims=True), 1e-5)
    normal = np.stack((-derivative[:, 1], derivative[:, 0]), axis=1)
    return pts, derivative, normal


def _rgb(palette, index, lift=1.0):
    return tuple(float(v) for v in np.clip(palette[index % len(palette)] * lift, 0.0, 1.0))


def _render(angle_b=False):
    n = WORK
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x, y = (xx + .5) / n, (yy + .5) / n
    palette = PALETTE_B if angle_b else PALETTE_A

    # Low-amplitude optical substrate, not a uniqueness carrier.
    phase = (0.41 * x + 0.57 * y
             + .033 * np.sin(2 * np.pi * (2.3 * x - 1.7 * y))
             + .021 * np.cos(2 * np.pi * (3.1 * y + .8 * x)))
    if angle_b:
        phase = 1.0 - phase + .17
    q = np.mod(phase, 1.0) * len(palette)
    i0 = np.floor(q).astype(np.int16) % len(palette)
    f = (q - np.floor(q))[..., None]
    paint = palette[i0] * (1.0 - f) + palette[(i0 + 1) % len(palette)] * f
    relief = .19 + .08 * (np.sin(2 * np.pi * (4.7 * x + 3.9 * y)) * .5 + .5)
    paint *= relief[..., None]

    masks = {name: np.zeros((n, n), np.uint8) for name in (
        "rachis_braid", "pinnate_blades", "dichotomous_forks",
        "serrated_fans", "curl_tendrils", "torn_windows", "node_bands",
        "over_under_scars")}

    records = []
    for lineage in range(23):
        edge = lineage % 4
        seed = lineage * 0.61803398875
        a = seed % 1.0
        b = (seed * 1.754877666) % 1.0
        if edge == 0:
            p0, p3 = np.array([-70., 70. + 900. * a]), np.array([1090., 90. + 850. * b])
        elif edge == 1:
            p0, p3 = np.array([80. + 850. * a, -70.]), np.array([100. + 820. * b, 1090.])
        elif edge == 2:
            p0, p3 = np.array([1090., 60. + 900. * a]), np.array([-70., 100. + 830. * b])
        else:
            p0, p3 = np.array([70. + 880. * a, 1090.]), np.array([80. + 850. * b, -70.])
        chord = p3 - p0
        side = np.array([-chord[1], chord[0]], np.float32)
        side /= max(float(np.linalg.norm(side)), 1e-5)
        bend1 = (74. + 83. * ((lineage * 7) % 11) / 10.) * (-1 if lineage % 3 == 0 else 1)
        bend2 = (56. + 91. * ((lineage * 5) % 13) / 12.) * (-1 if lineage % 4 < 2 else 1)
        p1 = p0 + chord * (.27 + .04 * (lineage % 3)) + side * bend1
        p2 = p0 + chord * (.67 - .035 * (lineage % 4)) + side * bend2
        pts, tangent, normal = _bezier(p0, p1, p2, p3)
        wave = (7. + lineage % 5) * np.sin(np.linspace(0, (3 + lineage % 4) * np.pi, len(pts)) + lineage)
        pts = pts + normal * wave[:, None]
        width = 3 + lineage % 4
        poly = np.rint(pts).astype(np.int32)

        # Broken colored rachis: never one uninterrupted rail.
        for start in range(0, len(poly) - 2, 10 + lineage % 5):
            stop = min(len(poly), start + 7 + (start + lineage) % 5)
            if stop - start < 2:
                continue
            shade = (lineage * 4 + start // 5 + (8 if angle_b else 0)) % 15
            cv2.polylines(paint, [poly[start:stop]], False, _rgb(palette, shade, .72 + .07 * (lineage % 4)), width, cv2.LINE_AA)
            cv2.polylines(masks["rachis_braid"], [poly[start:stop]], False, 255, width, cv2.LINE_AA)

        stride = 9 + (lineage * 3) % 8
        for k in range(8 + lineage % 6, len(pts) - 8, stride):
            c, tg, nm = pts[k], tangent[k], normal[k]
            handed = -1.0 if ((k // stride + lineage) % 2) else 1.0
            family = (lineage * 3 + k // stride) % 7
            length = 4.0 + ((lineage + k) % 5)  # 8-16 px native half-extent
            breadth = 2.5 + ((lineage * 2 + k) % 4)
            col = _rgb(palette, lineage * 5 + k // 3 + (6 if angle_b else 0), .88 + .08 * ((k + lineage) % 4))
            dark = _rgb(palette, lineage * 2 + k // 7 + 1, .34)
            root = c + nm * handed * (width * .45)
            tip = root + nm * handed * (length + 4) + tg * (((k + lineage) % 7) - 3)

            if family == 0:  # asymmetric pinnate blade
                poly_leaf = np.rint(np.stack((root, root + tg * breadth + nm * handed * length * .55,
                                               tip, root - tg * breadth + nm * handed * length * .42))).astype(np.int32)
                cv2.fillConvexPoly(paint, poly_leaf, col, cv2.LINE_AA)
                cv2.polylines(masks["pinnate_blades"], [poly_leaf], True, 255, 2, cv2.LINE_AA)
                cv2.line(paint, tuple(np.rint(root).astype(int)), tuple(np.rint(tip).astype(int)), dark, 1, cv2.LINE_AA)
            elif family == 1:  # attached dichotomous fork
                elbow = root + nm * handed * (length * .7)
                ends = (elbow + nm * handed * 5 + tg * (breadth + 2), elbow + nm * handed * 6 - tg * (breadth + 1))
                for end in ends:
                    cv2.line(paint, tuple(np.rint(root).astype(int)), tuple(np.rint(end).astype(int)), col, 2, cv2.LINE_AA)
                    cv2.line(masks["dichotomous_forks"], tuple(np.rint(root).astype(int)), tuple(np.rint(end).astype(int)), 255, 2, cv2.LINE_AA)
            elif family == 2:  # three-tooth serrated fan
                fan = [root]
                for tooth in (-1, 0, 1):
                    fan.append(root + nm * handed * (length + 3 - abs(tooth)) + tg * tooth * (breadth + 2))
                fan.append(root)
                arr = np.rint(np.stack(fan)).astype(np.int32)
                cv2.polylines(paint, [arr], False, col, 2, cv2.LINE_AA)
                cv2.polylines(masks["serrated_fans"], [arr], False, 255, 2, cv2.LINE_AA)
            elif family == 3:  # curled tip, attached to the same node
                centre = root + nm * handed * (length * .72)
                ang = math.degrees(math.atan2(nm[1] * handed, nm[0] * handed))
                cv2.ellipse(paint, tuple(np.rint(centre).astype(int)), (int(length), int(breadth + 2)), ang, 30, 305, col, 2, cv2.LINE_AA)
                cv2.ellipse(masks["curl_tendrils"], tuple(np.rint(centre).astype(int)), (int(length), int(breadth + 2)), ang, 30, 305, 255, 2, cv2.LINE_AA)
            elif family == 4:  # torn window in a short leaf lip
                centre = root + nm * handed * (length * .65)
                ang = math.degrees(math.atan2(nm[1] * handed, nm[0] * handed))
                cv2.ellipse(paint, tuple(np.rint(centre).astype(int)), (int(breadth + 3), int(length)), ang, 0, 360, col, -1, cv2.LINE_AA)
                cv2.ellipse(paint, tuple(np.rint(centre + tg * 1.5).astype(int)), (max(2, int(breadth - 1)), max(3, int(length * .45))), ang, 0, 360, dark, -1, cv2.LINE_AA)
                cv2.ellipse(masks["torn_windows"], tuple(np.rint(centre).astype(int)), (int(breadth + 3), int(length)), ang, 0, 360, 255, 2, cv2.LINE_AA)
            elif family == 5:  # node band determined by rachis location
                a0, a1 = c - nm * (width + 3), c + nm * (width + 3)
                cv2.line(paint, tuple(np.rint(a0).astype(int)), tuple(np.rint(a1).astype(int)), col, 3, cv2.LINE_AA)
                cv2.line(masks["node_bands"], tuple(np.rint(a0).astype(int)), tuple(np.rint(a1).astype(int)), 255, 3, cv2.LINE_AA)
            else:  # over/under scar: short angled occlusion, not a glyph scatter
                a0 = c - tg * (length + 2) - nm * handed * 2
                a1 = c + tg * (length + 2) + nm * handed * 2
                cv2.line(paint, tuple(np.rint(a0).astype(int)), tuple(np.rint(a1).astype(int)), dark, 4, cv2.LINE_AA)
                cv2.line(paint, tuple(np.rint(a0 + nm * handed * 2).astype(int)), tuple(np.rint(a1 + nm * handed * 2).astype(int)), col, 2, cv2.LINE_AA)
                cv2.line(masks["over_under_scars"], tuple(np.rint(a0).astype(int)), tuple(np.rint(a1).astype(int)), 255, 4, cv2.LINE_AA)
        records.append(poly)

    # Sparse crossing collars are only placed at true chronology intersections.
    crossings = []
    samples = [p[::12] for p in records]
    for a in range(len(samples)):
        for b in range(a + 1, len(samples)):
            d = np.sum((samples[a][:, None, :] - samples[b][None, :, :]) ** 2, axis=2)
            ia, ib = np.unravel_index(np.argmin(d), d.shape)
            if d[ia, ib] < 64:
                c = (samples[a][ia] + samples[b][ib]) // 2
                if -10 < c[0] < n + 10 and -10 < c[1] < n + 10 and all(np.linalg.norm(c - q) > 42 for q in crossings):
                    crossings.append(c)
    for j, c in enumerate(crossings):
        cv2.ellipse(paint, tuple(c), (5 + j % 4, 3 + (j * 2) % 3), (j * 47) % 180, 0, 360,
                    _rgb(palette, j * 7 + 11, 1.12), 2, cv2.LINE_AA)
        cv2.ellipse(masks["over_under_scars"], tuple(c), (5 + j % 4, 3 + (j * 2) % 3), (j * 47) % 180, 0, 360, 255, 2, cv2.LINE_AA)
    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/leaf_whorl_braid_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats, masks = [], [], None
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
    return "fractured-wilds-leaf-whorl-braid-i1: rejected and fail-closed"


if __name__ == "__main__":
    main()
