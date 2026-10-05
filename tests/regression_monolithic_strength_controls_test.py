import contextlib
import io

import numpy as np
from PIL import Image


def test_monolithic_base_and_color_strength_are_literal_source_fades(tmp_path, monkeypatch):
    import shokker_engine_v2 as eng

    paint_path = tmp_path / "mono_strength_source.png"
    source = np.full((32, 32, 4), 255, dtype=np.uint8)
    Image.fromarray(source).save(paint_path)

    def _flat_spec(shape, mask, seed, sm):
        h, w = shape
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        spec[:, :, 1] = 50
        spec[:, :, 2] = 80
        spec[:, :, 3] = 255
        return spec

    def _full_replacement_gold(paint, shape, mask, seed, pm, bb):
        out = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
        out[:, :, 0] = 1.0
        out[:, :, 1] = 0.72
        return out

    def _underpaint_sensitive_material(paint, shape, mask, seed, pm, bb):
        material_tone = np.array([0.2, 0.4, 0.6], dtype=np.float32)
        return np.asarray(paint, dtype=np.float32)[:, :, :3] * 0.5 + material_tone * 0.5

    monkeypatch.setitem(
        eng.MONOLITHIC_REGISTRY,
        "synthetic_full_replacement_gold",
        (_flat_spec, _full_replacement_gold),
    )
    monkeypatch.setitem(
        eng.MONOLITHIC_REGISTRY,
        "synthetic_underpaint_sensitive",
        (_flat_spec, _underpaint_sensitive_material),
    )

    def _render(strength, color_strength=1.0, finish="synthetic_full_replacement_gold"):
        zone = {
            "name": f"strength {strength}",
            "color": "everything",
            "region_mask": np.ones((32, 32), dtype=np.float32),
            "finish": finish,
            "intensity": "100",
            "base_color_mode": "solid",
            "base_color": [0.0, 0.0, 0.0],
            "base_color_strength": color_strength,
            "base_strength": strength,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            paint, _spec = eng.build_multi_zone(
                str(paint_path),
                str(tmp_path / f"out_{finish}_{strength}_{color_strength}"),
                [zone],
                seed=517,
                preview_mode=True,
            )
        return paint.astype(np.float32)

    hidden = _render(0.0)
    quarter = _render(0.25)
    full = _render(1.0)

    # Base Strength envelopes the complete base + chosen-color result.
    # 0 is exact source white, 1 is the chosen black, and 0.25 is a literal mix.
    assert np.allclose(hidden, 255.0, atol=1.0)
    assert np.allclose(quarter, 255.0 * 0.75, atol=2.0)
    assert np.allclose(full, 0.0, atol=1.0)

    no_color = _render(1.0, 0.0)
    half_color = _render(1.0, 0.5)
    full_color = _render(1.0, 1.0)

    expected_gold = np.array([255.0, 0.72 * 255.0, 0.0], dtype=np.float32)
    assert np.allclose(no_color[0, 0], expected_gold, atol=2.0)
    assert np.allclose(half_color[0, 0], expected_gold * 0.5, atol=2.0)
    assert np.allclose(full_color, 0.0, atol=1.0)

    # A renderer that samples underpaint must still receive the chosen color
    # exactly once; otherwise 50% gets applied before and after the material.
    sensitive_base = _render(1.0, 0.0, "synthetic_underpaint_sensitive")
    sensitive_half = _render(1.0, 0.5, "synthetic_underpaint_sensitive")
    sensitive_full = _render(1.0, 1.0, "synthetic_underpaint_sensitive")
    assert np.allclose(sensitive_half, sensitive_base * 0.5, atol=2.0)
    assert np.allclose(sensitive_full, 0.0, atol=1.0)
