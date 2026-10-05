# -*- coding: utf-8 -*-
"""Native-2048 Black Opal I2 paint-only Bragg-order study.

FROZEN REJECT (SPB-105 tick 2026-08-25): actual 2048 is homogeneous
multicolour static with faint vertical moire. Mathematical nonrepetition does
not create readable opal anatomy, and authored paint is over budget. No spec
maps were made.

SPB-105 / 2026-08-25 native rebuild tick. I1's checker/capsule
phase-separation paver is frozen. I2 replaces that carrier with a continuous
nine-order complex Bragg parameter coupled through deterministic lattice
dislocations. Area-valued coherence, strain, phase slip, potch and crazing
observables build the paint; no dots or lines are placed to fake uniqueness.
All optical wavelengths are 8-32 px native. Paint/A-B only until native eye.

No RNG, sampled noise, grain, cells, stamps, point scatter, shared composer or
legacy renderer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import cv2
import numpy as np


ID = "fmo_black_opal"
WORK = 1024
NATIVE = 2048

OPAL_A = np.asarray([
    (1, 2, 7), (4, 5, 22), (15, 7, 47), (42, 8, 75),
    (79, 11, 96), (122, 17, 107), (168, 28, 111), (208, 47, 105),
    (239, 75, 94), (255, 112, 81), (255, 158, 76), (248, 205, 91),
    (201, 231, 121), (121, 220, 151), (54, 168, 166),
], np.float32)
OPAL_B = np.asarray([
    (1, 5, 9), (1, 17, 28), (1, 39, 51), (2, 68, 70),
    (3, 101, 83), (6, 137, 91), (15, 172, 95), (34, 204, 96),
    (69, 229, 102), (118, 244, 119), (176, 248, 151), (229, 238, 190),
    (255, 204, 218), (240, 143, 225), (167, 82, 207),
], np.float32)

DISLOCATIONS = (
    (151.0, 178.0, 1.0, 73.0), (447.0, 125.0, -1.0, 91.0),
    (781.0, 209.0, 1.0, 67.0), (284.0, 421.0, -1.0, 83.0),
    (635.0, 394.0, 1.0, 109.0), (907.0, 518.0, -1.0, 79.0),
    (117.0, 704.0, 1.0, 97.0), (471.0, 697.0, -1.0, 71.0),
    (749.0, 811.0, 1.0, 101.0), (321.0, 913.0, -1.0, 61.0),
)


def _palette(values: np.ndarray, stops: np.ndarray) -> np.ndarray:
    scaled = np.mod(values, 1.0) * len(stops)
    lo = np.floor(scaled).astype(np.int16)
    mix = (scaled - lo)[..., None]
    return stops[lo] * (1.0 - mix) + stops[(lo + 1) % len(stops)] * mix


def _unit(values: np.ndarray) -> np.ndarray:
    lo = float(values.min())
    hi = float(values.max())
    return np.clip((values - lo) / max(hi - lo, 1e-7), 0.0, 1.0)


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, float], dict[str, np.ndarray]]:
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    u = x.copy()
    v = y.copy()
    # Smooth displacement from ten signed lattice dislocations. atan2 is used
    # only through sin/cos below, so there is no visible branch-cut seam.
    bend = np.zeros_like(x)
    twist_sin = np.zeros_like(x)
    twist_cos = np.zeros_like(x)
    for cx, cy, charge, radius in DISLOCATIONS:
        dx = x - cx
        dy = y - cy
        r2 = dx * dx + dy * dy + radius * radius
        weight = np.exp(-(dx * dx + dy * dy) / (2.0 * (radius * 2.15) ** 2))
        u += charge * 18.0 * dy / np.sqrt(r2) * weight
        v -= charge * 18.0 * dx / np.sqrt(r2) * weight
        angle = np.arctan2(dy, dx)
        bend += charge * np.sin(3.0 * angle) * weight
        twist_sin += np.sin(angle) * weight
        twist_cos += np.cos(angle) * weight

    # Nine incommensurate wave orders form a true complex coherence parameter.
    # Wavelengths are 4.5-15.5 work px = 9-31 native px.
    real = np.zeros_like(x)
    imag = np.zeros_like(x)
    real2 = np.zeros_like(x)
    imag2 = np.zeros_like(x)
    real3 = np.zeros_like(x)
    imag3 = np.zeros_like(x)
    for order in range(9):
        theta = order * 2.39996323 + 0.11 * np.sin(order * 1.7)
        wavelength = 4.5 + order * 1.37
        direction = u * np.cos(theta) + v * np.sin(theta)
        cross = -u * np.sin(theta) + v * np.cos(theta)
        phase = (
            2.0 * np.pi * direction / wavelength
            + 0.34 * np.sin(cross / (19.0 + order * 3.1) + order * 0.71)
            + (0.18 + 0.025 * order) * bend
        )
        real += np.cos(phase)
        imag += np.sin(phase)
        real2 += np.cos(2.0 * phase + order * 0.37)
        imag2 += np.sin(2.0 * phase + order * 0.37)
        real3 += np.cos(3.0 * phase - order * 0.23)
        imag3 += np.sin(3.0 * phase - order * 0.23)
    real /= 9.0
    imag /= 9.0
    real2 /= 9.0
    imag2 /= 9.0
    real3 /= 9.0
    imag3 /= 9.0

    coherence = np.sqrt(real * real + imag * imag)
    second = np.sqrt(real2 * real2 + imag2 * imag2)
    third = np.sqrt(real3 * real3 + imag3 * imag3)
    phase_angle = np.mod(np.arctan2(imag, real) / (2.0 * np.pi), 1.0)
    strain = _unit(np.abs(second - coherence) + 0.42 * np.abs(third - second))

    gy, gx = np.gradient(coherence)
    edge_energy = _unit(np.sqrt(gx * gx + gy * gy))
    lap = cv2.Laplacian(coherence, cv2.CV_32F, ksize=3)
    crazing = _unit(np.abs(lap))
    potch = np.clip((0.15 - coherence) / 0.15, 0.0, 1.0) * np.clip((strain - 0.33) / 0.67, 0.0, 1.0)
    color_bar = np.clip((second - 0.24) / 0.48, 0.0, 1.0) * np.clip((0.56 - coherence) / 0.56, 0.0, 1.0)
    dislocation = _unit(np.sqrt(twist_sin * twist_sin + twist_cos * twist_cos))

    chroma = np.mod(
        phase_angle + 0.29 * second - 0.21 * third + 0.12 * bend
        + (0.37 if angle_b else 0.0),
        1.0,
    )
    if angle_b:
        chroma = np.mod(chroma + 0.10 * np.sin(2.0 * np.pi * phase_angle + strain * 3.0), 1.0)
        stops = OPAL_B
    else:
        stops = OPAL_A
    image = _palette(chroma, stops)
    # Ordered faces, stressed boundaries, dark potch and narrow crazing are
    # area responses of different observables—not decorations on one glyph.
    light = (
        0.08 + 0.88 * np.power(coherence, 0.72)
        + 0.24 * color_bar + 0.18 * edge_energy
        - 0.42 * potch - 0.19 * crazing
    )
    image = np.clip(image * np.clip(light, 0.035, 1.18)[..., None], 0, 255).astype(np.uint8)

    masks = {
        "coherent_bragg": np.clip(coherence * 255.0, 0, 255).astype(np.uint8),
        "strain": np.clip(strain * 255.0, 0, 255).astype(np.uint8),
        "phase_slip": np.clip(edge_energy * 255.0, 0, 255).astype(np.uint8),
        "potch": np.clip(potch * 255.0, 0, 255).astype(np.uint8),
        "crazing": np.clip(crazing * 255.0, 0, 255).astype(np.uint8),
        "color_bar": np.clip(color_bar * 255.0, 0, 255).astype(np.uint8),
        "dislocation": np.clip(dislocation * 255.0, 0, 255).astype(np.uint8),
    }
    coverage = {
        "coherent_bragg": round(float(np.mean(coherence > 0.22)), 6),
        "strain": round(float(np.mean(strain > 0.48)), 6),
        "phase_slip": round(float(np.mean(edge_energy > 0.52)), 6),
        "potch": round(float(np.mean(potch > 0.28)), 6),
        "crazing": round(float(np.mean(crazing > 0.57)), 6),
        "color_bar": round(float(np.mean(color_bar > 0.24)), 6),
        "dislocation": round(float(np.mean(dislocation > 0.28)), 6),
    }
    return image, coverage, masks


def _write(path: Path, rgb: np.ndarray) -> None:
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                       [cv2.IMWRITE_PNG_COMPRESSION, 0]):
        raise OSError(f"could not write {path}")


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "black_opal_bragg_i2"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    a, coverage, _ = _paint(False)
    b, _, _ = _paint(True)
    native_a = cv2.resize(a, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(b, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4)
    elapsed = time.perf_counter() - started
    paint = output / f"{ID}_paint_2048.png"
    _write(paint, native_a)
    shutil.copyfile(paint, output / f"{ID}_angle_a_2048.png")
    _write(output / f"{ID}_angle_b_2048.png", native_b)
    _write(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    delta = np.mean(np.abs(native_a.astype(np.float32) - native_b.astype(np.float32)), axis=2) / 255.0
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-black-opal-bragg-i2/1",
        "status": "REJECT-HOMOGENEOUS-MULTICOLOR-STATIC-MOIRE-DO-NOT-WIRE",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [NATIVE, NATIVE],
        "topology": "continuous nine-order Bragg parameter with signed lattice dislocations",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "authored_native_seconds": round(float(elapsed), 6),
        "determinism": "analytic complex order parameter; no RNG/noise/grain/cells/stamps/points/shared composer",
        "spec_authored": False,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
