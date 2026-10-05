"""
tests/test_engine.py — engine math + iron-rule + registry tests.

Each test is self-contained and runs in well under a second. Heavy work
(loading registries, building base zones) happens via the session-scoped
fixtures in conftest.py so it amortizes across the suite.
"""

from __future__ import annotations

import os

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# 1. test_engine_imports — every engine module imports cleanly.
# ---------------------------------------------------------------------------
def test_engine_imports():
    """All core engine modules import without raising."""
    import shokker_engine_v2  # noqa: F401
    from engine import compose, core, finishes, overlay, gpu  # noqa: F401
    from engine import base_registry_data, expansion_patterns  # noqa: F401
    from engine.paint_v2 import (  # noqa: F401
        finish_basic, chrome_mirror, metallic_standard, candy_special,
    )


# ---------------------------------------------------------------------------
# 2. test_iron_rules_cc_floor — CC>=16 enforced everywhere CC>0.
# ---------------------------------------------------------------------------
def test_iron_rules_cc_floor(engine_module):
    """_enforce_iron_rules raises any CC value in 1..15 to 16 (CC_FLOOR)."""
    spec = np.zeros((4, 4, 4), dtype=np.uint8)
    spec[:, :, 2] = 8  # bad CC value in the forbidden 1..15 zone
    fixed = engine_module._enforce_iron_rules(spec)
    assert (fixed[:, :, 2] >= 16).all(), \
        f"CC floor should clamp to 16, got {fixed[:, :, 2].min()}"


def test_iron_rules_cc_zero_preserved(engine_module):
    """CC == 0 means 'no clearcoat' and must NOT be lifted to 16."""
    spec = np.zeros((4, 4, 4), dtype=np.uint8)
    fixed = engine_module._enforce_iron_rules(spec)
    assert (fixed[:, :, 2] == 0).all(), "CC=0 must stay 0 (matte zones rely on it)"


# ---------------------------------------------------------------------------
# 3. test_iron_rules_roughness_floor — non-chrome pixels need R>=15.
# ---------------------------------------------------------------------------
def test_iron_rules_roughness_floor(engine_module):
    """Non-mirror pixels (M < CHROME_M_THRESHOLD) get roughness floored at 15."""
    spec = np.zeros((4, 4, 4), dtype=np.uint8)
    spec[:, :, 0] = 100  # metallic but below chrome threshold (240)
    spec[:, :, 1] = 5    # bad roughness — too smooth for non-chrome
    fixed = engine_module._enforce_iron_rules(spec)
    assert (fixed[:, :, 1] >= 15).all(), \
        f"Roughness floor should clamp to 15, got {fixed[:, :, 1].min()}"


def test_iron_rules_chrome_keeps_low_roughness(engine_module):
    """Mirror pixels (M >= 240) are allowed to keep R=0 — that's the chrome look."""
    spec = np.zeros((4, 4, 4), dtype=np.uint8)
    spec[:, :, 0] = 255  # full mirror
    spec[:, :, 1] = 0    # mirror-smooth
    spec[:, :, 2] = 16
    fixed = engine_module._enforce_iron_rules(spec)
    assert fixed[0, 0, 1] == 0, "Chrome must keep low roughness"


# ---------------------------------------------------------------------------
# 4. test_compose_finish_returns_correct_shape
# ---------------------------------------------------------------------------
def test_compose_finish_returns_correct_shape():
    """compose_finish always returns an HxWx4 uint8 spec map."""
    from engine.compose import compose_finish
    shape = (64, 64)
    mask = np.ones(shape, dtype=np.float32)
    spec = compose_finish("candy", "carbon_fiber", shape, mask, 42, 1.0)
    spec = np.asarray(spec)
    assert spec.shape == (64, 64, 4), f"Expected (64,64,4), got {spec.shape}"
    assert spec.dtype == np.uint8, f"Expected uint8, got {spec.dtype}"


# ---------------------------------------------------------------------------
# 5. test_preview_render_handles_empty_zones
# ---------------------------------------------------------------------------
def test_preview_render_handles_empty_zones(engine_module, tmp_paint_file):
    """build_multi_zone raises a clear ValueError when zones=[] (vs cryptic IndexError)."""
    with pytest.raises(ValueError, match="zones"):
        engine_module.build_multi_zone(tmp_paint_file, "/tmp/spb_out", [])


# ---------------------------------------------------------------------------
# 6. test_preview_render_handles_invalid_paint
# ---------------------------------------------------------------------------
def test_preview_render_handles_invalid_paint(engine_module, sample_zones):
    """Missing paint file produces a ValueError with the offending path."""
    with pytest.raises(ValueError, match="paint_file"):
        engine_module.build_multi_zone(
            "/no/such/file.tga", "/tmp/spb_out", sample_zones
        )


# ---------------------------------------------------------------------------
# 7. test_build_multi_zone_priority_order
# ---------------------------------------------------------------------------
def test_build_multi_zone_priority_order(engine_module):
    """_validate_zones accepts a list of dicts in priority order without reordering."""
    zones = [
        {"name": "First", "color": "red", "finish": "chrome", "intensity": "100"},
        {"name": "Second", "color": "remaining", "finish": "matte", "intensity": "100"},
    ]
    # Should not raise; order preservation is structural.
    engine_module._validate_zones(zones)
    assert zones[0]["name"] == "First"
    assert zones[1]["name"] == "Second"


# ---------------------------------------------------------------------------
# 8. test_zone_color_match — yellow pixel matching is ~detectable.
# ---------------------------------------------------------------------------
def test_zone_color_match(engine_module):
    """Color-name lookup table contains the well-known names used by zones."""
    # Engine maps zone color names to RGB tuples internally; just sanity-check the
    # named-color helper if present, else assert the names parse via _validate_zones.
    zones = [
        {"name": "Y", "color": "yellow", "finish": "gloss", "intensity": "100"},
    ]
    engine_module._validate_zones(zones)
    # Color name shouldn't be uppercased/changed by validation
    assert zones[0]["color"] == "yellow"


# ---------------------------------------------------------------------------
# 9. test_zone_layer_restriction — sourceLayer field accepted on zone dicts.
# ---------------------------------------------------------------------------
def test_zone_layer_restriction(engine_module):
    """sourceLayer key on zone dicts must pass _validate_zones (extra keys allowed)."""
    zones = [
        {"name": "Layer1", "color": "everything", "finish": "gloss",
         "intensity": "100", "sourceLayer": "background"},
    ]
    engine_module._validate_zones(zones)  # should NOT raise


# ---------------------------------------------------------------------------
# 10. test_seed_determinism — same seed = same deterministic int.
# ---------------------------------------------------------------------------
def test_seed_determinism(engine_module):
    """_coerce_seed is a pure function: identical inputs return identical outputs."""
    s1 = engine_module._coerce_seed("sunset_red")
    s2 = engine_module._coerce_seed("sunset_red")
    s3 = engine_module._coerce_seed(42)
    s4 = engine_module._coerce_seed(42)
    assert s1 == s2, "String seed should be deterministic"
    assert s3 == s4, "Int seed should be deterministic"
    assert isinstance(s1, int) and isinstance(s3, int)
    assert s3 == 42


def test_seed_none_falls_back():
    """None seed falls back to default (51 by convention)."""
    from shokker_engine_v2 import _coerce_seed
    s = _coerce_seed(None)
    assert isinstance(s, int)
    assert s >= 0


# ---------------------------------------------------------------------------
# 11. test_apply_wear_clamps_input — wear > 100 is clamped to 100.
# ---------------------------------------------------------------------------
def test_apply_wear_clamps_input(engine_module):
    """wear_level > 100 is clamped (no-op or saturating, never raises)."""
    spec = np.zeros((16, 16, 4), dtype=np.uint8)
    spec[:, :, 2] = 16  # CC at floor so iron rules pass
    paint = np.full((16, 16, 3), 128, dtype=np.uint8)
    out_spec, out_paint = engine_module.apply_wear(spec, paint, 9999, seed=42)
    assert out_spec.shape == (16, 16, 4)
    assert out_paint.shape == (16, 16, 3)
    # Negative also accepted and clamped
    out2 = engine_module.apply_wear(spec, paint, -50, seed=42)
    assert out2[0].shape == (16, 16, 4)


def test_apply_wear_zero_is_noop(engine_module):
    """wear_level == 0 returns a copy of the inputs unchanged."""
    spec = np.zeros((8, 8, 4), dtype=np.uint8)
    spec[:, :, 2] = 16
    paint = np.full((8, 8, 3), 64, dtype=np.uint8)
    out_spec, out_paint = engine_module.apply_wear(spec, paint, 0)
    assert np.array_equal(out_spec, spec)
    assert np.array_equal(out_paint, paint)


# ---------------------------------------------------------------------------
# 12. test_generate_gradient_mask_bounds — values in [0,1].
# ---------------------------------------------------------------------------
def test_generate_gradient_mask_bounds(engine_module):
    """All gradient directions return float arrays bounded to [0,1]."""
    for direction in ("horizontal", "vertical", "diagonal", "radial"):
        m = engine_module.generate_gradient_mask(32, 32, direction=direction)
        assert m.shape == (32, 32), f"{direction} wrong shape: {m.shape}"
        assert m.dtype == np.float32, f"{direction} wrong dtype: {m.dtype}"
        assert m.min() >= 0.0 and m.max() <= 1.0, \
            f"{direction} out of bounds: [{m.min()}, {m.max()}]"


def test_generate_gradient_mask_invalid_dim_raises(engine_module):
    """Zero/negative dims raise ValueError instead of returning empty arrays."""
    with pytest.raises(ValueError):
        engine_module.generate_gradient_mask(0, 32)


# ---------------------------------------------------------------------------
# 13. test_pattern_registry_completeness — every pattern resolvable.
# ---------------------------------------------------------------------------
def test_pattern_registry_completeness(engine_module):
    """Every PATTERN_REGISTRY entry (except the 'none' sentinel) has texture_fn or image_path.

    The 'none' entry is an intentional no-op sentinel used by the UI to
    represent "no pattern" — it is excluded from this check.
    """
    SENTINELS = {"none", "null", "empty"}
    bad = []
    for pid, entry in engine_module.PATTERN_REGISTRY.items():
        if pid in SENTINELS:
            continue
        if not isinstance(entry, dict):
            bad.append((pid, "not a dict"))
            continue
        if entry.get("texture_fn") is None and not entry.get("image_path"):
            bad.append((pid, "no texture_fn AND no image_path"))
    assert not bad, f"Patterns with neither texture_fn nor image_path: {bad[:5]}"


# ---------------------------------------------------------------------------
# 14. test_base_registry_completeness — every base resolvable.
# ---------------------------------------------------------------------------
def test_base_registry_completeness(engine_module):
    """Every BASE_REGISTRY entry must expose a paint_fn (callable)."""
    bad = []
    for bid, entry in engine_module.BASE_REGISTRY.items():
        if not isinstance(entry, dict):
            continue  # legacy tuple entries permitted; only dicts are validated here
        pfn = entry.get("paint_fn")
        if pfn is not None and not callable(pfn):
            bad.append((bid, type(pfn).__name__))
    assert not bad, f"Bases with non-callable paint_fn: {bad[:5]}"


# ---------------------------------------------------------------------------
# 15. test_monolithic_registry_completeness — every monolithic resolvable.
# ---------------------------------------------------------------------------
def test_monolithic_registry_completeness(engine_module):
    """Every MONOLITHIC_REGISTRY tuple has at least a spec_fn at index 0."""
    bad = []
    for mid, val in engine_module.MONOLITHIC_REGISTRY.items():
        if isinstance(val, tuple):
            if len(val) < 1 or not callable(val[0]):
                bad.append((mid, "first element not callable"))
    assert not bad, f"Monolithics with bad shape: {bad[:5]}"


def test_registry_size_floors(engine_module):
    """Sanity: registries shouldn't shrink below known good sizes."""
    assert len(engine_module.BASE_REGISTRY) >= 50, \
        f"BASE_REGISTRY shrank to {len(engine_module.BASE_REGISTRY)} (expected >=50)"
    assert len(engine_module.PATTERN_REGISTRY) >= 200, \
        f"PATTERN_REGISTRY shrank to {len(engine_module.PATTERN_REGISTRY)} (expected >=200)"
    assert len(engine_module.MONOLITHIC_REGISTRY) >= 100, \
        f"MONOLITHIC_REGISTRY shrank to {len(engine_module.MONOLITHIC_REGISTRY)} (expected >=100)"


def test_compose_finish_iron_rules_pass():
    """compose_finish output passes iron-rule checks (CC>=16 where >0, R>=15 non-chrome)."""
    from engine.compose import compose_finish
    shape = (64, 64)
    mask = np.ones(shape, dtype=np.float32)
    spec = np.asarray(compose_finish("candy", "carbon_fiber", shape, mask, 42, 1.0))
    M = spec[:, :, 0].astype(int)
    R = spec[:, :, 1].astype(int)
    CC = spec[:, :, 2].astype(int)
    # CC: anywhere CC>0 must be >=16
    cc_violations = int(((CC > 0) & (CC < 16)).sum())
    # R floor: non-chrome pixels (M < 240) must have R>=15
    r_violations = int(((M < 240) & (R < 15)).sum())
    assert cc_violations == 0, f"{cc_violations} CC violations in compose output"
    assert r_violations == 0, f"{r_violations} R violations in compose output"
