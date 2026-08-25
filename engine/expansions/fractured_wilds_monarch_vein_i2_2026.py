# -*- coding: utf-8 -*-
"""Native-2048 Monarch Vein I2 carrier replacement.

I2 replaces I1's outlined scale cells, repeated fault glyphs and ladder cross-
veins with overlapping tapered scale packets, silent omissions with attached
torn lips, oblique unequal closures, compressed node collars and hooked fringe.
Paint/A-B only; no RNG/noise/shared composer/material maps.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np

from .fractured_wilds_monarch_vein_i1_2026 import (
    COLORS_A, COLORS_B, ID, NATIVE, WORK, _curve, _mix,
)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    palette = COLORS_B if angle_b else COLORS_A
    image = np.zeros((WORK, WORK, 3), np.uint8)
    image[:] = (13, 8, 10) if not angle_b else (9, 9, 19)
    packet_mask = np.zeros((WORK, WORK), np.uint8)
    packet_relief = np.zeros((WORK, WORK), np.uint8)
    optical_order = np.zeros((WORK, WORK), np.uint8)
    torn_mask = np.zeros((WORK, WORK), np.uint8)

    # Overlapping tapered packets have no enclosing outlines and no visible
    # cell boundaries. The broad direction changes gradually across the wing.
    packet_count = 0
    omitted = 0
    for row, cy in enumerate(range(-12, WORK + 18, 8)):
        offset = 5 if row % 2 else 0
        for col, cx in enumerate(range(-12 + offset, WORK + 18, 10)):
            flow = 0.28 * np.sin(0.047 * cy) + 0.19 * np.sin(0.039 * cx + 0.7)
            dx = int(np.rint(2.5 * np.sin(0.31 * row + 0.73 * col) + 3.0 * flow))
            length = 7 + int(4 * abs(np.sin(0.41 * row - 0.37 * col)))
            half = 3 + int(2 * abs(np.cos(0.29 * row + 0.53 * col)))
            omit = (np.sin(0.17 * row + 0.59 * col) > 0.965
                    and np.cos(0.71 * row - 0.23 * col) > 0.55)
            if omit:
                omitted += 1
                # Only the immediately adjacent scale receives a short torn lip.
                cv2.line(torn_mask, (cx - half, cy + 2), (cx + half + dx, cy + 4),
                         255, 2, cv2.LINE_AA)
                continue
            poly = np.asarray([
                (cx - half, cy - 2), (cx + dx, cy - length),
                (cx + half + dx, cy - 1), (cx + half - 1, cy + 5),
                (cx - half + 1, cy + 5),
            ], np.int32)
            idx = (row * 3 + col * 5 + int(abs(np.sin(row - col)) * 7)) % len(palette)
            factor = 0.68 + 0.27 * (0.5 + 0.5 * np.sin(0.19 * row + 0.33 * col))
            cv2.fillConvexPoly(image, poly, _mix(palette[idx], factor), cv2.LINE_AA)
            cv2.fillConvexPoly(packet_relief, poly, int(42 + 205 * factor), cv2.LINE_AA)
            order_value = int(28 + 218 * (0.5 + 0.5 * np.sin(0.27 * row + 0.91 * col)))
            cv2.fillConvexPoly(optical_order, poly, order_value, cv2.LINE_AA)
            if (row + col) % 7 == 0:
                cv2.line(image, (cx - half + 1, cy + 3), (cx + half - 2, cy + 3),
                         _mix(palette[(idx + 2) % len(palette)], 1.04), 2, cv2.LINE_AA)
            cv2.fillConvexPoly(packet_mask, poly, 255, cv2.LINE_AA)
            packet_count += 1

    image[torn_mask > 180] = tuple(int(v) for v in palette[6 if not angle_b else 4])

    # Four cropped primaries vary strongly in curvature and width. They never
    # share a visible source and therefore do not form a fan or repeated rails.
    primaries = [
        (_curve([(-120, 110), (190, 25), (690, 80), (1110, 300)]), 15),
        (_curve([(-100, 395), (245, 245), (555, 405), (1090, 445)]), 12),
        (_curve([(-90, 690), (180, 530), (690, 720), (1110, 610)]), 16),
        (_curve([(-100, 970), (300, 735), (650, 935), (1100, 790)]), 13),
    ]
    vein_mask = np.zeros((WORK, WORK), np.uint8)
    for i, (pts, width) in enumerate(primaries):
        cv2.polylines(vein_mask, [pts], False, 255, width, cv2.LINE_AA)
        cv2.polylines(image, [pts], False, (3, 4, 7), width, cv2.LINE_AA)
        cv2.polylines(image, [pts], False,
                      _mix(palette[(i + 5) % len(palette)], 0.30), 3, cv2.LINE_AA)

    # Oblique closures change direction and span; no vertical ladder cadence.
    closures = [
        [(90, 92), (155, 155), (255, 250), (330, 320)],
        [(410, 70), (455, 165), (390, 285), (475, 365)],
        [(720, 118), (650, 230), (760, 340), (815, 418)],
        [(170, 350), (245, 440), (205, 550), (285, 610)],
        [(565, 385), (630, 480), (550, 590), (640, 675)],
        [(900, 430), (835, 505), (900, 575), (930, 625)],
        [(350, 645), (420, 735), (365, 835), (455, 885)],
        [(760, 685), (835, 760), (780, 840), (860, 870)],
    ]
    node_mask = np.zeros((WORK, WORK), np.uint8)
    for i, controls in enumerate(closures):
        pts = _curve(controls, 100)
        width = 5 + (i * 3) % 5
        cv2.polylines(vein_mask, [pts], False, 255, width, cv2.LINE_AA)
        cv2.polylines(image, [pts], False, (5, 5, 8), width, cv2.LINE_AA)
        # Compressed collars are one-off angular wedges, not repeated rings.
        for endpoint, sign in ((pts[0], 1), (pts[-1], -1)):
            ex, ey = map(int, endpoint)
            collar = np.asarray([(ex - 7, ey), (ex, ey - 4 * sign),
                                 (ex + 8, ey), (ex, ey + 5 * sign)], np.int32)
            cv2.fillConvexPoly(node_mask, collar, 255, cv2.LINE_AA)
            cv2.fillConvexPoly(image, collar,
                               _mix(palette[(i + 6) % len(palette)], 0.42), cv2.LINE_AA)

    # Three short abrasion faults branch from real vein sleeves.
    fault_paths = [
        _curve([(320, 330), (350, 345), (370, 375), (405, 392)], 55),
        _curve([(635, 676), (660, 655), (690, 640), (715, 625)], 55),
        _curve([(815, 420), (835, 402), (850, 385), (875, 372)], 55),
    ]
    for i, pts in enumerate(fault_paths):
        cv2.polylines(image, [pts], False, (12, 8, 12), 8, cv2.LINE_AA)
        cv2.polylines(image, [pts], False,
                      _mix(palette[(i + 1) % len(palette)], 0.92), 2, cv2.LINE_AA)

    # The cropped margin carries unequal pale insets and individually hooked fringe.
    margin = _curve([(525, -18), (720, 7), (900, 58), (1065, 180)], 160)
    cv2.polylines(image, [margin], False, (3, 4, 7), 15, cv2.LINE_AA)
    cv2.polylines(vein_mask, [margin], False, 255, 15, cv2.LINE_AA)
    inset_mask = np.zeros((WORK, WORK), np.uint8)
    for i, t in enumerate((0.08, 0.15, 0.24, 0.34, 0.45, 0.57, 0.70, 0.82, 0.92)):
        cx, cy = map(int, margin[int(t * (len(margin) - 1))])
        axes = (4 + (3 * i) % 6, 7 + (5 * i) % 7)
        cv2.ellipse(inset_mask, (cx, cy), axes, 22 + 6 * i, 0, 360, 255, -1, cv2.LINE_AA)
        cv2.ellipse(image, (cx, cy), axes, 22 + 6 * i, 0, 360,
                    (232, 232, 212) if not angle_b else (208, 240, 250), -1, cv2.LINE_AA)

    fringe_mask = np.zeros((WORK, WORK), np.uint8)
    for i in range(58):
        x0 = 560 + 8 * i
        if x0 >= WORK:
            break
        y0 = int(7 + 0.0010 * (x0 - 560) ** 2)
        bend = -6 + (7 * i) % 13
        length = 7 + (11 * i) % 9
        p1 = (x0 + bend // 2, y0 - length // 2)
        p2 = (x0 + bend, y0 - length)
        cv2.line(fringe_mask, (x0, y0), p1, 255, 2, cv2.LINE_AA)
        cv2.line(fringe_mask, p1, p2, 255, 2, cv2.LINE_AA)
        cv2.line(image, (x0, y0), p1, _mix(palette[(i + 2) % len(palette)], 0.90), 2, cv2.LINE_AA)
        cv2.line(image, p1, p2, _mix(palette[(i + 4) % len(palette)], 1.02), 2, cv2.LINE_AA)

    coverage = {
        "scale_packets": float(packet_count), "silent_omissions": float(omitted),
        "packet_coverage": float(np.mean(packet_mask > 0)),
        "torn_lip_coverage": float(np.mean(torn_mask > 0)),
        "vein_coverage": float(np.mean(vein_mask > 0)),
        "node_coverage": float(np.mean(node_mask > 0)),
        "inset_coverage": float(np.mean(inset_mask > 0)),
        "fringe_coverage": float(np.mean(fringe_mask > 0)),
    }
    maps = {
        "packet": packet_mask, "relief": packet_relief, "order": optical_order,
        "torn": torn_mask,
        "vein": vein_mask, "node": node_mask, "inset": inset_mask,
        "fringe": fringe_mask,
    }
    return image, coverage, maps


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def _spread(field: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(field, (3.0, 97.0))
    return np.clip((field - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)


def _tier(field: np.ndarray, levels: tuple[int, ...]) -> np.ndarray:
    index = np.minimum((np.clip(field, 0.0, 1.0) * len(levels)).astype(np.int32), len(levels) - 1)
    return np.asarray(levels, np.uint8)[index]


def _material(maps: dict[str, np.ndarray]) -> np.ndarray:
    # SPB-105 / SPB-WILDS-MONARCH-I2, 2026-08-24. Owner verdict: repeated
    # paint/spec carriers are the app's "biggest cardinal sin PERIOD". These
    # channels begin only after native paint/collision review and use different
    # anatomical causes; no paint luminance or shared threshold is consumed.
    # Spec state moved absent -> M/R/Cc std 52.467/60.472/90.124, full eight-
    # tier ranges and correlations -0.659/0.349/-0.347; paint pixels unchanged.
    relief = maps["relief"].astype(np.float32) / 255.0
    order = maps["order"].astype(np.float32) / 255.0
    vein = maps["vein"].astype(np.float32) / 255.0
    node = maps["node"].astype(np.float32) / 255.0
    torn = maps["torn"].astype(np.float32) / 255.0
    inset = maps["inset"].astype(np.float32) / 255.0
    fringe = maps["fringe"].astype(np.float32) / 255.0
    distance = cv2.distanceTransform(255 - maps["vein"], cv2.DIST_L2, 3)
    sleeve_falloff = np.exp(-distance / 18.0).astype(np.float32)
    local_lips = cv2.GaussianBlur(torn, (0, 0), 2.0)
    metal_raw = np.clip(0.08 + 0.62 * relief + 0.58 * vein + 0.51 * node
                        + 0.38 * torn - 0.36 * inset - 0.18 * fringe, 0.0, 1.0)
    rough_raw = np.clip(0.12 + 0.63 * (1.0 - relief) + 0.72 * local_lips
                        + 0.55 * fringe + 0.34 * sleeve_falloff
                        - 0.48 * vein - 0.31 * inset, 0.0, 1.0)
    coat_raw = np.clip(0.05 + 0.76 * order + 0.68 * inset + 0.52 * node
                       + 0.23 * vein - 0.49 * torn - 0.31 * fringe, 0.0, 1.0)
    metal = _tier(_spread(metal_raw), (6, 31, 60, 94, 130, 169, 213, 250))
    rough = _tier(_spread(rough_raw), (14, 41, 72, 106, 142, 181, 220, 249))
    coat = _tier(_spread(coat_raw), (5, 28, 57, 90, 128, 169, 214, 252))
    return np.stack((metal, rough, coat), axis=2)


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "monarch_vein_i2"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage, maps = _paint(False)
    b, _, _ = _paint(True)
    spec = _material(maps)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_spec = cv2.resize(spec, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    elapsed = time.perf_counter() - started
    _write(output / f"{ID}_paint_2048.png", native_a)
    _write(output / f"{ID}_angle_a_2048.png", native_a)
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    for channel, suffix in enumerate(("metal", "roughness", "clearcoat")):
        if not cv2.imwrite(str(output / f"{ID}_{suffix}_2048.png"), native_spec[..., channel]):
            raise OSError(f"could not write {suffix}")
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    stats = {}
    for channel, name in enumerate(("metal", "roughness", "clearcoat")):
        values = native_spec[..., channel]
        stats[name] = {
            "std": round(float(values.std()), 6),
            "range": [int(values.min()), int(values.max())],
            "values": [int(v) for v in np.unique(values)],
        }
    correlations = {
        "metal_roughness": round(float(np.corrcoef(native_spec[..., 0].ravel(), native_spec[..., 1].ravel())[0, 1]), 6),
        "metal_clearcoat": round(float(np.corrcoef(native_spec[..., 0].ravel(), native_spec[..., 2].ravel())[0, 1]), 6),
        "roughness_clearcoat": round(float(np.corrcoef(native_spec[..., 1].ravel(), native_spec[..., 2].ravel())[0, 1]), 6),
    }
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-monarch-vein-i2/1",
        "status": "KEEP-CANDIDATE-I2-NATIVE-2048-ISOLATED",
        "owner_accepted": False, "production_wired": False,
        "finish_id": ID, "native_size": [2048, 2048],
        "topology": "close-cropped wing with tapered scale packets and oblique venation",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit anatomical raster; no RNG/noise/cells/shared composer",
        "spec_authored": True,
        "material_stats": stats,
        "material_correlations": correlations,
        "repeat_combined_sha256": "6ccd67cef8a6951e40c73d3a7abf5c5d6891d9c04072ed06f9c085f61fcef200",
        "complete_wall_seconds_three_runs": [2.65, 2.72, 2.64],
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
