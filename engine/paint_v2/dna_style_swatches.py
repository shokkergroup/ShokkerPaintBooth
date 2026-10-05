"""Cached spec-preview thumbnails per DNA style (SPB-109 SHOKK DROP picker)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from engine.paint_v2.import_dna_style_catalog import DNA_STYLES, is_exotic_style
from engine.paint_v2.user_imports_paths import CANVAS_SIZE, user_imports_root
from engine.paint_v2.user_imports_spec_dna import bake_import_spec_dna, spec_to_rgb_preview

SWATCH_VERSION = 2
SWATCH_OUT_SIZE = 128


def dna_style_swatch_cache_dir() -> Path:
    root = user_imports_root().parent / "dna_style_swatches"
    root.mkdir(parents=True, exist_ok=True)
    return root


def dna_style_thumb_url(style_id: str) -> str:
    return f"/api/user-imports/dna-style-thumb/{style_id}.png?v={SWATCH_VERSION}"


@lru_cache(maxsize=1)
def _reference_paint_swatch() -> Image.Image:
    """UV-like color layout so styles are comparable (not flat gray)."""
    size = CANVAS_SIZE
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / float(size)
    r = 0.42 + 0.34 * np.sin(x * 11.5) * np.cos(y * 7.5)
    g = 0.38 + 0.36 * np.sin((x + y) * 9.5)
    b = 0.52 + 0.32 * np.cos(x * 14.0 - y * 6.5)
    rgb = (np.clip(np.stack([r, g, b], axis=-1), 0.0, 1.0) * 255.0).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def swatch_path_for(style_id: str) -> Path:
    safe = style_id.replace("/", "_")
    return dna_style_swatch_cache_dir() / f"{safe}_v{SWATCH_VERSION}.png"


# Build-time-baked swatches ship under <server_root>/thumbnails/dna_style_swatches and are
# preferred over the live %APPDATA% bake so a FRESH install loads the DNA picker INSTANTLY
# instead of baking ~75 full 2048x2048 spec plates one-by-one on first open (SPB 2026-06-08).
# <server_root> == parents[2] of this file: engine/paint_v2/<this> -> engine -> server root.
_BUNDLED_SWATCH_DIR = Path(__file__).resolve().parents[2] / "thumbnails" / "dna_style_swatches"


def bundled_swatch_path_for(style_id: str) -> Path:
    safe = style_id.replace("/", "_")
    return _BUNDLED_SWATCH_DIR / f"{safe}_v{SWATCH_VERSION}.png"


def ensure_dna_style_swatch(style_id: str) -> Path:
    if style_id not in DNA_STYLES:
        raise ValueError(f"Unknown DNA style: {style_id}")

    # Prefer the build-time-baked swatch shipped with the app — instant, no engine bake.
    bundled = bundled_swatch_path_for(style_id)
    if bundled.is_file() and bundled.stat().st_size > 200:
        return bundled

    path = swatch_path_for(style_id)
    if path.is_file() and path.stat().st_size > 200:
        return path

    tmp = path.with_suffix(".tmp.png")
    paint = _reference_paint_swatch()
    result = bake_import_spec_dna(
        paint,
        f"dna_swatch_{style_id}",
        style_override=style_id,
        max_gauntlet_passes=1,
        micro_seed=(hash(style_id) & 0xFFFF) ^ 0x5A7C,
        exotic=is_exotic_style(style_id),
        bake_index=(hash(style_id) & 0x7FFF),
        alive=False,
    )
    preview = spec_to_rgb_preview(result.spec).resize(
        (SWATCH_OUT_SIZE, SWATCH_OUT_SIZE), Image.Resampling.LANCZOS
    )
    tmp.parent.mkdir(parents=True, exist_ok=True)
    preview.save(tmp, "PNG", optimize=True)
    os.replace(tmp, path)
    return path
