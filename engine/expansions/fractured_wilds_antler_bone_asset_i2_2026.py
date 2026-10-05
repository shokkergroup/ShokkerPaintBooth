# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Antler Bone I2, texture-backed calcified trabeculae.

SPB-105 / owner Wilds rebuild, 2026-08-26. The rejected spinodoid approach
read as homogeneous foam. I2 instead uses a versioned close material asset:
continuous calcified lamellae, embedded trabecular pores, polished growth
layers and mineral fracture flashes. M/R/Cc are causal but independently
owned by dense, dark pore, ridge and optical-mineral responses. There is no
legacy composer, recolour fallback or synthetic static; A/B swaps the optical
owner of the same calcified structure.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np

ID = "fc_antler_bone"
NATIVE = 2048
M_T = np.asarray((7, 29, 56, 88, 123, 163, 207, 251), np.uint8)
R_T = np.asarray((13, 39, 68, 102, 140, 181, 219, 248), np.uint8)
C_T = np.asarray((5, 26, 54, 84, 120, 159, 207, 252), np.uint8)


def _tier(field: np.ndarray, targets: np.ndarray) -> np.ndarray:
    return targets[np.digitize(field, np.quantile(field, np.linspace(.125, .875, 7)))].astype(np.uint8)


def _asset() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "antler_bone_trabecular_i2.png"


@lru_cache(maxsize=2)
def _fields() -> dict[str, np.ndarray]:
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    local = cv2.GaussianBlur(lum, (0, 0), 5.0)
    pore = np.clip((local - lum) / (np.quantile(np.abs(local - lum), .995) + 1e-8), 0, 1)
    grain = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.2))
    grain /= grain.max() + 1e-8
    strata = cv2.GaussianBlur(lum, (0, 0), 10.0)
    strata = (strata - strata.min()) / (strata.max() - strata.min() + 1e-8)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    ridge = np.hypot(gx, gy)
    ridge /= ridge.max() + 1e-8
    cool = np.clip((rgb[:, :, 2] - rgb[:, :, 0] + .08) / .30, 0, 1)
    warm = np.clip((rgb[:, :, 0] + .24 * rgb[:, :, 1] - .74 * rgb[:, :, 2] - .02) / .42, 0, 1)
    mineral = np.clip(.48 * cool + .28 * warm + .24 * ridge, 0, 1)
    return {"rgb": rgb, "pore": pore, "grain": grain, "strata": strata, "ridge": ridge, "cool": cool, "warm": warm, "mineral": mineral}


def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    field = _fields()
    rgb = field["rgb"]
    if not angle_b:
        return rgb, field
    # Fractured B reveals cool mineral travel through the same pore/ridge relief.
    b = rgb * .53 + np.dstack((.09 * field["warm"] + .05 * field["ridge"], .15 * field["cool"] + .05 * field["mineral"], .29 * field["cool"] + .15 * field["ridge"]))
    b += np.dstack((.08 * field["pore"], .035 * field["pore"], .13 * field["pore"]))
    return np.clip(b, 0, 1), field


def _material(field: dict[str, np.ndarray]) -> np.ndarray:
    metal = .38 * field["warm"] + .29 * field["mineral"] + .20 * field["ridge"] + .16 * field["strata"]
    rough = .48 * field["pore"] + .27 * field["grain"] + .21 * (1 - field["strata"]) + .17 * field["ridge"] - .13 * field["cool"]
    coat = .45 * field["cool"] + .28 * field["mineral"] + .24 * field["ridge"] * (1 - field["pore"]) - .20 * field["pore"]
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
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "antler_bone_asset_i2"), indent=2))
