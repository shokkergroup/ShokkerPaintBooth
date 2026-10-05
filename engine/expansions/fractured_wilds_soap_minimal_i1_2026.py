# -*- coding: utf-8 -*-
"""Isolated native-2048 Soap Bubble differential-film topology study.

SPB-WILDS-SOAP-I1 / SPB-105, 2026-08-24. One deterministic thin-film height
surface supplies Gaussian/mean curvature, saddle patches, Plateau arcs, necks,
drainage streaks, rupture lips, coalescence seams, contact lenses and thickness
windows. No RNG, sampled noise, grain, placed cells, stamps, Voronoi geometry,
winner territories or shared Wilds composer is used.

Native verdict: KEEP-CANDIDATE-I1 / ISOLATED. The 2048 paint is a dense
anisotropic saddle/neck film, not a recolor of Violet's broad growth folds or
Amber's transported lamellae. Eight causal film events remain visible; A/B
mean/p95 delta is 0.088084/0.137650. M/R/Cc are independently authored with
std 60.734/57.692/64.437 and correlations -0.148/0.072/-0.276. Cold authored
native work is 0.41-0.46 s with exact combined hashes. Still not owner accepted,
production wired or runtime synchronized; installer remains fail-closed.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import time

import cv2
import numpy as np


ID = "fmo_soap_bubble"
WORK = 512
PI = float(np.pi)


PALETTE_A = np.asarray([
    (0.010, 0.020, 0.045), (0.025, 0.070, 0.145),
    (0.035, 0.170, 0.310), (0.030, 0.340, 0.500),
    (0.040, 0.570, 0.620), (0.120, 0.770, 0.600),
    (0.380, 0.900, 0.470), (0.740, 0.920, 0.260),
    (0.960, 0.710, 0.170), (0.990, 0.410, 0.200),
    (0.870, 0.170, 0.410), (0.610, 0.100, 0.630),
    (0.330, 0.100, 0.650), (0.120, 0.120, 0.410),
], np.float32)
PALETTE_B = np.asarray([
    (0.018, 0.012, 0.040), (0.095, 0.025, 0.155),
    (0.240, 0.040, 0.280), (0.480, 0.060, 0.350),
    (0.750, 0.100, 0.330), (0.930, 0.230, 0.230),
    (0.990, 0.480, 0.130), (0.900, 0.730, 0.120),
    (0.550, 0.820, 0.160), (0.190, 0.710, 0.300),
    (0.050, 0.540, 0.480), (0.040, 0.350, 0.570),
    (0.075, 0.180, 0.500), (0.160, 0.070, 0.320),
], np.float32)


def _f(value: np.ndarray) -> np.ndarray:
    return np.clip(value, 0.0, 1.0).astype(np.float32)


def _spread(value: np.ndarray, low: float = 3.0, high: float = 97.0) -> np.ndarray:
    lo, hi = np.percentile(value, (low, high))
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


def _tier(field: np.ndarray, levels: tuple[int, ...]) -> np.ndarray:
    index = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[index.astype(np.int32)]


def _fields() -> dict[str, np.ndarray]:
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    x = (xx + 0.5) / WORK * 2.0 - 1.0
    y = (yy + 0.5) / WORK * 2.0 - 1.0

    # Smooth coordinate transport bends the film modes without inserting a
    # visible carrier. Frequencies below produce 8-32px native primitives.
    u = x + 0.055 * np.sin(2.7 * PI * y + 0.4 * np.sin(1.9 * PI * x))
    u += 0.026 * np.sin(5.3 * PI * (x - 0.21 * y))
    v = y - 0.049 * np.sin(2.3 * PI * x - 0.5 * np.sin(1.7 * PI * y))
    v += 0.024 * np.sin(4.9 * PI * (y + 0.18 * x))

    height = (
        0.34 * np.sin(61.0 * PI * u) * np.cos(53.0 * PI * v)
        + 0.25 * np.sin(73.0 * PI * (0.77 * u + 0.36 * v) + 0.4 * np.sin(3.1 * PI * v))
        + 0.21 * np.cos(83.0 * PI * (0.29 * u - 0.91 * v) - 0.3 * np.sin(2.7 * PI * u))
        + 0.14 * np.sin(97.0 * PI * (0.58 * u + 0.63 * v))
    ).astype(np.float32)

    hx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    hy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    hxx = cv2.Sobel(hx, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    hyy = cv2.Sobel(hy, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    hxy = cv2.Sobel(hx, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    grad = np.sqrt(hx * hx + hy * hy)
    denom = np.maximum(1.0 + hx * hx + hy * hy, 1e-5)
    gaussian = (hxx * hyy - hxy * hxy) / (denom * denom)
    mean = ((1.0 + hy * hy) * hxx - 2.0 * hx * hy * hxy
            + (1.0 + hx * hx) * hyy) / (2.0 * np.power(denom, 1.5))

    neg_k = _spread(np.clip(-gaussian, 0.0, None))
    pos_k = _spread(np.clip(gaussian, 0.0, None))
    abs_h = _spread(np.abs(mean))
    grad_n = _spread(grad)

    saddle_patches = _f(neg_k * (0.35 + 0.65 * (1.0 - abs_h)))
    plateau_arcs = _f((1.0 - _smooth(0.06, 0.22, abs_h)) * _smooth(0.32, 0.68, grad_n))
    necks = _f(pos_k * abs_h * _smooth(0.42, 0.72, grad_n))

    flow_angle = np.arctan2(hy, hx)
    drain_phase = np.mod(0.095 * (xx * np.cos(flow_angle) + yy * np.sin(flow_angle))
                         + 0.17 * height, 1.0)
    drainage_streaks = _f(_pulse(drain_phase, 0.36, 0.065)
                          * _smooth(0.24, 0.66, grad_n) * (0.25 + 0.75 * saddle_patches))

    rupture_phase = np.mod(0.061 * xx - 0.083 * yy + 0.31 * mean, 1.0)
    rupture_lips = _f(_pulse(rupture_phase, 0.71, 0.052)
                      * _smooth(0.48, 0.78, abs_h) * (0.25 + 0.75 * grad_n))

    seam_phase = np.mod(0.047 * xx + 0.069 * yy + 0.24 * gaussian, 1.0)
    coalescence_seams = _f(_pulse(seam_phase, 0.18, 0.070)
                           * np.minimum(_smooth(0.20, 0.56, neg_k),
                                        _smooth(0.18, 0.54, pos_k + abs_h)))

    lens_phase = np.mod(0.055 * xx - 0.043 * yy + 0.19 * height + 0.11 * mean, 1.0)
    contact_lenses = _f(_pulse(lens_phase, 0.51, 0.057)
                        * _smooth(0.45, 0.76, pos_k) * (1.0 - 0.55 * rupture_lips))

    thickness_phase = np.mod(0.38 * height + 0.17 * mean + 0.13 * gaussian
                             + 0.026 * xx + 0.019 * yy, 1.0)
    thickness_windows = _f(_pulse(thickness_phase, 0.82, 0.090)
                           * (0.30 + 0.70 * saddle_patches))

    return {
        "height": height, "gaussian": gaussian, "mean": mean,
        "thickness_phase": thickness_phase,
        "saddle_patches": saddle_patches, "plateau_arcs": plateau_arcs,
        "necks": necks, "drainage_streaks": drainage_streaks,
        "rupture_lips": rupture_lips, "coalescence_seams": coalescence_seams,
        "contact_lenses": contact_lenses, "thickness_windows": thickness_windows,
    }


def _compose(fields: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    phase = fields["thickness_phase"]
    phase = np.mod(phase + (0.16 if angle_b else 0.0)
                   + (0.11 if angle_b else -0.08) * fields["saddle_patches"], 1.0)
    paint = _palette(palette, phase)
    light = (0.26 + 0.28 * fields["plateau_arcs"] + 0.24 * fields["necks"]
             + 0.17 * fields["thickness_windows"] - 0.12 * fields["saddle_patches"])
    paint *= _f(light)[..., None]

    overlays = (
        ("plateau_arcs", 5 if not angle_b else 9, 0.42),
        ("necks", 8 if not angle_b else 6, 0.66),
        ("drainage_streaks", 2 if not angle_b else 11, 0.58),
        ("rupture_lips", 10 if not angle_b else 7, 0.76),
        ("coalescence_seams", 12 if not angle_b else 4, 0.62),
        ("contact_lenses", 7 if not angle_b else 10, 0.55),
        ("thickness_windows", 4 if not angle_b else 12, 0.40),
    )
    for name, index, strength in overlays:
        mask = np.clip(fields[name] * strength, 0.0, 0.86)[..., None]
        paint = paint * (1.0 - mask) + palette[index] * mask
    return _f(paint)


def _write_rgb(path: Path, rgb: np.ndarray) -> None:
    u8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    if not cv2.imwrite(str(path), cv2.cvtColor(u8, cv2.COLOR_RGB2BGR)):
        raise OSError(f"could not write {path}")


def _write_gray(path: Path, gray: np.ndarray) -> None:
    if not cv2.imwrite(str(path), np.asarray(gray, np.uint8)):
        raise OSError(f"could not write {path}")


def _material(fields: dict[str, np.ndarray]) -> np.ndarray:
    # SPB-105 / SPB-WILDS-SOAP-I1 tick S-I1, 2026-08-24. Owner verdict:
    # "the biggest cardinal sin PERIOD ... LAZY" and no repeated spec maps.
    # Material state moved from absent (paint-only review) to causal eight-tier
    # M/R/Cc std 60.734/57.692/64.437, ranges 6-250/14-249/5-252 and
    # correlations -0.148/0.072/-0.276; native paint pixels were unchanged.
    metal_raw = _f(
        0.05 + 0.68 * fields["necks"] + 0.57 * fields["rupture_lips"]
        + 0.49 * fields["thickness_windows"] + 0.31 * fields["contact_lenses"]
        - 0.30 * fields["drainage_streaks"] - 0.18 * fields["saddle_patches"]
    )
    rough_raw = _f(
        0.08 + 0.66 * fields["saddle_patches"] + 0.61 * fields["drainage_streaks"]
        + 0.48 * fields["coalescence_seams"] + 0.35 * fields["rupture_lips"]
        - 0.37 * fields["plateau_arcs"] - 0.24 * fields["contact_lenses"]
    )
    coat_raw = _f(
        0.04 + 0.72 * fields["plateau_arcs"] + 0.63 * fields["contact_lenses"]
        + 0.54 * fields["thickness_windows"] + 0.38 * fields["coalescence_seams"]
        - 0.39 * fields["saddle_patches"] - 0.29 * fields["rupture_lips"]
    )
    metal = _tier(_spread(metal_raw), (6, 31, 60, 94, 130, 169, 213, 250))
    rough = _tier(_spread(rough_raw), (14, 41, 72, 106, 142, 181, 220, 249))
    coat = _tier(_spread(coat_raw), (5, 28, 57, 90, 128, 169, 214, 252))
    return np.stack((metal, rough, coat), axis=2)


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "soap_minimal_i1"
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    fields = _fields()
    angle_a = _compose(fields, PALETTE_A, False)
    angle_b = _compose(fields, PALETTE_B, True)
    spec = _material(fields)
    native_a = cv2.resize(angle_a, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    native_b = cv2.resize(angle_b, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    native_spec = cv2.resize(spec, (2048, 2048), interpolation=cv2.INTER_NEAREST)
    elapsed = time.perf_counter() - started
    _write_rgb(output / f"{ID}_paint_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_a_2048.png", native_a)
    _write_rgb(output / f"{ID}_angle_b_2048.png", native_b)
    _write_rgb(output / f"{ID}_detail_1to1_1024.png", native_a[512:1536, 512:1536])
    if not cv2.imwrite(str(output / f"{ID}_spec_2048.png"), native_spec):
        raise OSError("could not write native spec")
    _write_gray(output / f"{ID}_metal_2048.png", native_spec[:, :, 0])
    _write_gray(output / f"{ID}_roughness_2048.png", native_spec[:, :, 1])
    _write_gray(output / f"{ID}_clearcoat_2048.png", native_spec[:, :, 2])
    delta = np.mean(np.abs(native_a - native_b), axis=2)
    coverage = {
        name: round(float(np.mean(value > 0.08)), 6)
        for name, value in fields.items()
        if name not in {"height", "gaussian", "mean", "thickness_phase"}
    }
    channels = [native_spec[:, :, index].astype(np.float32).ravel() for index in range(3)]
    corr = np.corrcoef(np.stack(channels))
    combined_hash = hashlib.sha256(
        np.ascontiguousarray(native_a).tobytes()
        + np.ascontiguousarray(native_b).tobytes()
        + np.ascontiguousarray(native_spec).tobytes()
    ).hexdigest()
    (output / "manifest.json").write_text(json.dumps({
        "schema": "spb-wilds-soap-minimal-i1/1",
        "status": "KEEP-CANDIDATE-I1-NATIVE-2048-ISOLATED",
        "owner_accepted": False,
        "production_wired": False,
        "finish_id": ID,
        "native_size": [2048, 2048],
        "topology": "one deterministic differential thin-film surface",
        "causal_mark_coverage": coverage,
        "angle_delta_mean": round(float(delta.mean()), 6),
        "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
        "native_builder_seconds": round(float(elapsed), 6),
        "within_3_second_budget": elapsed <= 3.0,
        "spec_stats": {
            label: {
                "min": int(native_spec[:, :, index].min()),
                "max": int(native_spec[:, :, index].max()),
                "std": round(float(native_spec[:, :, index].std()), 6),
                "unique_values": int(np.unique(native_spec[:, :, index]).size),
            }
            for index, label in enumerate(("M", "R", "Cc"))
        },
        "spec_correlations_mr_mc_rc": [
            round(float(corr[0, 1]), 6), round(float(corr[0, 2]), 6),
            round(float(corr[1, 2]), 6),
        ],
        "combined_paint_angle_spec_sha256": combined_hash,
        "determinism": "analytic surface derivatives only; no RNG/noise/grain/cells/stamps",
        "spec_authored": True,
    }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
