# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Magpie Wing I4, structural vane-lacquer candidate.

SPB-105 / owner screen 2026-08-26: installed I2 is a photographic bristle
pile.  The earlier graphic vane source eliminated that visual defect but its
spec channels were coupled and failed M7.  I4 preserves the authored black
lacquer, broken cyan/violet/silver vane inserts, fine internal barbs and black
release cuts, while assigning independent physical maps: chromatic inlay metal,
microbarb abrasion roughness, and membrane-tension clearcoat.  No noise layer,
recolor-only edit, shared Wilds carrier, tile border or generic spec clone.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib, json, time

import cv2
import numpy as np

ID = "fmo_magpie_wing"
NATIVE = 2048
M_T = np.asarray((7, 29, 56, 88, 123, 163, 207, 251), np.uint8)
R_T = np.asarray((13, 39, 68, 102, 140, 181, 219, 248), np.uint8)
C_T = np.asarray((5, 26, 54, 84, 120, 159, 207, 252), np.uint8)


def _norm(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return (a - a.min()) / (a.max() - a.min() + 1e-8)


def _tier(field: np.ndarray, values: np.ndarray) -> np.ndarray:
    return values[np.digitize(field, np.quantile(field, np.linspace(.125, .875, 7)))].astype(np.uint8)


def _asset() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "magpie_wing_i3.png"


@lru_cache(maxsize=2)
def _fields() -> dict[str, np.ndarray]:
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.0
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    seam = _norm(np.hypot(gx, gy))
    microbarb = _norm(np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.05)))
    abrasion = _norm(np.abs(cv2.GaussianBlur(lum, (0, 0), 2.0) - cv2.GaussianBlur(lum, (0, 0), 8.0)))
    bay = _norm(cv2.GaussianBlur(lum, (0, 0), 18.0))
    bgx = cv2.Sobel(bay, cv2.CV_32F, 1, 0, ksize=3)
    bgy = cv2.Sobel(bay, cv2.CV_32F, 0, 1, ksize=3)
    tension_heading = (np.arctan2(bgy, bgx) + np.pi) / (2.0 * np.pi)
    tension_strength = _norm(np.hypot(bgx, bgy))
    cross_etch = _norm(np.abs(.76 * gx - .65 * gy))
    cyan = np.clip((rgb[:, :, 2] + .47 * rgb[:, :, 1] - 1.13 * rgb[:, :, 0] - .05) / .44, 0, 1)
    violet = np.clip((rgb[:, :, 0] + rgb[:, :, 2] - 1.17 * rgb[:, :, 1] - .04) / .43, 0, 1)
    silver = np.clip((lum - .46 + .14 * (1 - sat)) / .35, 0, 1)
    inlay = _norm(np.maximum(cyan, violet) + .48 * silver + .21 * seam)
    return {"rgb": rgb, "sat": sat, "lum": lum, "seam": seam, "microbarb": microbarb,
            "abrasion": abrasion, "bay": bay, "tension_heading": tension_heading,
            "tension_strength": tension_strength, "cross_etch": cross_etch, "cyan": cyan,
            "violet": violet, "silver": silver, "inlay": inlay}


def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    f = _fields()
    a = np.clip(f["rgb"] * .86 + np.dstack((.07 * f["silver"] + .035 * f["violet"],
                                             .09 * f["cyan"] + .05 * f["silver"],
                                             .17 * f["cyan"] + .10 * f["violet"])), 0, 1)
    if not angle_b:
        return a, f
    # Only structural vane inlays exchange optical ownership; black releases,
    # barb density and silver repair geometry stay stable across the flip.
    b = a * .23 + np.dstack((.33 * f["violet"] + .17 * f["silver"],
                             .20 * f["cyan"] + .12 * f["silver"],
                             .61 * f["cyan"] + .36 * f["violet"]))
    b += np.dstack((.04 * f["seam"], .07 * f["microbarb"], .13 * f["cross_etch"]))
    return np.clip(b, 0, 1), f


def _material(f: dict[str, np.ndarray]) -> np.ndarray:
    metal = _norm(.57 * f["inlay"] + .24 * f["silver"] + .19 * f["cyan"]
                  + .18 * _norm(cv2.GaussianBlur(f["inlay"], (0, 0), 7.0)))
    rough = _norm(.47 * f["microbarb"] + .30 * f["abrasion"] + .27 * f["cross_etch"]
                  + .18 * _norm(cv2.GaussianBlur(f["abrasion"], (0, 0), 4.0)))
    clear = _norm(.57 * f["tension_heading"] + .24 * f["tension_strength"]
                  + .17 * f["bay"] - .15 * f["abrasion"]
                  + .17 * _norm(cv2.GaussianBlur(f["tension_strength"], (0, 0), 13.0)))
    return np.stack((_tier(metal, M_T), _tier(rough, R_T), _tier(clear, C_T)), axis=2)


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, fields = _paint(False)
    return paint, _material(fields)


def clear_cache() -> None:
    _fields.cache_clear()


def render_evidence(directory: Path) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    elapsed, digests, last = [], [], None
    for _ in range(3):
        clear_cache(); started = time.perf_counter()
        a, fields = _paint(False); b, _ = _paint(True); spec = _material(fields)
        elapsed.append(time.perf_counter() - started)
        digests.append(hashlib.sha256(a.tobytes() + b.tobytes() + spec.tobytes()).hexdigest())
        last = a, b, spec
    a, b, spec = last; delta = np.abs(a - b)
    for name, image in (("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for i, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, i])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {"id": ID, "timings_s": elapsed, "deterministic": len(set(digests)) == 1,
              "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
              "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
              "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])],
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95))}
    (directory / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    return report


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "magpie_wing_livery_i4"), indent=2))
