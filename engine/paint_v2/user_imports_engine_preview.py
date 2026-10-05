"""Engine-accurate UV preview for USER IMPORTS (build_multi_zone @ reduced size)."""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any

import numpy as np
from PIL import Image

from engine.paint_v2.user_imports import reload_user_imports, sync_registry
from engine.paint_v2.user_imports_paths import ID_PREFIX

DEFAULT_SIZE = 512


def render_engine_uv_bytes(
    finish_id: str,
    *,
    size: int = DEFAULT_SIZE,
    seed: int = 42,
    engine: Any = None,
) -> bytes:
    """Render ui_* monolithic through build_multi_zone; return PNG bytes."""
    if not finish_id.startswith(ID_PREFIX):
        raise ValueError("Engine preview only supports user import ids")
    reload_user_imports()
    import shokker_engine_v2 as eng

    if engine is not None:
        eng.MONOLITHIC_REGISTRY = engine.MONOLITHIC_REGISTRY
        eng.PATTERN_REGISTRY = engine.PATTERN_REGISTRY
        eng.BASE_REGISTRY = engine.BASE_REGISTRY
    sync_registry(eng.MONOLITHIC_REGISTRY, eng.PATTERN_REGISTRY)
    eng._spb_apply_regular_pattern_rebuilds()

    if finish_id not in eng.MONOLITHIC_REGISTRY:
        raise FileNotFoundError(finish_id)

    side = max(256, min(1024, int(size)))
    gray = np.full((side, side, 3), 140, dtype=np.uint8)
    zone = {
        "name": "UI-Engine-Preview",
        "color": "remaining",
        "finish": finish_id,
        "intensity": "100",
    }
    with tempfile.TemporaryDirectory(prefix="spb_ui_eng_prev_") as tmp:
        src = os.path.join(tmp, "paint_src.png")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)
        Image.fromarray(gray).save(src)
        paint_out, _spec, _extras = eng.build_multi_zone(
            src,
            out_dir,
            [zone],
            seed=seed,
            preview_mode=False,
            save_debug_images=False,
        )
    rgb = np.clip(paint_out, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="PNG", optimize=True)
    return buf.getvalue()
