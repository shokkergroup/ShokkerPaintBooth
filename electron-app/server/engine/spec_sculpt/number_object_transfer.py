"""Mask-isolated, orientation-neutral visual views for number-object transfer learning."""

from __future__ import annotations

import cv2
import numpy as np


VIEW_SIZE = 224


def isolated_object_views(
    rgb: np.ndarray,
    mask: np.ndarray,
    size: int = VIEW_SIZE,
) -> np.ndarray:
    """Return appearance and silhouette D4 views as N,C,H,W float tensors.

    The crop is derived only from the proposal mask.  Absolute canvas position is
    discarded.  The eight rotations/reflections are averaged by the caller.
    """
    image = np.asarray(rgb, np.uint8)
    support = np.asarray(mask, bool)
    rows, columns = np.nonzero(support)
    if not len(columns):
        raise ValueError("object mask is empty")
    x0, x1 = int(columns.min()), int(columns.max()) + 1
    y0, y1 = int(rows.min()), int(rows.max()) + 1
    width, height = x1 - x0, y1 - y0
    margin = max(2, int(round(max(width, height) * 0.12)))
    side = max(width, height) + 2 * margin
    crop = image[y0:y1, x0:x1]
    crop_mask = support[y0:y1, x0:x1]
    appearance = np.full((side, side, 3), 127, np.uint8)
    silhouette = np.zeros((side, side, 3), np.uint8)
    offset_x = (side - width) // 2
    offset_y = (side - height) // 2
    target = appearance[offset_y:offset_y + height, offset_x:offset_x + width]
    target[crop_mask] = crop[crop_mask]
    silhouette[offset_y:offset_y + height, offset_x:offset_x + width][crop_mask] = 255
    appearance = cv2.resize(appearance, (size, size), interpolation=cv2.INTER_LINEAR)
    silhouette = cv2.resize(silhouette, (size, size), interpolation=cv2.INTER_NEAREST)
    views = []
    for base in (appearance, silhouette):
        for turns in range(4):
            rotated = np.rot90(base, turns).copy()
            views.append(rotated)
            views.append(np.flip(rotated, axis=1).copy())
    return np.transpose(np.stack(views).astype(np.float32) / 255.0, (0, 3, 1, 2))
