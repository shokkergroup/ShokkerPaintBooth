# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Batwing I4, engineered membrane-lacquer candidate.

SPB-105 / Wilds rebuild / tick 2026-08-27.  Owner's full-canvas verdict
rejected I2's leather photograph.  A prior structural-livery direction was
visually viable but scored below M7 because its channels were too coupled.
I4 starts from one new authored black membrane livery: unequal tension bays,
forked dark release seams, cyan/violet/gold fracture inlays, compact seam
stitches and contained dry-brush etches.  Metal follows iridescent inlays,
roughness follows membrane abrasion relief, and clearcoat follows polished
black bay planes; no channel is a recolored/copy-pasted spec topology.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np

ID = "fc_batwing"
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
    return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "batwing_livery_i4.png"


@lru_cache(maxsize=2)
def _fields() -> dict[str, np.ndarray]:
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    hue, sat = hsv[:, :, 0] / 180.0, hsv[:, :, 1] / 255.0
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    seam = _norm(np.hypot(gx, gy))
    micro = _norm(np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.25)))
    abrasion = _norm(np.abs(cv2.GaussianBlur(lum, (0, 0), 2.2) - cv2.GaussianBlur(lum, (0, 0), 9.5)))
    bay = _norm(cv2.GaussianBlur(lum, (0, 0), 17.0))
    bgx = cv2.Sobel(bay, cv2.CV_32F, 1, 0, ksize=3)
    bgy = cv2.Sobel(bay, cv2.CV_32F, 0, 1, ksize=3)
    # Tension heading is a true membrane-bay variable: clearcoat cures along
    # the stretched direction, independently of inlay color or abrasion value.
    tension_heading = (np.arctan2(bgy, bgx) + np.pi) / (2.0 * np.pi)
    tension_strength = _norm(np.hypot(bgx, bgy))
    # Visible material identities in the source livery.
    cyan = np.clip((rgb[:, :, 2] + .48 * rgb[:, :, 1] - 1.12 * rgb[:, :, 0] - .06) / .44, 0, 1)
    violet = np.clip((rgb[:, :, 0] + rgb[:, :, 2] - 1.18 * rgb[:, :, 1] - .04) / .42, 0, 1)
    gold = np.clip((rgb[:, :, 0] + .83 * rgb[:, :, 1] - 1.18 * rgb[:, :, 2] - .10) / .38, 0, 1)
    silver = np.clip((lum - .44 + .13 * (1 - sat)) / .36, 0, 1)
    # One-sided directional etches distinguish membrane wear from release seams.
    oriented = _norm(np.abs(.74 * gx - .67 * gy))
    # Opposed incident-light derivative: this is the dry-polish direction on
    # membrane bays, distinct from the cross-grain abrasion used for roughness.
    polish_dir = _norm(np.abs(.67 * gx + .74 * gy))
    inlay = _norm(np.maximum(cyan, violet) + .65 * gold + .25 * seam)
    return {"rgb": rgb, "hue": hue, "sat": sat, "lum": lum, "seam": seam,
            "micro": micro, "abrasion": abrasion, "bay": bay,
            "tension_heading": tension_heading, "tension_strength": tension_strength, "cyan": cyan,
            "violet": violet, "gold": gold, "silver": silver, "oriented": oriented,
            "polish_dir": polish_dir, "inlay": inlay}


def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    f = _fields()
    a = np.clip(f["rgb"] * .83 + np.dstack((.07 * f["gold"] + .06 * f["silver"],
                                             .10 * f["cyan"] + .05 * f["silver"],
                                             .16 * f["cyan"] + .11 * f["violet"])), 0, 1)
    if not angle_b:
        return a, f
    # Structural flip changes only the optical inlay owner.  Black membrane
    # bays, cuts and stitches stay fixed, so this is not a hue-rotation trick.
    b = a * .24 + np.dstack((.36 * f["violet"] + .22 * f["gold"] + .09 * f["silver"],
                             .16 * f["cyan"] + .10 * f["silver"],
                             .58 * f["cyan"] + .47 * f["violet"] + .10 * f["gold"]))
    b += np.dstack((.04 * f["seam"], .07 * f["micro"], .14 * f["oriented"]))
    return np.clip(b, 0, 1), f


def _material(f: dict[str, np.ndarray]) -> np.ndarray:
    # Three maps deliberately privilege different physical evidence.  Their
    # blurred spreads are derived only from their own parent mark type.
    metal = _norm(.56 * f["inlay"] + .23 * f["gold"] + .18 * f["silver"]
                  + .18 * _norm(cv2.GaussianBlur(f["inlay"], (0, 0), 7.0)))
    rough = _norm(.48 * f["abrasion"] + .31 * f["oriented"] + .23 * f["micro"]
                  + .19 * _norm(cv2.GaussianBlur(f["abrasion"], (0, 0), 4.0)))
    clear = _norm(.56 * f["tension_heading"] + .23 * f["tension_strength"]
                  + .17 * f["polish_dir"] - .16 * f["abrasion"]
                  + .16 * _norm(cv2.GaussianBlur(f["tension_strength"], (0, 0), 13.0)))
    return np.stack((_tier(metal, M_T), _tier(rough, R_T), _tier(clear, C_T)), axis=2)


def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, fields = _paint(False)
    return paint, _material(fields)


def clear_cache() -> None:
    _fields.cache_clear()


def render_evidence(directory: Path) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    timings, hashes, last = [], [], None
    for _ in range(3):
        clear_cache(); started = time.perf_counter()
        a, fields = _paint(False); b, _ = _paint(True); spec = _material(fields)
        timings.append(time.perf_counter() - started)
        hashes.append(hashlib.sha256(a.tobytes() + b.tobytes() + spec.tobytes()).hexdigest())
        last = a, b, spec
    a, b, spec = last; delta = np.abs(a - b)
    for name, image in (("angle_a", a), ("angle_b", b), ("angle_delta_x2", np.clip(delta * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for i, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, i])
    corr = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {"id": ID, "timings_s": timings, "deterministic": len(set(hashes)) == 1,
              "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
              "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
              "spec_corr_m_r_cc": [float(corr[0, 1]), float(corr[0, 2]), float(corr[1, 2])],
              "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95))}
    (directory / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    return report


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "batwing_livery_i4"), indent=2))
