# -*- coding: utf-8 -*-
"""Native-2048 Leaf Whorl differential-growth lamina.

SPB-105 / Wilds attempt 98 / 2026-08-25. This is a continuous asymmetric leaf
lamina assembled by nested growth lips that pinch, split and rejoin around one
off-centre damaged whorl. Five causal fine anatomies remain part of the sheet:
primary lips, secondary split veins, serrated growth fronts, rupture windows,
and over/under seam crossings. No RNG/noise, leaf stamps, glyph scatter,
radial rosette, generic chevrons or shared composer. Fractured A/B reverses
optical face history without moving geometry. All visible bands are 8--32 px
at native 2048.

SPB-105 / Wilds attempt 98: owner doctrine rejects recolored or repeated
carriers and rejects noise used as a distinction. Native review is a provisional
owner-test keep: M7 N/A -> 87.6, collision audit vs. 17 survivors has no
actionable pair (max paint 0.239303; max spec 0.041602), exact native
paint+spec is under 0.434 s. Owner accepted: false.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fbl_leaf_whorl"
ATTEMPT = 98
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (3, 9, 20), (8, 27, 43), (9, 54, 58), (11, 86, 66),
    (19, 122, 67), (42, 158, 66), (78, 188, 67), (128, 209, 70),
    (184, 222, 78), (225, 218, 91), (245, 188, 105), (244, 143, 117),
    (220, 94, 129), (174, 58, 136), (104, 38, 119),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (22, 4, 30), (50, 6, 57), (82, 9, 79), (117, 14, 94),
    (155, 23, 101), (194, 37, 98), (226, 58, 87), (246, 88, 72),
    (253, 126, 62), (246, 168, 64), (220, 205, 75), (165, 222, 91),
    (102, 216, 111), (46, 188, 128), (20, 137, 132),
], np.float32) / 255.0

M_TIERS = np.asarray((14, 39, 70, 105, 143, 181, 220, 248), np.uint8)
R_TIERS = np.asarray((18, 45, 76, 111, 148, 187, 225, 252), np.uint8)
CC_TIERS = np.asarray((10, 34, 63, 98, 136, 176, 216, 250), np.uint8)


def _fields():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + .5) / WORK * 2 - 1
    y = (yy + .5) / WORK * 2 - 1
    z = x + 1j * y
    wx = x + .11 * np.sin(5.3 * y + 1.1 * np.sin(3.1 * x))
    wy = y + .09 * np.sin(4.1 * x - 1.3 * np.cos(2.7 * y))
    radius = np.sqrt((wx * (1 + .18 * y)) ** 2 + (wy * (1 - .13 * x)) ** 2)
    angle = np.arctan2(wy, wx)
    chronology = (radius * (31 + 4 * np.sin(3 * angle))
                  + 1.7 * np.sin(5 * angle) + .8 * np.sin(9 * angle + 8 * radius)
                  + .35 * np.real(z ** 3))
    primary_wave = np.sin(np.pi * chronology)
    split_phase = chronology * .503 + 5.7 * angle + .23 * np.sin(7 * radius - 3 * angle)
    split_wave = np.sin(np.pi * split_phase)
    lip = (1 - np.abs(primary_wave)) ** 2
    split_vein = (1 - np.abs(split_wave)) ** 4
    serration = (1 - np.abs(np.sin(np.pi * (chronology * .247 - 9.3 * angle)))) ** 5
    pinch = np.exp(-((radius - (.20 + .055 * np.sin(3 * angle))) / .075) ** 2)
    crossing = lip * split_vein
    rupture = np.clip(crossing * (1 - serration) * (1.15 - radius), 0, 1) ** 2
    relief = lip + .38 * split_vein + .18 * serration + .32 * pinch
    return {"x": x, "y": y, "radius": radius, "angle": angle,
            "chronology": chronology, "primary_wave": primary_wave,
            "split_wave": split_wave, "growth_lips": lip,
            "split_veins": split_vein, "serrated_fronts": serration,
            "pinch_seams": pinch, "rupture_windows": rupture,
            "over_under_crossings": crossing, "relief": relief}


def _palette_map(t, palette):
    q = np.mod(t, 1.0) * len(palette)
    i = np.floor(q).astype(np.int16) % len(palette)
    f = (q - np.floor(q))[..., None]
    return palette[i] * (1 - f) + palette[(i + 1) % len(palette)] * f


def _paint(angle_b=False):
    f = _fields()
    palette = PALETTE_B if angle_b else PALETTE_A
    chronology = f["chronology"]
    optical = (chronology / 31 + .11 * np.sin(2 * f["angle"] + 7 * f["radius"])
               + .045 * f["split_wave"])
    if angle_b:
        optical = 1.07 - optical + .16 * np.sin(3 * f["angle"] - 5 * f["radius"])
    rgb = _palette_map(optical, palette)
    light = (.28 + .48 * np.clip(f["relief"], 0, 1)
             + .14 * (f["primary_wave"] * .5 + .5)
             + .08 * (f["split_wave"] * .5 + .5))
    rgb *= light[..., None]
    # Anatomy changes sheet optics rather than arriving as pasted symbols.
    rgb += f["serrated_fronts"][..., None] * palette[10] * .10
    rgb += f["pinch_seams"][..., None] * palette[12] * .12
    rgb *= (1 - f["rupture_windows"][..., None] * .62)
    return np.clip(rgb, 0, 1).astype(np.float32), f


def _spec_maps(f):
    # Three independent continuous material histories. Tiering happens only
    # after causal sheet anatomy is combined, avoiding the former angular ×
    # radial checker carrier and its macro forced-value pinch ring.
    age = f["chronology"]
    ang = f["angle"]
    rad = f["radius"]
    metal = (.39 + .34 * np.sin(np.pi * (.713 * age + 2.9 * ang + 1.7 * rad))
             + .21 * f["growth_lips"] + .13 * f["over_under_crossings"]
             - .25 * f["rupture_windows"] + .05 * f["pinch_seams"])
    rough = (.50 + .25 * np.cos(np.pi * (1.117 * age - 4.1 * ang + .9 * rad))
             + .20 * f["serrated_fronts"] + .12 * f["rupture_windows"]
             - .17 * f["split_veins"] - .06 * f["pinch_seams"])
    coat = (.41 + .32 * np.sin(np.pi * (.379 * age + 7.3 * ang - 2.4 * rad))
            + .22 * f["split_veins"] + .14 * f["serrated_fronts"]
            - .19 * f["rupture_windows"] + .04 * f["pinch_seams"])
    mi = np.floor(np.clip(metal, 0, .9999) * 8).astype(np.int16)
    ri = np.floor(np.clip(rough, 0, .9999) * 8).astype(np.int16)
    ci = np.floor(np.clip(coat, 0, .9999) * 8).astype(np.int16)
    return M_TIERS[mi], R_TIERS[ri], CC_TIERS[ci]


def _authored():
    paint, fields = _paint(False)
    spec = np.stack(_spec_maps(fields), axis=2)
    return paint, spec


def _native_paint(paint):
    return cv2.resize(paint, (NATIVE, NATIVE), interpolation=cv2.INTER_CUBIC)


def main():
    out = Path("_wilds_fullres_progress_20260824/leaf_whorl_lamina_i2")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats, fields = [], [], None
    for _ in range(3):
        started = time.perf_counter()
        paint, fields = _paint(False)
        native = np.clip(_native_paint(paint) * 255 + .5, 0, 255).astype(np.uint8)
        repeats.append(native)
        timings.append(time.perf_counter() - started)
    angle_b, _ = _paint(True)
    native_a = repeats[0]
    native_b = np.clip(_native_paint(angle_b) * 255 + .5, 0, 255).astype(np.uint8)
    for name, image in (("paint", native_a), ("angle_a", native_a), ("angle_b", native_b)):
        cv2.imwrite(str(out / f"{ID}_{name}_2048.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(native_a[704:1344, 704:1344], cv2.COLOR_RGB2BGR))
    spec = np.stack(_spec_maps(fields), axis=2)
    spec_native = cv2.resize(spec, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    for name, channel in zip(("metallic", "roughness", "clearcoat"), cv2.split(spec_native)):
        cv2.imwrite(str(out / f"{ID}_{name}_2048.png"), channel)
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255
    flat = spec_native.reshape(-1, 3).astype(np.float32)
    corr = np.corrcoef(flat, rowvar=False)
    report = {"id": ID, "attempt": ATTEMPT, "status": "NATIVE-2048-GATES-PENDING",
              "timings_s": timings, "deterministic": bool(all(np.array_equal(native_a, im) for im in repeats[1:])),
              "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95)),
              "coverage": {name: float((fields[name] > threshold).mean()) for name, threshold in (
                  ("growth_lips", .62), ("split_veins", .58), ("serrated_fronts", .72),
                  ("pinch_seams", .58), ("rupture_windows", .20), ("over_under_crossings", .34))},
              "spec_ranges": {name: [int(flat[:, i].min()), int(flat[:, i].max())] for i, name in enumerate(("M", "R", "Cc"))},
              "spec_std": {name: float(flat[:, i].std()) for i, name in enumerate(("M", "R", "Cc"))},
              "spec_correlations": {"M_R": float(corr[0, 1]), "M_Cc": float(corr[0, 2]), "R_Cc": float(corr[1, 2])},
              "owner_accepted": False, "production_wired": False}
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-leaf-whorl-lamina-i2: fail-closed pending gates"


if __name__ == "__main__":
    main()
