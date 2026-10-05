# -*- coding: utf-8 -*-
"""Isolated native-2048 Bornite Patina Newton-oxidation study.

An asymmetric six-root Newton flow supplies one continuous reacted crystal
sheet. Basin ancestry, convergence age, orbit turn and stalled residual create
attached oxidation anatomy. No RNG, noise, grain, cell placement, stamps,
Voronoi construction or reused Wilds composer is involved.

SPB-WILDS-BORNITE-I1 / SPB-105, 2026-08-24. Native verdict: REJECT. The actual
2048 paint is a textbook Newton-fractal poster: huge flat ancestry basins,
repeated bulb/eye clusters and macro boundaries dominate the canvas. Fine
orbit texture merely decorates those forbidden carriers. No root, iteration,
palette, scale or spec repair is authorized. Installer remains fail-closed.
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


ID = "fmo_bornite_patina"
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


def _spread(field: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(field, (3.0, 97.0))
    return _f((field - float(lo)) / max(float(hi - lo), 1e-5))


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    idx = np.clip(np.floor(_spread(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx.astype(np.int32)]


def _palette(t: np.ndarray) -> np.ndarray:
    colors = np.asarray([
        (0.025, 0.018, 0.035), (0.13, 0.035, 0.12),
        (0.36, 0.055, 0.35), (0.72, 0.10, 0.47),
        (0.96, 0.22, 0.35), (0.99, 0.48, 0.16),
        (0.90, 0.78, 0.16), (0.31, 0.76, 0.24),
        (0.035, 0.62, 0.43), (0.025, 0.51, 0.69),
        (0.08, 0.28, 0.74), (0.25, 0.11, 0.55),
    ], np.float32)
    u = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(u).astype(np.int32) % len(colors)
    i1 = (i0 + 1) % len(colors)
    q = (u - np.floor(u))[..., None]
    return colors[i0] * (1.0 - q) + colors[i1] * q


@lru_cache(maxsize=1)
def _build() -> Grammar:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK * 2.45 - 1.19
    y = (yy + 0.5) / WORK * 2.35 - 1.13
    z0 = (x + 0.17 * y + 0.035 * np.sin(5.1 * y)
          + 1j * (y - 0.11 * x + 0.031 * np.sin(4.7 * x))).astype(np.complex64)
    roots = np.asarray([
        -0.91 + 0.13j, -0.42 - 0.83j, 0.31 - 0.72j,
        0.94 - 0.09j, 0.47 + 0.79j, -0.37 + 0.91j,
    ], np.complex64)

    z = z0.copy()
    previous_step = np.ones_like(z, np.complex64)
    orbit_turn = np.zeros((WORK, WORK), np.float32)
    orbit_length = np.zeros((WORK, WORK), np.float32)
    hit_age = np.full((WORK, WORK), 23.0, np.float32)
    active = np.ones((WORK, WORK), bool)
    for iteration in range(23):
        diff = z[..., None] - roots[None, None, :]
        product = np.prod(diff, axis=2)
        derivative = product * np.sum(1.0 / (diff + np.complex64(1e-6 + 1e-6j)), axis=2)
        step = product / (derivative + np.complex64(1e-6 + 1e-6j))
        ratio = step / (previous_step + np.complex64(1e-6 + 1e-6j))
        orbit_turn += np.abs(np.angle(ratio)).astype(np.float32) * active
        orbit_length += np.minimum(np.abs(step), 1.0).astype(np.float32) * active
        z = np.where(active, z - step, z)
        nearest = np.min(np.abs(z[..., None] - roots[None, None, :]), axis=2)
        newly = active & (nearest < 1e-4)
        hit_age[newly] = iteration + np.clip(nearest[newly] * 1e4, 0, 0.999)
        active &= ~newly
        z = np.where(np.abs(z) < 5.0, z, z / np.maximum(np.abs(z), 1.0) * 4.5)
        previous_step = step

    distances = np.abs(z[..., None] - roots[None, None, :])
    label = np.argmin(distances, axis=2).astype(np.int16)
    residual = np.min(distances, axis=2).astype(np.float32)
    age = _f(hit_age / 23.0)
    turn = _spread(orbit_turn)
    travel = _spread(orbit_length)
    phase0 = np.mod(np.angle(z0) / (2.0 * np.pi) + 1.0, 1.0).astype(np.float32)

    boundary_u8 = np.zeros((WORK, WORK), np.uint8)
    boundary_u8[:, 1:] |= (label[:, 1:] != label[:, :-1]).astype(np.uint8) * 255
    boundary_u8[1:, :] |= (label[1:, :] != label[:-1, :]).astype(np.uint8) * 255
    boundary = cv2.GaussianBlur(boundary_u8.astype(np.float32) / 255.0, (0, 0), 0.75)
    boundary = _f(boundary * 1.35)
    boundary_halo = _f(cv2.GaussianBlur(boundary, (0, 0), 2.0) - 0.18 * boundary)

    ancestry_a = _f(np.isin(label, (0, 2, 5)).astype(np.float32)
                    * (0.34 + 0.66 * (1.0 - age)))
    ancestry_b = _f(np.isin(label, (1, 3, 4)).astype(np.float32)
                    * (0.32 + 0.68 * (1.0 - age)))
    oxidation_step = _f(_pulse(np.mod(8.3 * age + 0.37 * turn + 0.11 * phase0, 1.0),
                               0.17, 0.053) * (0.25 + 0.75 * travel))
    dendritic_feather = _f(boundary_halo
                           * _pulse(np.mod(17.0 * phase0 + 3.7 * turn, 1.0),
                                    0.61, 0.058))
    stalled_front = _f(_pulse(np.mod(6.7 * travel + 0.43 * turn, 1.0), 0.38, 0.061)
                       * age * (0.24 + 0.76 * (1.0 - residual)))
    sulphide_core = _f(_pulse(np.mod(4.1 * phase0 + 0.27 * travel, 1.0), 0.82, 0.078)
                       * (1.0 - boundary_halo) * (0.20 + 0.80 * (1.0 - age)))
    pinhole = _f(_pulse(np.mod(23.0 * phase0 + 11.0 * age + 0.23 * turn, 1.0),
                        0.44, 0.025) * boundary_halo * (0.3 + 0.7 * travel))
    cleavage_nick = _f(_pulse(np.mod(15.0 * (0.71 * x - 0.29 * y)
                                            + 0.31 * turn, 1.0), 0.09, 0.031)
                       * boundary * (0.20 + 0.80 * age))
    healed_seam = _f(cv2.GaussianBlur(boundary, (0, 0), 1.65)
                     * oxidation_step * (0.28 + 0.72 * (1.0 - stalled_front)))

    color_phase = np.mod(label / 6.0 + 0.21 * phase0 + 0.19 * age
                         + 0.07 * turn, 1.0)
    paint = _palette(color_phase)
    light = 0.36 + 0.28 * (1.0 - age) + 0.18 * travel - 0.12 * residual
    paint *= light[..., None]
    paint += oxidation_step[..., None] * np.asarray((0.48, 0.24, 0.04), np.float32)
    paint += dendritic_feather[..., None] * np.asarray((0.08, 0.43, 0.31), np.float32)
    paint += stalled_front[..., None] * np.asarray((0.42, 0.05, 0.30), np.float32)
    paint -= sulphide_core[..., None] * np.asarray((0.18, 0.14, 0.12), np.float32)
    paint += pinhole[..., None] * np.asarray((0.63, 0.52, 0.14), np.float32)
    paint += cleavage_nick[..., None] * np.asarray((0.64, 0.18, 0.07), np.float32)
    paint += healed_seam[..., None] * np.asarray((0.05, 0.27, 0.45), np.float32)
    paint = _f(paint)
    neutral = _f(np.dot(paint, np.asarray((0.2126, 0.7152, 0.0722), np.float32)))
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    metal_field = _f(0.04 + 0.48 * ancestry_a + 0.62 * oxidation_step
                     + 0.57 * pinhole + 0.42 * cleavage_nick - 0.31 * sulphide_core)
    rough_field = _f(0.08 + 0.64 * ancestry_b + 0.52 * dendritic_feather
                     + 0.61 * stalled_front + 0.39 * sulphide_core - 0.25 * healed_seam)
    coat_field = _f(0.05 + 0.66 * healed_seam + 0.43 * travel
                    + 0.47 * boundary_halo + 0.28 * ancestry_a
                    - 0.35 * cleavage_nick - 0.24 * stalled_front)
    metal = _tier(metal_field, (6, 30, 59, 93, 130, 169, 213, 250))
    rough = _tier(rough_field, (14, 40, 71, 105, 141, 180, 220, 249))
    coat = _tier(coat_field, (5, 28, 57, 90, 128, 169, 214, 252))

    marks = (
        ("oxidation_ancestry_A", ancestry_a, "A"),
        ("oxidation_ancestry_B", ancestry_b, "B"),
        ("convergence_age_steps", oxidation_step, "A"),
        ("basin_edge_feathers", dendritic_feather, "B"),
        ("stalled_reaction_fronts", stalled_front, "B"),
        ("sulphide_core_windows", sulphide_core, "N"),
        ("reaction_pinholes", pinhole, "A"),
        ("cleavage_nicks", cleavage_nick, "N"),
        ("healed_oxidation_seams", healed_seam, "B"),
        ("orbit_turn_relief", turn, "N"),
    )
    absent = [(name, float(mask.std())) for name, mask, _bank in marks
              if float(mask.std()) < 0.003]
    if absent:
        raise ValueError(f"Bornite I1 has absent causal marks: {absent}")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="one asymmetric six-root Newton oxidation sheet with causal orbit chronology",
    )


def clear_cache() -> None:
    _build.cache_clear()


def debug_grammar() -> Grammar:
    return _build()


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    owners = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        owners[bank] = np.maximum(owners[bank], mask)
    return owners


def debug_angle_pair() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    grammar = _build()
    owners = owner_unions(grammar)
    a = grammar.paint * (0.45 + 0.51 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.04, 0.50, 0.39), np.float32)
    a += owners["B"][..., None] * np.asarray((0.28, 0.07, 0.34), np.float32)
    b = grammar.paint * (0.44 + 0.52 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.59, 0.08, 0.36), np.float32)
    b += owners["A"][..., None] * np.asarray((0.36, 0.27, 0.03), np.float32)
    a, b = _f(a), _f(b)
    return a, b, np.abs(a - b).astype(np.float32)


def render_native(size: int = 2048) -> Tuple[np.ndarray, np.ndarray]:
    grammar = _build()
    paint = grammar.paint
    spec = np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)
    if size != WORK:
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
    for label_name, channel in zip(("M", "R", "Cc"), cv2.split(spec)):
        if not cv2.imwrite(str(paths[label_name]), channel):
            raise OSError(f"failed to write {paths[label_name]}")
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
        "schema": "spb-wilds-bornite-newton-i1/1",
        "status": "REJECT-MACRO-NEWTON-BASINS-BULB-CLUSTERS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": grammar.topology,
        "determinism": "analytic Newton flow only; no RNG/noise/grain/cells/stamps",
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
            label_name: {"min": int(c.min()), "max": int(c.max()),
                         "std": round(float(c.std()), 6),
                         "unique_values": int(np.unique(c).size)}
            for label_name, c in zip(("M", "R", "Cc"), cv2.split(spec))
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
    return "fractured-wilds-bornite-newton-i1: 0 pending studies advanced"


if __name__ == "__main__":
    render_evidence(
        Path(__file__).resolve().parents[2]
        / "_wilds_fullres_progress_20260824" / "bornite_newton_i1"
    )


__all__ = [
    "ID", "Grammar", "clear_cache", "debug_angle_pair", "debug_grammar",
    "install_into_engine", "owner_unions", "render_evidence", "render_native",
]
