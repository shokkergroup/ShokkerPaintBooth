# -*- coding: utf-8 -*-
"""Isolated native-2048 Emperor Scale Bouligand-crosscut study.

SPB-105 / Wilds attempt 82 / 2026-08-25.  This paint-first contact tests an
explicit helicoidal arthropod-cuticle construction rather than another scalar
contour, paver, shard field or recoloured scale sheet.  Successive material
plies rotate through depth; finite tapered lamellae overlap across ply seams
and carry attached split tips, kink bands, resin pockets, z-bridges,
delamination rims and abrasion notches.  Every drawn primitive is 8--32 px at
native 2048.  Placement is a deterministic low-discrepancy chronology, not
sampled noise.

Native-2048 verdict: REJECTED.  The low-discrepancy coordinates phase-locked
into widely separated diagonal bead/rail lanes over an almost empty ground;
the six intended depth plies never became a continuous crosscut.  The attached
events merely decorated the same repeated tapered unit.  Frozen before spec,
M7, runtime or owner-test publication.  No sequence, count, ply-angle, density,
palette, lamella, accessory, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_emperor_scale"
WORK = 1024
NATIVE = 2048
ATTEMPT = 82

PALETTE_A = np.asarray([
    (8, 7, 18), (24, 8, 39), (52, 10, 59), (85, 14, 70),
    (121, 22, 76), (158, 36, 75), (192, 57, 69), (219, 84, 61),
    (237, 116, 58), (246, 151, 65), (247, 186, 81), (238, 215, 110),
    (207, 235, 147), (155, 240, 183), (91, 227, 210),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 12, 21), (4, 31, 42), (3, 58, 63), (4, 88, 80),
    (9, 121, 91), (22, 154, 95), (45, 184, 93), (77, 209, 91),
    (116, 226, 94), (158, 235, 106), (197, 232, 126), (227, 214, 150),
    (244, 181, 175), (239, 139, 199), (207, 98, 219),
], np.float32) / 255.0


def _body_poly(cx, cy, theta, half_len, half_width, bend):
    """Seven-point tapered lamella with an asymmetric through-thickness bow."""
    t = np.asarray((np.cos(theta), np.sin(theta)), np.float32)
    n = np.asarray((-t[1], t[0]), np.float32)
    c = np.asarray((cx, cy), np.float32)
    p0 = c - t * half_len
    p1 = c - t * (half_len * .36) + n * (half_width + bend)
    p2 = c + t * (half_len * .32) + n * (half_width - bend * .35)
    p3 = c + t * half_len + n * bend * .18
    p4 = c + t * (half_len * .35) - n * (half_width + bend * .24)
    p5 = c - t * (half_len * .38) - n * (half_width - bend * .42)
    return np.rint(np.asarray((p0, p1, p2, p3, p4, p5))).astype(np.int32), t, n


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    base = np.asarray((.010, .008, .022) if not angle_b else
                      (.003, .017, .023), np.float32)
    glow = np.asarray((.080, .025, .095) if not angle_b else
                      (.010, .085, .074), np.float32)
    vignette = np.clip(1.0 - np.hypot((xx - 463) / 890, (yy - 538) / 820), 0, 1)
    paint = base + glow * vignette[..., None] * .42

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "lamellar_bodies", "ply_seams", "split_tips", "kink_bands",
        "resin_pockets", "z_bridges", "delamination_rims", "abrasion_notches")}

    # Six explicit depth plies.  The low-discrepancy schedule makes material
    # coverage even without any sampled noise, while each ply owns a different
    # director and occludes the previous one like a physical cross-section.
    phi = (5.0 ** .5 - 1.0) * .5
    counts = (1550, 1680, 1810, 1940, 2070, 2200)
    for ply, count in enumerate(counts):
        alpha = .28 + ply * .19
        depth_angle = -.91 + ply * .337 + .12 * np.sin(ply * 1.7)
        for i in range(count):
            u = (i * phi + ply * .137) % 1.0
            v = (i * phi * phi + ply * .263) % 1.0
            cx = -18.0 + u * (WORK + 36.0)
            cy = -18.0 + v * (WORK + 36.0)
            # Three off-canvas stress sources bend the helicoidal plies without
            # turning them into a repeated global stripe field.
            theta = (depth_angle
                     + .31 * np.sin((cy + 37 * ply) / 123.0)
                     - .24 * np.cos((cx - 61 * ply) / 157.0)
                     + .13 * np.sin((cx + cy) / 79.0 + ply))
            half_len = 4.2 + ((i * 17 + ply * 11) % 8) * .52
            half_width = 2.0 + ((i * 13 + ply * 7) % 5) * .43
            bend = np.sin(i * 2.399963 + ply * .91) * half_width * .48
            poly, tangent, normal = _body_poly(cx, cy, theta, half_len, half_width, bend)

            phase = (i * 7 + ply * 3 + int((cx + 1.7 * cy) / 41.0)
                     + (5 if angle_b else 0)) % len(palette)
            shade = .50 + .085 * ply + .16 * np.sin(theta + (-.7 if angle_b else .55))
            color = tuple(float(x) for x in np.clip(palette[phase] * shade, 0, 1))
            shadow = poly + np.asarray((2 + ply % 2, 2 - ply % 3), np.int32)
            cv2.fillConvexPoly(paint, shadow, (0.004, 0.004, 0.010), cv2.LINE_AA)
            cv2.fillConvexPoly(paint, poly, color, cv2.LINE_AA)
            cv2.fillConvexPoly(masks["lamellar_bodies"], poly, 255, cv2.LINE_AA)

            edge_color = tuple(float(x) for x in np.clip(
                palette[(phase + 4) % len(palette)] * (1.02 + .035 * ply), 0, 1))
            cv2.polylines(paint, [poly], True, edge_color, 1, cv2.LINE_AA)
            cv2.polylines(masks["ply_seams"], [poly], True, 255, 1, cv2.LINE_AA)

            centre = np.asarray((cx, cy), np.float32)
            # Attached events have mutually prime clocks and stay causal to the
            # parent lamella instead of forming an independent scatter layer.
            if (i + 3 * ply) % 19 == 0:
                tip = centre + tangent * half_len
                a = tip - tangent * 3 + normal * 2
                b = tip + tangent * 4
                c = tip - tangent * 3 - normal * 2
                pts = np.rint((a, b, c)).astype(np.int32)
                cv2.polylines(paint, [pts], False, (0.006, 0.008, 0.015), 2, cv2.LINE_AA)
                cv2.polylines(masks["split_tips"], [pts], False, 255, 2, cv2.LINE_AA)
            if (i + 5 * ply) % 23 == 0:
                p0 = centre - normal * half_width * .8
                p1 = centre + normal * half_width * .8
                cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                         edge_color, 2, cv2.LINE_AA)
                cv2.line(masks["kink_bands"], tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)), 255, 2, cv2.LINE_AA)
            if (i + 7 * ply) % 31 == 0:
                p = tuple(np.rint(centre - tangent * half_len * .18).astype(int))
                axes = (2 + (i % 3), 1 + ((i // 3) % 2))
                cv2.ellipse(paint, p, axes, int(np.degrees(theta)), 0, 360,
                            tuple(float(x) for x in np.clip(palette[(phase + 8) % 15] * 1.2, 0, 1)),
                            -1, cv2.LINE_AA)
                cv2.ellipse(masks["resin_pockets"], p, axes, int(np.degrees(theta)),
                            0, 360, 255, -1, cv2.LINE_AA)
            if (i + 11 * ply) % 37 == 0:
                p0 = centre - tangent * half_len * .6 - normal * half_width
                p1 = centre + tangent * half_len * .6 + normal * half_width
                cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
                         tuple(float(x) for x in np.clip(palette[(phase + 11) % 15] * 1.18, 0, 1)),
                         2, cv2.LINE_AA)
                cv2.line(masks["z_bridges"], tuple(np.rint(p0).astype(int)),
                         tuple(np.rint(p1).astype(int)), 255, 2, cv2.LINE_AA)
            if (i + 13 * ply) % 41 == 0:
                p = tuple(np.rint(centre + normal * half_width * .42).astype(int))
                cv2.ellipse(paint, p, (3 + i % 4, 2), int(np.degrees(theta)), 20, 205,
                            (0.004, 0.006, 0.012), 2, cv2.LINE_AA)
                cv2.ellipse(masks["delamination_rims"], p, (3 + i % 4, 2),
                            int(np.degrees(theta)), 20, 205, 255, 2, cv2.LINE_AA)
            if (i + 17 * ply) % 47 == 0:
                p = tuple(np.rint(centre - tangent * half_len * .72).astype(int))
                cv2.circle(paint, p, 2 + i % 2, (0.003, 0.004, 0.009), -1, cv2.LINE_AA)
                cv2.circle(masks["abrasion_notches"], p, 2 + i % 2, 255, -1, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/emperor_bouligand_crosscut_i2")
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
    crop = native_a[672:1376, 672:1376]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID, "module": __name__, "attempt": ATTEMPT,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {name: float((mask > 8).mean()) for name, mask in masks.items()},
        "owner_accepted": False, "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-emperor-bouligand-crosscut-i2: fail-closed pending native review"


if __name__ == "__main__":
    main()
