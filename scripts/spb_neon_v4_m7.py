"""Run the official M1/M2/M5/M6/M7 stack on all 25 Neon v4 builders.

The run is isolated beneath ``_neon_v4_work``. It measures the new authored
arrays directly and never mutates the shipping scorecard. Owner-eye contact and
the v4 review report remain additional gates because v3 proved M7 alone cannot
validate art direction. SPB-105 / NU-V4.
"""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.neon_underground_v4.catalog import CATALOG, ORDER, module_name  # noqa: E402
from engine.expansions.neon_underground_v4.core import resize_result  # noqa: E402
from scripts.spb_wilds_m7_evidence import _paint_metrics, _spec_metrics  # noqa: E402


RUN = ROOT / "_neon_v4_work" / "official_m7"
METRICS = RUN / "metrics"
THUMBS = RUN / "thumbnails"
SCORECARD = RUN / "scorecard_neon_v4.js"
REPORT = RUN / "report.json"
BASE_IDS = {
    "neon_blacklight", "neon_cyber_yellow", "neon_dual_glow", "neon_electric_blue",
    "neon_ice_white", "neon_orange_hazard", "neon_pink_blaze", "neon_rainbow_tube",
    "neon_red_alert", "neon_toxic_green",
}


def _key(finish_id: str) -> str:
    return ("base:" if finish_id in BASE_IDS else "monolithic:") + finish_id


def _load_shipping_scorecard() -> dict[str, dict[str, Any]]:
    source = (ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"=\s*(\{.*\});", source, flags=re.S)
    if match is None:
        raise RuntimeError("could not parse shipping scorecard")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def _write_thumb(key: str, paint: np.ndarray) -> None:
    surface, finish_id = key.split(":", 1)
    folder = THUMBS / surface
    folder.mkdir(parents=True, exist_ok=True)
    rgb = cv2.resize(
        np.clip(np.asarray(paint, np.float32) * 255.0, 0, 255).astype(np.uint8),
        (512, 512), interpolation=cv2.INTER_AREA,
    )
    path = folder / f"{finish_id}.png"
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise OSError(path)


def _copy_neon_siblings(scorecard: dict[str, dict[str, Any]]) -> None:
    for key, row in scorecard.items():
        if row.get("category") != "Neon" or ":" not in key:
            continue
        surface, finish_id = key.split(":", 1)
        source = ROOT / "thumbnails" / surface / f"{finish_id}.png"
        if not source.is_file():
            continue
        destination = THUMBS / surface / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _candidate_row(
    template: dict[str, Any], key: str, paint: np.ndarray, spec: np.ndarray, elapsed: float,
) -> dict[str, Any]:
    pm = _paint_metrics(paint)
    sm = _spec_metrics(spec)
    row = dict(template)
    row.update({
        "surface": "Base" if key.startswith("base:") else "Special / Monolithic",
        "surface_kind": "base" if key.startswith("base:") else "monolithic",
        "category": "Neon",
        "priority": "KEEP-CANDIDATE",
        "status": "LIVE-DEV-CANDIDATE",
        "estimated2048Ms": round(float(elapsed * 1000.0), 3),
        "qualityProfile": "expressive_finish",
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


def _run_module(module: str, scorecard: Path, out: Path, env: dict[str, str]) -> None:
    code = (
        f"from pathlib import Path; score=Path(r'{scorecard}'); out=Path(r'{out}'); "
        f"import {module} as m; m.SCORECARD=score; m.OUT_DIR=out; "
        "raise SystemExit(m.main())"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, text=True,
        encoding="utf-8", errors="replace", capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"{module}: {(result.stdout + result.stderr)[-5000:]}")


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    METRICS.mkdir(parents=True, exist_ok=True)
    scorecard = _load_shipping_scorecard()
    _copy_neon_siblings(scorecard)
    template = dict(scorecard["base:neon_electric_blue"])
    direct: dict[str, dict[str, Any]] = {}

    for finish_id in ORDER:
        module = importlib.import_module(module_name(finish_id))
        started = time.perf_counter()
        result = module.build()
        paint_native, paint_b_native, spec_native = resize_result(result)
        elapsed = time.perf_counter() - started
        key = _key(finish_id)
        scorecard[key] = _candidate_row(scorecard.get(key, template), key, paint_native, spec_native, elapsed)
        _write_thumb(key, paint_native)
        delta = np.mean(np.abs(paint_native - paint_b_native), axis=2)
        direct[key] = {
            "finish_id": finish_id,
            "name": CATALOG[finish_id][1],
            "module": module_name(finish_id),
            "builder_seconds": round(elapsed, 6),
            "angle_delta_mean": round(float(delta.mean()), 6),
            "angle_delta_p95": round(float(np.percentile(delta, 95)), 6),
            "paint_metrics": _paint_metrics(paint_native),
            "spec_metrics": _spec_metrics(spec_native),
        }

    SCORECARD.write_text(
        "// Isolated Neon v4 workbook evidence; generated, never hand-edited.\n"
        "window.SPB_NEON_V4_SCORECARD = "
        + json.dumps(scorecard, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    m1_code = (
        f"from pathlib import Path; score=Path(r'{SCORECARD}'); out=Path(r'{METRICS}'); "
        f"thumbs=Path(r'{THUMBS}'); import scripts.spb_workbook_compute_m1 as m; "
        "m.SCORECARD=score; m.OUT_DIR=out; m.THUMBS=thumbs; raise SystemExit(m.main())"
    )
    m1 = subprocess.run(
        [sys.executable, "-c", m1_code], cwd=ROOT, env=env, text=True,
        encoding="utf-8", errors="replace", capture_output=True,
    )
    if m1.returncode:
        raise RuntimeError((m1.stdout + m1.stderr)[-5000:])
    for module in ("scripts.spb_workbook_compute_m2", "scripts.spb_workbook_compute_m5",
                   "scripts.spb_workbook_compute_m6"):
        _run_module(module, SCORECARD, METRICS, env)
    m7_code = (
        f"from pathlib import Path; score=Path(r'{SCORECARD}'); out=Path(r'{METRICS}'); "
        "import scripts.spb_workbook_compute_m7 as m; m.SCORECARD=score; m.OUT_DIR=out; "
        "m.M1=out/'m1_sibling_diff.json'; m.M2=out/'m2_intent_fit.json'; "
        "m.M5=out/'m5_spec_paint_coherence.json'; m.M6=out/'m6_intent_floor_ceiling.json'; "
        "raise SystemExit(m.main())"
    )
    m7 = subprocess.run(
        [sys.executable, "-c", m7_code], cwd=ROOT, env=env, text=True,
        encoding="utf-8", errors="replace", capture_output=True,
    )
    if m7.returncode:
        raise RuntimeError((m7.stdout + m7.stderr)[-5000:])

    by_finish = json.loads((METRICS / "m7_composite.json").read_text(encoding="utf-8"))["byFinish"]
    rows: dict[str, dict[str, Any]] = {}
    for finish_id in ORDER:
        key = _key(finish_id)
        workbook = by_finish[key]
        composite = workbook.get("composite")
        rows[key] = {
            **direct[key],
            "composite": composite,
            "pass_85": isinstance(composite, (int, float)) and composite >= 85.0,
            "intent": workbook.get("intent"),
            "components": workbook.get("components"),
            "tier": workbook.get("tier"),
        }
    payload = {
        "schema": "spb-neon-v4-official-m7/1",
        "status": "LIVE-DEV-CANDIDATE-OWNER-EYE-GOVERNS",
        "ship_bar": 85.0,
        "all_pass_85": all(row["pass_85"] for row in rows.values()),
        "byFinish": rows,
        "scorecard": str(SCORECARD.relative_to(ROOT)).replace("\\", "/"),
        "metrics_dir": str(METRICS.relative_to(ROOT)).replace("\\", "/"),
    }
    REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_pass_85": payload["all_pass_85"],
        "scores": {key: row["composite"] for key, row in rows.items()},
    }, indent=2))
    return 0 if payload["all_pass_85"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
