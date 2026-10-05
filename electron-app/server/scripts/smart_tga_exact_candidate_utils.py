"""Lightweight exact-candidate helpers shared by Smart TGA research probes."""
from __future__ import annotations

import cv2
import numpy as np


CONTROL_PAINTS = {
    "dirtlatemodel 350/car_num_1006305.tga",
    "dirtlatemodel 350/car_num_1007631.tga",
    "dirtlatemodel 358/car_num_1008515.tga",
    "dirtlatemodel 358/car_num_1328151.tga",
    "dirtlatemodel 358/car_num_247671.tga",
}


def decode_support(exact, index: int) -> np.ndarray:
    offset = int(exact["offsets"][index])
    length = int(exact["lengths"][index])
    height, width = map(int, exact["shapes"][index])
    return np.unpackbits(exact["packed"][offset:offset + length])[:height * width].reshape(
        height, width,
    ).astype(bool)


def normalized_patch(rgb: np.ndarray, support: np.ndarray, size: int) -> np.ndarray:
    """Return aligned RGB/support/edge/distance patches in all eight D4 views."""
    if rgb.shape[:2] != support.shape:
        raise ValueError(f"source/mask shape mismatch: {rgb.shape[:2]} vs {support.shape}")
    height, width = support.shape
    scale = float(size - 8) / max(height, width)
    target_h = max(1, min(size, int(round(height * scale))))
    target_w = max(1, min(size, int(round(width * scale))))
    mask_u8 = support.astype(np.uint8)
    masked_rgb = rgb.astype(np.float32) / 255.0
    masked_rgb *= support[:, :, None]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.magnitude(grad_x, grad_y) * support
    if edge.max() > 0:
        edge /= edge.max()
    distance = cv2.distanceTransform(mask_u8, cv2.DIST_L2, 3)
    if distance.max() > 0:
        distance /= distance.max()
    channels = np.dstack((masked_rgb, support.astype(np.float32), edge, distance))
    resized = np.concatenate((
        cv2.resize(channels[:, :, :3], (target_w, target_h), interpolation=cv2.INTER_AREA),
        cv2.resize(channels[:, :, 3:], (target_w, target_h), interpolation=cv2.INTER_AREA),
    ), axis=2)
    canvas = np.zeros((size, size, channels.shape[2]), dtype=np.float32)
    top, left = (size - target_h) // 2, (size - target_w) // 2
    canvas[top:top + target_h, left:left + target_w] = resized
    views = []
    for turns in range(4):
        rotated = np.rot90(canvas, turns, axes=(0, 1))
        views.extend((rotated, np.fliplr(rotated)))
    return np.ascontiguousarray(
        np.stack(views).transpose(0, 3, 1, 2), dtype=np.float32,
    )
