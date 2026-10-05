"""Confidence-bearing, livery-agnostic car-space anchor proposals.

The proposer measures direct reference geometry only.  It never inspects a
filename, sponsor, color identity, or livery name.  Low-confidence geometry is
returned for review (or explicitly abstained) instead of being promoted into a
projector.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from .contracts import ContractError, confine_child
from .evidence import sha256_file


SCHEMA = "shokk-forge.anchor-proposals/v1"
FIELD_SCHEMA = "shokk-forge.anchor-field/v1"
AUTO_ACCEPT_THRESHOLD = 0.82
REVIEW_THRESHOLD = 0.45

ROLE_ANCHOR_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "left": ("rear_wheel_center", "front_wheel_center", "body_top_y", "rocker_y"),
    "right": ("rear_wheel_center", "front_wheel_center", "body_top_y", "rocker_y"),
    "top": ("hood_quad", "roof_quad", "rear_deck_quad"),
    "front": ("center_x", "half_width", "ground_y", "hood_seam_y"),
    "rear": ("rear_deck_quad", "spoiler_inside_quad", "spoiler_outside_quad"),
}


def _round_value(value: Any) -> Any:
    if isinstance(value, (float, np.floating)):
        return round(float(value), 6)
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_round_value(item) for item in value]
    return value


def _field(value: Any, confidence: float, provenance: str, *, forced_status: str | None = None, reason: str | None = None) -> dict[str, Any]:
    bounded = max(0.0, min(1.0, float(confidence)))
    if forced_status:
        status = forced_status
    elif value is None:
        status = "abstain"
    elif bounded >= AUTO_ACCEPT_THRESHOLD:
        status = "accepted"
    elif bounded >= REVIEW_THRESHOLD:
        status = "review"
    else:
        status = "abstain"
    payload = {
        "$schema": FIELD_SCHEMA,
        "value": _round_value(value),
        "confidence": round(bounded, 6),
        "status": status,
        "provenance": provenance,
    }
    if reason:
        payload["reason"] = reason
    return payload


def _load_reference(job_dir: Path, entry: dict[str, Any]) -> np.ndarray:
    path = confine_child(job_dir, job_dir / str(entry["stored_path"]))
    if not path.is_file() or sha256_file(path) != entry["sha256"]:
        raise ContractError(f"stored reference authority changed: {entry['id']}")
    try:
        with Image.open(path) as opened:
            opened.load()
            rgb = np.asarray(opened.convert("RGB"), dtype=np.uint8)
    except (OSError, UnidentifiedImageError) as exc:
        raise ContractError(f"stored reference is not a decodable image: {entry['id']}") from exc
    if rgb.shape[1] > 900:
        scale = 900.0 / rgb.shape[1]
        rgb = cv2.resize(rgb, (900, max(1, int(round(rgb.shape[0] * scale)))), interpolation=cv2.INTER_AREA)
    return rgb


def _foreground(rgb: np.ndarray) -> np.ndarray:
    height, width = rgb.shape[:2]
    border_width = max(2, min(height, width) // 80)
    border = np.concatenate(
        (
            rgb[:border_width].reshape(-1, 3),
            rgb[-border_width:].reshape(-1, 3),
            rgb[:, :border_width].reshape(-1, 3),
            rgb[:, -border_width:].reshape(-1, 3),
        )
    )
    background = np.median(border, axis=0)
    distance = np.linalg.norm(rgb.astype(np.float32) - background, axis=2)
    mask = (distance >= 18.0).astype(np.uint8)
    if int(mask.sum()) < max(64, int(mask.size * 0.002)):
        adaptive = min(18.0, max(4.0, float(np.percentile(distance, 99.0)) * 0.6))
        mask = (distance >= adaptive).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 5))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def _primary_object(rgb: np.ndarray, role: str) -> dict[str, Any]:
    mask = _foreground(rgb)
    height, width = mask.shape
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    candidates: list[tuple[float, int]] = []
    for index in range(1, count):
        x, y, box_width, box_height, area = [int(value) for value in stats[index]]
        if area < max(64, int(mask.size * 0.001)):
            continue
        width_fraction = box_width / width
        height_fraction = box_height / height
        if box_height < height * 0.16 or box_width < width * 0.25:
            continue
        aspect = box_width / max(1.0, box_height)
        role_shape = 1.0
        if role in {"left", "right", "top"}:
            role_shape = min(1.0, aspect / 1.7)
        elif role in {"front", "rear"}:
            role_shape = min(1.0, width_fraction / 0.45) * min(1.0, height_fraction / 0.35)
        center_x = (x + box_width / 2.0) / width
        centrality = max(0.0, 1.0 - abs(center_x - 0.5) * 1.4)
        score = area * (0.58 + 0.22 * role_shape + 0.12 * centrality + 0.08 * min(1.0, width_fraction / 0.65))
        candidates.append((score, index))
    if not candidates:
        raise ContractError(f"no dominant physical object found in {role} reference")
    candidates.sort(reverse=True)
    best_score, index = candidates[0]
    x, y, box_width, box_height, area = [int(value) for value in stats[index]]
    component = (labels == index).astype(np.uint8)
    dominance = 1.0 if len(candidates) == 1 else min(1.0, best_score / max(best_score, candidates[1][0] * 1.8))
    coverage = min(1.0, area / max(1.0, box_width * box_height * 0.42))
    confidence = 0.68 + 0.18 * dominance + 0.14 * coverage
    return {
        "bbox": [x, y, x + box_width, y + box_height],
        "bbox_normalized": [x / width, y / height, (x + box_width) / width, (y + box_height) / height],
        "mask": component,
        "confidence": min(0.99, confidence),
        "area": area,
    }


def _dedupe_circles(circles: list[tuple[float, float, float]], width: int) -> list[tuple[float, float, float]]:
    result: list[tuple[float, float, float]] = []
    for candidate in circles:
        if any(math.hypot(candidate[0] - prior[0], candidate[1] - prior[1]) < width * 0.035 for prior in result):
            continue
        result.append(candidate)
    return result


def _wheel_pair(gray: np.ndarray, primary_confidence: float) -> tuple[list[tuple[float, float, float]] | None, float, dict[str, float]]:
    height, width = gray.shape
    blurred = cv2.GaussianBlur(gray, (9, 9), 1.5)
    circles: list[tuple[float, float, float]] = []
    for threshold in (26, 30, 34):
        found = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=max(24.0, width * 0.15),
            param1=100,
            param2=threshold,
            minRadius=max(6, int(height * 0.13)),
            maxRadius=max(10, int(height * 0.36)),
        )
        if found is not None:
            circles.extend(tuple(float(value) for value in row) for row in found[0])
    circles = _dedupe_circles(sorted(circles, key=lambda row: row[2], reverse=True), width)
    left_candidates = [row for row in circles if 0.06 <= row[0] / width <= 0.46 and row[1] / height >= 0.42]
    right_candidates = [row for row in circles if 0.54 <= row[0] / width <= 0.94 and row[1] / height >= 0.42]
    best: tuple[float, tuple[float, float, float], tuple[float, float, float], dict[str, float]] | None = None
    for left in left_candidates:
        for right in right_candidates:
            separation = (right[0] - left[0]) / width
            if not 0.38 <= separation <= 0.74:
                continue
            position = 1.0 - min(1.0, (abs(left[0] / width - 0.22) + abs(right[0] / width - 0.76)) / 0.32)
            separation_score = 1.0 - min(1.0, abs(separation - 0.55) / 0.2)
            bottom_score = float(np.mean([
                1.0 - min(1.0, abs((circle[1] + circle[2]) / height - 0.96) / 0.28)
                for circle in (left, right)
            ]))
            vertical = 1.0 - min(1.0, abs(left[1] - right[1]) / (height * 0.32))
            radius = 1.0 - min(1.0, abs(left[2] - right[2]) / max(left[2], right[2], 1.0))
            score = 0.27 * position + 0.25 * separation_score + 0.23 * bottom_score + 0.13 * vertical + 0.07 * radius + 0.05 * primary_confidence
            details = {
                "position": position,
                "separation": separation_score,
                "ground_alignment": bottom_score,
                "vertical_alignment": vertical,
                "radius_similarity": radius,
            }
            if best is None or score > best[0]:
                best = (score, left, right, details)
    if best is None:
        return None, 0.0, {}
    confidence = max(0.0, min(0.96, 0.48 + 0.52 * best[0]))
    return [best[1], best[2]], confidence, best[3]


def _horizontal_anchor(gray: np.ndarray, low: float, high: float, prior: float) -> tuple[float, float]:
    height, width = gray.shape
    gradient = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    x0, x1 = int(width * 0.08), int(width * 0.92)
    row_energy = np.percentile(gradient[:, x0:x1], 70, axis=1)
    row_energy = cv2.GaussianBlur(row_energy.reshape(-1, 1), (1, 9), 0).reshape(-1)
    start, stop = max(0, int(height * low)), min(height, int(height * high))
    indices = np.arange(start, stop)
    distance_weight = np.exp(-0.5 * ((indices / height - prior) / 0.11) ** 2)
    local = row_energy[start:stop]
    weighted = local * (0.58 + 0.42 * distance_weight)
    chosen = int(indices[int(np.argmax(weighted))])
    median = float(np.median(local)) + 1e-6
    prominence = min(1.0, max(0.0, float(row_energy[chosen]) / median - 1.0) / 2.2)
    prior_agreement = max(0.0, 1.0 - abs(chosen / height - prior) / 0.2)
    confidence = min(0.93, 0.58 + 0.23 * prominence + 0.19 * prior_agreement)
    return float(chosen), confidence


def _side_proposal(rgb: np.ndarray, role: str, primary: dict[str, Any]) -> dict[str, Any]:
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = primary["bbox"]
    crop = rgb[y0:y1, x0:x1]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    pair, wheel_confidence, pair_scores = _wheel_pair(gray, primary["confidence"])
    fields: dict[str, Any] = {}
    reasons: list[str] = []
    measured_wheels: dict[str, Any] = {}
    if pair is None:
        for name in ("rear_wheel_center", "front_wheel_center"):
            fields[name] = _field(None, 0.0, "direct_profile_circle_consensus/v1", reason="two_wheel_consensus_failed")
        body_prior, rocker_prior = 0.48, 0.9
        reasons.append("two_wheel_consensus_failed")
    else:
        image_left, image_right = pair
        front, rear = (image_left, image_right) if role == "left" else (image_right, image_left)
        for name, circle in (("front_wheel_center", front), ("rear_wheel_center", rear)):
            center = [(x0 + circle[0]) / width, (y0 + circle[1]) / height]
            fields[name] = _field(
                center,
                wheel_confidence,
                f"direct_profile_circle_consensus/v1+dlm_{role}_view_direction",
            )
            measured_wheels[name] = {
                "center": _round_value(center),
                "radius_pixels": round(float(circle[2]), 3),
                "radius_normalized_x": round(float(circle[2]) / width, 6),
                "radius_normalized_y": round(float(circle[2]) / height, 6),
                "provenance": "direct_profile_circle_consensus/v1",
            }
        mean_y = float(np.mean([row[1] for row in pair]))
        mean_radius = float(np.mean([row[2] for row in pair]))
        body_prior = max(0.28, min(0.64, (mean_y - 0.65 * mean_radius) / gray.shape[0]))
        rocker_prior = max(0.72, min(0.97, (mean_y + 0.76 * mean_radius) / gray.shape[0]))
    body_y, body_confidence = _horizontal_anchor(gray, 0.25, 0.68, body_prior)
    rocker_y, rocker_confidence = _horizontal_anchor(gray, 0.7, 0.99, rocker_prior)
    fields["body_top_y"] = _field((y0 + body_y) / height, min(wheel_confidence or 0.55, body_confidence), "measured_profile_horizontal_edge/v1")
    fields["rocker_y"] = _field((y0 + rocker_y) / height, min(wheel_confidence or 0.55, rocker_confidence), "measured_profile_horizontal_edge/v1")
    required = ROLE_ANCHOR_REQUIREMENTS[role]
    statuses = [fields[name]["status"] for name in required]
    role_confidence = min(fields[name]["confidence"] for name in required)
    status = "accepted" if all(value == "accepted" for value in statuses) else ("review" if all(fields[name]["value"] is not None for name in required) else "abstain")
    return {
        "role": role,
        "status": status,
        "confidence": round(role_confidence, 6),
        "primary_object_bbox": _round_value(primary["bbox_normalized"]),
        "primary_object_confidence": round(primary["confidence"], 6),
        "fields": fields,
        "diagnostics": {
            "wheel_pair": {key: round(value, 6) for key, value in pair_scores.items()},
            "measured_wheels": measured_wheels,
        },
        "reasons": reasons,
    }


def _ordered_box(mask: np.ndarray, bbox: list[int]) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    ys, xs = np.nonzero(mask[y0:y1, x0:x1])
    points = np.column_stack((xs + x0, ys + y0)).astype(np.float32)
    rectangle = cv2.minAreaRect(points)
    box = cv2.boxPoints(rectangle)
    center = box.mean(axis=0)
    angles = np.arctan2(box[:, 1] - center[1], box[:, 0] - center[0])
    return box[np.argsort(angles)]


def _major_axis(box: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    edges = [float(np.linalg.norm(box[(index + 1) % 4] - box[index])) for index in range(4)]
    index = int(np.argmax(edges))
    a0, a1 = box[index], box[(index + 1) % 4]
    b0, b1 = box[(index - 1) % 4], box[(index + 2) % 4]
    if a0[0] > a1[0]:
        a0, a1, b0, b1 = a1, a0, b1, b0
    # minAreaRect does not promise which parallel edge is returned first.
    # Normalize the paired-edge contract so generated quads always start on
    # the screen-top edge and retain a non-reflecting cyclic winding.
    if float(a0[1] + a1[1]) > float(b0[1] + b1[1]):
        a0, a1, b0, b1 = b0, b1, a0, a1
    return a0, a1, b0, b1


def _segment_quad(axis: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], start: float, stop: float, width: int, height: int) -> list[list[float]]:
    a0, a1, b0, b1 = axis
    top_start = a0 + (a1 - a0) * start
    top_stop = a0 + (a1 - a0) * stop
    bottom_start = b0 + (b1 - b0) * start
    bottom_stop = b0 + (b1 - b0) * stop
    return [[point[0] / width, point[1] / height] for point in (top_start, top_stop, bottom_stop, bottom_start)]


def _isolated_top_panel_quads(rgb: np.ndarray, primary: dict[str, Any]) -> tuple[dict[str, list[list[float]]], dict[str, Any]] | None:
    """Find three clean panel components without relying on livery identity.

    Qualified Forge asset sheets commonly include hood/roof/deck orthographic
    panels next to the assembled top view.  The physical car remains the
    largest component; this detector considers only large, panel-shaped,
    non-overlapping components and assigns their sheet layout with an explicit
    review-only confidence contract.
    """
    foreground = _foreground(rgb)
    height, width = foreground.shape
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    primary_mask = primary["mask"].astype(bool)
    candidates: list[dict[str, Any]] = []
    for index in range(1, count):
        x, y, box_width, box_height, area = [int(value) for value in stats[index]]
        if area < max(96, int(foreground.size * 0.01)):
            continue
        aspect = box_width / max(1.0, box_height)
        if not (0.5 <= aspect <= 1.9):
            continue
        if box_width < width * 0.08 or box_height < height * 0.16:
            continue
        component = labels == index
        primary_overlap = float(np.logical_and(component, primary_mask).sum()) / max(1.0, float(component.sum()))
        if primary_overlap > 0.1:
            continue
        candidates.append(
            {
                "bbox": [x, y, x + box_width, y + box_height],
                "area": area,
                "aspect": round(aspect, 6),
                "center": [x + box_width / 2.0, y + box_height / 2.0],
                "fill": round(area / max(1.0, box_width * box_height), 6),
            }
        )
    if len(candidates) < 3:
        return None
    selected = sorted(candidates, key=lambda row: row["area"], reverse=True)[:3]
    centers_y = [float(row["center"][1]) for row in selected]
    if max(centers_y) - min(centers_y) <= height * 0.14:
        ordered = sorted(selected, key=lambda row: row["center"][0])
        layout = "single_row_left_to_right"
    else:
        rear = max(selected, key=lambda row: row["center"][1])
        upper = sorted((row for row in selected if row is not rear), key=lambda row: row["center"][0])
        if len(upper) != 2 or abs(float(upper[0]["center"][1]) - float(upper[1]["center"][1])) > height * 0.18:
            return None
        ordered = [upper[0], upper[1], rear]
        layout = "upper_pair_plus_lower_rear"
    names = ("hood_quad", "roof_quad", "rear_deck_quad")
    quads: dict[str, list[list[float]]] = {}
    for name, row in zip(names, ordered):
        x0, y0, x1, y1 = row["bbox"]
        quads[name] = [[x0 / width, y0 / height], [x1 / width, y0 / height], [x1 / width, y1 / height], [x0 / width, y1 / height]]
        row["assigned_anchor"] = name
    diagnostics = {
        "layout": layout,
        "candidate_count": len(candidates),
        "selected": selected,
        "contract": "largest_three_disjoint_panel_components+review/v1",
    }
    return quads, diagnostics


def _top_proposal(rgb: np.ndarray, primary: dict[str, Any]) -> dict[str, Any]:
    height, width = rgb.shape[:2]
    isolated = _isolated_top_panel_quads(rgb, primary)
    if isolated is not None:
        quads, diagnostics = isolated
        confidence = min(0.9, primary["confidence"] * 0.88)
        fields = {
            name: _field(
                value,
                confidence,
                "direct_isolated_panel_component+sheet_layout/v1",
                forced_status="review",
                reason="isolated_panel_assignment_requires_confirmation",
            )
            for name, value in quads.items()
        }
        return {
            "role": "top",
            "status": "review",
            "confidence": round(confidence, 6),
            "primary_object_bbox": _round_value(primary["bbox_normalized"]),
            "primary_object_confidence": round(primary["confidence"], 6),
            "fields": fields,
            "diagnostics": {"isolated_panel_detection": diagnostics},
            "reasons": ["isolated_top_panels_detected_and_require_confirmation"],
        }
    axis = _major_axis(_ordered_box(primary["mask"], primary["bbox"]))
    confidence = min(0.76, primary["confidence"] * 0.74)
    fields = {
        "hood_quad": _field(_segment_quad(axis, 0.02, 0.34, width, height), confidence, "measured_top_car_quad+dlm_topology_prior/v1", forced_status="review", reason="front_direction_requires_confirmation"),
        "roof_quad": _field(_segment_quad(axis, 0.38, 0.61, width, height), confidence, "measured_top_car_quad+dlm_topology_prior/v1", forced_status="review", reason="surface_boundary_requires_confirmation"),
        "rear_deck_quad": _field(_segment_quad(axis, 0.62, 0.9, width, height), confidence, "measured_top_car_quad+dlm_topology_prior/v1", forced_status="review", reason="front_direction_requires_confirmation"),
    }
    return {
        "role": "top",
        "status": "review",
        "confidence": round(confidence, 6),
        "primary_object_bbox": _round_value(primary["bbox_normalized"]),
        "primary_object_confidence": round(primary["confidence"], 6),
        "fields": fields,
        "reasons": ["top_reference_direction_and_surface_partitions_need_confirmation"],
    }


def _front_proposal(rgb: np.ndarray, primary: dict[str, Any]) -> dict[str, Any]:
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = primary["bbox"]
    crop_mask = primary["mask"][y0:y1, x0:x1]
    symmetry = float(np.logical_and(crop_mask, np.fliplr(crop_mask)).sum()) / max(1.0, float(np.logical_or(crop_mask, np.fliplr(crop_mask)).sum()))
    geometry_confidence = min(0.96, 0.67 + 0.19 * symmetry + 0.1 * primary["confidence"])
    gray = cv2.cvtColor(rgb[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
    # The hood/valance ownership seam is a lower-body edge.  Searching the
    # whole front object lets logo baselines win; constrain the measured
    # corridor to the lower 30% learned across active + controls + holdout.
    seam_y, seam_confidence = _horizontal_anchor(gray, 0.6, 0.9, 0.75)
    isolated_valance = _isolated_front_valance_quad(rgb, primary)
    valance_top_y, valance_top_confidence, valance_top_diagnostics = _front_valance_top_y(
        rgb,
        primary,
    )
    fields = {
        "center_x": _field(((x0 + x1) / 2.0) / width, geometry_confidence, "front_silhouette_symmetry/v1"),
        "half_width": _field(((x1 - x0) / 2.0) / width, geometry_confidence, "front_silhouette_extent/v1"),
        "ground_y": _field(y1 / height, geometry_confidence, "front_silhouette_ground_contact/v1"),
        "hood_seam_y": _field((y0 + seam_y) / height, min(0.79, seam_confidence), "front_horizontal_edge_corridor/v1", forced_status="review", reason="hood_valance_semantic_boundary_requires_confirmation"),
        "valance_top_y": _field(
            valance_top_y,
            valance_top_confidence,
            "front_lower_band_physical_v_prior+horizontal_edge/v1",
            forced_status="review",
            reason="partial_valance_boundary_requires_confirmation",
        ),
    }
    isolated_diagnostics = None
    if isolated_valance is not None:
        valance_quad, valance_confidence, isolated_diagnostics = isolated_valance
        fields["front_valance_quad"] = _field(
            valance_quad,
            valance_confidence,
            "direct_isolated_front_valance_component/v1",
            forced_status="review",
            reason="isolated_front_valance_assignment_requires_confirmation",
        )
    else:
        fields["front_valance_quad"] = _field(
            None,
            0.0,
            "direct_isolated_front_valance_component/v1",
            reason="no_unique_isolated_front_valance_component",
        )
    return {
        "role": "front",
        "status": "review",
        "confidence": round(min(field["confidence"] for field in fields.values()), 6),
        "primary_object_bbox": _round_value(primary["bbox_normalized"]),
        "primary_object_confidence": round(primary["confidence"], 6),
        "fields": fields,
        "diagnostics": {
            "silhouette_symmetry_iou": round(symmetry, 6),
            "front_valance_top": valance_top_diagnostics,
            "isolated_front_valance_detection": isolated_diagnostics,
        },
        "reasons": ["hood_seam_and_partial_valance_need_semantic_confirmation"],
    }


def _front_valance_top_y(
    rgb: np.ndarray,
    primary: dict[str, Any],
) -> tuple[float, float, dict[str, Any]]:
    """Measure the narrow physical lower-front band, independent of its livery.

    The normalization is the same two-half-width front space used by the DLM
    inverse projector.  A soft physical prior limits the search to the lower
    2.5-10% of the front width while direct horizontal edge energy chooses the
    actual boundary.  The result always remains review-only.
    """

    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = [int(value) for value in primary["bbox"]]
    full_width = max(1.0, float(x1 - x0))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gradient = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    ix0 = max(0, x0 + int(round(full_width * 0.08)))
    ix1 = min(width, x1 - int(round(full_width * 0.08)))
    candidates: list[tuple[float, int, float, float]] = []
    for physical_v in np.linspace(0.025, 0.10, 76):
        row = int(round(y1 - physical_v * full_width))
        if row <= y0 or row >= y1 or ix1 <= ix0:
            continue
        energy = float(np.percentile(gradient[row, ix0:ix1], 72))
        prior = math.exp(-0.5 * ((physical_v - 0.055) / 0.025) ** 2)
        candidates.append((physical_v, row, energy, prior))
    if not candidates:
        fallback = max(y0, y1 - int(round(full_width * 0.055))) / height
        return fallback, 0.45, {"reason": "front_lower_band_search_empty"}
    energies = np.asarray([row[2] for row in candidates], dtype=np.float32)
    low, high = float(np.percentile(energies, 10)), float(np.percentile(energies, 95))
    span = max(1e-6, high - low)
    ranked = [
        (0.45 * max(0.0, min(1.0, (energy - low) / span)) + 0.55 * prior, physical_v, row, energy, prior)
        for physical_v, row, energy, prior in candidates
    ]
    score, physical_v, row, energy, prior = max(ranked, key=lambda item: item[0])
    confidence = min(0.81, 0.58 + 0.14 * score + 0.07 * primary["confidence"])
    return row / height, confidence, {
        "physical_v": round(float(physical_v), 6),
        "selected_row": int(row),
        "edge_energy": round(float(energy), 6),
        "prior_agreement": round(float(prior), 6),
        "search_physical_v_range": [0.025, 0.1],
        "contract": "lower_front_band_edge+two_half_width_prior/v1",
    }


def _isolated_front_valance_quad(
    rgb: np.ndarray,
    primary: dict[str, Any],
) -> tuple[list[list[float]], float, dict[str, Any]] | None:
    """Find one isolated wide/shallow valance asset anywhere on a front sheet.

    Sheet layout is deliberately irrelevant.  The component must be disjoint
    from the assembled car, sufficiently filled, and uniquely win a purely
    geometric score.  Logos, titles and hood panels fail the aspect/height/
    fill combination; ambiguous sheets abstain.
    """

    height, width = rgb.shape[:2]
    foreground = _foreground(rgb)
    joined = cv2.morphologyEx(
        foreground,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (11, 5)),
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, 8)
    primary_mask = primary["mask"].astype(bool)
    candidates: list[dict[str, Any]] = []
    for index in range(1, count):
        x, y, box_width, box_height, area = [int(value) for value in stats[index]]
        width_fraction = box_width / width
        height_fraction = box_height / height
        aspect = box_width / max(1.0, box_height)
        if area < max(96, int(joined.size * 0.002)):
            continue
        if not 0.18 <= width_fraction <= 0.62 or not 0.02 <= height_fraction <= 0.15 or not 4.0 <= aspect <= 15.0:
            continue
        component = labels == index
        overlap = float(np.logical_and(component, primary_mask).sum()) / max(1.0, float(component.sum()))
        if overlap > 0.08:
            continue
        contours, _ = cv2.findContours(component.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        silhouette = np.zeros_like(foreground)
        if contours:
            cv2.drawContours(silhouette, contours, -1, 1, thickness=cv2.FILLED)
        fill = float(silhouette.sum()) / max(1.0, box_width * box_height)
        if fill < 0.35:
            continue
        aspect_score = max(0.0, 1.0 - abs(aspect - 8.0) / 10.0)
        score = 0.42 * aspect_score + 0.32 * min(1.0, fill / 0.75) + 0.26 * min(1.0, width_fraction / 0.38)
        candidates.append({
            "index": index,
            "score": score,
            "bbox": [x, y, x + box_width, y + box_height],
            "aspect": aspect,
            "width_fraction": width_fraction,
            "height_fraction": height_fraction,
            "silhouette_fill": fill,
            "primary_overlap": overlap,
        })
    if not candidates:
        return None
    ordered = sorted(candidates, key=lambda row: row["score"], reverse=True)
    if len(ordered) > 1 and ordered[0]["score"] - ordered[1]["score"] < 0.08:
        return None
    selected = ordered[0]
    x0, y0, x1, y1 = selected["bbox"]
    quad = [[x0 / width, y0 / height], [x1 / width, y0 / height], [x1 / width, y1 / height], [x0 / width, y1 / height]]
    confidence = min(0.91, 0.73 + 0.08 * min(1.0, selected["width_fraction"] / 0.38) + 0.06 * min(1.0, selected["silhouette_fill"] / 0.75) + 0.04 * primary["confidence"])
    diagnostics = {
        "candidate_count": len(candidates),
        "selected_bbox": selected["bbox"],
        "aspect": round(float(selected["aspect"]), 6),
        "width_fraction": round(float(selected["width_fraction"]), 6),
        "height_fraction": round(float(selected["height_fraction"]), 6),
        "silhouette_fill": round(float(selected["silhouette_fill"]), 6),
        "primary_overlap": round(float(selected["primary_overlap"]), 6),
        "contract": "unique_wide_shallow_disjoint_panel_component+review/v1",
    }
    return quad, confidence, diagnostics


def _isolated_spoiler_face_quad(
    rgb: np.ndarray,
    primary: dict[str, Any],
) -> tuple[list[list[float]], float, dict[str, Any]] | None:
    """Find a clean horizontal spoiler-face panel outside the assembled car.

    Qualified asset sheets often carry one isolated, bordered spoiler face.
    The rule is purely structural: a wide, shallow, panel-filled component
    that does not belong to the dominant assembled rear view.  Titles,
    underlines, side plates and rear-quarter panels fail the geometry gates.
    """
    height, width = rgb.shape[:2]
    foreground = _foreground(rgb)
    joined = cv2.morphologyEx(
        foreground,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (11, 5)),
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, 8)
    primary_mask = primary["mask"].astype(bool)
    candidates: list[dict[str, Any]] = []
    for index in range(1, count):
        x, y, box_width, box_height, area = [int(value) for value in stats[index]]
        width_fraction = box_width / width
        height_fraction = box_height / height
        aspect = box_width / max(1.0, box_height)
        if area < max(96, int(joined.size * 0.0025)):
            continue
        if width_fraction < 0.22 or not 0.025 <= height_fraction <= 0.16 or not 3.0 <= aspect <= 14.0:
            continue
        component = labels == index
        overlap = float(np.logical_and(component, primary_mask).sum()) / max(1.0, float(component.sum()))
        if overlap > 0.08:
            continue
        contours, _ = cv2.findContours(component.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        silhouette = np.zeros_like(foreground)
        if contours:
            cv2.drawContours(silhouette, contours, -1, 1, thickness=cv2.FILLED)
        silhouette_fill = float(silhouette.sum()) / max(1.0, box_width * box_height)
        if silhouette_fill < 0.42:
            continue
        primary_y0, primary_y1 = int(primary["bbox"][1]), int(primary["bbox"][3])
        vertical_gap = max(0, primary_y0 - (y + box_height), y - primary_y1) / height
        if vertical_gap > 0.12:
            continue
        rectangularity = min(1.0, silhouette_fill / 0.82)
        aspect_score = max(0.0, 1.0 - abs(aspect - 7.5) / 10.0)
        proximity = max(0.0, 1.0 - vertical_gap / 0.12)
        score = (
            0.34 * aspect_score
            + 0.3 * proximity
            + 0.22 * rectangularity
            + 0.14 * min(1.0, width_fraction / 0.4)
        )
        candidates.append(
            {
                "index": index,
                "score": score,
                "bbox": [x, y, x + box_width, y + box_height],
                "area": area,
                "aspect": aspect,
                "width_fraction": width_fraction,
                "height_fraction": height_fraction,
                "silhouette_fill": silhouette_fill,
                "primary_overlap": overlap,
                "vertical_gap": vertical_gap,
                "silhouette": silhouette,
            }
        )
    if not candidates:
        return None
    selected = max(candidates, key=lambda row: row["score"])
    original_bbox = list(selected["bbox"])
    sx0, sy0, sx1, sy1 = original_bbox
    original_crop = foreground[sy0:sy1, sx0:sx1]
    row_support = original_crop.mean(axis=1)
    dense_rows = row_support >= 0.2
    bands: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(np.r_[dense_rows, False]):
        if value and start is None:
            start = index
        elif not value and start is not None:
            bands.append((start, index))
            start = None
    if not bands:
        return None
    band_start, band_stop = max(
        bands,
        key=lambda row: (row[1] - row[0]) * float(row_support[row[0] : row[1]].mean()),
    )
    band = original_crop[band_start:band_stop]
    column_support = band.mean(axis=0)
    dense_columns = np.flatnonzero(column_support >= 0.08)
    if not dense_columns.size:
        return None
    rx0 = sx0 + int(dense_columns.min())
    rx1 = sx0 + int(dense_columns.max()) + 1
    ry0, ry1 = sy0 + band_start, sy0 + band_stop
    refined_mask = np.zeros_like(foreground)
    refined_mask[ry0:ry1, rx0:rx1] = foreground[ry0:ry1, rx0:rx1]
    refined_mask = cv2.morphologyEx(
        refined_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (7, 3)),
    )
    refined_bbox = [rx0, ry0, rx1, ry1]
    axis = _major_axis(_ordered_box(refined_mask, refined_bbox))
    quad = _segment_quad(axis, 0.0, 1.0, width, height)
    confidence = min(
        0.92,
        0.72
        + 0.09 * min(1.0, selected["width_fraction"] / 0.4)
        + 0.07 * min(1.0, selected["silhouette_fill"] / 0.82)
        + 0.04 * primary["confidence"],
    )
    diagnostics = {
        "candidate_count": len(candidates),
        "candidate_bbox": original_bbox,
        "selected_bbox": refined_bbox,
        "aspect": round(float(selected["aspect"]), 6),
        "width_fraction": round(float(selected["width_fraction"]), 6),
        "height_fraction": round(float(selected["height_fraction"]), 6),
        "silhouette_fill": round(float(selected["silhouette_fill"]), 6),
        "primary_overlap": round(float(selected["primary_overlap"]), 6),
        "primary_vertical_gap": round(float(selected["vertical_gap"]), 6),
        "page_label_rows_trimmed": int((ry0 - sy0) + (sy1 - ry1)),
        "contract": "wide_shallow_disjoint_panel_component+review/v1",
    }
    return quad, confidence, diagnostics


def _rear_proposal(rgb: np.ndarray, primary: dict[str, Any], top: dict[str, Any] | None) -> dict[str, Any]:
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = primary["bbox"]
    bar_height = max(2.0, (y1 - y0) * 0.2)
    outside = [[x0 / width, y0 / height], [x1 / width, y0 / height], [x1 / width, (y0 + bar_height) / height], [x0 / width, (y0 + bar_height) / height]]
    outside_confidence = min(0.78, primary["confidence"] * 0.77)
    outside_provenance = "rear_primary_upper_bar/v1"
    outside_reason = "spoiler_face_boundary_requires_confirmation"
    isolated = _isolated_spoiler_face_quad(rgb, primary)
    isolated_diagnostics = None
    if isolated is not None:
        outside, outside_confidence, isolated_diagnostics = isolated
        outside_provenance = "direct_isolated_spoiler_face_component/v1"
        outside_reason = "isolated_spoiler_face_assignment_requires_confirmation"
    deck_field = None if top is None else top["fields"]["rear_deck_quad"]["value"]
    deck_confidence = 0.0 if top is None else min(0.72, top["fields"]["rear_deck_quad"]["confidence"])
    fields = {
        "rear_deck_quad": _field(deck_field, deck_confidence, "direct_top_cross_view_rear_deck/v1", forced_status="review" if deck_field is not None else "abstain", reason="rear_deck_comes_from_top_view_and_requires_confirmation" if deck_field is not None else "top_view_missing"),
        "spoiler_outside_quad": _field(outside, outside_confidence, outside_provenance, forced_status="review", reason=outside_reason),
        "spoiler_inside_quad": _field(None, 0.0, "rear_visibility_contract/v1", reason="inside_face_not_directly_visible_from_rear"),
    }
    return {
        "role": "rear",
        "status": "abstain",
        "confidence": 0.0,
        "primary_object_bbox": _round_value(primary["bbox_normalized"]),
        "primary_object_confidence": round(primary["confidence"], 6),
        "fields": fields,
        "diagnostics": {"isolated_spoiler_face_detection": isolated_diagnostics},
        "reasons": ["spoiler_inside_requires_direct_inside_evidence"],
    }


def propose_anchors(job_dir: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic proposals keyed by physical view role."""

    by_role = {str(entry.get("role")): entry for entry in entries if not entry.get("duplicate_of")}
    images: dict[str, np.ndarray] = {}
    primary: dict[str, dict[str, Any]] = {}
    for role in ROLE_ANCHOR_REQUIREMENTS:
        entry = by_role.get(role)
        if entry is None:
            continue
        images[role] = _load_reference(job_dir, entry)
        primary[role] = _primary_object(images[role], role)
    proposals: dict[str, Any] = {}
    for role in ("left", "right"):
        if role in images:
            proposals[role] = _side_proposal(images[role], role, primary[role])
    if "top" in images:
        proposals["top"] = _top_proposal(images["top"], primary["top"])
    if "front" in images:
        proposals["front"] = _front_proposal(images["front"], primary["front"])
    if "rear" in images:
        proposals["rear"] = _rear_proposal(images["rear"], primary["rear"], proposals.get("top"))
    accepted_roles = sorted(role for role, proposal in proposals.items() if proposal["status"] == "accepted")
    review_roles = sorted(role for role, proposal in proposals.items() if proposal["status"] == "review")
    abstained_roles = sorted(role for role, proposal in proposals.items() if proposal["status"] == "abstain")
    return {
        "$schema": SCHEMA,
        "coordinate_space": "normalized_source_image_xy",
        "auto_accept_threshold": AUTO_ACCEPT_THRESHOLD,
        "review_threshold": REVIEW_THRESHOLD,
        "roles": proposals,
        "summary": {
            "role_count": len(proposals),
            "accepted_roles": accepted_roles,
            "review_roles": review_roles,
            "abstained_roles": abstained_roles,
            "accepted_role_count": len(accepted_roles),
            "review_role_count": len(review_roles),
            "abstained_role_count": len(abstained_roles),
        },
    }


def accepted_anchor_values(proposals: dict[str, Any], role: str) -> dict[str, Any]:
    proposal = (proposals.get("roles") or {}).get(role) or {}
    fields = proposal.get("fields") or {}
    required = ROLE_ANCHOR_REQUIREMENTS[role]
    return {
        name: fields[name]["value"]
        for name in required
        if (fields.get(name) or {}).get("status") == "accepted" and fields[name].get("value") is not None
    }
