# -*- coding: utf-8 -*-
"""Native-2048 Feathered Wing I1 paint-only pennaceous-vane study.

FROZEN REJECT (SPB-105 tick 2026-08-25): the 22-packet native contact was
sparse; the owner-doctrine 3x density correction proved the carrier itself was
wrong. Actual 2048 became a dark rail network decorated with repeated tiny
triangular barbs. No spec maps were made.

SPB-105 / 2026-08-25 native rebuild tick. Actual 2048 controls. The carrier is
an overlapping close-cropped vane mat built from fine tapered barb packets,
not long lines, rows, a fan icon or a short-stroke cloud. Rachides only bind
their own packets; hooklet bridges, downy roots, scalloped overlap lips,
missing-barb wakes and split tips have separate attachment rules. All visible
barb primitives are 8-32 px native. Paint/A-B only until native eye.

No RNG, sampled noise, grain, cells, stamp atlas, shared composer or legacy
renderer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fc_feathered_wing"
WORK = 1024
NATIVE = 2048

VANE_A = np.asarray([
    (4, 3, 12), (18, 6, 39), (48, 8, 70), (84, 11, 96),
    (123, 17, 113), (163, 28, 124), (199, 44, 127), (228, 65, 124),
    (247, 93, 117), (255, 130, 109), (255, 170, 105), (248, 209, 116),
    (211, 233, 143), (145, 225, 171), (79, 186, 181),
], np.float32)
VANE_B = np.asarray([
    (2, 7, 14), (2, 23, 39), (2, 47, 62), (3, 75, 78),
    (5, 107, 89), (10, 140, 96), (21, 173, 102), (43, 202, 110),
    (79, 225, 124), (127, 239, 145), (181, 244, 174), (229, 236, 207),
    (255, 199, 227), (241, 139, 229), (172, 84, 208),
], np.float32)


def _palette_color(value: float, stops: np.ndarray) -> tuple[int, int, int]:
    scaled = (value % 1.0) * len(stops)
    lo = int(np.floor(scaled))
    mix = scaled - lo
    rgb = stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix
    return tuple(int(v) for v in np.clip(rgb, 0, 255))


def _schedule(index: int, modulus: int, multiplier: int, offset: int = 0) -> int:
    return (index * multiplier + index * index * 13 + offset) % modulus


def _cubic(ctrl: np.ndarray, n: int = 120) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
    q = 1.0 - t
    return q ** 3 * ctrl[0] + 3.0 * q ** 2 * t * ctrl[1] + 3.0 * q * t ** 2 * ctrl[2] + t ** 3 * ctrl[3]


def _packet_curve(index: int) -> np.ndarray:
    # Roots begin outside or close to crop boundaries; overlapping packets read
    # as one material rather than twenty-two feather specimens.
    edge = index % 4
    lane = (index // 4) % 6
    generation = index // 24
    offset = generation * 47.0
    if edge == 0:
        p0 = np.asarray((-34.0, 24.0 + lane * 174.0 + offset), np.float32)
        p3 = np.asarray((305.0 + _schedule(index, 239, 41), 97.0 + lane * 154.0 + offset), np.float32)
    elif edge == 1:
        p0 = np.asarray((WORK + 34.0, 45.0 + lane * 171.0 + offset), np.float32)
        p3 = np.asarray((714.0 - _schedule(index, 227, 37), 119.0 + lane * 151.0 + offset), np.float32)
    elif edge == 2:
        p0 = np.asarray((39.0 + lane * 171.0 + offset, -34.0), np.float32)
        p3 = np.asarray((107.0 + lane * 151.0 + offset, 328.0 + _schedule(index, 211, 43)), np.float32)
    else:
        p0 = np.asarray((51.0 + lane * 169.0 + offset, WORK + 34.0), np.float32)
        p3 = np.asarray((139.0 + lane * 148.0 + offset, 711.0 - _schedule(index, 213, 47)), np.float32)
    bend = np.asarray(((-1) ** index * (57 + _schedule(index, 71, 29)),
                       (-1) ** (index // 2) * (63 + _schedule(index, 79, 31))), np.float32)
    p1 = p0 * 0.68 + p3 * 0.32 + bend
    p2 = p0 * 0.31 + p3 * 0.69 - bend * 0.57
    pts = _cubic(np.asarray((p0, p1, p2, p3), np.float32))
    keep = ((pts[:, 0] >= -24) & (pts[:, 0] <= WORK + 24)
            & (pts[:, 1] >= -24) & (pts[:, 1] <= WORK + 24))
    return pts[keep]


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Substrate is quiet and continuous; anatomy supplies the actual pattern.
    substrate = (
        0.17 + 0.06 * np.sin((x + 0.63 * y) / 143.0)
        + 0.04 * np.cos((1.17 * x - y) / 191.0)
    )
    image = np.zeros((WORK, WORK, 3), np.uint8)
    base = (10, 5, 19) if not angle_b else (3, 15, 20)
    for channel, value in enumerate(base):
        image[..., channel] = np.clip(value * (0.92 + substrate), 0, 255).astype(np.uint8)

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "rachis", "barb", "hooklet", "down_root", "overlap_lip",
        "missing_wake", "split_tip",
    )}
    stops = VANE_B if angle_b else VANE_A
    # Owner density correction after first 2048 contact: 22 sparse packets let
    # the dark rachis network dominate. Three unequal generations (66 packets)
    # keep every barb fine while making attached vane anatomy the surface.
    for packet in range(66):
        pts = _packet_curve(packet)
        if len(pts) < 24:
            continue
        # Rachis is dark and subordinate. It binds, rather than dominates, the
        # brighter filled barb anatomy.
        rachis = np.rint(pts).astype(np.int32)
        cv2.polylines(masks["rachis"], [rachis], False, 76 + 21 * (packet % 8), 2 + packet % 2, cv2.LINE_AA)
        cv2.polylines(image, [rachis], False,
                      (24, 10, 33) if not angle_b else (6, 34, 37), 2 + packet % 2, cv2.LINE_AA)

        previous_tips: dict[int, np.ndarray] = {}
        count = 43 + packet % 18
        for barb_index in range(count):
            k = 3 + int((len(pts) - 8) * (barb_index + 0.55) / count)
            if k >= len(pts) - 3:
                continue
            # Causal missing-barb wakes: absence, not a bright repeated glyph.
            omitted = ((packet * 17 + barb_index * 29 + barb_index * barb_index) % 37) in (0, 1, 9)
            anchor = pts[k]
            tangent = pts[k + 2] - pts[k - 2]
            tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            side = -1 if (barb_index + packet // 3) % 2 else 1
            # 8-32 px native length, 6-14 px native filled width.
            length = 6.0 + _schedule(packet * 53 + barb_index, 11, 31)
            width = 3.2 + _schedule(packet * 31 + barb_index, 6, 23) * 0.55
            lean = -2.0 + _schedule(packet * 19 + barb_index, 9, 17) * 0.5
            tip = anchor + normal * side * length + tangent * lean
            if omitted:
                wake = np.rint(np.asarray([
                    anchor - tangent * 2.0,
                    anchor + normal * side * (length * 0.48),
                    anchor + tangent * 2.0,
                ])).astype(np.int32)
                cv2.polylines(masks["missing_wake"], [wake], False,
                              78 + 22 * ((packet + barb_index) % 8), 2, cv2.LINE_AA)
                cv2.polylines(image, [wake], False, (2, 2, 5), 2, cv2.LINE_AA)
                continue
            poly = np.rint(np.asarray([
                anchor - tangent * width,
                anchor + tangent * width,
                tip + tangent * (width * 0.32),
                tip - tangent * (width * 0.32),
            ])).astype(np.int32)
            tier = 74 + 22 * ((packet * 3 + barb_index) % 8)
            cv2.fillConvexPoly(masks["barb"], poly, tier, cv2.LINE_AA)
            value = packet * 0.137 + barb_index * 0.071 + (0.41 if angle_b else 0.0)
            color = _palette_color(value, stops)
            cv2.fillConvexPoly(image, poly, tuple(int(v * 0.76) for v in color), cv2.LINE_AA)
            # Bright shoulder and dark vane-side bevel make each filled barb a
            # three-face packet rather than a repeated flat stroke.
            shoulder = np.rint(np.asarray([anchor - tangent * width * 0.72,
                                           tip - tangent * width * 0.18])).astype(np.int32)
            cv2.polylines(image, [shoulder], False, color, 1, cv2.LINE_AA)

            # Split tips affect only selected mature barbs and vary handedness.
            if (packet * 11 + barb_index * 7) % 17 == 0:
                split = np.rint(np.asarray([
                    tip,
                    tip + normal * side * (2 + barb_index % 3) + tangent * 2,
                    tip + normal * side * (3 + packet % 4) - tangent * 2,
                ])).astype(np.int32)
                cv2.polylines(masks["split_tip"], [split], False, tier, 2, cv2.LINE_AA)
                cv2.polylines(image, [split], False, color, 1, cv2.LINE_AA)

            # Hooklet bridges join adjacent barbs on the same vane side. They
            # are physical connectors, not an independent line cloud.
            if side in previous_tips and (packet + barb_index) % 3 != 0:
                prev = previous_tips[side]
                bridge = np.rint(np.asarray([
                    prev * 0.42 + tip * 0.58,
                    prev * 0.30 + tip * 0.70 + tangent * (2 + barb_index % 3),
                ])).astype(np.int32)
                cv2.polylines(masks["hooklet"], [bridge], False, tier, 2, cv2.LINE_AA)
                cv2.polylines(image, [bridge], False,
                              _palette_color(value + 0.09, stops), 1, cv2.LINE_AA)
            previous_tips[side] = tip

        # Downy root clusters use several short unequal curls at packet roots.
        root = pts[min(5, len(pts) - 1)]
        for curl in range(4 + packet % 4):
            theta = packet * 0.71 + curl * 1.43
            points = []
            for step in range(6):
                radius = 1.5 + step * (0.65 + 0.08 * curl)
                angle = theta + step * (0.41 + 0.03 * packet)
                points.append(root + np.asarray((np.cos(angle), np.sin(angle))) * radius)
            curl_pts = np.rint(points).astype(np.int32)
            tier = 78 + 22 * ((packet + curl) % 8)
            cv2.polylines(masks["down_root"], [curl_pts], False, tier, 2, cv2.LINE_AA)
            cv2.polylines(image, [curl_pts], False,
                          _palette_color(packet * 0.13 + curl * 0.09 + (0.41 if angle_b else 0), stops),
                          1, cv2.LINE_AA)

        # A short scalloped overlap lip closes the distal packet edge.
        lip_start = max(5, len(pts) - 22 - packet % 11)
        lip = np.rint(pts[lip_start::2]).astype(np.int32)
        if len(lip) >= 4:
            tier = 80 + 21 * (packet % 8)
            cv2.polylines(masks["overlap_lip"], [lip], False, tier, 3, cv2.LINE_AA)
            cv2.polylines(image, [lip], False,
                          _palette_color(packet * 0.137 + 0.27 + (0.41 if angle_b else 0), stops),
                          2, cv2.LINE_AA)

    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    return image, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "feathered_wing_vane_i1"
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
        "schema": "spb-wilds-feathered-wing-vane-i1/1",
        "status": "REJECT-DECORATED-RACHIS-RAIL-NETWORK-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "overlapping close-cropped pennaceous vane mechanics",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit attached vane anatomy; no RNG/noise/grain/cells/stamps/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
