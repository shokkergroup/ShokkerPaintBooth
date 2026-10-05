"""Focused contracts for opt-in Whole Car paint-aware material routing.

The production finish functions are replaced with tiny deterministic authored
M/R/Cc plates so these tests isolate blend semantics instead of catalog startup
or renderer artwork.  Default catalog callers and one-finish Whole Car remain
byte-identical; only an explicit 2–4 layer context gets spatial routing.
"""

from __future__ import annotations

import numpy as np
import pytest

from engine.spec_sculpt import catalog_blend


@pytest.fixture()
def authored_catalog(monkeypatch):
    import engine.compose as compose

    values = {
        "matte": (20.0, 220.0, 25.0),
        "gloss": (220.0, 28.0, 235.0),
        "mid": (112.0, 124.0, 148.0),
        "unsafe_low": (-80.0, np.nan, -40.0),
        "unsafe_high": (380.0, np.inf, 440.0),
    }

    def resolve(finish_id, shape, mask, seed, sm, **_kwargs):
        h, w = shape
        metallic, roughness, clearcoat = values[finish_id]
        return (
            np.full((h, w), metallic, dtype=np.float32),
            np.full((h, w), roughness, dtype=np.float32),
            np.full((h, w), clearcoat, dtype=np.float32),
        )

    monkeypatch.setattr(compose, "_resolve_finish_spec", resolve)
    monkeypatch.setattr(catalog_blend, "_full_monolithic_registry", lambda: None)
    return values, resolve


def livery(height=80, width=120):
    yy, xx = np.indices((height, width), dtype=np.float32)
    x = xx / max(1.0, float(width - 1))
    y = yy / max(1.0, float(height - 1))
    rgb = np.empty((height, width, 3), dtype=np.float32)
    rgb[..., 0] = np.clip(0.05 + x * 0.90, 0.0, 1.0)
    rgb[..., 1] = np.clip(0.08 + y * 0.72 + (np.sin(xx * 0.42) > 0) * 0.16, 0.0, 1.0)
    rgb[..., 2] = np.clip(0.92 - x * 0.76 + (np.cos(yy * 0.31) > 0) * 0.06, 0.0, 1.0)
    return rgb


def render(stack, source, *, aware):
    mask = np.ones(source.shape[:2], dtype=np.float32)
    if aware:
        with catalog_blend.paint_aware_spatial_mix(source):
            return catalog_blend.blend_registered_specs_float(
                source.shape[:2], mask, seed=9101, sm=1.0, stack=stack
            )
    return catalog_blend.blend_registered_specs_float(
        source.shape[:2], mask, seed=9101, sm=1.0, stack=stack
    )


def test_default_path_is_the_original_uniform_weighted_average(authored_catalog):
    _values, resolve = authored_catalog
    source = livery(32, 48)
    stack = [("matte", 0.65), ("gloss", 0.35)]

    actual = render(stack, source, aware=False)
    matte = resolve("matte", source.shape[:2], np.ones(source.shape[:2]), 9101, 1.0)
    gloss = resolve("gloss", source.shape[:2], np.ones(source.shape[:2]), 9101, 1.0)
    expected = np.zeros((*source.shape[:2], 4), dtype=np.float32)
    for channel in range(3):
        expected[..., channel] = matte[channel] * 0.65 + gloss[channel] * 0.35
    expected[..., 3] = 255.0

    assert np.array_equal(actual, expected)


def test_one_finish_is_byte_identical_even_inside_opt_in_context(authored_catalog):
    source = livery()
    stack = [("gloss", 1.0)]

    default = render(stack, source, aware=False)
    opted_in = render(stack, source, aware=True)

    assert np.array_equal(opted_in, default)


def test_multi_finish_mix_is_deterministic_and_never_mutates_source(authored_catalog):
    source = livery()
    before = source.copy()
    stack = [("matte", 0.55), ("gloss", 0.30), ("mid", 0.15)]

    first = render(stack, source, aware=True)
    second = render(stack, source, aware=True)

    assert np.array_equal(first, second)
    assert np.array_equal(source, before), "spec routing modified diffuse/source paint"


def test_multi_finish_weights_vary_smoothly_but_keep_global_user_coverage(authored_catalog):
    source = livery(96, 144)
    stack = [("matte", 0.60), ("gloss", 0.40)]

    uniform = render(stack, source, aware=False)
    spatial = render(stack, source, aware=True)

    assert float(np.std(uniform[..., 0])) == pytest.approx(0.0)
    assert float(np.std(spatial[..., 0])) >= 8.0
    # Constant authored plates make the global prior directly observable:
    # 60% * M20 + 40% * M220 = M100.
    assert float(np.mean(spatial[..., 0])) == pytest.approx(100.0, abs=0.8)
    # Smooth routing should not introduce one-pixel assignment noise.
    neighbor_jump = np.abs(np.diff(spatial[..., 0], axis=1))
    assert float(np.percentile(neighbor_jump, 99.0)) < 28.0


def test_user_weight_remains_the_dominant_global_control(authored_catalog):
    source = livery(72, 108)
    matte_heavy = render([("matte", 0.85), ("gloss", 0.15)], source, aware=True)
    gloss_heavy = render([("matte", 0.15), ("gloss", 0.85)], source, aware=True)

    assert float(np.mean(matte_heavy[..., 0])) == pytest.approx(50.0, abs=1.0)
    assert float(np.mean(gloss_heavy[..., 0])) == pytest.approx(190.0, abs=1.0)
    assert float(np.mean(gloss_heavy[..., 0]) - np.mean(matte_heavy[..., 0])) >= 135.0


def test_opt_in_mix_sanitizes_channels_and_keeps_opaque_iracing_alpha(authored_catalog):
    source = livery(40, 64)
    result = render([("unsafe_low", 0.45), ("unsafe_high", 0.55)], source, aware=True)

    assert result.dtype == np.float32
    assert np.all(np.isfinite(result))
    assert float(np.min(result[..., :3])) >= 0.0
    assert float(np.max(result[..., :3])) <= 255.0
    assert np.all(result[..., 3] == 255.0)

