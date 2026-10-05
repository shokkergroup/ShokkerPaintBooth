from __future__ import annotations

import contextlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import shokker_engine_v2 as eng
from engine.compose import compose_paint_mod, compose_paint_mod_stacked


REPO = Path(__file__).resolve().parent.parent
SHAPE = (64, 64)
LAYER_SHAPE = (48, 48)


def _run_overlay_payload_harness() -> dict:
    result = subprocess.run(
        ["node", "tests/_runtime_harness/overlay_only_zone_payload.mjs"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def test_special_overlay_payload_preserves_all_color_source_combinations():
    payload = _run_overlay_payload_harness()

    assert payload["scoped_white_special_overlay"][0]["source_layer_mask"] == "region-rle"
    assert payload["scoped_white_special_overlay"][0]["second_base"] == "mono:firefly_glow"
    assert payload["scoped_white_special_overlay"][0]["second_base_color_source"] == "overlay"

    assert payload["special_overlay_solid_color"][0]["second_base"] == "mono:firefly_glow"
    assert payload["special_overlay_solid_color"][0]["second_base_color_source"] == "solid"
    assert payload["special_overlay_solid_color"][0]["second_base_hue_shift"] == 42
    assert payload["special_overlay_solid_color"][0]["second_base_saturation"] == 18
    assert payload["special_overlay_solid_color"][0]["second_base_brightness"] == -12

    assert payload["legacy_special_overlay_solid_color"][0]["second_base"] == "mono:firefly_glow"
    assert payload["legacy_special_overlay_solid_color"][0]["second_base_color_source"] == "overlay"

    assert payload["regular_overlay_special_color"][0]["second_base"] == "f_metallic"
    assert payload["regular_overlay_special_color"][0]["second_base_color_source"] == "mono:firefly_glow"

    assert payload["fifth_layer_special_color"][0]["fifth_base"] == "f_metallic"
    assert payload["fifth_layer_special_color"][0]["fifth_base_color_source"] == "mono:firefly_glow"
    assert payload["fifth_layer_special_color"][0]["fifth_base_hue_shift"] == -35
    assert payload["fifth_layer_special_color"][0]["fifth_base_saturation"] == 22
    assert payload["fifth_layer_special_color"][0]["fifth_base_brightness"] == 9


def test_preview_server_base_overlay_passthrough_includes_visual_tuning_fields():
    src = (REPO / "server.py").read_text(encoding="utf-8")
    start = src.index("# Base Overlay Layers")
    end = src.index("# Region mask", start)
    block = src[start:end]
    for suffix in (
        "_spec_strength",
        "_hue_shift",
        "_saturation",
        "_brightness",
        "_pattern_hue_shift",
        "_pattern_saturation",
        "_pattern_brightness",
        "_pattern_flip_h",
        "_pattern_flip_v",
        "_fit_zone",
    ):
        assert f'f"{{_pfx}}{suffix}"' in block, (
            f"Live preview overlay passthrough is missing {suffix}; "
            "preview would diverge from final render."
        )


def _compose_with_layer(fn, layer_key: str) -> np.ndarray:
    paint = np.full((SHAPE[0], SHAPE[1], 3), 0.34, dtype=np.float32)
    mask = np.ones(SHAPE, dtype=np.float32)
    bb = np.zeros(SHAPE, dtype=np.float32)
    kwargs = {
        layer_key: "f_metallic",
        f"{layer_key}_strength": 1.0,
        f"{layer_key}_color_source": "mono:firefly_glow",
        f"{layer_key}_blend_mode": "tint",
    }
    with contextlib.redirect_stdout(io.StringIO()):
        if fn is compose_paint_mod_stacked:
            return fn("gloss", [], paint.copy(), SHAPE, mask, 42, 1.0, bb, monolithic_registry=eng.MONOLITHIC_REGISTRY, **kwargs)
        return fn("gloss", "none", paint.copy(), SHAPE, mask, 42, 1.0, bb, monolithic_registry=eng.MONOLITHIC_REGISTRY, **kwargs)


def test_special_overlay_color_sources_change_paint_for_all_five_zone_layers():
    baseline = np.full((SHAPE[0], SHAPE[1], 3), 0.34, dtype=np.float32)
    for fn in (compose_paint_mod, compose_paint_mod_stacked):
        for layer_key in ("second_base", "third_base", "fourth_base", "fifth_base"):
            out = _compose_with_layer(fn, layer_key)
            delta = float(np.mean(np.abs(out[:, :, :3] - baseline)))
            assert np.isfinite(out).all(), (fn.__name__, layer_key)
            assert delta > 0.08, (fn.__name__, layer_key, delta)


def _write_red_layer_fixture(tmp_path: Path) -> tuple[Path, np.ndarray, np.ndarray]:
    h, w = LAYER_SHAPE
    source = np.full((h, w, 4), 255, dtype=np.uint8)
    source[:, :, :3] = [255, 0, 0]
    source[:, :, 3] = 255
    source_path = tmp_path / "overlay_matrix_source.png"
    Image.fromarray(source).save(source_path)

    source_layer_mask = np.zeros((h, w), dtype=np.float32)
    source_layer_mask[:, : w // 2] = 1.0
    return source_path, source, source_layer_mask


def _stacked_overlay_matrix_zone(source_layer_mask: np.ndarray) -> dict:
    return {
        "name": "SPB-9 overlay matrix",
        "color": {"color_rgb": [255, 0, 0], "tolerance": 12},
        "base": "f_metallic",
        "pattern": "carbon_fiber",
        "intensity": "100",
        "source_layer_mask": source_layer_mask,
        "base_color_mode": "solid",
        "base_color": [0.25, 0.30, 0.95],
        "second_base": "mono:firefly_glow",
        "second_base_color_source": "overlay",
        "second_base_strength": 1.0,
        "second_base_spec_strength": 1.0,
        "second_base_blend_mode": "tint",
        "second_base_pattern": "speed_lines",
        "third_base": "f_metallic",
        "third_base_color_source": "mono:firefly_glow",
        "third_base_strength": 0.8,
        "third_base_blend_mode": "pattern_vivid",
        "third_base_pattern": "carbon_fiber",
        "fourth_base": "gloss",
        "fourth_base_color_source": "solid",
        "fourth_base_color": [1.0, 0.1, 0.1],
        "fourth_base_strength": 0.6,
        "fourth_base_blend_mode": "noise",
        "fifth_base": "f_metallic",
        "fifth_base_color_source": "mono:firefly_glow",
        "fifth_base_strength": 0.5,
        "fifth_base_blend_mode": "tint",
        "fifth_base_pattern": "speed_lines",
        "spec_pattern_stack": [
            {"pattern": "crushed_glass", "opacity": 0.5, "channels": "MR", "scale": 1.0},
        ],
        "overlay_spec_pattern_stack": [
            {"pattern": "sparkle_galaxy_swirl", "opacity": 0.4, "channels": "M"},
        ],
    }


def _assert_layer_restricted_overlay_rendered(paint, spec, source):
    w_mid = paint.shape[1] // 2
    default_spec = np.array([5, 100, 16], dtype=np.float32)

    active_paint_delta = float(np.mean(np.abs(paint[:, :w_mid].astype(float) - source[:, :w_mid, :3].astype(float))))
    inactive_paint_delta = float(np.mean(np.abs(paint[:, w_mid:].astype(float) - source[:, w_mid:, :3].astype(float))))
    active_spec_delta = float(np.mean(np.abs(spec[:, :w_mid, :3].astype(float) - default_spec)))
    inactive_spec_delta = float(np.mean(np.abs(spec[:, w_mid:, :3].astype(float) - default_spec)))

    assert active_paint_delta > 25.0
    assert inactive_paint_delta < 1.0
    assert active_spec_delta > 10.0
    assert inactive_spec_delta < 1.0


def test_stacked_base_overlay_matrix_renders_in_preview_final_and_export_layers(tmp_path):
    source_path, source, source_layer_mask = _write_red_layer_fixture(tmp_path)
    zone = _stacked_overlay_matrix_zone(source_layer_mask)

    with contextlib.redirect_stdout(io.StringIO()):
        preview_paint, preview_spec = eng.build_multi_zone(
            str(source_path),
            str(tmp_path / "preview"),
            [dict(zone)],
            seed=123,
            preview_mode=True,
        )
        final_paint, final_spec, final_masks, export_layers = eng.build_multi_zone(
            str(source_path),
            str(tmp_path / "final"),
            [dict(zone)],
            seed=123,
            preview_mode=False,
            export_layers=True,
        )

    _assert_layer_restricted_overlay_rendered(preview_paint, preview_spec, source)
    _assert_layer_restricted_overlay_rendered(final_paint, final_spec, source)

    assert len(final_masks) == 1
    assert final_masks[0][:, : LAYER_SHAPE[1] // 2].mean() > 0.95
    assert final_masks[0][:, LAYER_SHAPE[1] // 2 :].mean() < 0.01
    assert len(export_layers) == 1
    assert export_layers[0]["mask"].sum() == pytest.approx(float(source_layer_mask.sum()))
    assert export_layers[0]["paint"][:, : LAYER_SHAPE[1] // 2].mean() > 1.0
    assert export_layers[0]["paint"][:, LAYER_SHAPE[1] // 2 :].mean() == pytest.approx(0.0)


def test_mono_prefixed_base_registry_specials_are_valid_overlay_inputs(tmp_path):
    source_path, source, source_layer_mask = _write_red_layer_fixture(tmp_path)
    zone = {
        "name": "SPB-9 mono-prefixed base special",
        "color": {"color_rgb": [255, 0, 0], "tolerance": 12},
        "base": "mono:firefly_glow",
        "intensity": "100",
        "source_layer_mask": source_layer_mask,
        "second_base": "f_metallic",
        "second_base_color_source": "solid",
        "second_base_color": [0.1, 0.2, 1.0],
        "second_base_strength": 1.0,
        "second_base_blend_mode": "tint",
    }

    eng._validate_all_zone_render_ids([zone])

    with contextlib.redirect_stdout(io.StringIO()):
        paint, spec = eng.build_multi_zone(
            str(source_path),
            str(tmp_path / "mono_prefixed"),
            [zone],
            seed=321,
            preview_mode=True,
        )

    _assert_layer_restricted_overlay_rendered(paint, spec, source)


def test_split_preview_zoom_does_not_bubble_into_source_canvas_zoom():
    src = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "stopImmediatePropagation" in src
    assert "e.target.closest('#splitPreview" in src
    assert "#livePreviewImg" in src
    assert "#previewSpecPane" in src


def test_render_dock_and_spec_thumbnail_stay_compact_in_split_view():
    css = (REPO / "paint-booth-v2.css").read_text(encoding="utf-8")
    assert "width: 168px !important;" in css
    assert "max-width: 118px;" in css
    assert "width: 20%;" in css
