# -*- coding: utf-8 -*-
"""Isolated native-2048 Atlas Wing mimic-tapestry study.

SPB-105 / Wilds attempt 93 / 2026-08-25. One off-canvas close crop of an Atlas
moth snake-head mimic fills the surface through unequal cheek, crown, jaw,
throat and costal territories. Each is physically filled by fine scale packets
whose order terminates at hooked seams. False-mouth clefts, serrated jaw teeth,
vein locks, torn scale pockets, powder plates, hinge wedges and repair bars are
attached to those boundaries. No repeated head stamp, eye/bullseye, paver,
sampled noise, sparse rail sketch, recolour fallback or shared composer is used.
Primitive widths are 8--32 px native; large organization emerges from them.

Native-2048 verdict: REJECTED. Full coverage exposes uniform diagonal dot/rail
wallpaper divided into polygon panels and thick road-like seams. The mimic,
clefts, teeth, locks, pockets, powder, wedges and repairs remain overlay
decoration. Frozen before spec/M7/runtime. No region, phase, spacing, seam,
palette, event, density, scale, spec or noise repair is authorized; a successor
must replace both the fine carrier and panel/road language.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_atlas_wing"
ATTEMPT = 93
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (5, 4, 15), (20, 7, 35), (42, 11, 56), (70, 16, 72), (99, 22, 82),
    (129, 30, 86), (158, 41, 86), (186, 56, 81), (209, 75, 75),
    (226, 99, 72), (237, 128, 78), (239, 158, 94), (230, 187, 119),
    (211, 214, 151), (182, 233, 191),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (2, 10, 24), (3, 29, 48), (4, 53, 68), (5, 79, 82), (8, 107, 88),
    (14, 136, 87), (24, 165, 81), (40, 190, 72), (62, 211, 65),
    (89, 227, 66), (123, 237, 77), (161, 239, 96), (197, 232, 123),
    (224, 216, 157), (241, 193, 199),
], np.float32) / 255.0

REGIONS = (
    # name, polygon, rotation, spacing, optical base
    ("crown", ((-90, -70), (558, -42), (946, 92), (1118, 318), (874, 410), (518, 304), (96, 231), (-76, 111)), -17, 10.5, .08),
    ("upper_cheek", ((-84, 202), (145, 165), (478, 271), (716, 432), (639, 584), (319, 520), (56, 408)), 23, 11.5, .26),
    ("false_mouth", ((279, 343), (527, 337), (760, 450), (884, 589), (738, 663), (503, 575), (343, 489)), -31, 8.5, .47),
    ("lower_jaw", ((-112, 469), (196, 402), (441, 541), (662, 750), (567, 1018), (76, 1098), (-96, 881)), 18, 12.0, .67),
    ("throat", ((559, 577), (831, 468), (1110, 501), (1110, 1059), (537, 1059), (612, 817)), -43, 9.5, .83),
    ("costal_hook", ((688, -32), (1091, -38), (1095, 520), (878, 495), (767, 292)), 39, 13.0, .94),
)


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _region_mask(poly):
    mask = np.zeros((WORK, WORK), np.uint8)
    cv2.fillPoly(mask, [np.asarray(poly, np.int32)], 255, cv2.LINE_AA)
    return mask


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    substrate = _ramp((xx * .00031 + yy * .00019 + (.17 if angle_b else 0)) % 1, palette)
    paint = substrate * .09
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "mimic_surface", "crown_scales", "cheek_scales", "mouth_scales",
        "jaw_scales", "throat_scales", "costal_scales", "hooked_seams",
        "false_mouth_clefts", "serrated_jaw_teeth", "vein_locks",
        "torn_scale_pockets", "powder_plates", "hinge_wedges", "repair_bars")}
    region_masks = []

    for region_index, (name, poly, degrees, spacing, optical_base) in enumerate(REGIONS):
        mask = _region_mask(poly)
        region_masks.append(mask)
        masks["mimic_surface"] = np.maximum(masks["mimic_surface"], mask)
        theta = np.deg2rad(degrees)
        ca, sa = np.cos(theta), np.sin(theta)
        u = xx * ca + yy * sa
        v = -xx * sa + yy * ca
        # Fine overlapping scale packets: ridge phase is chopped by a second
        # oblique phase so it cannot become an uninterrupted rail field.
        bend = 5.4 * np.sin(v / (47 + region_index * 6) + region_index * .8)
        ridge_phase = (u + bend + 7.0 * np.sin((u + v) / 109.0)) / spacing
        cut_phase = (v + 4.0 * np.sin(u / 61.0)) / (7.0 + region_index * .7)
        ridge = .5 + .5 * np.cos(2 * np.pi * ridge_phase)
        packet_gate = (.5 + .5 * np.cos(2 * np.pi * cut_phase))
        packet_relief = np.clip((ridge - .42) * 1.7, 0, 1) * (.47 + .53 * packet_gate)
        gy, gx = np.gradient(packet_relief)
        travel = (optical_base + ridge_phase * .071 + packet_gate * .16
                  + gx * .17 - gy * .11 + (.39 if angle_b else 0.0)) % 1.0
        shade = np.clip(.24 + .68 * packet_relief + .13 * gx - .08 * gy, .08, 1.06)
        color = _ramp(travel, palette) * shade[..., None]
        active = mask > 8
        paint[active] = color[active]
        scale_key = ("crown_scales", "cheek_scales", "mouth_scales",
                     "jaw_scales", "throat_scales", "costal_scales")[region_index]
        scale_active = active & (packet_relief > .31)
        masks[scale_key][scale_active] = 255

    # The six territory boundaries are physically different seams. Dark lips
    # and bright return edges stay fine while their long organization emerges.
    seam_curves = (
        ((-20, 222), (158, 188), (365, 244), (558, 337), (742, 417), (1019, 333)),
        ((31, 420), (193, 391), (354, 470), (513, 584), (692, 661), (917, 603), (1042, 521)),
        ((314, 345), (452, 365), (591, 432), (712, 509), (852, 584)),
        ((-30, 490), (151, 461), (304, 522), (441, 631), (573, 756), (592, 992)),
        ((610, 610), (755, 552), (894, 516), (1047, 548)),
        ((704, -8), (741, 145), (789, 303), (882, 475)),
    )
    seam_points = []
    for j, control in enumerate(seam_curves):
        curve = np.asarray(control, np.int32)
        seam_points.append(curve)
        cv2.polylines(paint, [curve], False, (0.003, .002, .007), 9 + j % 4, cv2.LINE_AA)
        cv2.polylines(paint, [curve], False,
                      tuple(float(v) for v in np.clip(palette[(j * 3 + 12) % 15] * 1.18, 0, 1)), 3, cv2.LINE_AA)
        cv2.polylines(masks["hooked_seams"], [curve], False, 255, 9 + j % 4, cv2.LINE_AA)

    # False-mouth clefts are unequal hooked fissures inside the dedicated
    # territory, never an eye/target or repeated head icon.
    clefts = (
        ((377, 417), (455, 393), (535, 418), (581, 466), (550, 497)),
        ((506, 490), (593, 471), (675, 505), (729, 552), (701, 586)),
        ((623, 570), (699, 559), (771, 586), (807, 620)),
    )
    for j, control in enumerate(clefts):
        curve = np.asarray(control, np.int32)
        cv2.polylines(paint, [curve], False, (0.002, .001, .004), 12 - j * 2, cv2.LINE_AA)
        cv2.polylines(masks["false_mouth_clefts"], [curve], False, 255, 12 - j * 2, cv2.LINE_AA)

    # Teeth, vein locks, tears, powder plates, wedges, and repairs attach to
    # explicit seam arc locations—no random fleck layer is permitted.
    for seam_index, curve in enumerate(seam_points):
        for k in range(1, len(curve) - 1):
            a, b, c = curve[k - 1].astype(np.float32), curve[k].astype(np.float32), curve[k + 1].astype(np.float32)
            tangent = c - a
            tangent /= np.linalg.norm(tangent) + 1e-6
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            for q in (.22, .46, .71):
                p = b * (1 - q) + c * q
                event = (seam_index * 11 + k * 5 + int(q * 100)) % 6
                color = tuple(float(v) for v in np.clip(palette[(seam_index * 4 + k + event + 9) % 15] * 1.2, 0, 1))
                if event == 0:
                    p0, p1 = p, p + normal * (7 + seam_index % 5) + tangent * 4
                    cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)), color, 3, cv2.LINE_AA)
                    cv2.line(masks["serrated_jaw_teeth"], tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)), 255, 3, cv2.LINE_AA)
                elif event == 1:
                    p0, p1 = p - normal * 6, p + normal * 7
                    cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)), color, 3, cv2.LINE_AA)
                    cv2.line(masks["vein_locks"], tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)), 255, 3, cv2.LINE_AA)
                elif event == 2:
                    cv2.ellipse(paint, tuple(np.rint(p).astype(int)), (6 + k % 4, 3 + seam_index % 3),
                                int(np.degrees(np.arctan2(tangent[1], tangent[0]))), 0, 360, (0.003, .002, .006), 3, cv2.LINE_AA)
                    cv2.ellipse(masks["torn_scale_pockets"], tuple(np.rint(p).astype(int)), (6 + k % 4, 3 + seam_index % 3), 0, 0, 360, 255, 3, cv2.LINE_AA)
                elif event == 3:
                    cv2.circle(paint, tuple(np.rint(p).astype(int)), 4 + (k + seam_index) % 4, color, 2, cv2.LINE_AA)
                    cv2.circle(masks["powder_plates"], tuple(np.rint(p).astype(int)), 4 + (k + seam_index) % 4, 255, 2, cv2.LINE_AA)
                elif event == 4:
                    tri = np.asarray((p - tangent * 5, p + tangent * 6 - normal * 5, p + tangent * 4 + normal * 6), np.int32)
                    cv2.polylines(paint, [tri], True, color, 3, cv2.LINE_AA)
                    cv2.fillPoly(masks["hinge_wedges"], [tri], 255, cv2.LINE_AA)
                else:
                    for step in (-1, 1):
                        p0 = p + tangent * step * 5 - normal * 5
                        p1 = p + tangent * step * 5 + normal * 5
                        cv2.line(paint, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)), color, 2, cv2.LINE_AA)
                        cv2.line(masks["repair_bars"], tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)), 255, 2, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/atlas_wing_mimic_i1")
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
    return "fractured-wilds-atlas-wing-mimic-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
