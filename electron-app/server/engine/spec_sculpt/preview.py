"""Flat PNG previews (composite RGB spec + per-channel grayscale)."""

from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image


def spec_preview_png_data_urls(spec_rgba_u8: np.ndarray) -> dict:
    """Return data:image/png;base64,... entries for UI (no 3D ball — flat maps only)."""
    s = np.asarray(spec_rgba_u8, dtype=np.uint8)
    if s.ndim != 3 or s.shape[2] < 3:
        raise ValueError("spec must be HxWx4 (or HxWx3+)")

    def _png_b64(rgb_or_rgba: np.ndarray) -> str:
        arr = np.clip(rgb_or_rgba, 0, 255).astype(np.uint8)
        if arr.ndim == 2:
            img = Image.fromarray(arr, mode="L").convert("RGB")
        elif arr.shape[2] == 3:
            img = Image.fromarray(arr, mode="RGB")
        else:
            img = Image.fromarray(arr[:, :, :4], mode="RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    mch = s[:, :, 0]
    rgh = s[:, :, 1]
    cch = s[:, :, 2]
    composite = np.stack([mch, rgh, cch], axis=2)

    def _tint_gray(ch: np.ndarray, rgb: tuple[float, float, float]) -> np.ndarray:
        """Tint single-channel spec data as RGB (matches Paint Booth-style channel previews)."""
        g = np.clip(ch.astype(np.float32), 0.0, 255.0) / 255.0
        rr, gg, bb = rgb
        r_out = np.clip(g * float(rr) * 255.0, 0.0, 255.0).astype(np.uint8)
        g_out = np.clip(g * float(gg) * 255.0, 0.0, 255.0).astype(np.uint8)
        b_out = np.clip(g * float(bb) * 255.0, 0.0, 255.0).astype(np.uint8)
        return np.stack([r_out, g_out, b_out], axis=2)

    return {
        "composite": _png_b64(composite),
        "channelR": _png_b64(_tint_gray(mch, (1.0, 0.22, 0.22))),
        "channelG": _png_b64(_tint_gray(rgh, (0.22, 1.0, 0.28))),
        "channelB": _png_b64(_tint_gray(cch, (0.28, 0.42, 1.0))),
    }
