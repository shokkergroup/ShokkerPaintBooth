"""Torque Scar — isolated Neon Underground v3 owner-review pilot.

SPB-105 / owner verdict 2026-08-27: the rejected Neon rebuild reduced racing
ideas to literal icons and repeated wallpaper. Torque Scar is instead one
carbon-black elastomer transfer sheet: irregular local shear packets expose
different physical consequences in paint, metalness, roughness and clearcoat.
No live registry/catalog wiring is permitted before owner review.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Iterable

import cv2
import numpy as np

from engine.paint_v2.neon_material_core_v3 import (
    GeometryMark,
    NATIVE,
    PilotResult,
    WORK,
    blur,
    geometry_stats,
    mask_coverage,
    material_stats,
    pack_material,
    render_evidence,
    resize_result,
    seeded,
    timed_result,
)


FINISH_ID = "neon2_torque_scar"
DISPLAY_NAME = "Torque Scar"
DEFAULT_SEED = 0x70A9_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)


def _work_px(native: float, size: int) -> float:
    return float(native) * float(size) / float(NATIVE)


def _quad(
    mask: np.ndarray,
    center: tuple[float, float],
    length_native: float,
    width_native: float,
    theta: float,
    value: float,
    size: int,
    skew: float = 0.0,
    taper: float = 0.72,
) -> np.ndarray:
    """Draw one asymmetric four-sided transfer packet and return its vertices."""
    half_l = _work_px(length_native, size) * 0.5
    half_w = _work_px(width_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    points = np.asarray(
        (
            (cx - ux * half_l - vx * half_w * (0.82 + skew), cy - uy * half_l - vy * half_w * (0.82 + skew)),
            (cx + ux * half_l - vx * half_w * taper, cy + uy * half_l - vy * half_w * taper),
            (cx + ux * half_l + vx * half_w * (0.54 + 0.18 * skew), cy + uy * half_l + vy * half_w * (0.54 + 0.18 * skew)),
            (cx - ux * half_l + vx * half_w, cy - uy * half_l + vy * half_w),
        ),
        np.float32,
    )
    cv2.fillConvexPoly(mask, np.rint(points).astype(np.int32), float(value), cv2.LINE_AA)
    return points


def _line(
    mask: np.ndarray,
    p0: tuple[float, float],
    p1: tuple[float, float],
    width_native: float,
    value: float,
    size: int,
) -> None:
    width = max(1, int(round(_work_px(width_native, size))))
    cv2.line(
        mask,
        (int(round(p0[0])), int(round(p0[1]))),
        (int(round(p1[0])), int(round(p1[1]))),
        float(value), width, cv2.LINE_AA,
    )


def _diamond(
    mask: np.ndarray,
    center: tuple[float, float],
    diameter_native: float,
    theta: float,
    value: float,
    size: int,
) -> None:
    radius = _work_px(diameter_native, size) * 0.5
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    cx, cy = center
    points = np.asarray(
        (
            (cx + ux * radius, cy + uy * radius),
            (cx + vx * radius * 0.72, cy + vy * radius * 0.72),
            (cx - ux * radius, cy - uy * radius),
            (cx - vx * radius * 0.72, cy - vy * radius * 0.72),
        ),
        np.float32,
    )
    cv2.fillConvexPoly(mask, np.rint(points).astype(np.int32), float(value), cv2.LINE_AA)


def _point(
    center: tuple[float, float], theta: float, along: float, across: float, size: int,
) -> tuple[float, float]:
    ux, uy = math.cos(theta), math.sin(theta)
    vx, vy = -uy, ux
    return (
        center[0] + ux * _work_px(along, size) + vx * _work_px(across, size),
        center[1] + uy * _work_px(along, size) + vy * _work_px(across, size),
    )


def _geometry(counter: Counter[tuple[str, float]]) -> tuple[GeometryMark, ...]:
    return tuple(
        GeometryMark(family, dimension, count)
        for (family, dimension), count in sorted(counter.items())
    )


def _mark(counter: Counter[tuple[str, float]], family: str, dimension: float) -> None:
    # Record the largest authored dimension, not merely stroke thickness. This
    # makes the owner 8–32px doctrine auditable rather than easy to game.
    counter[(family, round(float(dimension), 3))] += 1


def build_torque_scar(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    if int(size) != WORK:
        raise ValueError(f"Torque Scar is authored at WORK={WORK}, got {size}")
    rng = seeded(seed)
    shape = (size, size)
    masks = {
        "carbon elastomer facets": np.zeros(shape, np.float32),
        "facet shear edges": np.zeros(shape, np.float32),
        "raw rubber transfers": np.zeros(shape, np.float32),
        "tread microblocks": np.zeros(shape, np.float32),
        "red heat lips": np.zeros(shape, np.float32),
        "rubber crumbs": np.zeros(shape, np.float32),
        "violet glaze islands": np.zeros(shape, np.float32),
        "cross-shear cuts": np.zeros(shape, np.float32),
        "smoke-etch whiskers": np.zeros(shape, np.float32),
        "exposed-clear gaps": np.zeros(shape, np.float32),
        "icy substrate scores": np.zeros(shape, np.float32),
        "embedded hot grit": np.zeros(shape, np.float32),
    }
    geometry: Counter[tuple[str, float]] = Counter()

    # A jittered 20px-native field is dense enough to become a continuous
    # material, while every authored component stays independently 8–32px.
    cell = max(5, int(round(_work_px(20.0, size))))
    margin = max(8, int(round(_work_px(24.0, size))))

    for gy, y0 in enumerate(range(-cell, size + cell, cell)):
        for gx, x0 in enumerate(range(-cell, size + cell, cell)):
            cx = float(x0 + rng.uniform(-0.46, 0.46) * cell)
            cy = float(y0 + rng.uniform(-0.46, 0.46) * cell)
            if cx < -margin or cy < -margin or cx > size + margin or cy > size + margin:
                continue

            domain_x, domain_y = gx // 5, gy // 5
            domain_hash = (
                (domain_x * 0x9E3779B1)
                ^ (domain_y * 0x85EBCA77)
                ^ ((domain_x + domain_y * 3) * 0xC2B2AE3D)
            ) & 0xFFFFFFFF
            domain_theta = -1.08 + (domain_hash % 17) / 16.0 * 2.16
            theta = float(domain_theta + rng.uniform(-0.30, 0.30))
            tier = float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))])

            # Continuous carbon/elastomer carrier: one asymmetric platelet per
            # site plus a single shear edge. No unrelated FBM/noise underlay.
            carrier_len = float(rng.uniform(14.0, 24.0))
            carrier_w = float(rng.uniform(8.0, 13.0))
            carrier_theta = theta + float(rng.uniform(-0.22, 0.22))
            carrier_points = _quad(
                masks["carbon elastomer facets"], (cx, cy), carrier_len, carrier_w,
                carrier_theta, tier, size, float(rng.uniform(-0.16, 0.16)), float(rng.uniform(0.52, 0.84)),
            )
            _mark(geometry, "carbon elastomer facets", max(carrier_len, carrier_w))
            if rng.random() < 0.68:
                edge = int(rng.integers(0, 4))
                p0 = tuple(carrier_points[edge])
                p1 = tuple(carrier_points[(edge + 1) % 4])
                edge_dim = float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)) * NATIVE / size)
                _line(masks["facet shear edges"], p0, p1, 8.0, tier, size)
                _mark(geometry, "facet shear edges", min(32.0, max(8.0, edge_dim)))

            if rng.random() >= 0.76:
                continue

            # One off-centre raw transfer. Attached events occupy only one
            # side/end so no site can become a radial insect/flower glyph.
            raw_len = float(rng.uniform(18.0, 32.0))
            raw_w = float(rng.uniform(8.0, 14.0))
            raw_center = _point((cx, cy), theta, rng.uniform(-2.5, 2.5), rng.uniform(-3.0, 3.0), size)
            _quad(
                masks["raw rubber transfers"], raw_center, raw_len, raw_w, theta,
                tier, size, float(rng.uniform(-0.22, 0.18)), float(rng.uniform(0.38, 0.76)),
            )
            _mark(geometry, "raw rubber transfers", raw_len)

            side = -1.0 if rng.random() < 0.5 else 1.0
            front = _point(raw_center, theta, raw_len * 0.34, side * raw_w * 0.40, size)
            trail = _point(raw_center, theta, -raw_len * 0.42, -side * raw_w * 0.18, size)

            if rng.random() < 0.34:
                block_len = float(rng.uniform(10.0, 18.0))
                block_w = float(rng.uniform(8.0, 13.0))
                block_center = _point(trail, theta, -rng.uniform(3.0, 7.0), side * rng.uniform(2.0, 5.0), size)
                _quad(
                    masks["tread microblocks"], block_center, block_len, block_w,
                    theta + rng.uniform(-0.16, 0.16),
                    float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))]),
                    size, float(rng.uniform(-0.18, 0.18)), float(rng.uniform(0.62, 0.90)),
                )
                _mark(geometry, "tread microblocks", max(block_len, block_w))

            if rng.random() < 0.46:
                lip_len = float(rng.uniform(12.0, 28.0))
                lip_center = _point(raw_center, theta, rng.uniform(-2.0, 4.0), side * raw_w * 0.48, size)
                p0 = _point(lip_center, theta, -lip_len * 0.52, 0.0, size)
                p1 = _point(lip_center, theta, lip_len * 0.48, rng.uniform(-1.2, 1.2), size)
                _line(masks["red heat lips"], p0, p1, 8.0, tier, size)
                _mark(geometry, "red heat lips", lip_len)

            if rng.random() < 0.37:
                glaze_len = float(rng.uniform(12.0, 26.0))
                glaze_w = float(rng.uniform(8.0, 12.0))
                glaze_center = _point(raw_center, theta, rng.uniform(-3.0, 3.0), -side * raw_w * 0.34, size)
                _quad(
                    masks["violet glaze islands"], glaze_center, glaze_len, glaze_w,
                    theta + rng.uniform(-0.10, 0.10),
                    float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))]),
                    size, float(rng.uniform(-0.12, 0.12)), float(rng.uniform(0.52, 0.78)),
                )
                _mark(geometry, "violet glaze islands", glaze_len)

            if rng.random() < 0.32:
                cut_len = float(rng.uniform(10.0, 22.0))
                cut_theta = theta + side * rng.uniform(0.72, 1.10)
                cut_center = _point(raw_center, theta, rng.uniform(-4.0, 6.0), side * rng.uniform(-1.0, 3.0), size)
                p0 = _point(cut_center, cut_theta, -cut_len * 0.44, 0.0, size)
                p1 = _point(cut_center, cut_theta, cut_len * 0.56, 0.0, size)
                _line(masks["cross-shear cuts"], p0, p1, 8.0, tier, size)
                _mark(geometry, "cross-shear cuts", cut_len)

            if rng.random() < 0.27:
                whisker_len = float(rng.uniform(10.0, 24.0))
                whisker_theta = theta + side * rng.uniform(0.22, 0.48)
                p0 = _point(trail, whisker_theta, -2.0, 0.0, size)
                p1 = _point(trail, whisker_theta, -whisker_len, side * rng.uniform(0.0, 2.0), size)
                _line(masks["smoke-etch whiskers"], p0, p1, 8.0, tier, size)
                _mark(geometry, "smoke-etch whiskers", whisker_len)

            if rng.random() < 0.26:
                gap_len = float(rng.uniform(10.0, 18.0))
                gap_w = float(rng.uniform(8.0, 11.0))
                gap_center = _point(raw_center, theta, rng.uniform(-5.0, 5.0), side * rng.uniform(-1.5, 2.5), size)
                _quad(
                    masks["exposed-clear gaps"], gap_center, gap_len, gap_w,
                    theta + rng.uniform(-0.18, 0.18), tier, size,
                    float(rng.uniform(-0.16, 0.16)), float(rng.uniform(0.42, 0.72)),
                )
                _mark(geometry, "exposed-clear gaps", gap_len)

            if rng.random() < 0.24:
                score_len = float(rng.uniform(10.0, 24.0))
                score_theta = theta + side * rng.uniform(0.42, 0.76)
                score_center = _point(front, theta, rng.uniform(0.0, 4.0), -side * rng.uniform(0.0, 3.0), size)
                p0 = _point(score_center, score_theta, -score_len * 0.58, 0.0, size)
                p1 = _point(score_center, score_theta, score_len * 0.42, 0.0, size)
                _line(masks["icy substrate scores"], p0, p1, 8.0, tier, size)
                _mark(geometry, "icy substrate scores", score_len)

            crumb_total = int(rng.integers(1, 4)) if rng.random() < 0.48 else 0
            for crumb_index in range(crumb_total):
                crumb_size = float(rng.uniform(8.0, 11.0))
                crumb_center = _point(
                    trail, theta,
                    -rng.uniform(4.0 + crumb_index * 2.0, 10.0 + crumb_index * 4.0),
                    side * rng.uniform(-6.0, 8.0), size,
                )
                _diamond(
                    masks["rubber crumbs"], crumb_center, crumb_size,
                    theta + rng.uniform(-0.7, 0.7),
                    float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))]), size,
                )
                _mark(geometry, "rubber crumbs", crumb_size)

            if rng.random() < 0.16:
                grit_size = float(rng.uniform(8.0, 10.0))
                grit_center = _point(front, theta, rng.uniform(1.0, 7.0), side * rng.uniform(-5.0, 5.0), size)
                _diamond(
                    masks["embedded hot grit"], grit_center, grit_size,
                    theta + rng.uniform(-0.6, 0.6),
                    float(EVENT_TIERS[int(rng.integers(0, len(EVENT_TIERS)))]), size,
                )
                _mark(geometry, "embedded hot grit", grit_size)

    carrier = masks["carbon elastomer facets"]
    carrier_edge = masks["facet shear edges"]
    raw = masks["raw rubber transfers"]
    tread = masks["tread microblocks"]
    heat = masks["red heat lips"]
    crumbs = masks["rubber crumbs"]
    glaze = masks["violet glaze islands"]
    cuts = masks["cross-shear cuts"]
    whiskers = masks["smoke-etch whiskers"]
    gaps = masks["exposed-clear gaps"]
    scores = masks["icy substrate scores"]
    grit = masks["embedded hot grit"]

    paint = np.zeros((size, size, 3), np.float32)
    paint[:] = np.asarray((0.004, 0.007, 0.013), np.float32)
    paint += carrier[..., None] * np.asarray((0.027, 0.035, 0.052), np.float32)
    paint += carrier_edge[..., None] * np.asarray((0.026, 0.045, 0.074), np.float32)
    paint += raw[..., None] * np.asarray((0.34, 0.018, 0.048), np.float32)
    paint += tread[..., None] * np.asarray((0.055, 0.085, 0.125), np.float32)
    paint += glaze[..., None] * np.asarray((0.30, 0.025, 0.26), np.float32)
    paint *= 1.0 - gaps[..., None] * 0.86
    paint *= 1.0 - cuts[..., None] * 0.68
    paint += heat[..., None] * np.asarray((1.0, 0.105, 0.018), np.float32) * 0.94
    paint += crumbs[..., None] * np.asarray((0.88, 0.23, 0.025), np.float32) * 0.76
    paint += whiskers[..., None] * np.asarray((0.22, 0.33, 0.48), np.float32) * 0.46
    paint += scores[..., None] * np.asarray((0.66, 0.86, 1.0), np.float32) * 0.88
    paint += grit[..., None] * np.asarray((1.0, 0.61, 0.06), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    intact_clear = np.clip(1.0 - blur(np.clip(raw + tread + cuts + crumbs, 0.0, 1.0), 9.0, size), 0.0, 1.0)
    carrier_reach = blur(carrier, 7.0, size)
    metal_score = (
        0.34 * carrier + 0.46 * carrier_edge + 2.45 * scores + 1.86 * grit
        + 0.62 * gaps + 0.18 * carrier_reach - 0.88 * raw - 0.58 * glaze - 0.26 * tread
    )
    rough_score = (
        1.58 * raw + 1.28 * tread + 1.72 * crumbs + 1.64 * cuts
        + 1.02 * whiskers + 0.28 * carrier_edge - 1.28 * glaze
        - 0.54 * heat - 0.28 * intact_clear
    )
    coat_score = (
        0.55 * intact_clear + 2.00 * glaze + 1.00 * carrier + 1.10 * scores
        - 0.62 * raw - 0.58 * tread - 0.55 * cuts - 0.42 * crumbs
        - 0.28 * whiskers + 0.50 * heat
    )
    spec = pack_material(metal_score, rough_score, coat_score)

    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=_geometry(geometry),
        material_story={
            "M": "icy substrate scores, embedded hot grit, and exposed metallic carrier edges",
            "R": "raw rubber transfers, tread blocks, crumbs, cross-cuts, and smoke-etch whiskers",
            "Cc": "intact clear and violet glaze islands, interrupted by raw transfer and cuts",
        },
        carrier="clear-coated carbon-black elastomer transfer over a metallic dark microfaceted base",
        vetoes=(
            "complete or mentally completable circles",
            "rings, donuts, bubbles, radial packet clusters",
            "tire illustration",
            "floating smoke ribbon",
            "generic noise underlay",
        ),
    )


def _hash_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


def write_pilot_evidence(output: Path, seed: int = DEFAULT_SEED) -> dict[str, object]:
    result = timed_result(build_torque_scar, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_torque_scar, seed)
    deterministic = bool(
        np.array_equal(result.paint, repeat.paint)
        and np.array_equal(result.spec, repeat.spec)
    )
    active = np.maximum.reduce(tuple(np.asarray(mask) for mask in result.masks.values())) > 0.15
    void_distance = cv2.distanceTransform((~active).astype(np.uint8), cv2.DIST_L2, 5)
    max_void_native = float(void_distance.max() * NATIVE / WORK)
    picker64 = cv2.resize(paint_native, (64, 64), interpolation=cv2.INTER_AREA)
    picker128 = cv2.resize(paint_native, (128, 128), interpolation=cv2.INTER_AREA)
    luma64 = cv2.cvtColor(np.clip(picker64 * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    luma128 = cv2.cvtColor(np.clip(picker128 * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    stats = material_stats(spec_native)
    geometry = geometry_stats(result.geometry)
    checks = {
        "deterministic": deterministic,
        "native_paint_spec_under_3_seconds": native_elapsed <= 3.0,
        "repeat_under_3_seconds": repeat.elapsed_seconds <= 3.0,
        "ten_plus_attached_families": geometry["family_count"] >= 10,
        "all_dimensions_8_32_native": geometry["fine_8_32_fraction"] == 1.0,
        "eight_tiers_each_channel": all(value == 8 for value in stats["tier_count"].values()),
        "std_at_least_30_each_channel": all(value >= 30.0 for value in stats["std"].values()),
        "channels_not_copied_or_inverse": all(abs(value) < 0.80 for value in stats["correlation"].values()),
        "full_canvas_no_void_over_64px": max_void_native <= 64.0,
        "picker_64_survives": float(luma64.std()) >= 3.0,
        "picker_128_survives": float(luma128.std()) >= 4.0,
    }
    audit = {
        "schema": "spb-neon-oil-slick-pilot-audit/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "seed": seed,
        "builder_elapsed_seconds": round(float(result.elapsed_seconds), 6),
        "native_paint_spec_elapsed_seconds": round(float(native_elapsed), 6),
        "repeat_elapsed_seconds": round(float(repeat.elapsed_seconds), 6),
        "deterministic": deterministic,
        "paint_sha256": _hash_array(result.paint),
        "spec_sha256": _hash_array(result.spec),
        "material_stats_native": stats,
        "geometry_stats": geometry,
        "causal_mask_coverage": mask_coverage(result.masks),
        "max_unmarked_void_native_px": round(max_void_native, 3),
        "picker_luma_std": {"64": round(float(luma64.std()), 6), "128": round(float(luma128.std()), 6)},
        "checks": checks,
        "all_mechanical_checks_green": all(checks.values()),
        "catalog_m7": "PENDING isolated official workbook harness",
        "mapped_car": "PENDING; three-position material light proxy supplied for owner screening",
        "manifest": manifest,
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render isolated Torque Scar owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "torque_scar",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
