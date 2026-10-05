"""Apply zone base placement to image-authored cultural plates at sample time."""

from __future__ import annotations

import cv2
import numpy as np

from engine.paint_v2.placement_context import get_zone_placement, mark_zone_placement_applied


def _placement_active(pl: dict) -> bool:
    scale = float(pl.get("scale", 1.0))
    if abs(scale - 1.0) > 0.01:
        return True
    if abs(float(pl.get("offset_x", 0.5)) - 0.5) > 0.001:
        return True
    if abs(float(pl.get("offset_y", 0.5)) - 0.5) > 0.001:
        return True
    if abs(float(pl.get("rotation", 0.0)) % 360.0) > 0.5:
        return True
    if pl.get("flip_h") or pl.get("flip_v"):
        return True
    return False


def _transform_cultural_plate_global(
    plate: np.ndarray,
    shape,
    *,
    scale: float,
    offset_x: float,
    offset_y: float,
    rotation: float,
    flip_h: bool,
    flip_v: bool,
) -> np.ndarray:
    """Canonical canvas-space scale for cultural plates.

    SPB-2026-05-19: every previous custom path either (a) tiled the whole UV unwrap
    (hall of mirrors), (b) scaled per UV island (uneven density), or (c) clamped
    sample coords (edge streaks). Delegate to the engine's canonical placement
    transform so paint and spec behave like every other zone control.
    """
    from engine.compose import _transform_base_color_source

    h, w = int(shape[0]), int(shape[1])
    src = np.asarray(plate, dtype=np.float32)
    if src.ndim == 2:
        src = np.repeat(src[:, :, np.newaxis], 3, axis=2)
    hi = 1.0 if float(np.nanmax(src)) <= 1.0 + 1e-3 else 255.0
    work = src[:, :, :3] if hi == 1.0 else (src[:, :, :3] / 255.0)
    out = _transform_base_color_source(
        work,
        (h, w),
        scale=scale,
        offset_x=offset_x,
        offset_y=offset_y,
        rotation=rotation,
        flip_h=flip_h,
        flip_v=flip_v,
    )
    if hi != 1.0:
        out = out * 255.0
    return np.clip(out, 0.0, hi).astype(np.float32)


def _transform_plate_per_mask_islands(
    plate: np.ndarray,
    mask,
    shape,
    *,
    scale: float,
    offset_x: float,
    offset_y: float,
    rotation: float,
    flip_h: bool,
    flip_v: bool,
) -> np.ndarray:
    """Alias for spec post-pass — same global transform as paint (mask unused here)."""
    del mask
    return _transform_cultural_plate_global(
        plate,
        shape,
        scale=scale,
        offset_x=offset_x,
        offset_y=offset_y,
        rotation=rotation,
        flip_h=flip_h,
        flip_v=flip_v,
    )


def _apply_placement(plate: np.ndarray, shape, mask=None) -> np.ndarray:
    pl = get_zone_placement()
    if pl is None or not _placement_active(pl):
        return plate
    h, w = int(shape[0]), int(shape[1])
    kwargs = dict(
        scale=float(pl["scale"]),
        offset_x=float(pl["offset_x"]),
        offset_y=float(pl["offset_y"]),
        rotation=float(pl["rotation"]),
        flip_h=bool(pl.get("flip_h")),
        flip_v=bool(pl.get("flip_v")),
    )
    out = _transform_cultural_plate_global(plate, (h, w), **kwargs)
    mark_zone_placement_applied()
    return out


def apply_zone_placement_rgb(tex: np.ndarray, shape, mask=None) -> np.ndarray:
    """Scale/zoom an RGB float plate using the current zone placement context."""
    pl = get_zone_placement()
    if pl is None or not _placement_active(pl):
        return tex
    h, w = int(shape[0]), int(shape[1])
    arr = np.clip(np.asarray(tex, dtype=np.float32), 0.0, 1.0)
    if arr.ndim == 2:
        arr = np.repeat(arr[:, :, np.newaxis], 3, axis=2)
    out = _apply_placement(arr[:, :, :3], (h, w), mask=mask)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def apply_zone_placement_spec(spec: np.ndarray, shape, mask=None) -> np.ndarray:
    """Scale/zoom M/R/CC spec channels consistently with paint placement."""
    pl = get_zone_placement()
    if pl is None or not _placement_active(pl):
        return spec
    h, w = int(shape[0]), int(shape[1])
    spec = np.asarray(spec, dtype=np.float32)
    rgb = np.stack(
        [
            np.clip(spec[:, :, 0], 0, 255),
            np.clip(spec[:, :, 1], 0, 255),
            np.clip(spec[:, :, 2], 0, 255),
        ],
        axis=2,
        dtype=np.float32,
    ) / 255.0
    rgb = _apply_placement(rgb, (h, w), mask=mask)
    out = spec.copy()
    out[:, :, 0] = np.clip(rgb[:, :, 0] * 255.0, 0, 255)
    out[:, :, 1] = np.clip(rgb[:, :, 1] * 255.0, 0, 255)
    out[:, :, 2] = np.clip(rgb[:, :, 2] * 255.0, 0, 255)
    return out
