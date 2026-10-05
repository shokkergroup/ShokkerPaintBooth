"""Isolated Sodium Scuff owner-review pilot for Neon Underground v3.

SPB-105 / Neon reset tick #2 / owner verdict 2026-08-27: "Claude's
rebuild has failed miserably."  Metric movement: rejected/unwired legacy
visual (no trustworthy M7) -> isolated causal pilot pending owner survival
and catalog M7.  Nothing in this module registers or replaces the live ID.

The carrier is one black polyurethane sheet containing dragged, partially
embedded retroreflective orange microbeads.  Every visible response and each
M/R/Cc score is derived from the same seven named process masks.  There is no
generic FBM/spec backdrop and no shared finish composer.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
from typing import Iterable, Sequence

import cv2
import numpy as np

from engine.paint_v2.neon_material_core_v3 import (
    NATIVE,
    WORK,
    GeometryMark,
    PilotResult,
    material_stats,
    pack_material,
    render_evidence,
    resize_result,
    seeded,
    timed_result,
)


FINISH_ID = "neon_orange_hazard"
DISPLAY_NAME = "Sodium Scuff"
DEFAULT_SEED = 0x5A0D1A

_TIERS = np.asarray((0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92), np.float32)
_TONE = np.asarray((0.08, 0.19, 0.31, 0.43, 0.56, 0.69, 0.82, 0.97), np.float32)
_FAMILIES = (
    "bead_clusters",
    "exposed_cores",
    "resin_tails",
    "crushed_shards",
    "polished_skid_lips",
    "deep_gouges",
    "rebound_specks",
)


def _axis_shifts(lo: float, hi: float, size: int) -> list[int]:
    shifts = [0]
    if lo < 0:
        shifts.append(size)
    if hi >= size:
        shifts.append(-size)
    return shifts


def _draw_line_periodic(
    canvas: np.ndarray,
    p0: Sequence[float],
    p1: Sequence[float],
    value: float,
    thickness: int,
) -> None:
    size = int(canvas.shape[0])
    margin = float(thickness + 2)
    xs = _axis_shifts(min(p0[0], p1[0]) - margin, max(p0[0], p1[0]) + margin, size)
    ys = _axis_shifts(min(p0[1], p1[1]) - margin, max(p0[1], p1[1]) + margin, size)
    for dx in xs:
        for dy in ys:
            q0 = (int(round(p0[0] + dx)), int(round(p0[1] + dy)))
            q1 = (int(round(p1[0] + dx)), int(round(p1[1] + dy)))
            cv2.line(canvas, q0, q1, float(value), int(thickness), cv2.LINE_AA)


def _draw_ellipse_periodic(
    canvas: np.ndarray,
    center: Sequence[float],
    axes: Sequence[int],
    angle_degrees: float,
    value: float,
) -> None:
    size = int(canvas.shape[0])
    radius = float(max(axes) + 2)
    xs = _axis_shifts(center[0] - radius, center[0] + radius, size)
    ys = _axis_shifts(center[1] - radius, center[1] + radius, size)
    for dx in xs:
        for dy in ys:
            c = (int(round(center[0] + dx)), int(round(center[1] + dy)))
            cv2.ellipse(
                canvas,
                c,
                (int(axes[0]), int(axes[1])),
                float(angle_degrees),
                0.0,
                360.0,
                float(value),
                -1,
                cv2.LINE_AA,
            )


def _draw_polygon_periodic(canvas: np.ndarray, points: np.ndarray, value: float) -> None:
    size = int(canvas.shape[0])
    points = np.asarray(points, np.float32)
    xs = _axis_shifts(float(points[:, 0].min()) - 2, float(points[:, 0].max()) + 2, size)
    ys = _axis_shifts(float(points[:, 1].min()) - 2, float(points[:, 1].max()) + 2, size)
    for dx in xs:
        for dy in ys:
            shifted = np.rint(points + np.asarray((dx, dy), np.float32)).astype(np.int32)
            cv2.fillConvexPoly(canvas, shifted, float(value), cv2.LINE_AA)


def _wrap_blur(values: np.ndarray, sigma_native: float) -> np.ndarray:
    sigma = max(0.35, float(sigma_native) * values.shape[0] / float(NATIVE))
    pad = max(2, int(np.ceil(sigma * 4.0)))
    wrapped = np.pad(np.asarray(values, np.float32), ((pad, pad), (pad, pad)), mode="wrap")
    blurred = cv2.GaussianBlur(wrapped, (0, 0), sigma)
    return blurred[pad:-pad, pad:-pad]


def _blend(paint: np.ndarray, mask: np.ndarray, color: np.ndarray, opacity: float) -> None:
    alpha = np.clip(np.asarray(mask, np.float32) * float(opacity), 0.0, 1.0)
    if color.ndim == 1:
        color = np.broadcast_to(color, paint.shape)
    paint *= 1.0 - alpha[..., None]
    paint += np.asarray(color, np.float32) * alpha[..., None]


def _warm_color(tone: np.ndarray, low: Sequence[float], high: Sequence[float]) -> np.ndarray:
    t = np.clip(np.asarray(tone, np.float32), 0.0, 1.0)[..., None]
    lo = np.asarray(low, np.float32)
    hi = np.asarray(high, np.float32)
    return lo + (hi - lo) * t


def _hash_array(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def _geometry(counter: Counter[tuple[str, float]]) -> list[GeometryMark]:
    return [
        GeometryMark(family=family, width_native=width, count=count)
        for (family, width), count in sorted(counter.items())
    ]


def _record(counter: Counter[tuple[str, float]], family: str, width_native: float) -> None:
    counter[(family, round(float(width_native), 3))] += 1


def build_sodium_scuff(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic paint/spec result at the v3 working resolution."""
    if int(size) != WORK:
        raise ValueError(f"Sodium Scuff is authored at WORK={WORK}, got {size}")

    rng = seeded(seed)
    masks = {name: np.zeros((size, size), np.float32) for name in _FAMILIES}
    tones = {name: np.zeros((size, size), np.float32) for name in _FAMILIES}
    ledger: Counter[tuple[str, float]] = Counter()

    # More short local histories beat fewer long ropes: this raises full-sheet
    # coverage while keeping the buyer read as abrasion instead of glowing wire.
    rows = 22
    cols = 22
    cell_x = size / float(cols)
    cell_y = size / float(rows)

    for row in range(rows):
        for col in range(cols):
            anchor_x = (col + 0.5 + rng.uniform(-0.43, 0.43)) * cell_x
            anchor_y = (row + 0.5 + rng.uniform(-0.43, 0.43)) * cell_y
            phase = rng.uniform(-np.pi, np.pi)
            field = (
                -0.34
                + 0.22 * np.sin(2.0 * np.pi * (2.0 * anchor_x + 3.0 * anchor_y) / size)
                + 0.15 * np.cos(2.0 * np.pi * (5.0 * anchor_x - 2.0 * anchor_y) / size)
            )
            mode = int(rng.choice(5, p=(0.31, 0.25, 0.20, 0.13, 0.11)))
            field += (0.0, 0.0, 0.0, 0.62, -0.57)[mode]
            theta = float(field + rng.normal(0.0, 0.11))
            direction = np.asarray((np.cos(theta), np.sin(theta)), np.float32)
            normal = np.asarray((-direction[1], direction[0]), np.float32)
            count = int(rng.integers(3, 7))
            spacing = float(rng.uniform(7.0, 13.0))

            for packet in range(count):
                along = (packet - 0.5 * (count - 1)) * spacing
                side = np.sin(packet * 1.61 + phase) * rng.uniform(0.5, 2.7)
                center = np.asarray((anchor_x, anchor_y), np.float32) + direction * along + normal * side
                center %= float(size)

                tier_index = int(rng.integers(0, len(_TIERS)))
                strength = float(_TIERS[tier_index])
                tone = float(np.clip(_TONE[tier_index] + rng.uniform(-0.08, 0.08), 0.04, 1.0))
                angle = float(np.degrees(theta) + rng.uniform(-8.0, 8.0))

                # Pooled polyurethane is pulled behind every bead packet, so the
                # orange material never becomes a disconnected dot field.
                tail_length = float(rng.uniform(4.5, 15.5))
                tail_width = int(rng.integers(4, 9))
                tail_end = center - direction * tail_length + normal * rng.uniform(-1.5, 1.5)
                _draw_line_periodic(masks["resin_tails"], center, tail_end, strength, tail_width)
                _draw_line_periodic(tones["resin_tails"], center, tail_end, tone, tail_width)
                _record(ledger, "resin_tails", tail_width * 2.0)

                bead_count = int(rng.integers(1, 4))
                for bead in range(bead_count):
                    offset = normal * rng.uniform(-4.4, 4.4) + direction * rng.uniform(-3.5, 3.5)
                    bead_center = center + offset
                    major = int(rng.integers(4, 9))
                    minor = int(rng.integers(2, min(6, major + 1)))
                    _draw_ellipse_periodic(
                        masks["bead_clusters"], bead_center, (major, minor), angle, strength
                    )
                    _draw_ellipse_periodic(
                        tones["bead_clusters"], bead_center, (major, minor), angle, tone
                    )
                    _record(ledger, "bead_clusters", minor * 4.0)

                    if rng.random() < 0.39:
                        core_major = int(rng.integers(2, 5))
                        core_minor = int(rng.integers(2, min(4, core_major + 1)))
                        core_center = bead_center - normal * rng.uniform(0.5, 2.4)
                        core_strength = float(np.clip(strength + rng.uniform(0.10, 0.30), 0.0, 1.0))
                        _draw_ellipse_periodic(
                            masks["exposed_cores"],
                            core_center,
                            (core_major, core_minor),
                            angle,
                            core_strength,
                        )
                        _draw_ellipse_periodic(
                            tones["exposed_cores"], core_center, (core_major, core_minor), angle, tone
                        )
                        _record(ledger, "exposed_cores", core_minor * 4.0)

                if rng.random() < 0.77:
                    lip_length = float(rng.uniform(7.0, 15.5))
                    lip_width = int(rng.integers(4, 7))
                    lip_center = center + normal * rng.uniform(3.0, 6.0)
                    half = direction * (0.5 * lip_length)
                    _draw_line_periodic(
                        masks["polished_skid_lips"], lip_center - half, lip_center + half, strength, lip_width
                    )
                    _draw_line_periodic(
                        tones["polished_skid_lips"], lip_center - half, lip_center + half, tone, lip_width
                    )
                    _record(ledger, "polished_skid_lips", lip_width * 2.0)

                gouged = rng.random() < 0.46
                if gouged:
                    gouge_length = float(rng.uniform(8.0, 16.0))
                    gouge_width = int(rng.integers(4, 8))
                    gouge_center = center - normal * rng.uniform(2.0, 5.5)
                    half = direction * (0.5 * gouge_length)
                    gouge_strength = float(np.clip(strength + rng.uniform(0.02, 0.22), 0.0, 1.0))
                    _draw_line_periodic(
                        masks["deep_gouges"], gouge_center - half, gouge_center + half, gouge_strength, gouge_width
                    )
                    _draw_line_periodic(
                        tones["deep_gouges"], gouge_center - half, gouge_center + half, tone, gouge_width
                    )
                    _record(ledger, "deep_gouges", gouge_width * 2.0)

                    if rng.random() < 0.52:
                        shard_length = float(rng.uniform(4.0, 10.0))
                        shard_width = float(rng.uniform(4.0, min(9.0, shard_length + 2.0)))
                        shard_center = gouge_center + direction * rng.uniform(-5.0, 5.0)
                        triangle = np.stack(
                            (
                                shard_center + direction * shard_length * 0.55,
                                shard_center - direction * shard_length * 0.45 + normal * shard_width * 0.5,
                                shard_center - direction * shard_length * 0.45 - normal * shard_width * 0.5,
                            )
                        )
                        _draw_polygon_periodic(masks["crushed_shards"], triangle, strength)
                        _draw_polygon_periodic(tones["crushed_shards"], triangle, tone)
                        _record(ledger, "crushed_shards", shard_width * 2.0)

            # Rebound fragments form a decaying chain at the physical end of
            # each drag history; none are free-floating filler.
            endpoint = (
                np.asarray((anchor_x, anchor_y), np.float32)
                + direction * (0.5 * (count - 1) * spacing + rng.uniform(5.0, 10.0))
            )
            rebound_count = int(rng.integers(2, 6))
            for rebound in range(rebound_count):
                distance = float(5.0 + rebound * rng.uniform(3.5, 6.5))
                bead_center = endpoint + direction * distance + normal * rng.uniform(-4.5, 4.5)
                major = int(rng.integers(2, 5))
                minor = int(rng.integers(2, min(4, major + 1)))
                rebound_strength = float(
                    np.clip(rng.choice(_TIERS) * (1.0 - 0.10 * rebound), 0.16, 0.92)
                )
                rebound_tone = float(np.clip(rng.choice(_TONE) + rng.uniform(-0.08, 0.08), 0.04, 1.0))
                _draw_ellipse_periodic(
                    masks["rebound_specks"], bead_center, (major, minor), np.degrees(theta), rebound_strength
                )
                _draw_ellipse_periodic(
                    tones["rebound_specks"], bead_center, (major, minor), np.degrees(theta), rebound_tone
                )
                _record(ledger, "rebound_specks", minor * 4.0)

    bead = np.clip(masks["bead_clusters"], 0.0, 1.0)
    core = np.clip(masks["exposed_cores"], 0.0, 1.0)
    tail = np.clip(masks["resin_tails"], 0.0, 1.0)
    shard = np.clip(masks["crushed_shards"], 0.0, 1.0)
    lip = np.clip(masks["polished_skid_lips"], 0.0, 1.0)
    gouge = np.clip(masks["deep_gouges"], 0.0, 1.0)
    rebound = np.clip(masks["rebound_specks"], 0.0, 1.0)

    activity = np.maximum.reduce((bead, core, tail, shard, lip, gouge, rebound))
    compression = np.clip(_wrap_blur(activity, 18.0) * 2.4, 0.0, 1.0)
    damage = np.maximum.reduce((gouge, shard, core, rebound * 0.65))
    intact_resin = np.clip(
        1.0 - 0.88 * _wrap_blur(damage, 10.0) - 0.24 * bead + 0.34 * _wrap_blur(tail, 7.0),
        0.0,
        1.0,
    )

    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    polymer_micro = (
        np.sin(2.0 * np.pi * (91.0 * xx + 13.0 * yy) / size)
        + 0.55 * np.sin(2.0 * np.pi * (137.0 * xx - 29.0 * yy) / size + 0.7)
    ) / 1.55
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = 0.010 + 0.018 * compression + 0.0035 * polymer_micro * intact_resin
    paint[..., 1] = 0.006 + 0.006 * compression + 0.0020 * polymer_micro * intact_resin
    paint[..., 2] = 0.008 + 0.003 * compression + 0.0025 * polymer_micro * intact_resin

    _blend(
        paint,
        tail,
        _warm_color(tones["resin_tails"], (0.16, 0.018, 0.002), (0.56, 0.115, 0.004)),
        0.78,
    )
    _blend(
        paint,
        bead,
        _warm_color(tones["bead_clusters"], (0.27, 0.035, 0.002), (1.00, 0.43, 0.012)),
        0.94,
    )
    _blend(
        paint,
        rebound,
        _warm_color(tones["rebound_specks"], (0.34, 0.040, 0.002), (1.00, 0.33, 0.006)),
        0.90,
    )
    _blend(paint, gouge, np.asarray((0.0015, 0.0010, 0.0018), np.float32), 0.96)
    _blend(
        paint,
        shard,
        _warm_color(tones["crushed_shards"], (0.55, 0.075, 0.002), (1.00, 0.58, 0.025)),
        0.98,
    )
    _blend(
        paint,
        lip,
        _warm_color(tones["polished_skid_lips"], (0.46, 0.045, 0.002), (1.00, 0.39, 0.008)),
        0.96,
    )
    _blend(
        paint,
        core,
        _warm_color(tones["exposed_cores"], (0.88, 0.23, 0.006), (1.00, 0.88, 0.19)),
        1.0,
    )

    hot_glow = _wrap_blur(np.maximum(core, lip * 0.72), 5.5)
    paint += hot_glow[..., None] * np.asarray((0.32, 0.075, 0.001), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    # The response maps answer different questions about this same anatomy:
    # reflective backing/exposed fragments; abrasion/rupture; intact/pulled
    # polyurethane.  Separate causal terms keep them related without copies.
    m_score = (
        0.08
        + 0.48 * compression
        + 0.62 * bead
        + 1.16 * core
        + 1.02 * shard
        + 0.43 * lip
        + 0.16 * rebound
        - 0.57 * gouge
        - 0.12 * tail
    )
    r_score = (
        0.21
        + 0.22 * compression
        + 1.14 * gouge
        + 0.91 * shard
        + 0.52 * rebound
        + 0.39 * tail
        - 0.70 * lip
        - 0.42 * core
        - 0.27 * bead
    )
    c_score = (
        0.17
        + 1.02 * intact_resin
        + 0.94 * tail
        + 0.31 * compression
        + 0.24 * lip
        - 1.08 * core
        - 0.91 * gouge
        - 0.78 * shard
        - 0.30 * rebound
        - 0.16 * bead
    )
    spec = pack_material(m_score, r_score, c_score)

    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=_geometry(ledger),
        material_story={
            "M": "Reflective bead backing, exposed cores, crushed shards, and polished skid lips rise; deep gouges fall.",
            "R": "Deep gouges, crushed shards, resin drag and rebound debris rise; burnished lips and intact bead faces fall.",
            "Cc": "Intact black polyurethane and pooled orange resin tails rise; exposed tracks, cores, shards and gouges fall.",
        },
        carrier="Retroreflective orange microbeads embedded, dragged, and burnished through one black polyurethane sheet.",
        vetoes=(
            "caution tape",
            "chevrons",
            "polka dots",
            "random confetti",
            "asphalt scene",
            "Oil Slick flow topology",
        ),
    )


def _seam_audit(paint: np.ndarray, spec: np.ndarray) -> dict[str, object]:
    def ratio(values: np.ndarray, axis: int) -> float:
        if axis == 1:
            seam = np.mean(np.abs(values[:, 0].astype(np.float32) - values[:, -1].astype(np.float32)))
            local = np.mean(np.abs(np.diff(values.astype(np.float32), axis=1)))
        else:
            seam = np.mean(np.abs(values[0].astype(np.float32) - values[-1].astype(np.float32)))
            local = np.mean(np.abs(np.diff(values.astype(np.float32), axis=0)))
        return round(float(seam / max(float(local), 1e-7)), 6)

    return {
        "paint_x_to_local_ratio": ratio(paint, 1),
        "paint_y_to_local_ratio": ratio(paint, 0),
        "M_x_to_local_ratio": ratio(spec[..., 0], 1),
        "M_y_to_local_ratio": ratio(spec[..., 0], 0),
        "R_x_to_local_ratio": ratio(spec[..., 1], 1),
        "R_y_to_local_ratio": ratio(spec[..., 1], 0),
        "Cc_x_to_local_ratio": ratio(spec[..., 2], 1),
        "Cc_y_to_local_ratio": ratio(spec[..., 2], 0),
    }


def write_pilot_evidence(output: Path, seed: int = DEFAULT_SEED) -> dict[str, object]:
    result = timed_result(build_sodium_scuff, seed)
    resize_start = time.perf_counter()
    paint_native, spec_native = resize_result(result, NATIVE)
    native_render_elapsed = result.elapsed_seconds + (time.perf_counter() - resize_start)
    manifest = render_evidence(result, output)

    repeat = timed_result(build_sodium_scuff, seed)
    deterministic = bool(
        np.array_equal(result.paint, repeat.paint)
        and np.array_equal(result.spec, repeat.spec)
        and all(np.array_equal(result.masks[name], repeat.masks[name]) for name in _FAMILIES)
    )
    active = np.maximum.reduce(tuple(np.asarray(result.masks[name]) for name in _FAMILIES)) > 0.15
    void_distance = cv2.distanceTransform((~active).astype(np.uint8), cv2.DIST_L2, 5)
    max_void_native = round(float(void_distance.max() * NATIVE / WORK), 3)
    stats = material_stats(spec_native)
    seam = _seam_audit(result.paint, result.spec)

    geometry = manifest["geometry_stats"]
    checks = {
        "deterministic": deterministic,
        "builder_under_3_seconds": bool(result.elapsed_seconds <= 3.0),
        "native_paint_spec_under_3_seconds": bool(native_render_elapsed <= 3.0),
        "repeat_under_3_seconds": bool(repeat.elapsed_seconds <= 3.0),
        "seven_attached_families": bool(geometry["family_count"] >= 7),
        "all_widths_8_32_native": bool(geometry["fine_8_32_fraction"] == 1.0),
        "eight_tiers_each_channel": all(v == 8 for v in stats["tier_count"].values()),
        "std_at_least_30_each_channel": all(v >= 30.0 for v in stats["std"].values()),
        "full_canvas_no_void_over_64px": bool(max_void_native <= 64.0),
        "channels_not_copied_or_inverse": all(
            abs(v) < 0.92 for v in stats["correlation"].values()
        ),
    }
    audit = {
        "schema": "spb-neon-oil-slick-pilot-audit/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "seed": int(seed),
        "builder_elapsed_seconds": round(float(result.elapsed_seconds), 6),
        "native_paint_spec_elapsed_seconds": round(float(native_render_elapsed), 6),
        "repeat_elapsed_seconds": round(float(repeat.elapsed_seconds), 6),
        "deterministic": deterministic,
        "paint_sha256": _hash_array(result.paint),
        "spec_sha256": _hash_array(result.spec),
        "material_stats_native": stats,
        "geometry_stats": geometry,
        "max_unmarked_void_native_px": max_void_native,
        "seam_ratios_vs_local_neighbor_change": seam,
        "checks": checks,
        "all_mechanical_checks_green": bool(all(checks.values())),
        "catalog_m7": "PENDING: isolated pilot is deliberately not registered or baked",
        "mapped_car": "PENDING: core light-sweep proxy supplied; true car proof requires promotion harness",
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render isolated Sodium Scuff owner evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "_neon_oil_slick_reset_work" / "sodium_scuff",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = write_pilot_evidence(args.output, args.seed)
    print(json.dumps(audit, indent=2))
    return 0 if audit["all_mechanical_checks_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
