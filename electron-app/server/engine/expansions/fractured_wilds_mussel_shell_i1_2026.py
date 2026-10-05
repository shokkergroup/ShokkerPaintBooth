# -*- coding: utf-8 -*-
"""Isolated native-2048 Mussel Shell eroded-growth topology study.

SPB-WILDS-MUSSEL-I1 / SPB-105, 2026-08-24. One off-canvas shell-growth
surface supplies accelerating ribs, asymmetric ridge shoulders, growth checks,
bore tracks, chipped terraces, ligament scars, mineral seams, abrasion notches
and polished runs. All local primitives target 8-32 px at native 2048.

Paint/A-B review only. No RNG, sampled noise, grain, placed cells, stamps,
Voronoi geometry, shared Wilds composer or material maps are used. Fail closed
until the actual native canvas survives owner-eye review.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_mussel_shell"
WORK = 512
PI = float(np.pi)


PALETTE_A = np.asarray([
    (0.008, 0.014, 0.026), (0.012, 0.045, 0.080),
    (0.018, 0.105, 0.145), (0.020, 0.205, 0.205),
    (0.035, 0.330, 0.270), (0.090, 0.470, 0.300),
    (0.270, 0.570, 0.270), (0.560, 0.600, 0.210),
    (0.820, 0.540, 0.160), (0.920, 0.340, 0.185),
    (0.720, 0.160, 0.300), (0.430, 0.080, 0.350),
    (0.190, 0.060, 0.270), (0.045, 0.030, 0.120),
], np.float32)
PALETTE_B = np.asarray([
    (0.018, 0.010, 0.030), (0.075, 0.020, 0.105),
    (0.175, 0.030, 0.180), (0.345, 0.045, 0.235),
    (0.570, 0.075, 0.235), (0.790, 0.150, 0.180),
    (0.940, 0.320, 0.115), (0.970, 0.570, 0.090),
    (0.780, 0.730, 0.105), (0.410, 0.690, 0.175),
    (0.120, 0.555, 0.315), (0.030, 0.380, 0.445),
    (0.035, 0.205, 0.440), (0.070, 0.085, 0.255),
], np.float32)


def _f(value: np.ndarray) -> np.ndarray:
    return np.clip(value, 0.0, 1.0).astype(np.float32)


def _smooth(lo: float, hi: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _pd(phase: np.ndarray, center: float) -> np.ndarray:
    return np.abs((phase - center + 0.5) % 1.0 - 0.5).astype(np.float32)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    q = _pd(phase, center) / max(width, 1e-6)
    return np.exp(-2.5 * q * q).astype(np.float32)


def _palette(palette: np.ndarray, phase: np.ndarray) -> np.ndarray:
    u = np.mod(phase, 1.0) * len(palette)
    i0 = np.floor(u).astype(np.int32) % len(palette)
    i1 = (i0 + 1) % len(palette)
    q = (u - np.floor(u))[..., None]
    return palette[i0] * (1.0 - q) + palette[i1] * q


def _fields() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK * 2.0 - 1.0
    y = (yy + 0.5) / WORK * 2.0 - 1.0

    # The umbo is outside the canvas. Its eccentric metric and analytic shear
    # keep the surface from becoming a centred fan or a stack of perfect arcs.
    u = x + 1.31
    v = 1.24 * (y - 0.17)
    radius = np.sqrt(u * u + v * v)
    theta = np.arctan2(v, u)
    growth = radius
    growth += 0.050 * np.sin(3.1 * theta + 2.2 * radius)
    growth += 0.024 * np.sin(8.3 * theta - 3.7 * radius)
    growth += 0.013 * np.sin(15.0 * theta + 5.2 * radius)

    # Roughly 15-27 native pixels between ribs; the crown and shoulder marks
    # stay within the owner's 8-32 px local-feature doctrine.
    rib_phase = np.mod(38.0 * growth + 1.7 * np.sin(2.4 * theta)
                       + 0.55 * np.sin(9.0 * theta + 1.8 * radius), 1.0)
    rib_crowns = _pulse(rib_phase, 0.51, 0.155)
    leading_shoulders = _pulse(rib_phase, 0.34, 0.115)
    trailing_shoulders = _pulse(rib_phase, 0.70, 0.125)
    grooves = _pulse(rib_phase, 0.02, 0.175)

    # Older growth checks cross and locally flatten the fine ribs; they are a
    # physical interruption, not a second decorative stripe family.
    check_phase = np.mod((38.0 * growth) / 8.7 + 0.18 * np.sin(5.0 * theta), 1.0)
    growth_checks = _pulse(check_phase, 0.18, 0.075)
    check_lips = _pulse(check_phase, 0.30, 0.060)

    # Three differently curved borer histories cut through the rib chronology.
    center_1 = -0.49 + 0.105 * np.sin(4.7 * radius) + 0.026 * np.sin(15.0 * radius)
    center_2 = 0.16 + 0.085 * np.sin(5.4 * radius + 0.8)
    center_3 = 0.58 + 0.050 * np.sin(7.2 * radius - 0.5)
    d1 = np.abs(theta - center_1)
    d2 = np.abs(theta - center_2)
    d3 = np.abs(theta - center_3)
    bore_core = np.maximum.reduce((
        np.exp(-2.2 * (d1 / 0.016) ** 2),
        np.exp(-2.2 * (d2 / 0.012) ** 2),
        np.exp(-2.2 * (d3 / 0.010) ** 2),
    )).astype(np.float32)
    bore_lips = np.maximum.reduce((
        np.exp(-2.0 * ((d1 - 0.026) / 0.009) ** 2),
        np.exp(-2.0 * ((d2 - 0.021) / 0.007) ** 2),
        np.exp(-2.0 * ((d3 - 0.018) / 0.006) ** 2),
    )).astype(np.float32)
    bore_chambers = _f(bore_core * _pulse(np.mod(11.0 * radius, 1.0), 0.42, 0.13))

    # Erosion opens bounded terrace chips only where old checks and shoulders
    # already weakened the shell. This avoids random masks or loose flecks.
    weakness = (0.56 * np.sin(6.1 * theta + 4.2 * radius)
                + 0.44 * np.sin(11.3 * theta - 2.7 * radius))
    chip_gate = _smooth(0.43, 0.82, weakness)
    chipped_terraces = _f(chip_gate * (0.45 * growth_checks + 0.55 * trailing_shoulders))
    chip_lips = _f(chip_gate * check_lips * (1.0 - bore_core))

    # The hinge/ligament zone is an attached compressed interruption at the
    # off-canvas origin, filled with transverse 8-20 px slots rather than a flat patch.
    ligament_zone = np.exp(-2.2 * (((radius - 0.54) / 0.25) ** 2
                                   + ((theta + 0.02) / 0.23) ** 2)).astype(np.float32)
    ligament_slots = _f(ligament_zone * _pulse(
        np.mod(28.0 * radius + 2.1 * np.sin(5.0 * theta), 1.0), 0.56, 0.14))

    # Mineral seams follow fracture-prone shoulders but skip active bore cuts.
    seam_phase = np.mod(19.0 * radius - 6.0 * theta + 0.8 * np.sin(4.0 * radius), 1.0)
    mineral_seams = _f(_pulse(seam_phase, 0.21, 0.090)
                       * leading_shoulders * (1.0 - 0.85 * bore_core))

    # Fine abrasion notches are causally attached to exposed crowns.
    notch_phase = np.mod(23.0 * theta + 9.0 * radius, 1.0)
    abrasion_notches = _f(_pulse(notch_phase, 0.64, 0.105)
                          * rib_crowns * (0.30 + 0.70 * chip_gate))
    polished_runs = _f(rib_crowns * (1.0 - 0.72 * chip_gate)
                       * (1.0 - 0.82 * ligament_zone))

    color_phase = np.mod(0.31 * growth - 0.12 * theta
                         + 0.16 * rib_phase + 0.10 * check_phase
                         + 0.07 * np.sin(4.0 * theta + 3.0 * radius), 1.0)
    return {
        "color_phase": color_phase,
        "rib_crowns": rib_crowns,
        "leading_shoulders": leading_shoulders,
        "trailing_shoulders": trailing_shoulders,
        "grooves": grooves,
        "growth_checks": growth_checks,
        "check_lips": check_lips,
        "bore_core": bore_core,
        "bore_lips": bore_lips,
        "bore_chambers": bore_chambers,
        "chipped_terraces": chipped_terraces,
        "chip_lips": chip_lips,
        "ligament_slots": ligament_slots,
        "mineral_seams": mineral_seams,
        "abrasion_notches": abrasion_notches,
        "polished_runs": polished_runs,
    }


def _compose(fields: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    flip = (0.18 if angle_b else 0.0)
    phase = np.mod(fields["color_phase"] + flip
                   + (0.13 if angle_b else -0.08) * fields["polished_runs"]
                   - (0.10 if angle_b else 0.04) * fields["grooves"], 1.0)
    paint = _palette(palette, phase)
    light = _f(0.22 + 0.34 * fields["rib_crowns"]
               + 0.19 * fields["leading_shoulders"]
               + 0.15 * fields["growth_checks"]
               - 0.17 * fields["grooves"]
               - 0.25 * fields["bore_core"])
    paint *= light[..., None]

    overlays = (
        ("trailing_shoulders", 4 if not angle_b else 10, 0.38),
        ("growth_checks", 7 if not angle_b else 5, 0.36),
        ("bore_lips", 9 if not angle_b else 8, 0.76),
        ("bore_chambers", 12 if not angle_b else 2, 0.82),
        ("chipped_terraces", 1 if not angle_b else 13, 0.70),
        ("chip_lips", 8 if not angle_b else 6, 0.72),
        ("ligament_slots", 10 if not angle_b else 3, 0.66),
        ("mineral_seams", 6 if not angle_b else 11, 0.75),
        ("abrasion_notches", 13 if not angle_b else 7, 0.78),
        ("polished_runs", 5 if not angle_b else 9, 0.25),
    )
    for name, index, strength in overlays:
        mask = np.clip(fields[name] * strength, 0.0, 0.90)[..., None]
        paint = paint * (1.0 - mask) + palette[index] * mask
    return _f(paint)


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    u8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "mussel_shell_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    fields = _fields()
    angle_a = _compose(fields, PALETTE_A, False)
    angle_b = _compose(fields, PALETTE_B, True)
    native_a = cv2.resize(angle_a, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(angle_b, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    _write_rgb(output / f"{ID}_paint_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_a_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_b_2048.png", native_b)
    _write_rgb(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a - native_b), axis=2)
    coverage = {
        name: round(float(np.mean(value > 0.08)), 6)
        for name, value in fields.items() if name != "color_phase"
    }
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-mussel-shell-i1/1",
        "status": "REJECT-PARALLEL-RIB-RAILS-WITH-MACRO-TRACKS-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "one off-canvas eroded logarithmic shell-growth surface",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic shell chronology only; no RNG/noise/grain/cells/stamps",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
