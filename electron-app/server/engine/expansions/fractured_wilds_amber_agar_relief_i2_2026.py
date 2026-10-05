# -*- coding: utf-8 -*-
"""Isolated native-2048 Amber Agar desiccation-relief study.

SPB-105 / Wilds attempt 75 / 2026-08-25. The rejected sparse rail/loop source
and scalar-lobe capsule I1 are discarded. I2 constructs one continuous
desiccation heightfield: primary ruptures spawn secondary crazing; one-sided
lifted lips, healed bridges, junction pits, moist interiors and receding gel
fronts all inherit the same crack geometry and surface normals.

Widths and local relief events remain 4--16 work pixels (8--32 px native). No
RNG, sampled noise, FBM, cell paver, repeated glyph, shared composer or recolor
fallback.

Native-2048 verdict: REJECTED. The relief is continuous but the sheet is huge
flat orange plates crossed by oversized black tube/rail cracks; healed bridges
repeat as white ticks. Frozen before spec/M7/runtime. No crack, width, density,
plate, bridge, palette, normal, scale, spec or noise repair is authorized.
"""
from __future__ import annotations

from functools import lru_cache
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
    (18, 5, 4), (37, 9, 4), (61, 14, 4), (88, 21, 4),
    (117, 30, 5), (147, 42, 7), (176, 57, 10), (201, 75, 15),
    (222, 97, 23), (238, 123, 36), (248, 152, 55), (253, 183, 82),
    (255, 211, 121), (251, 232, 168), (229, 244, 214),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (4, 15, 23), (4, 29, 41), (4, 47, 59), (4, 68, 75),
    (6, 92, 88), (11, 118, 98), (20, 145, 104), (35, 172, 107),
    (56, 197, 109), (84, 218, 113), (119, 234, 124), (159, 242, 143),
    (202, 243, 169), (237, 230, 199), (248, 197, 218),
], np.float32) / 255.0


def _director(x, y, lineage, step):
    xn, yn = x / WORK, y / WORK
    gx = (1.13 * np.cos(TAU * (1.17 * xn + .43 * yn) + lineage * .091)
          + .71 * np.cos(TAU * (.37 * xn - 1.51 * yn) + step * .019)
          + .39 * np.sin(TAU * (2.03 * xn + .89 * yn)))
    gy = (1.07 * np.sin(TAU * (.53 * xn + 1.39 * yn) - lineage * .073)
          - .64 * np.sin(TAU * (1.73 * xn - .61 * yn) + step * .014)
          + .43 * np.cos(TAU * (1.07 * xn + 1.91 * yn)))
    return float(np.arctan2(gy, gx))


@lru_cache(maxsize=1)
def _geometry():
    primary = np.zeros((WORK, WORK), np.uint8)
    secondary = np.zeros_like(primary)
    lips = np.zeros_like(primary)
    bridges = np.zeros_like(primary)
    pit_seeds = np.zeros_like(primary)
    tips = []
    for i in range(46):
        side = (i * 7 + i // 4) % 4
        q = ((i * .6180339887498948 + .11 * np.sin(i * .77)) % 1.0)
        if side == 0:
            x, y, angle = 1.0, 12 + 1000 * q, 0.0
        elif side == 1:
            x, y, angle = 1022.0, 12 + 1000 * q, np.pi
        elif side == 2:
            x, y, angle = 12 + 1000 * q, 1.0, np.pi / 2
        else:
            x, y, angle = 12 + 1000 * q, 1022.0, -np.pi / 2
        tips.append((x, y, angle, 4 + (i * 5) % 5,
                     115 + (i * 37) % 190, i, 0))
    for i in range(23):
        x = 18 + 988 * ((i * .7548776662466927 + .09 * np.sin(i)) % 1.0)
        y = 18 + 988 * ((i * .5698402909980532 + .07 * np.sin(i * 1.3)) % 1.0)
        angle = _director(x, y, 100 + i, 0)
        tips.append((x, y, angle, 4 + i % 4, 73 + (i * 29) % 97,
                     100 + i, 1))

    branch_count = 0
    for x, y, angle, width, life, lineage, generation in tips:
        last = np.asarray([x, y], np.float32)
        for step in range(int(life)):
            desired = _director(float(last[0]), float(last[1]), lineage, step)
            delta = np.arctan2(np.sin(desired - angle), np.cos(desired - angle))
            angle += .061 * delta + .019 * np.sin(step * .37 + lineage * .23)
            stride = 2.2 + .27 * np.sin(step * .43 + lineage * .17)
            nxt = last + np.asarray([np.cos(angle), np.sin(angle)], np.float32) * stride
            if not (2 <= nxt[0] < WORK - 2 and 2 <= nxt[1] < WORK - 2):
                break
            target = primary if generation == 0 else secondary
            p0, p1 = tuple(np.rint(last).astype(int)), tuple(np.rint(nxt).astype(int))
            cv2.line(target, p0, p1, 255, int(width), cv2.LINE_AA)
            normal = np.asarray([-np.sin(angle), np.cos(angle)], np.float32)
            side_sign = -1 if ((lineage * 17 + step // 31) % 3) else 1
            offset = normal * side_sign * (4 + width * .52)
            cv2.line(lips, tuple(np.rint(last + offset).astype(int)),
                     tuple(np.rint(nxt + offset).astype(int)), 255,
                     3 + (lineage + step // 23) % 4, cv2.LINE_AA)
            if (lineage * 31 + step * 19) % 173 < 2:
                span = 5 + (lineage * 7 + step) % 11
                cv2.line(bridges, tuple(np.rint(nxt - normal * span).astype(int)),
                         tuple(np.rint(nxt + normal * span).astype(int)), 255,
                         4 + lineage % 4, cv2.LINE_AA)
                cv2.circle(target, p1, 4 + lineage % 4, 0, -1, cv2.LINE_AA)
            if (lineage * 13 + step * 7) % 211 < 2:
                cv2.circle(pit_seeds, p1, 3 + lineage % 5, 255, -1, cv2.LINE_AA)
            last = nxt

        # Secondary cracks inherit varied points from the root chronology but
        # are generated as separate curved fractures, never repeated glyphs.
        if generation == 0:
            for child in range(2 + lineage % 3):
                t = .23 + .19 * child + .07 * np.sin(lineage * .41 + child)
                sx = x + np.cos(angle) * life * 2.2 * t
                sy = y + np.sin(angle) * life * 2.2 * t
                if 8 < sx < WORK - 8 and 8 < sy < WORK - 8:
                    cangle = (angle + (-1 if child & 1 else 1) *
                              (0.59 + .17 * np.sin(lineage + child)))
                    points = []
                    pos = np.asarray([sx, sy], np.float32)
                    for cstep in range(27 + (lineage * 11 + child * 17) % 47):
                        cangle += .028 * np.sin(cstep * .53 + lineage)
                        pos = pos + np.asarray([np.cos(cangle), np.sin(cangle)]) * 2.1
                        if not (3 < pos[0] < WORK - 3 and 3 < pos[1] < WORK - 3):
                            break
                        points.append(pos.copy())
                    if len(points) > 1:
                        cv2.polylines(secondary, [np.rint(points).astype(np.int32)],
                                      False, 255, 3 + child % 4, cv2.LINE_AA)
                        branch_count += 1

    crack = np.maximum(primary, secondary)
    # Junctions are physical high-degree overlaps, not placed dots.
    binary = (crack > 20).astype(np.uint8)
    neighborhood = cv2.filter2D(binary, cv2.CV_16U, np.ones((9, 9), np.uint8))
    junctions = ((neighborhood > 42) & (binary > 0)).astype(np.uint8) * 255
    junctions = cv2.dilate(junctions, np.ones((5, 5), np.uint8))
    pits = np.maximum(pit_seeds, junctions)
    return primary, secondary, lips, bridges, pits, branch_count


def _fields():
    primary, secondary, lips, bridges, pits, branch_count = _geometry()
    crack = np.maximum(primary, secondary).astype(np.float32) / 255.0
    free = (crack < .12).astype(np.uint8)
    distance = cv2.distanceTransform(free, cv2.DIST_L2, 5).astype(np.float32)
    plate = np.clip(distance / 21.0, 0, 1)
    receding = np.clip(1.0 - np.abs(distance - 12.0) / 3.5, 0, 1)
    moist_gate = (.5 + .5 * np.sin(np.indices(distance.shape)[1] / 43.0
                                   + np.indices(distance.shape)[0] / 59.0))
    moist = (np.clip((distance - 17.0) / 11.0, 0, 1) *
             np.clip((moist_gate - .35) / .55, 0, 1))
    lip = lips.astype(np.float32) / 255.0
    bridge = bridges.astype(np.float32) / 255.0
    pit = pits.astype(np.float32) / 255.0
    height = .18 + .68 * plate + .31 * lip + .19 * bridge - .52 * crack - .44 * pit
    height = cv2.GaussianBlur(height.astype(np.float32), (0, 0), 1.35)
    gy, gx = np.gradient(height)
    return {
        "height": height,
        "plate": plate,
        "primary_cracks": primary.astype(np.float32) / 255.0,
        "secondary_crazing": secondary.astype(np.float32) / 255.0,
        "lifted_lips": lip,
        "healed_bridges": bridge,
        "junction_pits": pit,
        "moist_interiors": moist.astype(np.float32),
        "receding_fronts": receding.astype(np.float32),
        "gx": gx.astype(np.float32),
        "gy": gy.astype(np.float32),
        "branch_count": branch_count,
    }


def _palette_ramp(t, palette):
    q = np.clip(t, 0, 1) * (len(palette) - 1)
    lo = np.floor(q).astype(np.int32)
    hi = np.minimum(lo + 1, len(palette) - 1)
    f = (q - lo)[..., None]
    return palette[lo] * (1 - f) + palette[hi] * f


def _paint(angle_b=False):
    f = _fields()
    palette = PALETTE_B if angle_b else PALETTE_A
    age = np.clip(.62 * f["plate"] + .23 * f["moist_interiors"]
                  + .15 * f["receding_fronts"], 0, 1)
    paint = _palette_ramp(age, palette)
    light = np.asarray((-.58, .42, .69) if angle_b else (.46, -.51, .73), np.float32)
    nx, ny = -f["gx"] * 2.8, -f["gy"] * 2.8
    nz = np.ones_like(nx)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    shade = np.clip((nx * light[0] + ny * light[1] + nz * light[2]) / norm,
                    -.35, 1.0)
    paint *= (.46 + .61 * shade[..., None])
    if angle_b:
        layers = (
            (f["primary_cracks"], (.015, .04, .07), .97),
            (f["secondary_crazing"], (.30, .08, .50), .87),
            (f["lifted_lips"], (.20, .96, .77), .90),
            (f["healed_bridges"], (.95, .82, .33), .95),
            (f["junction_pits"], (.005, .015, .025), .99),
            (f["moist_interiors"], (.89, .25, .70), .47),
            (f["receding_fronts"], (.73, .96, .55), .62),
        )
    else:
        layers = (
            (f["primary_cracks"], (.08, .012, .004), .97),
            (f["secondary_crazing"], (.35, .045, .008), .87),
            (f["lifted_lips"], (1.0, .72, .23), .90),
            (f["healed_bridges"], (1.0, .94, .61), .95),
            (f["junction_pits"], (.015, .004, .002), .99),
            (f["moist_interiors"], (.92, .22, .08), .47),
            (f["receding_fronts"], (.99, .66, .21), .62),
        )
    for mask, color, alpha in layers:
        a = np.clip(mask * alpha, 0, 1)[..., None]
        paint = paint * (1 - a) + np.asarray(color, np.float32) * a
    return np.clip(paint, 0, 1), f


def _native(rgb):
    return cv2.resize(rgb, (NATIVE, NATIVE), interpolation=cv2.INTER_LINEAR)


def _u8(rgb):
    return np.clip(rgb * 255.0 + .5, 0, 255).astype(np.uint8)


def main():
    out = Path("_wilds_fullres_progress_20260824/amber_agar_relief_i2")
    out.mkdir(parents=True, exist_ok=True)
    timings, repeats = [], []
    fields = None
    for _ in range(3):
        started = time.perf_counter()
        paint, fields = _paint(False)
        repeats.append(_u8(_native(paint)))
        timings.append(time.perf_counter() - started)
    angle_b, _ = _paint(True)
    native_a, native_b = repeats[0], _u8(_native(angle_b))
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
        "attempt": 75,
        "math": "deterministic branching fracture heightfield with surface-normal shading",
        "timings_s": timings,
        "deterministic": bool(all(np.array_equal(repeats[0], item) for item in repeats[1:])),
        "deterministic_digest": hashlib.sha256(native_a.tobytes()).hexdigest(),
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, .95)),
        "coverage": {name: float(value.mean()) for name, value in fields.items()
                     if isinstance(value, np.ndarray) and name not in ("height", "gx", "gy")},
        "branch_count": int(fields["branch_count"]),
        "owner_accepted": False,
        "production_wired": False,
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
