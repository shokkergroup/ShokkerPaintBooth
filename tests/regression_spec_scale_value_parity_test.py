# -*- coding: utf-8 -*-
"""Regression guard: the spec-pattern scale-down fast path must preserve CHANNEL
VALUES, not just layout.

Owner report 2026-07-08: "the spec colors coming through are off, especially the
Red (Metallic) channels." Root cause: the 2026-07-07 tile-res speedup generated
patterns at tile resolution, but statistics-dependent generators self-normalize
per call — a 512² tile carries different channel means/stds than the 2048²
generation (measured up to 15/255 mean drift on spec_laser_etched). The cure
moment-matches the tile to cached canvas-res reference stats.

If this test fails, someone removed the moment-match (values drift again) or
broke its stats cache (scale drags re-pay full-res generation every tick).
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.compose import _scale_down_spec_pattern, _SPEC_SCALE_REF_STATS_CACHE


def _make_stats_sensitive_fn(call_log):
    """Amplitude and offset depend on resolution — self-normalizing generator
    stand-in. At canvas res (1024) mean≈0.45/std≈0.058; at tile res the raw
    output drifts hard, so any surviving drift means the correction is gone."""
    def fn(shape, seed=0, sm=1.0, **kwargs):
        call_log.append(tuple(shape[:2]))
        h, w = int(shape[0]), int(shape[1])
        amp = 200.0 / min(h, w)          # resolution-dependent amplitude
        yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
        xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
        field = 0.5 * np.sin(yy * 37.0) * np.cos(xx * 29.0) + 0.5
        return np.clip(0.25 + 0.1 * min(h, w) / 1024.0 + amp * (field - 0.5), 0.0, 1.0)
    return fn


def test_scale_down_values_match_canvas_res_reference():
    _SPEC_SCALE_REF_STATS_CACHE.clear()
    calls = []
    fn = _make_stats_sensitive_fn(calls)
    ref = np.asarray(fn((1024, 1024), 7, 1.0), dtype=np.float32)
    calls.clear()

    out = _scale_down_spec_pattern(fn, 0.25, (1024, 1024), 7, 1.0, {})
    d_mean = abs(float(out.mean()) - float(ref.mean())) * 255.0
    d_std = abs(float(out.std()) - float(ref.std())) * 255.0
    assert d_mean < 2.0, f"scale-down mean drifted {d_mean:.1f}/255 from canvas-res values"
    assert d_std < 4.0, f"scale-down std drifted {d_std:.1f}/255 from canvas-res values"


def test_reference_stats_generated_once_per_canvas_not_per_scale():
    _SPEC_SCALE_REF_STATS_CACHE.clear()
    calls = []
    fn = _make_stats_sensitive_fn(calls)
    for scale in (0.5, 0.4, 0.3, 0.25, 0.2):
        _scale_down_spec_pattern(fn, scale, (1024, 1024), 7, 1.0, {})
    full_res_calls = [c for c in calls if c == (1024, 1024)]
    tile_calls = [c for c in calls if c != (1024, 1024)]
    assert len(full_res_calls) == 1, (
        f"canvas-res reference regenerated {len(full_res_calls)}x across a 5-tick "
        f"scale drag — the stats cache is broken (drag perf regression)")
    assert len(tile_calls) == 5, f"expected 5 tile generations, got {calls}"


def test_three_channel_patterns_also_corrected():
    _SPEC_SCALE_REF_STATS_CACHE.clear()
    calls = []
    base = _make_stats_sensitive_fn(calls)

    def fn3(shape, seed=0, sm=1.0, **kwargs):
        f = np.asarray(base(shape, seed, sm), dtype=np.float32)
        return np.stack([f, np.clip(f * 0.5 + 0.2, 0, 1), np.clip(1.0 - f, 0, 1)], axis=2)

    ref = np.asarray(fn3((1024, 1024), 7, 1.0), dtype=np.float32)
    calls.clear()
    out = _scale_down_spec_pattern(fn3, 0.25, (1024, 1024), 7, 1.0, {})
    assert out.ndim == 3 and out.shape[2] == 3
    for c, name in enumerate(('M', 'R', 'CC')):
        d = abs(float(out[:, :, c].mean()) - float(ref[:, :, c].mean())) * 255.0
        assert d < 2.0, f"channel {name} mean drifted {d:.1f}/255"
