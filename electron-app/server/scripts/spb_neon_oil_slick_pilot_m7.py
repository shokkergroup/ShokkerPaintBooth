"""Run the official workbook M1/M2/M5/M6/M7 stack on isolated Neon pilots.

The candidates remain unwired.  This script creates a private scorecard and a
private Neon-only thumbnail tree beneath the evidence directory, refreshes the
candidate rows from their real paint/spec arrays, and invokes the unchanged
official workbook modules against that isolated state.
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

from scripts.spb_wilds_m7_evidence import _paint_metrics, _spec_metrics  # noqa: E402
from engine.paint_v2 import neon_material_core_v3 as core  # noqa: E402


RUN = ROOT / "_neon_oil_slick_reset_work" / "isolated_official_m7"
METRICS = RUN / "metrics"
THUMBS = RUN / "thumbnails"
SCORECARD = RUN / "scorecard_neon_pilots.js"
REPORT = ROOT / "_neon_oil_slick_reset_work" / "official_isolated_m7.json"

CANDIDATES = (
    {
        "slug": "blue_breakdown",
        "module": "engine.expansions.neon_underground_v3.blue_breakdown",
        "builder": "build_blue_breakdown",
        "key": "base:neon_electric_blue",
    },
    {
        "slug": "sodium_scuff",
        "module": "engine.expansions.neon_underground_v3.sodium_scuff",
        "builder": "build_sodium_scuff",
        "key": "base:neon_orange_hazard",
    },
    {
        "slug": "redline_shear",
        "module": "engine.expansions.neon_underground_v3.redline_shear",
        "builder": "build_redline_shear",
        "key": "base:neon_red_alert",
    },
    {
        "slug": "quarter_mile_weave",
        "module": "engine.expansions.neon_underground_v3.quarter_mile_weave",
        "builder": "build",
        "key": "monolithic:neon2_quarter_mile_weave",
    },
    {
        "slug": "torque_scar",
        "module": "engine.expansions.neon_underground_v3.torque_scar",
        "builder": "build_torque_scar",
        "key": "monolithic:neon2_torque_scar",
    },
    {
        "slug": "ultraviolet_bloom",
        "module": "engine.expansions.neon_underground_v3.ultraviolet_bloom",
        "builder": "build_ultraviolet_bloom",
        "key": "base:neon_blacklight",
    },
    {
        "slug": "phantom_mica",
        "module": "engine.expansions.neon_underground_v3.phantom_mica",
        "builder": "build_phantom_mica",
        "key": "monolithic:neon2_phantom_mica",
    },
    {
        "slug": "frequency_fault",
        "module": "engine.expansions.neon_underground_v3.frequency_fault",
        "builder": "build_frequency_fault",
        "key": "monolithic:neon2_frequency_fault",
    },
    {
        "slug": "voltage_plate",
        "module": "engine.expansions.neon_underground_v3.voltage_plate",
        "builder": "build_voltage_plate",
        "key": "base:neon_cyber_yellow",
    },
    {
        "slug": "janus_lensfield",
        "module": "engine.expansions.neon_underground_v3.janus_lensfield",
        "builder": "build_janus_lensfield",
        "key": "base:neon_dual_glow",
    },
    {
        "slug": "cryoglass_fiber",
        "module": "engine.expansions.neon_underground_v3.cryoglass_fiber",
        "builder": "build_cryoglass_fiber",
        "key": "base:neon_ice_white",
    },
    {
        "slug": "emberwake_delam",
        "module": "engine.expansions.neon_underground_v3.emberwake_delam",
        "builder": "build_emberwake_delam",
        "key": "monolithic:neon2_emberwake_delam",
    },
    {
        "slug": "pink_quench",
        "module": "engine.expansions.neon_underground_v3.pink_quench",
        "builder": "build_pink_quench",
        "key": "base:neon_pink_blaze",
    },
    {
        "slug": "prism_fault",
        "module": "engine.expansions.neon_underground_v3.prism_fault",
        "builder": "build_prism_fault",
        "key": "base:neon_rainbow_tube",
    },
    {
        "slug": "radium_capillary",
        "module": "engine.expansions.neon_underground_v3.radium_capillary",
        "builder": "build_radium_capillary",
        "key": "base:neon_toxic_green",
    },
    {
        "slug": "vacuum_phosphor",
        "module": "engine.expansions.neon_underground_v3.vacuum_phosphor",
        "builder": "build_vacuum_phosphor",
        "key": "monolithic:neon2_sign_tubes",
    },
    {
        "slug": "copper_ghost",
        "module": "engine.expansions.neon_underground_v3.copper_ghost",
        "builder": "build_copper_ghost",
        "key": "monolithic:neon2_circuit_city",
    },
    {
        "slug": "fresnel_rain_skin",
        "module": "engine.expansions.neon_underground_v3.fresnel_rain_skin",
        "builder": "build_fresnel_rain_skin",
        "key": "monolithic:neon2_rain",
    },
    {
        "slug": "pulse_ablation",
        "module": "engine.expansions.neon_underground_v3.pulse_ablation",
        "builder": "build_pulse_ablation",
        "key": "monolithic:neon2_laser_web",
    },
    {
        "slug": "burner_impact",
        "module": "engine.expansions.neon_underground_v3.burner_impact",
        "builder": "build_burner_impact",
        "key": "monolithic:neon2_splatter",
    },
    {
        "slug": "live_mesh_delam",
        "module": "engine.expansions.neon_underground_v3.live_mesh_delam",
        "builder": "build_live_mesh_delam",
        "key": "monolithic:neon2_wireframe",
    },
    {
        "slug": "boost_helix",
        "module": "engine.expansions.neon_underground_v3.boost_helix",
        "builder": "build_boost_helix",
        "key": "monolithic:neon2_plasma_tubes",
    },
    {
        "slug": "electrocell",
        "module": "engine.expansions.neon_underground_v3.electrocell",
        "builder": "build_electrocell",
        "key": "monolithic:neon2_honeycomb",
    },
    {
        "slug": "pulsefoil_pleats",
        "module": "engine.expansions.neon_underground_v3.pulsefoil_pleats",
        "builder": "build_pulsefoil_pleats",
        "key": "monolithic:neon2_flow_tubes",
    },
    {
        "slug": "velvet_static",
        "module": "engine.expansions.neon_underground_v3.velvet_static",
        "builder": "build_velvet_static",
        "key": "monolithic:neon2_synthwave_sun",
    },
)


def _load_shipping_scorecard() -> dict[str, dict[str, Any]]:
    source = (ROOT / "paint-booth-0-catalog-scorecard.js").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"=\s*(\{.*\});", source, flags=re.S)
    if match is None:
        raise RuntimeError("could not parse shipping scorecard")
    return json.loads(re.sub(r"//[^\n]*", "", match.group(1)))


def _write_candidate_thumb(key: str, paint: np.ndarray) -> None:
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
    # M1 only needs the actual siblings in this category.  Keep the isolated
    # tree compact instead of duplicating thousands of unrelated thumbnails.
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
    template: dict[str, Any], key: str, paint_array: np.ndarray,
    spec_array: np.ndarray, elapsed: float,
) -> dict[str, Any]:
    paint = _paint_metrics(paint_array)
    spec = _spec_metrics(spec_array)
    surface = "Base" if key.startswith("base:") else "Special / Monolithic"
    row = dict(template)
    row.update({
        "surface": surface,
        "surface_kind": "base" if key.startswith("base:") else "monolithic",
        "category": "Neon",
        "priority": "KEEP-CANDIDATE",
        "status": "ISOLATED",
        "estimated2048Ms": round(float(elapsed * 1000.0), 3),
        "qualityProfile": "expressive_finish",
        "paintLumaStd": round(paint["paint_luma_std"], 6),
        "paintLumaSpan": round(paint["paint_luma_span"], 6),
        "paintFineEnergy": round(paint["paint_fine_energy"], 6),
        "paintResidualEnergy": round(paint["paint_residual_energy"], 6),
        "paintBlockEnergy": round(paint["paint_block_energy"], 6),
        "paintMacroEnergy": round(paint["paint_macro_energy"], 6),
        "paintMicroMacroRatio": round(paint["paint_micro_macro_ratio"], 6),
        "paintColorPopulation": int(paint["paint_color_population"]),
        "paintSaturationMean": round(paint["paint_saturation_mean"], 6),
        "specMRange": round(spec["m_range"], 6),
        "specRRange": round(spec["r_range"], 6),
        "specCcRange": round(spec["cc_range"], 6),
        "specMStd": round(spec["m_std"], 6),
        "specRStd": round(spec["r_std"], 6),
        "specCcStd": round(spec["cc_std"], 6),
        "specChannelIndependence": round(spec["independence"], 6),
    })
    return row


def main() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    METRICS.mkdir(parents=True, exist_ok=True)
    scorecard = _load_shipping_scorecard()
    _copy_neon_siblings(scorecard)

    template = dict(scorecard["base:neon_electric_blue"])
    direct: dict[str, dict[str, Any]] = {}
    for candidate in CANDIDATES:
        module = importlib.import_module(str(candidate["module"]))
        builder = getattr(module, str(candidate["builder"]))
        start = time.perf_counter()
        result = builder()
        paint_native, spec_native = core.resize_result(result)
        elapsed = time.perf_counter() - start
        key = str(candidate["key"])
        original = scorecard.get(key, template)
        scorecard[key] = _candidate_row(original, key, paint_native, spec_native, elapsed)
        _write_candidate_thumb(key, paint_native)
        direct[key] = {
            "slug": candidate["slug"],
            "finish_id": result.finish_id,
            "builder_seconds": round(elapsed, 6),
            "paint_metrics": _paint_metrics(paint_native),
            "spec_metrics": _spec_metrics(spec_native),
        }

    SCORECARD.write_text(
        "// Isolated Neon pilot workbook evidence; never shipped.\n"
        "window.SPB_NEON_PILOT_SCORECARD = "
        + json.dumps(scorecard, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    # M1 owns an extra THUMBS input. All other modules share SCORECARD/OUT_DIR.
    m1_code = (
        f"from pathlib import Path; score=Path(r'{SCORECARD}'); out=Path(r'{METRICS}'); "
        f"thumbs=Path(r'{THUMBS}'); import scripts.spb_workbook_compute_m1 as m; "
        "m.SCORECARD=score; m.OUT_DIR=out; m.THUMBS=thumbs; raise SystemExit(m.main())"
    )
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    m1_result = subprocess.run(
        [sys.executable, "-c", m1_code], cwd=ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", capture_output=True,
    )
    if m1_result.returncode:
        raise RuntimeError((m1_result.stdout + m1_result.stderr)[-5000:])

    for module_name in (
        "scripts.spb_workbook_compute_m2",
        "scripts.spb_workbook_compute_m5",
        "scripts.spb_workbook_compute_m6",
    ):
        code = (
            f"from pathlib import Path; score=Path(r'{SCORECARD}'); out=Path(r'{METRICS}'); "
            f"import {module_name} as m; m.SCORECARD=score; m.OUT_DIR=out; "
            "raise SystemExit(m.main())"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=ROOT, env=env,
            text=True, encoding="utf-8", errors="replace", capture_output=True,
        )
        if result.returncode:
            raise RuntimeError(f"{module_name}: {(result.stdout + result.stderr)[-5000:]}")

    m7_code = (
        f"from pathlib import Path; score=Path(r'{SCORECARD}'); out=Path(r'{METRICS}'); "
        "import scripts.spb_workbook_compute_m7 as m; m.SCORECARD=score; m.OUT_DIR=out; "
        "m.M1=out/'m1_sibling_diff.json'; m.M2=out/'m2_intent_fit.json'; "
        "m.M5=out/'m5_spec_paint_coherence.json'; m.M6=out/'m6_intent_floor_ceiling.json'; "
        "raise SystemExit(m.main())"
    )
    m7_result = subprocess.run(
        [sys.executable, "-c", m7_code], cwd=ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", capture_output=True,
    )
    if m7_result.returncode:
        raise RuntimeError((m7_result.stdout + m7_result.stderr)[-5000:])

    by_finish = json.loads((METRICS / "m7_composite.json").read_text(encoding="utf-8"))["byFinish"]
    rows: dict[str, dict[str, Any]] = {}
    for candidate in CANDIDATES:
        key = str(candidate["key"])
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
        "schema": "spb-neon-oil-slick-isolated-official-m7/2",
        "status": "ISOLATED-OWNER-REVIEW-NOT-WIRED",
        "ship_bar": 85.0,
        "official_workbook_modules": ["M1", "M2", "M5", "M6", "M7"],
        "all_pass_85": all(row["pass_85"] for row in rows.values()),
        "byFinish": rows,
        "scorecard": str(SCORECARD.relative_to(ROOT)).replace("\\", "/"),
        "metrics_dir": str(METRICS.relative_to(ROOT)).replace("\\", "/"),
        "shipping_state_changed": False,
    }
    REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_pass_85": payload["all_pass_85"],
        "scores": {key: row["composite"] for key, row in rows.items()},
    }, indent=2))
    return 0 if payload["all_pass_85"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
