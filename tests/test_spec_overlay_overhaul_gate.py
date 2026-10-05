"""SPB-105 spec-overlay overhaul gate contracts.

Owner verdict (2026-07-13): "WIDE diversity in spec pattern LOOKS... gloss,
flat, chrome, FRACTURED... FIVE ROUNDS."  These tests keep the Round-1 auditor
on native three-channel M/R/CC data and prevent silent regression to its stale
2D-only behavior.
"""

from __future__ import annotations

import numpy as np
import cv2

from scripts.audit_spec_pattern_quality import (
    _channel_metrics,
    _grade,
    _load_ui_spec_patterns,
    _structure_and_channels,
)
from engine.spec_pattern_families.overhaul_2026 import (
    _PALETTES,
    _grammar_for,
    _material_for,
    _stable,
    build_overhaul_catalog,
)
from engine.spec_pattern_families.visible_overlays_2026 import PICKER_VISIBLE_SPEC_IDS
from engine.spec_pattern_families.semantic_overlays_2026 import (
    semantic_archetype,
    semantic_field,
    semantic_texture_policy,
)


def test_modern_three_channel_spec_overlay_is_graded_as_mrc():
    y, x = np.indices((64, 64), dtype=np.float32)
    m = (x % 17) / 16.0
    r = (y % 13) / 12.0
    cc = ((x + y) % 19) / 18.0
    arr = np.dstack([m, r, cc]).astype(np.float32)

    structure, channels = _structure_and_channels(arr)
    stds, spans, max_corr = _channel_metrics(channels)

    assert structure.shape == (64, 64)
    assert len(channels) == 3
    assert min(stds) > 20.0 / 255.0
    assert min(spans) >= 0.99
    assert max_corr < 0.85


def test_gate_hard_flags_duplicate_weak_coupled_material_response():
    y, x = np.indices((64, 64), dtype=np.float32)
    structure = ((x + y) % 8) / 7.0
    meta = {"name": "Weak Chrome", "group": "Machined"}

    row = _grade(
        "weak_chrome",
        meta,
        structure,
        0.91,
        "same_math_elsewhere",
        [0.02, 0.03, 0.01],
        [0.20, 0.25, 0.15],
        0.97,
        12.0,
        85.0,
    )

    assert row.rebuild_required
    assert row.nearest_id == "same_math_elsewhere"
    assert {"NEAR_DUPLICATE", "WEAK_CHANNEL_STD", "NARROW_CHANNEL_RANGE", "CHANNEL_COUPLED"} <= set(row.flags)


def test_material_and_grammar_profiles_are_semantic_not_hash_accidents():
    cases = {
        "spec_weld_stack_rainbow": ("weld_bead", "optical"),
        "spec_mud_crackle_dried": ("lava_crack", "fractured"),
        "spec_carbon_2x2_twill": ("carbon_mesh", "composite"),
        "spec_ceramic_brake_sinter": ("pebble", "flat"),
        "spec_rain_bead_aero": ("dew_droplet", "gloss"),
        "jaguar_rosette": ("jaguar_rosette", None),
        "spec_noir_houndstooth_star": ("houndstooth", "flat"),
    }
    for pid, (grammar, material) in cases.items():
        key = _stable(pid)
        assert _grammar_for(pid, key) == grammar
        if material is not None:
            assert _material_for(pid, key) == material


def test_every_material_palette_has_eight_wide_mrc_tiers():
    assert set(_PALETTES) == {
        "chrome", "gloss", "satin", "flat", "fractured", "optical", "composite", "weathered"
    }
    for channels in _PALETTES.values():
        assert len(channels) == 3
        for values in channels:
            assert len(values) == 8
            assert max(values) - min(values) >= 0.85


def test_legacy_alias_shares_canonical_renderer_object():
    catalog = build_overhaul_catalog(("abstract_kandinsky_shapes", "voodoo_sigil_field"))
    assert catalog["abstract_kandinsky_shapes"] is catalog["voodoo_sigil_field"]


def test_saved_frequency_and_angle_controls_still_change_rendered_geometry():
    renderer = build_overhaul_catalog(("brushed_diagonal",))["brushed_diagonal"]
    coarse = renderer((128, 128), 42, 1.0, frequency=20, angle_deg=0)
    fine_rotated = renderer((128, 128), 42, 1.0, frequency=100, angle_deg=70)
    assert coarse.shape == (128, 128, 3)
    assert fine_rotated.shape == (128, 128, 3)
    assert not np.allclose(coarse, fine_rotated)


def test_python_overhaul_boundary_matches_js_picker_exactly():
    specs, _groups = _load_ui_spec_patterns()
    assert tuple(meta["id"] for meta in specs) == PICKER_VISIBLE_SPEC_IDS


def test_every_picker_overlay_has_an_explicit_semantic_identity():
    archetypes = [semantic_archetype(pid) for pid in PICKER_VISIBLE_SPEC_IDS]
    assert all(archetypes)
    assert len(set(archetypes)) >= 80
    assert semantic_archetype("spec_brick_mortar") == "brick_mortar"
    assert semantic_archetype("checker_flag_subtle") == "checker_cloth"
    assert semantic_archetype("spec_fish_scales") == "fish_scale"
    assert semantic_archetype("spec_snake_scales") == "snake_scale"


def test_loose_texture_is_opt_in_and_clean_is_the_catalog_default():
    policies = [semantic_texture_policy(pid) for pid in PICKER_VISIBLE_SPEC_IDS]
    assert all(policy in {"clean", "particulate", "surface"} for policy in policies)
    assert policies.count("clean") >= 140
    assert semantic_texture_policy("spec_brick_mortar") == "clean"
    assert semantic_texture_policy("checker_flag_subtle") == "clean"
    assert semantic_texture_policy("spec_fish_scales") == "clean"
    assert semantic_texture_policy("spec_snake_scales") == "clean"
    assert semantic_texture_policy("holographic_flake") == "particulate"
    assert semantic_texture_policy("metallic_sand") == "particulate"


def test_owner_named_clean_overlays_do_not_regress_to_tiny_color_confetti():
    ids = (
        "spec_brick_mortar", "checker_flag_subtle", "spec_fish_scales",
        "spec_snake_scales", "alligator_hide", "dragon_scale_macro",
    )
    catalog = build_overhaul_catalog(ids)
    for pid in ids:
        rendered = catalog[pid]((2048, 2048), 20260713, 1.0)
        rgb = np.clip(rendered[768:1280, 768:1280] * 255.0, 0, 255).astype(np.uint8)
        median = np.stack([cv2.medianBlur(rgb[:, :, channel], 3) for channel in range(3)], axis=2)
        outliers = (np.max(np.abs(rgb.astype(np.int16) - median.astype(np.int16)), axis=2) > 55).astype(np.uint8)
        count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(outliers, 8)
        tiny_pixels = sum(int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)
                          if int(stats[index, cv2.CC_STAT_AREA]) <= 4)
        assert tiny_pixels / float(rgb.shape[0] * rgb.shape[1]) < .005, pid


def test_owner_named_subject_fields_are_structurally_distinct_and_nonempty():
    x = np.arange(256, dtype=np.float32)[None, :]
    y = np.arange(256, dtype=np.float32)[:, None]
    ids = (
        "spec_brick_mortar", "checker_flag_subtle", "spec_fish_scales",
        "spec_snake_scales", "alligator_hide", "dragon_scale_macro",
    )
    fields = [semantic_field(pid, x, y, 2.4, .2, 1234, 2) for pid in ids]
    assert all(field is not None and field.shape == (256, 256) for field in fields)
    assert min(float(np.std(field)) for field in fields) > .15
    for i, field in enumerate(fields):
        for other in fields[i + 1:]:
            corr = abs(float(np.corrcoef(field.ravel(), other.ravel())[0, 1]))
            assert corr < .40


def test_intensity_is_neutral_at_zero_and_linear_around_delta_midpoint():
    renderer = build_overhaul_catalog(("spec_chrome_oval_chain",))["spec_chrome_oval_chain"]
    full = renderer((96, 96), 7, 1.0)
    half = renderer((96, 96), 7, 0.5)
    neutral = renderer((96, 96), 7, 0.0)
    assert np.allclose(neutral, 0.5)
    assert np.allclose(half - 0.5, (full - 0.5) * 0.5, atol=1e-6)
