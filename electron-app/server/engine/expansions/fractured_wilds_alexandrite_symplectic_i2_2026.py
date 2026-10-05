# -*- coding: utf-8 -*-
"""Isolated native-2048 Alexandrite symplectic-twin study.

SPB-105 / Wilds attempt 70 / 2026-08-25. I1's winner-take-all polygon domains
and diagonal stripe wallpaper are discarded. I2 uses a deterministic iterated
area-preserving shear map (the newer coordinate-map math) to fold three
continuous crystal twin systems through one another without discrete domains.
Visible observables are primary twins, secondary branches, wedge fronts,
dislocation forks, healed crossings, cleavage nicks and inclusion trails.

All local bands are 4--16 work pixels (8--32 px native). No RNG, sampled noise,
FBM, scalar geology, polygon territories, stamp bank, shared composer or recolor
fallback.

Native-2048 verdict: REJECTED. The sheet is attractive but visibly one warped
parallel-line/guilloche carrier; wedges, nicks, trails and crossings only change
line color or cadence, and the dislocation-fork mask is empty. Frozen before
spec/M7/runtime. No frequency, shear, palette, line, mask, screw, scale, spec or
noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_alexandrite_dusk"
WORK = 1024
NATIVE = 2048
TAU = np.float32(2.0 * np.pi)

PALETTE_A = np.asarray([
    (12, 5, 22), (24, 7, 45), (42, 9, 73), (64, 12, 101),
    (88, 16, 126), (116, 22, 145), (147, 31, 157), (177, 45, 161),
    (204, 65, 158), (225, 91, 151), (239, 122, 146), (244, 157, 149),
    (234, 193, 169), (197, 221, 198), (136, 229, 219),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 18, 25), (4, 35, 44), (3, 57, 62), (3, 83, 78),
    (5, 111, 90), (12, 140, 99), (28, 169, 105), (52, 196, 109),
    (84, 218, 114), (124, 235, 124), (171, 244, 142), (216, 245, 168),
    (250, 232, 195), (255, 193, 188), (244, 136, 190),
], np.float32) / 255.0


def _norm(value):
    value = value.astype(np.float32)
    return (value - value.min()) / (float(np.ptp(value)) + 1e-7)


def _distance_to_integer(phase):
    frac = phase - np.floor(phase)
    return np.minimum(frac, 1.0 - frac)


def _fields():
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    u = xx / WORK - .5
    v = yy / WORK - .5
    # Five exact symplectic kick-drift passes: each shear has determinant one.
    for turn in range(5):
        u = u + (.017 + turn * .0023) * np.sin(
            TAU * ((3.0 + turn * .37) * v + .13 * np.sin(TAU * (u - .21 * v)))
            + turn * .71)
        v = v + (.015 + turn * .0019) * np.sin(
            TAU * ((2.6 + turn * .41) * u - .17 * np.sin(TAU * (v + .19 * u)))
            - turn * .53)

    # Seventeen analytic screw dislocations alter the phase but are never
    # rendered as circles/icons; they create local branch/fork events in twins.
    screw = np.zeros_like(u)
    for i in range(17):
        cx = -.46 + .92 * ((i * .6180339887498948 + .07 * np.sin(i)) % 1.0)
        cy = -.46 + .92 * ((i * .4142135623730950 + .09 * np.sin(i * 1.31)) % 1.0)
        sign = -1.0 if i & 1 else 1.0
        screw += sign * np.arctan2(v - cy, u - cx) / TAU

    p1 = 71.0 * u + 23.0 * v + .47 * screw + .26 * np.sin(TAU * (3.1 * v - .7 * u))
    p2 = -31.0 * u + 67.0 * v - .39 * screw + .21 * np.sin(TAU * (2.7 * u + 1.3 * v))
    p3 = 49.0 * (u + v) + .23 * screw + .18 * np.sin(TAU * (2.2 * u - 2.5 * v))

    d1, d2, d3 = (_distance_to_integer(p) for p in (p1, p2, p3))
    primary = np.clip((.105 - d1) / .055, 0, 1)
    secondary = np.clip((.092 - d2) / .050, 0, 1)
    tertiary = np.clip((.072 - d3) / .038, 0, 1)

    # Observable families come from causal intersections of the three twins.
    healed = np.minimum(primary, secondary)
    wedges = np.clip(primary * (1.0 - secondary) *
                     (.5 + .5 * np.sin(TAU * (p2 * .17 + p3 * .11))), 0, 1)
    branches = np.clip(secondary * (1.0 - .72 * primary) + .55 * healed, 0, 1)
    nicks = np.clip(tertiary * primary *
                    (.5 + .5 * np.sin(TAU * (p2 * .31 - p1 * .19))), 0, 1)

    # Fork cores are winding-gradient maxima, not placed glyphs.
    gy1, gx1 = np.gradient(np.sin(TAU * p1).astype(np.float32))
    gy2, gx2 = np.gradient(np.sin(TAU * p2).astype(np.float32))
    winding = _norm(np.abs(gx1 * gy2 - gy1 * gx2))
    forks = np.clip((winding - .72) / .24, 0, 1) * np.clip(1.4 * healed, 0, 1)

    # Inclusion trails are interrupted along tertiary cleavage only where the
    # local two-twin strain exceeds a physical threshold.
    strain = _norm(np.abs(np.sin(TAU * p1) - np.sin(TAU * p2)))
    gate = np.clip((strain - .66) / .22, 0, 1)
    trail_cadence = np.clip((np.sin(TAU * (p1 * .113 + p2 * .071)) - .18) / .65, 0, 1)
    trails = tertiary * gate * trail_cadence

    relief = (.33 * np.sin(TAU * p1) + .28 * np.sin(TAU * p2)
              + .19 * np.sin(TAU * p3) + .20 * np.sin(TAU * (p1 - p2) * .37))
    relief = _norm(relief)
    return {
        "primary_twins": primary.astype(np.float32),
        "secondary_branches": branches.astype(np.float32),
        "wedge_fronts": wedges.astype(np.float32),
        "dislocation_forks": forks.astype(np.float32),
        "healed_crossings": healed.astype(np.float32),
        "cleavage_nicks": nicks.astype(np.float32),
        "inclusion_trails": trails.astype(np.float32),
        "relief": relief.astype(np.float32),
        "phase": _norm(.43 * p1 + .37 * p2 + .20 * p3).astype(np.float32),
    }


def _paint(angle_b=False):
    f = _fields()
    palette = PALETTE_B if angle_b else PALETTE_A
    phase = np.mod(f["phase"] * 2.7 + .21 * f["relief"], 1.0)
    idx = np.clip(np.floor(phase * 15.0).astype(np.int32), 0, 14)
    paint = palette[idx] * (.47 + .47 * f["relief"][..., None])
    if angle_b:
        layers = (
            (f["primary_twins"], (0.06, .92, .72), .86),
            (f["secondary_branches"], (.90, .22, .74), .84),
            (f["wedge_fronts"], (.93, .78, .20), .87),
            (f["dislocation_forks"], (.98, .95, .66), .97),
            (f["healed_crossings"], (.22, .52, .96), .90),
            (f["cleavage_nicks"], (.99, .45, .31), .94),
            (f["inclusion_trails"], (.07, .08, .12), .97),
        )
    else:
        layers = (
            (f["primary_twins"], (.88, .19, .69), .87),
            (f["secondary_branches"], (.24, .91, .84), .84),
            (f["wedge_fronts"], (.99, .51, .25), .88),
            (f["dislocation_forks"], (1.0, .92, .64), .97),
            (f["healed_crossings"], (.46, .30, .92), .90),
            (f["cleavage_nicks"], (.99, .74, .20), .94),
            (f["inclusion_trails"], (.025, .012, .05), .98),
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
    out = Path("_wilds_fullres_progress_20260824/alexandrite_symplectic_i2")
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
    crop = native_a[640:1152, 704:1216]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    report = {
        "id": ID,
        "module": __name__,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 70,
        "math": "five-pass deterministic symplectic kick-drift map plus analytic screw phase",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {key: float(value.mean()) for key, value in fields.items()
                     if key not in ("relief", "phase")},
        "owner_accepted": False,
        "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
