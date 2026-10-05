"""Normalized template-position corroboration for number context proposals."""

from __future__ import annotations

import math
from typing import Mapping, Sequence


POSITION_FEATURE_NAMES = (
    "center_x", "center_y", "width", "height", "log_area", "log_aspect",
    "border_distance", "center_x_distance", "center_y_distance",
    "center_product", "center_x_squared", "center_y_squared",
)


def position_feature_mapping(
    bbox_or_proposal: Sequence[int] | Mapping[str, object], *, image_side: int = 1024,
) -> dict[str, float]:
    bbox = (
        bbox_or_proposal.get("bbox") if isinstance(bbox_or_proposal, Mapping)
        else bbox_or_proposal
    )
    if bbox is None or len(bbox) != 4:
        raise ValueError("number-context position features require one bbox")
    x, y, width, height = (float(value) for value in bbox)
    side = float(max(1, image_side))
    center_x = (x + width / 2.0) / side
    center_y = (y + height / 2.0) / side
    result = {
        "center_x": center_x,
        "center_y": center_y,
        "width": width / side,
        "height": height / side,
        "log_area": math.log(max(1.0, width * height)) / math.log(side**2),
        "log_aspect": math.log(max(width, 1.0) / max(height, 1.0)),
        "border_distance": min(x, y, side - x - width, side - y - height) / side,
        "center_x_distance": abs(center_x - 0.5),
        "center_y_distance": abs(center_y - 0.5),
        "center_product": center_x * center_y,
        "center_x_squared": center_x**2,
        "center_y_squared": center_y**2,
    }
    return result


__all__ = ["POSITION_FEATURE_NAMES", "position_feature_mapping"]
