"""Shared math utilities for Neon Underground v4.

The v3 failure was a shared *visual* grammar: dark micro-packet carpets and
equal-population material tiers.  This module therefore supplies mechanics,
not a finish composer.  Every finish owns its broad carrier, paint hierarchy,
alternate view state, and physical M/R/Cc score equations.

SPB-105 / NU-V4-1, 2026-08-27. Owner verdict: the prior 25 neither looked
neon nor carried Oil Slick's coherent SPEC behavior.  V4 keeps Oil Slick's
continuous-field causality while restoring tuner/nightlife identity.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Mapping, Sequence

import cv2
import numpy as np


WORK = 1024
NATIVE = 2048

M_LEVELS = np.asarray((6, 27, 50, 75, 102, 131, 162, 194, 224, 250), np.uint8)
R_LEVELS = np.asarray((12, 32, 55, 80, 107, 136, 167, 198, 226, 249), np.uint8)
C_LEVELS = np.asarray((5, 29, 53, 78, 105, 134, 165, 197, 226, 252), np.uint8)


@dataclass(frozen=True)
class FinishResult:
    finish_id: str
    display_name: str
    paint: np.ndarray
    spec: np.ndarray
    paint_b: np.ndarray
    carrier: str
    material_story: Mapping[str, str]
    elapsed_seconds: float


def begin() -> float:
    return time.perf_counter()


def coords(size: int = WORK) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    return (x + 0.5) / size * 2.0 - 1.0, (y + 0.5) / size * 2.0 - 1.0


def unit(values: np.ndarray) -> np.ndarray:
    a = np.asarray(values, np.float32)
    lo, hi = float(np.min(a)), float(np.max(a))
    return np.clip((a - lo) / max(hi - lo, 1e-7), 0.0, 1.0)


def smooth(lo: float, hi: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((np.asarray(values, np.float32) - lo) / max(hi - lo, 1e-7), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def blur(values: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(np.asarray(values, np.float32), (0, 0), max(0.35, float(sigma)))


def soft_noise(seed: int, size: int, sigma: float, detail_sigma: float | None = None) -> np.ndarray:
    """Deterministic subordinate texture; never use as a finish carrier."""
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    broad = unit(blur(rng.standard_normal((size, size), dtype=np.float32), sigma))
    if detail_sigma is None:
        return broad
    detail = unit(blur(rng.standard_normal((size, size), dtype=np.float32), detail_sigma))
    return np.clip(0.76 * broad + 0.24 * detail, 0.0, 1.0)


def warp_vortices(
    x: np.ndarray,
    y: np.ndarray,
    vortices: Sequence[tuple[float, float, float, float]],
) -> tuple[np.ndarray, np.ndarray]:
    qx, qy = np.asarray(x, np.float32).copy(), np.asarray(y, np.float32).copy()
    for cx, cy, radius, strength in vortices:
        dx, dy = qx - cx, qy - cy
        influence = np.exp(-(dx * dx + dy * dy) / max(radius * radius, 1e-5))
        angle = strength * influence
        ca, sa = np.cos(angle), np.sin(angle)
        qx, qy = cx + ca * dx - sa * dy, cy + sa * dx + ca * dy
    return qx, qy


def palette_cycle(phase: np.ndarray, stops: Sequence[Sequence[float]]) -> np.ndarray:
    p = np.mod(np.asarray(phase, np.float32), 1.0)
    colors = np.asarray(stops, np.float32)
    if colors.max() > 1.5:
        colors = colors / 255.0
    scaled = p * len(colors)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return colors[lo] * (1.0 - mix) + colors[(lo + 1) % len(colors)] * mix


def palette_ramp(values: np.ndarray, stops: Sequence[Sequence[float]]) -> np.ndarray:
    v = np.clip(np.asarray(values, np.float32), 0.0, 1.0)
    colors = np.asarray(stops, np.float32)
    if colors.max() > 1.5:
        colors = colors / 255.0
    scaled = v * (len(colors) - 1)
    lo = np.minimum(np.floor(scaled).astype(np.int16), len(colors) - 2)
    mix = (scaled - lo)[..., None]
    return colors[lo] * (1.0 - mix) + colors[lo + 1] * mix


def ridge(phase: np.ndarray, width: float = 0.12) -> np.ndarray:
    """Periodic line bundle with controllable fine width."""
    d = np.abs(np.mod(np.asarray(phase, np.float32) + 0.5, 1.0) - 0.5)
    return np.exp(-((d / max(width, 1e-4)) ** 2))


def edge(field: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(np.asarray(field, np.float32))
    return unit(np.sqrt(gx * gx + gy * gy))


def normal_light(height: np.ndarray, light: tuple[float, float, float]) -> np.ndarray:
    gy, gx = np.gradient(np.asarray(height, np.float32))
    nz = np.ones_like(gx) * 0.025
    norm = np.sqrt(gx * gx + gy * gy + nz * nz)
    nx, ny, nz = -gx / norm, -gy / norm, nz / norm
    lx, ly, lz = light
    return np.clip(nx * lx + ny * ly + nz * lz, -0.55, 1.0)


def tier_channel(
    score: np.ndarray,
    cuts: Sequence[float],
    levels: np.ndarray,
) -> np.ndarray:
    """Physical thresholds, never quantiles; territory populations stay organic."""
    s = np.clip(np.asarray(score, np.float32), 0.0, 1.0)
    if len(cuts) != len(levels) - 1:
        raise ValueError("cuts must contain exactly len(levels)-1 thresholds")
    return np.asarray(levels, np.uint8)[np.digitize(s, np.asarray(cuts, np.float32))]


DEFAULT_CUTS = (0.07, 0.15, 0.24, 0.34, 0.45, 0.57, 0.69, 0.81, 0.91)


def pack_physical(
    metal: np.ndarray,
    rough: np.ndarray,
    coat: np.ndarray,
    *,
    m_cuts: Sequence[float] = DEFAULT_CUTS,
    r_cuts: Sequence[float] = DEFAULT_CUTS,
    c_cuts: Sequence[float] = DEFAULT_CUTS,
) -> np.ndarray:
    return np.stack(
        (
            tier_channel(metal, m_cuts, M_LEVELS),
            tier_channel(rough, r_cuts, R_LEVELS),
            tier_channel(coat, c_cuts, C_LEVELS),
        ),
        axis=2,
    )


def finish(
    started: float,
    finish_id: str,
    display_name: str,
    paint: np.ndarray,
    paint_b: np.ndarray,
    spec: np.ndarray,
    carrier: str,
    material_story: Mapping[str, str],
) -> FinishResult:
    a = np.ascontiguousarray(np.clip(np.asarray(paint, np.float32), 0.0, 1.0))
    b = np.ascontiguousarray(np.clip(np.asarray(paint_b, np.float32), 0.0, 1.0))
    s = np.ascontiguousarray(np.clip(np.asarray(spec), 0, 255).astype(np.uint8))
    if a.ndim != 3 or a.shape[2] != 3 or b.shape != a.shape or s.shape != a.shape:
        raise ValueError(f"invalid Neon v4 result shapes: {a.shape}, {b.shape}, {s.shape}")
    return FinishResult(
        finish_id=finish_id,
        display_name=display_name,
        paint=a,
        spec=s,
        paint_b=b,
        carrier=carrier,
        material_story=dict(material_story),
        elapsed_seconds=time.perf_counter() - started,
    )


def resize_result(result: FinishResult, size: int = NATIVE) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = cv2.resize(result.paint, (size, size), interpolation=cv2.INTER_CUBIC)
    b = cv2.resize(result.paint_b, (size, size), interpolation=cv2.INTER_CUBIC)
    s = cv2.resize(result.spec, (size, size), interpolation=cv2.INTER_NEAREST)
    return np.clip(a, 0.0, 1.0), np.clip(b, 0.0, 1.0), s
