"""Validation primitives for the local SHOKK FORGE job service.

This module owns job/API shape only. Livery interpretation and geometry remain
in the tested ``_forge_*`` libraries and versioned template adapters.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


JOB_SCHEMA = "shokk-forge.job/v1"
ADAPTER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,80}$")
JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
REFERENCE_ID_RE = re.compile(r"^ref-[0-9a-f]{12}$")
ALLOWED_MODES = {"guided", "full_auto"}
REQUIRED_DLM_ROLES = ("left", "right", "top", "front", "rear")
ALLOWED_REFERENCE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga"}
CORRECTION_SECTIONS = {"view_roles", "anchors", "surface_ownership", "readable_orientation"}
ANCHOR_FIELDS_BY_ROLE = {
    "left": {"rear_wheel_center", "front_wheel_center", "body_top_y", "rocker_y"},
    "right": {"rear_wheel_center", "front_wheel_center", "body_top_y", "rocker_y"},
    "top": {"hood_quad", "roof_quad", "rear_deck_quad"},
    "front": {"center_x", "half_width", "ground_y", "hood_seam_y", "valance_top_y", "front_valance_quad"},
    "rear": {"rear_deck_quad", "spoiler_inside_quad", "spoiler_outside_quad"},
}


class ContractError(ValueError):
    """A client-visible Forge contract violation."""


def require_mapping(value: Any, label: str = "payload") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object")
    return value


def validate_create_payload(value: Any, adapter_ids: set[str]) -> tuple[str, str]:
    payload = require_mapping(value)
    adapter_id = str(payload.get("adapter_id") or "").strip()
    mode = str(payload.get("mode") or "guided").strip()
    if not ADAPTER_ID_RE.fullmatch(adapter_id):
        raise ContractError("adapter_id is invalid")
    if adapter_id not in adapter_ids:
        raise ContractError("adapter_id is not registered")
    if mode not in ALLOWED_MODES:
        raise ContractError("mode must be guided or full_auto")
    return adapter_id, mode


def validate_job_id(job_id: str) -> str:
    job_id = str(job_id or "").strip().lower()
    if not JOB_ID_RE.fullmatch(job_id):
        raise ContractError("job_id is invalid")
    return job_id


def validate_reference_role(role: str, allowed_roles: tuple[str, ...]) -> str:
    role = str(role or "").strip().lower()
    if role not in allowed_roles:
        raise ContractError(f"reference role must be one of: {', '.join(allowed_roles)}")
    return role


def validate_reference_id(reference_id: str) -> str:
    reference_id = str(reference_id or "").strip().lower()
    if not REFERENCE_ID_RE.fullmatch(reference_id):
        raise ContractError("reference_id is invalid")
    return reference_id


def validate_reference_filename(filename: str) -> tuple[str, str]:
    name = Path(str(filename or "")).name
    if not name or name in {".", ".."}:
        raise ContractError("reference filename is missing")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_REFERENCE_EXTENSIONS:
        raise ContractError("unsupported reference image type")
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._")[:80]
    if not safe_stem:
        safe_stem = "reference"
    return safe_stem, suffix


def confine_child(root: Path, child: Path) -> Path:
    root = root.resolve()
    resolved = child.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ContractError("path escapes the configured Forge jobs root") from exc
    return resolved


def validate_corrections_payload(value: Any) -> dict[str, dict[str, Any]]:
    payload = require_mapping(value)
    unknown = set(payload) - CORRECTION_SECTIONS
    if unknown:
        raise ContractError(f"unknown correction section: {sorted(unknown)[0]}")
    normalized: dict[str, dict[str, Any]] = {}
    for section, raw in payload.items():
        mapping = require_mapping(raw, section)
        if len(mapping) > 64:
            raise ContractError(f"{section} has too many entries")
        normalized[section] = {}
        for key, item in mapping.items():
            safe_key = str(key or "").strip()
            if not ADAPTER_ID_RE.fullmatch(safe_key):
                raise ContractError(f"{section} contains an invalid key")
            if section == "anchors":
                _validate_anchor_correction(safe_key, item)
            else:
                _validate_json_correction(item, f"{section}.{safe_key}", depth=0)
            normalized[section][safe_key] = item
    return normalized


def _normalized_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label} must be a normalized number")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ContractError(f"{label} must be between 0 and 1")
    return number


def _normalized_point(value: Any, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ContractError(f"{label} must be an [x, y] point")
    return _normalized_number(value[0], f"{label}[0]"), _normalized_number(value[1], f"{label}[1]")


def _normalized_quad(value: Any, label: str) -> list[tuple[float, float]]:
    if not isinstance(value, list) or len(value) != 4:
        raise ContractError(f"{label} must contain four ordered points")
    points = [_normalized_point(point, f"{label}[{index}]") for index, point in enumerate(value)]
    area = abs(sum(
        points[index][0] * points[(index + 1) % 4][1]
        - points[(index + 1) % 4][0] * points[index][1]
        for index in range(4)
    ) / 2.0)
    if area < 0.001:
        raise ContractError(f"{label} is too small or folded")
    signs = []
    for index in range(4):
        a, b, c = points[index], points[(index + 1) % 4], points[(index + 2) % 4]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) > 0.00001:
            signs.append(1 if cross > 0 else -1)
    if len(signs) < 4 or any(sign != signs[0] for sign in signs):
        raise ContractError(f"{label} points must stay ordered and convex")
    return points


def _validate_anchor_correction(role: str, value: Any) -> None:
    if role not in ANCHOR_FIELDS_BY_ROLE:
        raise ContractError("anchors contains an unsupported physical role")
    mapping = require_mapping(value, f"anchors.{role}")
    unknown = set(mapping) - ANCHOR_FIELDS_BY_ROLE[role]
    if unknown:
        raise ContractError(f"anchors.{role} contains an unknown field: {sorted(unknown)[0]}")
    for field, raw in mapping.items():
        label = f"anchors.{role}.{field}"
        if field.endswith("_quad"):
            _normalized_quad(raw, label)
        elif field.endswith("_center"):
            _normalized_point(raw, label)
        else:
            _normalized_number(raw, label)
    if role in {"left", "right"} and {"body_top_y", "rocker_y"} <= set(mapping):
        if float(mapping["body_top_y"]) >= float(mapping["rocker_y"]) - 0.02:
            raise ContractError(f"anchors.{role}.body_top_y must remain above rocker_y")
    if role == "front" and {"hood_seam_y", "ground_y"} <= set(mapping):
        if float(mapping["hood_seam_y"]) >= float(mapping["ground_y"]) - 0.025:
            raise ContractError("anchors.front.hood_seam_y must remain above ground_y")
    if role == "front" and {"valance_top_y", "ground_y"} <= set(mapping):
        if float(mapping["valance_top_y"]) >= float(mapping["ground_y"]) - 0.01:
            raise ContractError("anchors.front.valance_top_y must remain above ground_y")
    if role == "front" and {"center_x", "half_width"} <= set(mapping):
        center, half = float(mapping["center_x"]), float(mapping["half_width"])
        if half < 0.02 or center - half < 0 or center + half > 1:
            raise ContractError("anchors.front center/half_width must stay inside the source image")
    if role == "top" and {"hood_quad", "roof_quad", "rear_deck_quad"} <= set(mapping):
        centers = [
            sum(point[0] for point in _normalized_quad(mapping[name], f"anchors.top.{name}")) / 4.0
            for name in ("hood_quad", "roof_quad", "rear_deck_quad")
        ]
        increasing = centers[0] + 0.02 < centers[1] and centers[1] + 0.02 < centers[2]
        decreasing = centers[2] + 0.02 < centers[1] and centers[1] + 0.02 < centers[0]
        if not increasing and not decreasing:
            raise ContractError("anchors.top surfaces must keep a consistent physical order")


def _validate_json_correction(value: Any, label: str, *, depth: int) -> None:
    if depth > 4:
        raise ContractError(f"{label} is nested too deeply")
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str) and len(value) > 500:
            raise ContractError(f"{label} is too long")
        return
    if isinstance(value, (int, float)):
        if not (-1_000_000 <= float(value) <= 1_000_000):
            raise ContractError(f"{label} is outside the supported numeric range")
        return
    if isinstance(value, list):
        if len(value) > 32:
            raise ContractError(f"{label} has too many values")
        for index, item in enumerate(value):
            _validate_json_correction(item, f"{label}[{index}]", depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 32:
            raise ContractError(f"{label} has too many fields")
        for key, item in value.items():
            safe_key = str(key or "").strip()
            if not safe_key or len(safe_key) > 80:
                raise ContractError(f"{label} contains an invalid field")
            _validate_json_correction(item, f"{label}.{safe_key}", depth=depth + 1)
        return
    raise ContractError(f"{label} contains an unsupported value")
