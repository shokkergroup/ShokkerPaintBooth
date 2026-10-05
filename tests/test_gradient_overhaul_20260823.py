"""Fail-closed shipping gates for SPB-GRADIENT-OVERHAUL-2026-08-23."""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _engine():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()
    return engine


def _shipping_ids(engine):
    ids = sorted(
        finish_id
        for finish_id in engine.MONOLITHIC_REGISTRY
        if finish_id.startswith(("grad_", "grd_", "gradient_"))
    )
    return ids


def test_gradient_shipping_census_and_catalog_home_are_exact():
    engine = _engine()
    ids = _shipping_ids(engine)
    assert sum(fid.startswith("grad_") for fid in ids) == 125
    assert sum(fid.startswith("grd_") for fid in ids) == 43
    assert sum(fid.startswith("gradient_") for fid in ids) == 10
    assert len(ids) == len(set(ids)) == 178

    text = (ROOT / "paint-booth-0-finish-data.js").read_text(encoding="utf-8")
    block = re.search(
        r"const _SPECIALS_GRADIENTS\s*=\s*\{.*?\[\s*(.*?)\s*\]\s*\};",
        text,
        re.S,
    )
    assert block, "missing 🌈 GRADIENTS catalog group"
    catalog_ids = re.findall(r'"(grd_[^"]+)"', block.group(1))
    assert len(catalog_ids) == len(set(catalog_ids)) == 43
    assert set(catalog_ids) == {fid for fid in ids if fid.startswith("grd_")}


def test_every_shipping_gradient_uses_final_v3_and_required_palette_depth():
    engine = _engine()
    from engine.expansions.gradient_overhaul_2026 import (
        EXTREME_SPECS,
        MATH_SPECS,
        gradient_palette_occupancy,
        gradient_recipe,
    )

    for finish_id in _shipping_ids(engine):
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
        assert spec_fn.__module__ == "engine.expansions.gradient_overhaul_2026", finish_id
        assert paint_fn.__module__ == "engine.expansions.gradient_overhaul_2026", finish_id
        recipe = gradient_recipe(finish_id)
        assert recipe is not None, finish_id
        assert recipe.stop_count == len(recipe.palette)
        distinct = {tuple(round(channel, 5) for channel in color) for color in recipe.palette}
        assert len(distinct) == recipe.stop_count, finish_id
        if finish_id.startswith("grad_"):
            assert 7 <= recipe.stop_count <= 9, finish_id
        elif finish_id.startswith("grd_"):
            assert 10 <= recipe.stop_count <= 15, finish_id
        else:
            assert 8 <= recipe.stop_count <= 10, finish_id

    assert len(EXTREME_SPECS) == 20
    assert len(MATH_SPECS) == 12
    assert all(10 <= gradient_recipe(fid).stop_count <= 15 for fid in EXTREME_SPECS)
    assert all(min(gradient_palette_occupancy(fid)) >= 0.01 for fid in EXTREME_SPECS)


def test_registered_gradients_win_all_production_zone_routes_and_both_registries():
    engine = _engine()
    import engine.registry as package_registry

    ids = _shipping_ids(engine)
    assert {
        finish_id for finish_id in package_registry.MONOLITHIC_REGISTRY
        if finish_id.startswith(("grad_", "grd_", "gradient_"))
    } == set(ids)
    for finish_id in ids:
        package_entry = package_registry.MONOLITHIC_REGISTRY[finish_id]
        legacy_entry = engine.MONOLITHIC_REGISTRY[finish_id]
        assert package_entry[0].__module__ == "engine.expansions.gradient_overhaul_2026"
        assert package_entry[1].__module__ == "engine.expansions.gradient_overhaul_2026"
        assert legacy_entry[0].__module__ == "engine.expansions.gradient_overhaul_2026"
        assert legacy_entry[1].__module__ == "engine.expansions.gradient_overhaul_2026"

    # G-4 regression: all three duplicated zone render loops used to send every
    # registered grad_* card through the generic two-endpoint renderer first.
    source = (ROOT / "shokker_engine_v2.py").read_text(encoding="utf-8")
    authored_first_guard = (
        'finish_name and zone.get("finish_colors") and '
        'finish_name not in MONOLITHIC_REGISTRY and ('
    )
    assert source.count(authored_first_guard) == 3


def test_gradient_v3_authority_is_import_order_independent_in_fresh_processes():
    """Cold package/server imports must not let later registry loads restore v2."""
    code = r"""
import sys

mode = sys.argv[1]
if mode == "engine-first":
    import engine
    registry = engine.MONOLITHIC_REGISTRY
elif mode == "server-first":
    import server
    registry = server.engine.MONOLITHIC_REGISTRY
else:
    raise AssertionError(mode)

ids = sorted(
    finish_id
    for finish_id in registry
    if finish_id.startswith(("grad_", "grd_", "gradient_"))
)
counts = (
    sum(finish_id.startswith("grad_") for finish_id in ids),
    sum(finish_id.startswith("grd_") for finish_id in ids),
    sum(finish_id.startswith("gradient_") for finish_id in ids),
)
wrong = []
for finish_id in ids:
    entry = registry[finish_id]
    functions = entry[:2] if isinstance(entry, (tuple, list)) else (
        entry.get("spec_fn"), entry.get("paint_fn")
    )
    modules = tuple(getattr(fn, "__module__", "") for fn in functions)
    if modules != (
        "engine.expansions.gradient_overhaul_2026",
        "engine.expansions.gradient_overhaul_2026",
    ):
        wrong.append((finish_id, modules))

if len(ids) != 178 or counts != (125, 43, 10) or wrong:
    print(f"mode={mode} count={len(ids)} prefixes={counts} wrong={wrong[:25]}")
    raise SystemExit(1)
"""
    for mode in ("engine-first", "server-first"):
        result = subprocess.run(
            [sys.executable, "-c", code, mode],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_enlarged_swatch_routes_registered_gradient_to_v3_and_custom_to_generic(
    monkeypatch,
):
    """Dynamic-prefix routing must defer to authored registry ownership."""
    import contextlib
    import io

    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        import server

    registered_id = "grad_fire_fade"
    custom_id = "grad_custom_dynamic_regression"
    registry = server.engine.MONOLITHIC_REGISTRY
    assert registered_id in registry
    assert custom_id not in registry

    original_spec, original_paint = registry[registered_id][:2]
    assert original_spec.__module__ == "engine.expansions.gradient_overhaul_2026"
    assert original_paint.__module__ == "engine.expansions.gradient_overhaul_2026"
    calls = {"spec": 0, "paint": 0, "generic": []}

    def spec_spy(*args, **kwargs):
        calls["spec"] += 1
        return original_spec(*args, **kwargs)

    def paint_spy(*args, **kwargs):
        calls["paint"] += 1
        return original_paint(*args, **kwargs)

    # Keep the registered entry structurally representative while making the
    # authored path observable. Generic rendering must remain untouched here.
    spec_spy.__module__ = original_spec.__module__
    paint_spy.__module__ = original_paint.__module__
    monkeypatch.setitem(registry, registered_id, (spec_spy, paint_spy))

    def generic_spy(finish_id, zone, paint, shape, mask, seed, *args):
        calls["generic"].append((finish_id, zone.get("finish_colors")))
        output = paint.copy()
        output[:, :, :3] = np.asarray((0.12, 0.45, 0.78), dtype=np.float32)
        return None, output

    monkeypatch.setattr(server.engine, "render_generic_finish", generic_spy)

    authored_png = server._render_swatch_bytes(
        "monolithic", registered_id, "112233", 512, 4242
    )
    assert authored_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert calls == {"spec": 1, "paint": 1, "generic": []}

    import finish_colors_lookup

    original_lookup = finish_colors_lookup.get_finish_colors
    custom_colors = {"colors": ["#ff0000", "#00ff00", "#0000ff"]}
    monkeypatch.setattr(
        finish_colors_lookup,
        "get_finish_colors",
        lambda finish_id: custom_colors if finish_id == custom_id else original_lookup(finish_id),
    )
    custom_png = server._render_swatch_bytes(
        "monolithic", custom_id, "112233", 512, 4242
    )
    assert custom_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert calls["spec"] == calls["paint"] == 1
    assert calls["generic"] == [(custom_id, custom_colors)]

    source = (ROOT / "server.py").read_text(encoding="utf-8")
    guard = "is_dynamic_mono and finish_key not in engine.MONOLITHIC_REGISTRY"
    assert source.count(guard) == 1


def test_legacy_direction_and_vortex_names_are_renderer_contracts():
    engine = _engine()
    from engine.expansions.gradient_overhaul_2026 import gradient_recipe

    legacy_ids = [fid for fid in _shipping_ids(engine) if fid.startswith("grad_")]
    vortex = [fid for fid in legacy_ids if fid.endswith("_vortex")]
    horizontal = [fid for fid in legacy_ids if fid.endswith("_h")]
    diagonal = [fid for fid in legacy_ids if fid.endswith("_diag")]
    assert (len(vortex), len(horizontal), len(diagonal)) == (50, 10, 8)
    assert all(gradient_recipe(fid).orientation == "vortex" for fid in vortex)
    assert all(gradient_recipe(fid).orientation == "horizontal" for fid in horizontal)
    assert all(gradient_recipe(fid).orientation == "diagonal" for fid in diagonal)
    assert all("vortex" in gradient_recipe(fid).topology or gradient_recipe(fid).topology in {
        "spiral", "cyclone_cells", "shockwave", "oil_whorl", "accretion",
        "dual_vortex", "petal_whirl", "broken_rotor", "tidal_vortex",
        "eddy_chain", "logarithmic_shells", "vortex_bubbles", "pinwheel_shards",
        "whirlpool_rift", "turbine_blades", "coral_cell_vortex",
        "topaz_shard_vortex",
    } for fid in vortex)
    # G17 broke up the prior amber/coral/topaz triangle-lattice cluster. Amber
    # intentionally remains the sole lattice; coral and topaz now have distinct
    # curling polyp-cell and gem-shard silhouettes.
    assert sum(gradient_recipe(fid).topology == "vortex_lattice" for fid in vortex) == 1


def test_all_shipping_gradients_have_rich_decorrelated_spec_and_unique_small_renders():
    engine = _engine()
    size = 96
    paint = np.full((size, size, 3), 0.21, np.float32)
    mask = np.ones((size, size), np.float32)
    bb = np.zeros((size, size), np.float32)
    hashes = []
    failures = []
    for finish_id in _shipping_ids(engine):
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
        rendered = paint_fn(paint, (size, size), mask, 7301, 1.0, bb)
        spec = spec_fn((size, size), mask, 7301, 1.0)
        hashes.append(hashlib.sha256(rendered.tobytes() + spec.tobytes()).hexdigest())
        stds = [float(spec[:, :, c].std()) for c in range(3)]
        spans = [float(np.ptp(spec[:, :, c])) for c in range(3)]
        corr = np.corrcoef(spec[:, :, :3].reshape(-1, 3), rowvar=False)
        max_corr = float(np.max(np.abs(corr[np.triu_indices(3, 1)])))
        if (
            float(rendered.std()) < 0.025
            or min(stds) < 20.0
            or min(spans) < 200.0
            or max_corr >= 0.85
        ):
            failures.append((finish_id, float(rendered.std()), stds, spans, max_corr))
    assert not failures, failures[:10]
    assert len(hashes) == len(set(hashes)) == 178


def test_gradient_output_is_process_deterministic_across_hash_seeds():
    code = r"""
import hashlib
import numpy as np
import shokker_engine_v2 as engine
engine._ensure_expansions_loaded()
finish_id = 'grd_hyperprism_supernova'
spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
n = 96
paint = np.full((n,n,3), .2, np.float32)
mask = np.ones((n,n), np.float32)
bb = np.zeros((n,n), np.float32)
rgb = paint_fn(paint, (n,n), mask, 7301, 1.0, bb)
spec = spec_fn((n,n), mask, 7301, 1.0)
print('GRADIENT_DIGEST=' + hashlib.sha256(rgb.tobytes() + spec.tobytes()).hexdigest())
"""
    digests = []
    for hash_seed in ("1", "987654"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = hash_seed
        output = subprocess.check_output(
            [sys.executable, "-c", code], cwd=ROOT, env=env, text=True,
            encoding="utf-8", errors="replace",
        )
        digests.append(re.search(r"GRADIENT_DIGEST=([0-9a-f]{64})", output).group(1))
    assert len(set(digests)) == 1, digests


def test_every_gradient_topology_is_under_native_2048_three_second_budget():
    engine = _engine()
    from engine.expansions.gradient_overhaul_2026 import (
        clear_gradient_cache,
        gradient_recipe,
    )

    # One deterministic representative per renderer topology is the smallest
    # honest census: family-only samples previously exercised only 3 code paths.
    # Keep a diversity floor instead of freezing an exact count so deliberately
    # added renderer families cannot make this quality/performance gate stale.
    representatives = {}
    for finish_id in _shipping_ids(engine):
        representatives.setdefault(gradient_recipe(finish_id).topology, finish_id)
    assert len(representatives) >= 72

    size = 2048
    paint = np.full((size, size, 3), 0.2, np.float32)
    mask = np.ones((size, size), np.float32)
    bb = np.zeros((size, size), np.float32)
    timings = []
    for topology, finish_id in sorted(representatives.items()):
        clear_gradient_cache()
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
        started = time.perf_counter()
        spec = spec_fn((size, size), mask, 7301, 1.0)
        rendered = paint_fn(paint, (size, size), mask, 7301, 1.0, bb)
        elapsed = time.perf_counter() - started
        timings.append((topology, finish_id, elapsed))
        assert spec.shape == (size, size, 4)
        assert rendered.shape == (size, size, 3)
    assert max(elapsed for _topology, _finish_id, elapsed in timings) < 3.0, timings


def test_mask_and_strength_contracts_are_non_destructive():
    engine = _engine()
    size = 128
    base = np.full((size, size, 3), 0.217, np.float32)
    zero = np.zeros((size, size), np.float32)
    ones = np.ones((size, size), np.float32)
    bb = np.zeros((size, size), np.float32)
    for finish_id in ("grad_fire_fade", "grd_quantum_carnival", "gradient_ember_ice"):
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
        assert np.array_equal(paint_fn(base, (size, size), zero, 9, 1.0, bb), base)
        assert np.array_equal(paint_fn(base, (size, size), ones, 9, 0.0, bb), base)
        spec = spec_fn((size, size), zero, 9, 1.0)
        assert np.all(spec[:, :, 0] == 4)
        assert np.all(spec[:, :, 1] == 120)
        assert np.all(spec[:, :, 2] == 80)
        assert np.all(spec[:, :, 3] == 255)
