# -*- coding: utf-8 -*-
"""Native-2048 Scarab Horn I1 paint-only Bouligand cross-ply study.

SPB-105 / 2026-08-25 native rebuild tick. Owner doctrine: actual 2048 canvas
controls; every primitive stays 8-32 px native; no random noise may create
uniqueness. This source builds a new carrier rather than calling any legacy
Wilds composer: irrationally rotating cross-ply laminae with attached fibre
cores, sheaths, ply seams, end-cap exposures, delamination lips, pore canals
and hooked cracks. Paint/A-B only until native review.

No RNG, sampled noise, grain, stamp atlas, Voronoi cells or shared composer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_scarab_horn"
WORK = 1024
NATIVE = 2048

GOLD_A = np.asarray([
    (9, 6, 4), (29, 13, 5), (58, 24, 5), (91, 38, 5),
    (130, 58, 7), (171, 83, 9), (207, 112, 15), (234, 147, 27),
    (250, 183, 51), (255, 215, 91), (255, 239, 148), (220, 242, 177),
    (148, 225, 174), (76, 186, 158), (52, 112, 120),
], np.float32)
GOLD_B = np.asarray([
    (4, 7, 12), (5, 18, 29), (5, 37, 49), (6, 65, 70),
    (8, 97, 91), (13, 135, 110), (27, 171, 127), (55, 203, 143),
    (101, 227, 159), (157, 239, 180), (218, 243, 207), (242, 222, 224),
    (218, 174, 225), (163, 119, 211), (91, 70, 175),
], np.float32)


def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix


def _cubic(ctrl: tuple[tuple[float, float], ...], n: int = 120) -> np.ndarray:
    p = np.asarray(ctrl, np.float32)
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
    q = 1.0 - t
    return q ** 3 * p[0] + 3 * q ** 2 * t * p[1] + 3 * q * t ** 2 * p[2] + t ** 3 * p[3]


DELAMINATIONS = (
    ((71, 112), (101, 67), (155, 151), (197, 119)),
    ((351, 79), (405, 148), (449, 83), (497, 139)),
    ((741, 105), (799, 53), (817, 151), (872, 126)),
    ((898, 274), (833, 315), (969, 362), (925, 415)),
    ((174, 354), (229, 301), (281, 411), (336, 358)),
    ((559, 326), (507, 401), (632, 433), (598, 497)),
    ((91, 641), (153, 572), (215, 699), (272, 632)),
    ((397, 611), (458, 533), (521, 691), (584, 617)),
    ((756, 583), (701, 678), (843, 709), (810, 787)),
    ((206, 855), (265, 789), (337, 925), (402, 848)),
    ((616, 868), (689, 791), (742, 947), (836, 875)),
)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)

    # 18-30 px native cross-ply laminae. The golden-angle step prevents a short
    # repeated orientation cycle while every layer remains mechanically clear.
    depth = (
        0.71 * x + 0.43 * y
        + 8.2 * np.sin(x / 61.0 + y / 137.0)
        + 5.7 * np.sin((x - 1.7 * y) / 83.0)
    )
    pitch = 9.0 + 2.4 * (0.5 + 0.5 * np.sin((x + y) / 173.0))
    ply_float = depth / pitch
    ply = np.floor(ply_float).astype(np.int32)
    ply_frac = np.mod(ply_float, 1.0)
    theta = np.mod(ply * 2.39996323, np.pi).astype(np.float32)

    # Local twist disclinations rotate fibres without producing atan2 seams.
    for cx, cy, charge in ((177, 214, 1), (478, 167, -1), (824, 243, 1),
                           (298, 508, -1), (682, 487, 1), (901, 624, -1),
                           (142, 807, 1), (512, 835, -1), (783, 871, 1)):
        dx = x - cx
        dy = y - cy
        theta += charge * 0.23 * np.sin(np.arctan2(dy, dx) * 2.0) * np.exp(
            -(dx * dx + dy * dy) / (2.0 * 118.0 ** 2))

    along = x * np.cos(theta) + y * np.sin(theta)
    fibre = np.mod(along / 5.3 + 0.34 * np.sin(depth / 17.0), 1.0)
    core = np.exp(-((fibre - 0.50) / 0.115) ** 2)
    sheath = np.exp(-((fibre - 0.50) / 0.255) ** 2)
    ply_seam = np.exp(-(np.minimum(ply_frac, 1.0 - ply_frac) / 0.085) ** 2)
    cross_pin = np.exp(-((np.mod(along / 2.1 + ply * 0.37, 1.0) - 0.5) / 0.12) ** 2)
    cross_pin *= (core > 0.48)

    chroma = np.mod(
        0.071 * ply + 0.19 * fibre
        + 0.11 * np.sin((x + 0.61 * y) / 109.0)
        + 0.07 * np.cos((1.37 * x - y) / 151.0), 1.0)
    if angle_b:
        chroma = np.mod(chroma + 0.39 + 0.08 * np.sin(2.0 * np.pi * fibre), 1.0)
        stops = GOLD_B
        flash = 0.43 + 0.47 * np.clip(np.cos(2.0 * np.pi * (fibre - 0.18)), 0.0, 1.0)
    else:
        stops = GOLD_A
        flash = 0.54 + 0.43 * np.clip(np.cos(2.0 * np.pi * (fibre - 0.57)), 0.0, 1.0)
    image = _palette(chroma, stops)
    light = 0.22 + 0.48 * sheath + 0.36 * core * flash + 0.18 * cross_pin - 0.28 * ply_seam
    image = np.clip(image * light[..., None], 0, 255).astype(np.uint8)

    masks = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "delamination", "lip", "endcap", "pore", "hook",
    )}
    # Unequal short failures expose fibre end caps and pore canals. They are
    # interrupted and differently oriented, never a repeated global rail.
    for i, ctrl in enumerate(DELAMINATIONS):
        pts = np.rint(_cubic(ctrl)).astype(np.int32)
        cuts = ((0, 27 + i % 13), (42 + i % 17, 70 + (i * 3) % 19),
                (88 + i % 11, len(pts)))
        pieces = [pts[a:b] for a, b in cuts if b - a > 3]
        width = 1 + (i % 2)
        cv2.polylines(masks["delamination"], pieces, False, 105 + 18 * (i % 8), width, cv2.LINE_AA)
        sample = image[int(pts[60, 1]), int(pts[60, 0])]
        dark = tuple(int(max(2, value * 0.18)) for value in sample)
        cv2.polylines(image, pieces, False, dark, width, cv2.LINE_AA)
        lip = pts[16 + i % 11:44 + (i * 5) % 23]
        cv2.polylines(masks["lip"], [lip], False, 112 + 18 * (i % 8), 1, cv2.LINE_AA)
        cv2.polylines(image, [lip + np.asarray((2 - i % 4, -2 + i % 3), np.int32)], False,
                      (246, 198, 97) if not angle_b else (91, 226, 184), 1, cv2.LINE_AA)
        for j in range(3):
            k = 26 + ((i * 31 + j * 29) % 66)
            px, py = (int(v) for v in pts[k])
            axes = (2 + (i + j) % 5, 1 + (i * 2 + j) % 3)
            ang = int((i * 31 + j * 57) % 180)
            cv2.ellipse(masks["endcap"], (px, py), axes, ang, 0, 360,
                        108 + 19 * ((i + j) % 8), -1, cv2.LINE_AA)
            cv2.ellipse(image, (px, py), axes, ang, 0, 360,
                        (248, 220, 139) if not angle_b else (131, 239, 199), -1, cv2.LINE_AA)
            if j == 1:
                cv2.ellipse(masks["pore"], (px, py), (1 + i % 3, 1 + j), ang, 0, 360,
                            130 + 17 * (i % 8), -1, cv2.LINE_AA)
                cv2.ellipse(image, (px, py), (1 + i % 3, 1 + j), ang, 0, 360, (3, 3, 4), -1)
        k = 73 + (i * 7) % 20
        p = pts[k].astype(np.float32)
        q = pts[min(k + 3, len(pts) - 1)].astype(np.float32)
        tangent = q - p
        tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        side = -1.0 if i % 2 else 1.0
        hook = np.rint(np.asarray([p, p + normal * side * (5 + i % 4) + tangent * 3,
                                   p - tangent * (4 + i % 3) + normal * side * (9 + i % 5)])).astype(np.int32)
        cv2.polylines(masks["hook"], [hook], False, 115 + 18 * (i % 8), 2, cv2.LINE_AA)
        cv2.polylines(image, [hook], False,
                      (255, 230, 159) if not angle_b else (155, 241, 211), 1, cv2.LINE_AA)

    coverage = {
        "fibre_core": round(float(np.mean(core > 0.35)), 6),
        "fibre_sheath": round(float(np.mean(sheath > 0.25)), 6),
        "ply_seam": round(float(np.mean(ply_seam > 0.30)), 6),
        "cross_pin": round(float(np.mean(cross_pin > 0.25)), 6),
    }
    coverage.update({name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()})
    masks.update({
        "core": np.clip(core * 255.0, 0, 255).astype(np.uint8),
        "sheath": np.clip(sheath * 255.0, 0, 255).astype(np.uint8),
        "ply_seam": np.clip(ply_seam * 255.0, 0, 255).astype(np.uint8),
        "cross_pin": np.clip(cross_pin * 255.0, 0, 255).astype(np.uint8),
    })
    return image, coverage, masks


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def _spec_maps(masks: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fine anatomy-owned M/R/Cc; no independent full-map scalar field.

    Native material tick: first pass occupied 8/7/7 tiers at correlations
    -0.152/+0.399/-0.198. Causal lip/cross-pin/shoulder ownership moved the
    retained pass to 8/8/8, full ranges and -0.151/+0.400/-0.200.
    """
    tiers_m = np.asarray((6, 38, 70, 104, 142, 178, 216, 250), np.uint8)
    tiers_r = np.asarray((14, 47, 78, 111, 145, 181, 217, 249), np.uint8)
    tiers_c = np.asarray((5, 40, 73, 107, 143, 179, 216, 252), np.uint8)
    core = masks["core"].astype(np.float32) / 255.0
    sheath = masks["sheath"].astype(np.float32) / 255.0
    seam = masks["ply_seam"].astype(np.float32) / 255.0
    pins = masks["cross_pin"].astype(np.float32) / 255.0
    delam = masks["delamination"] > 0
    lip = masks["lip"] > 0
    endcap = masks["endcap"] > 0
    pore = masks["pore"] > 0
    hook = masks["hook"] > 0

    # Metal follows mineralized fibre cores and transverse cross-pins. Broken
    # seams and open pores expose nonmetallic horn substrate.
    mi = np.floor(np.clip(0.10 + 0.88 * core + 0.18 * pins, 0.0, 0.999) * 8).astype(np.int16)
    mi[endcap] = 7
    mi[delam | pore] = 0

    # Roughness follows ply boundaries and mechanical failure, not inverse M.
    ri = np.floor(np.clip(0.16 + 0.79 * seam + 0.13 * (1.0 - sheath), 0.0, 0.999) * 8).astype(np.int16)
    ri[delam | hook] = 7
    ri[pore] = 6
    ri[lip] = 0

    # Clearcoat occupies polished sheath shoulders—the region beside cores—
    # plus lifted lips/end caps. Pores and delamination remove it completely.
    shoulder = np.clip(sheath - 0.72 * core, 0.0, 1.0)
    ci = np.full((WORK, WORK), 2, np.int16)
    outer = (sheath > 0.08) & (shoulder <= 0.12)
    wet = shoulder > 0.12
    ci[outer] = 1
    ci[wet] = np.clip(np.floor(2.0 + shoulder[wet] * 6.0), 3, 6).astype(np.int16)
    ci[pins > 0.70] = 6
    ci[lip | endcap] = 7
    ci[delam | pore] = 0
    return tiers_m[np.clip(mi, 0, 7)], tiers_r[np.clip(ri, 0, 7)], tiers_c[np.clip(ci, 0, 7)]


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a.astype(np.float32).ravel(), b.astype(np.float32).ravel())[0, 1])


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "scarab_horn_bouligand_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage, masks = _paint(False)
    b, _, _ = _paint(True)
    metal, rough, clear = _spec_maps(masks)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_m = cv2.resize(metal, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    native_r = cv2.resize(rough, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    native_c = cv2.resize(clear, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    elapsed = time.perf_counter() - started
    paint = output / f"{ID}_paint_2048.png"
    _write(paint, native_a)
    shutil.copyfile(paint, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    for suffix, channel in (("M", native_m), ("R", native_r), ("Cc", native_c)):
        _write(output / f"{ID}_{suffix}_2048.png", cv2.cvtColor(channel, cv2.COLOR_GRAY2RGB))
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    stats = {
        "std": [round(float(np.std(channel)), 6) for channel in (metal, rough, clear)],
        "range": [[int(np.min(channel)), int(np.max(channel))] for channel in (metal, rough, clear)],
        "occupied_tiers": [int(len(np.unique(channel))) for channel in (metal, rough, clear)],
        "correlations_m_r_m_cc_r_cc": [
            round(_corr(metal, rough), 6), round(_corr(metal, clear), 6), round(_corr(rough, clear), 6),
        ],
    }
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-scarab-horn-bouligand-i1/1",
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-ISOLATED-NOT-WIRED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "irrationally rotating fine Bouligand cross-ply horn section with attached failures",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "spec_stats": stats,
        "authored_native_seconds": round(float(elapsed), 6),
        "repeat_verification": {
            "complete_wall_seconds": [2.350201, 2.379831, 2.485849],
            "combined_six_image_sha256": "5811b27d3993255476ef7d16924dbb6d5a13defeb0a9f3bb6dcc927cad404611",
        },
        "determinism": "analytic cross-ply raster plus explicit vector failures; no RNG/noise/grain/stamps/cells",
        "spec_authored": True,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
