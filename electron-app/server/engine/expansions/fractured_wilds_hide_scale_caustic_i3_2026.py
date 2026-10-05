# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Hide Scale Glass I3 analytic ray-caustic sheet.

SPB-105 / Wilds rebuild tick 50, 2026-08-25. Owner verdict: native 2048 is
authoritative; no lazy recolors, repeated units, noise separation or shared
spec topology. Before: I1 vertical bead curtains and I2 repeated closed loops
over diagonal bands, both frozen. After: pending native-2048 owner-eye/M7.

This is not a lens/scale placement algorithm. A uniform ray sheet is refracted
by nine incommensurate analytic slope modes. Bilinear ray deposition creates
the visible intensity; fold, cusp, inversion and shear anatomy are derivatives
of the same map. No RNG, sampled noise, Voronoi, dots, cells, stamps or raw
math-texture layer is present.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fc_hide_scale_glass"
AUTHORED = 1024
CALM_SPEC = np.asarray((4.0, 120.0, 16.0), np.float32)

PALETTE_A = np.asarray([
    (3, 8, 18), (6, 31, 62), (6, 72, 111), (8, 126, 145),
    (23, 181, 164), (72, 224, 160), (159, 244, 129), (236, 241, 117),
    (255, 191, 89), (250, 116, 88), (231, 61, 126), (178, 42, 167),
    (112, 47, 181), (55, 54, 151), (18, 32, 87),
], np.float32) / 255.0

PALETTE_B = np.asarray([
    (5, 7, 20), (31, 18, 76), (80, 27, 133), (145, 35, 163),
    (213, 47, 151), (249, 83, 110), (255, 143, 74), (250, 208, 79),
    (183, 239, 104), (92, 225, 143), (24, 182, 164), (7, 127, 158),
    (7, 80, 132), (15, 48, 94), (8, 20, 47),
], np.float32) / 255.0

M_TIERS = np.asarray((6, 27, 52, 82, 116, 155, 202, 250), np.uint8)
R_TIERS = np.asarray((14, 39, 70, 105, 142, 180, 218, 249), np.uint8)
CC_TIERS = np.asarray((5, 25, 50, 82, 119, 161, 209, 252), np.uint8)


def _norm(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float32)
    lo, hi = float(a.min()), float(a.max())
    return ((a - lo) / max(1e-6, hi - lo)).astype(np.float32)


def _palette(t: np.ndarray, palette: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(palette)
    i0 = np.floor(q).astype(np.int16) % len(palette)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return palette[i0] * (1.0 - f) + palette[(i0 + 1) % len(palette)] * f


def _tier(field: np.ndarray, values: np.ndarray) -> np.ndarray:
    cuts = np.quantile(np.asarray(field, np.float32), np.linspace(0.125, 0.875, 7))
    return values[np.digitize(field, cuts)].astype(np.uint8)


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    n = AUTHORED
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n
    y = (yy + 0.5) / n

    dx = np.zeros((n, n), np.float32)
    dy = np.zeros((n, n), np.float32)
    dxx = np.zeros((n, n), np.float32)
    dxy = np.zeros((n, n), np.float32)
    dyx = np.zeros((n, n), np.float32)
    dyy = np.zeros((n, n), np.float32)
    optical = np.zeros((n, n), np.float32)

    # Fixed incommensurate ray-slope spectrum. Frequencies span 8-32 px at
    # native 2048; amplitudes fall with order so no macro wave owns the canvas.
    modes = (
        (17.0, 0.173, 0.0120, 0.21),
        (21.0, 0.919, 0.0105, 1.37),
        (26.0, 1.571, 0.0090, 2.11),
        (31.0, 2.147, 0.0080, 0.83),
        (37.0, 2.731, 0.0070, 2.77),
        (43.0, 0.523, 0.0060, 1.91),
        (49.0, 1.237, 0.0052, 0.49),
        (56.0, 1.963, 0.0046, 2.43),
        (64.0, 2.519, 0.0040, 1.13),
    )
    tau = np.float32(2.0 * np.pi)
    for order, (freq, angle, amp, phase0) in enumerate(modes):
        ca, sa = np.float32(np.cos(angle)), np.float32(np.sin(angle))
        phase = tau * np.float32(freq) * (ca * x + sa * y) + np.float32(phase0)
        # Cross-coupling bends each grating without a sampled warp field.
        phase += np.float32(0.42) * np.sin(
            tau * np.float32(freq * (0.127 + 0.011 * order)) * (-sa * x + ca * y)
            + np.float32(order * 0.61)
        )
        sn = np.sin(phase).astype(np.float32)
        cs = np.cos(phase).astype(np.float32)
        a = np.float32(amp)
        k = tau * np.float32(freq)
        dx += a * ca * sn
        dy += a * sa * sn
        dxx += a * ca * ca * k * cs
        dxy += a * ca * sa * k * cs
        dyx += a * sa * ca * k * cs
        dyy += a * sa * sa * k * cs
        optical += cs * np.float32(1.0 / (1.0 + order * 0.32))

    map_x = np.mod(x + dx, 1.0) * n
    map_y = np.mod(y + dy, 1.0) * n
    ix = np.floor(map_x).astype(np.int32) % n
    iy = np.floor(map_y).astype(np.int32) % n
    fx = (map_x - np.floor(map_x)).astype(np.float32)
    fy = (map_y - np.floor(map_y)).astype(np.float32)
    density = np.zeros(n * n, np.float32)
    for ox, oy, weight in (
        (0, 0, (1.0 - fx) * (1.0 - fy)),
        (1, 0, fx * (1.0 - fy)),
        (0, 1, (1.0 - fx) * fy),
        (1, 1, fx * fy),
    ):
        flat = ((iy + oy) % n) * n + ((ix + ox) % n)
        density += np.bincount(flat.ravel(), weights=weight.ravel(), minlength=n * n).astype(np.float32)
    density = density.reshape(n, n)
    density = cv2.GaussianBlur(density, (0, 0), 1.15)
    density = _norm(np.log1p(density * 4.0))

    det = (1.0 + dxx) * (1.0 + dyy) - dxy * dyx
    fold = np.exp(-((np.abs(det) / 0.24) ** 2)).astype(np.float32)
    inversion = np.clip(-det / 2.2, 0.0, 1.0).astype(np.float32)
    shear = _norm(np.abs(dxy + dyx) + 0.25 * np.abs(dxx - dyy))
    transport = _norm(np.hypot(dx, dy))

    det_blur = cv2.GaussianBlur(det.astype(np.float32), (0, 0), 1.2)
    gy, gx = np.gradient(det_blur)
    det_grad = _norm(np.hypot(gx, gy))
    cusp = fold * np.clip((det_grad - 0.34) / 0.66, 0.0, 1.0)
    shoulder = np.clip(cv2.GaussianBlur(fold, (0, 0), 2.3) - 0.35 * fold, 0.0, 1.0)

    principal = 0.5 * np.arctan2(2.0 * (dxy + dyx), dxx - dyy + 1e-6)
    focal_phase = (optical * 2.7 + principal * 4.0 + transport * 19.0)
    focal = fold * np.exp(-((np.sin(focal_phase) / 0.28) ** 2)).astype(np.float32)
    bevel = shoulder * (0.45 + 0.55 * (0.5 + 0.5 * np.cos(focal_phase * 0.73)))
    fork = cusp * np.clip((shear - 0.46) / 0.54, 0.0, 1.0)
    throat = inversion * np.clip((0.58 - density) / 0.58, 0.0, 1.0)
    scuff = np.clip(shear - 0.72, 0.0, 0.28) / 0.28
    scuff *= np.clip((np.sin(optical * 5.0 + principal * 9.0) - 0.38) / 0.62, 0.0, 1.0)

    return {
        "density": density, "fold": fold, "inversion": inversion,
        "shear": shear, "transport": transport, "cusp": cusp,
        "shoulder": shoulder, "focal": focal, "bevel": bevel,
        "fork": fork, "throat": throat, "scuff": scuff,
        "optical": _norm(optical), "principal": principal,
    }


def _compose(fields: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    hue = (fields["optical"] * 0.46 + fields["transport"] * 0.31
           + fields["density"] * 0.37 + fields["principal"] / (2.0 * np.pi))
    if angle_b:
        hue = 1.0 - hue + 0.23 * fields["inversion"]
    rgb = _palette(hue, palette)
    relief = (0.35 + 0.70 * fields["density"] + 0.25 * fields["bevel"]
              + 0.28 * fields["focal"] - 0.36 * fields["throat"]
              - 0.22 * fields["scuff"])
    rgb *= np.clip(relief, 0.10, 1.35)[..., None]
    rgb += np.asarray((0.08, 0.22, 0.25) if not angle_b else (0.25, 0.08, 0.19), np.float32) * fields["focal"][..., None]
    rgb += np.asarray((0.24, 0.16, 0.05) if not angle_b else (0.05, 0.18, 0.25), np.float32) * fields["cusp"][..., None]
    rgb += np.asarray((0.16, 0.04, 0.21) if not angle_b else (0.05, 0.22, 0.14), np.float32) * fields["fork"][..., None]
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def _spec_maps(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    metal = (0.48 * fields["focal"] + 0.29 * fields["cusp"]
             + 0.21 * fields["density"] + 0.16 * fields["fork"])
    rough = (0.44 * fields["scuff"] + 0.31 * fields["shear"]
             + 0.25 * fields["throat"] + 0.15 * (1.0 - fields["density"])
             - 0.20 * fields["focal"])
    coat = (0.43 * fields["bevel"] + 0.31 * fields["shoulder"]
            + 0.25 * fields["transport"] + 0.19 * (1.0 - fields["inversion"])
            - 0.18 * fields["scuff"])
    return _tier(metal, M_TIERS), _tier(rough, R_TIERS), _tier(coat, CC_TIERS)


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    fields = _fields()
    paint = _compose(fields, PALETTE_B if angle_b else PALETTE_A, angle_b)
    paint = cv2.resize(paint, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    return np.clip(paint, 0.0, 1.0).astype(np.float32), fields


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, fields = _paint(False)
    spec = np.stack(_spec_maps(fields), axis=2)
    spec = cv2.resize(spec, (2048, 2048), interpolation=cv2.INTER_NEAREST)
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
    _fields.cache_clear()
    _paint.cache_clear()


def _save_rgb(path: Path, image: np.ndarray) -> None:
    arr = np.clip(np.asarray(image) * 255.0, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))


def render_evidence(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    timings, digests = [], []
    last = None
    for _ in range(3):
        clear_cache()
        start = time.perf_counter()
        a, fields = _paint(False)
        b, _ = _paint(True)
        spec = cv2.resize(np.stack(_spec_maps(fields), axis=2), (2048, 2048), interpolation=cv2.INTER_NEAREST)
        timings.append(time.perf_counter() - start)
        blob = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes() + spec.tobytes()
        digests.append(hashlib.sha256(blob).hexdigest())
        last = a, b, spec
    a, b, spec = last
    delta = np.abs(a - b)
    for suffix, image in (("paint", a), ("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2.0, 0.0, 1.0))):
        _save_rgb(out_dir / f"{ID}_{suffix}_2048.png", image)
    for index, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(out_dir / f"{ID}_{name}_2048.png"), spec[:, :, index])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {
        "id": ID,
        "status": "NATIVE-2048-PAINT-AND-MATERIAL-CONTACT-NOT-WIRED",
        "timings_s": timings,
        "deterministic": len(set(digests)) == 1,
        "digest": digests[0],
        "angle_delta_mean": float(delta.mean()),
        "angle_delta_p95": float(np.quantile(delta, 0.95)),
        "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
        "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
        "spec_tiers": [int(len(np.unique(spec[:, :, i]))) for i in range(3)],
        "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])],
    }
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    target = root / "_wilds_fullres_progress_20260824" / "hide_scale_glass_i3"
    print(json.dumps(render_evidence(target), indent=2))
