# -*- coding: utf-8 -*-
"""Isolated official M1->M7 evidence run for the 70 rebuilt Wilds finishes.

SPB-WILDS 2026-08-23, tick W-1. Owner verdict: "Too much redundancy way
too similar looks. Must be VERY UNIQUE" and retain FRACTURED color flipping.
This script never edits the shipping scorecard. It copies the scorecard to
``_wilds_work``, refreshes the 70 render-derived fields from the final accepted
W3 render set, and evaluates each lane under its actual shipping category.
All official workbook modules run against that isolated copy and the current
fail-closed real-engine thumbnails.
"""
from __future__ import annotations

import json
import hashlib
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

WORK = ROOT / "_wilds_work"
RENDERS = WORK / "owner_eye_w3_final"
RUN = WORK / "m7_evidence"
METRICS = RUN / "metrics"
THUMBS = RUN / "thumbnails"
TEMP_SCORECARD = RUN / "scorecard_wilds_eval.js"


def _spec_metrics(spec: np.ndarray) -> dict[str, float]:
    arr = spec[:, :, :3].astype(np.float32)
    chans = [arr[:, :, i] for i in range(3)]
    ranges = [float(ch.max() - ch.min()) for ch in chans]
    stds = [float(ch.std()) for ch in chans]
    independence = []
    for a in range(3):
        for b in range(a + 1, 3):
            x, y = chans[a].ravel(), chans[b].ravel()
            independence.append(0.0 if x.std() < 1e-5 or y.std() < 1e-5
                                else 1.0 - abs(float(np.corrcoef(x, y)[0, 1])))
    return {
        "m_range": ranges[0], "r_range": ranges[1], "cc_range": ranges[2],
        "m_std": stds[0], "r_std": stds[1], "cc_std": stds[2],
        "independence": float(np.mean(independence)),
    }


def _paint_metrics(paint: np.ndarray) -> dict[str, float]:
    rgb = (paint * 255).astype(np.float32) if paint.max() <= 1.5 else paint.astype(np.float32)
    luma = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    pad = np.pad(luma, 1, mode="edge")
    box = (pad[:-2, :-2] + pad[:-2, 1:-1] + pad[:-2, 2:]
           + pad[1:-1, :-2] + pad[1:-1, 1:-1] + pad[1:-1, 2:]
           + pad[2:, :-2] + pad[2:, 1:-1] + pad[2:, 2:]) / 9.0
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


def _load_scorecard() -> dict:
    text = (ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\});", text, flags=re.S)
    if match is None:
        raise RuntimeError("Could not parse source scorecard")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def _refresh_entry(entry: dict, fid: str, paint: np.ndarray, spec: np.ndarray) -> dict:
    pm = _paint_metrics(paint)
    sm = _spec_metrics(spec)
    result = dict(entry)
    result.update({
        "id": fid,
        "name": result.get("name", fid.replace("_", " ").title()),
        "category": (
            "👣 FRACTURED CRYPTID" if fid.startswith("fc_")
            else "🦋 FRACTURED MORPHO"
        ),
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


def prepare() -> list[str]:
    METRICS.mkdir(parents=True, exist_ok=True)
    mono = THUMBS / "monolithic"
    mono.mkdir(parents=True, exist_ok=True)
    scorecard = _load_scorecard()
    ids = sorted(p.stem for p in (RENDERS / "paint").glob("fc_*.png"))
    ids += sorted(p.stem for p in (RENDERS / "paint").glob("fmo_*.png"))
    if len(ids) != 70:
        raise RuntimeError(f"Expected 70 rendered Wilds finishes, got {len(ids)}")
    for fid in ids:
        paint_path = RENDERS / "paint" / f"{fid}.png"
        spec_path = RENDERS / "spec" / f"{fid}.png"
        paint = np.asarray(Image.open(paint_path).convert("RGB"), np.float32) / 255.0
        proof = np.asarray(Image.open(spec_path).convert("RGB"), np.uint8)
        spec = np.stack((proof[:, :, 0], 255 - proof[:, :, 1], proof[:, :, 2]), axis=2)
        key = f"monolithic:{fid}"
        scorecard[key] = _refresh_entry(scorecard.get(key, {}), fid, paint, spec)
        # SPB-WILDS tick 5 (2026-08-23). The owner requires review through
        # actual baked thumbnails. Use the corrected real-engine picker bake
        # for M1, while the native paint/spec render remains the metric source.
        thumb_path = ROOT / "thumbnails" / "monolithic" / f"{fid}.png"
        if not thumb_path.exists():
            raise RuntimeError(f"Missing real-engine Wilds thumbnail: {thumb_path}")
        thumb = np.asarray(Image.open(thumb_path).convert("RGB"), np.uint8)
        if float(thumb.std()) < 4.0:
            raise RuntimeError(f"Flat real-engine Wilds thumbnail rejected: {fid}")
        shutil.copy2(thumb_path, mono / thumb_path.name)
    TEMP_SCORECARD.write_text(
        "// Isolated SPB-WILDS evidence; never shipped.\nwindow.SPB_WILDS_SCORECARD = "
        + json.dumps(scorecard, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    return ids


def run() -> dict:
    ids = prepare()
    env = dict(__import__("os").environ)
    env.update({
        "SPB_WILDS_SCORECARD": str(TEMP_SCORECARD),
        "SPB_WILDS_METRICS": str(METRICS),
        "SPB_WILDS_THUMBS": str(THUMBS),
        "PYTHONIOENCODING": "utf-8",
    })
    common = (
        "import os; from pathlib import Path; "
        "score=Path(os.environ['SPB_WILDS_SCORECARD']); "
        "out=Path(os.environ['SPB_WILDS_METRICS']); "
    )
    commands = [
        common + "import scripts.spb_workbook_compute_m1 as m; m.SCORECARD=score; m.OUT_DIR=out; "
                 "m.THUMBS=Path(os.environ['SPB_WILDS_THUMBS']); raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m2 as m; m.SCORECARD=score; m.OUT_DIR=out; raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m5 as m; m.SCORECARD=score; m.OUT_DIR=out; raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m6 as m; m.SCORECARD=score; m.OUT_DIR=out; raise SystemExit(m.main())",
        common + "import scripts.spb_workbook_compute_m7 as m; m.SCORECARD=score; m.OUT_DIR=out; "
                 "m.M1=out/'m1_sibling_diff.json'; m.M2=out/'m2_intent_fit.json'; "
                 "m.M5=out/'m5_spec_paint_coherence.json'; m.M6=out/'m6_intent_floor_ceiling.json'; "
                 "raise SystemExit(m.main())",
    ]
    for code in commands:
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)
    all_scores = json.loads((METRICS / "m7_composite.json").read_text(encoding="utf-8"))["byFinish"]
    rows = [{"id": fid, **all_scores[f"monolithic:{fid}"]} for fid in ids]
    scored = [r for r in rows if isinstance(r.get("composite"), (int, float))]
    summary = {
        "schema": 1,
        "ticket": "SPB-WILDS 2026-08-23 tick W-3",
        "scorecard_mode": "isolated copy; final W3 renders; actual shipping categories",
        "count": len(rows),
        "scored": len(scored),
        "minimum_composite": min(r["composite"] for r in scored),
        "mean_composite": round(sum(r["composite"] for r in scored) / len(scored), 3),
        "count_below_85": sum(r["composite"] < 85.0 for r in scored),
        "lowest": sorted(scored, key=lambda r: r["composite"])[:12],
        "finishes": rows,
    }
    (RUN / "wilds_m7_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    before = json.loads((WORK / "before" / "audit.json").read_text(encoding="utf-8"))
    after = json.loads((RENDERS / "audit.json").read_text(encoding="utf-8"))
    validation_path = RENDERS / "validation_summary.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    native = validation["native_2048"]
    validation["isolated_m7"] = {
        "count": summary["count"],
        "scored": summary["scored"],
        "minimum_composite": summary["minimum_composite"],
        "mean_composite": summary["mean_composite"],
        "count_below_85": summary["count_below_85"],
        "report": "../m7_evidence/wilds_m7_summary.json",
    }
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    after_rows = after["finishes"]
    channel_floor = {}
    for name in ("M", "R", "CC"):
        chans = [next(c for c in row["spec_channels"] if c["name"] == name) for row in after_rows]
        channel_floor[name] = {
            "minimum_std": round(min(c["std"] for c in chans), 6),
            "minimum_range": min(c["max"] - c["min"] for c in chans),
            "minimum_levels": min(c["levels"] for c in chans),
        }
    old_fc_corr = []
    coupling_path = ROOT / "scripts" / "spec_coupling.jsonl"
    for line in coupling_path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("id", "")).startswith("fc_"):
            old_fc_corr.append(float(row["maxcorr"]))
    source_files = [
        ROOT / "engine" / "expansions" / "fractured_wilds_signatures_2026.py",
        ROOT / "engine" / "expansions" / "fractured_themes_2026.py",
        ROOT / "engine" / "expansions" / "fractured_themes_fix_2026.py",
        ROOT / "engine" / "expansions" / "fractured_morpho_2026.py",
        ROOT / "scripts" / "spb_wilds_audit.py",
        ROOT / "scripts" / "spb_wilds_m7_evidence.py",
        ROOT / "tests" / "test_fractured_wilds_20260823.py",
    ]
    report = {
        "schema": 2,
        "ticket": "SPB-WILDS 2026-08-23 tick W-3",
        "owner_verdict": "Too much redundancy way too similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping stuff.",
        "scope": {"count": 70, "cryptid": 20, "morpho": 50, "ids_preserved": True},
        "similarity": {
            "before": {k: before["similarity"][k] for k in (
                "max_structural_similarity", "median_structural_similarity",
                "p95_structural_similarity", "max_look_similarity", "look_ge_0_80")},
            "after": {k: after["similarity"][k] for k in (
                "max_structural_similarity", "median_structural_similarity",
                "p95_structural_similarity", "max_look_similarity", "look_ge_0_80")},
            "max_structural_delta": round(
                after["similarity"]["max_structural_similarity"]
                - before["similarity"]["max_structural_similarity"], 6),
        },
        "fine_doctrine": {
            "authored_primitive_px_at_2048": [8, 32],
            "mark_families_per_finish": 7,
            "minimum_paint_fine_energy": min(r["paint_fine_energy"] for r in after_rows),
            "minimum_color_population": min(r["color_population"] for r in after_rows),
        },
        "material_channels": {
            "before_cryptid_maxcorr": {
                "count": len(old_fc_corr), "minimum": min(old_fc_corr),
                "median": float(np.median(old_fc_corr)), "maximum": max(old_fc_corr),
            },
            "after_all70_max_abs_corr": max(r["spec_max_abs_corr"] for r in after_rows),
            "floors": channel_floor,
        },
        "angle_flip": {
            "response_delta_minimum": min(r["flip_response_delta"] for r in after_rows),
            "response_delta_median": round(float(np.median([r["flip_response_delta"] for r in after_rows])), 6),
            "saturation_weighted_hue_histogram_tv_minimum": min(r["flip_hue_histogram_tv"] for r in after_rows),
            "saturation_weighted_hue_histogram_tv_median": round(float(np.median([r["flip_hue_histogram_tv"] for r in after_rows])), 6),
            "saturation_weighted_hue_histogram_tv_maximum": max(r["flip_hue_histogram_tv"] for r in after_rows),
            "weighted_chroma_delta_median": round(float(np.median([r["flip_weighted_chroma_delta"] for r in after_rows])), 6),
            "note": "Hue TV compares normalized saturation-weighted hue populations under two M/R/CC angle mixes; it cannot pass on brightness change alone.",
        },
        "native_2048": {
            "count": native["count"],
            "median_seconds_2048": native["median_seconds"],
            "p95_seconds_2048": native["p95_seconds"],
            "max_seconds_2048": native["max_seconds"],
            "count_over_3_seconds": native["count_over_3_seconds"],
        },
        "m7": {k: summary[k] for k in (
            "scorecard_mode", "count", "scored", "minimum_composite",
            "mean_composite", "count_below_85")},
        "tests": {
            "command": validation["tests"]["command"],
            "result": validation["tests"]["result"],
            "observed_seconds": validation["tests"]["seconds"],
        },
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_files
        },
        "artifacts": [
            "_wilds_work/before/contact_sheet.png",
            "_wilds_work/owner_eye_w3_final/paint_contact_sheet.png",
            "_wilds_work/owner_eye_w3_final/spec_contact_sheet.png",
            "_wilds_work/owner_eye_w3_final/angle_ab_contact_sheet.png",
            "_wilds_work/owner_eye_w3_final/native_2048_crops.png",
            "_wilds_work/owner_eye_w3_final/audit.json",
            "_wilds_work/owner_eye_w3_final/validation_summary.json",
            "_wilds_work/owner_eye_w3_native_perf/native_perf.json",
            "_wilds_work/m7_evidence/wilds_m7_summary.json",
        ],
    }
    (WORK / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    report = run()
    print(json.dumps({k: report[k] for k in (
        "count", "scored", "minimum_composite", "mean_composite", "count_below_85")}, indent=2))
