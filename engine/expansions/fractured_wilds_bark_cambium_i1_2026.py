# -*- coding: utf-8 -*-
"""Isolated native-2048 Bark Camo cambial-history study.

One continuous off-canvas cambial timeline owns the finish. Unequal annual
fronts are deformed by four historical wound events; earlywood, latewood,
radial rays, callus bridges, resin seams, peeling lips, groove fractures and
lenticel cuts all descend from that chronology. There is no RNG, sampled
noise, FBM, cell placement, stamp field, or reused Wilds composer.

SPB-WILDS-BARK-I1, 2026-08-24. Owner target: native 2048 art, fine 8-32 px
features, dense causal anatomy, real A/B color flipping and separately built
M/R/Cc. Native verdict: KEEP-CANDIDATE. Cold 2048 repeats are 0.2897-0.3045 s;
A/B mean/p95 delta is 0.137278/0.515467; M/R/Cc std is
25.925/41.930/59.757 with correlations -0.041/-0.176/-0.245. This module stays
isolated and fail-closed: provisional is not owner acceptance or production.
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


ID = "fc_bark_camo"
WORK = 512
CALM_SPEC = np.asarray((6, 184, 8), np.uint8)


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
    d = _phase_distance(phase, center) / max(width, 1e-5)
    return np.exp(-(d * d) * 2.4).astype(np.float32)


def _palette(t: np.ndarray) -> np.ndarray:
    # Twelve authored cambial/structural colors; sliders can still recolor the
    # finish, so topology never depends on random chroma separation.
    colors = np.asarray([
        (0.025, 0.075, 0.095), (0.035, 0.22, 0.22),
        (0.05, 0.46, 0.39), (0.10, 0.70, 0.58),
        (0.42, 0.82, 0.53), (0.86, 0.78, 0.30),
        (0.98, 0.52, 0.20), (0.92, 0.24, 0.34),
        (0.72, 0.12, 0.52), (0.46, 0.13, 0.67),
        (0.18, 0.27, 0.74), (0.04, 0.52, 0.76),
    ], np.float32)
    u = (np.mod(t, 1.0) * len(colors)).astype(np.float32)
    i0 = np.floor(u).astype(np.int32) % len(colors)
    i1 = (i0 + 1) % len(colors)
    q = (u - np.floor(u))[..., None]
    return colors[i0] * (1.0 - q) + colors[i1] * q


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    q = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    lut = np.asarray(levels, np.uint8)
    return lut[q.astype(np.int32)]


def _build() -> Grammar:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK
    y = (yy + 0.5) / WORK

    # The trunk center is outside the canvas. This avoids a bullseye/specimen
    # while keeping every visible line part of one chronological growth event.
    cx, cy = -0.28, 0.53
    dx, dy = x - cx, y - cy
    radius = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx)

    # Four unequal historical wound events deform the chronology continuously.
    # Their influence is visible only through attached ring anatomy, never as
    # repeated dots, stamps, cells or large painted blobs.
    events = (
        (0.54, -0.46, 0.018, 0.14, 0.20, 1.7),
        (0.83, 0.21, -0.015, 0.18, 0.16, 2.3),
        (1.04, -0.09, 0.013, 0.12, 0.23, 2.9),
        (1.22, 0.34, -0.011, 0.16, 0.18, 3.7),
    )
    warped_r = radius.copy()
    event_field = np.zeros_like(radius)
    event_age = np.zeros_like(radius)
    for er, et, amp, sr, st, freq in events:
        ad = np.arctan2(np.sin(theta - et), np.cos(theta - et))
        influence = np.exp(-((radius - er) / sr) ** 2 - (ad / st) ** 2)
        warped_r += amp * influence * np.sin(freq * ad / st + 0.7 * radius)
        event_field = np.maximum(event_field, influence)
        event_age += influence * (0.5 + 0.5 * np.sin(7.0 * radius + freq * theta))

    # 86 fronts across the working field produce roughly 8-28 px anatomy at
    # native 2048. Incommensurate angular terms prevent periodic ring spacing.
    age = (86.0 * warped_r
           + 1.25 * np.sin(2.31 * theta + 4.7 * warped_r)
           + 0.53 * np.sin(5.17 * theta - 2.9 * warped_r)
           + 0.31 * np.sin(9.43 * theta + 7.1 * warped_r))
    phase = np.mod(age, 1.0)

    earlywood = _pulse(phase, 0.31, 0.23)
    latewood = _pulse(phase, 0.79, 0.075)
    groove = np.maximum(_pulse(phase, 0.00, 0.035),
                        _pulse(phase, 0.94, 0.026))

    # Radial rays remain broken, age-bound micro-bands instead of a global fan.
    ray_phase = np.mod(17.0 * theta / (2.0 * np.pi)
                       + 0.071 * age + 0.19 * np.sin(3.7 * theta), 1.0)
    ray_gate = 0.5 + 0.5 * np.sin(0.71 * age + 5.3 * theta)
    rays = _pulse(ray_phase, 0.08, 0.055) * np.clip((ray_gate - 0.43) * 2.2, 0, 1)

    # Wounds create attached callus, resin and peeling consequences. Each is
    # gated by a different chronological observable, so the mark families do
    # not collapse into one shared mask.
    callus = _f(event_field * _pulse(phase, 0.56, 0.11)
                * (0.35 + 0.65 * event_age))
    resin = _f(np.sqrt(event_field) * _pulse(phase, 0.15, 0.045)
               * (0.35 + 0.65 * np.maximum(0, np.sin(11.0 * theta + 0.19 * age))))
    peel_gate = np.clip((np.sin(7.7 * theta - 0.27 * age) - 0.28) * 1.35, 0, 1)
    peeling = _f(latewood * peel_gate * (0.30 + 0.70 * (1.0 - event_field)))

    # Lenticel cuts are short intersections of a ring-local phase and a broken
    # angular schedule; they remain subordinate to the cambial chronology.
    lenticel_phase = np.mod(29.0 * theta / (2.0 * np.pi)
                            - 0.043 * age + 0.17 * np.sin(2.2 * age), 1.0)
    lenticel = _pulse(lenticel_phase, 0.17, 0.032)
    lenticel *= _pulse(phase, 0.48, 0.095)
    lenticel *= np.clip((np.sin(0.43 * age + 8.1 * theta) - 0.15) * 1.5, 0, 1)
    lenticel = _f(lenticel)

    fracture_gate = np.clip((np.cos(13.0 * theta + 0.37 * age) - 0.52) * 1.7, 0, 1)
    groove_fracture = _f(groove * fracture_gate * (0.25 + 0.75 * event_field))

    chronology_t = np.mod(0.071 * age + 0.13 * np.sin(3.1 * theta)
                           + 0.08 * event_age, 1.0)
    tissue = _palette(chronology_t)
    brightness = 0.34 + 0.39 * earlywood + 0.18 * latewood
    paint = tissue * brightness[..., None]
    paint *= (1.0 - 0.68 * groove[..., None])
    paint += latewood[..., None] * np.asarray((0.08, 0.16, 0.22), np.float32)
    paint += rays[..., None] * np.asarray((0.24, 0.38, 0.31), np.float32)
    paint += callus[..., None] * np.asarray((0.62, 0.18, 0.32), np.float32)
    paint += resin[..., None] * np.asarray((0.82, 0.61, 0.20), np.float32)
    paint += peeling[..., None] * np.asarray((0.22, 0.10, 0.44), np.float32)
    paint += lenticel[..., None] * np.asarray((0.72, 0.54, 0.28), np.float32)
    paint -= groove_fracture[..., None] * np.asarray((0.18, 0.10, 0.08), np.float32)
    paint = _f(paint)

    # Fixed-luminance contact proves that chronology—not palette—is the read.
    neutral = _f(0.18 + 0.34 * earlywood + 0.22 * latewood
                 - 0.25 * groove + 0.23 * rays + 0.30 * callus
                 + 0.37 * resin + 0.18 * peeling + 0.25 * lenticel)
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    # Three material maps descend from different physical consequences.
    metal_field = _f(0.03 + 0.88 * resin + 0.72 * callus
                     + 0.55 * lenticel
                     + 0.50 * latewood * (1.0 - 0.65 * peeling)
                     + 0.33 * rays * (0.25 + 0.75 * event_field)
                     - 0.22 * groove)
    rough_field = _f(0.12 + 0.62 * groove + 0.54 * peeling
                     + 0.36 * groove_fracture + 0.19 * rays - 0.31 * resin)
    coat_field = _f(0.05 + 0.67 * earlywood + 0.52 * rays
                    + 0.41 * callus - 0.42 * groove - 0.25 * peeling)
    metal = _tier(metal_field, (8, 34, 62, 94, 126, 164, 207, 246))
    rough = _tier(rough_field, (14, 42, 73, 106, 141, 178, 216, 248))
    coat = _tier(coat_field, (6, 29, 58, 91, 129, 169, 211, 250))

    marks = (
        ("earlywood_laminae", earlywood, "A"),
        ("latewood_ridges", latewood, "B"),
        ("cambial_grooves", groove, "N"),
        ("broken_radial_rays", rays, "B"),
        ("wound_callus_bridges", callus, "A"),
        ("resin_seams", resin, "A"),
        ("peeling_lips", peeling, "B"),
        ("lenticel_cuts", lenticel, "B"),
        ("groove_fractures", groove_fracture, "N"),
    )
    if any(float(mask.std()) < 0.005 for _name, mask, _bank in marks):
        raise ValueError("Bark I1 has an absent causal mark")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="one continuous off-canvas cambial chronology deformed by four wound histories",
    )


@lru_cache(maxsize=1)
def _authored() -> Tuple[np.ndarray, np.ndarray]:
    grammar = _build()
    spec = np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)
    return grammar.paint, spec


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
    a = grammar.paint * (0.46 + 0.46 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.05, 0.44, 0.58), np.float32)
    a += owners["B"][..., None] * np.asarray((0.18, 0.04, 0.22), np.float32)
    b = grammar.paint * (0.45 + 0.47 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.55, 0.09, 0.38), np.float32)
    b += owners["A"][..., None] * np.asarray((0.28, 0.23, 0.04), np.float32)
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

    crop = paint[512:1536, 512:1536]
    crop_path = output / f"{ID}_detail_1to1_1024.png"
    _write_rgb(crop_path, crop)
    paths["detail_1to1"] = crop_path

    grammar = _build()
    owners = owner_unions(grammar)
    channels = [c.astype(np.float32).ravel() for c in cv2.split(spec)]
    corr = np.corrcoef(np.stack(channels))
    payload = {
        "schema": "spb-wilds-bark-cambium-i1/1",
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-ISOLATED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": grammar.topology,
        "determinism": "analytic chronology only; no RNG/noise/grain/stamps",
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
            label: {"min": int(channel.min()), "max": int(channel.max()),
                    "std": round(float(channel.std()), 6),
                    "unique_values": int(np.unique(channel).size)}
            for label, channel in zip(("M", "R", "Cc"), cv2.split(spec))
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
    # Fail-closed until the native evidence receives a visual KEEP verdict.
    return "fractured-wilds-bark-cambium-i1: 0 pending studies advanced"


if __name__ == "__main__":
    render_evidence(
        Path(__file__).resolve().parents[2]
        / "_wilds_fullres_progress_20260824" / "bark_cambium_i1"
    )


__all__ = [
    "ID", "Grammar", "clear_cache", "debug_angle_pair", "debug_grammar",
    "install_into_engine", "owner_unions", "render_evidence", "render_native",
]
