"""Per-render zone placement (base scale/offset/rotate) for image-authored monolithics."""

from __future__ import annotations

import threading
from typing import Any

_local = threading.local()


def set_zone_placement(
    *,
    scale: float = 1.0,
    offset_x: float = 0.5,
    offset_y: float = 0.5,
    rotation: float = 0.0,
    flip_h: bool = False,
    flip_v: bool = False,
) -> None:
    _local.data = {
        "scale": float(scale),
        "offset_x": float(offset_x),
        "offset_y": float(offset_y),
        "rotation": float(rotation),
        "flip_h": bool(flip_h),
        "flip_v": bool(flip_v),
        "applied": False,
    }


def get_zone_placement() -> dict[str, Any] | None:
    return getattr(_local, "data", None)


def mark_zone_placement_applied() -> None:
    data = getattr(_local, "data", None)
    if data is not None:
        data["applied"] = True


def zone_placement_was_applied() -> bool:
    data = getattr(_local, "data", None)
    return bool(data and data.get("applied"))


def clear_zone_placement() -> None:
    if hasattr(_local, "data"):
        del _local.data
