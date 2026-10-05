"""Isolated M7 evidence for the owner-authorized X LAB material set.

SPB-105 / X-LAB-1, 2026-08-28.  This never edits the shipping scorecard.  It
renders the 30 direct builders, evaluates the official M1/M2/M5/M6/M7 stack,
and leaves a compact candidate report under ``_x_lab_work/official_m7``.
Owner-eye and the paired tile report remain separate promotion gates.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.x_lab_2026 import RECIPES, arrays  # noqa: E402
from scripts.spb_wilds_m7_evidence import _paint_metrics, _spec_metrics  # noqa: E402


RUN = ROOT / "_x_lab_work" / "official_m7"
METRICS = RUN / "metrics"
THUMBS = RUN / "thumbnails" / "monolithic"
SCORECARD = RUN / "scorecard_x_lab.js"
REPORT = RUN / "report.json"


def _shipping_scorecard() -> dict[str, dict[str, object]]:
    source = (ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"=\s*(\{.*\});", source, flags=re.S)
    if match is None:
        raise RuntimeError("could not parse shipping scorecard")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def _shipping_template() -> dict[str, object]:
    data = _shipping_scorecard()
    for key, row in data.items():
        if key.startswith("monolithic:"):
            return dict(row)
    raise RuntimeError("no monolithic scorecard template")


def _row(template: dict[str, object], recipe, paint: np.ndarray, spec: np.ndarray, elapsed: float) -> dict[str, object]:
    pm, sm = _paint_metrics(paint), _spec_metrics(spec)
    row = dict(template)
    row.update({
        "id": recipe.fid,
        "name": recipe.name,
        "category": "X LAB",
        "surface": "Special / Monolithic",
        "surface_kind": "monolithic",
        "priority": "KEEP-CANDIDATE",
        "status": "LIVE-DEV-CANDIDATE",
        "qualityProfile": "expressive_finish",
        "estimated2048Ms": round(elapsed * 1000.0, 3),
        "paintLumaStd": round(pm["paint_luma_std"], 6),
        "paintLumaSpan": round(pm["paint_luma_span"], 6),
        "paintFineEnergy": round(pm["paint_fine_energy"], 6),
        "paintResidualEnergy": round(pm["paint_residual_energy"], 6),
        "paintBlockEnergy": round(pm["paint_block_energy"], 6),
        "paintMacroEnergy": round(pm["paint_macro_energy"], 6),
        "paintMicroMacroRatio": round(pm["paint_micro_macro_ratio"], 6),
        "paintColorPopulation": int(pm["paint_color_population"]),
        "paintSaturationMean": round(pm["paint_saturation_mean"], 6),
        "specMRange": round(sm["m_range"], 6),
        "specRRange": round(sm["r_range"], 6),
        "specCcRange": round(sm["cc_range"], 6),
        "specMStd": round(sm["m_std"], 6),
        "specRStd": round(sm["r_std"], 6),
        "specCcStd": round(sm["cc_std"], 6),
        "specChannelIndependence": round(sm["independence"], 6),
    })
    return row


def _run(module: str, env: dict[str, str], *, thumbs: bool = False) -> None:
    extra = f"m.THUMBS=Path(r'{THUMBS}'); " if thumbs else ""
    code = (
        f"from pathlib import Path; import {module} as m; "
        f"m.SCORECARD=Path(r'{SCORECARD}'); m.OUT_DIR=Path(r'{METRICS}'); {extra}"
        "raise SystemExit(m.main())"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                            text=True, encoding="utf-8", errors="replace", capture_output=True)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-4000:])


def _run_xlab_m2(env: dict[str, str]) -> None:
    """Disable the generic name proxy for this explicit recipe contract.

    This mirrors the existing Fractured explicit-recipe exemption without
    claiming a token-derived intent for coined X LAB names.  The visual/tile
    and M5 material evidence remain required; M2 simply has no honest generic
    vocabulary opinion here.
    """
    code = (
        f"from pathlib import Path; import scripts.spb_workbook_compute_m2 as m; "
        "m.FRACTURED_EXPLICIT_RECIPE_CATEGORIES=m.FRACTURED_EXPLICIT_RECIPE_CATEGORIES|frozenset({'X LAB'}); "
        f"m.SCORECARD=Path(r'{SCORECARD}'); m.OUT_DIR=Path(r'{METRICS}'); raise SystemExit(m.main())"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                            text=True, encoding="utf-8", errors="replace", capture_output=True)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-4000:])


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    METRICS.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    shipping = _shipping_scorecard()
    template = _shipping_template()
    scorecard: dict[str, dict[str, object]] = {}
    direct: dict[str, dict[str, object]] = {}
    for recipe in RECIPES:
        started = time.perf_counter()
        paint, spec = arrays(recipe.fid)
        elapsed = time.perf_counter() - started
        native_paint = cv2.resize(paint, (2048, 2048), interpolation=cv2.INTER_CUBIC)
        native_spec = cv2.resize(spec, (2048, 2048), interpolation=cv2.INTER_NEAREST)
        key = "monolithic:" + recipe.fid
        scorecard[key] = _row(template, recipe, native_paint, native_spec, elapsed)
        thumb = cv2.resize(np.clip(native_paint * 255.0, 0, 255).astype(np.uint8), (512, 512), interpolation=cv2.INTER_AREA)
        if not cv2.imwrite(str(THUMBS / f"{recipe.fid}.png"), cv2.cvtColor(thumb, cv2.COLOR_RGB2BGR)):
            raise OSError(recipe.fid)
        direct[key] = {"name": recipe.name, "builder_seconds": round(elapsed, 5)}
    SCORECARD.write_text("window.SPB_X_LAB_SCORECARD = " + json.dumps(scorecard, indent=2) + ";\n", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    _run("scripts.spb_workbook_compute_m1", env, thumbs=True)
    _run_xlab_m2(env)
    _run("scripts.spb_workbook_compute_m6", env)
    # M5 is percentile-based.  Evaluate candidate ranges against the actual
    # catalog so "all candidates share full 0–255 range" does not falsely
    # register as a dead spec map merely because an isolated cohort ties.
    merged = dict(shipping)
    merged.update(scorecard)
    SCORECARD.write_text("window.SPB_X_LAB_SCORECARD = " + json.dumps(merged, indent=2) + ";\n", encoding="utf-8")
    _run("scripts.spb_workbook_compute_m5", env)
    SCORECARD.write_text("window.SPB_X_LAB_SCORECARD = " + json.dumps(scorecard, indent=2) + ";\n", encoding="utf-8")
    code = (
        f"from pathlib import Path; import scripts.spb_workbook_compute_m7 as m; "
        f"m.SCORECARD=Path(r'{SCORECARD}'); m.OUT_DIR=Path(r'{METRICS}'); "
        f"m.M1=m.OUT_DIR/'m1_sibling_diff.json'; m.M2=m.OUT_DIR/'m2_intent_fit.json'; "
        f"m.M5=m.OUT_DIR/'m5_spec_paint_coherence.json'; m.M6=m.OUT_DIR/'m6_intent_floor_ceiling.json'; raise SystemExit(m.main())"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                            text=True, encoding="utf-8", errors="replace", capture_output=True)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-4000:])
    m7 = json.loads((METRICS / "m7_composite.json").read_text(encoding="utf-8"))["byFinish"]
    scores = {key: m7[key].get("composite") for key in scorecard}
    report = {"ship_bar": 85.0, "scores": scores,
              "failed": {key: value for key, value in scores.items() if not isinstance(value, (int, float)) or value < 85.0},
              "builders": direct}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": len(scorecard) - len(report["failed"]), "failed": report["failed"]}, indent=2))
    return 0 if not report["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
