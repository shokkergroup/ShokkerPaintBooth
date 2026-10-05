"""Livery-agnostic image evidence inspection for Forge pipeline stages."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

from .contracts import ContractError, confine_child


SCHEMA = "shokk-forge.image-geometry-evidence/v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_reference(job_dir: Path, entry: dict[str, Any]) -> dict[str, Any]:
    path = confine_child(job_dir, job_dir / str(entry["stored_path"]))
    if not path.is_file():
        raise ContractError(f"stored reference is missing: {entry['id']}")
    actual_sha = sha256_file(path)
    if actual_sha != entry["sha256"]:
        raise ContractError(f"stored reference hash changed: {entry['id']}")
    try:
        with Image.open(path) as opened:
            opened.load()
            original_size = opened.size
            source_mode = opened.mode
            work = opened.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise ContractError(f"stored reference is not a decodable image: {entry['id']}") from exc

    if min(original_size) < 64:
        raise ContractError(f"stored reference is too small for geometry: {entry['id']}")
    work.thumbnail((512, 512), Image.Resampling.LANCZOS)
    array = np.asarray(work, dtype=np.uint8)
    rgb = array[:, :, :3].astype(np.float32)
    alpha = array[:, :, 3]
    border_width = max(2, min(work.size) // 80)
    border = np.concatenate(
        (
            rgb[:border_width].reshape(-1, 3),
            rgb[-border_width:].reshape(-1, 3),
            rgb[:, :border_width].reshape(-1, 3),
            rgb[:, -border_width:].reshape(-1, 3),
        )
    )
    background = np.median(border, axis=0)
    distance = np.linalg.norm(rgb - background, axis=2)
    foreground = (alpha > 8) & (distance >= 18.0)
    if int(foreground.sum()) < max(32, int(foreground.size * 0.002)):
        foreground = alpha > 8
    ys, xs = np.nonzero(foreground)
    if len(xs):
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        bbox_normalized = [
            round(bbox[0] / work.width, 6),
            round(bbox[1] / work.height, 6),
            round(bbox[2] / work.width, 6),
            round(bbox[3] / work.height, 6),
        ]
    else:
        bbox = None
        bbox_normalized = None
    foreground_fraction = float(foreground.mean())
    dimension_confidence = min(1.0, min(original_size) / 512.0)
    foreground_confidence = 1.0 if 0.01 <= foreground_fraction <= 0.98 else 0.6
    return {
        "$schema": SCHEMA,
        "reference_id": entry["id"],
        "role": entry["role"],
        "role_source": entry.get("role_source"),
        "role_confidence": float(entry.get("role_confidence") or 0.0),
        "stored_path": entry["stored_path"],
        "sha256": actual_sha,
        "bytes": int(entry["bytes"]),
        "width": int(original_size[0]),
        "height": int(original_size[1]),
        "mode": source_mode,
        "sample_size": [work.width, work.height],
        "border_background_rgb": [int(round(value)) for value in background],
        "foreground_bbox_sample": bbox,
        "foreground_bbox_normalized": bbox_normalized,
        "foreground_fraction": round(foreground_fraction, 6),
        "mean_alpha": round(float(alpha.mean()) / 255.0, 6),
        "geometry_confidence": round(
            float(entry.get("role_confidence") or 0.0) * dimension_confidence * foreground_confidence,
            6,
        ),
        "valid": bbox is not None,
    }
