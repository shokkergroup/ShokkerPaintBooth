from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np


def _budget_summary(records):
    slowest = sorted(records, key=lambda row: row[1], reverse=True)[:8]
    return ", ".join(f"{name}={elapsed:.3f}s" for name, elapsed in slowest)


def _time_case(records, name, fn):
    t0 = time.perf_counter()
    out = fn()
    records.append((name, time.perf_counter() - t0))
    return out


def test_spec_overlay_small_scale_uses_canvas_sized_generation():
    from engine.compose import _scale_down_spec_pattern

    calls = []

    def fake_spec(shape, seed=0, sm=1.0, **kwargs):
        calls.append(tuple(shape))
        return np.full(shape[:2], 0.5, dtype=np.float32)

    out = _scale_down_spec_pattern(fake_spec, 0.30, (512, 512), 123, 1.0, {})

    assert out.shape == (512, 512)
    assert calls == [(512, 512)]


def test_regular_pattern_rebuilds_are_allowlisted_not_family_broad():
    import shokker_engine_v2 as eng

    bespoke = eng._SPB_BESPOKE_PATTERN_REBUILD_IDS
    candidates = eng._SPB_PATTERN_REBUILD_MODES

    # SPB-4 is intentionally replacing weak renderer IDs in bounded batches.
    # Keep this as a broad-family guard, not a freeze on legitimate per-ID fixes.
    assert len(bespoke) < 124
    assert len(bespoke) < len(candidates)
    assert "zigzag_bands" not in bespoke
    assert "fiber_optic" in bespoke
    assert "flame_inferno_wall" in bespoke


def test_regular_pattern_hot_paths_stay_under_budget():
    import shokker_engine_v2  # noqa: F401 - applies registry patches
    from engine.registry import PATTERN_REGISTRY

    shape = (512, 512)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((shape[0], shape[1], 3), 0.45, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    hot_ids = (
        "circuit_traces",
        "hex_circuit",
        "biomech_cables",
        "dendrite_web",
        "crystal_lattice",
        "chainmail_hex",
        "fiber_optic",
        "graphene_hex",
        "gear_mesh",
        "vinyl_record",
        "sonar_ping",
        "waveform_stack",
        "hex_mandala",
        "shokk_fracture",
        "shokk_waveform",
        "shokk_plasma_storm",
        "shokk_tesseract",
        "flame_inferno_wall",
        "flame_blue_propane",
        "flame_ember_field",
    )
    records = []
    start = time.perf_counter()
    for pid in hot_ids:
        entry = PATTERN_REGISTRY[pid]
        tex_fn = entry.get("texture_fn")
        paint_fn = entry.get("paint_fn")
        if tex_fn is not None:
            _time_case(records, f"{pid}.texture", lambda tex_fn=tex_fn: tex_fn(shape, mask, 123, 1.0))
        if paint_fn is not None:
            _time_case(
                records,
                f"{pid}.paint",
                lambda paint_fn=paint_fn: paint_fn(paint.copy(), shape, mask, 123, 1.0, bb),
            )

    worst_name, worst_elapsed = max(records, key=lambda row: row[1])
    assert worst_elapsed < 1.25, f"{worst_name} took {worst_elapsed:.3f}s; slowest: {_budget_summary(records)}"
    total = time.perf_counter() - start
    assert total < 12.0, f"regular pattern perf suite took {total:.3f}s; slowest: {_budget_summary(records)}"


def test_spb5_tech_circuit_patterns_have_distinct_texture_identity():
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        import shokker_engine_v2  # noqa: F401 - applies registry patches
        from engine.registry import PATTERN_REGISTRY

    tech_ids = (
        "circuit_traces",
        "hex_circuit",
        "biomech_cables",
        "dendrite_web",
        "crystal_lattice",
        "chainmail_hex",
        "fiber_optic",
        "graphene_hex",
        "gear_mesh",
        "vinyl_record",
        "sonar_ping",
        "waveform_stack",
    )
    shape = (192, 192)
    mask = np.ones(shape, dtype=np.float32)
    normalized = {}
    weak = {}

    for pattern_id in tech_ids:
        entry = PATTERN_REGISTRY[pattern_id]
        tex = entry["texture_fn"](shape, mask, 321, 1.0)
        val = np.asarray(tex["pattern_val"], dtype=np.float32)
        std = float(val.std())
        mid_coverage = float(((val > 0.20) & (val < 0.95)).mean())
        if std < 0.07 or mid_coverage < 0.05:
            weak[pattern_id] = {"std": round(std, 4), "mid_coverage": round(mid_coverage, 4)}
        normalized[pattern_id] = (val - float(val.mean())) / (std + 1e-6)

    too_similar = []
    for idx, left in enumerate(tech_ids):
        for right in tech_ids[idx + 1:]:
            corr = float(np.mean(normalized[left] * normalized[right]))
            if corr > 0.72:
                too_similar.append((left, right, round(corr, 4)))

    assert weak == {}
    assert too_similar == []


def test_spec_pattern_hot_paths_stay_under_budget():
    from engine.spec_patterns import PATTERN_CATALOG, _SPB_SPEC_REBUILD_MODES

    shape = (512, 512)
    hot_ids = tuple(dict.fromkeys((
        "sparkle_comet",
        "electric_branches",
        "tire_smoke_residue",
        "galaxy_swirl",
        "spec_electroplated_chrome",
        "spec_xirallic_crystal",
        "spec_pvd_coating",
        "quantum_noise",
        "brake_dust_buildup",
        "spec_subsurface_depth",
        "gold_leaf_torn",
        "spec_iridescent_film",
        "sparkle_nebula",
        *_SPB_SPEC_REBUILD_MODES.keys(),
    )))
    records = []
    start = time.perf_counter()
    for pid in hot_ids:
        out = _time_case(records, pid, lambda pid=pid: PATTERN_CATALOG[pid](shape, seed=123, sm=1.0))
        assert out.shape == shape

    worst_name, worst_elapsed = max(records, key=lambda row: row[1])
    assert worst_elapsed < 0.90, f"{worst_name} took {worst_elapsed:.3f}s; slowest: {_budget_summary(records)}"
    total = time.perf_counter() - start
    assert total < 12.0, f"spec pattern perf suite took {total:.3f}s; slowest: {_budget_summary(records)}"


def test_spb3_metallic_spec_overlays_have_distinct_identity():
    from engine.spec_patterns import PATTERN_CATALOG

    metallic_ids = (
        "flake_scatter",
        "diamond_dust",
        "metallic_sand",
        "holographic_flake",
        "crystal_shimmer",
        "stardust_fine",
        "pearl_micro",
        "gold_flake",
        "crushed_glass",
        "prismatic_dust",
    )
    shape = (192, 192)
    normalized = {}
    weak = {}

    for pattern_id in metallic_ids:
        val = np.asarray(PATTERN_CATALOG[pattern_id](shape, seed=8403, sm=1.0), dtype=np.float32)
        std = float(val.std())
        fine_energy = float(np.abs(np.diff(val, axis=0)).mean() + np.abs(np.diff(val, axis=1)).mean())
        if std < 0.045 or fine_energy < 0.006:
            weak[pattern_id] = {"std": round(std, 4), "fine_energy": round(fine_energy, 4)}
        normalized[pattern_id] = (val - float(val.mean())) / (std + 1e-6)

    too_similar = []
    for idx, left in enumerate(metallic_ids):
        for right in metallic_ids[idx + 1:]:
            corr = float(np.mean(normalized[left] * normalized[right]))
            if corr > 0.60:
                too_similar.append((left, right, round(corr, 4)))

    assert weak == {}
    assert too_similar == []


def test_spb3_optical_rebuilds_have_fine_distinct_identity():
    from engine.spec_patterns import PATTERN_CATALOG

    optical_ids = (
        "spec_fresnel_gradient",
        "plasma_turbulence",
        "heat_distortion",
        "sonic_boom",
        "spec_bokeh_scatter",
        "magnetic_field",
        "spec_gravity_well",
    )
    shape = (192, 192)
    normalized = {}
    weak = {}

    for pattern_id in optical_ids:
        val = np.asarray(PATTERN_CATALOG[pattern_id](shape, seed=8428, sm=1.0), dtype=np.float32)
        std = float(val.std())
        fine_energy = float(np.abs(np.diff(val, axis=0)).mean() + np.abs(np.diff(val, axis=1)).mean())
        if std < 0.045 or fine_energy < 0.008:
            weak[pattern_id] = {"std": round(std, 4), "fine_energy": round(fine_energy, 4)}
        normalized[pattern_id] = (val - float(val.mean())) / (std + 1e-6)

    too_similar = []
    for idx, left in enumerate(optical_ids):
        for right in optical_ids[idx + 1:]:
            corr = float(np.mean(normalized[left] * normalized[right]))
            if corr > 0.60:
                too_similar.append((left, right, round(corr, 4)))

    assert weak == {}
    assert too_similar == []


def test_monolithic_and_fusion_hot_paths_stay_under_budget():
    from engine.expansions import fusions

    shape = (512, 512)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.full((shape[0], shape[1], 3), 0.16, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    hot_ids = (
        "sparkle_galaxy",
        "sparkle_diamond_dust",
        "halo_voronoi_metal",
        "halo_wave_candy",
        "multiscale_chrome_sand",
        "wave_moire_metal",
        "fractal_liquid_fire",
        "spectral_prismatic_flip",
        "trizone_frozen_ember_chrome",
        "depth_vortex",
    )
    records = []
    start = time.perf_counter()
    for finish_id in hot_ids:
        spec_fn, paint_fn = fusions.FUSION_REGISTRY[finish_id]
        spec = _time_case(
            records,
            f"{finish_id}.spec",
            lambda spec_fn=spec_fn: spec_fn(shape, mask, seed=901, sm=1.0),
        )
        painted = _time_case(
            records,
            f"{finish_id}.paint",
            lambda paint_fn=paint_fn: paint_fn(paint.copy(), shape, mask, seed=901, pm=1.0, bb=bb),
        )
        assert spec.shape == (shape[0], shape[1], 4), finish_id
        assert painted.shape == paint.shape, finish_id

    worst_name, worst_elapsed = max(records, key=lambda row: row[1])
    assert worst_elapsed < 1.25, f"{worst_name} took {worst_elapsed:.3f}s; slowest: {_budget_summary(records)}"
    total = time.perf_counter() - start
    assert total < 12.0, f"monolithic/fusion perf suite took {total:.3f}s; slowest: {_budget_summary(records)}"


def test_renderer_performance_audit_smoke_reports_named_budget_rows():
    from scripts import audit_renderer_performance

    rc = audit_renderer_performance.main([
        "--size",
        "96",
        "--pattern-ids",
        "circuit_traces,fiber_optic",
        "--spec-ids",
        "sparkle_comet,spec_iridescent_film",
        "--fusion-ids",
        "sparkle_galaxy,halo_voronoi_metal",
        "--pattern-budget",
        "2.5",
        "--spec-budget",
        "2.5",
        "--fusion-budget",
        "2.5",
        "--out-dir",
        ".pytest-tmp/renderer_performance_smoke",
        "--fail-on-budget",
    ])
    assert rc == 0

    payload = json.loads(Path(".pytest-tmp/renderer_performance_smoke/report.json").read_text(encoding="utf-8"))
    assert payload["count"] >= 8
    assert payload["over_budget_count"] == 0
    seen = {(row["kind"], row["id"]) for row in payload["rows"]}
    assert ("pattern", "circuit_traces") in seen
    assert ("spec_pattern", "sparkle_comet") in seen
    assert ("fusion", "sparkle_galaxy") in seen
