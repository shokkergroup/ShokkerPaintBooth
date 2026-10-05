"""Hash-bound manual surface review for specialized DLM evidence.

The four-corner seed is UI guidance only.  This module is the sole authority
that can persist a reviewed specialized surface, and it binds the result to
the exact source bytes, adapter bytes, physical role, and target surface.
"""

from __future__ import annotations

import math
from typing import Any

from .contracts import ContractError, require_mapping, validate_reference_id
from .surface_capture_quality import assess_review_quad


SCHEMA = "shokk-forge.surface-evidence-review/v1"
PROVENANCE = "guided_user_surface_quad/v1"


def _polygon_area(points: list[list[float]]) -> float:
    return sum(
        points[index][0] * points[(index + 1) % 4][1]
        - points[(index + 1) % 4][0] * points[index][1]
        for index in range(4)
    ) / 2.0


def validate_surface_quad(value: Any, contract: dict[str, Any]) -> list[list[float]]:
    """Validate normalized TL,TR,BR,BL source points without repairing them."""

    if not isinstance(value, list) or len(value) != 4:
        raise ContractError("surface evidence quad must contain four ordered points")
    points: list[list[float]] = []
    for raw in value:
        if not isinstance(raw, list) or len(raw) != 2:
            raise ContractError("surface evidence quad contains an invalid point")
        try:
            point = [float(raw[0]), float(raw[1])]
        except (TypeError, ValueError) as exc:
            raise ContractError("surface evidence quad contains an invalid point") from exc
        if not all(math.isfinite(axis) and 0.0 <= axis <= 1.0 for axis in point):
            raise ContractError("surface evidence quad must stay inside the source image")
        points.append(point)

    area = _polygon_area(points)
    if area < float(contract.get("minimum_area") or 0.005):
        raise ContractError("surface evidence quad is too small, reversed, or folded")
    signs: list[int] = []
    for index in range(4):
        a, b, c = points[index], points[(index + 1) % 4], points[(index + 2) % 4]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) <= 0.00001:
            raise ContractError("surface evidence quad must remain ordered and convex")
        signs.append(1 if cross > 0 else -1)
    if any(sign != signs[0] for sign in signs):
        raise ContractError("surface evidence quad must remain ordered and convex")
    if not (
        points[0][0] < points[1][0]
        and points[3][0] < points[2][0]
        and points[0][1] < points[3][1]
        and points[1][1] < points[2][1]
    ):
        raise ContractError("surface evidence quad must use screen TL,TR,BR,BL order")
    return points


def build_surface_review(
    *,
    adapter: dict[str, Any],
    adapter_sha256: str,
    role: str,
    reference: dict[str, Any],
    quad: Any,
) -> dict[str, Any]:
    """Build the only persisted review form accepted by the local service."""

    spec = require_mapping((adapter.get("optional_evidence_roles") or {}).get(role), "evidence role")
    contract = require_mapping(spec.get("review_contract"), "surface review contract")
    reference_id = validate_reference_id(reference.get("id"))
    points = validate_surface_quad(quad, contract)
    review_quality = assess_review_quad(
        require_mapping(reference.get("capture_quality"), "capture quality"),
        points,
        spec.get("capture_quality_contract"),
    )
    if not review_quality["admissible"]:
        raise ContractError("surface evidence quad lacks usable source pixels: " + ", ".join(review_quality["hard_failures"]))
    return {
        "$schema": SCHEMA,
        "role": role,
        "surface": spec.get("surface"),
        "physical_scope": spec.get("physical_scope"),
        "anchor_field": contract.get("anchor_field"),
        "point_order": contract.get("point_order"),
        "coordinate_space": contract.get("coordinate_space"),
        "quad": points,
        "reference_id": reference_id,
        "reference_sha256": reference.get("sha256"),
        "adapter_sha256": adapter_sha256,
        "provenance": PROVENANCE,
        "user_confirmed": True,
        "capture_quality": reference.get("capture_quality"),
        "review_quality": review_quality,
    }
