import contextlib
import io

import numpy as np
from PIL import Image


def test_monolithic_finish_base_strength_lerps_against_solid_underpaint(tmp_path, monkeypatch):
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

    monkeypatch.setitem(
        eng.MONOLITHIC_REGISTRY,
        "synthetic_full_replacement_gold",
        (_flat_spec, _full_replacement_gold),
    )

    def _render(strength):
        zone = {
            "name": f"strength {strength}",
            "color": "everything",
            "region_mask": np.ones((32, 32), dtype=np.float32),
            "finish": "synthetic_full_replacement_gold",
            "intensity": "100",
            "base_color_mode": "solid",
            "base_color": [0.0, 0.0, 0.0],
            "base_color_strength": 1.0,
            "base_strength": strength,
        }
        with contextlib.redirect_stdout(io.StringIO()):
            paint, _spec = eng.build_multi_zone(
                str(paint_path),
                str(tmp_path / f"out_{strength}"),
                [zone],
                seed=517,
                preview_mode=True,
            )
        return paint.astype(np.float32)

    hidden = _render(0.0)
    quarter = _render(0.25)
    full = _render(1.0)

    assert float(hidden.mean()) < 2.0
    assert float(full.mean()) > 120.0
    assert float(quarter.mean()) > float(hidden.mean()) + 20.0
    assert float(quarter.mean()) < float(full.mean()) * 0.40
