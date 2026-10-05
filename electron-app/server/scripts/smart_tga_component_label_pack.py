"""Apply reviewed Smart TGA component labels to an inspection run.

This is offline Smart TGA tooling. It consumes component records from
``smart_tga_route_layer_inspector.py`` plus a small human-reviewed label map,
then writes corrected masks/overlay and a compact summary. The output is not a
runtime rule; it is an oracle fixture for one-car-at-a-time quality work.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
LAYER_ORDER = ("numbers", "sponsors", "template", "brand_graphics", "paint")
OVERLAY_ORDER = ("paint", "brand_graphics", "template", "sponsors", "numbers")
LAYER_COLORS = {
    "numbers": (255, 45, 45, 185),
    "sponsors": (55, 95, 255, 150),
    "template": (45, 220, 90, 150),
    "brand_graphics": (255, 170, 30, 150),
    "paint": (210, 210, 210, 35),
}


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_mask(mask: np.ndarray, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask.astype(np.uint8) * 255, "L").save(path)
    return str(path.resolve())


def _read_mask(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")) > 127


def _write_overlay(source: Image.Image, masks: dict[str, np.ndarray], path: Path) -> str:
    overlay = source.convert("RGBA")
    for layer in OVERLAY_ORDER:
        mask = masks.get(layer)
        if mask is None:
            continue
        tint = Image.new("RGBA", overlay.size, LAYER_COLORS[layer])
        alpha = Image.fromarray(mask.astype(np.uint8) * 255, "L")
        overlay.alpha_composite(Image.composite(tint, Image.new("RGBA", overlay.size, (0, 0, 0, 0)), alpha))
    path.parent.mkdir(parents=True, exist_ok=True)
    overlay.convert("RGB").save(path)
    return str(path.resolve())


def _find_record(records_path: Path, paint_label: str) -> dict[str, Any]:
    records = _read_json(records_path)
    for record in records:
        if record.get("paint_label") == paint_label:
            return record
    raise ValueError(f"paint_label {paint_label!r} not found in {records_path}")


def _component_masks(mask: np.ndarray, min_area: int) -> list[tuple[np.ndarray, list[int], int]]:
    n, labels, stats, _cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    out: list[tuple[np.ndarray, list[int], int]] = []
    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        out.append((labels == idx, [x, y, w, h], area))
    return out


def _expected_bbox_ok(actual: list[int], expected: list[int] | None) -> bool:
    if not expected:
        return True
    return all(abs(int(a) - int(e)) <= 1 for a, e in zip(actual, expected))


def _component_features(source_rgb: np.ndarray, comp_mask: np.ndarray, bbox: list[int], area: int) -> dict[str, Any]:
    x, y, w, h = [int(v) for v in bbox]
    crop = source_rgb[y:y + h, x:x + w]
    crop_mask = comp_mask[y:y + h, x:x + w]
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


def _clip_bbox(bbox: list[int], width: int, height: int) -> list[int]:
    x, y, w, h = [int(v) for v in bbox]
    x = max(0, min(width, x))
    y = max(0, min(height, y))
    w = max(0, min(width - x, w))
    h = max(0, min(height - y, h))
    return [x, y, w, h]


def _mask_bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return None
    x0 = int(xs.min())
    y0 = int(ys.min())
    return [x0, y0, int(xs.max() - x0 + 1), int(ys.max() - y0 + 1)]


def _extract_review_submask(
    source_rgb: np.ndarray,
    comp_mask: np.ndarray,
    review_bbox: list[int],
    options: dict[str, Any] | None,
) -> tuple[np.ndarray, list[int], int]:
    options = options or {}
    height, width = comp_mask.shape
    x, y, w, h = _clip_bbox(review_bbox, width, height)
    if w <= 0 or h <= 0:
        raise ValueError(f"review_bbox {review_bbox} is outside image bounds")

    out = np.zeros_like(comp_mask, dtype=bool)
    region_comp = comp_mask[y:y + h, x:x + w]
    if not region_comp.any():
        raise ValueError(f"review_bbox {review_bbox} does not intersect the source component")

    mode = options.get("mode", "component_region")
    if mode == "component_region":
        region_mask = region_comp.copy()
    elif mode == "hsv_union":
        crop = source_rgb[y:y + h, x:x + w]
        hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
        hue = hsv[:, :, 0].astype(np.float32)
        sat = hsv[:, :, 1].astype(np.float32) / 255.0
        val = hsv[:, :, 2].astype(np.float32) / 255.0
        region_mask = np.zeros((h, w), dtype=bool)
        for condition in options.get("conditions", []):
            keep = np.ones((h, w), dtype=bool)
            if "hue_min" in condition or "hue_max" in condition:
                hue_min = float(condition.get("hue_min", 0.0))
                hue_max = float(condition.get("hue_max", 179.0))
                if hue_min <= hue_max:
                    keep &= (hue >= hue_min) & (hue <= hue_max)
                else:
                    keep &= (hue >= hue_min) | (hue <= hue_max)
            if "saturation_min" in condition:
                keep &= sat >= float(condition["saturation_min"])
            if "saturation_max" in condition:
                keep &= sat <= float(condition["saturation_max"])
            if "value_min" in condition:
                keep &= val >= float(condition["value_min"])
            if "value_max" in condition:
                keep &= val <= float(condition["value_max"])
            region_mask |= keep
        region_mask &= region_comp
    else:
        crop = source_rgb[y:y + h, x:x + w]
        border = np.zeros((h, w), dtype=bool)
        border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
        border_samples = crop[region_comp & border]
        samples = border_samples if len(border_samples) >= 16 else crop[region_comp]
        bg = np.median(samples.reshape(-1, 3), axis=0)
        color_dist = np.linalg.norm(crop.astype(np.float32) - bg.astype(np.float32), axis=2)

        threshold = float(options.get("color_distance", 30.0))
        edge_threshold = float(options.get("edge_color_distance", max(18.0, threshold * 0.55)))
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, int(options.get("canny_low", 48)), int(options.get("canny_high", 144)))
        edge_kernel = max(0, int(options.get("edge_dilate", 1)))
        if edge_kernel:
            kernel = np.ones((edge_kernel * 2 + 1, edge_kernel * 2 + 1), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
        region_mask = region_comp & ((color_dist >= threshold) | ((edges > 0) & (color_dist >= edge_threshold)))

        close_kernel = max(0, int(options.get("close", 1)))
        if close_kernel:
            kernel = np.ones((close_kernel * 2 + 1, close_kernel * 2 + 1), np.uint8)
            region_mask = cv2.morphologyEx(region_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel).astype(bool)
            region_mask &= region_comp

        min_area = int(options.get("min_area", 8))
        if min_area > 1:
            n, labels, stats, _cent = cv2.connectedComponentsWithStats(region_mask.astype(np.uint8), 8)
            keep = np.zeros_like(region_mask, dtype=bool)
            for idx in range(1, n):
                if int(stats[idx, cv2.CC_STAT_AREA]) >= min_area:
                    keep |= labels == idx
            region_mask = keep

    if mode == "hsv_union":
        close_kernel = max(0, int(options.get("close", 0)))
        if close_kernel:
            kernel = np.ones((close_kernel * 2 + 1, close_kernel * 2 + 1), np.uint8)
            region_mask = cv2.morphologyEx(region_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel).astype(bool)
            region_mask &= region_comp

        min_area = int(options.get("min_area", 1))
        if min_area > 1:
            n, labels, stats, _cent = cv2.connectedComponentsWithStats(region_mask.astype(np.uint8), 8)
            keep = np.zeros_like(region_mask, dtype=bool)
            for idx in range(1, n):
                if int(stats[idx, cv2.CC_STAT_AREA]) >= min_area:
                    keep |= labels == idx
            region_mask = keep

    out[y:y + h, x:x + w] = region_mask
    bbox = _mask_bbox(out)
    if bbox is None:
        raise ValueError(f"review_bbox {review_bbox} produced an empty reviewed submask")
    area = int(out.sum())
    return out, bbox, area


def apply_labels(args: argparse.Namespace) -> dict[str, Any]:
    labels_path = _repo_path(args.labels)
    labels_doc = _read_json(labels_path)
    records_path = _repo_path(labels_doc["inspection_records"])
    record = _find_record(records_path, labels_doc["paint_label"])

    masks = {layer: _read_mask(Path(record["mask_paths"][layer])) for layer in record["mask_paths"]}
    for layer in LAYER_ORDER:
        masks.setdefault(layer, np.zeros_like(next(iter(masks.values()))))

    source = Image.open(record["source_1024"]).convert("RGB")
    source_rgb = np.asarray(source)
    h, w = next(iter(masks.values())).shape
    total = float(w * h)
    components_by_layer: dict[str, list[tuple[np.ndarray, list[int], int]]] = {}
    for layer, mask in masks.items():
        min_area = 20 if layer != "paint" else max(64, int(0.0001 * w * h))
        components_by_layer[layer] = _component_masks(mask, min_area)

    applied: list[dict[str, Any]] = []
    for label in labels_doc.get("component_labels", []):
        src = str(label["layer"])
        idx = int(label["component_index"])
        target = str(label.get("target_layer", src))
        if src not in components_by_layer:
            raise ValueError(f"unknown source layer {src!r}")
        if target not in LAYER_ORDER:
            raise ValueError(f"unknown target layer {target!r}")
        comps = components_by_layer[src]
        if idx < 0 or idx >= len(comps):
            raise ValueError(f"component {src}:{idx} missing; only {len(comps)} components")
        comp_mask, bbox, area = comps[idx]
        expected_bbox = label.get("expected_bbox")
        if not _expected_bbox_ok(bbox, expected_bbox):
            raise ValueError(f"component {src}:{idx} bbox drifted: got {bbox}, expected {expected_bbox}")
        move_mask = comp_mask
        move_bbox = bbox
        move_area = area
        if label.get("review_bbox"):
            move_mask, move_bbox, move_area = _extract_review_submask(
                source_rgb,
                comp_mask,
                label["review_bbox"],
                label.get("foreground"),
            )
        if target != src:
            masks[src][move_mask] = False
            if target != "paint":
                masks[target][move_mask] = True
        applied.append({
            "layer": src,
            "component_index": idx,
            "target_layer": target,
            "operation": "review_submask" if label.get("review_bbox") else "component",
            "label": label.get("label"),
            "note": label.get("note"),
            "component_bbox": bbox,
            "bbox": move_bbox,
            "area_px": move_area,
            "area_frac": round(move_area / total, 7),
            "review_bbox": label.get("review_bbox"),
            "features": _component_features(source_rgb, move_mask, move_bbox, move_area),
            "moved": target != src,
        })

    occupied = np.zeros_like(next(iter(masks.values())), dtype=bool)
    for layer in ("numbers", "sponsors", "template", "brand_graphics"):
        occupied |= masks[layer]
    masks["paint"] = ~occupied

    out_dir = _repo_path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    mask_paths = {layer: _write_mask(masks[layer], out_dir / "masks" / f"{layer}.png") for layer in LAYER_ORDER}
    overlay_path = _write_overlay(source, masks, out_dir / "corrected_overlay.png")

    fractions = {layer: round(float(masks[layer].mean()), 5) for layer in LAYER_ORDER}
    original_fractions = record.get("route_fractions") or {}
    summary = {
        "label_pack": str(labels_path.resolve()),
        "inspection_records": str(records_path.resolve()),
        "paint_label": labels_doc["paint_label"],
        "source_1024": record["source_1024"],
        "corrected_overlay": overlay_path,
        "mask_paths": mask_paths,
        "original_fractions": original_fractions,
        "corrected_fractions": fractions,
        "fraction_delta": {
            layer: round(fractions.get(layer, 0.0) - float(original_fractions.get(layer, 0.0) or 0.0), 5)
            for layer in LAYER_ORDER
        },
        "applied_labels": applied,
        "label_counts": dict(Counter(str(item.get("label")) for item in applied)),
        "move_counts": dict(Counter(f"{item['layer']}->{item['target_layer']}" for item in applied if item["moved"])),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    feature_rows = [
        {
            "paint_label": labels_doc["paint_label"],
            "layer": item["layer"],
            "component_index": item["component_index"],
            "target_layer": item["target_layer"],
            "label": item["label"],
            "bbox": item["bbox"],
            "area_px": item["area_px"],
            **item["features"],
        }
        for item in applied
    ]
    (out_dir / "component_features.json").write_text(json.dumps(feature_rows, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, help="Reviewed component label map JSON")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(apply_labels(parse_args()), indent=2))


if __name__ == "__main__":
    main()
