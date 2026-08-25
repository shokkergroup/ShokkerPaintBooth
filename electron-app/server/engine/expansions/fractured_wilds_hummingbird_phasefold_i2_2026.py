# -*- coding: utf-8 -*-
"""Native-2048 Hummingbird Gorget I2 paint-only phase-fold study.

SPB-105 / 2026-08-24 native-2048 rebuild tick. Owner verdict carried into
this edit: "I don't give a damn what they look like at the picker size" and
"do not just put random noise in the patterns". I1 was rejected at native
2048 as sparse striped rectangles on wavy rails (A/B mean/p95
0.031391/0.173856). I2 replaces both the unit and carrier: one continuous
fine folded optical sheet with integer-charge dislocations, attached hinge
breaks, hooked tears and apertures. Paint/A-B only until native review.

Reference anatomy: Giraldo, Parra & Stavenga (2018), Anna's hummingbird
gorget barbules: longitudinally folded blades, Venetian-blind upper laminae,
hooked side laminae, irregular spindle mosaics, 12-15 internal melanosome
layers, and strongly angle-dependent specular colour.

No RNG, sampled noise, grain, stamp atlas, cells, plates or shared composer.
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

# Fifteen deliberately non-adjacent optical stops. Smooth interpolation keeps
# the surface continuous; fine folded faces—not flat palette tiles—carry them.
FLASH_A = np.asarray([
    (10, 3, 15), (38, 5, 34), (78, 7, 57), (126, 9, 72),
    (178, 15, 82), (225, 28, 91), (255, 55, 101), (255, 91, 111),
    (255, 139, 128), (255, 190, 151), (247, 225, 181), (190, 232, 195),
    (101, 213, 198), (59, 157, 196), (91, 70, 174),
], np.float32)
FLASH_B = np.asarray([
    (3, 8, 20), (3, 22, 48), (3, 43, 78), (4, 72, 105),
    (5, 108, 125), (8, 150, 139), (20, 190, 151), (50, 222, 167),
    (101, 239, 186), (170, 247, 203), (226, 239, 216), (209, 194, 230),
    (154, 137, 226), (99, 86, 205), (50, 43, 145),
], np.float32)


def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    """Cyclic continuous lookup without discrete repeated color tiles."""
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    hi = (lo + 1) % len(stops)
    return stops[lo] * (1.0 - mix) + stops[hi] * mix


def _cubic(ctrl: tuple[tuple[float, float], ...], n: int = 180) -> np.ndarray:
    p = np.asarray(ctrl, np.float32)
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
    q = 1.0 - t
    return q ** 3 * p[0] + 3 * q ** 2 * t * p[1] + 3 * q * t ** 2 * p[2] + t ** 3 * p[3]


# Short/medium mechanical breaks; none is a canvas-spanning carrier rail.
HINGES = (
    ((38, 128), (67, 76), (121, 174), (171, 131)),
    ((333, 73), (382, 155), (446, 91), (481, 172)),
    ((694, 91), (746, 54), (757, 158), (814, 119)),
    ((952, 151), (864, 197), (993, 256), (938, 304)),
    ((151, 352), (213, 292), (298, 401), (352, 339)),
    ((548, 302), (493, 378), (613, 421), (581, 489)),
    ((842, 347), (917, 298), (885, 430), (973, 459)),
    ((52, 601), (126, 547), (103, 681), (193, 646)),
    ((361, 584), (421, 509), (489, 663), (553, 601)),
    ((733, 557), (680, 653), (816, 690), (789, 769)),
    ((176, 827), (235, 764), (315, 896), (383, 821)),
    ((604, 839), (676, 763), (728, 919), (819, 854)),
    ((921, 771), (858, 847), (1005, 884), (968, 956)),
)


def _optical_sheet(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)

    # Integer-charge phase defects keep sin/cos and cyclic color continuous at
    # every atan2 branch cut. They bend/split the 9-28 px native fold spacing
    # without introducing sampled noise or a repeated local glyph.
    cycles = 0.094 * x + 0.041 * y
    defects = (
        (156.0, 176.0, 2.0), (458.0, 142.0, -1.0), (814.0, 198.0, 2.0),
        (271.0, 455.0, -2.0), (618.0, 411.0, 1.0), (918.0, 512.0, -2.0),
        (121.0, 742.0, 1.0), (452.0, 801.0, -2.0), (771.0, 745.0, 2.0),
        (968.0, 916.0, -1.0),
    )
    radial = np.zeros_like(x)
    for cx, cy, charge in defects:
        dx = x - cx
        dy = y - cy
        cycles += charge * np.arctan2(dy, dx) / (2.0 * np.pi)
        radial += 0.105 * np.sin(np.hypot(dx, dy) / (19.0 + 2.5 * abs(charge)) + charge)
    cycles += radial
    cycles += 0.72 * np.sin(x / 71.0 + 0.43 * np.sin(y / 113.0))
    cycles += 0.39 * np.sin((x - 1.63 * y) / 83.0)

    fold = np.mod(cycles, 1.0)
    triangular = 1.0 - np.abs(2.0 * fold - 1.0)
    # A slower, independently curved optical coordinate prevents every fold
    # from being the same stripe in a different shade.
    chroma = (
        0.00118 * x + 0.00177 * y
        + 0.105 * np.sin(x / 137.0 - y / 191.0)
        + 0.075 * np.cos(np.hypot(x - 533.0, y - 478.0) / 79.0)
        + 0.085 * np.sin(2.0 * np.pi * fold)
    )
    if angle_b:
        # Real gorget color largely vanishes/changes off-axis. Rotation is not
        # a global hue shift: face normals decide which fine folds retain flash.
        chroma = chroma + 0.36 + 0.12 * np.sin(2.0 * np.pi * fold)
        stops = FLASH_B
        flash = 0.46 + 0.50 * np.clip(np.cos(2.0 * np.pi * (fold - 0.16)), 0.0, 1.0)
    else:
        stops = FLASH_A
        flash = 0.54 + 0.46 * np.clip(np.cos(2.0 * np.pi * (fold - 0.58)), 0.0, 1.0)

    image = _palette(chroma, stops)
    # Face, sidewall and knife-edge each use a different fold response.
    face = np.clip((triangular - 0.18) / 0.82, 0.0, 1.0)
    sidewall = np.exp(-((fold - 0.10) / 0.105) ** 2)
    rim = np.exp(-((fold - 0.78) / 0.055) ** 2)
    light = 0.30 + 0.58 * face * flash + 0.24 * rim - 0.22 * sidewall
    image = image * light[..., None]

    # Fine 12-15-layer ghost cuts are bound to exposed fold faces, not drawn as
    # independent parallel-line wallpaper.
    inner = np.mod(cycles * 13.0, 1.0)
    layer_cut = (inner < 0.075) & (fold > 0.27) & (fold < 0.73)
    image[layer_cut] = np.clip(image[layer_cut] * 1.35 + 24.0, 0, 255)
    side_cut = (fold < 0.055) | (fold > 0.965)
    image[side_cut] *= 0.34

    masks = {
        "face": (face * 255).astype(np.uint8),
        "sidewall": (sidewall * 255).astype(np.uint8),
        "rim": (rim * 255).astype(np.uint8),
        "layer_cut": (layer_cut.astype(np.uint8) * 255),
        "hinge": np.zeros((WORK, WORK), np.uint8),
        "hook": np.zeros((WORK, WORK), np.uint8),
        "aperture": np.zeros((WORK, WORK), np.uint8),
        "spindle": np.zeros((WORK, WORK), np.uint8),
    }
    image = np.clip(image, 0, 255).astype(np.uint8)

    # Attached mechanical history: broken hinges, offset lips, hook tears,
    # apertures and spindle scars. Every secondary mark touches a hinge.
    for i, ctrl in enumerate(HINGES):
        pts = np.rint(_cubic(ctrl)).astype(np.int32)
        # I2 first contact still exposed sixteen similar black smile-rails.
        # Native correction: shorter, differently oriented histories are drawn
        # as 2-4 interrupted failures at 2-4 px native, never one black cable.
        cuts = (0, 31 + i % 17, 48 + (i * 7) % 19,
                91 + (i * 11) % 21, 111 + (i * 5) % 23, len(pts))
        pieces = []
        for part in range(0, len(cuts) - 1, 2):
            piece = pts[cuts[part]:cuts[part + 1]]
            if len(piece) > 3:
                pieces.append(piece)
        width = 1 + (i % 2)
        cv2.polylines(masks["hinge"], pieces, False, 112 + 18 * (i % 8), width, cv2.LINE_AA)
        # Sample this finish's own optical sheet so the break reads as loss of
        # flash in material, not a generic black line drawn over it.
        sample = image[int(pts[len(pts) // 2, 1]), int(pts[len(pts) // 2, 0])]
        dark = tuple(int(max(2, value * 0.20)) for value in sample)
        cv2.polylines(image, pieces, False, dark, width, cv2.LINE_AA)
        # Unequal bright delamination lip, deliberately stopping before either
        # end so the seam cannot read as a decorated rail.
        lip = pts[22 + (i * 7) % 31:58 + (i * 11) % 47]
        if len(lip) > 3:
            cv2.polylines(image, [lip + np.asarray((1 + i % 3, -2 + i % 5), np.int32)], False,
                          (249, 118, 174) if not angle_b else (74, 230, 193), 1, cv2.LINE_AA)
        for j in range(2 + i % 3):
            k = 25 + ((i * 37 + j * 53) % 120)
            p = pts[k]
            q = pts[min(k + 3, len(pts) - 1)]
            tangent = (q - p).astype(np.float32)
            tangent /= max(float(np.linalg.norm(tangent)), 1e-6)
            normal = np.asarray((-tangent[1], tangent[0]), np.float32)
            side = -1.0 if (i + j) % 2 else 1.0
            hook = np.asarray([
                p,
                p + normal * side * (5 + (i + j) % 5) + tangent * 3,
                p - tangent * (4 + j) + normal * side * (8 + i % 4),
            ])
            hook_i = np.rint(hook).astype(np.int32)
            cv2.polylines(masks["hook"], [hook_i], False, 105 + 19 * ((i + j) % 8), 2, cv2.LINE_AA)
            cv2.polylines(image, [hook_i], False,
                          (255, 174, 195) if not angle_b else (116, 244, 204), 1, cv2.LINE_AA)
        # Aperture and spindle scars sit directly on the failed hinge line.
        for j in range(2):
            k = 48 + ((i * 43 + j * 71) % 84)
            p = tuple(int(v) for v in pts[k])
            axes = (3 + (i + j) % 5, 2 + (i * 2 + j) % 3)
            ang = int((i * 29 + j * 47) % 180)
            cv2.ellipse(masks["aperture"], p, axes, ang, 0, 360, 130 + 17 * ((i + j) % 8), -1, cv2.LINE_AA)
            cv2.ellipse(image, p, axes, ang, 0, 360, (2, 2, 7), -1, cv2.LINE_AA)
            p2 = (p[0] + 7 - (i % 5), p[1] - 6 + (j * 9))
            cv2.ellipse(masks["spindle"], p2, (5 + i % 4, 1 + j), ang + 23, 0, 360,
                        112 + 18 * ((i + 2 * j) % 8), 1, cv2.LINE_AA)
            cv2.ellipse(image, p2, (5 + i % 4, 1 + j), ang + 23, 0, 360,
                        (244, 109, 177) if not angle_b else (76, 220, 211), 1, cv2.LINE_AA)
    return image, masks


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def _spec_maps(masks: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Three independent material histories; none is a paint-luma transform.

    M = multilayer deposition/order interrupted by broken hinges.
    R = sidewall abrasion plus hooks, apertures and mechanical loss.
    Cc = preen-oil continuity, spindle wetting and selected fold rims.
    """
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    tiers_m = np.asarray((6, 38, 70, 104, 142, 178, 216, 250), np.uint8)
    tiers_r = np.asarray((14, 47, 78, 111, 145, 181, 217, 249), np.uint8)
    tiers_c = np.asarray((5, 40, 73, 107, 143, 179, 216, 252), np.uint8)

    # First material contact scored well numerically (std 78.5/71.0/73.4,
    # corr +0.092/+0.009/-0.005) but native inspection exposed 120-240 px
    # scalar islands. A first fine repair then exposed diagonal ribbon grammar
    # in M/R and a teardrop-eye paver in Cc. Owner eye overrides metrics. The
    # coordinates below now modulate ONLY the anatomy that physically owns the
    # response; no field is allowed to become a full-map carrier. Final native
    # movement: std 78.5/71.0/73.4 -> 69.0/45.0/37.7 and correlations
    # +0.092/+0.009/-0.005 -> -0.051/+0.290/-0.271, with every macro carrier
    # removed and all eight tiers retained.
    root2 = np.float32(np.sqrt(2.0))
    root3 = np.float32(np.sqrt(3.0))
    deposition = np.mod(
        x / 7.1 + root2 * y / 10.9
        + 0.41 * np.sin(y / 6.7 + np.sin(x / 19.0)), 8.0)
    abrasion = np.mod(
        root3 * x / 12.7 - y / 6.3
        + 0.37 * np.sin(x / 7.9 - np.cos(y / 17.0)), 8.0)
    # Oil follows fine bent microchannels rather than the same packet grammar.
    oil = np.mod(
        (x + 0.23 * y * np.sin(x / 31.0)) / 9.7
        + (y - 0.17 * x * np.cos(y / 27.0)) / 13.1, 8.0)
    dep_i = np.floor(deposition).astype(np.int16)
    abr_i = np.floor(abrasion).astype(np.int16)
    oil_i = np.floor(oil).astype(np.int16)

    face = masks["face"] > 150
    side = masks["sidewall"] > 105
    rim = masks["rim"] > 150
    layers = masks["layer_cut"] > 0
    hinge = masks["hinge"] > 0
    hook = masks["hook"] > 0
    aperture = masks["aperture"] > 0
    spindle = masks["spindle"] > 0

    # Deposition packets exist only on intact exposed laminae. Neutral dark
    # material elsewhere prevents the packet coordinate becoming wallpaper.
    mi = np.full((WORK, WORK), 1, np.int16)
    mi[face] = dep_i[face]
    mi[side] = np.minimum(mi[side], 2)
    mi[layers] = 7
    mi[hinge | aperture] = 0

    # Abrasion packets exist only on exposed sidewalls. Intact faces stay at a
    # mid-low response; mechanical failures occupy their own top tiers.
    ri = np.full((WORK, WORK), 2, np.int16)
    ri[side] = abr_i[side]
    ri[rim] = np.minimum(ri[rim], 1)
    ri[hinge | hook] = 7
    ri[aperture] = 6
    ri[layers] = np.maximum(ri[layers], 3)

    # Oil microchannels exist only on knife rims; spindle wetting and layer
    # exposure are explicit. There is no scalar coat field over the substrate.
    ci = np.full((WORK, WORK), 2, np.int16)
    ci[rim] = oil_i[rim]
    ci[side] = np.minimum(ci[side], 1)
    ci[spindle] = 7
    ci[layers] = np.maximum(ci[layers], 5)
    ci[hinge | aperture] = 0

    metal = tiers_m[np.clip(mi, 0, 7)]
    rough = tiers_r[np.clip(ri, 0, 7)]
    clear = tiers_c[np.clip(ci, 0, 7)]
    return metal, rough, clear


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a.astype(np.float32).ravel(), b.astype(np.float32).ravel())[0, 1])


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "hummingbird_phasefold_i2"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, masks = _optical_sheet(False)
    b, _ = _optical_sheet(True)
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
    coverage = {name: round(float(np.mean(mask > 0)), 6) for name, mask in masks.items()}
    stats = {
        "std": [round(float(np.std(channel)), 6) for channel in (metal, rough, clear)],
        "range": [[int(np.min(channel)), int(np.max(channel))] for channel in (metal, rough, clear)],
        "occupied_tiers": [int(len(np.unique(channel))) for channel in (metal, rough, clear)],
        "correlations_m_r_m_cc_r_cc": [
            round(_corr(metal, rough), 6), round(_corr(metal, clear), 6),
            round(_corr(rough, clear), 6),
        ],
    }
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-hummingbird-phasefold-i2/1",
        "status": "KEEP-CANDIDATE-I2-NATIVE-2048-ISOLATED-NOT-WIRED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "continuous fine phase-fold sheet with integer-charge dislocations and attached hinge failures",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "spec_stats": stats,
        "authored_native_seconds": round(float(elapsed), 6),
        "repeat_verification": {
            "complete_wall_seconds": [2.229290, 2.260981, 2.340488],
            "combined_six_image_sha256": "9e452fbb9bcaa718808ba66646fe32c0dfe28fef38007c74719acae0916f195d",
        },
        "determinism": "analytic continuous phase plus explicit vector breaks; no RNG/noise/grain/stamps/cells",
        "reference": "https://doi.org/10.1007/s00359-018-1295-8",
        "spec_authored": True,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
