"""Evaluate a lightweight learned race-number crop detector.

This is offline Smart TGA tooling. It trains an OpenCV SVM from a corpus
manifest produced by `scripts/smart_tga_number_corpus.py` and reports paired
source-holdout results. It does not wire anything into Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw


DEFAULT_CORPUS = Path("_smart_tga_runs/cycle60_number_corpus_v2/manifest.json")
FEATURE_VERSIONS = {
    "base": "edge_hsv_center_v1",
    "hog": "edge_hsv_hog_projection_v2",
    "geom": "edge_hsv_hog_projection_component_geometry_v3",
    "rich": "edge_hsv_hog_projection_geometry_pressure_shape_v4",
    "context": "edge_hsv_hog_projection_geometry_pressure_shape_context_v5",
}
HOG = cv2.HOGDescriptor(
    _winSize=(96, 96),
    _blockSize=(24, 24),
    _blockStride=(12, 12),
    _cellSize=(12, 12),
    _nbins=9,
)


def _component_features(mask: np.ndarray) -> np.ndarray:
    mask = (mask > 0).astype(np.uint8)
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask, 8)
    h, w = mask.shape[:2]
    total = float(max(1, h * w))
    comps: list[dict[str, float]] = []
    for idx in range(1, n):
        area = float(stats[idx, cv2.CC_STAT_AREA])
        if area < 8:
            continue
        x = float(stats[idx, cv2.CC_STAT_LEFT])
        y = float(stats[idx, cv2.CC_STAT_TOP])
        cw = float(stats[idx, cv2.CC_STAT_WIDTH])
        ch = float(stats[idx, cv2.CC_STAT_HEIGHT])
        comps.append({
            "area": area,
            "width": cw,
            "height": ch,
            "aspect": cw / max(1.0, ch),
            "fill": area / max(1.0, cw * ch),
            "center_x": (x + cw * 0.5) / max(1.0, w),
            "center_y": (y + ch * 0.5) / max(1.0, h),
            "touch_border": 1.0 if x <= 1 or y <= 1 or x + cw >= w - 2 or y + ch >= h - 2 else 0.0,
        })
    comps.sort(key=lambda c: c["area"], reverse=True)
    top = comps[:5]
    values: list[float] = [
        len(comps) / 32.0,
        float(mask.mean()),
        float(mask[24:72, 24:72].mean()) if mask.shape[0] >= 96 else float(mask.mean()),
        float(mask[:, :12].mean() + mask[:, -12:].mean() + mask[:12, :].mean() + mask[-12:, :].mean()) / 4.0,
    ]
    for slot in range(5):
        if slot < len(top):
            comp = top[slot]
            values.extend([
                comp["area"] / total,
                comp["width"] / max(1.0, w),
                comp["height"] / max(1.0, h),
                min(comp["aspect"], 8.0) / 8.0,
                comp["fill"],
                comp["center_x"],
                comp["center_y"],
                comp["touch_border"],
            ])
        else:
            values.extend([0.0] * 8)
    if mask.any():
        left = mask[:, : w // 2]
        right = np.fliplr(mask[:, w - left.shape[1]:])
        top_half = mask[: h // 2, :]
        bottom_half = np.flipud(mask[h - top_half.shape[0]:, :])
        values.extend([
            1.0 - float(np.mean(np.abs(left.astype(np.float32) - right.astype(np.float32)))),
            1.0 - float(np.mean(np.abs(top_half.astype(np.float32) - bottom_half.astype(np.float32)))),
        ])
    else:
        values.extend([0.0, 0.0])
    return np.asarray(values, dtype=np.float32)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _edge_component_stats(gray: np.ndarray) -> dict[str, float]:
    edges = cv2.Canny(gray, 35, 125)
    joined = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats((joined > 0).astype(np.uint8), 8)
    small = 0
    medium = 0
    large = 0
    for idx in range(1, count):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < 8:
            continue
        if area < 70:
            small += 1
        elif area < 420:
            medium += 1
        else:
            large += 1
    return {
        "edge_density": float((edges > 0).mean()),
        "small_edge_components": float(small),
        "medium_edge_components": float(medium),
        "large_edge_components": float(large),
    }


def _border_edge_score(edges: np.ndarray) -> float:
    h, w = edges.shape[:2]
    band = max(2, int(min(h, w) * 0.10))
    top = float((edges[:band, :] > 0).mean())
    bottom = float((edges[h - band:, :] > 0).mean())
    left = float((edges[:, :band] > 0).mean())
    right = float((edges[:, w - band:] > 0).mean())
    center = float((edges[band:h - band, band:w - band] > 0).mean()) if h > band * 2 and w > band * 2 else 0.0
    return _clamp01(((top + bottom + left + right) * 0.25) * 2.2 - center * 0.55)


def _digit_mask_quality(mask: np.ndarray, valid: np.ndarray) -> dict[str, float]:
    mask = (mask > 0) & valid
    total = int(mask.sum())
    valid_count = max(1, int(valid.sum()))
    if total <= 8:
        return {"score": 0.0}
    labels_count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    components: list[tuple[int, int, int, int, int]] = []
    small_count = 0
    for comp in range(1, labels_count):
        x, y, w, h, area = [int(v) for v in stats[comp]]
        if area < 5:
            continue
        touches_border = x <= 1 or y <= 1 or x + w >= mask.shape[1] - 1 or y + h >= mask.shape[0] - 1
        if touches_border and area > valid_count * 0.28:
            continue
        if area < 80:
            small_count += 1
        components.append((x, y, w, h, area))
    if not components:
        return {"score": 0.0}
    components.sort(key=lambda item: item[4], reverse=True)
    large_components = [item for item in components if item[4] >= max(80, valid_count * 0.012)]
    if not large_components:
        return {"score": 0.0}

    top_area = sum(item[4] for item in components[:3])
    total_area = sum(item[4] for item in components)
    x0 = min(item[0] for item in large_components)
    y0 = min(item[1] for item in large_components)
    x1 = max(item[0] + item[2] for item in large_components)
    y1 = max(item[1] + item[3] for item in large_components)
    span_x = (x1 - x0) / float(mask.shape[1])
    span_y = (y1 - y0) / float(mask.shape[0])
    fill = total_area / float(valid_count)
    top_share = top_area / max(1.0, float(total_area))
    large_count = len(large_components)

    fill_score = max(0.0, 1.0 - abs(fill - 0.26) / 0.30)
    span_score = _clamp01((max(span_x, span_y) - 0.28) / 0.40)
    top_share_score = _clamp01((top_share - 0.42) / 0.42)
    large_count_score = _clamp01(1.0 - abs(large_count - 3.0) / 7.0)
    clutter_penalty = _clamp01((small_count - 14) / 34.0)
    extreme_penalty = 0.0
    if fill < 0.035 or fill > 0.72:
        extreme_penalty += 0.22
    if span_x < 0.14 and span_y < 0.14:
        extreme_penalty += 0.22

    score = (
        0.30 * fill_score
        + 0.26 * span_score
        + 0.24 * top_share_score
        + 0.20 * large_count_score
    )
    score *= max(0.0, 1.0 - 0.65 * clutter_penalty - extreme_penalty)
    return {
        "score": _clamp01(score),
        "fill": fill,
        "span_x": span_x,
        "span_y": span_y,
        "top_share": top_share,
        "large_count": float(large_count),
        "small_count": float(small_count),
    }


def _number_stroke_features(arr: np.ndarray) -> np.ndarray:
    arr96 = cv2.resize(arr, (96, 96), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(arr96, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(arr96, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    valid = arr96.max(axis=2) > 5
    if int(valid.sum()) < 64:
        valid = np.ones(gray.shape, dtype=bool)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _thr, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = otsu == 0
    bright = otsu > 0
    edges = cv2.Canny(gray, 35, 130) > 0
    edge_stroke = cv2.dilate(edges.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1) > 0
    sat_stroke = (sat > 80) & edge_stroke
    best = max(
        (
            _digit_mask_quality(dark, valid),
            _digit_mask_quality(bright, valid),
            _digit_mask_quality(edge_stroke, valid),
            _digit_mask_quality(sat_stroke | edge_stroke, valid),
        ),
        key=lambda row: row.get("score", 0.0),
    )
    return np.asarray([
        best.get("score", 0.0),
        best.get("fill", 0.0),
        best.get("span_x", 0.0),
        best.get("span_y", 0.0),
        best.get("top_share", 0.0),
        min(best.get("large_count", 0.0), 10.0) / 10.0,
        min(best.get("small_count", 0.0), 40.0) / 40.0,
    ], dtype=np.float32)


def _shape_pressure_features(arr: np.ndarray) -> np.ndarray:
    arr160 = cv2.resize(arr, (160, 160), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(arr160, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(arr160, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    edges = cv2.Canny(gray, 35, 125)
    comp = _edge_component_stats(gray)
    color_std = arr160.reshape(-1, 3).std(axis=0)
    luma_std = float(gray.std())
    sat_density = float((sat > 70).mean())
    dark_frac = float((gray < 45).mean())
    bright_frac = float((gray > 210).mean())
    low_sat_frac = float((sat < 45).mean())
    border_score = _border_edge_score(edges)
    small_components = comp["small_edge_components"]
    medium_components = comp["medium_edge_components"]
    textline_score = min(1.0, comp["edge_density"] * 2.25 + min(1.0, (small_components + medium_components * 0.55) / 46.0) * 0.62)
    panel_score = min(1.0, border_score * 0.66 + min(1.0, (low_sat_frac + bright_frac) * 0.35) + min(1.0, comp["edge_density"] * 1.15) * 0.20)
    template_score = min(1.0, low_sat_frac * 0.34 + dark_frac * 0.28 + border_score * 0.42)
    graphic_score = min(1.0, sat_density * 0.50 + min(1.0, float(color_std.mean()) / 80.0) * 0.38 + min(1.0, luma_std / 90.0) * 0.18)

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _thr, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, hierarchy = cv2.findContours(otsu, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    circularities: list[float] = []
    fills: list[float] = []
    areas: list[float] = []
    circle_like = 0
    hole_count = 0
    if hierarchy is not None:
        hole_count = int(sum(1 for row in hierarchy[0] if int(row[3]) >= 0))
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < 20:
            continue
        perimeter = float(cv2.arcLength(contour, True))
        if perimeter <= 0:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        circularity = _clamp01((4.0 * np.pi * area) / (perimeter * perimeter))
        aspect = float(w) / float(max(1, h))
        fill = area / float(max(1, w * h))
        circularities.append(circularity)
        fills.append(fill)
        areas.append(area / float(arr160.shape[0] * arr160.shape[1]))
        if circularity >= 0.58 and 0.55 <= aspect <= 1.85 and area >= 140:
            circle_like += 1

    row_density = (edges > 0).mean(axis=1)
    col_density = (edges > 0).mean(axis=0)
    stripe_score = _clamp01(float((row_density > 0.28).mean() + (col_density > 0.28).mean()) * 1.8)
    hue_hist = cv2.calcHist([hsv], [0], None, [18], [0, 180]).astype(np.float32).ravel()
    hue_hist /= max(1.0, float(hue_hist.sum()))
    dominant_hue = float(hue_hist.max())

    return np.asarray([
        comp["edge_density"],
        min(small_components, 60.0) / 60.0,
        min(medium_components, 40.0) / 40.0,
        min(comp["large_edge_components"], 20.0) / 20.0,
        sat_density,
        dark_frac,
        bright_frac,
        low_sat_frac,
        min(luma_std / 128.0, 1.0),
        min(float(color_std.mean()) / 128.0, 1.0),
        border_score,
        textline_score,
        panel_score,
        template_score,
        graphic_score,
        max(circularities) if circularities else 0.0,
        float(np.mean(circularities)) if circularities else 0.0,
        max(fills) if fills else 0.0,
        max(areas) if areas else 0.0,
        min(circle_like, 8) / 8.0,
        min(hole_count, 8) / 8.0,
        stripe_score,
        dominant_hue,
    ], dtype=np.float32)


def _context_ring_features(arr: np.ndarray) -> np.ndarray:
    arr96 = cv2.resize(arr, (96, 96), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(arr96, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(arr96, cv2.COLOR_RGB2HSV)
    edges = cv2.Canny(gray, 35, 125) > 0
    center_mask = np.zeros(gray.shape, dtype=bool)
    center_mask[24:72, 24:72] = True
    ring_mask = ~center_mask

    def _region_stats(mask: np.ndarray) -> list[float]:
        rgb_region = arr96[mask]
        hsv_region = hsv[mask]
        gray_region = gray[mask]
        edge_region = edges[mask]
        if rgb_region.size == 0:
            return [0.0] * 10
        hue_hist = cv2.calcHist([hsv_region[:, 0].reshape(-1, 1)], [0], None, [12], [0, 180]).astype(np.float32).ravel()
        hue_hist /= max(1.0, float(hue_hist.sum()))
        entropy = float(-(hue_hist[hue_hist > 0] * np.log2(hue_hist[hue_hist > 0])).sum() / np.log2(12.0))
        return [
            float(gray_region.mean()) / 255.0,
            float(gray_region.std()) / 128.0,
            float(hsv_region[:, 1].mean()) / 255.0,
            float(hsv_region[:, 1].std()) / 128.0,
            float(hsv_region[:, 2].mean()) / 255.0,
            float(hsv_region[:, 2].std()) / 128.0,
            float(edge_region.mean()),
            float(rgb_region.std(axis=0).mean()) / 128.0,
            float(hue_hist.max()),
            entropy,
        ]

    center_stats = np.asarray(_region_stats(center_mask), dtype=np.float32)
    ring_stats = np.asarray(_region_stats(ring_mask), dtype=np.float32)
    diff_stats = np.abs(center_stats - ring_stats)

    boundary = np.zeros(gray.shape, dtype=bool)
    boundary[23:25, 24:72] = True
    boundary[71:73, 24:72] = True
    boundary[24:72, 23:25] = True
    boundary[24:72, 71:73] = True
    boundary_edge = float(edges[boundary].mean()) if boundary.any() else 0.0
    outer_edge = float(edges[:12, :].mean() + edges[-12:, :].mean() + edges[:, :12].mean() + edges[:, -12:].mean()) / 4.0
    center_blueish = float(((hsv[:, :, 0] > 85) & (hsv[:, :, 0] < 125) & center_mask & (hsv[:, :, 1] > 70)).mean()) * 4.0
    ring_blueish = float(((hsv[:, :, 0] > 85) & (hsv[:, :, 0] < 125) & ring_mask & (hsv[:, :, 1] > 70)).mean()) * (96 * 96 / max(1, int(ring_mask.sum())))
    center_redish = float((((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 168)) & center_mask & (hsv[:, :, 1] > 70)).mean()) * 4.0
    ring_redish = float((((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 168)) & ring_mask & (hsv[:, :, 1] > 70)).mean()) * (96 * 96 / max(1, int(ring_mask.sum())))

    return np.concatenate([
        center_stats,
        ring_stats,
        diff_stats,
        np.asarray([
            boundary_edge,
            outer_edge,
            _clamp01(center_blueish),
            _clamp01(ring_blueish),
            _clamp01(center_redish),
            _clamp01(ring_redish),
        ], dtype=np.float32),
    ]).astype(np.float32)


def _source_group(record: dict[str, Any]) -> str:
    if record["label"] == "number":
        return str(record.get("folder") or Path(record.get("car_num", record["file"])).parent.name)
    return str(record.get("probe_label") or Path(record.get("paint", record["file"])).stem)


def _paint_group(record: dict[str, Any]) -> str:
    source = record.get("paint") or record.get("car_num") or record.get("car") or record.get("file")
    path = Path(str(source))
    parent = path.parent.name if path.parent.name else "unknown"
    return f"{parent}/{path.stem}"


def _features(path: str | Path, feature_set: str) -> np.ndarray:
    img = np.asarray(Image.open(path).convert("RGB").resize((96, 96), Image.Resampling.LANCZOS))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 130)
    small_edges = cv2.resize(edges, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32).reshape(-1) / 255.0
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    hhist = cv2.calcHist([hsv], [0], None, [12], [0, 180]).astype(np.float32).ravel()
    shist = cv2.calcHist([hsv], [1], None, [8], [0, 256]).astype(np.float32).ravel()
    vhist = cv2.calcHist([hsv], [2], None, [8], [0, 256]).astype(np.float32).ravel()
    hhist /= max(1.0, float(hhist.sum()))
    shist /= max(1.0, float(shist.sum()))
    vhist /= max(1.0, float(vhist.sum()))
    center = np.array([edges[24:72, 24:72].mean() / 255.0], np.float32)
    border = np.array([edges.mean() / 255.0 - center[0]], np.float32)
    base = np.concatenate([small_edges, hhist, shist, vhist, center, border]).astype(np.float32)
    if feature_set == "base":
        return base
    if feature_set not in {"hog", "geom", "rich", "context"}:
        raise ValueError(f"unsupported feature set: {feature_set}")
    hog = HOG.compute(gray).astype(np.float32).ravel()
    hog /= max(1.0, float(np.linalg.norm(hog)))
    binary = (edges > 0).astype(np.float32)
    row_projection = cv2.resize(binary.mean(axis=1).reshape(96, 1), (1, 16), interpolation=cv2.INTER_AREA).ravel()
    col_projection = cv2.resize(binary.mean(axis=0).reshape(1, 96), (16, 1), interpolation=cv2.INTER_AREA).ravel()
    quadrant_density = np.array([
        binary[:48, :48].mean(),
        binary[:48, 48:].mean(),
        binary[48:, :48].mean(),
        binary[48:, 48:].mean(),
    ], np.float32)
    hog_features = np.concatenate([
        base,
        hog,
        row_projection.astype(np.float32),
        col_projection.astype(np.float32),
        quadrant_density,
    ]).astype(np.float32)
    if feature_set == "hog":
        return hog_features

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _otsu_value, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edge_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    sat_mask = (hsv[:, :, 1] > 92).astype(np.uint8) * 255
    dark_mask = (gray < 92).astype(np.uint8) * 255
    light_mask = (gray > 168).astype(np.uint8) * 255
    geom = np.concatenate([
        _component_features(edge_closed),
        _component_features(otsu),
        _component_features(255 - otsu),
        _component_features(sat_mask),
        _component_features(dark_mask),
        _component_features(light_mask),
    ]).astype(np.float32)
    geom_features = np.concatenate([hog_features, geom]).astype(np.float32)
    if feature_set == "geom":
        return geom_features
    rich_features = np.concatenate([geom_features, _shape_pressure_features(img), _number_stroke_features(img)]).astype(np.float32)
    if feature_set == "rich":
        return rich_features
    return np.concatenate([rich_features, _context_ring_features(img)]).astype(np.float32)


def _train_svm(x: np.ndarray, y: np.ndarray, kernel: str, c_value: float, gamma: float) -> cv2.ml_SVM:
    svm = cv2.ml.SVM_create()
    svm.setType(cv2.ml.SVM_C_SVC)
    svm.setC(float(c_value))
    if kernel == "linear":
        svm.setKernel(cv2.ml.SVM_LINEAR)
    elif kernel == "rbf":
        svm.setKernel(cv2.ml.SVM_RBF)
        svm.setGamma(float(gamma))
    else:
        raise ValueError(f"unsupported SVM kernel: {kernel}")
    svm.train(x.astype(np.float32), cv2.ml.ROW_SAMPLE, y.astype(np.int32))
    return svm


def _predict(svm: cv2.ml_SVM, x: np.ndarray) -> np.ndarray:
    _ok, pred = svm.predict(x.astype(np.float32))
    return pred.ravel().astype(np.int32)


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 6
    cell = 190
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        img = Image.open(rec["file"]).convert("RGB").resize((156, 156), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 17, y + 24))
        draw.text((x + 6, y + 5), f"truth {rec['truth']} pred {rec['pred']}", fill=(255, 220, 120))
        draw.text((x + 6, y + 176), str(rec.get("source", ""))[:27], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def evaluate(
    manifest: Path,
    output: Path,
    feature_set: str = "base",
    svm_kernel: str = "linear",
    svm_c: float = 0.7,
    svm_gamma: float = 0.01,
    holdout_mode: str = "source",
) -> dict[str, Any]:
    if feature_set not in FEATURE_VERSIONS:
        raise ValueError(f"unsupported feature set: {feature_set}")
    manifest_path = manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rec in manifest:
        if holdout_mode == "source":
            rec["source_group"] = _source_group(rec)
        elif holdout_mode == "paint":
            rec["source_group"] = _paint_group(rec)
        else:
            raise ValueError(f"unsupported holdout mode: {holdout_mode}")
    x = np.stack([_features(rec["file"], feature_set) for rec in manifest]).astype(np.float32)
    y = np.array([1 if rec["label"] == "number" else 0 for rec in manifest], np.int32)
    pos_groups = sorted({rec["source_group"] for rec in manifest if rec["label"] == "number"})
    neg_groups = sorted({rec["source_group"] for rec in manifest if rec["label"] != "number"})

    folds: list[dict[str, Any]] = []
    mistakes: list[dict[str, Any]] = []
    for pos_group in pos_groups:
        for neg_group in neg_groups:
            test_idx = [
                idx for idx, rec in enumerate(manifest)
                if rec["source_group"] in {pos_group, neg_group}
            ]
            train_idx = [idx for idx in range(len(manifest)) if idx not in test_idx]
            if len({int(v) for v in y[train_idx]}) < 2 or len({int(v) for v in y[test_idx]}) < 2:
                continue
            svm = _train_svm(x[train_idx], y[train_idx], svm_kernel, svm_c, svm_gamma)
            pred = _predict(svm, x[test_idx])
            truth = y[test_idx]
            fold_mistakes: list[dict[str, Any]] = []
            for idx, p, t in zip(test_idx, pred, truth):
                if int(p) == int(t):
                    continue
                rec = manifest[idx]
                mistake = {
                    "file": rec["file"],
                    "truth": int(t),
                    "pred": int(p),
                    "label": rec["label"],
                    "source": rec["source_group"],
                    "fold": f"{pos_group}__{neg_group}",
                }
                fold_mistakes.append(mistake)
                mistakes.append(mistake)
            folds.append({
                "holdout_positive": pos_group,
                "holdout_negative": neg_group,
                "train": len(train_idx),
                "test": len(test_idx),
                "accuracy": round(float((pred == truth).mean()), 4),
                "false_positive": int(((pred == 1) & (truth == 0)).sum()),
                "false_negative": int(((pred == 0) & (truth == 1)).sum()),
                "mistakes": fold_mistakes,
            })

    accuracies = [f["accuracy"] for f in folds]
    summary = {
        "manifest": str(manifest_path),
        "feature_set": feature_set,
        "feature_version": FEATURE_VERSIONS[feature_set],
        "svm_kernel": svm_kernel,
        "svm_c": svm_c,
        "svm_gamma": svm_gamma if svm_kernel == "rbf" else None,
        "holdout_mode": holdout_mode,
        "samples": len(manifest),
        "positive_samples": int((y == 1).sum()),
        "hard_negative_samples": int((y == 0).sum()),
        "positive_groups": pos_groups,
        "negative_groups": neg_groups,
        "folds": len(folds),
        "mean_accuracy": round(float(np.mean(accuracies)), 4) if accuracies else 0.0,
        "min_accuracy": round(float(np.min(accuracies)), 4) if accuracies else 0.0,
        "total_false_positive": sum(f["false_positive"] for f in folds),
        "total_false_negative": sum(f["false_negative"] for f in folds),
        "unique_false_positive_files": len({m["file"] for m in mistakes if m["truth"] == 0 and m["pred"] == 1}),
        "unique_false_negative_files": len({m["file"] for m in mistakes if m["truth"] == 1 and m["pred"] == 0}),
        "unique_false_positive_names": sorted({
            Path(m["file"]).name for m in mistakes if m["truth"] == 0 and m["pred"] == 1
        }),
        "unique_false_negative_names": sorted({
            Path(m["file"]).name for m in mistakes if m["truth"] == 1 and m["pred"] == 0
        }),
        "fold_results": folds,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "holdout_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _contact_sheet(
        mistakes[:36],
        output / "mistakes_contact_sheet.png",
        f"Smart TGA mistakes {feature_set}/{svm_kernel}/C={svm_c:g}",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=Path("_smart_tga_runs/smart_tga_number_detector_eval"))
    parser.add_argument("--feature-set", choices=sorted(FEATURE_VERSIONS), default="base")
    parser.add_argument("--svm-kernel", choices=["linear", "rbf"], default="linear")
    parser.add_argument("--svm-c", type=float, default=0.7)
    parser.add_argument("--svm-gamma", type=float, default=0.01)
    parser.add_argument("--holdout-mode", choices=["source", "paint"], default="source")
    return parser.parse_args()


def main() -> None:
    summary = evaluate(**vars(parse_args()))
    brief = {k: v for k, v in summary.items() if k != "fold_results"}
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
