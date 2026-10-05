# -*- coding: utf-8 -*-
"""Isolated native-2048 Tiger Beetle maculation/corrugation study.

SPB-105 / Wilds attempt 90 / 2026-08-25. One full-frame elytral surface carries
continuously shifting fine furrows crossed by a non-repeating branching cream
maculation. Puncta, raised interstriae, sutures, spines, abrasion breaks,
edge-bristles, callus plates, fork collars and repair bars attach to those two
systems. No sampled noise, dot scatter, paver, repeated stamp, recolour fallback
or shared composer is used. Visible primitive widths are 8--32 px at native.

Native-2048 verdict: REJECTED. The background becomes repeated black ring/pit
columns on corrugated rails while the cream system reads as a branching path
diagram. Sutures, bristles, spines, abrasion and repair marks remain decorative.
Fine density did not cure repeated-unit laziness. Frozen before spec/M7/runtime.
No furrow, puncta, path, palette, density, scale, spec or noise repair is
authorized; a successor must replace both carrier and maculation language.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_tiger_beetle"
ATTEMPT = 90
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (2, 8, 12), (3, 24, 30), (4, 48, 50), (5, 74, 62), (8, 101, 68),
    (14, 129, 68), (25, 157, 65), (43, 183, 60), (69, 205, 57),
    (101, 222, 63), (139, 232, 80), (178, 234, 108), (211, 226, 143),
    (232, 209, 178), (243, 184, 212),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (15, 3, 19), (38, 4, 39), (66, 5, 57), (96, 8, 68), (127, 13, 73),
    (157, 22, 73), (185, 34, 69), (210, 50, 65), (229, 72, 63),
    (242, 99, 67), (247, 130, 78), (245, 162, 99), (233, 192, 128),
    (213, 216, 163), (184, 232, 201),
], np.float32) / 255.0

CREAM_A = np.asarray((242, 220, 158), np.float32) / 255.0
CREAM_B = np.asarray((161, 239, 220), np.float32) / 255.0


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _path(points, samples=180):
    points = np.asarray(points, np.float32)
    curve = []
    for j in range(len(points) - 1):
        a = points[max(0, j - 1)]
        b = points[j]
        c = points[j + 1]
        d = points[min(len(points) - 1, j + 2)]
        count = max(8, samples // (len(points) - 1))
        for t in np.linspace(0, 1, count, endpoint=False, dtype=np.float32):
            t2, t3 = t * t, t * t * t
            p = .5 * ((2 * b) + (-a + c) * t +
                      (2 * a - 5 * b + 4 * c - d) * t2 +
                      (-a + 3 * b - 3 * c + d) * t3)
            curve.append(p)
    curve.append(points[-1])
    return np.rint(np.asarray(curve)).astype(np.int32)


MACULATION = (
    ((-40, 164), (92, 211), (202, 304), (315, 362), (430, 402), (555, 489), (690, 548)),
    ((238, 321), (204, 219), (244, 128), (340, 42), (413, -32)),
    ((414, 396), (478, 302), (552, 224), (620, 119), (651, -25)),
    ((554, 490), (532, 604), (586, 706), (693, 783), (814, 820), (1056, 792)),
    ((657, 545), (742, 485), (812, 389), (851, 258), (952, 176), (1050, 158)),
    ((587, 701), (488, 779), (381, 842), (247, 867), (111, 942), (-42, 1014)),
    ((814, 819), (777, 918), (807, 1013), (845, 1060)),
)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    cream = CREAM_B if angle_b else CREAM_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)

    # Fine corrugated surface: spacing and direction change continuously, and
    # two phase slips interrupt the order. There is no stochastic carrier.
    bend = (xx + 54 * np.sin(yy / 83.0) + 23 * np.sin((xx + yy) / 147.0)
            + .00019 * (yy - 510) ** 2)
    spacing = 10.5 + 1.9 * np.sin(yy / 109.0) + 1.2 * np.sin(xx / 173.0)
    phase = bend / spacing
    phase += .63 * (xx > (407 + .18 * yy)) + .41 * (xx > (768 - .13 * yy))
    ridge = .5 + .5 * np.cos(2 * np.pi * phase)
    ridge2 = .5 + .5 * np.cos(4 * np.pi * phase + .7)
    relief = .70 * ridge ** 5 + .30 * ridge2 ** 7
    gy, gx = np.gradient(relief)
    optical = (phase * .043 + .20 * np.arctan2(gy, gx) / np.pi
               + .17 * relief + (.41 if angle_b else 0.0)) % 1.0
    shade = np.clip(.24 + .64 * relief + .14 * gx - .09 * gy, .08, 1.05)
    paint = _ramp(optical, palette) * shade[..., None]

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "corrugated_elytron", "branching_maculation", "cream_edge_bristles",
        "ordered_puncta", "elytral_sutures", "abrasion_breaks", "fork_collars",
        "repair_bars", "shoulder_callus", "spine_roots")}
    masks["corrugated_elytron"][:] = 255

    mac = np.zeros((WORK, WORK), np.uint8)
    curves = []
    for j, control in enumerate(MACULATION):
        curve = _path(control)
        curves.append(curve)
        width = 10 + (j * 5) % 7  # 20--32 px native.
        cv2.polylines(mac, [curve], False, 255, width, cv2.LINE_AA)
    # Fork collars are local enlargements at real branch junctions.
    for p, axes, angle in (((414, 396), (16, 9), 28), ((554, 490), (14, 8), 61),
                           ((587, 701), (15, 9), -32), ((814, 819), (13, 8), 18)):
        cv2.ellipse(mac, p, axes, angle, 0, 360, 255, -1, cv2.LINE_AA)
        cv2.ellipse(masks["fork_collars"], p, axes, angle, 0, 360, 255, 3, cv2.LINE_AA)

    # Cream is modulated by the underlying corrugation so it remains paint on
    # the same physical shell, not a flat vector overlay.
    cream_field = cream[None, None, :] * (.63 + .36 * relief[..., None])
    active = mac > 8
    paint[active] = cream_field[active]
    masks["branching_maculation"] = mac

    # Edge bristles attach to alternating sides of the actual cream paths.
    for j, curve in enumerate(curves):
        for k in range(9 + j % 4, len(curve) - 10, 11 + (j * 3) % 7):
            a = curve[k - 2].astype(np.float32)
            b = curve[k + 2].astype(np.float32)
            tangent = b - a
            tangent /= np.linalg.norm(tangent) + 1e-6
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            side = -1 if (j + k) % 3 else 1
            root = curve[k].astype(np.float32) + normal * side * (5 + j % 3)
            tip = root + normal * side * (4 + (j * 7 + k) % 9) + tangent * ((k % 5) - 2)
            color = tuple(float(v) for v in np.clip(palette[(j * 3 + k) % 15] * 1.23, 0, 1))
            cv2.line(paint, tuple(np.rint(root).astype(int)), tuple(np.rint(tip).astype(int)), color, 2, cv2.LINE_AA)
            cv2.line(masks["cream_edge_bristles"], tuple(np.rint(root).astype(int)),
                     tuple(np.rint(tip).astype(int)), 255, 2, cv2.LINE_AA)

    # Ordered puncta occupy interstriae but are deleted where maculation or wear
    # says they cannot exist. Their position derives from the corrugation order.
    puncta = masks["ordered_puncta"]
    for row in range(8, 1024, 13):
        offset = int(17 * np.sin(row / 71.0) + (row * 7) % 23)
        for col in range(-20 + offset, 1044, 23 + (row // 91) % 5):
            x = int(col + 15 * np.sin(row / 89.0) + 7 * np.sin(col / 137.0))
            y = int(row + 3 * np.sin(col / 47.0))
            if 4 <= x < 1020 and 4 <= y < 1020 and mac[y, x] < 24:
                radius = 2 + ((row * 5 + col * 3) % 4)
                cv2.ellipse(paint, (x, y), (radius + 1, radius), int(phase[y, x] * 19) % 180,
                            0, 360, (0.002, .004, .005), 2, cv2.LINE_AA)
                cv2.ellipse(puncta, (x, y), (radius + 1, radius), 0, 0, 360, 255, 2, cv2.LINE_AA)

    # Two unequal shell sutures interrupt both furrows and puncta.
    for j, control in enumerate((((-20, 721), (176, 665), (348, 649), (519, 612), (704, 596), (1045, 631)),
                                 ((737, -20), (721, 166), (747, 347), (721, 518), (744, 704), (697, 1046)))):
        curve = _path(control, 240)
        cv2.polylines(paint, [curve], False, (0.002, .003, .006), 7 + j * 2, cv2.LINE_AA)
        cv2.polylines(paint, [curve], False,
                      tuple(float(v) for v in np.clip(palette[10 - 2 * j] * 1.12, 0, 1)),
                      2, cv2.LINE_AA)
        cv2.polylines(masks["elytral_sutures"], [curve], False, 255, 7 + j * 2, cv2.LINE_AA)

    # Abrasion breaks are short, oriented cuts tied to cream/furrow crossings.
    for j, centre in enumerate(((178, 276), (352, 384), (523, 474), (676, 556),
                                (785, 421), (596, 739), (277, 858), (820, 817))):
        x, y = centre
        angle = phase[y, x] * .23 + j * .61
        tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        for k in (-2, -1, 0, 1, 2):
            root = np.asarray(centre, np.float32) + normal * k * 4
            tip = root + tangent * (7 + (j + k) % 7)
            cv2.line(paint, tuple(np.rint(root).astype(int)), tuple(np.rint(tip).astype(int)),
                     tuple(float(v) for v in np.clip(palette[(j * 4 + k + 8) % 15] * 1.18, 0, 1)), 3, cv2.LINE_AA)
            cv2.line(masks["abrasion_breaks"], tuple(np.rint(root).astype(int)),
                     tuple(np.rint(tip).astype(int)), 255, 3, cv2.LINE_AA)

    # Callus and spine roots are asymmetric anchors, never repeated stamps.
    callus = _path(((868, 58), (905, 89), (919, 143), (903, 197), (862, 226), (824, 195), (817, 126), (836, 76)))
    cv2.polylines(paint, [callus], True, tuple(float(v) for v in np.clip(palette[12] * 1.1, 0, 1)), 6, cv2.LINE_AA)
    cv2.polylines(masks["shoulder_callus"], [callus], True, 255, 6, cv2.LINE_AA)
    for j, root in enumerate(((91, 208), (248, 319), (430, 405), (554, 490), (690, 548), (814, 819))):
        x, y = root
        tip = (x + 7 + j % 4, y - 9 - (j * 3) % 8)
        cv2.line(paint, root, tip, (0.006, .004, .008), 4, cv2.LINE_AA)
        cv2.circle(masks["spine_roots"], root, 4 + j % 3, 255, 2, cv2.LINE_AA)
        cv2.line(masks["spine_roots"], root, tip, 255, 4, cv2.LINE_AA)

    # Fine repair bars cross phase-slip seams at unequal locations.
    for j, (x, y) in enumerate(((405, 114), (433, 279), (472, 533), (505, 812),
                                (764, 95), (745, 338), (739, 683), (716, 906))):
        cv2.line(paint, (x - 5 - j % 3, y - 3), (x + 6, y + 4 + j % 4),
                 tuple(float(v) for v in np.clip(palette[(j * 2 + 11) % 15] * 1.2, 0, 1)), 3, cv2.LINE_AA)
        cv2.line(masks["repair_bars"], (x - 5 - j % 3, y - 3), (x + 6, y + 4 + j % 4), 255, 3, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/tiger_beetle_maculation_i1")
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
    return "fractured-wilds-tiger-beetle-maculation-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
