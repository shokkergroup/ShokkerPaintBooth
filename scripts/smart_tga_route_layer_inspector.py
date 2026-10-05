"""Inspect `/api/auto-layers` output for one or more real Smart TGA files.

This is offline Smart TGA tooling. It calls the Flask test client, decodes the
Auto-build layer masks, writes per-layer PNGs/overlays, and exports component
records/contact sheets for Numbers, Sponsors, Template, Brand Graphics, and
Paint. It is meant for one-car-at-a-time quality work without touching the
running app server.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_route_layer_inspector")
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LAYER_ORDER = ("numbers", "sponsors", "template", "brand_graphics", "paint")
LAYER_COLORS = {
    "numbers": (255, 45, 45, 185),
    "sponsors": (55, 95, 255, 150),
    "template": (45, 220, 90, 150),
    "brand_graphics": (255, 170, 30, 150),
    "paint": (210, 210, 210, 35),
}


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:100] or "sample"


def _decode_data_url_mask(data_url: str, size: tuple[int, int] | None = None) -> np.ndarray:
    raw = base64.b64decode(data_url.split(",", 1)[1])
    img = Image.open(io.BytesIO(raw)).convert("L")
    if size and img.size != size:
        img = img.resize(size, Image.Resampling.NEAREST)
    return np.asarray(img) > 127


def _parse_worker_env(items: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"--worker-env must be KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"--worker-env has an empty key: {item!r}")
        env[key] = value
    return env


def _route_client(args: argparse.Namespace):
    args.worker_env_map = _parse_worker_env(args.worker_env)
    for key, value in args.worker_env_map.items():
        os.environ[key] = value
    if args.no_gpu_cache:
        os.environ["SPB_SMART_TGA_GPU_CACHE"] = "0"
    if args.disable_gpu:
        os.environ["SPB_SMART_TGA_GPU"] = "0"
    os.environ.setdefault("SPB_SMART_TGA_COMPANION_DECALS", "1")
    os.environ.setdefault("SPB_SMART_TGA_COMPANION_DECAL_RGB_FALLBACK", "1")
    os.environ.setdefault("SPB_SMART_TGA_COMPANION_DECAL_MIN", "0.00025")
    import server

    server.app.config["TESTING"] = True
    return server.app.test_client()


def _post_auto_layers(client: Any, paint: Path, args: argparse.Namespace) -> tuple[dict[str, Any], float, int]:
    car_hint_path = str(args.car_hint_path or paint)
    payload = {
        "paint_file": str(paint),
        "paint_file_hint": str(paint),
        "car_hint_path": car_hint_path,
        "preview_size": args.preview_size,
        "brand_graphics_merge": args.brand_graphics_merge,
    }
    start = time.perf_counter()
    response = client.post("/api/auto-layers", json=payload, headers={"X-Shokker-Internal": "1"})
    elapsed = time.perf_counter() - start
    return response.get_json() or {}, elapsed, int(response.status_code)


def _read_source(path: Path, size: tuple[int, int]) -> Image.Image:
    return Image.open(path).convert("RGB").resize(size, Image.Resampling.LANCZOS)


def _write_mask_png(mask: np.ndarray, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask.astype(np.uint8) * 255, "L").save(path)
    return str(path.resolve())


def _write_overlay(source: Image.Image, masks: dict[str, np.ndarray], path: Path) -> str:
    overlay = source.convert("RGBA")
    for layer in ("paint", "brand_graphics", "template", "sponsors", "numbers"):
        mask = masks.get(layer)
        if mask is None:
            continue
        tint = Image.new("RGBA", overlay.size, LAYER_COLORS[layer])
        overlay.alpha_composite(Image.composite(tint, Image.new("RGBA", overlay.size, (0, 0, 0, 0)), Image.fromarray(mask.astype(np.uint8) * 255, "L")))
    path.parent.mkdir(parents=True, exist_ok=True)
    overlay.convert("RGB").save(path)
    return str(path.resolve())


def _write_ocr_region_overlay(source: Image.Image, shadow: dict[str, Any], path: Path) -> str | None:
    samples = list((shadow or {}).get("ocr_region_samples") or ())
    if not samples:
        return None
    canvas = source.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    for sample in samples:
        polygon = sample.get("polygon") or ()
        if len(polygon) < 3:
            continue
        points = [(int(round(point[0])), int(round(point[1]))) for point in polygon]
        mirrored = bool(sample.get("mirrored"))
        color = (255, 70, 210) if mirrored else (70, 210, 255)
        draw.line(points + [points[0]], fill=color, width=3)
        x, y = points[0]
        text = str(sample.get("text") or "?")[:24]
        label = f"{'M' if mirrored else 'N'} {float(sample.get('confidence') or 0):.2f} {text}"
        box = draw.textbbox((x, y), label)
        label_y = max(0, y - (box[3] - box[1]) - 4)
        draw.rectangle((x, label_y, x + (box[2] - box[0]) + 5, y), fill=(8, 12, 18))
        draw.text((x + 2, label_y + 1), label, fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return str(path.resolve())


def _component_role(layer: str, area_frac: float, bbox_w: float, bbox_h: float, aspect: float, fill: float) -> str:
    if layer == "numbers":
        if area_frac < 0.00008:
            return "tiny_number_fragment"
        if aspect > 8 or aspect < 0.12:
            return "number_stroke_or_textline_review"
        return "number_candidate"
    if layer == "sponsors":
        if bbox_w > 0.85 and bbox_h > 0.20:
            return "large_sponsor_panel_or_livery_review"
        if area_frac <= 0.0012:
            return "small_contingency_or_logo"
        if aspect >= 8 and bbox_h <= 0.08:
            return "sponsor_textline_or_stripe"
        if fill > 0.38 and area_frac >= 0.018:
            return "large_sponsor_panel"
        return "sponsor_logo_or_graphic"
    if layer == "template":
        if bbox_w > 0.85 and bbox_h > 0.85:
            return "template_whole_canvas_review"
        if area_frac <= 0.001:
            return "small_template_detail"
        return "template_part_candidate"
    if layer == "brand_graphics":
        return "brand_graphic_candidate"
    if area_frac >= 0.10:
        return "paint_livery_mass"
    return "paint_component"


def _component_crop(source: Image.Image, mask: np.ndarray, bbox: list[int], label: str, path: Path) -> str:
    x, y, bw, bh = [int(v) for v in bbox]
    w, h = source.size
    pad = 24
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    crop = source.crop((x0, y0, x1, y1)).convert("RGBA")
    local = mask[y0:y1, x0:x1]
    tint = Image.new("RGBA", crop.size, (255, 255, 255, 170))
    crop.alpha_composite(Image.composite(tint, Image.new("RGBA", crop.size, (0, 0, 0, 0)), Image.fromarray(local.astype(np.uint8) * 255, "L")))
    draw = ImageDraw.Draw(crop)
    draw.rectangle((x - x0, y - y0, x + bw - x0 - 1, y + bh - y0 - 1), outline=(255, 50, 180, 255), width=3)
    draw.text((4, 4), label[:30], fill=(255, 255, 120, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    crop.convert("RGB").save(path)
    return str(path.resolve())


def _bbox_crop(source: Image.Image, bbox: list[int], label: str, path: Path) -> str:
    x, y, bw, bh = [int(v) for v in bbox]
    w, h = source.size
    pad = 24
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    crop = source.crop((x0, y0, x1, y1)).convert("RGBA")
    draw = ImageDraw.Draw(crop)
    draw.rectangle((x - x0, y - y0, x + bw - x0 - 1, y + bh - y0 - 1), outline=(255, 210, 40, 255), width=3)
    draw.text((4, 4), label[:36], fill=(255, 255, 120, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    crop.convert("RGB").save(path)
    return str(path.resolve())


def _component_features(source_rgb: np.ndarray, comp_mask: np.ndarray, bbox: list[int], area: int) -> dict[str, Any]:
    x, y, bw, bh = [int(v) for v in bbox]
    crop = source_rgb[y:y + bh, x:x + bw]
    crop_mask = comp_mask[y:y + bh, x:x + bw]
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
    mask_area = max(1, int(crop_mask.sum()))

    return {
        "mean_rgb": [round(float(v), 3) for v in rgb_mean],
        "std_rgb": [round(float(v), 3) for v in rgb_std],
        "mean_saturation": round(float(hsv_pixels[:, 1].mean()) / 255.0, 4),
        "mean_value": round(float(hsv_pixels[:, 2].mean()) / 255.0, 4),
        "edge_density": round(float((edges > 0)[crop_mask].sum()) / float(mask_area), 4),
        "color_std": round(float(rgb_std.mean()) / 255.0, 4),
    }


def _components_for_layer(source: Image.Image, layer: str, mask: np.ndarray, sample_dir: Path) -> list[dict[str, Any]]:
    h, w = mask.shape[:2]
    source_rgb = np.asarray(source)
    n, labels, stats, cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    records: list[dict[str, Any]] = []
    min_area = 20 if layer != "paint" else max(64, int(0.0001 * w * h))
    for idx in range(1, n):
        area_px = int(stats[idx, cv2.CC_STAT_AREA])
        if area_px < min_area:
            continue
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        bw = int(stats[idx, cv2.CC_STAT_WIDTH])
        bh = int(stats[idx, cv2.CC_STAT_HEIGHT])
        area_frac = area_px / float(w * h)
        bbox_w = bw / float(w)
        bbox_h = bh / float(h)
        aspect = bw / float(max(1, bh))
        fill = area_px / float(max(1, bw * bh))
        role = _component_role(layer, area_frac, bbox_w, bbox_h, aspect, fill)
        comp_mask = labels == idx
        rec = {
            "layer": layer,
            "component_index": len(records),
            "area_px": area_px,
            "area_frac": round(area_frac, 7),
            "bbox": [x, y, bw, bh],
            "bbox_w_frac": round(bbox_w, 5),
            "bbox_h_frac": round(bbox_h, 5),
            "aspect": round(aspect, 4),
            "fill": round(fill, 4),
            "centroid_x": round(float(cent[idx][0]) / float(w), 4),
            "centroid_y": round(float(cent[idx][1]) / float(h), 4),
            "role_guess": role,
        }
        rec.update(_component_features(source_rgb, comp_mask, rec["bbox"], area_px))
        crop_path = sample_dir / "component_crops" / layer / f"{len(records):03d}_{_safe_name(role)}.png"
        rec["crop_file"] = _component_crop(source, comp_mask, rec["bbox"], f"{layer}:{role}", crop_path)
        records.append(rec)
    return records


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> str | None:
    if not records:
        return None
    cols = 5
    cell = 220
    header_h = 30
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, header_h + rows * cell), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records[: cols * max(rows, 1)]):
        x = (idx % cols) * cell
        y = header_h + (idx // cols) * cell
        img = Image.open(rec["crop_file"]).convert("RGB").resize((158, 158), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 31, y + 24))
        role = str(rec.get("role_guess") or rec.get("review_reason") or "component")
        draw.text((x + 7, y + 5), f"{rec['layer']} {role}"[:33], fill=(255, 230, 160))
        bbox_w = rec.get("bbox_w_frac")
        if bbox_w is None and rec.get("bbox"):
            bbox_w = float(rec["bbox"][2]) / float(max(1, Image.open(rec["crop_file"]).size[0]))
        detail = f"a={float(rec.get('area_frac', 0.0)):.5f} bw={float(bbox_w or 0.0):.2f} ar={float(rec.get('aspect', 0.0)):.1f}"
        draw.text((x + 7, y + 190), detail[:33], fill=(190, 210, 255))
        draw.text((x + 7, y + 206), str(rec.get("paint_label") or "")[:33], fill=(220, 220, 220))
    draw.text((8, 8), title[:120], fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return str(out_path.resolve())


def _write_guard_visual_artifacts(source: Image.Image, record: dict[str, Any], sample_dir: Path) -> None:
    guard_records: list[dict[str, Any]] = []
    guard_sheets: dict[str, str] = {}
    for key, guard in sorted(record.items()):
        if not key.startswith("route_") or not key.endswith("_guard"):
            continue
        if not isinstance(guard, dict) or guard.get("status") != "applied":
            continue
        guard_name = key[len("route_"):-len("_guard")]
        per_guard: list[dict[str, Any]] = []
        for idx, component in enumerate(guard.get("components") or []):
            bbox = component.get("bbox")
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            reason = str(component.get("reason") or guard_name)
            rec = {
                "layer": "guard",
                "guard": guard_name,
                "component_index": idx,
                "area_px": int(component.get("area") or 0),
                "area_frac": float(component.get("area_frac") or 0.0),
                "bbox": [int(v) for v in bbox],
                "bbox_w_frac": round(float(bbox[2]) / float(max(1, source.size[0])), 5),
                "bbox_h_frac": round(float(bbox[3]) / float(max(1, source.size[1])), 5),
                "aspect": round(float(max(bbox[2], bbox[3])) / float(max(1, min(bbox[2], bbox[3]))), 4),
                "role_guess": f"{guard_name}:{reason}",
                "reason": reason,
                "paint_label": record.get("paint_label"),
            }
            crop_path = sample_dir / "guard_crops" / guard_name / f"{idx:03d}_{_safe_name(reason)}.png"
            rec["crop_file"] = _bbox_crop(source, rec["bbox"], f"{guard_name}:{reason}", crop_path)
            per_guard.append(rec)
            guard_records.append(rec)
        sheet = _contact_sheet(
            per_guard,
            sample_dir / "guard_sheets" / f"{guard_name}.png",
            f"{record['paint_label']} {guard_name} guard components",
        )
        if sheet:
            guard_sheets[guard_name] = sheet
    if guard_records:
        guard_records_path = sample_dir / "guard_component_records.json"
        guard_records_path.write_text(json.dumps(guard_records, indent=2), encoding="utf-8")
        record["guard_component_records"] = str(guard_records_path.resolve())
        record["guard_component_count"] = len(guard_records)
    if guard_sheets:
        record["guard_component_sheets"] = guard_sheets


def _component_color_fractions(source_rgb: np.ndarray, comp_mask: np.ndarray, bbox: list[int]) -> dict[str, float]:
    x, y, bw, bh = [int(v) for v in bbox]
    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if not local.any():
        return {"red": 0.0, "warm": 0.0, "white": 0.0, "colored": 0.0, "edge": 0.0, "dark": 0.0}
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 120)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))
    warm = (((hue <= 42) | (hue >= 170)) & (sat > 80) & (val > 55))
    white = (sat < 70) & (val > 132)
    colored = (sat > 75) & (val > 70)
    dark = val < 84
    denom = float(max(1, int(local.sum())))
    return {
        "red": round(float((red & local).sum()) / denom, 4),
        "warm": round(float((warm & local).sum()) / denom, 4),
        "white": round(float((white & local).sum()) / denom, 4),
        "colored": round(float((colored & local).sum()) / denom, 4),
        "edge": round(float(((edges > 0) & local).sum()) / denom, 4),
        "dark": round(float((dark & local).sum()) / denom, 4),
    }


def _is_repeated_large_number_graphic_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    bbox_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for repeated same-scale number art already kept in Numbers."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.008 <= area_frac <= 0.040
        and 0.010 <= bbox_frac <= 0.060
        and 85 <= bw <= 360
        and 75 <= bh <= 260
        and 1.0 <= aspect <= 2.6
        and 0.42 <= fill <= 0.97
        and color["edge"] >= 0.10
    ):
        return False

    local = comp_mask[y:y + bh, x:x + bw]
    if local.size == 0 or not local.any():
        return False
    current_shape = cv2.resize(local.astype(np.uint8), (64, 64), interpolation=cv2.INTER_NEAREST) > 0
    cx = x + bw / 2.0
    cy = y + bh / 2.0
    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])

    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area <= 0 or ow <= 0 or oh <= 0:
            continue
        other_fill = other_area / float(max(1, ow * oh))
        other_bbox_frac = (ow * oh) / float(max(1, source_rgb.shape[0] * source_rgb.shape[1]))
        other_aspect = max(ow / float(max(1, oh)), oh / float(max(1, ow)))
        if not (
            0.008 <= (other_area / float(max(1, source_rgb.shape[0] * source_rgb.shape[1]))) <= 0.040
            and 0.010 <= other_bbox_frac <= 0.060
            and 85 <= ow <= 360
            and 75 <= oh <= 260
            and 1.0 <= other_aspect <= 2.6
            and 0.42 <= other_fill <= 0.97
        ):
            continue

        area_ratio = max(area_px, other_area) / float(max(1, min(area_px, other_area)))
        width_ratio = max(bw, ow) / float(max(1, min(bw, ow)))
        height_ratio = max(bh, oh) / float(max(1, min(bh, oh)))
        if area_ratio > 1.22 or width_ratio > 1.22 or height_ratio > 1.22:
            continue
        if abs(fill - other_fill) > 0.11 or abs(aspect - other_aspect) > 0.22:
            continue

        ocx = ox + ow / 2.0
        ocy = oy + oh / 2.0
        x_sep = abs(ocx - cx)
        y_sep = abs(ocy - cy)
        separated_same_column = x_sep <= max(bw, ow) * 0.55 and y_sep >= max(bh, oh) * 1.60
        separated_same_row = y_sep <= max(bh, oh) * 0.55 and x_sep >= max(bw, ow) * 1.60
        if not (separated_same_column or separated_same_row or (x_sep * x_sep + y_sep * y_sep) ** 0.5 >= 230.0):
            continue

        other_mask = labels == other_idx
        other_color = _component_color_fractions(source_rgb, other_mask, [ox, oy, ow, oh])
        if any(abs(color[key] - other_color[key]) > limit for key, limit in (
            ("white", 0.10),
            ("colored", 0.12),
            ("edge", 0.08),
            ("dark", 0.10),
            ("red", 0.14),
            ("warm", 0.14),
        )):
            continue

        other_local = other_mask[oy:oy + oh, ox:ox + ow]
        other_shape = cv2.resize(other_local.astype(np.uint8), (64, 64), interpolation=cv2.INTER_NEAREST) > 0
        union = float(np.logical_or(current_shape, other_shape).sum())
        if union <= 0:
            continue
        shape_iou = float(np.logical_and(current_shape, other_shape).sum()) / union
        if shape_iou >= 0.54:
            return True

    return False


def _is_multi_position_race_number_art_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    bbox_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for varied-scale race-number art already correctly kept in Numbers."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0045 <= area_frac <= 0.040
        and 0.006 <= bbox_frac <= 0.065
        and 80 <= bw <= 370
        and 70 <= bh <= 270
        and 0.95 <= aspect <= 3.05
        and 0.45 <= fill <= 0.86
        and color["edge"] >= 0.115
        and color["dark"] <= 0.68
    ):
        return False

    canvas_area = float(max(1, source_rgb.shape[0] * source_rgb.shape[1]))
    context_large = 0
    context_small = 0
    cx = x + bw / 2.0
    cy = y + bh / 2.0
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area < 650 or ow <= 0 or oh <= 0:
            continue
        other_area_frac = other_area / canvas_area
        other_bbox_frac = (ow * oh) / canvas_area
        other_fill = other_area / float(max(1, ow * oh))
        other_aspect = max(ow / float(max(1, oh)), oh / float(max(1, ow)))
        if not (
            0.0006 <= other_area_frac <= 0.045
            and 0.00075 <= other_bbox_frac <= 0.070
            and 18 <= ow <= 380
            and 22 <= oh <= 310
            and 0.40 <= other_fill <= 0.98
            and other_aspect <= 4.35
        ):
            continue
        ox_c = ox + ow / 2.0
        oy_c = oy + oh / 2.0
        if ((ox_c - cx) * (ox_c - cx) + (oy_c - cy) * (oy_c - cy)) ** 0.5 < 150.0:
            continue

        other_mask = labels == other_idx
        other_color = _component_color_fractions(source_rgb, other_mask, [ox, oy, ow, oh])
        if other_color["edge"] < 0.085 or other_color["dark"] > 0.78:
            continue
        if abs(color["white"] - other_color["white"]) > 0.34:
            continue
        if abs(color["colored"] - other_color["colored"]) > 0.40:
            continue
        if abs(color["dark"] - other_color["dark"]) > 0.38:
            continue
        if other_area_frac >= 0.0045 and other_bbox_frac >= 0.006 and ow >= 80 and oh >= 65:
            context_large += 1
        else:
            context_small += 1

    return context_large >= 2 or (context_large >= 1 and context_small >= 1)


def _is_paired_dark_panel_micro_sponsor(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    color: dict[str, float],
) -> bool:
    """True for tiny paired red decals that should stay out of the livery queue."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    if not (20 <= area_px <= 90 and 4 <= bw <= 14 and 4 <= bh <= 9):
        return False
    fill = area_px / float(max(1, bw * bh))
    aspect = max(bw / float(max(1, bh)), bh / float(max(1, bw)))
    if not (
        0.50 <= fill <= 0.78
        and aspect <= 2.1
        and 0.48 <= color["red"] <= 0.64
        and color["white"] <= 0.01
        and 0.40 <= color["colored"] <= 0.62
        and 0.42 <= color["dark"] <= 0.70
        and 0.20 <= color["edge"] <= 0.40
    ):
        return False

    cy = y + bh / 2.0
    paired = False
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        oa = int(stats[other_idx, cv2.CC_STAT_AREA])
        if not (20 <= oa <= 90 and 4 <= ow <= 14 and 4 <= oh <= 9):
            continue
        if abs((oy + oh / 2.0) - cy) > 4.0:
            continue
        gap = min(abs(ox - (x + bw)), abs(x - (ox + ow)))
        if 3 <= gap <= 18:
            paired = True
            break
    if not paired:
        return False

    h, w = source_rgb.shape[:2]
    pad = 17
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    ring = np.zeros((h, w), bool)
    ring[y0:y1, x0:x1] = True
    ring &= ~comp_mask
    if not ring.any():
        return False

    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 120) > 0
    ring_hsv = hsv[ring]
    hue = ring_hsv[:, 0]
    sat = ring_hsv[:, 1]
    val = ring_hsv[:, 2]
    ring_red = float(((((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))).mean())
    ring_colored = float(((sat > 75) & (val > 70)).mean())
    ring_dark = float((val < 84).mean())
    ring_white = float(((sat < 55) & (val > 165)).mean())
    ring_edge = float(edges[ring].mean())

    sponsors = masks.get("sponsors")
    ring_sponsor = float((sponsors[ring]).mean()) if sponsors is not None else 0.0
    protected = np.zeros((h, w), bool)
    for name in ("numbers", "template", "brand_graphics"):
        layer_mask = masks.get(name)
        if layer_mask is not None:
            protected |= layer_mask
    ring_protected = float((protected[ring]).mean())
    return (
        ring_dark >= 0.94
        and ring_red <= 0.03
        and ring_colored <= 0.03
        and ring_white <= 0.01
        and ring_edge <= 0.08
        and ring_sponsor <= 0.035
        and ring_protected <= 0.02
    )


def _is_tiny_contingency_sponsor_mark_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    color: dict[str, float],
) -> bool:
    """True for tiny red/dark contingency marks embedded in sponsor stacks."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    if not (45 <= area_px <= 180 and 6 <= bw <= 18 and 6 <= bh <= 18):
        return False
    fill = area_px / float(max(1, bw * bh))
    aspect = max(bw / float(max(1, bh)), bh / float(max(1, bw)))
    if not (
        0.45 <= fill <= 0.90
        and aspect <= 1.75
        and 0.48 <= color["red"] <= 0.78
        and color["white"] <= 0.04
        and 0.35 <= color["colored"] <= 0.78
        and 0.22 <= color["dark"] <= 0.70
        and 0.20 <= color["edge"] <= 0.38
    ):
        return False

    neighbor_count = 0
    neighbor_area = 0
    has_textline_neighbor = False
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        oa = int(stats[other_idx, cv2.CC_STAT_AREA])
        if oa < 20 or ow <= 0 or oh <= 0:
            continue
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = max(oy - (y + bh), y - (oy + oh), 0)
        other_fill = oa / float(max(1, ow * oh))
        if dx <= 34 and dy <= 34 and oa <= 1200 and other_fill >= 0.24:
            neighbor_count += 1
            neighbor_area += oa
            if ow >= 24 and oh <= 22:
                has_textline_neighbor = True
    if neighbor_count < 2 or neighbor_area < 220 or not has_textline_neighbor:
        return False

    h, w = source_rgb.shape[:2]
    pad = 42
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    ring = np.zeros((h, w), bool)
    ring[y0:y1, x0:x1] = True
    ring &= ~comp_mask
    if not ring.any():
        return False

    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 120) > 0
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    ring_red = float(((((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))[ring]).mean())
    ring_yellow = float((((hue >= 18) & (hue <= 45) & (sat > 70) & (val > 90))[ring]).mean())
    ring_white = float((((sat < 70) & (val > 132))[ring]).mean())
    ring_colored = float((((sat > 75) & (val > 70))[ring]).mean())
    ring_dark = float(((val < 84)[ring]).mean())
    ring_edge = float(edges[ring].mean())

    sponsors = masks.get("sponsors")
    ring_sponsor = float((sponsors[ring]).mean()) if sponsors is not None else 0.0
    protected = np.zeros((h, w), bool)
    for name in ("numbers", "template", "brand_graphics"):
        layer_mask = masks.get(name)
        if layer_mask is not None:
            protected |= layer_mask
    ring_protected = float((protected[ring]).mean())

    return (
        ring_sponsor >= 0.025
        and ring_sponsor <= 0.35
        and ring_protected <= 0.03
        and ring_edge >= 0.14
        and ring_white >= 0.05
        and ring_colored >= 0.12
        and 0.14 <= ring_dark <= 0.72
        and (ring_red + ring_yellow + ring_white) >= 0.18
    )


def _is_tiny_horizontal_contingency_sponsor_mark_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    color: dict[str, float],
) -> bool:
    """True for tiny flat red sponsor/contingency marks in dense stacks."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    if not (30 <= area_px <= 145 and 7 <= bw <= 24 and 3 <= bh <= 9):
        return False
    fill = area_px / float(max(1, bw * bh))
    aspect = max(bw / float(max(1, bh)), bh / float(max(1, bw)))
    if not (
        0.50 <= fill <= 1.0
        and 1.65 <= aspect <= 4.4
        and 0.48 <= color["red"] <= 0.84
        and color["white"] <= 0.24
        and 0.42 <= color["colored"] <= 0.86
        and color["dark"] <= 0.62
        and 0.16 <= color["edge"] <= 0.38
    ):
        return False

    neighbor_count = 0
    neighbor_area = 0
    has_sponsor_cluster_neighbor = False
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        oa = int(stats[other_idx, cv2.CC_STAT_AREA])
        if oa < 18 or ow <= 0 or oh <= 0:
            continue
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = max(oy - (y + bh), y - (oy + oh), 0)
        other_fill = oa / float(max(1, ow * oh))
        if dx <= 42 and dy <= 34 and oa <= 1800 and other_fill >= 0.22:
            neighbor_count += 1
            neighbor_area += oa
            if ow >= 22 and oh <= 46:
                has_sponsor_cluster_neighbor = True
            if ow >= 18 and oh <= 16:
                has_sponsor_cluster_neighbor = True
    if neighbor_count < 2 or neighbor_area < 170 or not has_sponsor_cluster_neighbor:
        return False

    h, w = source_rgb.shape[:2]
    pad = 40
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    ring = np.zeros((h, w), bool)
    ring[y0:y1, x0:x1] = True
    ring &= ~comp_mask
    if not ring.any():
        return False

    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 120) > 0
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    ring_red = float(((((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))[ring]).mean())
    ring_yellow = float((((hue >= 18) & (hue <= 45) & (sat > 70) & (val > 90))[ring]).mean())
    ring_white = float((((sat < 70) & (val > 132))[ring]).mean())
    ring_colored = float((((sat > 75) & (val > 70))[ring]).mean())
    ring_dark = float(((val < 84)[ring]).mean())
    ring_edge = float(edges[ring].mean())

    sponsors = masks.get("sponsors")
    ring_sponsor = float((sponsors[ring]).mean()) if sponsors is not None else 0.0
    protected = np.zeros((h, w), bool)
    for name in ("numbers", "template", "brand_graphics"):
        layer_mask = masks.get(name)
        if layer_mask is not None:
            protected |= layer_mask
    bbox_protected = float(protected[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 1.0
    ring_protected = float((protected[ring]).mean())
    protected_context_ok = ring_protected <= 0.14 or (
        ring_protected <= 0.68
        and ring_sponsor >= 0.20
        and ring_white >= 0.20
        and neighbor_area >= 900
    )

    return (
        bbox_protected <= 0.02
        and 0.018 <= ring_sponsor <= 0.42
        and protected_context_ok
        and ring_edge >= 0.10
        and ring_white >= 0.035
        and ring_colored >= 0.08
        and 0.04 <= ring_dark <= 0.74
        and (ring_red + ring_yellow + ring_white) >= 0.14
    )


def _is_compact_contingency_sponsor_badge_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    color: dict[str, float],
) -> bool:
    """True for compact red/yellow logo badges embedded in sponsor stacks."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    if not (
        170 <= area_px <= 650
        and 14 <= bw <= 45
        and 8 <= bh <= 28
        and 0.50 <= area_px / float(max(1, bw * bh)) <= 0.93
        and max(bw / float(max(1, bh)), bh / float(max(1, bw))) <= 3.25
        and color["red"] >= 0.48
        and color["warm"] >= 0.48
        and color["white"] <= 0.24
        and color["colored"] >= 0.40
        and color["dark"] <= 0.70
        and 0.28 <= color["edge"] <= 0.43
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges_crop = (cv2.Canny(gray_crop, 45, 120) > 0) & local
    hue_crop = hsv_crop[:, :, 0]
    sat_crop = hsv_crop[:, :, 1]
    val_crop = hsv_crop[:, :, 2]
    red = (((hue_crop <= 14) | (hue_crop >= 170) | ((hue_crop >= 15) & (hue_crop <= 28))) & (sat_crop > 80) & (val_crop > 55) & local)
    yellow = (hue_crop >= 18) & (hue_crop <= 45) & (sat_crop > 70) & (val_crop > 90) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    edge_rows = edges_crop.sum(axis=1) / row_den
    edge_cols = edges_crop.sum(axis=0) / col_den
    if not (
        float(red.sum()) / denom >= 0.48
        and float(yellow.sum()) / denom >= 0.30
        and float((edge_rows >= 0.14).mean()) >= 0.82
        and float((edge_cols >= 0.14).mean()) >= 0.80
    ):
        return False

    neighbor_count = 0
    neighbor_area = 0
    has_textline_neighbor = False
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        oa = int(stats[other_idx, cv2.CC_STAT_AREA])
        if oa < 18 or ow <= 0 or oh <= 0:
            continue
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = max(oy - (y + bh), y - (oy + oh), 0)
        other_fill = oa / float(max(1, ow * oh))
        if dx <= 60 and dy <= 45 and oa <= 3200 and other_fill >= 0.18:
            neighbor_count += 1
            neighbor_area += oa
            if (ow >= 24 and oh <= 46) or (ow >= 18 and oh <= 18):
                has_textline_neighbor = True
    if neighbor_area < 650 or not has_textline_neighbor:
        return False
    if neighbor_count < 2 and not (neighbor_area >= 650 and bw <= 22):
        return False

    h, w = source_rgb.shape[:2]
    protected = np.zeros((h, w), bool)
    for name in ("numbers", "template", "brand_graphics"):
        layer_mask = masks.get(name)
        if layer_mask is not None:
            protected |= layer_mask
    bbox_protected = float(protected[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 1.0
    if bbox_protected > 0.03:
        return False

    pad = max(32, min(90, int(round(max(bw, bh) * 1.40))))
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    ring = np.zeros((h, w), bool)
    ring[y0:y1, x0:x1] = True
    ring &= ~comp_mask
    if not ring.any():
        return False

    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 120) > 0
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    sponsors = masks.get("sponsors")
    ring_sponsor = float((sponsors[ring]).mean()) if sponsors is not None else 0.0
    ring_protected = float((protected[ring]).mean())
    protected_context_ok = ring_protected <= 0.10 or (
        ring_protected <= 0.22
        and neighbor_area >= 2500
        and ring_sponsor >= 0.12
    )
    ring_edge = float(edges[ring].mean())
    ring_white = float((((sat < 70) & (val > 132))[ring]).mean())
    ring_dark = float(((val < 84)[ring]).mean())
    ring_colored = float((((sat > 75) & (val > 70))[ring]).mean())
    ring_red = float(((((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))[ring]).mean())
    ring_yellow = float((((hue >= 18) & (hue <= 45) & (sat > 70) & (val > 90))[ring]).mean())

    return (
        0.045 <= ring_sponsor <= 0.35
        and protected_context_ok
        and ring_edge >= 0.08
        and 0.01 <= ring_white <= 0.24
        and 0.04 <= ring_colored <= 0.30
        and 0.20 <= ring_dark <= 0.88
        and (ring_red + ring_yellow + ring_white) >= 0.12
    )


def _is_top_edge_number_panel_contingency_sponsor_chip_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tiny top-edge contingency chips recovered beside number panels."""
    x, y, bw, bh = [int(v) for v in bbox]
    h, w = source_rgb.shape[:2]
    area_px = int(comp_mask.sum())
    if not (
        y <= max(76, int(round(0.082 * h)))
        and 35 <= area_px <= 90
        and area_frac <= 0.00010
        and 4 <= min(bw, bh) <= 8
        and max(bw, bh) <= 12
        and aspect <= 1.65
        and fill >= 0.82
        and color["red"] >= 0.60
        and color["colored"] >= 0.60
        and color["white"] <= 0.18
        and color["dark"] <= 0.08
        and 0.14 <= color["edge"] <= 0.36
    ):
        return False

    numbers = masks.get("numbers")
    sponsors = masks.get("sponsors")
    template = masks.get("template")
    brand = masks.get("brand_graphics")
    if numbers is None or sponsors is None:
        return False

    bbox_number = float(numbers[y:y + bh, x:x + bw].mean())
    bbox_sponsor = float(sponsors[y:y + bh, x:x + bw].mean())
    bbox_template = float(template[y:y + bh, x:x + bw].mean()) if template is not None else 0.0
    bbox_brand = float(brand[y:y + bh, x:x + bw].mean()) if brand is not None else 0.0
    if bbox_sponsor < 0.80 or bbox_number > 0.08 or bbox_template > 0.02 or bbox_brand > 0.02:
        return False

    pad = max(8, int(round(0.014 * min(h, w))))
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    local = np.zeros((h, w), bool)
    local[y0:y1, x0:x1] = True
    if not local.any():
        return False

    local_number = float(numbers[local].mean())
    local_sponsor = float(sponsors[local].mean())
    local_template = float(template[local].mean()) if template is not None else 0.0
    local_brand = float(brand[local].mean()) if brand is not None else 0.0
    return (
        local_number >= 0.42
        and local_sponsor <= 0.24
        and local_template <= 0.03
        and local_brand <= 0.03
    )


def _is_number_panel_embedded_contingency_strip_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tiny red/green contingency wordmarks recovered inside number panels."""
    x, y, bw, bh = [int(v) for v in bbox]
    h, w = source_rgb.shape[:2]
    area_px = int(comp_mask.sum())
    if not (
        80 <= area_px <= 145
        and area_frac <= 0.00015
        and 4 <= bh <= 7
        and 16 <= bw <= 32
        and 3.10 <= aspect <= 6.50
        and fill >= 0.86
        and color["red"] >= 0.55
        and color["colored"] >= 0.78
        and color["white"] <= 0.14
        and color["dark"] <= 0.08
        and 0.18 <= color["edge"] <= 0.48
    ):
        return False

    numbers = masks.get("numbers")
    sponsors = masks.get("sponsors")
    template = masks.get("template")
    brand = masks.get("brand_graphics")
    if numbers is None or sponsors is None:
        return False

    bbox_sponsor = float(sponsors[y:y + bh, x:x + bw].mean())
    bbox_number = float(numbers[y:y + bh, x:x + bw].mean())
    bbox_template = float(template[y:y + bh, x:x + bw].mean()) if template is not None else 0.0
    bbox_brand = float(brand[y:y + bh, x:x + bw].mean()) if brand is not None else 0.0
    if bbox_sponsor < 0.80 or bbox_number > 0.08 or bbox_template > 0.02 or bbox_brand > 0.02:
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local_comp = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local_comp.any():
        return False
    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    hue = hsv_crop[:, :, 0]
    sat = hsv_crop[:, :, 1]
    val = hsv_crop[:, :, 2]
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55) & local_comp)
    green = ((hue >= 45) & (hue <= 88) & (sat > 70) & (val > 70) & local_comp)
    denom = float(max(1, int(local_comp.sum())))
    if not (float(red.sum()) / denom >= 0.55 and 0.12 <= float(green.sum()) / denom <= 0.35):
        return False

    pad = max(8, int(round(0.014 * min(h, w))))
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    local = np.zeros((h, w), bool)
    local[y0:y1, x0:x1] = True
    ring = local.copy()
    ring &= ~comp_mask
    if not ring.any():
        return False

    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    sat_all = hsv[:, :, 1]
    val_all = hsv[:, :, 2]
    local_number = float(numbers[local].mean())
    local_sponsor = float(sponsors[local].mean())
    local_template = float(template[local].mean()) if template is not None else 0.0
    local_brand = float(brand[local].mean()) if brand is not None else 0.0
    bright_ring = float((((val_all > 145) & (sat_all < 125))[ring]).mean())
    dark_ring = float(((val_all < 90)[ring]).mean())
    return (
        local_number >= 0.50
        and 0.04 <= local_sponsor <= 0.24
        and local_template <= 0.03
        and local_brand <= 0.03
        and bright_ring >= 0.70
        and dark_ring <= 0.08
    )


def _is_tiny_magenta_red_sponsor_detail_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    color: dict[str, float],
) -> bool:
    """True for tiny saturated sponsor trim/letter chips in busy sponsor panels."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    aspect = max(bw / float(max(1, bh)), bh / float(max(1, bw)))
    fill = area_px / float(max(1, bw * bh))
    if not (
        20 <= area_px <= 520
        and 1 <= min(bw, bh) <= 28
        and max(bw, bh) <= 80
        and 0.25 <= fill <= 1.0
        and aspect <= 45.0
        and color["colored"] >= 0.45
        and color["white"] <= 0.25
        and color["edge"] <= 0.42
    ):
        return False
    saturated_red_chip = color["red"] >= 0.48 and color["warm"] >= 0.48
    saturated_trim_chip = color["colored"] >= 0.92 and (min(bw, bh) <= 2 or color["dark"] >= 0.85)
    if not (saturated_red_chip or saturated_trim_chip):
        return False

    h, w = source_rgb.shape[:2]
    protected = np.zeros((h, w), bool)
    for name in ("numbers", "template", "brand_graphics"):
        layer_mask = masks.get(name)
        if layer_mask is not None:
            protected |= layer_mask
    bbox_protected = float(protected[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 1.0
    sponsors = masks.get("sponsors")
    bbox_sponsor = float(sponsors[y:y + bh, x:x + bw].mean()) if sponsors is not None and bw > 0 and bh > 0 else 0.0
    allow_protected_sponsor_chip = (
        saturated_red_chip
        and area_px <= 80
        and bbox_protected <= 0.35
        and bbox_sponsor >= 0.85
    )
    if bbox_protected > 0.03 and not allow_protected_sponsor_chip:
        return False

    neighbor_count = 0
    neighbor_area = 0
    has_text_or_logo_neighbor = False
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        oa = int(stats[other_idx, cv2.CC_STAT_AREA])
        if oa < 18 or ow <= 0 or oh <= 0:
            continue
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = max(oy - (y + bh), y - (oy + oh), 0)
        other_fill = oa / float(max(1, ow * oh))
        if dx <= 48 and dy <= 42 and oa <= 2400 and other_fill >= 0.18:
            neighbor_count += 1
            neighbor_area += oa
            if ow >= 18 or oh >= 18:
                has_text_or_logo_neighbor = True
    if neighbor_count < 1 or neighbor_area < 120 or not has_text_or_logo_neighbor:
        return False

    pad = 42
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    ring = np.zeros((h, w), bool)
    ring[y0:y1, x0:x1] = True
    ring &= ~comp_mask
    if not ring.any():
        return False

    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 120) > 0
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    ring_white = float((((sat < 70) & (val > 132))[ring]).mean())
    ring_colored = float((((sat > 75) & (val > 70))[ring]).mean())
    ring_dark = float(((val < 84)[ring]).mean())
    ring_edge = float(edges[ring].mean())
    ring_sponsor = float((sponsors[ring]).mean()) if sponsors is not None else 0.0
    ring_protected = float((protected[ring]).mean())
    protected_context_ok = ring_protected <= 0.34 or (
        saturated_red_chip
        and ring_protected <= 0.48
        and ring_sponsor >= 0.18
        and ring_edge >= 0.10
        and ring_white >= 0.30
        and ring_colored >= 0.15
    )
    colored_context_ok = ring_colored >= 0.055 or (
        saturated_red_chip
        and ring_sponsor >= 0.075
        and ring_edge >= 0.055
        and ring_white >= 0.07
    ) or (
        saturated_red_chip
        and ring_sponsor >= 0.075
        and ring_edge >= 0.07
        and ring_white >= 0.05
        and ring_colored >= 0.045
        and ring_dark <= 0.91
    ) or (
        saturated_trim_chip
        and ring_sponsor >= 0.09
        and ring_edge >= 0.09
        and ring_white >= 0.12
        and ring_dark <= 0.86
    )
    dark_context_ok = 0.08 <= ring_dark <= 0.82 or (
        saturated_red_chip
        and ring_sponsor >= 0.075
        and ring_edge >= 0.07
        and ring_white >= 0.05
        and ring_colored >= 0.045
        and ring_dark <= 0.91
    )

    return (
        0.020 <= ring_sponsor <= 0.55
        and protected_context_ok
        and ring_edge >= 0.055
        and ring_white >= 0.035
        and colored_context_ok
        and dark_context_ok
    )


def _is_compact_red_sponsor_wordmark_panel_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    comp_mask: np.ndarray,
    bbox: list[int],
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for compact red sponsor panels with internal wordmark/glyph texture."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(comp_mask.sum())
    if not (
        220 <= area_px <= 1100
        and 30 <= bw <= 80
        and 9 <= bh <= 22
        and 0.56 <= fill <= 0.96
        and 2.0 <= aspect <= 6.2
        and 0.48 <= color["red"] <= 0.78
        and color["white"] <= 0.24
        and 0.48 <= color["colored"] <= 0.78
        and color["dark"] <= 0.32
        and 0.31 <= color["edge"] <= 0.39
    ):
        return False

    h, w = source_rgb.shape[:2]
    protected = np.zeros((h, w), bool)
    for name in ("numbers", "template", "brand_graphics"):
        layer_mask = masks.get(name)
        if layer_mask is not None:
            protected |= layer_mask
    bbox_protected = float(protected[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 1.0
    if bbox_protected > 0.22:
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    white = (sat < 70) & (val > 132) & local
    dark = (val < 84) & local

    def _component_summary(mask: np.ndarray) -> tuple[int, int, int]:
        n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        count = 0
        max_area = 0
        for idx in range(1, n):
            area = int(stats[idx, cv2.CC_STAT_AREA])
            if area >= 3:
                count += 1
                max_area = max(max_area, area)
        if mask.any():
            xs = np.where(mask.any(axis=0))[0]
            span = int(np.ptp(xs) + 1)
        else:
            span = 0
        return count, max_area, span

    white_count, white_max_area, white_span = _component_summary(white)
    dark_count, dark_max_area, dark_span = _component_summary(dark)
    broad_span = max(white_span, dark_span)
    has_glyph_components = (
        (white_count >= 2 and white_max_area >= 10)
        or (dark_count >= 2 and dark_max_area >= 8)
        or (white_count >= 1 and dark_count >= 4)
    )
    return has_glyph_components and broad_span >= max(24, int(round(0.58 * bw)))


def _is_clustered_red_white_sponsor_decal_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for red/white sponsor decals embedded in a local sponsor cluster."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(comp_mask.sum())
    if not (
        180 <= area_px <= 1800
        and 24 <= bw <= 84
        and 9 <= bh <= 38
        and area_frac <= 0.0018
        and 0.50 <= fill <= 1.0
        and 1.55 <= aspect <= 5.80
        and 0.45 <= color["red"] <= 0.86
        and 0.08 <= color["white"] <= 0.42
        and 0.48 <= color["colored"] <= 0.88
        and color["dark"] <= 0.24
        and 0.28 <= color["edge"] <= 0.50
    ):
        return False

    h, w = source_rgb.shape[:2]
    numbers = masks.get("numbers")
    sponsors = masks.get("sponsors")
    template = masks.get("template")
    brand = masks.get("brand_graphics")
    paint = masks.get("paint")
    if sponsors is None:
        return False
    numbers = numbers if numbers is not None else np.zeros((h, w), bool)
    template = template if template is not None else np.zeros((h, w), bool)
    brand = brand if brand is not None else np.zeros((h, w), bool)
    paint = paint if paint is not None else np.zeros((h, w), bool)
    protected = numbers | template | brand
    anchor = (sponsors | brand) & ~comp_mask

    bbox_protected = float(protected[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 1.0
    bbox_template = float(template[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 1.0
    bbox_sponsor = float(sponsors[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 0.0
    if bbox_sponsor < 0.50 or bbox_template > 0.04 or bbox_protected > 0.13:
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 70) & (val > 55) & local)
    white = ((sat < 85) & (val > 132) & local)
    dark = ((val < 95) & local)
    edges = ((cv2.Canny(gray, 45, 120) > 0) & local)
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den
    white_rows = white.sum(axis=1) / row_den
    white_cols = white.sum(axis=0) / col_den
    if not (
        float(red.sum()) / denom >= 0.42
        and float(white.sum()) / denom >= 0.16
        and float(dark.sum()) / denom <= 0.17
        and float(edges.sum()) / denom >= 0.29
        and float(edge_rows.max()) >= 0.72
        and float(edge_cols.max()) >= 0.36
        and (float(white_rows.max()) >= 0.34 or float(white_cols.max()) >= 0.34)
    ):
        return False

    pad = max(24, int(round(0.035 * min(h, w))))
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + bw + pad)
    y1 = min(h, y + bh + pad)
    local_context = np.zeros((h, w), bool)
    local_context[y0:y1, x0:x1] = True
    ring = local_context.copy()
    ring[y:y + bh, x:x + bw] = False
    if not ring.any():
        return False
    ring_sponsor = float(anchor[ring].mean())
    ring_protected = float(protected[ring].mean())
    ring_paint = float(paint[ring].mean())
    if ring_protected > 0.22 or ring_paint < 0.42:
        return False

    close_siblings = 0
    rich_siblings = 0
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area < 180:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        if ow <= 0 or oh <= 0:
            continue
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = max(oy - (y + bh), y - (oy + oh), 0)
        dist = float((dx * dx + dy * dy) ** 0.5)
        if dist > 92.0:
            continue
        close_siblings += 1
        sibling_color = _component_color_fractions(source_rgb, labels == other_idx, [ox, oy, ow, oh])
        if (
            sibling_color["white"] >= 0.18
            and sibling_color["edge"] >= 0.24
            and sibling_color["dark"] <= 0.82
        ):
            rich_siblings += 1

    return close_siblings >= 1 and (ring_sponsor >= 0.035 or rich_siblings >= 2)


def _is_sidecar_red_logo_chip_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    comp_mask: np.ndarray,
    bbox: list[int],
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tiny red sponsor-nameplate edge chips sitting in Number bleed."""
    x, y, bw, bh = [int(v) for v in bbox]
    area_px = int(comp_mask.sum())
    if not (
        34 <= area_px <= 48
        and 5 <= bw <= 9
        and 4 <= bh <= 8
        and 0.82 <= fill <= 1.0
        and aspect <= 1.45
        and 0.24 <= color["edge"] <= 0.48
        and 0.58 <= color["red"] <= 0.76
        and 0.58 <= color["colored"] <= 0.76
        and 0.22 <= color["dark"] <= 0.42
        and color["white"] <= 0.08
    ):
        return False

    h, w = source_rgb.shape[:2]
    numbers = masks.get("numbers")
    sponsors = masks.get("sponsors")
    template = masks.get("template")
    brand = masks.get("brand_graphics")
    if numbers is None or sponsors is None:
        return False
    template = template if template is not None else np.zeros((h, w), bool)
    brand = brand if brand is not None else np.zeros((h, w), bool)
    anchor = (sponsors | brand) & ~comp_mask

    bbox_area = float(max(1, bw * bh))
    bbox_number_fill = float(numbers[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 0.0
    bbox_template_fill = float(template[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 0.0
    bbox_sponsor_fill = float(anchor[y:y + bh, x:x + bw].mean()) if bw > 0 and bh > 0 else 0.0
    if bbox_number_fill > 0.08 or bbox_template_fill > 0.02 or bbox_sponsor_fill > 0.10:
        return False

    min_dim = float(max(1, min(h, w)))
    radius = max(6, int(round(0.038 * min_dim)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
    sponsor_anchor = cv2.dilate(anchor.astype(np.uint8), kernel) > 0
    number_anchor = cv2.dilate(numbers.astype(np.uint8), kernel) > 0
    sponsor_overlap = float((comp_mask & sponsor_anchor).sum()) / float(max(1, area_px))
    number_overlap = float((comp_mask & number_anchor).sum()) / float(max(1, area_px))
    if sponsor_overlap < 0.98 or number_overlap < 0.75:
        return False

    margin = max(4, int(round(0.008 * min_dim)))
    x0 = max(0, x - margin)
    y0 = max(0, y - margin)
    x1 = min(w, x + bw + margin)
    y1 = min(h, y + bh + margin)
    local = np.zeros((h, w), bool)
    local[y0:y1, x0:x1] = True
    ring = local.copy()
    ring[y:y + bh, x:x + bw] = False
    near_sponsor = float((local & anchor).sum()) / float(max(1, local.sum()))
    near_number = float((local & numbers).sum()) / float(max(1, local.sum()))
    near_template = float((local & template).sum()) / float(max(1, local.sum()))
    if near_template > 0.04 or near_number < 0.45 or not (0.03 <= near_sponsor <= 0.38):
        return False

    side_pad_y = max(4, int(round(0.012 * min_dim)))
    side_span = max(48, int(round(0.094 * min_dim)))
    side_y0 = max(0, y - side_pad_y)
    side_y1 = min(h, y + bh + side_pad_y)
    left_side = anchor[side_y0:side_y1, max(0, x - side_span):x]
    right_side = anchor[side_y0:side_y1, min(w, x + bw):min(w, x + bw + side_span)]
    side_band_sponsor = max(
        float(left_side.mean()) if left_side.size else 0.0,
        float(right_side.mean()) if right_side.size else 0.0,
    )
    if side_band_sponsor < 0.18:
        return False

    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    bright_bg = float((((val > 145) & (sat < 125) & ring).sum())) / float(max(1, ring.sum()))
    saturated_bg = float((((sat > 90) & (val > 75) & ring).sum())) / float(max(1, ring.sum()))
    blue_bg = float((((hue >= 92) & (hue <= 132) & (sat > 80) & (val > 60) & ring).sum())) / float(max(1, ring.sum()))
    green_bg = float((((hue >= 45) & (hue <= 88) & (sat > 70) & (val > 70) & ring).sum())) / float(max(1, ring.sum()))
    yellow_bg = float((((hue >= 22) & (hue <= 45) & (sat > 80) & (val > 110) & ring).sum())) / float(max(1, ring.sum()))
    dark_bg = float((((val < 90) & ring).sum())) / float(max(1, ring.sum()))

    return (
        0.58 <= bright_bg <= 0.92
        and 0.02 <= saturated_bg <= 0.24
        and 0.04 <= dark_bg <= 0.22
        and blue_bg <= 0.04
        and green_bg <= 0.04
        and yellow_bg <= 0.04
    )


def _is_sponsor_card_panel_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for filled red/magenta sponsor-card backgrounds with text bands."""
    if not (
        0.0030 <= area_frac <= 0.0055
        and 0.90 <= fill <= 1.0
        and 0.80 <= aspect <= 1.30
        and 0.54 <= color["red"] <= 0.75
        and 0.12 <= color["white"] <= 0.25
        and color["dark"] <= 0.14
        and 0.05 <= color["edge"] <= 0.24
    ):
        return False

    x, y, bw, bh = [int(v) for v in bbox]
    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    pale = (sat < 90) & (val > 132) & local
    blue = (hue >= 82) & (hue <= 128) & (sat > 55) & (val > 95) & local
    red = (((hue <= 14) | (hue >= 165) | ((hue >= 145) & (hue <= 164))) & (sat > 70) & (val > 65) & local)
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    pale_rows = pale.sum(axis=1) / row_den
    blue_rows = blue.sum(axis=1) / row_den
    red_rows = red.sum(axis=1) / row_den
    top_end = max(1, int(round(bh * 0.36)))
    bottom_start = min(bh - 1, int(round(bh * 0.64)))
    middle_start = max(0, int(round(bh * 0.34)))
    middle_end = max(middle_start + 1, int(round(bh * 0.76)))
    top_pale = float(pale_rows[:top_end].max()) if pale_rows.size else 0.0
    bottom_pale = float(pale_rows[bottom_start:].max()) if pale_rows.size else 0.0
    top_blue = float(blue_rows[:top_end].max()) if blue_rows.size else 0.0
    middle_red = float(red_rows[middle_start:middle_end].mean()) if red_rows.size else 0.0
    return (
        top_pale >= 0.34
        and bottom_pale >= 0.24
        and top_blue >= 0.10
        and middle_red >= 0.58
    )


def _is_stacked_sponsor_card_panel_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tall multi-sponsor card stacks already correct as Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0080 <= area_frac <= 0.0240
        and 85 <= bw <= 190
        and 130 <= bh <= 320
        and 1.20 <= aspect <= 2.45
        and 0.30 <= fill <= 0.68
        and color["warm"] >= 0.52
        and color["colored"] >= 0.68
        and 0.035 <= color["white"] <= 0.18
        and color["dark"] <= 0.16
        and 0.08 <= color["edge"] <= 0.24
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    pale = (sat < 90) & (val > 132) & local
    white = (sat < 70) & (val > 132) & local
    green = (hue >= 42) & (hue <= 90) & (sat > 55) & (val > 70) & local
    warm = (((hue <= 42) | (hue >= 170)) & (sat > 80) & (val > 55) & local)
    denom = float(max(1, int(local.sum())))

    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    pale_rows = pale.sum(axis=1) / row_den
    green_rows = green.sum(axis=1) / row_den
    edge_rows = edges.sum(axis=1) / row_den
    green_cols = green.sum(axis=0) / col_den
    pale_cols = pale.sum(axis=0) / col_den

    def count_runs(signal: np.ndarray, min_len: int = 3) -> int:
        count = 0
        run = 0
        for value in signal:
            if bool(value):
                run += 1
            else:
                if run >= min_len:
                    count += 1
                run = 0
        if run >= min_len:
            count += 1
        return count

    sponsor_rows = (green_rows >= 0.12) | (pale_rows >= 0.12) | (edge_rows >= 0.24)
    pale_components = cv2.connectedComponentsWithStats(pale.astype(np.uint8), 8)[2]
    edge_components = cv2.connectedComponentsWithStats(edges.astype(np.uint8), 8)[2]
    pale_large = sum(int(pale_components[i, cv2.CC_STAT_AREA]) >= 12 for i in range(1, pale_components.shape[0]))
    edge_large = sum(int(edge_components[i, cv2.CC_STAT_AREA]) >= 12 for i in range(1, edge_components.shape[0]))

    return (
        float(green.sum()) / denom >= 0.055
        and float(pale.sum()) / denom >= 0.045
        and float(white.sum()) / denom >= 0.035
        and float(warm.sum()) / denom >= 0.52
        and float(edges.sum()) / denom >= 0.09
        and float((green_rows >= 0.12).mean()) >= 0.14
        and float((pale_rows >= 0.12).mean()) >= 0.14
        and float((green_cols >= 0.12).mean()) >= 0.18
        and float((pale_cols >= 0.12).mean()) >= 0.16
        and count_runs(sponsor_rows, 3) >= 1
        and pale_large >= 3
        and edge_large >= 8
    )


def _is_vertical_multicolor_wordmark_decal_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tall multicolor sponsor decals that are already correct Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0012 <= area_frac <= 0.0028
        and 18 <= bw <= 34
        and 80 <= bh <= 130
        and 3.20 <= aspect <= 5.40
        and 0.70 <= fill <= 0.90
        and 0.44 <= color["red"] <= 0.66
        and color["warm"] >= 0.54
        and color["colored"] >= 0.78
        and color["white"] <= 0.07
        and color["dark"] <= 0.18
        and color["edge"] >= 0.28
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    warm = (((hue <= 42) | (hue >= 170)) & (sat > 80) & (val > 55) & local)
    yellow = ((hue >= 18) & (hue <= 42) & (sat > 80) & (val > 85) & local)
    dark = (val < 84) & local

    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    warm_rows = warm.sum(axis=1) / row_den
    yellow_rows = yellow.sum(axis=1) / row_den
    edge_rows = edges.sum(axis=1) / row_den
    dark_cols = dark.sum(axis=0) / col_den
    edge_cols = edges.sum(axis=0) / col_den

    return (
        float((warm_rows >= 0.34).mean()) >= 0.70
        and float((yellow_rows >= 0.16).mean()) >= 0.18
        and float((edge_rows >= 0.18).mean()) >= 0.70
        and float((edge_cols >= 0.22).mean()) >= 0.45
        and float((dark_cols >= 0.18).mean()) >= 0.10
    )


def _is_tiny_sponsor_wordmark_underline_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tiny red underline strokes attached to real sponsor wordmarks."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.000020 <= area_frac <= 0.000055
        and 8 <= bw <= 18
        and 2 <= bh <= 5
        and 2.40 <= aspect <= 5.40
        and fill >= 0.72
        and 0.30 <= color["colored"] <= 0.64
        and 0.45 <= color["red"] <= 0.62
        and color["white"] <= 0.01
        and color["dark"] >= 0.60
        and color["edge"] <= 0.42
    ):
        return False

    ih, iw = source_rgb.shape[:2]
    above = source_rgb[max(0, y - 36):y, max(0, x - 8):min(iw, x + bw + 8)]
    if above.size == 0:
        return False
    hsv = cv2.cvtColor(above, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    white = (sat < 70) & (val > 145)
    dark = val < 84
    colored = (sat > 75) & (val > 70)
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))
    return (
        float(white.mean()) >= 0.085
        and float(dark.mean()) >= 0.68
        and float(colored.mean()) <= 0.12
        and float(red.mean()) <= 0.04
    )


def _is_vertical_sponsor_side_marker_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tiny vertical red side markers beside sponsor/brand text."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.000035 <= area_frac <= 0.000105
        and 5 <= bw <= 9
        and 8 <= bh <= 24
        and 1.10 <= aspect <= 3.25
        and 0.42 <= fill <= 0.72
        and color["red"] >= 0.70
        and color["white"] <= 0.01
        and color["dark"] >= 0.68
        and color["edge"] <= 0.32
    ):
        return False

    ih, iw = source_rgb.shape[:2]

    def fractions(crop: np.ndarray) -> dict[str, float]:
        if crop.size == 0:
            return {"white": 0.0, "red": 0.0, "colored": 0.0, "dark": 0.0, "edge": 0.0}
        hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        hue = hsv[:, :, 0]
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))
        white = (sat < 70) & (val > 145)
        colored = (sat > 75) & (val > 70)
        dark = val < 84
        edge = cv2.Canny(gray, 45, 120) > 0
        return {
            "white": float(white.mean()),
            "red": float(red.mean()),
            "colored": float(colored.mean()),
            "dark": float(dark.mean()),
            "edge": float(edge.mean()),
        }

    left = fractions(source_rgb[max(0, y - 12):min(ih, y + bh + 12), max(0, x - 64):x])
    right = fractions(source_rgb[max(0, y - 12):min(ih, y + bh + 12), x + bw:min(iw, x + bw + 44)])
    return (
        left["white"] >= 0.11
        and left["red"] >= 0.25
        and left["colored"] >= 0.25
        and left["edge"] >= 0.17
        and 0.52 <= left["dark"] <= 0.76
        and right["dark"] >= 0.92
        and right["colored"] <= 0.04
        and right["white"] <= 0.025
    )


def _is_long_blue_website_sponsor_strip_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for long blue/cyan website sponsor strips already in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.00045 <= area_frac <= 0.00150
        and 90 <= bw <= 150
        and 8 <= bh <= 16
        and aspect >= 8.5
        and color["red"] <= 0.02
        and 0.35 <= color["colored"] <= 0.55
        and 0.10 <= color["white"] <= 0.34
        and 0.28 <= color["edge"] <= 0.42
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    blue = (hue >= 75) & (hue <= 135) & (sat > 55) & (val > 55) & local
    pale = (sat < 95) & (val > 116) & local
    white = (sat < 70) & (val > 132) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    blue_rows = blue.sum(axis=1) / row_den
    pale_rows = pale.sum(axis=1) / row_den
    return (
        float(blue.sum()) / denom >= 0.24
        and float(pale.sum()) / denom >= 0.13
        and float(white.sum()) / denom >= 0.10
        and float(blue_rows.max(initial=0.0)) >= 0.52
        and float(pale_rows.max(initial=0.0)) >= 0.30
        and float((blue_rows >= 0.10).mean()) >= 0.36
        and float((pale_rows >= 0.10).mean()) >= 0.45
    )


def _is_long_sponsor_wordmark_top_strip_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for a thin colored sponsor strip attached to dense wordmark text."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.00012 <= area_frac <= 0.00095
        and 70 <= bw <= 180
        and 3 <= bh <= 8
        and aspect >= 12.0
        and 0.35 <= fill <= 1.0
        and color["white"] <= 0.05
        and 0.35 <= color["colored"] <= 0.86
        and 0.14 <= color["dark"] <= 0.70
        and 0.20 <= color["edge"] <= 0.48
    ):
        return False

    ih, iw = source_rgb.shape[:2]
    below_h = max(16, min(34, bh * 6))
    x0 = max(0, x - 4)
    x1 = min(iw, x + bw + 4)
    y0 = y + bh
    y1 = min(ih, y + bh + below_h)
    below = source_rgb[y0:y1, x0:x1]
    if below.size == 0:
        return False

    hsv = cv2.cvtColor(below, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(below, cv2.COLOR_RGB2GRAY)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    white = (sat < 70) & (val > 132)
    pale = (sat < 95) & (val > 116)
    dark = val < 84
    colored = (sat > 75) & (val > 70)
    edges = cv2.Canny(gray, 45, 120) > 0
    white_rows = white.mean(axis=1)
    edge_rows = edges.mean(axis=1)

    ay0 = max(0, y - max(10, below_h // 2))
    above = source_rgb[ay0:y, x0:x1]
    if above.size == 0:
        above_dark = above_white = above_colored = above_edge = 0.0
    else:
        above_hsv = cv2.cvtColor(above, cv2.COLOR_RGB2HSV)
        above_gray = cv2.cvtColor(above, cv2.COLOR_RGB2GRAY)
        above_sat = above_hsv[:, :, 1]
        above_val = above_hsv[:, :, 2]
        above_dark = float((above_val < 84).mean())
        above_white = float(((above_sat < 70) & (above_val > 132)).mean())
        above_colored = float(((above_sat > 75) & (above_val > 70)).mean())
        above_edge = float((cv2.Canny(above_gray, 45, 120) > 0).mean())

    return (
        float(white.mean()) >= 0.20
        and float(pale.mean()) >= 0.20
        and float(dark.mean()) >= 0.25
        and float(colored.mean()) <= 0.08
        and float(edges.mean()) >= 0.12
        and float(white_rows.max(initial=0.0)) >= 0.55
        and float((white_rows >= 0.15).mean()) >= 0.35
        and float(edge_rows.max(initial=0.0)) >= 0.50
        and above_dark >= 0.70
        and above_white <= 0.08
        and above_colored <= 0.08
        and above_edge <= 0.14
    )


def _is_long_textlike_url_sponsor_strip_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for long URL/wordmark strips already correctly kept in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0012 <= area_frac <= 0.0032
        and 145 <= bw <= 260
        and 9 <= bh <= 20
        and 9.0 <= aspect <= 24.0
        and 0.68 <= fill <= 1.0
        and 0.22 <= color["red"] <= 0.66
        and 0.14 <= color["white"] <= 0.44
        and 0.34 <= color["colored"] <= 0.68
        and 0.10 <= color["dark"] <= 0.40
        and 0.24 <= color["edge"] <= 0.46
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55) & local)
    warm = (((hue <= 42) | (hue >= 170)) & (sat > 80) & (val > 55) & local)
    white = ((sat < 70) & (val > 132) & local)
    dark = ((val < 84) & local)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local

    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    red_cols = red.sum(axis=0) / col_den
    warm_cols = warm.sum(axis=0) / col_den
    white_cols = white.sum(axis=0) / col_den
    dark_cols = dark.sum(axis=0) / col_den
    edge_cols = edges.sum(axis=0) / col_den
    edge_rows = edges.sum(axis=1) / row_den

    active_cols = local.sum(axis=0) > 0
    if not active_cols.any():
        return False

    return (
        float((red_cols[active_cols] >= 0.20).mean()) >= 0.24
        and float((warm_cols[active_cols] >= 0.28).mean()) >= 0.38
        and float((white_cols[active_cols] >= 0.18).mean()) >= 0.22
        and float((dark_cols[active_cols] >= 0.12).mean()) >= 0.18
        and float((edge_cols[active_cols] >= 0.18).mean()) >= 0.28
        and float(edge_rows.max(initial=0.0)) >= 0.55
        and float((edge_rows >= 0.22).mean()) >= 0.42
    )


def _is_long_red_white_sponsor_wordmark_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for long red/white sponsor wordmarks already correctly kept in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.00035 <= area_frac <= 0.00680
        and 85 <= bw <= 280
        and 18 <= bh <= 52
        and 3.20 <= aspect <= 8.80
        and 0.18 <= fill <= 0.78
        and 0.45 <= color["red"] <= 0.84
        and 0.08 <= color["white"] <= 0.31
        and color["dark"] <= 0.42
        and 0.45 <= color["colored"] <= 0.90
        and 0.18 <= color["edge"] <= 0.38
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 70) & (val > 55) & local)
    white = ((sat < 85) & (val > 132) & local)
    dark = ((val < 94) & local)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local

    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    active_cols = local.sum(axis=0) > 0
    active_rows = local.sum(axis=1) > 0
    if int(active_cols.sum()) < 60 or int(active_rows.sum()) < 12:
        return False

    red_cols = red.sum(axis=0) / col_den
    white_cols = white.sum(axis=0) / col_den
    dark_cols = dark.sum(axis=0) / col_den
    edge_cols = edges.sum(axis=0) / col_den
    edge_rows = edges.sum(axis=1) / row_den

    white_column_density = float((white_cols[active_cols] >= 0.14).mean())
    dark_column_density = float((dark_cols[active_cols] >= 0.10).mean())
    return (
        float((red_cols[active_cols] >= 0.25).mean()) >= 0.70
        and float((edge_cols[active_cols] >= 0.16).mean()) >= 0.60
        and float(edge_rows[active_rows].max(initial=0.0)) >= 0.55
        and float((edge_rows[active_rows] >= 0.18).mean()) >= 0.50
        and (
            white_column_density >= 0.58
            or (white_column_density >= 0.20 and dark_column_density >= 0.35)
        )
    )


def _is_low_fill_grille_mesh_paint_boundary_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for sparse Paint islands riding grille/vent mesh boundaries."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        area_frac <= 0.00018
        and 18 <= bw <= 70
        and 12 <= bh <= 55
        and aspect <= 3.40
        and 0.02 <= fill <= 0.18
        and color["white"] <= 0.06
        and color["colored"] >= 0.45
        and color["edge"] >= 0.22
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 120) > 0
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    dark = val < 70
    black = val < 45
    yellow_body = (hue >= 18) & (hue <= 42) & (sat > 80) & (val > 120)
    white = (sat < 55) & (val > 170)
    dark_cols = dark.mean(axis=0)
    dark_rows = dark.mean(axis=1)
    yellow_cols = yellow_body.mean(axis=0)
    yellow_rows = yellow_body.mean(axis=1)
    return (
        float(dark.mean()) >= 0.34
        and float(black.mean()) >= 0.25
        and float(yellow_body.mean()) >= 0.30
        and float(white.mean()) <= 0.08
        and float(edges.mean()) >= 0.18
        and float((edges & dark).mean()) >= 0.08
        and float((dark_cols >= 0.40).mean()) >= 0.50
        and float((dark_rows >= 0.35).mean()) >= 0.45
        and float((yellow_cols >= 0.25).mean()) >= 0.45
        and float((yellow_rows >= 0.25).mean()) >= 0.35
    )


def _is_bottom_edge_flat_livery_panel_paint_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for bottom-edge flat livery panels that are already Paint."""
    x, y, bw, bh = [int(v) for v in bbox]
    ih, _iw = source_rgb.shape[:2]
    if not (
        y >= int(round(ih * 0.94))
        and 0.00050 <= area_frac <= 0.00150
        and 24 <= bw <= 80
        and 18 <= bh <= 38
        and 1.05 <= aspect <= 2.80
        and 0.72 <= fill <= 1.0
        and 0.46 <= color["red"] <= 0.68
        and 0.46 <= color["warm"] <= 0.68
        and 0.46 <= color["colored"] <= 0.70
        and 0.30 <= color["dark"] <= 0.54
        and color["white"] <= 0.025
        and 0.085 <= color["edge"] <= 0.210
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    warm = (((hue <= 28) | (hue >= 170)) & (sat > 75) & (val > 55) & local)
    dark = (val < 96) & local
    white = ((sat < 70) & (val > 145) & local)
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    warm_rows = warm.sum(axis=1) / row_den
    dark_rows = dark.sum(axis=1) / row_den
    return (
        float(warm.sum()) / denom >= 0.46
        and float(dark.sum()) / denom >= 0.30
        and float(white.sum()) / denom <= 0.025
        and float((warm_rows >= 0.40).mean()) >= 0.46
        and float((dark_rows >= 0.38).mean()) >= 0.18
    )


def _is_cyan_template_livery_stripe_paint_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tiny cyan/white livery stripe shards correctly left in Paint."""
    x, y, bw, bh = [int(v) for v in bbox]
    ih, iw = source_rgb.shape[:2]
    if not (
        0.000020 <= area_frac <= 0.000090
        and 14 <= bw <= 42
        and 6 <= bh <= 24
        and 1.15 <= aspect <= 3.40
        and 0.055 <= fill <= 0.24
        and color["red"] <= 0.05
        and color["warm"] <= 0.08
        and color["white"] <= 0.22
        and color["colored"] >= 0.58
        and color["dark"] <= 0.20
        and color["edge"] >= 0.22
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False

    template = np.asarray(masks.get("template", np.zeros(comp_mask.shape, bool))).astype(bool)
    sponsors = np.asarray(masks.get("sponsors", np.zeros(comp_mask.shape, bool))).astype(bool)
    numbers = np.asarray(masks.get("numbers", np.zeros(comp_mask.shape, bool))).astype(bool)
    paint = np.asarray(masks.get("paint", np.zeros(comp_mask.shape, bool))).astype(bool)
    margin = max(6, int(round(0.008 * min(ih, iw))))
    x0 = max(0, x - margin)
    y0 = max(0, y - margin)
    x1 = min(iw, x + bw + margin)
    y1 = min(ih, y + bh + margin)
    local_box = np.zeros(comp_mask.shape, bool)
    local_box[y0:y1, x0:x1] = True
    ring = local_box.copy()
    ring[y:y + bh, x:x + bw] = False
    bbox_area = float(max(1, bw * bh))
    local_area = float(max(1, int(local_box.sum())))
    ring_area = float(max(1, int(ring.sum())))
    bbox_template = float(template[y:y + bh, x:x + bw].sum()) / bbox_area
    bbox_number = float(numbers[y:y + bh, x:x + bw].sum()) / bbox_area
    near_template = float((local_box & template).sum()) / local_area
    near_number = float((local_box & numbers).sum()) / local_area
    ring_template = float((ring & template).sum()) / ring_area
    ring_paint = float((ring & paint).sum()) / ring_area
    ring_sponsor = float((ring & sponsors).sum()) / ring_area
    if not (
        bbox_number <= 0.02
        and near_number <= 0.03
        and (bbox_template >= 0.045 or near_template >= 0.26 or ring_template >= 0.32)
        and ring_template >= 0.24
        and (ring_paint >= 0.12 or ring_sponsor >= 0.06)
    ):
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    cyan = (hue >= 82) & (hue <= 104) & (sat > 60) & (val > 85) & local
    blue = (hue >= 88) & (hue <= 132) & (sat > 60) & (val > 60) & local
    white = (sat < 75) & (val > 145) & local
    warm = (((hue <= 30) | (hue >= 168)) & (sat > 70) & (val > 55) & local)
    dark = (val < 88) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    cyan_rows = cyan.sum(axis=1) / row_den
    blue_cols = blue.sum(axis=0) / col_den
    edge_rows = edges.sum(axis=1) / row_den
    return (
        float(blue.sum()) / denom >= 0.46
        and float(cyan.sum()) / denom >= 0.34
        and float(warm.sum()) / denom <= 0.04
        and float(white.sum()) / denom <= 0.24
        and float(dark.sum()) / denom <= 0.24
        and float((cyan_rows >= 0.12).mean()) >= 0.35
        and float((blue_cols >= 0.12).mean()) >= 0.45
        and float((edge_rows >= 0.12).mean()) >= 0.35
    )


def _is_template_adjacent_green_livery_edge_paint_review(
    source_rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for tiny green/dark livery edge shards correctly left in Paint."""
    x, y, bw, bh = [int(v) for v in bbox]
    ih, iw = source_rgb.shape[:2]
    if not (
        0.000015 <= area_frac <= 0.000055
        and 3 <= bw <= 8
        and 18 <= bh <= 34
        and bh > bw
        and aspect >= 3.0
        and 0.12 <= fill <= 0.36
        and color["red"] <= 0.04
        and color["warm"] <= 0.06
        and color["white"] <= 0.08
        and color["colored"] >= 0.42
        and color["dark"] >= 0.52
        and color["edge"] >= 0.24
    ):
        return False

    template = np.asarray(masks.get("template", np.zeros(comp_mask.shape, bool))).astype(bool)
    numbers = np.asarray(masks.get("numbers", np.zeros(comp_mask.shape, bool))).astype(bool)
    sponsors = np.asarray(masks.get("sponsors", np.zeros(comp_mask.shape, bool))).astype(bool)
    paint = np.asarray(masks.get("paint", np.zeros(comp_mask.shape, bool))).astype(bool)
    margin = max(12, int(round(0.014 * min(ih, iw))))
    x0 = max(0, x - margin)
    y0 = max(0, y - margin)
    x1 = min(iw, x + bw + margin)
    y1 = min(ih, y + bh + margin)
    local_box = np.zeros(comp_mask.shape, bool)
    local_box[y0:y1, x0:x1] = True
    ring = local_box.copy()
    ring[y:y + bh, x:x + bw] = False
    bbox_area = float(max(1, bw * bh))
    local_area = float(max(1, int(local_box.sum())))
    ring_area = float(max(1, int(ring.sum())))
    bbox_template = float(template[y:y + bh, x:x + bw].sum()) / bbox_area
    bbox_number = float(numbers[y:y + bh, x:x + bw].sum()) / bbox_area
    near_template = float((local_box & template).sum()) / local_area
    near_number = float((local_box & numbers).sum()) / local_area
    ring_template = float((ring & template).sum()) / ring_area
    ring_paint = float((ring & paint).sum()) / ring_area
    ring_sponsor = float((ring & sponsors).sum()) / ring_area
    if not (
        bbox_number <= 0.02
        and near_number <= 0.03
        and (bbox_template >= 0.16 or near_template >= 0.32 or ring_template >= 0.32)
        and (ring_template >= 0.22 or near_template >= 0.38)
        and (ring_paint >= 0.08 or ring_sponsor >= 0.08)
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    context = source_rgb[y0:y1, x0:x1]
    if crop.size == 0 or context.size == 0 or not local.any():
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    green = (hue >= 42) & (hue <= 92) & (sat > 45) & (val > 38) & local
    blue = (hue >= 94) & (hue <= 132) & (sat > 55) & (val > 58) & local
    yellow = (hue >= 20) & (hue <= 42) & (sat > 65) & (val > 85) & local
    dark = (val < 92) & local
    saturated = (sat > 60) & (val > 35) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    green_rows = green.sum(axis=1) / row_den
    dark_rows = dark.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den

    ctx_hsv = cv2.cvtColor(context, cv2.COLOR_RGB2HSV)
    ctx_hue = ctx_hsv[:, :, 0]
    ctx_sat = ctx_hsv[:, :, 1]
    ctx_val = ctx_hsv[:, :, 2]
    ctx_green = (ctx_hue >= 42) & (ctx_hue <= 96) & (ctx_sat > 36) & (ctx_val > 35)
    ctx_dark = ctx_val < 96
    ctx_yellow = (ctx_hue >= 18) & (ctx_hue <= 44) & (ctx_sat > 65) & (ctx_val > 90)
    ctx_blue = (ctx_hue >= 96) & (ctx_hue <= 136) & (ctx_sat > 55) & (ctx_val > 60)
    return (
        float(green.sum()) / denom >= 0.24
        and float(saturated.sum()) / denom >= 0.36
        and float(dark.sum()) / denom >= 0.54
        and float(blue.sum()) / denom <= 0.05
        and float(yellow.sum()) / denom <= 0.08
        and float(edges.sum()) / denom >= 0.24
        and float((green_rows >= 0.10).mean()) >= 0.34
        and float((dark_rows >= 0.45).mean()) >= 0.62
        and float((edge_cols >= 0.20).mean()) >= 0.38
        and float(ctx_green.mean()) >= 0.16
        and float(ctx_dark.mean()) >= 0.34
        and float(ctx_yellow.mean()) <= 0.08
        and float(ctx_blue.mean()) <= 0.08
    )


def _is_compact_multicolor_sponsor_badge_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for compact multicolor sponsor badges that are already Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0010 <= area_frac <= 0.0024
        and 30 <= bw <= 66
        and 26 <= bh <= 60
        and aspect <= 1.75
        and 0.74 <= fill <= 1.0
        and color["red"] >= 0.72
        and color["warm"] >= 0.82
        and color["colored"] >= 0.84
        and color["white"] <= 0.04
        and color["dark"] <= 0.10
        and 0.16 <= color["edge"] <= 0.34
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    orange = (hue >= 10) & (hue <= 28) & (sat > 70) & (val > 70) & local
    yellow = (hue >= 20) & (hue <= 45) & (sat > 70) & (val > 95) & local
    greenblue = (hue >= 55) & (hue <= 135) & (sat > 45) & (val > 70) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    yellow_rows = yellow.sum(axis=1) / row_den
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den
    return (
        float(orange.sum()) / denom >= 0.45
        and float(yellow.sum()) / denom >= 0.38
        and float(greenblue.sum()) / denom >= 0.045
        and float((yellow_rows >= 0.12).mean()) >= 0.62
        and float((edge_rows >= 0.15).mean()) >= 0.62
        and float((edge_cols >= 0.15).mean()) >= 0.42
    )


def _is_paired_square_sponsor_badge_panel_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for mirrored square-ish multicolor sponsor badge panels."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0020 <= area_frac <= 0.0032
        and 46 <= bw <= 72
        and 56 <= bh <= 82
        and 1.02 <= aspect <= 1.45
        and 0.62 <= fill <= 0.84
        and 0.22 <= color["red"] <= 0.42
        and 0.36 <= color["warm"] <= 0.62
        and 0.62 <= color["colored"] <= 0.88
        and 0.07 <= color["white"] <= 0.19
        and color["dark"] <= 0.11
        and 0.26 <= color["edge"] <= 0.38
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    orange = (hue >= 8) & (hue <= 26) & (sat > 65) & (val > 70) & local
    yellow = (hue >= 22) & (hue <= 50) & (sat > 55) & (val > 92) & local
    green = (hue >= 42) & (hue <= 92) & (sat > 45) & (val > 65) & local
    blue = (hue >= 88) & (hue <= 135) & (sat > 45) & (val > 70) & local
    pale = (sat < 90) & (val > 145) & local
    dark = (val < 84) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    yellow_rows = yellow.sum(axis=1) / row_den
    yellow_cols = yellow.sum(axis=0) / col_den
    blue_rows = blue.sum(axis=1) / row_den
    blue_cols = blue.sum(axis=0) / col_den
    pale_cols = pale.sum(axis=0) / col_den
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den
    if not (
        float(orange.sum()) / denom >= 0.14
        and float(yellow.sum()) / denom >= 0.24
        and float(green.sum()) / denom >= 0.04
        and float(blue.sum()) / denom >= 0.16
        and float(pale.sum()) / denom >= 0.07
        and float(dark.sum()) / denom <= 0.10
        and float(edges.sum()) / denom >= 0.24
        and float((yellow_rows >= 0.14).mean()) >= 0.50
        and float((yellow_cols >= 0.12).mean()) >= 0.65
        and float((blue_rows >= 0.12).mean()) >= 0.35
        and float((blue_cols >= 0.12).mean()) >= 0.58
        and float((pale_cols >= 0.10).mean()) >= 0.50
        and float((edge_rows >= 0.14).mean()) >= 0.68
        and float((edge_cols >= 0.14).mean()) >= 0.78
    ):
        return False

    ih, iw = labels.shape[:2]
    cx = x + bw * 0.5
    cy = y + bh * 0.5
    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area < 20:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        if ow <= 0 or oh <= 0:
            continue
        other_fill = other_area / float(max(1, ow * oh))
        ocx = ox + ow * 0.5
        ocy = oy + oh * 0.5
        vertical_overlap = max(0, min(y + bh, oy + oh) - max(y, oy)) / float(max(1, min(bh, oh)))
        center_sep = abs(ocx - cx) / float(max(1, iw))
        sibling_color = _component_color_fractions(source_rgb, labels == other_idx, [ox, oy, ow, oh])
        if (
            0.65 <= other_area / float(max(1, area_px)) <= 1.45
            and abs(ow - bw) <= 12
            and abs(oh - bh) <= 12
            and abs(other_fill - fill) <= 0.16
            and abs(ocy - cy) <= max(8.0, bh * 0.16)
            and vertical_overlap >= 0.78
            and 0.18 <= center_sep <= 0.62
            and abs(sibling_color["warm"] - color["warm"]) <= 0.18
            and abs(sibling_color["colored"] - color["colored"]) <= 0.18
            and abs(sibling_color["white"] - color["white"]) <= 0.10
            and sibling_color["dark"] <= 0.13
        ):
            return True
    return False


def _is_wide_paired_sponsor_logo_panel_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for paired wide sponsor-logo panels already correctly in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0015 <= area_frac <= 0.0024
        and 85 <= bw <= 130
        and 34 <= bh <= 62
        and 1.75 <= aspect <= 2.75
        and 0.34 <= fill <= 0.50
        and 0.52 <= color["red"] <= 0.76
        and 0.16 <= color["white"] <= 0.24
        and 0.58 <= color["colored"] <= 0.74
        and color["dark"] <= 0.14
        and 0.18 <= color["edge"] <= 0.30
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    pale = (sat < 95) & (val > 140) & local
    dark = (val < 84) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den
    if not (
        float(pale.sum()) / denom >= 0.18
        and float(dark.sum()) / denom <= 0.13
        and float((edge_rows >= 0.14).mean()) >= 0.58
        and float((edge_cols >= 0.14).mean()) >= 0.68
    ):
        return False

    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area < 400:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = abs((oy + oh * 0.5) - (y + bh * 0.5))
        if (
            dx <= 38
            and dy <= 16
            and abs(ow - bw) <= 12
            and abs(oh - bh) <= 12
            and 0.72 <= other_area / float(max(1, area_px)) <= 1.28
        ):
            return True
    return False


def _is_vertically_repeated_red_sponsor_card_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for repeated wide red sponsor-card panels already in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0030 <= area_frac <= 0.0048
        and 88 <= bw <= 140
        and 36 <= bh <= 62
        and 1.85 <= aspect <= 2.90
        and 0.68 <= fill <= 0.86
        and 0.80 <= color["red"] <= 0.94
        and 0.075 <= color["white"] <= 0.16
        and color["colored"] >= 0.80
        and color["dark"] <= 0.08
        and 0.13 <= color["edge"] <= 0.24
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    pale = (sat < 95) & (val > 140) & local
    dark = (val < 84) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den
    if not (
        0.085 <= float(pale.sum()) / denom <= 0.15
        and float(dark.sum()) / denom <= 0.08
        and float((edge_rows >= 0.08).mean()) >= 0.48
        and float((edge_cols >= 0.08).mean()) >= 0.48
        and float(edge_rows.max()) >= 0.60
        and float(edge_cols.max()) >= 0.45
    ):
        return False

    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    cx = x + bw * 0.5
    cy = y + bh * 0.5
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area < 2400:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        if ow <= 0 or oh <= 0:
            continue
        ocx = ox + ow * 0.5
        ocy = oy + oh * 0.5
        horizontal_overlap = max(0, min(x + bw, ox + ow) - max(x, ox)) / float(max(1, min(bw, ow)))
        vertical_gap = max(oy - (y + bh), y - (oy + oh), 0)
        sibling_color = _component_color_fractions(source_rgb, labels == other_idx, [ox, oy, ow, oh])
        if (
            0.86 <= other_area / float(max(1, area_px)) <= 1.16
            and abs(ow - bw) <= 10
            and abs(oh - bh) <= 8
            and horizontal_overlap >= 0.88
            and abs(ocx - cx) <= 10.0
            and 54 <= vertical_gap <= 170
            and abs(ocy - cy) >= 70
            and abs(sibling_color["red"] - color["red"]) <= 0.04
            and abs(sibling_color["white"] - color["white"]) <= 0.025
            and sibling_color["dark"] <= 0.08
            and 0.13 <= sibling_color["edge"] <= 0.24
        ):
            return True
    return False


def _is_compact_blue_pale_sponsor_badge_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for compact blue/pale/yellow sponsor-logo badges already in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0009 <= area_frac <= 0.0022
        and 32 <= bw <= 58
        and 32 <= bh <= 58
        and aspect <= 1.16
        and 0.74 <= fill <= 0.86
        and 0.78 <= color["colored"] <= 0.90
        and 0.10 <= color["white"] <= 0.16
        and color["dark"] <= 0.11
        and 0.18 <= color["edge"] <= 0.39
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    blue = (hue >= 88) & (hue <= 140) & (sat > 45) & (val > 70) & local
    yellow = (hue >= 18) & (hue <= 50) & (sat > 55) & (val > 90) & local
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55) & local)
    pale = (sat < 95) & (val > 140) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den
    return (
        float(blue.sum()) / denom >= 0.20
        and float(pale.sum()) / denom >= 0.13
        and (float(yellow.sum()) / denom >= 0.18 or float(red.sum()) / denom >= 0.52)
        and float((edge_rows >= 0.14).mean()) >= 0.62
        and float((edge_cols >= 0.14).mean()) >= 0.62
    )


def _is_black_panel_yellow_sponsor_text_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for yellow/red sponsor text strokes on a black sponsor panel."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.00003 <= area_frac <= 0.0018
        and 8 <= bw <= 140
        and 6 <= bh <= 58
        and aspect <= 7.20
        and 0.24 <= fill <= 0.86
        and color["white"] <= 0.12
        and color["colored"] >= 0.45
        and color["dark"] >= 0.14
        and 0.22 <= color["edge"] <= 0.39
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    yellow = (hue >= 18) & (hue <= 45) & (sat > 70) & (val > 95) & local
    redorange = (((hue <= 14) | (hue >= 170) | ((hue >= 10) & (hue <= 28))) & (sat > 70) & (val > 55) & local)
    dark = (val < 88) & local
    black = (val < 52) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    yellow_rows = yellow.sum(axis=1) / row_den
    yellow_cols = yellow.sum(axis=0) / col_den
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den

    pad = max(8, min(90, int(round(max(bw, bh) * 0.50))))
    ih, iw = source_rgb.shape[:2]
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(iw, x + bw + pad), min(ih, y + bh + pad)
    context = source_rgb[y1:y2, x1:x2]
    if context.size == 0:
        return False
    ctx_hsv = cv2.cvtColor(context, cv2.COLOR_RGB2HSV)
    yy, xx = np.indices(context.shape[:2])
    inner = (xx >= x - x1) & (xx < x - x1 + bw) & (yy >= y - y1) & (yy < y - y1 + bh)
    ring = ~inner
    if not ring.any():
        return False
    rhue = ctx_hsv[:, :, 0]
    rsat = ctx_hsv[:, :, 1]
    rval = ctx_hsv[:, :, 2]
    ring_black = float((rval[ring] < 52).mean())
    ring_dark = float((rval[ring] < 88).mean())
    ring_yellow = float(((rhue[ring] >= 18) & (rhue[ring] <= 45) & (rsat[ring] > 70) & (rval[ring] > 95)).mean())

    return (
        float(yellow.sum()) / denom >= 0.40
        and float(redorange.sum()) / denom >= 0.50
        and float(dark.sum()) / denom >= 0.14
        and float(black.sum()) / denom >= 0.10
        and float(edges.sum()) / denom >= 0.22
        and float((yellow_rows >= 0.22).mean()) >= 0.50
        and float((yellow_cols >= 0.20).mean()) >= 0.55
        and (
            float((edge_rows >= 0.18).mean()) >= 0.30
            or float((edge_cols >= 0.18).mean()) >= 0.35
        )
        and (ring_black >= 0.55 or ring_dark >= 0.68)
        and ring_yellow <= 0.30
    )


def _is_distressed_yellow_wordmark_sponsor_card_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for distressed yellow/red sponsor cards with real wordmark ink."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.0030 <= area_frac <= 0.0064
        and 82 <= bw <= 150
        and 36 <= bh <= 72
        and 1.45 <= aspect <= 3.20
        and 0.52 <= fill <= 0.84
        and 0.46 <= color["warm"] <= 0.74
        and 0.52 <= color["colored"] <= 0.78
        and 0.075 <= color["white"] <= 0.19
        and 0.10 <= color["dark"] <= 0.30
        and 0.17 <= color["edge"] <= 0.34
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    yellow = (hue >= 18) & (hue <= 46) & (sat > 55) & (val > 88) & local
    redorange = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 30))) & (sat > 72) & (val > 55) & local)
    purple_blue = (hue >= 88) & (hue <= 168) & (sat > 42) & (val > 64) & local
    pale = (sat < 98) & (val > 140) & local
    dark = (val < 92) & local
    black = (val < 55) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    yellow_rows = yellow.sum(axis=1) / row_den
    edge_rows = edges.sum(axis=1) / row_den
    edge_cols = edges.sum(axis=0) / col_den
    pale_rows = pale.sum(axis=1) / row_den
    dark_cols = dark.sum(axis=0) / col_den
    return (
        float(yellow.sum()) / denom >= 0.42
        and float(redorange.sum()) / denom >= 0.44
        and float(purple_blue.sum()) / denom >= 0.055
        and float(pale.sum()) / denom >= 0.075
        and float(dark.sum()) / denom >= 0.12
        and float(black.sum()) / denom >= 0.035
        and float(edges.sum()) / denom >= 0.17
        and float((yellow_rows >= 0.20).mean()) >= 0.62
        and float((edge_rows >= 0.10).mean()) >= 0.70
        and float((edge_cols >= 0.10).mean()) >= 0.70
        and float(pale_rows.max(initial=0.0)) >= 0.22
        and float(dark_cols.max(initial=0.0)) >= 0.62
    )


def _is_edge_contingency_sponsor_panel_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for edge-mounted contingency/sponsor stacks already in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    ih, iw = source_rgb.shape[:2]
    touches_vertical_edge = x <= 8 or (x + bw) >= (iw - 8)
    if not (
        touches_vertical_edge
        and 0.010 <= area_frac <= 0.040
        and 42 <= bw <= 120
        and 170 <= bh <= 460
        and 3.10 <= aspect <= 7.40
        and fill >= 0.82
        and color["warm"] >= 0.70
        and color["colored"] >= 0.62
        and 0.035 <= color["white"] <= 0.22
        and color["dark"] <= 0.18
        and color["edge"] <= 0.18
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = (cv2.Canny(gray, 45, 120) > 0) & local
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    yellow = (hue >= 18) & (hue <= 45) & (sat > 65) & (val > 90) & local
    orange = (hue >= 10) & (hue <= 30) & (sat > 65) & (val > 55) & local
    white = (sat < 65) & (val > 150) & local
    dark = (val < 88) & local
    denom = float(max(1, int(local.sum())))
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    yellow_rows = yellow.sum(axis=1) / row_den
    yellow_cols = yellow.sum(axis=0) / col_den
    white_rows = white.sum(axis=1) / row_den
    edge_rows = edges.sum(axis=1) / row_den
    dark_cols = dark.sum(axis=0) / col_den

    pad = max(24, min(150, int(round(max(bw, bh) * 0.40))))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(iw, x + bw + pad), min(ih, y + bh + pad)
    context = source_rgb[y1:y2, x1:x2]
    if context.size == 0:
        return False
    ctx_hsv = cv2.cvtColor(context, cv2.COLOR_RGB2HSV)
    yy, xx = np.indices(context.shape[:2])
    inner = (xx >= x - x1) & (xx < x - x1 + bw) & (yy >= y - y1) & (yy < y - y1 + bh)
    ring = ~inner
    if not ring.any():
        return False
    rhue = ctx_hsv[:, :, 0]
    rsat = ctx_hsv[:, :, 1]
    rval = ctx_hsv[:, :, 2]
    ring_dark = float((rval[ring] < 90).mean())
    ring_black = float((rval[ring] < 56).mean())
    ring_yellow = float(((rhue[ring] >= 18) & (rhue[ring] <= 45) & (rsat[ring] > 65) & (rval[ring] > 90)).mean())

    return (
        float(yellow.sum()) / denom >= 0.52
        and float(orange.sum()) / denom >= 0.38
        and float(white.sum()) / denom >= 0.035
        and float(edges.sum()) / denom >= 0.045
        and float((yellow_rows >= 0.25).mean()) >= 0.72
        and float((yellow_cols >= 0.25).mean()) >= 0.72
        and float((white_rows >= 0.035).mean()) >= 0.16
        and float((edge_rows >= 0.06).mean()) >= 0.16
        and float((dark_cols >= 0.20).mean()) <= 0.22
        and (ring_dark >= 0.48 or ring_black >= 0.45)
        and ring_yellow <= 0.22
    )


def _is_dark_panel_yellow_sponsor_mark_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for yellow sponsor-logo marks embedded in black sponsor panels."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.00035 <= area_frac <= 0.0033
        and 22 <= bw <= 78
        and 18 <= bh <= 190
        and 1.00 <= aspect <= 4.40
        and 0.20 <= fill <= 0.64
        and color["warm"] >= 0.86
        and color["colored"] >= 0.82
        and color["white"] <= 0.04
        and color["dark"] <= 0.14
        and color["edge"] <= 0.31
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    yellow = (hue >= 18) & (hue <= 45) & (sat > 65) & (val > 90) & local
    orange = (hue >= 10) & (hue <= 30) & (sat > 65) & (val > 55) & local
    denom = float(max(1, int(local.sum())))

    ih, iw = source_rgb.shape[:2]
    pad = max(20, min(105, int(round(max(bw, bh) * 0.55))))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(iw, x + bw + pad), min(ih, y + bh + pad)
    context = source_rgb[y1:y2, x1:x2]
    if context.size == 0:
        return False
    ctx_hsv = cv2.cvtColor(context, cv2.COLOR_RGB2HSV)
    yy, xx = np.indices(context.shape[:2])
    inner = (xx >= x - x1) & (xx < x - x1 + bw) & (yy >= y - y1) & (yy < y - y1 + bh)
    ring = ~inner
    if not ring.any():
        return False
    rhue = ctx_hsv[:, :, 0]
    rsat = ctx_hsv[:, :, 1]
    rval = ctx_hsv[:, :, 2]
    ring_dark = float((rval[ring] < 90).mean())
    ring_black = float((rval[ring] < 56).mean())
    ring_yellow = float(((rhue[ring] >= 18) & (rhue[ring] <= 45) & (rsat[ring] > 65) & (rval[ring] > 90)).mean())
    ring_white = float(((rsat[ring] < 70) & (rval[ring] > 145)).mean())

    return (
        float(yellow.sum()) / denom >= 0.62
        and float(orange.sum()) / denom >= 0.45
        and (ring_dark >= 0.62 or ring_black >= 0.58)
        and 0.07 <= ring_yellow <= 0.32
        and ring_white <= 0.08
    )


def _is_green_wordmark_separator_bar_review(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for colored divider bars embedded in green sponsor wordmark panels."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.00018 <= area_frac <= 0.0045
        and aspect >= 9.0
        and 2 <= min(bw, bh) <= 16
        and max(bw, bh) <= 150
        and 0.58 <= fill <= 1.0
        and color["colored"] >= 0.90
        and color["white"] <= 0.045
        and color["dark"] <= 0.065
        and color["red"] <= 0.08
        and 0.13 <= color["edge"] <= 0.58
    ):
        return False

    ih, iw = source_rgb.shape[:2]
    pad = max(24, min(110, int(round(max(bw, bh) * 1.20))))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(iw, x + bw + pad), min(ih, y + bh + pad)
    context = source_rgb[y1:y2, x1:x2]
    if context.size == 0:
        return False
    ctx_hsv = cv2.cvtColor(context, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(context, cv2.COLOR_RGB2GRAY)
    edge = cv2.Canny(gray, 45, 120) > 0
    yy, xx = np.indices(context.shape[:2])
    inner = (xx >= x - x1) & (xx < x - x1 + bw) & (yy >= y - y1) & (yy < y - y1 + bh)
    ring = ~inner
    if not ring.any():
        return False

    grow = max(18, min(72, int(round(max(bw, bh) * 0.55))))
    near = np.zeros(ring.shape, bool)
    near[
        max(0, y - y1 - grow):min(context.shape[0], y - y1 + bh + grow),
        max(0, x - x1 - grow):min(context.shape[1], x - x1 + bw + grow),
    ] = True
    near &= ring
    if not near.any():
        return False

    hue = ctx_hsv[:, :, 0]
    sat = ctx_hsv[:, :, 1]
    val = ctx_hsv[:, :, 2]
    white = (sat < 70) & (val > 145)
    green = (hue >= 42) & (hue <= 92) & (sat > 55) & (val > 70)

    white_near = float(white[near].mean())
    green_near = float(green[near].mean())
    edge_near = float(edge[near].mean())
    if not (white_near >= 0.065 and green_near >= 0.160 and edge_near >= 0.095):
        return False

    num, labels, stats, _cent = cv2.connectedComponentsWithStats((white & near).astype(np.uint8), 8)
    boxes: list[tuple[int, int, int, int]] = []
    for idx in range(1, num):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < 15:
            continue
        bx = int(stats[idx, cv2.CC_STAT_LEFT])
        by = int(stats[idx, cv2.CC_STAT_TOP])
        ww = int(stats[idx, cv2.CC_STAT_WIDTH])
        hh = int(stats[idx, cv2.CC_STAT_HEIGHT])
        if ww <= 0 or hh <= 0:
            continue
        boxes.append((bx, by, ww, hh))
    if len(boxes) < 4:
        return False

    min_x = min(bx for bx, _by, _ww, _hh in boxes)
    max_x = max(bx + ww for bx, _by, ww, _hh in boxes)
    min_y = min(by for _bx, by, _ww, _hh in boxes)
    max_y = max(by + hh for _bx, by, _ww, hh in boxes)
    span_x = (max_x - min_x) / float(max(1, iw))
    span_y = (max_y - min_y) / float(max(1, ih))
    return span_x >= 0.08 or span_y >= 0.08


def _is_sponsor_panel_wordmark_detail_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for compact sponsor wordmark details embedded in sponsor clusters."""
    x, y, bw, bh = [int(v) for v in bbox]
    if not (
        0.00010 <= area_frac <= 0.0048
        and 6 <= bw <= 80
        and 8 <= bh <= 90
        and aspect <= 3.60
        and 0.24 <= fill <= 0.90
        and color["warm"] >= 0.45
        and color["colored"] >= 0.52
        and 0.12 <= color["edge"] <= 0.56
        and color["white"] <= 0.24
        and color["dark"] <= 0.22
    ):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False

    ih, iw = source_rgb.shape[:2]
    pad = max(18, min(96, int(round(max(bw, bh) * 1.15))))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(iw, x + bw + pad), min(ih, y + bh + pad)
    context = source_rgb[y1:y2, x1:x2]
    if context.size == 0:
        return False

    ctx_hsv = cv2.cvtColor(context, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(context, cv2.COLOR_RGB2GRAY)
    edge = cv2.Canny(gray, 45, 120) > 0
    yy, xx = np.indices(context.shape[:2])
    inner = (xx >= x - x1) & (xx < x - x1 + bw) & (yy >= y - y1) & (yy < y - y1 + bh)
    ring = ~inner
    if not ring.any():
        return False

    hue = ctx_hsv[:, :, 0]
    sat = ctx_hsv[:, :, 1]
    val = ctx_hsv[:, :, 2]
    green = (hue >= 42) & (hue <= 92) & (sat > 55) & (val > 70)
    warm = (((hue <= 42) | (hue >= 170)) & (sat > 70) & (val > 55))
    yellow = (hue >= 18) & (hue <= 45) & (sat > 65) & (val > 90)
    pale = (sat < 90) & (val > 132)
    dark = val < 90

    ring_green = float(green[ring].mean())
    ring_warm = float(warm[ring].mean())
    ring_yellow = float(yellow[ring].mean())
    ring_pale = float(pale[ring].mean())
    ring_dark = float(dark[ring].mean())
    ring_edge = float(edge[ring].mean())

    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    sibling_boxes: list[tuple[int, int, int, int]] = []
    close_siblings = 0
    near_limit = max(42.0, min(86.0, max(bw, bh) * 1.55))
    close_limit = max(13.0, min(28.0, max(bw, bh) * 0.55))
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area < 20 or other_area > max(4200, area_px * 28):
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        if ow <= 0 or oh <= 0:
            continue
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = max(oy - (y + bh), y - (oy + oh), 0)
        dist = float((dx * dx + dy * dy) ** 0.5)
        if dist > near_limit:
            continue
        sibling_boxes.append((ox, oy, ow, oh))
        if dist <= close_limit:
            close_siblings += 1

    if sibling_boxes:
        min_x = min(ox for ox, _oy, _ow, _oh in sibling_boxes)
        max_x = max(ox + ow for ox, _oy, ow, _oh in sibling_boxes)
        min_y = min(oy for _ox, oy, _ow, _oh in sibling_boxes)
        max_y = max(oy + oh for _ox, oy, _ow, oh in sibling_boxes)
        sibling_span_x = (max_x - min_x) / float(max(1, iw))
        sibling_span_y = (max_y - min_y) / float(max(1, ih))
    else:
        sibling_span_x = 0.0
        sibling_span_y = 0.0

    green_card_detail = (
        area_frac <= 0.0009
        and bw <= 28
        and bh <= 32
        and color["red"] >= 0.46
        and color["white"] >= 0.06
        and ring_green >= 0.24
        and ring_pale >= 0.08
        and ring_edge >= 0.05
        and ring_dark <= 0.42
        and close_siblings >= 1
    )
    warm_cluster_badge = (
        0.0018 <= area_frac <= 0.0048
        and 18 <= bw <= 70
        and 24 <= bh <= 82
        and 0.60 <= aspect <= 2.20
        and 0.36 <= fill <= 0.78
        and color["red"] >= 0.54
        and color["warm"] >= 0.78
        and color["colored"] >= 0.82
        and 0.015 <= color["white"] <= 0.085
        and color["dark"] <= 0.07
        and 0.24 <= color["edge"] <= 0.50
        and ring_warm >= 0.62
        and ring_yellow >= 0.08
        and ring_edge >= 0.08
        and len(sibling_boxes) >= 2
        and (sibling_span_x >= 0.08 or sibling_span_y >= 0.08)
    )
    return green_card_detail or warm_cluster_badge


def _is_orange_cream_sponsor_logo_cluster_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for repeated orange/cream DLM sponsor-logo panels already in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    mascot_logo_panel = (
        0.0050 <= area_frac <= 0.0268
        and 90 <= bw <= 190
        and 55 <= bh <= 205
        and 0.80 <= aspect <= 3.20
        and 0.50 <= fill <= 0.78
        and 0.48 <= color["red"] <= 0.92
        and 0.48 <= color["warm"] <= 0.92
        and 0.48 <= color["colored"] <= 0.92
        and 0.045 <= color["white"] <= 0.30
        and color["dark"] <= 0.42
        and 0.080 <= color["edge"] <= 0.240
    )
    orange_logo_chip = (
        0.00045 <= area_frac <= 0.00110
        and 18 <= bw <= 38
        and 18 <= bh <= 44
        and 0.85 <= aspect <= 1.80
        and 0.72 <= fill <= 0.92
        and color["red"] >= 0.84
        and color["warm"] >= 0.84
        and color["colored"] >= 0.84
        and color["white"] <= 0.025
        and 0.060 <= color["dark"] <= 0.18
        and 0.10 <= color["edge"] <= 0.22
    )
    large_logo_panel = (
        0.0060 <= area_frac <= 0.0160
        and 95 <= bw <= 175
        and 90 <= bh <= 190
        and 0.90 <= aspect <= 1.50
        and 0.48 <= fill <= 0.68
        and 0.54 <= color["red"] <= 0.72
        and 0.54 <= color["warm"] <= 0.72
        and 0.54 <= color["colored"] <= 0.72
        and color["white"] <= 0.040
        and 0.28 <= color["dark"] <= 0.50
        and 0.080 <= color["edge"] <= 0.180
    )
    paired_logo_fragment = (
        0.00055 <= area_frac <= 0.00110
        and 22 <= bw <= 42
        and 28 <= bh <= 52
        and 1.05 <= aspect <= 1.80
        and 0.55 <= fill <= 0.82
        and color["red"] >= 0.90
        and color["warm"] >= 0.90
        and color["colored"] >= 0.90
        and color["white"] <= 0.025
        and color["dark"] <= 0.065
        and 0.080 <= color["edge"] <= 0.160
    )
    if not (mascot_logo_panel or orange_logo_chip or large_logo_panel or paired_logo_fragment):
        return False

    canvas_area = float(max(1, labels.shape[0] * labels.shape[1]))
    repeated_mascot_panels = 0
    close_mascot_panels = 0
    repeated_large_panels = 0
    close_small_fragments = 0
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if ow <= 0 or oh <= 0 or other_area < 20:
            continue
        other_area_frac = other_area / canvas_area
        other_fill = other_area / float(max(1, ow * oh))
        other_aspect = max(ow / float(max(1, oh)), oh / float(max(1, ow)))
        other_color = _component_color_fractions(source_rgb, labels == other_idx, [ox, oy, ow, oh])
        other_mascot_panel = (
            0.0046 <= other_area_frac <= 0.0285
            and 80 <= ow <= 205
            and 50 <= oh <= 220
            and 0.75 <= other_aspect <= 3.35
            and 0.46 <= other_fill <= 0.82
            and 0.44 <= other_color["red"] <= 0.95
            and 0.44 <= other_color["warm"] <= 0.95
            and 0.44 <= other_color["colored"] <= 0.95
            and other_color["white"] <= 0.26
            and other_color["dark"] <= 0.46
            and 0.070 <= other_color["edge"] <= 0.260
        )
        other_large_logo_panel = (
            0.0058 <= other_area_frac <= 0.0175
            and 90 <= ow <= 185
            and 85 <= oh <= 200
            and 0.85 <= other_aspect <= 1.60
            and 0.46 <= other_fill <= 0.70
            and 0.50 <= other_color["red"] <= 0.76
            and 0.50 <= other_color["warm"] <= 0.76
            and 0.50 <= other_color["colored"] <= 0.76
        )
        other_small_logo_fragment = (
            0.00045 <= other_area_frac <= 0.00125
            and 18 <= ow <= 48
            and 24 <= oh <= 58
            and 1.00 <= other_aspect <= 1.95
            and 0.50 <= other_fill <= 0.86
            and other_color["red"] >= 0.84
            and other_color["warm"] >= 0.84
            and other_color["colored"] >= 0.84
        )
        if large_logo_panel and other_large_logo_panel:
            repeated_large_panels += 1
        if mascot_logo_panel and other_mascot_panel:
            repeated_mascot_panels += 1
        if orange_logo_chip and other_mascot_panel:
            dx = max(ox - (x + bw), x - (ox + ow), 0)
            dy = max(oy - (y + bh), y - (oy + oh), 0)
            if float((dx * dx + dy * dy) ** 0.5) <= 96.0:
                close_mascot_panels += 1
        if paired_logo_fragment and other_small_logo_fragment:
            dx = max(ox - (x + bw), x - (ox + ow), 0)
            dy = max(oy - (y + bh), y - (oy + oh), 0)
            if float((dx * dx + dy * dy) ** 0.5) <= max(22.0, max(bw, bh) * 0.80):
                close_small_fragments += 1

    if mascot_logo_panel:
        crop = source_rgb[y:y + bh, x:x + bw]
        local = comp_mask[y:y + bh, x:x + bw]
        if crop.size == 0 or not local.any():
            return False
        hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        hue = hsv[:, :, 0]
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        cream = ((hue >= 12) & (hue <= 35) & (sat > 20) & (sat < 115) & (val > 130) & local)
        white = ((sat < 85) & (val > 150) & local)
        dark = ((val < 95) & local)
        edges = ((cv2.Canny(gray, 45, 120) > 0) & local)
        denom = float(max(1, int(local.sum())))
        col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
        row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
        active_cols = local.sum(axis=0) > 0
        active_rows = local.sum(axis=1) > 0
        cream_cols = cream.sum(axis=0) / col_den
        white_cols = white.sum(axis=0) / col_den
        dark_cols = dark.sum(axis=0) / col_den
        edge_rows = edges.sum(axis=1) / row_den
        internal_logo_anatomy = (
            (float(cream.sum()) / denom >= 0.045 or float(white.sum()) / denom >= 0.060)
            and (float(dark.sum()) / denom >= 0.025 or float(edges.sum()) / denom >= 0.13)
            and (
                float((cream_cols[active_cols] >= 0.08).mean()) >= 0.16
                or float((white_cols[active_cols] >= 0.08).mean()) >= 0.18
                or float((dark_cols[active_cols] >= 0.06).mean()) >= 0.30
            )
            and float((edge_rows[active_rows] >= 0.12).mean()) >= 0.12
        )
        single_rich_mascot_decal = (
            repeated_mascot_panels == 0
            and area_frac >= 0.0058
            and fill >= 0.58
            and color["white"] >= 0.18
            and color["dark"] >= 0.10
            and color["edge"] >= 0.18
        )
        return (repeated_mascot_panels >= 1 or single_rich_mascot_decal) and internal_logo_anatomy

    if orange_logo_chip:
        return close_mascot_panels >= 1

    if large_logo_panel:
        return repeated_large_panels >= 1

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
    ring = (cv2.dilate(comp_mask.astype(np.uint8), kernel) > 0) & ~comp_mask
    if not ring.any():
        return False
    hsv = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    ring_red = float(((((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 80) & (val > 55))[ring]).mean())
    ring_white = float((((sat < 70) & (val > 132))[ring]).mean())
    ring_dark = float(((val < 84)[ring]).mean())
    ring_sponsor = float(((labels > 0)[ring]).mean())
    return (
        close_small_fragments >= 1
        and 0.14 <= ring_red <= 0.48
        and ring_white <= 0.040
        and ring_dark >= 0.45
        and ring_sponsor <= 0.22
    )


def _is_red_white_sponsor_icon_cell_review(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    stats: np.ndarray,
    component_idx: int,
    comp_mask: np.ndarray,
    bbox: list[int],
    area_frac: float,
    fill: float,
    aspect: float,
    color: dict[str, float],
) -> bool:
    """True for compact red/white sponsor icon cells already in Sponsors."""
    x, y, bw, bh = [int(v) for v in bbox]
    tiny_icon = (
        0.00030 <= area_frac <= 0.00060
        and 18 <= bw <= 30
        and 18 <= bh <= 30
        and aspect <= 1.30
        and 0.78 <= fill <= 0.96
        and 0.62 <= color["red"] <= 0.84
        and 0.62 <= color["warm"] <= 0.84
        and 0.62 <= color["colored"] <= 0.84
        and 0.18 <= color["white"] <= 0.34
        and color["dark"] <= 0.035
        and 0.26 <= color["edge"] <= 0.44
    )
    stacked_logo_cell = (
        0.0032 <= area_frac <= 0.0046
        and 56 <= bw <= 86
        and 82 <= bh <= 116
        and 1.15 <= aspect <= 1.75
        and 0.50 <= fill <= 0.68
        and 0.66 <= color["red"] <= 0.86
        and 0.66 <= color["warm"] <= 0.86
        and 0.66 <= color["colored"] <= 0.88
        and 0.040 <= color["white"] <= 0.10
        and 0.12 <= color["dark"] <= 0.24
        and 0.080 <= color["edge"] <= 0.150
    )
    if not (tiny_icon or stacked_logo_cell):
        return False

    crop = source_rgb[y:y + bh, x:x + bw]
    local = comp_mask[y:y + bh, x:x + bw]
    if crop.size == 0 or not local.any():
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    red = (((hue <= 14) | (hue >= 170) | ((hue >= 15) & (hue <= 28))) & (sat > 70) & (val > 55) & local)
    white = ((sat < 90) & (val > 132) & local)
    dark = ((val < 92) & local)
    edges = ((cv2.Canny(gray, 45, 120) > 0) & local)
    row_den = np.maximum(1, local.sum(axis=1)).astype(np.float32)
    col_den = np.maximum(1, local.sum(axis=0)).astype(np.float32)
    active_rows = local.sum(axis=1) > 0
    active_cols = local.sum(axis=0) > 0

    def _span_score(mask: np.ndarray, cutoff: float) -> tuple[float, float, float, float]:
        rows = mask.sum(axis=1) / row_den
        cols = mask.sum(axis=0) / col_den
        row_score = float((rows[active_rows] >= cutoff).mean()) if active_rows.any() else 0.0
        col_score = float((cols[active_cols] >= cutoff).mean()) if active_cols.any() else 0.0
        return row_score, col_score, float(rows.max()) if rows.size else 0.0, float(cols.max()) if cols.size else 0.0

    red_rows, red_cols, _red_row_max, _red_col_max = _span_score(red, 0.12)
    white_rows, white_cols, white_row_max, white_col_max = _span_score(white, 0.12)
    dark_rows, dark_cols, dark_row_max, dark_col_max = _span_score(dark, 0.12)
    edge_rows, edge_cols, edge_row_max, edge_col_max = _span_score(edges, 0.12)

    area_px = int(stats[component_idx, cv2.CC_STAT_AREA])
    close_sponsor_neighbors = 0
    stacked_sibling = False
    for other_idx in range(1, stats.shape[0]):
        if other_idx == component_idx:
            continue
        other_area = int(stats[other_idx, cv2.CC_STAT_AREA])
        if other_area < 20:
            continue
        ox = int(stats[other_idx, cv2.CC_STAT_LEFT])
        oy = int(stats[other_idx, cv2.CC_STAT_TOP])
        ow = int(stats[other_idx, cv2.CC_STAT_WIDTH])
        oh = int(stats[other_idx, cv2.CC_STAT_HEIGHT])
        if ow <= 0 or oh <= 0:
            continue
        dx = max(ox - (x + bw), x - (ox + ow), 0)
        dy = max(oy - (y + bh), y - (oy + oh), 0)
        dist = float((dx * dx + dy * dy) ** 0.5)
        if dist <= 90.0 and 0.015 <= other_area / float(max(1, area_px)) <= 16.0:
            close_sponsor_neighbors += 1
        x_overlap = max(0, min(x + bw, ox + ow) - max(x, ox)) / float(max(1, min(bw, ow)))
        y_gap = max(oy - (y + bh), y - (oy + oh), 0)
        if (
            0.35 <= other_area / float(max(1, area_px)) <= 0.85
            and x_overlap >= 0.72
            and y_gap <= 8
            and abs((ox + ow * 0.5) - (x + bw * 0.5)) <= max(10.0, bw * 0.18)
        ):
            sibling_color = _component_color_fractions(source_rgb, labels == other_idx, [ox, oy, ow, oh])
            if sibling_color["dark"] >= 0.18 and sibling_color["white"] >= 0.04:
                stacked_sibling = True

    if tiny_icon:
        return (
            close_sponsor_neighbors >= 2
            and red_rows >= 0.82
            and red_cols >= 0.82
            and white_rows >= 0.42
            and white_cols >= 0.50
            and edge_rows >= 0.72
            and edge_cols >= 0.72
            and white_row_max >= 0.72
            and white_col_max >= 0.72
        )

    return (
        stacked_sibling
        and red_rows >= 0.72
        and red_cols >= 0.72
        and (white_rows >= 0.18 or white_cols >= 0.12 or white_row_max >= 0.80)
        and (dark_rows >= 0.18 or dark_cols >= 0.42 or dark_col_max >= 0.70)
        and edge_rows >= 0.32
        and edge_cols >= 0.22
        and edge_row_max >= 0.70
        and edge_col_max >= 0.70
    )


def _suspect_review_for_masks(source: Image.Image, masks: dict[str, np.ndarray], sample_dir: Path) -> tuple[list[dict[str, Any]], str | None]:
    """Export a compact review queue for likely wrong-bucket components.

    This does not alter Auto-build output. It keeps the one-car loop honest by
    surfacing the next visual suspects: whole graphic number badges, sponsor
    masks that look like livery stripes, and tiny Paint islands that still look
    like sponsor text/logo.
    """
    source_rgb = np.asarray(source)
    h, w = source_rgb.shape[:2]
    canvas_area = float(max(1, h * w))
    suspects: list[dict[str, Any]] = []
    for layer in ("numbers", "sponsors", "paint"):
        mask = masks.get(layer)
        if mask is None:
            continue
        n, labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        min_area = 20
        for idx in range(1, n):
            area_px = int(stats[idx, cv2.CC_STAT_AREA])
            if area_px < min_area:
                continue
            x = int(stats[idx, cv2.CC_STAT_LEFT])
            y = int(stats[idx, cv2.CC_STAT_TOP])
            bw = int(stats[idx, cv2.CC_STAT_WIDTH])
            bh = int(stats[idx, cv2.CC_STAT_HEIGHT])
            area_frac = area_px / canvas_area
            bbox_frac = (bw * bh) / canvas_area
            aspect = max(bw / float(max(1, bh)), bh / float(max(1, bw)))
            fill = area_px / float(max(1, bw * bh))
            comp_mask = labels == idx
            color = _component_color_fractions(source_rgb, comp_mask, [x, y, bw, bh])
            reason = None
            if layer == "numbers":
                if area_frac >= 0.0045 and bbox_frac >= 0.006 and fill >= 0.45 and color["edge"] >= 0.12:
                    if _is_repeated_large_number_graphic_review(
                        source_rgb,
                        labels,
                        stats,
                        idx,
                        comp_mask,
                        [x, y, bw, bh],
                        area_frac,
                        bbox_frac,
                        fill,
                        aspect,
                        color,
                    ):
                        continue
                    if _is_multi_position_race_number_art_review(
                        source_rgb,
                        labels,
                        stats,
                        idx,
                        comp_mask,
                        [x, y, bw, bh],
                        area_frac,
                        bbox_frac,
                        fill,
                        aspect,
                        color,
                    ):
                        continue
                    reason = "large_number_badge_or_graphic_review"
            elif layer == "sponsors":
                if _is_dark_panel_yellow_sponsor_mark_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                if _is_green_wordmark_separator_bar_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                if _is_sponsor_panel_wordmark_detail_review(
                    source_rgb,
                    labels,
                    stats,
                    idx,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_paired_square_sponsor_badge_panel_review(
                    source_rgb,
                    labels,
                    stats,
                    idx,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_orange_cream_sponsor_logo_cluster_review(
                    source_rgb,
                    labels,
                    stats,
                    idx,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_red_white_sponsor_icon_cell_review(
                    source_rgb,
                    labels,
                    stats,
                    idx,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_wide_paired_sponsor_logo_panel_review(
                    source_rgb,
                    labels,
                    stats,
                    idx,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_vertically_repeated_red_sponsor_card_review(
                    source_rgb,
                    labels,
                    stats,
                    idx,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_compact_blue_pale_sponsor_badge_review(
                    source_rgb,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_distressed_yellow_wordmark_sponsor_card_review(
                    source_rgb,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                if _is_compact_contingency_sponsor_badge_review(source_rgb, masks, labels, stats, idx, comp_mask, [x, y, bw, bh], color):
                    continue
                compact_warm_motif = (
                    0.00045 <= area_frac <= 0.0045
                    and 0.45 <= aspect <= 2.45
                    and 0.26 <= fill <= 0.88
                    and color["warm"] >= 0.46
                    and color["colored"] >= 0.55
                    and color["white"] < 0.22
                    and color["dark"] < 0.22
                    and 0.08 <= color["edge"] <= 0.38
                )
                if compact_warm_motif:
                    reason = "decorative_livery_like_sponsor_review"
                elif _is_paired_dark_panel_micro_sponsor(source_rgb, masks, labels, stats, idx, comp_mask, [x, y, bw, bh], color):
                    continue
                elif _is_tiny_contingency_sponsor_mark_review(source_rgb, masks, labels, stats, idx, comp_mask, [x, y, bw, bh], color):
                    continue
                elif _is_tiny_horizontal_contingency_sponsor_mark_review(source_rgb, masks, labels, stats, idx, comp_mask, [x, y, bw, bh], color):
                    continue
                elif _is_top_edge_number_panel_contingency_sponsor_chip_review(
                    source_rgb,
                    masks,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                elif _is_number_panel_embedded_contingency_strip_review(
                    source_rgb,
                    masks,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                elif _is_tiny_magenta_red_sponsor_detail_review(source_rgb, masks, labels, stats, idx, comp_mask, [x, y, bw, bh], color):
                    continue
                elif _is_clustered_red_white_sponsor_decal_review(
                    source_rgb,
                    masks,
                    labels,
                    stats,
                    idx,
                    comp_mask,
                    [x, y, bw, bh],
                    area_frac,
                    fill,
                    aspect,
                    color,
                ):
                    continue
                elif _is_compact_red_sponsor_wordmark_panel_review(source_rgb, masks, comp_mask, [x, y, bw, bh], fill, aspect, color):
                    continue
                elif _is_sidecar_red_logo_chip_review(source_rgb, masks, comp_mask, [x, y, bw, bh], fill, aspect, color):
                    continue
                elif _is_edge_contingency_sponsor_panel_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_black_panel_yellow_sponsor_text_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_sponsor_card_panel_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_stacked_sponsor_card_panel_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_vertical_multicolor_wordmark_decal_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_compact_multicolor_sponsor_badge_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_tiny_sponsor_wordmark_underline_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_vertical_sponsor_side_marker_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_long_blue_website_sponsor_strip_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_long_sponsor_wordmark_top_strip_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_long_textlike_url_sponsor_strip_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_long_red_white_sponsor_wordmark_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif color["red"] >= 0.48 and color["white"] < 0.25 and color["edge"] < 0.38:
                    reason = "red_livery_like_sponsor_review"
                elif aspect >= 9.0 and color["colored"] >= 0.35 and color["white"] < 0.35:
                    reason = "stripe_like_sponsor_review"
            elif layer == "paint":
                if area_frac < 0.006 and color["white"] >= 0.35 and color["edge"] >= 0.13:
                    reason = "remaining_text_like_paint_review"
                elif _is_low_fill_grille_mesh_paint_boundary_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_bottom_edge_flat_livery_panel_paint_review(source_rgb, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_cyan_template_livery_stripe_paint_review(source_rgb, masks, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif _is_template_adjacent_green_livery_edge_paint_review(source_rgb, masks, comp_mask, [x, y, bw, bh], area_frac, fill, aspect, color):
                    continue
                elif area_frac < 0.006 and color["colored"] >= 0.45 and color["edge"] >= 0.10:
                    reason = "remaining_logo_like_paint_review"
            if not reason:
                continue

            rec = {
                "layer": layer,
                "component_label": int(idx),
                "review_reason": reason,
                "area_px": area_px,
                "area_frac": round(area_frac, 7),
                "bbox": [x, y, bw, bh],
                "bbox_w_frac": round(float(bw) / float(max(1, w)), 5),
                "bbox_h_frac": round(float(bh) / float(max(1, h)), 5),
                "bbox_frac": round(bbox_frac, 7),
                "aspect": round(aspect, 4),
                "fill": round(fill, 4),
                **{f"{key}_frac": value for key, value in color.items()},
            }
            crop_path = sample_dir / "suspect_review_crops" / f"{len(suspects):03d}_{_safe_name(reason)}.png"
            rec["crop_file"] = _component_crop(source, comp_mask, rec["bbox"], f"{layer}:{reason}", crop_path)
            suspects.append(rec)

    suspects.sort(key=lambda item: (item["layer"] != "numbers", -float(item["area_frac"]), item["review_reason"]))
    sheet = _contact_sheet(suspects, sample_dir / "suspect_review_components.png", "Possible Smart TGA wrong-bucket components")
    return suspects, sheet


def inspect_paint(client: Any, paint: Path, args: argparse.Namespace) -> dict[str, Any]:
    body, elapsed, status_code = _post_auto_layers(client, paint, args)
    sample_dir = args.output / _safe_name(paint.parent.name + "_" + paint.stem)
    sample_dir.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "paint": str(paint),
        "paint_label": f"{paint.parent.name}/{paint.name}",
        "http_status": status_code,
        "elapsed_sec": round(float(elapsed), 3),
        "success": bool(body.get("success")),
    }
    if not body.get("success"):
        record["error"] = body.get("error")
        return record

    first_layer = next(iter((body.get("layers") or {}).values()))
    base_mask = _decode_data_url_mask(first_layer)
    size = (base_mask.shape[1], base_mask.shape[0])
    source = _read_source(paint, size)
    source_path = sample_dir / "source_1024.png"
    source.save(source_path)
    record["source_1024"] = str(source_path.resolve())

    masks: dict[str, np.ndarray] = {}
    mask_paths: dict[str, str] = {}
    components: list[dict[str, Any]] = []
    for layer in LAYER_ORDER:
        data_url = (body.get("layers") or {}).get(layer)
        if not data_url:
            continue
        mask = _decode_data_url_mask(data_url, size=size)
        masks[layer] = mask
        mask_paths[layer] = _write_mask_png(mask, sample_dir / "masks" / f"{layer}.png")
        layer_records = _components_for_layer(source, layer, mask, sample_dir)
        for rec in layer_records:
            rec["paint"] = str(paint)
            rec["paint_label"] = record["paint_label"]
        components.extend(layer_records)

    overlay_path = _write_overlay(source, masks, sample_dir / "route_layer_overlay.png")
    record.update({
        "route_engine": body.get("engine"),
        "route_smart_tga": body.get("smart_tga"),
        "route_fractions": body.get("fractions"),
        "route_gpu_cache": body.get("gpu_cache"),
        "route_adjudicator_shadow": body.get("adjudicator_shadow"),
        "route_template_guard": body.get("template_guard"),
        "route_layer_priority_guard": body.get("layer_priority_guard"),
        "route_sponsor_fragment_guard": body.get("sponsor_fragment_guard"),
        "route_isolated_wordmark_guard": body.get("isolated_wordmark_guard"),
        "route_tiny_logotype_guard": body.get("tiny_logotype_guard"),
        "route_micro_logotype_guard": body.get("micro_logotype_guard"),
        "route_colored_micro_logo_guard": body.get("colored_micro_logo_guard"),
        "route_bright_panel_micro_logo_guard": body.get("bright_panel_micro_logo_guard"),
        "route_panel_text_residual_guard": body.get("panel_text_residual_guard"),
        "route_stacked_front_clip_template_guard": body.get("stacked_front_clip_template_guard"),
        "route_horizontal_front_clip_template_guard": body.get("horizontal_front_clip_template_guard"),
        "route_paired_rear_lamp_template_guard": body.get("paired_rear_lamp_template_guard"),
        "route_number_template_false_positive_guard": body.get("number_template_false_positive_guard"),
        "route_template_contained_paint_trim_guard": body.get("template_contained_paint_trim_guard"),
        "route_neutral_body_watermark_template_guard": body.get("neutral_body_watermark_template_guard"),
        "route_faint_number_outline_guard": body.get("faint_number_outline_guard"),
        "route_flat_livery_sponsor_guard": body.get("flat_livery_sponsor_guard"),
        "route_warm_edge_livery_sponsor_guard": body.get("warm_edge_livery_sponsor_guard"),
        "route_vertical_livery_stripe_sponsor_guard": body.get("vertical_livery_stripe_sponsor_guard"),
        "route_solid_warm_livery_sponsor_guard": body.get("solid_warm_livery_sponsor_guard"),
        "route_bright_warm_body_color_sponsor_guard": body.get("bright_warm_body_color_sponsor_guard"),
        "route_warm_tan_body_panel_sponsor_guard": body.get("warm_tan_body_panel_sponsor_guard"),
        "route_diagonal_warm_livery_slash_sponsor_guard": body.get("diagonal_warm_livery_slash_sponsor_guard"),
        "route_decorative_livery_sponsor_guard": body.get("decorative_livery_sponsor_guard"),
        "route_large_red_livery_sponsor_guard": body.get("large_red_livery_sponsor_guard"),
        "route_smooth_red_body_panel_sponsor_guard": body.get("smooth_red_body_panel_sponsor_guard"),
        "route_small_flat_red_livery_sponsor_guard": body.get("small_flat_red_livery_sponsor_guard"),
        "route_red_orange_livery_block_sponsor_guard": body.get("red_orange_livery_block_sponsor_guard"),
        "route_warm_livery_arc_sponsor_guard": body.get("warm_livery_arc_sponsor_guard"),
        "route_geometric_livery_sponsor_guard": body.get("geometric_livery_sponsor_guard"),
        "route_pale_body_panel_sponsor_guard": body.get("pale_body_panel_sponsor_guard"),
        "route_ornamental_neutral_livery_sponsor_guard": body.get("ornamental_neutral_livery_sponsor_guard"),
        "route_dark_body_panel_sponsor_guard": body.get("dark_body_panel_sponsor_guard"),
        "route_white_livery_sponsor_guard": body.get("white_livery_sponsor_guard"),
        "route_tiny_dark_sponsor_speck_guard": body.get("tiny_dark_sponsor_speck_guard"),
        "route_number_logo_false_positive_guard": body.get("number_logo_false_positive_guard"),
        "route_number_family_template_inlay_guard": body.get("number_family_template_inlay_guard"),
        "route_multicolor_logo_false_positive_guard": body.get("multicolor_logo_false_positive_guard"),
        "route_green_white_logo_false_positive_guard": body.get("green_white_logo_false_positive_guard"),
        "route_large_green_logo_false_positive_guard": body.get("large_green_logo_false_positive_guard"),
        "route_white_livery_number_panel_guard": body.get("white_livery_number_panel_guard"),
        "route_small_sponsor_panel_false_positive_guard": body.get("small_sponsor_panel_false_positive_guard"),
        "route_thin_textline_number_false_positive_guard": body.get("thin_textline_number_false_positive_guard"),
        "route_red_single_digit_number_guard": body.get("red_single_digit_number_guard"),
        "route_red_two_digit_number_guard": body.get("red_two_digit_number_guard"),
        "route_number_trim_fragment_guard": body.get("number_trim_fragment_guard"),
        "route_number_badge_graphic_guard": body.get("number_badge_graphic_guard"),
        "route_round_badge_number_guard": body.get("round_badge_number_guard"),
        "route_repeated_round_badge_number_guard": body.get("repeated_round_badge_number_guard"),
        "route_yellow_panel_number_guard": body.get("yellow_panel_number_guard"),
        "route_pale_sponsor_panel_number_guard": body.get("pale_sponsor_panel_number_guard"),
        "route_hot_pink_paint_number_guard": body.get("hot_pink_paint_number_guard"),
        "route_black_blue_paint_number_guard": body.get("black_blue_paint_number_guard"),
        "route_white_purple_paint_number_guard": body.get("white_purple_paint_number_guard"),
        "route_red_white_dark_paint_number_guard": body.get("red_white_dark_paint_number_guard"),
        "route_badge_interior_guard": body.get("badge_interior_guard"),
        "route_badge_number_crumb_guard": body.get("badge_number_crumb_guard"),
        "route_badge_sponsor_crumb_guard": body.get("badge_sponsor_crumb_guard"),
        "route_large_stylized_number_shell_guard": body.get("large_stylized_number_shell_guard"),
        "route_companion_numbers": body.get("companion_numbers"),
        "route_companion_decals": body.get("companion_decals"),
        "route_car": body.get("car"),
        "mask_paths": mask_paths,
        "overlay": overlay_path,
        "component_count": len(components),
        "component_role_counts": dict(Counter(str(rec["role_guess"]) for rec in components)),
        "component_layer_counts": dict(Counter(str(rec["layer"]) for rec in components)),
    })
    ocr_overlay = _write_ocr_region_overlay(
        source,
        body.get("adjudicator_shadow") or {},
        sample_dir / "ocr_region_overlay.png",
    )
    if ocr_overlay:
        record["ocr_region_overlay"] = ocr_overlay
    _write_guard_visual_artifacts(source, record, sample_dir)
    components_path = sample_dir / "component_records.json"
    components_path.write_text(json.dumps(components, indent=2), encoding="utf-8")
    record["component_records"] = str(components_path.resolve())

    for layer in LAYER_ORDER:
        sheet = _contact_sheet(
            [rec for rec in components if rec["layer"] == layer],
            sample_dir / f"{layer}_components.png",
            f"{record['paint_label']} {layer} components",
        )
        if sheet:
            record[f"{layer}_components_sheet"] = sheet
    sheet = _contact_sheet(components, sample_dir / "all_layer_components.png", f"{record['paint_label']} all Auto-build components")
    if sheet:
        record["all_components_sheet"] = sheet
    suspects, suspect_sheet = _suspect_review_for_masks(source, masks, sample_dir)
    if suspects:
        suspect_path = sample_dir / "suspect_review_components.json"
        suspect_path.write_text(json.dumps(suspects, indent=2), encoding="utf-8")
        record["suspect_review_records"] = str(suspect_path.resolve())
        record["suspect_review_counts"] = dict(Counter(str(rec["review_reason"]) for rec in suspects))
    if suspect_sheet:
        record["suspect_review_sheet"] = suspect_sheet
    return record


def _guard_reasons(guard: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for component in guard.get("components") or []:
        reason = str(component.get("reason") or "").strip()
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def _build_scoreboard(records: list[dict[str, Any]], records_path: Path) -> dict[str, Any]:
    successful = [rec for rec in records if rec.get("success")]
    suspect_totals: Counter[str] = Counter()
    applied_guard_totals: Counter[str] = Counter()
    applied_guard_samples: dict[str, list[str]] = {}
    samples: list[dict[str, Any]] = []
    for rec in records:
        suspect_counts = dict(rec.get("suspect_review_counts") or {})
        suspect_totals.update({str(k): int(v) for k, v in suspect_counts.items()})
        sample_label = str(rec.get("paint_label") or rec.get("paint") or "").strip()
        applied_guards: dict[str, Any] = {}
        for key, value in sorted(rec.items()):
            if not key.startswith("route_") or not key.endswith("_guard"):
                continue
            if not isinstance(value, dict) or value.get("status") != "applied":
                continue
            guard_name = key[len("route_"):-len("_guard")]
            component_count = int(value.get("component_count") or len(value.get("components") or []) or 0)
            applied_guard_totals[guard_name] += component_count or 1
            if sample_label:
                labels = applied_guard_samples.setdefault(guard_name, [])
                if sample_label not in labels:
                    labels.append(sample_label)
            applied_guards[guard_name] = {
                "components": component_count,
                "added_px": int(value.get("added_px") or value.get("demoted_px") or 0),
                "reasons": _guard_reasons(value),
                "passes": list(value.get("passes") or []),
            }
        layer_counts = {
            layer: int((rec.get("component_layer_counts") or {}).get(layer, 0))
            for layer in ("numbers", "sponsors", "template", "brand_graphics", "paint")
        }
        samples.append({
            "paint": rec.get("paint"),
            "paint_label": rec.get("paint_label"),
            "success": bool(rec.get("success")),
            "engine": rec.get("route_engine"),
            "elapsed_sec": rec.get("elapsed_sec"),
            "fractions": rec.get("route_fractions") or {},
            "component_counts": layer_counts,
            "suspect_review_counts": suspect_counts,
            "applied_guards": applied_guards,
        })
    return {
        "schema": "smart_tga_route_scoreboard_v1",
        "records": str(records_path.resolve()),
        "samples": len(records),
        "success": len(successful),
        "failed": len(records) - len(successful),
        "engines": dict(Counter(str(rec.get("route_engine")) for rec in successful)),
        "component_layer_totals": {
            layer: int(sum(int((rec.get("component_layer_counts") or {}).get(layer, 0)) for rec in successful))
            for layer in ("numbers", "sponsors", "template", "brand_graphics", "paint")
        },
        "suspect_review_totals": dict(suspect_totals),
        "applied_guard_totals": dict(applied_guard_totals),
        "applied_guard_samples": applied_guard_samples,
        "sample_scoreboard": samples,
    }


def inspect(args: argparse.Namespace) -> dict[str, Any]:
    if not args.paint:
        raise ValueError("provide at least one --paint")
    args.output.mkdir(parents=True, exist_ok=True)
    client = _route_client(args)
    records_path = args.output / "inspection_records.json"
    records = []
    for paint in args.paint:
        records.append(inspect_paint(client, Path(paint).resolve(), args))
        # Checkpoint every completed real paint. Long GPU/OCR batches must not
        # lose earlier work when the caller's command timeout interrupts a
        # later sample.
        records_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    successful = [rec for rec in records if rec.get("success")]
    summary = {
        "samples": len(records),
        "success": len(successful),
        "failed": len(records) - len(successful),
        "disable_gpu": bool(args.disable_gpu),
        "no_gpu_cache": bool(args.no_gpu_cache),
        "worker_env": dict(getattr(args, "worker_env_map", {}) or {}),
        "brand_graphics_merge": args.brand_graphics_merge,
        "records": str(records_path.resolve()),
        "engines": dict(Counter(str(rec.get("route_engine")) for rec in successful)),
        "mean_elapsed_sec": round(float(np.mean([float(rec["elapsed_sec"]) for rec in successful])) if successful else 0.0, 3),
        "total_components": int(sum(int(rec.get("component_count", 0)) for rec in successful)),
        "layer_counts": dict(Counter(layer for rec in successful for layer, count in (rec.get("component_layer_counts") or {}).items() for _ in range(int(count)))),
    }
    scoreboard_path = args.output / "scoreboard.json"
    scoreboard = _build_scoreboard(records, records_path)
    scoreboard_path.write_text(json.dumps(scoreboard, indent=2), encoding="utf-8")
    summary["scoreboard"] = str(scoreboard_path.resolve())
    summary["suspect_review_totals"] = scoreboard["suspect_review_totals"]
    summary["applied_guard_totals"] = scoreboard["applied_guard_totals"]
    summary["applied_guard_samples"] = scoreboard["applied_guard_samples"]
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paint", action="append", default=[])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--preview-size", type=int, default=1024)
    parser.add_argument("--brand-graphics-merge", default="sponsors")
    parser.add_argument(
        "--car-hint-path",
        default="",
        help="Selected iRacing car folder/path to send as car_hint_path while inspecting loose paint files.",
    )
    parser.add_argument("--disable-gpu", action="store_true")
    parser.add_argument("--no-gpu-cache", action="store_true")
    parser.add_argument("--worker-env", action="append", default=[],
                        help="Set a worker/app env var for this offline route process, e.g. NUMBER_CLIP_REJECT_MAX_TOTAL=0.16")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(inspect(parse_args()), indent=2))


if __name__ == "__main__":
    main()
