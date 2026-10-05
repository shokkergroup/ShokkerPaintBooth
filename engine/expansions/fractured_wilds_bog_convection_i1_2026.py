# -*- coding: utf-8 -*-
"""Isolated native-2048 Bog Murk buoyant-raft convection study.

SPB-105 / Wilds attempt 64 / 2026-08-25. Owner verdict controlling this edit:
native 2048 art, fine 8-32 px detail, no lazy recolors, no random noise used to
fake uniqueness, and authentic Fractured color travel.

W36's disconnected bent short-mark swarm is frozen. I1 starts from blank
topology: a continuous analytic material sheet is inverse-transported through
unequal buoyant vortices and shear events. Filled microbial rafts own the
surface; meniscus borders, methane mouths, reed interruptions, sinking tongues,
wake curls, fold laminae and rupture lips are separate causal consequences.
There is no RNG, sampled noise, FBM, particles, cells, glyph placement, or
shared Wilds composer. Native verdict: REJECTED. Exact runs were 0.889-0.933 s
with A/B 0.174180/0.400704, but the image collapsed into broad scalar color
territories, contour rails and repeated square vent marks. Frozen root-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

import cv2
import numpy as np


ID = "fc_bog_murk"
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


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.nan_to_num(np.asarray(a, np.float32))
    lo, hi = np.percentile(a, (0.5, 99.5))
    if float(hi - lo) < 1e-7:
        return np.zeros_like(a)
    return _f((a - lo) / (hi - lo))


def _phase_distance(phase: np.ndarray, center: float) -> np.ndarray:
    return np.abs((phase - center + 0.5) % 1.0 - 0.5)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    d = _phase_distance(phase, center) / max(float(width), 1e-5)
    return np.exp(-2.7 * d * d).astype(np.float32)


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    idx = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx.astype(np.int32)]


def _palette(t: np.ndarray) -> np.ndarray:
    colors = np.asarray([
        (0.012, 0.025, 0.020),
        (0.020, 0.120, 0.075),
        (0.035, 0.285, 0.135),
        (0.160, 0.480, 0.175),
        (0.480, 0.620, 0.155),
        (0.800, 0.670, 0.175),
        (0.915, 0.420, 0.145),
        (0.660, 0.180, 0.250),
        (0.450, 0.090, 0.430),
        (0.235, 0.120, 0.585),
        (0.080, 0.265, 0.620),
        (0.025, 0.485, 0.540),
        (0.040, 0.390, 0.260),
    ], np.float32)
    u = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(u).astype(np.int32) % len(colors)
    i1 = (i0 + 1) % len(colors)
    q = (u - np.floor(u))[..., None]
    return colors[i0] * (1.0 - q) + colors[i1] * q


def _transport(x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    qx, qy = x.copy(), y.copy()
    curl = np.zeros_like(x)
    events = (
        (-0.72, -0.18, +0.0080, 0.16, +0.0016),
        (-0.23, +0.42, -0.0105, 0.20, -0.0012),
        (+0.29, -0.44, +0.0072, 0.14, +0.0019),
        (+0.68, +0.18, -0.0064, 0.22, -0.0015),
        (+0.05, +0.78, +0.0047, 0.18, +0.0011),
    )
    for _ in range(8):
        vx = 0.0018 + 0.0015 * qy
        vy = -0.0046 + 0.0009 * np.sin(2.3 * qx)
        for cx, cy, spin, core, shear in events:
            dx, dy = qx - cx, qy - cy
            r2 = dx * dx + dy * dy + core * core
            env = np.exp(-0.72 * r2)
            vx += env * (-spin * dy / r2 + shear * dx)
            vy += env * (+spin * dx / r2 - shear * dy)
            curl += env * spin / (core + np.sqrt(r2))
        qx -= vx
        qy -= vy
    return qx.astype(np.float32), qy.astype(np.float32), curl.astype(np.float32)


def _build() -> Grammar:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK * 2.0 - 1.0
    y = (yy + 0.5) / WORK * 2.0 - 1.0
    qx, qy, curl = _transport(x, y)

    # Several unequal material modes form connected area, not contour art.
    density_raw = (
        0.95 * np.sin(5.7 * qx + 2.1 * qy)
        + 0.72 * np.sin(-3.2 * qx + 7.4 * qy + 0.8)
        + 0.48 * np.sin(8.9 * qx + 5.1 * qy - 0.4)
        + 0.31 * np.sin(13.7 * qx - 4.3 * qy + 0.9)
        + 2.2 * curl
    )
    density = _norm(density_raw)
    raft = _f(1.0 / (1.0 + np.exp(-(density - 0.48) * 8.5)))

    # Meniscus is narrow, but its two shoulders belong to different angle banks.
    smooth = cv2.GaussianBlur(raft, (0, 0), 1.15)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    edge = _norm(np.hypot(gx, gy))
    meniscus_a = _f(edge * (0.5 + 0.5 * np.tanh(4.0 * (gx - 0.25 * gy))))
    meniscus_b = _f(edge * (0.5 + 0.5 * np.tanh(4.0 * (-gx + 0.25 * gy))))

    # Fine fold laminae are confined to raft interiors. At WORK=512 their
    # 2-7 px cadence becomes 8-28 px on the native canvas.
    fold_phase = np.mod(17.0 * qx + 11.0 * qy
                        + 1.8 * np.sin(3.1 * qx - 2.4 * qy)
                        + 0.7 * curl, 1.0)
    folds = _f(_pulse(fold_phase, 0.16, 0.075) * raft)

    # Methane mouths require a pressure crest, a cross-material phase meeting,
    # and positive curl. They are not placed dots or a free ring field.
    pressure = np.mod(4.1 * qx - 6.3 * qy + 0.24 * density_raw, 1.0)
    throat = np.mod(7.7 * qx + 3.9 * qy - 0.31 * density_raw, 1.0)
    mouth_core = _pulse(pressure, 0.08, 0.060) * _pulse(throat, 0.61, 0.070)
    mouths = _f(mouth_core * raft * np.clip(3.5 * curl + 0.35, 0, 1))
    mouth_rims = _f(cv2.dilate(mouths, np.ones((5, 5), np.uint8), iterations=1) - mouths)

    # Reed interruptions are thin cuts through existing mass, broken by raft
    # age; sinking tongues use a downward material derivative, not a glyph.
    reed_phase = np.mod(14.0 * qx + 0.9 * np.sin(5.2 * qy), 1.0)
    reed_gate = np.clip((np.sin(0.47 * density_raw + 8.6 * qy) - 0.25) * 1.5, 0, 1)
    reeds = _f(_pulse(reed_phase, 0.52, 0.038) * reed_gate * (0.4 + 0.6 * raft))
    ddy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    tongue_phase = np.mod(5.3 * qx + 0.18 * density_raw - 1.9 * qy, 1.0)
    tongues = _f(np.clip(ddy * 3.2, 0, 1) * _pulse(tongue_phase, 0.73, 0.11)
                 * (0.35 + 0.65 * raft))

    wake_phase = np.mod(3.7 * np.arctan2(gy, gx) / (2.0 * np.pi)
                        + 0.16 * density_raw + 2.2 * curl, 1.0)
    wakes = _f(_pulse(wake_phase, 0.27, 0.055)
               * np.clip(np.abs(curl) * 5.5, 0, 1)
               * (0.25 + 0.75 * (1.0 - raft)))
    rupture = _f(np.maximum(meniscus_a, meniscus_b)
                 * _pulse(np.mod(fold_phase + pressure, 1.0), 0.91, 0.055)
                 * (0.35 + 0.65 * tongues))

    age_t = np.mod(0.19 * density_raw + 0.27 * qx - 0.16 * qy
                   + 0.11 * folds + 0.09 * curl, 1.0)
    tissue = _palette(age_t)
    paint = tissue * (0.27 + 0.45 * raft + 0.13 * folds)[..., None]
    paint += meniscus_a[..., None] * np.asarray((0.06, 0.48, 0.40), np.float32)
    paint += meniscus_b[..., None] * np.asarray((0.56, 0.12, 0.38), np.float32)
    paint += mouth_rims[..., None] * np.asarray((0.80, 0.62, 0.18), np.float32)
    paint -= mouths[..., None] * np.asarray((0.23, 0.18, 0.13), np.float32)
    paint += tongues[..., None] * np.asarray((0.16, 0.37, 0.50), np.float32)
    paint += wakes[..., None] * np.asarray((0.52, 0.25, 0.55), np.float32)
    paint -= reeds[..., None] * np.asarray((0.19, 0.15, 0.12), np.float32)
    paint += rupture[..., None] * np.asarray((0.74, 0.34, 0.13), np.float32)
    paint = _f(paint)

    neutral = _f(0.18 + 0.43 * raft + 0.18 * folds + 0.24 * meniscus_a
                 + 0.20 * meniscus_b + 0.28 * mouth_rims - 0.22 * mouths
                 + 0.23 * tongues + 0.19 * wakes - 0.17 * reeds
                 + 0.24 * rupture)
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    metal_field = _f(0.04 + 0.71 * meniscus_a + 0.58 * mouth_rims
                     + 0.45 * rupture + 0.32 * folds - 0.26 * mouths)
    rough_field = _f(0.12 + 0.62 * raft + 0.55 * reeds + 0.43 * tongues
                     - 0.36 * meniscus_a - 0.28 * mouth_rims)
    coat_field = _f(0.05 + 0.67 * meniscus_b + 0.52 * wakes
                    + 0.41 * folds + 0.35 * mouth_rims - 0.31 * reeds)
    metal = _tier(metal_field, (7, 31, 59, 91, 127, 167, 209, 248))
    rough = _tier(rough_field, (14, 41, 71, 105, 141, 179, 218, 250))
    coat = _tier(coat_field, (6, 28, 56, 89, 126, 167, 211, 252))

    marks = (
        ("microbial_rafts", raft, "A"),
        ("leading_menisci", meniscus_a, "A"),
        ("trailing_menisci", meniscus_b, "B"),
        ("fold_laminae", folds, "A"),
        ("methane_mouths", mouths, "B"),
        ("mouth_rims", mouth_rims, "A"),
        ("reed_interruptions", reeds, "N"),
        ("sinking_tongues", tongues, "B"),
        ("wake_curls", wakes, "B"),
        ("rupture_lips", rupture, "A"),
    )
    if any(float(mask.std()) < 0.004 for _name, mask, _bank in marks):
        raise ValueError("Bog Murk I1 has an absent causal mark")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="continuous buoyant microbial raft sheet with attached convection consequences",
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
    out = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        out[bank] = np.maximum(out[bank], mask)
    return out


def debug_angle_pair(fid: str = ID) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if fid != ID:
        raise KeyError(fid)
    grammar = _build()
    owners = owner_unions(grammar)
    a = grammar.paint * (0.38 + 0.59 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.05, 0.48, 0.38), np.float32)
    a += owners["B"][..., None] * np.asarray((0.19, 0.04, 0.24), np.float32)
    b = grammar.paint * (0.37 + 0.60 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.58, 0.08, 0.40), np.float32)
    b += owners["A"][..., None] * np.asarray((0.31, 0.28, 0.04), np.float32)
    a, b = _f(a), _f(b)
    return a, b, np.abs(a - b).astype(np.float32)


BUILDERS = {ID: _build}
