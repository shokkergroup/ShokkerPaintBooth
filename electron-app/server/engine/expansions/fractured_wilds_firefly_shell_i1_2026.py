# -*- coding: utf-8 -*-
"""Isolated native-2048 Firefly Shell articulated-lantern study.

SPB-WILDS-FIREFLY-I1 / SPB-105, 2026-08-24. One close-cropped dark shell uses
unequal joint lips, luminous windows, spiracle slits, hinge ribs, Morse bars,
bristle hooks, scutellum wedges and terminal breaks. Local anatomy targets
8-32 px at native 2048.

Paint/A-B review only. No RNG, sampled noise, regular circuit grid, repeated
segment stamp, shared Wilds composer or material maps. Fail closed.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_firefly_shell"
WORK = 1024
NATIVE = 2048
PI = float(np.pi)

PALETTE_A = [
    (32, 246, 126), (145, 255, 52), (242, 236, 48), (255, 169, 35),
    (255, 79, 57), (224, 51, 154), (128, 61, 225), (37, 164, 230),
]
PALETTE_B = [
    (38, 211, 239), (62, 125, 242), (113, 73, 233), (198, 56, 218),
    (246, 58, 149), (255, 80, 73), (255, 166, 38), (116, 239, 85),
]


def _curve(points: list[tuple[float, float]], samples: int = 180) -> np.ndarray:
    p = np.asarray(points, np.float32)
    t = np.linspace(0.0, 1.0, samples, dtype=np.float32)[:, None]
    q = ((1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1]
         + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3])
    return np.rint(q).astype(np.int32)


def _base(angle_b: bool) -> np.ndarray:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x, y = xx / WORK, yy / WORK
    sheen = 0.5 + 0.5 * np.sin(3.7 * x + 2.9 * y + 0.55 * np.sin(5.1 * x - 3.3 * y))
    ridge = 0.5 + 0.5 * np.sin(9.0 * x - 6.0 * y)
    if angle_b:
        rgb = np.stack((11 + 12 * sheen, 8 + 8 * ridge, 22 + 20 * sheen), axis=2)
    else:
        rgb = np.stack((6 + 5 * ridge, 17 + 16 * sheen, 13 + 10 * ridge), axis=2)
    return np.clip(rgb, 0, 255).astype(np.uint8)


JOINTS = [
    [(-80, 130), (245, 45), (590, 180), (1100, 95)],
    [(-70, 390), (250, 245), (620, 430), (1090, 330)],
    [(-90, 690), (180, 510), (640, 715), (1100, 610)],
    [(-60, 980), (260, 765), (665, 940), (1085, 805)],
    [(135, -70), (250, 245), (150, 520), (295, 1080)],
    [(650, -80), (545, 245), (800, 500), (675, 1090)],
    [(1085, 185), (820, 310), (950, 620), (805, 1065)],
]


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, float]]:
    palette = PALETTE_B if angle_b else PALETTE_A
    image = _base(angle_b)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "joint", "window", "spiracle", "hinge", "morse", "bristle",
        "wedge", "terminal")}
    paths = []
    for i, controls in enumerate(JOINTS):
        pts = _curve(controls)
        paths.append(pts)
        width = 7 + (5 * i) % 9
        cv2.polylines(image, [pts], False, (3, 5, 7), width + 5, cv2.LINE_AA)
        cv2.polylines(image, [pts], False, palette[(i + 6) % len(palette)], 2, cv2.LINE_AA)
        cv2.polylines(masks["joint"], [pts], False, 85 + 22 * (i % 8), width + 3, cv2.LINE_AA)

    window_count = spiracle_count = morse_count = 0
    # Luminous apertures attach to different joint histories. Five geometry
    # roles and varying size/orientation prevent a repeated segment stamp.
    for i in range(74):
        x = int(30 + ((i * 0.61803398875) % 1.0) * 964)
        y = int(28 + ((i * 0.41421356237 + 0.17 * np.sin(i)) % 1.0) * 968)
        role = (7 * i + i // 3) % 5
        ax = 4 + (3 * i) % 10
        ay = 5 + (7 * i) % 11
        angle = int((31 * i + 17 * np.sin(i * 0.7)) % 180)
        color = palette[(i + role) % len(palette)]
        if role == 0:
            cv2.ellipse(image, (x, y), (ax, ay), angle, 0, 360, color, -1, cv2.LINE_AA)
            cv2.ellipse(masks["window"], (x, y), (ax, ay), angle, 0, 360,
                        90 + 20 * (i % 8), -1, cv2.LINE_AA)
        elif role == 1:
            pts = cv2.boxPoints(((x, y), (2 * ax, 2 * ay), angle)).astype(np.int32)
            pts[0] += (2, -1)
            cv2.fillConvexPoly(image, pts, color, cv2.LINE_AA)
            cv2.fillConvexPoly(masks["window"], pts, 95 + 19 * (i % 8), cv2.LINE_AA)
        elif role == 2:
            tri = np.asarray([(x - ax, y + ay), (x + ax, y + ay // 2),
                              (x + ax // 3, y - ay)], np.int32)
            cv2.fillConvexPoly(image, tri, color, cv2.LINE_AA)
            cv2.fillConvexPoly(masks["window"], tri, 100 + 18 * (i % 8), cv2.LINE_AA)
        elif role == 3:
            cv2.ellipse(image, (x, y), (ax + 2, ay), angle, 25, 325, color, 4, cv2.LINE_AA)
            cv2.ellipse(masks["window"], (x, y), (ax + 2, ay), angle, 25, 325,
                        105 + 17 * (i % 8), 4, cv2.LINE_AA)
        else:
            cv2.circle(image, (x - ax // 2, y), max(3, ax // 2), color, -1, cv2.LINE_AA)
            cv2.circle(image, (x + ax // 2, y), max(2, ay // 3), palette[(i + 3) % 8], -1, cv2.LINE_AA)
            cv2.line(masks["window"], (x - ax, y), (x + ax, y), 110 + 16 * (i % 8), 5, cv2.LINE_AA)
        window_count += 1

        if i % 4 == 0:
            # Paired spiracle slits sit beside, not inside, their window.
            dx, dy = int(1.4 * ax), int(1.2 * ay)
            for sign in (-1, 1):
                p0 = (x + dx, y + sign * dy)
                p1 = (x + dx + 5 + i % 4, y + sign * dy + sign * 3)
                cv2.line(image, p0, p1, palette[(i + 5) % 8], 3, cv2.LINE_AA)
                cv2.line(masks["spiracle"], p0, p1, 100 + 22 * (i % 7), 3, cv2.LINE_AA)
            spiracle_count += 1

        if i % 6 == 1:
            # Unequal Morse bars encode each plate window differently.
            for bar in range(2 + i % 4):
                length = 4 + (i + 3 * bar) % 8
                yb = y + ay + 5 + 4 * bar
                cv2.line(image, (x - length, yb), (x + length, yb),
                         palette[(i + bar + 2) % 8], 2, cv2.LINE_AA)
                cv2.line(masks["morse"], (x - length, yb), (x + length, yb),
                         90 + 25 * (bar % 7), 2, cv2.LINE_AA)
            morse_count += 1

    # Short hinge ribs, hooks and wedges attach directly to selected joint lips.
    for j, path in enumerate(paths):
        for k, t in enumerate((0.17, 0.36, 0.58, 0.79)):
            idx = int(t * (len(path) - 2))
            p = path[idx].astype(np.float32)
            tangent = path[idx + 1].astype(np.float32) - path[idx].astype(np.float32)
            normal = np.asarray([-tangent[1], tangent[0]], np.float32)
            normal /= max(float(np.linalg.norm(normal)), 1e-6)
            length = 6 + (j * 3 + k * 5) % 10
            q = p + normal * length * (-1 if (j + k) % 2 else 1)
            p0, p1 = tuple(np.rint(p).astype(int)), tuple(np.rint(q).astype(int))
            cv2.line(image, p0, p1, palette[(j + k + 1) % 8], 3, cv2.LINE_AA)
            cv2.line(masks["hinge"], p0, p1, 95 + 20 * ((j + k) % 8), 3, cv2.LINE_AA)
            if (j + k) % 3 == 0:
                tri = np.asarray([p0, p1, (p1[0] + 5, p1[1] + 3)], np.int32)
                cv2.fillConvexPoly(image, tri, palette[(j + k + 4) % 8], cv2.LINE_AA)
                cv2.fillConvexPoly(masks["wedge"], tri, 110 + 17 * ((j + k) % 8), cv2.LINE_AA)
            else:
                cv2.ellipse(image, p1, (5, 3), 25 * (j + k), 180, 355,
                            palette[(j + k + 6) % 8], 2, cv2.LINE_AA)
                cv2.ellipse(masks["bristle"], p1, (5, 3), 25 * (j + k), 180, 355,
                            100 + 18 * ((j + k) % 8), 2, cv2.LINE_AA)

    # Terminal breaks are derived only where joint histories meet the canvas edge.
    border = np.zeros((WORK, WORK), np.uint8)
    border[:9] = border[-9:] = border[:, :9] = border[:, -9:] = 255
    terminal = cv2.bitwise_and(masks["joint"], border)
    masks["terminal"] = terminal
    image[terminal > 0] = palette[4 if not angle_b else 7]

    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    coverage.update({"windows": float(window_count), "spiracle_pairs": float(spiracle_count),
                     "morse_sequences": float(morse_count)})
    return image, masks, coverage


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "firefly_shell_i1"
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
        "schema": "spb-wilds-firefly-shell-i1/1",
        "status": "REJECT-SPARSE-GLYPH-SCATTER-IN-CIRCUIT-PANELS-DO-NOT-WIRE",
        "owner_accepted": False, "production_wired": False,
        "finish_id": ID, "native_size": [2048, 2048],
        "topology": "close-cropped articulated lantern-shell code",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit shell anatomy; no RNG/noise/grid/segment stamps",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
