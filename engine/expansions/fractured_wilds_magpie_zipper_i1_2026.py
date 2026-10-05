# -*- coding: utf-8 -*-
"""Native-2048 Magpie Wing I1 paint carrier study.

One cropped asymmetric black/white vane interface. Two different feather-side
mechanics interlock through unequal tooth hooks, broken barb bridges, spectral
edge lips, shaft notches and down pockets. Paint/A-B only until native review.
No RNG/noise/rows/stamp atlas/shared composer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_magpie_wing"
WORK = 1024
NATIVE = 2048

BLACK_A = ((5, 13, 20), (7, 29, 41), (9, 61, 72), (15, 104, 105),
           (29, 154, 138), (49, 202, 170), (72, 222, 217),
           (76, 112, 214), (105, 74, 204), (163, 62, 196))
WHITE_A = ((73, 82, 91), (105, 119, 127), (139, 151, 154), (172, 183, 181),
           (202, 211, 202), (230, 234, 217), (251, 239, 196),
           (239, 202, 159), (193, 227, 232), (151, 201, 220))
BLACK_B = ((13, 6, 23), (35, 9, 54), (73, 16, 99), (123, 24, 131),
           (181, 38, 135), (226, 62, 114), (252, 106, 79),
           (241, 164, 55), (185, 210, 53), (88, 207, 114))
WHITE_B = ((52, 56, 77), (82, 88, 112), (119, 125, 145), (155, 160, 174),
           (190, 194, 199), (220, 220, 210), (244, 229, 186),
           (231, 193, 217), (189, 194, 242), (144, 166, 234))


def _mix(color: tuple[int, int, int], factor: float,
         lift: tuple[int, int, int] = (2, 3, 5)) -> tuple[int, int, int]:
    return tuple(int(np.clip(lift[i] + color[i] * factor, 0, 255)) for i in range(3))


def _seam_y(x: np.ndarray | float) -> np.ndarray | float:
    # One strongly asymmetric cropped interface; all waves are much larger
    # than a primitive but are constructed from fine attached vane anatomy.
    return (164.0 + 0.62 * x
            + 64.0 * np.sin(0.0058 * x + 0.25)
            + 25.0 * np.sin(0.0173 * x - 0.70)
            + 11.0 * np.sin(0.0430 * x + 1.10))


def _ground(angle_b: bool) -> tuple[np.ndarray, np.ndarray]:
    black = BLACK_B if angle_b else BLACK_A
    white = WHITE_B if angle_b else WHITE_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    seam = _seam_y(xx)
    signed = yy - seam
    # Each side gets a different optical chronology rather than one color field
    # recolored across the interface.
    phase_dark = np.mod(0.006 * xx + 0.010 * yy
                        + 1.2 * np.sin(0.013 * xx - 0.008 * yy)
                        + (4.0 if angle_b else 0.0), len(black))
    phase_light = np.mod(0.011 * xx - 0.004 * yy
                         + 0.9 * np.sin(0.009 * xx + 0.015 * yy)
                         + (5.0 if angle_b else 0.0), len(white))

    def interpolate(palette: tuple[tuple[int, int, int], ...], phase: np.ndarray) -> np.ndarray:
        pal = np.asarray(palette, np.float32)
        i0 = np.floor(phase).astype(np.int32)
        i1 = (i0 + 1) % len(pal)
        t = (phase - i0)[..., None]
        return pal[i0] * (1.0 - t) + pal[i1] * t

    dark_rgb = interpolate(black, phase_dark)
    light_rgb = interpolate(white, phase_light)
    # Fine offset fingers make the two vane populations interdigitate without
    # a periodic zipper cadence.
    interlock = signed + 9.0 * np.sin(0.081 * xx + 0.037 * yy)
    image = np.where((interlock > 0)[..., None], dark_rgb, light_rgb)
    shade = 0.72 + 0.20 * (0.5 + 0.5 * np.sin(0.027 * xx + 0.021 * yy))
    image = np.clip(image * shade[..., None] + np.asarray((3, 4, 6)), 0, 255).astype(np.uint8)
    return image, signed


def _packet(image: np.ndarray, masks: dict[str, np.ndarray], x: int, y: int,
            side_dark: bool, row: int, col: int, angle_b: bool) -> None:
    black = BLACK_B if angle_b else BLACK_A
    white = WHITE_B if angle_b else WHITE_A
    palette = black if side_dark else white
    # Packets on opposite sides use different flow laws and barb asymmetry.
    if side_dark:
        theta = -0.43 + 0.20 * np.sin(0.019 * x + 0.031 * y) + 0.07 * np.sin(0.33 * row)
        length = 6 + ((row * 7 + col * 11) % 8)
        barb_count = 2 + ((row + col) % 4)
        side_bias = -1
    else:
        theta = 0.31 + 0.16 * np.sin(0.025 * x - 0.018 * y) + 0.05 * np.cos(0.29 * col)
        length = 7 + ((row * 13 + col * 5) % 7)
        barb_count = 3 + ((2 * row + col) % 3)
        side_bias = 1
    dx, dy = np.cos(theta), np.sin(theta)
    nx, ny = -dy, dx
    p0 = np.asarray((x, y), np.float32)
    p1 = p0 + np.asarray((dx, dy)) * length
    idx = (row * 3 + col * 7 + (4 if angle_b else 0)) % len(palette)
    shaft_color = _mix(palette[idx], 0.72 if side_dark else 0.90)
    cv2.line(image, tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
             shaft_color, 1, cv2.LINE_AA)
    cv2.line(masks["shaft"], tuple(np.rint(p0).astype(int)), tuple(np.rint(p1).astype(int)),
             85 + 21 * ((row + col) % 8), 1, cv2.LINE_AA)
    # Unequal barbs share the shaft but alternate reach and attachment side.
    for b in range(barb_count):
        t = (b + 1) / (barb_count + 1)
        root = p0 * (1.0 - t) + p1 * t
        sign = side_bias if (b + row + col) % 3 else -side_bias
        reach = 2 + ((row * 5 + col * 3 + b * 7) % 5)
        tip = root + np.asarray((nx, ny)) * sign * reach + np.asarray((dx, dy)) * (1 + b % 2)
        color = _mix(palette[(idx + 2 + b) % len(palette)], 1.02 if not side_dark else 0.88)
        cv2.line(image, tuple(np.rint(root).astype(int)), tuple(np.rint(tip).astype(int)),
                 color, 1, cv2.LINE_AA)
        cv2.line(masks["barb"], tuple(np.rint(root).astype(int)), tuple(np.rint(tip).astype(int)),
                 90 + 20 * ((row + col + b) % 8), 1, cv2.LINE_AA)
    # Selected packets terminate in a real notch or split hook—not detached marks.
    if (row * 17 + col * 29) % 61 == 7:
        q = p1 - np.asarray((dx, dy)) * 2
        for sign in (-1, 1):
            tip = q + np.asarray((nx, ny)) * sign * (2 + (row + col) % 3)
            cv2.line(image, tuple(np.rint(q).astype(int)), tuple(np.rint(tip).astype(int)),
                     _mix(palette[(idx + 5 + sign) % len(palette)], 1.08), 1, cv2.LINE_AA)
            cv2.line(masks["notch"], tuple(np.rint(q).astype(int)), tuple(np.rint(tip).astype(int)),
                     110 + 18 * ((row + col) % 8), 1, cv2.LINE_AA)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    image, signed = _ground(angle_b)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "shaft", "barb", "seam", "hook", "bridge", "lip", "notch", "down",
    )}
    packet_count = 0
    # Dense fine vane packets are staggered without a visible row baseline.
    for row, y in enumerate(range(-10, WORK + 12, 9)):
        for col, x in enumerate(range(-12 + (row * 7) % 13, WORK + 14, 11)):
            yy = y + int(3 * np.sin(0.37 * row + 0.71 * col))
            xx = x + int(2 * np.sin(0.53 * row - 0.29 * col))
            if 0 <= xx < WORK and 0 <= yy < WORK:
                _packet(image, masks, xx, yy, bool(signed[yy, xx] > 0), row, col, angle_b)
                packet_count += 1

    # The actual edge zipper is a chain of unequal micro-teeth following the
    # one seam. No tooth is larger than 30 px native and cadence never repeats.
    palette_dark = BLACK_B if angle_b else BLACK_A
    palette_light = WHITE_B if angle_b else WHITE_A
    seam_pts = []
    for x in range(-10, WORK + 12, 4):
        y = int(round(float(_seam_y(float(x)))))
        seam_pts.append((x, y))
    seam_arr = np.asarray(seam_pts, np.int32)
    cv2.polylines(image, [seam_arr], False, (2, 3, 5), 3, cv2.LINE_AA)
    cv2.polylines(masks["seam"], [seam_arr], False, 255, 3, cv2.LINE_AA)
    hook_count = bridge_count = down_count = 0
    for i in range(4, len(seam_pts) - 4, 3 + (len(seam_pts) % 2)):
        x, y = seam_pts[i]
        phase = (i * 17 + i * i * 3) % 43
        reach = 3 + phase % 8
        sign = -1 if (i * 5) % 7 < 3 else 1
        hook = np.asarray([(x - 3, y), (x + 1, y + sign * reach),
                           (x + 5, y + sign * (reach - 2)), (x + 7, y + sign * 2)], np.int32)
        colors = palette_light if sign > 0 else palette_dark
        cv2.polylines(image, [hook], False,
                      _mix(colors[(i + (5 if angle_b else 0)) % len(colors)], 1.08), 2, cv2.LINE_AA)
        cv2.polylines(masks["hook"], [hook], False,
                      95 + 20 * (i % 8), 2, cv2.LINE_AA)
        hook_count += 1
        if i % 5 == 2:
            bridge = np.asarray([(x - 4, y - 3), (x + 5, y + 4),
                                 (x + 7, y + 2), (x - 2, y - 5)], np.int32)
            cv2.fillConvexPoly(image, bridge,
                               _mix((WHITE_B if angle_b else WHITE_A)[(i + 6) % 10], 1.05), cv2.LINE_AA)
            cv2.fillConvexPoly(masks["bridge"], bridge, 120 + 17 * (i % 8), cv2.LINE_AA)
            bridge_count += 1

    # Broken spectral lip segments alternate side and length; together they
    # expose a discontinuous optical edge, not a second continuous outline.
    for j in range(74):
        x = -6 + j * 15
        if x > WORK + 8:
            break
        y = int(round(float(_seam_y(float(x)))))
        span = 4 + (j * 7) % 9
        sign = -1 if j % 3 == 0 else 1
        palette = palette_light if sign > 0 else palette_dark
        cv2.line(image, (x, y + sign * 3), (x + span, y + sign * 4),
                 _mix(palette[(j * 3 + (5 if angle_b else 0)) % len(palette)], 1.14), 2, cv2.LINE_AA)
        cv2.line(masks["lip"], (x, y + sign * 3), (x + span, y + sign * 4),
                 100 + 19 * (j % 8), 2, cv2.LINE_AA)

    # Down pockets are attached immediately behind selected white-side seam
    # teeth and contain short soft filaments rather than round black holes.
    for j in range(23):
        x = 18 + ((j * 149 + j * j * 11) % 990)
        y = int(round(float(_seam_y(float(x))))) - (7 + (j * 5) % 13)
        for f in range(3 + j % 4):
            p0 = (x - 3 + f * 2, y)
            p1 = (x - 5 + f * 3, y - 4 - (j + f) % 7)
            cv2.line(image, p0, p1, (28, 31, 37), 2, cv2.LINE_AA)
            cv2.line(masks["down"], p0, p1, 105 + 18 * ((j + f) % 8), 2, cv2.LINE_AA)
        down_count += 1

    coverage = {
        "vane_packets": float(packet_count),
        "shaft_coverage": round(float(np.mean(masks["shaft"] > 0)), 6),
        "barb_coverage": round(float(np.mean(masks["barb"] > 0)), 6),
        "edge_hooks": float(hook_count),
        "broken_bridges": float(bridge_count),
        "spectral_lip_coverage": round(float(np.mean(masks["lip"] > 0)), 6),
        "notch_coverage": round(float(np.mean(masks["notch"] > 0)), 6),
        "down_pockets": float(down_count),
    }
    return image, coverage, masks


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "magpie_zipper_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage, _ = _paint(False)
    b, _, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint_path = output / f"{ID}_paint_2048.png"
    _write(paint_path, native_a)
    shutil.copyfile(paint_path, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-magpie-zipper-i1/1",
        "status": "REJECT-MACRO-TWO-TERRITORY-SEAM-OVER-SHORT-STROKE-SWARM-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "asymmetric interlocking black-white vane interface",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit vane/seam raster; no RNG/noise/rows/stamps/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
