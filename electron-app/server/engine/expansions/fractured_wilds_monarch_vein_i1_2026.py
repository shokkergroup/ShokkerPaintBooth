# -*- coding: utf-8 -*-
"""Isolated native-2048 Monarch Vein anatomical raster study.

SPB-WILDS-MONARCH-I1 / SPB-105, 2026-08-24. Explicit wing anatomy replaces
full-frame scalar texture: individually varied overlapping scales, black vein
sleeves, unequal closed cross-veins, white marginal insets, node collars,
missing-scale faults, hooklets and fringe. Local marks are 8-32 px at native.

Paint/A-B review only. No RNG, sampled noise, procedural cells, shared Wilds
composer or material maps. Fail closed until native 2048 owner-eye review.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_monarch_vein"
WORK = 1024
NATIVE = 2048

COLORS_A = np.asarray([
    (220, 58, 18), (244, 91, 19), (255, 126, 22), (232, 142, 35),
    (195, 48, 35), (150, 35, 52), (250, 181, 52), (184, 80, 25),
], np.uint8)
COLORS_B = np.asarray([
    (18, 188, 215), (31, 222, 184), (55, 145, 238), (93, 87, 231),
    (177, 52, 221), (230, 48, 165), (54, 232, 116), (28, 110, 180),
], np.uint8)


def _curve(points: list[tuple[float, float]], samples: int = 180) -> np.ndarray:
    """Sample a cubic Bezier as int32 x/y points."""
    p = np.asarray(points, np.float32)
    t = np.linspace(0.0, 1.0, samples, dtype=np.float32)[:, None]
    q = ((1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1]
         + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3])
    return np.rint(q).astype(np.int32)


def _mix(rgb: np.ndarray, factor: float) -> tuple[int, int, int]:
    return tuple(int(np.clip(round(float(c) * factor), 0, 255)) for c in rgb)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    palette = COLORS_B if angle_b else COLORS_A
    image = np.zeros((WORK, WORK, 3), np.uint8)
    image[:] = (8, 7, 12) if not angle_b else (10, 7, 17)
    scale_mask = np.zeros((WORK, WORK), np.uint8)
    fault_mask = np.zeros((WORK, WORK), np.uint8)

    # Thousands of individually varied overlapping scales create the substrate.
    # Their phase is analytic but each polygon's width, height, tilt and colour
    # vary; missing slots are causal faults rather than random speckles.
    scale_count = 0
    missing_count = 0
    row_step = 10
    col_step = 12
    for row, cy in enumerate(range(-8, WORK + 15, row_step)):
        offset = 6 if row % 2 else 0
        for col, cx in enumerate(range(-12 + offset, WORK + 18, col_step)):
            phase = np.sin(0.71 * row + 1.13 * col) + np.cos(0.43 * row - 0.89 * col)
            w = 5 + int(abs(np.sin(0.37 * row + 0.83 * col)) * 5)
            h = 7 + int(abs(np.cos(0.51 * row - 0.62 * col)) * 6)
            lean = int(np.rint(3.0 * np.sin(0.19 * row + 0.47 * col)))
            missing = (np.sin(0.23 * row + 0.61 * col) > 0.91
                       and np.cos(0.67 * row - 0.29 * col) > 0.35)
            poly = np.asarray([
                (cx - w, cy - h // 2), (cx + lean, cy - h),
                (cx + w, cy - h // 3), (cx + w - 1, cy + h // 2),
                (cx, cy + h), (cx - w + 1, cy + h // 2),
            ], np.int32)
            if missing:
                cv2.fillConvexPoly(image, poly, (12, 9, 17), lineType=cv2.LINE_AA)
                cv2.polylines(fault_mask, [poly], True, 230, 2, cv2.LINE_AA)
                missing_count += 1
                continue
            idx = int(abs(phase) * 3.7 + row + 2 * col) % len(palette)
            factor = 0.62 + 0.35 * (0.5 + 0.5 * np.sin(0.31 * row - 0.41 * col))
            color = _mix(palette[idx], factor)
            cv2.fillConvexPoly(image, poly, color, lineType=cv2.LINE_AA)
            cv2.polylines(image, [poly], True, _mix(palette[(idx + 5) % len(palette)], 0.33), 1, cv2.LINE_AA)
            # Alternating tip glints keep scales from becoming flat tesserae.
            if (row + 2 * col) % 5 in (0, 1):
                cv2.line(image, (cx - w + 2, cy + h // 2), (cx, cy + h - 1),
                         _mix(palette[(idx + 2) % len(palette)], 1.08), 2, cv2.LINE_AA)
            cv2.fillConvexPoly(scale_mask, poly, 255, lineType=cv2.LINE_AA)
            scale_count += 1

    # Five unequal primary sleeves are cropped from a wing, not emitted from a
    # visible hub. Their shapes, widths and branching roles are all different.
    primaries = [
        (_curve([(-90, 105), (220, 50), (655, 80), (1110, 225)]), 15),
        (_curve([(-80, 305), (245, 210), (585, 305), (1085, 410)]), 13),
        (_curve([(-70, 505), (210, 420), (615, 535), (1100, 560)]), 16),
        (_curve([(-90, 735), (240, 610), (620, 715), (1090, 690)]), 12),
        (_curve([(-80, 955), (285, 780), (690, 865), (1100, 820)]), 14),
    ]
    vein_mask = np.zeros((WORK, WORK), np.uint8)
    for pts, width in primaries:
        cv2.polylines(vein_mask, [pts], False, 255, width, cv2.LINE_AA)
        cv2.polylines(image, [pts], False, (5, 7, 10), width, cv2.LINE_AA)
        cv2.polylines(image, [pts], False, (33, 30, 38), max(2, width // 4), cv2.LINE_AA)

    # Unequal cross-veins close different spans; none repeats as a global grid.
    cross_specs = [
        ((150, 92), (170, 170), (205, 245), (210, 286), 7),
        ((335, 76), (370, 175), (350, 245), (365, 280), 5),
        ((570, 89), (600, 170), (565, 265), (590, 315), 8),
        ((805, 130), (790, 230), (850, 325), (830, 355), 6),
        ((255, 285), (275, 365), (245, 445), (270, 476), 6),
        ((470, 285), (450, 365), (505, 485), (490, 505), 8),
        ((720, 335), (755, 420), (700, 500), (725, 545), 5),
        ((920, 385), (895, 455), (945, 530), (930, 552), 7),
        ((175, 485), (185, 565), (160, 650), (185, 688), 5),
        ((390, 495), (425, 590), (385, 665), (410, 690), 7),
        ((650, 535), (625, 600), (690, 675), (670, 704), 6),
        ((875, 555), (905, 610), (860, 675), (885, 690), 8),
        ((290, 680), (315, 745), (285, 805), (315, 835), 6),
        ((545, 700), (520, 750), (575, 820), (555, 842), 5),
        ((790, 690), (825, 750), (790, 800), (810, 830), 7),
    ]
    node_mask = np.zeros((WORK, WORK), np.uint8)
    for x0, x1, x2, x3, width in cross_specs:
        pts = _curve([x0, x1, x2, x3], 90)
        cv2.polylines(vein_mask, [pts], False, 255, width, cv2.LINE_AA)
        cv2.polylines(image, [pts], False, (7, 8, 12), width, cv2.LINE_AA)
        cv2.circle(node_mask, tuple(pts[0]), width + 3, 255, -1, cv2.LINE_AA)
        cv2.circle(node_mask, tuple(pts[-1]), width + 2, 255, -1, cv2.LINE_AA)
        cv2.circle(image, tuple(pts[0]), width + 2, (20, 20, 25), 2, cv2.LINE_AA)
        cv2.circle(image, tuple(pts[-1]), width + 1, (20, 20, 25), 2, cv2.LINE_AA)

    # A cropped marginal sleeve carries unequal white insets and hooked fringe.
    margin = _curve([(540, -20), (740, 10), (940, 55), (1060, 175)], 150)
    cv2.polylines(image, [margin], False, (4, 5, 8), 16, cv2.LINE_AA)
    cv2.polylines(vein_mask, [margin], False, 255, 16, cv2.LINE_AA)
    inset_mask = np.zeros((WORK, WORK), np.uint8)
    for i in range(12):
        t = (i + 0.7) / 12.5
        idx = min(int(t * (len(margin) - 1)), len(margin) - 1)
        cx, cy = map(int, margin[idx])
        ax = 4 + (i * 3) % 7
        ay = 7 + (i * 5) % 8
        cv2.ellipse(inset_mask, (cx, cy), (ax, ay), 18 + i * 4, 0, 360, 255, -1, cv2.LINE_AA)
        cv2.ellipse(image, (cx, cy), (ax, ay), 18 + i * 4, 0, 360,
                    (224, 231, 218) if not angle_b else (214, 242, 255), -1, cv2.LINE_AA)

    fringe_mask = np.zeros((WORK, WORK), np.uint8)
    for i in range(75):
        x0 = 550 + i * 7
        if x0 >= WORK:
            break
        y0 = int(8 + 0.0011 * (x0 - 550) ** 2)
        length = 6 + (i * 7) % 10
        tilt = -5 + (i * 11) % 12
        cv2.line(fringe_mask, (x0, y0), (x0 + tilt, y0 - length), 255, 2, cv2.LINE_AA)
        cv2.line(image, (x0, y0), (x0 + tilt, y0 - length),
                 _mix(palette[(i + 3) % len(palette)], 0.92), 2, cv2.LINE_AA)

    # Fault lips are recoloured only where a real missing scale was outlined.
    fault_color = tuple(int(v) for v in palette[6 if not angle_b else 4])
    image[fault_mask > 180] = fault_color
    return image, {
        "scales": float(scale_count), "missing_scales": float(missing_count),
        "vein_coverage": float(np.mean(vein_mask > 0)),
        "node_coverage": float(np.mean(node_mask > 0)),
        "inset_coverage": float(np.mean(inset_mask > 0)),
        "fringe_coverage": float(np.mean(fringe_mask > 0)),
        "fault_coverage": float(np.mean(fault_mask > 0)),
    }


def _write(path: Path, rgb_u8: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "monarch_vein_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage = _paint(False)
    b, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    _write(output / f"{ID}_paint_2048.png", native_a)
    _write(output / f"{ID}_angle_a_2048.png", native_a)
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-monarch-vein-i1/1",
        "status": "REJECT-SCALE-CELL-CARPET-GLYPH-FAULTS-LADDER-VEINS-DO-NOT-WIRE",
        "owner_accepted": False, "production_wired": False,
        "finish_id": ID, "native_size": [2048, 2048],
        "topology": "explicit close-cropped monarch wing anatomy",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit anatomical raster; no RNG/noise/procedural cells/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
