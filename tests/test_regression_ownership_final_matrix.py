"""Cheap final-output invariants for source-layer ownership.

These tests deliberately cross ``build_multi_zone`` and inspect the final spec
array plus the effective masks that reached compose.  Helper-only coverage did
not catch the 2026-08-22 final-priority subtraction bug.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CLIENT_MATRIX = ROOT / "tests" / "_runtime_harness" / "ownership_alpha_matrix.mjs"
DEFAULT_SPEC = (5, 100, 16, 255)
OWNER_SPEC = (40, 60, 32, 255)
REMAINDER_SPEC = (80, 120, 64, 255)
GLOBAL_SPEC = (120, 160, 96, 255)
LOWER_30_SPEC = (150, 180, 112, 255)
TOP_30_SPEC = (180, 200, 128, 255)


def _client_alpha_matrix() -> dict:
    result = subprocess.run(
        ["node", str(CLIENT_MATRIX)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _source_png(tmp_path: Path, name: str, shape: tuple[int, int]) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w = shape
    rgba = np.empty((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = (32, 96, 160)
    rgba[:, :, 3] = 255
    Image.fromarray(rgba, "RGBA").save(path)
    return path


def _constant_spec_renderer(spec_tuple: tuple[int, int, int, int]):
    def render(shape, mask, seed, strength):
        h, w = shape[:2]
        result = np.empty((h, w, 4), dtype=np.uint8)
        result[:, :] = spec_tuple
        return result

    return render


def _paint_passthrough(paint, shape, mask, seed, paint_mult, brightness):
    return np.asarray(paint, dtype=np.float32).copy()


def _install_constant_finishes(engine_module, monkeypatch) -> None:
    for finish_id, spec_tuple in {
        "__ownership_owner": OWNER_SPEC,
        "__ownership_remainder": REMAINDER_SPEC,
        "__ownership_global": GLOBAL_SPEC,
        "__ownership_lower30": LOWER_30_SPEC,
        "__ownership_top30": TOP_30_SPEC,
    }.items():
        monkeypatch.setitem(
            engine_module.FINISH_REGISTRY,
            finish_id,
            (_constant_spec_renderer(spec_tuple), _paint_passthrough),
        )


def _render(engine_module, source: Path, zones: list[dict], *, export_layers: bool = True):
    return engine_module.build_multi_zone(
        str(source),
        str(source.parent),
        zones,
        preview_mode=True,
        export_layers=export_layers,
    )


def _tuples(image: np.ndarray) -> set[tuple[int, int, int, int]]:
    return {tuple(int(value) for value in pixel) for pixel in image.reshape(-1, 4)}


def _clear_zone_cache(engine_module) -> None:
    cache = getattr(engine_module.build_multi_zone, "_zone_cache", None)
    if cache is not None:
        cache.clear()


def _mutant_soft_compose(
    owner: tuple[int, int, int, int],
    remainder: tuple[int, int, int, int],
    fractional_mask: np.ndarray,
) -> np.ndarray:
    """Negative control: the retired fractional-owner interpolation."""
    mask3 = fractional_mask[:, :, np.newaxis].astype(np.float32)
    a = np.asarray(owner, dtype=np.float32)
    b = np.asarray(remainder, dtype=np.float32)
    return np.rint(a * mask3 + b * (1.0 - mask3)).astype(np.uint8)


def test_final_compose_is_binary_one_hot_at_127_128_and_60_20_mesh(
    tmp_path, engine_module, monkeypatch
):
    """Boundary and grill inputs may split, but can never create soft owners."""
    _install_constant_finishes(engine_module, monkeypatch)
    monkeypatch.setattr(engine_module, "is_gpu", lambda: False)
    _clear_zone_cache(engine_module)

    client = _client_alpha_matrix()
    assert client["alphaBoundary"]["boundary"] == [0, 255]
    assert client["grillMesh"]["mesh"] == [255, 0]

    h, w = 8, 8
    source = _source_png(tmp_path, "ownership_boundary_mesh.png", (h, w))
    raw = np.tile(np.array([127, 128, 153, 51], dtype=np.uint8), (h, 2))
    expected_owner = (raw >= 128).astype(np.float32)
    zones = [
        {
            "name": "Restricted owner",
            "color": "everything",
            "finish": "__ownership_owner",
            "source_layer_mask": raw,
            "hard_edge": False,
        },
        {
            "name": "Everything Else",
            "color": "remaining",
            "finish": "__ownership_remainder",
            "hard_edge": True,
        },
    ]

    _paint, final_spec, layers = _render(engine_module, source, zones)
    by_index = {layer["zone_index"]: layer for layer in layers}
    owner_mask = by_index[0]["mask"]
    remainder_mask = by_index[1]["mask"]

    assert set(np.unique(owner_mask)) <= {0.0, 1.0}
    assert set(np.unique(remainder_mask)) <= {0.0, 1.0}
    assert np.array_equal(owner_mask, expected_owner)
    assert np.array_equal(remainder_mask, 1.0 - expected_owner)
    assert np.array_equal(owner_mask + remainder_mask, np.ones((h, w), dtype=np.float32))
    assert _tuples(final_spec) == {OWNER_SPEC, REMAINDER_SPEC}
    assert DEFAULT_SPEC not in _tuples(final_spec)
    assert np.all(final_spec[expected_owner == 1] == np.asarray(OWNER_SPEC, dtype=np.uint8))
    assert np.all(final_spec[expected_owner == 0] == np.asarray(REMAINDER_SPEC, dtype=np.uint8))

    # Relevance proof: a local mutant that lets 127/128/60/20 fractions reach
    # compose immediately manufactures forbidden interpolated material tuples.
    mutant = _mutant_soft_compose(OWNER_SPEC, REMAINDER_SPEC, raw.astype(np.float32) / 255.0)
    assert not _tuples(mutant).issubset({OWNER_SPEC, REMAINDER_SPEC})


def test_stacked_thirty_percent_layers_reach_one_hot_remainder_without_orphans(
    tmp_path, engine_module, monkeypatch
):
    """Pin current plumbing without claiming that the product policy is ideal.

    Two ~30% layers source-over to >50% above the base, while neither layer's
    own footprint reaches 50%.  The current crisp-50 policy therefore assigns
    none of the three restricted zones and leaves the pixel to Everything Else.
    Whether one semantic translucent object should instead own it is an owner
    decision; the invariant here is exact one-hot final output with no orphan.
    """
    _install_constant_finishes(engine_module, monkeypatch)
    monkeypatch.setattr(engine_module, "is_gpu", lambda: False)
    _clear_zone_cache(engine_module)

    client = _client_alpha_matrix()["stackedThirty"]
    assert client == {"base": [0], "lower30": [0], "top30": [0]}

    h, w = 8, 8
    source = _source_png(tmp_path, "ownership_stacked_thirty.png", (h, w))
    zero_masks = {
        key: np.full((h, w), values[0], dtype=np.float32) / 255.0
        for key, values in client.items()
    }
    zones = [
        {"name": "Base", "color": "everything", "finish": "__ownership_owner", "source_layer_mask": zero_masks["base"], "hard_edge": False},
        {"name": "Lower 30", "color": "everything", "finish": "__ownership_lower30", "source_layer_mask": zero_masks["lower30"], "hard_edge": False},
        {"name": "Top 30", "color": "everything", "finish": "__ownership_top30", "source_layer_mask": zero_masks["top30"], "hard_edge": False},
        {"name": "Everything Else", "color": "remaining", "finish": "__ownership_remainder", "hard_edge": True},
    ]

    _paint, final_spec, layers = _render(engine_module, source, zones)
    assert [layer["zone_index"] for layer in layers] == [3]
    assert np.array_equal(layers[0]["mask"], np.ones((h, w), dtype=np.float32))
    assert _tuples(final_spec) == {REMAINDER_SPEC}
    assert DEFAULT_SPEC not in _tuples(final_spec)


def test_final_compose_preserves_restricted_remainder_after_global_claim(
    tmp_path, engine_module, monkeypatch
):
    """The source-local exception must survive into the final spec, not only its helper."""
    _install_constant_finishes(engine_module, monkeypatch)
    monkeypatch.setattr(engine_module, "is_gpu", lambda: False)
    _clear_zone_cache(engine_module)

    h, w = 8, 8
    source = _source_png(tmp_path, "ownership_global_then_local.png", (h, w))
    restricted_scope = np.zeros((h, w), dtype=np.float32)
    restricted_scope[:, 2:6] = 1.0
    zones = [
        {"name": "Global", "color": "remaining", "finish": "__ownership_global", "hard_edge": True},
        {
            "name": "Layer-local remainder",
            "color": "remaining",
            "finish": "__ownership_owner",
            "source_layer_mask": restricted_scope,
            "hard_edge": False,
        },
    ]

    _paint, final_spec, layers = _render(engine_module, source, zones)
    by_index = {layer["zone_index"]: layer for layer in layers}
    assert np.array_equal(by_index[1]["mask"], restricted_scope)
    assert _tuples(final_spec) == {GLOBAL_SPEC, OWNER_SPEC}
    assert np.all(final_spec[restricted_scope == 1] == np.asarray(OWNER_SPEC, dtype=np.uint8))
    assert np.all(final_spec[restricted_scope == 0] == np.asarray(GLOBAL_SPEC, dtype=np.uint8))
    assert DEFAULT_SPEC not in _tuples(final_spec)

    # Historical-final-loop mutant: subtracting the earlier global claim a
    # second time erases every local pixel, which this final-spec assertion sees.
    mutant_effective = restricted_scope * (1.0 - np.ones_like(restricted_scope))
    assert not np.array_equal(mutant_effective, by_index[1]["mask"])


def test_cpu_cache_hit_replays_identical_final_spec(
    tmp_path, engine_module, monkeypatch
):
    """Cache miss and verified CPU cache hit must have byte-identical outputs."""
    _install_constant_finishes(engine_module, monkeypatch)
    monkeypatch.setattr(engine_module, "is_gpu", lambda: False)
    _clear_zone_cache(engine_module)

    h, w = 8, 8
    source = _source_png(tmp_path, "ownership_cache_parity.png", (h, w))
    checker = (np.indices((h, w)).sum(axis=0) % 2).astype(np.float32)
    zones = [
        {"name": "Owner", "color": "everything", "finish": "__ownership_owner", "source_layer_mask": checker, "hard_edge": False},
        {"name": "Everything Else", "color": "remaining", "finish": "__ownership_remainder", "hard_edge": True},
    ]

    miss_paint, miss_spec = _render(engine_module, source, zones, export_layers=False)
    cache_keys_after_miss = set(engine_module.build_multi_zone._zone_cache)
    assert len(cache_keys_after_miss) == 2

    cached_blends = []
    original_blend = engine_module._blend_cached_spec_region

    def recording_cached_blend(*args, **kwargs):
        cached_blends.append(True)
        return original_blend(*args, **kwargs)

    monkeypatch.setattr(engine_module, "_blend_cached_spec_region", recording_cached_blend)
    hit_paint, hit_spec = _render(engine_module, source, zones, export_layers=False)

    assert cached_blends, "The second render did not exercise the CPU cache-hit compose path"
    assert set(engine_module.build_multi_zone._zone_cache) == cache_keys_after_miss
    assert np.array_equal(hit_paint, miss_paint)
    assert np.array_equal(hit_spec, miss_spec)
    assert _tuples(hit_spec) == {OWNER_SPEC, REMAINDER_SPEC}
