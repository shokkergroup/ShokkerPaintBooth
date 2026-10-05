"""Stag Carapace I3 — fractured armor-lacquer candidate; SPB-105 2026-08-27.

I1 is a repeating oval shell field.  I3 is an edge-to-edge field of unequal
protective impact plates: fine cross-scuffs live *inside* plates and cyan,
violet, and bronze are restricted to their own broken fracture lips.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np

ID = "fmo_stag_carapace"; NATIVE = 2048
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
    asset = Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "stag_carapace_livery_i3.png"
    raw = cv2.imread(str(asset), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(asset)
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    lip = _norm(np.hypot(gx, gy))
    cross_scuff = _norm(np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.2)))
    impact_split = _norm(np.abs(.78 * gx - .62 * gy))
    plate_body = _norm(cv2.GaussianBlur(lum, (0, 0), 14.0))
    plate_gloss = _norm(np.abs(cv2.Laplacian(cv2.GaussianBlur(lum, (0, 0), 5), cv2.CV_32F)))
    abrasion_heading = (np.arctan2(gy, gx) + np.pi) / (2 * np.pi)
    hue = hsv[:, :, 0] / 180.
    cyan = np.clip((rgb[:, :, 2] + .48 * rgb[:, :, 1] - 1.08 * rgb[:, :, 0] - .08) / .38, 0, 1)
    violet = np.clip((rgb[:, :, 2] + .34 * rgb[:, :, 0] - 1.12 * rgb[:, :, 1] - .08) / .36, 0, 1)
    bronze = np.clip((rgb[:, :, 0] + .42 * rgb[:, :, 1] - 1.15 * rgb[:, :, 2] - .08) / .42, 0, 1)
    oxblood = np.clip((1.05 * rgb[:, :, 0] - .48 * rgb[:, :, 1] - .46 * rgb[:, :, 2] - .05) / .40, 0, 1)
    silver = np.clip((lum - .38 + .18 * (1 - hsv[:, :, 1] / 255.)) / .42, 0, 1)
    return {"rgb": rgb, "lip": lip, "cross_scuff": cross_scuff, "impact_split": impact_split,
            "plate_body": plate_body, "plate_gloss": plate_gloss, "cyan": cyan, "violet": violet,
            "bronze": bronze, "oxblood": oxblood, "silver": silver, "abrasion_heading": abrasion_heading,
            "hue": hue}


def _paint(angle_b: bool = False) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    f = _fields()
    a = np.clip(f["rgb"] * .79 + np.dstack((.11 * f["bronze"] * f["lip"] + .06 * f["oxblood"] * f["cross_scuff"],
                                               .08 * f["cyan"] * f["lip"] + .05 * f["bronze"] * f["impact_split"],
                                               .15 * f["cyan"] * f["lip"] + .12 * f["violet"] * f["impact_split"])), 0, 1)
    if not angle_b:
        return a, f
    # The armor plate stays fixed while its exposed fracture lip changes owner.
    b = a * .25 + np.dstack((.31 * f["violet"] + .18 * f["bronze"] + .08 * f["silver"],
                               .20 * f["cyan"] + .13 * f["silver"],
                               .62 * f["cyan"] + .43 * f["violet"] + .09 * f["lip"]))
    b += np.dstack((.03 * f["impact_split"], .06 * f["cross_scuff"], .12 * f["lip"]))
    return np.clip(b, 0, 1), f


def _material(f: dict[str, np.ndarray]) -> np.ndarray:
    metal = _norm(.39 * f["cyan"] + .32 * f["violet"] + .29 * f["bronze"] + .20 * f["silver"] + .16 * f["lip"])
    # SPB-105: these maps follow different physical evidence: exposed alloy,
    # the direction of abrasion, and deep plate clearcoat.  Do not reuse the
    # same edge map in all three merely to inflate their variance.
    directional_scuff = np.abs(np.sin(2 * np.pi * (f["abrasion_heading"] + .31 * f["plate_body"])))
    rough = _norm(.52 * f["cross_scuff"] + .28 * directional_scuff + .24 * f["impact_split"] - .17 * f["lip"])
    clear = _norm(.51 * f["plate_body"] + .26 * f["plate_gloss"] + .20 * f["hue"] + .18 * _norm(cv2.GaussianBlur(f["lip"], (0, 0), 11)) - .19 * f["cross_scuff"])
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
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "stag_carapace_livery_i3"), indent=2))
