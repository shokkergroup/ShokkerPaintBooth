"""Load source paint images into HxWx3 float32 RGB 0..1."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from PIL import Image


def load_paint_rgb_float01(
    path: str | Path,
    *,
    target_size: int | None = 2048,
) -> tuple[np.ndarray, tuple[int, int], tuple[int, int]]:
    """Load TGA/PNG/JPEG; optionally resize to ``target_size`` square.

    Returns:
        tex_rgb: HxWx3 float32 in 0..1
        original_hw: (h, w) before resize
        final_hw: (h, w) after resize
    """
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(str(p))
    img = Image.open(str(p))
    if img.mode == "RGBA":
        rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    elif img.mode == "RGB":
        rgb = np.asarray(img, dtype=np.uint8)
    else:
        rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    oh, ow = int(rgb.shape[0]), int(rgb.shape[1])
    if target_size is None or (oh == target_size and ow == target_size):
        tex = (rgb.astype(np.float32) / 255.0).astype(np.float32)
        return tex, (oh, ow), (oh, ow)
    resized = cv2.resize(rgb, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
    tex = (resized.astype(np.float32) / 255.0).astype(np.float32)
    return tex, (oh, ow), (target_size, target_size)
