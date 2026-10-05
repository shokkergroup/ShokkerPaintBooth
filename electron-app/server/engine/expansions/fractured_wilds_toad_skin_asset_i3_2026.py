# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Toad Skin I3, texture-backed glandular dermis.

SPB-105 / owner Wilds rebuild, 2026-08-26. I2's sparse, dot-over-fold
carrier was rejected as decorative scatter. I3 uses a versioned close dermis
asset selected for dense connected pebbled tissue, recessed pores, wet creases
and attached blue/amber interference ridges. Its material maps derive from
physical relief, pore recession and wet/cool responses; no random noise,
legacy recolour, or shared Wilds composer is introduced. A/B changes which
side of each same physical ridge owns the optical flash.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np

ID = "fc_toad_skin"
NATIVE = 2048
M_T = np.asarray((7, 29, 56, 88, 123, 163, 207, 251), np.uint8)
R_T = np.asarray((13, 39, 68, 102, 140, 181, 219, 248), np.uint8)
C_T = np.asarray((5, 26, 54, 84, 120, 159, 207, 252), np.uint8)


def _tier(field: np.ndarray, targets: np.ndarray) -> np.ndarray:
    return targets[np.digitize(field, np.quantile(field, np.linspace(.125, .875, 7)))].astype(np.uint8)


def _asset() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "toad_skin_gland_i3.png"


@lru_cache(maxsize=2)
def _fields() -> dict[str, np.ndarray]:
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    local = cv2.GaussianBlur(lum, (0, 0), 3.2)
    pore = np.clip((local - lum) / (np.quantile(np.abs(local - lum), .995) + 1e-8), 0, 1)
    fine = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.05))
    fine /= fine.max() + 1e-8
    broad = cv2.GaussianBlur(lum, (0, 0), 8.0)
    broad = (broad - broad.min()) / (broad.max() - broad.min() + 1e-8)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    ridge = np.hypot(gx, gy)
    ridge /= ridge.max() + 1e-8
    cool = np.clip((rgb[:, :, 2] - rgb[:, :, 0] + .14) / .38, 0, 1)
    warm = np.clip((rgb[:, :, 0] - .60 * rgb[:, :, 2] + .06) / .38, 0, 1)
    wet = np.clip(cool * (.34 + .66 * ridge) + .22 * warm * ridge, 0, 1)
    gland = np.clip(.46 * fine + .31 * ridge + .23 * (1 - pore) * broad, 0, 1)
    return {"rgb": rgb, "pore": pore, "fine": fine, "broad": broad, "ridge": ridge, "cool": cool, "warm": warm, "wet": wet, "gland": gland}


def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    field = _fields()
    rgb = field["rgb"]
    if not angle_b:
        return rgb, field
    # Same dermal ridges exchange amber body light for blue-green wet flash.
    b = rgb * .45 + np.dstack((.07 * field["warm"] + .06 * field["ridge"], .17 * field["cool"] + .08 * field["wet"], .34 * field["cool"] + .16 * field["ridge"]))
    b += np.dstack((.10 * field["pore"], .025 * field["pore"], .16 * field["pore"]))
    return np.clip(b, 0, 1), field


def _material(field: dict[str, np.ndarray]) -> np.ndarray:
    metal = .39 * field["warm"] + .27 * field["ridge"] + .20 * field["gland"] + .18 * field["wet"]
    rough = .46 * field["pore"] + .29 * field["fine"] + .22 * (1 - field["broad"]) + .16 * field["gland"] - .16 * field["cool"]
    coat = .44 * field["cool"] + .31 * field["wet"] + .23 * field["ridge"] * (1 - field["pore"]) - .19 * field["pore"]
    return np.stack((_tier(metal, M_T), _tier(rough, R_T), _tier(coat, C_T)), axis=2)


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, field = _paint(False)
    return paint, _material(field)


def clear_cache() -> None:
    _fields.cache_clear()


def render_evidence(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    timings, hashes, last = [], [], None
    for _ in range(3):
        clear_cache()
        started = time.perf_counter()
        a, field = _paint(False)
        b, _ = _paint(True)
        spec = _material(field)
        timings.append(time.perf_counter() - started)
        hashes.append(hashlib.sha256(np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes() + spec.tobytes()).hexdigest())
        last = a, b, spec
    a, b, spec = last
    delta = np.abs(a - b)
    for name, image in (("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for channel, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, channel])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    out = {"id": ID, "timings_s": timings, "deterministic": len(set(hashes)) == 1, "spec_std": [float(spec[:, :, i].std()) for i in range(3)], "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)], "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])], "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95))}
    (directory / "manifest.json").write_text(json.dumps(out, indent=2), encoding="utf8")
    return out


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "toad_skin_asset_i3"), indent=2))
