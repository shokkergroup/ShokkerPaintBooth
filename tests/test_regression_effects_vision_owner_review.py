from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image

from engine.expansions import owner_review_effects


OWNER_CONFIRMED_EFFECTS_FIRST_WAVE_IDS = [
    "cel_shade",
    "cursed",
    "datamosh",
    "glitch",
    "infrared",
]


OWNER_CONFIRMED_EFFECTS_SPB67_WAVE1_IDS = [
    "negative",
    "polarized",
    "graveyard",
    "reaper",
    "halftone",
    "phantom",
    "chromatic_aberration",
    "refraction",
]


OWNER_CONFIRMED_EFFECTS_SPB67_WAVE2_IDS = [
    "double_exposure",
    "gargoyle",
    "death_metal",
    "necrotic",
    "fish_eye",
    "embossed",
    "shadow_realm",
    "nightmare",
]


OWNER_CONFIRMED_EFFECTS_SPB67_WAVE3_IDS = [
    "x_ray",
    "catacombs",
    "film_burn",
    "long_exposure",
    "solarization",
    "parallax",
    "voodoo",
    "iron_maiden",
]


OWNER_CONFIRMED_EFFECTS_SPB67_WAVE4_IDS = [
    "eclipse",
    "demon_forge",
    "dark_ritual",
    "banshee",
    "hellhound",
    "lich_king",
    "spectral",
    "haunted",
]


OWNER_CONFIRMED_EFFECTS_SPB67_WAVE5_IDS = [
    "kaleidoscope",
    "aurora",
    "holographic_wrap",
    "uv_blacklight",
    "wraith",
    "possessed",
    "crt_scanline",
    "thermochromic",
]


OWNER_CONFIRMED_EFFECTS_SPB67_WAVE6_IDS = [
    "blood_oath",
    "rust",
]


OWNER_REJECTED_EFFECTS_PERF_AND_CONCEPT_FIX_IDS = [
    "reaper",
    "film_burn",
]


def test_owner_confirmed_effects_first_wave_is_semantic_and_distinct():
    from scripts import spb_visual_workbench

    out_dir = Path(".pytest-tmp") / "effects_vision_owner_first_wave"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_EFFECTS_FIRST_WAVE_IDS),
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
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_EFFECTS_FIRST_WAVE_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["paint_luma_std"] for row in rows) > 0.050
    assert min(row["fine_energy"] for row in rows) > 0.030
    assert min(row["residual_energy"] for row in rows) > 0.025
    assert min(row["color_population"] for row in rows) >= 6
    assert min(row["spec_m_range"] for row in rows) >= 150.0
    assert min(row["spec_r_range"] for row in rows) >= 110.0

    vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.97


def test_spb67_effects_vision_wave1_uses_source_owned_v4_micro_spec_models():
    from scripts import spb_visual_workbench

    for effect_id in OWNER_CONFIRMED_EFFECTS_SPB67_WAVE1_IDS:
        spec_fn, paint_fn = owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS[effect_id]
        expected = "_v5" if effect_id == "reaper" else "_v4"
        assert spec_fn.__name__.endswith(expected)
        assert paint_fn.__name__.endswith(expected)

    out_dir = Path(".pytest-tmp") / "effects_vision_spb67_wave1"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE1_IDS),
        "--kind",
        "monolithic",
        "--size",
        "128",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE1_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["paint_luma_std"] for row in rows) > 0.024
    assert min(row["fine_energy"] for row in rows) > 0.035
    assert min(row["residual_energy"] for row in rows) > 0.015
    assert min(row["color_population"] for row in rows) >= 7
    assert min(row["spec_m_range"] for row in rows) >= 140.0
    assert min(row["spec_cc_range"] for row in rows) >= 175.0

    vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.97


def test_spb67_effects_vision_wave2_uses_source_owned_v4_micro_spec_models():
    from scripts import spb_visual_workbench

    for effect_id in OWNER_CONFIRMED_EFFECTS_SPB67_WAVE2_IDS:
        spec_fn, paint_fn = owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS[effect_id]
        assert spec_fn.__name__.endswith("_v4")
        assert paint_fn.__name__.endswith("_v4")

    out_dir = Path(".pytest-tmp") / "effects_vision_spb67_wave2"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE2_IDS),
        "--kind",
        "monolithic",
        "--size",
        "128",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE2_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["fine_energy"] for row in rows) > 0.030
    assert min(row["residual_energy"] for row in rows) > 0.014
    assert min(row["color_population"] for row in rows) >= 5
    assert min(row["spec_m_range"] for row in rows) >= 140.0
    assert min(row["spec_cc_range"] for row in rows) >= 165.0

    vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.97


def test_spb67_effects_vision_wave3_uses_source_owned_v5_concept_first_models():
    from scripts import spb_visual_workbench

    for effect_id in OWNER_CONFIRMED_EFFECTS_SPB67_WAVE3_IDS:
        spec_fn, paint_fn = owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS[effect_id]
        expected = "_v6" if effect_id == "film_burn" else "_v5"
        assert spec_fn.__name__.endswith(expected)
        assert paint_fn.__name__.endswith(expected)

    out_dir = Path(".pytest-tmp") / "effects_vision_spb67_wave3"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE3_IDS),
        "--kind",
        "monolithic",
        "--size",
        "128",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE3_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["fine_energy"] for row in rows) > 0.030
    assert min(row["residual_energy"] for row in rows) > 0.014
    assert min(row["color_population"] for row in rows) >= 5
    assert min(row["spec_m_range"] for row in rows) >= 135.0
    assert min(row["spec_cc_range"] for row in rows) >= 165.0
    assert min(row["paint_luma_std"] for row in rows) > 0.020

    vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.97


def test_spb67_effects_vision_wave4_uses_concept_first_v4_models():
    from scripts import spb_visual_workbench

    for effect_id in OWNER_CONFIRMED_EFFECTS_SPB67_WAVE4_IDS:
        spec_fn, paint_fn = owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS[effect_id]
        assert spec_fn.__name__.endswith("_v4")
        assert paint_fn.__name__.endswith("_v4")

    out_dir = Path(".pytest-tmp") / "effects_vision_spb67_wave4"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE4_IDS),
        "--kind",
        "monolithic",
        "--size",
        "128",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE4_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["fine_energy"] for row in rows) > 0.024
    assert min(row["residual_energy"] for row in rows) > 0.010
    assert min(row["color_population"] for row in rows) >= 5
    assert min(row["spec_m_range"] for row in rows) >= 140.0
    assert min(row["spec_cc_range"] for row in rows) >= 195.0


def test_spb67_effects_vision_wave5_uses_optical_material_v5_models():
    from scripts import spb_visual_workbench

    for effect_id in OWNER_CONFIRMED_EFFECTS_SPB67_WAVE5_IDS:
        spec_fn, paint_fn = owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS[effect_id]
        assert spec_fn.__name__.endswith("_v5")
        assert paint_fn.__name__.endswith("_v5")

    out_dir = Path(".pytest-tmp") / "effects_vision_spb67_wave5"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE5_IDS),
        "--kind",
        "monolithic",
        "--size",
        "128",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE5_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["fine_energy"] for row in rows) > 0.022
    assert min(row["residual_energy"] for row in rows) > 0.010
    assert min(row["color_population"] for row in rows) >= 6
    assert min(row["spec_m_range"] for row in rows) >= 125.0
    assert min(row["spec_cc_range"] for row in rows) >= 150.0
    assert min(row["paint_luma_std"] for row in rows) > 0.018

    vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.97


def test_spb67_effects_vision_wave6_uses_tail_material_v4_models():
    from scripts import spb_visual_workbench

    for effect_id in OWNER_CONFIRMED_EFFECTS_SPB67_WAVE6_IDS:
        spec_fn, paint_fn = owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS[effect_id]
        assert spec_fn.__name__.endswith("_v4")
        assert paint_fn.__name__.endswith("_v4")

    out_dir = Path(".pytest-tmp") / "effects_vision_spb67_wave6"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE6_IDS),
        "--kind",
        "monolithic",
        "--size",
        "128",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_CONFIRMED_EFFECTS_SPB67_WAVE6_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert min(row["fine_energy"] for row in rows) > 0.022
    assert min(row["residual_energy"] for row in rows) > 0.010
    assert min(row["color_population"] for row in rows) >= 5
    assert min(row["spec_m_range"] for row in rows) >= 135.0
    assert min(row["spec_cc_range"] for row in rows) >= 150.0
    assert min(row["paint_luma_std"] for row in rows) > 0.018

    vectors = {}
    for row in rows:
        img = Image.open(out_dir / row["files"]["paint_preview"]).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=np.float32).reshape(-1)
        vectors[row["id"]] = (arr - float(arr.mean())) / (float(arr.std()) + 1e-6)

    max_abs_corr = max(
        abs(float(np.dot(vectors[a], vectors[b]) / len(vectors[a])))
        for a, b in itertools.combinations(vectors, 2)
    )
    assert max_abs_corr < 0.97


def test_spb67_effects_vision_owner_rejected_perf_and_concept_fixes_are_fast_enough():
    from scripts import spb_visual_workbench

    expected_suffix = {
        "reaper": "_v5",
        "film_burn": "_v6",
    }
    for effect_id in OWNER_REJECTED_EFFECTS_PERF_AND_CONCEPT_FIX_IDS:
        spec_fn, paint_fn = owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS[effect_id]
        assert spec_fn.__name__.endswith(expected_suffix[effect_id])
        assert paint_fn.__name__.endswith(expected_suffix[effect_id])

    out_dir = Path(".pytest-tmp") / "effects_vision_spb67_owner_rejected_perf_concept"
    rc = spb_visual_workbench.main([
        "--ids",
        ",".join(OWNER_REJECTED_EFFECTS_PERF_AND_CONCEPT_FIX_IDS),
        "--kind",
        "monolithic",
        "--size",
        "256",
        "--out-dir",
        str(out_dir),
    ])
    assert rc == 0
    payload = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert {row["id"] for row in rows} == set(OWNER_REJECTED_EFFECTS_PERF_AND_CONCEPT_FIX_IDS)
    assert all(row["status"] == "OK" for row in rows)
    assert all(row["render_ms"] < 900.0 for row in rows)
    assert min(row["fine_energy"] for row in rows) > 0.030
    assert min(row["residual_energy"] for row in rows) > 0.012
    assert min(row["spec_m_range"] for row in rows) >= 135.0
    assert min(row["spec_cc_range"] for row in rows) >= 165.0


def test_owner_confirmed_effects_respect_zone_mask():
    shape = (64, 64)
    paint = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    paint[:, :, 0] = 0.18
    paint[:, :, 1] = 0.42
    paint[:, :, 2] = 0.67
    mask = np.zeros(shape, dtype=np.float32)
    mask[16:48, 16:48] = 1.0
    outside = mask < 0.5

    for effect_id, (_, paint_fn) in owner_review_effects.OWNER_REVIEW_EFFECTS_MONOLITHICS.items():
        rendered = paint_fn(paint.copy(), shape, mask, seed=211, pm=1.0, bb=0.0)
        np.testing.assert_allclose(
            rendered[outside],
            paint[outside],
            atol=1e-6,
            err_msg=f"{effect_id} changed paint outside the zone mask",
        )
