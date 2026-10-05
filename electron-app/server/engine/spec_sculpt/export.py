"""TGA export with SPB iron rules (iRacing channel safety)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def save_spec_tga_iron_safe(
    spec_rgba_u8: np.ndarray,
    path: str | Path,
    *,
    already_safe: bool = False,
) -> str:
    """Write a 32-bit RGBA TGA and return its absolute path.

    ``already_safe`` is reserved for callers that just ran the shared iron-rule
    fixer. It avoids a second 2048-square float copy while preserving the exact
    bytes written; every other caller keeps the defensive enforcement default.
    """

    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    if already_safe:
        safe = np.asarray(spec_rgba_u8, dtype=np.uint8)
    else:
        from shokker_engine_v2 import _enforce_iron_rules

        safe = _enforce_iron_rules(np.asarray(spec_rgba_u8))
    if safe.shape[2] == 4:
        img = Image.fromarray(safe, mode="RGBA")
    else:
        img = Image.fromarray(safe[:, :, :4], mode="RGBA")
    img.save(str(p), format="TGA")
    return str(p.resolve())
