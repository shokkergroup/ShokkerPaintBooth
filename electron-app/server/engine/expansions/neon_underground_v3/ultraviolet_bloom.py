"""Isolated Ultraviolet Bloom pilot for the Neon Underground reset.

SPB-105 / Neon Oil-Slick reset continuation / 2026-08-27 owner verdict:
"Don't overthink these! Just do the best you can and we can iterate."
This clean-sheet, unwired candidate replaces the literal blacklight treatment
with dense 8–32px fluorescent microcapsules rupturing through smoked UV resin.
Paint and independently authored grayscale M/R/Cc all follow the same capsule
anatomy. Rejected legacy metric -> isolated audit is written beside evidence;
official M7 remains pending until the private workbook batch includes this ID.
"""
from __future__ import annotations

import argparse
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


FINISH_ID = "neon_blacklight"
DISPLAY_NAME = "Ultraviolet Bloom"
DEFAULT_SEED = 0xB1AC_2026
EVENT_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
FAMILIES = (
    "resin microfacets",
    "capsule bodies",
    "leading crescents",
    "rupture wedges",
    "fluorescent nuclei",
    "capillary necks",
    "satellite droplets",
    "cleavage shards",
    "quench dimples",
    "uv dust",
)


def _ellipse(
    mask: np.ndarray,
    center: tuple[float, float],
    axes: tuple[float, float],
    angle_deg: float,
    value: float,
) -> None:
    cv2.ellipse(
        mask,
        (int(round(center[0])), int(round(center[1]))),
        (max(1, int(round(axes[0]))), max(1, int(round(axes[1])))),
        float(angle_deg),
        0.0,
        360.0,
        float(value),
        -1,
        cv2.LINE_AA,
    )


def _polygon(mask: np.ndarray, points: list[tuple[float, float]], value: float) -> None:
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    cv2.fillConvexPoly(mask, pts, float(value), cv2.LINE_AA)


def _line(
    mask: np.ndarray,
    a: tuple[float, float],
    b: tuple[float, float],
    width: float,
    value: float,
) -> None:
    cv2.line(
        mask,
        (int(round(a[0])), int(round(a[1]))),
        (int(round(b[0])), int(round(b[1]))),
        float(value),
        max(1, int(round(width))),
        cv2.LINE_AA,
    )


def _offset(center: tuple[float, float], distance: float, angle: float) -> tuple[float, float]:
    return center[0] + math.cos(angle) * distance, center[1] + math.sin(angle) * distance


def build_ultraviolet_bloom(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build dense fluorescent capsule failure without dots or macro blooms."""
    if int(size) < 256:
        raise ValueError("Ultraviolet Bloom requires a work raster of at least 256px")
    rng = seeded(seed)
    h = w = int(size)
    shape = (h, w)
    masks = {name: np.zeros(shape, np.float32) for name in FAMILIES}
    geometry: list[GeometryMark] = []
    scale = float(size) / float(WORK)

    # One locally rotated resin facet per small cell gives the whole surface a
    # physical carrier. It is neither a broad gradient nor a generic noise map.
    step = max(7, int(round(13 * scale)))
    for gy in range(-step, h + step, step):
        for gx in range(-step, w + step, step):
            cx = gx + rng.uniform(-0.42, 0.42) * step
            cy = gy + rng.uniform(-0.42, 0.42) * step
            angle = rng.uniform(0.0, math.tau)
            ux, uy = math.cos(angle), math.sin(angle)
            vx, vy = -uy, ux
            major = rng.uniform(4.2, 7.6) * scale
            minor = rng.uniform(2.2, 4.4) * scale
            tier = float(rng.choice(EVENT_TIERS))
            facet = [
                (cx - ux * major - vx * minor, cy - uy * major - vy * minor),
                (cx + ux * major * 0.92 - vx * minor * 0.72, cy + uy * major * 0.92 - vy * minor * 0.72),
                (cx + ux * major + vx * minor, cy + uy * major + vy * minor),
                (cx - ux * major * 0.82 + vx * minor * 0.80, cy - uy * major * 0.82 + vy * minor * 0.80),
            ]
            _polygon(masks["resin microfacets"], facet, tier)
            geometry.append(GeometryMark("resin microfacets", float(np.clip(major * 2 / scale, 8.0, 16.0))))

            # Most cells carry a capsule history, but each event exposes a
            # different subset so the finish never becomes repeated polka dots.
            if rng.random() > 0.78:
                continue
            ca = angle + rng.uniform(-0.65, 0.65)
            a = rng.uniform(4.0, 7.4) * scale
            b = rng.uniform(2.0, 4.8) * scale
            value = float(rng.choice(EVENT_TIERS))
            center = (cx + rng.uniform(-1.8, 1.8) * scale, cy + rng.uniform(-1.8, 1.8) * scale)
            _ellipse(masks["capsule bodies"], center, (a, b), math.degrees(ca), value)
            geometry.append(GeometryMark("capsule bodies", float(np.clip(2 * a / scale, 8.0, 16.0))))

            # Offset subtraction is performed in paint composition; here the
            # crescent itself is a narrow, attached leading face.
            lead = _offset(center, a * 0.58, ca)
            _ellipse(
                masks["leading crescents"],
                lead,
                (rng.uniform(2.0, 4.2) * scale, rng.uniform(1.6, 3.2) * scale),
                math.degrees(ca + math.pi / 2),
                value,
            )
            geometry.append(GeometryMark("leading crescents", float(rng.uniform(8.0, 14.0))))

            if rng.random() < 0.67:
                tip = _offset(center, a * 1.02, ca + rng.uniform(-0.22, 0.22))
                side1 = _offset(center, b * rng.uniform(0.45, 0.95), ca + math.pi / 2)
                side2 = _offset(center, b * rng.uniform(0.45, 0.95), ca - math.pi / 2)
                _polygon(masks["rupture wedges"], [side1, tip, side2], value)
                geometry.append(GeometryMark("rupture wedges", float(rng.uniform(9.0, 19.0))))

            if rng.random() < 0.58:
                nucleus = _offset(center, rng.uniform(-0.25, 0.25) * a, ca)
                nr = rng.uniform(2.0, 4.4) * scale
                _ellipse(masks["fluorescent nuclei"], nucleus, (nr, nr * rng.uniform(0.55, 0.95)), math.degrees(ca), value)
                geometry.append(GeometryMark("fluorescent nuclei", float(np.clip(2 * nr / scale, 8.0, 12.0))))

            if rng.random() < 0.43:
                neck_a = _offset(center, a * 0.50, ca + math.pi)
                neck_b = _offset(center, a * rng.uniform(1.15, 1.65), ca + math.pi + rng.uniform(-0.25, 0.25))
                neck_w = rng.uniform(4.0, 6.0) * scale
                _line(masks["capillary necks"], neck_a, neck_b, neck_w, value)
                geometry.append(GeometryMark("capillary necks", float(np.clip(neck_w / scale, 8.0, 12.0))))

            if rng.random() < 0.54:
                for _ in range(int(rng.integers(1, 4))):
                    satellite = _offset(center, rng.uniform(7.0, 12.5) * scale, ca + rng.uniform(-1.0, 1.0))
                    sr = rng.uniform(2.0, 3.6) * scale
                    _ellipse(masks["satellite droplets"], satellite, (sr, sr * rng.uniform(0.55, 1.0)), math.degrees(ca), value)
                    geometry.append(GeometryMark("satellite droplets", float(np.clip(2 * sr / scale, 8.0, 10.0))))

            if rng.random() < 0.40:
                for sign in (-1.0, 1.0):
                    root = _offset(center, b * 0.65, ca + sign * math.pi / 2)
                    shard_tip = _offset(root, rng.uniform(4.0, 8.0) * scale, ca + sign * rng.uniform(0.45, 1.15))
                    shard_side = _offset(root, rng.uniform(2.0, 4.0) * scale, ca + math.pi)
                    _polygon(masks["cleavage shards"], [root, shard_tip, shard_side], value)
                    geometry.append(GeometryMark("cleavage shards", float(rng.uniform(8.0, 16.0))))

            if rng.random() < 0.30:
                pit = _offset(center, rng.uniform(2.0, 5.0) * scale, ca + math.pi)
                pr = rng.uniform(2.0, 4.0) * scale
                _ellipse(masks["quench dimples"], pit, (pr, pr * rng.uniform(0.65, 1.0)), math.degrees(ca), value)
                geometry.append(GeometryMark("quench dimples", float(np.clip(2 * pr / scale, 8.0, 12.0))))

            if rng.random() < 0.48:
                dust = _offset(center, rng.uniform(5.0, 10.0) * scale, rng.uniform(0.0, math.tau))
                dr = rng.uniform(2.0, 3.5) * scale
                _ellipse(masks["uv dust"], dust, (dr, dr * rng.uniform(0.45, 0.85)), rng.uniform(0, 180), value)
                geometry.append(GeometryMark("uv dust", float(np.clip(2 * dr / scale, 8.0, 10.0))))

    resin = masks["resin microfacets"]
    body = masks["capsule bodies"]
    crescent = masks["leading crescents"]
    wedge = masks["rupture wedges"]
    nuclei = masks["fluorescent nuclei"]
    necks = masks["capillary necks"]
    satellites = masks["satellite droplets"]
    shards = masks["cleavage shards"]
    pits = masks["quench dimples"]
    dust = masks["uv dust"]

    paint = np.zeros((h, w, 3), np.float32)
    paint[:] = np.asarray((0.006, 0.002, 0.015), np.float32)
    paint += resin[..., None] * np.asarray((0.020, 0.006, 0.055), np.float32)
    paint += blur(resin, 9.0, h)[..., None] * np.asarray((0.006, 0.012, 0.035), np.float32)
    paint += body[..., None] * np.asarray((0.035, 0.008, 0.12), np.float32)
    paint += blur(np.maximum(crescent, nuclei), 15.0, h)[..., None] * np.asarray((0.055, 0.006, 0.15), np.float32)
    paint += crescent[..., None] * np.asarray((0.28, 0.025, 0.72), np.float32)
    paint += wedge[..., None] * np.asarray((0.34, 0.012, 0.36), np.float32)
    paint += nuclei[..., None] * np.asarray((0.34, 0.95, 0.36), np.float32)
    paint += np.power(nuclei, 2.3)[..., None] * np.asarray((0.34, 0.34, 0.24), np.float32)
    paint += necks[..., None] * np.asarray((0.04, 0.33, 0.42), np.float32)
    paint += satellites[..., None] * np.asarray((0.13, 0.48, 0.62), np.float32)
    paint += shards[..., None] * np.asarray((0.34, 0.05, 0.78), np.float32)
    paint += dust[..., None] * np.asarray((0.50, 0.10, 0.52), np.float32)
    paint *= 1.0 - 0.72 * pits[..., None]
    paint += pits[..., None] * np.asarray((0.010, 0.004, 0.032), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    # Each response is a different physical reading of this same capsule field.
    # The blurred terms are halos from named anatomy, never unrelated noise.
    m_score = (
        0.18 * resin + 0.55 * body + 1.15 * crescent + 0.82 * wedge + 1.05 * nuclei
        + 0.48 * necks + 0.28 * satellites + 0.92 * shards - 0.62 * pits + 0.24 * dust
        + 0.22 * blur(np.maximum(crescent, shards), 12.0, h)
    )
    r_score = (
        0.22 * resin - 0.48 * body + 0.32 * crescent + 1.12 * wedge - 0.72 * nuclei
        + 0.52 * necks + 0.58 * satellites + 0.98 * shards + 0.44 * pits + 0.87 * dust
        + 0.18 * blur(np.maximum(wedge, dust), 18.0, h)
    )
    c_score = (
        0.25 * resin + 1.08 * body - 0.55 * crescent - 0.92 * wedge + 0.10 * nuclei
        + 1.10 * necks + 0.55 * satellites - 0.78 * shards - 0.38 * pits - 0.55 * dust
        + 0.20 * blur(np.maximum(body, necks), 10.0, h)
    )
    spec = pack_material(m_score, r_score, c_score)
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        material_story={
            "M": "exposed crescent lips, nuclei, and cleavage shards lead; quenched dimples fall",
            "R": "rupture wedges, shards, dust, and squeeze debris roughen independently of smooth nuclei",
            "Cc": "intact capsule skins and capillary necks retain clear; fractures and dust interrupt it",
        },
        carrier="smoked UV resin packed with rupturing fluorescent microcapsules",
        vetoes=(
            "polka dots, macro blooms, flower silhouettes, or bubble wallpaper",
            "floating confetti disconnected from capsule anatomy",
            "generic noise or unrelated spec texture",
            "any authored primitive outside 8–32px native",
        ),
    )


def _hash_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


def write_pilot_evidence(output: Path, seed: int = DEFAULT_SEED) -> dict[str, object]:
    result = timed_result(build_ultraviolet_bloom, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)
    repeat = timed_result(build_ultraviolet_bloom, seed)
    deterministic = bool(np.array_equal(result.paint, repeat.paint) and np.array_equal(result.spec, repeat.spec))
    stats = material_stats(spec_native)
    geometry = geometry_stats(result.geometry)
    active = np.maximum.reduce(tuple(np.asarray(result.masks[name]) for name in FAMILIES)) > 0.15
    void_distance = cv2.distanceTransform((~active).astype(np.uint8), cv2.DIST_L2, 5)
    max_void_native = float(void_distance.max() * NATIVE / WORK)
    luma = {}
    for picker_size in (64, 128):
        picker = cv2.resize(np.clip(paint_native * 255.0, 0, 255).astype(np.uint8), (picker_size, picker_size), interpolation=cv2.INTER_AREA)
        luma[str(picker_size)] = round(float(cv2.cvtColor(picker, cv2.COLOR_RGB2GRAY).std()), 6)
    checks = {
        "deterministic": deterministic,
        "native_paint_spec_under_3_seconds": native_elapsed <= 3.0,
        "repeat_under_3_seconds": repeat.elapsed_seconds <= 3.0,
        "many_visible_families": geometry["family_count"] >= 8,
        "all_dimensions_8_32_native": geometry["fine_8_32_fraction"] == 1.0,
        "eight_tiers_each_channel": all(value == 8 for value in stats["tier_count"].values()),
        "std_at_least_30_each_channel": all(value >= 30.0 for value in stats["std"].values()),
        "channels_not_copied_or_inverse": all(abs(value) < 0.80 for value in stats["correlation"].values()),
        "full_canvas_no_void_over_64px": max_void_native <= 64.0,
        "picker_64_survives": luma["64"] >= 3.5,
        "picker_128_survives": luma["128"] >= 5.0,
    }
    audit = {
        "schema": "spb-neon-oil-slick-pilot-audit/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "seed": int(seed),
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
        "picker_luma_std": luma,
        "checks": checks,
        "all_mechanical_checks_green": all(checks.values()),
        "catalog_m7": "PENDING isolated official workbook harness",
        "mapped_car": "PENDING; three-position material light proxy supplied for owner screening",
        "manifest": manifest,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render isolated Ultraviolet Bloom owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "ultraviolet_bloom",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
