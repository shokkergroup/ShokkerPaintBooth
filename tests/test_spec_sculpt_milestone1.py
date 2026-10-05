"""Milestone 1: spec_sculpt scratch → iron-safe RGBA."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.registry import BASE_REGISTRY
from engine.spec_sculpt.catalog_blend import (
    blend_registered_specs_float,
    ensure_full_catalog_registries,
    normalize_catalog_stack,
)
from engine.spec_sculpt.generate import scratch_spec_from_any_paint
from engine.spec_sculpt.presets import preset_layer_chromatic
from engine.spec_sculpt.export import save_spec_tga_iron_safe
from shokker_engine_v2 import CC_FLOOR, CHROME_M_THRESHOLD, ROUGHNESS_FLOOR_NONMIRROR, _enforce_iron_rules


def test_scratch_spec_shape_dtype():
    rng = np.random.default_rng(42)
    tex = rng.random((64, 64, 3)).astype(np.float32)
    out = scratch_spec_from_any_paint(tex, seed=12345, chromatic_shift=False)
    assert out.shape == (64, 64, 4)
    assert out.dtype == np.uint8
    assert np.all(out[:, :, 3] == 255)


def test_iron_rules_after_export_roundtrip(tmp_path):
    tex = np.full((32, 32, 3), 0.5, dtype=np.float32)
    spec = scratch_spec_from_any_paint(tex, seed=99, chromatic_shift=False)
    path = tmp_path / "out.tga"
    save_spec_tga_iron_safe(spec, path)
    from PIL import Image

    loaded = np.asarray(Image.open(path).convert("RGBA"))
    safe = _enforce_iron_rules(loaded)
    M = safe[:, :, 0].astype(np.float32)
    R = safe[:, :, 1].astype(np.float32)
    B = safe[:, :, 2].astype(np.float32)
    cc_bad = (B > 0) & (B < CC_FLOOR)
    assert not np.any(cc_bad)
    rough_bad = (M < CHROME_M_THRESHOLD) & (R < ROUGHNESS_FLOOR_NONMIRROR)
    assert not np.any(rough_bad)


def test_prevalidated_export_is_byte_identical_to_default_safe_export(tmp_path):
    rng = np.random.default_rng(777)
    already_safe = _enforce_iron_rules(rng.integers(0, 256, (96, 96, 4), dtype=np.uint8))
    default_path = tmp_path / "default-safe.tga"
    fast_path = tmp_path / "prevalidated-safe.tga"

    save_spec_tga_iron_safe(already_safe, default_path)
    save_spec_tga_iron_safe(already_safe, fast_path, already_safe=True)

    assert default_path.read_bytes() == fast_path.read_bytes()


def test_catalog_blend_one_base_registry_spec():
    fid = sorted(BASE_REGISTRY.keys())[0]
    tex = np.ones((24, 24, 3), dtype=np.float32) * 0.4
    h, w = tex.shape[:2]
    m = np.ones((h, w), dtype=np.float32)
    stack = normalize_catalog_stack([{"id": fid, "weight": 1.0}])
    out = blend_registered_specs_float((h, w), m, seed=42, sm=1.0, stack=stack)
    assert out.shape == (24, 24, 4)
    assert out.dtype == np.float32


def test_full_catalog_merge_keeps_runtime_only_cards_selectable_and_renderable():
    bases, monolithics = ensure_full_catalog_registries()
    assert "track_worn" in bases
    assert "anime2_speed_lines" in monolithics

    mask = np.ones((16, 16), dtype=np.float32)
    for finish_id in ("track_worn", "anime2_speed_lines"):
        stack = normalize_catalog_stack([{"id": finish_id, "weight": 1.0}])
        assert stack == [(finish_id, 1.0)]
        out = blend_registered_specs_float((16, 16), mask, seed=42, sm=1.0, stack=stack)
        assert out.shape == (16, 16, 4)


def test_catalog_registry_pin_makes_duplicate_id_cards_render_their_own_thumbnail_material():
    bases, monolithics = ensure_full_catalog_registries()
    finish_id = "acid_rain"
    assert finish_id in bases and finish_id in monolithics

    base_stack = normalize_catalog_stack([{"id": finish_id, "weight": 1.0, "registry_type": "base"}])
    special_stack = normalize_catalog_stack([{"id": finish_id, "weight": 1.0, "registry_type": "monolithic"}])
    assert base_stack == [("base::acid_rain", 1.0)]
    assert special_stack == [("monolithic::acid_rain", 1.0)]

    mask = np.ones((32, 32), dtype=np.float32)
    base_spec = blend_registered_specs_float((32, 32), mask, seed=42, sm=1.0, stack=base_stack)
    special_spec = blend_registered_specs_float((32, 32), mask, seed=42, sm=1.0, stack=special_stack)
    assert base_spec.shape == special_spec.shape == (32, 32, 4)
    assert not np.array_equal(base_spec[:, :, :3], special_spec[:, :, :3])


def test_fusion_mix_endpoints_match_catalog_and_scratch():
    tex = np.ones((16, 16, 3), dtype=np.float32) * 0.5
    fid = sorted(BASE_REGISTRY.keys())[0]
    cat = normalize_catalog_stack([{"id": fid, "weight": 1.0}])
    preset = [("mirror_chrome", 1.0)]
    only_cat = scratch_spec_from_any_paint(
        tex, seed=7, chromatic_shift=False, catalog_stack=cat, preset_stack=None, fusion_mix=None
    )
    only_pre = scratch_spec_from_any_paint(
        tex, seed=7, chromatic_shift=False, catalog_stack=None, preset_stack=preset, fusion_mix=None
    )
    fuse1 = scratch_spec_from_any_paint(
        tex, seed=7, chromatic_shift=False, catalog_stack=cat, preset_stack=preset, fusion_mix=1.0
    )
    fuse0 = scratch_spec_from_any_paint(
        tex, seed=7, chromatic_shift=False, catalog_stack=cat, preset_stack=preset, fusion_mix=0.0
    )
    assert np.array_equal(only_cat[:, :, :3], fuse1[:, :, :3])
    assert np.array_equal(only_pre[:, :, :3], fuse0[:, :, :3])


def test_catalog_stack_differs_from_scratch_preset():
    tex = np.ones((16, 16, 3), dtype=np.float32) * 0.5
    fid = sorted(BASE_REGISTRY.keys())[0]
    cat = normalize_catalog_stack([{"id": fid, "weight": 1.0}])
    reg = scratch_spec_from_any_paint(tex, seed=7, chromatic_shift=False, catalog_stack=cat)
    proc = scratch_spec_from_any_paint(tex, seed=7, chromatic_shift=False, preset_stack=[("mirror_chrome", 1.0)])
    assert reg.shape == proc.shape == (16, 16, 4)
    assert not np.array_equal(reg[:, :, :3], proc[:, :, :3])


def test_preset_layer_chromatic_gate():
    # 2026-06-01: chromatic flag retired (presets now map to real finishes). The shim
    # simply mirrors the global chromatic toggle regardless of preset id.
    assert preset_layer_chromatic("mirror_chrome", True) is True
    assert preset_layer_chromatic("mirror_chrome", False) is False
    assert preset_layer_chromatic("forged_carbon", False) is False


def test_seed_changes_output():
    tex = np.ones((16, 16, 3), dtype=np.float32) * 0.3
    a = scratch_spec_from_any_paint(tex, seed=1, chromatic_shift=False)
    b = scratch_spec_from_any_paint(tex, seed=2, chromatic_shift=False)
    assert not np.array_equal(a[:, :, :3], b[:, :, :3])
