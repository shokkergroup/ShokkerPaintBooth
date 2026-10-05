"""Livery-neutral integrity metrics for specialized physical-view captures.

Only decodeability and adapter-declared spatial resolution are hard gates.
Appearance metrics are advisory because a valid livery can be intentionally
solid, dark, bright, or low-detail.  No brand, color, filename, or car-specific
heuristic is allowed here.
"""

from __future__ import annotations

import io
import math
from typing import Any

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError


SCHEMA = "shokk-forge.surface-capture-quality/v1"
REVIEW_SCHEMA = "shokk-forge.surface-review-quality/v1"


def inspect_capture(body: bytes, contract: dict[str, Any] | None) -> dict[str, Any]:
    contract = contract or {}
    failures: list[str] = []
    warnings: list[str] = []
    try:
        with Image.open(io.BytesIO(body)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
            image_format = str(source.format or "unknown").lower()
    except (UnidentifiedImageError, OSError, ValueError):
        return {
            "$schema": SCHEMA,
            "admissible": False,
            "hard_failures": ["undecodable_image"],
            "warnings": [],
            "width": 0,
            "height": 0,
            "short_edge": 0,
            "pixel_count": 0,
            "megapixels": 0.0,
            "format": "unknown",
        }

    width, height = image.size
    short_edge = min(width, height)
    pixel_count = width * height
    hard_limits = {
        "width_below_adapter_minimum": (width, int(contract.get("minimum_width") or 0)),
        "height_below_adapter_minimum": (height, int(contract.get("minimum_height") or 0)),
        "short_edge_below_adapter_minimum": (short_edge, int(contract.get("minimum_short_edge") or 0)),
        "pixel_count_below_adapter_minimum": (pixel_count, int(contract.get("minimum_pixels") or 0)),
    }
    failures.extend(name for name, (actual, minimum) in hard_limits.items() if minimum and actual < minimum)

    sample = image.copy()
    sample.thumbnail((512, 512), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(sample)
    stat = ImageStat.Stat(gray)
    luma_mean = float(stat.mean[0])
    luma_stddev = float(stat.stddev[0])
    histogram = gray.histogram()
    total = max(1, sum(histogram))
    shadow_fraction = sum(histogram[:8]) / total
    highlight_fraction = sum(histogram[248:]) / total
    edge_mean = float(ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0])

    advisory = (
        ("low_luma_variation_review", luma_stddev < float(contract.get("advisory_minimum_luma_stddev") or 0.0)),
        ("low_edge_energy_review", edge_mean < float(contract.get("advisory_minimum_edge_mean") or 0.0)),
        ("mostly_shadow_review", shadow_fraction > float(contract.get("advisory_maximum_shadow_fraction") or 1.0)),
        ("mostly_highlight_review", highlight_fraction > float(contract.get("advisory_maximum_highlight_fraction") or 1.0)),
    )
    warnings.extend(name for name, active in advisory if active)
    return {
        "$schema": SCHEMA,
        "admissible": not failures,
        "hard_failures": failures,
        "warnings": warnings,
        "width": width,
        "height": height,
        "short_edge": short_edge,
        "pixel_count": pixel_count,
        "megapixels": round(pixel_count / 1_000_000.0, 4),
        "format": image_format,
        "luma_mean": round(luma_mean, 4),
        "luma_stddev": round(luma_stddev, 4),
        "edge_mean": round(edge_mean, 4),
        "shadow_fraction": round(shadow_fraction, 6),
        "highlight_fraction": round(highlight_fraction, 6),
    }


def assess_review_quad(
    capture_quality: dict[str, Any],
    quad: list[list[float]],
    contract: dict[str, Any] | None,
) -> dict[str, Any]:
    """Measure whether the confirmed physical face has enough source pixels."""

    contract = contract or {}
    width = int(capture_quality.get("width") or 0)
    height = int(capture_quality.get("height") or 0)
    area_norm = abs(
        sum(
            quad[index][0] * quad[(index + 1) % 4][1]
            - quad[(index + 1) % 4][0] * quad[index][1]
            for index in range(4)
        )
        / 2.0
    )
    area_pixels = area_norm * width * height
    edge_pixels = [
        math.hypot(
            (quad[(index + 1) % 4][0] - quad[index][0]) * width,
            (quad[(index + 1) % 4][1] - quad[index][1]) * height,
        )
        for index in range(4)
    ]
    minimum_edge = min(edge_pixels, default=0.0)
    failures: list[str] = []
    if area_pixels < float(contract.get("review_minimum_quad_pixels") or 0.0):
        failures.append("reviewed_surface_pixel_area_below_adapter_minimum")
    if minimum_edge < float(contract.get("review_minimum_edge_pixels") or 0.0):
        failures.append("reviewed_surface_edge_below_adapter_minimum")
    margin = min(min(x for x, _ in quad), min(y for _, y in quad), min(1.0 - x for x, _ in quad), min(1.0 - y for _, y in quad))
    warnings = []
    if margin < float(contract.get("review_boundary_warning_margin") or 0.0):
        warnings.append("reviewed_surface_touches_frame_review")
    return {
        "$schema": REVIEW_SCHEMA,
        "admissible": not failures,
        "hard_failures": failures,
        "warnings": warnings,
        "normalized_area": round(area_norm, 6),
        "pixel_area": int(round(area_pixels)),
        "minimum_edge_pixels": round(minimum_edge, 3),
        "frame_margin": round(margin, 6),
        "source_width": width,
        "source_height": height,
    }
