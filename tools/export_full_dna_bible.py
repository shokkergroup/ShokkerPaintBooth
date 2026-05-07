#!/usr/bin/env python3
"""Headless full-catalog Finish DNA exporter.

This intentionally uses the same live Python registry/render path as the
Finish Viewer API, then emits a browser-compatible DNA Bible package under
docs/DNA_FINISH_EXPORTS/<timestamp>_full-catalog/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DNA_SCHEMA_VERSION = 2.1
EXPORT_SCHEMA_VERSION = "1.1"
CHANNEL_MAP = {
    "profile": "SPB/iRacing packed spec bytes",
    "line": "Ch0=Metallic (R), Ch1=Roughness (G), Ch2=Clearcoat (B)",
    "clearcoatRule": "Ch2 raw 0-15 disables clearcoat; Ch2 raw 16 is maximum clearcoat gloss; values above 16 progressively reduce clearcoat gloss.",
    "byteValueRule": "Prescriptions apply to packed byte values post-decode, same as renderer.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_slug(text: str) -> str:
    out = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in str(text or ""))
    return out.strip("._") or "unknown"


def sha256_short(paths: list[Path]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        try:
            data = path.read_bytes()
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()[:16]
        except Exception:
            continue
    return hashes


def finite(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, finite(value)))


def percentile(values: np.ndarray, q: float) -> float:
    if values.size == 0:
        return 0.0
    return float(np.percentile(values, q * 100.0))


def clearcoat_gloss01(raw_c: np.ndarray | float) -> np.ndarray | float:
    return np.where(np.asarray(raw_c) < 16, 0.0, np.clip((255.0 - np.asarray(raw_c)) / 239.0, 0.0, 1.0))


def spec_potential01(m: np.ndarray, r: np.ndarray, c: np.ndarray) -> np.ndarray:
    smooth = 1.0 - r / 255.0
    return np.maximum((m / 255.0) * smooth, clearcoat_gloss01(c) * smooth * 0.68)


def is_true_void(m: np.ndarray, r: np.ndarray, c: np.ndarray) -> np.ndarray:
    return (m < 12) & (r > 220) & (c < 16)


def is_flare(m: np.ndarray, r: np.ndarray, c: np.ndarray) -> np.ndarray:
    return (m > 160) & (r < 85) & (c < 115)


def is_chrome(m: np.ndarray, r: np.ndarray, c: np.ndarray) -> np.ndarray:
    return (m > 220) & (r < 45) & (c < 70)


def normalize_paint_spec(paint_arr: Any, spec_arr: Any) -> tuple[np.ndarray, np.ndarray]:
    paint = np.asarray(paint_arr)
    spec = np.asarray(spec_arr)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3]
    if paint.dtype != np.uint8:
        paint = np.clip(paint[:, :, :3], 0, 1) * 255 if float(np.nanmax(paint)) <= 1.5 else np.clip(paint[:, :, :3], 0, 255)
        paint = paint.astype(np.uint8)
    if spec.ndim == 3 and spec.shape[2] > 4:
        spec = spec[:, :, :4]
    if spec.dtype != np.uint8:
        spec = np.clip(spec, 0, 255).astype(np.uint8)
    if spec.ndim == 2:
        spec = np.dstack([spec, spec, spec, np.full_like(spec, 255)])
    if spec.shape[2] == 3:
        spec = np.dstack([spec, np.full(spec.shape[:2], 255, dtype=np.uint8)])
    return paint[:, :, :3], spec[:, :, :4]


def material_verdict(metrics: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    tune: list[str] = []
    sim_score = finite(metrics.get("simFlashScore"), 100)
    if metrics["livingScore"] < 45:
        blockers.append("living score low")
    elif metrics["livingScore"] < 68:
        tune.append("raise living score")
    if metrics["pinFlashScore"] < 34:
        blockers.append("pin flash weak")
    elif metrics["pinFlashScore"] < 58:
        tune.append("sharpen pin flash")
    if metrics["angleSpreadScore"] < 34:
        blockers.append("angle spread dead")
    elif metrics["angleSpreadScore"] < 54:
        tune.append("improve angle spread")
    if sim_score < 34:
        blockers.append("sim flash dead")
    elif sim_score < 54:
        tune.append("improve sim flash")
    if metrics["darkPaintPct"] > 8 and metrics["darkGlossPct"] > 30:
        blockers.append("dark gloss leak")
    elif metrics["darkPaintPct"] > 8 and metrics["darkGlossPct"] > 18:
        tune.append("flatten dark floor")
    if metrics["darkPaintPct"] > 8 and metrics["darkVoidPct"] < 50:
        blockers.append("void floor weak")
    elif metrics["darkPaintPct"] > 8 and metrics["darkVoidPct"] < 65:
        tune.append("strengthen void floor")
    if metrics["sparkleHotPct"] > 5.2:
        tune.append("hot dots broad")
    if metrics["sparkleMidPct"] > 18:
        tune.append("glow too broad")
    if metrics["detail"] < 14:
        tune.append("low fine detail")

    if blockers:
        grade = "D" if metrics["livingScore"] < 35 or len(blockers) > 1 else "C"
        label = "Rework"
        tone = "bad"
    elif tune:
        grade = "B" if metrics["livingScore"] >= 70 and metrics["pinFlashScore"] >= 52 and metrics["angleSpreadScore"] >= 48 and sim_score >= 48 else "C"
        label = "Promising" if grade == "B" else "Tune"
        tone = "watch" if grade == "B" else "warn"
    elif metrics["livingScore"] < 78 or metrics["pinFlashScore"] < 65 or metrics["angleSpreadScore"] < 62 or sim_score < 62:
        grade = "B"
        label = "Strong"
        tone = "watch"
    else:
        grade = "A"
        label = "Ready"
        tone = "good"
    return {
        "grade": grade,
        "label": label,
        "tone": tone,
        "blockers": blockers,
        "tune": tune,
        "text": f"{grade} {label}" + (f" - {'; '.join(blockers or tune)}" if blockers or tune else ""),
    }


def preview_luma_model() -> dict[str, Any]:
    return {
        "colorSpace": "sRGB byte paint data",
        "decode": "byte values are sampled from rendered preview arrays; no additional gamma conversion is applied before dark-mask math",
        "luma": "Rec.709 coefficients on preview bytes: 0.2126*R + 0.7152*G + 0.0722*B",
        "darkCutoff": 34,
        "resizeKernel": "offline renderer output at analysisTextureSize; no browser canvas resize in CLI",
        "bitDepth": "8-bit packed byte values",
        "specPipeline": CHANNEL_MAP["byteValueRule"],
    }


def dark_mask_hash(paint: np.ndarray) -> dict[str, Any]:
    cells = 32
    h, w = paint.shape[:2]
    bits: list[str] = []
    dark = 0
    for y in range(cells):
        sy = min(h - 1, int((y + 0.5) / cells * h))
        for x in range(cells):
            sx = min(w - 1, int((x + 0.5) / cells * w))
            r, g, b = paint[sy, sx, :3].astype(float)
            bit = (r * 0.2126 + g * 0.7152 + b * 0.0722) < 34
            bits.append("1" if bit else "0")
            dark += 1 if bit else 0
    digest = hashlib.sha1("".join(bits).encode("ascii")).hexdigest()[:16]
    return {"cells": cells, "darkCells": dark, "hash": digest}


def synthetic_angle_and_sim_scores(metrics: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    # Offline approximation of the viewer's light sweeps. It intentionally uses
    # the same map-derived flash potential and range inputs, but avoids browser
    # shader dependencies so CI/nightly exports are deterministic.
    base_peak = max(0.001, metrics["p995"] * 0.56 + metrics["p999"] * 0.44)
    range_factor = clamp(metrics["rangeScore"], 0, 100) / 100.0
    detail_factor = clamp(metrics["detail"], 0, 100) / 100.0
    balance = max(0.04, min(1.0, (metrics["p90"] + 0.015) / max(0.025, metrics["p995"])))
    active = int(round(max(1, min(5, 1 + range_factor * 2.2 + detail_factor * 1.4 + (1 - balance) * 0.8))))
    angle_score = clamp(active / 5 * 78 + balance * 22)
    angle_peaks = [
        {"label": label, "value": base_peak * mult, "pct": min(100, mult * 100), "active": mult >= 0.56}
        for label, mult in [("front-left", 1.00), ("front-right", 0.86), ("side-sweep", 0.72), ("rear-left", 0.63), ("rear-right", max(0.30, balance))]
    ]
    sim_multipliers = [
        ("Full Sun", "full_sun", 0.72),
        ("Partly Cloudy", "partly_cloudy", 0.64),
        ("Mostly Cloudy", "mostly_cloudy", 0.56),
        ("Cloudy", "cloudy", 0.48),
        ("Low Sun", "low_sun", 1.00),
        ("Night Lights", "night", 0.92),
    ]
    sim_peaks = [{"label": label, "key": key, "value": base_peak * mult, "pct": min(100, mult * 100), "active": mult >= 0.56} for label, key, mult in sim_multipliers]
    diffuse_max = max(item["value"] for item in sim_peaks[:4])
    peak = max(item["value"] for item in sim_peaks)
    diffuse_deadband = diffuse_max < peak * 0.52
    sim_active = sum(1 for item in sim_peaks if item["active"])
    sim_balance = min(item["value"] for item in sim_peaks) / max(peak, 0.0001)
    sim_score = clamp(sim_active / len(sim_peaks) * 76 + sim_balance * 24 - (9 if diffuse_deadband else 0))
    return (
        {
            "score": angle_score,
            "active": active,
            "total": 5,
            "balance": balance,
            "best": angle_peaks[0]["label"],
            "weakest": min(angle_peaks, key=lambda item: item["value"])["label"],
            "peaks": angle_peaks,
            "normalized": angle_peaks,
            "proofTarget": "synthetic / uncaptured",
        },
        {
            "score": sim_score,
            "active": sim_active,
            "total": len(sim_peaks),
            "balance": sim_balance,
            "best": max(sim_peaks, key=lambda item: item["value"])["label"],
            "weakest": min(sim_peaks, key=lambda item: item["value"])["label"],
            "peaks": sim_peaks,
            "normalized": sim_peaks,
            "diffuseDeadband": diffuse_deadband,
            "proofTarget": "synthetic / uncaptured",
        },
    )


def compute_diagnostics(paint_arr: Any, spec_arr: Any) -> dict[str, Any]:
    paint, spec = normalize_paint_spec(paint_arr, spec_arr)
    m = spec[:, :, 0].astype(np.float32)
    r = spec[:, :, 1].astype(np.float32)
    c = spec[:, :, 2].astype(np.float32)
    total = int(m.size)
    luma = paint[:, :, 0].astype(np.float32) * 0.2126 + paint[:, :, 1].astype(np.float32) * 0.7152 + paint[:, :, 2].astype(np.float32) * 0.0722
    potentials = spec_potential01(m, r, c).reshape(-1)

    true_void = is_true_void(m, r, c)
    flare = is_flare(m, r, c)
    chrome = is_chrome(m, r, c)
    dark = luma < 34
    cc_gloss = clearcoat_gloss01(c)
    dark_gloss = dark & ((m > 18) | (r < 205) | (cc_gloss > 0.06))

    edge_m = np.abs(m[::3, :-1:3] - m[::3, 1::3])
    edge_r = np.abs(r[::3, :-1:3] - r[::3, 1::3])
    edge_c = np.abs(c[::3, :-1:3] - c[::3, 1::3])
    edge_m2 = np.abs(m[:-1:3, ::3] - m[1::3, ::3])
    edge_r2 = np.abs(r[:-1:3, ::3] - r[1::3, ::3])
    edge_c2 = np.abs(c[:-1:3, ::3] - c[1::3, ::3])
    edge_total = float(edge_m.sum() + edge_r.sum() + edge_c.sum() + edge_m2.sum() + edge_r2.sum() + edge_c2.sum())
    edge_samples = max(1, edge_m.size * 3 + edge_m2.size * 3)
    detail = min(100.0, edge_total / edge_samples * 2.4)

    min_m, max_m = int(m.min()), int(m.max())
    min_r, max_r = int(r.min()), int(r.max())
    min_c, max_c = int(c.min()), int(c.max())
    p50, p90, p995, p999 = [percentile(potentials, q) for q in (0.50, 0.90, 0.995, 0.999)]
    twinkle = p995 / p50 if p50 > 0 else p995 * 100
    range_score = ((max_m - min_m) + (max_r - min_r) + (max_c - min_c)) / 765.0 * 100.0
    flare_pct = float(flare.mean() * 100.0)
    chrome_pct = float(chrome.mean() * 100.0)
    void_pct = float(true_void.mean() * 100.0)
    dark_paint_pct = float(dark.mean() * 100.0)
    dark_count = int(dark.sum())
    dark_gloss_pct = float(dark_gloss.sum() / dark_count * 100.0) if dark_count else 0.0
    dark_void_pct = float((dark & true_void).sum() / dark_count * 100.0) if dark_count else 0.0
    sparkle_hot_pct = float((potentials > 0.58).mean() * 100.0)
    sparkle_mid_pct = float((potentials > 0.26).mean() * 100.0)
    material_buckets = {
        "trueVoidPct": void_pct,
        "hotPinPct": sparkle_hot_pct,
        "midGlowPct": max(0.0, sparkle_mid_pct - sparkle_hot_pct),
        "chromePct": chrome_pct,
        "flarePct": flare_pct,
        "darkGlossLeakPct": float(dark_gloss.sum() / total * 100.0),
        "darkVoidPct": dark_void_pct,
    }
    pin_contrast = p999 / max(0.005, p90)
    contrast_score = min(100.0, pin_contrast * 8.0)
    rarity_score = sparkle_hot_pct * 1200.0 if sparkle_hot_pct < 0.05 else 100.0 if sparkle_hot_pct <= 3.2 else max(0.0, 100.0 - (sparkle_hot_pct - 3.2) * 16.0)
    narrow_score = 100.0 if sparkle_mid_pct <= 8 else max(0.0, 100.0 - (sparkle_mid_pct - 8.0) * 7.0)
    pin_flash_score = clamp(contrast_score * 0.50 + rarity_score * 0.30 + narrow_score * 0.20)
    prelim = {"p90": p90, "p995": p995, "p999": p999, "rangeScore": range_score, "detail": detail}
    angle_spread, sim_flash = synthetic_angle_and_sim_scores(prelim)
    angle_score = finite(angle_spread.get("score"))
    sim_score = finite(sim_flash.get("score"))
    living_score = clamp(
        range_score * 0.30
        + min(100.0, twinkle * 3.2) * 0.30
        + min(100.0, detail) * 0.22
        + min(100.0, flare_pct * 10.0) * 0.12
        + min(100.0, chrome_pct * 18.0) * 0.08
        + angle_score * 0.04
        - max(0.0, void_pct - 72.0) * 0.45
    )
    metrics = {
        "minM": min_m,
        "maxM": max_m,
        "minR": min_r,
        "maxR": max_r,
        "minC": min_c,
        "maxC": max_c,
        "mRange": max_m - min_m,
        "rRange": max_r - min_r,
        "ccRange": max_c - min_c,
        "voidCount": int(true_void.sum()),
        "flareCount": int(flare.sum()),
        "chromeCount": int(chrome.sum()),
        "darkPaintCount": dark_count,
        "darkGlossCount": int(dark_gloss.sum()),
        "darkVoidCount": int((dark & true_void).sum()),
        "sparkleHotCount": int((potentials > 0.58).sum()),
        "sparkleMidCount": int((potentials > 0.26).sum()),
        "total": total,
        "twinkle": twinkle,
        "detail": detail,
        "livingScore": living_score,
        "darkPaintPct": dark_paint_pct,
        "darkGlossPct": dark_gloss_pct,
        "darkVoidPct": dark_void_pct,
        "sparkleHotPct": sparkle_hot_pct,
        "sparkleMidPct": sparkle_mid_pct,
        "materialBuckets": material_buckets,
        "pinContrast": pin_contrast,
        "pinFlashScore": pin_flash_score,
        "angleSpreadScore": angle_score,
        "angleSpread": angle_spread,
        "simFlashScore": sim_score,
        "simFlash": sim_flash,
        "p50": p50,
        "p90": p90,
        "p995": p995,
        "p999": p999,
        "rangeScore": range_score,
        "previewLumaModel": preview_luma_model(),
        "darkPaintMaskPreview": dark_mask_hash(paint),
    }
    alerts = []
    if dark_paint_pct > 8 and dark_gloss_pct > 18:
        alerts.append(f"dark spec leak {dark_gloss_pct:.0f}%")
    if dark_paint_pct > 8 and dark_void_pct < 65:
        alerts.append(f"void floor weak {dark_void_pct:.0f}%")
    if range_score < 18:
        alerts.append("low spec range")
    if twinkle < 2.2 and flare_pct < 0.4:
        alerts.append("weak twinkle contrast")
    if flare_pct > 18:
        alerts.append("flash may be overbroad")
    if pin_flash_score < 42:
        alerts.append(f"pin flash weak {pin_flash_score:.0f}")
    if sparkle_mid_pct > 15:
        alerts.append(f"sparkle too broad {sparkle_mid_pct:.0f}%")
    if sparkle_hot_pct > 4:
        alerts.append(f"sparkle dots too large {sparkle_hot_pct:.1f}%")
    if angle_score < 46:
        alerts.append(f"angle spread weak {angle_score:.0f}")
    if sim_score < 46:
        alerts.append(f"sim flash weak {sim_score:.0f}")
    metrics["alertText"] = " | ".join(alerts) if alerts else "OK"
    metrics["hints"] = alerts[:3]
    metrics["hintText"] = " | ".join(alerts[:3]) if alerts else "No critical material fixes suggested"
    metrics["verdict"] = material_verdict(metrics)
    return metrics


def finish_tokens(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(k, "")) for k in ("id", "name", "category", "group", "type")).lower()


def finish_flash_mode(row: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    text = finish_tokens(row)
    hero_words = any(word in text for word in ("wave", "flame", "haze", "oil", "water", "lake", "neon", "electric", "pulse", "ripple"))
    pin_words = any(word in text for word in ("flake", "twinkle", "star", "spark", "led", "dot", "pin"))
    buckets = diagnostics.get("materialBuckets", {})
    hot = finite(buckets.get("hotPinPct"))
    mid = finite(buckets.get("midGlowPct"))
    living = finite(diagnostics.get("livingScore"))
    pin = finite(diagnostics.get("pinFlashScore"))
    if pin_words and not hero_words:
        mode = "pinfield"
    elif hero_words and not pin_words:
        mode = "heroBand"
    elif hero_words and (hot > 4 or mid > 18 or living - pin > 28):
        mode = "heroBand"
    else:
        mode = "mixed"
    return {
        "mode": mode,
        "evidence": f"tokens hero={'yes' if hero_words else 'no'} pin={'yes' if pin_words else 'no'} | hotPinPct {hot:.2f}% | midGlowPct {mid:.1f}% | living-pin delta {(living - pin):.0f}",
    }


def finish_dna_report(row: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    m_range, r_range, c_range = [finite(diagnostics.get(k)) for k in ("mRange", "rRange", "ccRange")]
    range_score = clamp((m_range + r_range + c_range) / 3.0 / 2.2)
    detail_score = clamp(finite(diagnostics.get("detail")) * 2.8)
    living = clamp(finite(diagnostics.get("livingScore")))
    pin = clamp(finite(diagnostics.get("pinFlashScore")))
    sim = clamp(finite(diagnostics.get("simFlashScore")))
    angle = clamp(finite(diagnostics.get("angleSpreadScore")))
    score = round(clamp(living * 0.24 + pin * 0.18 + sim * 0.20 + angle * 0.12 + detail_score * 0.13 + range_score * 0.13))
    label = "Elite" if score >= 86 else "Strong" if score >= 74 else "Promising" if score >= 62 else "Rework"
    flash_mode = finish_flash_mode(row, diagnostics)
    hero_band = flash_mode["mode"] == "heroBand"
    buckets = diagnostics.get("materialBuckets", {})
    target_metrics = {
        "livingScore": max(74, round(living + 18)),
        "pinFlashScore": max(38 if hero_band else 58, round(pin + (12 if hero_band else 22))),
        "simFlashScore": max(62, round(sim + 26)),
        "detail": max(24, round(finite(diagnostics.get("detail")) + 10)),
        "crestSharpnessProxy": max(62, round(detail_score * 0.45 + angle * 0.35 + range_score * 0.20 + 10)) if hero_band else None,
        "mRange": max(150, round(m_range)),
        "rRange": max(150, round(r_range)),
        "ccRange": max(80, round(c_range)),
        "midGlowPctMax": 24,
        "hotPinPctMax": 14 if hero_band else 5.5 if any(w in finish_tokens(row) for w in ("twinkle", "star", "spark", "led")) else 9,
        "darkGlossPctMax": 14,
        "darkVoidPctMin": 65,
    }
    strengths: list[str] = []
    weaknesses: list[str] = []
    repair_recipe: list[str] = []
    repair_tasks: list[dict[str, Any]] = []
    agent_plan: list[dict[str, Any]] = []
    if living >= 72:
        strengths.append(f"Living response is visible ({living:.0f}/100).")
    if range_score >= 60:
        strengths.append(f"Spec channels have meaningful spread (range score {range_score:.0f}).")
    if finite(diagnostics.get("darkVoidPct")) >= 65:
        strengths.append(f"Dark floor has a believable void component ({finite(diagnostics.get('darkVoidPct')):.1f}%).")
    if range_score < 60:
        weaknesses.append("Spec map channel range is too narrow; finish may read flat.")
        repair_recipe.append("Widen Ch0/Ch1/Ch2 with true lows, true highs, and fine broken transitions.")
        task = {
            "priority": 1,
            "operation": "widen-packed-spec-range",
            "target": "Widen packed spec range without changing channel semantics.",
            "channelRecipe": "Introduce low Ch0/high Ch1/low Ch2 voids and localized high Ch0/low Ch1/Ch2=16 flash islands.",
        }
        agent_plan.append(task)
        repair_tasks.append({"id": task["operation"], "metric": "diagnostics.mRange/diagnostics.rRange/diagnostics.ccRange", "current": {"mRange": round(m_range), "rRange": round(r_range), "ccRange": round(c_range)}, "target": {"mRange": target_metrics["mRange"], "rRange": target_metrics["rRange"], "ccRange": target_metrics["ccRange"]}, "verify": "Regenerate DNA and confirm ranges widen while gradeContext.hardBlockers does not grow."})
    if pin < 55:
        weaknesses.append(f"Pin flash is weak ({pin:.0f}/100)." if not hero_band else f"Pin metric is weak ({pin:.0f}/100), but hero-band intent may still be visually valid.")
        repair_recipe.append("Sharpen hero crests and protected bright cores." if hero_band else "Add tiny separated hot-pin cores over flatter rough/void surroundings.")
        task = {
            "priority": 2,
            "operation": "sharpen-flash-islands",
            "target": f"Pin flash {target_metrics['pinFlashScore']}+ with controlled hot/mid glow.",
            "channelRecipe": "Shrink broad glow, add tiny bright centers, and surround them with rough or void pixels.",
        }
        agent_plan.append(task)
        repair_tasks.append({"id": task["operation"], "metric": "diagnostics.pinFlashScore/diagnostics.materialBuckets.hotPinPct/diagnostics.materialBuckets.midGlowPct", "current": {"pinFlashScore": round(pin), "hotPinPct": finite(buckets.get("hotPinPct")), "midGlowPct": finite(buckets.get("midGlowPct"))}, "target": {"pinFlashScore": target_metrics["pinFlashScore"], "hotPinPctMax": target_metrics["hotPinPctMax"], "midGlowPctMax": target_metrics["midGlowPctMax"]}, "verify": "Regenerate and confirm pinFlashScore or hero crest proxy improves without erasing intended identity."})
    if sim < 58:
        weaknesses.append(f"Practical sim-light response is weak ({sim:.0f}/100).")
        repair_recipe.append("Strengthen diffuse/normal lighting response, not only Low Sun/Night hero flash.")
        task = {"priority": 3, "operation": "raise-practical-sim-flash", "target": f"Sim flash {target_metrics['simFlashScore']}+", "channelRecipe": "Add small metallic/clearcoat micro-islands in mid and dark paint zones for full-sun/cloudy visibility."}
        agent_plan.append(task)
        repair_tasks.append({"id": task["operation"], "metric": "diagnostics.simFlashScore", "current": round(sim), "target": target_metrics["simFlashScore"], "verify": "Regenerate and confirm synthetic simFlashScore rises; proof captures remain synthetic until image-backed captures exist."})
    if finite(diagnostics.get("darkGlossPct")) > target_metrics["darkGlossPctMax"] or finite(diagnostics.get("darkVoidPct")) < target_metrics["darkVoidPctMin"]:
        weaknesses.append(f"Dark floor leak: gloss {finite(diagnostics.get('darkGlossPct')):.1f}% / void {finite(diagnostics.get('darkVoidPct')):.1f}%.")
        repair_recipe.append("Flatten dark-background spec toward Ch0<12, Ch1>220, Ch2<16, protecting intentional flash corridors.")
        task = {"priority": 4, "operation": "flatten-dark-void-floor", "target": "Dark gloss below 14% and dark void above 65%.", "channelRecipe": "Apply void rules to dark floor/deepest quantile, not protected highlight islands."}
        agent_plan.append(task)
        repair_tasks.append({"id": task["operation"], "metric": "diagnostics.darkGlossPct/diagnostics.darkVoidPct", "current": {"darkGlossPct": finite(diagnostics.get("darkGlossPct")), "darkVoidPct": finite(diagnostics.get("darkVoidPct"))}, "target": {"darkGlossPctMax": 14, "darkVoidPctMin": 65}, "verify": "Regenerate and confirm darkGlossPct falls and darkVoidPct rises without deleting hero flashes."})
    if detail_score < 58:
        weaknesses.append("Fine detail is too low; finish risks reading lazy or smooth.")
        repair_recipe.append("Add multiscale hairline channel texture and sub-dot details inside bright marks.")
    if not repair_recipe:
        repair_recipe.append("Polish rather than rebuild: preserve balance and add localized channel variation.")
    metric_tension = {
        "active": (hero_band and (living >= 68 or angle >= 58) and pin < 35) or (hero_band and finite(buckets.get("hotPinPct")) > 4),
        "note": "Hero-band visual intent may score weak pins; preserve visible streak/corridor before forcing pin metrics." if hero_band else "No major visual-vs-diagnostic conflict detected.",
        "fields": {"livingScore": round(living), "angleSpreadScore": round(angle), "pinFlashScore": round(pin), "hotPinPct": round(finite(buckets.get("hotPinPct")), 2), "finishFlashMode": flash_mode["mode"]},
    }
    grade_context = {
        "materialGrade": diagnostics.get("verdict", {}).get("grade", "--"),
        "effectiveLabel": diagnostics.get("verdict", {}).get("label", "--"),
        "hardBlockers": diagnostics.get("verdict", {}).get("blockers", []),
        "advisoryBlockers": diagnostics.get("verdict", {}).get("tune", []),
        "thresholds": {
            "reworkBlockers": ["livingScore < 45", "pinFlashScore < 34", "angleSpreadScore < 34", "simFlashScore < 34", "darkPaintPct > 8 and darkGlossPct > 30", "darkPaintPct > 8 and darkVoidPct < 50"],
            "strongBMinimums": "B/Strong wants livingScore >= 78, pinFlashScore >= 65, angleSpreadScore >= 62, simFlashScore >= 62 with no blocker/tune flags.",
        },
    }
    return {
        "version": DNA_SCHEMA_VERSION,
        "dnaSchemaVersion": DNA_SCHEMA_VERSION,
        "rendererProfile": {"shaderBuild": "offline-python-exporter", "channelMapProfile": CHANNEL_MAP["profile"]},
        "channelMap": CHANNEL_MAP,
        "score": score,
        "label": label,
        "summary": f"{row.get('name') or row.get('id')} DNA {score}/100 - {label}.",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "repairRecipe": repair_recipe[:8],
        "agentRepairPlan": sorted(agent_plan, key=lambda item: item["priority"])[:8],
        "repair_tasks": repair_tasks,
        "targetMetrics": target_metrics,
        "finishFlashMode": flash_mode,
        "metricTension": metric_tension,
        "gradeContext": grade_context,
    }


def compact_record(row: dict[str, Any], diagnostics: dict[str, Any], dna: dict[str, Any]) -> dict[str, Any]:
    grade = dna.get("gradeContext", {}).get("materialGrade") or diagnostics.get("verdict", {}).get("grade", "--")
    return {
        "id": row["id"],
        "name": row.get("name") or row["id"],
        "type": row.get("renderType") or row.get("type"),
        "group": row.get("bibleGroupLabel") or row.get("category") or row.get("type"),
        "category": row.get("category") or "",
        "dnaScore": int(dna.get("score", 0)),
        "dnaLabel": dna.get("label", "No DNA"),
        "grade": grade,
        "effectiveGrade": dna.get("gradeContext", {}).get("effectiveLabel", ""),
        "flashMode": dna.get("finishFlashMode", {}).get("mode", ""),
        "metricTension": bool(dna.get("metricTension", {}).get("active")),
        "livingScore": round(finite(diagnostics.get("livingScore"))),
        "pinFlashScore": round(finite(diagnostics.get("pinFlashScore"))),
        "simFlashScore": round(finite(diagnostics.get("simFlashScore"))),
        "angleSpreadScore": round(finite(diagnostics.get("angleSpreadScore"))),
        "detail": round(finite(diagnostics.get("detail"))),
        "mRange": round(finite(diagnostics.get("mRange"))),
        "rRange": round(finite(diagnostics.get("rRange"))),
        "ccRange": round(finite(diagnostics.get("ccRange"))),
        "darkGlossPct": round(finite(diagnostics.get("darkGlossPct")), 1),
        "darkVoidPct": round(finite(diagnostics.get("darkVoidPct")), 1),
        "renderTypeUsed": row.get("renderTypeUsed") or row.get("renderType") or row.get("type"),
        "topWeakness": (dna.get("weaknesses") or [""])[0],
        "firstRepair": (dna.get("repair_tasks") or [{}])[0].get("id", "") if dna.get("repair_tasks") else "",
        "proofTarget": "synthetic / uncaptured",
    }


def priority_signals(row: dict[str, Any]) -> list[dict[str, Any]]:
    signals = []
    grade_text = f"{row.get('effectiveGrade','')} {row.get('grade','')}".lower()
    if finite(row.get("dnaScore")) < 58:
        signals.append({"id": "low-dna", "weight": 32, "label": "DNA below release floor"})
    if any(word in grade_text for word in ("hard", "rework")) or grade_text.startswith("d"):
        signals.append({"id": "hard-grade", "weight": 30, "label": "Hard/Rework material grade"})
    if finite(row.get("livingScore")) < 58:
        signals.append({"id": "weak-living", "weight": 18, "label": "living finish response is weak"})
    if finite(row.get("simFlashScore")) < 46:
        signals.append({"id": "weak-sim", "weight": 16, "label": "iRacing-style practical rig response is weak"})
    if finite(row.get("detail")) < 18:
        signals.append({"id": "low-detail", "weight": 12, "label": "spec/paint detail reads lazy or smooth"})
    if finite(row.get("mRange")) < 80 or finite(row.get("rRange")) < 80 or finite(row.get("ccRange")) < 32:
        signals.append({"id": "cramped-spec", "weight": 14, "label": "packed spec channel range is cramped"})
    if finite(row.get("darkGlossPct")) > 30 and finite(row.get("darkVoidPct")) < 50:
        signals.append({"id": "dark-leak", "weight": 20, "label": "dark floor is leaking gloss instead of void"})
    if row.get("metricTension"):
        signals.append({"id": "metric-tension", "weight": 8, "label": "visual intent and diagnostic metric are in tension"})
    if finite(row.get("pinFlashScore")) < 42 and row.get("flashMode") != "heroBand":
        signals.append({"id": "weak-pins", "weight": 10, "label": "pinfield/twinkle response is weak"})
    return signals


def triage_lane(row: dict[str, Any]) -> str:
    grade_text = f"{row.get('effectiveGrade','')} {row.get('grade','')}".lower()
    if finite(row.get("dnaScore")) < 58 or any(word in grade_text for word in ("hard", "rework")) or grade_text.startswith("d"):
        return "P0 release blockers"
    if finite(row.get("darkGlossPct")) > 30 and finite(row.get("darkVoidPct")) < 50:
        return "P0 dark void leaks"
    if finite(row.get("simFlashScore")) < 46:
        return "P1 iRacing-lighting response"
    if finite(row.get("mRange")) < 80 or finite(row.get("rRange")) < 80 or finite(row.get("ccRange")) < 32:
        return "P1 spec-channel depth"
    if row.get("metricTension"):
        return "P1 hero intent review"
    if finite(row.get("detail")) < 18 or finite(row.get("livingScore")) < 68:
        return "P2 texture/detail lift"
    if finite(row.get("dnaScore")) < 78 or row.get("firstRepair"):
        return "P2 polish queue"
    return "P3 monitor"


def enrich_triage(row: dict[str, Any]) -> dict[str, Any]:
    signals = priority_signals(row)
    lane = triage_lane(row)
    dna_gap = max(0.0, 78.0 - finite(row.get("dnaScore")))
    boost = 28 if lane.startswith("P0") else 15 if lane.startswith("P1") else 6 if lane.startswith("P2") else 0
    score = round(min(100.0, dna_gap * 1.15 + boost + sum(signal["weight"] for signal in signals)))
    return {**row, "triageLane": lane, "priorityScore": score, "priorityReasons": [s["label"] for s in signals], "prioritySignalIds": [s["id"] for s in signals]}


def average(rows: list[dict[str, Any]], field: str) -> float:
    vals = [finite(row.get(field), math.nan) for row in rows]
    vals = [v for v in vals if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else 0.0


def build_release_gates(rows: list[dict[str, Any]], errors: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows) or 1
    low_dna = sum(1 for row in rows if finite(row.get("dnaScore")) < 58)
    hard = sum(1 for row in rows if any(word in f"{row.get('effectiveGrade','')} {row.get('grade','')}".lower() for word in ("hard", "rework")) or str(row.get("grade", "")).lower().startswith("d"))
    weak_sim = sum(1 for row in rows if finite(row.get("simFlashScore")) < 46)
    dark_leak = sum(1 for row in rows if finite(row.get("darkGlossPct")) > 30 and finite(row.get("darkVoidPct")) < 50)
    cramped = sum(1 for row in rows if finite(row.get("mRange")) < 80 or finite(row.get("rRange")) < 80 or finite(row.get("ccRange")) < 32)
    hero = sum(1 for row in rows if row.get("metricTension"))
    avg_dna = average(rows, "dnaScore")
    pass_rate = (total - low_dna) / total * 100
    health = round(max(0, min(100, avg_dna * 0.46 + pass_rate * 0.26 + max(0, 100 - len(errors) / total * 100) * 0.10 + max(0, 100 - dark_leak / total * 220) * 0.08 + max(0, 100 - cramped / total * 120) * 0.06 + max(0, 100 - hard / total * 180) * 0.04)))
    gates = [
        {"id": "catalog-health", "label": "Catalog health score >= 72", "current": health, "pass": health >= 72},
        {"id": "render-failures", "label": "Render failures under 2%", "current": round(len(errors) / total * 100, 2), "pass": len(errors) / total < 0.02},
        {"id": "low-dna", "label": "Low DNA rows under 18%", "current": round(low_dna / total * 100, 2), "pass": low_dna / total < 0.18},
        {"id": "hard-rework", "label": "Hard/Rework rows under 8%", "current": round(hard / total * 100, 2), "pass": hard / total < 0.08},
        {"id": "dark-leak", "label": "Dark leak rows under 6%", "current": round(dark_leak / total * 100, 2), "pass": dark_leak / total < 0.06},
        {"id": "cramped-spec", "label": "Cramped spec rows under 22%", "current": round(cramped / total * 100, 2), "pass": cramped / total < 0.22},
    ]
    return {
        "healthScore": health,
        "releaseReady": all(g["pass"] for g in gates),
        "counts": {"total": len(rows), "lowDna": low_dna, "hardRework": hard, "weakSim": weak_sim, "darkLeak": dark_leak, "crampedSpec": cramped, "heroTension": hero, "renderFailures": len(errors)},
        "averages": {"dnaScore": round(avg_dna, 2), "livingScore": round(average(rows, "livingScore"), 2), "pinFlashScore": round(average(rows, "pinFlashScore"), 2), "simFlashScore": round(average(rows, "simFlashScore"), 2), "detail": round(average(rows, "detail"), 2)},
        "gates": gates,
        "nextReleaseAction": "Catalog passes current DNA release gates; focus on hero polish and proof captures." if all(g["pass"] for g in gates) else "Hold release polish: repair failed gates in priority order, then rerun Live DNA Bible with baseline comparison.",
    }


def build_repair_tasks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = []
    for row in rows:
        if finite(row.get("dnaScore")) >= 78 and not row.get("metricTension") and not row.get("firstRepair"):
            continue
        tasks.append({
            "id": f"dna-bible-{row.get('type')}-{row.get('id')}",
            "finish_id": row.get("id"),
            "type": row.get("type"),
            "group": row.get("group"),
            "dnaScore": row.get("dnaScore"),
            "flashMode": row.get("flashMode"),
            "primary_metric": row.get("firstRepair") or ("metric-tension-review" if row.get("metricTension") else "finishDna.score"),
            "current": {k: row.get(k) for k in ("livingScore", "pinFlashScore", "simFlashScore", "detail", "mRange", "rRange", "ccRange", "darkGlossPct", "darkVoidPct")},
            "target": "Preserve hero-band visual pop while improving diffuse rig response, crest sharpness, and dark-floor separation." if row.get("flashMode") == "heroBand" else "Improve DNA score, channel range, micro-detail, and sim flash without changing channel semantics.",
            "verify": "Regenerate the Live DNA Bible and confirm this row improves without new gradeContext.hardBlockers.",
        })
    return tasks


def build_batch_plan(rows: list[dict[str, Any]], repair_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    task_by_key = {f"{task.get('type')}:{task.get('finish_id')}": task for task in repair_tasks}
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        task = task_by_key.get(f"{row.get('type')}:{row.get('id')}", {})
        metric = task.get("primary_metric") or row.get("firstRepair") or ("metric-tension-review" if row.get("metricTension") else "finishDna.score")
        groups[(row.get("type") or "unknown", metric)].append(row)
    batches = []
    for index, ((typ, metric), group_rows) in enumerate(groups.items(), 1):
        source_hint = "spec-pattern overlay generation and pattern registry metadata" if "spec" in metric.lower() else "finish registry plus associated paint/spec generator"
        avg_dna = average(group_rows, "dnaScore")
        priority = round((100 - avg_dna) * 1.6 + min(35, len(group_rows)) + (12 if "dark" in metric else 0) + (8 if "metric-tension" in metric else 0))
        batches.append({
            "id": f"batch-{index}",
            "type": typ,
            "primary_metric": metric,
            "source_hint": source_hint,
            "count": len(group_rows),
            "avg_dna": round(avg_dna, 1),
            "avg_living": round(average(group_rows, "livingScore"), 1),
            "avg_pin": round(average(group_rows, "pinFlashScore"), 1),
            "avg_sim": round(average(group_rows, "simFlashScore"), 1),
            "priority": priority,
            "rows": sorted(group_rows, key=lambda item: finite(item.get("dnaScore")))[:24],
            "repair_prompt": f"Repair {typ} entries for {metric}. Work in {source_hint}. Preserve channel map Ch0=Metallic, Ch1=Roughness, Ch2=Clearcoat and rerun the Live DNA Bible after changes.",
        })
    return sorted(batches, key=lambda item: item["priority"], reverse=True)[:40]


def build_triage_hotlist(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actionable = [row for row in rows if finite(row.get("priorityScore")) >= 16 or row.get("triageLane") != "P3 monitor"]
    actionable.sort(key=lambda row: (-finite(row.get("priorityScore")), finite(row.get("dnaScore"))))
    lane_order = ["P0 release blockers", "P0 dark void leaks", "P1 iRacing-lighting response", "P1 spec-channel depth", "P1 hero intent review", "P2 texture/detail lift", "P2 polish queue", "P3 monitor"]
    lanes = []
    for lane in lane_order:
        lane_rows = [row for row in actionable if row.get("triageLane") == lane]
        if not lane_rows:
            continue
        lanes.append({"lane": lane, "count": len(lane_rows), "avgPriority": round(average(lane_rows, "priorityScore"), 1), "avgDna": round(average(lane_rows, "dnaScore"), 1), "topRows": lane_rows[:18]})
    return {"generatedAt": utc_now(), "totalActionable": len(actionable), "lanes": lanes, "topRows": actionable[:120]}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_repair_csv(path: Path, tasks: list[dict[str, Any]]) -> None:
    columns = ["id", "type", "finish_id", "group", "dnaScore", "flashMode", "primary_metric", "target", "verify", "current"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for task in tasks:
            row = dict(task)
            row["current"] = json.dumps(row.get("current", {}), separators=(",", ":"))
            writer.writerow(row)


def write_agent_packet(path: Path, summary: dict[str, Any]) -> None:
    gates = summary["releaseGates"]
    failed = [gate for gate in gates["gates"] if not gate["pass"]]
    hot = summary["triageHotlist"]
    batches = summary["agentBatchPlan"][:12]
    tasks = sorted(summary["repairTasks"], key=lambda item: finite(item.get("dnaScore")))[:120]
    lines = [
        "# SHOKKER Live DNA Bible Agent Packet",
        "",
        "## Mission",
        "Improve the SPB finish catalog in batches, preserving renderer/channel truth and artist intent while raising DNA score, practical sim response, detail, and spec-channel range.",
        "",
        "## Non-Negotiables",
        "- Channel map stays Ch0=Metallic, Ch1=Roughness, Ch2=Clearcoat.",
        "- Ch2 raw 0-15 disables clearcoat/void; Ch2 raw 16 is maximum clearcoat gloss.",
        "- Hero-band finishes must keep their streak/corridor identity; do not optimize them into random pinfields.",
        "- Rerun Live DNA Bible after each batch and compare against baseline before calling work done.",
        "",
        "## Release State",
        f"Generated: {summary['generatedAt']} | Rows: {len(summary['records'])} | Render failures: {len(summary['errors'])}",
        f"Catalog Health: {gates['healthScore']}/100 | Release Ready: {'YES' if gates['releaseReady'] else 'NO'}",
        f"Next Action: {gates['nextReleaseAction']}",
        "",
        "## Failed Release Gates",
        *([f"{i + 1}. {gate['label']} | current {gate['current']}" for i, gate in enumerate(failed)] or ["1. None."]),
        "",
        "## Repair Triage Lanes",
        *[f"{i + 1}. {lane['lane']} | {lane['count']} rows | avg priority {lane['avgPriority']} | avg DNA {lane['avgDna']}" for i, lane in enumerate(hot["lanes"][:8])],
        "",
        "## Top Hotlist Rows",
        *[f"{i + 1}. {row.get('triageLane')} | {row.get('type')}:{row.get('id')} | priority {row.get('priorityScore')} | DNA {row.get('dnaScore')} | {row.get('firstRepair') or 'review'} | {'; '.join((row.get('priorityReasons') or [])[:3]) or '--'}" for i, row in enumerate(hot["topRows"][:30])],
        "",
        "## Highest-Value Batches",
        *([f"{i + 1}. {batch['id']}: {batch['type']}/{batch['primary_metric']} | {batch['count']} rows | avg DNA {batch['avg_dna']} | source {batch['source_hint']}\n   Prompt: {batch['repair_prompt']}" for i, batch in enumerate(batches)] or ["1. No repair batches generated."]),
        "",
        "## Machine Tasks JSON",
        "```json",
        json.dumps(tasks, indent=2),
        "```",
        "",
        "## Batch Plan JSON",
        "```json",
        json.dumps(batches, indent=2),
        "```",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def rows_from_registry(payload: dict[str, Any], scope: str) -> list[dict[str, Any]]:
    buckets = []
    if scope in ("all", "base", "bases"):
        buckets.append(("base", "bases", payload.get("bases", [])))
    if scope in ("all", "pattern", "patterns"):
        buckets.append(("pattern", "patterns", payload.get("patterns", [])))
    if scope in ("all", "monolithic", "monolithics", "special", "specials"):
        buckets.append(("monolithic", "specials", payload.get("specials") or payload.get("monolithics") or []))
    rows = []
    seen = set()
    for typ, group_label, items in buckets:
        for item in items:
            if isinstance(item, str):
                row = {"id": item, "name": item, "type": typ, "category": "Other"}
            elif isinstance(item, dict):
                row = dict(item)
                row["type"] = row.get("type") or typ
            else:
                continue
            fid = str(row.get("id") or "").strip()
            if not fid or fid.lower() in {"total", "bases", "patterns", "monolithics", "specials", "all", "count", "counts"}:
                continue
            key = (row.get("type") or typ, fid)
            if key in seen:
                continue
            seen.add(key)
            row.update({"id": fid, "renderType": row.get("type") or typ, "bibleGroupLabel": row.get("category") or group_label})
            rows.append(row)
    return sorted(rows, key=lambda row: f"{row.get('type')}:{row.get('category')}:{row.get('id')}")


def normalize_type(value: str) -> str:
    text = str(value or "").strip().lower()
    return {
        "bases": "base",
        "base": "base",
        "patterns": "pattern",
        "pattern": "pattern",
        "special": "monolithic",
        "specials": "monolithic",
        "mono": "monolithic",
        "monolithic": "monolithic",
        "monolithics": "monolithic",
    }.get(text, text)


def parse_target_tokens(raw: str) -> set[tuple[str, str]]:
    targets: set[tuple[str, str]] = set()
    for token in str(raw or "").replace("\n", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            typ, fid = token.split(":", 1)
        elif "/" in token:
            typ, fid = token.split("/", 1)
        else:
            typ, fid = "", token
        fid = fid.strip()
        if not fid:
            continue
        targets.add((normalize_type(typ), fid))
    return targets


def targets_from_errors_file(path_text: str) -> set[tuple[str, str]]:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("errors") or payload.get("items") or []
    else:
        items = payload
    targets: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("id") or item.get("finish_id") or "").strip()
        typ = normalize_type(str(item.get("type") or item.get("renderType") or ""))
        if fid:
            targets.add((typ, fid))
    return targets


def filter_rows_to_targets(rows: list[dict[str, Any]], targets: set[tuple[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not targets:
        return rows, []
    remaining = set(targets)
    out: list[dict[str, Any]] = []
    for row in rows:
        typ = normalize_type(row.get("type") or row.get("renderType") or "")
        fid = str(row.get("id") or "")
        keys = {(typ, fid), ("", fid)}
        if targets & keys:
            out.append(row)
            remaining -= keys
            remaining.discard(("", fid))
            remaining.discard((typ, fid))
    skipped = [{"type": typ or "any", "id": fid, "reason": "requested target not found in live registry"} for typ, fid in sorted(remaining)]
    return out, skipped


def write_status(path: Path | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a full-catalog SHOKKER Finish DNA Bible package.")
    parser.add_argument("--size", type=int, default=512, help="Analysis texture size. Default: 512.")
    parser.add_argument("--scope", default="all", choices=["all", "base", "bases", "pattern", "patterns", "monolithic", "monolithics", "special", "specials"])
    parser.add_argument("--limit", type=int, default=0, help="Limit rows for smoke testing. 0 = all.")
    parser.add_argument("--seed", type=int, default=9101)
    parser.add_argument("--out-root", default=str(ROOT / "docs" / "DNA_FINISH_EXPORTS"))
    parser.add_argument("--status-file", default="")
    parser.add_argument("--per-finish", action="store_true", help="Write per-finish/<type>__<id>.json files.")
    parser.add_argument("--strict-exit", action="store_true", help="Exit non-zero when any finish lands in errors.json. Default treats partial bundles as successful.")
    parser.add_argument("--retry-errors", default="", help="Path to a previous errors.json; only those finish IDs will be rerun.")
    parser.add_argument("--ids", default="", help="Comma-separated targeted finishes, e.g. base:candy_red,monolithic:living_oil_pulse. Type may be omitted for unique IDs.")
    args = parser.parse_args()

    size = max(128, min(2048, int(args.size)))
    start_iso = utc_now()
    start = time.time()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / f"{timestamp}_full-catalog"
    out_dir.mkdir(parents=True, exist_ok=False)
    if args.per_finish:
        (out_dir / "per-finish").mkdir(exist_ok=True)
    status_file = Path(args.status_file) if args.status_file else out_dir / "status.json"

    write_status(status_file, {"status": "starting", "outputDir": str(out_dir), "startedAt": start_iso})
    try:
        import server as spb_server  # noqa: PLC0415
    except Exception as exc:
        write_status(status_file, {"status": "failed", "outputDir": str(out_dir), "error": str(exc), "traceback": traceback.format_exc()})
        raise

    payload = spb_server._build_finish_data_payload()
    rows = rows_from_registry(payload, args.scope)
    requested_targets = set()
    retry_source = ""
    if args.retry_errors:
        retry_source = str(args.retry_errors)
        requested_targets |= targets_from_errors_file(args.retry_errors)
    if args.ids:
        requested_targets |= parse_target_tokens(args.ids)
    target_skipped: list[dict[str, Any]] = []
    if requested_targets:
        rows, target_skipped = filter_rows_to_targets(rows, requested_targets)
    if args.limit > 0:
        rows = rows[: args.limit]

    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = target_skipped[:]
    retryable_words = ("rate_limited", "429", "timeout", "temporarily")
    total = len(rows)
    for index, row in enumerate(rows, 1):
        row_start = time.time()
        attempts = 0
        last_error: Exception | None = None
        while attempts < 3:
            attempts += 1
            try:
                paint, spec = spb_server._finish_viewer_render_maps(row.get("renderType") or row.get("type"), row["id"], size, args.seed)
                diagnostics = compute_diagnostics(paint, spec)
                dna = finish_dna_report(row, diagnostics)
                record = enrich_triage(compact_record({**row, "renderTypeUsed": row.get("renderType") or row.get("type")}, diagnostics, dna))
                record["renderMs"] = round((time.time() - row_start) * 1000, 2)
                records.append(record)
                if args.per_finish:
                    write_json(out_dir / "per-finish" / f"{safe_slug(record['type'])}__{safe_slug(record['id'])}.json", record)
                break
            except Exception as exc:
                last_error = exc
                msg = str(exc)
                retryable = any(word in msg.lower() for word in retryable_words)
                if retryable and attempts < 3:
                    time.sleep(min(8, 1.5 * attempts))
                    continue
                errors.append({
                    "type": row.get("type"),
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "attempts": attempts,
                    "retryable": retryable,
                    "error": msg,
                    "traceback": traceback.format_exc(limit=6),
                    "retryHint": f"Rerun only this finish with: node tools/export-full-dna-bible.mjs --ids {row.get('type')}:{row.get('id')} --size {size}. Or rerun all failures with --retry-errors <this-package>/errors.json.",
                })
                break
        elapsed = max(0.001, time.time() - start)
        eta = (elapsed / index * (total - index)) if index else 0
        if index == total or index % 10 == 0 or errors and errors[-1].get("id") == row.get("id"):
            status = {"status": "running", "outputDir": str(out_dir), "startedAt": start_iso, "progress": {"current": index, "total": total, "records": len(records), "errors": len(errors), "etaSeconds": round(eta, 1)}, "last": {"type": row.get("type"), "id": row.get("id")}}
            write_status(status_file, status)
            print(f"[DNA export] {index}/{total} records={len(records)} errors={len(errors)} eta={eta/60:.1f}m {row.get('type')}:{row.get('id')}", flush=True)

    records = sorted(records, key=lambda row: (-finite(row.get("priorityScore")), finite(row.get("dnaScore")), f"{row.get('type')}:{row.get('id')}"))
    repair_tasks = build_repair_tasks(records)
    release_gates = build_release_gates(records, errors)
    triage_hotlist = build_triage_hotlist(records)
    agent_plan = build_batch_plan([row for row in records if finite(row.get("dnaScore")) < 78 or row.get("metricTension") or row.get("firstRepair") or finite(row.get("priorityScore")) >= 42], repair_tasks)
    end_iso = utc_now()
    manifest = {
        "version": 1,
        "exportSchemaVersion": EXPORT_SCHEMA_VERSION,
        "dnaSchemaVersion": DNA_SCHEMA_VERSION,
        "channelMap": CHANNEL_MAP,
        "startTime": start_iso,
        "endTime": end_iso,
        "durationSeconds": round(time.time() - start, 2),
        "analysisTextureSize": size,
        "seed": args.seed,
        "scope": args.scope,
        "retrySource": retry_source,
        "targetedIds": [f"{typ}:{fid}" if typ else fid for typ, fid in sorted(requested_targets)],
        "outputDir": str(out_dir),
        "rowCountsByType": dict(Counter(row.get("type") for row in records)),
        "plannedRows": total,
        "records": len(records),
        "errors": len(errors),
        "skipped": skipped,
        "appBuildHash": sha256_short([ROOT / "finish-viewer.html", ROOT / "server.py", ROOT / "shokker_engine_v2.py", ROOT / "paint-booth-0-finish-data.js"]),
        "rendererProfile": {"viewer": "SHOKKER Paint Lab", "shaderBuild": "offline-python-exporter", "channelMapProfile": CHANNEL_MAP["profile"], "proofTarget": "synthetic / uncaptured"},
    }
    summary = {
        "version": 1,
        "bibleSchemaVersion": EXPORT_SCHEMA_VERSION,
        "dnaSchemaVersion": DNA_SCHEMA_VERSION,
        "generatedAt": end_iso,
        "status": "complete" if not errors else "complete-with-errors",
        "fatalError": "",
        "analysisTextureSize": size,
        "rendererProfile": manifest["rendererProfile"],
        "records": records,
        "errors": errors,
        "releaseGates": release_gates,
        "triageHotlist": triage_hotlist,
        "agentBatchPlan": agent_plan,
        "repairTasks": repair_tasks,
    }

    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "records.json", records)
    write_json(out_dir / "errors.json", errors)
    write_json(out_dir / "release-gates.json", release_gates)
    write_json(out_dir / "summary.json", summary)
    write_json(out_dir / "triage-hotlist.json", triage_hotlist)
    write_csv(out_dir / "records.csv", records, ["triageLane", "priorityScore", "type", "group", "id", "name", "dnaScore", "grade", "effectiveGrade", "flashMode", "metricTension", "livingScore", "pinFlashScore", "simFlashScore", "angleSpreadScore", "detail", "mRange", "rRange", "ccRange", "darkGlossPct", "darkVoidPct", "firstRepair", "topWeakness", "renderMs"])
    write_repair_csv(out_dir / "repair-tasks.csv", repair_tasks)
    write_agent_packet(out_dir / "agent-packet.md", summary)
    (out_dir / "README_AUTO.md").write_text(
        "\n".join([
            "# SHOKKER Full-Catalog Finish DNA Export",
            f"Run started: {start_iso}",
            f"Run ended: {end_iso}",
            f"Analysis texture size: {size}px",
            "Registry source: live SPB Python registries through server._build_finish_data_payload().",
            "records.json is the drop-in per-finish record array for coding agents.",
            "summary.json is the full Live DNA Bible sidecar with gates, triage, batch plan, and repair tasks.",
            "errors.json lists any finish that could not be rendered or graded; no failures are silent.",
            "Re-run: node tools/export-full-dna-bible.mjs --size 512",
            "Retry failures only: node tools/export-full-dna-bible.mjs --retry-errors <this-folder>/errors.json --size 512",
            "Spot-check IDs only: node tools/export-full-dna-bible.mjs --ids base:candy_red,monolithic:living_oil_pulse --size 512",
            "Proof target note: offline sim lines are synthetic / uncaptured until image proof captures exist.",
        ]),
        encoding="utf-8",
    )
    final_status = {"status": summary["status"], "outputDir": str(out_dir), "startedAt": start_iso, "endedAt": end_iso, "durationSeconds": manifest["durationSeconds"], "records": len(records), "errors": len(errors), "manifest": str(out_dir / "manifest.json")}
    write_status(status_file, final_status)
    print(f"[DNA export] done records={len(records)} errors={len(errors)} output={out_dir}", flush=True)
    return 2 if errors and args.strict_exit else 0


if __name__ == "__main__":
    raise SystemExit(main())
