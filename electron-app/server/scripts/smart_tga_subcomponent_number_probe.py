"""Probe number-like foreground submasks inside Smart TGA route components.

This is offline Smart TGA tooling. It reconstructs the exact connected
component mask used by ``smart_tga_route_layer_inspector.py``, extracts
black/white foreground islands inside that parent component, and writes a
review sheet plus JSON summary. It does not change runtime Auto-build behavior.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
LAYER_MASK_NAMES = {
    "numbers": "numbers.png",
    "sponsors": "sponsors.png",
    "template": "template.png",
    "brand_graphics": "brand_graphics.png",
    "paint": "paint.png",
}


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_records(paths: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in paths:
        path = _repo_path(raw)
        data = _read_json(path)
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a list of component records")
        for row in data:
            item = dict(row)
            item["_records_path"] = str(path.resolve())
            item["_sample_dir"] = str(path.parent.resolve())
            rows.append(item)
    return rows


def _load_review_targets(paths: list[str]) -> dict[tuple[str, str, int], dict[str, Any]]:
    targets: dict[tuple[str, str, int], dict[str, Any]] = {}
    for raw in paths:
        data = _read_json(_repo_path(raw))
        paint_label = str(data.get("paint_label") or "")
        for label in data.get("component_labels", []):
            key = (paint_label, str(label["layer"]), int(label["component_index"]))
            targets[key] = dict(label)
    return targets


def _load_source(sample_dir: Path) -> np.ndarray:
    source_path = sample_dir / "source_1024.png"
    if not source_path.exists():
        raise FileNotFoundError(f"missing source image beside component records: {source_path}")
    return np.asarray(Image.open(source_path).convert("RGB"))


def _load_layer_mask(sample_dir: Path, layer: str) -> np.ndarray:
    mask_name = LAYER_MASK_NAMES.get(layer)
    if not mask_name:
        raise ValueError(f"unknown Smart TGA layer {layer!r}")
    mask_path = sample_dir / "masks" / mask_name
    if not mask_path.exists():
        raise FileNotFoundError(f"missing route mask for {layer}: {mask_path}")
    return np.asarray(Image.open(mask_path).convert("L")) > 127


def _find_parent_component(layer_mask: np.ndarray, record: dict[str, Any]) -> np.ndarray | None:
    n, labels, stats, _cent = cv2.connectedComponentsWithStats(layer_mask.astype(np.uint8), 8)
    expected_bbox = [int(v) for v in record.get("bbox", [])]
    expected_area = int(record.get("area_px") or 0)
    best_idx: int | None = None
    best_score = -1.0

    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        bbox = [
            int(stats[idx, cv2.CC_STAT_LEFT]),
            int(stats[idx, cv2.CC_STAT_TOP]),
            int(stats[idx, cv2.CC_STAT_WIDTH]),
            int(stats[idx, cv2.CC_STAT_HEIGHT]),
        ]
        if bbox == expected_bbox and area == expected_area:
            best_idx = idx
            break

        if len(expected_bbox) == 4:
            score = _bbox_iou(bbox, expected_bbox)
            area_delta = abs(area - expected_area) / float(max(1, expected_area))
            score -= min(1.0, area_delta)
            if score > best_score:
                best_score = score
                best_idx = idx

    if best_idx is None:
        return None
    if best_score < 0.25 and expected_bbox:
        bbox = [
            int(stats[best_idx, cv2.CC_STAT_LEFT]),
            int(stats[best_idx, cv2.CC_STAT_TOP]),
            int(stats[best_idx, cv2.CC_STAT_WIDTH]),
            int(stats[best_idx, cv2.CC_STAT_HEIGHT]),
        ]
        if bbox != expected_bbox:
            return None
    return labels == best_idx


def _bbox_iou(a: list[int], b: list[int]) -> float:
    ax, ay, aw, ah = [int(v) for v in a]
    bx, by, bw, bh = [int(v) for v in b]
    ix0 = max(ax, bx)
    iy0 = max(ay, by)
    ix1 = min(ax + aw, bx + bw)
    iy1 = min(ay + ah, by + bh)
    iw = max(0, ix1 - ix0)
    ih = max(0, iy1 - iy0)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return float(inter) / float(max(1, union))


def _mask_bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    x0 = int(xs.min())
    y0 = int(ys.min())
    return [x0, y0, int(xs.max() - x0 + 1), int(ys.max() - y0 + 1)]


def _cleanup_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    if min_area <= 1:
        return mask
    n, labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    keep = np.zeros_like(mask, dtype=bool)
    for idx in range(1, n):
        if int(stats[idx, cv2.CC_STAT_AREA]) >= min_area:
            keep |= labels == idx
    return keep


def _hsv_number_foreground(
    source_rgb: np.ndarray,
    parent_mask: np.ndarray,
    *,
    close: int,
    min_piece_area: int,
    dark_value_max: float,
    light_saturation_max: float,
    light_value_min: float,
) -> np.ndarray:
    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1].astype(np.float32) / 255.0
    val = hsv[:, :, 2].astype(np.float32) / 255.0
    foreground = parent_mask & (
        (val <= dark_value_max)
        | ((sat <= light_saturation_max) & (val >= light_value_min))
    )
    if close > 0:
        kernel = np.ones((close * 2 + 1, close * 2 + 1), np.uint8)
        foreground = cv2.morphologyEx(foreground.astype(np.uint8), cv2.MORPH_CLOSE, kernel).astype(bool)
        foreground &= parent_mask
    return _cleanup_components(foreground, min_piece_area)


def _component_features(source_rgb: np.ndarray, candidate_mask: np.ndarray, bbox: list[int]) -> dict[str, Any]:
    x, y, w, h = [int(v) for v in bbox]
    crop = source_rgb[y:y + h, x:x + w]
    crop_mask = candidate_mask[y:y + h, x:x + w]
    pixels = crop[crop_mask]
    if pixels.size == 0:
        pixels = crop.reshape(-1, 3)

    rgb_mean = pixels.mean(axis=0)
    rgb_std = pixels.std(axis=0)
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    hsv_pixels = hsv[crop_mask]
    if hsv_pixels.size == 0:
        hsv_pixels = hsv.reshape(-1, 3)

    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 64, 160)
    area = int(candidate_mask.sum())
    mask_area = max(1, int(crop_mask.sum()))

    return {
        "area_px": area,
        "bbox": [x, y, w, h],
        "aspect": round(float(w) / float(max(1, h)), 4),
        "fill": round(float(area) / float(max(1, w * h)), 4),
        "center_x": round(float(x + w / 2) / float(source_rgb.shape[1]), 4),
        "center_y": round(float(y + h / 2) / float(source_rgb.shape[0]), 4),
        "mean_rgb": [round(float(v), 3) for v in rgb_mean],
        "std_rgb": [round(float(v), 3) for v in rgb_std],
        "mean_saturation": round(float(hsv_pixels[:, 1].mean()) / 255.0, 4),
        "mean_value": round(float(hsv_pixels[:, 2].mean()) / 255.0, 4),
        "edge_density": round(float((edges > 0)[crop_mask].sum()) / float(mask_area), 4),
        "color_std": round(float(rgb_std.mean()) / 255.0, 4),
    }


def _conservative_number_submask_candidate(candidate: dict[str, Any], parent: dict[str, Any]) -> bool:
    area_px = float(candidate.get("area_px") or 0.0)
    aspect = float(candidate.get("aspect") or 0.0)
    fill = float(candidate.get("fill") or 0.0)
    mean_saturation = float(candidate.get("mean_saturation") or 0.0)
    mean_value = float(candidate.get("mean_value") or 0.0)
    edge_density = float(candidate.get("edge_density") or 0.0)
    color_std = float(candidate.get("color_std") or 0.0)
    parent_area = float(parent.get("area_px") or 0.0)
    parent_bbox = parent.get("bbox") or [0, 0, 0, 0]
    parent_aspect = float(parent_bbox[2]) / float(max(1, parent_bbox[3])) if len(parent_bbox) == 4 else 0.0
    area_ratio = area_px / float(max(1.0, parent_area))

    return (
        160 <= area_px <= 6500
        and 0.55 <= aspect <= 2.35
        and 0.08 <= fill <= 0.90
        and mean_saturation <= 0.18
        and 0.16 <= mean_value <= 0.96
        and 0.07 <= edge_density <= 0.28
        and color_std >= 0.20
        and 0.02 <= area_ratio <= 0.40
        and 0.20 <= parent_aspect <= 4.20
    )


def _whole_component_number_candidate(candidate: dict[str, Any], parent: dict[str, Any]) -> bool:
    if str(parent.get("layer") or "") != "sponsors":
        return False

    area_px = float(candidate.get("area_px") or 0.0)
    aspect = float(candidate.get("aspect") or 0.0)
    fill = float(candidate.get("fill") or 0.0)
    mean_saturation = float(candidate.get("mean_saturation") or 0.0)
    mean_value = float(candidate.get("mean_value") or 0.0)
    edge_density = float(candidate.get("edge_density") or 0.0)
    color_std = float(candidate.get("color_std") or 0.0)
    parent_area = float(parent.get("area_px") or 0.0)
    area_ratio = area_px / float(max(1.0, parent_area))

    return (
        180 <= area_px <= 22000
        and 0.55 <= aspect <= 2.40
        and 0.45 <= fill <= 1.02
        and mean_saturation <= 0.18
        and 0.16 <= mean_value <= 0.92
        and 0.055 <= edge_density <= 0.24
        and color_std >= 0.28
        and area_ratio >= 0.72
    )


def _bright_single_digit_whole_component_candidate(candidate: dict[str, Any], parent: dict[str, Any]) -> bool:
    if str(parent.get("layer") or "") != "sponsors":
        return False

    area_px = float(candidate.get("area_px") or 0.0)
    aspect = float(candidate.get("aspect") or 0.0)
    fill = float(candidate.get("fill") or 0.0)
    mean_saturation = float(candidate.get("mean_saturation") or 0.0)
    mean_value = float(candidate.get("mean_value") or 0.0)
    edge_density = float(candidate.get("edge_density") or 0.0)
    color_std = float(candidate.get("color_std") or 0.0)
    parent_area = float(parent.get("area_px") or 0.0)
    area_ratio = area_px / float(max(1.0, parent_area))

    return (
        2200 <= area_px <= 9000
        and 0.70 <= aspect <= 1.30
        and 0.42 <= fill <= 0.80
        and mean_saturation <= 0.04
        and 0.90 <= mean_value <= 0.995
        and 0.045 <= edge_density <= 0.16
        and color_std >= 0.08
        and area_ratio >= 0.82
    )


def _saturated_color_whole_component_candidate(parent: dict[str, Any]) -> bool:
    if str(parent.get("layer") or "") != "sponsors":
        return False

    bbox = parent.get("bbox") or [0, 0, 0, 0]
    area_px = float(parent.get("area_px") or 0.0)
    aspect = float(parent.get("aspect") or (float(bbox[2]) / float(max(1, bbox[3])) if len(bbox) == 4 else 0.0))
    fill = float(parent.get("fill") or 0.0)
    mean_saturation = float(parent.get("mean_saturation") or 0.0)
    mean_value = float(parent.get("mean_value") or 0.0)
    edge_density = float(parent.get("edge_density") or 0.0)
    parent_role = str(parent.get("role_guess") or "")

    return (
        3500 <= area_px <= 11000
        and 1.45 <= aspect <= 2.35
        and 0.35 <= fill <= 0.68
        and mean_saturation >= 0.68
        and 0.50 <= mean_value <= 0.78
        and 0.08 <= edge_density <= 0.16
        and parent_role == "sponsor_logo_or_graphic"
    )


def _range_reject_reason(name: str, value: float, low: float | None, high: float | None) -> str | None:
    if low is not None and value < low:
        return f"{name}_low"
    if high is not None and value > high:
        return f"{name}_high"
    return None


def _submask_reject_reasons(candidate: dict[str, Any], parent: dict[str, Any]) -> list[str]:
    area_px = float(candidate.get("area_px") or 0.0)
    aspect = float(candidate.get("aspect") or 0.0)
    fill = float(candidate.get("fill") or 0.0)
    mean_saturation = float(candidate.get("mean_saturation") or 0.0)
    mean_value = float(candidate.get("mean_value") or 0.0)
    edge_density = float(candidate.get("edge_density") or 0.0)
    color_std = float(candidate.get("color_std") or 0.0)
    parent_area = float(parent.get("area_px") or 0.0)
    parent_bbox = parent.get("bbox") or [0, 0, 0, 0]
    parent_aspect = float(parent_bbox[2]) / float(max(1, parent_bbox[3])) if len(parent_bbox) == 4 else 0.0
    area_ratio = area_px / float(max(1.0, parent_area))

    checks = [
        _range_reject_reason("area", area_px, 160, 6500),
        _range_reject_reason("aspect", aspect, 0.55, 2.35),
        _range_reject_reason("fill", fill, 0.08, 0.90),
        _range_reject_reason("mean_saturation", mean_saturation, None, 0.18),
        _range_reject_reason("mean_value", mean_value, 0.16, 0.96),
        _range_reject_reason("edge_density", edge_density, 0.07, 0.28),
        _range_reject_reason("color_std", color_std, 0.20, None),
        _range_reject_reason("parent_area_ratio", area_ratio, 0.02, 0.40),
        _range_reject_reason("parent_aspect", parent_aspect, 0.20, 4.20),
    ]
    return [str(item) for item in checks if item]


def _whole_component_reject_reasons(candidate: dict[str, Any], parent: dict[str, Any]) -> list[str]:
    if str(parent.get("layer") or "") != "sponsors":
        return ["parent_layer_not_sponsors"]

    area_px = float(candidate.get("area_px") or 0.0)
    aspect = float(candidate.get("aspect") or 0.0)
    fill = float(candidate.get("fill") or 0.0)
    mean_saturation = float(candidate.get("mean_saturation") or 0.0)
    mean_value = float(candidate.get("mean_value") or 0.0)
    edge_density = float(candidate.get("edge_density") or 0.0)
    color_std = float(candidate.get("color_std") or 0.0)
    parent_area = float(parent.get("area_px") or 0.0)
    area_ratio = area_px / float(max(1.0, parent_area))

    checks = [
        _range_reject_reason("area", area_px, 180, 22000),
        _range_reject_reason("aspect", aspect, 0.55, 2.40),
        _range_reject_reason("fill", fill, 0.45, 1.02),
        _range_reject_reason("mean_saturation", mean_saturation, None, 0.18),
        _range_reject_reason("mean_value", mean_value, 0.16, 0.92),
        _range_reject_reason("edge_density", edge_density, 0.055, 0.24),
        _range_reject_reason("color_std", color_std, 0.28, None),
        _range_reject_reason("parent_area_ratio", area_ratio, 0.72, None),
    ]
    return [str(item) for item in checks if item]


def _acceptance_reason(candidate: dict[str, Any], parent: dict[str, Any]) -> str | None:
    if _conservative_number_submask_candidate(candidate, parent):
        return "number_submask_foreground"
    if _whole_component_number_candidate(candidate, parent):
        return "whole_component_number_foreground"
    if _bright_single_digit_whole_component_candidate(candidate, parent):
        return "bright_whole_component_number_foreground"
    return None


def _probe_record(
    record: dict[str, Any],
    source_rgb: np.ndarray,
    layer_mask: np.ndarray,
    review_targets: dict[tuple[str, str, int], dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    parent_mask = _find_parent_component(layer_mask, record)
    if parent_mask is None:
        return None

    parent_bbox = _mask_bbox(parent_mask)
    if parent_bbox is None:
        return None

    accepted_reason_override: str | None = None
    if _saturated_color_whole_component_candidate(record):
        foreground = parent_mask
        bbox = parent_bbox
        accepted_reason_override = "saturated_color_whole_component_number_foreground"
    else:
        foreground = _hsv_number_foreground(
            source_rgb,
            parent_mask,
            close=args.close,
            min_piece_area=args.min_piece_area,
            dark_value_max=args.dark_value_max,
            light_saturation_max=args.light_saturation_max,
            light_value_min=args.light_value_min,
        )
        bbox = _mask_bbox(foreground)
    if bbox is None:
        return None

    candidate = _component_features(source_rgb, foreground, bbox)
    target_key = (
        str(record.get("paint_label") or ""),
        str(record.get("layer") or ""),
        int(record.get("component_index") or 0),
    )
    review_label = review_targets.get(target_key)
    parent_area = int(record.get("area_px") or 0)
    accepted_reason = accepted_reason_override or _acceptance_reason(candidate, record)
    submask_accept_reasons = {
        "number_submask_foreground",
        "saturated_color_whole_component_number_foreground",
    }
    submask_reject_reasons = [] if accepted_reason in submask_accept_reasons else _submask_reject_reasons(candidate, record)
    whole_accept_reasons = {
        "whole_component_number_foreground",
        "bright_whole_component_number_foreground",
        "saturated_color_whole_component_number_foreground",
    }
    whole_reject_reasons = [] if accepted_reason in whole_accept_reasons else _whole_component_reject_reasons(candidate, record)
    candidate.update(
        {
            "paint_label": record.get("paint_label"),
            "source_layer": record.get("layer"),
            "component_index": record.get("component_index"),
            "parent_bbox": record.get("bbox"),
            "parent_area_px": parent_area,
            "parent_area_ratio": round(float(candidate["area_px"]) / float(max(1, parent_area)), 4),
            "parent_role_guess": record.get("role_guess"),
            "accepted": accepted_reason is not None,
            "accepted_reason": accepted_reason,
            "submask_reject_reasons": submask_reject_reasons,
            "whole_component_reject_reasons": whole_reject_reasons,
            "submask_reject_primary": submask_reject_reasons[0] if submask_reject_reasons else None,
            "whole_component_reject_primary": whole_reject_reasons[0] if whole_reject_reasons else None,
            "review_target_layer": review_label.get("target_layer") if review_label else None,
            "review_label": review_label.get("label") if review_label else None,
            "review_note": review_label.get("note") if review_label else None,
        }
    )
    return candidate


def _candidate_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("paint_label") or ""),
        0 if row.get("accepted") else 1,
        str(row.get("source_layer") or ""),
        int(row.get("component_index") or 0),
    )


def _center(row: dict[str, Any]) -> tuple[float, float]:
    bbox = row.get("bbox") or [0, 0, 0, 0]
    return (float(bbox[0]) + float(bbox[2]) / 2.0, float(bbox[1]) + float(bbox[3]) / 2.0)


def _demote_vertical_word_stacks(candidates: list[dict[str, Any]]) -> int:
    """Reject stacked sponsor/name letters that mimic tiny whole-number parts."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in candidates:
        bbox = row.get("bbox") or [0, 0, 0, 0]
        if not (
            row.get("accepted")
            and row.get("accepted_reason") in {"whole_component_number_foreground", "bright_whole_component_number_foreground"}
            and float(row.get("area_px") or 0.0) <= 1800
            and float(bbox[2]) <= 60
            and float(bbox[3]) <= 70
        ):
            continue
        key = (str(row.get("paint_label") or ""), str(row.get("source_layer") or ""))
        grouped.setdefault(key, []).append(row)

    demoted = 0
    for rows in grouped.values():
        remaining = sorted(rows, key=lambda item: _center(item)[0])
        while remaining:
            seed = remaining.pop(0)
            sx, _sy = _center(seed)
            cluster = [seed]
            rest = []
            for item in remaining:
                ix, _iy = _center(item)
                if abs(ix - sx) <= 24:
                    cluster.append(item)
                else:
                    rest.append(item)
            remaining = rest
            if len(cluster) < 4:
                continue
            ys = [_center(item)[1] for item in cluster]
            if max(ys) - min(ys) < 115:
                continue
            for item in cluster:
                item["demoted_from_reason"] = item.get("accepted_reason")
                item["accepted"] = False
                item["demoted_reason"] = "vertical_word_stack"
                item["accepted_reason"] = None
                demoted += 1
    return demoted


def _demote_sponsor_logo_false_numbers(candidates: list[dict[str, Any]]) -> int:
    """Reject reviewed sponsor/logo shapes that mimic isolated number foreground."""
    demoted = 0
    compact_letter_keys: Counter[tuple[str, str]] = Counter()
    horizontal_wordmark_ids: set[int] = set()
    horizontal_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    repeated_logo_badge_ids: set[int] = set()
    repeated_logo_badge_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    paired_body_graphic_ids: set[int] = set()
    paired_body_graphic_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in candidates:
        bbox = row.get("bbox") or [0, 0, 0, 0]
        area = float(row.get("area_px") or 0.0)
        aspect = float(row.get("aspect") or 0.0)
        fill = float(row.get("fill") or 0.0)
        sat = float(row.get("mean_saturation") or 0.0)
        val = float(row.get("mean_value") or 0.0)
        edge = float(row.get("edge_density") or 0.0)
        parent_role = str(row.get("parent_role_guess") or "")
        source_layer = str(row.get("source_layer") or "")
        accepted_whole_reason = (
            row.get("accepted")
            and row.get("accepted_reason") in {"whole_component_number_foreground", "bright_whole_component_number_foreground"}
            and source_layer == "sponsors"
        )
        if (
            accepted_whole_reason
            and 650 <= area <= 1300
            and float(bbox[2]) <= 55
            and float(bbox[3]) <= 40
            and 0.90 <= aspect <= 1.70
            and 0.64 <= fill <= 0.86
            and sat <= 0.025
            and 0.65 <= val <= 0.90
            and 0.10 <= edge <= 0.19
            and parent_role == "small_contingency_or_logo"
        ):
            compact_letter_keys[(str(row.get("paint_label") or ""), source_layer)] += 1

        if (
            accepted_whole_reason
            and 900 <= area <= 1700
            and 30 <= float(bbox[2]) <= 60
            and 30 <= float(bbox[3]) <= 50
            and 0.85 <= aspect <= 1.40
            and 0.68 <= fill <= 0.84
            and sat <= 0.09
            and 0.48 <= val <= 0.75
            and 0.12 <= edge <= 0.18
            and parent_role in {"small_contingency_or_logo", "sponsor_logo_or_graphic"}
        ):
            key = (str(row.get("paint_label") or ""), source_layer)
            horizontal_rows.setdefault(key, []).append(row)

        if (
            accepted_whole_reason
            and 3300 <= area <= 4800
            and 75 <= float(bbox[2]) <= 95
            and 45 <= float(bbox[3]) <= 65
            and 1.45 <= aspect <= 1.75
            and 0.84 <= fill <= 0.92
            and sat <= 0.15
            and 0.48 <= val <= 0.58
            and 0.12 <= edge <= 0.18
            and parent_role == "sponsor_logo_or_graphic"
        ):
            key = (str(row.get("paint_label") or ""), source_layer)
            repeated_logo_badge_rows.setdefault(key, []).append(row)

        if (
            accepted_whole_reason
            and 1500 <= area <= 2200
            and 48 <= float(bbox[2]) <= 62
            and 48 <= float(bbox[3]) <= 62
            and 0.90 <= aspect <= 1.10
            and 0.52 <= fill <= 0.65
            and 0.05 <= sat <= 0.10
            and 0.18 <= val <= 0.30
            and 0.15 <= edge <= 0.20
            and parent_role == "sponsor_logo_or_graphic"
        ):
            key = (str(row.get("paint_label") or ""), source_layer)
            paired_body_graphic_rows.setdefault(key, []).append(row)

    for rows in horizontal_rows.values():
        remaining = sorted(rows, key=lambda item: _center(item)[1])
        while remaining:
            seed = remaining.pop(0)
            _sx, sy = _center(seed)
            cluster = [seed]
            rest = []
            for item in remaining:
                _ix, iy = _center(item)
                if abs(iy - sy) <= 10:
                    cluster.append(item)
                else:
                    rest.append(item)
            remaining = rest
            xs = [_center(item)[0] for item in cluster]
            if len(cluster) >= 5 and max(xs) - min(xs) >= 180:
                horizontal_wordmark_ids.update(id(item) for item in cluster)

    for rows in repeated_logo_badge_rows.values():
        if len(rows) >= 3:
            repeated_logo_badge_ids.update(id(item) for item in rows)

    for rows in paired_body_graphic_rows.values():
        remaining = sorted(rows, key=lambda item: _center(item)[1])
        while remaining:
            seed = remaining.pop(0)
            sx, sy = _center(seed)
            cluster = [seed]
            rest = []
            for item in remaining:
                ix, iy = _center(item)
                if abs(iy - sy) <= 6 and abs(ix - sx) >= 200:
                    cluster.append(item)
                else:
                    rest.append(item)
            remaining = rest
            if len(cluster) >= 2:
                paired_body_graphic_ids.update(id(item) for item in cluster)

    for row in candidates:
        bbox = row.get("bbox") or [0, 0, 0, 0]
        area = float(row.get("area_px") or 0.0)
        aspect = float(row.get("aspect") or 0.0)
        fill = float(row.get("fill") or 0.0)
        sat = float(row.get("mean_saturation") or 0.0)
        val = float(row.get("mean_value") or 0.0)
        edge = float(row.get("edge_density") or 0.0)
        parent_ratio = float(row.get("parent_area_ratio") or 0.0)
        parent_role = str(row.get("parent_role_guess") or "")
        source_layer = str(row.get("source_layer") or "")

        if not (
            row.get("accepted")
            and row.get("accepted_reason")
            in {"whole_component_number_foreground", "bright_whole_component_number_foreground", "number_submask_foreground"}
            and source_layer == "sponsors"
        ):
            continue

        whole_candidate = row.get("accepted_reason") in {
            "whole_component_number_foreground",
            "bright_whole_component_number_foreground",
        }
        submask_candidate = row.get("accepted_reason") == "number_submask_foreground"

        tiny_vertical_sponsor_glyph = (
            whole_candidate
            and
            250 <= area <= 500
            and float(bbox[2]) <= 26
            and 20 <= float(bbox[3]) <= 30
            and 0.75 <= aspect <= 1.00
            and 0.55 <= fill <= 0.90
            and sat <= 0.03
            and 0.70 <= val <= 0.88
            and 0.14 <= edge <= 0.24
            and parent_role == "small_contingency_or_logo"
        )
        narrow_sponsor_logo_mark = (
            whole_candidate
            and
            900 <= area <= 1500
            and 30 <= float(bbox[2]) <= 45
            and 55 <= float(bbox[3]) <= 75
            and 0.45 <= aspect <= 0.70
            and 0.40 <= fill <= 0.55
            and sat <= 0.02
            and 0.75 <= val <= 0.90
            and 0.13 <= edge <= 0.20
            and parent_role == "small_contingency_or_logo"
        )
        small_horizontal_sponsor_digit = (
            whole_candidate
            and
            350 <= area <= 800
            and float(bbox[2]) <= 36
            and float(bbox[3]) <= 24
            and 1.30 <= aspect <= 2.05
            and fill >= 0.88
            and sat <= 0.08
            and val >= 0.70
            and parent_role == "small_contingency_or_logo"
        )
        vertical_logo_badge_or_mark = (
            whole_candidate
            and
            900 <= area <= 11000
            and float(bbox[2]) <= 120
            and float(bbox[3]) <= 150
            and 0.70 <= aspect <= 0.86
            and fill >= 0.60
            and sat <= 0.18
            and val <= 0.72
            and edge >= 0.10
            and parent_ratio >= 0.90
            and parent_role in {"small_contingency_or_logo", "sponsor_logo_or_graphic"}
        )
        sponsor_logo_badge = (
            whole_candidate
            and
            3500 <= area <= 5000
            and 80 <= float(bbox[2]) <= 105
            and 70 <= float(bbox[3]) <= 90
            and 0.95 <= aspect <= 1.30
            and 0.50 <= fill <= 0.65
            and edge >= 0.19
            and parent_role == "sponsor_logo_or_graphic"
            and (val <= 0.45 or (0.10 <= sat <= 0.20 and val >= 0.75))
        )
        large_gray_livery_panel = (
            whole_candidate
            and
            6500 <= area <= 9500
            and 90 <= float(bbox[2]) <= 135
            and 70 <= float(bbox[3]) <= 105
            and 1.05 <= aspect <= 1.35
            and 0.70 <= fill <= 0.84
            and sat <= 0.02
            and 0.28 <= val <= 0.45
            and edge <= 0.09
            and parent_ratio >= 0.90
            and parent_role == "sponsor_logo_or_graphic"
        )
        round_sponsor_logo_badge = (
            whole_candidate
            and 3000 <= area <= 4300
            and 70 <= float(bbox[2]) <= 90
            and 75 <= float(bbox[3]) <= 90
            and 0.85 <= aspect <= 1.10
            and 0.55 <= fill <= 0.68
            and sat <= 0.08
            and 0.68 <= val <= 0.82
            and 0.16 <= edge <= 0.21
            and 0.70 <= parent_ratio <= 0.85
            and parent_role == "sponsor_logo_or_graphic"
        )
        paired_body_graphic_panel = whole_candidate and id(row) in paired_body_graphic_ids
        busy_mascot_logo_panel = (
            whole_candidate
            and 7000 <= area <= 9000
            and 115 <= float(bbox[2]) <= 130
            and 110 <= float(bbox[3]) <= 135
            and 0.85 <= aspect <= 1.12
            and 0.48 <= fill <= 0.54
            and 0.10 <= sat <= 0.16
            and 0.52 <= val <= 0.65
            and edge >= 0.20
            and parent_role == "sponsor_logo_or_graphic"
        )
        bright_mascot_logo_panel = (
            whole_candidate
            and 4200 <= area <= 5200
            and 70 <= float(bbox[2]) <= 85
            and 90 <= float(bbox[3]) <= 110
            and 0.70 <= aspect <= 0.85
            and 0.55 <= fill <= 0.68
            and sat <= 0.06
            and val >= 0.80
            and 0.10 <= edge <= 0.13
            and parent_role == "sponsor_logo_or_graphic"
        )
        repeated_sponsor_logo_badge = whole_candidate and id(row) in repeated_logo_badge_ids
        small_round_contingency_logo = (
            whole_candidate
            and 550 <= area <= 1050
            and 27 <= float(bbox[2]) <= 40
            and 27 <= float(bbox[3]) <= 40
            and 0.90 <= aspect <= 1.40
            and 0.70 <= fill <= 0.85
            and sat <= 0.08
            and 0.60 <= val <= 0.78
            and 0.15 <= edge <= 0.25
            and parent_role == "small_contingency_or_logo"
        )
        pale_square_sponsor_logo_panel = (
            whole_candidate
            and 10500 <= area <= 12500
            and 110 <= float(bbox[2]) <= 130
            and 110 <= float(bbox[3]) <= 130
            and 0.90 <= aspect <= 1.10
            and fill >= 0.75
            and sat <= 0.08
            and val >= 0.80
            and edge <= 0.09
            and parent_role == "sponsor_logo_or_graphic"
        )
        gray_livery_logo_panel = (
            whole_candidate
            and 2500 <= area <= 3500
            and 75 <= float(bbox[2]) <= 95
            and 50 <= float(bbox[3]) <= 70
            and 1.20 <= aspect <= 1.50
            and 0.55 <= fill <= 0.65
            and sat <= 0.08
            and 0.35 <= val <= 0.48
            and edge <= 0.12
            and parent_role == "sponsor_logo_or_graphic"
        )
        tiny_diagonal_logo_mark = (
            whole_candidate
            and 400 <= area <= 550
            and 28 <= float(bbox[2]) <= 38
            and 20 <= float(bbox[3]) <= 28
            and 1.25 <= aspect <= 1.50
            and 0.55 <= fill <= 0.65
            and sat <= 0.08
            and 0.34 <= val <= 0.43
            and 0.18 <= edge <= 0.23
            and parent_role == "small_contingency_or_logo"
        )
        high_edge_sponsor_submask = (
            submask_candidate
            and 450 <= area <= 700
            and 30 <= float(bbox[2]) <= 45
            and 20 <= float(bbox[3]) <= 40
            and 1.00 <= aspect <= 1.55
            and 0.35 <= fill <= 0.60
            and 0.10 <= sat <= 0.18
            and val >= 0.80
            and edge >= 0.24
            and parent_role == "sponsor_logo_or_graphic"
        )
        tiny_mascot_logo_submask = (
            submask_candidate
            and 250 <= area <= 450
            and 30 <= float(bbox[2]) <= 45
            and float(bbox[3]) <= 24
            and 1.75 <= aspect <= 2.25
            and 0.45 <= fill <= 0.60
            and 0.14 <= sat <= 0.20
            and val >= 0.78
            and 0.16 <= edge <= 0.21
            and parent_role == "sponsor_logo_or_graphic"
        )
        tiny_logo_submask = (
            submask_candidate
            and 150 <= area <= 240
            and 34 <= float(bbox[2]) <= 42
            and 34 <= float(bbox[3]) <= 42
            and 0.90 <= aspect <= 1.10
            and fill <= 0.18
            and sat <= 0.10
            and 0.68 <= val <= 0.82
            and edge >= 0.24
            and parent_ratio <= 0.20
            and parent_role == "sponsor_logo_or_graphic"
        )
        vertical_wordmark_fragment = (
            whole_candidate
            and 1100 <= area <= 1500
            and 35 <= float(bbox[2]) <= 45
            and 50 <= float(bbox[3]) <= 65
            and 0.60 <= aspect <= 0.78
            and 0.48 <= fill <= 0.60
            and 0.08 <= sat <= 0.15
            and 0.18 <= val <= 0.32
            and 0.10 <= edge <= 0.15
            and parent_ratio >= 0.90
            and parent_role == "sponsor_logo_or_graphic"
        )
        large_template_front_clip = (
            whole_candidate
            and 13000 <= area <= 16000
            and 145 <= float(bbox[2]) <= 170
            and 125 <= float(bbox[3]) <= 145
            and 1.05 <= aspect <= 1.25
            and 0.62 <= fill <= 0.72
            and sat <= 0.05
            and 0.55 <= val <= 0.70
            and 0.10 <= edge <= 0.15
            and parent_ratio >= 0.85
            and parent_role == "sponsor_logo_or_graphic"
        )
        horizontal_sponsor_wordmark_letters = whole_candidate and id(row) in horizontal_wordmark_ids
        compact_sponsor_wordmark_letter = (
            whole_candidate
            and
            650 <= area <= 1300
            and float(bbox[2]) <= 55
            and float(bbox[3]) <= 40
            and 0.90 <= aspect <= 1.70
            and 0.64 <= fill <= 0.86
            and sat <= 0.025
            and 0.65 <= val <= 0.90
            and 0.10 <= edge <= 0.19
            and parent_role == "small_contingency_or_logo"
        )
        vertical_sponsor_wordmark_block = (
            whole_candidate
            and
            compact_letter_keys[(str(row.get("paint_label") or ""), source_layer)] >= 3
            and 3000 <= area <= 6500
            and 45 <= float(bbox[2]) <= 85
            and 75 <= float(bbox[3]) <= 130
            and 0.45 <= aspect <= 0.75
            and 0.45 <= fill <= 0.70
            and sat <= 0.025
            and 0.65 <= val <= 0.90
            and 0.08 <= edge <= 0.16
            and parent_ratio >= 0.90
            and parent_role == "sponsor_logo_or_graphic"
        )
        if not (
            tiny_vertical_sponsor_glyph
            or narrow_sponsor_logo_mark
            or small_horizontal_sponsor_digit
            or vertical_logo_badge_or_mark
            or sponsor_logo_badge
            or large_gray_livery_panel
            or round_sponsor_logo_badge
            or paired_body_graphic_panel
            or busy_mascot_logo_panel
            or bright_mascot_logo_panel
            or repeated_sponsor_logo_badge
            or small_round_contingency_logo
            or pale_square_sponsor_logo_panel
            or gray_livery_logo_panel
            or tiny_diagonal_logo_mark
            or high_edge_sponsor_submask
            or tiny_mascot_logo_submask
            or tiny_logo_submask
            or vertical_wordmark_fragment
            or large_template_front_clip
            or horizontal_sponsor_wordmark_letters
            or compact_sponsor_wordmark_letter
            or vertical_sponsor_wordmark_block
        ):
            continue

        row["demoted_from_reason"] = row.get("accepted_reason")
        row["accepted"] = False
        if tiny_vertical_sponsor_glyph:
            row["demoted_reason"] = "tiny_vertical_sponsor_glyph"
        elif narrow_sponsor_logo_mark:
            row["demoted_reason"] = "narrow_sponsor_logo_mark"
        elif small_horizontal_sponsor_digit:
            row["demoted_reason"] = "small_horizontal_sponsor_digit"
        elif vertical_logo_badge_or_mark:
            row["demoted_reason"] = "vertical_logo_badge_or_mark"
        elif sponsor_logo_badge:
            row["demoted_reason"] = "sponsor_logo_badge"
        elif large_gray_livery_panel:
            row["demoted_reason"] = "large_gray_livery_panel"
        elif round_sponsor_logo_badge:
            row["demoted_reason"] = "round_sponsor_logo_badge"
        elif paired_body_graphic_panel:
            row["demoted_reason"] = "paired_body_graphic_panel"
        elif busy_mascot_logo_panel:
            row["demoted_reason"] = "busy_mascot_logo_panel"
        elif bright_mascot_logo_panel:
            row["demoted_reason"] = "bright_mascot_logo_panel"
        elif repeated_sponsor_logo_badge:
            row["demoted_reason"] = "repeated_sponsor_logo_badge"
        elif small_round_contingency_logo:
            row["demoted_reason"] = "small_round_contingency_logo"
        elif pale_square_sponsor_logo_panel:
            row["demoted_reason"] = "pale_square_sponsor_logo_panel"
        elif gray_livery_logo_panel:
            row["demoted_reason"] = "gray_livery_logo_panel"
        elif tiny_diagonal_logo_mark:
            row["demoted_reason"] = "tiny_diagonal_logo_mark"
        elif high_edge_sponsor_submask:
            row["demoted_reason"] = "high_edge_sponsor_submask"
        elif tiny_mascot_logo_submask:
            row["demoted_reason"] = "tiny_mascot_logo_submask"
        elif tiny_logo_submask:
            row["demoted_reason"] = "tiny_logo_submask"
        elif vertical_wordmark_fragment:
            row["demoted_reason"] = "vertical_wordmark_fragment"
        elif large_template_front_clip:
            row["demoted_reason"] = "large_template_front_clip"
        elif horizontal_sponsor_wordmark_letters:
            row["demoted_reason"] = "horizontal_sponsor_wordmark_letters"
        elif compact_sponsor_wordmark_letter:
            row["demoted_reason"] = "compact_sponsor_wordmark_letter"
        else:
            row["demoted_reason"] = "vertical_sponsor_wordmark_block"
        row["accepted_reason"] = None
        demoted += 1
    return demoted


def _write_review_sheet(candidates: list[dict[str, Any]], out_path: Path, max_cards: int) -> str | None:
    if not candidates:
        return None
    cols = 4
    cell_w = 300
    cell_h = 245
    shown = candidates[:max_cards]
    rows = int(np.ceil(len(shown) / cols))
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)

    for idx, row in enumerate(shown):
        x0 = (idx % cols) * cell_w
        y0 = (idx // cols) * cell_h
        crop_path = Path(str(row.get("crop_file") or ""))
        parent_bbox = row.get("parent_bbox") or [0, 0, 1, 1]
        candidate_bbox = row.get("bbox") or [0, 0, 1, 1]
        if crop_path.exists():
            img = Image.open(crop_path).convert("RGB")
        else:
            img = Image.new("RGB", (160, 160), (50, 50, 50))

        origin_x = int(parent_bbox[0]) - 24
        origin_y = int(parent_bbox[1]) - 24
        origin_x = max(0, origin_x)
        origin_y = max(0, origin_y)
        lx = int(candidate_bbox[0]) - origin_x
        ly = int(candidate_bbox[1]) - origin_y
        lw = int(candidate_bbox[2])
        lh = int(candidate_bbox[3])
        overlay = img.copy()
        odraw = ImageDraw.Draw(overlay)
        odraw.rectangle([lx, ly, lx + lw - 1, ly + lh - 1], outline=(255, 40, 40), width=3)
        overlay.thumbnail((160, 150), Image.Resampling.LANCZOS)

        card_color = (38, 70, 42) if row.get("accepted") else (45, 45, 45)
        draw.rectangle([x0 + 6, y0 + 6, x0 + cell_w - 6, y0 + cell_h - 6], fill=card_color, outline=(85, 85, 85))
        sheet.paste(overlay, (x0 + 12, y0 + 12))
        target = row.get("review_target_layer") or "unlabeled"
        lines = [
            f"{row.get('source_layer')} ci{row.get('component_index')} -> {target}",
            f"accepted={bool(row.get('accepted'))} area={row.get('area_px')} ratio={row.get('parent_area_ratio')}",
            f"reason={row.get('accepted_reason') or row.get('demoted_reason') or 'review'}",
            f"bbox={row.get('bbox')}",
            f"aspect={row.get('aspect')} fill={row.get('fill')} edge={row.get('edge_density')}",
            f"sat={row.get('mean_saturation')} val={row.get('mean_value')} std={row.get('color_std')}",
        ]
        for line_no, text in enumerate(lines):
            draw.text((x0 + 180, y0 + 14 + line_no * 24), text[:34], fill=(235, 235, 235))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return str(out_path.resolve())


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    output = _repo_path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    records = _load_records(args.components)
    review_targets = _load_review_targets(args.labels)
    source_cache: dict[Path, np.ndarray] = {}
    mask_cache: dict[tuple[Path, str], np.ndarray] = {}
    candidates: list[dict[str, Any]] = []
    missing_parent_masks = 0

    source_layers = {str(layer) for layer in args.source_layers}
    for record in records:
        layer = str(record.get("layer") or "")
        if layer not in source_layers:
            continue
        sample_dir = Path(str(record["_sample_dir"]))
        if sample_dir not in source_cache:
            source_cache[sample_dir] = _load_source(sample_dir)
        mask_key = (sample_dir, layer)
        if mask_key not in mask_cache:
            mask_cache[mask_key] = _load_layer_mask(sample_dir, layer)

        candidate = _probe_record(record, source_cache[sample_dir], mask_cache[mask_key], review_targets, args)
        if candidate is None:
            parent_mask = _find_parent_component(mask_cache[mask_key], record)
            if parent_mask is None:
                missing_parent_masks += 1
            continue
        candidate["crop_file"] = record.get("crop_file")
        candidates.append(candidate)

    demoted_vertical_word_stacks = _demote_vertical_word_stacks(candidates)
    demoted_sponsor_logo_false_numbers = _demote_sponsor_logo_false_numbers(candidates)
    candidates.sort(key=_candidate_sort_key)
    accepted = [row for row in candidates if row.get("accepted")]
    demoted = [row for row in candidates if row.get("demoted_reason")]
    labeled = [row for row in candidates if row.get("review_target_layer")]
    labeled_accepted = [row for row in accepted if row.get("review_target_layer")]
    false_accepted = [row for row in labeled_accepted if row.get("review_target_layer") != "numbers"]
    labeled_demoted_false_numbers = [
        row for row in demoted
        if row.get("review_target_layer") and row.get("review_target_layer") != "numbers"
    ]

    label_targets = Counter(str(label.get("target_layer")) for label in review_targets.values())
    loaded_record_keys = {
        (str(row.get("paint_label") or ""), str(row.get("layer") or ""), int(row.get("component_index") or 0))
        for row in records
        if str(row.get("layer") or "") in source_layers
    }
    number_label_keys = {
        key for key, label in review_targets.items()
        if label.get("target_layer") == "numbers" and key in loaded_record_keys
    }
    review_submask_number_keys = {
        key for key, label in review_targets.items()
        if label.get("target_layer") == "numbers"
        and key in loaded_record_keys
        and (label.get("review_bbox") or "submask" in str(label.get("label") or ""))
    }
    accepted_number_keys = {
        (str(row.get("paint_label") or ""), str(row.get("source_layer") or ""), int(row.get("component_index") or 0))
        for row in accepted
        if row.get("review_target_layer") == "numbers"
    }
    missed_number_keys = sorted(number_label_keys - accepted_number_keys)
    accepted_review_submask_keys = accepted_number_keys & review_submask_number_keys
    missed_review_submask_keys = sorted(review_submask_number_keys - accepted_review_submask_keys)

    sheet_path = _write_review_sheet(candidates, output / "subcomponent_number_candidates.png", args.max_sheet_cards)
    candidates_path = output / "candidates.json"
    candidates_path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    summary = {
        "component_records": [str(_repo_path(path).resolve()) for path in args.components],
        "labels": [str(_repo_path(path).resolve()) for path in args.labels],
        "source_layers": sorted(source_layers),
        "records_loaded": len(records),
        "records_scanned": sum(1 for row in records if str(row.get("layer") or "") in source_layers),
        "candidates_total": len(candidates),
        "accepted_total": len(accepted),
        "accepted_by_source_layer": dict(Counter(str(row.get("source_layer")) for row in accepted)),
        "accepted_by_reason": dict(Counter(str(row.get("accepted_reason") or "unknown") for row in accepted)),
        "accepted_by_review_target": dict(Counter(str(row.get("review_target_layer") or "unlabeled") for row in accepted)),
        "demoted_total": len(demoted),
        "demoted_by_reason": dict(Counter(str(row.get("demoted_reason") or "unknown") for row in demoted)),
        "demoted_by_previous_reason": dict(Counter(str(row.get("demoted_from_reason") or "unknown") for row in demoted)),
        "submask_reject_primary_counts": dict(
            Counter(str(row.get("submask_reject_primary") or "none") for row in candidates if not row.get("accepted"))
        ),
        "whole_component_reject_primary_counts": dict(
            Counter(str(row.get("whole_component_reject_primary") or "none") for row in candidates if not row.get("accepted"))
        ),
        "review_label_targets_loaded": dict(sorted(label_targets.items())),
        "reviewed_candidate_rows": len(labeled),
        "reviewed_accepted_rows": len(labeled_accepted),
        "reviewed_number_labels_in_scope": len(number_label_keys),
        "reviewed_number_labels_hit": len(accepted_number_keys),
        "reviewed_number_labels_missed": missed_number_keys,
        "reviewed_submask_number_labels_in_scope": len(review_submask_number_keys),
        "reviewed_submask_number_labels_hit": len(accepted_review_submask_keys),
        "reviewed_submask_number_labels_missed": missed_review_submask_keys,
        "reviewed_false_accepted_count": len(false_accepted),
        "reviewed_false_accepted": [
            {
                "paint_label": row.get("paint_label"),
                "source_layer": row.get("source_layer"),
                "component_index": row.get("component_index"),
                "target_layer": row.get("review_target_layer"),
                "label": row.get("review_label"),
                "bbox": row.get("bbox"),
                "area_px": row.get("area_px"),
            }
            for row in false_accepted[:50]
        ],
        "reviewed_demoted_false_number_risks_count": len(labeled_demoted_false_numbers),
        "reviewed_demoted_false_number_risks": [
            {
                "paint_label": row.get("paint_label"),
                "source_layer": row.get("source_layer"),
                "component_index": row.get("component_index"),
                "target_layer": row.get("review_target_layer"),
                "label": row.get("review_label"),
                "bbox": row.get("bbox"),
                "area_px": row.get("area_px"),
                "demoted_reason": row.get("demoted_reason"),
                "demoted_from_reason": row.get("demoted_from_reason"),
            }
            for row in labeled_demoted_false_numbers[:50]
        ],
        "demoted_vertical_word_stacks": demoted_vertical_word_stacks,
        "demoted_sponsor_logo_false_numbers": demoted_sponsor_logo_false_numbers,
        "missing_parent_masks": missing_parent_masks,
        "candidate_json": str(candidates_path.resolve()),
        "review_sheet": sheet_path,
        "runtime_hook": False,
        "runtime_decision": "Offline diagnostic only; accepted submasks need more reviewed-car pressure before Auto-build uses them.",
    }
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--components", nargs="+", required=True, help="component_records.json paths")
    parser.add_argument("--labels", nargs="*", default=[], help="optional reviewed component label JSON paths")
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--source-layers", nargs="+", default=["sponsors", "paint"], help="layers to scan")
    parser.add_argument("--close", type=int, default=1, help="HSV foreground close kernel radius")
    parser.add_argument("--min-piece-area", type=int, default=40, help="minimum foreground island area")
    parser.add_argument("--dark-value-max", type=float, default=0.34, help="black/dark digit value ceiling")
    parser.add_argument("--light-saturation-max", type=float, default=0.16, help="white digit saturation ceiling")
    parser.add_argument("--light-value-min", type=float, default=0.68, help="white digit value floor")
    parser.add_argument("--max-sheet-cards", type=int, default=96, help="maximum candidates drawn on review sheet")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_probe(args)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
