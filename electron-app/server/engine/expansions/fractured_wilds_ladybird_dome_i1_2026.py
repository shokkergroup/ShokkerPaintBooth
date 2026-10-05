# -*- coding: utf-8 -*-
"""Frozen native-2048 Ladybird Dome I1 rejection (never wired).

SPB-105 / Wilds attempt 66 / 2026-08-25. The owner acceptance surface is the
full 2048 canvas. This blank-topology attempt replaces the recovered macro
moire Ladybird with a deterministic asymmetric shell assembled from unequal
curved 8-32 px microfacets. Black lacunae grow through discrete neighboring
facets rather than circles; sutures, highlight crescents, pore arcs, chipped
corners, compression notches and the elytral seam are attached to those same
facets. No RNG, sampled noise, scalar contour texture, dots, stamp bank,
Voronoi/cell solver, long carrier rail or shared Wilds composer is used.

Native verdict: the unequal curved facets still form a red brick/mosaic paver;
crescents repeat as C/hook glyphs, lacunae become blocky macro patches and the
center seam reads as a zipper. Strong A/B and speed do not rescue the failed
carrier. No parameter, palette, density, seam, spec or runtime repair is
authorized; see the colocated REJECTION.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_ladybird_dome"
WORK = 1024
NATIVE = 2048

PALETTE_A = np.asarray([
    (76, 8, 8), (105, 10, 8), (133, 13, 8), (161, 18, 8),
    (190, 25, 8), (218, 36, 9), (239, 55, 11), (251, 78, 13),
    (230, 99, 20), (196, 48, 16), (150, 24, 19), (246, 137, 39),
], np.uint8)
PALETTE_B = np.asarray([
    (6, 35, 71), (5, 55, 100), (7, 79, 128), (6, 106, 150),
    (4, 137, 165), (8, 168, 167), (19, 193, 151), (39, 211, 126),
    (81, 191, 202), (66, 105, 211), (119, 64, 211), (224, 176, 45),
], np.uint8)
MACULE_A = np.asarray([(7, 8, 9), (14, 12, 15), (25, 15, 19), (43, 19, 24)], np.uint8)
MACULE_B = np.asarray([(18, 8, 47), (27, 12, 72), (38, 19, 96), (71, 31, 117)], np.uint8)
EDGE_A = (255, 154, 49)
EDGE_B = (103, 244, 207)


def _blank_masks() -> dict[str, np.ndarray]:
    names = ("facet", "suture", "macule", "crescent", "pore", "chip", "compression", "seam", "class")
    return {name: np.zeros((WORK, WORK), np.uint8) for name in names}


def _curve_y(base: float, x: float, row: int, side: int) -> int:
    xn = (x - WORK * .5) / (WORK * .5)
    dome = (1.0 - min(1.0, xn * xn))
    value = (base + 5.2 * np.sin(x * .0107 + row * .391)
             + 2.4 * np.sin(x * .0263 - row * .217)
             + side * 7.5 * dome * np.sin(row * .173))
    return int(round(value))


def _is_macule(row: int, col: int, side: int) -> bool:
    # Discrete stress-grown lacunae. Each seed expands across neighboring
    # facets with a skewed taxicab metric; no circle/distance-field raster is
    # painted, and boundary teeth remain individual shell facets.
    seeds = (
        (12, 13, 5.2, 7.8, .42), (23, 31, 6.4, 5.0, -.35),
        (35, 18, 4.7, 8.2, .61), (47, 39, 7.2, 5.5, -.52),
        (58, 9, 5.8, 6.7, .28), (69, 29, 4.8, 8.5, -.66),
        (81, 17, 6.8, 5.2, .49), (93, 37, 5.0, 7.0, -.31),
        (104, 24, 4.5, 6.0, .58),
    )
    local_col = col if side < 0 else col + 2
    for sr, sc, rr, rc, skew in seeds:
        dr = row - sr
        dc = local_col - sc - skew * dr
        tooth = ((row * 7 + col * 11 + sr) % 7) * .075
        if abs(dr) / rr + abs(dc) / rc + tooth < 1.0:
            return True
    return False


def _paint(flipped: bool = False):
    palette = PALETTE_B if flipped else PALETTE_A
    macules = MACULE_B if flipped else MACULE_A
    edge = EDGE_B if flipped else EDGE_A
    image = np.zeros((WORK, WORK, 3), np.uint8)
    masks = _blank_masks()
    facet_count = crescent_count = pore_count = chip_count = notch_count = 0

    row = 0
    y_base = -7.0
    while y_base < WORK + 8:
        row_h = 7 + ((row * 5 + row // 3) % 6)  # 7-12 work px => 14-24 native
        y_next = y_base + row_h
        for side in (-1, 1):
            x_min, x_max = ((-10, WORK // 2 + 15) if side < 0 else (WORK // 2 - 15, WORK + 10))
            col = 0
            x = float(x_min - ((row * 13 + (3 if side > 0 else 0)) % 17))
            while x < x_max:
                width = 7 + ((row * 11 + col * 7 + (row * col) % 13 + (5 if side > 0 else 0)) % 10)
                x1 = x + width
                shear = side * (((row * 3 + col * 5) % 7) - 3)
                polygon = np.asarray([
                    (int(round(x)), _curve_y(y_base, x, row, side)),
                    (int(round(x1)), _curve_y(y_base, x1, row, side)),
                    (int(round(x1 + shear)), _curve_y(y_next, x1 + shear, row + 1, side)),
                    (int(round(x + shear)), _curve_y(y_next, x + shear, row + 1, side)),
                ], np.int32)
                center_x = int(round(float(polygon[:, 0].mean())))
                center_y = int(round(float(polygon[:, 1].mean())))
                if center_x < -20 or center_x > WORK + 20 or center_y < -20 or center_y > WORK + 20:
                    x = x1
                    col += 1
                    continue
                macule = _is_macule(row, col, side)
                dome_rank = int(np.clip(5.0 * (1.0 - abs(center_x - WORK * .5) / (WORK * .5)), 0, 5))
                class_id = (row * 7 + col * 5 + (row * col) % 11 + dome_rank) % len(palette)
                color = macules[(row + col * 3) % len(macules)] if macule else palette[class_id]
                cv2.fillConvexPoly(image, polygon, tuple(int(v) for v in color), lineType=cv2.LINE_AA)
                cv2.fillConvexPoly(masks["facet"], polygon, 255)
                cv2.fillConvexPoly(masks["class"], polygon, int(18 + class_id * 20))
                if macule:
                    cv2.fillConvexPoly(masks["macule"], polygon, 255)
                border_color = (13, 9, 12) if not flipped else (9, 22, 52)
                cv2.polylines(image, [polygon], True, border_color, 1, cv2.LINE_AA)
                cv2.polylines(masks["suture"], [polygon], True, 255, 1, cv2.LINE_AA)

                # Attached highlight crescent: follows a facet edge and never
                # forms a free circle or repeated dot.
                if (row * 3 + col * 5 + side) % 9 in (0, 1):
                    p0 = polygon[0].astype(np.float32)
                    p1 = polygon[1].astype(np.float32)
                    mid = (p0 + p1) * .5 + np.asarray((0.0, 2.0 + ((row + col) % 3)), np.float32)
                    crescent = np.asarray([p0 * .72 + mid * .28, mid, p1 * .72 + mid * .28], np.int32)
                    cv2.polylines(image, [crescent], False, edge, 2, cv2.LINE_AA)
                    cv2.polylines(masks["crescent"], [crescent], False, 255, 2, cv2.LINE_AA)
                    crescent_count += 1

                # Pore arcs are open ellipses, varied in aspect and orientation.
                if (row * 17 + col * 11) % 13 == 0:
                    axes = (3 + ((row + col) % 4), 2 + ((row * 2 + col) % 3))
                    angle = float((row * 19 + col * 31 + (17 if side > 0 else 0)) % 180)
                    cv2.ellipse(image, (center_x, center_y), axes, angle, 25, 265,
                                (247, 187, 98) if not flipped else (119, 225, 255), 1, cv2.LINE_AA)
                    cv2.ellipse(masks["pore"], (center_x, center_y), axes, angle, 25, 265, 255, 1, cv2.LINE_AA)
                    pore_count += 1

                # Chipped lacuna: remove one corner with a small unequal wedge.
                if (row * 23 + col * 29 + side) % 31 == 0:
                    corner = polygon[(row + col) % 4]
                    wedge = np.asarray([
                        corner,
                        corner + (polygon[((row + col) % 4 + 1) % 4] - corner) * .42,
                        corner + (polygon[((row + col) % 4 - 1) % 4] - corner) * .35,
                    ], np.int32)
                    cv2.fillConvexPoly(image, wedge, (8, 7, 10) if not flipped else (20, 8, 47), cv2.LINE_AA)
                    cv2.fillConvexPoly(masks["chip"], wedge, 255)
                    chip_count += 1

                # Short rim-compression notch, contained inside the facet.
                if (row * 5 + col * 7) % 11 == 0:
                    length = 4 + ((row + col * 2) % 8)
                    dx = side * length
                    cv2.line(image, (center_x - dx // 2, center_y),
                             (center_x + dx // 2, center_y + ((row + col) % 3 - 1)),
                             (85, 24, 17) if not flipped else (25, 64, 112), 2, cv2.LINE_AA)
                    cv2.line(masks["compression"], (center_x - dx // 2, center_y),
                             (center_x + dx // 2, center_y + ((row + col) % 3 - 1)), 255, 2, cv2.LINE_AA)
                    notch_count += 1
                facet_count += 1
                x = x1
                col += 1
        y_base = y_next
        row += 1

    # One asymmetric elytral seam, fine in width but compositionally coherent.
    seam_points = []
    for y in range(-8, WORK + 9, 6):
        x = int(round(WORK * .5 + 10.0 * np.sin(y * .0109)
                      + 4.0 * np.sin(y * .0317 + .8)))
        seam_points.append((x, y))
    seam = np.asarray(seam_points, np.int32)
    cv2.polylines(image, [seam], False, (9, 7, 10) if not flipped else (18, 9, 46), 7, cv2.LINE_AA)
    cv2.polylines(image, [seam], False, edge, 2, cv2.LINE_AA)
    cv2.polylines(masks["seam"], [seam], False, 255, 7, cv2.LINE_AA)
    # Seam pressure collars are short unequal cross-marks, not a zipper cadence.
    for index, (x, y) in enumerate(seam_points[2:-2]):
        if index % 3 == 0:
            reach_l = 5 + (index * 7 % 9)
            reach_r = 4 + (index * 11 % 10)
            cv2.line(image, (x - reach_l, y - 1), (x - 3, y + 2), edge, 1, cv2.LINE_AA)
            cv2.line(image, (x + 3, y + 2), (x + reach_r, y - 2), edge, 1, cv2.LINE_AA)
            cv2.line(masks["compression"], (x - reach_l, y - 1), (x - 3, y + 2), 255, 1, cv2.LINE_AA)
            cv2.line(masks["compression"], (x + 3, y + 2), (x + reach_r, y - 2), 255, 1, cv2.LINE_AA)
            notch_count += 2

    coverage = {
        "microfacets": facet_count,
        "highlight_crescents": crescent_count,
        "pore_arcs": pore_count,
        "chipped_lacunae": chip_count,
        "compression_notches": notch_count,
        "macule_fraction": round(float(np.mean(masks["macule"] > 0)), 6),
        "suture_fraction": round(float(np.mean(masks["suture"] > 0)), 6),
    }
    return image, coverage, masks


def _spread(field: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(field, (2.0, 98.0))
    return np.clip((field - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)


def _tier(field: np.ndarray, levels: tuple[int, ...]) -> np.ndarray:
    idx = np.minimum((np.clip(field, 0.0, 1.0) * len(levels)).astype(np.int32), len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx]


def _material(masks: dict[str, np.ndarray]) -> np.ndarray:
    """Provisional anatomy-owned maps; not acceptance evidence before paint review."""
    cls = masks["class"].astype(np.float32) / 255.0
    sut = masks["suture"].astype(np.float32) / 255.0
    mac = masks["macule"].astype(np.float32) / 255.0
    cre = masks["crescent"].astype(np.float32) / 255.0
    pore = masks["pore"].astype(np.float32) / 255.0
    chip = masks["chip"].astype(np.float32) / 255.0
    comp = masks["compression"].astype(np.float32) / 255.0
    seam = masks["seam"].astype(np.float32) / 255.0
    suture_halo = cv2.GaussianBlur(sut, (0, 0), 1.7)
    pore_halo = cv2.GaussianBlur(pore, (0, 0), 2.4)
    chip_halo = cv2.GaussianBlur(chip, (0, 0), 3.1)
    metal_raw = np.clip(.08 + .62 * cls + .33 * mac + .45 * comp - .28 * chip_halo, 0, 1)
    rough_raw = np.clip(.06 + .67 * pore_halo + .54 * chip_halo + .31 * suture_halo - .23 * cre, 0, 1)
    coat_raw = np.clip(.09 + .72 * cre + .51 * seam + .27 * (1.0 - cls) - .24 * pore_halo, 0, 1)
    metal = _tier(_spread(metal_raw), (5, 29, 57, 91, 128, 168, 211, 250))
    rough = _tier(_spread(rough_raw), (12, 39, 70, 104, 141, 181, 222, 250))
    coat = _tier(_spread(coat_raw), (4, 27, 55, 88, 126, 168, 214, 253))
    return np.stack((metal, rough, coat), axis=2)


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "ladybird_dome_i1"
    output.mkdir(parents=True, exist_ok=True)
    timings = []
    first = None
    for _ in range(3):
        started = time.perf_counter()
        a, coverage, masks = _paint(False)
        b, _, _ = _paint(True)
        spec = _material(masks)
        timings.append(time.perf_counter() - started)
        if first is None:
            first = (a.copy(), b.copy(), spec.copy())
    a, b, spec = first
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_spec = cv2.resize(spec, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    _write(output / f"{ID}_paint_2048.png", native_a)
    _write(output / f"{ID}_angle_a_2048.png", native_a)
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_crop_1to1.png", native_a[512:1536, 512:1536])
    for channel, name in enumerate(("metal", "roughness", "clearcoat")):
        cv2.imwrite(str(output / f"{ID}_{name}_2048.png"), native_spec[..., channel],
                    [cv2.IMWRITE_PNG_COMPRESSION, 0])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    digest = hashlib.sha256(native_a.tobytes() + native_b.tobytes() + native_spec.tobytes()).hexdigest()
    manifest = {
        "id": ID,
        "module": "engine.expansions.fractured_wilds_ladybird_dome_i1_2026",
        "status": "NATIVE-2048-PAINT-CONTACT-NOT-WIRED",
        "attempt": 66,
        "timings_s": timings,
        "deterministic_digest": digest,
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.percentile(delta, 95)),
        "spec_std_provisional": [float(native_spec[..., i].std()) for i in range(3)],
        "coverage": coverage,
        "owner_accepted": False,
        "production_wired": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
