"""Generic, non-authoritative template-position evidence for decal instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class PositionBlockMatch:
    block_kind: str
    block_name: str
    instance_fraction: float
    block_fraction: float


@dataclass(frozen=True)
class TemplatePositionEvidence:
    template_name: str
    matches: tuple[PositionBlockMatch, ...]
    best_number_fraction: float
    best_sponsor_fraction: float
    best_mandatory_fraction: float
    casts_votes: bool = False
    ownership_authority: bool = False


def _space(panel_map: Mapping[str, Any]) -> tuple[int, int]:
    value = str(panel_map.get("space") or "1024x1024").lower().replace(" ", "")
    try:
        width, height = (int(part) for part in value.split("x", 1))
    except Exception as exc:
        raise ValueError("panel map space must be WIDTHxHEIGHT") from exc
    if min(width, height) <= 0:
        raise ValueError("panel map space must be positive")
    return width, height


def _blocks(panel_map: Mapping[str, Any]) -> Sequence[tuple[str, str, Sequence[int]]]:
    result = []
    for kind, key in (("number", "number_blocks"), ("sponsor", "sponsor_blocks")):
        for item in panel_map.get(key) or ():
            result.append((kind, str(item.get("name") or key), item.get("bbox") or ()))
    for index, item in enumerate(panel_map.get("mandatory_decals") or ()):
        result.append(("mandatory", str(item.get("name") or f"mandatory_{index}"), item.get("bbox") or ()))
    return result


def compute_template_position_evidence(
    instance_bbox: Sequence[int],
    local_mask: np.ndarray,
    canvas_shape: Sequence[int],
    panel_map: Mapping[str, Any],
) -> TemplatePositionEvidence:
    """Measure exact instance-mask overlap with learned template blocks.

    The caller supplies the template map; this function contains no vehicle,
    filename, or target exceptions and never converts overlap into ownership.
    """
    x, y, width, height = [int(value) for value in instance_bbox]
    mask = np.asarray(local_mask) > 0
    if mask.shape != (height, width) or not mask.any():
        raise ValueError("position evidence requires a matching non-empty local mask")
    canvas_height, canvas_width = [int(value) for value in canvas_shape[:2]]
    source_width, source_height = _space(panel_map)
    instance_area = int(np.count_nonzero(mask))
    matches = []
    for kind, name, bbox in _blocks(panel_map):
        if len(bbox) != 4:
            continue
        bx, by, bw, bh = [float(value) for value in bbox]
        sx = int(round(bx * canvas_width / source_width))
        sy = int(round(by * canvas_height / source_height))
        sw = max(1, int(round(bw * canvas_width / source_width)))
        sh = max(1, int(round(bh * canvas_height / source_height)))
        ix0, iy0 = max(x, sx), max(y, sy)
        ix1, iy1 = min(x + width, sx + sw), min(y + height, sy + sh)
        if ix1 <= ix0 or iy1 <= iy0:
            overlap = 0
        else:
            overlap = int(np.count_nonzero(mask[iy0 - y:iy1 - y, ix0 - x:ix1 - x]))
        if not overlap:
            continue
        matches.append(PositionBlockMatch(
            block_kind=kind,
            block_name=name,
            instance_fraction=round(overlap / float(max(1, instance_area)), 6),
            block_fraction=round(overlap / float(max(1, sw * sh)), 6),
        ))
    matches.sort(key=lambda item: (-item.instance_fraction, item.block_kind, item.block_name))
    best = {
        kind: max((item.instance_fraction for item in matches if item.block_kind == kind), default=0.0)
        for kind in ("number", "sponsor", "mandatory")
    }
    return TemplatePositionEvidence(
        template_name=str(panel_map.get("template") or "unknown"),
        matches=tuple(matches),
        best_number_fraction=round(best["number"], 6),
        best_sponsor_fraction=round(best["sponsor"], 6),
        best_mandatory_fraction=round(best["mandatory"], 6),
    )


__all__ = ["PositionBlockMatch", "TemplatePositionEvidence", "compute_template_position_evidence"]
