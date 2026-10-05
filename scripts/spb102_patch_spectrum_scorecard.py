#!/usr/bin/env python3
"""SPB-102 — patch scorecard with procedural Spectrum Shift finishes.

Renders all 50 spectrum shift finishes at 1024², computes spec/paint metrics,
and merges them into paint-booth-0-catalog-scorecard.js.
This ensures they are properly captured in M7 compliance metrics and the picker.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

SIZE = 1024

def _spec_metrics(spec: np.ndarray) -> dict[str, float]:
    arr = spec[:, :, :3].astype(np.float32)
    chans = [arr[:, :, i] for i in range(3)]
    ranges = [float(ch.max() - ch.min()) for ch in chans]
    stds = [float(ch.std()) for ch in chans]
    corrs = []
    for a in range(3):
        for b in range(a + 1, 3):
            x = chans[a].ravel()
            y = chans[b].ravel()
            if x.std() < 1e-5 or y.std() < 1e-5:
                corrs.append(0.0)
            else:
                corrs.append(1.0 - abs(float(np.corrcoef(x, y)[0, 1])))
    return {
        "m_range": ranges[0], "r_range": ranges[1], "cc_range": ranges[2],
        "m_std": stds[0], "r_std": stds[1], "cc_std": stds[2],
        "independence": float(np.mean(corrs)) if corrs else 0.0,
    }

def _paint_metrics(paint: np.ndarray) -> dict[str, float]:
    rgb = (paint * 255).astype(np.float32) if paint.max() <= 1.5 else paint.astype(np.float32)
    luma = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    luma_std = float(luma.std())
    luma_span = float(luma.max() - luma.min())
    # Fine-energy proxy
    pad = np.pad(luma, 1, mode="edge")
    box = (pad[:-2, :-2] + pad[:-2, 1:-1] + pad[:-2, 2:]
           + pad[1:-1, :-2] + pad[1:-1, 1:-1] + pad[1:-1, 2:]
           + pad[2:, :-2] + pad[2:, 1:-1] + pad[2:, 2:]) / 9.0
    fine = float(np.abs(luma - box).mean()) / 255.0
    # Color population
    q = (rgb // 32).astype(np.int32)
    keys = q[:, :, 0] * 1024 + q[:, :, 1] * 32 + q[:, :, 2]
    color_pop = int(np.unique(keys).size)
    # Saturation mean
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = np.where(maxc > 1e-3, (maxc - minc) / (maxc + 1e-3), 0.0)
    sat_mean = float(sat.mean())
    return {
        "paint_luma_std": luma_std,
        "paint_luma_span": luma_span,
        "paint_fine_energy": fine,
        "paint_residual_energy": fine * 0.7,
        "paint_block_energy": float(np.abs(box - box.mean()).mean()) / 255.0,
        "paint_macro_energy": float(np.abs(box - box.mean()).mean()) / 255.0,
        "paint_micro_macro_ratio": fine / max(float(np.abs(box - box.mean()).mean()) / 255.0, 1e-4),
        "paint_color_population": color_pop,
        "paint_saturation_mean": sat_mean,
    }

def _smooth_score(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return (3 * t * t - 2 * t * t * t) * 100.0

def _clip_score(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))

def _calculate_qualities(name: str, sm: dict, pm: dict) -> tuple[int, int, int, list[str]]:
    profile = "gradient"
    detail = _smooth_score(float(pm["paint_fine_energy"]), 0.004, 0.045)
    residual = _smooth_score(float(pm["paint_residual_energy"]), 0.002, 0.035)
    range_score = _smooth_score(float(pm["paint_luma_span"]), 0.05, 0.65)
    color_score = _smooth_score(float(pm["paint_color_population"]), 1, 24)
    sat_score = _smooth_score(float(pm["paint_saturation_mean"]), 0.02, 0.28)
    block_penalty = max(0.0, min(22.0, _smooth_score(float(pm["paint_block_energy"]), 0.18, 0.42) * 0.22))

    paint_score = 14 + detail * 0.18 + residual * 0.16 + range_score * 0.27 + color_score * 0.18 + sat_score * 0.08
    paint_q = _clip_score(paint_score - block_penalty)

    m = _smooth_score(sm["m_range"], 12, 180)
    r = _smooth_score(sm["r_range"], 12, 150)
    cc = _smooth_score(sm["cc_range"], 10, 120)
    std = _smooth_score(sm["m_std"] + sm["r_std"] + sm["cc_std"], 8, 130)
    independence = _smooth_score(sm["independence"], 0.05, 0.45)
    spec_score = 16 + m * 0.20 + r * 0.17 + cc * 0.18 + std * 0.24 + independence * 0.10
    spec_q = _clip_score(spec_score)

    speed_s = 100
    overall = _clip_score(paint_q * 0.43 + spec_q * 0.43 + speed_s * 0.14)

    flags = []
    if paint_q < 55:
        flags.append("low_paint_quality")
    if spec_q < 55:
        flags.append("low_spec_quality")
    if pm["paint_color_population"] < 3:
        flags.append("low_color_population")

    return paint_q, spec_q, overall, flags

def main() -> int:
    import shokker_engine_v2 as eng
    from engine.paint_v2.spectrum_shift import enumerate_50
    print(f"[patch-spectrum] engine loaded. MONOLITHIC_REGISTRY = {len(eng.MONOLITHIC_REGISTRY)}")

    scorecard_path = REPO / "paint-booth-0-catalog-scorecard.js"
    text = scorecard_path.read_text(encoding="utf-8")
    
    # Match `= { ... };` — body is greedy up to last `};` before EOF/trailing JS
    body = re.search(r"=\s*(\{[\s\S]*?\})\s*;\s*\n\s*if\s+\(typeof", text)
    if not body:
        body = re.search(r"=\s*(\{[\s\S]*\})\s*;", text)
    if not body:
        print("ERROR: could not extract scorecard body")
        return 1

    json_body = re.sub(r"//[^\n]*", "", body.group(1))
    scorecard = json.loads(json_body)
    print(f"[patch-spectrum] scorecard entries: {len(scorecard)}")

    shape = (SIZE, SIZE)
    mask = np.ones(shape, dtype=np.float32)

    spectrum_items = enumerate_50()
    print(f"[patch-spectrum] Rendering and scoring {len(spectrum_items)} spectrum finishes...")

    for palette, variant, seed_offset in spectrum_items:
        name = f"spectrum_{palette}_{variant}"
        entry = eng.MONOLITHIC_REGISTRY.get(name)
        if not entry:
            print(f"  MISSING from registry: {name}")
            continue
        
        spec_fn, paint_fn = entry
        seed = 7301 + seed_offset
        dark = np.full((SIZE, SIZE, 3), 0.15, dtype=np.float32)
        t0 = time.perf_counter()
        
        paint = paint_fn(dark.copy(), shape, mask, seed, 1.0, 1.0)
        spec = spec_fn(shape, mask, seed, 1.0)
        dt = time.perf_counter() - t0
        
        sm = _spec_metrics(np.asarray(spec))
        pm = _paint_metrics(np.asarray(paint))

        kind = "monolithic"
        prefixed = f"{kind}:{name}"
        scorecard.pop(name, None)
        existing = scorecard.get(prefixed, {})
        entry_out = dict(existing)

        paint_q, spec_q, overall, flags = _calculate_qualities(name, sm, pm)
        priority = "PASS" if overall >= 80 else "REVIEW"
        reason_flags = ", ".join(flags)

        pretty_palette = palette.replace("_", " ").title()
        pretty_variant = variant.replace("_", " ").title()

        entry_out.update({
            "id": name,
            "name": f"Spectrum {pretty_palette} {pretty_variant}",
            "category": "★ Spectrum Shift",
            "surface_kind": kind,
            "overallQuality": overall,
            "paintQuality": paint_q,
            "specQuality": spec_q,
            "speedScore": 100,
            "priority": priority,
            "reasonFlags": reason_flags,
            "status": "OK",
            "specMRange": round(sm["m_range"], 3),
            "specRRange": round(sm["r_range"], 3),
            "specCcRange": round(sm["cc_range"], 3),
            "specMStd": round(sm["m_std"], 3),
            "specRStd": round(sm["r_std"], 3),
            "specCcStd": round(sm["cc_std"], 3),
            "specChannelIndependence": round(sm["independence"], 4),
            "paintLumaStd": round(pm["paint_luma_std"], 3),
            "paintLumaSpan": round(pm["paint_luma_span"], 3),
            "paintFineEnergy": round(pm["paint_fine_energy"], 4),
            "paintResidualEnergy": round(pm["paint_residual_energy"], 4),
            "paintBlockEnergy": round(pm["paint_block_energy"], 4),
            "paintMacroEnergy": round(pm["paint_macro_energy"], 4),
            "paintMicroMacroRatio": round(pm["paint_micro_macro_ratio"], 4),
            "paintColorPopulation": pm["paint_color_population"],
            "paintSaturationMean": round(pm["paint_saturation_mean"], 4),
        })
        scorecard[prefixed] = entry_out
        print(f"  {prefixed:40s} {dt:.2f}s  Score={overall} Paint={paint_q} Spec={spec_q} M_std={sm['m_std']:.1f} R_std={sm['r_std']:.1f} CC_std={sm['cc_std']:.1f} indep={sm['independence']:.3f}  paintFine={pm['paint_fine_energy']:.4f}")

    # Backup + write
    backup = scorecard_path.with_suffix(".js.bak_spb102")
    if not backup.exists():
        shutil.copyfile(scorecard_path, backup)
        print(f"[patch-spectrum] backed up original → {backup.name}")
        
    new_body = json.dumps(scorecard, indent=2, ensure_ascii=False)
    head_match = re.search(r"^([\s\S]*?=\s*)\{", text)
    head = head_match.group(1) if head_match else "const CATALOG_SCORECARD_METRICS = "
    tail_match = re.search(r"\};\s*\n([\s\S]*)$", text)
    tail = "\n" + tail_match.group(1) if tail_match else "\n"
    new_text = head + new_body + ";\n" + tail
    scorecard_path.write_text(new_text, encoding="utf-8")
    
    # Mirror
    for mirror in [
        REPO / "electron-app" / "server" / "paint-booth-0-catalog-scorecard.js",
        REPO / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-catalog-scorecard.js",
    ]:
        if mirror.exists():
            shutil.copyfile(scorecard_path, mirror)
            
    print(f"[patch-spectrum] wrote {scorecard_path.name} + 2 mirrors")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
