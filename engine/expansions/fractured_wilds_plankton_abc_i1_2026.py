# -*- coding: utf-8 -*-
"""Isolated native-2048 Magenta Plankton ABC-flow topology study.

SPB-WILDS-PLANKTON-I1 / SPB-105, 2026-08-24. One deterministic
Arnold-Beltrami-Childress flow supplies path curvature, orbit age, shear,
compression, vorticity sign, paired wakes, collision knots, flagellar curls,
feeding eddies and shed membranes. No RNG, sampled noise, FBM, grain, speck
scatter, placed organisms, stamps, cells or shared Wilds composer is used.

Native verdict is made at 2048. Reject before spec work if the result reads as
Amber lamellae, smoke/marble, generic fluid texture, line soup, reaction noise,
repeated organisms or macro vortex icons. Installer is fail-closed.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


ID = "fpe_magenta_plankton"
WORK = 512
TAU = float(np.pi * 2.0)


PALETTE_A = np.asarray([
    (0.012, 0.020, 0.050), (0.030, 0.060, 0.145),
    (0.055, 0.130, 0.300), (0.075, 0.260, 0.500),
    (0.075, 0.480, 0.620), (0.090, 0.690, 0.650),
    (0.240, 0.850, 0.560), (0.560, 0.920, 0.360),
    (0.850, 0.820, 0.220), (0.980, 0.560, 0.190),
    (0.970, 0.280, 0.300), (0.810, 0.120, 0.510),
    (0.540, 0.090, 0.680), (0.260, 0.100, 0.540),
], np.float32)
PALETTE_B = np.asarray([
    (0.018, 0.012, 0.045), (0.080, 0.025, 0.130),
    (0.210, 0.035, 0.240), (0.430, 0.055, 0.330),
    (0.700, 0.090, 0.360), (0.920, 0.180, 0.300),
    (0.990, 0.360, 0.190), (0.980, 0.610, 0.130),
    (0.760, 0.820, 0.150), (0.380, 0.790, 0.240),
    (0.100, 0.650, 0.380), (0.040, 0.470, 0.520),
    (0.055, 0.290, 0.560), (0.120, 0.120, 0.360),
], np.float32)


def _f(value: np.ndarray) -> np.ndarray:
    return np.clip(value, 0.0, 1.0).astype(np.float32)


def _spread(value: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(value, (3.0, 97.0))
    return _f((value - float(lo)) / max(float(hi - lo), 1e-6))


def _smooth(lo: float, hi: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _pd(phase: np.ndarray, center: float) -> np.ndarray:
    return np.abs((phase - center + 0.5) % 1.0 - 0.5).astype(np.float32)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    q = _pd(phase, center) / max(width, 1e-5)
    return np.exp(-2.5 * q * q).astype(np.float32)


def _palette(palette: np.ndarray, phase: np.ndarray) -> np.ndarray:
    u = np.mod(phase, 1.0) * len(palette)
    i0 = np.floor(u).astype(np.int32) % len(palette)
    i1 = (i0 + 1) % len(palette)
    q = (u - np.floor(u))[..., None]
    return palette[i0] * (1.0 - q) + palette[i1] * q


def _velocity(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # ABC coefficients are deliberately unequal so no axis or repeated icon
    # can dominate the projected ecology.
    a, b, c = 1.0, 0.77, 0.53
    vx = a * np.sin(z) + c * np.cos(y)
    vy = b * np.sin(x) + a * np.cos(z)
    vz = c * np.sin(y) + b * np.cos(x)
    mag = np.sqrt(vx * vx + vy * vy + vz * vz) + 1e-5
    return (vx / mag).astype(np.float32), (vy / mag).astype(np.float32), (vz / mag).astype(np.float32)


def _fields() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # 64 principal turns across the work frame -> 8 work px / 32 native px.
    x = np.mod(TAU * (64.0 * xx / WORK + 0.13 * np.sin(TAU * 3.0 * yy / WORK)), TAU)
    y = np.mod(TAU * (61.0 * yy / WORK - 0.11 * np.sin(TAU * 2.0 * xx / WORK)), TAU)
    z = np.mod(TAU * (37.0 * (xx + yy) / WORK + 0.17 * np.sin(TAU * (xx - yy) / WORK)), TAU)

    arc = np.zeros_like(x, np.float32)
    turn = np.zeros_like(x, np.float32)
    compression_history = np.zeros_like(x, np.float32)
    vx0, vy0, vz0 = _velocity(x, y, z)
    previous = (vx0, vy0, vz0)
    for step in range(7):
        vx, vy, vz = _velocity(x, y, z)
        dot = np.clip(vx * previous[0] + vy * previous[1] + vz * previous[2], -1.0, 1.0)
        turn += np.arccos(dot).astype(np.float32)
        arc += np.sqrt(vx * vx + vy * vy + vz * vz)
        compression_history += np.clip(-(vx + vy + vz) / 3.0, 0.0, 1.0)
        dt = 0.37 + 0.035 * step
        x = np.mod(x + dt * vx, TAU)
        y = np.mod(y + dt * vy, TAU)
        z = np.mod(z + dt * vz, TAU)
        previous = (vx, vy, vz)

    vx, vy, vz = _velocity(x, y, z)
    dx_x = cv2.Sobel(x, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    dx_y = cv2.Sobel(x, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    dy_x = cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    dy_y = cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    shear = np.sqrt((dx_x - dy_y) ** 2 + (dx_y + dy_x) ** 2)
    rotation = dy_x - dx_y
    determinant = dx_x * dy_y - dx_y * dy_x

    turn_n = _spread(turn)
    shear_n = _spread(shear)
    compression = _spread(compression_history + np.clip(-determinant, 0.0, None))
    rotation_n = _spread(np.abs(rotation))

    vortex_cores = _f(turn_n * (1.0 - 0.62 * shear_n))
    wake_phase = np.mod(0.19 * arc + 0.31 * x - 0.23 * y + 0.13 * z, 1.0)
    paired_wakes = _f((_pulse(wake_phase, 0.23, 0.060) + _pulse(wake_phase, 0.68, 0.060))
                      * (0.30 + 0.70 * vortex_cores))
    orbit_phase = np.mod(0.27 * arc + 0.17 * turn + 0.11 * z, 1.0)
    orbit_chains = _f(_pulse(orbit_phase, 0.47, 0.050) * (0.25 + 0.75 * rotation_n))
    shear_gaps = _f(_smooth(0.48, 0.82, shear_n) * (1.0 - 0.72 * paired_wakes))
    collision_knots = _f(compression * turn_n * _smooth(0.35, 0.72, rotation_n))
    curl_phase = np.mod(0.21 * x + 0.29 * y - 0.17 * z + 0.23 * rotation, 1.0)
    flagellar_curls = _f(_pulse(curl_phase, 0.74, 0.055)
                         * (0.25 + 0.75 * turn_n) * (1.0 - 0.45 * shear_gaps))
    feeding_eddies = _f(_smooth(0.42, 0.75, rotation_n)
                        * _smooth(0.28, 0.68, compression) * (0.35 + 0.65 * vortex_cores))
    shed_phase = np.mod(0.16 * arc - 0.22 * turn + 0.14 * (x + y), 1.0)
    shed_membranes = _f(_pulse(shed_phase, 0.15, 0.072)
                        * (0.25 + 0.75 * paired_wakes) * (1.0 - 0.55 * collision_knots))

    color_phase = np.mod(0.13 * x + 0.17 * y + 0.19 * z + 0.21 * turn_n
                         - 0.11 * compression + 0.09 * rotation_n, 1.0)
    return {
        "color_phase": color_phase, "vortex_cores": vortex_cores,
        "paired_wakes": paired_wakes, "orbit_chains": orbit_chains,
        "shear_gaps": shear_gaps, "collision_knots": collision_knots,
        "flagellar_curls": flagellar_curls, "feeding_eddies": feeding_eddies,
        "shed_membranes": shed_membranes,
    }


def _compose(fields: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    phase = np.mod(fields["color_phase"] + (0.18 if angle_b else 0.0)
                   + (0.12 if angle_b else -0.09) * fields["paired_wakes"], 1.0)
    paint = _palette(palette, phase)
    light = (0.24 + 0.24 * fields["vortex_cores"] + 0.22 * fields["paired_wakes"]
             + 0.19 * fields["collision_knots"] - 0.13 * fields["shear_gaps"])
    paint *= _f(light)[..., None]
    overlays = (
        ("vortex_cores", 4 if not angle_b else 10, 0.42),
        ("paired_wakes", 6 if not angle_b else 8, 0.58),
        ("orbit_chains", 8 if not angle_b else 5, 0.56),
        ("shear_gaps", 0, 0.72),
        ("collision_knots", 10 if not angle_b else 7, 0.70),
        ("flagellar_curls", 12 if not angle_b else 4, 0.61),
        ("feeding_eddies", 7 if not angle_b else 11, 0.50),
        ("shed_membranes", 3 if not angle_b else 9, 0.46),
    )
    for name, index, strength in overlays:
        mask = np.clip(fields[name] * strength, 0.0, 0.86)[..., None]
        paint = paint * (1.0 - mask) + palette[index] * mask
    return _f(paint)


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    u8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "plankton_abc_i1"
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
        for name, value in fields.items() if name != "color_phase"
    }
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-plankton-abc-i1/1",
        "status": "REJECT-HOMOGENEOUS-HIGH-FREQUENCY-LINE-SOUP-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "one deterministic projected ABC-flow ecology",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "determinism": "analytic ABC trajectories only; no RNG/noise/FBM/grain/specks/stamps",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
