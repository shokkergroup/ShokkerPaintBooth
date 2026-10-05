# -*- coding: utf-8 -*-
"""Native-2048 Ammolite Skin I1 paint carrier study.

The carrier is a close-cropped ammonitic suture fabric: unequal crenulated
septa, attached side lobes, saddle clefts, short radial costae, siphuncle
points, chip windows, mineral seams and repair scars. Paint/A-B only until the
actual 2048 canvas survives review. No RNG/noise/shared composer/icon stamp.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_ammolite_skin"
WORK = 1024
NATIVE = 2048

COLORS_A = np.asarray((
    (16, 30, 34), (16, 77, 79), (20, 127, 113), (50, 180, 139),
    (120, 224, 155), (223, 244, 158), (255, 207, 105), (255, 143, 71),
    (242, 73, 83), (209, 43, 131), (151, 43, 170), (91, 55, 174),
    (47, 89, 180), (57, 159, 201), (157, 226, 223),
), np.float32)
COLORS_B = np.asarray((
    (26, 12, 49), (62, 20, 100), (111, 29, 146), (172, 39, 162),
    (225, 57, 132), (255, 92, 83), (255, 154, 47), (249, 220, 45),
    (166, 239, 61), (65, 219, 122), (26, 191, 184), (31, 137, 221),
    (73, 86, 231), (136, 68, 229), (234, 179, 244),
), np.float32)


def _mix(color: np.ndarray | tuple[int, int, int], factor: float,
         lift: tuple[int, int, int] = (3, 5, 8)) -> tuple[int, int, int]:
    return tuple(int(np.clip(lift[i] + float(color[i]) * factor, 0, 255)) for i in range(3))


def _optical_ground(angle_b: bool) -> np.ndarray:
    palette = COLORS_B if angle_b else COLORS_A
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # A coherent mineral-travel field gives adjacent chambers shared color
    # ancestry. It contains no sampled/random texture and does not define the
    # visible suture topology.
    phase = (0.0058 * xx + 0.0089 * yy
             + 1.26 * np.sin(0.0105 * xx + 0.0062 * yy)
             + 0.73 * np.sin(0.0170 * xx - 0.0110 * yy))
    phase += 5.5 if angle_b else 0.0
    wrapped = np.mod(phase, float(len(palette)))
    i0 = np.floor(wrapped).astype(np.int32)
    i1 = (i0 + 1) % len(palette)
    t = (wrapped - i0)[..., None]
    rgb = palette[i0] * (1.0 - t) + palette[i1] * t
    shade = (0.62 + 0.26 * (0.5 + 0.5 * np.sin(
        0.031 * xx + 0.027 * yy + 0.8 * np.sin(0.009 * yy))))[..., None]
    return np.clip(rgb * shade + np.asarray((4, 5, 8), np.float32), 0, 255).astype(np.uint8)


def _suture_points(index: int) -> np.ndarray:
    """One non-periodic crenulated septal trace, cropped beyond both edges."""
    base = -18.0 + index * 19.5
    ys = np.arange(-24, WORK + 28, 3, dtype=np.float32)
    # Low drift separates complete septa; faster terms create 8-32 px native
    # lobes/saddles rather than a smooth contour rail.
    x = (base
         + 7.0 * np.sin(0.010 * ys + 0.43 * index)
         + 4.4 * np.sin(0.037 * ys - 0.71 * index)
         + 2.7 * np.sin(0.103 * ys + 1.17 * index)
         + 1.6 * np.sin(0.229 * ys - 0.29 * index))
    # Unequal localized lobe excursions alter individual histories and keep
    # neighboring sutures from sharing a repeated waveform.
    for event in range(9):
        centre = -10 + ((index * 83 + event * 109 + event * event * 17) % 1060)
        width = 8.0 + ((index * 7 + event * 13) % 15)
        amp = 3.0 + ((index * 11 + event * 5) % 8)
        sign = -1.0 if (index + 2 * event) % 3 == 0 else 1.0
        x += sign * amp * np.exp(-((ys - centre) / width) ** 2)
    return np.stack((np.rint(x), np.rint(ys)), axis=1).astype(np.int32)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    palette = COLORS_B if angle_b else COLORS_A
    image = _optical_ground(angle_b)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "suture", "lobe", "saddle", "costa", "siphuncle", "chip",
        "mineral", "scar",
    )}
    suture_count = lobe_count = saddle_count = costa_count = 0
    siphuncle_count = chip_count = mineral_count = scar_count = 0

    sutures = [_suture_points(i) for i in range(55)]
    for i, pts in enumerate(sutures):
        # Unequal dark cleft and one-sided mineral lip expose septal thickness.
        cleft_width = 2 + (i % 3 == 0)
        cv2.polylines(image, [pts], False, (2, 4, 7), cleft_width, cv2.LINE_AA)
        cv2.polylines(masks["suture"], [pts], False,
                      80 + 21 * (i % 8), cleft_width, cv2.LINE_AA)
        lip_pts = pts.copy()
        lip_pts[:, 0] += 2 if i % 2 else -2
        lip_color = _mix(palette[(3 * i + (6 if angle_b else 0)) % len(palette)], 1.08)
        cv2.polylines(image, [lip_pts], False, lip_color, 1, cv2.LINE_AA)
        suture_count += 1

        # Attached lobes and saddle clefts have unequal orientation, span and
        # cadence. They are continuations of a real suture, never loose glyphs.
        for j in range(11):
            k = 10 + ((i * 31 + j * 27 + j * j * 5) % (len(pts) - 22))
            x, y = map(int, pts[k])
            side = -1 if (i + j) % 2 else 1
            reach = 4 + ((i * 5 + j * 7) % 10)
            rise = 3 + ((i * 11 + j * 3) % 7)
            lobe = np.asarray([
                (x, y - rise), (x + side * reach, y - rise // 2),
                (x + side * (reach + 2), y + rise // 3),
                (x + side * (reach - 2), y + rise), (x, y + rise // 2),
            ], np.int32)
            cv2.polylines(image, [lobe], False, (3, 5, 8), 2, cv2.LINE_AA)
            cv2.polylines(masks["lobe"], [lobe], False,
                          90 + 20 * ((i + j) % 8), 2, cv2.LINE_AA)
            if j % 3 == 1:
                cleft = np.asarray([(x, y), (x - side * 3, y + 3),
                                    (x + side * 1, y + 6)], np.int32)
                cv2.polylines(image, [cleft], False,
                              _mix(palette[(i + 5 * j) % len(palette)], 0.92), 1, cv2.LINE_AA)
                cv2.polylines(masks["saddle"], [cleft], False,
                              105 + 18 * ((i + j) % 8), 1, cv2.LINE_AA)
                saddle_count += 1
            lobe_count += 1

        # Short costae bridge only adjacent septa; none becomes a full-width
        # rib, radial fan or generic crosshatch.
        if i < len(sutures) - 1:
            neighbour = sutures[i + 1]
            for j in range(4):
                k = 18 + ((i * 47 + j * 73) % (len(pts) - 36))
                p0 = tuple(map(int, pts[k]))
                q = neighbour[min(k + ((i + j) % 5 - 2), len(neighbour) - 1)]
                p1 = tuple(map(int, q))
                if abs(p1[0] - p0[0]) <= 34 and abs(p1[1] - p0[1]) <= 16:
                    cv2.line(image, p0, p1,
                             _mix(palette[(i + 4 * j + 8) % len(palette)], 0.74), 1, cv2.LINE_AA)
                    cv2.line(masks["costa"], p0, p1,
                             95 + 22 * ((i + j) % 8), 1, cv2.LINE_AA)
                    costa_count += 1

        # Sparse siphuncle points sit inside a septal saddle and carry a tiny
        # asymmetric collar so they do not read as free dots.
        if i % 4 == 1:
            k = 26 + ((i * 61) % (len(pts) - 52))
            x, y = map(int, pts[k])
            centre = (x + (5 if i % 2 else -5), y)
            cv2.ellipse(image, centre, (3 + i % 3, 2), 17 * i, 0, 310,
                        _mix(palette[(i + 9) % len(palette)], 1.12), 2, cv2.LINE_AA)
            cv2.ellipse(masks["siphuncle"], centre, (3 + i % 3, 2), 17 * i, 0, 310,
                        115 + 17 * (i % 8), 2, cv2.LINE_AA)
            siphuncle_count += 1

    # Chip windows expose missing shell across several nearby septa. Their
    # edges are irregular and individually repaired; they are not a cell pack.
    for j in range(17):
        cx = 28 + ((j * 137 + j * j * 19) % 972)
        cy = 31 + ((j * 211 + j * j * 23) % 962)
        rx = 6 + (j * 7) % 10
        ry = 5 + (j * 11) % 9
        poly = np.asarray([
            (cx - rx, cy - 1), (cx - rx // 2, cy - ry),
            (cx + rx // 3, cy - ry + 1), (cx + rx, cy - 2),
            (cx + rx - 2, cy + ry), (cx - rx // 2, cy + ry + 1),
        ], np.int32)
        cv2.fillPoly(image, [poly], (3, 7, 11), cv2.LINE_AA)
        cv2.fillPoly(masks["chip"], [poly], 255, cv2.LINE_AA)
        # A stepped mineral repair occupies one edge only.
        repair = np.asarray([poly[1], poly[2], (cx + 2, cy - ry - 3),
                             (cx - 3, cy - ry - 2)], np.int32)
        cv2.fillConvexPoly(image, repair,
                           _mix(palette[(3 * j + 5) % len(palette)], 1.10), cv2.LINE_AA)
        cv2.fillConvexPoly(masks["scar"], repair,
                           110 + 18 * (j % 8), cv2.LINE_AA)
        chip_count += 1
        scar_count += 1

    # Three cropped mineral seams splice actual suture clefts, each made from
    # short crystalline steps rather than a single macro stroke.
    for seam in range(3):
        y0 = 170 + seam * 310
        x = -12 + seam * 43
        sign = 1 if seam != 1 else -1
        segment = 0
        while x < WORK + 15:
            span = 7 + ((seam * 5 + segment * 3) % 9)
            y1 = int(y0 + 29 * np.sin(0.017 * x + 1.2 * seam)
                     + 11 * np.sin(0.049 * x - seam))
            p0 = (x, y1)
            p1 = (x + span, y1 + sign * (2 + segment % 5))
            cv2.line(image, p0, p1,
                     _mix(palette[(seam * 5 + segment + 7) % len(palette)], 1.16), 2, cv2.LINE_AA)
            cv2.line(masks["mineral"], p0, p1,
                     105 + 19 * ((seam + segment) % 8), 2, cv2.LINE_AA)
            x += span + 1
            segment += 1
            mineral_count += 1

    coverage = {
        "crenulated_sutures": float(suture_count),
        "attached_lobes": float(lobe_count),
        "saddle_clefts": float(saddle_count),
        "short_costae": float(costa_count),
        "siphuncle_collars": float(siphuncle_count),
        "chip_windows": float(chip_count),
        "mineral_steps": float(mineral_count),
        "repair_scars": float(scar_count),
    }
    return image, coverage, masks


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "ammolite_suture_i1"
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
        "schema": "spb-wilds-ammolite-suture-i1/1",
        "status": "REJECT-VERTICAL-WAVY-RAILS-WITH-GLYPH-DECORATION-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "close-cropped crenulated ammonitic suture fabric",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit septal raster; no RNG/noise/icon stamp/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
