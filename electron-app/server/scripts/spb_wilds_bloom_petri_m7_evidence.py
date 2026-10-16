# -*- coding: utf-8 -*-
"""Isolated official M1->M7 evidence for Fractured Bloom and Petri.

SPB-WILDS 2026-08-23. Owner verdict: "Too much redundancy way too similar
looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping
stuff."  The shipping scorecard contains historical render fields, so this
script never edits it. It refreshes render-derived fields in an isolated copy
from the final native-2048 center crops, uses the corrected real-engine
thumbnails for M1, and runs the official M1/M2/M5/M6/M7 modules unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORK = ROOT / "_wilds_work" / "bloom_petri"
CROPS = WORK / "after" / "native_512_crops"
RUN = WORK / "m7_evidence"
METRICS = RUN / "metrics"
THUMBS = RUN / "thumbnails"
TEMP_SCORECARD = RUN / "scorecard_bloom_petri_eval.js"
SOURCE_SCORECARD = ROOT / "paint-booth-0-catalog-scorecard.js"
ROOT_M7 = ROOT / "_workbook_metrics" / "m7_composite.json"
PREFIXES = ("fbl_", "fpe_")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_scorecard(path: Path = SOURCE_SCORECARD) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\});", text, flags=re.S)
    if match is None:
        raise RuntimeError(f"Could not parse scorecard: {path}")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def _spec_metrics(spec: np.ndarray) -> dict[str, float]:
    arr = spec[:, :, :3].astype(np.float32)
    chans = [arr[:, :, i] for i in range(3)]
    ranges = [float(ch.max() - ch.min()) for ch in chans]
    stds = [float(ch.std()) for ch in chans]
    independence = []
    for a in range(3):
        for b in range(a + 1, 3):
            x, y = chans[a].ravel(), chans[b].ravel()
            independence.append(
                0.0 if x.std() < 1e-5 or y.std() < 1e-5
                else 1.0 - abs(float(np.corrcoef(x, y)[0, 1]))
            )
    return {
        "m_range": ranges[0], "r_range": ranges[1], "cc_range": ranges[2],
        "m_std": stds[0], "r_std": stds[1], "cc_std": stds[2],
        "independence": float(np.mean(independence)),
    }


def _paint_metrics(paint: np.ndarray) -> dict[str, float]:
    rgb = paint.astype(np.float32)
    luma = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    pad = np.pad(luma, 1, mode="edge")
    box = (
        pad[:-2, :-2] + pad[:-2, 1:-1] + pad[:-2, 2:]
        + pad[1:-1, :-2] + pad[1:-1, 1:-1] + pad[1:-1, 2:]
        + pad[2:, :-2] + pad[2:, 1:-1] + pad[2:, 2:]
    ) / 9.0
    fine = float(np.abs(luma - box).mean()) / 255.0
    macro = float(np.abs(box - box.mean()).mean()) / 255.0
    q = (rgb // 32).astype(np.int32)
    keys = q[:, :, 0] * 1024 + q[:, :, 1] * 32 + q[:, :, 2]
    maxc, minc = rgb.max(axis=2), rgb.min(axis=2)
    sat = np.where(maxc > 1e-3, (maxc - minc) / (maxc + 1e-3), 0.0)
    return {
        "paint_luma_std": float(luma.std()),
        "paint_luma_span": float(luma.max() - luma.min()),
        "paint_fine_energy": fine,
        "paint_residual_energy": fine * 0.7,
        "paint_block_energy": macro,
        "paint_macro_energy": macro,
        "paint_micro_macro_ratio": fine / max(macro, 1e-4),
        "paint_color_population": int(np.unique(keys).size),
        "paint_saturation_mean": float(sat.mean()),
    }


def _refresh_entry(entry: dict, paint: np.ndarray, spec: np.ndarray) -> dict:
    pm, sm = _paint_metrics(paint), _spec_metrics(spec)
    result = dict(entry)
    result.update({
        "surface": "Special / Monolithic",
        "surface_kind": "monolithic",
        "specMRange": round(sm["m_range"], 4),
        "specRRange": round(sm["r_range"], 4),
        "specCcRange": round(sm["cc_range"], 4),
        "specMStd": round(sm["m_std"], 4),
        "specRStd": round(sm["r_std"], 4),
        "specCcStd": round(sm["cc_std"], 4),
        "specChannelIndependence": round(sm["independence"], 4),
        "paintLumaStd": round(pm["paint_luma_std"], 4),
        "paintLumaSpan": round(pm["paint_luma_span"], 4),
        "paintFineEnergy": round(pm["paint_fine_energy"], 6),
        "paintResidualEnergy": round(pm["paint_residual_energy"], 6),
        "paintBlockEnergy": round(pm["paint_block_energy"], 6),
        "paintMacroEnergy": round(pm["paint_macro_energy"], 6),
        "paintMicroMacroRatio": round(pm["paint_micro_macro_ratio"], 6),
        "paintColorPopulation": pm["paint_color_population"],
        "paintSaturationMean": round(pm["paint_saturation_mean"], 6),
    })
    return result


def _ids() -> list[str]:
    ids = sorted(
        p.name.removesuffix("_paint.png")
        for p in CROPS.glob("*_paint.png")
        if p.name.startswith(PREFIXES)
    )
    if len(ids) != 40 or len(set(ids)) != 40:
        raise RuntimeError(f"Expected exactly 40 Bloom/Petri crops, got {len(ids)}")
    return ids


def prepare() -> tuple[list[str], dict]:
    ids = _ids()
    METRICS.mkdir(parents=True, exist_ok=True)
    mono = THUMBS / "monolithic"
    mono.mkdir(parents=True, exist_ok=True)
    scorecard = _load_scorecard()
    refreshed = {}
    thumbnail_std = {}
    for fid in ids:
        key = f"monolithic:{fid}"
        if key not in scorecard:
            raise RuntimeError(f"Missing shipping scorecard contract: {key}")
        paint = np.asarray(Image.open(CROPS / f"{fid}_paint.png").convert("RGB"), np.uint8)
        spec = np.asarray(Image.open(CROPS / f"{fid}_spec.png").convert("RGB"), np.uint8)
        scorecard[key] = _refresh_entry(scorecard[key], paint, spec)
        refreshed[fid] = {
            "category": scorecard[key]["category"],
            "paint": _paint_metrics(paint),
            "spec": _spec_metrics(spec),
        }
        thumb = ROOT / "thumbnails" / "monolithic" / f"{fid}.png"
        if not thumb.exists():
            raise RuntimeError(f"Missing corrected real-engine thumbnail: {thumb}")
        std = float(np.asarray(Image.open(thumb).convert("RGB"), np.float32).std())
        if std < 4.0:
            raise RuntimeError(f"Flat real-engine thumbnail rejected: {fid} RGB std={std:.4f}")
        thumbnail_std[fid] = round(std, 6)
        shutil.copy2(thumb, mono / thumb.name)
    TEMP_SCORECARD.write_text(
        "// Isolated SPB-WILDS Bloom/Petri evidence; never shipped.\n"
        "window.SPB_WILDS_BP_SCORECARD = "
        + json.dumps(scorecard, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    inputs = {
        "sourceScorecardSha256": _sha256(SOURCE_SCORECARD),
        "isolatedScorecardSha256": _sha256(TEMP_SCORECARD),
        "thumbnailRgbStdMinimum": min(thumbnail_std.values()),
        "thumbnailRgbStdMedian": round(float(np.median(list(thumbnail_std.values()))), 6),
        "refreshed": refreshed,
    }
    return ids, inputs


def _run_official_modules() -> None:
    env = dict(os.environ)
    env.update({
        "SPB_BP_SCORECARD": str(TEMP_SCORECARD),
        "SPB_BP_METRICS": str(METRICS),
        "SPB_BP_THUMBS": str(THUMBS),
        "PYTHONIOENCODING": "utf-8",
    })
    common = (
        "import os; from pathlib import Path; "
        "score=Path(os.environ['SPB_BP_SCORECARD']); "
        "out=Path(os.environ['SPB_BP_METRICS']); "
    )
    commands = [
        common + "import scripts.spb_workbook_compute_m1 as m; m.SCORECARD=score; "
        "m.OUT_DIR=out; m.THUMBS=Path(os.environ['SPB_BP_THUMBS']); raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m2 as m; m.SCORECARD=score; "
        "m.OUT_DIR=out; raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m5 as m; m.SCORECARD=score; "
        "m.OUT_DIR=out; raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m6 as m; m.SCORECARD=score; "
        "m.OUT_DIR=out; raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m7 as m; m.SCORECARD=score; "
        "m.OUT_DIR=out; m.M1=out/'m1_sibling_diff.json'; m.M2=out/'m2_intent_fit.json'; "
        "m.M5=out/'m5_spec_paint_coherence.json'; m.M6=out/'m6_intent_floor_ceiling.json'; "
        "raise SystemExit(m.main())",
    ]
    for code in commands:
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)


def _root_scores(ids: list[str]) -> dict:
    if not ROOT_M7.exists():
        return {"available": False}
    by_finish = json.loads(ROOT_M7.read_text(encoding="utf-8")).get("byFinish", {})
    rows = {fid: by_finish[f"monolithic:{fid}"]["composite"] for fid in ids
            if f"monolithic:{fid}" in by_finish}
    return {
        "available": len(rows) == len(ids),
        "count": len(rows),
        "minimum": min(rows.values()) if rows else None,
        "median": round(float(np.median(list(rows.values()))), 3) if rows else None,
        "maximum": max(rows.values()) if rows else None,
        "countBelow85": sum(v < 85.0 for v in rows.values()),
        "perFinish": rows,
        "caveat": "Honest corrected root-thumbnail bake, but M5 uses stale shipping-scorecard render fields.",
    }


def run() -> dict:
    ids, inputs = prepare()
    _run_official_modules()
    by_finish = json.loads((METRICS / "m7_composite.json").read_text(encoding="utf-8"))["byFinish"]
    rows = {fid: by_finish[f"monolithic:{fid}"] for fid in ids}
    composites = [float(row["composite"]) for row in rows.values()]
    below = sorted(
        ({"id": fid, **row} for fid, row in rows.items() if row["composite"] < 85.0),
        key=lambda row: row["composite"],
    )
    summary = {
        "schema": 1,
        "ticket": "SPB-WILDS 2026-08-23",
        "ownerVerdict": "Too much redundancy way too similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping stuff.",
        "method": {
            "scorecard": "isolated copy; shipping scorecard untouched",
            "paintAndSpec": "final native-2048 center 512 crops",
            "m1": "corrected non-flat real-engine thumbnails",
            "officialModules": ["M1", "M2", "M5", "M6", "M7"],
            "categories": "shipping Bloom/Petri categories preserved; no profile alias",
        },
        "inputs": inputs,
        "rootBakeWithStaleShippingM5": _root_scores(ids),
        "isolatedRenderRefreshedM7": {
            "count": len(rows),
            "minimum": min(composites),
            "median": round(float(np.median(composites)), 3),
            "mean": round(float(np.mean(composites)), 3),
            "maximum": max(composites),
            "countAtOrAbove85": sum(v >= 85.0 for v in composites),
            "countBelow85": len(below),
            "below85": below,
            "perFinish": rows,
        },
    }
    out = RUN / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    report = run()
    print(json.dumps(report["isolatedRenderRefreshedM7"], indent=2)[:2000])
