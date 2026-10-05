# -*- coding: utf-8 -*-
"""Isolated native-2048 Magenta Bloom growth-genealogy study.

SPB-105 / Wilds attempt 89 / 2026-08-25. A single connected, close-cropped
compound surface grows through an explicit parent/daughter history. Unequal
lobes, compressed division necks, contact saddles, age skins, wet rims,
rupture scars, tethered buds and repair stitches are derived from that history.
This is not a repeated-cell field, Voronoi/paver, particle scatter, sampled
noise, recolour fallback or shared composer. Local marks are 8--32 px native.

Native-2048 verdict: REJECTED. The smooth union exposes a huge amoeba/bubble
diagram: macro lobes, pale perimeter and dark voids dominate while genealogy
marks read as decorative cartoon scars. This violates both the fine-feature
doctrine and the predeclared bubble/cell veto. Frozen before spec/M7/runtime.
No lobe, union threshold, crop, palette, rim, scar, density, scale or noise
repair is authorized; a successor must replace the carrier completely.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_magenta_bloom"
ATTEMPT = 89
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (12, 2, 26), (31, 3, 53), (57, 5, 82), (87, 8, 107),
    (119, 12, 128), (151, 18, 143), (181, 27, 151), (207, 43, 154),
    (226, 66, 153), (239, 94, 151), (246, 127, 153), (246, 162, 164),
    (239, 194, 185), (220, 220, 211), (188, 238, 235),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (2, 17, 28), (3, 38, 55), (4, 64, 77), (6, 91, 95),
    (10, 119, 106), (18, 147, 108), (31, 174, 104), (51, 198, 96),
    (78, 218, 87), (111, 232, 83), (149, 239, 88), (187, 239, 105),
    (217, 232, 132), (238, 216, 169), (248, 194, 209),
], np.float32) / 255.0

# x, y, rx, ry, rotation degrees, parent, age. Large overlap is deliberate:
# this must form one organism, not a field of coin-like cells.
LOBES = (
    (442, 559, 238, 184, -19, -1, .92),
    (268, 425, 181, 136, 31, 0, .78),
    (635, 420, 203, 149, -34, 0, .71),
    (651, 669, 188, 139, 29, 0, .66),
    (313, 713, 168, 122, -41, 0, .61),
    (116, 321, 146, 104, 18, 1, .48),
    (317, 233, 127, 91, -24, 1, .43),
    (781, 283, 161, 106, 42, 2, .39),
    (871, 505, 138, 98, -13, 2, .34),
    (827, 781, 147, 104, 12, 3, .31),
    (575, 878, 139, 95, -38, 3, .27),
    (151, 842, 122, 86, 33, 4, .22),
    (-4, 176, 105, 72, -21, 5, .18),
    (361, 92, 96, 67, 47, 6, .15),
    (933, 165, 114, 76, -46, 7, .12),
    (1055, 561, 112, 78, 28, 8, .10),
    (957, 927, 101, 69, -17, 9, .08),
    (483, 1037, 92, 62, 39, 10, .06),
)


def _ramp(t, palette):
    u = np.clip(t, 0, 1) * (len(palette) - 1)
    i = np.minimum(u.astype(np.int32), len(palette) - 2)
    f = (u - i)[..., None]
    return palette[i] * (1 - f) + palette[i + 1] * f


def _ellipse_metric(xx, yy, lobe):
    x, y, rx, ry, degrees, _parent, _age = lobe
    angle = np.deg2rad(degrees)
    ca, sa = np.cos(angle), np.sin(angle)
    dx, dy = xx - x, yy - y
    u = (ca * dx + sa * dy) / rx
    v = (-sa * dx + ca * dy) / ry
    return u * u + v * v


def _point(lobe, fraction):
    x, y, _rx, _ry, _degrees, parent, _age = lobe
    if parent < 0:
        return np.asarray((x, y), np.float32)
    px, py = LOBES[parent][0], LOBES[parent][1]
    return np.asarray((px + (x - px) * fraction, py + (y - py) * fraction), np.float32)


def _render(angle_b=False):
    palette = PALETTE_B if angle_b else PALETTE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)

    # Analytic smooth union. Top-two influence is retained to locate actual
    # parent/daughter saddles rather than scattering marks over the canvas.
    influences = []
    for lobe in LOBES:
        d2 = _ellipse_metric(xx, yy, lobe)
        influences.append(np.exp(-2.72 * d2))
    weights = np.stack(influences, axis=0).astype(np.float32)
    total = weights.sum(axis=0)
    inside = total > .177
    dominant = np.argmax(weights, axis=0)
    sorted_w = np.partition(weights, -2, axis=0)
    saddle = np.clip(sorted_w[-2] / (sorted_w[-1] + 1e-6), 0, 1)

    # Relief is one compound surface with compressed necks. It does not expose
    # the individual ellipse outlines as a repeated motif.
    height = np.zeros_like(total)
    height[inside] = np.clip(np.log(total[inside] / .177) / 2.20, 0, 1)
    height *= .72 + .28 * (1 - saddle ** 1.7)
    gy, gx = np.gradient(height)
    nz = np.ones_like(height) * .46
    norm = np.sqrt(gx * gx + gy * gy + nz * nz) + 1e-6
    nx, ny, nz = -gx / norm, -gy / norm, nz / norm
    lx, ly = ((-.71, -.37) if angle_b else (.62, -.54))
    shade = np.clip(.35 + .56 * (nx * lx + ny * ly + nz * .74), .10, 1.03)

    ages = np.asarray([v[6] for v in LOBES], np.float32)
    age_field = ages[dominant]
    # Fractured color flipping comes from optical travel over the curved surface,
    # age and saddle compression; no noise perturbs or disguises the topology.
    travel = (age_field * .43 + (nx * .19 + ny * .13) + height * .38
              + saddle * .17 + (.38 if angle_b else 0.0)) % 1.0
    paint = _ramp(travel, palette) * shade[..., None]
    substrate = _ramp(((xx * .00023 + yy * .00017) + (.19 if angle_b else 0)) % 1, palette)
    paint[~inside] = substrate[~inside] * .085

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "compound_surface", "division_necks", "contact_saddles", "age_skins",
        "wet_rims", "rupture_scars", "tethered_buds", "repair_stitches",
        "daughter_fans", "healed_pores")}
    masks["compound_surface"][inside] = 255

    # One outer wet rim follows the union silhouette, never each source lobe.
    union_u8 = masks["compound_surface"]
    contours, _ = cv2.findContours(union_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(masks["wet_rims"], contours, -1, 255, 6, cv2.LINE_AA)
    cv2.drawContours(paint, contours, -1,
                     tuple(float(v) for v in np.clip(palette[12] * 1.08, 0, 1)),
                     5, cv2.LINE_AA)

    # Draw compressed necks and short saddle fans only between real relations.
    for j, lobe in enumerate(LOBES[1:], start=1):
        parent = lobe[5]
        child = np.asarray(lobe[:2], np.float32)
        elder = np.asarray(LOBES[parent][:2], np.float32)
        axis = child - elder
        axis /= np.linalg.norm(axis) + 1e-6
        normal = np.asarray((-axis[1], axis[0]), np.float32)
        neck = _point(lobe, .54 + .05 * ((j % 3) - 1))
        half = 5 + (j * 7) % 11  # 10--30 px native total width.
        a, b = neck - normal * half, neck + normal * half
        color = tuple(float(v) for v in np.clip(palette[(j * 5 + 3) % 15] * 1.15, 0, 1))
        cv2.line(paint, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), color, 3, cv2.LINE_AA)
        cv2.line(masks["division_necks"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)), 255, 3, cv2.LINE_AA)
        for k in (-2, -1, 1, 2):
            root = neck + axis * (4 + 3 * abs(k))
            tip = root + normal * k * (3 + j % 4) + axis * (6 + (j + k) % 5)
            cv2.line(paint, tuple(np.rint(root).astype(int)), tuple(np.rint(tip).astype(int)),
                     color, 2, cv2.LINE_AA)
            cv2.line(masks["daughter_fans"], tuple(np.rint(root).astype(int)),
                     tuple(np.rint(tip).astype(int)), 255, 2, cv2.LINE_AA)

    # Saddle mask is causal analytic overlap, rendered as fine broken tissue.
    saddle_zone = inside & (saddle > .71)
    masks["contact_saddles"][saddle_zone] = 255
    saddle_edge = cv2.Canny((saddle_zone.astype(np.uint8) * 255), 80, 160)
    saddle_edge = cv2.bitwise_and(saddle_edge, union_u8)
    paint[saddle_edge > 0] = np.clip(palette[3] * .54, 0, 1)

    # Age skins are sparse short arcs inside selected older lobes—not complete
    # rings. Ruptures interrupt those arcs and carry their own attached stitches.
    for j in (0, 1, 2, 3, 4, 7, 10):
        x, y, rx, ry, degrees, _parent, _age = LOBES[j]
        for q, radius in enumerate((.34, .51, .68)):
            start = (j * 47 + q * 83 + 19) % 260
            sweep = 31 + (j * 13 + q * 9) % 58
            axes = (max(4, int(rx * radius)), max(4, int(ry * radius)))
            color = tuple(float(v) for v in np.clip(palette[(j * 4 + q * 3 + 7) % 15] * (1.02 + .04 * q), 0, 1))
            cv2.ellipse(paint, (x, y), axes, degrees, start, start + sweep, color, 3, cv2.LINE_AA)
            cv2.ellipse(masks["age_skins"], (x, y), axes, degrees, start, start + sweep, 255, 3, cv2.LINE_AA)

    rupture_specs = ((0, .12, -13), (1, .72, 8), (2, .61, -9), (3, .46, 12), (7, .53, -7), (10, .67, 10))
    for j, fraction, bend in rupture_specs:
        x, y, rx, ry, degrees, _parent, _age = LOBES[j]
        a = np.deg2rad(degrees + 31 + j * 29)
        centre = np.asarray((x + np.cos(a) * rx * fraction, y + np.sin(a) * ry * fraction), np.float32)
        tangent = np.asarray((-np.sin(a), np.cos(a)), np.float32)
        normal = np.asarray((np.cos(a), np.sin(a)), np.float32)
        pts = []
        for k in range(-4, 5):
            p = centre + tangent * k * (3.1 + (j % 2)) + normal * (bend * (1 - (k / 4) ** 2) + 2.4 * np.sin(k * 1.7 + j))
            pts.append(np.rint(p).astype(np.int32))
        poly = np.asarray(pts, np.int32)
        cv2.polylines(paint, [poly], False, (0.004, 0.002, 0.009), 5, cv2.LINE_AA)
        cv2.polylines(masks["rupture_scars"], [poly], False, 255, 5, cv2.LINE_AA)
        for k in (-3, -1, 1, 3):
            p = pts[k + 4].astype(np.float32)
            a0, b0 = p - normal * (3 + j % 3), p + normal * (4 + (j + k) % 4)
            cv2.line(paint, tuple(np.rint(a0).astype(int)), tuple(np.rint(b0).astype(int)),
                     tuple(float(v) for v in np.clip(palette[(j * 3 + k + 11) % 15] * 1.2, 0, 1)), 2, cv2.LINE_AA)
            cv2.line(masks["repair_stitches"], tuple(np.rint(a0).astype(int)),
                     tuple(np.rint(b0).astype(int)), 255, 2, cv2.LINE_AA)

    # Tiny pores are placed on genealogy landmarks, not random sites.
    for j in range(1, len(LOBES), 2):
        p = _point(LOBES[j], .76)
        radius = 3 + j % 5
        cv2.circle(paint, tuple(np.rint(p).astype(int)), radius, (0.006, .003, .012), 2, cv2.LINE_AA)
        cv2.circle(masks["healed_pores"], tuple(np.rint(p).astype(int)), radius, 255, 2, cv2.LINE_AA)

    # Last-generation edge buds remain connected to their parent by short tethers.
    for j in range(12, len(LOBES)):
        child = np.asarray(LOBES[j][:2], np.float32)
        tether = _point(LOBES[j], .78)
        cv2.line(paint, tuple(np.rint(tether).astype(int)), tuple(np.rint(child).astype(int)),
                 tuple(float(v) for v in np.clip(palette[(j + 9) % 15] * 1.12, 0, 1)), 4, cv2.LINE_AA)
        cv2.line(masks["tethered_buds"], tuple(np.rint(tether).astype(int)),
                 tuple(np.rint(child).astype(int)), 255, 4, cv2.LINE_AA)

    return np.clip(paint, 0, 1), masks


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/magenta_bloom_genealogy_i1")
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
    return "fractured-wilds-magenta-bloom-genealogy-i1: fail-closed pending native review"


if __name__ == "__main__":
    main()
