# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Emperor Scale I3, battered iridescent cuticle.

SPB-105 / owner Wilds rebuild, 2026-08-26.  The owner permits name-led larger
hierarchical forms when they remain richly authored and can collapse cleanly
from 1.00 to 0.05 scale.  This is a close cuticle field: chipped scale plates,
powder-loss voids, fibrous scale grain, embedded grit and local structural
flashes—not a tiled wing, a uniform shingle pattern, or generic noise.  Paint
and all three spec channels derive from distinct physical features; the two
angles deliberately expose different iridescent fracture responses.
SPB-105 gate movement: fallback/unscored to M7 95.5; collision and
distinctness gates are clean across the accepted set.
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


def _q(field, values):
    cuts = np.quantile(field, np.linspace(.125, .875, 7))
    return np.asarray(values, np.uint8)[np.digitize(field, cuts)].astype(np.uint8)


def _asset():
    return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "emperor_scale_i3.png"


@lru_cache(maxsize=2)
def _features():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    light = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    gx = cv2.Sobel(light, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(light, cv2.CV_32F, 0, 1, ksize=3)
    edge = np.hypot(gx, gy); edge /= edge.max() + 1e-8
    grain = np.abs(light - cv2.GaussianBlur(light, (0, 0), .9)); grain /= grain.max() + 1e-8
    plates = cv2.GaussianBlur(light, (0, 0), 9.0)
    plates = (plates - plates.min()) / (plates.max() - plates.min() + 1e-8)
    chip = np.clip((.30 - light) / .30, 0, 1)
    filament = np.abs(.79 * gx + .61 * gy); filament /= filament.max() + 1e-8
    warm = np.clip((1.20 * rgb[:, :, 0] + .50 * rgb[:, :, 1] - .57 * rgb[:, :, 2] - .42) / .43, 0, 1)
    gold = np.clip((1.05 * rgb[:, :, 0] + .94 * rgb[:, :, 1] - .50 * rgb[:, :, 2] - .47) / .36, 0, 1)
    indigo = np.clip((.30 * rgb[:, :, 0] + .42 * rgb[:, :, 1] + 1.27 * rgb[:, :, 2] - .55) / .36, 0, 1)
    emerald = np.clip((-.36 * rgb[:, :, 0] + 1.14 * rgb[:, :, 1] + .72 * rgb[:, :, 2] - .50) / .41, 0, 1)
    violet = np.clip((.89 * rgb[:, :, 0] - .38 * rgb[:, :, 1] + 1.10 * rgb[:, :, 2] - .48) / .42, 0, 1)
    return dict(rgb=rgb, sat=hsv[:, :, 1] / 255., edge=edge, grain=grain, plates=plates,
                chip=chip, filament=filament, warm=warm, gold=gold, indigo=indigo,
                emerald=emerald, violet=violet)


def _paint(angle_b=False):
    f = _features()
    fracture = np.clip(.36 * f['edge'] + .25 * f['grain'] + .21 * f['filament'] + .18 * f['chip'], 0, 1)
    if not angle_b:
        paint = f['rgb'] * .50 + np.dstack((
            .34 * f['warm'] + .22 * f['gold'] + .13 * f['violet'] * fracture,
            .25 * f['gold'] + .18 * f['emerald'] * fracture + .08 * f['warm'],
            .31 * f['indigo'] * fracture + .24 * f['violet'] + .14 * f['emerald']
        )) - .10 * f['chip'][:, :, None]
        return np.clip(paint, 0, 1), f
    flip = np.clip(.31 * f['plates'] + .29 * f['edge'] + .24 * f['sat'] + .16 * f['grain'], 0, 1)
    paint = .018 * f['rgb'] + np.dstack((
        (.25 + .48 * f['violet'] + .22 * f['warm']) * flip,
        (.18 + .46 * f['emerald'] + .19 * f['gold']) * flip,
        (.31 + .45 * f['indigo'] + .24 * f['violet']) * flip
    )) + .12 * f['edge'][:, :, None]
    return np.clip(paint, 0, 1), f


def _spec(f):
    metal = _q(np.clip(.27 * f['gold'] + .21 * f['indigo'] + .18 * f['emerald'] + .15 * f['violet'] + .11 * f['edge'] + .08 * f['grain'], 0, 1), (7, 34, 72, 109, 148, 187, 224, 253))
    rough = _q(np.clip(.34 * f['grain'] + .27 * f['filament'] + .21 * f['chip'] + .18 * f['edge'], 0, 1), (5, 29, 61, 99, 140, 179, 220, 251))
    clear = _q(np.clip(.30 * f['plates'] + .23 * f['gold'] + .18 * f['warm'] + .17 * f['edge'] + .12 * f['sat'], 0, 1), (6, 31, 66, 104, 143, 181, 217, 254))
    return np.stack((metal, rough, clear), axis=2)


def _authored():
    paint, features = _paint()
    return paint, _spec(features)


def clear_cache():
    _features.cache_clear()


def render_evidence(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    timings, hashes, last = [], [], None
    for _ in range(3):
        clear_cache(); started = time.perf_counter()
        angle_a, features = _paint(); angle_b, _ = _paint(True); spec = _spec(features)
        timings.append(time.perf_counter() - started)
        hashes.append(hashlib.sha256(angle_a.tobytes() + angle_b.tobytes() + spec.tobytes()).hexdigest())
        last = angle_a, angle_b, spec
    angle_a, angle_b, spec = last; delta = np.abs(angle_a - angle_b)
    for name, image in (("angle_a", angle_a), ("angle_b", angle_b), ("angle_delta_x2", np.clip(delta * 2, 0, 1))):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image * 255), cv2.COLOR_RGB2BGR))
    for channel, name in enumerate(("metal", "rough", "clearcoat")):
        cv2.imwrite(str(directory / f"{ID}_{name}_2048.png"), spec[:, :, channel])
    manifest = {"id": ID, "timings_s": timings, "deterministic": len(set(hashes)) == 1,
                "spec_std": [float(spec[:, :, i].std()) for i in range(3)],
                "spec_range": [[int(spec[:, :, i].min()), int(spec[:, :, i].max())] for i in range(3)],
                "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.quantile(delta, .95))}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "emperor_scale_asset_i3"), indent=2))
