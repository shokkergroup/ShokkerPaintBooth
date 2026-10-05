# -*- coding: utf-8 -*-
"""Native-2048 Jewel Scarab I1 paint-only close-cropped elytra study.

FROZEN REJECT (SPB-105 tick 2026-08-25): actual 2048 review is a schematic
bilateral rib/circuit diagram. Long pale costae and the median seam dominate;
punctures, files, phase slips and schiller packets are decoration. No spec maps
were made.

SPB-105 / 2026-08-25 native rebuild tick. The actual 2048 canvas controls.
This is not a beetle icon, stripe fill or repeated stamp field: alternating
suture zones emit unequal costae that split, stop and shear; punctures belong
to particular rib orders; scutellum wedges, rim teeth, stridulatory files,
phase-slip seams and schiller runs are attached mechanical histories. Visible
feature widths are 8-32 px native. Paint/A-B only until native review.

No RNG, sampled noise, grain, cells, stamp atlas, shared composer or legacy
Wilds renderer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_jewel_scarab"
WORK = 1024
NATIVE = 2048

JEWEL_A = np.asarray([
    (2, 5, 12), (3, 20, 38), (3, 46, 66), (3, 79, 84),
    (5, 116, 95), (10, 153, 98), (26, 188, 93), (59, 216, 85),
    (110, 235, 79), (171, 241, 85), (226, 231, 103), (255, 197, 115),
    (255, 143, 121), (229, 83, 137), (148, 47, 151),
], np.float32)
JEWEL_B = np.asarray([
    (8, 3, 17), (31, 5, 48), (65, 7, 80), (104, 10, 106),
    (148, 17, 124), (190, 29, 132), (226, 49, 130), (249, 78, 120),
    (255, 117, 111), (255, 164, 108), (251, 210, 120), (210, 237, 151),
    (139, 232, 180), (71, 197, 190), (42, 126, 180),
], np.float32)


def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix


def _cubic(ctrl: np.ndarray, n: int = 180) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
    q = 1.0 - t
    return q ** 3 * ctrl[0] + 3.0 * q ** 2 * t * ctrl[1] + 3.0 * q * t ** 2 * ctrl[2] + t ** 3 * ctrl[3]


def _schedule(index: int, modulus: int, multiplier: int, offset: int = 0) -> int:
    return (index * multiplier + index * index * 11 + offset) % modulus


def _curve_points(index: int, side: int) -> np.ndarray:
    root_y = -36 + index * 19.1 + 6.0 * np.sin(index * 1.71)
    root_x = 508 + side * (8 + index % 9)
    end_y = root_y + (-46 + _schedule(index, 93, 37))
    end_x = -34 if side < 0 else WORK + 34
    ctrl = np.asarray([
        (root_x, root_y),
        (root_x + side * (112 + _schedule(index, 94, 41)), root_y - 54 + _schedule(index, 109, 31)),
        (root_x + side * (323 + _schedule(index, 133, 29)), end_y + 62 - _schedule(index, 127, 43)),
        (end_x, end_y),
    ], np.float32)
    pts = np.rint(_cubic(ctrl)).astype(np.int32)
    keep = ((pts[:, 0] >= -12) & (pts[:, 0] <= WORK + 12)
            & (pts[:, 1] >= -12) & (pts[:, 1] <= WORK + 12))
    return pts[keep]


def _segments(points: np.ndarray, index: int, side: int) -> list[np.ndarray]:
    if len(points) < 16:
        return []
    keep = np.ones(len(points), dtype=bool)
    for event in range(2 + index % 4):
        center = 10 + _schedule(index + event * 17 + (side > 0), max(11, len(points) - 20), 31, event * 47)
        half = 2 + _schedule(index + event * 7, 5, 23)
        keep[max(0, center - half):min(len(points), center + half)] = False
    starts = np.flatnonzero(keep & np.r_[True, ~keep[:-1]])
    ends = np.flatnonzero(keep & np.r_[~keep[1:], True]) + 1
    return [points[a:b] for a, b in zip(starts, ends) if b - a >= 5]


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    center = 510.0 + 17.0 * np.sin(y / 83.0) + 8.0 * np.sin(y / 31.0)
    side_distance = np.abs(x - center)
    # Substrate color crosses the suture instead of making two giant halves.
    chroma = np.mod(
        0.00053 * x + 0.00039 * y
        + 0.13 * np.sin((x + 0.83 * y) / 151.0)
        + 0.08 * np.sin((1.27 * x - y) / 97.0)
        + 0.06 * np.cos(side_distance / 61.0),
        1.0,
    )
    if angle_b:
        chroma = np.mod(chroma + 0.41 + 0.10 * np.sin((x - 1.4 * y) / 79.0), 1.0)
        stops = JEWEL_B
    else:
        stops = JEWEL_A
    image = _palette(chroma, stops)
    light = 0.24 + 0.15 * np.cos(side_distance / 113.0) + 0.09 * np.sin((x + y) / 137.0)
    image = np.clip(image * light[..., None], 0, 255).astype(np.uint8)

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "suture", "costa", "puncture", "phase_slip", "scutellum",
        "file", "rim_tooth", "schiller",
    )}

    # The close-cropped median seam changes width, side and interruption state.
    seam_pts = np.rint(np.stack((center[:, 0], y[:, 0]), axis=1)).astype(np.int32)
    for zone in range(16):
        a = zone * 64 + _schedule(zone, 17, 13)
        b = min(WORK, a + 39 + _schedule(zone, 24, 19))
        piece = seam_pts[a:b]
        if len(piece) < 3:
            continue
        tier = 72 + 22 * (zone % 8)
        width = 3 + zone % 5
        cv2.polylines(masks["suture"], [piece], False, tier, width, cv2.LINE_AA)
        cv2.polylines(image, [piece], False, (2, 2, 5), width + 3, cv2.LINE_AA)
        cv2.polylines(image, [piece + np.asarray(((-1) ** zone * 3, 0), np.int32)], False,
                      (235, 224, 127) if not angle_b else (101, 228, 184), 2, cv2.LINE_AA)

    costae: list[tuple[int, int, np.ndarray]] = []
    for i in range(56):
        for side in (-1, 1):
            pts = _curve_points(i, side)
            pieces = _segments(pts, i, side)
            if not pieces:
                continue
            costae.append((i, side, pts))
            tier = 75 + 21 * ((i + (side > 0) * 3) % 8)
            width = 2 + (i + (side > 0)) % 4
            shifted = [piece + np.asarray((0, 2 + i % 3), np.int32) for piece in pieces]
            cv2.polylines(masks["costa"], pieces, False, tier, width, cv2.LINE_AA)
            cv2.polylines(image, shifted, False, (2, 4, 7), width + 3, cv2.LINE_AA)
            lip = (228, 225, 107) if not angle_b else (84, 227, 176)
            cv2.polylines(image, pieces, False, lip, width, cv2.LINE_AA)

            # Schiller lives on short sections of selected costa faces; angle B
            # activates a disjoint section rather than recolouring one mask.
            for p_index, piece in enumerate(pieces):
                if len(piece) < 10 or (i + p_index + int(angle_b) * 2) % 4 == 0:
                    continue
                start = _schedule(i + p_index * 13 + (side > 0) * 7, max(1, len(piece) - 8), 17)
                run = 4 + _schedule(i + p_index * 19, 10, 29)
                glint = piece[start:min(len(piece), start + run)]
                if len(glint) >= 3:
                    cv2.polylines(masks["schiller"], [glint], False, 92 + 20 * (i % 8), 2, cv2.LINE_AA)
                    cv2.polylines(image, [glint], False,
                                  (255, 151, 181) if not angle_b else (234, 154, 232), 1, cv2.LINE_AA)

            # Punctures belong to every third costa and follow its tangent.
            if i % 3 == 1 and len(pts) > 25:
                for j in range(3 + i % 4):
                    k = 8 + _schedule(i + j * 23 + (side > 0) * 5, len(pts) - 16, 41)
                    px, py = (int(v) for v in pts[k])
                    q = pts[min(k + 3, len(pts) - 1)] - pts[max(0, k - 3)]
                    angle = int(np.degrees(np.arctan2(float(q[1]), float(q[0]))))
                    axes = (2 + (i + j) % 5, 1 + (i * 2 + j) % 3)
                    cv2.ellipse(masks["puncture"], (px, py), axes, angle, 0, 360,
                                82 + 23 * ((i + j) % 8), -1, cv2.LINE_AA)
                    cv2.ellipse(image, (px, py), axes, angle, 0, 360, (1, 2, 4), -1, cv2.LINE_AA)
                    cv2.ellipse(image, (px - side * 2, py - 1), axes, angle, 205, 315,
                                (244, 197, 107) if not angle_b else (103, 219, 203), 1, cv2.LINE_AA)

    # Phase slips cross only selected costa orders and terminate with wedges.
    for event in range(19):
        cy = 37 + _schedule(event, 948, 53)
        cx = 89 + _schedule(event, 846, 71)
        direction = -1 if event % 2 else 1
        pts = np.asarray([
            (cx - 11, cy - direction * 7), (cx - 3, cy + direction * 2),
            (cx + 5, cy - direction * 4), (cx + 13, cy + direction * 7),
        ], np.int32)
        tier = 77 + 22 * (event % 8)
        cv2.polylines(masks["phase_slip"], [pts], False, tier, 3, cv2.LINE_AA)
        cv2.polylines(image, [pts], False,
                      (245, 91, 136) if not angle_b else (165, 91, 225), 2, cv2.LINE_AA)
        wedge = np.asarray([(cx + 13, cy + direction * 7),
                            (cx + 20, cy + direction * 3),
                            (cx + 17, cy + direction * 13)], np.int32)
        cv2.fillConvexPoly(masks["scutellum"], wedge, tier, cv2.LINE_AA)
        cv2.fillConvexPoly(image, wedge,
                           (248, 210, 119) if not angle_b else (112, 227, 200), cv2.LINE_AA)

    # Six localized stridulatory files: short transverse teeth tied to one rib,
    # never a global hatch or independent line field.
    for band in range(6):
        cx = 138 + _schedule(band, 748, 127)
        cy = 96 + _schedule(band, 822, 163)
        theta = -0.8 + 0.31 * band
        along = np.asarray((np.cos(theta), np.sin(theta)), np.float32)
        normal = np.asarray((-along[1], along[0]), np.float32)
        for tooth in range(5 + band % 4):
            anchor = np.asarray((cx, cy), np.float32) + along * (tooth * 6 - 17)
            half = 3 + (band + tooth) % 4
            pts = np.rint(np.asarray([anchor - normal * half, anchor + normal * half])).astype(np.int32)
            cv2.polylines(masks["file"], [pts], False, 78 + 22 * ((band + tooth) % 8), 2, cv2.LINE_AA)
            cv2.polylines(image, [pts], False,
                          (242, 181, 94) if not angle_b else (88, 213, 189), 1, cv2.LINE_AA)

    # Edge compression teeth enter from off-canvas rather than outlining a
    # beetle silhouette. Their length/angle/spacing schedule never repeats.
    for side in (-1, 1):
        edge_x = 2 if side < 0 else WORK - 3
        for tooth in range(31):
            cy = 14 + tooth * 33 + _schedule(tooth + (side > 0) * 9, 15, 17)
            length = 5 + _schedule(tooth + (side > 0) * 5, 11, 23)
            tilt = -4 + _schedule(tooth, 9, 19)
            pts = np.asarray([(edge_x, cy), (edge_x - side * length, cy + tilt)], np.int32)
            tier = 74 + 22 * ((tooth + (side > 0) * 3) % 8)
            cv2.polylines(masks["rim_tooth"], [pts], False, tier, 3, cv2.LINE_AA)
            cv2.polylines(image, [pts], False,
                          (236, 218, 114) if not angle_b else (99, 223, 187), 2, cv2.LINE_AA)

    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    return image, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "jewel_scarab_elytra_i1"
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
        "schema": "spb-wilds-jewel-scarab-elytra-i1/1",
        "status": "REJECT-BILATERAL-RIB-CIRCUIT-DIAGRAM-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "close-cropped asymmetric bilateral elytra mechanics",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit unequal elytral histories; no RNG/noise/grain/cells/stamps/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
