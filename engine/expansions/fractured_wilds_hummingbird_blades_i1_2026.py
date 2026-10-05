# -*- coding: utf-8 -*-
"""Native-2048 Hummingbird Gorget I1 anatomical paint study.

Reference anatomy: Giraldo, Parra & Stavenga (2018), Anna's hummingbird gorget
barbules. Folded upper laminae behave like Venetian blinds, side laminae carry
terminal hooks, surfaces contain spindle mosaics and internal multilayers
produce strongly angle-dependent specular colour. Paint/A-B only until native
review. No RNG/noise/stamp atlas/shared composer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_hummingbird_gorget"
WORK = 1024
NATIVE = 2048

FLASH_A = (
    (35, 7, 22), (76, 10, 45), (122, 14, 70), (171, 22, 91),
    (219, 40, 106), (250, 70, 112), (255, 112, 123), (255, 161, 145),
    (250, 210, 174), (221, 230, 195), (149, 218, 203), (79, 180, 198),
    (61, 118, 187), (84, 70, 169), (139, 47, 160),
)
FLASH_B = (
    (5, 10, 22), (6, 27, 48), (7, 53, 81), (7, 89, 109),
    (10, 132, 128), (24, 173, 145), (58, 208, 161), (113, 229, 178),
    (181, 239, 195), (221, 232, 204), (203, 198, 220), (162, 151, 220),
    (112, 103, 207), (72, 70, 177), (42, 42, 126),
)


def _mix(color: tuple[int, int, int], factor: float,
         lift: tuple[int, int, int] = (2, 2, 4)) -> tuple[int, int, int]:
    return tuple(int(np.clip(lift[i] + color[i] * factor, 0, 255)) for i in range(3))


def _bezier(ctrl: tuple[tuple[float, float], ...], n: int = 420) -> np.ndarray:
    p = np.asarray(ctrl, np.float32)
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
    omt = 1.0 - t
    pts = (omt ** 3 * p[0] + 3.0 * omt ** 2 * t * p[1]
           + 3.0 * omt * t ** 2 * p[2] + t ** 3 * p[3])
    return pts


FRONTS = (
    ((-90, 70), (210, -15), (620, 60), (1110, 245)),
    ((-100, 145), (155, 30), (625, 145), (1115, 335)),
    ((-80, 225), (250, 70), (670, 240), (1100, 410)),
    ((-105, 315), (170, 180), (570, 320), (1095, 500)),
    ((-85, 405), (240, 225), (720, 425), (1110, 570)),
    ((-110, 500), (175, 340), (575, 505), (1100, 665)),
    ((-90, 590), (280, 385), (735, 590), (1110, 735)),
    ((-115, 685), (145, 535), (565, 690), (1095, 830)),
    ((-90, 775), (245, 600), (710, 785), (1110, 905)),
    ((-120, 870), (185, 700), (605, 870), (1095, 980)),
    ((-80, 965), (280, 780), (745, 940), (1105, 1045)),
    ((70, -80), (10, 250), (155, 655), (350, 1110)),
    ((420, -90), (300, 245), (410, 675), (600, 1110)),
    ((760, -80), (635, 235), (715, 655), (850, 1100)),
    ((1060, -60), (920, 280), (930, 665), (1050, 1080)),
)


def _blade(image: np.ndarray, masks: dict[str, np.ndarray], root: np.ndarray,
           tangent: np.ndarray, front: int, blade: int, angle_b: bool) -> None:
    palette = FLASH_B if angle_b else FLASH_A
    tangent = tangent / max(float(np.linalg.norm(tangent)), 1e-6)
    normal = np.asarray((-tangent[1], tangent[0]), np.float32)
    side = -1.0 if (front + blade) % 3 == 0 else 1.0
    # Folded blades are 16-32 px native long and 8-16 px native wide.
    length = 8 + ((front * 7 + blade * 5) % 9)
    half = 3 + ((front * 3 + blade * 7) % 5)
    tilt = 0.34 * np.sin(0.31 * front + 0.19 * blade)
    direction = normal * side + tangent * tilt
    direction /= max(float(np.linalg.norm(direction)), 1e-6)
    cross = np.asarray((-direction[1], direction[0]), np.float32)
    tip = root + direction * length
    # Upper speculum lamina, sidewall and hook are separate attached surfaces.
    upper = np.asarray([
        root - cross * half,
        root + cross * half,
        tip + cross * (half - 1),
        tip - cross * (half + 1),
    ], np.float32)
    upper_i = np.rint(upper).astype(np.int32)
    optical = (front * 4 + blade * 7 + int(6 * (0.5 + 0.5 * np.sin(
        0.17 * front + 0.23 * blade)))) % len(palette)
    factor = 0.62 + 0.32 * (0.5 + 0.5 * np.sin(0.29 * front - 0.37 * blade))
    cv2.fillConvexPoly(image, upper_i, _mix(palette[optical], factor), cv2.LINE_AA)
    cv2.fillConvexPoly(masks["lamina"], upper_i,
                       85 + 21 * ((front + blade) % 8), cv2.LINE_AA)

    wall_tip = tip - direction * 2 + cross * (half + 2)
    wall = np.asarray([upper[1], upper[2], wall_tip + direction * 3,
                       root + cross * (half + 2)], np.float32)
    wall_i = np.rint(wall).astype(np.int32)
    cv2.fillConvexPoly(image, wall_i, _mix(palette[(optical + 9) % len(palette)], 0.35), cv2.LINE_AA)
    cv2.fillConvexPoly(masks["sidewall"], wall_i,
                       95 + 20 * ((front + 2 * blade) % 8), cv2.LINE_AA)

    # Projected multilayer stack: 3-5 unequal fine lamina cuts, all inside this
    # blade, representing the observed 12-15 internal melanosome layers.
    layer_count = 3 + ((front + blade) % 3)
    for layer in range(layer_count):
        t = (layer + 1) / (layer_count + 1)
        a = root * (1.0 - t) + tip * t - cross * (half - 1)
        b = root * (1.0 - t) + tip * t + cross * (half - 2)
        cv2.line(image, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                 _mix(palette[(optical + layer + 3) % len(palette)], 1.04), 1, cv2.LINE_AA)
        cv2.line(masks["multilayer"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                 90 + 20 * ((front + blade + layer) % 8), 1, cv2.LINE_AA)

    # The sidewall prolongs into the observed terminal hook; selected hooks are
    # broken or notched rather than repeated identically.
    hook_root = wall_tip + direction * 2
    bend = hook_root + direction * (3 + (blade % 4)) + cross * side * 2
    hook_tip = bend - direction * (2 + ((front + blade) % 3)) + cross * side * 2
    if (front * 19 + blade * 13) % 37 != 5:
        hook = np.rint(np.asarray([hook_root, bend, hook_tip])).astype(np.int32)
        cv2.polylines(image, [hook], False,
                      _mix(palette[(optical + 6) % len(palette)], 0.92), 1, cv2.LINE_AA)
        cv2.polylines(masks["hook"], [hook], False,
                      105 + 18 * ((front + blade) % 8), 1, cv2.LINE_AA)
    else:
        cv2.line(masks["notch"], tuple(np.rint(tip - cross * 2).astype(int)),
                 tuple(np.rint(tip + cross * 1).astype(int)), 220, 2, cv2.LINE_AA)
        cv2.line(image, tuple(np.rint(tip - cross * 2).astype(int)),
                 tuple(np.rint(tip + cross * 1).astype(int)), (3, 4, 7), 2, cv2.LINE_AA)

    # Irregular spindle mosaic is sparse and attached to the exposed lamina.
    if (front * 23 + blade * 17) % 11 in (2, 5):
        centre = root * 0.38 + tip * 0.62
        axes = (2 + (blade % 3), 1)
        angle = float(np.degrees(np.arctan2(direction[1], direction[0])))
        cv2.ellipse(image, tuple(np.rint(centre).astype(int)), axes, angle, 0, 360,
                    _mix(palette[(optical + 11) % len(palette)], 1.12), 1, cv2.LINE_AA)
        cv2.ellipse(masks["spindle"], tuple(np.rint(centre).astype(int)), axes, angle, 0, 360,
                    110 + 18 * ((front + blade) % 8), 1, cv2.LINE_AA)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    image = np.zeros((WORK, WORK, 3), np.uint8)
    image[:] = (5, 4, 9) if not angle_b else (4, 6, 12)
    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "rachis", "lamina", "sidewall", "multilayer", "hook", "notch",
        "spindle", "pocket", "glint",
    )}
    blade_count = pocket_count = glint_count = 0
    for front_i, ctrl in enumerate(FRONTS):
        pts = _bezier(ctrl)
        pts_i = np.rint(pts).astype(np.int32)
        shaft_width = 3 + (front_i % 4 == 0)
        cv2.polylines(image, [pts_i], False, (2, 3, 6), shaft_width, cv2.LINE_AA)
        cv2.polylines(masks["rachis"], [pts_i], False,
                      90 + 20 * (front_i % 8), shaft_width, cv2.LINE_AA)
        # Physical arc-length-ish sampling with incommensurate skip prevents
        # equal row cadence while keeping every blade attached to its barb.
        index = 4 + (front_i * 11) % 17
        blade_i = 0
        while index < len(pts) - 5:
            tangent = pts[index + 2] - pts[index - 2]
            _blade(image, masks, pts[index], tangent, front_i, blade_i, angle_b)
            blade_count += 1
            index += 3 + ((front_i * 5 + blade_i * 7 + blade_i * blade_i) % 5)
            blade_i += 1

        # Basal melanin pockets are compressed tears attached to this rachis,
        # not repeated dots or free black gaps.
        for j in range(3):
            k = 22 + ((front_i * 71 + j * 113) % (len(pts) - 44))
            p = pts[k]
            tangent = pts[k + 2] - pts[k - 2]
            tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            side = -1 if (front_i + j) % 2 else 1
            pocket = np.asarray([
                p - tangent * 5,
                p + normal * side * (5 + (front_i + j) % 5),
                p + tangent * 7 + normal * side * 2,
                p + tangent * 3,
            ], np.float32)
            pocket_i = np.rint(pocket).astype(np.int32)
            cv2.fillConvexPoly(image, pocket_i, (2, 2, 5), cv2.LINE_AA)
            cv2.fillConvexPoly(masks["pocket"], pocket_i,
                               110 + 18 * ((front_i + j) % 8), cv2.LINE_AA)
            pocket_count += 1

        # A few blade-edge glint cuts break long optical fronts without forming
        # another line family.
        for j in range(4):
            k = 16 + ((front_i * 53 + j * 89) % (len(pts) - 32))
            p = pts[k]
            tangent = pts[k + 2] - pts[k - 2]
            tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
            a = p - tangent * (3 + j % 3)
            b = p + tangent * (5 + (front_i + j) % 5)
            palette = FLASH_B if angle_b else FLASH_A
            cv2.line(image, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                     _mix(palette[(front_i * 3 + j + 8) % len(palette)], 1.20), 2, cv2.LINE_AA)
            cv2.line(masks["glint"], tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
                     105 + 19 * ((front_i + j) % 8), 2, cv2.LINE_AA)
            glint_count += 1

    coverage = {
        "folded_barbule_blades": float(blade_count),
        "rachis_coverage": round(float(np.mean(masks["rachis"] > 0)), 6),
        "upper_lamina_coverage": round(float(np.mean(masks["lamina"] > 0)), 6),
        "sidewall_coverage": round(float(np.mean(masks["sidewall"] > 0)), 6),
        "multilayer_coverage": round(float(np.mean(masks["multilayer"] > 0)), 6),
        "hook_coverage": round(float(np.mean(masks["hook"] > 0)), 6),
        "notch_coverage": round(float(np.mean(masks["notch"] > 0)), 6),
        "spindle_coverage": round(float(np.mean(masks["spindle"] > 0)), 6),
        "basal_pockets": float(pocket_count),
        "glint_cuts": float(glint_count),
    }
    return image, coverage, masks


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "hummingbird_blades_i1"
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
        "schema": "spb-wilds-hummingbird-blades-i1/1",
        "status": "REJECT-SPARSE-RECTANGULAR-CIRCUIT-BOARD-RAILS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "close-cropped folded gorget barbules on unequal barb fronts",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "explicit anatomical raster; no RNG/noise/stamp atlas/shared composer",
        "reference": "https://doi.org/10.1007/s00359-018-1295-8",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
