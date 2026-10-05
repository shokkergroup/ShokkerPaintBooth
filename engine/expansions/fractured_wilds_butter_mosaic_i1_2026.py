# -*- coding: utf-8 -*-
"""Isolated native-2048 Butter Mosaic aperiodic floral tessera study.

SPB-WILDS-BUTTER-MOSAIC-I1 / SPB-105, 2026-08-24. Five incommensurate line
families fracture one sheet into unequal quasicrystal tesserae. Tile bevels,
grout capillaries, ray florets, button centres, missing-tile scars, repair
wedges and chipped corners are derived from that topology at 8-32 px.

Paint/A-B review only. No RNG, sampled noise, regular grid, repeated monotile,
shared Wilds composer or material maps. Fail closed until native owner review.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fbl_butter_mosaic"
WORK = 1024
NATIVE = 2048
PI = float(np.pi)

PALETTE_A = np.asarray([
    (255, 216, 49), (255, 176, 32), (244, 119, 26), (224, 61, 43),
    (185, 43, 88), (139, 48, 137), (83, 64, 174), (48, 96, 190),
    (32, 147, 178), (42, 184, 137), (103, 199, 80), (173, 207, 52),
    (246, 231, 108), (255, 145, 75),
], np.uint8)
PALETTE_B = np.asarray([
    (35, 231, 197), (30, 192, 228), (39, 137, 238), (72, 83, 229),
    (129, 57, 220), (190, 48, 210), (238, 53, 158), (255, 78, 92),
    (255, 130, 43), (250, 197, 51), (182, 224, 62), (83, 222, 112),
    (98, 242, 225), (196, 99, 237),
], np.uint8)


def _topology() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = xx - 0.5 * WORK
    y = yy - 0.5 * WORK
    spacings = (37.0, 41.0, 43.0, 47.0, 53.0)
    offsets = (0.13, 0.37, 0.61, 0.23, 0.79)
    grout = np.zeros((WORK, WORK), np.uint8)
    family_count = np.zeros((WORK, WORK), np.uint8)
    family_role = np.zeros((WORK, WORK), np.float32)
    for k, (spacing, offset) in enumerate(zip(spacings, offsets)):
        angle = 0.17 + k * PI / 5.0
        projection = (x * np.cos(angle) + y * np.sin(angle)) / spacing + offset
        distance = np.abs((projection + 0.5) % 1.0 - 0.5) * spacing
        line = distance < (2.0 + 0.35 * (k % 3))
        grout[line] = 255
        family_count[line] = np.clip(family_count[line] + 1, 0, 255)
        family_role[line] = (k + 1) / 5.0
    # Four-work-pixel grout becomes 8 native px after upscale.
    grout = cv2.dilate(grout, np.ones((3, 3), np.uint8), iterations=1)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        (grout == 0).astype(np.uint8), 8)
    if count < 32:
        raise RuntimeError(f"pentagrid produced only {count} tesserae")
    return labels, stats, centroids, np.stack((grout, family_count, np.clip(family_role * 255, 0, 255).astype(np.uint8)), axis=2)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    palette = PALETTE_B if angle_b else PALETTE_A
    labels, stats, centroids, grout_bundle = _topology()
    grout, junctions, family_role = [grout_bundle[..., i] for i in range(3)]
    max_label = int(labels.max())
    lut = np.zeros((max_label + 1, 3), np.uint8)
    for label in range(1, max_label + 1):
        area = int(stats[label, cv2.CC_STAT_AREA])
        cx, cy = centroids[label]
        index = int(label * 7 + area * 0.031 + cx * 0.017 + cy * 0.023) % len(palette)
        factor = 0.62 + 0.36 * (0.5 + 0.5 * np.sin(label * 1.61803398875 + area * 0.011))
        lut[label] = np.clip(np.rint(palette[index].astype(np.float32) * factor), 0, 255)
    image = lut[labels]

    # Distance from grout produces two bevel roles without changing tile labels.
    interior = (grout == 0).astype(np.uint8)
    distance = cv2.distanceTransform(interior, cv2.DIST_L2, 3)
    bevel_bright = ((distance > 0.5) & (distance <= 3.5)).astype(np.uint8) * 255
    bevel_dark = ((distance > 3.5) & (distance <= 7.0)).astype(np.uint8) * 255
    image[bevel_dark > 0] = (image[bevel_dark > 0].astype(np.float32) * 0.55).astype(np.uint8)
    bright_color = np.asarray((255, 242, 162) if not angle_b else (160, 247, 255), np.uint8)
    image[bevel_bright > 0] = bright_color
    image[grout > 0] = (14, 9, 16) if not angle_b else (8, 11, 24)

    masks = {
        "grout": grout.copy(), "bevel": bevel_bright.copy(),
        "capillary": np.zeros((WORK, WORK), np.uint8),
        "floret": np.zeros((WORK, WORK), np.uint8),
        "button": np.zeros((WORK, WORK), np.uint8),
        "missing": np.zeros((WORK, WORK), np.uint8),
        "repair": np.zeros((WORK, WORK), np.uint8),
        "chip": np.zeros((WORK, WORK), np.uint8),
    }

    # Multi-family intersections become fine grout capillaries and chipped nodes.
    junction_mask = (junctions >= 2).astype(np.uint8) * 255
    n, _, _, junction_centres = cv2.connectedComponentsWithStats(junction_mask, 8)
    cap_color = tuple(int(v) for v in palette[10 if not angle_b else 12])
    chip_color = tuple(int(v) for v in palette[3 if not angle_b else 7])
    for j in range(1, n):
        cx, cy = map(int, junction_centres[j])
        if not (2 <= cx < WORK - 2 and 2 <= cy < WORK - 2):
            continue
        if j % 3 == 0:
            angle = 0.31 * j
            end = (int(cx + 5 * np.cos(angle)), int(cy + 5 * np.sin(angle)))
            cv2.line(image, (cx, cy), end, cap_color, 2, cv2.LINE_AA)
            cv2.line(masks["capillary"], (cx, cy), end, 90 + 20 * (j % 7), 2, cv2.LINE_AA)
        if j % 7 == 0:
            tri = np.asarray([(cx - 3, cy), (cx + 3, cy - 2), (cx + 2, cy + 4)], np.int32)
            cv2.fillConvexPoly(image, tri, chip_color, cv2.LINE_AA)
            cv2.fillConvexPoly(masks["chip"], tri, 100 + 18 * (j % 8), cv2.LINE_AA)

    # Different component roles receive different anatomy. Florets are sparse,
    # unequal and clipped to their parent tessera rather than stamped everywhere.
    floret_color = tuple(int(v) for v in palette[12 if not angle_b else 9])
    button_color = tuple(int(v) for v in palette[5 if not angle_b else 11])
    repair_color = tuple(int(v) for v in palette[8 if not angle_b else 2])
    floret_count = button_count = missing_count = repair_count = 0
    for label in range(1, max_label + 1):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < 85:
            continue
        cx, cy = map(int, centroids[label])
        tile = (labels == label).astype(np.uint8) * 255
        role = (label * 11 + area * 3 + cx + 2 * cy) % 29
        if role in (0, 6, 17) and area > 135:
            rays = 4 + (label % 4)
            radius = min(7, max(4, int(np.sqrt(area) * 0.18)))
            local = np.zeros((WORK, WORK), np.uint8)
            for ray in range(rays):
                a = 2 * PI * ray / rays + 0.17 * label
                end = (int(cx + radius * np.cos(a)), int(cy + radius * np.sin(a)))
                cv2.line(local, (cx, cy), end, 150 + 14 * (ray % 7), 2, cv2.LINE_AA)
            local = cv2.bitwise_and(local, tile)
            image[local > 0] = floret_color
            masks["floret"] = np.maximum(masks["floret"], local)
            floret_count += 1
        elif role in (4, 19) and area > 110:
            radius = 3 + label % 4
            cv2.circle(image, (cx, cy), radius, button_color, -1, cv2.LINE_AA)
            cv2.circle(masks["button"], (cx, cy), radius, 110 + 20 * (label % 7), -1, cv2.LINE_AA)
            button_count += 1
        elif role == 9 and area > 160:
            image[tile > 0] = (9, 7, 13) if not angle_b else (7, 8, 19)
            masks["missing"][tile > 0] = 210
            # A one-off repair wedge fills only part of the missing tessera.
            w = int(stats[label, cv2.CC_STAT_WIDTH])
            h = int(stats[label, cv2.CC_STAT_HEIGHT])
            wedge = np.asarray([(cx - w // 4, cy + h // 4),
                                (cx + w // 3, cy + h // 5),
                                (cx + w // 5, cy - h // 3)], np.int32)
            local = np.zeros((WORK, WORK), np.uint8)
            cv2.fillConvexPoly(local, wedge, 190, cv2.LINE_AA)
            local = cv2.bitwise_and(local, tile)
            image[local > 0] = repair_color
            masks["repair"] = np.maximum(masks["repair"], local)
            missing_count += 1
            repair_count += 1

    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    coverage.update({
        "tesserae": float(max_label), "florets": float(floret_count),
        "buttons": float(button_count), "missing_tiles": float(missing_count),
        "repair_wedges": float(repair_count),
    })
    return image, masks, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "butter_mosaic_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, _, coverage = _paint(False)
    b, _, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    _write(output / f"{ID}_paint_2048.png", native_a)
    _write(output / f"{ID}_angle_a_2048.png", native_a)
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-butter-mosaic-i1/1",
        "status": "REJECT-REPEATED-PENTAGRID-STARBURST-HUBS-OVER-BUDGET-DO-NOT-WIRE",
        "owner_accepted": False, "production_wired": False,
        "finish_id": ID, "native_size": [2048, 2048],
        "topology": "five-family aperiodic floral tessera fracture",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic pentagrid/component anatomy; no RNG/noise/regular grid/monotile",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
