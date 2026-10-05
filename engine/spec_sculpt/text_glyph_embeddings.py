"""Local EasyOCR contextual glyph embeddings for exact Smart TGA masks."""
from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np
import torch
from torch.nn import functional as F

from engine.spec_sculpt.tiled_visual_embeddings import d4_views


def prepare_text_glyph_views(
    squares: Sequence[np.ndarray], *, width: int = 96, height: int = 64,
) -> np.ndarray:
    """Convert exact RGB squares into eight contrast-normalized OCR views."""
    prepared = []
    for square in squares:
        gray = cv2.cvtColor(np.asarray(square, dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        gray = cv2.equalizeHist(gray)
        for view in d4_views(gray):
            resized = cv2.resize(view, (width, height), interpolation=cv2.INTER_AREA)
            prepared.append(resized.astype(np.float32) / 127.5 - 1.0)
    if not prepared:
        return np.zeros((0, 8, 1, height, width), dtype=np.float32)
    return np.asarray(prepared, dtype=np.float32).reshape(len(squares), 8, 1, height, width)


def encode_text_glyph_views(
    recognizer: torch.nn.Module,
    squares: Sequence[np.ndarray],
    *,
    batch_size: int = 128,
) -> np.ndarray:
    """Pool EasyOCR contextual sequence features without decoding text."""
    prepared = prepare_text_glyph_views(squares)
    if not len(prepared):
        return np.zeros((0, 8, 512), dtype=np.float32)
    flat = prepared.reshape(-1, *prepared.shape[2:])
    encoded = []
    recognizer.eval()
    with torch.inference_mode():
        for start in range(0, len(flat), batch_size):
            values = torch.from_numpy(flat[start:start + batch_size])
            visual = recognizer.FeatureExtraction(values)
            visual = recognizer.AdaptiveAvgPool(visual.permute(0, 3, 1, 2)).squeeze(3)
            contextual = recognizer.SequenceModeling(visual)
            pooled = torch.cat((contextual.mean(dim=1), contextual.amax(dim=1)), dim=1)
            encoded.append(F.normalize(pooled, dim=1).cpu().numpy().astype(np.float32))
    output = np.concatenate(encoded).reshape(len(squares), 8, -1)
    output.setflags(write=False)
    return output


__all__ = ["encode_text_glyph_views", "prepare_text_glyph_views"]
