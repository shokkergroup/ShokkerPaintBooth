"""Evaluate Smart TGA race-number proposal recall on reviewed TGA boxes.

This is offline Smart TGA tooling. It measures whether the connected-component
proposal step finds the number boxes we already trust, before any classifier or
layer-building code gets involved. It does not affect Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from smart_tga_number_candidate_miner import WORK, _box_iou, _candidate_boxes, _read_rgb


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle65_arcachevy_reviewed_corpus_v1/manifest.json")
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_number_proposal_eval")
IOU_LEVELS = (0.25, 0.35, 0.50)


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:90] or "sample"


def _raw_xywh_to_xyxy(raw_box: list[int]) -> list[int]:
    x, y, w, h = [int(v) for v in raw_box]
    return [x, y, x + w, y + h]


def _as_xyxy(rec: dict[str, Any]) -> list[int] | None:
    raw = rec.get("raw_box")
    if isinstance(raw, list) and len(raw) == 4:
        return _raw_xywh_to_xyxy(raw)
    box = rec.get("box")
    if isinstance(box, list) and len(box) == 4:
        return [int(v) for v in box]
    return None


def _source_path(rec: dict[str, Any]) -> Path | None:
    for key in ("paint", "car_num", "car"):
        value = rec.get(key)
        if value:
            path = Path(value)
            if path.is_file():
                return path
    return None


def _source_bucket(rec: dict[str, Any]) -> str:
    source_kind = str(rec.get("source_kind") or "")
    if source_kind:
        return source_kind
    if rec.get("paint") and rec.get("source_queue"):
        return "reviewed_candidate_queue"
    if rec.get("car_num") and rec.get("car"):
        return "safe_overlay_pair"
    return "unknown_positive_source"


def _passes_folder(rec: dict[str, Any], prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    folder = str(rec.get("folder") or "")
    path = str(rec.get("paint") or rec.get("car_num") or rec.get("car") or "")
    haystack = f"{folder} {path}".lower()
    return any(prefix.lower() in haystack for prefix in prefixes)


def _edge_component_boxes(rgb: np.ndarray, max_boxes: int, mode: str) -> list[dict[str, Any]]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges_main = cv2.Canny(gray, 45, 135)
    edges_soft = cv2.Canny(gray, 25, 100)
    variants: list[tuple[str, np.ndarray, tuple[int, int], tuple[int, int], int]] = [
        ("default_shape", edges_main, (5, 5), (13, 9), 1),
        ("tight_strokes", edges_main, (3, 3), (7, 5), 1),
        ("wide_wordlike", edges_main, (5, 5), (23, 7), 1),
        ("tall_digits", edges_main, (5, 5), (9, 19), 1),
    ]
    if mode == "multi_soft":
        variants.extend(
            [
                ("soft_default", edges_soft, (5, 5), (13, 9), 1),
                ("soft_tall", edges_soft, (5, 5), (9, 21), 1),
            ]
        )

    boxes: list[dict[str, Any]] = []
    for variant_name, edges, dilate_kernel, close_kernel, iterations in variants:
        mask = cv2.dilate(edges, np.ones(dilate_kernel, np.uint8), iterations=iterations)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones(close_kernel, np.uint8))
        n, labels, stats, _cent = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
        for idx in range(1, n):
            x = int(stats[idx, cv2.CC_STAT_LEFT])
            y = int(stats[idx, cv2.CC_STAT_TOP])
            w = int(stats[idx, cv2.CC_STAT_WIDTH])
            h = int(stats[idx, cv2.CC_STAT_HEIGHT])
            area = int(stats[idx, cv2.CC_STAT_AREA])
            if w < 24 or h < 20 or w > 520 or h > 420:
                continue
            aspect = w / max(1.0, float(h))
            if aspect < 0.25 or aspect > 8.0:
                continue
            fill = area / float(w * h)
            if fill < 0.025 or fill > 0.86:
                continue
            edge_density = float((edges_main[y:y + h, x:x + w] > 0).mean())
            soft_edge_density = float((edges_soft[y:y + h, x:x + w] > 0).mean())
            sat_density = float((sat[y:y + h, x:x + w] > 55).mean())
            if max(edge_density, soft_edge_density) < 0.022:
                continue
            pad = int(max(w, h) * 0.18)
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(WORK, x + w + pad)
            y1 = min(WORK, y + h + pad)
            aspect_bonus = 1.0 - min(1.0, abs(np.log(max(0.2, min(6.0, aspect)))) / 2.2)
            size_bonus = min(1.0, (w * h) / float(150 * 150))
            score = (
                edge_density * 2.2
                + soft_edge_density * 0.9
                + sat_density * 0.55
                + aspect_bonus * 0.25
                + size_bonus * 0.18
            )
            boxes.append(
                {
                    "box": [x0, y0, x1, y1],
                    "raw_box": [x, y, w, h],
                    "area": area,
                    "fill": round(fill, 4),
                    "edge_density": round(edge_density, 4),
                    "soft_edge_density": round(soft_edge_density, 4),
                    "sat_density": round(sat_density, 4),
                    "aspect": round(aspect, 4),
                    "proposal_variant": variant_name,
                    "proposal_score": round(float(score), 6),
                }
            )

    boxes.sort(key=lambda b: float(b.get("proposal_score", 0.0)), reverse=True)
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        raw_xyxy = _raw_xywh_to_xyxy(box["raw_box"])
        if any(_box_iou(raw_xyxy, _raw_xywh_to_xyxy(existing["raw_box"])) >= 0.68 for existing in deduped):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _window_boxes(rgb: np.ndarray, max_boxes: int) -> list[dict[str, Any]]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges = cv2.Canny(gray, 30, 110)
    edge_integral = cv2.integral((edges > 0).astype(np.float32))
    sat_integral = cv2.integral((sat > 55).astype(np.float32))

    def isum(integral: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> float:
        return float(integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0])

    sizes: list[tuple[int, int]] = []
    for w, h in (
        (72, 56),
        (96, 76),
        (124, 96),
        (160, 120),
        (200, 150),
        (240, 180),
        (300, 220),
        (360, 260),
        (420, 300),
        (260, 260),
        (340, 340),
        (460, 380),
    ):
        sizes.append((w, h))
        if abs(w - h) > 20:
            sizes.append((h, w))

    boxes: list[dict[str, Any]] = []
    for w, h in sizes:
        step_x = max(20, w // 4)
        step_y = max(20, h // 4)
        for y in range(0, WORK - h + 1, step_y):
            for x in range(0, WORK - w + 1, step_x):
                area = float(w * h)
                edge_density = isum(edge_integral, x, y, x + w, y + h) / area
                if edge_density < 0.006:
                    continue
                sat_density = isum(sat_integral, x, y, x + w, y + h) / area
                aspect = w / float(h)
                aspect_bonus = 1.0 - min(1.0, abs(np.log(max(0.2, min(6.0, aspect)))) / 2.2)
                size_bonus = min(1.0, area / float(300 * 220))
                score = edge_density * 4.0 + sat_density * 0.35 + aspect_bonus * 0.12 + size_bonus * 0.20
                boxes.append(
                    {
                        "box": [x, y, x + w, y + h],
                        "raw_box": [x, y, w, h],
                        "area": int(area),
                        "fill": 1.0,
                        "edge_density": round(edge_density, 4),
                        "sat_density": round(sat_density, 4),
                        "aspect": round(aspect, 4),
                        "proposal_variant": "window",
                        "proposal_score": round(float(score), 6),
                    }
                )

    boxes.sort(key=lambda b: float(b.get("proposal_score", 0.0)), reverse=True)
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        if any(_box_iou(box["box"], existing["box"]) >= 0.74 for existing in deduped):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _focused_window_boxes(rgb: np.ndarray, seed_windows: list[dict[str, Any]], max_boxes: int) -> list[dict[str, Any]]:
    """Create tighter hypotheses inside broad windows that already cover number-like detail."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges_main = cv2.Canny(gray, 35, 115)
    edges_soft = cv2.Canny(gray, 22, 90)
    focus_mask = cv2.dilate(edges_soft, np.ones((3, 3), np.uint8), iterations=1)
    focus_mask = cv2.morphologyEx(focus_mask, cv2.MORPH_CLOSE, np.ones((11, 7), np.uint8))
    boxes: list[dict[str, Any]] = []
    parent_limit = min(len(seed_windows), max(60, max_boxes * 2))
    scales = (
        (1.18, 1.18),
        (1.38, 1.24),
        (1.24, 1.38),
        (1.65, 1.35),
        (1.35, 1.65),
        (2.05, 1.45),
        (1.45, 2.05),
    )
    for parent_index, seed in enumerate(seed_windows[:parent_limit]):
        raw = seed.get("raw_box")
        if isinstance(raw, list) and len(raw) == 4:
            px0, py0, px1, py1 = _raw_xywh_to_xyxy(raw)
        else:
            px0, py0, px1, py1 = [int(v) for v in seed.get("box", [0, 0, 0, 0])]
        px0 = max(0, min(WORK - 1, px0))
        py0 = max(0, min(WORK - 1, py0))
        px1 = max(px0 + 1, min(WORK, px1))
        py1 = max(py0 + 1, min(WORK, py1))
        pw = px1 - px0
        ph = py1 - py0
        if pw < 92 or ph < 68 or pw * ph < 9000:
            continue
        local = focus_mask[py0:py1, px0:px1]
        n, _labels, stats, _cent = cv2.connectedComponentsWithStats((local > 0).astype(np.uint8), 8)
        components: list[dict[str, Any]] = []
        for idx in range(1, n):
            x = int(stats[idx, cv2.CC_STAT_LEFT])
            y = int(stats[idx, cv2.CC_STAT_TOP])
            w = int(stats[idx, cv2.CC_STAT_WIDTH])
            h = int(stats[idx, cv2.CC_STAT_HEIGHT])
            area = int(stats[idx, cv2.CC_STAT_AREA])
            if w < 18 or h < 16 or w > pw * 0.96 or h > ph * 0.96:
                continue
            if w * h < 360:
                continue
            aspect = w / max(1.0, float(h))
            if aspect < 0.22 or aspect > 7.0:
                continue
            fill = area / float(max(1, w * h))
            if fill < 0.025 or fill > 0.82:
                continue
            ax0, ay0, ax1, ay1 = px0 + x, py0 + y, px0 + x + w, py0 + y + h
            edge_density = float((edges_main[ay0:ay1, ax0:ax1] > 0).mean())
            soft_edge_density = float((edges_soft[ay0:ay1, ax0:ax1] > 0).mean())
            sat_density = float((sat[ay0:ay1, ax0:ax1] > 55).mean())
            if max(edge_density, soft_edge_density) < 0.018 and sat_density < 0.12:
                continue
            aspect_bonus = 1.0 - min(1.0, abs(np.log(max(0.2, min(6.0, aspect)))) / 2.2)
            compact_bonus = 1.0 - min(1.0, (w * h) / float(max(1, pw * ph)))
            score = (
                edge_density * 2.8
                + soft_edge_density * 1.1
                + sat_density * 0.38
                + aspect_bonus * 0.18
                + compact_bonus * 0.16
                + float(seed.get("proposal_score", 0.0)) * 0.12
            )
            components.append(
                {
                    "x0": ax0,
                    "y0": ay0,
                    "x1": ax1,
                    "y1": ay1,
                    "w": w,
                    "h": h,
                    "fill": fill,
                    "edge_density": edge_density,
                    "soft_edge_density": soft_edge_density,
                    "sat_density": sat_density,
                    "aspect": aspect,
                    "score": float(score),
                    "parent_box": [px0, py0, pw, ph],
                    "parent_variant": seed.get("proposal_variant", "window"),
                    "parent_index": parent_index,
                }
            )
        components.sort(key=lambda c: c["score"], reverse=True)
        for comp in components[:4]:
            cx = (comp["x0"] + comp["x1"]) * 0.5
            cy = (comp["y0"] + comp["y1"]) * 0.5
            for scale_x, scale_y in scales:
                bw = max(38, min(620, int(round(comp["w"] * scale_x))))
                bh = max(30, min(520, int(round(comp["h"] * scale_y))))
                bx0 = max(0, min(WORK - 1, int(round(cx - bw * 0.5))))
                by0 = max(0, min(WORK - 1, int(round(cy - bh * 0.5))))
                bx1 = max(bx0 + 1, min(WORK, int(round(cx + bw * 0.5))))
                by1 = max(by0 + 1, min(WORK, int(round(cy + bh * 0.5))))
                bw = bx1 - bx0
                bh = by1 - by0
                if bw < 38 or bh < 30:
                    continue
                aspect = bw / max(1.0, float(bh))
                if aspect < 0.22 or aspect > 7.2:
                    continue
                area = bw * bh
                scale_penalty = 1.0 / max(1.0, scale_x * scale_y * 0.35)
                boxes.append(
                    {
                        "box": [bx0, by0, bx1, by1],
                        "raw_box": [bx0, by0, bw, bh],
                        "area": int(area),
                        "fill": round(min(1.0, comp["fill"] * scale_penalty), 4),
                        "edge_density": round(float((edges_main[by0:by1, bx0:bx1] > 0).mean()), 4),
                        "soft_edge_density": round(float((edges_soft[by0:by1, bx0:bx1] > 0).mean()), 4),
                        "sat_density": round(float((sat[by0:by1, bx0:bx1] > 55).mean()), 4),
                        "aspect": round(aspect, 4),
                        "proposal_variant": "focused_window",
                        "proposal_parent_box": comp["parent_box"],
                        "proposal_parent_variant": comp["parent_variant"],
                        "proposal_parent_index": comp["parent_index"],
                        "proposal_score": round(comp["score"] * (0.98 if scale_x <= 1.4 and scale_y <= 1.4 else 0.9), 6),
                    }
                )

    return _dedupe_ranked(boxes, max_boxes)


def _side_panel_boxes(rgb: np.ndarray, max_boxes: int) -> list[dict[str, Any]]:
    """Create side-number-sized boxes around high-contrast stroke clusters.

    Cycle 79's safe-overlay audit showed the strongest misses are not tiny
    glyph fragments; they are whole side-number panels that broad windows cover
    poorly and focused windows over-shrink. This proposal family intentionally
    grows from stroke clusters to likely race-number panel boxes.
    """
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges_soft = cv2.Canny(gray, 22, 95)
    edges_hard = cv2.Canny(gray, 55, 155)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(grad_x, grad_y)
    stroke_seed = ((edges_soft > 0) | (grad > 38)).astype(np.uint8) * 255
    kernels = (
        ("side_panel_wide", (7, 5), (31, 13), 1),
        ("side_panel_tall", (5, 7), (17, 29), 1),
        ("side_panel_block", (5, 5), (23, 23), 1),
        ("side_panel_loose", (9, 7), (43, 17), 1),
    )
    scales = (
        (1.12, 1.12),
        (1.32, 1.18),
        (1.55, 1.24),
        (1.24, 1.55),
        (1.85, 1.36),
        (1.36, 1.85),
    )
    boxes: list[dict[str, Any]] = []
    for variant_name, dilate_kernel, close_kernel, iterations in kernels:
        mask = cv2.dilate(stroke_seed, np.ones(dilate_kernel, np.uint8), iterations=iterations)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones(close_kernel, np.uint8))
        n, _labels, stats, _cent = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
        for idx in range(1, n):
            x = int(stats[idx, cv2.CC_STAT_LEFT])
            y = int(stats[idx, cv2.CC_STAT_TOP])
            w = int(stats[idx, cv2.CC_STAT_WIDTH])
            h = int(stats[idx, cv2.CC_STAT_HEIGHT])
            area = int(stats[idx, cv2.CC_STAT_AREA])
            if w < 42 or h < 32 or w > 650 or h > 510:
                continue
            if w * h > WORK * WORK * 0.22:
                continue
            aspect = w / max(1.0, float(h))
            if aspect < 0.26 or aspect > 7.2:
                continue
            fill = area / float(max(1, w * h))
            if fill < 0.025 or fill > 0.92:
                continue
            y1 = y + h
            x1 = x + w
            edge_density = float((edges_hard[y:y1, x:x1] > 0).mean())
            soft_edge_density = float((edges_soft[y:y1, x:x1] > 0).mean())
            sat_density = float((sat[y:y1, x:x1] > 55).mean())
            luma_std = float(gray[y:y1, x:x1].std() / 255.0)
            if max(edge_density, soft_edge_density) < 0.012 and luma_std < 0.08:
                continue
            aspect_bonus = 1.0 - min(1.0, abs(np.log(max(0.2, min(6.0, aspect)))) / 2.2)
            size_bonus = min(1.0, (w * h) / float(260 * 180))
            fill_bonus = 1.0 - min(1.0, abs(fill - 0.22) / 0.38)
            base_score = (
                edge_density * 2.6
                + soft_edge_density * 0.9
                + luma_std * 0.85
                + sat_density * 0.24
                + aspect_bonus * 0.18
                + size_bonus * 0.16
                + fill_bonus * 0.12
            )
            cx = x + w * 0.5
            cy = y + h * 0.5
            for scale_x, scale_y in scales:
                bw = max(54, min(700, int(round(w * scale_x))))
                bh = max(42, min(560, int(round(h * scale_y))))
                bx0 = max(0, min(WORK - 1, int(round(cx - bw * 0.5))))
                by0 = max(0, min(WORK - 1, int(round(cy - bh * 0.5))))
                bx1 = max(bx0 + 1, min(WORK, int(round(cx + bw * 0.5))))
                by1 = max(by0 + 1, min(WORK, int(round(cy + bh * 0.5))))
                bw = bx1 - bx0
                bh = by1 - by0
                if bw < 54 or bh < 42:
                    continue
                panel_aspect = bw / max(1.0, float(bh))
                if panel_aspect < 0.24 or panel_aspect > 7.4:
                    continue
                scale_penalty = 1.0 / max(1.0, scale_x * scale_y * 0.42)
                score = base_score * scale_penalty
                boxes.append(
                    {
                        "box": [bx0, by0, bx1, by1],
                        "raw_box": [bx0, by0, bw, bh],
                        "stroke_box": [x, y, w, h],
                        "area": int(area),
                        "fill": round(fill, 4),
                        "edge_density": round(edge_density, 4),
                        "soft_edge_density": round(soft_edge_density, 4),
                        "sat_density": round(sat_density, 4),
                        "aspect": round(panel_aspect, 4),
                        "proposal_variant": variant_name,
                        "proposal_score": round(float(score), 6),
                    }
                )

    boxes.sort(key=lambda b: float(b.get("proposal_score", 0.0)), reverse=True)
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        if any(_box_iou(box["box"], existing["box"]) >= 0.66 for existing in deduped):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _expanded_component_boxes(seed_boxes: list[dict[str, Any]], max_boxes: int) -> list[dict[str, Any]]:
    """Turn tight digit/logo components into whole-number panel hypotheses."""
    scales = (
        (1.35, 1.35),
        (1.65, 1.45),
        (1.45, 1.65),
        (1.95, 1.55),
        (1.55, 1.95),
        (2.35, 1.75),
        (1.75, 2.35),
    )
    boxes: list[dict[str, Any]] = []
    for seed in seed_boxes:
        raw = seed.get("raw_box")
        if isinstance(raw, list) and len(raw) == 4:
            x0, y0, x1, y1 = _raw_xywh_to_xyxy(raw)
        else:
            x0, y0, x1, y1 = [int(v) for v in seed.get("box", [0, 0, 0, 0])]
        w = max(1, x1 - x0)
        h = max(1, y1 - y0)
        if w < 16 or h < 16:
            continue
        cx = (x0 + x1) * 0.5
        cy = (y0 + y1) * 0.5
        base_score = float(seed.get("proposal_score", seed.get("edge_density", 0.0)))
        for sx, sy in scales:
            ew = max(36, min(620, int(round(w * sx))))
            eh = max(28, min(520, int(round(h * sy))))
            nx0 = max(0, min(WORK - 1, int(round(cx - ew * 0.5))))
            ny0 = max(0, min(WORK - 1, int(round(cy - eh * 0.5))))
            nx1 = max(nx0 + 1, min(WORK, int(round(cx + ew * 0.5))))
            ny1 = max(ny0 + 1, min(WORK, int(round(cy + eh * 0.5))))
            nw = nx1 - nx0
            nh = ny1 - ny0
            if nw < 36 or nh < 28:
                continue
            aspect = nw / max(1.0, float(nh))
            if aspect < 0.25 or aspect > 8.0:
                continue
            expanded = dict(seed)
            expanded.update(
                {
                    "box": [nx0, ny0, nx1, ny1],
                    "raw_box": [nx0, ny0, nw, nh],
                    "area": int(nw * nh),
                    "fill": min(1.0, float(seed.get("fill", 0.0)) / max(0.18, sx * sy * 0.35)),
                    "aspect": round(aspect, 4),
                    "proposal_variant": f"expanded_{seed.get('proposal_variant', 'component')}",
                    "proposal_parent_box": seed.get("raw_box") or seed.get("box"),
                    "proposal_score": round(base_score * 0.92, 6),
                }
            )
            boxes.append(expanded)

    boxes.sort(key=lambda b: float(b.get("proposal_score", 0.0)), reverse=True)
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        xyxy = _raw_xywh_to_xyxy(box["raw_box"])
        if any(_box_iou(xyxy, _raw_xywh_to_xyxy(existing["raw_box"])) >= 0.72 for existing in deduped):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _dedupe_ranked(boxes: list[dict[str, Any]], max_boxes: int) -> list[dict[str, Any]]:
    boxes.sort(key=lambda b: float(b.get("proposal_score", b.get("edge_density", 0.0))), reverse=True)
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        raw = box.get("raw_box")
        xyxy = _raw_xywh_to_xyxy(raw) if isinstance(raw, list) and len(raw) == 4 else box["box"]
        if any(
            _box_iou(
                xyxy,
                _raw_xywh_to_xyxy(existing["raw_box"])
                if isinstance(existing.get("raw_box"), list) and len(existing["raw_box"]) == 4
                else existing["box"],
            )
            >= 0.72
            for existing in deduped
        ):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _dedupe_ordered(boxes: list[dict[str, Any]], max_boxes: int) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    for box in boxes:
        raw = box.get("raw_box")
        xyxy = _raw_xywh_to_xyxy(raw) if isinstance(raw, list) and len(raw) == 4 else box["box"]
        if any(
            _box_iou(
                xyxy,
                _raw_xywh_to_xyxy(existing["raw_box"])
                if isinstance(existing.get("raw_box"), list) and len(existing["raw_box"]) == 4
                else existing["box"],
            )
            >= 0.72
            for existing in deduped
        ):
            continue
        deduped.append(box)
        if len(deduped) >= max_boxes:
            break
    return deduped


def _proposal_boxes(rgb: np.ndarray, max_boxes: int, variant: str) -> list[dict[str, Any]]:
    if variant == "default":
        return _candidate_boxes(rgb, max_boxes)
    if variant in {"multi", "multi_soft"}:
        return _edge_component_boxes(rgb, max_boxes, variant)
    if variant == "window":
        return _window_boxes(rgb, max_boxes)
    if variant == "hybrid":
        component_budget = min(max_boxes, max(14, max_boxes // 4))
        grouped_budget = min(max_boxes, max(10, max_boxes // 4))
        window_budget = max_boxes
        boxes = _candidate_boxes(rgb, component_budget)
        boxes.extend(_edge_component_boxes(rgb, grouped_budget, "multi_soft"))
        boxes.extend(_window_boxes(rgb, window_budget))
        return _dedupe_ordered(boxes, max_boxes)
    if variant == "hybrid_expand":
        component_budget = min(max_boxes, max(18, max_boxes // 5))
        grouped_budget = min(max_boxes, max(16, max_boxes // 5))
        base = _candidate_boxes(rgb, component_budget)
        grouped = _edge_component_boxes(rgb, grouped_budget, "multi_soft")
        expanded = _expanded_component_boxes(base + grouped, max_boxes)
        windows = _window_boxes(rgb, max(20, max_boxes // 2))
        return _dedupe_ordered(base + grouped + expanded + windows, max_boxes)
    if variant == "hybrid_focus":
        component_budget = min(max_boxes, max(18, max_boxes // 5))
        grouped_budget = min(max_boxes, max(18, max_boxes // 5))
        window_budget = max(max_boxes, 360)
        base = _candidate_boxes(rgb, component_budget)
        grouped = _edge_component_boxes(rgb, grouped_budget, "multi_soft")
        windows = _window_boxes(rgb, window_budget)
        focused = _focused_window_boxes(rgb, windows, max_boxes)
        return _dedupe_ordered(base + grouped + focused + windows, max_boxes)
    if variant == "hybrid_side_panel":
        component_budget = min(max_boxes, max(18, max_boxes // 6))
        grouped_budget = min(max_boxes, max(18, max_boxes // 6))
        side_budget = min(max_boxes, max(72, max_boxes // 2))
        window_budget = max(max_boxes, 360)
        base = _candidate_boxes(rgb, component_budget)
        grouped = _edge_component_boxes(rgb, grouped_budget, "multi_soft")
        side_panels = _side_panel_boxes(rgb, side_budget)
        windows = _window_boxes(rgb, window_budget)
        return _dedupe_ordered(base + grouped + side_panels + windows, max_boxes)
    raise ValueError(f"unsupported variant: {variant}")


def _best_match(gt: list[int], candidates: list[dict[str, Any]]) -> tuple[float, dict[str, Any] | None]:
    best_iou = 0.0
    best: dict[str, Any] | None = None
    for cand in candidates:
        raw = cand.get("raw_box")
        if isinstance(raw, list) and len(raw) == 4:
            cand_box = _raw_xywh_to_xyxy(raw)
        else:
            cand_box = [int(v) for v in cand.get("box", [0, 0, 0, 0])]
        iou = _box_iou(gt, cand_box)
        if iou > best_iou:
            best_iou = iou
            best = cand
    return best_iou, best


def _aggregate(records: list[dict[str, Any]], variant: str, max_boxes: int) -> dict[str, Any]:
    key = f"{variant}_{max_boxes}"
    best_values = [float(rec["results"][key]["best_iou"]) for rec in records]
    aggregate: dict[str, Any] = {
        "samples": len(records),
        "variant": variant,
        "max_boxes": max_boxes,
        "median_best_iou": round(float(np.median(best_values)) if best_values else 0.0, 6),
        "mean_best_iou": round(float(np.mean(best_values)) if best_values else 0.0, 6),
    }
    for threshold in IOU_LEVELS:
        covered = sum(1 for value in best_values if value >= threshold)
        aggregate[f"recall_iou_{threshold:.2f}"] = round(covered / max(1, len(best_values)), 6)
        aggregate[f"covered_iou_{threshold:.2f}"] = covered
    return aggregate


def _aggregate_by(records: list[dict[str, Any]], variant: str, max_boxes: int, field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        groups.setdefault(str(rec.get(field) or "unknown"), []).append(rec)
    return {name: _aggregate(items, variant, max_boxes) for name, items in sorted(groups.items())}


def _crop_overlay(rgb: np.ndarray, gt: list[int], best: dict[str, Any] | None, label: str, best_iou: float) -> Image.Image:
    boxes = [gt]
    if best:
        raw = best.get("raw_box")
        boxes.append(_raw_xywh_to_xyxy(raw) if isinstance(raw, list) and len(raw) == 4 else best.get("box", gt))
    x0 = max(0, min(int(b[0]) for b in boxes) - 44)
    y0 = max(0, min(int(b[1]) for b in boxes) - 44)
    x1 = min(WORK, max(int(b[2]) for b in boxes) + 44)
    y1 = min(WORK, max(int(b[3]) for b in boxes) + 44)
    crop = Image.fromarray(rgb[y0:y1, x0:x1]).convert("RGB")
    draw = ImageDraw.Draw(crop)
    gt_local = [gt[0] - x0, gt[1] - y0, gt[2] - x0, gt[3] - y0]
    draw.rectangle(gt_local, outline=(255, 80, 80), width=4)
    if best:
        raw = best.get("raw_box")
        bx = _raw_xywh_to_xyxy(raw) if isinstance(raw, list) and len(raw) == 4 else [int(v) for v in best.get("box", gt)]
        best_local = [bx[0] - x0, bx[1] - y0, bx[2] - x0, bx[3] - y0]
        draw.rectangle(best_local, outline=(255, 225, 50), width=3)
    draw.text((6, 6), f"{best_iou:.3f} {label[:36]}", fill=(255, 255, 255))
    return crop


def _contact_sheet(rows: list[dict[str, Any]], out_path: Path, title: str, result_key: str) -> None:
    if not rows:
        return
    cols = 5
    cell_w = 230
    cell_h = 216
    rows_count = int(np.ceil(len(rows) / cols))
    sheet = Image.new("RGB", (cols * cell_w, rows_count * cell_h), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(rows):
        rgb = _read_rgb(Path(rec["source_path"]))
        result = rec["results"][result_key]
        img = _crop_overlay(
            rgb,
            rec["gt_box"],
            result.get("best_candidate"),
            f"{rec.get('folder') or Path(rec['source_path']).parent.name}",
            float(result["best_iou"]),
        )
        img.thumbnail((210, 164), Image.Resampling.LANCZOS)
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        sheet.paste(img, (x + 10, y + 28))
        draw.text((x + 7, y + 6), f"#{idx:02d} IoU {float(result['best_iou']):.3f}", fill=(255, 230, 150))
        draw.text((x + 7, y + 196), str(rec.get("folder") or "")[:32], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise ValueError("manifest must be a list")
    args.output.mkdir(parents=True, exist_ok=True)

    positives: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for idx, rec in enumerate(manifest):
        if rec.get("label") != "number":
            continue
        if not _passes_folder(rec, args.folder_prefix):
            continue
        gt = _as_xyxy(rec)
        source = _source_path(rec)
        if not gt or not source:
            skipped.append({"index": idx, "reason": "missing_gt_or_source", "record": rec})
            continue
        positives.append(
            {
                "manifest_index": idx,
                "source_path": str(source.resolve()),
                "folder": rec.get("folder") or source.parent.name,
                "source_bucket": _source_bucket(rec),
                "gt_box": gt,
                "record_file": rec.get("file"),
                "results": {},
            }
        )

    cache: dict[str, np.ndarray] = {}
    candidate_cache: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in positives:
        path = row["source_path"]
        if path not in cache:
            cache[path] = _read_rgb(Path(path))
        rgb = cache[path]
        for variant in args.variant:
            for max_boxes in args.max_boxes:
                cand_key = (path, variant, max_boxes)
                if cand_key not in candidate_cache:
                    candidate_cache[cand_key] = _proposal_boxes(rgb, max_boxes, variant)
                candidates = candidate_cache[cand_key]
                best_iou, best = _best_match(row["gt_box"], candidates)
                row["results"][f"{variant}_{max_boxes}"] = {
                    "best_iou": round(best_iou, 6),
                    "best_candidate": best,
                    "candidate_count": len(candidates),
                }

    summary: dict[str, Any] = {
        "manifest": str(args.manifest),
        "output": str(args.output.resolve()),
        "positive_records": len(positives),
        "skipped_records": len(skipped),
        "variants": args.variant,
        "max_boxes": args.max_boxes,
        "iou_levels": list(IOU_LEVELS),
        "overall": {},
        "by_source_bucket": {},
        "by_folder": {},
        "notes": [
            "Reviewed-candidate positives are partially biased because earlier miner proposals discovered them.",
            "Safe-overlay-pair positives are the better recall signal for independently labeled number boxes.",
        ],
    }
    for variant in args.variant:
        for max_boxes in args.max_boxes:
            result_key = f"{variant}_{max_boxes}"
            summary["overall"][result_key] = _aggregate(positives, variant, max_boxes)
            summary["by_source_bucket"][result_key] = _aggregate_by(positives, variant, max_boxes, "source_bucket")
            summary["by_folder"][result_key] = _aggregate_by(positives, variant, max_boxes, "folder")
            misses = [
                rec
                for rec in positives
                if float(rec["results"][result_key]["best_iou"]) < args.miss_iou
            ][: args.sheet_items]
            _contact_sheet(
                misses,
                args.output / f"misses_{result_key}_iou{str(args.miss_iou).replace('.', '')}.png",
                f"Smart TGA proposal misses: {result_key} IoU<{args.miss_iou}",
                result_key,
            )
            low = sorted(positives, key=lambda rec: float(rec["results"][result_key]["best_iou"]))[: args.sheet_items]
            _contact_sheet(
                low,
                args.output / f"lowest_iou_{result_key}.png",
                f"Smart TGA lowest proposal IoU: {result_key}",
                result_key,
            )

    (args.output / "proposal_records.json").write_text(json.dumps(positives, indent=2), encoding="utf-8")
    (args.output / "skipped_records.json").write_text(json.dumps(skipped, indent=2), encoding="utf-8")
    (args.output / "proposal_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--folder-prefix", action="append", default=[])
    parser.add_argument(
        "--variant",
        action="append",
        choices=[
            "default",
            "multi",
            "multi_soft",
            "window",
            "hybrid",
            "hybrid_expand",
            "hybrid_focus",
            "hybrid_side_panel",
        ],
        default=None,
    )
    parser.add_argument("--max-boxes", type=int, action="append", default=None)
    parser.add_argument("--miss-iou", type=float, default=0.25)
    parser.add_argument("--sheet-items", type=int, default=45)
    args = parser.parse_args()
    args.variant = args.variant or ["default", "multi", "multi_soft"]
    args.max_boxes = args.max_boxes or [14, 24, 40]
    return args


def main() -> None:
    summary = evaluate(parse_args())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
