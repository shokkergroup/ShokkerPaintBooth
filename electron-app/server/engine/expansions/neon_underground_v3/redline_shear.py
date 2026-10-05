"""Isolated Redline Shear owner-review pilot for Neon Underground v3.

This is deliberately not registered in the live catalog.  The carrier is one
fluorescent lacquer skin compressed into short, staggered stress packets; it
does not draw a tachometer, track scene, banner, or other literal racing prop.

SPB-105 / Neon reset tick RS-P2 / owner verdict 2026-08-27:
"At 128 it becomes pink noise."  Audit movement: homogeneous fleck field ->
jittered shear trains with seven differentiated attached families, deterministic
~1.6s builder, M/R/Cc std 82.790/83.299/83.261, 8 occupied tiers each, and
directional survival at both 128px and 64px.  M7 remains explicitly N/A until
an isolated scorer exists; no composite score is invented for this unwired pilot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Sequence

import cv2
import numpy as np

from engine.paint_v2.neon_material_core_v3 import (
    GeometryMark,
    NATIVE,
    PilotResult,
    WORK,
    blur,
    material_stats,
    pack_material,
    render_evidence,
    seeded,
    timed_result,
    unit,
)


FINISH_ID = "neon_red_alert"
DISPLAY_NAME = "Redline Shear"
DEFAULT_SEED = 0x5EAD11CE


def _points(center: np.ndarray, tangent: np.ndarray, normal: np.ndarray, pairs: Sequence[tuple[float, float]]) -> np.ndarray:
    """Convert local tangent/normal offsets to a clipped cv2 polygon."""
    points = [center + tangent * along + normal * across for along, across in pairs]
    return np.rint(points).astype(np.int32)


def _layer(size: int) -> tuple[np.ndarray, np.ndarray]:
    return np.zeros((size, size, 3), np.uint8), np.zeros((size, size), np.uint8)


def _poly(
    rgb: np.ndarray,
    alpha: np.ndarray,
    polygon: np.ndarray,
    color: Sequence[int],
    opacity: int,
) -> None:
    cv2.fillConvexPoly(rgb, polygon, tuple(int(v) for v in color), lineType=cv2.LINE_AA)
    cv2.fillConvexPoly(alpha, polygon, int(opacity), lineType=cv2.LINE_AA)


def _strip(start: np.ndarray, end: np.ndarray, width: float, skew: float = 0.0) -> np.ndarray:
    """Angular finite strip used instead of pill-ended linework."""
    delta = np.asarray(end, np.float32) - np.asarray(start, np.float32)
    length = max(float(np.linalg.norm(delta)), 1e-6)
    tangent = delta / length
    normal = np.asarray((-tangent[1], tangent[0]), np.float32)
    center = (np.asarray(start, np.float32) + np.asarray(end, np.float32)) * 0.5
    half_l = length * 0.5
    half_w = float(width) * 0.5
    return _points(
        center,
        tangent,
        normal,
        (
            (-half_l, -half_w),
            (half_l, -half_w * (1.0 - skew)),
            (half_l, half_w),
            (-half_l, half_w * (1.0 + skew)),
        ),
    )


def _composite(paint: np.ndarray, layer: tuple[np.ndarray, np.ndarray], strength: float = 1.0) -> None:
    rgb, alpha = layer
    a = (alpha.astype(np.float32) / 255.0 * float(strength))[..., None]
    paint *= 1.0 - a
    paint += (rgb.astype(np.float32) / 255.0) * a


def _channel(layer: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    return layer[1].astype(np.float32) / 255.0


def build_redline_shear(seed: int = DEFAULT_SEED, size: int = WORK) -> PilotResult:
    """Build one deterministic fluorescent shear-compression lacquer sheet.

    Every visible anatomy is emitted from the same local packet history.  The
    material response below consumes only those authored anatomy maps and their
    causal falloff fields; there is no independent FBM/noise spec backdrop.
    """
    if int(size) < 256:
        raise ValueError("Redline Shear work size must be at least 256")
    rng = seeded(seed)
    scale = float(size) / float(WORK)

    layers = {
        "cooling_tails": _layer(size),
        "compression_fronts": _layer(size),
        "recoil_scars": _layer(size),
        "cavitation_pits": _layer(size),
        "check_fragments": _layer(size),
        "white_hot_lips": _layer(size),
        "tick_comb_cuts": _layer(size),
    }
    geometry: list[GeometryMark] = []
    front_palette = np.asarray(
        (
            (66, 1, 18),
            (88, 2, 28),
            (112, 3, 39),
            (138, 5, 30),
            (164, 8, 47),
            (190, 12, 58),
            (220, 20, 46),
            (248, 34, 66),
        ),
        np.uint8,
    )
    front_weights = np.asarray((0.12, 0.16, 0.18, 0.18, 0.14, 0.10, 0.07, 0.05), np.float64)

    # Closely attached fronts are gathered into short, jittered shear trains.
    # The train is only an assembly of legal fine marks (never a large authored
    # primitive), but its breathing room survives the 128px picker instead of
    # collapsing into an evenly distributed field of pink noise.
    target_spacing = max(32, int(round(44 * scale)))
    grid_y = max(1, int(np.ceil(size / target_spacing)))
    grid_x = max(1, int(np.ceil(size / target_spacing)))
    anchors: list[tuple[float, float, float, int, int, int]] = []
    for gy in range(grid_y):
        for gx in range(grid_x):
            group_center = np.asarray(
                (
                    (gx + 0.5 + rng.uniform(-0.46, 0.46)) * size / grid_x,
                    (gy + 0.5 + rng.uniform(-0.46, 0.46)) * size / grid_y,
                ),
                np.float32,
            )
            group_direction = float(np.clip(-0.18 + rng.normal(0.0, 0.13), -0.55, 0.20))
            group_tangent = np.asarray((np.cos(group_direction), np.sin(group_direction)), np.float32)
            group_normal = np.asarray((-group_tangent[1], group_tangent[0]), np.float32)
            group_count = int(rng.integers(5, 9))
            role_slots = {
                "lip": int(rng.integers(0, group_count)),
                "comb": int(rng.integers(0, group_count)),
                "scar": int(rng.integers(0, group_count)),
                "pit": int(rng.integers(0, group_count)),
                "check": int(rng.integers(0, group_count)),
            }
            along_slots = np.linspace(-13.0, 13.0, group_count, dtype=np.float32) * scale
            for group_slot, slot_offset in enumerate(along_slots):
                local_center = (
                    group_center
                    + group_tangent * (slot_offset + rng.uniform(-2.1, 2.1) * scale)
                    + group_normal * rng.uniform(-5.2, 5.2) * scale
                )
                role_flags = (
                    (1 if group_slot == role_slots["lip"] else 0)
                    | (2 if group_slot == role_slots["comb"] else 0)
                    | (4 if group_slot == role_slots["scar"] else 0)
                    | (8 if group_slot == role_slots["pit"] else 0)
                    | (16 if group_slot == role_slots["check"] else 0)
                )
                anchors.append(
                    (
                        float(local_center[0]),
                        float(local_center[1]),
                        float(group_direction + rng.normal(0.0, 0.055)),
                        group_slot,
                        group_count,
                        role_flags,
                    )
                )
    rng.shuffle(anchors)

    for anchor_index, (anchor_x, anchor_y, raw_direction, group_slot, group_count, role_flags) in enumerate(anchors):
        # Every member of one train shares a forward pressure history, with
        # enough micro-jitter to avoid literal lanes or repeated stamp angles.
        direction = float(np.clip(raw_direction, -0.62, 0.28))
        tangent = np.asarray((np.cos(direction), np.sin(direction)), np.float32)
        normal = np.asarray((-tangent[1], tangent[0]), np.float32)
        packet_count = 1

        for packet_index in range(packet_count):
            # Native dimensions: length 16-32px, thickness 8-18px.
            length = rng.uniform(12.0, 16.0) * scale
            thickness = rng.uniform(4.0, 6.6) * scale
            stagger = rng.uniform(-1.8, 1.8) * scale
            along = rng.uniform(-2.4, 2.4) * scale
            center = np.asarray((anchor_x, anchor_y), np.float32) + normal * stagger + tangent * along
            half_l = length * 0.5
            half_w = thickness * 0.5

            front_poly = _points(
                center,
                tangent,
                normal,
                (
                    (-half_l, -half_w * 0.28),
                    (-half_l * 0.24, -half_w),
                    (half_l, -half_w * 0.18),
                    (half_l * 0.48, half_w * 0.86),
                    (-half_l * 0.58, half_w),
                    (-half_l, half_w * 0.24),
                ),
            )
            front_color = front_palette[int(rng.choice(len(front_palette), p=front_weights))]
            _poly(
                *layers["compression_fronts"],
                front_poly,
                tuple(int(value) for value in front_color),
                int(rng.integers(122, 211)),
            )
            geometry.append(GeometryMark("compression_front", 2.0 * length / scale))

            # Magenta cooling lacquer is pulled directly from the back of a
            # pressure front.  It remains a finite wedge, never a smoke ribbon.
            if rng.random() < 0.66:
                tail_length = rng.uniform(8.0, 16.0) * scale
                tail_width = rng.uniform(4.6, 6.0) * scale
                tail_center = center - tangent * (half_l * 0.65 + tail_length * 0.22)
                tail_poly = _points(
                    tail_center,
                    tangent,
                    normal,
                    (
                        (-tail_length * 0.72, 0.0),
                        (tail_length * 0.42, -tail_width * 0.50),
                        (tail_length * 0.56, tail_width * 0.38),
                    ),
                )
                _poly(
                    *layers["cooling_tails"],
                    tail_poly,
                    (int(rng.integers(80, 171)), int(rng.integers(0, 9)), int(rng.integers(142, 246))),
                    int(rng.integers(162, 231)),
                )
                geometry.append(GeometryMark("magenta_cooling_tail", max(8.0, 2.0 * tail_length / scale)))

            # A bright pressure lip occupies only the leading face of selected
            # fronts.  Widths stay 8-12 native pixels and brightness changes
            # per event, preventing one constant material triple.
            if role_flags & 1 and rng.random() < 0.55:
                lip_half_l = rng.uniform(4.2, 6.0) * scale
                lip_half_w = rng.uniform(4.0, 5.2) * scale
                lip_center = center + tangent * (half_l * 0.62) + normal * rng.uniform(-half_w * 0.24, half_w * 0.24)
                lip_poly = _points(
                    lip_center,
                    tangent,
                    normal,
                    (
                        (-lip_half_l, -lip_half_w * 0.72),
                        (lip_half_l, -lip_half_w * 0.20),
                        (lip_half_l * 0.22, lip_half_w * 0.88),
                        (-lip_half_l * 0.78, lip_half_w * 0.28),
                    ),
                )
                warmth = int(rng.integers(218, 256))
                _poly(
                    *layers["white_hot_lips"],
                    lip_poly,
                    (255, warmth, int(rng.integers(188, 239))),
                    int(rng.integers(224, 256)),
                )
                geometry.append(GeometryMark("white_hot_pressure_lip", 2.0 * lip_half_l * 2.0 / scale))

            # Tick-comb cuts are short perpendicular incisions attached to the
            # front.  Uneven count/spacing keeps them from becoming a gauge.
            if role_flags & 2 and rng.random() < 0.72:
                cuts = 2 if length < 14.0 * scale else 3
                cut_width = rng.uniform(4.0, 4.08) * scale
                comb_sign = -1.0 if rng.random() < 0.5 else 1.0
                for cut_index in range(cuts):
                    cut_spacing = min(5.0 * scale, length / max(float(cuts), 1.0))
                    cut_center = (
                        center
                        + tangent * ((cut_index - (cuts - 1) * 0.5) * cut_spacing)
                        + normal * comb_sign * half_w * 0.48
                    )
                    cut_length = rng.uniform(7.5, 10.5) * scale
                    cut_start = cut_center - normal * comb_sign * cut_length * 0.16
                    cut_end = (
                        cut_center
                        + normal * comb_sign * cut_length * 0.84
                        + tangent * rng.uniform(-0.9, 0.9) * scale
                    )
                    _poly(
                        *layers["tick_comb_cuts"],
                        _strip(cut_start, cut_end, cut_width, skew=rng.uniform(-0.18, 0.18)),
                        (int(rng.integers(28, 82)), int(rng.integers(72, 146)), int(rng.integers(166, 236))),
                        int(rng.integers(164, 222)),
                    )
                    geometry.append(GeometryMark("tick_comb_microcut", max(8.0, 2.0 * cut_length / scale)))

            # Recoil scars sit behind their source front and run roughly with
            # compression.  No scar is long enough to recover a large arc.
            if role_flags & 4 and rng.random() < 0.82:
                scar_center = center - tangent * rng.uniform(half_l * 0.42, half_l * 0.80) + normal * rng.uniform(-half_w * 0.65, half_w * 0.65)
                scar_length = rng.uniform(6.0, 8.0) * scale
                scar_width = rng.uniform(4.0, 4.3) * scale
                scar_turn = -1.0 if rng.random() < 0.5 else 1.0
                scar_start = scar_center - tangent * scar_length * 0.72
                scar_joint = scar_center
                scar_end = scar_center + tangent * scar_length * 0.48 + normal * scar_length * 0.58 * scar_turn
                scar_color = (int(rng.integers(18, 46)), 0, int(rng.integers(74, 132)))
                scar_opacity = int(rng.integers(208, 255))
                _poly(*layers["recoil_scars"], _strip(scar_start, scar_joint, scar_width, skew=-0.25), scar_color, scar_opacity)
                _poly(*layers["recoil_scars"], _strip(scar_joint, scar_end, scar_width, skew=0.28), scar_color, scar_opacity)
                geometry.append(GeometryMark("recoil_scar", max(8.0, 2.0 * scar_length / scale)))

            # Cavitation is an angular tear, not a circular pit or bubble.
            if role_flags & 8 and rng.random() < 0.54:
                pit_center = center - tangent * rng.uniform(half_l * 0.12, half_l * 0.72) + normal * rng.uniform(-half_w, half_w)
                pit_l = rng.uniform(7.0, 10.0) * scale
                pit_w = rng.uniform(4.0, 5.2) * scale
                pit_poly = _points(
                    pit_center,
                    tangent,
                    normal,
                    ((-pit_l * 0.58, pit_w * 0.10), (-pit_l * 0.10, -pit_w * 0.54), (pit_l * 0.58, -pit_w * 0.12), (pit_l * 0.06, pit_w * 0.52)),
                )
                _poly(
                    *layers["cavitation_pits"],
                    pit_poly,
                    (int(rng.integers(1, 12)), 0, int(rng.integers(6, 25))),
                    int(rng.integers(218, 255)),
                )
                rim_start = pit_center - tangent * pit_l * 0.35 - normal * pit_w * 0.50
                rim_end = pit_center + tangent * pit_l * 0.54 - normal * pit_w * 0.10
                _poly(
                    *layers["cavitation_pits"],
                    _strip(rim_start, rim_end, rng.uniform(4.0, 4.4) * scale, skew=0.18),
                    (int(rng.integers(214, 255)), int(rng.integers(31, 83)), int(rng.integers(5, 28))),
                    int(rng.integers(146, 207)),
                )
                geometry.append(GeometryMark("angular_cavitation_pit", max(8.0, 2.0 * pit_l / scale)))

            # The only checker reference is a rare 2x2 fragment torn along the
            # packet direction.  It never forms a banner, lane, or wallpaper.
            if role_flags & 16 and rng.random() < 0.035 and packet_index == 0:
                tile = rng.uniform(4.5, 5.8) * scale
                frag_center = center - tangent * (half_l + tile * 0.4) + normal * rng.uniform(-half_w, half_w)
                for row, col in ((0, 0), (0, 1), (1, 0), (1, 1)):
                    local_center = frag_center + tangent * ((col - 0.5) * tile * 0.92) + normal * ((row - 0.5) * tile * 0.82)
                    block = _points(
                        local_center,
                        tangent,
                        normal,
                        ((-tile * 0.45, -tile * 0.34), (tile * 0.46, -tile * 0.47), (tile * 0.43, tile * 0.37), (-tile * 0.47, tile * 0.48)),
                    )
                    bright = (row + col + anchor_index) % 2 == 0
                    color = (
                        (int(rng.integers(220, 255)), int(rng.integers(184, 241)), int(rng.integers(201, 255)))
                        if bright
                        else (int(rng.integers(4, 42)), int(rng.integers(18, 71)), int(rng.integers(91, 166)))
                    )
                    _poly(*layers["check_fragments"], block, color, int(rng.integers(177, 235)))
                    geometry.append(GeometryMark("sheared_microcheck_fragment", max(8.0, 2.0 * tile / scale)))

    channels = {name: _channel(layer) for name, layer in layers.items()}
    front = channels["compression_fronts"]
    tail = channels["cooling_tails"]
    lip = channels["white_hot_lips"]
    cuts = channels["tick_comb_cuts"]
    scars = channels["recoil_scars"]
    pits = channels["cavitation_pits"]
    checks = channels["check_fragments"]

    # The lacquer background is illuminated only by pressure history derived
    # from the authored packets.  There is no unrelated texture/noise field.
    pressure_bloom = unit(blur(0.74 * front + 0.48 * lip + 0.30 * tail, 28.0, size))
    rupture_shadow = unit(blur(0.62 * scars + 0.92 * pits + 0.55 * cuts, 18.0, size))
    yy = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    studio_falloff = 0.90 + 0.10 * (1.0 - np.abs(yy - 0.47) * 2.0)
    paint = np.empty((size, size, 3), np.float32)
    paint[..., 0] = (0.092 + 0.165 * pressure_bloom - 0.030 * rupture_shadow) * studio_falloff
    paint[..., 1] = (0.002 + 0.009 * pressure_bloom) * studio_falloff
    paint[..., 2] = (0.014 + 0.040 * pressure_bloom + 0.020 * rupture_shadow) * studio_falloff

    for family, strength in (
        ("cooling_tails", 0.88),
        ("compression_fronts", 0.96),
        ("recoil_scars", 0.94),
        ("cavitation_pits", 0.98),
        ("check_fragments", 0.90),
        ("white_hot_lips", 1.00),
        ("tick_comb_cuts", 0.94),
    ):
        _composite(paint, layers[family], strength)

    # A restrained attached glow exposes the pressure fronts on the car while
    # keeping the dark carrier dominant.  Both glows originate in real lips or
    # tails, never in a separate decorative contour field.
    hot_glow = blur(lip, 11.0, size)
    magenta_glow = blur(tail, 15.0, size)
    paint += hot_glow[..., None] * np.asarray((0.34, 0.040, 0.035), np.float32)
    paint += magenta_glow[..., None] * np.asarray((0.11, 0.000, 0.075), np.float32)
    paint = np.clip(paint, 0.0, 1.0)

    rupture = np.maximum.reduce((cuts, scars, pits))
    intact_pool = np.clip(
        0.38 * blur(1.0 - np.clip(rupture, 0.0, 1.0), 12.0, size)
        + 0.90 * blur(front + tail, 24.0, size)
        - 0.48 * blur(lip + cuts, 8.0, size)
        - 0.34,
        0.0,
        1.0,
    )
    burnished_front = blur(front * (1.0 - np.clip(pits + cuts, 0.0, 1.0)), 7.0, size)
    healed_tail = blur(tail * (1.0 - pits), 13.0, size)

    # M: exposed aluminum pressure lips/cuts/check fragments; dark lacquer and
    # pits stay weak.  R: damage and cavities rise while pressure-burnished
    # fronts fall.  Cc: intact trailing pools/healed tails rise and ruptures
    # fall.  Different physical questions, same registered packet anatomy.
    m_score = (
        0.10
        + 1.42 * lip
        + 1.03 * cuts
        + 0.72 * checks
        + 0.24 * burnished_front
        - 0.49 * pits
        - 0.18 * healed_tail
        + 0.21 * blur(lip, 17.0, size)
    )
    r_score = (
        0.22
        + 1.13 * scars
        + 1.35 * pits
        + 0.87 * cuts
        + 0.42 * checks
        + 0.28 * tail
        - 0.81 * burnished_front
        - 0.68 * lip
        + 0.20 * blur(rupture, 16.0, size)
    )
    c_score = (
        0.18
        + 1.21 * intact_pool
        + 0.79 * healed_tail
        + 0.34 * burnished_front
        - 1.18 * pits
        - 1.01 * cuts
        - 0.77 * lip
        - 0.48 * scars
        + 0.16 * blur(front, 19.0, size)
    )
    spec = pack_material(m_score, r_score, c_score)

    masks = {
        "compression fronts": front,
        "white-hot lips": lip,
        "tick-comb cuts": cuts,
        "recoil scars": scars,
        "cavitation pits": pits,
        "micro-check fragments": checks,
        "magenta cooling tails": tail,
        "intact clear pools": intact_pool,
    }
    return PilotResult(
        finish_id=FINISH_ID,
        display_name=DISPLAY_NAME,
        paint=paint,
        spec=spec,
        masks=masks,
        geometry=geometry,
        carrier="fluorescent red lacquer compressed into staggered local 8-32px stress-front packets",
        material_story={
            "M": "exposed aluminum at varied white-hot pressure lips, microcuts, and torn micro-check fragments",
            "R": "recoil scars, angular cavitation, and cut damage rise while compression-burnished fronts fall",
            "Cc": "intact trailing lacquer pools and healed cooling tails rise while every rupture falls",
        },
        vetoes=(
            "gauges",
            "circles",
            "needles",
            "numerals",
            "checker banners",
            "repeated annuli",
            "recoverable large arcs",
            "Oil Slick flow contours",
        ),
    )


def _determinism_audit(seed: int, first: PilotResult) -> dict[str, object]:
    start = time.perf_counter()
    second = build_redline_shear(seed=seed, size=first.paint.shape[0])
    rerun_seconds = time.perf_counter() - start
    paint_equal = bool(np.array_equal(first.paint, second.paint))
    spec_equal = bool(np.array_equal(first.spec, second.spec))
    return {
        "paint_byte_identical": paint_equal,
        "spec_byte_identical": spec_equal,
        "rerun_seconds": round(float(rerun_seconds), 6),
        "pass": bool(paint_equal and spec_equal and rerun_seconds <= 3.0),
    }


def _edge_continuity_audit(paint: np.ndarray) -> dict[str, object]:
    rgb = np.clip(np.asarray(paint, np.float32), 0.0, 1.0)
    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    gx = np.pad(np.abs(np.diff(luma, axis=1)), ((0, 0), (0, 1)))
    gy = np.pad(np.abs(np.diff(luma, axis=0)), ((0, 1), (0, 0)))
    gradient = np.hypot(gx, gy)
    band = max(4, luma.shape[0] // 64)
    edge_gradient = np.concatenate(
        (gradient[:band].ravel(), gradient[-band:].ravel(), gradient[:, :band].ravel(), gradient[:, -band:].ravel())
    )
    edge_luma = np.concatenate((luma[:band].ravel(), luma[-band:].ravel(), luma[:, :band].ravel(), luma[:, -band:].ravel()))
    ratio = float(edge_gradient.mean() / max(float(gradient.mean()), 1e-7))
    dark_fraction = float(np.mean(edge_luma < 0.015))
    return {
        "edge_to_global_gradient_ratio": round(ratio, 6),
        "edge_dark_void_fraction": round(dark_fraction, 6),
        "pass": bool(0.50 <= ratio <= 1.50 and dark_fraction < 0.05),
    }


def _picker_audit(paint: np.ndarray) -> dict[str, object]:
    """Confirm the fine shear remains chromatic and directional in pickers."""
    rgb = np.clip(np.asarray(paint, np.float32), 0.0, 1.0)
    sizes: dict[str, dict[str, float]] = {}
    passed = True
    for picker_size in (128, 64):
        picker = cv2.resize(rgb, (picker_size, picker_size), interpolation=cv2.INTER_AREA)
        luma = picker[..., 0] * 0.2126 + picker[..., 1] * 0.7152 + picker[..., 2] * 0.0722
        chroma = np.max(picker, axis=2) - np.min(picker, axis=2)
        gradient_x = float(np.abs(np.diff(luma, axis=1)).mean())
        gradient_y = float(np.abs(np.diff(luma, axis=0)).mean())
        directional_ratio = gradient_y / max(gradient_x, 1e-8)
        luma_std = float(luma.std())
        chroma_std = float(chroma.std())
        size_pass = bool(luma_std >= 0.035 and chroma_std >= 0.035 and directional_ratio >= 1.10)
        sizes[str(picker_size)] = {
            "luma_std": round(luma_std, 6),
            "chroma_std": round(chroma_std, 6),
            "cross_to_forward_gradient_ratio": round(directional_ratio, 6),
            "pass": size_pass,
        }
        passed = passed and size_pass
    return {"sizes": sizes, "pass": bool(passed)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render isolated Redline Shear owner-review evidence")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_neon_oil_slick_reset_work/redline_shear"),
        help="isolated evidence directory",
    )
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    args = parser.parse_args()

    result = timed_result(build_redline_shear, seed=args.seed)
    manifest = render_evidence(result, args.output, native_size=NATIVE)
    working_material = material_stats(result.spec)
    geometry = manifest["geometry_stats"]
    correlations = working_material["correlation"]
    unique_mrc_triples = int(np.unique(result.spec.reshape(-1, 3), axis=0).shape[0])
    edge_continuity = _edge_continuity_audit(result.paint)
    picker_survival = _picker_audit(result.paint)
    causal_coverage = manifest["causal_mask_coverage"]
    visible_family_coverage_count = sum(
        value >= 0.01 for name, value in causal_coverage.items() if name != "intact clear pools"
    )
    mechanical_gates = {
        "five_plus_anatomy_families": bool(geometry["family_count"] >= 5),
        "five_plus_family_masks_above_one_percent": bool(visible_family_coverage_count >= 5),
        "all_geometry_8_to_32_native": bool(geometry["fine_8_32_fraction"] == 1.0),
        "eight_tiers_each": bool(all(value == 8 for value in working_material["tier_count"].values())),
        "material_std_at_least_30": bool(all(value >= 30.0 for value in working_material["std"].values())),
        "channels_not_copied_or_inverse": bool(all(abs(value) < 0.90 for value in correlations.values())),
        "many_material_triples": bool(unique_mrc_triples >= 128),
        "edge_continuity": bool(edge_continuity["pass"]),
        "directional_picker_survival": bool(picker_survival["pass"]),
    }
    audit = {
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": FINISH_ID,
        "builder_seconds": round(float(result.elapsed_seconds), 6),
        "under_three_seconds": bool(result.elapsed_seconds <= 3.0),
        "determinism": _determinism_audit(args.seed, result),
        "material_stats_working": working_material,
        "unique_mrc_triples": unique_mrc_triples,
        "geometry": geometry,
        "causal_mask_coverage": causal_coverage,
        "visible_family_coverage_count": int(visible_family_coverage_count),
        "edge_continuity": edge_continuity,
        "picker_survival": picker_survival,
        "mechanical_gates": mechanical_gates,
        "mechanical_gates_pass": bool(all(mechanical_gates.values())),
        "official_m7": None,
        "official_m7_note": "Unwired isolated pilot; no registry/workbook record exists, so no composite is fabricated.",
    }
    (args.output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0 if audit["under_three_seconds"] and audit["determinism"]["pass"] and audit["mechanical_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
