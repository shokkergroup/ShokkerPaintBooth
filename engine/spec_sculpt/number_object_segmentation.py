"""Small owner-neutral number-object segmentation model and supervision helpers.

The model consumes only image-derived channels.  Layer assignments, filenames, car
identity, and bounding-box coordinates are deliberately absent from inference.
Reviewed boxes are used only while building supervision masks.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, Sequence

import cv2
import numpy as np


MODEL_SIZE = 256
INPUT_CHANNELS = 7


def probability_region_proposals(
    probability: np.ndarray,
    output_shape: Sequence[int],
    *,
    quantiles: Sequence[float] = (0.90, 0.95, 0.98),
    min_model_pixels: int = 5,
) -> tuple[dict, ...]:
    """Expose high-recall regions from a semantic map without assigning an owner.

    Multiple relative thresholds deliberately preserve nested hypotheses. These
    immutable proposals are evidence for a later classifier/adjudicator; they do
    not cast votes or mutate any output layer.
    """
    values = np.asarray(probability, np.float32)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("probability must be a finite HxW array")
    out_height, out_width = int(output_shape[0]), int(output_shape[1])
    proposals = []
    for quantile in quantiles:
        if not 0.0 < float(quantile) < 1.0:
            raise ValueError("proposal quantiles must be between zero and one")
        threshold = float(np.quantile(values, float(quantile)))
        binary = (values >= threshold).astype(np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, 8)
        for label in range(1, count):
            x, y, width, height, area = (int(value) for value in stats[label])
            if area < int(min_model_pixels):
                continue
            x0 = max(0, int(np.floor(x * out_width / values.shape[1])))
            y0 = max(0, int(np.floor(y * out_height / values.shape[0])))
            x1 = min(out_width, int(np.ceil((x + width) * out_width / values.shape[1])))
            y1 = min(out_height, int(np.ceil((y + height) * out_height / values.shape[0])))
            local = labels[y:y + height, x:x + width] == label
            support = cv2.resize(local.astype(np.uint8), (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST) > 0
            support.setflags(write=False)
            digest = hashlib.sha256()
            digest.update(support.tobytes())
            digest.update(f"{x0},{y0},{x1-x0},{y1-y0},{quantile:.6f}".encode("utf-8"))
            component_values = values[labels == label]
            proposals.append({
                "proposal_id": "number-map:" + digest.hexdigest()[:16],
                "proposal_bbox": [x0, y0, x1 - x0, y1 - y0],
                "raw_support": support,
                "owner_neutral": True,
                "ownership_authority": False,
                "provenance": {
                    "source_stage": "number_object_probability_map",
                    "relative_quantile": float(quantile), "threshold": threshold,
                    "model_pixels": area, "mean_probability": float(component_values.mean()),
                    "max_probability": float(component_values.max()),
                },
            })
    return tuple(proposals)


def image_feature_tensor(rgb: np.ndarray, size: int = MODEL_SIZE) -> np.ndarray:
    """Return a compact full-image feature tensor in C,H,W layout."""
    image = cv2.resize(np.asarray(rgb, np.uint8), (size, size), interpolation=cv2.INTER_AREA)
    floating = image.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = np.clip(np.sqrt(gx * gx + gy * gy), 0.0, 1.0)
    mean = cv2.boxFilter(gray, cv2.CV_32F, (9, 9), normalize=True)
    square_mean = cv2.boxFilter(gray * gray, cv2.CV_32F, (9, 9), normalize=True)
    local_std = np.sqrt(np.maximum(0.0, square_mean - mean * mean))
    channels = (
        floating[..., 0], floating[..., 1], floating[..., 2],
        hsv[..., 1] / 255.0, gray, gradient, np.clip(local_std * 4.0, 0.0, 1.0),
    )
    return np.stack(channels).astype(np.float32)


def project_local_support(
    local_mask: np.ndarray,
    bbox: Sequence[int],
    canvas_shape: Sequence[int],
    size: int = MODEL_SIZE,
) -> np.ndarray:
    """Place a bbox-local mask on canvas, then pool exactly like supervision."""
    canvas_height, canvas_width = int(canvas_shape[0]), int(canvas_shape[1])
    x, y, width, height = (int(value) for value in bbox)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas_width, x + width), min(canvas_height, y + height)
    support = np.asarray(local_mask, bool)
    if support.shape != (height, width):
        support = cv2.resize(
            support.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST,
        ) > 0
    canvas = np.zeros((canvas_height, canvas_width), np.float32)
    if x1 > x0 and y1 > y0:
        source_x0, source_y0 = x0 - x, y0 - y
        canvas[y0:y1, x0:x1] = support[
            source_y0:source_y0 + (y1 - y0), source_x0:source_x0 + (x1 - x0)
        ]
    return cv2.resize(canvas, (size, size), interpolation=cv2.INTER_AREA) > 0


def component_mask(
    layer_mask: np.ndarray,
    bbox: Sequence[int],
    expected_area: int | None = None,
) -> np.ndarray:
    """Recover one reviewed connected component from its recorded tight bbox."""
    binary = np.asarray(layer_mask, bool).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, 8)
    x, y, width, height = (int(value) for value in bbox)
    candidates: list[tuple[float, int]] = []
    for label in range(1, count):
        sx, sy, sw, sh, area = (int(value) for value in stats[label])
        box_error = abs(sx - x) + abs(sy - y) + abs(sw - width) + abs(sh - height)
        area_error = 0.0 if expected_area is None else abs(area - expected_area) / max(1, expected_area)
        candidates.append((box_error * 10.0 + area_error, label))
    if not candidates:
        return np.zeros_like(binary, dtype=bool)
    score, selected = min(candidates)
    if score > 12.0:
        raise ValueError(f"no component matches bbox {list(bbox)} (best score {score:.3f})")
    return labels == selected


def pooled_supervision(
    positive: np.ndarray,
    negative: np.ndarray,
    size: int = MODEL_SIZE,
) -> tuple[np.ndarray, np.ndarray]:
    """Downsample exact masks without turning unlabeled pixels into negatives."""
    # Float input preserves fractional coverage for sub-cell reviewed fragments;
    # uint8 area resampling can round a real one-pixel fragment down to zero.
    positive_small = cv2.resize(positive.astype(np.float32), (size, size), interpolation=cv2.INTER_AREA) > 0
    negative_small = cv2.resize(negative.astype(np.float32), (size, size), interpolation=cv2.INTER_AREA) > 0
    conflict = positive_small & negative_small
    positive_small[conflict] = False
    negative_small[conflict] = False
    target = positive_small.astype(np.float32)
    known = (positive_small | negative_small).astype(np.float32)
    return target, known


def pooled_boxes(
    boxes: Iterable[Sequence[int]],
    source_shape: Sequence[int],
    size: int = MODEL_SIZE,
) -> np.ndarray:
    """Return weak MIL boxes at model resolution."""
    height, width = (int(source_shape[0]), int(source_shape[1]))
    output = np.zeros((size, size), np.uint8)
    for box in boxes:
        x, y, box_width, box_height = (int(value) for value in box)
        x0 = max(0, min(size, int(np.floor(x * size / width))))
        y0 = max(0, min(size, int(np.floor(y * size / height))))
        x1 = max(x0 + 1, min(size, int(np.ceil((x + box_width) * size / width))))
        y1 = max(y0 + 1, min(size, int(np.ceil((y + box_height) * size / height))))
        output[y0:y1, x0:x1] = 1
    return output.astype(bool)


def build_tiny_unet(base_channels: int = 12):
    """Construct the CPU-friendly one-pass model lazily to keep imports light."""
    import torch
    from torch import nn

    class Block(nn.Module):
        def __init__(self, incoming: int, outgoing: int):
            super().__init__()
            self.layers = nn.Sequential(
                nn.Conv2d(incoming, outgoing, 3, padding=1, bias=False),
                nn.BatchNorm2d(outgoing), nn.SiLU(inplace=True),
                nn.Conv2d(outgoing, outgoing, 3, padding=1, bias=False),
                nn.BatchNorm2d(outgoing), nn.SiLU(inplace=True),
            )

        def forward(self, value):
            return self.layers(value)

    class TinyUNet(nn.Module):
        def __init__(self):
            super().__init__()
            b = base_channels
            self.down1, self.down2, self.bridge = Block(INPUT_CHANNELS, b), Block(b, b * 2), Block(b * 2, b * 4)
            self.pool = nn.MaxPool2d(2)
            self.up2 = nn.ConvTranspose2d(b * 4, b * 2, 2, stride=2)
            self.decode2 = Block(b * 4, b * 2)
            self.up1 = nn.ConvTranspose2d(b * 2, b, 2, stride=2)
            self.decode1 = Block(b * 2, b)
            self.head = nn.Conv2d(b, 1, 1)

        def forward(self, value):
            first = self.down1(value)
            second = self.down2(self.pool(first))
            bridge = self.bridge(self.pool(second))
            decoded2 = self.decode2(torch.cat((self.up2(bridge), second), dim=1))
            return self.head(self.decode1(torch.cat((self.up1(decoded2), first), dim=1)))

    return TinyUNet()
