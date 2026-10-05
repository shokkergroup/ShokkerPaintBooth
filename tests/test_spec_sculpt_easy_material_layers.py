"""Focused contracts for guided Spec Sculpt color layers and linked scale."""

from __future__ import annotations

import json

import numpy as np

from engine.spec_sculpt.easy_material_layers import (
    MAX_EASY_COLOR_LAYERS,
    apply_material_impact,
    apply_material_impact_to_report,
    composite_easy_color_layers,
    normalize_material_impact,
    normalize_material_scale,
    parse_easy_color_layers,
    pattern_tile_for_scale,
    recolor_easy_paint,
)


def test_linked_base_scale_only_allows_finer_materials():
    assert normalize_material_scale(3.0) == 1.0
    assert normalize_material_scale(0.63) == 0.65
    assert normalize_material_scale(0.01) == 0.25
    assert pattern_tile_for_scale(1.0) == 1.0
    assert pattern_tile_for_scale(0.5) == 2.0
    assert pattern_tile_for_scale(0.25) == 4.0


def test_material_impact_preserves_authored_pattern_while_changing_response():
    neutral = [0, 160, 255]
    spec = np.array([[[*neutral, 255], [100, 80, 40, 255]]], dtype=np.uint8)

    balanced = apply_material_impact(spec, "balanced")
    subtle = apply_material_impact(spec, "subtle")
    bold = apply_material_impact(spec, "bold")

    assert normalize_material_impact("LOUD") == "balanced"
    assert normalize_material_impact("BOLD") == "bold"
    assert np.array_equal(balanced, spec)
    assert np.array_equal(subtle[0, 0], spec[0, 0])
    assert np.array_equal(bold[0, 0], spec[0, 0])
    assert np.all(np.abs(subtle[0, 1, :3] - neutral) < np.abs(spec[0, 1, :3].astype(int) - neutral))
    assert np.all(np.abs(bold[0, 1, :3].astype(int) - neutral) >= np.abs(spec[0, 1, :3].astype(int) - neutral))
    assert subtle[0, 1, 3] == bold[0, 1, 3] == 255


def test_material_impact_updates_selected_color_response_report():
    report = [{
        "slot_id": "cyan",
        "material_means": [0.5, 0.3, 0.8],
        "material_deviations": [0.1, 0.2, 0.3],
    }]

    subtle = apply_material_impact_to_report(report, "subtle")[0]
    bold = apply_material_impact_to_report(report, "bold")[0]

    # Metal is closer to zero and raw blue closer to 255 (less human coat) in
    # Subtle; Bold moves both the other way. Source data stays reusable.
    assert subtle["material_means"][0] < report[0]["material_means"][0] < bold["material_means"][0]
    assert subtle["material_means"][2] > report[0]["material_means"][2] > bold["material_means"][2]
    assert subtle["material_deviations"][1] < report[0]["material_deviations"][1] < bold["material_deviations"][1]
    assert report[0]["material_means"] == [0.5, 0.3, 0.8]


def test_easy_color_payload_is_validated_clamped_and_bounded():
    raw = [
        {
            "slot_id": f"slot-{index}",
            "color": [300, -4, 40],
            "tolerance": 500,
            "kind": "catalog",
            "look_id": f"look-{index}",
            "seed": 0x100000001,
            "material_scale": 0.48,
            "replacement_color": [0, 300, 20],
        }
        for index in range(MAX_EASY_COLOR_LAYERS + 3)
    ]
    parsed = parse_easy_color_layers(json.dumps(raw))

    assert len(parsed) == MAX_EASY_COLOR_LAYERS
    assert parsed[0]["color"] == [255, 0, 40]
    assert parsed[0]["tolerance"] == 90.0
    assert parsed[0]["seed"] == 1
    assert parsed[0]["material_scale"] == 0.5
    assert parsed[0]["replacement_color"] == [0, 255, 20]
    assert parse_easy_color_layers([{"kind": "preset", "look_id": "x", "color": [1, 2, 3], "seed": "bad"}])[0]["seed"] is None
    assert parse_easy_color_layers([{"kind": "mode", "look_id": "unknown", "color": [1, 2, 3]}]) == []


def test_recolor_easy_paint_changes_only_the_selected_color_and_keeps_shading():
    paint = np.zeros((32, 32, 3), np.float32)
    paint[:, :16] = [0.9, 0.08, 0.08]
    paint[:, 16:] = [0.08, 0.12, 0.9]
    paint[8:16, :16] *= 0.55
    layer = parse_easy_color_layers(
        [{
            "slot_id": "red",
            "color": [230, 20, 20],
            "tolerance": 18,
            "kind": "preset",
            "look_id": "mirror_chrome",
            "replacement_color": [20, 230, 60],
        }]
    )

    result = recolor_easy_paint(paint, layer)

    assert result[4, 5, 1] > result[4, 5, 0]
    assert result[10, 5, 1] < result[4, 5, 1]
    assert np.allclose(result[10, 27], paint[10, 27], atol=1e-4)


def test_color_material_composite_changes_only_the_sampled_paint_area():
    paint = np.zeros((32, 32, 3), np.float32)
    paint[:, :16] = [0.9, 0.08, 0.08]
    paint[:, 16:] = [0.08, 0.12, 0.9]
    base = np.full((32, 32, 4), 20, np.uint8)
    base[..., 3] = 255
    layer = parse_easy_color_layers(
        [{
            "slot_id": "red",
            "color": [230, 20, 20],
            "tolerance": 18,
            "kind": "preset",
            "look_id": "mirror_chrome",
            "material_scale": 0.5,
        }]
    )

    def render(_layer):
        result = np.full_like(base, 220)
        result[..., 3] = 255
        return result

    result, report = composite_easy_color_layers(base, paint, layer, render)

    assert result.dtype == np.uint8
    assert result.shape == base.shape
    assert result[10, 5, 0] > 180
    assert result[10, 27, 0] == 20
    assert np.all(result[..., 3] == 255)
    assert report[0]["matched"] is True
    assert 45.0 < report[0]["coverage_pct"] < 55.0
    assert np.allclose(report[0]["material_means"], [220 / 255.0] * 3, atol=1e-4)
    assert np.allclose(report[0]["material_deviations"], [0.0, 0.0, 0.0], atol=1e-5)
