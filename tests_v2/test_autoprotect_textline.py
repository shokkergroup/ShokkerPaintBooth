"""Auto-protect over-protect + text-line recall gate (2026-06-26).

Locks the #1 rule (never over-protect a busy/patterned BASE) AND the text-line recall win (recover car
numbers/wordmarks on busy all-over liveries) so neither can silently regress:
  1. OVER-PROTECT SAFETY — solid / carbon-noise / coarse-weave / polka / camo / template-grid bases must
     return None or a small fraction (<0.14). The text-line fallback must reject ALL of these.
  2. RECALL — a synthetic numbered car (numbers + wordmark on a busy base) must be detected.
"""
from __future__ import annotations
import numpy as np
import cv2
import pytest
from PIL import Image, ImageDraw

from engine.spec_sculpt.generate import auto_protect_mask_from_paint as ap, _normalize_rgb_u8, _glyph_textline_mask

RNG = np.random.default_rng(7)


def _frac(m):
    return None if m is None else float((m == 0).mean())


def _carbon():
    return np.clip(RNG.normal(0.3, 0.07, (512, 512, 1)).repeat(3, 2), 0, 1).astype(np.float32)


def _weave():
    a = (np.sin(np.linspace(0, 160, 512))[None, :] * np.sin(np.linspace(0, 160, 512))[:, None])
    a = (a - a.min()) / (a.max() - a.min()) * 0.4 + 0.1
    return np.dstack([a] * 3).astype(np.float32)


def _polka():
    a = np.full((512, 512, 3), 0.2, np.float32)
    for y in range(0, 512, 40):
        for x in range(0, 512, 40):
            cv2.circle(a, (x + 20, y + 20), 12, (0.9, 0.9, 0.9), -1)
    return a


def _camo():
    a = np.full((512, 512, 3), 0.0, np.float32)
    a[:, :] = [0.25, 0.30, 0.15]
    for _ in range(60):
        cx, cy = RNG.integers(0, 512, 2)
        cv2.circle(a, (int(cx), int(cy)), int(RNG.integers(20, 60)),
                   [float(RNG.uniform(0.1, 0.4)) for _ in range(3)], -1)
    return np.clip(a, 0, 1).astype(np.float32)


def _grid():
    a = np.full((512, 512, 3), 0.15, np.float32)
    a[::16, :] = [0, 0.8, 0.9]
    a[:, ::16] = [0, 0.8, 0.9]
    return a


def _numbered():
    im = Image.new("RGB", (512, 512), (30, 30, 40))
    d = ImageDraw.Draw(im)
    d.text((210, 210), "55", fill=(245, 245, 245))
    d.text((60, 400), "SHOKKER", fill=(235, 235, 235))
    return np.asarray(im, np.uint8).astype(np.float32) / 255.0


BASES = {"solid": np.full((512, 512, 3), 0.5, np.float32), "carbon": _carbon(), "weave": _weave(),
         "polka": _polka(), "camo": _camo(), "grid": _grid()}


@pytest.mark.parametrize("name", list(BASES))
def test_does_not_overprotect_base(name):
    """A busy/patterned BASE finish must never be heavily protected (the #1 rule)."""
    fr = _frac(ap(BASES[name]))
    assert fr is None or fr < 0.14, f"{name}: over-protected base ({fr:.3f})"


@pytest.mark.parametrize("name", ["carbon", "weave", "polka", "camo", "grid"])
def test_textline_fallback_rejects_textures(name):
    """The text-line recall fallback in ISOLATION must reject every textured base (no text rows)."""
    tex = BASES[name]
    rgb = _normalize_rgb_u8(tex)
    Hw, Ww = rgb.shape[:2]
    f = rgb.astype(np.float32) / 255.0
    m = _glyph_textline_mask(f, Hw, Ww, Hw * Ww, 0.55, Hw, Ww)
    assert m is None, f"{name}: text-line fallback fired on a texture (frac={_frac(m):.3f})"


def test_numbered_car_is_detected():
    fr = _frac(ap(_numbered()))
    assert fr is not None and fr > 0.001, "synthetic numbered car not detected"
