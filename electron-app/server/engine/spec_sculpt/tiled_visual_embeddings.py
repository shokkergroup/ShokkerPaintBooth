"""D4 visual embeddings for exact immutable tiled candidates.

This is an offline/shadow evidence adapter.  It consumes exact source pixels
and masks, never filenames, car identifiers, or reviewed boxes.  Similarity is
corroborative evidence only and cannot create ownership.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision.models import efficientnet_b0


IMAGENET_MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)


def exact_masked_square(
    image_rgb: np.ndarray,
    bbox: Sequence[int],
    support: np.ndarray,
    *,
    size: int = 112,
) -> np.ndarray:
    """Place exact supported source pixels on a neutral square canvas."""
    image = np.asarray(image_rgb, dtype=np.uint8)
    x, y, width, height = map(int, bbox)
    mask = np.asarray(support, dtype=bool)
    if mask.shape != (height, width):
        raise ValueError("support shape does not match bbox")
    source = image[y:y + height, x:x + width]
    if source.shape[:2] != mask.shape:
        raise ValueError("bbox falls outside source image")
    side = max(width, height)
    neutral = np.round(IMAGENET_MEAN * 255.0).astype(np.uint8)
    square = np.empty((side, side, 3), dtype=np.uint8)
    square[:] = neutral
    top, left = (side - height) // 2, (side - width) // 2
    target = square[top:top + height, left:left + width]
    target[mask] = source[mask]
    return cv2.resize(square, (size, size), interpolation=cv2.INTER_AREA)


def d4_views(square_rgb: np.ndarray) -> tuple[np.ndarray, ...]:
    """Return all four rotations and their mirrors in a stable order."""
    square = np.asarray(square_rgb, dtype=np.uint8)
    views = []
    for rotations in range(4):
        rotated = np.rot90(square, rotations).copy()
        views.extend((rotated, np.fliplr(rotated).copy()))
    return tuple(views)


def load_efficientnet_encoder(weights_path: Path | str) -> torch.nn.Module:
    """Load cached weights without network access and expose pooled features."""
    path = Path(weights_path)
    if not path.is_file():
        raise FileNotFoundError(f"cached EfficientNet weights not found: {path}")
    model = efficientnet_b0(weights=None)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    encoder = torch.nn.Sequential(model.features, model.avgpool, torch.nn.Flatten(1))
    encoder.eval()
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    return encoder


def embed_d4_candidates(
    encoder: torch.nn.Module,
    squares: Sequence[np.ndarray],
    *,
    batch_size: int = 64,
) -> np.ndarray:
    """Average normalized encoder evidence across D4 views per candidate."""
    views = embed_d4_candidate_views(encoder, squares, batch_size=batch_size)
    if not len(views):
        return np.zeros((0, 1280), dtype=np.float32)
    output = views.mean(axis=1)
    norms = np.linalg.norm(output, axis=1, keepdims=True)
    output /= np.maximum(norms, 1e-8)
    output.setflags(write=False)
    return output


def embed_d4_candidate_views(
    encoder: torch.nn.Module,
    squares: Sequence[np.ndarray],
    *,
    batch_size: int = 64,
) -> np.ndarray:
    """Preserve eight normalized views for exact max-over-D4 matching."""
    if not squares:
        return np.zeros((0, 8, 1280), dtype=np.float32)
    candidate_indices, tensors = [], []
    for candidate_index, square in enumerate(squares):
        for view in d4_views(square):
            normalized = (view.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
            tensors.append(np.transpose(normalized, (2, 0, 1)))
            candidate_indices.append(candidate_index)
    output = None
    view_offsets = np.zeros(len(squares), dtype=np.int32)
    with torch.inference_mode():
        for start in range(0, len(tensors), batch_size):
            batch = torch.from_numpy(np.stack(tensors[start:start + batch_size]))
            values = encoder(batch).cpu().numpy().astype(np.float32)
            if output is None:
                output = np.zeros((len(squares), 8, values.shape[1]), dtype=np.float32)
            for offset, value in enumerate(values):
                candidate_index = candidate_indices[start + offset]
                view_index = int(view_offsets[candidate_index])
                output[candidate_index, view_index] = value
                view_offsets[candidate_index] += 1
    norms = np.linalg.norm(output, axis=2, keepdims=True)
    output /= np.maximum(norms, 1e-8)
    output.setflags(write=False)
    return output


def d4_orbit_similarity(candidate_views: np.ndarray) -> np.ndarray:
    """Return symmetric max-relative-view similarity for every candidate pair."""
    views = np.asarray(candidate_views, dtype=np.float32)
    if views.ndim != 3 or views.shape[1] != 8:
        raise ValueError("candidate views must have shape (candidate, 8, feature)")
    if not len(views):
        return np.zeros((0, 0), dtype=np.float32)
    relative = views[:, 0] @ views.reshape(-1, views.shape[-1]).T
    relative = relative.reshape(len(views), len(views), 8).max(axis=2)
    similarity = np.maximum(relative, relative.T)
    np.fill_diagonal(similarity, 1.0)
    similarity.setflags(write=False)
    return similarity


__all__ = [
    "d4_orbit_similarity", "d4_views", "embed_d4_candidates",
    "embed_d4_candidate_views", "exact_masked_square",
    "load_efficientnet_encoder",
]
