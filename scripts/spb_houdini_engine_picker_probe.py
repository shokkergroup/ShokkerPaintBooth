"""Stage-only exact-engine picker probe for FRACTURED HOUDINI H1.

This deliberately bypasses ``server.py`` and its manifest writer.  It tests the
same source canvas and preview scale that the official picker route uses, so a
successful run proves the renderer is not the reason the old writer stalled.
It never changes catalog/static/manifest state.
"""
from __future__ import annotations

import tempfile
import time
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import shokker_engine_v2 as engine  # noqa: E402

FINISH = "houdini_veiled_skull"
SOURCE = 2048


def main() -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        source_path = Path(tmp.name)
    try:
        Image.new("RGB", (SOURCE, SOURCE), (136, 136, 136)).save(source_path)
        zone = {
            "name": "H1PickerEngineProbe", "color": [.533, .533, .533],
            "intensity": 100, "base_strength": 1.0,
            "base_spec_strength": 1.0, "base_color_mode": "authored_swatch",
            "base_color": [1.0, 1.0, 1.0], "region_mask": np.ones((SOURCE, SOURCE), np.float32),
            "apply_area_shape_only": True, "finish": FINISH,
        }
        began = time.perf_counter()
        paint, spec, elapsed = engine.preview_render(str(source_path), [zone], seed=42, preview_scale=.5)
        wall = time.perf_counter() - began
    finally:
        source_path.unlink(missing_ok=True)
    if paint is None or spec is None:
        raise RuntimeError("engine probe returned no paint/spec")
    paint = np.asarray(paint)[..., :3].astype(np.uint8)
    spec = np.asarray(spec)[..., :3].astype(np.uint8)
    if paint.shape[:2] != (1024, 1024) or spec.shape[:2] != (1024, 1024):
        raise RuntimeError(f"unexpected preview shape {paint.shape} / {spec.shape}")
    left = cv2.resize(paint, (48, 48), interpolation=cv2.INTER_AREA)
    right = cv2.resize(spec, (48, 48), interpolation=cv2.INTER_AREA)
    split = np.concatenate((left, right), axis=1); split[:, 47:49] = 20
    out = ROOT / "_houdini_h1_engine_picker_probe.png"
    if not cv2.imwrite(str(out), cv2.cvtColor(split, cv2.COLOR_RGB2BGR)):
        raise RuntimeError(out)
    standard = cv2.resize(paint, (256, 256), interpolation=cv2.INTER_AREA)
    standard_out = ROOT / "_houdini_h1_engine_standard_probe.png"
    if not cv2.imwrite(str(standard_out), cv2.cvtColor(standard, cv2.COLOR_RGB2BGR)):
        raise RuntimeError(standard_out)
    print(f"engine_elapsed_s={elapsed:.3f} wall_s={wall:.3f} shape={paint.shape[1]}x{paint.shape[0]}")
    print(f"paint_std={paint.std()/255:.4f} mrc_std={spec[...,0].std():.2f}/{spec[...,1].std():.2f}/{spec[...,2].std():.2f}")
    print(f"probe={out}")
    print(f"standard_probe={standard_out}")


if __name__ == "__main__":
    main()
