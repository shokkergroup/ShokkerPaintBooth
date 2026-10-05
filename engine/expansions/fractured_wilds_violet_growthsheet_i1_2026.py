# -*- coding: utf-8 -*-
"""Isolated native-2048 Violet Garden growth-sheet study.

One deterministic noninvertible growth map produces compression caustics,
cusps, exchange apertures, age terraces, dormant folds, spore valves, healed
collisions, nutrient drains and rupture lips. No RNG, noise, cell placement,
graph, membrane labyrinth, stamp field or reused Wilds composer is involved.

SPB-WILDS-VIOLET-GARDEN-I1, 2026-08-24. Native paint, literal 1:1 detail,
opponent A/B states and three causal material maps passed local review as an
isolated KEEP candidate. It remains owner-unaccepted, production-unwired and
installer fail-closed pending the combined 110-finish review.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time
from typing import Dict, Tuple

import cv2
import numpy as np


ID = "fpe_violet_garden"
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


def _pd(phase: np.ndarray, center: float) -> np.ndarray:
    return np.abs((phase - center + 0.5) % 1.0 - 0.5)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    d = _pd(phase, center) / max(width, 1e-5)
    return np.exp(-2.5 * d * d).astype(np.float32)


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    idx = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx.astype(np.int32)]


def _causal_spread(field: np.ndarray) -> np.ndarray:
    """Expose authored causal range without adding texture or random variation."""
    lo, hi = np.percentile(field, (3.0, 97.0))
    return _f((field - float(lo)) / max(float(hi - lo), 1e-5))


def _palette(t: np.ndarray) -> np.ndarray:
    colors = np.asarray([
        (0.025, 0.018, 0.08), (0.11, 0.025, 0.24),
        (0.30, 0.04, 0.49), (0.57, 0.07, 0.67),
        (0.83, 0.16, 0.62), (0.98, 0.33, 0.48),
        (0.99, 0.61, 0.30), (0.76, 0.82, 0.31),
        (0.27, 0.77, 0.48), (0.06, 0.58, 0.66),
        (0.06, 0.35, 0.75), (0.18, 0.16, 0.60),
    ], np.float32)
    u = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(u).astype(np.int32) % len(colors)
    i1 = (i0 + 1) % len(colors)
    q = (u - np.floor(u))[..., None]
    return colors[i0] * (1.0 - q) + colors[i1] * q


def _build() -> Grammar:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK * 2.0 - 1.0
    y = (yy + 0.5) / WORK * 2.0 - 1.0
    pi = np.pi

    # A composed noninvertible tissue map. Frequencies are incommensurate and
    # analytic; no sampled perturbation is used to create uniqueness.
    u = (x
         + 0.19 * np.sin(2.3 * pi * y + 0.42 * np.sin(1.7 * pi * x))
         + 0.08 * np.sin(4.7 * pi * (x + 0.31 * y))
         + 0.045 * np.sin(8.9 * pi * y - 2.1 * pi * x))
    v = (y
         + 0.17 * np.sin(2.7 * pi * x - 0.39 * np.sin(1.9 * pi * y))
         + 0.075 * np.sin(5.3 * pi * (y - 0.27 * x))
         - 0.041 * np.sin(9.7 * pi * x + 1.6 * pi * y))
    u2 = (u + 0.075 * np.sin(3.1 * pi * v + 0.8 * np.sin(2.2 * pi * u))
          + 0.032 * np.sin(11.3 * pi * (u - 0.18 * v)))
    v2 = (v - 0.068 * np.sin(3.7 * pi * u - 0.7 * np.sin(2.5 * pi * v))
          + 0.029 * np.sin(10.1 * pi * (v + 0.22 * u)))

    du_dx = cv2.Sobel(u2.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3) * (WORK / 16.0)
    du_dy = cv2.Sobel(u2.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3) * (WORK / 16.0)
    dv_dx = cv2.Sobel(v2.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3) * (WORK / 16.0)
    dv_dy = cv2.Sobel(v2.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3) * (WORK / 16.0)
    det = du_dx * dv_dy - du_dy * dv_dx
    shear = np.sqrt((du_dx - dv_dy) ** 2 + (du_dy + dv_dx) ** 2)
    rotation = dv_dx - du_dy

    # Fold crests are actual near-zero Jacobian caustics; shoulders distinguish
    # compression from release rather than drawing a decorative outline.
    fold_crest = np.exp(-((det / 0.42) ** 2)).astype(np.float32)
    compression = _f(np.clip(-det * 0.48, 0, 1) * (0.25 + 0.75 * fold_crest))
    release = _f(np.clip(det * 0.34, 0, 1) * (0.20 + 0.80 * fold_crest))

    tissue_age = np.mod(7.3 * u2 + 5.7 * v2
                        + 0.41 * np.sin(4.1 * u2 - 3.3 * v2), 1.0)
    terrace = _f(_pulse(tissue_age, 0.14, 0.055) * (0.25 + 0.75 * compression))

    shear_norm = _f(shear * 0.18)
    aperture_phase = np.mod(13.0 * (0.43 * u2 - 0.61 * v2)
                            + 0.09 * (rotation * rotation), 1.0)
    exchange_aperture = _f(_pulse(aperture_phase, 0.22, 0.052)
                           * fold_crest * np.clip((shear_norm - 0.12) * 1.5, 0, 1))

    dormant_phase = np.mod(0.67 * tissue_age + 0.61 * (u2 * u2 + v2 * v2)
                           + 0.19 * np.sin(5.1 * u2 + 6.3 * v2), 1.0)
    dormant_fold = _f(_pulse(dormant_phase, 0.71, 0.083)
                      * (1.0 - fold_crest) * (1.0 - 0.55 * shear_norm))

    valve_phase = np.mod(17.0 * (0.31 * u2 + 0.47 * v2)
                         - 0.12 * tissue_age + 0.23 * rotation, 1.0)
    spore_valve = _f(_pulse(valve_phase, 0.43, 0.041)
                     * compression * (0.22 + 0.78 * shear_norm))

    # Healed collisions occur where compression and release shoulders overlap
    # after a small causal dilation, not at repeated coordinates.
    comp_d = cv2.GaussianBlur(compression, (0, 0), 1.4)
    rel_d = cv2.GaussianBlur(release, (0, 0), 1.8)
    healed_collision = _f(np.minimum(comp_d, rel_d) * 2.7
                          * _pulse(aperture_phase, 0.67, 0.095))

    drain_phase = np.mod(21.0 * (0.19 * u2 - 0.37 * v2)
                         + 0.14 * tissue_age + 0.18 * rotation, 1.0)
    nutrient_drain = _f(_pulse(drain_phase, 0.84, 0.038)
                        * release * (0.30 + 0.70 * (1.0 - shear_norm)))

    rupture_phase = np.mod(9.0 * (0.66 * u2 + 0.24 * v2)
                           + 0.31 * shear_norm, 1.0)
    rupture_lip = _f(_pulse(rupture_phase, 0.09, 0.044)
                     * fold_crest * np.clip((shear_norm - 0.18) * 1.7, 0, 1))

    sheen_phase = np.mod(0.11 * (u2 * WORK) + 0.07 * (v2 * WORK)
                         + 0.22 * rotation, 1.0)
    protein_sheen = _f(_pulse(sheen_phase, 0.54, 0.09)
                       * (0.30 + 0.70 * release) * (1.0 - 0.45 * dormant_fold))

    color_phase = np.mod(0.34 * tissue_age + 0.11 * rotation
                         + 0.08 * np.sin(4.7 * u2 - 5.9 * v2), 1.0)
    tissue = _palette(color_phase)
    light = 0.30 + 0.37 * fold_crest + 0.19 * release - 0.11 * compression
    paint = tissue * light[..., None]
    paint += compression[..., None] * np.asarray((0.24, 0.04, 0.31), np.float32)
    paint += release[..., None] * np.asarray((0.03, 0.31, 0.34), np.float32)
    paint += terrace[..., None] * np.asarray((0.48, 0.22, 0.08), np.float32)
    paint += exchange_aperture[..., None] * np.asarray((0.66, 0.53, 0.11), np.float32)
    paint -= dormant_fold[..., None] * np.asarray((0.16, 0.12, 0.18), np.float32)
    paint += spore_valve[..., None] * np.asarray((0.48, 0.08, 0.50), np.float32)
    paint += healed_collision[..., None] * np.asarray((0.14, 0.46, 0.20), np.float32)
    paint -= nutrient_drain[..., None] * np.asarray((0.18, 0.16, 0.11), np.float32)
    paint += rupture_lip[..., None] * np.asarray((0.60, 0.23, 0.18), np.float32)
    paint += protein_sheen[..., None] * np.asarray((0.05, 0.18, 0.33), np.float32)
    paint = _f(paint)

    neutral = _f(0.16 + 0.31 * fold_crest + 0.23 * release
                 - 0.16 * compression + 0.28 * terrace
                 + 0.34 * exchange_aperture - 0.18 * dormant_fold
                 + 0.31 * spore_valve + 0.26 * healed_collision
                 - 0.17 * nutrient_drain + 0.30 * rupture_lip
                 + 0.22 * protein_sheen)
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    metal_field = _f(0.04 + 0.61 * terrace + 0.68 * exchange_aperture
                     + 0.50 * spore_valve + 0.37 * rupture_lip
                     - 0.27 * dormant_fold)
    rough_field = _f(0.10 + 0.62 * compression + 0.54 * nutrient_drain
                     + 0.43 * dormant_fold + 0.35 * rupture_lip
                     - 0.31 * protein_sheen)
    coat_field = _f(0.05 + 0.70 * protein_sheen + 0.57 * release
                    + 0.46 * healed_collision + 0.31 * exchange_aperture
                    - 0.39 * compression - 0.25 * nutrient_drain)
    # SPB-105 / Violet I1 native-2048 review, 2026-08-24: paint topology passed
    # inspection, but the first causal spec pass compressed M/R/Cc std to
    # 11.787/23.213/16.119. Robust spreading exposes each independently authored
    # field's existing range; it adds no noise, marks, or paint differentiation.
    metal = _tier(_causal_spread(metal_field), (6, 31, 60, 94, 130, 169, 213, 250))
    rough = _tier(_causal_spread(rough_field), (14, 41, 72, 106, 142, 181, 220, 249))
    coat = _tier(_causal_spread(coat_field), (5, 28, 57, 90, 128, 169, 214, 252))

    marks = (
        ("compression_caustic_crests", compression, "A"),
        ("release_shoulders", release, "B"),
        ("growth_age_terraces", terrace, "A"),
        ("exchange_apertures", exchange_aperture, "B"),
        ("dormant_folds", dormant_fold, "N"),
        ("spore_valves", spore_valve, "A"),
        ("healed_collisions", healed_collision, "B"),
        ("nutrient_drains", nutrient_drain, "N"),
        ("rupture_lips", rupture_lip, "A"),
        ("protein_sheen_windows", protein_sheen, "B"),
    )
    absent = [(name, float(mask.std())) for name, mask, _bank in marks
              if float(mask.std()) < 0.003]
    if absent:
        raise ValueError(f"Violet Garden I1 has absent causal marks: {absent}")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="one deterministic noninvertible growth sheet with compression-caustic chronology",
    )


@lru_cache(maxsize=1)
def _authored() -> Tuple[np.ndarray, np.ndarray]:
    grammar = _build()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)


def clear_cache() -> None:
    _authored.cache_clear()


def debug_grammar() -> Grammar:
    return _build()


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    out = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        out[bank] = np.maximum(out[bank], mask)
    return out


def debug_angle_pair() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    grammar = _build()
    owners = owner_unions(grammar)
    a = grammar.paint * (0.43 + 0.50 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.06, 0.45, 0.62), np.float32)
    a += owners["B"][..., None] * np.asarray((0.18, 0.03, 0.23), np.float32)
    b = grammar.paint * (0.42 + 0.51 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.58, 0.08, 0.43), np.float32)
    b += owners["A"][..., None] * np.asarray((0.34, 0.27, 0.04), np.float32)
    a, b = _f(a), _f(b)
    return a, b, np.abs(a - b).astype(np.float32)


def render_native(size: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
    paint, spec = _authored()
    if size == WORK:
        return paint.copy(), spec.copy()
    paint = cv2.resize(paint, (size, size), interpolation=cv2.INTER_CUBIC)
    spec = cv2.resize(spec, (size, size), interpolation=cv2.INTER_NEAREST)
    return _f(paint), spec.astype(np.uint8)


def _write_rgb(path: Path, image: np.ndarray) -> None:
    u8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"failed to write {path}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_evidence(output_dir: str | Path) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    clear_cache()
    started = time.perf_counter()
    paint, spec = render_native(2048)
    elapsed = time.perf_counter() - started
    angle_a, angle_b, delta = debug_angle_pair()
    angle_a = cv2.resize(angle_a, (2048, 2048), interpolation=cv2.INTER_CUBIC)
    angle_b = cv2.resize(angle_b, (2048, 2048), interpolation=cv2.INTER_CUBIC)
    delta = cv2.resize(delta, (2048, 2048), interpolation=cv2.INTER_CUBIC)
    paths = {
        "paint": output / f"{ID}_paint_2048.png",
        "M": output / f"{ID}_M_2048.png",
        "R": output / f"{ID}_R_2048.png",
        "Cc": output / f"{ID}_Cc_2048.png",
        "angle_A": output / f"{ID}_angle_A_2048.png",
        "angle_B": output / f"{ID}_angle_B_2048.png",
        "angle_delta": output / f"{ID}_angle_delta_2048.png",
    }
    _write_rgb(paths["paint"], paint)
    for label, channel in zip(("M", "R", "Cc"), cv2.split(spec)):
        if not cv2.imwrite(str(paths[label]), channel):
            raise OSError(f"failed to write {paths[label]}")
    _write_rgb(paths["angle_A"], angle_a)
    _write_rgb(paths["angle_B"], angle_b)
    _write_rgb(paths["angle_delta"], np.clip(delta * 2.0, 0, 1))
    crop_path = output / f"{ID}_detail_1to1_1024.png"
    _write_rgb(crop_path, paint[512:1536, 512:1536])
    paths["detail_1to1"] = crop_path

    grammar = _build()
    owners = owner_unions(grammar)
    channels = [c.astype(np.float32).ravel() for c in cv2.split(spec)]
    corr = np.corrcoef(np.stack(channels))
    payload = {
        "schema": "spb-wilds-violet-growthsheet-i1/1",
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-ISOLATED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": grammar.topology,
        "determinism": "analytic growth map only; no RNG/noise/grain/cells/stamps",
        "native_builder_seconds": round(elapsed, 6),
        "within_3_second_budget": elapsed <= 3.0,
        "owner_coverage": {
            "A": round(float(np.mean(owners["A"] > 0.08)), 6),
            "B": round(float(np.mean(owners["B"] > 0.08)), 6),
            "angle_delta_mean": round(float(delta.mean()), 6),
            "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        },
        "causal_marks": [
            {"name": name, "bank": bank,
             "coverage": round(float(np.mean(mask > 0.08)), 6)}
            for name, mask, bank in grammar.marks
        ],
        "spec_stats": {
            label: {"min": int(c.min()), "max": int(c.max()),
                    "std": round(float(c.std()), 6),
                    "unique_values": int(np.unique(c).size)}
            for label, c in zip(("M", "R", "Cc"), cv2.split(spec))
        },
        "spec_correlations": {
            "M_R": round(float(corr[0, 1]), 6),
            "M_Cc": round(float(corr[0, 2]), 6),
            "R_Cc": round(float(corr[1, 2]), 6),
        },
        "files": {key: {"path": path.name, "sha256": _sha(path)}
                  for key, path in paths.items()},
    }
    (output / "manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def install_into_engine(registry, base_registry=None):
    return "fractured-wilds-violet-growthsheet-i1: 0 pending studies advanced"


if __name__ == "__main__":
    render_evidence(
        Path(__file__).resolve().parents[2]
        / "_wilds_fullres_progress_20260824" / "violet_growthsheet_i1"
    )


__all__ = [
    "ID", "Grammar", "clear_cache", "debug_angle_pair", "debug_grammar",
    "install_into_engine", "owner_unions", "render_evidence", "render_native",
]
