# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Coarse Hide I3, armored hide-lacquer candidate.

SPB-105 / owner doctrine tick 2026-08-27. I2 is photographed gravel: a
grainy aggregate close-up rather than a race-car finish. I3 instead treats
"coarse hide" as engineered fractured armor—unequal black lacquer plates,
inner scuff hatching, copper break seams and cyan/violet foil cavities. Its
coarse outer armor is deliberately hierarchy, while its actual surface detail
is carried by fine 8–32px cracks, abrasion and inlay cuts. Material tracks are
derived separately from foil chemistry, abrasion relief and plate tension; no
random filler, shared Wilds composer or tile-frame rescue is used.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np

ID = "fc_coarse_hide"
NATIVE = 2048
M_T = np.asarray((7, 29, 56, 88, 123, 163, 207, 251), np.uint8)
R_T = np.asarray((13, 39, 68, 102, 140, 181, 219, 248), np.uint8)
C_T = np.asarray((5, 26, 54, 84, 120, 159, 207, 252), np.uint8)


def _norm(value):
    value = value.astype(np.float32)
    return (value - value.min()) / (value.max() - value.min() + 1e-8)


def _tier(value, levels):
    cuts = np.quantile(value, np.linspace(.125, .875, 7))
    return levels[np.digitize(value, cuts)].astype(np.uint8)


def _asset():
    return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "coarse_hide_livery_i3.png"


@lru_cache(maxsize=2)
def _fields():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    sat = hsv[:, :, 1] / 255.0
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    seam = _norm(np.hypot(gx, gy))
    scuff = _norm(np.abs(cv2.GaussianBlur(lum, (0, 0), 1.15) - cv2.GaussianBlur(lum, (0, 0), 4.2)))
    plate = _norm(cv2.GaussianBlur(lum, (0, 0), 17.0))
    pgx = cv2.Sobel(plate, cv2.CV_32F, 1, 0, ksize=3)
    pgy = cv2.Sobel(plate, cv2.CV_32F, 0, 1, ksize=3)
    heading = (np.arctan2(pgy, pgx) + np.pi) / (2 * np.pi)
    tension = _norm(np.hypot(pgx, pgy))
    diagonal = _norm(np.abs(.72 * gx - .69 * gy))
    cyan = np.clip((rgb[:, :, 2] + .50 * rgb[:, :, 1] - 1.08 * rgb[:, :, 0] - .08) / .42, 0, 1)
    violet = np.clip((rgb[:, :, 2] + .26 * rgb[:, :, 0] - 1.12 * rgb[:, :, 1] - .08) / .38, 0, 1)
    copper = np.clip((rgb[:, :, 0] + .38 * rgb[:, :, 1] - 1.10 * rgb[:, :, 2] - .11) / .38, 0, 1)
    foil = _norm(.72 * cyan + .54 * violet + .42 * copper + .18 * seam)
    return {"rgb": rgb, "lum": lum, "sat": sat, "seam": seam, "scuff": scuff, "plate": plate, "heading": heading, "tension": tension, "diagonal": diagonal, "cyan": cyan, "violet": violet, "copper": copper, "foil": foil}


def _paint(angle_b=False):
    f = _fields()
    angle_a = np.clip(f["rgb"] * .80 + np.dstack((.11 * f["copper"] + .04 * f["violet"], .06 * f["copper"] + .08 * f["cyan"], .14 * f["cyan"] + .11 * f["violet"])), 0, 1)
    if not angle_b:
        return angle_a, f
    # Color flip is constrained to the foil cavities and cut edges; the black
    # armor stays structurally stable between angles instead of simply recoloring.
    angle_b = angle_a * .24 + np.dstack((.18 * f["copper"] + .34 * f["violet"], .13 * f["cyan"] + .15 * f["copper"], .63 * f["cyan"] + .52 * f["violet"] + .11 * f["seam"]))
    return np.clip(angle_b, 0, 1), f


def _material(f):
    metal = _norm(.58 * f["foil"] + .25 * f["cyan"] + .22 * f["copper"] + .16 * _norm(cv2.GaussianBlur(f["foil"], (0, 0), 6.0)))
    rough = _norm(.50 * f["scuff"] + .31 * f["diagonal"] + .24 * f["seam"] + .17 * _norm(cv2.GaussianBlur(f["scuff"], (0, 0), 4.0)))
    clearcoat = _norm(.53 * f["heading"] + .28 * f["tension"] + .22 * f["plate"] - .18 * f["scuff"] + .15 * _norm(cv2.GaussianBlur(f["tension"], (0, 0), 13.0)))
    return np.stack((_tier(metal, M_T), _tier(rough, R_T), _tier(clearcoat, C_T)), axis=2)


def _authored():
    paint, fields = _paint(False)
    return paint, _material(fields)


def clear_cache():
    _fields.cache_clear()


def render_evidence(directory):
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
    delta = np.abs(angle_a - angle_b)
    for name, image in (("angle_a", angle_a), ("angle_b", angle_b), ("angle_delta_x2", np.clip(delta * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for index, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, index])
    correlation = np.corrcoef(spec.reshape(-1, 3).astype(np.float32), rowvar=False)
    report = {"id": ID, "timings_s": timings, "deterministic": len(set(hashes)) == 1, "spec_std": [float(spec[:, :, index].std()) for index in range(3)], "spec_range": [[int(spec[:, :, index].min()), int(spec[:, :, index].max())] for index in range(3)], "spec_corr_m_r_cc": [float(correlation[0, 1]), float(correlation[0, 2]), float(correlation[1, 2])], "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95))}
    (directory / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    return report


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "coarse_hide_livery_i3"), indent=2))
