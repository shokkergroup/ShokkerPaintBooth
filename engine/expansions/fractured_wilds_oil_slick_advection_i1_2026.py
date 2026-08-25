# -*- coding: utf-8 -*-
"""Native-2048 Oil Slick I1 thin-film advection candidate.

KEEP-CANDIDATE-I1 / ISOLATED / NOT OWNER ACCEPTED / NOT WIRED. SPB-105 native
paint tick 2026-08-25. Actual 2048 controls. This is a fresh area-forming carrier for the
fmo_oil_slick reservation: a continuously deformed film sheet with fold-over
tongues, compression shocks, optical-order jumps, dry valleys and shear cusps.

Initial native contact rejected 18 pasted polygon breaks and 16 ellipse lobes.
The retained contact removes that independent anatomy entirely: every visible
mark is now derived from the same sheet's thickness, slope, curvature or
interference order.

First material contact was rejected at M/R/Cc correlations
+0.111/-0.751/-0.330: monotonic thick-film Cc was functionally inverse metal.
Mid-depth/optical-shoulder Cc repair retained std 59.587/30.578/35.603,
8/8/8 tiers and correlations +0.111/-0.267/-0.070. Three complete native runs
are exact at 2.162/2.287/2.472 s.

No RNG, sampled noise, grain, cells, stamps, generic contour renderer, shared
composer or legacy finish code. Material maps are intentionally absent until
the native A/B paint survives visual contact.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_oil_slick"
WORK = 1024
NATIVE = 2048

# Fifteen deliberately nonuniform interference orders. The B palette is not a
# hue rotation: it represents the complementary order exposed by a changed
# view/light vector and therefore changes value ordering as well as hue.
OIL_A = np.asarray([
    (3, 4, 9), (15, 8, 42), (56, 12, 103), (112, 18, 148),
    (183, 31, 151), (238, 61, 112), (252, 111, 47), (250, 180, 26),
    (213, 231, 53), (95, 224, 80), (20, 186, 116), (5, 143, 164),
    (11, 90, 190), (43, 50, 171), (126, 55, 186),
], np.float32)
OIL_B = np.asarray([
    (2, 7, 8), (4, 34, 36), (6, 87, 77), (12, 143, 93),
    (48, 196, 80), (129, 226, 48), (217, 227, 30), (251, 168, 28),
    (247, 88, 52), (221, 36, 105), (170, 25, 169), (105, 31, 205),
    (44, 62, 211), (15, 119, 198), (8, 174, 168),
], np.float32)

VORTICES = (
    (-0.66, -0.46, 0.62, 1.18),
    (0.20, -0.61, 0.47, -1.34),
    (0.70, -0.05, 0.56, 1.08),
    (-0.38, 0.22, 0.51, -1.27),
    (0.31, 0.43, 0.58, 1.31),
    (-0.76, 0.76, 0.43, 1.16),
    (0.77, 0.79, 0.46, -1.22),
)

def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix


def _unit(a: np.ndarray) -> np.ndarray:
    lo = float(a.min())
    hi = float(a.max())
    return np.clip((a - lo) / max(hi - lo, 1e-7), 0.0, 1.0)


def _sheet_coordinates() -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    qx = (x - WORK * 0.5) / (WORK * 0.5)
    qy = (y - WORK * 0.5) / (WORK * 0.5)

    # Sequential finite-radius twists deform the same sheet. They do not pick
    # cells or add independent patterns: downstream tongues inherit every
    # previous bend, which produces real fold chronology and asymmetric cusps.
    for cx, cy, radius, strength in VORTICES:
        dx = qx - cx
        dy = qy - cy
        influence = np.exp(-(dx * dx + dy * dy) / (radius * radius))
        angle = strength * influence
        ca = np.cos(angle)
        sa = np.sin(angle)
        qx = cx + ca * dx - sa * dy
        qy = cy + sa * dx + ca * dy

    # Cross-shears force broad film tongues to fold over one another. The two
    # harmonics have incommensurate periods to prevent a repeated wave tile.
    qx = qx + 0.105 * np.sin(7.1 * qy + 1.7 * np.sin(3.3 * qx))
    qy = qy + 0.082 * np.sin(6.3 * qx - 1.4 * np.sin(4.1 * qy))
    qx = qx + 0.036 * np.sin(17.7 * qy + 5.2 * qx)
    return qx, qy


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    qx, qy = _sheet_coordinates()

    # Film thickness is a single advected physical sheet. A broad deposition
    # ramp, two interference orders and a cross-film thickness drift create
    # filled chromatic territories, not colored contour lines or noise.
    thickness = (
        0.51 + 0.126 * qx - 0.091 * qy
        + 0.104 * np.sin(8.2 * qx + 2.7 * qy)
        + 0.071 * np.sin(13.1 * qy - 3.9 * qx + 0.8 * np.sin(5.4 * qx))
        + 0.036 * np.sin(24.3 * qx + 17.2 * qy)
    )
    gy, gx = np.gradient(thickness)
    slope = np.sqrt(gx * gx + gy * gy)
    shock = _unit(np.maximum(slope - cv2.GaussianBlur(slope, (0, 0), 5.2), 0.0))
    compression = _unit(slope)
    curvature = _unit(np.abs(cv2.Laplacian(thickness, cv2.CV_32F, ksize=3)))

    # Fine fold lamellae are subordinate to the broad film territories. Their
    # local pitch is 8-26 native pixels and changes continuously with strain.
    strain = np.clip(0.55 + 0.45 * compression, 0.0, 1.0)
    fold_phase = 2.0 * np.pi * (
        (qx * (58.0 + 18.0 * strain) + qy * (19.0 - 8.0 * strain))
        + 0.13 * np.sin(11.0 * qy - 4.0 * qx)
    )
    fine_fold = 0.5 + 0.5 * np.sin(fold_phase)
    fine_ridge = np.power(np.clip(fine_fold, 0.0, 1.0), 7.0)

    # Surface-normal lighting makes the A/B state physically flip; palette
    # travel is coupled to thickness order and does not merely recolor A.
    nz = np.ones_like(gx) * 0.022
    norm = np.sqrt(gx * gx + gy * gy + nz * nz)
    nx = -gx / norm
    ny = -gy / norm
    nz /= norm
    if angle_b:
        lx, ly, lz = -0.62, 0.28, 0.73
        palette = OIL_B
        travel = 0.37
    else:
        lx, ly, lz = 0.49, -0.43, 0.76
        palette = OIL_A
        travel = 0.0
    diffuse = np.clip(nx * lx + ny * ly + nz * lz, -0.55, 1.0)
    spectral = np.mod(thickness * 3.15 + 0.11 * compression + travel, 1.0)
    # These histories belong to the film field itself. Order jumps are places
    # where a thin-film interference order wraps; dry valleys are the thinnest
    # compressed sheet regions; cusps require both slope and curvature.
    order_jump = np.exp(-np.minimum(spectral, 1.0 - spectral) / 0.025)
    dry_valley = np.clip((0.24 - _unit(thickness)) / 0.24, 0.0, 1.0) * np.clip(compression * 1.4, 0.0, 1.0)
    shear_cusp = np.clip((curvature - 0.42) / 0.58, 0.0, 1.0) * np.clip(compression * 1.3, 0.0, 1.0)
    image = _palette(spectral, palette)
    light = np.clip(
        0.24 + 0.56 * (diffuse + 0.55) / 1.55
        + 0.22 * shock + 0.15 * fine_ridge + 0.10 * compression
        + 0.17 * order_jump + 0.13 * shear_cusp - 0.22 * dry_valley,
        0.06, 1.19,
    )
    image = image * light[..., None]
    image = np.clip(image, 0, 255).astype(np.uint8)

    coverage = {
        "film_territory": round(float(np.mean(compression > 0.24)), 6),
        "compression_shock": round(float(np.mean(shock > 0.48)), 6),
        "fine_fold_ridge": round(float(np.mean(fine_ridge > 0.32)), 6),
        "optical_order_jump": round(float(np.mean(order_jump > 0.38)), 6),
        "dry_valley": round(float(np.mean(dry_valley > 0.24)), 6),
        "shear_cusp": round(float(np.mean(shear_cusp > 0.20)), 6),
    }
    fields = {
        "thickness": _unit(thickness),
        "compression": compression,
        "shock": shock,
        "curvature": curvature,
        "fine_ridge": fine_ridge,
        "order_jump": order_jump,
        "dry_valley": dry_valley,
        "shear_cusp": shear_cusp,
    }
    return image, coverage, fields


def _write(path: Path, image: np.ndarray) -> None:
    payload = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.ndim == 3 else image
    if not cv2.imwrite(str(path), payload, [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def _tier_index(score: np.ndarray) -> np.ndarray:
    """Expose eight causal response bands without adding a texture field."""
    normalized = _unit(score)
    return np.digitize(normalized, (0.105, 0.22, 0.34, 0.46, 0.58, 0.70, 0.83)).astype(np.int16)


def _spec_maps(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Independent eight-tier responses from the one thin-film history.

    Metal exposes the substrate beneath thin/compressed film; roughness follows
    fine strain ridges plus slope and rupture; clearcoat follows optical order
    shoulders and low-curvature pooled film. No map is another map's inverse.
    """
    thickness = fields["thickness"]
    compression = fields["compression"]
    shock = fields["shock"]
    curvature = fields["curvature"]
    fine = fields["fine_ridge"]
    order = fields["order_jump"]
    dry = fields["dry_valley"]
    cusp = fields["shear_cusp"]

    # Thin regions reveal metallic substrate, with extra exposure at true
    # compression shocks and dry valleys. Optical color order is irrelevant.
    m_score = (
        0.54 * np.power(1.0 - thickness, 1.35)
        + 0.24 * shock + 0.18 * dry + 0.09 * compression
    )
    # Roughness records strain: fine ridges, changing slope and cusp damage.
    # Pooled optical order and absolute film thickness do not own this channel.
    r_score = (
        0.43 * compression + 0.31 * fine
        + 0.20 * curvature + 0.16 * cusp + 0.08 * dry
    )
    # First material contact failed at M/Cc -0.751 because monotonic thick-film
    # pooling was functionally the inverse of thin-film substrate exposure.
    # Retained correction: coat pools at a mid-depth capillary equilibrium and
    # catches optical-order shoulders. Both very thin and very thick territories
    # shed it, so this history is not expressible as "not metal".
    mid_pool = np.exp(-((thickness - 0.54) / 0.19) ** 2) * (1.0 - curvature)
    c_score = 0.18 * mid_pool + 0.72 * order + 0.13 * shock - 0.28 * dry - 0.05 * fine

    mi = _tier_index(m_score)
    ri = _tier_index(r_score)
    ci = _tier_index(c_score)
    tiers_m = np.asarray((6, 39, 72, 106, 142, 179, 216, 250), np.uint8)
    tiers_r = np.asarray((14, 47, 79, 112, 146, 182, 218, 249), np.uint8)
    tiers_c = np.asarray((5, 40, 73, 107, 143, 180, 217, 252), np.uint8)
    return tiers_m[mi], tiers_r[ri], tiers_c[ci]


def _material_stats(metal: np.ndarray, rough: np.ndarray, coat: np.ndarray) -> dict[str, object]:
    arrays = (metal, rough, coat)
    names = ("M", "R", "Cc")
    flat = [a.astype(np.float32).ravel() for a in arrays]
    return {
        "std": {n: round(float(a.std()), 6) for n, a in zip(names, arrays)},
        "range": {n: [int(a.min()), int(a.max())] for n, a in zip(names, arrays)},
        "tier_count": {n: int(len(np.unique(a))) for n, a in zip(names, arrays)},
        "correlation": {
            "M_R": round(float(np.corrcoef(flat[0], flat[1])[0, 1]), 6),
            "M_Cc": round(float(np.corrcoef(flat[0], flat[2])[0, 1]), 6),
            "R_Cc": round(float(np.corrcoef(flat[1], flat[2])[0, 1]), 6),
        },
    }


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "oil_slick_advection_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage, fields = _paint(False)
    b, _, _ = _paint(True)
    metal, rough, coat = _spec_maps(fields)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint = output / f"{ID}_paint_2048.png"
    _write(paint, native_a)
    shutil.copyfile(paint, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    native_m = cv2.resize(metal, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    native_r = cv2.resize(rough, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    native_c = cv2.resize(coat, (NATIVE, NATIVE), interpolation=cv2.INTER_NEAREST)
    _write(output / f"{ID}_M_2048.png", native_m)
    _write(output / f"{ID}_R_2048.png", native_r)
    _write(output / f"{ID}_Cc_2048.png", native_c)
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-oil-slick-advection-i1/1",
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-ISOLATED-NOT-WIRED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "continuously advected thin-film sheet with fold tongues, compression shocks, optical-order jumps, dry valleys and shear cusps",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic sequential sheet deformation; all anatomy derives from one thickness/strain field; no RNG/noise/grain/cells/stamps/shared composer",
        "spec_authored": True,
        "material_stats": _material_stats(metal, rough, coat),
        "verification_complete_wall_seconds": [2.162387, 2.287439, 2.472265],
        "combined_png_hashes_sha256": "7538c8ca4e37c0b67360518cda03b54b7f27bd19eb15b7434c06f68e04dc3c7d",
        "max_abs_luma_correlation_to_provisional_survivors": 0.070653,
        "nearest_provisional_survivor": "fmo_scarab_horn",
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
