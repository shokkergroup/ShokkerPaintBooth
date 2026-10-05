# -*- coding: utf-8 -*-
"""Isolated native-2048 Abalone Drift screw-dislocation study.

One continuous nacre growth sheet carries four interacting screw dislocations.
Every tablet lip, mortar seam, offset ledge, crack-deflection bridge, boring
track, blister crest, repair wake and terminal end cap descends from that phase
history. There is no RNG, noise, grain, stamp placement or reused composer.

SPB-WILDS-ABALONE-I1, 2026-08-24. Native verdict: REJECT. The actual 2048 image
reads as a diagonal contour-stripe carrier and exposes horizontal atan2 branch-
cut seams. M/Cc correlation is also 0.771967 despite eight broad tiers. This is
frozen negative evidence: no coefficient, palette, density or spec repair is
authorized. The installer remains fail-closed.
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


ID = "fmo_abalone_drift"
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


def _dist(phase: np.ndarray, center: float) -> np.ndarray:
    return np.abs((phase - center + 0.5) % 1.0 - 0.5)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    d = _dist(phase, center) / max(width, 1e-5)
    return np.exp(-2.5 * d * d).astype(np.float32)


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    idx = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx.astype(np.int32)]


def _palette(t: np.ndarray) -> np.ndarray:
    colors = np.asarray([
        (0.018, 0.055, 0.10), (0.025, 0.22, 0.38),
        (0.02, 0.56, 0.68), (0.10, 0.78, 0.67),
        (0.51, 0.87, 0.52), (0.92, 0.82, 0.35),
        (1.00, 0.53, 0.29), (0.95, 0.24, 0.40),
        (0.75, 0.13, 0.63), (0.45, 0.16, 0.78),
        (0.20, 0.31, 0.88), (0.09, 0.57, 0.83),
        (0.34, 0.83, 0.80),
    ], np.float32)
    u = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(u).astype(np.int32) % len(colors)
    i1 = (i0 + 1) % len(colors)
    q = (u - np.floor(u))[..., None]
    return colors[i0] * (1.0 - q) + colors[i1] * q


def _build() -> Grammar:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK
    y = (yy + 0.5) / WORK

    defects = (
        (0.18, 0.24, 1.0, 0.17),
        (0.73, 0.20, -1.0, 0.14),
        (0.42, 0.69, 2.0, 0.20),
        (0.86, 0.76, -1.0, 0.16),
    )
    screw = np.zeros_like(x)
    strain = np.zeros_like(x)
    charge_field = np.zeros_like(x)
    nearest = np.full_like(x, 9.0)
    for px, py, charge, reach in defects:
        dx, dy = x - px, y - py
        rr = np.sqrt(dx * dx + dy * dy) + 1e-4
        ang = np.arctan2(dy, dx)
        screw += charge * ang / (2.0 * np.pi)
        local = np.exp(-(rr / reach) ** 2)
        strain = np.maximum(strain, local)
        charge_field += charge * local
        nearest = np.minimum(nearest, rr)

    # One global sheet: the diagonal advance and four signed dislocations share
    # the same phase. Seventy-three fronts keep visible anatomy in the native
    # 8-32 px range without forming separately placed rings or tablets.
    sheet = (73.0 * (0.74 * x + 0.41 * y)
             + 5.8 * screw
             + 0.71 * np.sin(5.3 * x - 3.7 * y + 1.8 * screw)
             + 0.39 * np.sin(8.9 * y + 2.1 * x - 2.7 * screw))
    phase = np.mod(sheet, 1.0)

    # Tangential chronology does not place objects; it breaks and rejoins the
    # continuous fronts according to local sheet age and defect strain.
    tangent = np.mod(19.0 * (0.31 * x - 0.83 * y)
                     + 0.067 * sheet + 0.73 * screw
                     + 0.22 * np.sin(6.2 * x + 5.1 * y), 1.0)
    long_age = np.mod(0.061 * sheet + 0.17 * screw, 1.0)

    growth_lip = _pulse(phase, 0.06, 0.045)
    organic_mortar = _pulse(phase, 0.48, 0.064)
    back_step = _pulse(phase, 0.82, 0.035)

    # End caps occur only where a chronological front loses continuity near a
    # strained defect. This avoids a full-card dash or brick matrix.
    cap_gate = _pulse(tangent, 0.19, 0.052)
    end_caps = _f(growth_lip * cap_gate * (0.18 + 0.82 * strain))

    bridge_gate = _pulse(tangent, 0.63, 0.046)
    bridges = _f(bridge_gate * (0.35 * growth_lip + 0.65 * back_step)
                 * np.clip((strain - 0.08) * 1.9, 0, 1))

    # Fine boring tracks are phase-attached interruptions in just two age
    # windows, not a scatter of independent holes.
    bore_age = np.maximum(_pulse(long_age, 0.23, 0.055),
                          _pulse(long_age, 0.71, 0.042))
    bore_cross = _pulse(tangent, 0.87, 0.035)
    boring_tracks = _f(bore_age * bore_cross * (0.30 + 0.70 * (1.0 - strain)))

    # Blister crests are small curvature consequences surrounding the screw
    # cores. The center is removed, so they cannot read as filled bubble dots.
    blister_core = np.exp(-((nearest - 0.027) / 0.011) ** 2)
    blister_break = np.clip((np.sin(0.23 * sheet + 4.7 * charge_field) - 0.05)
                            * 1.35, 0, 1)
    blister_crest = _f(blister_core * blister_break)

    # Repair wakes are oblique attached folds downstream of defects; a second
    # gate prevents a generic contour or ray field.
    wake_phase = np.mod(15.0 * (0.66 * x + 0.34 * y)
                        - 0.11 * sheet + 1.3 * charge_field, 1.0)
    wake_gate = _pulse(wake_phase, 0.35, 0.047)
    repair_wake = _f(wake_gate * np.sqrt(strain)
                     * np.clip((np.cos(5.7 * x - 7.1 * y) + 0.15) * 1.2, 0, 1))

    # Crack-deflection seams ride the mortar but are restricted to high strain
    # shoulders, where the nacre sheet visibly turns them.
    strain_edge = cv2.Laplacian(strain.astype(np.float32), cv2.CV_32F)
    strain_edge = _f(np.abs(strain_edge) * 180.0)
    crack_deflection = _f(organic_mortar * strain_edge
                          * (0.35 + 0.65 * _pulse(tangent, 0.42, 0.09)))

    color_phase = np.mod(0.079 * sheet + 0.21 * screw
                         + 0.08 * np.sin(5.4 * tangent * 2.0 * np.pi), 1.0)
    nacre = _palette(color_phase)
    light = 0.36 + 0.34 * growth_lip + 0.18 * back_step
    paint = nacre * light[..., None]
    paint *= (1.0 - 0.57 * organic_mortar[..., None])
    paint += growth_lip[..., None] * np.asarray((0.18, 0.28, 0.35), np.float32)
    paint += back_step[..., None] * np.asarray((0.10, 0.12, 0.25), np.float32)
    paint += end_caps[..., None] * np.asarray((0.55, 0.40, 0.12), np.float32)
    paint += bridges[..., None] * np.asarray((0.20, 0.62, 0.48), np.float32)
    paint -= boring_tracks[..., None] * np.asarray((0.25, 0.20, 0.12), np.float32)
    paint += blister_crest[..., None] * np.asarray((0.72, 0.40, 0.46), np.float32)
    paint += repair_wake[..., None] * np.asarray((0.20, 0.32, 0.68), np.float32)
    paint -= crack_deflection[..., None] * np.asarray((0.20, 0.16, 0.11), np.float32)
    paint = _f(paint)

    neutral = _f(0.17 + 0.38 * growth_lip + 0.20 * back_step
                 - 0.28 * organic_mortar + 0.30 * end_caps + 0.26 * bridges
                 - 0.18 * boring_tracks + 0.31 * blister_crest
                 + 0.24 * repair_wake - 0.17 * crack_deflection)
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    metal_field = _f(0.04 + 0.62 * growth_lip + 0.54 * back_step
                     + 0.68 * bridges + 0.41 * blister_crest
                     - 0.35 * organic_mortar - 0.18 * boring_tracks)
    rough_field = _f(0.09 + 0.65 * organic_mortar + 0.56 * boring_tracks
                     + 0.48 * crack_deflection + 0.31 * end_caps
                     - 0.38 * blister_crest)
    coat_field = _f(0.05 + 0.68 * growth_lip + 0.61 * blister_crest
                    + 0.47 * repair_wake + 0.29 * bridges
                    - 0.44 * organic_mortar - 0.26 * boring_tracks)
    metal = _tier(metal_field, (7, 32, 61, 94, 129, 168, 211, 249))
    rough = _tier(rough_field, (13, 40, 70, 104, 140, 179, 219, 250))
    coat = _tier(coat_field, (5, 28, 56, 89, 127, 168, 212, 252))

    marks = (
        ("aragonite_growth_lips", growth_lip, "A"),
        ("organic_mortar_seams", organic_mortar, "N"),
        ("offset_back_steps", back_step, "B"),
        ("terminal_tablet_caps", end_caps, "B"),
        ("crack_deflection_bridges", bridges, "A"),
        ("boring_tracks", boring_tracks, "N"),
        ("blister_crests", blister_crest, "A"),
        ("dislocation_repair_wakes", repair_wake, "B"),
        ("mortar_crack_deflections", crack_deflection, "N"),
    )
    if any(float(mask.std()) < 0.003 for _name, mask, _bank in marks):
        raise ValueError("Abalone I1 has an absent causal mark")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="one continuous nacre growth sheet with four interacting signed screw dislocations",
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
    a = grammar.paint * (0.43 + 0.49 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.04, 0.49, 0.62), np.float32)
    a += owners["B"][..., None] * np.asarray((0.17, 0.04, 0.24), np.float32)
    b = grammar.paint * (0.42 + 0.50 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.60, 0.08, 0.40), np.float32)
    b += owners["A"][..., None] * np.asarray((0.31, 0.25, 0.04), np.float32)
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
        "schema": "spb-wilds-abalone-helicoid-i1/1",
        "status": "REJECT-CONTOUR-STRIPES-BRANCH-CUTS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": grammar.topology,
        "determinism": "analytic phase chronology only; no RNG/noise/grain/stamps",
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
    return "fractured-wilds-abalone-helicoid-i1: 0 pending studies advanced"


if __name__ == "__main__":
    render_evidence(
        Path(__file__).resolve().parents[2]
        / "_wilds_fullres_progress_20260824" / "abalone_helicoid_i1"
    )


__all__ = [
    "ID", "Grammar", "clear_cache", "debug_angle_pair", "debug_grammar",
    "install_into_engine", "owner_unions", "render_evidence", "render_native",
]
