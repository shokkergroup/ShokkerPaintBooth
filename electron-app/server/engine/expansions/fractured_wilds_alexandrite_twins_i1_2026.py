# -*- coding: utf-8 -*-
"""Isolated native-2048 Alexandrite hierarchical-twin topology study.

SPB-WILDS-ALEXANDRITE-I1 / SPB-105, 2026-08-24. Native verdict: REJECT. Six
competing crystal variants became broad polygonal winner territories filled
with uniform diagonal stripe wallpaper. Strong A/B color travel, branching,
wedge, dislocation, nick, trail and seam masks do not rescue the paver carrier.
No frequency, palette, score-field, boundary, accessory or spec repair is
authorized. Installer remains fail-closed.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


ID = "fmo_alexandrite_dusk"
WORK = 512
TAU = float(np.pi * 2.0)

PALETTE_A = np.asarray([
    (0.015, 0.020, 0.045), (0.035, 0.055, 0.125),
    (0.065, 0.110, 0.245), (0.110, 0.220, 0.440),
    (0.170, 0.390, 0.620), (0.140, 0.610, 0.690),
    (0.190, 0.790, 0.620), (0.410, 0.900, 0.450),
    (0.720, 0.870, 0.270), (0.930, 0.650, 0.180),
    (0.950, 0.310, 0.260), (0.820, 0.130, 0.440),
    (0.580, 0.100, 0.620), (0.310, 0.100, 0.520),
], np.float32)
PALETTE_B = np.asarray([
    (0.020, 0.025, 0.030), (0.070, 0.055, 0.095),
    (0.180, 0.070, 0.210), (0.390, 0.080, 0.300),
    (0.650, 0.100, 0.300), (0.870, 0.190, 0.210),
    (0.980, 0.390, 0.120), (0.940, 0.650, 0.120),
    (0.680, 0.820, 0.180), (0.310, 0.730, 0.260),
    (0.100, 0.580, 0.390), (0.080, 0.420, 0.520),
    (0.100, 0.240, 0.490), (0.180, 0.100, 0.360),
], np.float32)


def _smooth(lo: float, hi: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _phase_distance(value: np.ndarray, center: float) -> np.ndarray:
    return np.abs(((value - center + 0.5) % 1.0) - 0.5).astype(np.float32)


def _fields() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx - WORK * 0.5) / WORK
    y = (yy - WORK * 0.5) / WORK

    angles = np.asarray((-1.16, -0.71, -0.24, 0.27, 0.73, 1.12), np.float32)
    scores = []
    coordinates = []
    crosscoords = []
    for index, angle in enumerate(angles):
        ca, sa = float(np.cos(angle)), float(np.sin(angle))
        along = x * ca + y * sa
        cross = -x * sa + y * ca
        score = (
            np.sin(TAU * (0.74 * along + 0.31 * cross) + index * 0.83)
            + 0.66 * np.cos(TAU * (0.29 * along - 0.91 * cross) - index * 1.17)
            + 0.34 * np.sin(TAU * (1.23 * along + 0.18 * cross) + index * 0.41)
        )
        scores.append(score.astype(np.float32))
        coordinates.append(along)
        crosscoords.append(cross)
    stack = np.stack(scores)
    order = np.argsort(stack, axis=0)
    variant = order[-1].astype(np.int16)
    best = np.take_along_axis(stack, order[-1:,:,:], axis=0)[0]
    second = np.take_along_axis(stack, order[-2:-1,:,:], axis=0)[0]
    rivalry = np.clip(best - second, 0.0, 2.0)
    interface = 1.0 - _smooth(0.035, 0.19, rivalry)

    along = np.choose(variant, coordinates).astype(np.float32)
    cross = np.choose(variant, crosscoords).astype(np.float32)
    period = np.choose(variant, np.asarray((0.0105, 0.0130, 0.0155, 0.0118, 0.0172, 0.0141), np.float32))
    branch_gate = 0.5 + 0.5 * np.sin(TAU * (2.9 * cross - 0.43 * along) + variant * 0.73)
    branch = interface * (branch_gate > 0.48).astype(np.float32)
    local = along / period + 0.46 * np.sin(TAU * (1.65 * cross + 0.23 * along))
    local += branch * (0.42 + 0.28 * np.sin(TAU * 3.1 * cross))
    phase = np.mod(local, 1.0).astype(np.float32)

    lamina_a = 1.0 - _smooth(0.16, 0.29, _phase_distance(phase, 0.22))
    lamina_b = 1.0 - _smooth(0.14, 0.27, _phase_distance(phase, 0.70))
    midrib = 1.0 - _smooth(0.035, 0.095, _phase_distance(phase, 0.47))
    split_phase = np.mod(local * 0.5 + 1.7 * cross, 1.0)
    secondary = (1.0 - _smooth(0.055, 0.12, _phase_distance(split_phase, 0.5))) * (0.25 + 0.75 * interface)

    wedge_gate = 0.5 + 0.5 * np.sin(TAU * (4.3 * cross + 1.1 * along) + variant * 1.31)
    wedge_tips = interface * _smooth(0.76, 0.94, wedge_gate) * _smooth(0.28, 0.72, lamina_a + lamina_b)

    mismatch = np.abs(np.sin(TAU * (local - (along / period))))
    dislocation = interface * _smooth(0.52, 0.90, mismatch)

    trail_phase = np.mod(7.0 * cross + 1.3 * along + variant * 0.137, 1.0)
    inclusion_trails = (1.0 - _smooth(0.055, 0.12, _phase_distance(trail_phase, 0.5)))
    inclusion_trails *= _smooth(0.18, 0.58, interface + midrib * 0.42)

    nick_phase = np.mod(11.0 * cross - 2.7 * along + variant * 0.091, 1.0)
    cleavage_nicks = interface * (1.0 - _smooth(0.07, 0.16, _phase_distance(nick_phase, 0.5)))
    cleavage_nicks *= _smooth(0.42, 0.83, 0.5 + 0.5 * np.cos(TAU * 2.2 * along))

    heal_gate = 0.5 + 0.5 * np.sin(TAU * (1.7 * x - 2.3 * y) + variant * 0.57)
    healed_seams = interface * _smooth(0.62, 0.88, heal_gate) * (1.0 - cleavage_nicks)

    pause_phase = np.mod(2.1 * along + 3.7 * cross + variant * 0.11, 1.0)
    growth_pauses = 1.0 - _smooth(0.045, 0.105, _phase_distance(pause_phase, 0.5))
    growth_pauses *= 0.35 + 0.65 * (1.0 - interface)

    extinction_a = np.clip(0.56 * lamina_a + 0.42 * wedge_tips + 0.28 * healed_seams, 0.0, 1.0)
    extinction_b = np.clip(0.57 * lamina_b + 0.46 * dislocation + 0.26 * cleavage_nicks, 0.0, 1.0)

    return {
        "variant": variant, "phase": phase, "interface": interface,
        "lamina_a": lamina_a, "lamina_b": lamina_b, "midrib": midrib,
        "secondary_twins": secondary, "wedge_tips": wedge_tips,
        "dislocation_steps": dislocation, "inclusion_trails": inclusion_trails,
        "cleavage_nicks": cleavage_nicks, "healed_seams": healed_seams,
        "growth_pauses": growth_pauses, "extinction_a": extinction_a,
        "extinction_b": extinction_b,
    }


def _compose(fields: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    variant = fields["variant"]
    phase = fields["phase"]
    band_state = (phase > 0.50).astype(np.int16)
    zone_state = (fields["secondary_twins"] > 0.48).astype(np.int16)
    index = (variant * 2 + band_state * 3 + zone_state * 5) % len(palette)
    paint = palette[index].copy()

    owner = fields["extinction_b" if angle_b else "extinction_a"]
    opponent = fields["extinction_a" if angle_b else "extinction_b"]
    flash_index = (index + (7 if angle_b else 4)) % len(palette)
    paint = paint * (1.0 - owner[..., None] * 0.58) + palette[flash_index] * owner[..., None] * 0.58
    paint *= (0.72 + 0.28 * (1.0 - opponent))[..., None]

    overlays = (
        ("interface", 13, 0.62), ("midrib", 1, 0.42),
        ("wedge_tips", 8 if not angle_b else 6, 0.78),
        ("dislocation_steps", 10 if not angle_b else 11, 0.70),
        ("inclusion_trails", 5 if not angle_b else 9, 0.55),
        ("cleavage_nicks", 0, 0.82), ("healed_seams", 12 if not angle_b else 4, 0.64),
        ("growth_pauses", 2 if not angle_b else 3, 0.35),
    )
    for name, color_index, strength in overlays:
        mask = np.clip(fields[name] * strength, 0.0, 0.88)[..., None]
        paint = paint * (1.0 - mask) + palette[color_index] * mask
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    u8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "alexandrite_twins_i1"
    output.mkdir(parents=True, exist_ok=True)
    fields = _fields()
    angle_a = _compose(fields, PALETTE_A, False)
    angle_b = _compose(fields, PALETTE_B, True)
    native_a = cv2.resize(angle_a, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(angle_b, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    _write_rgb(output / f"{ID}_paint_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_a_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_b_2048.png", native_b)
    _write_rgb(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a - native_b), axis=2)
    coverage = {
        name: round(float(np.mean(value > 0.08)), 6)
        for name, value in fields.items()
        if name not in {"variant", "phase"}
    }
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-alexandrite-twins-i1/1",
        "status": "REJECT-STRIPED-WINNER-TERRITORY-PAVER-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "six-variant rank-two crystal-twin intergrowth",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "determinism": "analytic competing variants only; no RNG/noise/grain/cells/stamps",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
