# -*- coding: utf-8 -*-
"""Run the official isolated M5/M6/M7 gate for one Wilds candidate module.

The module must expose ``ID`` and ``_authored() -> (paint_rgb_float, spec_u8)``.
Shipping scorecards and global workbook metrics are read-only; all refreshed
rows and outputs live below the requested evidence directory.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_wilds_m7_evidence import _paint_metrics, _spec_metrics  # noqa: E402


def _scorecard() -> dict:
    text = (ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\});", text, flags=re.S)
    if match is None:
        raise RuntimeError("Could not parse shipping scorecard")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def _run(module: str, score: Path, out: Path, extra: str = "") -> None:
    code = (f"from pathlib import Path; score=Path(r'{score}'); out=Path(r'{out}'); "
            f"import {module} as m; m.SCORECARD=score; m.OUT_DIR=out; "
            + extra + "raise SystemExit(m.main())")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                            text=True, encoding="utf-8", errors="replace",
                            capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{module} failed: {(result.stdout + result.stderr)[-3000:]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("evidence_dir")
    args = parser.parse_args()
    candidate = importlib.import_module(args.module)
    fid = candidate.ID
    paint, spec = candidate._authored()
    pm, sm = _paint_metrics(paint), _spec_metrics(spec)
    run = (ROOT / args.evidence_dir).resolve()
    metrics = run / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    score_path = run / "scorecard_candidate_eval.js"
    report_path = run / "m7_report.json"
    scorecard = _scorecard()
    key = f"monolithic:{fid}"
    if key not in scorecard:
        raise KeyError(f"candidate missing from shipping scorecard: {key}")
    row = dict(scorecard[key])
    row.update({
        "id": fid, "surface": "Special / Monolithic", "surface_kind": "monolithic",
        "specMRange": round(sm["m_range"], 4), "specRRange": round(sm["r_range"], 4),
        "specCcRange": round(sm["cc_range"], 4), "specMStd": round(sm["m_std"], 4),
        "specRStd": round(sm["r_std"], 4), "specCcStd": round(sm["cc_std"], 4),
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
    scorecard[key] = row
    score_path.write_text(
        "// Isolated Wilds candidate M7 evidence; never shipped.\n"
        "window.SPB_WILDS_CANDIDATE_SCORECARD = "
        + json.dumps(scorecard, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8")
    _run("scripts.spb_workbook_compute_m5", score_path, metrics)
    _run("scripts.spb_workbook_compute_m6", score_path, metrics)
    _run("scripts.spb_workbook_compute_m7", score_path, metrics,
         f"m.M1=Path(r'{ROOT / '_workbook_metrics/m1_sibling_diff.json'}'); "
         f"m.M2=Path(r'{ROOT / '_workbook_metrics/m2_intent_fit.json'}'); "
         "m.M5=out/'m5_spec_paint_coherence.json'; "
         "m.M6=out/'m6_intent_floor_ceiling.json'; ")
    all_rows = json.loads((metrics / "m7_composite.json").read_text(encoding="utf-8"))["byFinish"]
    entry = all_rows[key]
    composite = entry.get("composite")
    payload = {
        "schema": "spb-wilds-single-candidate-m7/1", "id": fid,
        "module": args.module, "ship_bar": 85.0, "composite": composite,
        "pass": isinstance(composite, (int, float)) and composite >= 85.0,
        "intent": entry.get("intent"), "components": entry.get("components"),
        "paint_metrics": pm, "spec_metrics": sm,
    }
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

