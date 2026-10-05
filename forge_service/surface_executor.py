"""Authority-bound execution of adapter-approved Forge UV surfaces.

This module knows DLM projector math, never livery identity.  It emits only
pixels supported by a direct source, confirmed/accepted anchors, and a hashed
official surface mask.  Unsupported projectors abstain instead of falling back
to affine presentation-sheet stretching.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from .contracts import confine_child
from .evidence import sha256_file


SCHEMA = "shokk-forge.surface-execution/v1"


def _mask_path(adapter_path: Path, surface: dict[str, Any]) -> Path:
    raw = Path(str(surface.get("mask_path") or ""))
    if not raw.as_posix():
        raise ValueError("adapter surface has no executable mask_path")
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (adapter_path.parent / raw).resolve()
        confine_child(adapter_path.parent, candidate)
    if not candidate.is_file():
        raise ValueError("adapter surface mask is missing")
    expected = str(surface.get("mask_sha256") or "").lower()
    actual = sha256_file(candidate)
    if not expected or actual != expected:
        raise ValueError("adapter surface mask hash does not match authority")
    return candidate


def _source_entry(inputs: list[dict[str, Any]], role: str) -> dict[str, Any]:
    matches = [row for row in inputs if row.get("role") == role and not row.get("duplicate_of")]
    if len(matches) != 1:
        raise ValueError(f"{role} requires exactly one unique direct source")
    return matches[0]


def _border_white(rgb: np.ndarray) -> np.ndarray:
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    white = ((rgb.mean(axis=2) >= 226.0) & (spread <= 18)).astype(np.uint8)
    count, labels = cv2.connectedComponents(white, connectivity=8)
    if count <= 1:
        return np.zeros(white.shape, dtype=bool)
    border = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    return np.isin(labels, border[border != 0])


def _source_valid_mask(
    rgb: np.ndarray,
    proposal: dict[str, Any],
    anchors: dict[str, Any],
) -> tuple[np.ndarray, dict[str, float]]:
    height, width = rgb.shape[:2]
    bbox = proposal.get("primary_object_bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError("source proposal lacks a physical-car bbox")
    x0, y0, x1, y1 = [float(value) for value in bbox]
    valid = np.zeros((height, width), dtype=bool)
    valid[max(0, int(y0 * height)) : min(height, int(np.ceil(y1 * height))), max(0, int(x0 * width)) : min(width, int(np.ceil(x1 * width)))] = True
    valid &= ~_border_white(rgb)
    yy, xx = np.ogrid[:height, :width]
    measured = (proposal.get("diagnostics") or {}).get("measured_wheels") or {}
    radii: dict[str, float] = {}
    rocker_y = float(anchors["rocker_y"]) * height
    for name in ("front_wheel_center", "rear_wheel_center"):
        center = anchors[name]
        cx, cy = float(center[0]) * width, float(center[1]) * height
        direct = (measured.get(name) or {}).get("radius_pixels")
        radius = float(direct) if direct is not None else max(4.0, abs(rocker_y - cy) * 0.88)
        radii[name] = radius
        valid &= (xx - cx) ** 2 + (yy - cy) ** 2 > (radius * 1.1) ** 2
    return valid, radii


def _profile_transform(
    anchors: dict[str, Any],
    source_size: tuple[int, int],
    surface: dict[str, Any],
) -> np.ndarray:
    width, height = source_size
    front = anchors["front_wheel_center"]
    rear = anchors["rear_wheel_center"]
    fx, fy = float(front[0]) * width, float(front[1]) * height
    rx, ry = float(rear[0]) * width, float(rear[1]) * height
    signed_wheelbase = fx - rx
    wheelbase = abs(signed_wheelbase)
    if wheelbase < 8.0:
        raise ValueError("side anchors produce an invalid wheelbase")
    rocker = float(anchors["rocker_y"]) * height
    extent = surface.get("car_space_extent")
    if not isinstance(extent, dict):
        raise ValueError("inverse-ready wheelbase surface lacks car_space_extent")
    x_min, x_max = float(extent["x_min"]), float(extent["x_max"])
    y_bottom, y_top = float(extent["y_bottom"]), float(extent["y_top"])
    x_span, y_span = x_max - x_min, y_top - y_bottom
    if x_span <= 0.0 or y_span <= 0.0:
        raise ValueError("adapter car-space extent is invalid")
    bx0, by0, bx1, by1 = (float(value) for value in surface["bbox"])
    uv_width, uv_height = bx1 - bx0, by1 - by0
    pixel_to_car = np.array(
        [[1.0 / signed_wheelbase, 0.0, -rx / signed_wheelbase], [0.0, -1.0 / wheelbase, rocker / wheelbase], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    if signed_wheelbase < 0.0:
        car_to_uv = np.array([[-uv_width / x_span, 0.0, bx0 + uv_width * x_max / x_span], [0.0, -uv_height / y_span, by0 + uv_height * y_top / y_span], [0.0, 0.0, 1.0]])
    else:
        car_to_uv = np.array([[uv_width / x_span, 0.0, bx0 - uv_width * x_min / x_span], [0.0, -uv_height / y_span, by0 + uv_height * y_top / y_span], [0.0, 0.0, 1.0]])
    transform = car_to_uv @ pixel_to_car
    rotation = int(surface.get("upright_rotation_deg") or 0)
    if rotation == 180:
        transform = np.array([[-1.0, 0.0, bx0 + bx1], [0.0, -1.0, by0 + by1], [0.0, 0.0, 1.0]]) @ transform
    elif rotation != 0:
        raise ValueError("wheelbase executor supports stored rotations 0/180 only")
    return transform


def _quad_transform(
    anchors: dict[str, Any],
    source_size: tuple[int, int],
    surface: dict[str, Any],
    source_anchor: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Map a directly observed, cyclic source quad into stored UV orientation."""
    width, height = source_size
    raw = anchors.get(source_anchor)
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError(f"direct surface requires a four-corner {source_anchor}")
    source_quad = np.asarray(
        [[float(point[0]) * width, float(point[1]) * height] for point in raw],
        dtype=np.float32,
    )
    if not np.isfinite(source_quad).all():
        raise ValueError("direct surface quad contains a non-finite coordinate")
    if (source_quad[:, 0] < 0).any() or (source_quad[:, 0] >= width).any() or (source_quad[:, 1] < 0).any() or (source_quad[:, 1] >= height).any():
        raise ValueError("direct surface quad escapes its source")
    contour = source_quad.reshape((-1, 1, 2))
    if not cv2.isContourConvex(contour) or abs(float(cv2.contourArea(contour, oriented=True))) < 64.0:
        raise ValueError("direct surface quad is degenerate or non-convex")
    x0, y0, x1, y1 = (float(value) for value in surface["bbox"])
    corners = np.asarray(
        [[x0, y0], [x1 - 1.0, y0], [x1 - 1.0, y1 - 1.0], [x0, y1 - 1.0]],
        dtype=np.float32,
    )
    rotation = int(surface.get("upright_rotation_deg") or 0) % 360
    corner_orders = {
        0: (0, 1, 2, 3),
        90: (3, 0, 1, 2),
        180: (2, 3, 0, 1),
        270: (1, 2, 3, 0),
    }
    if rotation not in corner_orders:
        raise ValueError("quad executor supports stored rotations 0/90/180/270 only")
    destination = corners[list(corner_orders[rotation])]
    source_sign = np.sign(cv2.contourArea(source_quad.reshape((-1, 1, 2)), oriented=True))
    destination_sign = np.sign(cv2.contourArea(destination.reshape((-1, 1, 2)), oriented=True))
    if source_sign == 0 or destination_sign == 0 or source_sign != destination_sign:
        raise ValueError("direct surface corner order would reflect readable artwork")
    return cv2.getPerspectiveTransform(source_quad, destination), source_quad


def _quad_source_confidence(
    rgb: np.ndarray,
    source_quad: np.ndarray,
    *,
    isolated_component: bool,
    preserve_quad_interior: bool = False,
) -> tuple[np.ndarray, dict[str, Any], np.ndarray]:
    """Reject presentation background and soften confidence toward evidence edges."""
    height, width = rgb.shape[:2]
    polygon = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(polygon, np.rint(source_quad).astype(np.int32), 1)
    diagnostics: dict[str, Any] = {"support_mode": "confirmed_quad_nonstudio"}
    effective_quad = source_quad.copy()
    if isolated_component and preserve_quad_interior:
        valid = polygon.astype(bool)
        diagnostics = {
            "support_mode": "isolated_panel_quad_interior",
            "white_paint_preservation": "explicit_confirmed_quad_interior",
            "effective_component_quad_pixels": np.round(effective_quad, 3).tolist(),
        }
    elif isolated_component:
        x0 = max(0, int(np.floor(source_quad[:, 0].min())))
        y0 = max(0, int(np.floor(source_quad[:, 1].min())))
        x1 = min(width, int(np.ceil(source_quad[:, 0].max())) + 1)
        y1 = min(height, int(np.ceil(source_quad[:, 1].max())) + 1)
        crop = rgb[y0:y1, x0:x1]
        border_width = max(2, min(height, width) // 80)
        border_pixels = np.concatenate(
            (
                rgb[:border_width].reshape(-1, 3),
                rgb[-border_width:].reshape(-1, 3),
                rgb[:, :border_width].reshape(-1, 3),
                rgb[:, -border_width:].reshape(-1, 3),
            )
        )
        background = np.median(border_pixels, axis=0)
        distance = np.linalg.norm(crop.astype(np.float32) - background.astype(np.float32), axis=2)
        local = (distance >= 18.0).astype(np.uint8)
        local &= polygon[y0:y1, x0:x1]
        local = cv2.morphologyEx(local, cv2.MORPH_CLOSE, np.ones((5, 5), dtype=np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(local, 8)
        if count <= 1:
            raise ValueError("isolated top panel has no supported component")
        index = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        border_frame_rejected = False
        sx, sy, sw, sh, _ = [int(value) for value in stats[index]]
        if sx == 0 and sy == 0 and sw == local.shape[1] and sh == local.shape[0]:
            # Some presentation sheets draw a thin rectangular preview frame
            # around the real panel.  A frame touching every crop edge is not
            # physical artwork; remove only that outer band and resolve again.
            margin = max(2, int(round(min(local.shape) * 0.035)))
            inset = local.copy()
            inset[:margin] = 0
            inset[-margin:] = 0
            inset[:, :margin] = 0
            inset[:, -margin:] = 0
            inset_count, inset_labels, inset_stats, _ = cv2.connectedComponentsWithStats(inset, 8)
            if inset_count > 1:
                labels, stats, count = inset_labels, inset_stats, inset_count
                index = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
                border_frame_rejected = True
        component = (labels == index).astype(np.uint8)
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        silhouette = np.zeros_like(component)
        if contours:
            cv2.drawContours(silhouette, contours, -1, 1, thickness=cv2.FILLED)
        component = silhouette.astype(bool)
        component_y, component_x = np.where(component)
        effective_quad = np.asarray(
            [
                [x0 + component_x.min(), y0 + component_y.min()],
                [x0 + component_x.max(), y0 + component_y.min()],
                [x0 + component_x.max(), y0 + component_y.max()],
                [x0 + component_x.min(), y0 + component_y.max()],
            ],
            dtype=np.float32,
        )
        valid = np.zeros((height, width), dtype=bool)
        valid[y0:y1, x0:x1] = component
        diagnostics = {
            "support_mode": "isolated_largest_component",
            "component_count": int(count - 1),
            "selected_component_pixels": int(component.sum()),
            "selected_component_fraction": round(float(component.sum()) / max(1, int(local.sum())), 6),
            "white_paint_preservation": "external_contour_hole_fill",
            "presentation_frame_rejected": border_frame_rejected,
            "effective_component_quad_pixels": np.round(effective_quad, 3).tolist(),
        }
    else:
        valid = polygon.astype(bool) & ~_border_white(rgb)
    if not valid.any():
        raise ValueError("direct surface quad contains no supported evidence")
    distance = cv2.distanceTransform(valid.astype(np.uint8), cv2.DIST_L2, 5)
    scale = max(4.0, np.sqrt(float(valid.sum())) * 0.12)
    interior = np.clip(distance / scale, 0.0, 1.0)
    return valid.astype(np.float32) * (0.18 + 0.82 * np.sqrt(interior)), diagnostics, effective_quad


def _guide_mask(adapter: dict[str, Any], key: str, canvas_size: tuple[int, int]) -> np.ndarray:
    guide = (adapter.get("guides") or {}).get(key) or {}
    path = Path(str(guide.get("source_path") or "")).resolve()
    if not path.is_file() or sha256_file(path) != str(guide.get("source_sha256") or "").lower():
        raise ValueError(f"adapter {key} guide authority is missing or stale")
    with Image.open(path) as opened:
        alpha = np.asarray(opened.convert("RGBA"), dtype=np.uint8)[:, :, 3]
    width, height = canvas_size
    if alpha.shape != (height, width):
        alpha = cv2.resize(alpha, (width, height), interpolation=cv2.INTER_NEAREST)
    return alpha > 0


def _front_scanline_map(
    u: np.ndarray,
    v: np.ndarray,
    bbox: tuple[int, int, int, int],
    surface_v_range: tuple[float, float],
    allowed_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map upright front samples through each official stored-UV scanline."""

    x0, y0, x1, y1 = bbox
    v0, v1 = surface_v_range
    if x1 <= x0 or y1 <= y0 or v1 <= v0:
        raise ValueError("front valance has an invalid UV extent")
    py = np.rint(y0 + ((1.0 - u) * 0.5) * (y1 - y0 - 1)).astype(int)
    fraction = np.clip((v - v0) / (v1 - v0), 0.0, 1.0)
    px = np.full(len(py), -1, dtype=int)
    snap = np.full(len(py), np.inf, dtype=np.float32)
    for row in np.unique(py):
        indexes = np.where(py == row)[0]
        if row < 0 or row >= allowed_mask.shape[0]:
            continue
        allowed = np.where(allowed_mask[row, x0:x1])[0]
        if not len(allowed):
            continue
        absolute = x0 + allowed
        left, right = int(absolute.min()) + 1, int(absolute.max()) - 1
        if right < left:
            left = right = int(np.median(absolute))
        desired = np.rint(right - fraction[indexes] * (right - left)).astype(int)
        positions = np.searchsorted(absolute, desired)
        upper = absolute[np.clip(positions, 0, len(absolute) - 1)]
        lower = absolute[np.clip(positions - 1, 0, len(absolute) - 1)]
        chosen = np.where(np.abs(desired - lower) <= np.abs(upper - desired), lower, upper)
        px[indexes] = chosen
        snap[indexes] = np.abs(chosen - desired)
    return px, py, snap


def _front_valance_pixels(
    *,
    rgb: np.ndarray,
    anchors: dict[str, Any],
    source_anchor: str,
    surface: dict[str, Any],
    surface_mask: np.ndarray,
    mandatory_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any], np.ndarray, dict[str, Any]]:
    """Project only one qualified isolated valance into the stored DLM nose."""

    height, width = rgb.shape[:2]
    # Reuse the cyclic-quad/reflection contract, then parameterize its interior
    # in physical front space instead of affine-stretching it across the nose.
    _, source_quad = _quad_transform(anchors, (width, height), surface, source_anchor)
    confidence, support, _ = _quad_source_confidence(
        rgb,
        source_quad,
        isolated_component=True,
        preserve_quad_interior=True,
    )
    canonical = np.asarray([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=np.float32)
    source_to_physical = cv2.getPerspectiveTransform(source_quad, canonical)
    yy, xx = np.where(confidence > 0)
    points = np.column_stack((xx, yy)).astype(np.float32).reshape((-1, 1, 2))
    local = cv2.perspectiveTransform(points, source_to_physical).reshape((-1, 2))
    in_quad = (local[:, 0] >= -0.001) & (local[:, 0] <= 1.001) & (local[:, 1] >= -0.001) & (local[:, 1] <= 1.001)
    xx, yy, local = xx[in_quad], yy[in_quad], np.clip(local[in_quad], 0.0, 1.0)
    source_weights = confidence[yy, xx].astype(np.float64)
    center_x = float(anchors["center_x"])
    half_width = float(anchors["half_width"])
    ground_y = float(anchors["ground_y"])
    valance_top_y = float(anchors["valance_top_y"])
    if half_width <= 0 or not valance_top_y < ground_y:
        raise ValueError("front valance physical landmarks are invalid")
    physical_v_top = (ground_y - valance_top_y) * height / (2.0 * half_width * width)
    surface_range_raw = surface.get("surface_v_range") or [0.0, 0.4]
    surface_v_range = (float(surface_range_raw[0]), float(surface_range_raw[1]))
    if not surface_v_range[0] < physical_v_top <= surface_v_range[1]:
        raise ValueError("front valance physical height escapes the qualified partial-nose range")
    u = -1.0 + 2.0 * local[:, 0]
    v = physical_v_top * (1.0 - local[:, 1])
    bbox = tuple(int(value) for value in surface["bbox"])

    pre_x, pre_y, _ = _front_scanline_map(u, v, bbox, surface_v_range, surface_mask)
    pre_valid = (pre_x >= 0) & (pre_y >= 0) & (pre_x < surface_mask.shape[1]) & (pre_y < surface_mask.shape[0])
    mandatory_before = int(np.count_nonzero(pre_valid & mandatory_mask[np.clip(pre_y, 0, mandatory_mask.shape[0] - 1), np.clip(pre_x, 0, mandatory_mask.shape[1] - 1)]))

    allowed_mask = surface_mask & ~mandatory_mask
    px, py, snap = _front_scanline_map(u, v, bbox, surface_v_range, allowed_mask)
    valid = (px >= 0) & (py >= 0) & (px < allowed_mask.shape[1]) & (py < allowed_mask.shape[0])
    valid &= allowed_mask[np.clip(py, 0, allowed_mask.shape[0] - 1), np.clip(px, 0, allowed_mask.shape[1] - 1)]
    if not valid.any():
        raise ValueError("qualified front valance produced no owned UV pixels")
    flat = py[valid] * allowed_mask.shape[1] + px[valid]
    unique, inverse = np.unique(flat, return_inverse=True)
    colors = rgb[yy[valid], xx[valid]].astype(np.float64)
    weights = source_weights[valid]
    color_sums = np.zeros((len(unique), 3), dtype=np.float64)
    weight_sums = np.zeros(len(unique), dtype=np.float64)
    np.add.at(color_sums, inverse, colors * weights[:, None])
    np.add.at(weight_sums, inverse, weights)
    averaged = np.clip(np.rint(color_sums / np.maximum(weight_sums[:, None], 1e-9)), 0, 255).astype(np.uint8)
    out_y, out_x = unique // allowed_mask.shape[1], unique % allowed_mask.shape[1]
    observed = np.zeros_like(allowed_mask, dtype=bool)
    observed[out_y, out_x] = True
    uv_rgb = np.zeros((*allowed_mask.shape, 3), dtype=np.uint8)
    uv_rgb[out_y, out_x] = averaged
    uv_confidence = np.zeros(allowed_mask.shape, dtype=np.float32)
    uv_confidence[out_y, out_x] = np.clip(weight_sums / np.maximum(1.0, np.bincount(inverse, minlength=len(unique))), 0.0, 1.0)
    finite_snap = snap[valid & np.isfinite(snap)]
    diagnostics = {
        "projection_mode": "official_mask_scanline_piecewise",
        "qualified_scope": surface.get("qualified_scope", "front_valance_only"),
        "full_surface_inverse_ready": False,
        "physical_u_range": [-1.0, 1.0],
        "physical_v_range": [0.0, round(float(physical_v_top), 9)],
        "surface_v_range": list(surface_v_range),
        "mandatory_contamination_before_exclusion": mandatory_before,
        "mandatory_contamination_after_exclusion": int(np.count_nonzero(observed & mandatory_mask)),
        "mask_snap_mean_px": round(float(finite_snap.mean()), 6) if finite_snap.size else 0.0,
        "mask_snap_max_px": round(float(finite_snap.max()), 6) if finite_snap.size else 0.0,
        "stored_direction": "front-left -> UV-bottom; front-right -> UV-top; ground -> UV-right",
        "source_to_physical_homography": (source_to_physical / source_to_physical[2, 2]).round(9).tolist(),
    }
    support.update({
        "support_mode": "isolated_front_valance_quad_interior",
        "source_support_excludes": surface.get("source_support_excludes") or [],
    })
    return uv_rgb, observed, observed.copy(), uv_confidence, diagnostics, source_quad, support


def _execute_one(
    *,
    job_dir: Path,
    adapter_path: Path,
    adapter: dict[str, Any],
    inputs: list[dict[str, Any]],
    proposal: dict[str, Any],
    anchors: dict[str, Any],
    plan: dict[str, Any],
    authority: str,
) -> tuple[dict[str, Any], np.ndarray]:
    surface_name = str(plan["surface"])
    base_surface = adapter["surfaces"][surface_name]
    surface = {**base_surface, **(plan.get("qualified_projector_config") or {})}
    projector = str(plan.get("projector") or "")
    if projector not in {"wheelbase_profile", "direct_top_quad", "direct_quad", "front_valance_scanline"}:
        raise ValueError(f"projector is not implemented by local executor: {projector}")
    entry = _source_entry(inputs, str(plan["role"]))
    source = confine_child(job_dir, job_dir / entry["stored_path"])
    if sha256_file(source) != entry["sha256"]:
        raise ValueError("direct source hash changed before surface execution")
    rgb = np.asarray(Image.open(source).convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    radii: dict[str, float] = {}
    source_quad: np.ndarray | None = None
    source_anchor: str | None = None
    source_support: dict[str, Any] = {}
    front_diagnostics: dict[str, Any] | None = None
    transform: np.ndarray | None = None
    canvas_width, canvas_height = (int(value) for value in adapter["canvas"])
    mask_path = _mask_path(adapter_path, base_surface)
    mask = np.asarray(Image.open(mask_path).convert("L"), dtype=np.uint8) > 0
    if mask.shape != (canvas_height, canvas_width):
        raise ValueError("adapter surface mask size does not match canvas")
    if projector == "front_valance_scanline":
        source_anchor = str(plan.get("source_anchor") or surface.get("source_anchor") or "")
        if not source_anchor:
            raise ValueError("front valance projector lacks an adapter-declared source_anchor")
        mandatory = _guide_mask(adapter, "mandatory", (canvas_width, canvas_height))
        uv_rgb, observed, projected, uv_confidence, front_diagnostics, source_quad, source_support = _front_valance_pixels(
            rgb=rgb,
            anchors=anchors,
            source_anchor=source_anchor,
            surface=surface,
            surface_mask=mask,
            mandatory_mask=mandatory,
        )
        outside = np.zeros_like(observed)
    elif projector == "wheelbase_profile":
        valid, radii = _source_valid_mask(rgb, proposal, anchors)
        transform = _profile_transform(anchors, (width, height), surface)
        extent = surface["car_space_extent"]
        front, rear = anchors["front_wheel_center"], anchors["rear_wheel_center"]
        fx, rx = float(front[0]) * width, float(rear[0]) * width
        signed_wheelbase = fx - rx
        wheelbase = abs(signed_wheelbase)
        yy, xx = np.mgrid[:height, :width]
        car_x = (xx.astype(np.float32) - rx) / signed_wheelbase
        car_y = (float(anchors["rocker_y"]) * height - yy.astype(np.float32)) / wheelbase
        dx = np.minimum((car_x - float(extent["x_min"])) / (float(extent["x_max"]) - float(extent["x_min"])), (float(extent["x_max"]) - car_x) / (float(extent["x_max"]) - float(extent["x_min"])))
        dy = np.minimum((car_y - float(extent["y_bottom"])) / (float(extent["y_top"]) - float(extent["y_bottom"])), (float(extent["y_top"]) - car_y) / (float(extent["y_top"]) - float(extent["y_bottom"])))
        interior = np.clip(4.0 * np.minimum(dx, dy), 0.0, 1.0)
        source_confidence = valid.astype(np.float32) * (0.18 + 0.82 * np.sqrt(interior))
    else:
        source_anchor = str(plan.get("source_anchor") or surface.get("source_anchor") or "")
        if not source_anchor:
            raise ValueError("direct quad projector lacks an adapter-declared source_anchor")
        transform, source_quad = _quad_transform(anchors, (width, height), surface, source_anchor)
        proposal_field = ((proposal.get("fields") or {}).get(source_anchor) or {})
        provenance = str(proposal_field.get("provenance") or "")
        isolated_component = provenance.startswith("direct_isolated_")
        preserve_quad_interior = provenance.startswith("direct_isolated_spoiler_face_component/")
        source_confidence, source_support, effective_quad = _quad_source_confidence(
            rgb,
            source_quad,
            isolated_component=isolated_component,
            preserve_quad_interior=preserve_quad_interior,
        )
        if isolated_component:
            normalized_quad = [
                [float(point[0]) / width, float(point[1]) / height]
                for point in effective_quad
            ]
            transform, source_quad = _quad_transform(
                {source_anchor: normalized_quad},
                (width, height),
                surface,
                source_anchor,
            )
    if projector != "front_valance_scanline":
        if transform is None:
            raise ValueError("surface executor did not produce a source-to-UV transform")
        weighted = rgb.astype(np.float32) * source_confidence[:, :, None]
        uv_weighted = cv2.warpPerspective(weighted, transform, (canvas_width, canvas_height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
        uv_confidence = cv2.warpPerspective(source_confidence, transform, (canvas_width, canvas_height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
        projected = uv_confidence >= 0.04
        observed = projected & mask
        outside = projected & ~mask
        if not observed.any():
            raise ValueError("direct evidence produced no owned UV pixels")
        uv_rgb = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
        uv_rgb[observed] = np.clip(np.rint(uv_weighted[observed] / uv_confidence[observed, None]), 0, 255).astype(np.uint8)
    rgba = np.dstack((uv_rgb, observed.astype(np.uint8) * 255))
    target = confine_child(job_dir, job_dir / "artifacts" / "surfaces" / authority / f"{surface_name}.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(target, optimize=True)
    relative = target.relative_to(job_dir).as_posix()
    satisfies_full_surface = bool(
        surface.get("satisfies_full_surface", surface.get("full_surface_inverse_ready", True))
    )
    record = {
        "surface": surface_name,
        "role": plan["role"],
        "family": plan.get("family"),
        "status": "complete",
        "surface_completion": "complete" if satisfies_full_surface else "partial",
        "satisfies_full_surface": satisfies_full_surface,
        "projector": projector,
        "source_reference_id": entry["id"],
        "source_sha256": entry["sha256"],
        "layer_path": relative,
        "layer_sha256": sha256_file(target),
        "mask_path": str(mask_path),
        "mask_sha256": base_surface["mask_sha256"],
        "mask_pixels": int(mask.sum()),
        "projected_pixels_before_clip": int(projected.sum()),
        "owned_uv_pixels": int(observed.sum()),
        "outside_surface_pixels_before_clip": int(outside.sum()),
        "containment": 1.0,
        "preclip_mask_retention": round(float(observed.sum()) / max(1, int(projected.sum())), 6),
        "owned_mask_coverage": round(float(observed.sum()) / max(1, int(mask.sum())), 6),
        "mean_confidence": round(float(uv_confidence[observed].mean()), 6),
        "measured_wheel_radii_px": {key: round(value, 3) for key, value in radii.items()},
        "reflection_used": False,
        "physical_instance_id": f"{entry['id']}:{surface.get('qualified_scope') or surface_name}",
    }
    if not satisfies_full_surface:
        record["completed_scope"] = surface.get("qualified_scope")
        record["remaining_scope"] = surface.get("remaining_scope")
        record["coverage_contract"] = surface.get("coverage_contract") or "partial_surface/v1"
    if transform is not None:
        record["source_to_uv_homography"] = (transform / transform[2, 2]).round(9).tolist()
    if projector == "wheelbase_profile":
        record["profile_to_uv_homography"] = record["source_to_uv_homography"]
    else:
        record["source_anchor"] = source_anchor
        record["source_quad_pixels"] = np.round(source_quad, 3).tolist()
        record["stored_rotation_deg"] = int(surface.get("upright_rotation_deg") or 0) % 360
        record["source_domain"] = surface.get("source_domain") or (
            "direct_top_orthographic_panel_quad" if projector == "direct_top_quad" else "direct_confirmed_surface_quad"
        )
        record["source_support"] = source_support
    if front_diagnostics is not None:
        record.update(front_diagnostics)
        record["source_anchor"] = source_anchor
        record["source_quad_pixels"] = np.round(source_quad, 3).tolist()
        record["stored_rotation_deg"] = int(surface.get("upright_rotation_deg") or 0) % 360
        record["source_domain"] = surface.get("source_domain")
        record["source_support"] = source_support
    return record, observed


def execute_ready_surfaces(
    *,
    job_dir: Path,
    adapter_path: Path,
    adapter: dict[str, Any],
    inputs: list[dict[str, Any]],
    proposals: dict[str, Any],
    resolved_anchors: dict[str, dict[str, Any]],
    plans: list[dict[str, Any]],
    authority: str,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    observed_masks: list[np.ndarray] = []
    for plan in plans:
        if plan.get("status") != "ready":
            continue
        role = str(plan.get("role") or "")
        try:
            record, observed = _execute_one(
                job_dir=job_dir,
                adapter_path=adapter_path,
                adapter=adapter,
                inputs=inputs,
                proposal=(proposals.get("roles") or {}).get(role) or {},
                anchors=resolved_anchors[role],
                plan=plan,
                authority=authority,
            )
            records.append(record)
            observed_masks.append(observed)
        except (KeyError, OSError, ValueError) as exc:
            records.append({"surface": plan.get("surface"), "role": role, "status": "abstain", "reason": str(exc)})
    overlap = 0
    unique_pixels = 0
    if observed_masks:
        stack = np.stack(observed_masks, axis=0)
        overlap = int(np.count_nonzero(stack.sum(axis=0) > 1))
        unique_pixels = int(np.count_nonzero(stack.any(axis=0)))
    complete = [row for row in records if row["status"] == "complete"]
    fully_complete = [row for row in complete if row.get("satisfies_full_surface", True)]
    partial = [row for row in complete if not row.get("satisfies_full_surface", True)]
    failed = [row for row in records if row["status"] != "complete"]
    return {
        "$schema": SCHEMA,
        "authority_sha256": authority,
        "records": records,
        "summary": {
            "requested_surface_count": sum(plan.get("status") == "ready" for plan in plans),
            "executed_surface_count": len(complete),
            "fully_complete_surface_count": len(fully_complete),
            "partial_surface_count": len(partial),
            "abstained_execution_count": len(failed),
            "generated_uv_pixels": sum(int(row["owned_uv_pixels"]) for row in complete),
            "fully_complete_uv_pixels": sum(int(row["owned_uv_pixels"]) for row in fully_complete),
            "partial_uv_pixels": sum(int(row["owned_uv_pixels"]) for row in partial),
            "unique_uv_pixels": unique_pixels,
            "cross_surface_overlap_pixels": overlap,
            "minimum_containment": min((float(row["containment"]) for row in complete), default=0.0),
            "reflection_used": False,
            "duplicate_physical_instances": len({row["physical_instance_id"] for row in complete}) != len(complete),
        },
        "valid": not failed and overlap == 0 and bool(complete),
    }
