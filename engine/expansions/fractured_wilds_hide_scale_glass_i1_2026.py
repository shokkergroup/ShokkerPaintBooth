# -*- coding: utf-8 -*-
"""Native-2048 Hide Scale Glass I1 paint-only lenticular shoal study.

SPB-105 / 2026-08-25 native rebuild tick. Owner doctrine: actual 2048 canvas
controls; primitives stay 8-32 px native; noise never creates uniqueness.
This source draws a deterministic low-discrepancy caustic shoal of overlapping
unequal asymmetric lenses. Each body owns a bevel, focal line, occlusion edge,
stress vein and scuff arc. Paint/A-B only until native review.

No RNG, sampled noise, grain, rows, stamp atlas or shared composer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fc_hide_scale_glass"
WORK = 1024
NATIVE = 2048
COUNT = 6600

GLASS_A = np.asarray([
    (7, 5, 14), (22, 8, 39), (52, 12, 73), (91, 16, 101),
    (137, 22, 122), (184, 34, 137), (225, 54, 147), (249, 83, 151),
    (255, 123, 157), (255, 171, 169), (252, 214, 192), (205, 235, 210),
    (130, 225, 215), (69, 185, 215), (66, 110, 194),
], np.float32)
GLASS_B = np.asarray([
    (3, 9, 17), (3, 26, 43), (3, 52, 69), (4, 84, 90),
    (6, 120, 107), (13, 157, 121), (31, 193, 137), (62, 222, 154),
    (110, 239, 176), (170, 245, 203), (225, 239, 228), (218, 197, 237),
    (174, 146, 230), (122, 96, 208), (68, 58, 164),
], np.float32)


def _color(value: float, stops: np.ndarray, factor: float = 1.0) -> tuple[int, int, int]:
    scaled = (value % 1.0) * len(stops)
    lo = int(np.floor(scaled))
    mix = scaled - lo
    rgb = stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix
    return tuple(int(np.clip(channel * factor, 0, 255)) for channel in rgb)


def _lens_points(cx: float, cy: float, length: float, half: float,
                 angle: float, skew: float) -> np.ndarray:
    tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
    normal = np.asarray((-tangent[1], tangent[0]), np.float32)
    pts = []
    # Two unequal cubic-like arcs form one biconvex body without an ellipse
    # stamp. Six samples per side preserve asymmetric shoulders at fine scale.
    for side in (1.0, -1.0):
        seq = range(6) if side > 0 else range(5, -1, -1)
        for j in seq:
            t = j / 5.0
            along = (t - 0.5) * length
            bulge = np.sin(np.pi * t) * half * (1.0 + side * skew * (t - 0.5))
            p = np.asarray((cx, cy), np.float32) + tangent * along + normal * side * bulge
            pts.append(p)
    return np.rint(np.asarray(pts)).astype(np.int32)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    stops = GLASS_B if angle_b else GLASS_A
    image = np.zeros((WORK, WORK, 3), np.uint8)
    image[:] = (4, 5, 11) if not angle_b else (3, 8, 13)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "body", "bevel", "focus", "occlusion", "stress", "scuff",
    )}
    phi = (np.sqrt(5.0) - 1.0) * 0.5
    root2 = np.sqrt(2.0) - 1.0
    for n in range(COUNT):
        # R2 low-discrepancy coverage: deterministic, nonrandom and row-free.
        cx = ((0.5 + (n + 1) * phi) % 1.0) * WORK
        cy = ((0.5 + (n + 1) * root2) % 1.0) * WORK
        # Continuous caustic currents organize local shoals; ten vortical terms
        # bend orientation but do not place lens centres or create color noise.
        angle = (
            0.31 * np.sin(cx / 83.0 + cy / 137.0)
            + 0.47 * np.sin((cx - 1.4 * cy) / 119.0)
            + 0.29 * np.cos((1.7 * cx + cy) / 151.0)
        )
        for vx, vy, charge in ((168, 189, 1), (486, 142, -1), (812, 233, 1),
                               (267, 523, -1), (623, 477, 1), (902, 598, -1),
                               (139, 801, 1), (489, 849, -1), (791, 829, 1)):
            dx, dy = cx - vx, cy - vy
            angle += charge * 0.11 * np.sin(2.0 * np.arctan2(dy, dx)) * np.exp(
                -(dx * dx + dy * dy) / (2.0 * 151.0 ** 2))
        length = 6.0 + ((n * 17 + n * n * 3) % 10)
        half = 2.3 + ((n * 11 + n * n) % 6) * 0.55
        skew = -0.52 + ((n * 37) % 101) / 100.0
        body = _lens_points(cx, cy, length, half, angle, skew)
        optical = (
            0.0013 * cx + 0.0019 * cy + 0.071 * (n % 13)
            + 0.09 * np.sin(angle * 3.0)
        )
        if angle_b:
            optical += 0.38 + 0.08 * np.sin(angle * 5.0)
        face = _color(optical, stops, 0.44 + 0.39 * (0.5 + 0.5 * np.sin(n * 0.381)))
        cv2.fillPoly(image, [body], face, cv2.LINE_AA)
        cv2.fillPoly(masks["body"], [body], 92 + 20 * (n % 8), cv2.LINE_AA)

        bevel = _color(optical + 0.17, stops, 0.93)
        cv2.polylines(image, [body], True, bevel, 1, cv2.LINE_AA)
        cv2.polylines(masks["bevel"], [body], True, 108 + 18 * (n % 8), 1, cv2.LINE_AA)
        tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        centre = np.asarray((cx, cy), np.float32)
        # Focal caustic is offset by lens asymmetry, never dead-centred.
        fa = centre - tangent * length * 0.31 + normal * skew * half * 0.45
        fb = centre + tangent * length * 0.34 + normal * skew * half * 0.65
        cv2.line(image, tuple(np.rint(fa).astype(int)), tuple(np.rint(fb).astype(int)),
                 _color(optical + 0.31, stops, 1.20), 1, cv2.LINE_AA)
        cv2.line(masks["focus"], tuple(np.rint(fa).astype(int)), tuple(np.rint(fb).astype(int)),
                 115 + 18 * (n % 8), 1, cv2.LINE_AA)
        # The downstream shoulder owns occlusion; it is not a generic outline.
        oa = centre - tangent * length * 0.27 - normal * half * 0.72
        ob = centre + tangent * length * 0.24 - normal * half * 0.79
        cv2.line(image, tuple(np.rint(oa).astype(int)), tuple(np.rint(ob).astype(int)),
                 (3, 4, 8), 1, cv2.LINE_AA)
        cv2.line(masks["occlusion"], tuple(np.rint(oa).astype(int)), tuple(np.rint(ob).astype(int)),
                 110 + 19 * (n % 8), 1, cv2.LINE_AA)

        if n % 3 == 0:
            # Stress vein is a short attached fork whose handedness follows the
            # same asymmetry that bends the body.
            root = centre + tangent * length * (0.05 + 0.12 * skew)
            tip1 = root + normal * half * 0.88 + tangent * length * 0.13
            tip2 = root - normal * half * 0.61 + tangent * length * 0.19
            vein = np.rint(np.asarray([tip1, root, tip2])).astype(np.int32)
            cv2.polylines(image, [vein], False, _color(optical + 0.52, stops, 0.95), 1, cv2.LINE_AA)
            cv2.polylines(masks["stress"], [vein], False, 105 + 19 * (n % 8), 1, cv2.LINE_AA)
        if n % 5 == 1:
            # Scuff arc clips only the upper shoulder; no free flecks.
            sc = centre + normal * half * 0.54
            sa = sc - tangent * length * 0.22
            sb = sc + tangent * length * 0.17 + normal * half * 0.12
            cv2.line(image, tuple(np.rint(sa).astype(int)), tuple(np.rint(sb).astype(int)),
                     _color(optical + 0.73, stops, 0.76), 1, cv2.LINE_AA)
            cv2.line(masks["scuff"], tuple(np.rint(sa).astype(int)), tuple(np.rint(sb).astype(int)),
                     112 + 18 * (n % 8), 1, cv2.LINE_AA)
    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    coverage["lens_count"] = float(COUNT)
    return image, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "hide_scale_glass_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage = _paint(False)
    b, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint = output / f"{ID}_paint_2048.png"
    _write(paint, native_a)
    shutil.copyfile(paint, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-hide-scale-glass-i1/1",
        "status": "REJECT-VERTICAL-BEAD-CURTAINS-OF-REPEATED-LENS-GLYPHS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "overlapping low-discrepancy asymmetric lenticular caustic shoal",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "R2 low-discrepancy vector assembly; no RNG/noise/grain/rows/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
