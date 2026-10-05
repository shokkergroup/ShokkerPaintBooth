# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Emperor Scale I5, fractured armor race livery.

SPB-105 / owner direction 2026-08-26: I3's photographic grit is rejected.
I5 uses an authored, non-photographic black/cyan/violet/gold armor-livery plate
selected at full canvas.  Its visual grammar is layered scale zones, lacquered
carbon panels, exposed gold fracture seams and short foil transitions—not dirt,
grain, a regular hex grid, a generic scalar field, or palette-only reuse.

The image is a versioned source plate, while M/R/Cc are independently authored
from colour zones, panel depth, scale rims, fracture lines and polish response.
M7 movement must be recorded after the exact adapter is wired and evaluated.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_emperor_scale"
NATIVE = 2048


def _norm(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, np.float32)
    return (value - float(value.min())) / max(float(value.max() - value.min()), 1e-6)


def _tier(field: np.ndarray, values: tuple[int, ...]) -> np.ndarray:
    return np.asarray(values, np.uint8)[np.digitize(field, np.quantile(field, np.linspace(.125, .875, 7)))].astype(np.uint8)


def _asset() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "emperor_scale_i5.png"


@lru_cache(maxsize=2)
def _features() -> dict[str, np.ndarray]:
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    hue, sat, value = hsv[:, :, 0] / 180.0, hsv[:, :, 1] / 255.0, hsv[:, :, 2] / 255.0
    light = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    gx = cv2.Sobel(light, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(light, cv2.CV_32F, 0, 1, ksize=3)
    rim = _norm(np.hypot(gx, gy))
    fracture = _norm(np.abs(.81 * gx - .59 * gy))
    panel = _norm(cv2.GaussianBlur(light, (0, 0), 18.0))
    polish = _norm(np.maximum(0.0, light - cv2.GaussianBlur(light, (0, 0), 4.0)))
    dark = np.clip((.27 - light) / .27, 0, 1)
    cyan = np.clip((1.08 * rgb[:, :, 2] + .74 * rgb[:, :, 1] - .62 * rgb[:, :, 0] - .39) / .42, 0, 1)
    violet = np.clip((1.14 * rgb[:, :, 0] + .82 * rgb[:, :, 2] - .66 * rgb[:, :, 1] - .40) / .43, 0, 1)
    gold = np.clip((1.18 * rgb[:, :, 0] + .93 * rgb[:, :, 1] - .65 * rgb[:, :, 2] - .49) / .36, 0, 1)
    blue = np.clip((1.18 * rgb[:, :, 2] + .31 * rgb[:, :, 1] - .62 * rgb[:, :, 0] - .38) / .40, 0, 1)
    return dict(rgb=rgb, hue=hue, sat=sat, value=value, rim=rim, fracture=fracture,
                panel=panel, polish=polish, dark=dark, cyan=cyan, violet=violet,
                gold=gold, blue=blue)


def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    f = _features()
    if not angle_b:
        paint = f["rgb"] * .76 + np.dstack((
            .20 * f["gold"] * f["rim"] + .13 * f["violet"] * f["polish"],
            .18 * f["cyan"] * f["rim"] + .10 * f["gold"] * f["panel"],
            .24 * f["blue"] * f["rim"] + .15 * f["cyan"] * f["polish"],
        )) - .07 * f["dark"][:, :, None]
        return np.clip(paint, 0, 1), f
    # B is a physically distinct optical travel: cyan/green panels brighten as
    # violet/gold foil zones recede, while the same edge anatomy remains fixed.
    carrier = np.clip(.24 * f["panel"] + .23 * f["rim"] + .20 * f["sat"]
                      + .18 * f["polish"] + .15 * f["fracture"], 0, 1)
    paint = .035 * f["rgb"] + np.dstack((
        (.10 + .48 * f["violet"] + .20 * f["gold"]) * carrier,
        (.18 + .53 * f["cyan"] + .19 * f["gold"]) * carrier,
        (.24 + .54 * f["blue"] + .18 * f["violet"]) * carrier,
    )) + .10 * f["rim"][:, :, None]
    return np.clip(paint, 0, 1), f


def _material(f: dict[str, np.ndarray]) -> np.ndarray:
    metal = _tier(np.clip(.27 * f["cyan"] + .23 * f["violet"] + .19 * f["gold"]
                          + .15 * f["rim"] + .09 * f["polish"] + .07 * f["panel"], 0, 1),
                  (7, 34, 72, 109, 148, 187, 224, 253))
    rough = _tier(np.clip(.32 * f["fracture"] + .25 * f["dark"] + .20 * (1.0 - f["panel"])
                          + .14 * f["rim"] + .09 * (1.0 - f["polish"]), 0, 1),
                  (5, 29, 61, 99, 140, 179, 220, 251))
    clear = _tier(np.clip(.30 * f["polish"] + .24 * f["rim"] + .19 * f["panel"]
                          + .15 * f["gold"] + .12 * f["sat"], 0, 1),
                  (6, 31, 66, 104, 143, 181, 217, 254))
    return np.stack((metal, rough, clear), axis=2)


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, fields = _paint(False)
    return paint.astype(np.float32), _material(fields)


def clear_cache() -> None:
    _features.cache_clear()


def render_evidence(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    timings, hashes, last = [], [], None
    for _ in range(3):
        clear_cache()
        started = time.perf_counter()
        angle_a, fields = _paint(False)
        angle_b, _ = _paint(True)
        spec = _material(fields)
        timings.append(time.perf_counter() - started)
        hashes.append(hashlib.sha256(angle_a.tobytes() + angle_b.tobytes() + spec.tobytes()).hexdigest())
        last = angle_a, angle_b, spec
    angle_a, angle_b, spec = last
    for name, image in (("angle_a", angle_a), ("angle_b", angle_b),
                        ("angle_delta_x2", np.clip(np.abs(angle_a - angle_b) * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"),
                    cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for channel, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, channel])
    report = {
        "id": ID, "attempt": "I5", "native": [NATIVE, NATIVE],
        "deterministic": len(set(hashes)) == 1, "timings_s": timings,
        "spec_std_m_r_cc": [float(spec[:, :, i].std()) for i in range(3)],
        "spec_range_m_r_cc": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
        "angle_delta_mean": float(np.abs(angle_a - angle_b).mean()),
        "angle_delta_p95": float(np.quantile(np.abs(angle_a - angle_b), .95)),
    }
    (directory / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]
                                     / "_wilds_fullres_progress_20260824"
                                     / "emperor_scale_livery_i5"), indent=2))
