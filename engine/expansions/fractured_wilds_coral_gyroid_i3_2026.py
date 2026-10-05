# -*- coding: utf-8 -*-
"""Isolated native-2048 Coral Cluster porous-accretion study.

SPB-105 / Wilds attempt 71 / 2026-08-25. The rejected cell/polyp paver and
tree-with-polyp-stamps are discarded. I3 is one continuous, analytically warped
triply-periodic accretion sheet. Corallite walls, coenosteum pores, septa,
calice throats, budding necks, broken rims and growth lips are distinct
intersections of the same material chronology, not placed objects.

Local wall/pore periods are 4--16 work pixels (8--32 px native). No RNG,
sampled noise, FBM, DLA/tree, cell stamps, scalar texture, shared composer or
recolor fallback.

Native-2048 verdict: REJECTED. The continuous gyroid intersections collapse
into homogeneous high-frequency static/micro-maze; nine named masks are not
visually distinguishable. Deterministic math does not excuse noise-like contact.
Frozen before spec/M7/runtime. No frequency, phase, warp, palette, threshold,
mask, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fbl_coral_cluster"
WORK = 1024
NATIVE = 2048
TAU = np.float32(2.0 * np.pi)

PALETTE_A = np.asarray([
    (25, 5, 12), (49, 8, 18), (78, 12, 25), (109, 17, 31),
    (141, 24, 38), (174, 34, 47), (203, 48, 57), (228, 67, 70),
    (245, 91, 86), (253, 120, 106), (255, 153, 130), (253, 185, 157),
    (242, 213, 183), (211, 232, 204), (157, 232, 218),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (3, 20, 28), (3, 37, 49), (3, 58, 69), (4, 82, 88),
    (7, 108, 103), (15, 136, 113), (29, 163, 119), (52, 188, 121),
    (84, 211, 123), (123, 228, 131), (167, 239, 148), (209, 243, 173),
    (242, 235, 201), (254, 204, 202), (245, 158, 210),
], np.float32) / 255.0


def _norm(a):
    a = a.astype(np.float32)
    return (a - a.min()) / (float(np.ptp(a)) + 1e-7)


def _ridge(value, center, halfwidth):
    return np.clip(1.0 - np.abs(value - center) / halfwidth, 0.0, 1.0)


def _fields():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    u = xx / WORK
    v = yy / WORK
    # Analytic invertible drift avoids a rectilinear cubic-phase screen while
    # preserving one continuous sheet and exact determinism.
    for turn in range(3):
        u = u + (.0069 + turn * .0011) * np.sin(
            TAU * ((3.3 + .41 * turn) * v + .27 * np.sin(TAU * u)) + turn)
        v = v + (.0061 + turn * .0009) * np.sin(
            TAU * ((2.9 + .37 * turn) * u - .23 * np.sin(TAU * v)) - turn * .7)

    x = TAU * (67.0 * u + 11.0 * v)
    y = TAU * (-17.0 * u + 71.0 * v)
    z = TAU * (43.0 * (u + v) + .23 * np.sin(TAU * (2.7 * u - 1.9 * v)))
    g = (np.sin(x) * np.cos(y) + np.sin(y) * np.cos(z)
         + np.sin(z) * np.cos(x)) / 1.5

    x2 = TAU * (59.0 * u - 23.0 * v + .07 * np.sin(z))
    y2 = TAU * (29.0 * u + 61.0 * v + .06 * np.sin(x))
    z2 = TAU * (-47.0 * u + 37.0 * v + .05 * np.cos(y))
    h = (np.sin(x2) * np.cos(y2) + np.sin(y2) * np.cos(z2)
         + np.sin(z2) * np.cos(x2)) / 1.5

    ag, ah = np.abs(g), np.abs(h)
    body = np.clip((.66 - ag) / .18, 0, 1)
    wall = _ridge(ag, .34, .105)
    growth_lips = _ridge(ag, .57, .070)
    calice_throats = np.clip((ah - .61) / .22, 0, 1) * body
    septa = _ridge(np.sin(TAU * (8.0 * u + 5.0 * v + .17 * h)), 0.0, .14)
    septa *= calice_throats * np.clip((.54 - ag) / .18, 0, 1)
    bud_necks = _ridge(ag, .22, .065) * _ridge(ah, .28, .080)
    pores = _ridge(ah, .08, .050) * np.clip((.58 - ag) / .22, 0, 1)
    broken_gate = np.clip((np.sin(TAU * (13.0 * u - 9.0 * v + .21 * g)) - .34) / .56,
                          0, 1)
    broken_rims = wall * broken_gate
    healed = np.minimum(wall, _ridge(ah, .43, .075))

    # A relief normal gives mass; it is a physical derivative, not a texture.
    relief = _norm(.52 * g + .31 * h + .17 * np.sin(x - y + .37 * z))
    age = _norm(.46 * g - .39 * h + .15 * np.sin(.7 * x + .4 * z))
    return {
        "coenosteum_body": body.astype(np.float32),
        "corallite_walls": wall.astype(np.float32),
        "calice_throats": calice_throats.astype(np.float32),
        "septa": septa.astype(np.float32),
        "budding_necks": bud_necks.astype(np.float32),
        "coenosteum_pores": pores.astype(np.float32),
        "broken_rims": broken_rims.astype(np.float32),
        "healed_crossings": healed.astype(np.float32),
        "growth_lips": growth_lips.astype(np.float32),
        "relief": relief.astype(np.float32),
        "age": age.astype(np.float32),
    }


def _paint(angle_b=False):
    f = _fields()
    palette = PALETTE_B if angle_b else PALETTE_A
    phase = np.mod(f["age"] * 3.2 + .19 * f["relief"], 1.0)
    idx = np.clip(np.floor(phase * 15.0).astype(np.int32), 0, 14)
    paint = palette[idx] * (.34 + .61 * f["relief"][..., None])
    # Inert void is still colored but subdued; the sheet remains full-canvas.
    body = f["coenosteum_body"][..., None]
    paint = paint * (.38 + .62 * body)
    if angle_b:
        layers = (
            (f["coenosteum_body"], (.04, .46, .41), .43),
            (f["corallite_walls"], (.13, .94, .75), .91),
            (f["calice_throats"], (.73, .19, .81), .86),
            (f["septa"], (.98, .86, .29), .96),
            (f["budding_necks"], (.98, .45, .69), .92),
            (f["coenosteum_pores"], (.015, .04, .07), .98),
            (f["broken_rims"], (.98, .35, .24), .95),
            (f["healed_crossings"], (.30, .50, .97), .91),
            (f["growth_lips"], (.78, .96, .57), .88),
        )
    else:
        layers = (
            (f["coenosteum_body"], (.54, .07, .10), .43),
            (f["corallite_walls"], (.98, .31, .28), .91),
            (f["calice_throats"], (.09, .73, .70), .87),
            (f["septa"], (1.0, .87, .43), .96),
            (f["budding_necks"], (.96, .54, .26), .92),
            (f["coenosteum_pores"], (.025, .01, .018), .98),
            (f["broken_rims"], (.99, .68, .24), .95),
            (f["healed_crossings"], (.72, .30, .87), .91),
            (f["growth_lips"], (.98, .57, .55), .88),
        )
    for mask, color, alpha in layers:
        a = np.clip(mask * alpha, 0, 1)[..., None]
        paint = paint * (1.0 - a) + np.asarray(color, np.float32) * a
    return np.clip(paint, 0, 1), f


def _up(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_LINEAR)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/coral_gyroid_i3")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    fields = None
    for _ in range(3):
        started = time.perf_counter()
        paint, fields = _paint(False)
        repeats.append(_u8(_up(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _paint(True)
    native_a, native_b = repeats[0], _u8(_up(angle_b))
    cv2.imwrite(str(out / f"{ID}_paint_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_a_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_b_2048.png"), cv2.cvtColor(native_b, cv2.COLOR_RGB2BGR))
    crop = native_a[704:1216, 832:1344]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID,
        "module": __name__,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 71,
        "math": "warped triply-periodic gyroid accretion intersections",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {key: float(value.mean()) for key, value in fields.items()
                     if key not in ("relief", "age")},
        "owner_accepted": False,
        "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
