from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image


OWNER_CONFIRMED_COLOR_CLASH_IDS = [
    "cc_plasma_edge",
    "cc_chemical_spill",
    "cc_electric_conflict",
    "cc_fever_dream",
    "cc_neon_bruise",
    "cc_neon_war",
    "cc_nuclear_dawn",
    "cc_toxic_sunset",
    "cc_ultraviolet_burn",
    "cc_blood_orange",
    "cc_acid_burn",
    "cc_bruised_sky",
    "cc_candy_poison",
    "cc_coral_venom",
    "cc_deep_friction",
    "cc_digital_rot",
    "cc_flash_burn",
    "cc_magma_freeze",
    "cc_radioactive",
    "cc_rust_vs_ice",
    "cc_solar_clash",
    "cc_venom_strike",
    "cc_voltage_split",
]


def test_owner_confirmed_color_clash_v2_is_detailed_and_distinct():
    from scripts import spb_visual_workbench

    out_dir = Path(".pytest-tmp") / "color_clash_owner_confirmed"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_COLOR_CLASH_IDS),
        "--kind",
        "monolithic",
        "--size",
        "96",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_COLOR_CLASH_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["paint_luma_std"] for row in rows) > 0.045
    assert min(row["fine_energy"] for row in rows) > 0.070
    assert min(row["residual_energy"] for row in rows) > 0.030
    assert min(row["color_population"] for row in rows) >= 10
    assert min(row["spec_cc_range"] for row in rows) >= 120.0

    vectors = {}
    luma_vectors = {}
    spec_vectors = {}
    spec_luma_vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)
        luma = img.convert("L")
        luma_arr = np.asarray(luma, dtype=np.float32).reshape(-1)
        luma_vectors[row["id"]] = (luma_arr - float(luma_arr.mean())) / (float(luma_arr.std()) + 1e-6)
        spec_img = Image.open(out_dir / row["files"]["spec_preview"]).convert("RGB").resize((32, 32))
        spec_arr = np.asarray(spec_img, dtype=np.float32).reshape(-1)
        spec_vectors[row["id"]] = (spec_arr - float(spec_arr.mean())) / (float(spec_arr.std()) + 1e-6)
        spec_luma = spec_img.convert("L")
        spec_luma_arr = np.asarray(spec_luma, dtype=np.float32).reshape(-1)
        spec_luma_vectors[row["id"]] = (
            spec_luma_arr - float(spec_luma_arr.mean())
        ) / (float(spec_luma_arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.98

    max_abs_luma_corr = max(
        abs(float(np.dot(luma_vectors[a], luma_vectors[b]) / len(luma_vectors[a])))
        for a, b in itertools.combinations(luma_vectors, 2)
    )
    assert max_abs_luma_corr < 0.82

    max_abs_spec_corr = max(
        abs(float(np.dot(spec_vectors[a], spec_vectors[b]) / len(spec_vectors[a])))
        for a, b in itertools.combinations(spec_vectors, 2)
    )
    assert max_abs_spec_corr < 0.95

    max_abs_spec_luma_corr = max(
        abs(float(np.dot(spec_luma_vectors[a], spec_luma_vectors[b]) / len(spec_luma_vectors[a])))
        for a, b in itertools.combinations(spec_luma_vectors, 2)
    )
    assert max_abs_spec_luma_corr < 0.82
