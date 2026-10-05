# -*- coding: utf-8 -*-
"""Isolated native-2048 Sasquatch Fur vorticity-pelage study.

SPB-105 / Wilds attempt 63 / 2026-08-25. Owner verdict controlling this edit:
"EXACT SAME pattern just recolored" is the cardinal sin; native 2048 is the
acceptance surface and random noise may not manufacture uniqueness.

The rejected registered W16 was a flow-aligned swarm of one short capsule/tuft
unit (0.425-0.504 s, A/B 0.059884/0.238995). I1 starts from blank topology. An
analytic inverse-flow chronology deforms material coordinates through six
unequal vortex/saddle events. Underfur laminae, guard bundles, root collars,
compression bands, split wakes, hook seams, and abrasion windows are distinct
consequences of that chronology. No RNG, noise, FBM, particles, placed strokes,
cells, glyph stamps, or inherited Wilds composer are used.

Native result: REJECTED at paint contact. Although exact runs were
1.086-1.150 s with A/B 0.073134/0.283547, the full canvas collapsed into broad
advected contour ribbons whose attached marks read as fine internal ticks. The
source is frozen root-only and must never be registered or synchronized.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

import cv2
import numpy as np


ID = "fc_sasquatch_fur"
WORK = 512


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]
    topology: str


def _f(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def _phase_distance(phase: np.ndarray, center: float) -> np.ndarray:
    return np.abs((phase - center + 0.5) % 1.0 - 0.5)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    d = _phase_distance(phase, center) / max(float(width), 1e-5)
    return np.exp(-2.5 * d * d).astype(np.float32)


def _palette(t: np.ndarray) -> np.ndarray:
    # Thirteen opponent pelage/mineral colors. Hue is deliberately independent
    # of luminance so the hue-null contact remains a valid topology audit.
    colors = np.asarray([
        (0.018, 0.035, 0.030),
        (0.025, 0.150, 0.120),
        (0.030, 0.330, 0.250),
        (0.055, 0.590, 0.410),
        (0.240, 0.790, 0.480),
        (0.720, 0.820, 0.330),
        (0.970, 0.650, 0.210),
        (0.920, 0.350, 0.125),
        (0.690, 0.120, 0.190),
        (0.530, 0.080, 0.390),
        (0.330, 0.110, 0.600),
        (0.100, 0.250, 0.690),
        (0.025, 0.500, 0.650),
    ], np.float32)
    u = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(u).astype(np.int32) % len(colors)
    i1 = (i0 + 1) % len(colors)
    q = (u - np.floor(u))[..., None]
    return colors[i0] * (1.0 - q) + colors[i1] * q


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    index = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[index.astype(np.int32)]


def _inverse_pelage_flow(x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Backtrace a material sheet through unequal analytic pole/saddle events.

    This is the reusable-math contribution requested by the owner: a bounded
    semi-Lagrangian coordinate transform, not a prebuilt texture field. The
    material-coordinate phase is evaluated only after the deformation.
    """
    qx, qy = x.copy(), y.copy()
    curl_acc = np.zeros_like(x)
    events = (
        (-0.18, 0.16, +0.0105, +1.00, 0.17),
        (0.23, -0.20, -0.0085, +0.82, 0.13),
        (0.62, 0.31, +0.0070, -0.62, 0.19),
        (-0.57, -0.39, -0.0065, +0.70, 0.15),
        (0.07, 0.70, +0.0055, -0.54, 0.21),
        (0.74, -0.66, -0.0048, +0.48, 0.12),
    )
    for _step in range(9):
        vx = np.full_like(qx, 0.0038)
        vy = np.full_like(qy, -0.0017)
        for cx, cy, spin, saddle, core in events:
            dx, dy = qx - cx, qy - cy
            r2 = dx * dx + dy * dy + core * core
            envelope = np.exp(-0.78 * r2)
            # Rotational and trace-free saddle motion coexist; neither creates
            # a scalar basin or a stamped vortex icon.
            vx += envelope * ((-spin * dy / r2) + 0.0018 * saddle * dx)
            vy += envelope * ((+spin * dx / r2) - 0.0018 * saddle * dy)
            curl_acc += envelope * (spin / (core + np.sqrt(r2)))
        qx -= vx
        qy -= vy
    return qx.astype(np.float32), qy.astype(np.float32), curl_acc.astype(np.float32)


def _build() -> Grammar:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK * 2.0 - 1.0
    y = (yy + 0.5) / WORK * 2.0 - 1.0
    qx, qy, vorticity = _inverse_pelage_flow(x, y)

    # Two incommensurate material coordinates create connected ancestry rather
    # than independent placed hairs. Primary spacings land at 14-31 native px.
    along = (38.0 * qx + 4.4 * np.sin(2.7 * qy + 1.1 * qx)
             + 1.9 * np.sin(7.1 * qy - 0.8 * qx)
             + 0.75 * np.sin(13.3 * qy + 2.4 * qx))
    across = (17.0 * qy - 2.8 * np.sin(1.9 * qx - 0.4 * qy)
              + 1.15 * np.sin(5.3 * qx + 1.7 * qy))
    age = np.mod(along, 1.0)
    lineage = np.mod(across + 0.071 * along, 1.0)

    underfur = _f(_pulse(age, 0.18, 0.17) * (0.52 + 0.48 * _pulse(lineage, 0.62, 0.31)))
    medulla = _f(_pulse(age, 0.55, 0.075) * (0.35 + 0.65 * _pulse(lineage, 0.15, 0.24)))

    # Guard bundles widen and narrow continuously with lineage age. They are
    # regions of the sheet, not short stroke/glyph instances.
    bundle_center = np.mod(0.78 + 0.13 * np.sin(0.41 * along + 5.1 * qy), 1.0)
    guard = _f(_pulse(age, bundle_center, 0.105)
               * (0.30 + 0.70 * _pulse(lineage, 0.42, 0.23)))

    # Root collars occur only where lineages exchange dominance; compression
    # bands are transverse consequences inside existing guard/underfur mass.
    exchange = _pulse(np.mod(lineage + 0.19 * np.sin(0.23 * along), 1.0), 0.02, 0.060)
    root_collar = _f(exchange * _pulse(age, 0.84, 0.12)
                     * (0.45 + 0.55 * np.clip(np.abs(vorticity) * 8.0, 0, 1)))
    cross_phase = np.mod(0.29 * along + 5.0 * lineage + 0.22 * np.sin(3.1 * qx), 1.0)
    compression = _f(_pulse(cross_phase, 0.48, 0.045)
                     * (0.45 * underfur + 0.80 * guard))

    # A fold in the material chronology opens two unequal descendant phases.
    # Their difference makes split wakes that remain attached to parent lanes.
    fold = np.tanh(4.5 * vorticity + 0.55 * np.sin(2.6 * qx - 3.1 * qy))
    child_a = _pulse(np.mod(along + 0.36 * fold, 1.0), 0.34, 0.055)
    child_b = _pulse(np.mod(along - 0.21 * fold, 1.0), 0.67, 0.050)
    split_wake = _f(np.minimum(child_a + child_b, 1.0)
                    * _pulse(lineage, 0.78, 0.18)
                    * np.clip(np.abs(fold) - 0.18, 0, 1))

    hook_phase = np.mod(2.6 * lineage + 0.17 * along
                        + 0.31 * np.sin(4.7 * qx + 2.3 * qy), 1.0)
    hook_seam = _f(_pulse(hook_phase, 0.26, 0.040)
                   * _pulse(age, 0.05, 0.14)
                   * (0.35 + 0.65 * guard))

    abrasion_phase = np.mod(0.11 * along - 3.7 * lineage
                            + 0.55 * np.sin(1.8 * qx - 2.5 * qy), 1.0)
    abrasion = _f(_pulse(abrasion_phase, 0.71, 0.095)
                  * (0.38 * underfur + 0.62 * medulla)
                  * (1.0 - 0.55 * root_collar))

    pigment_t = np.mod(0.067 * along + 0.29 * lineage
                       + 0.09 * fold + 0.13 * guard - 0.08 * abrasion, 1.0)
    tissue = _palette(pigment_t)
    brightness = _f(0.23 + 0.30 * underfur + 0.22 * medulla + 0.27 * guard)
    paint = tissue * brightness[..., None]
    paint += root_collar[..., None] * np.asarray((0.82, 0.55, 0.16), np.float32)
    paint += compression[..., None] * np.asarray((0.10, 0.57, 0.58), np.float32)
    paint += split_wake[..., None] * np.asarray((0.56, 0.12, 0.45), np.float32)
    paint += hook_seam[..., None] * np.asarray((0.79, 0.30, 0.12), np.float32)
    paint -= abrasion[..., None] * np.asarray((0.15, 0.10, 0.08), np.float32)
    paint = _f(paint)

    neutral = _f(0.16 + 0.31 * underfur + 0.24 * medulla + 0.29 * guard
                 + 0.33 * root_collar + 0.25 * compression
                 + 0.27 * split_wake + 0.22 * hook_seam - 0.19 * abrasion)
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    # Eight-tier channels use different anatomy and opponent ownership. No
    # shared rank map, inverse pair, random tint, or decorative spec substrate.
    metal_field = _f(0.03 + 0.75 * medulla + 0.68 * root_collar
                     + 0.57 * split_wake + 0.34 * guard - 0.28 * abrasion)
    rough_field = _f(0.11 + 0.65 * underfur + 0.58 * abrasion
                     + 0.39 * compression - 0.36 * root_collar - 0.24 * medulla)
    coat_field = _f(0.04 + 0.72 * guard + 0.59 * hook_seam
                    + 0.42 * split_wake - 0.31 * compression - 0.24 * abrasion)
    metal = _tier(metal_field, (7, 31, 58, 91, 128, 169, 211, 249))
    rough = _tier(rough_field, (13, 40, 69, 103, 139, 177, 216, 250))
    coat = _tier(coat_field, (5, 27, 54, 87, 124, 165, 209, 252))

    marks = (
        ("underfur_laminae", underfur, "A"),
        ("medulla_channels", medulla, "B"),
        ("guard_bundles", guard, "B"),
        ("root_collars", root_collar, "A"),
        ("compression_crossbands", compression, "A"),
        ("split_wakes", split_wake, "B"),
        ("hook_seams", hook_seam, "A"),
        ("abrasion_windows", abrasion, "N"),
    )
    if any(float(mask.std()) < 0.005 for _name, mask, _bank in marks):
        raise ValueError("Sasquatch I1 has an absent causal mark")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="semi-Lagrangian vorticity pelage ancestry with attached material consequences",
    )


@lru_cache(maxsize=1)
def _cached() -> Tuple[np.ndarray, np.ndarray]:
    grammar = _build()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)


def _authored(fid: str = ID) -> Tuple[np.ndarray, np.ndarray]:
    if fid != ID:
        raise KeyError(fid)
    paint, spec = _cached()
    return paint.copy(), spec.copy()


def clear_cache() -> None:
    _cached.cache_clear()


def debug_grammar() -> Grammar:
    return _build()


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    owners = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        owners[bank] = np.maximum(owners[bank], mask)
    return owners


def debug_angle_pair(fid: str = ID) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if fid != ID:
        raise KeyError(fid)
    grammar = _build()
    owners = owner_unions(grammar)
    a = grammar.paint * (0.39 + 0.57 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.07, 0.50, 0.49), np.float32)
    a += owners["B"][..., None] * np.asarray((0.20, 0.03, 0.25), np.float32)
    b = grammar.paint * (0.38 + 0.58 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.62, 0.08, 0.38), np.float32)
    b += owners["A"][..., None] * np.asarray((0.31, 0.27, 0.03), np.float32)
    a, b = _f(a), _f(b)
    return a, b, np.abs(a - b).astype(np.float32)


BUILDERS = {ID: _build}
