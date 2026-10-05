from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path

from engine.overlay import blend_dual_base_spec, get_base_overlay_alpha


def _solid_spec(metallic: int, roughness: int, clearcoat: int, shape=(8, 8)) -> np.ndarray:
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:, :, 0] = metallic
    spec[:, :, 1] = roughness
    spec[:, :, 2] = clearcoat
    spec[:, :, 3] = 255
    return spec


def test_base_overlay_spec_strength_is_linear_for_full_pattern_mask():
    primary = _solid_spec(40, 80, 32)
    secondary = _solid_spec(200, 140, 192)
    pattern = np.ones(primary.shape[:2], dtype=np.float32)

    for strength in (0.0, 0.10, 0.50, 1.0):
        blended, alpha = blend_dual_base_spec(
            primary,
            secondary,
            strength=strength,
            blend_mode="pattern",
            pattern_mask=pattern,
        )

        assert np.allclose(alpha, strength)
        expected_metallic = int(40 * (1.0 - strength) + 200 * strength)
        expected_roughness = int(80 * (1.0 - strength) + 140 * strength)
        expected_clearcoat = int(32 * (1.0 - strength) + 192 * strength)
        assert np.all(blended[:, :, 0] == expected_metallic)
        assert np.all(blended[:, :, 1] == expected_roughness)
        assert np.all(blended[:, :, 2] == expected_clearcoat)


def test_base_overlay_tint_can_fully_replace_spec_at_100_percent():
    primary = _solid_spec(40, 80, 32)
    secondary = _solid_spec(200, 140, 192)

    blended, alpha = blend_dual_base_spec(
        primary,
        secondary,
        strength=1.0,
        blend_mode="tint",
    )

    assert np.allclose(alpha, 1.0)
    assert np.all(blended[:, :, :3] == secondary[:, :, :3])


def test_base_overlay_noise_spec_has_no_low_strength_leakage():
    def flat_noise(shape, scales, weights, seed):
        return np.ones(shape, dtype=np.float32)

    alpha = get_base_overlay_alpha(
        (64, 64),
        strength=0.0,
        blend_mode="noise",
        noise_fn=flat_noise,
    )

    assert np.max(alpha) == 0.0


@pytest.mark.parametrize(
    "blend_mode",
    (
        "pattern",
        "pattern-pop",
        "pattern-edges",
        "pattern-peaks",
        "pattern-contour",
        "pattern-screen",
        "pattern-threshold",
    ),
)
def test_pattern_overlay_modes_noop_without_overlay_pattern_mask(blend_mode):
    alpha = get_base_overlay_alpha(
        (32, 32),
        strength=1.0,
        blend_mode=blend_mode,
    )

    assert np.max(alpha) == 0.0


def test_tint_overlay_without_pattern_remains_uniform_zone_wash():
    alpha = get_base_overlay_alpha(
        (32, 32),
        strength=0.4,
        blend_mode="tint",
    )

    assert np.allclose(alpha, 0.4)


def test_pattern_overlay_spec_without_pattern_mask_leaves_primary_unchanged():
    primary = _solid_spec(40, 80, 32)
    secondary = _solid_spec(200, 140, 192)

    blended, alpha = blend_dual_base_spec(
        primary,
        secondary,
        strength=1.0,
        blend_mode="pattern-edges",
    )

    assert np.max(alpha) == 0.0
    assert np.array_equal(blended, primary)


def test_pattern_pop_full_pattern_mask_can_fully_replace_spec():
    primary = _solid_spec(40, 80, 32)
    secondary = _solid_spec(200, 140, 192)
    pattern = np.ones(primary.shape[:2], dtype=np.float32)

    blended, alpha = blend_dual_base_spec(
        primary,
        secondary,
        strength=1.0,
        blend_mode="pattern-pop",
        pattern_mask=pattern,
    )

    assert np.allclose(alpha, 1.0)
    assert np.array_equal(blended[:, :, :3], secondary[:, :, :3])


def test_overlay_pattern_reactive_empty_ui_value_uses_zone_primary_pattern():
    from engine.compose import _resolve_overlay_pattern_mask_id

    assert (
        _resolve_overlay_pattern_mask_id("", "art_deco", "pattern-pop")
        == "art_deco"
    )
    assert (
        _resolve_overlay_pattern_mask_id(None, "art_deco", "pattern-reactive")
        == "art_deco"
    )


def test_overlay_pattern_reactive_without_any_pattern_noops():
    from engine.compose import _resolve_overlay_pattern_mask_id

    assert _resolve_overlay_pattern_mask_id("", None, "pattern-pop") is None
    assert _resolve_overlay_pattern_mask_id("", "art_deco", "tint") is None


@pytest.mark.parametrize("blank_value", ("", "__none__", "None (Independent)"))
def test_pattern_pop_blank_overlay_pattern_inherits_primary_pattern(blank_value):
    from engine.compose import _resolve_overlay_pattern_mask_id

    assert (
        _resolve_overlay_pattern_mask_id(blank_value, "Art_Deco", "pattern-pop")
        == "Art_Deco"
    )


def test_tint_blank_overlay_pattern_stays_independent():
    from engine.compose import _resolve_overlay_pattern_mask_id

    assert _resolve_overlay_pattern_mask_id("__none__", "Art_Deco", "tint") is None


def test_render_bridge_preserves_empty_overlay_pattern_as_zone_primary():
    from shokker_engine_v2 import _normalize_base_overlay_pattern_id

    assert _normalize_base_overlay_pattern_id("") == ""
    assert _normalize_base_overlay_pattern_id("__none__") == "__none__"
    assert _normalize_base_overlay_pattern_id(None) is None


def test_solid_overlay_color_does_not_run_base_paint_renderer():
    from engine.compose import _overlay_should_apply_base_paint_fn

    assert _overlay_should_apply_base_paint_fn("solid") is False
    assert _overlay_should_apply_base_paint_fn(None) is False
    assert _overlay_should_apply_base_paint_fn("base:some_finish") is False
    assert _overlay_should_apply_base_paint_fn("overlay") is True


@pytest.mark.parametrize("prefix", ("second", "third", "fourth", "fifth"))
@pytest.mark.parametrize(
    "blend_mode",
    (
        "pattern-pop",
        "pattern-edges",
        "pattern-peaks",
        "pattern-contour",
        "pattern-screen",
        "pattern-threshold",
    ),
)
def test_pattern_reactive_solid_base_overlay_is_confined_to_linked_pattern(prefix, blend_mode, monkeypatch):
    from engine.compose import _get_pattern_mask, compose_paint_mod
    from engine.registry import PATTERN_REGISTRY

    shape = (96, 96)
    mask = np.ones(shape, dtype=np.float32)
    seed = 23771
    paint = np.full((shape[0], shape[1], 3), 0.22, dtype=np.float32)

    def _texture_center_bar(shape, mask, seed, sm):
        arr = np.zeros(shape, dtype=np.float32)
        arr[:, shape[1] // 3 : shape[1] * 2 // 3] = 1.0
        return arr

    pattern_id = "_test_overlay_center_bar"
    monkeypatch.setitem(
        PATTERN_REGISTRY,
        pattern_id,
        {"desc": "test center bar", "texture_fn": _texture_center_bar},
    )
    pattern_mask = _get_pattern_mask(
        pattern_id,
        shape,
        mask,
        seed,
        1.0,
        scale=1.0,
        rotation=0.0,
        opacity=1.0,
        strength=1.0,
    )
    assert pattern_mask is not None

    kwargs = {
        f"{prefix}_base_color": [1.0, 0.0, 0.0],
        f"{prefix}_base_strength": 1.0,
        f"{prefix}_base_blend_mode": blend_mode,
        f"{prefix}_base_pattern": "",
        f"{prefix}_base_pattern_scale": 1.0,
        f"{prefix}_base_pattern_opacity": 1.0,
        f"{prefix}_base_pattern_strength": 1.0,
    }
    out = compose_paint_mod(
        "gloss",
        pattern_id,
        paint.copy(),
        shape,
        mask,
        seed,
        1.0,
        1.0,
        **kwargs,
    )
    out = np.asarray(out)[:, :, :3]

    alpha = get_base_overlay_alpha(
        shape,
        strength=1.0,
        blend_mode=blend_mode,
        pattern_mask=pattern_mask,
        zone_mask=mask,
    )
    low_mask = alpha < 0.02
    high_mask = alpha > 0.25
    assert low_mask.any()
    assert high_mask.any()
    assert float(np.mean(np.abs(out[low_mask] - paint[low_mask]))) < 0.08
    assert float(np.mean(out[high_mask, 0] - np.maximum(out[high_mask, 1], out[high_mask, 2]))) > 0.08


@pytest.mark.parametrize("overlay_pattern", ("", "__none__"))
@pytest.mark.parametrize("pattern_id", ("art_deco", "Art_Deco"))
def test_art_deco_scaled_third_base_pattern_pop_harden_recolors_visible_pattern(overlay_pattern, pattern_id):
    from engine.compose import _get_pattern_mask, _harden_overlay_pattern_mask, compose_paint_mod

    shape = (128, 192)
    mask = np.ones(shape, dtype=np.float32)
    seed = 23771
    scale = 0.35
    paint = np.full((shape[0], shape[1], 3), 0.45, dtype=np.float32)

    out = compose_paint_mod(
        "gloss",
        pattern_id,
        paint.copy(),
        shape,
        mask,
        seed,
        1.0,
        1.0,
        scale=scale,
        third_base_color=[0.0, 0.20, 1.0],
        third_base_strength=1.0,
        third_base_color_source="solid",
        third_base_blend_mode="pattern-vivid",
        third_base_pattern=overlay_pattern,
        third_base_pattern_scale=scale,
        third_base_pattern_opacity=1.0,
        third_base_pattern_strength=1.0,
        third_base_pattern_harden=True,
    )
    out = np.asarray(out)[:, :, :3]
    pattern_mask = _get_pattern_mask(
        pattern_id,
        shape,
        mask,
        seed,
        1.0,
        scale=scale,
        opacity=1.0,
        strength=1.0,
    )
    pattern_mask = _harden_overlay_pattern_mask(pattern_mask)
    alpha = get_base_overlay_alpha(
        shape,
        strength=1.0,
        blend_mode="pattern-vivid",
        pattern_mask=pattern_mask,
        zone_mask=mask,
    )

    high_mask = alpha > 0.25
    low_mask = alpha < 0.02
    assert high_mask.any()
    assert low_mask.any()
    assert float(np.mean(out[high_mask, 2] - np.maximum(out[high_mask, 0], out[high_mask, 1]))) > 0.20
    assert float(np.mean(np.abs(out[low_mask] - paint[low_mask]))) < 0.15


def test_paint_overlay_pattern_masks_use_primary_seed_for_alignment():
    source = Path("engine/compose.py").read_text(encoding="utf-8")
    assert "seed + 5555" not in source
    assert "seed + 3333" not in source
    assert "seed + 4444" not in source


def test_monolithic_legacy_overlay_path_uses_shared_alpha_for_all_pattern_modes():
    source = Path("shokker_engine_v2.py").read_text(encoding="utf-8")
    assert '"pattern_edges"' in source
    assert '"pattern_peaks"' in source
    assert '"pattern_contour"' in source
    assert '"pattern_screen"' in source
    assert '"pattern_threshold"' in source
    assert "_sb_bm_norm in _sb_pattern_modes" in source
    assert "_sb_bm_norm in (\"pattern\", \"pattern_vivid\", \"tint\")" not in source
    assert "get_base_overlay_alpha(" in source
