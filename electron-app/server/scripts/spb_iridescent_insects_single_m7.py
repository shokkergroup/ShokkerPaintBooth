# -*- coding: utf-8 -*-
"""Run an isolated official M5/M6/M7 gate for one Insects BASE renderer.

SPB-105 / owner 2026-09-01.  The shipping scorecard is read-only.  This
adapter renders the candidate directly at 2048 square, replaces only its
row in an evidence scorecard, and evaluates that row with the official
workbook modules.  Global M1/M2 remain the current catalog/name evidence.
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

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spb_wilds_m7_evidence import _paint_metrics, _spec_metrics  # noqa: E402
from scripts.spb_finish_identity import (  # noqa: E402
    contract_from_module,
    validate_identity_key_uniqueness,
)
from scripts.spb_finish_law import (  # noqa: E402
    MAX_DEAD,
    MIN_FINE,
    MIN_FOLLOW,
    coverage_axis,
    follow_axis,
    richness_axis,
    richness_eff,
    scale_axis,
)


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
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"{module} failed: {(result.stdout + result.stderr)[-3000:]}")


def _render(candidate, paint_name: str, spec_name: str, seed: int) -> tuple[np.ndarray, np.ndarray]:
    shape = (2048, 2048)
    paint = np.zeros((2048, 2048, 3), dtype=np.float32)
    mask = np.ones((2048, 2048), dtype=np.float32)
    painted = getattr(candidate, paint_name)(paint, shape, mask, seed, 1.0, None)
    m, r, cc = getattr(candidate, spec_name)(shape, seed, 1.0, 128.0, 128.0)
    spec = np.stack([m, r, cc], axis=2).astype(np.float32)
    return np.clip(painted, 0.0, 1.0), np.clip(spec, 0.0, 255.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("finish_id")
    parser.add_argument("paint_function")
    parser.add_argument("spec_function")
    parser.add_argument("evidence_dir")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--template-id", default=None,
                        help="Existing BASE scorecard row to clone for a net-new candidate")
    args = parser.parse_args()

    candidate = importlib.import_module(args.module)
    identity_contract = contract_from_module(candidate, args.finish_id)
    prior_contracts = list((ROOT / "_iridescent_insects_2026").glob("*/identity_contract.json"))
    validate_identity_key_uniqueness(identity_contract, prior_contracts).require()
    paint, spec = _render(candidate, args.paint_function, args.spec_function, args.seed)
    pm, sm = _paint_metrics(paint), _spec_metrics(spec)
    paint_luma = (
        0.2126 * paint[..., 0] + 0.7152 * paint[..., 1] + 0.0722 * paint[..., 2]
    ).astype(np.float32)
    spec_unit = spec / 255.0
    spec_luma = (
        0.2126 * spec_unit[..., 0] + 0.7152 * spec_unit[..., 1] + 0.0722 * spec_unit[..., 2]
    ).astype(np.float32)
    paint_band, _paint_coarse = scale_axis(paint_luma)
    spec_band, _spec_coarse = scale_axis(spec_luma)
    follow_mi, follow_edge = follow_axis(paint, spec)
    dead = coverage_axis(paint)
    material_count, shade_count = richness_axis(spec)
    finish_law = {
        "fine": max(paint_band, spec_band),
        "paint_band": paint_band,
        "spec_band": spec_band,
        "follow_mi": follow_mi,
        "follow_edge": follow_edge,
        "dead": dead,
        "material_count": material_count,
        "shade_count": shade_count,
        "effective_materials": richness_eff(spec),
    }
    finish_law["pass"] = bool(
        finish_law["fine"] >= MIN_FINE
        and finish_law["follow_edge"] >= MIN_FOLLOW
        and finish_law["dead"] <= MAX_DEAD
    )
    run = (ROOT / args.evidence_dir).resolve()
    run.mkdir(parents=True, exist_ok=True)
    paint_u8 = np.clip(paint * 255.0, 0, 255).astype(np.uint8)
    spec_u8 = np.clip(spec, 0, 255).astype(np.uint8)
    Image.fromarray(paint_u8, "RGB").save(run / "paint_2048.png", optimize=True)
    Image.fromarray(spec_u8, "RGB").save(run / "mrc_2048.png", optimize=True)
    paint_pick = Image.fromarray(paint_u8, "RGB").resize((512, 512), Image.Resampling.LANCZOS)
    spec_pick = Image.fromarray(spec_u8, "RGB").resize((512, 512), Image.Resampling.LANCZOS)
    picker = Image.new("RGB", (1024, 512))
    picker.paste(paint_pick, (0, 0)); picker.paste(spec_pick, (512, 0))
    picker.save(run / "picker_split.png", optimize=True)
    identity_path = run / "identity_contract.json"
    identity_path.write_text(
        json.dumps(identity_contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    identity_gate = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "spb_iridescent_insects_similarity_gate.py"),
            "--replace", f"{args.finish_id}={run / 'picker_split.png'}", "--fail",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    identity_output = identity_gate.stdout + identity_gate.stderr
    (run / "identity_gate.txt").write_text(identity_output, encoding="utf-8")
    if identity_gate.returncode:
        raise RuntimeError(
            "Cross-card identity gate failed before M7:\n" + identity_output[-5000:]
        )
    metrics = run / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    score_path = run / "scorecard_candidate_eval.js"
    report_path = run / "m7_report.json"
    scorecard = _scorecard()
    key = f"base:{args.finish_id}"
    if key not in scorecard:
        if not args.template_id:
            raise KeyError(f"candidate missing from shipping scorecard: {key}")
        template_key = f"base:{args.template_id}"
        if template_key not in scorecard:
            raise KeyError(f"template missing from shipping scorecard: {template_key}")
        scorecard[key] = dict(scorecard[template_key])
    row = dict(scorecard[key])
    row.update({
        "id": args.finish_id,
        "name": args.finish_id.replace("_", " ").title(),
        "category": "Iridescent Insects",
        "surface": "Base",
        "surface_kind": "base",
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
    scorecard[key] = row
    score_path.write_text(
        "// Isolated Iridescent Insects candidate evidence; never shipped.\n"
        "window.SPB_IRIDESCENT_INSECTS_CANDIDATE_SCORECARD = "
        + json.dumps(scorecard, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    _run("scripts.spb_workbook_compute_m5", score_path, metrics)
    _run("scripts.spb_workbook_compute_m6", score_path, metrics)
    _run(
        "scripts.spb_workbook_compute_m7", score_path, metrics,
        f"m.M1=Path(r'{ROOT / '_workbook_metrics/m1_sibling_diff.json'}'); "
        f"m.M2=Path(r'{ROOT / '_workbook_metrics/m2_intent_fit.json'}'); "
        "m.M5=out/'m5_spec_paint_coherence.json'; "
        "m.M6=out/'m6_intent_floor_ceiling.json'; ",
    )
    rows = json.loads((metrics / "m7_composite.json").read_text(encoding="utf-8"))["byFinish"]
    entry = rows[key]
    composite = entry.get("composite")
    payload = {
        "schema": "spb-iridescent-insects-single-candidate-m7/1",
        "id": args.finish_id,
        "module": args.module,
        "ship_bar": 85.0,
        "composite": composite,
        "pass": bool(
            isinstance(composite, (int, float))
            and composite >= 85.0
            and finish_law["pass"]
        ),
        "intent": entry.get("intent"),
        "components": entry.get("components"),
        "paint_metrics": pm,
        "spec_metrics": sm,
        "identity_contract": identity_contract,
        "identity_gate": "pass",
        "finish_law": finish_law,
    }
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
