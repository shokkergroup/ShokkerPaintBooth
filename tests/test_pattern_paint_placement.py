"""Owner 2026-09-07: shrinking patterns must shrink ink, not fade the design."""
import contextlib
import io
import numpy as np
import pytest
from engine.pattern_paint_placement import render_pattern_paint


def stripes(paint, shape, mask, seed, pm, bb):
    x = np.arange(shape[1])[None, :]
    ink = np.where(x % 32 < 8, .16, -.04) * min(1., pm)
    return np.clip(paint + ink[:, :, None] * mask[:, :, None], 0, 1).astype(np.float32)
stripes._spb_pattern_direct_paint = True


def test_half_size_doubles_repetitions_without_fading_or_moving_source():
    shape = (128, 128)
    source = np.full((*shape, 3), .5, np.float32)
    source[20:30, 40:50] = (.7, .3, .5)  # an existing logo
    mask = np.zeros(shape, np.float32); mask[8:120, 8:120] = 1
    original = source.copy()
    normal = render_pattern_paint(stripes, source, shape, mask, 42, 1, 0)
    small = render_pattern_paint(stripes, source, shape, mask, 42, 1, 0, scale=.5)
    expected_ink = np.where(np.arange(128) % 16 < 4, .16, -.04)
    np.testing.assert_allclose(small, source + expected_ink[None, :, None]*mask[:, :, None], atol=1e-6)
    assert np.std((small-source)[64, :, 0]) > .9*np.std((normal-source)[64, :, 0])
    assert np.array_equal(small[mask == 0], source[mask == 0])
    assert np.array_equal(source, original)


@pytest.mark.parametrize('scale', [.7, .4, .25, 1.5])
@pytest.mark.parametrize('stacked', [False, True])
def test_public_composer_preserves_scaled_pattern_ink(monkeypatch, scale, stacked):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from engine.registry import PATTERN_REGISTRY
        from engine.compose import compose_paint_mod, compose_paint_mod_stacked
    monkeypatch.setitem(PATTERN_REGISTRY, '_placement_test', {'paint_fn': stripes})
    shape = (128, 128); mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), .5, np.float32)
    with contextlib.redirect_stdout(io.StringIO()):
        if stacked:
            out = compose_paint_mod_stacked('metallic', [dict(id='_placement_test', scale=scale, opacity=1)], source.copy(), shape, mask, 42, 1, 0, base_strength=0)
        else:
            out = compose_paint_mod('metallic', '_placement_test', source.copy(), shape, mask, 42, 1, 0, scale=scale, base_strength=0)
    expected = render_pattern_paint(stripes, source, shape, mask, 42, 1, 0, scale=scale)
    np.testing.assert_allclose(out, expected, atol=1e-6)


def test_actual_ammonite_native_unchanged_and_smaller_ink_stays_visible():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from engine.registry import PATTERN_REGISTRY
    fn = PATTERN_REGISTRY['ammonite_chambers']['paint_fn']
    shape = (512, 512); mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), .5, np.float32)
    native = fn(source.copy(), shape, mask, 42, 1.8, 0)
    assert np.array_equal(native, render_pattern_paint(fn, source.copy(), shape, mask, 42, 1.8, 0))
    delta = native-source
    for scale in [.7, .4, .25]:
        smaller = render_pattern_paint(fn, source.copy(), shape, mask, 42, 1.8, 0, scale=scale)-source
        assert smaller.std() > delta.std()*.7
        assert np.mean(np.abs(smaller-delta)) > .005


@pytest.mark.parametrize('scale', [.7, .4, .25])
def test_actual_ammonite_public_paint_uses_its_own_placed_design(scale):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from engine.registry import PATTERN_REGISTRY
        from engine.compose import compose_paint_mod
    fn = PATTERN_REGISTRY['ammonite_chambers']['paint_fn']
    shape=(512,512); mask=np.ones(shape,np.float32); source=np.full((*shape,3),.45,np.float32)
    expected=render_pattern_paint(fn,source.copy(),shape,mask,42,1.8,0,scale=scale)
    with contextlib.redirect_stdout(io.StringIO()):
        actual=compose_paint_mod('metallic','ammonite_chambers',source.copy(),shape,mask,42,1,0,scale=scale,base_strength=0)
    np.testing.assert_allclose(actual,expected,atol=1e-6)


def test_spec_size_repeats_features_and_all_placement_settings_reach_cached_output():
    from engine.compose import _cached_spec_pattern_array
    def field(shape, seed, sm, **params):
        a = np.zeros((*shape, 4), np.float32)
        a[:, :, :3] = (np.arange(shape[1])[None, :, None] % 32 < 8)*.8
        a[:, :, 3] = 1
        return a
    field._spb_overlay_version = 2
    def render(scale=1, rotation=0, x=.5, y=.5, box=100):
        return _cached_spec_pattern_array(field, '_placement_spec', (128,128), 42, 1, {}, scale, rotation, x, y, box)
    small = render(.5)
    assert np.sum(np.diff(small[64, :, 0] > .4).astype(int) != 0) >= 14
    assert small[:, :, 3].min() == 1  # Size must never shrink the coverage footprint.
    assert not np.array_equal(render(), small)
    assert not np.array_equal(small, render(.5, x=.6))
    assert not np.array_equal(small, render(.5, rotation=90))
    assert render(.5, box=25)[:, :, 3].mean() < .08
    assert np.array_equal(small, render(.5))  # Reusing a cache cannot substitute old size.
