# -*- coding: utf-8 -*-
"""Isolated M5/M6/M7 gate for runtime-wired Fractured Wilds survivors.

SPB-WILDS rollout tick 2026-08-25. This script reads the exact authored paint
and M/R/Cc returned by ``fractured_wilds_accepted_2026``, refreshes only those
scorecard rows in an isolated copy, and runs the official workbook modules.
It never edits the shipping scorecard or global workbook metrics.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.fractured_wilds_accepted_2026 import (  # noqa: E402
    ACCEPTED_IDS,
    _accepted_authored,
)
from scripts.spb_wilds_m7_evidence import _paint_metrics, _spec_metrics  # noqa: E402

RUN = ROOT / "_wilds_fullres_progress_20260824" / "accepted_runtime_rollout"
METRICS = RUN / "metrics"
SCORECARD = RUN / "scorecard_accepted_eval.js"
REPORT = RUN / "m7_report.json"


def _wilds_category(fid: str) -> str:
    """Restore the canonical M7 intent family for an accepted Wilds override."""
    if fid.startswith("fc_"):
        return "👣 FRACTURED CRYPTID"
    if fid.startswith("fmo_"):
        return "🦋 FRACTURED MORPHO"
    if fid.startswith("fpe_"):
        return "🧫 FRACTURED PETRI"
    if fid.startswith("fbl_"):
        return "🌸 FRACTURED BLOOM"
    raise ValueError(f"Unknown accepted Wilds family: {fid}")


def _load_scorecard() -> dict:
    text = (ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\});", text, flags=re.S)
    if match is None:
        raise RuntimeError("Could not parse shipping scorecard")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def _refresh(row: dict, fid: str) -> dict:
    paint, spec = _accepted_authored(fid)
    pm = _paint_metrics(paint)
    sm = _spec_metrics(spec)
    out = dict(row)
    out.update({
        "id": fid,
        "surface": "Special / Monolithic",
        "surface_kind": "monolithic",
        "category": _wilds_category(fid),
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
    return out


def _run_module(module: str, extra: str = "") -> None:
    common = (
        "from pathlib import Path; "
        f"score=Path({str(SCORECARD)!r}); out=Path({str(METRICS)!r}); "
    )
    code = common + f"import {module} as m; m.SCORECARD=score; m.OUT_DIR=out; " + extra + "raise SystemExit(m.main())"
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                            text=True, encoding="utf-8", errors="replace",
                            capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{module} failed: {(result.stdout + result.stderr)[-3000:]}")


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    METRICS.mkdir(parents=True, exist_ok=True)
    scorecard = _load_scorecard()
    missing = []
    for fid in ACCEPTED_IDS:
        key = f"monolithic:{fid}"
        if key not in scorecard:
            missing.append(key)
            continue
        scorecard[key] = _refresh(scorecard[key], fid)
    if missing:
        raise RuntimeError(f"Accepted Wilds missing from scorecard: {missing}")
    SCORECARD.write_text(
        "// Isolated accepted-Wilds M7 evidence; never shipped.\n"
        "window.SPB_WILDS_ACCEPTED_SCORECARD = "
        + json.dumps(scorecard, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    _run_module("scripts.spb_workbook_compute_m5")
    _run_module("scripts.spb_workbook_compute_m6")
    _run_module(
        "scripts.spb_workbook_compute_m7",
        f"m.M1=Path({str(ROOT / '_workbook_metrics/m1_sibling_diff.json')!r}); "
        f"m.M2=Path({str(ROOT / '_workbook_metrics/m2_intent_fit.json')!r}); "
        "m.M5=out/'m5_spec_paint_coherence.json'; "
        "m.M6=out/'m6_intent_floor_ceiling.json'; ",
    )
    m7 = json.loads((METRICS / "m7_composite.json").read_text(encoding="utf-8"))
    by_finish = m7["byFinish"]
    rows = []
    failures = []
    for fid in ACCEPTED_IDS:
        key = f"monolithic:{fid}"
        entry = by_finish.get(key, {})
        composite = entry.get("composite")
        row = {"id": fid, "composite": composite, "intent": entry.get("intent"),
               "components": entry.get("components")}
        rows.append(row)
        if not isinstance(composite, (int, float)) or composite < 85.0:
            failures.append(row)
    payload = {
        "schema": "spb-wilds-accepted-m7/1",
        "accepted_count": len(ACCEPTED_IDS),
        "ship_bar": 85.0,
        "all_pass": not failures,
        "rows": rows,
        "failures": failures,
    }
    REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(f"{row['id']:24s} M7={row['composite']} intent={row['intent']}")
    print(f"accepted M7: {len(rows) - len(failures)}/{len(rows)} >=85")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
