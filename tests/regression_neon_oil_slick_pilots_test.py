"""Fast contracts for the five isolated Neon Underground Oil-Slick pilots."""
from __future__ import annotations

import importlib

import numpy as np

from engine.paint_v2 import neon_material_core_v3 as core


PILOTS = (
    ("engine.expansions.neon_underground_v3.blue_breakdown", "build_blue_breakdown"),
    ("engine.expansions.neon_underground_v3.sodium_scuff", "build_sodium_scuff"),
    ("engine.expansions.neon_underground_v3.redline_shear", "build_redline_shear"),
    ("engine.expansions.neon_underground_v3.quarter_mile_weave", "build"),
    ("engine.expansions.neon_underground_v3.torque_scar", "build_torque_scar"),
)


def _build(module_name: str, builder_name: str):
    module = importlib.import_module(module_name)
    return getattr(module, builder_name)(size=core.WORK)


def test_five_pilots_keep_fine_causal_material_contracts() -> None:
    ids: list[str] = []
    for module_name, builder_name in PILOTS:
        result = _build(module_name, builder_name)
        ids.append(result.finish_id)

        assert result.paint.shape == (core.WORK, core.WORK, 3)
        assert result.spec.shape == (core.WORK, core.WORK, 3)
        assert np.isfinite(result.paint).all()
        assert np.isfinite(result.spec).all()
        assert len(result.masks) >= 5

        geometry = core.geometry_stats(result.geometry)
        assert geometry["family_count"] >= 5
        assert geometry["fine_8_32_fraction"] == 1.0

        material = core.material_stats(result.spec)
        assert all(value == 8 for value in material["tier_count"].values())
        assert all(value >= 20.0 for value in material["std"].values())
        assert all(abs(value) < 0.80 for value in material["correlation"].values())

    assert len(ids) == len(set(ids)) == 5


def test_five_pilots_are_deterministic() -> None:
    for module_name, builder_name in PILOTS:
        first = _build(module_name, builder_name)
        second = _build(module_name, builder_name)
        assert np.array_equal(first.paint, second.paint)
        assert np.array_equal(first.spec, second.spec)
