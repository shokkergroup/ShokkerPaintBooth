# -*- coding: utf-8 -*-
"""Isolated native-2048 Ground Beetle abrasion-knurl topology study.

SPB-WILDS-GROUND-I1 / SPB-105, 2026-08-24. Two fine ridge systems are
selectively suppressed, rotated and terminated by one deterministic wear
watershed. Basin rollovers, drainage notches, grit sockets, burnished islands,
fracture burrs and healed laps are causal consequences of that interaction.

Paint/A-B review only. No RNG, sampled noise, grain, cells, stamps, regular
knurl grid, shared Wilds composer or material maps. Fail closed until native
2048 owner-eye review.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_ground_beetle"
WORK = 512
PI = float(np.pi)

PALETTE_A = np.asarray([
    (0.006, 0.010, 0.020), (0.012, 0.035, 0.065),
    (0.015, 0.090, 0.135), (0.015, 0.180, 0.205),
    (0.020, 0.310, 0.290), (0.055, 0.470, 0.315),
    (0.190, 0.600, 0.285), (0.470, 0.680, 0.210),
    (0.760, 0.650, 0.145), (0.930, 0.465, 0.120),
    (0.910, 0.245, 0.185), (0.680, 0.105, 0.340),
    (0.370, 0.055, 0.390), (0.115, 0.040, 0.250),
], np.float32)
PALETTE_B = np.asarray([
    (0.014, 0.008, 0.024), (0.065, 0.018, 0.105),
    (0.160, 0.030, 0.200), (0.330, 0.045, 0.275),
    (0.575, 0.070, 0.275), (0.800, 0.145, 0.205),
    (0.950, 0.310, 0.115), (0.980, 0.545, 0.075),
    (0.820, 0.755, 0.090), (0.450, 0.735, 0.155),
    (0.125, 0.610, 0.290), (0.025, 0.450, 0.430),
    (0.025, 0.260, 0.470), (0.060, 0.105, 0.310),
], np.float32)


def _f(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def _smooth(lo: float, hi: float, a: np.ndarray) -> np.ndarray:
    t = np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _pulse(phase: np.ndarray, center: float, width: float) -> np.ndarray:
    d = np.abs((phase - center + 0.5) % 1.0 - 0.5)
    return np.exp(-2.5 * (d / max(width, 1e-6)) ** 2).astype(np.float32)


def _palette(palette: np.ndarray, phase: np.ndarray) -> np.ndarray:
    u = np.mod(phase, 1.0) * len(palette)
    i0 = np.floor(u).astype(np.int32) % len(palette)
    q = (u - np.floor(u))[..., None]
    return palette[i0] * (1.0 - q) + palette[(i0 + 1) % len(palette)] * q


def _fields() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK * 2.0 - 1.0
    y = (yy + 0.5) / WORK * 2.0 - 1.0

    # Five overlapping analytic wear pressures form one connected watershed.
    # Their union is not used as flat colour; it rotates, suppresses and ends
    # the ridges that carry all visible structure.
    wells = []
    for cx, cy, ax, ay, tilt in (
        (-0.72, -0.50, 0.44, 0.27, 0.30),
        (-0.18, -0.18, 0.55, 0.23, -0.45),
        (0.45, -0.57, 0.38, 0.31, 0.62),
        (0.66, 0.24, 0.50, 0.25, -0.25),
        (-0.35, 0.62, 0.58, 0.28, 0.48),
    ):
        ct, st = np.cos(tilt), np.sin(tilt)
        dx, dy = x - cx, y - cy
        qx, qy = ct * dx + st * dy, -st * dx + ct * dy
        wells.append(np.exp(-2.2 * ((qx / ax) ** 2 + (qy / ay) ** 2)))
    pressure = _f(np.maximum.reduce(wells))
    px = cv2.Sobel(pressure, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    py = cv2.Sobel(pressure, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    rim = _f(np.sqrt(px * px + py * py) * 26.0)

    # Ridge direction turns continuously with the pressure gradient. A role
    # selector makes one family dominate locally so a uniform crosshatch never forms.
    phi = (0.32 * np.sin(1.6 * PI * x) - 0.28 * np.sin(1.8 * PI * y)
           + 0.44 * np.arctan2(py, px + 1e-6))
    c, s = np.cos(phi), np.sin(phi)
    u = c * x + s * y + 0.075 * np.sin(3.2 * PI * y + 1.4 * pressure)
    v = -s * x + c * y + 0.061 * np.sin(2.7 * PI * x - 1.8 * pressure)
    role = _smooth(0.38, 0.62, 0.5 + 0.5 * np.sin(
        1.35 * PI * x - 1.65 * PI * y + 2.1 * pressure))

    p1 = np.mod(48.0 * u + 2.2 * pressure + 0.7 * np.sin(5.0 * y), 1.0)
    p2 = np.mod(44.0 * v - 2.6 * pressure + 0.6 * np.sin(4.0 * x), 1.0)
    raw1 = _pulse(p1, 0.50, 0.155)
    raw2 = _pulse(p2, 0.50, 0.155)
    shoulder1 = _pulse(p1, 0.31, 0.100)
    shoulder2 = _pulse(p2, 0.69, 0.105)
    suppression = _f(1.0 - 0.78 * pressure)
    primary_ridges = _f(raw1 * (0.28 + 0.72 * (1.0 - role)) * suppression)
    secondary_ridges = _f(raw2 * (0.28 + 0.72 * role) * suppression)
    ridge_shoulders = _f((shoulder1 * (1.0 - role) + shoulder2 * role)
                         * suppression)

    # Rollover lips mark actual ridge termination at the wear rim.
    rollovers = _f(rim * (0.45 * raw1 + 0.55 * raw2))
    drainage_phase = np.mod(19.0 * np.arctan2(py, px + 1e-6)
                            + 8.0 * pressure + 3.0 * x, 1.0)
    drainage_notches = _f(rim * _pulse(drainage_phase, 0.57, 0.095))

    # Loaded crossings create sockets, while their low-pressure counterparts
    # become burnished islands. Neither exists away from both ridge families.
    crossing = _f(raw1 * raw2)
    grit_sockets = _f(crossing * _smooth(0.22, 0.58, pressure)
                      * _pulse(np.mod(13.0 * x + 17.0 * y, 1.0), 0.43, 0.14))
    burnished_islands = _f(crossing * (1.0 - pressure)
                           * _pulse(np.mod(11.0 * x - 15.0 * y, 1.0), 0.68, 0.16))

    # Rollover shear spawns short burrs and healed laps along the rim only.
    burr_phase = np.mod(24.0 * (x * px + y * py) + 7.0 * pressure, 1.0)
    fracture_burrs = _f(rollovers * _pulse(burr_phase, 0.22, 0.105))
    lap_phase = np.mod(15.0 * (x * py - y * px) - 5.0 * pressure, 1.0)
    healed_laps = _f(rim * _pulse(lap_phase, 0.76, 0.125)
                     * (1.0 - 0.72 * drainage_notches))

    # Scuff crescents stay inside the worn metal and follow its local gradient.
    scuff_phase = np.mod(21.0 * (x * c + y * s) + 4.0 * pressure, 1.0)
    scuff_crescents = _f(pressure * _pulse(scuff_phase, 0.36, 0.105)
                         * (0.35 + 0.65 * rim))
    color_phase = np.mod(0.17 * x - 0.13 * y + 0.27 * pressure
                         + 0.18 * p1 - 0.12 * p2 + 0.09 * role, 1.0)
    return {
        "color_phase": color_phase, "pressure": pressure,
        "primary_ridges": primary_ridges, "secondary_ridges": secondary_ridges,
        "ridge_shoulders": ridge_shoulders, "rollovers": rollovers,
        "drainage_notches": drainage_notches, "grit_sockets": grit_sockets,
        "burnished_islands": burnished_islands, "fracture_burrs": fracture_burrs,
        "healed_laps": healed_laps, "scuff_crescents": scuff_crescents,
    }


def _compose(f: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    phase = np.mod(f["color_phase"] + (0.19 if angle_b else 0.0)
                   + (0.12 if angle_b else -0.07) * f["primary_ridges"]
                   - (0.09 if angle_b else 0.05) * f["pressure"], 1.0)
    paint = _palette(palette, phase)
    light = _f(0.20 + 0.31 * f["primary_ridges"]
               + 0.27 * f["secondary_ridges"] + 0.21 * f["ridge_shoulders"]
               + 0.18 * f["burnished_islands"] - 0.18 * f["pressure"]
               - 0.22 * f["grit_sockets"])
    paint *= light[..., None]
    overlays = (
        ("rollovers", 7 if not angle_b else 10, 0.60),
        ("drainage_notches", 1 if not angle_b else 13, 0.78),
        ("grit_sockets", 12 if not angle_b else 2, 0.86),
        ("burnished_islands", 8 if not angle_b else 6, 0.66),
        ("fracture_burrs", 10 if not angle_b else 8, 0.82),
        ("healed_laps", 5 if not angle_b else 11, 0.67),
        ("scuff_crescents", 3 if not angle_b else 9, 0.55),
    )
    for name, index, strength in overlays:
        mask = np.clip(f[name] * strength, 0.0, 0.92)[..., None]
        paint = paint * (1.0 - mask) + palette[index] * mask
    return _f(paint)


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    u8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "ground_beetle_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    fields = _fields()
    a = _compose(fields, PALETTE_A, False)
    b = _compose(fields, PALETTE_B, True)
    native_a = cv2.resize(a, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    _write_rgb(output / f"{ID}_paint_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_a_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_b_2048.png", native_b)
    _write_rgb(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a - native_b), axis=2)
    coverage = {name: round(float(np.mean(value > 0.08)), 6)
                for name, value in fields.items() if name != "color_phase"}
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-ground-beetle-i1/1",
        "status": "REJECT-REPEATED-FINGERPRINT-BASINS-RAVEN-RELATIVE-DO-NOT-WIRE",
        "owner_accepted": False, "production_wired": False,
        "finish_id": ID, "native_size": [2048, 2048],
        "topology": "one abrasion-deformed knurl watershed",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic wear/ridge interaction; no RNG/noise/grain/cells/stamps",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
