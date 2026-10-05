# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Amber Moldring I1 collision-censored growth fronts.

SPB-105 / Wilds rebuild tick 49, 2026-08-25. Owner verdict driving this work:
"LAZY" recolors and shared spec maps are the category's cardinal sin; every
native primitive must stay fine (8-32 px at 2048), causal, dense and visibly
different. Before: legacy shared-composer mold-ring relative, no admissible
native-2048 evidence. After: pending owner-eye and M7 evidence.

No RNG, sampled noise, reaction texture, circle stamps, placed ring glyphs or
shared spec composer is used. Twenty-three unequal deterministic growth sources
compete by arrival time. Their fronts are clipped by the first physical
collision, and all secondary marks descend from that chronology.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fpe_amber_moldring"
AUTHORED = 1024
CALM_SPEC = np.asarray((4.0, 120.0, 16.0), np.float32)

PALETTE_A = np.asarray([
    (9, 8, 18), (32, 10, 28), (76, 16, 34), (136, 31, 25),
    (205, 67, 18), (248, 126, 18), (255, 191, 37), (225, 235, 74),
    (112, 212, 90), (30, 171, 117), (11, 118, 130), (20, 76, 142),
    (65, 38, 143), (127, 37, 139), (206, 50, 112),
], np.float32) / 255.0

PALETTE_B = np.asarray([
    (8, 11, 24), (17, 40, 75), (13, 83, 122), (16, 137, 139),
    (42, 190, 116), (129, 225, 69), (222, 236, 63), (255, 179, 45),
    (249, 96, 50), (221, 43, 93), (164, 39, 139), (102, 46, 156),
    (48, 53, 144), (25, 74, 116), (12, 33, 54),
], np.float32) / 255.0

M_TIERS = np.asarray((6, 28, 55, 84, 118, 157, 203, 250), np.uint8)
R_TIERS = np.asarray((14, 37, 66, 101, 139, 177, 216, 249), np.uint8)
CC_TIERS = np.asarray((5, 24, 48, 79, 116, 158, 207, 252), np.uint8)


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
    flat = np.asarray(field, np.float32).ravel()
    cuts = np.quantile(flat, np.linspace(0.125, 0.875, 7))
    return values[np.digitize(field, cuts)].astype(np.uint8)


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    n = AUTHORED
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx + 0.5) / n
    y = (yy + 0.5) / n

    first = np.full((n, n), 1e6, np.float32)
    second = np.full((n, n), 1e6, np.float32)
    owner = np.zeros((n, n), np.int16)
    owner_angle = np.zeros((n, n), np.float32)
    owner_radius = np.zeros((n, n), np.float32)

    golden = 0.6180339887498948
    silver = 0.4142135623730950
    for i in range(23):
        cx = ((0.113 + (i + 1) * golden) % 1.0)
        cy = ((0.271 + (i + 1) * silver) % 1.0)
        # Edge sources are deliberately pushed outside the crop. This prevents
        # a field of complete colony/ring icons while retaining their chronology.
        edge = i % 6
        if edge == 0:
            cx -= 0.15
        elif edge == 1:
            cx += 0.15
        elif edge == 2:
            cy -= 0.14
        elif edge == 3:
            cy += 0.14

        ang = np.float32((i * 2.399963229728653) % (2.0 * np.pi))
        ca, sa = np.cos(ang), np.sin(ang)
        dx, dy = x - np.float32(cx), y - np.float32(cy)
        u = ca * dx + sa * dy
        v = -sa * dx + ca * dy
        stretch = np.float32(0.72 + 0.26 * (0.5 + 0.5 * np.sin(i * 1.731)))
        radius = np.sqrt((u / stretch) ** 2 + (v * stretch) ** 2 + 1e-8)
        theta = np.arctan2(v * stretch, u / stretch)
        crenel = (0.0045 * np.sin(theta * (5 + i % 4) + i * 0.73)
                  + 0.0028 * np.sin(theta * (9 + i % 5) - radius * (21 + i % 7)))
        birth = np.float32(0.026 * (i % 7) + 0.011 * np.sin(i * 1.19))
        speed = np.float32(0.84 + 0.18 * np.sin(i * 1.37 + 0.4))
        arrival = radius / speed + birth + crenel

        better = arrival < first
        second = np.where(better, first, np.minimum(second, arrival))
        first = np.where(better, arrival, first)
        owner = np.where(better, i, owner)
        owner_angle = np.where(better, theta, owner_angle)
        owner_radius = np.where(better, radius, owner_radius)

    margin = np.clip(second - first, 0.0, 0.12)
    collision = np.exp(-((margin / 0.0105) ** 2)).astype(np.float32)
    collision_core = np.exp(-((margin / 0.0043) ** 2)).astype(np.float32)

    local_spacing = (0.0118 + 0.0022 * (0.5 + 0.5 * np.sin(owner * 1.47))).astype(np.float32)
    band_phase = (2.0 * np.pi * first / local_spacing
                  + 0.58 * np.sin(owner_angle * 5.0 + owner * 0.71)
                  + 0.24 * np.sin(owner_angle * 11.0 - owner_radius * 29.0))
    signed = np.sin(band_phase)
    band_core = np.exp(-((signed / 0.22) ** 2)).astype(np.float32)
    band_shoulder = np.exp(-((signed / 0.50) ** 2)).astype(np.float32)

    sector_phase = owner_angle * (3 + owner % 4) + owner * 0.83 + first * 31.0
    sector = np.exp(-((np.sin(sector_phase) / 0.24) ** 2)).astype(np.float32)
    sector *= (0.25 + 0.75 * band_shoulder)

    segment_gate = 0.5 + 0.5 * np.sin(owner_angle * (13 + owner % 5) + owner_radius * 47.0 + owner)
    spore_rim = band_core * np.clip((segment_gate - 0.34) / 0.66, 0.0, 1.0)
    starvation = band_core * np.clip((-segment_gate - 0.15) / 0.85, 0.0, 1.0)

    scar_gate = 0.5 + 0.5 * np.sin(first * 91.0 + owner_angle * 7.0 - owner * 0.37)
    healed = collision * np.clip((scar_gate - 0.48) / 0.52, 0.0, 1.0)
    open_scar = collision_core * np.clip((0.57 - scar_gate) / 0.57, 0.0, 1.0)

    fuzzy = np.clip(band_shoulder - band_core, 0.0, 1.0)
    fuzzy *= 0.45 + 0.55 * (0.5 + 0.5 * np.sin(owner_angle * 17.0 + first * 73.0))
    wedge = sector * collision * (0.40 + 0.60 * band_core)
    wet = np.clip(1.0 - first / 0.74, 0.0, 1.0)
    age = _norm(first + 0.018 * owner)
    order = np.mod(np.floor(first / local_spacing) + owner * 3, 15).astype(np.float32) / 15.0

    return {
        "first": first, "owner": owner.astype(np.float32), "angle": owner_angle,
        "age": age, "order": order, "collision": collision,
        "collision_core": collision_core, "band_core": band_core,
        "band_shoulder": band_shoulder, "sector": sector,
        "spore_rim": spore_rim, "starvation": starvation,
        "healed": healed, "open_scar": open_scar, "fuzzy": fuzzy,
        "wedge": wedge, "wet": wet,
    }


def _compose(fields: dict[str, np.ndarray], palette: np.ndarray, angle_b: bool) -> np.ndarray:
    travel = (fields["order"] * 0.72 + fields["age"] * 0.37
              + fields["owner"] * golden_fraction())
    if angle_b:
        travel = 1.0 - travel + 0.19 * fields["wet"]
    rgb = _palette(travel, palette)

    relief = (0.64 + 0.22 * fields["band_shoulder"]
              + 0.17 * fields["spore_rim"] - 0.31 * fields["starvation"]
              - 0.43 * fields["open_scar"])
    rgb *= np.clip(relief, 0.18, 1.25)[..., None]
    rgb += np.asarray((0.17, 0.11, 0.025) if not angle_b else (0.025, 0.12, 0.18), np.float32) * fields["spore_rim"][..., None]
    rgb += np.asarray((0.05, 0.22, 0.13) if not angle_b else (0.21, 0.045, 0.18), np.float32) * fields["healed"][..., None]
    rgb += np.asarray((0.18, 0.06, 0.20) if not angle_b else (0.04, 0.18, 0.21), np.float32) * fields["wedge"][..., None]
    rgb *= (1.0 - 0.36 * fields["collision_core"])[..., None]
    rgb *= (1.0 - 0.30 * fields["starvation"])[..., None]
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def golden_fraction() -> float:
    return 0.06180339887498948


def _spec_maps(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    metal = (0.50 * fields["spore_rim"] + 0.28 * fields["wedge"]
             + 0.17 * fields["healed"] + 0.12 * (1.0 - fields["age"]))
    rough = (0.48 * fields["fuzzy"] + 0.36 * fields["starvation"]
             + 0.23 * fields["sector"] + 0.13 * fields["age"]
             - 0.18 * fields["spore_rim"])
    coat = (0.44 * fields["wet"] + 0.34 * fields["healed"]
            + 0.20 * fields["band_shoulder"] + 0.17 * (1.0 - fields["collision"])
            - 0.29 * fields["open_scar"])
    return _tier(metal, M_TIERS), _tier(rough, R_TIERS), _tier(coat, CC_TIERS)


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    fields = _fields()
    paint = _compose(fields, PALETTE_B if angle_b else PALETTE_A, angle_b)
    paint = cv2.resize(paint, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)
    return np.clip(paint, 0.0, 1.0).astype(np.float32), fields


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, fields = _paint(False)
    m, r, cc = _spec_maps(fields)
    spec = np.stack((m, r, cc), axis=2)
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
    timings = []
    digests = []
    last = None
    for _ in range(3):
        clear_cache()
        start = time.perf_counter()
        a, fields = _paint(False)
        b, _ = _paint(True)
        m, r, cc = _spec_maps(fields)
        spec = cv2.resize(np.stack((m, r, cc), axis=2), (2048, 2048), interpolation=cv2.INTER_NEAREST)
        timings.append(time.perf_counter() - start)
        blob = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes() + spec.tobytes()
        digests.append(hashlib.sha256(blob).hexdigest())
        last = (a, b, spec)
    a, b, spec = last
    delta = np.abs(a - b)
    _save_rgb(out_dir / f"{ID}_paint_2048.png", a)
    _save_rgb(out_dir / f"{ID}_angle_a_2048.png", a)
    _save_rgb(out_dir / f"{ID}_angle_b_2048.png", b)
    _save_rgb(out_dir / f"{ID}_angle_delta_x2_2048.png", np.clip(delta * 2.0, 0.0, 1.0))
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
    target = root / "_wilds_fullres_progress_20260824" / "amber_moldring_i1"
    print(json.dumps(render_evidence(target), indent=2))
