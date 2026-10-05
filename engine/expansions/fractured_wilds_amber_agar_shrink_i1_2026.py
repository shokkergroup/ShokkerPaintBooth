# -*- coding: utf-8 -*-
"""Isolated native-2048 Amber Agar shrinkage-chronology study.

SPB-105 / Wilds attempt 68 / 2026-08-25. This replaces the rejected explicit
builder's sparse rail-and-loop carrier. A deterministic concurrent crack-growth
chronology creates primary ruptures, collision-stopped secondary crazing,
one-sided lifted lips, healed cross-bridges, junction pits, wet inclusions and
receding gel fronts. The stress director is analytic and is never painted.

Every drawn primitive is 4--16 work pixels (8--32 px at native 2048). There is
no RNG, sampled noise, FBM, Voronoi/polygon paver, stamp bank, shared composer,
or recolor fallback.

Native-2048 verdict: REJECTED. Collision stopping fragmented nearly every crack
into the same glowing bean/capsule unit while the distance coloring became giant
diagonal scalar lobes. Frozen before spec/M7/runtime. No collision, density,
director, age-field, palette, glyph, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fpe_amber_agar"
WORK = 1024
NATIVE = 2048
TAU = 2.0 * np.pi

PALETTE_A = np.asarray([
    (24, 10, 17), (45, 14, 18), (75, 23, 15), (108, 37, 12),
    (145, 58, 13), (187, 85, 18), (224, 122, 29), (247, 166, 55),
    (255, 207, 103), (255, 238, 169), (184, 88, 52), (116, 43, 58),
    (60, 29, 57), (39, 67, 67), (54, 112, 96),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (8, 21, 27), (10, 42, 49), (11, 70, 73), (13, 104, 99),
    (19, 142, 118), (42, 181, 132), (89, 213, 139), (156, 231, 143),
    (221, 242, 170), (250, 231, 190), (240, 162, 176), (222, 91, 172),
    (174, 57, 169), (108, 49, 150), (55, 44, 112),
], np.float32) / 255.0


def _director(x: float, y: float, lineage: int, step: int) -> float:
    """Analytic stress direction; never exposed as paint or texture."""
    xn, yn = x / WORK, y / WORK
    gx = (1.17 * np.cos(TAU * (1.31 * xn + .47 * yn) + lineage * .113)
          + .71 * np.cos(TAU * (.39 * xn - 1.73 * yn) + step * .017)
          + .43 * np.sin(TAU * (2.11 * xn + 1.07 * yn)))
    gy = (1.09 * np.sin(TAU * (.61 * xn + 1.43 * yn) - lineage * .071)
          - .66 * np.sin(TAU * (1.91 * xn - .53 * yn) + step * .013)
          + .47 * np.cos(TAU * (1.13 * xn + 2.03 * yn)))
    return float(np.arctan2(gy, gx))


def _seed_tips():
    tips = []
    # Unequal edge-origin chronology: no repeated radial nuclei or star hubs.
    for i in range(54):
        side = (i * 7 + i // 5) % 4
        q = ((i * .6180339887498948 + .137 * np.sin(i * 1.127)) % 1.0)
        if side == 0:
            x, y, angle = 2.0, 20.0 + 984.0 * q, -.16 + .32 * np.sin(i * .73)
        elif side == 1:
            x, y, angle = 1021.0, 20.0 + 984.0 * q, np.pi + .19 * np.sin(i * .61)
        elif side == 2:
            x, y, angle = 20.0 + 984.0 * q, 2.0, np.pi / 2 + .18 * np.sin(i * .67)
        else:
            x, y, angle = 20.0 + 984.0 * q, 1021.0, -np.pi / 2 + .17 * np.sin(i * .59)
        tips.append([x, y, angle, 4 + (i * 5) % 6, 215 + (i * 37) % 190,
                     i, 0, 0])
    # Late internal ruptures are single directed scars, never multi-ray hubs.
    for i in range(41):
        x = 24.0 + 976.0 * ((i * .7548776662466927 + .11 * np.sin(i * .83)) % 1.0)
        y = 24.0 + 976.0 * ((i * .5698402909980532 + .09 * np.sin(i * 1.31)) % 1.0)
        angle = _director(x, y, 100 + i, i * 3) + .44 * np.sin(i * .91)
        tips.append([x, y, angle, 4 + (i * 3) % 5, 125 + (i * 29) % 125,
                     100 + i, 0, 22 + (i * 11) % 96])
    return tips


def _grow_marks():
    primary = np.zeros((WORK, WORK), np.uint8)
    secondary = np.zeros_like(primary)
    lips = np.zeros_like(primary)
    bridges = np.zeros_like(primary)
    pits = np.zeros_like(primary)
    wet = np.zeros_like(primary)
    fronts = np.zeros_like(primary)
    chips = np.zeros_like(primary)
    occupied = np.zeros_like(primary)
    tips = _seed_tips()
    spawned = 0
    collision_count = 0

    cursor = 0
    while cursor < len(tips):
        x, y, angle, width, life, lineage, generation, delay = tips[cursor]
        cursor += 1
        if delay:
            # Delayed origins are chronology only; they are not drawn as marks.
            pass
        last = np.asarray([x, y], np.float32)
        alive_steps = 0
        for step in range(int(life)):
            desired = _director(float(last[0]), float(last[1]), int(lineage), step)
            # Nematic blend keeps continuity while allowing smooth deterministic turns.
            delta = np.arctan2(np.sin(desired - angle), np.cos(desired - angle))
            angle += .073 * delta + .026 * np.sin(step * .311 + lineage * .173)
            stride = 2.45 + .32 * np.sin(step * .47 + lineage * .19)
            nxt = last + np.asarray([np.cos(angle), np.sin(angle)], np.float32) * stride
            if not (3 <= nxt[0] < WORK - 3 and 3 <= nxt[1] < WORK - 3):
                break
            ix, iy = int(round(float(nxt[0]))), int(round(float(nxt[1])))
            if alive_steps > 11 and occupied[max(0, iy - 3):iy + 4,
                                             max(0, ix - 3):ix + 4].max():
                cv2.circle(pits, (ix, iy), 3 + (lineage % 4), 255, -1, cv2.LINE_AA)
                collision_count += 1
                break
            target = primary if generation == 0 else secondary
            w = int(max(2, width - generation * 2))
            p0 = tuple(np.rint(last).astype(int))
            p1 = tuple(np.rint(nxt).astype(int))
            cv2.line(target, p0, p1, 255, w, cv2.LINE_AA)
            cv2.line(occupied, p0, p1, 255, max(2, w // 2), cv2.LINE_8)

            # One-sided lifted lip switches only at causal buckle events.
            lip_side = -1.0 if ((lineage * 13 + step // 29) % 3) else 1.0
            normal = np.asarray([-np.sin(angle), np.cos(angle)], np.float32)
            offset = normal * lip_side * (4.0 + width * .58)
            cv2.line(lips, tuple(np.rint(last + offset).astype(int)),
                     tuple(np.rint(nxt + offset).astype(int)), 255,
                     2 + (lineage + step // 17) % 3, cv2.LINE_AA)

            # Cross-crack healing has a distinct bar silhouette and never repeats by cadence.
            if (step * 17 + lineage * 23) % 137 < 3:
                span = 5.0 + ((lineage * 7 + step) % 10)
                cv2.line(bridges, tuple(np.rint(nxt - normal * span).astype(int)),
                         tuple(np.rint(nxt + normal * span).astype(int)), 255,
                         3 + (lineage % 4), cv2.LINE_AA)

            # A branch inherits its parent's exact collision point and tangent.
            if generation < 2 and spawned < 390 and alive_steps > 17:
                gate = (step * 19 + lineage * 31 + generation * 47) % 173
                if gate < (3 if generation == 0 else 1):
                    side = -1.0 if ((step + lineage) & 1) else 1.0
                    child_angle = angle + side * (.58 + .21 * np.sin(lineage * .37))
                    child_life = 34 + (lineage * 17 + step * 5) % 92
                    tips.append([float(nxt[0]), float(nxt[1]), child_angle,
                                 max(3, width - 2), child_life,
                                 int(lineage * 11 + step + 401), generation + 1, 0])
                    spawned += 1

            # Wet inclusions and their open retreat fronts descend from local arrest events.
            if (step * 11 + lineage * 29) % 211 < 2:
                rx = 5 + (lineage * 7 + step) % 11
                ry = 4 + (lineage * 3 + step * 2) % 8
                center = tuple(np.rint(nxt + normal * (8 + lineage % 9)).astype(int))
                cv2.ellipse(wet, center, (rx, ry), np.degrees(angle),
                            18 + (lineage % 5) * 19, 282 - (step % 4) * 17,
                            255, 3 + lineage % 3, cv2.LINE_AA)
                cv2.ellipse(fronts, center, (rx + 4, ry + 3), np.degrees(angle),
                            42 + (step % 3) * 21, 238 + (lineage % 3) * 19,
                            255, 2, cv2.LINE_AA)

            if (step * 13 + lineage * 7) % 257 < 2:
                tip = nxt + normal * (5 + generation * 3)
                tri = np.asarray([
                    tip,
                    tip + normal * (5 + lineage % 7) +
                    np.asarray([np.cos(angle), np.sin(angle)]) * 4,
                    tip + normal * (2 + lineage % 4) +
                    np.asarray([np.cos(angle), np.sin(angle)]) * 11,
                ], np.int32)
                cv2.fillConvexPoly(chips, tri, 255, cv2.LINE_AA)
            last = nxt
            alive_steps += 1

    return {
        "primary": primary.astype(np.float32) / 255.0,
        "secondary": secondary.astype(np.float32) / 255.0,
        "lips": lips.astype(np.float32) / 255.0,
        "bridges": bridges.astype(np.float32) / 255.0,
        "pits": pits.astype(np.float32) / 255.0,
        "wet": wet.astype(np.float32) / 255.0,
        "fronts": fronts.astype(np.float32) / 255.0,
        "chips": chips.astype(np.float32) / 255.0,
        "spawned": spawned,
        "collisions": collision_count,
    }


def _paint(angle_b: bool = False):
    marks = _grow_marks()
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    crack = np.maximum(marks["primary"], marks["secondary"])
    distance = cv2.distanceTransform((crack < .08).astype(np.uint8), cv2.DIST_L2, 5)
    # Drying age is a causal distance from ruptures, quantized into 15 color strata.
    age = np.clip(distance / 23.0, 0.0, 1.0)
    age += .11 * np.sin((xx + .37 * yy) / 37.0)
    age += .07 * np.sin((.61 * xx - yy) / 53.0)
    idx = np.clip(np.floor(np.mod(age, 1.0) * 15.0).astype(np.int32), 0, 14)
    palette = PALETTE_B if angle_b else PALETTE_A
    paint = palette[idx]
    # The two viewing lobes swap which attached anatomy owns the strongest travel.
    if angle_b:
        layers = (
            (marks["primary"], (0.08, 0.79, 0.74), .93),
            (marks["secondary"], (0.72, 0.20, 0.80), .87),
            (marks["lips"], (0.96, 0.33, 0.73), .94),
            (marks["bridges"], (0.78, 0.95, 0.41), .94),
            (marks["pits"], (0.02, 0.05, 0.08), .98),
            (marks["wet"], (0.17, 0.90, 0.69), .88),
            (marks["fronts"], (0.90, 0.77, 0.23), .91),
            (marks["chips"], (0.91, 0.24, 0.46), .91),
        )
    else:
        layers = (
            (marks["primary"], (0.13, 0.025, 0.018), .96),
            (marks["secondary"], (0.42, 0.09, 0.02), .89),
            (marks["lips"], (1.00, 0.72, 0.16), .96),
            (marks["bridges"], (1.00, 0.94, 0.58), .96),
            (marks["pits"], (0.02, 0.012, 0.018), .99),
            (marks["wet"], (0.95, 0.33, 0.10), .90),
            (marks["fronts"], (0.98, 0.84, 0.34), .93),
            (marks["chips"], (0.67, 0.16, 0.08), .93),
        )
    for mask, color, alpha in layers:
        a = np.clip(mask * alpha, 0.0, 1.0)[..., None]
        paint = paint * (1.0 - a) + np.asarray(color, np.float32) * a
    return np.clip(paint, 0.0, 1.0), marks


def _up(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/amber_agar_shrink_i1")
    out.mkdir(parents=True, exist_ok=True)
    timings = []
    repeats = []
    marks = None
    for _ in range(3):
        started = time.perf_counter()
        paint, marks = _paint(False)
        repeats.append(_u8(_up(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _paint(True)
    native_b = _u8(_up(angle_b))
    native_a = repeats[0]
    cv2.imwrite(str(out / f"{ID}_paint_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_a_2048.png"), cv2.cvtColor(native_a, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out / f"{ID}_angle_b_2048.png"), cv2.cvtColor(native_b, cv2.COLOR_RGB2BGR))
    crop = native_a[512:1024, 768:1280]
    cv2.imwrite(str(out / f"{ID}_crop_1to1.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    delta = np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)) / 255.0
    digest = hashlib.sha256(repeats[0].tobytes()).hexdigest()
    report = {
        "id": ID,
        "module": __name__,
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 68,
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": digest,
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {key: float(value.mean()) for key, value in marks.items()
                     if isinstance(value, np.ndarray)},
        "spawned_branches": int(marks["spawned"]),
        "junction_collisions": int(marks["collisions"]),
        "owner_accepted": False,
        "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
