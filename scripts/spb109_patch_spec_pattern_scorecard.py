#!/usr/bin/env python3
"""SPB-106 (a.k.a. SPB-109 dev tag) — surgical scorecard patch for spec patterns.

Renders the specified spec pattern texture(s), composites them onto a neutral
substrate spec map at 1024², measures the same stats spb_catalog_scorecard.py
records, and merges entries (keyed as `spec_pattern:<id>`) into
paint-booth-0-catalog-scorecard.js. Avoids a full catalog regen.

Pass pattern ids as CLI args, e.g.:
    python scripts/spb109_patch_spec_pattern_scorecard.py sparkle_comet
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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
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
    pad = np.pad(luma, 1, mode="edge")
    box = (pad[:-2, :-2] + pad[:-2, 1:-1] + pad[:-2, 2:]
           + pad[1:-1, :-2] + pad[1:-1, 1:-1] + pad[1:-1, 2:]
           + pad[2:, :-2] + pad[2:, 1:-1] + pad[2:, 2:]) / 9.0
    fine = float(np.abs(luma - box).mean()) / 255.0
    q = (rgb // 32).astype(np.int32)
    keys = q[:, :, 0] * 1024 + q[:, :, 1] * 32 + q[:, :, 2]
    color_pop = int(np.unique(keys).size)
    maxc = rgb.max(axis=2); minc = rgb.min(axis=2)
    sat = np.where(maxc > 1e-3, (maxc - minc) / (maxc + 1e-3), 0.0)
    macro = float(np.abs(box - box.mean()).mean()) / 255.0
    return {
        "paint_luma_std": float(luma.std()),
        "paint_luma_span": float(luma.max() - luma.min()),
        "paint_fine_energy": fine,
        "paint_residual_energy": fine * 0.7,
        "paint_block_energy": macro,
        "paint_macro_energy": macro,
        "paint_micro_macro_ratio": fine / max(macro, 1e-4),
        "paint_color_population": color_pop,
        "paint_saturation_mean": float(sat.mean()),
    }


def _spec_from_texture(field: np.ndarray, seed: int = 0) -> np.ndarray:
    """Compose a 4-channel spec map from a single-channel pattern texture.

    SPB-106 tick 3 revision (2026-05-20): MUST mirror the official compose
    path in `scripts/spb_visual_workbench.py:301-312` — the engine renders
    spec patterns as:

      pv = norm01(texture)
      M  = pv * 255
      R  = (1 - pv) * 180 + 15
      CC = 16 + pv * 140

    M and R are intentionally anti-correlated by this formula; my earlier
    "independent transforms" fix produced channels that DIVERGED from
    the engine's actual behavior → M7 scores became dishonest. Reverting
    to the official formula so the metric reads what the engine actually
    produces.

    Improving spec patterns means improving the source TEXTURE so it
    has rich variation across the canvas — not faking channel independence
    in the patcher.
    """
    h, w = field.shape
    f = np.clip(field, 0.0, 1.0)
    # Mirror the official compose exactly
    M = np.clip(f * 255, 0, 255).astype(np.uint8)
    R = np.clip((1.0 - f) * 180 + 15, 15, 255).astype(np.uint8)
    CC = np.clip(16 + f * 140, 16, 255).astype(np.uint8)
    A = (np.clip(f * 1.4, 0, 1) * 255).astype(np.uint8)
    return np.stack([M, R, CC, A], axis=2)


def main() -> int:
    targets = sys.argv[1:]
    if not targets:
        print("usage: spb109_patch_spec_pattern_scorecard.py <id> [<id>...]")
        return 1
    import engine.spec_patterns as sp
    catalog = sp.PATTERN_CATALOG
    print(f"[patch-spec] PATTERN_CATALOG size: {len(catalog)}")

    scorecard_path = REPO / "paint-booth-0-catalog-scorecard.js"
    text = scorecard_path.read_text(encoding="utf-8")
    body = re.search(r"=\s*(\{[\s\S]*?\})\s*;\s*\n\s*if\s+\(typeof", text)
    if not body:
        body = re.search(r"=\s*(\{[\s\S]*\})\s*;", text)
    json_body = re.sub(r"//[^\n]*", "", body.group(1))
    scorecard = json.loads(json_body)
    print(f"[patch-spec] scorecard entries: {len(scorecard)}")

    shape = (SIZE, SIZE)
    for name in targets:
        if name not in catalog:
            print(f"  MISSING: {name}")
            continue
        fn = catalog[name]
        seed = hash(name) & 0x7FFFFFFF
        t0 = time.perf_counter()
        field = fn(shape, seed, 1.0)
        dt = time.perf_counter() - t0
        # Synthesize spec map and paint from texture (channel-independent)
        spec = _spec_from_texture(np.asarray(field, dtype=np.float32), seed=seed)
        # Paint thumbnail = grayscale field on dark base
        rgb = np.stack([field * 0.7, field * 0.7, field * 0.7], axis=2)
        sm = _spec_metrics(spec)
        pm = _paint_metrics(rgb)
        prefixed = f"spec_pattern:{name}"
        existing = scorecard.get(prefixed, {})
        entry = dict(existing)
        entry.update({
            "id": name,
            "name": existing.get("name", name.replace("_", " ").title()),
            "category": existing.get("category", "Spec Overlay Pattern"),
            "surface_kind": "spec-pattern",
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
        scorecard[prefixed] = entry
        print(f"  {prefixed:40s} {dt:.2f}s  M_rng={sm['m_range']:.0f} CC_rng={sm['cc_range']:.0f} indep={sm['independence']:.3f}")

    head_match = re.search(r"^([\s\S]*?=\s*)\{", text)
    head = head_match.group(1) if head_match else "const CATALOG_SCORECARD_METRICS = "
    tail_match = re.search(r"\};\s*\n([\s\S]*)$", text)
    tail = "\n" + tail_match.group(1) if tail_match else "\n"
    new_body = json.dumps(scorecard, indent=2, ensure_ascii=False)
    scorecard_path.write_text(head + new_body + ";\n" + tail, encoding="utf-8")
    for mirror in [
        REPO / "electron-app" / "server" / "paint-booth-0-catalog-scorecard.js",
        REPO / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-catalog-scorecard.js",
    ]:
        if mirror.exists():
            shutil.copyfile(scorecard_path, mirror)
    print("[patch-spec] wrote scorecard + 2 mirrors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
