# -*- coding: utf-8 -*-
"""Isolated native-2048 White Pollen obstacle-flow study.

SPB-105 / Wilds attempt 67 / 2026-08-25. Five deterministic boundary schools
move through an analytic potential-flow obstacle field. Every visible mark is
causal: flight dashes, obstacle impacts, rebound shells, adhesion films, wake
deposits, eddy chains and cracked grains. Obstacles are unequal 16-32 px native
microbodies and are not rendered as a repeated icon field. No RNG, noise/FBM,
particle dust, scalar texture, stamp bank, shared composer or recolor fallback.

Native-2048 verdict: REJECTED. The flight dashes collapse into regimented
particle rows around enormous empty voids; canvas-edge paths read as rails and
the impact/rebound anatomy repeats as decorative squiggle glyphs. Frozen before
spec/M7/runtime work. No density, obstacle, path, palette, impact, wake, crop,
scale, spec or noise repair is authorized.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fbl_white_pollen"
WORK = 1024
NATIVE = 2048
TAU = np.float32(2.0 * np.pi)

PALETTE_A = np.asarray([
    (244, 239, 213), (255, 225, 117), (246, 190, 49), (223, 143, 31),
    (186, 104, 28), (164, 218, 188), (102, 202, 185), (65, 163, 157),
    (248, 180, 146), (231, 113, 102), (206, 75, 98), (251, 248, 233),
], np.uint8)
PALETTE_B = np.asarray([
    (255, 73, 166), (224, 61, 205), (167, 72, 230), (93, 94, 236),
    (33, 148, 224), (17, 205, 184), (72, 230, 115), (178, 231, 55),
    (241, 209, 48), (255, 136, 53), (240, 70, 78), (238, 228, 255),
], np.uint8)


def _obstacles():
    rows = []
    phi = .6180339887498948
    psi = .4142135623730950
    for index in range(72):
        x = 28.0 + 968.0 * ((index * phi + .17 * np.sin(index * 1.137)) % 1.0)
        y = 28.0 + 968.0 * ((index * psi + .13 * np.sin(index * .731 + .4)) % 1.0)
        rx = 5.0 + ((index * 7 + index // 3) % 12) * .48
        ry = 5.0 + ((index * 11 + index // 5) % 11) * .53
        angle = (index * 137.507764 + 19.0 * np.sin(index * .37)) % 180.0
        rows.append((x, y, rx, ry, angle))
    return np.asarray(rows, np.float32)


def _initial_particles(count: int = 5200):
    index = np.arange(count, dtype=np.float32)
    school = (index.astype(np.int32) % 5)
    t = np.mod(index * np.float32(.61803398875) + school * np.float32(.113), 1.0)
    inset = 2.0 + np.mod(index * 7.0, 13.0)
    x = np.empty(count, np.float32)
    y = np.empty(count, np.float32)
    # Opposed and diagonal boundary histories ensure no single parallel stream
    # can become the visible carrier.
    x[school == 0], y[school == 0] = inset[school == 0], t[school == 0] * WORK
    x[school == 1], y[school == 1] = WORK - inset[school == 1], t[school == 1] * WORK
    x[school == 2], y[school == 2] = t[school == 2] * WORK, inset[school == 2]
    x[school == 3], y[school == 3] = t[school == 3] * WORK, WORK - inset[school == 3]
    x[school == 4], y[school == 4] = t[school == 4] * WORK, np.mod(t[school == 4] * 1.71, 1.0) * WORK
    return x, y, school


def _velocity(x, y, school, obstacles):
    base = np.asarray(((2.1, .35), (-1.95, -.42), (.38, 2.0), (-.44, -1.92), (1.35, -1.28)), np.float32)
    vx = base[school, 0].copy()
    vy = base[school, 1].copy()
    # Analytic doublet/vortex response. The small bodies bend local histories
    # without a raster noise field or sampled direction texture.
    for oi, (ox, oy, rx, ry, angle) in enumerate(obstacles):
        dx = x - ox
        dy = y - oy
        r2 = dx * dx + dy * dy + 18.0
        influence = np.minimum(1.0, (rx * ry * 5.0) / r2)
        spin = .36 * np.sin(oi * 1.171 + school * .83)
        vx += influence * (dx / np.sqrt(r2) - spin * dy / np.sqrt(r2))
        vy += influence * (dy / np.sqrt(r2) + spin * dx / np.sqrt(r2))
    speed = np.sqrt(vx * vx + vy * vy) + 1e-6
    return vx / speed, vy / speed


def _inside_nearest(x, y, obstacles):
    best = np.full(x.shape, np.inf, np.float32)
    owner = np.full(x.shape, -1, np.int32)
    for oi, (ox, oy, rx, ry, angle) in enumerate(obstacles):
        rad = np.deg2rad(angle)
        cs, sn = np.cos(rad), np.sin(rad)
        dx, dy = x - ox, y - oy
        u = (cs * dx + sn * dy) / rx
        v = (-sn * dx + cs * dy) / ry
        d = u * u + v * v
        better = d < best
        best[better] = d[better]
        owner[better] = oi
    return best <= 1.0, owner, best


def _paint(flipped: bool = False):
    palette = PALETTE_B if flipped else PALETTE_A
    image = np.zeros((WORK, WORK, 3), np.uint8)
    image[:] = (10, 19, 19) if not flipped else (15, 10, 29)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in
             ("flight", "impact", "rebound", "adhesion", "wake", "eddy", "crack", "obstacle", "school")}
    obstacles = _obstacles()
    x, y, school = _initial_particles()
    previous_x, previous_y = x.copy(), y.copy()
    impacted = np.zeros(x.shape, bool)
    impact_owner = np.full(x.shape, -1, np.int32)
    impact_count = flight_count = eddy_count = 0

    for step in range(64):
        vx, vy = _velocity(x, y, school, obstacles)
        step_len = 2.2 + .55 * np.sin(step * .47 + school * .91)
        previous_x[:], previous_y[:] = x, y
        x = np.mod(x + vx * step_len, WORK)
        y = np.mod(y + vy * step_len, WORK)
        hit, owner, _ = _inside_nearest(x, y, obstacles)
        newly = hit & ~impacted
        if np.any(newly):
            impact_owner[newly] = owner[newly]
            impacted[newly] = True
            # Deterministic reflection with an owner-specific turning angle.
            turn = .65 + .08 * (owner[newly] % 7)
            c, s = np.cos(turn), np.sin(turn)
            rvx = c * vx[newly] - s * vy[newly]
            rvy = s * vx[newly] + c * vy[newly]
            x[newly] = np.mod(previous_x[newly] + rvx * (3.0 + owner[newly] % 4), WORK)
            y[newly] = np.mod(previous_y[newly] + rvy * (3.0 + owner[newly] % 4), WORK)
        # Sparse flight deposition; marks are short local vectors, never full
        # particle trajectories or a spaghetti-line cloud.
        if step % 5 == 2:
            sample = np.arange(step % 7, x.size, 7)
            for pi in sample:
                p0 = (int(previous_x[pi]), int(previous_y[pi]))
                p1 = (int(x[pi]), int(y[pi]))
                color = tuple(int(v) for v in palette[(pi * 7 + step + school[pi] * 2) % len(palette)])
                thickness = 1 + ((pi + step) % 2)
                cv2.line(image, p0, p1, color, thickness, cv2.LINE_AA)
                cv2.line(masks["flight"], p0, p1, 255, thickness, cv2.LINE_AA)
                cv2.line(masks["school"], p0, p1, int(36 + school[pi] * 42), thickness, cv2.LINE_AA)
                flight_count += 1
        # Local eddy chains use three linked short tangents near a subset of
        # obstacles; they do not form free spirals or repeated ring stamps.
        if step in (19, 37, 55):
            for oi in range(step % 4, obstacles.shape[0], 9):
                ox, oy, rx, ry, angle = obstacles[oi]
                phase = np.deg2rad(angle + step * 11 + oi * 17)
                pts = []
                for k in range(5):
                    radius = max(rx, ry) + 3.0 + k * 1.6
                    a = phase + (k - 2) * .27
                    pts.append((int(ox + np.cos(a) * radius), int(oy + np.sin(a) * radius)))
                color = tuple(int(v) for v in palette[(oi * 5 + step) % len(palette)])
                cv2.polylines(image, [np.asarray(pts, np.int32)], False, color, 2, cv2.LINE_AA)
                cv2.polylines(masks["eddy"], [np.asarray(pts, np.int32)], False, 255, 2, cv2.LINE_AA)
                eddy_count += 1

    # Obstacle-contact anatomy is drawn from actual impacted ownership.
    for oi, (ox, oy, rx, ry, angle) in enumerate(obstacles):
        members = np.flatnonzero(impact_owner == oi)
        if members.size == 0:
            continue
        masks["obstacle"][max(0, int(oy - ry - 3)):min(WORK, int(oy + ry + 4)),
                          max(0, int(ox - rx - 3)):min(WORK, int(ox + rx + 4))] = 80
        color = tuple(int(v) for v in palette[(oi * 7 + members.size) % len(palette)])
        # Adhesion film: interrupted 80-210 degree arc, never a closed ellipse.
        start = float((oi * 53 + members.size * 7) % 180)
        span = float(80 + (oi * 17) % 130)
        axes = (int(rx + 2 + oi % 3), int(ry + 2 + (oi * 2) % 3))
        cv2.ellipse(image, (int(ox), int(oy)), axes, float(angle), start, start + span, color, 2, cv2.LINE_AA)
        cv2.ellipse(masks["adhesion"], (int(ox), int(oy)), axes, float(angle), start, start + span, 255, 2, cv2.LINE_AA)
        # Impact stars are unequal open forks located on the contacted rim.
        for local, pi in enumerate(members[:min(7, members.size)]):
            a = np.deg2rad(angle + (local * 47 + pi % 29))
            cx = int(ox + np.cos(a) * (rx + 1))
            cy = int(oy + np.sin(a) * (ry + 1))
            reach = 4 + ((pi + oi) % 7)
            tip = (int(cx + np.cos(a) * reach), int(cy + np.sin(a) * reach))
            wing1 = (int(cx + np.cos(a + .72) * (reach * .65)), int(cy + np.sin(a + .72) * (reach * .65)))
            wing2 = (int(cx + np.cos(a - .72) * (reach * .55)), int(cy + np.sin(a - .72) * (reach * .55)))
            cv2.line(image, (cx, cy), tip, color, 2, cv2.LINE_AA)
            cv2.line(image, (cx, cy), wing1, color, 1, cv2.LINE_AA)
            cv2.line(image, (cx, cy), wing2, color, 1, cv2.LINE_AA)
            cv2.line(masks["impact"], (cx, cy), tip, 255, 2, cv2.LINE_AA)
            cv2.line(masks["impact"], (cx, cy), wing1, 255, 1, cv2.LINE_AA)
            cv2.line(masks["impact"], (cx, cy), wing2, 255, 1, cv2.LINE_AA)
            impact_count += 1
            if (pi + oi) % 3 == 0:
                # Cracked grain: two unequal shell halves beyond the impact.
                cv2.ellipse(image, tip, (3 + pi % 3, 2 + oi % 2), float(angle), 20, 155, color, 1, cv2.LINE_AA)
                cv2.ellipse(image, tip, (3 + pi % 3, 2 + oi % 2), float(angle), 205, 335, color, 1, cv2.LINE_AA)
                cv2.ellipse(masks["crack"], tip, (3 + pi % 3, 2 + oi % 2), float(angle), 20, 155, 255, 1, cv2.LINE_AA)
                cv2.ellipse(masks["crack"], tip, (3 + pi % 3, 2 + oi % 2), float(angle), 205, 335, 255, 1, cv2.LINE_AA)
        # Wake deposit: short widening fan opposite the school-average velocity.
        wake_angle = np.deg2rad(angle + 150 + (oi * 31) % 60)
        for k in range(3 + oi % 4):
            dist = 5 + k * 4
            px = int(ox + np.cos(wake_angle + (k - 2) * .11) * dist)
            py = int(oy + np.sin(wake_angle + (k - 2) * .11) * dist)
            radius = 2 + (k % 3)
            cv2.ellipse(image, (px, py), (radius + 2, radius), float(np.rad2deg(wake_angle)), 10, 300,
                        tuple(int(v) for v in palette[(oi + k * 3) % len(palette)]), 1, cv2.LINE_AA)
            cv2.ellipse(masks["wake"], (px, py), (radius + 2, radius), float(np.rad2deg(wake_angle)), 10, 300, 255, 1, cv2.LINE_AA)

    coverage = {
        "flight_dashes": flight_count,
        "obstacle_impacts": impact_count,
        "eddy_chains": eddy_count,
        "impacted_obstacles": int(np.unique(impact_owner[impact_owner >= 0]).size),
        "flight_fraction": round(float(np.mean(masks["flight"] > 0)), 6),
        "adhesion_fraction": round(float(np.mean(masks["adhesion"] > 0)), 6),
        "wake_fraction": round(float(np.mean(masks["wake"] > 0)), 6),
    }
    return image, coverage, masks


def _write(path: Path, rgb: np.ndarray):
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(path)


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "white_pollen_flow_i1"
    output.mkdir(parents=True, exist_ok=True)
    timings = []
    first = None
    for _ in range(3):
        started = time.perf_counter()
        a, coverage, masks = _paint(False)
        b, _, _ = _paint(True)
        timings.append(time.perf_counter() - started)
        if first is None:
            first = (a.copy(), b.copy())
    a, b = first
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    _write(output / f"{ID}_paint_2048.png", native_a)
    _write(output / f"{ID}_angle_a_2048.png", native_a)
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_crop_1to1.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    digest = hashlib.sha256(native_a.tobytes() + native_b.tobytes()).hexdigest()
    manifest = {
        "id": ID,
        "module": "engine.expansions.fractured_wilds_white_pollen_flow_i1_2026",
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 67,
        "timings_s": timings,
        "deterministic_digest": digest,
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.percentile(delta, 95)),
        "coverage": coverage,
        "owner_accepted": False,
        "production_wired": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
