# -*- coding: utf-8 -*-
"""Isolated native-2048 Duck Speculum mirror-panel joint study.

SPB-105 / Wilds attempt 91 / 2026-08-25. Thousands of unequal fine feather
shingles form one continuous surface and terminate against an asymmetric,
damaged speculum joint. White/brown boundary laminae, microbarb mirrors,
overlap locks, water grooves, torn lips, order breaks, down pockets, pinched
tips and repair hooks are attached to that construction. There is no sampled
noise, generic feather row, horizontal stripe, Magpie zipper, paver-only output,
recolour fallback or shared composer. Primitive widths are 8--32 px native.

Native-2048 verdict: REJECTED. The thousands of packets collapse into a
homogeneous micro-shingle/static carpet split into brown and green territories;
the damaged joint and all attached events remain subordinate. Fine coverage did
not create hierarchy or a recognizable speculum material. Frozen before
spec/M7/runtime. No packet, region, palette, joint, event, density, scale, spec
or noise repair is authorized; a successor must replace both dominant carriers.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_duck_speculum"
ATTEMPT = 91
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (2, 5, 12), (3, 16, 31), (3, 32, 55), (4, 51, 75), (5, 73, 88),
    (8, 97, 94), (14, 122, 92), (25, 148, 83), (44, 172, 72),
    (70, 194, 65), (103, 210, 70), (140, 220, 87), (178, 221, 113),
    (211, 211, 147), (232, 191, 188),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (18, 2, 24), (43, 3, 47), (72, 5, 66), (102, 8, 78), (132, 14, 85),
    (161, 23, 88), (188, 36, 87), (212, 53, 83), (230, 75, 80),
    (242, 101, 82), (247, 131, 91), (244, 162, 109), (232, 191, 134),
    (211, 216, 166), (181, 232, 204),
], np.float32) / 255.0

BROWN = np.asarray((86, 47, 27), np.float32) / 255.0
WHITE = np.asarray((231, 224, 194), np.float32) / 255.0
BLACK = np.asarray((3, 5, 8), np.float32) / 255.0


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _halton(index, base):
    value, factor, n = 0.0, 1.0 / base, int(index) + 1
    while n:
        value += factor * (n % base)
        n //= base
        factor /= base
    return value


def _joint_u(v):
    return 483.0 + 52.0 * np.sin(v / 117.0 + .4) + 21.0 * np.sin(v / 43.0 - .9)


def _xy(u, v):
    angle = np.deg2rad(24.0)
    ca, sa = np.cos(angle), np.sin(angle)
    x = u * ca - v * sa + 102.0
    y = u * sa + v * ca - 173.0
    return np.asarray((x, y), np.float32)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    paint = np.zeros((WORK, WORK, 3), np.float32)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "unequal_shingles", "mirror_panel", "white_lamina", "brown_lamina",
        "microbarb_mirrors", "overlap_locks", "water_grooves", "torn_lips",
        "order_breaks", "down_pockets", "pinched_tips", "repair_hooks")}

    # Dark underfeather is a physical substrate revealed through overlaps.
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    base_phase = (xx * .00041 + yy * .00029 + (.21 if angle_b else 0.0)) % 1
    paint[:] = _ramp(base_phase, palette) * .075

    # Rows are curved and locally re-ordered. Every packet receives unequal
    # width, length, skew, optical order and damage from deterministic sequences.
    packet_index = 0
    for row, v in enumerate(np.arange(-270.0, 1240.0, 10.0)):
        row_shift = 18.0 * np.sin(row * .73) + 9.0 * np.sin(row * .217 + .6)
        u = -250.0 + row_shift
        while u < 1320.0:
            q2, q3, q5 = _halton(packet_index, 2), _halton(packet_index, 3), _halton(packet_index, 5)
            width = 5.0 + 8.0 * q2
            length = 7.0 + 9.0 * q3
            centre_u = u + width * .5
            boundary = _joint_u(v)
            distance = centre_u - boundary
            # Four physically different regions meet at one complex joint.
            if distance < -25:
                region, region_phase = "brown", .09
            elif distance < -12:
                region, region_phase = "white", .27
            elif distance < -4:
                region, region_phase = "black", .43
            else:
                region, region_phase = "mirror", .61

            local_turn = (7.5 * np.sin(v / 81.0 + centre_u / 233.0)
                          + 4.0 * np.sin(centre_u / 59.0 + row * .11))
            # Packets approaching the joint rotate into it and terminate rather
            # than crossing as an uninterrupted generic row.
            if abs(distance) < 76:
                local_turn += np.sign(distance) * (16.0 * (1 - abs(distance) / 76.0))
                length *= .72 + .28 * min(1.0, abs(distance) / 36.0)
            angle = np.deg2rad(local_turn)
            tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            c = _xy(centre_u, v + (q5 - .5) * 4.2)
            heel = c - tangent * length * .47
            tip = c + tangent * length * .53
            half = width * .48
            # Unequal six-point shingle with a pinched or torn leading tip.
            notch = (q2 - .5) * width * .35
            poly = np.asarray((
                heel - normal * half * .73,
                c - normal * half,
                tip - normal * half * .44,
                tip + tangent * (1.6 + 2.2 * q5) + normal * notch,
                tip + normal * half * .44,
                c + normal * half,
                heel + normal * half * .73,
            ), np.float32)
            poly_i = np.rint(poly).astype(np.int32)

            optical = (region_phase + q3 * .23 + q5 * .13
                       + local_turn / 110.0 + (.39 if angle_b else 0.0)) % 1
            if region == "brown":
                color = BROWN * (.53 + .39 * q3) + palette[int(optical * 14)] * .16
            elif region == "white":
                color = WHITE * (.66 + .29 * q2) + palette[int(optical * 14)] * .08
            elif region == "black":
                color = BLACK * .8 + palette[int(optical * 14)] * .11
            else:
                color = palette[int(optical * 14)] * (.49 + .47 * q2)
            color = tuple(float(z) for z in np.clip(color, 0, 1))
            cv2.fillPoly(paint, [poly_i], color, cv2.LINE_AA)
            cv2.fillPoly(masks["unequal_shingles"], [poly_i], 255, cv2.LINE_AA)
            if region == "mirror":
                cv2.fillPoly(masks["mirror_panel"], [poly_i], 255, cv2.LINE_AA)
            elif region == "white":
                cv2.fillPoly(masks["white_lamina"], [poly_i], 255, cv2.LINE_AA)
            elif region == "brown":
                cv2.fillPoly(masks["brown_lamina"], [poly_i], 255, cv2.LINE_AA)

            # Each packet owns a midrib mirror, overlap lip and either a lock,
            # groove, torn tip or repair hook—never detached decorative noise.
            rib_a = heel + tangent * length * .16
            rib_b = tip - tangent * length * .13
            rib_color = tuple(float(z) for z in np.clip(palette[(packet_index * 7 + 9) % 15] * 1.18, 0, 1))
            cv2.line(paint, tuple(np.rint(rib_a).astype(int)), tuple(np.rint(rib_b).astype(int)), rib_color, 2, cv2.LINE_AA)
            cv2.line(masks["microbarb_mirrors"], tuple(np.rint(rib_a).astype(int)), tuple(np.rint(rib_b).astype(int)), 255, 2, cv2.LINE_AA)
            cv2.line(paint, tuple(poly_i[0]), tuple(poly_i[-1]), tuple(float(z) for z in BLACK * .75), 2, cv2.LINE_AA)
            cv2.line(masks["overlap_locks"], tuple(poly_i[0]), tuple(poly_i[-1]), 255, 2, cv2.LINE_AA)

            event = (packet_index * 11 + row * 7) % 13
            if event in (0, 1, 2):
                a = c - normal * half * .55
                b = c + normal * half * .55
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                         tuple(float(z) for z in np.clip(palette[(packet_index + 12) % 15] * 1.2, 0, 1)), 2, cv2.LINE_AA)
                cv2.line(masks["water_grooves"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 2, cv2.LINE_AA)
            elif event in (3, 4):
                a = tip - normal * half * .35
                b = tip + normal * half * .32
                cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), tuple(float(z) for z in BLACK), 3, cv2.LINE_AA)
                cv2.line(masks["torn_lips"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)
            elif event == 5:
                cv2.circle(paint, tuple(np.rint(c).astype(int)), 3 + packet_index % 3,
                           tuple(float(z) for z in np.clip(palette[(packet_index + 5) % 15] * 1.12, 0, 1)), 2, cv2.LINE_AA)
                cv2.circle(masks["down_pockets"], tuple(np.rint(c).astype(int)), 3 + packet_index % 3, 255, 2, cv2.LINE_AA)
            elif event == 6:
                hook = tip + tangent * 3 + normal * (3 if packet_index % 2 else -3)
                cv2.line(paint, tuple(np.rint(tip).astype(int)), tuple(np.rint(hook).astype(int)), rib_color, 2, cv2.LINE_AA)
                cv2.circle(masks["repair_hooks"], tuple(np.rint(hook).astype(int)), 3, 255, 2, cv2.LINE_AA)
            elif event == 7:
                cv2.circle(masks["pinched_tips"], tuple(np.rint(tip).astype(int)), 3, 255, -1, cv2.LINE_AA)

            u += width * (.82 + .20 * q5)
            packet_index += 1

    # Joint-level order breaks displace real packet rows without becoming one
    # smooth zipper or stripe. Short saw cuts, wet lips and hook bridges attach.
    for j, v in enumerate(np.linspace(-110, 1130, 19, dtype=np.float32)):
        u = _joint_u(v) + (-9 if j % 3 == 0 else 7)
        c = _xy(u, v)
        tangent = _xy(u + 7, v) - _xy(u - 7, v)
        tangent /= np.linalg.norm(tangent) + 1e-6
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        a = c - normal * (4 + j % 5)
        b = c + normal * (5 + (j * 3) % 6)
        cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                 tuple(float(z) for z in np.clip(palette[(j * 4 + 10) % 15] * 1.2, 0, 1)), 3, cv2.LINE_AA)
        cv2.line(masks["order_breaks"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/duck_speculum_joint_i1")
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
              "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED", "packet_count": packet_index if False else None,
              "timings_s": timings,
              "deterministic": bool(all(np.array_equal(repeats[0], x) for x in repeats[1:])),
              "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95)),
              "coverage": {k: float((v > 8).mean()) for k, v in masks.items()},
              "owner_accepted": False, "production_wired": False}
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-duck-speculum-joint-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
