"""Shared utilities for the isolated Neon Underground Oil-Slick reset pilots.

SPB-105 / owner verdict 2026-08-27: the rejected Neon v2 field used literal
motif wallpaper and generic spec underlays.  This module intentionally owns no
carrier or finish composer.  It only provides deterministic raster helpers,
eight-tier grayscale material mapping, evidence rendering, and audit stats.
Every pilot must author its own paint anatomy and three causal score fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import time
from typing import Mapping, Sequence

import cv2
import numpy as np


NATIVE = 2048
WORK = 1024

M_LEVELS = np.asarray((7, 33, 67, 104, 142, 181, 219, 253), np.uint8)
R_LEVELS = np.asarray((8, 30, 61, 99, 140, 179, 220, 251), np.uint8)
C_LEVELS = np.asarray((6, 32, 65, 103, 143, 181, 217, 254), np.uint8)


@dataclass(frozen=True)
class GeometryMark:
    family: str
    width_native: float
    count: int = 1


@dataclass
class PilotResult:
    finish_id: str
    display_name: str
    paint: np.ndarray
    spec: np.ndarray
    masks: Mapping[str, np.ndarray]
    geometry: Sequence[GeometryMark]
    material_story: Mapping[str, str]
    carrier: str
    vetoes: Sequence[str] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0


def seeded(seed: int) -> np.random.Generator:
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def native_px(value: float, size: int = WORK) -> int:
    return max(1, int(round(float(value) * float(size) / float(NATIVE))))


def unit(values: np.ndarray) -> np.ndarray:
    a = np.asarray(values, np.float32)
    lo = float(np.min(a))
    hi = float(np.max(a))
    return np.clip((a - lo) / max(hi - lo, 1e-7), 0.0, 1.0)


def smoothstep(lo: float, hi: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((np.asarray(values, np.float32) - lo) / max(hi - lo, 1e-7), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def blur(mask: np.ndarray, sigma_native: float, size: int = WORK) -> np.ndarray:
    sigma = max(0.35, float(sigma_native) * float(size) / float(NATIVE))
    return cv2.GaussianBlur(np.asarray(mask, np.float32), (0, 0), sigma)


def distance(mask: np.ndarray) -> np.ndarray:
    binary = (np.asarray(mask) > 0.5).astype(np.uint8)
    return cv2.distanceTransform(binary, cv2.DIST_L2, 5).astype(np.float32)


def signed_distance(mask: np.ndarray) -> np.ndarray:
    binary = (np.asarray(mask) > 0.5).astype(np.uint8)
    return distance(binary) - distance(1 - binary)


def mask_edge(mask: np.ndarray, width_native: float, size: int = WORK) -> np.ndarray:
    sd = np.abs(signed_distance(mask))
    width = max(0.75, float(width_native) * float(size) / float(NATIVE))
    return np.clip(1.0 - sd / width, 0.0, 1.0).astype(np.float32)


def add_glow(
    paint: np.ndarray,
    mask: np.ndarray,
    color: Sequence[float],
    sigma_native: float,
    strength: float,
    size: int = WORK,
) -> None:
    glow = blur(mask, sigma_native, size)
    paint += glow[..., None] * np.asarray(color, np.float32) * float(strength)


def quantile_tiers(field_values: np.ndarray, levels: np.ndarray) -> np.ndarray:
    """Quantize one authored continuous response into eight occupied bands.

    The caller owns the causal score.  This helper only exposes its range; it
    must never be fed unrelated noise to manufacture channel variance.
    """
    values = np.asarray(field_values, np.float32)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("material score has no finite values")
    cuts = np.quantile(finite, np.arange(1, len(levels), dtype=np.float32) / len(levels))
    # Deterministic microscopic ordering resolves tied plateaus without adding
    # a visible texture field.  It is far below one uint8 material tier.
    yy, xx = np.mgrid[0:values.shape[0], 0:values.shape[1]]
    tie = ((xx * 0.754877666 + yy * 0.569840296) % 1.0).astype(np.float32) * 1e-7
    index = np.searchsorted(cuts, values + tie, side="right")
    return np.asarray(levels, np.uint8)[index]


def pack_material(m_score: np.ndarray, r_score: np.ndarray, c_score: np.ndarray) -> np.ndarray:
    return np.stack(
        (
            quantile_tiers(m_score, M_LEVELS),
            quantile_tiers(r_score, R_LEVELS),
            quantile_tiers(c_score, C_LEVELS),
        ),
        axis=2,
    )


def resize_result(result: PilotResult, size: int = NATIVE) -> tuple[np.ndarray, np.ndarray]:
    paint = cv2.resize(
        np.clip(np.asarray(result.paint, np.float32), 0.0, 1.0),
        (size, size),
        interpolation=cv2.INTER_CUBIC,
    )
    spec = cv2.resize(
        np.clip(np.asarray(result.spec), 0, 255).astype(np.uint8),
        (size, size),
        interpolation=cv2.INTER_NEAREST,
    )
    return np.clip(paint, 0.0, 1.0), spec


def material_stats(spec: np.ndarray) -> dict[str, object]:
    s = np.asarray(spec, np.float32)
    names = ("M", "R", "Cc")
    arrays = tuple(s[..., i] for i in range(3))
    corr = np.corrcoef(np.stack([a.ravel() for a in arrays]))
    return {
        "std": {name: round(float(a.std()), 6) for name, a in zip(names, arrays)},
        "range": {name: [int(a.min()), int(a.max())] for name, a in zip(names, arrays)},
        "tier_count": {name: int(len(np.unique(a))) for name, a in zip(names, arrays)},
        "correlation": {
            "M_R": round(float(corr[0, 1]), 6),
            "M_Cc": round(float(corr[0, 2]), 6),
            "R_Cc": round(float(corr[1, 2]), 6),
        },
    }


def geometry_stats(marks: Sequence[GeometryMark]) -> dict[str, object]:
    widths: list[float] = []
    families: dict[str, int] = {}
    for mark in marks:
        families[mark.family] = families.get(mark.family, 0) + int(mark.count)
        widths.extend([float(mark.width_native)] * max(1, int(mark.count)))
    a = np.asarray(widths, np.float32) if widths else np.asarray((0.0,), np.float32)
    fine = (a >= 8.0) & (a <= 32.0)
    return {
        "family_count": len(families),
        "families": families,
        "width_native_min": round(float(a.min()), 3),
        "width_native_median": round(float(np.median(a)), 3),
        "width_native_p90": round(float(np.percentile(a, 90)), 3),
        "width_native_max": round(float(a.max()), 3),
        "fine_8_32_fraction": round(float(np.mean(fine)), 6),
    }


def mask_coverage(masks: Mapping[str, np.ndarray]) -> dict[str, float]:
    return {
        name: round(float(np.mean(np.asarray(mask, np.float32) > 0.15)), 6)
        for name, mask in masks.items()
    }


def on_car_proxy(paint: np.ndarray, spec: np.ndarray, phase: float = 0.52) -> np.ndarray:
    """Small deterministic moving-light proxy used only for owner evidence."""
    alb = np.clip(np.asarray(paint, np.float32), 0.0, 1.0)
    s = np.asarray(spec, np.float32)
    m, r, coat = s[..., 0] / 255.0, s[..., 1] / 255.0, s[..., 2] / 255.0
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    travel = (xx / max(w - 1, 1)) * 0.63 + (yy / max(h - 1, 1)) * 0.37
    band = np.clip(1.0 - np.abs(travel - float(phase)) * 2.1, 0.0, 1.0)
    highlight = np.power(band, 5.0 + (1.0 - r) * 150.0)
    reflectance = 0.10 + 0.82 * m + 0.48 * coat
    sky = np.asarray((0.82, 0.89, 1.0), np.float32)
    reflected = (0.62 * alb + 0.38 * sky) * (reflectance * highlight)[..., None]
    return np.clip(alb * (0.48 + 0.22 * (1.0 - r))[..., None] + reflected, 0.0, 1.0)


def _write_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.clip(np.asarray(image), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise OSError(f"could not write {path}")


def _write_gray(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), np.clip(image, 0, 255).astype(np.uint8), [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise OSError(f"could not write {path}")


def _label_tile(image: np.ndarray, label: str) -> np.ndarray:
    tile = np.clip(np.asarray(image), 0, 255).astype(np.uint8).copy()
    cv2.rectangle(tile, (0, 0), (tile.shape[1], 38), (5, 7, 12), -1)
    cv2.putText(tile, label, (12, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 235, 130), 2, cv2.LINE_AA)
    return tile


def render_evidence(result: PilotResult, output: Path, native_size: int = NATIVE) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    paint, spec = resize_result(result, native_size)
    paint_u8 = np.clip(paint * 255.0, 0, 255).astype(np.uint8)
    _write_rgb(output / "paint_2048.png", paint_u8)
    _write_gray(output / "M_2048.png", spec[..., 0])
    _write_gray(output / "R_2048.png", spec[..., 1])
    _write_gray(output / "Cc_2048.png", spec[..., 2])
    _write_rgb(output / "spec_packed_rgb_2048.png", spec)

    proxy_tiles = []
    for phase, label in ((0.25, "LIGHT A"), (0.52, "LIGHT B"), (0.78, "LIGHT C")):
        proxy = on_car_proxy(paint, spec, phase)
        proxy_u8 = np.clip(proxy * 255.0, 0, 255).astype(np.uint8)
        _write_rgb(output / f"on_car_proxy_{label[-1].lower()}_2048.png", proxy_u8)
        proxy_tiles.append(_label_tile(cv2.resize(proxy_u8, (512, 512), interpolation=cv2.INTER_AREA), label))
    _write_rgb(output / "light_sweep_contact.png", np.concatenate(proxy_tiles, axis=1))

    material_tiles = [
        _label_tile(cv2.resize(paint_u8, (512, 512), interpolation=cv2.INTER_AREA), "PAINT"),
        _label_tile(cv2.cvtColor(cv2.resize(spec[..., 0], (512, 512), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2RGB), "METAL"),
        _label_tile(cv2.cvtColor(cv2.resize(spec[..., 1], (512, 512), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2RGB), "ROUGH"),
        _label_tile(cv2.cvtColor(cv2.resize(spec[..., 2], (512, 512), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2RGB), "CLEARCOAT"),
    ]
    _write_rgb(output / "material_contact.png", np.concatenate(material_tiles, axis=1))

    mask_tiles = []
    for name, mask in result.masks.items():
        m = cv2.resize(unit(mask), (384, 384), interpolation=cv2.INTER_AREA)
        mask_tiles.append(_label_tile(cv2.cvtColor((m * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB), name.upper()))
    if mask_tiles:
        cols = 3
        blank = np.zeros_like(mask_tiles[0])
        mask_tiles.extend([blank] * ((-len(mask_tiles)) % cols))
        rows = [np.concatenate(mask_tiles[i:i + cols], axis=1) for i in range(0, len(mask_tiles), cols)]
        _write_rgb(output / "causal_masks_contact.png", np.concatenate(rows, axis=0))

    center = native_size // 2
    half = 512
    crop = paint_u8[center - half:center + half, center - half:center + half]
    _write_rgb(output / "detail_1to1_1024.png", crop)
    for size in (512, 128, 64):
        reduced = cv2.resize(paint_u8, (size, size), interpolation=cv2.INTER_AREA)
        _write_rgb(output / f"paint_{size}.png", reduced)

    manifest = {
        "schema": "spb-neon-oil-slick-pilot/1",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "finish_id": result.finish_id,
        "display_name": result.display_name,
        "carrier": result.carrier,
        "material_story": dict(result.material_story),
        "vetoes": list(result.vetoes),
        "native_size": [native_size, native_size],
        "builder_elapsed_seconds": round(float(result.elapsed_seconds), 6),
        "material_stats": material_stats(spec),
        "geometry_stats": geometry_stats(result.geometry),
        "causal_mask_coverage": mask_coverage(result.masks),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def timed_result(builder, *args, **kwargs) -> PilotResult:
    start = time.perf_counter()
    result = builder(*args, **kwargs)
    result.elapsed_seconds = time.perf_counter() - start
    return result

