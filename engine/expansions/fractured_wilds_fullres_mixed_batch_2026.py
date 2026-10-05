# -*- coding: utf-8 -*-
"""Native-2048 isolated Fractured Wilds mixed rebuild candidates.

SPB-WILDS, 2026-08-24, owner full-resolution correction pass.  The owner
rejected recolours, repeated spec silhouettes, noise-based differentiation,
and picker-size acceptance as the app's cardinal failure.  This isolated
module therefore owns four unrelated physical processes at the real
2048-square canvas resolution:

* ``fmo_labradorite`` -- twinned feldspar cleavage microplates;
* ``fmo_fire_agate`` -- packed botryoidal chalcedony fire crowns;
* ``fbl_magenta_whorl`` -- phyllotactic scalloped rosette whorls;
* ``fbl_coral_cluster`` -- mineralised polygonal coral calices.

Every process constructs its own paint and M/R/Cc ancestry.  There is no RNG,
seed use, noise, grain, stochastic jitter, source image, or generic topology
router.  Feature pitches are 8--32 px at native 2048; hairline edge strokes
only articulate those features.  Each builder names at least six causally
attached marks and assigns opposed A/B material lobes so angle A emphasises
one colour family while angle B exposes its chromatic opponent.

This is evidence-only rejected-study code.  It is deliberately not imported
by the production engine, registry, catalog, or packaged runtime.  Native
2048 inspection rejected Labradorite as repeated capsule/lamella-row fabric,
Fire Agate as a dense equal-dot/botryoid paver, and both floral studies as
regular repeated cells.  M7 movement is intentionally not claimed here; the
owner's native-2048 eye is the acceptance authority for this pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


_SIZE = 2048
_CALM_SPEC = np.asarray([8.0, 132.0, 22.0], np.float32)


@dataclass(frozen=True)
class NativeFinish:
    """One native canvas result and its process audit vocabulary."""

    paint: np.ndarray
    spec: np.ndarray
    marks: Tuple[str, ...]
    process: str


@lru_cache(maxsize=1)
def _xy() -> Tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:_SIZE, 0:_SIZE].astype(np.float32)
    return x, y


def _f32(value: np.ndarray | float) -> np.ndarray:
    return np.clip(np.asarray(value, np.float32), 0.0, 1.0)


def _ridge(value: np.ndarray, period: float, half_width: float) -> np.ndarray:
    """A deterministic periodic ribbon; no stochastic field is involved."""
    distance = np.abs(np.mod(value + period * 0.5, period) - period * 0.5)
    return _f32(1.0 - distance / max(0.25, half_width))


def _ring(distance: np.ndarray, radius: np.ndarray | float, width: float) -> np.ndarray:
    return _f32(1.0 - np.abs(distance - np.asarray(radius, np.float32)) / max(0.25, width))


def _inside(distance: np.ndarray, radius: np.ndarray | float, feather: float = 1.5) -> np.ndarray:
    return _f32((np.asarray(radius, np.float32) - distance) / max(0.25, feather) + 0.5)


def _hex(token: str) -> Tuple[int, int, int]:
    text = token.lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


@lru_cache(maxsize=32)
def _lut(tokens: Tuple[str, ...]) -> np.ndarray:
    colours = np.asarray([_hex(token) for token in tokens], np.float32)
    positions = np.linspace(0.0, 255.0, len(colours), dtype=np.float32)
    query = np.arange(256, dtype=np.float32)
    table = np.empty((256, 3), np.uint8)
    for channel in range(3):
        table[:, channel] = np.clip(np.interp(query, positions, colours[:, channel]), 0, 255).astype(np.uint8)
    return table


def _colour(field: np.ndarray, palette: Sequence[str]) -> np.ndarray:
    index = np.clip(np.asarray(field, np.float32) * 255.0, 0, 255).astype(np.uint8)
    return _lut(tuple(palette))[index]


def _blend(base: np.ndarray, overlay: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = _f32(alpha)[..., None]
    b = np.asarray(base, np.float32)
    o = np.asarray(overlay, np.float32)
    return b + (o - b) * a


def _tiers(field: np.ndarray, values: Sequence[int]) -> np.ndarray:
    scale = _f32(field)
    bank = np.asarray(tuple(values), np.uint8)
    index = np.minimum((scale * len(bank)).astype(np.int16), len(bank) - 1)
    return bank[index]


def _rgb8(value: np.ndarray) -> np.ndarray:
    return np.clip(value, 0, 255).astype(np.uint8)


def _spec3(metal: np.ndarray, rough: np.ndarray, coat: np.ndarray) -> np.ndarray:
    return np.dstack((metal, rough, coat)).astype(np.uint8)


def _angle_pair(finish: NativeFinish) -> Tuple[np.ndarray, np.ndarray]:
    """Expose the opposed A=metal and B=clearcoat chromatic lobes at 2048."""
    paint = finish.paint.astype(np.float32) / 255.0
    metal = finish.spec[:, :, 0].astype(np.float32) / 255.0
    rough = finish.spec[:, :, 1].astype(np.float32) / 255.0
    coat = finish.spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.10 - 0.62 * rough, 0.22, 1.0)
    a_gain = np.clip(0.22 + 1.18 * metal * aperture, 0.18, 1.35)
    b_gain = np.clip(0.22 + 1.18 * coat * aperture, 0.18, 1.35)
    # These tints are deliberately opposed; topology decides where they land.
    cool = np.asarray([0.015, 0.105, 0.19], np.float32)
    warm = np.asarray([0.19, 0.055, 0.012], np.float32)
    angle_a = np.clip(paint * a_gain[..., None] + cool * (metal * aperture)[..., None], 0, 1)
    angle_b = np.clip(paint * b_gain[..., None] + warm * (coat * aperture)[..., None], 0, 1)
    return (angle_a * 255.0).astype(np.uint8), (angle_b * 255.0).astype(np.uint8)


# ---------------------------------------------------------------------------
# LABRADORITE -- twinned feldspar cleavage, authored independently at 2048.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_fmo_labradorite() -> NativeFinish:
    x, y = _xy()
    # Two incommensurate, coherently strained crystal axes break the former
    # textile-like repeat into finite twin lenses and irregular cleavage shards.
    u = x + 0.38 * y + 8.6 * np.sin(y / 47.0) + 5.2 * np.sin((x - y) / 83.0)
    v = y - 0.31 * x + 7.1 * np.sin(x / 53.0) + 4.4 * np.cos((x + y) / 97.0)
    wave_u = np.sin(u / 41.0)
    wave_v = np.cos(v / 37.0)
    domain_a = _f32((np.cos(v / 16.5 + 0.72 * wave_u) + 0.36) / 1.36)
    domain_b = _f32((np.sin(u / 19.0 - 0.58 * wave_v) + 0.42) / 1.42)
    plate_flip = (domain_a >= domain_b).astype(np.float32)

    seam_u = _ridge(u + 4.3 * wave_v, 29.0, 2.6) * _f32(0.24 + 0.76 * domain_b)
    seam_v = _ridge(v - 3.7 * wave_u, 31.0, 2.5) * _f32(0.26 + 0.74 * (1.0 - domain_a))
    cleavage_seam = np.maximum(seam_u, seam_v)
    plate_interior = _f32(1.0 - 0.92 * cleavage_seam)

    twin_phase = u + 4.8 * np.sin(v / 11.5)
    twin_lamella = _ridge(twin_phase, 18.0, 5.1) * plate_interior * domain_a
    cross_twin = _ridge(v + 0.17 * u, 25.0, 3.7) * plate_interior * domain_b
    diffraction_pinstripe = _ridge(twin_phase + 0.32 * v, 9.0, 1.8) * twin_lamella

    # Stepped terminations only exist at plate ends, as real twin lamellae do.
    stair = _ridge(u + 0.34 * v, 13.0, 2.4)
    stepped_termination = stair * np.maximum(seam_u, _ridge(v, 23.0, 2.8)) * domain_b
    cleavage_nick = _ridge(u - 0.72 * v, 27.0, 2.0) * cleavage_seam * (1.0 - domain_a * 0.55)
    flash_halo = cv2.GaussianBlur(
        np.maximum(twin_lamella * 0.75, diffraction_pinstripe).astype(np.float32),
        (0, 0), 2.2,
    )

    a_owner = _f32((0.72 * twin_lamella + 0.60 * diffraction_pinstripe + 0.32 * cross_twin) * plate_flip)
    b_owner = _f32((0.70 * twin_lamella + 0.48 * stepped_termination + 0.28 * cross_twin) * (1.0 - plate_flip))
    crystal_tone = _f32(
        0.38
        + 0.25 * wave_u
        + 0.18 * wave_v
        + 0.15 * diffraction_pinstripe
    )

    base = _colour(
        _f32(0.18 + 0.42 * crystal_tone + 0.12 * plate_flip),
        ("#02040a", "#07111b", "#111723", "#172330", "#242015", "#101827"),
    ).astype(np.float32)
    cool = _colour(
        _f32(0.08 + 0.58 * crystal_tone + 0.31 * cross_twin),
        (
            "#061225", "#092d55", "#075aa0", "#008bd2", "#00c5e9", "#85f8ff",
            "#42d5bb", "#2886ed", "#5634d8", "#a642e9", "#fb86ff", "#d9faff",
        ),
    )
    warm = _colour(
        _f32(0.10 + 0.55 * (1.0 - crystal_tone) + 0.34 * stepped_termination),
        (
            "#19060b", "#5a1710", "#9a3512", "#dc6815", "#ffad24", "#fff06b",
            "#b4ee38", "#42c969", "#0ca89d", "#6848d6", "#c23bc5", "#ffb05e",
        ),
    )
    paint = _blend(base, cool, _f32(0.22 * flash_halo + 0.78 * a_owner))
    paint = _blend(paint, warm, _f32(0.18 * flash_halo + 0.82 * b_owner))
    edge_colour = _colour(
        _f32(0.24 + 0.46 * crystal_tone + 0.30 * cleavage_nick),
        ("#02050a", "#0d1721", "#24313a", "#677f80", "#d2dfc2", "#3a240e"),
    )
    paint = _blend(paint, edge_colour, _f32(0.68 * cleavage_seam + 0.30 * cleavage_nick))
    paint = _blend(paint, np.full_like(cool, (207, 244, 255)), _f32(0.38 * diffraction_pinstripe))

    # Independent channel ancestry: lamellar metal, broken cleavage roughness,
    # and complementary plate clearcoat cannot collapse to one silhouette.
    metal_f = _f32(0.06 + 0.68 * a_owner + 0.36 * cross_twin + 0.24 * cleavage_nick)
    rough_f = _f32(0.18 + 0.63 * cleavage_seam + 0.30 * stepped_termination - 0.34 * twin_lamella + 0.16 * cross_twin)
    coat_f = _f32(0.10 + 0.76 * b_owner + 0.30 * plate_interior - 0.34 * cleavage_nick + 0.18 * flash_halo)
    spec = _spec3(
        _tiers(metal_f, (10, 28, 50, 78, 108, 145, 184, 218, 244)),
        _tiers(rough_f, (18, 36, 58, 82, 110, 142, 176, 214, 244)),
        _tiers(coat_f, (8, 24, 44, 68, 98, 132, 170, 212, 246)),
    )
    return NativeFinish(
        _rgb8(paint), spec,
        (
            "triclinic_microplates", "twin_lamellae", "cross_twin_ribs",
            "diffraction_pinstripes", "cleavage_seams", "stepped_terminations",
            "cleavage_nicks", "flash_halos",
        ),
        "twinned triclinic feldspar cleavage with opposed blue and gold labradorescence",
    )


# ---------------------------------------------------------------------------
# FIRE AGATE -- packed botryoidal chalcedony, no shared plate/whorl topology.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_fmo_fire_agate() -> NativeFinish:
    body_u8 = np.zeros((_SIZE, _SIZE), np.uint8)
    crown_u8 = np.zeros_like(body_u8)
    flame_u8 = np.zeros_like(body_u8)
    eye_u8 = np.zeros_like(body_u8)
    spoke_u8 = np.zeros_like(body_u8)
    bridge_u8 = np.zeros_like(body_u8)
    flare_u8 = np.zeros_like(body_u8)
    cell_tone_u8 = np.zeros_like(body_u8)

    pitch_x, pitch_y = 30, 26
    centres: Dict[Tuple[int, int], Tuple[int, int, int]] = {}
    rows = range(-1, _SIZE // pitch_y + 2)
    cols = range(-2, _SIZE // pitch_x + 3)
    for row in rows:
        for col in cols:
            cx = int(round(col * pitch_x + (row & 1) * 15 + 4.2 * math.sin(row * 0.61 + col * 0.37)))
            cy = int(round(row * pitch_y + 3.8 * math.cos(col * 0.47 - row * 0.29)))
            radius = int(round(13.5 + 2.6 * math.sin(row * 0.73 + col * 0.91)))
            centres[(row, col)] = (cx, cy, radius)
            phase = (row + 2 * col) % 6
            cv2.circle(body_u8, (cx, cy), radius, 210 + phase * 7, -1, cv2.LINE_AA)
            # Quadratic chirp phase: deterministic thin-film thickness order
            # without the diagonal bands produced by a linear lattice phase.
            chirp = 0.50 + 0.27 * math.sin(0.071 * row * row + 0.63 * col) + 0.23 * math.cos(0.053 * col * col - 0.49 * row)
            quasiphase = int(max(18, min(238, round(18 + 220 * chirp))))
            cv2.circle(cell_tone_u8, (cx, cy), radius, quasiphase, -1, cv2.LINE_AA)
            cv2.circle(crown_u8, (cx, cy), radius, 235, 4, cv2.LINE_AA)
            cv2.circle(crown_u8, (cx, cy), max(7, radius - 5), 170 + 12 * phase, 3, cv2.LINE_AA)
            cv2.circle(eye_u8, (cx, cy), 4 + (phase & 1), 185 + phase * 10, -1, cv2.LINE_AA)
            angle = int((row * 29 + col * 41) % 360)
            cv2.ellipse(flame_u8, (cx, cy), (max(7, radius - 3), max(5, radius - 6)), angle, 18, 244, 230, 3, cv2.LINE_AA)
            cv2.ellipse(flare_u8, (cx, cy), (max(5, radius - 6), max(4, radius - 8)), angle + 110, 24, 190, 220, 3, cv2.LINE_AA)
            for turn in (angle, angle + 120, angle + 240):
                rad = math.radians(turn)
                end = (int(round(cx + (radius - 4) * math.cos(rad))), int(round(cy + (radius - 4) * math.sin(rad))))
                cv2.line(spoke_u8, (cx, cy), end, 210, 2, cv2.LINE_AA)

    # Ordered siliceous bridges join neighbouring domes; they are not noise.
    for (row, col), (cx, cy, radius) in centres.items():
        if (row + col) % 3 == 0 and (row, col + 1) in centres:
            nx, ny, _ = centres[(row, col + 1)]
            cv2.line(bridge_u8, (cx, cy), (nx, ny), 215, 3, cv2.LINE_AA)
        if (2 * row + col) % 5 == 0 and (row + 1, col) in centres:
            nx, ny, _ = centres[(row + 1, col)]
            cv2.line(bridge_u8, (cx, cy), (nx, ny), 180, 2, cv2.LINE_AA)

    body = body_u8.astype(np.float32) / 255.0
    crown = crown_u8.astype(np.float32) / 255.0
    flame = flame_u8.astype(np.float32) / 255.0
    eye = eye_u8.astype(np.float32) / 255.0
    spokes = spoke_u8.astype(np.float32) / 255.0
    bridge = bridge_u8.astype(np.float32) / 255.0
    flare = flare_u8.astype(np.float32) / 255.0
    cell_tone = cell_tone_u8.astype(np.float32) / 255.0
    dome_distance = cv2.distanceTransform((body_u8 > 10).astype(np.uint8), cv2.DIST_L2, 3)
    dome = _f32(dome_distance / 15.5)
    interstice = _f32(1.0 - cv2.GaussianBlur(body, (0, 0), 1.4))
    # Each dome owns its own ordered thin-film phase.  This removes the former
    # canvas-wide diagonal rainbow carrier while retaining deterministic colour.
    ordered_fire = _f32(0.20 + 0.10 * cell_tone + 0.28 * dome + 0.25 * flame + 0.16 * eye - 0.12 * bridge)

    a_owner = _f32(0.64 * crown + 0.82 * flame + 0.34 * spokes)
    b_owner = _f32(0.72 * flare + 0.82 * eye + 0.20 * dome)
    base = _colour(
        _f32(0.10 + 0.47 * dome + 0.16 * ordered_fire),
        ("#070302", "#170704", "#33100a", "#5a2210", "#7b3515", "#2b180f", "#080505"),
    ).astype(np.float32)
    ember = _colour(
        _f32(0.08 + 0.54 * ordered_fire + 0.34 * crown),
        (
            "#210005", "#61070a", "#a61a0b", "#e94c08", "#ff8b0b", "#ffd12b",
            "#fff379", "#b8f03b", "#3ed449", "#06a973", "#037d9d", "#6d25b8",
            "#e62d94", "#ff8244", "#fff0aa",
        ),
    )
    spectral = _colour(
        _f32(0.06 + 0.48 * (1.0 - ordered_fire) + 0.42 * dome),
        (
            "#10031e", "#3a0868", "#7d0ba8", "#c520a2", "#f83e72", "#ff6c22",
            "#ffbd19", "#d9ed3b", "#43d95d", "#00b89f", "#087fc8", "#4249da",
            "#952cdb", "#f653b0", "#fff09d",
        ),
    )
    paint = _blend(base, ember, _f32(0.84 * a_owner + 0.18 * bridge))
    paint = _blend(paint, spectral, _f32(0.80 * b_owner + 0.12 * dome))
    paint = _blend(paint, np.full_like(spectral, (255, 210, 92)), _f32(0.46 * spokes + 0.24 * crown))
    paint = _blend(paint, np.full_like(spectral, (18, 7, 10)), _f32(0.62 * interstice + 0.58 * bridge))

    metal_f = _f32(0.04 + 0.74 * flame + 0.54 * crown + 0.30 * spokes + 0.12 * dome)
    rough_f = _f32(0.16 + 0.62 * interstice + 0.42 * bridge + 0.22 * crown - 0.38 * eye - 0.23 * dome)
    coat_f = _f32(0.08 + 0.74 * eye + 0.58 * flare + 0.44 * dome - 0.34 * bridge + 0.18 * flame)
    spec = _spec3(
        _tiers(metal_f, (6, 24, 46, 72, 102, 136, 174, 214, 246)),
        _tiers(rough_f, (16, 34, 56, 82, 112, 146, 182, 218, 246)),
        _tiers(coat_f, (8, 26, 48, 76, 108, 144, 182, 220, 248)),
    )
    return NativeFinish(
        _rgb8(paint), spec,
        (
            "botryoidal_domes", "double_chalcedony_crowns", "eccentric_flame_arcs",
            "ember_eyes", "radial_septa", "siliceous_bridges", "inner_flare_arcs",
            "interstitial_shadow",
        ),
        "packed botryoidal chalcedony domes with concentric ember and spectral fire",
    )


# ---------------------------------------------------------------------------
# MAGENTA WHORL -- analytic phyllotactic rosettes, not a recoloured mineral.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_fbl_magenta_whorl() -> NativeFinish:
    x, y = _xy()
    pitch_x, pitch_y = 31.0, 27.0
    row = np.floor(y / pitch_y).astype(np.int32)
    offset = (row & 1).astype(np.float32) * (pitch_x * 0.5)
    col = np.floor((x - offset) / pitch_x).astype(np.int32)
    cx = (col.astype(np.float32) + 0.5) * pitch_x + offset
    cy = (row.astype(np.float32) + 0.5) * pitch_y
    dx, dy = x - cx, y - cy
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    spin = 0.58 * np.sin(row.astype(np.float32) * 0.57) + 0.44 * np.cos(col.astype(np.float32) * 0.41)
    petal_count = 7.0 + ((row + col) & 1).astype(np.float32) * 2.0

    # Every flower is a mathematically coherent 27--31 px organism.  The
    # scalloped boundary, tier phase and spiral are all attached to its centre.
    boundary = 13.8 + 1.75 * np.cos(petal_count * theta + spin) + 0.65 * np.cos(2.0 * petal_count * theta - 0.35 * spin)
    petal_body = _inside(radius, boundary, 1.2)
    scalloped_corona = _ring(radius, boundary - 0.6, 2.2)
    outer_tier = _ring(radius, 10.6 + 0.85 * np.cos(petal_count * theta + spin), 1.55) * petal_body
    inner_tier = _ring(radius, 6.9 + 0.62 * np.cos(petal_count * theta - spin), 1.35) * petal_body
    spiral_ribbon = _ridge(
        (petal_count - 2.0) * theta + 0.72 * radius + spin,
        float(2.0 * np.pi), 0.54,
    ) * _inside(radius, boundary - 1.5, 1.0) * _inside(3.5, radius, 1.0)
    radial_filament = _f32(
        (np.cos(petal_count * theta - 0.18 * radius + spin) - 0.58) / 0.42
    ) * _inside(radius, boundary - 1.0, 1.2) * _inside(4.2, radius, 1.0)
    seed_pore = _inside(radius, 3.6 + 0.45 * np.cos(3.0 * theta + spin), 1.0)
    calyx_notch = _ring(radius, boundary + 1.0, 1.35) * _f32(
        (np.cos((petal_count + 2.0) * theta - spin) - 0.30) / 0.70
    )

    sector = (np.cos(petal_count * theta + 0.24 * radius + spin) >= 0.0).astype(np.float32)
    cell_flip = (((2 * row + col) & 3) < 2).astype(np.float32)
    a_owner = _f32(
        petal_body * (0.58 * sector + 0.42 * cell_flip)
        + 0.72 * spiral_ribbon
        + 0.30 * outer_tier
    )
    b_owner = _f32(
        petal_body * (0.58 * (1.0 - sector) + 0.42 * (1.0 - cell_flip))
        + 0.68 * inner_tier
        + 0.44 * seed_pore
    )
    whorl_tone = _f32(
        0.18 + 0.38 * (radius / 16.0) + 0.23 * np.sin(3.0 * theta + 0.31 * radius + spin)
        + 0.21 * scalloped_corona
    )

    base = _colour(
        _f32(0.10 + 0.50 * petal_body + 0.23 * whorl_tone),
        ("#09000b", "#21001f", "#3c0737", "#68115b", "#2c092f", "#0b0712"),
    ).astype(np.float32)
    magenta = _colour(
        _f32(0.04 + 0.65 * whorl_tone + 0.27 * spiral_ribbon),
        (
            "#220022", "#52004f", "#850076", "#b5009c", "#e000bd", "#ff28d7",
            "#ff72de", "#ffc0ec", "#ff739e", "#f43265", "#bf174e", "#75105b",
            "#5321a8", "#884bdf", "#f6a7ff",
        ),
    )
    opponent = _colour(
        _f32(0.08 + 0.55 * (1.0 - whorl_tone) + 0.32 * inner_tier),
        (
            "#02122a", "#003e73", "#006f9d", "#00a8b7", "#00d3aa", "#55ec83",
            "#c8ef42", "#ffe646", "#ffac32", "#ff6c45", "#f13679", "#a12bc4",
            "#522cbd", "#185fc5", "#65e9ee",
        ),
    )
    paint = _blend(base, magenta, _f32(0.84 * a_owner))
    paint = _blend(paint, opponent, _f32(0.78 * b_owner))
    paint = _blend(paint, np.full_like(opponent, (255, 216, 247)), _f32(0.42 * scalloped_corona + 0.36 * radial_filament))
    paint = _blend(paint, np.full_like(opponent, (56, 3, 48)), _f32(0.48 * seed_pore + 0.44 * calyx_notch))

    metal_f = _f32(0.05 + 0.66 * spiral_ribbon + 0.48 * radial_filament + 0.36 * a_owner + 0.16 * outer_tier)
    rough_f = _f32(0.14 + 0.56 * calyx_notch + 0.46 * seed_pore + 0.30 * scalloped_corona - 0.28 * inner_tier + 0.16 * radial_filament)
    coat_f = _f32(0.08 + 0.64 * b_owner + 0.42 * inner_tier + 0.31 * petal_body - 0.32 * seed_pore + 0.18 * outer_tier)
    spec = _spec3(
        _tiers(metal_f, (8, 26, 48, 74, 104, 140, 178, 216, 246)),
        _tiers(rough_f, (14, 32, 54, 80, 108, 140, 174, 212, 244)),
        _tiers(coat_f, (8, 24, 46, 72, 102, 138, 176, 216, 248)),
    )
    return NativeFinish(
        _rgb8(paint), spec,
        (
            "scalloped_petal_bodies", "corona_crests", "outer_petal_tiers",
            "inner_petal_tiers", "logarithmic_spiral_ribbons", "radial_filaments",
            "seed_pores", "calyx_notches",
        ),
        "edge-packed phyllotactic rosettes with scalloped tiers and opposed spiral sectors",
    )


# ---------------------------------------------------------------------------
# CORAL CLUSTER -- mineralised calice walls with living tissue in deep cups.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_fbl_coral_cluster() -> NativeFinish:
    x, y = _xy()
    pitch_x, pitch_y = 30.0, 26.0
    row = np.floor(y / pitch_y).astype(np.int32)
    offset = (row & 1).astype(np.float32) * 15.0
    col = np.floor((x - offset) / pitch_x).astype(np.int32)
    cx = (col.astype(np.float32) + 0.5) * pitch_x + offset
    cy = (row.astype(np.float32) + 0.5) * pitch_y
    phase = 0.47 * np.sin(row.astype(np.float32) * 0.43) + 0.39 * np.cos(col.astype(np.float32) * 0.59)
    # Cell-local distortion makes polygonal calices, not circular flower copies.
    dx = x - cx + 0.9 * np.sin((y - cy) * 0.31 + phase)
    dy = (y - cy) * 1.10 + 0.7 * np.cos((x - cx) * 0.27 - phase)
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)
    boundary = 13.1 + 1.15 * np.cos(6.0 * theta + phase) + 0.52 * np.cos(3.0 * theta - 0.6 * phase)

    calice_body = _inside(radius, boundary, 1.1)
    mineral_wall = _ring(radius, boundary - 0.3, 2.35)
    wall_crest = _ring(radius, boundary - 1.25, 1.10)
    cup_floor = _inside(radius, boundary - 3.2, 1.4)
    septal_teeth = _f32((np.cos(12.0 * theta + phase) - 0.54) / 0.46) * _inside(radius, boundary - 1.2, 1.0) * _inside(4.0, radius, 0.9)
    trabecular_ring = _ring(radius, 7.6 + 0.48 * np.cos(6.0 * theta - phase), 1.15) * cup_floor

    mouth_angle = 0.55 * np.sin(row.astype(np.float32) * 0.37 + col.astype(np.float32) * 0.23)
    ca, sa = np.cos(mouth_angle), np.sin(mouth_angle)
    mouth_x = dx * ca + dy * sa
    mouth_y = -dx * sa + dy * ca
    oral_slit_distance = np.sqrt((mouth_x / 4.8) ** 2 + (mouth_y / 2.1) ** 2)
    oral_pore = _inside(oral_slit_distance, 1.0, 0.26)

    # Daughter buds appear in a periodic biological budding sequence and stay
    # attached to their parent wall; this is not a detached fleck/noise pass.
    bud_selector = (((row + 2 * col) % 5) == 0).astype(np.float32)
    bud_angle = phase + 0.65
    bud_dx = dx - 7.2 * np.cos(bud_angle)
    bud_dy = dy - 7.2 * np.sin(bud_angle)
    bud_radius = np.sqrt(bud_dx * bud_dx + bud_dy * bud_dy)
    daughter_bud = _ring(bud_radius, 3.8, 1.35) * bud_selector * calice_body
    coenosarc_bridge = _f32(1.0 - calice_body) * cv2.GaussianBlur(mineral_wall.astype(np.float32), (0, 0), 2.0)

    depth = _f32(1.0 - radius / np.maximum(boundary, 1.0)) * cup_floor
    a_owner = _f32(0.70 * mineral_wall + 0.58 * wall_crest + 0.34 * septal_teeth + 0.28 * daughter_bud)
    b_owner = _f32(0.62 * cup_floor + 0.66 * trabecular_ring + 0.48 * oral_pore + 0.34 * daughter_bud)
    tissue_tone = _f32(0.12 + 0.48 * depth + 0.24 * np.sin(6.0 * theta + 0.22 * radius + phase) + 0.20 * trabecular_ring)

    base = _colour(
        _f32(0.16 + 0.43 * calice_body + 0.22 * depth),
        ("#100305", "#35100e", "#642118", "#8f3220", "#4c1519", "#17070c"),
    ).astype(np.float32)
    skeleton = _colour(
        _f32(0.08 + 0.52 * tissue_tone + 0.35 * wall_crest),
        (
            "#3b0507", "#78100b", "#b4220d", "#ec4716", "#ff7b2e", "#ffb14d",
            "#ffd37a", "#ff9b87", "#ff5b79", "#dd328e", "#9c2bad", "#5b319f",
            "#344cad", "#26a7a0", "#ffd1a1",
        ),
    )
    living = _colour(
        _f32(0.10 + 0.62 * (1.0 - tissue_tone) + 0.28 * trabecular_ring),
        (
            "#03142a", "#003f61", "#006f7b", "#009b8d", "#12c87d", "#76e665",
            "#d8ed54", "#ffe35d", "#ffad57", "#ff6f63", "#e83d87", "#aa33b7",
            "#6638c5", "#294db9", "#43d5ce",
        ),
    )
    paint = _blend(base, skeleton, _f32(0.88 * a_owner))
    paint = _blend(paint, living, _f32(0.76 * b_owner))
    paint = _blend(paint, np.full_like(living, (255, 205, 147)), _f32(0.42 * septal_teeth + 0.35 * wall_crest))
    paint = _blend(paint, np.full_like(living, (31, 2, 14)), _f32(0.74 * oral_pore))
    paint = _blend(paint, np.full_like(living, (68, 12, 19)), _f32(0.42 * coenosarc_bridge))

    metal_f = _f32(0.03 + 0.66 * mineral_wall + 0.48 * septal_teeth + 0.32 * daughter_bud + 0.18 * wall_crest)
    rough_f = _f32(0.12 + 0.56 * coenosarc_bridge + 0.48 * oral_pore + 0.34 * septal_teeth + 0.18 * mineral_wall - 0.32 * cup_floor)
    coat_f = _f32(0.08 + 0.68 * cup_floor + 0.52 * trabecular_ring + 0.38 * daughter_bud - 0.42 * oral_pore + 0.17 * depth)
    spec = _spec3(
        _tiers(metal_f, (6, 22, 42, 66, 94, 128, 166, 208, 244)),
        _tiers(rough_f, (16, 34, 56, 82, 112, 146, 182, 218, 246)),
        _tiers(coat_f, (8, 26, 48, 74, 104, 140, 178, 218, 248)),
    )
    return NativeFinish(
        _rgb8(paint), spec,
        (
            "polygonal_calice_bodies", "mineralised_walls", "wall_crests",
            "radial_septal_teeth", "trabecular_rings", "elliptical_oral_pores",
            "attached_daughter_buds", "coenosarc_bridges", "deep_cup_floors",
        ),
        "mineralised coral calices with septal teeth, living cup tissue, and attached buds",
    )


MIXED_FULLRES_IDS: Tuple[str, ...] = (
    "fmo_labradorite",
    "fmo_fire_agate",
    "fbl_magenta_whorl",
    "fbl_coral_cluster",
)

# The first native visual pass rejected the two floral studies as still too
# regular at full canvas scale.  The focused mineral studies were subsequently
# rejected too.  All four remain isolated negative evidence, never progress.
FULLRES_FOCUS_IDS: Tuple[str, ...] = ("fmo_labradorite", "fmo_fire_agate")
DEFERRED_IDS: Tuple[str, ...] = ("fbl_magenta_whorl", "fbl_coral_cluster")
REJECTED_IDS: Tuple[str, ...] = MIXED_FULLRES_IDS


_BUILDERS: Mapping[str, Callable[[], NativeFinish]] = {
    "fmo_labradorite": _build_fmo_labradorite,
    "fmo_fire_agate": _build_fmo_fire_agate,
    "fbl_magenta_whorl": _build_fbl_magenta_whorl,
    "fbl_coral_cluster": _build_fbl_coral_cluster,
}


def clear_cache() -> None:
    _build_fmo_labradorite.cache_clear()
    _build_fmo_fire_agate.cache_clear()
    _build_fbl_magenta_whorl.cache_clear()
    _build_fbl_coral_cluster.cache_clear()
    _xy.cache_clear()


def render_native(fid: str) -> NativeFinish:
    if fid not in _BUILDERS:
        raise KeyError(fid)
    return _BUILDERS[fid]()


def _mask2(mask: np.ndarray, height: int, width: int) -> np.ndarray:
    value = np.asarray(mask, np.float32)
    if value.ndim == 3:
        value = value[:, :, 0]
    if value.shape != (height, width):
        value = cv2.resize(value, (width, height), interpolation=cv2.INTER_LINEAR)
    return _f32(value)


def _paint_output(authored: NativeFinish, paint, shape, mask, pm) -> np.ndarray:
    height, width = int(shape[0]), int(shape[1])
    source = np.asarray(paint, np.float32)
    if source.ndim != 3 or source.shape[2] < 3:
        source = np.zeros((height, width, 3), np.float32)
    else:
        source = source[:, :, :3]
        if source.size and float(np.max(source)) > 1.5:
            source = source / 255.0
        if source.shape[:2] != (height, width):
            source = cv2.resize(source, (width, height), interpolation=cv2.INTER_LINEAR)
    candidate = authored.paint.astype(np.float32) / 255.0
    if (height, width) != (_SIZE, _SIZE):
        candidate = cv2.resize(candidate, (width, height), interpolation=cv2.INTER_AREA)
    alpha = (_mask2(mask, height, width) * max(0.0, float(pm)))[..., None]
    return np.clip(source * (1.0 - alpha) + candidate * alpha, 0, 1).astype(np.float32)


def _spec_output(authored: NativeFinish, shape, mask, sm) -> np.ndarray:
    height, width = int(shape[0]), int(shape[1])
    candidate = authored.spec
    if (height, width) != (_SIZE, _SIZE):
        candidate = cv2.resize(candidate, (width, height), interpolation=cv2.INTER_NEAREST)
    candidate_f = candidate.astype(np.float32)
    active = np.clip(_CALM_SPEC + (candidate_f - _CALM_SPEC) * max(0.0, float(sm)), 0, 255)
    alpha = _mask2(mask, height, width)[..., None]
    rgb = active * alpha + _CALM_SPEC * (1.0 - alpha)
    output = np.empty((height, width, 4), np.uint8)
    output[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    output[:, :, 3] = 255
    return output


# Dedicated module-level registry functions keep ownership auditable.  Each
# body calls its own physical builder; none is a closure or dynamic dispatcher.
def paint_fmo_labradorite(paint, shape, mask, seed, pm, bb):
    authored = _build_fmo_labradorite()
    return _paint_output(authored, paint, shape, mask, pm)


def spec_fmo_labradorite(shape, mask, seed, sm):
    authored = _build_fmo_labradorite()
    return _spec_output(authored, shape, mask, sm)


def paint_fmo_fire_agate(paint, shape, mask, seed, pm, bb):
    authored = _build_fmo_fire_agate()
    return _paint_output(authored, paint, shape, mask, pm)


def spec_fmo_fire_agate(shape, mask, seed, sm):
    authored = _build_fmo_fire_agate()
    return _spec_output(authored, shape, mask, sm)


def paint_fbl_magenta_whorl(paint, shape, mask, seed, pm, bb):
    authored = _build_fbl_magenta_whorl()
    return _paint_output(authored, paint, shape, mask, pm)


def spec_fbl_magenta_whorl(shape, mask, seed, sm):
    authored = _build_fbl_magenta_whorl()
    return _spec_output(authored, shape, mask, sm)


def paint_fbl_coral_cluster(paint, shape, mask, seed, pm, bb):
    authored = _build_fbl_coral_cluster()
    return _paint_output(authored, paint, shape, mask, pm)


def spec_fbl_coral_cluster(shape, mask, seed, sm):
    authored = _build_fbl_coral_cluster()
    return _spec_output(authored, shape, mask, sm)


_REGISTRY_ENTRIES = {
    "fmo_labradorite": (spec_fmo_labradorite, paint_fmo_labradorite),
    "fmo_fire_agate": (spec_fmo_fire_agate, paint_fmo_fire_agate),
    "fbl_magenta_whorl": (spec_fbl_magenta_whorl, paint_fbl_magenta_whorl),
    "fbl_coral_cluster": (spec_fbl_coral_cluster, paint_fbl_coral_cluster),
}


def install_into_engine(mono_reg, base_reg=None):
    """Fail closed: native inspection rejected every study in this module."""
    raise RuntimeError("rejected full-resolution Wilds studies must never be installed")


def _sha(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _write_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), cv2.cvtColor(np.asarray(image, np.uint8), cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def _write_gray(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), np.asarray(image, np.uint8)):
        raise OSError(f"could not write {path}")


def _detail_origin(fid: str) -> Tuple[int, int]:
    return {
        "fmo_labradorite": (704, 768),
        "fmo_fire_agate": (768, 640),
        "fbl_magenta_whorl": (736, 800),
        "fbl_coral_cluster": (800, 704),
    }[fid]


def audit_fullres(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for fid in FULLRES_FOCUS_IDS:
        clear_cache()
        started = time.perf_counter()
        first = render_native(fid)
        render_seconds = time.perf_counter() - started
        paint_sha = _sha(first.paint)
        spec_sha = _sha(first.spec)

        # A second uncached native build proves deterministic pixels and gives
        # an honest repeat timing rather than a cached timing claim.
        _BUILDERS[fid].cache_clear()
        repeat_started = time.perf_counter()
        repeat = render_native(fid)
        repeat_seconds = time.perf_counter() - repeat_started
        deterministic = paint_sha == _sha(repeat.paint) and spec_sha == _sha(repeat.spec)
        angle_a, angle_b = _angle_pair(first)

        stem = fid.upper()
        paths = {
            "paint": output / f"{stem}_PAINT_2048.png",
            "metal": output / f"{stem}_M_2048.png",
            "roughness": output / f"{stem}_R_2048.png",
            "clearcoat": output / f"{stem}_CC_2048.png",
            "angle_a": output / f"{stem}_ANGLE_A_2048.png",
            "angle_b": output / f"{stem}_ANGLE_B_2048.png",
            "detail": output / f"{stem}_PAINT_DETAIL_1TO1_512.png",
        }
        _write_rgb(paths["paint"], first.paint)
        _write_gray(paths["metal"], first.spec[:, :, 0])
        _write_gray(paths["roughness"], first.spec[:, :, 1])
        _write_gray(paths["clearcoat"], first.spec[:, :, 2])
        _write_rgb(paths["angle_a"], angle_a)
        _write_rgb(paths["angle_b"], angle_b)
        ox, oy = _detail_origin(fid)
        _write_rgb(paths["detail"], first.paint[oy:oy + 512, ox:ox + 512])

        channels = {}
        for index, name in enumerate(("M", "R", "Cc")):
            channel = first.spec[:, :, index]
            channels[name] = {
                "min": int(channel.min()),
                "max": int(channel.max()),
                "std": round(float(channel.std()), 4),
                "unique_values": int(np.unique(channel).size),
                "sha256": _sha(channel),
            }
        records.append({
            "id": fid,
            "visual_verdict": "REJECT-DEFER",
            "visual_reason": (
                "repeated capsule/lamella-row fabric"
                if fid == "fmo_labradorite"
                else "dense equal-dot/botryoid paver with repeated units"
            ),
            "native_size": [int(first.paint.shape[1]), int(first.paint.shape[0])],
            "process": first.process,
            "marks": list(first.marks),
            "mark_count": len(first.marks),
            "paint_sha256": paint_sha,
            "spec_sha256": spec_sha,
            "angle_a_sha256": _sha(angle_a),
            "angle_b_sha256": _sha(angle_b),
            "angle_flip_mean_abs_rgb": round(float(np.mean(np.abs(angle_a.astype(np.int16) - angle_b.astype(np.int16)))), 4),
            "render_seconds_uncached": round(render_seconds, 4),
            "repeat_seconds_uncached": round(repeat_seconds, 4),
            "render_budget_pass": bool(max(render_seconds, repeat_seconds) <= 3.0),
            "deterministic_repeat": bool(deterministic),
            "paint_rgb_std": [round(float(first.paint[:, :, i].std()), 4) for i in range(3)],
            "channels": channels,
            "files": {key: path.name for key, path in paths.items()},
        })
        del first, repeat, angle_a, angle_b

    payload = {
        "schema": "spb-fractured-wilds-native2048-mixed/1",
        "status": "rejected-fullres-studies-do-not-wire",
        "acceptance_target": "native 2048x2048 only; no picker-size acceptance",
        "prohibitions": ["rng", "seed variation", "noise", "grain", "stochastic jitter", "shared topology recolours"],
        "deferred_after_fullres_visual_rejection": list(DEFERRED_IDS),
        "records": records,
    }
    json_path = output / "FULLRES_AUDIT.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Fractured Wilds mixed native-2048 rebuild report",
        "",
        "Status: **REJECTED / DEFERRED**. Negative-study evidence only; never registry-wire.",
        "",
        "The visual acceptance target in this pass is the full 2048×2048 canvas. No picker-size image was generated or judged. Every reported row was rebuilt twice uncached to prove deterministic output and records independent paint/spec hashes.",
        "",
        "Rejected after native visual inspection: `fmo_labradorite` reads as repeated capsule/lamella-row fabric; `fmo_fire_agate` reads as a dense equal-dot/botryoid paver. Deferred after the first native visual pass: `fbl_magenta_whorl` and `fbl_coral_cluster`, both regular repeated-cell fields. None are dressed up as progress.",
        "",
        "| Finish | Visual verdict | Reason | Native render (first/repeat) | Deterministic | 3s budget |",
        "|---|---|---|---:|---:|---:|",
    ]
    for record in records:
        lines.append(
            f"| `{record['id']}` | **{record['visual_verdict']}** | {record['visual_reason']} | "
            f"{record['render_seconds_uncached']:.4f}s / {record['repeat_seconds_uncached']:.4f}s | "
            f"{'PASS' if record['deterministic_repeat'] else 'FAIL'} | "
            f"{'PASS' if record['render_budget_pass'] else 'FAIL'} |"
        )
    lines.extend(["", "## Independent material channels", ""])
    for record in records:
        lines.append(f"### `{record['id']}`")
        lines.append("")
        lines.append("Causal mark vocabulary: " + ", ".join(record["marks"]) + ".")
        lines.append("")
        lines.append("| Channel | Range | Std-dev | Distinct authored tiers | SHA-256 |")
        lines.append("|---|---:|---:|---:|---|")
        for name in ("M", "R", "Cc"):
            channel = record["channels"][name]
            lines.append(
                f"| {name} | {channel['min']}–{channel['max']} | {channel['std']:.4f} | "
                f"{channel['unique_values']} | `{channel['sha256']}` |"
            )
        lines.append("")
        lines.append(f"Paint hash: `{record['paint_sha256']}`  ")
        lines.append(f"Combined spec hash: `{record['spec_sha256']}`")
        lines.append("")
    lines.extend([
        "## Honest scope boundary",
        "",
        "These files preserve why mechanical compliance is insufficient. Native resolution, deterministic construction, timing, mark count, channel tiers, and A/B material separation did not rescue visibly repeated topology. All four studies are rejected/deferred and cannot be installed from this module.",
        "",
    ])
    (output / "FULLRES_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_wilds_fullres_progress_20260824/mixed"),
    )
    args = parser.parse_args()
    payload = audit_fullres(args.output)
    for record in payload["records"]:
        print(
            record["id"],
            f"{record['render_seconds_uncached']:.4f}s/{record['repeat_seconds_uncached']:.4f}s",
            "budget=PASS" if record["render_budget_pass"] else "budget=FAIL",
            "deterministic=PASS" if record["deterministic_repeat"] else "deterministic=FAIL",
        )
    return 0 if all(r["render_budget_pass"] and r["deterministic_repeat"] for r in payload["records"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "MIXED_FULLRES_IDS", "FULLRES_FOCUS_IDS", "DEFERRED_IDS", "REJECTED_IDS", "NativeFinish", "render_native", "clear_cache",
    "install_into_engine", "audit_fullres",
]
