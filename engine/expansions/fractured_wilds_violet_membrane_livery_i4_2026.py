"""Violet Membrane I4 — tension-film lacquer candidate; SPB-105 2026-08-27.

I3 is a photographic foam/cavity surface. I4 makes its color response causal:
violet film bays retain fine stress striations while only folded/ruptured lips
carry cyan, magenta and pearl optical travel.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np

ID = "fpe_violet_membrane"; NATIVE = 2048
M = np.asarray((7, 33, 67, 104, 142, 181, 219, 253), np.uint8)
R = np.asarray((5, 30, 61, 99, 140, 179, 220, 251), np.uint8)
C = np.asarray((6, 32, 65, 103, 143, 181, 217, 254), np.uint8)


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (a.max() - a.min() + 1e-8)


def _tier(a: np.ndarray, values: np.ndarray) -> np.ndarray:
    return values[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)


@lru_cache(maxsize=2)
def _fields() -> dict[str, np.ndarray]:
    asset = Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "violet_membrane_livery_i4.png"
    raw = cv2.imread(str(asset), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(asset)
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    fold_lip = _norm(np.hypot(gx, gy))
    striation = _norm(np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.15)))
    rupture = _norm(np.abs(.69 * gx + .72 * gy))
    bay_depth = _norm(cv2.GaussianBlur(lum, (0, 0), 15.0))
    fold_heading = (np.arctan2(gy, gx) + np.pi) / (2 * np.pi)
    pearl = np.clip((lum - .38 + .20 * (1 - hsv[:, :, 1] / 255.)) / .42, 0, 1)
    cyan = np.clip((rgb[:, :, 2] + .48 * rgb[:, :, 1] - 1.08 * rgb[:, :, 0] - .07) / .38, 0, 1)
    violet = np.clip((rgb[:, :, 2] + .36 * rgb[:, :, 0] - 1.11 * rgb[:, :, 1] - .05) / .36, 0, 1)
    magenta = np.clip((1.02 * rgb[:, :, 0] + rgb[:, :, 2] - 1.20 * rgb[:, :, 1] - .10) / .40, 0, 1)
    return {"rgb": rgb, "fold_lip": fold_lip, "striation": striation, "rupture": rupture,
            "bay_depth": bay_depth, "fold_heading": fold_heading, "pearl": pearl,
            "cyan": cyan, "violet": violet, "magenta": magenta}


def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    f = _fields()
    a = np.clip(f["rgb"] * .79 + np.dstack((.11 * f["magenta"] * f["fold_lip"] + .05 * f["pearl"] * f["rupture"],
                                               .08 * f["cyan"] * f["fold_lip"] + .04 * f["pearl"] * f["striation"],
                                               .17 * f["cyan"] * f["fold_lip"] + .13 * f["violet"] * f["rupture"])), 0, 1)
    if not angle_b:
        return a, f
    # Opposed view keeps bays/seams fixed and transfers only optical travel.
    b = a * .24 + np.dstack((.36 * f["magenta"] + .17 * f["pearl"], .18 * f["cyan"] + .13 * f["pearl"],
                               .62 * f["cyan"] + .46 * f["violet"] + .08 * f["fold_lip"]))
    b += np.dstack((.03 * f["rupture"], .06 * f["striation"], .12 * f["fold_lip"]))
    return np.clip(b, 0, 1), f


def _material(f: dict[str, np.ndarray]) -> np.ndarray:
    metal = _norm(.43 * f["cyan"] + .34 * f["violet"] + .27 * f["magenta"] + .21 * f["pearl"] + .15 * f["fold_lip"])
    directional = np.abs(np.sin(2 * np.pi * (f["fold_heading"] + .29 * f["bay_depth"])))
    rough = _norm(.51 * f["striation"] + .29 * directional + .23 * f["rupture"] - .18 * f["fold_lip"])
    clear = _norm(.54 * f["bay_depth"] + .27 * _norm(cv2.GaussianBlur(f["fold_lip"], (0, 0), 11)) + .19 * f["fold_heading"] - .18 * f["striation"])
    return np.stack((_tier(metal, M), _tier(rough, R), _tier(clear, C)), axis=2)


def _authored() -> tuple[np.ndarray, np.ndarray]:
    a, fields = _paint(False)
    return a, _material(fields)


def clear_cache() -> None:
    _fields.cache_clear()


def render_evidence(directory: Path) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True); timings, hashes, last = [], [], None
    for _ in range(3):
        clear_cache(); started = time.perf_counter()
        a, fields = _paint(False); b, _ = _paint(True); spec = _material(fields)
        timings.append(time.perf_counter() - started); hashes.append(hashlib.sha256(a.tobytes() + b.tobytes() + spec.tobytes()).hexdigest()); last = a, b, spec
    a, b, spec = last; delta = np.abs(a - b)
    for name, image in (("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for index, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, index])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {"id": ID, "timings_s": timings, "deterministic": len(set(hashes)) == 1,
              "spec_std": [float(spec[:, :, index].std()) for index in range(3)],
              "spec_range": [[int(spec[:, :, index].min()), int(spec[:, :, index].max())] for index in range(3)],
              "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])],
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95))}
    (directory / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    return report


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "violet_membrane_livery_i4"), indent=2))
