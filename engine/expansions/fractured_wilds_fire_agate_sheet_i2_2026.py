# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Fire Agate I2 paint-only analytic chalcedony sheet.

SPB-105 / Wilds rebuild tick 53, 2026-08-25. Native 2048 paint first. Before:
X1 equal-dot/botryoid paver, frozen. After: pending paint-only native verdict.

One complex sheet supplies open chalcedony growth bands. Analytic poles and
saddles bend, compress and split the sheet without placing dots, colonies,
rings, cells, stamps, noise or a shared composer. No material work is allowed
until this carrier survives actual 2048 review.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_fire_agate"
AUTHORED = 1024

PALETTE_A = np.asarray([
    (7, 4, 13), (32, 6, 19), (72, 10, 19), (122, 20, 17),
    (180, 39, 15), (231, 73, 13), (255, 119, 19), (255, 174, 30),
    (248, 221, 57), (173, 224, 72), (72, 190, 91), (19, 139, 111),
    (13, 88, 121), (42, 48, 121), (91, 28, 108),
], np.float32) / 255.0

PALETTE_B = np.asarray([
    (5, 6, 19), (13, 25, 61), (12, 57, 103), (8, 103, 128),
    (12, 151, 129), (44, 194, 103), (113, 219, 73), (197, 226, 56),
    (252, 195, 49), (255, 139, 48), (244, 81, 67), (211, 44, 104),
    (158, 32, 132), (98, 30, 137), (47, 25, 99),
], np.float32) / 255.0

CALM_SPEC = np.asarray((4.0, 120.0, 16.0), np.float32)
M_TIERS = np.asarray((6, 27, 53, 83, 117, 156, 203, 250), np.uint8)
R_TIERS = np.asarray((14, 38, 69, 104, 141, 179, 217, 249), np.uint8)
CC_TIERS = np.asarray((5, 24, 49, 81, 118, 160, 208, 252), np.uint8)


def _palette(t: np.ndarray, palette: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(palette)
    i0 = np.floor(q).astype(np.int16) % len(palette)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return palette[i0] * (1.0 - f) + palette[(i0 + 1) % len(palette)] * f


def _tier(field: np.ndarray, values: np.ndarray) -> np.ndarray:
    cuts = np.quantile(np.asarray(field, np.float32), np.linspace(0.125, 0.875, 7))
    return values[np.digitize(field, cuts)].astype(np.uint8)


@lru_cache(maxsize=4)
def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    n = AUTHORED
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n * 2.0 - 1.0
    y = (yy + 0.5) / n * 2.0 - 1.0
    z = x.astype(np.complex64) + 1j * y.astype(np.complex64)

    w = z.copy()
    derivative = np.ones_like(z)
    poles = (
        (-1.18 + 0.18j, 0.095 + 0.052j),
        (0.26 - 0.39j, -0.082 + 0.071j),
        (1.21 + 0.48j, 0.118 - 0.038j),
        (-0.31 + 1.16j, -0.076 - 0.063j),
        (0.58 + 0.56j, 0.057 + 0.046j),
        (-0.67 - 1.12j, 0.069 - 0.051j),
    )
    for pole, weight in poles:
        dz = z - np.complex64(pole)
        safe = dz + np.complex64(0.004 + 0.003j)
        w += np.complex64(weight) / safe
        derivative -= np.complex64(weight) / (safe * safe)

    phase = (w.real + 0.075 * np.sin(w.imag * 5.1)
             + 0.034 * np.sin(w.real * 8.7 - w.imag * 3.2)).astype(np.float32)
    stretch = np.clip(np.abs(derivative).astype(np.float32), 0.35, 4.2)
    spacing = 0.025 + 0.006 * (0.5 + 0.5 * np.sin(w.imag.astype(np.float32) * 4.7))
    band = phase / spacing
    cycle = np.mod(band, 1.0)
    order = np.mod(np.floor(band), 15.0) / 15.0

    palette = PALETTE_B if angle_b else PALETTE_A
    travel = order + 0.17 * np.tanh(w.imag.astype(np.float32)) + 0.08 * np.log1p(stretch)
    if angle_b:
        travel = 1.0 - travel + 0.21 * np.clip(stretch - 1.0, 0.0, 1.0)
    rgb = _palette(travel, palette)

    ridge = 0.5 + 0.5 * np.cos(2.0 * np.pi * cycle)
    lip = np.exp(-((np.sin(2.0 * np.pi * cycle) / 0.24) ** 2)).astype(np.float32)
    compression = np.clip((stretch - 1.25) / 2.4, 0.0, 1.0)
    dry = np.clip((0.64 - stretch) / 0.29, 0.0, 1.0)
    band_order = np.floor(band).astype(np.int32)
    gate = 0.5 + 0.5 * np.sin(w.imag.astype(np.float32) * 11.3 + phase * 4.1)
    etch = 0.5 + 0.5 * np.sin(
        w.real.astype(np.float32) * 13.1 + w.imag.astype(np.float32) * 9.7
        + band_order.astype(np.float32) * 0.43
    )
    resin = 0.5 + 0.5 * np.cos(
        w.real.astype(np.float32) * 5.3 - w.imag.astype(np.float32) * 12.7
        + band_order.astype(np.float32) * 0.79
    )
    pause = lip * ((np.mod(band_order, 6) == 0).astype(np.float32))
    fire_window = lip * compression * np.clip((gate - 0.24) / 0.76, 0.0, 1.0)
    mineral_break = lip * dry * np.clip((0.38 - gate) / 0.38, 0.0, 1.0)
    healed = pause * np.clip((gate - 0.57) / 0.43, 0.0, 1.0)
    cusp = np.clip((stretch - 2.05) / 2.15, 0.0, 1.0) * (0.35 + 0.65 * ridge)
    relief = 0.34 + 0.55 * ridge + 0.27 * lip + 0.22 * compression - 0.36 * dry
    rgb *= np.clip(relief, 0.08, 1.30)[..., None]
    rgb += np.asarray((0.27, 0.12, 0.025) if not angle_b else (0.025, 0.16, 0.27), np.float32) * (lip * compression)[..., None]
    rgb += np.asarray((0.06, 0.20, 0.12) if not angle_b else (0.22, 0.05, 0.17), np.float32) * (lip * (1.0 - compression))[..., None]
    rgb *= (1.0 - 0.46 * dry * lip)[..., None]
    rgb *= (1.0 - 0.30 * pause)[..., None]
    rgb += np.asarray((0.30, 0.17, 0.025) if not angle_b else (0.035, 0.20, 0.30), np.float32) * fire_window[..., None]
    rgb += np.asarray((0.06, 0.23, 0.15) if not angle_b else (0.26, 0.05, 0.19), np.float32) * healed[..., None]
    rgb += np.asarray((0.20, 0.055, 0.23) if not angle_b else (0.055, 0.24, 0.18), np.float32) * cusp[..., None]
    rgb *= (1.0 - 0.52 * mineral_break)[..., None]

    paint = cv2.resize(np.clip(rgb, 0.0, 1.0).astype(np.float32),
                       (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    return paint, {"ridge": ridge, "lip": lip, "compression": compression,
                   "dry": dry, "stretch": stretch, "cycle": cycle,
                   "pause": pause, "fire_window": fire_window,
                   "mineral_break": mineral_break, "healed": healed,
                   "cusp": cusp, "gate": gate, "etch": etch, "resin": resin}


def _spec_maps(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    metal = (0.47 * fields["fire_window"] + 0.30 * fields["cusp"]
             + 0.19 * fields["lip"] * fields["gate"]
             + 0.13 * fields["compression"])
    rough = (0.46 * fields["mineral_break"] + 0.31 * fields["dry"] * fields["etch"]
             + 0.25 * fields["pause"] * (0.25 + 0.75 * fields["etch"])
             + 0.15 * fields["etch"] * (1.0 - fields["compression"])
             - 0.15 * fields["fire_window"])
    coat = (0.43 * fields["healed"] + 0.31 * fields["resin"] * (1.0 - fields["dry"])
            + 0.22 * fields["resin"] * (1.0 - fields["compression"])
            + 0.17 * fields["lip"] * fields["gate"] * (1.0 - fields["etch"])
            - 0.18 * fields["mineral_break"])
    return _tier(metal, M_TIERS), _tier(rough, R_TIERS), _tier(coat, CC_TIERS)


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, fields = _paint(False)
    spec = cv2.resize(np.stack(_spec_maps(fields), axis=2), (2048, 2048), interpolation=cv2.INTER_NEAREST)
    return paint, spec.astype(np.uint8)


def _entry():
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)
        if src.ndim != 3 or src.shape[2] < 3:
            src = np.zeros((h, w, 3), np.float32)
        else:
            src = src[:, :, :3]
            if src.size and float(src.max()) > 1.5:
                src = src / 255.0
            if src.shape[:2] != (h, w):
                src = cv2.resize(src, (w, h), interpolation=cv2.INTER_LINEAR)
        zone = np.asarray(mask, np.float32)
        if zone.ndim == 3:
            zone = zone[:, :, 0]
        if zone.shape != (h, w):
            zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
        authored, _ = _authored()
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_LANCZOS4)
        alpha = np.clip(zone * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(src * (1.0 - alpha) + authored * alpha, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        h, w = int(shape[0]), int(shape[1])
        zone = np.asarray(mask, np.float32)
        if zone.ndim == 3:
            zone = zone[:, :, 0]
        if zone.shape != (h, w):
            zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
        _, authored = _authored()
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(CALM_SPEC + (authored - CALM_SPEC) * max(0.0, float(sm)), 0.0, 255.0)
        rgb = active * zone[..., None] + CALM_SPEC * (1.0 - zone[..., None])
        out = np.empty((h, w, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    return spec_fn, paint_fn


def clear_cache() -> None:
    _paint.cache_clear()


def render_evidence(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache(); start = time.perf_counter(); a, fields = _paint(False); b, _ = _paint(True)
        spec = cv2.resize(np.stack(_spec_maps(fields), axis=2), (2048, 2048), interpolation=cv2.INTER_NEAREST)
        timings.append(time.perf_counter() - start)
        blob = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes() + spec.tobytes()
        digests.append(hashlib.sha256(blob).hexdigest()); last = a, b, spec
    a, b, spec = last; delta = np.abs(a - b)
    for suffix, image in (("paint", a), ("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2.0, 0.0, 1.0))):
        arr = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out_dir / f"{ID}_{suffix}_2048.png"), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    for index, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(out_dir / f"{ID}_{name}_2048.png"), spec[:, :, index])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {"id": ID, "status": "NATIVE-2048-PAINT-AND-MATERIAL-CONTACT-NOT-WIRED",
              "timings_s": timings, "deterministic": len(set(digests)) == 1,
              "digest": digests[0], "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, 0.95)),
              "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
              "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
              "spec_tiers": [int(len(np.unique(spec[:, :, i]))) for i in range(3)],
              "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])]}
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" / "fire_agate_sheet_i2"), indent=2))
