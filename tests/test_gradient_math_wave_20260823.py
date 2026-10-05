"""Fail-closed gates for the 2026-08-23 mathematical Gradient wave.

The wave deliberately reuses the June-August procedural-math arsenal, but it
must ship as twelve new Gradient mechanisms rather than twelve palette swaps.
These tests pin the source provenance, deterministic field contract, buyer
catalog census, 10-15-color occupancy, fine detail, material richness, mask
semantics, and the bounded helper cost that feeds the existing native-2048
all-topology performance gate.
"""
from __future__ import annotations

import hashlib
import importlib
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MATH = (
    ("grd_domain_coloring_singularity", "domain_singularity"),
    ("grd_nebulabrot_ionstorm", "nebulabrot_ionstorm"),
    ("grd_superformula_starforge", "superformula_starforge"),
    ("grd_bismuth_colorquake", "bismuth_chladni"),
    ("grd_stable_ink_supercurrent", "stable_ink_caustics"),
    ("grd_electrostatic_candy_wells", "electrostatic_ridges"),
    ("grd_ferrofluid_spectrum_crown", "ferrofluid_gyroid"),
    ("grd_viscous_prism_fingers", "viscous_schlieren"),
    ("grd_scarab_shingle_cascade", "scarab_cascade"),
    ("grd_nacre_brickwave", "nacre_filament"),
    ("grd_singularity_loom", "singularity_loom"),
    ("grd_harmonic_cathedral", "harmonic_cathedral"),
)

EXPECTED_DEPENDENCIES = (
    "engine.paint_v2.fractured_math",
    "engine.paint_v2.exotic_packs.pack_complex_dynamics",
    "engine.paint_v2.exotic_packs.pack_curves_harmonic",
    "engine.paint_v2.exotic_packs.pack_optical_material",
    "engine.paint_v2.exotic_packs.pack_physical_fields",
    "engine.expansions.fractured_morpho_2026",
)


def _engine():
    import shokker_engine_v2 as engine

    engine._ensure_expansions_loaded()
    return engine


def _shipping_ids(engine):
    return sorted(
        finish_id
        for finish_id in engine.MONOLITHIC_REGISTRY
        if finish_id.startswith(("grad_", "grd_", "gradient_"))
    )


def test_math_helper_declares_exact_topologies_and_resolvable_provenance():
    from engine.expansions import gradient_math_wave_2026 as math_wave

    expected_topologies = tuple(topology for _finish_id, topology in EXPECTED_MATH)
    assert math_wave.MATH_TOPOLOGIES == expected_topologies
    assert math_wave.MATH_DEPENDENCY_MODULES == EXPECTED_DEPENDENCIES
    assert tuple(math_wave.MATH_TOPOLOGY_SOURCES) == expected_topologies

    used_dependencies = set()
    for topology in expected_topologies:
        sources = math_wave.MATH_TOPOLOGY_SOURCES[topology]
        assert isinstance(sources, tuple) and len(sources) == 2, (topology, sources)
        assert len(set(sources)) == 2, (topology, sources)
        for callable_path in sources:
            matches = [
                dependency
                for dependency in EXPECTED_DEPENDENCIES
                if callable_path.startswith(dependency + ".")
            ]
            assert len(matches) == 1, (topology, callable_path, matches)
            used_dependencies.add(matches[0])
            module_name, attribute = callable_path.rsplit(".", 1)
            source_module = importlib.import_module(module_name)
            assert callable(getattr(source_module, attribute, None)), callable_path
    assert used_dependencies == set(EXPECTED_DEPENDENCIES)


def test_math_helper_is_deterministic_nonflat_seeded_and_topology_unique():
    from engine.expansions.gradient_math_wave_2026 import (
        MATH_TOPOLOGIES,
        build_math_field,
    )

    hashes = []
    for index, topology in enumerate(MATH_TOPOLOGIES):
        seed = 8701 + index * 97
        first = build_math_field(topology, 192, 192, seed)
        second = build_math_field(topology, 192, 192, seed)
        changed_seed = build_math_field(topology, 192, 192, seed + 1)
        assert first.shape == (192, 192)
        assert first.dtype == np.float32
        assert np.isfinite(first).all()
        assert float(first.min()) >= 0.0 and float(first.max()) <= 1.0
        assert float(first.std()) >= 0.06, topology
        assert float(np.ptp(first)) >= 0.50, topology
        assert len(np.unique(np.rint(first * 255.0).astype(np.uint8))) >= 64, topology
        assert np.array_equal(first, second), topology
        assert float(np.mean(np.abs(first - changed_seed))) >= 0.005, topology
        hashes.append(hashlib.sha256(first.tobytes()).hexdigest())
    assert len(hashes) == len(set(hashes)) == 12

    with pytest.raises(KeyError):
        build_math_field("not_a_shipping_math_topology", 64, 64, 1)
    for height, width in ((0, 64), (64, 0), (-1, 64), (64, -1)):
        with pytest.raises(ValueError):
            build_math_field(MATH_TOPOLOGIES[0], height, width, 1)


def test_math_helper_is_process_deterministic_across_python_hash_seeds():
    code = r"""
import hashlib
from engine.expansions.gradient_math_wave_2026 import MATH_TOPOLOGIES, build_math_field

digest = hashlib.sha256()
for index, topology in enumerate(MATH_TOPOLOGIES):
    field = build_math_field(topology, 96, 96, 8701 + index * 97)
    digest.update(topology.encode("ascii"))
    digest.update(field.tobytes())
print("GRADIENT_MATH_DIGEST=" + digest.hexdigest())
"""
    digests = []
    for hash_seed in ("1", "987654"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = hash_seed
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        match = re.search(r"GRADIENT_MATH_DIGEST=([0-9a-f]{64})", result.stdout)
        assert match, result.stdout + result.stderr
        digests.append(match.group(1))
    assert len(set(digests)) == 1, digests


def test_math_helper_all_topologies_fit_the_bounded_1024_work_grid_budget():
    """The existing Gradient suite owns the full native-2048 paint+spec gate."""
    from engine.expansions.gradient_math_wave_2026 import (
        MATH_TOPOLOGIES,
        build_math_field,
    )

    timings = []
    for index, topology in enumerate(MATH_TOPOLOGIES):
        started = time.perf_counter()
        field = build_math_field(topology, 1024, 1024, 9301 + index * 101)
        elapsed = time.perf_counter() - started
        timings.append((topology, elapsed))
        assert field.shape == (1024, 1024)
        assert field.dtype == np.float32
        assert float(field.std()) >= 0.06
    assert max(elapsed for _topology, elapsed in timings) < 1.50, timings


def test_math_gradient_shipping_census_palette_depth_and_picker_dependencies_are_exact():
    engine = _engine()
    from engine.expansions.gradient_overhaul_2026 import (
        MATH_SPECS,
        gradient_palette_occupancy,
        gradient_recipe,
    )

    expected_ids = tuple(finish_id for finish_id, _topology in EXPECTED_MATH)
    expected_topologies = {finish_id: topology for finish_id, topology in EXPECTED_MATH}
    ids = _shipping_ids(engine)
    assert sum(finish_id.startswith("grad_") for finish_id in ids) == 125
    assert sum(finish_id.startswith("grd_") for finish_id in ids) == 43
    assert sum(finish_id.startswith("gradient_") for finish_id in ids) == 10
    assert len(ids) == len(set(ids)) == 178
    assert tuple(MATH_SPECS) == expected_ids
    assert set(expected_ids).issubset(ids)

    dependency_contract = (
        "engine.expansions.gradient_math_wave_2026",
        "engine.paint_v2.gradient_math",
        *EXPECTED_DEPENDENCIES,
    )
    for finish_id in expected_ids:
        topology = expected_topologies[finish_id]
        _name, declared_topology, declared_count, _anchors = MATH_SPECS[finish_id]
        assert declared_topology == topology
        assert 10 <= declared_count <= 15

        recipe = gradient_recipe(finish_id)
        assert recipe is not None
        assert recipe.family == "math"
        assert recipe.topology == topology
        assert recipe.color_space == "oklab"
        assert recipe.stop_count == len(recipe.palette) == declared_count
        rounded_colors = {
            tuple(round(float(channel), 6) for channel in color)
            for color in recipe.palette
        }
        assert len(rounded_colors) == declared_count, finish_id

        occupancy = gradient_palette_occupancy(finish_id, size=256, seed=8701)
        assert len(occupancy) == declared_count
        assert sum(occupancy) == pytest.approx(1.0, abs=1e-8)
        assert min(occupancy) >= 0.01, (finish_id, occupancy)

        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
        assert spec_fn.__module__ == "engine.expansions.gradient_overhaul_2026"
        assert paint_fn.__module__ == "engine.expansions.gradient_overhaul_2026"
        assert spec_fn._spb_picker_dependency_modules == dependency_contract
        assert paint_fn._spb_picker_dependency_modules == dependency_contract

    # A math topology is a new mechanism, never an alias for a pre-existing card.
    other_topologies = {
        gradient_recipe(finish_id).topology
        for finish_id in ids
        if finish_id not in expected_ids
    }
    assert set(expected_topologies.values()).isdisjoint(other_topologies)

    text = (ROOT / "paint-booth-0-finish-data.js").read_text(encoding="utf-8")
    block = re.search(
        r"const _SPECIALS_GRADIENTS\s*=\s*\{.*?\[\s*(.*?)\s*\]\s*\};",
        text,
        re.S,
    )
    assert block, "missing buyer-facing 🌈 GRADIENTS group"
    catalog_ids = re.findall(r'"(grd_[^"]+)"', block.group(1))
    assert len(catalog_ids) == len(set(catalog_ids)) == 43
    assert set(catalog_ids) == {finish_id for finish_id in ids if finish_id.startswith("grd_")}


def test_all_math_gradients_have_fine_color_detail_and_eight_rich_spec_shades():
    engine = _engine()
    size = 256
    base = np.full((size, size, 3), 0.217, np.float32)
    mask = np.ones((size, size), np.float32)
    bb = np.zeros((size, size), np.float32)
    hashes = []
    failures = []

    for finish_id, _topology in EXPECTED_MATH:
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
        spec = spec_fn((size, size), mask, 8701, 1.0)
        rendered = paint_fn(base.copy(), (size, size), mask, 8701, 1.0, bb)
        hashes.append(hashlib.sha256(rendered.tobytes() + spec.tobytes()).hexdigest())

        luma = rendered @ np.float32((0.2126, 0.7152, 0.0722))
        fine = luma - cv2.GaussianBlur(luma, (0, 0), 1.25)
        spec_rgb = spec[:, :, :3].astype(np.float32)
        stds = [float(spec_rgb[:, :, channel].std()) for channel in range(3)]
        spans = [float(np.ptp(spec_rgb[:, :, channel])) for channel in range(3)]
        levels = [len(np.unique(spec[:, :, channel])) for channel in range(3)]
        corr = np.corrcoef(spec_rgb.reshape(-1, 3), rowvar=False)
        max_corr = float(np.max(np.abs(corr[np.triu_indices(3, 1)])))
        rgb8 = np.rint(np.clip(rendered, 0.0, 1.0) * 255.0).astype(np.uint8)
        unique_rgb = len(np.unique(rgb8.reshape(-1, 3), axis=0))
        if (
            rendered.shape != (size, size, 3)
            or rendered.dtype != np.float32
            or spec.shape != (size, size, 4)
            or float(rendered.std()) < 0.05
            or float(fine.std()) < 0.006
            or unique_rgb < 1500
            or min(levels) < 8
            or min(stds) < 20.0
            or min(spans) < 200.0
            or max_corr >= 0.88
        ):
            failures.append(
                (finish_id, float(rendered.std()), float(fine.std()), unique_rgb,
                 levels, stds, spans, max_corr)
            )
    assert not failures, failures
    assert len(hashes) == len(set(hashes)) == 12


def test_math_gradient_mask_and_strength_contracts_are_non_destructive():
    engine = _engine()
    size = 128
    base = np.full((size, size, 3), 0.217, np.float32)
    zero = np.zeros((size, size), np.float32)
    ones = np.ones((size, size), np.float32)
    half = np.zeros((size, size), np.float32)
    half[:, : size // 2] = 1.0
    bb = np.zeros((size, size), np.float32)

    samples = (
        "grd_domain_coloring_singularity",
        "grd_stable_ink_supercurrent",
        "grd_scarab_shingle_cascade",
        "grd_harmonic_cathedral",
    )
    for finish_id in samples:
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[finish_id][:2]
        assert np.array_equal(
            paint_fn(base.copy(), (size, size), zero, 31, 1.0, bb), base
        )
        assert np.array_equal(
            paint_fn(base.copy(), (size, size), ones, 31, 0.0, bb), base
        )

        zero_spec = spec_fn((size, size), zero, 31, 1.0)
        assert np.all(zero_spec[:, :, 0] == 4)
        assert np.all(zero_spec[:, :, 1] == 120)
        assert np.all(zero_spec[:, :, 2] == 80)
        assert np.all(zero_spec[:, :, 3] == 255)

        partial = paint_fn(base.copy(), (size, size), half, 31, 1.0, bb)
        assert np.array_equal(partial[:, size // 2 :], base[:, size // 2 :])
        assert float(np.mean(np.abs(partial[:, : size // 2] - base[:, : size // 2]))) > 0.03
        partial_spec = spec_fn((size, size), half, 31, 1.0)
        assert np.all(partial_spec[:, size // 2 :, 0] == 4)
        assert np.all(partial_spec[:, size // 2 :, 1] == 120)
        assert np.all(partial_spec[:, size // 2 :, 2] == 80)

