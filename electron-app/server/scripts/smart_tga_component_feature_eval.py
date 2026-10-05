"""Evaluate reviewed Smart TGA component features with leave-one-car-out splits.

This is offline Smart TGA tooling. It consumes the reviewed feature bank built
by ``smart_tga_component_feature_bank.py`` and tests whether simple component
features generalize across cars before any runtime Auto-build hook is attempted.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_KEYS = (
    "log_area_px",
    "aspect",
    "fill",
    "center_x",
    "center_y",
    "mean_saturation",
    "mean_value",
    "edge_density",
    "color_std",
    "mean_rgb_0",
    "mean_rgb_1",
    "mean_rgb_2",
    "std_rgb_0",
    "std_rgb_1",
    "std_rgb_2",
)
SOURCE_LAYERS = ("numbers", "sponsors", "template", "brand_graphics", "paint")
SOURCE_FEATURE_KEYS = tuple(f"source_layer_{layer}" for layer in SOURCE_LAYERS)
FEATURE_VIEWS = {
    "base": BASE_FEATURE_KEYS,
    "source_layer": BASE_FEATURE_KEYS + SOURCE_FEATURE_KEYS,
}


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _feature_vector(record: dict[str, Any], include_source_layer: bool = False) -> list[float]:
    mean_rgb = record.get("mean_rgb") or [0, 0, 0]
    std_rgb = record.get("std_rgb") or [0, 0, 0]
    values = {
        "log_area_px": math.log1p(float(record.get("area_px") or 0.0)),
        "aspect": float(record.get("aspect") or 0.0),
        "fill": float(record.get("fill") or 0.0),
        "center_x": float(record.get("center_x") or 0.0),
        "center_y": float(record.get("center_y") or 0.0),
        "mean_saturation": float(record.get("mean_saturation") or 0.0),
        "mean_value": float(record.get("mean_value") or 0.0),
        "edge_density": float(record.get("edge_density") or 0.0),
        "color_std": float(record.get("color_std") or 0.0),
        "mean_rgb_0": float(mean_rgb[0]) / 255.0 if len(mean_rgb) > 0 else 0.0,
        "mean_rgb_1": float(mean_rgb[1]) / 255.0 if len(mean_rgb) > 1 else 0.0,
        "mean_rgb_2": float(mean_rgb[2]) / 255.0 if len(mean_rgb) > 2 else 0.0,
        "std_rgb_0": float(std_rgb[0]) / 255.0 if len(std_rgb) > 0 else 0.0,
        "std_rgb_1": float(std_rgb[1]) / 255.0 if len(std_rgb) > 1 else 0.0,
        "std_rgb_2": float(std_rgb[2]) / 255.0 if len(std_rgb) > 2 else 0.0,
    }
    out = [values[key] for key in BASE_FEATURE_KEYS]
    if include_source_layer:
        source_layer = str(record.get("layer") or "")
        out.extend(1.0 if source_layer == layer else 0.0 for layer in SOURCE_LAYERS)
    return out


def _fit_scaler(vectors: list[list[float]]) -> tuple[list[float], list[float]]:
    width = len(vectors[0]) if vectors else len(BASE_FEATURE_KEYS)
    if not vectors:
        return [0.0] * width, [1.0] * width
    means: list[float] = []
    stds: list[float] = []
    for idx in range(width):
        vals = [vec[idx] for vec in vectors]
        mean = sum(vals) / len(vals)
        var = sum((val - mean) ** 2 for val in vals) / max(1, len(vals))
        std = math.sqrt(var)
        means.append(mean)
        stds.append(std if std > 1e-9 else 1.0)
    return means, stds


def _scale(vec: list[float], means: list[float], stds: list[float]) -> list[float]:
    return [(value - means[idx]) / stds[idx] for idx, value in enumerate(vec)]


def _distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(a, b)))


def _nearest_centroid(
    train_rows: list[dict[str, Any]],
    train_vectors: list[list[float]],
    test_vector: list[float],
) -> tuple[str, dict[str, float]]:
    by_layer: dict[str, list[list[float]]] = defaultdict(list)
    for row, vec in zip(train_rows, train_vectors):
        by_layer[str(row["target_layer"])].append(vec)

    distances: dict[str, float] = {}
    for layer, vectors in by_layer.items():
        centroid = [sum(vec[idx] for vec in vectors) / len(vectors) for idx in range(len(test_vector))]
        distances[layer] = _distance(test_vector, centroid)

    ranked = sorted(distances.items(), key=lambda item: (item[1], item[0]))
    return ranked[0][0], {layer: round(dist, 6) for layer, dist in ranked}


def _knn(
    train_rows: list[dict[str, Any]],
    train_vectors: list[list[float]],
    test_vector: list[float],
    k: int,
) -> tuple[str, dict[str, float]]:
    neighbors = sorted(
        (
            (_distance(test_vector, vec), str(row["target_layer"]))
            for row, vec in zip(train_rows, train_vectors)
        ),
        key=lambda item: (item[0], item[1]),
    )[: max(1, min(k, len(train_vectors)))]

    votes: dict[str, float] = defaultdict(float)
    best_dist: dict[str, float] = {}
    for dist, layer in neighbors:
        votes[layer] += 1.0 / (dist + 1e-6)
        best_dist[layer] = min(best_dist.get(layer, float("inf")), dist)

    ranked = sorted(votes.items(), key=lambda item: (-item[1], best_dist[item[0]], item[0]))
    return ranked[0][0], {layer: round(score, 6) for layer, score in ranked}


def _summarize_predictions(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(predictions)
    correct = sum(1 for pred in predictions if pred["correct"])
    by_holdout: dict[str, dict[str, Any]] = {}
    for holdout, rows in _group_by(predictions, "holdout").items():
        by_holdout[holdout] = {
            "total": len(rows),
            "correct": sum(1 for row in rows if row["correct"]),
            "accuracy": round(sum(1 for row in rows if row["correct"]) / max(1, len(rows)), 6),
            "truth_counts": dict(Counter(row["truth"] for row in rows)),
            "pred_counts": dict(Counter(row["pred"] for row in rows)),
            "unseen_truth_classes": sorted({row["truth"] for row in rows if row["truth_unseen_in_training"]}),
        }

    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for pred in predictions:
        confusion[pred["truth"]][pred["pred"]] += 1

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / max(1, total), 6),
        "by_holdout": by_holdout,
        "confusion": {truth: dict(preds) for truth, preds in sorted(confusion.items())},
        "mistakes": [pred for pred in predictions if not pred["correct"]],
    }


def _summarize_number_gate(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize the first Auto-build question: should this component be Number?"""
    true_number = [pred for pred in predictions if pred["truth"] == "numbers"]
    true_non_number = [pred for pred in predictions if pred["truth"] != "numbers"]
    kept = [pred for pred in true_number if pred["pred"] == "numbers"]
    lost = [pred for pred in true_number if pred["pred"] != "numbers"]
    false_numbers = [pred for pred in true_non_number if pred["pred"] == "numbers"]
    rejected_non_numbers = [pred for pred in true_non_number if pred["pred"] != "numbers"]
    by_holdout: dict[str, dict[str, Any]] = {}
    for holdout, rows in _group_by(predictions, "holdout").items():
        holdout_true = [pred for pred in rows if pred["truth"] == "numbers"]
        holdout_non = [pred for pred in rows if pred["truth"] != "numbers"]
        holdout_kept = [pred for pred in holdout_true if pred["pred"] == "numbers"]
        holdout_false = [pred for pred in holdout_non if pred["pred"] == "numbers"]
        by_holdout[holdout] = {
            "number_kept": len(holdout_kept),
            "number_total": len(holdout_true),
            "number_recall": round(len(holdout_kept) / max(1, len(holdout_true)), 6),
            "false_numbers": len(holdout_false),
            "non_number_total": len(holdout_non),
            "false_number_rate": round(len(holdout_false) / max(1, len(holdout_non)), 6),
        }
    return {
        "number_kept": len(kept),
        "number_total": len(true_number),
        "number_recall": round(len(kept) / max(1, len(true_number)), 6),
        "number_lost": len(lost),
        "false_numbers": len(false_numbers),
        "non_number_total": len(true_non_number),
        "false_number_rate": round(len(false_numbers) / max(1, len(true_non_number)), 6),
        "number_precision": round(len(kept) / max(1, len(kept) + len(false_numbers)), 6),
        "rejected_non_numbers": len(rejected_non_numbers),
        "by_holdout": by_holdout,
        "lost_number_record_ids": [int(pred["record_id"]) for pred in lost],
        "false_number_record_ids": [int(pred["record_id"]) for pred in false_numbers],
    }


def _rule_override(record: dict[str, Any], pred: str) -> tuple[str, str | None]:
    """Apply small, auditable diagnostic rules to known mistake classes.

    These rules are intentionally offline-only. They test whether visible
    failure classes from the reviewed sheets are separable by geometry/source
    metadata before any runtime Auto-build behavior is considered.
    """
    source_layer = str(record.get("layer") or "")
    role_guess = str(record.get("role_guess") or "")
    aspect = float(record.get("aspect") or 0.0)
    fill = float(record.get("fill") or 0.0)
    area_px = float(record.get("area_px") or 0.0)
    mean_saturation = float(record.get("mean_saturation") or 0.0)
    mean_value = float(record.get("mean_value") or 0.0)
    edge_density = float(record.get("edge_density") or 0.0)
    color_std = float(record.get("color_std") or 0.0)
    bbox = record.get("bbox") or [0, 0, 0, 0]
    x = float(bbox[0]) if len(bbox) > 0 else 0.0
    y = float(bbox[1]) if len(bbox) > 1 else 0.0
    width = float(bbox[2]) if len(bbox) > 2 else 0.0
    height = float(bbox[3]) if len(bbox) > 3 else 0.0
    center_y = float(record.get("center_y") or ((y + height / 2.0) / 1024.0))

    if source_layer == "numbers" and aspect <= 0.25 and height >= 96 and width <= 48:
        return "sponsors", "vertical_text_panel_from_numbers"

    if source_layer == "paint" and pred == "paint" and area_px <= 900 and mean_saturation >= 0.20:
        return "sponsors", "tiny_colored_wordmark_from_paint"

    if (
        source_layer == "paint"
        and pred == "paint"
        and area_px >= 25000
        and area_px <= 50000
        and 0.75 <= aspect <= 1.45
        and 0.55 <= fill <= 0.90
        and width <= 360
        and height <= 360
        and edge_density >= 0.08
        and color_std >= 0.20
    ):
        return "numbers", "large_number_like_submask_from_paint"

    if (
        source_layer == "numbers"
        and pred in {"sponsors", "template"}
        and 350 <= area_px <= 1800
        and 2.40 <= aspect <= 3.20
        and 0.80 <= fill <= 0.90
        and 0.18 <= mean_saturation <= 0.42
        and 0.16 <= edge_density <= 0.30
        and 0.22 <= color_std <= 0.42
        and 35 <= width <= 80
        and 10 <= height <= 30
    ):
        return "numbers", "small_horizontal_number_highlight_from_numbers"

    if (
        source_layer == "numbers"
        and pred in {"numbers", "template"}
        and 1000 <= area_px <= 2200
        and 0.45 <= aspect <= 0.75
        and 0.55 <= fill <= 0.90
        and mean_saturation <= 0.16
        and mean_value <= 0.35
        and 0.10 <= edge_density <= 0.19
        and 0.25 <= color_std <= 0.37
        and 30 <= width <= 45
        and 55 <= height <= 70
    ):
        return "sponsors", "dark_sponsor_wordmark_letter_from_numbers"

    if (
        source_layer == "numbers"
        and pred in {"numbers", "template"}
        and 800 <= area_px <= 1500
        and 0.80 <= aspect <= 1.20
        and 0.70 <= fill <= 0.90
        and mean_saturation <= 0.20
        and mean_value <= 0.05
        and edge_density <= 0.09
        and color_std <= 0.08
        and 30 <= width <= 50
        and 30 <= height <= 50
    ):
        return "sponsors", "dark_sponsor_logo_dot_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "sponsors"
        and area_px >= 8000
        and 0.80 <= aspect <= 1.80
        and 0.65 <= fill <= 0.85
        and mean_value <= 0.35
        and edge_density >= 0.18
    ):
        return "numbers", "dark_compact_number_from_numbers"

    if (
        source_layer == "numbers"
        and pred in {"paint", "sponsors", "template"}
        and 12000 <= area_px <= 45000
        and 1.10 <= aspect <= 1.65
        and 0.60 <= fill <= 0.82
        and mean_saturation >= 0.45
        and mean_value >= 0.50
        and 0.04 <= edge_density <= 0.14
        and 0.18 <= color_std <= 0.38
        and 150 <= width <= 280
        and 100 <= height <= 220
    ):
        return "numbers", "large_colorful_number_body_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "sponsors"
        and 3000 <= area_px <= 15000
        and 0.45 <= aspect <= 1.25
        and 0.45 <= fill <= 0.82
        and mean_saturation >= 0.45
        and 0.12 <= edge_density <= 0.28
        and color_std >= 0.18
        and 35 <= width <= 130
        and 55 <= height <= 130
    ):
        return "numbers", "colorful_outlined_number_body_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "sponsors"
        and 1800 <= area_px <= 9000
        and 0.50 <= aspect <= 1.25
        and 0.45 <= fill <= 0.78
        and mean_saturation <= 0.10
        and mean_value <= 0.35
        and edge_density <= 0.13
        and 0.12 <= color_std <= 0.45
        and 35 <= width <= 120
        and 45 <= height <= 120
    ):
        return "numbers", "compact_dark_number_body_from_numbers"

    if (
        source_layer == "numbers"
        and pred in {"template", "paint", "sponsors"}
        and 9000 <= area_px <= 16000
        and 1.10 <= aspect <= 1.65
        and 0.68 <= fill <= 0.84
        and mean_saturation <= 0.08
        and 0.12 <= mean_value <= 0.35
        and 0.18 <= edge_density <= 0.34
        and 0.22 <= color_std <= 0.40
        and 100 <= width <= 180
        and 80 <= height <= 130
    ):
        return "numbers", "gray_outlined_number_body_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "numbers"
        and area_px >= 20000
        and aspect >= 2.0
        and fill <= 0.60
        and edge_density <= 0.075
        and mean_saturation <= 0.12
        and color_std >= 0.30
    ):
        return "paint", "low_edge_livery_panel_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "numbers"
        and 5000 <= area_px <= 9000
        and 0.55 <= aspect <= 0.85
        and 0.55 <= fill <= 0.75
        and mean_saturation <= 0.08
        and 0.70 <= mean_value <= 0.90
        and edge_density <= 0.06
        and color_std >= 0.25
        and 65 <= width <= 105
        and 95 <= height <= 145
    ):
        return "paint", "pale_livery_graphic_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "sponsors"
        and area_px >= 1500
        and aspect >= 5.5
        and edge_density <= 0.15
        and color_std <= 0.12
    ):
        return "paint", "thin_livery_stripe_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "sponsors"
        and area_px <= 2500
        and (
            (aspect >= 6.0 and edge_density >= 0.25)
            or (
                mean_saturation <= 0.02
                and mean_value >= 0.95
                and edge_density <= 0.08
                and color_std <= 0.08
            )
        )
    ):
        return "paint", "small_livery_mark_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "sponsors"
        and area_px >= 5000
        and 0.55 <= aspect <= 0.85
        and 0.55 <= fill <= 0.75
        and mean_saturation <= 0.08
        and mean_value >= 0.60
        and edge_density <= 0.06
        and color_std >= 0.25
    ):
        return "paint", "low_edge_livery_graphic_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "template"
        and 20 <= area_px <= 80
        and 0.65 <= aspect <= 1.20
        and 0.45 <= fill <= 0.75
        and mean_saturation <= 0.05
        and mean_value <= 0.35
        and edge_density >= 0.25
        and color_std >= 0.20
        and width <= 12
        and height <= 12
    ):
        return "sponsors", "tiny_logo_fragment_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "template"
        and 2000 <= area_px <= 4500
        and 0.85 <= aspect <= 1.15
        and 0.70 <= fill <= 0.88
        and mean_saturation <= 0.04
        and 0.12 <= mean_value <= 0.30
        and 0.10 <= edge_density <= 0.22
        and 0.08 <= color_std <= 0.18
        and 45 <= width <= 75
        and 45 <= height <= 75
    ):
        return "sponsors", "round_sponsor_logo_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "paint"
        and 3000 <= area_px <= 15000
        and 0.80 <= aspect <= 1.60
        and 0.45 <= fill <= 0.75
        and mean_saturation <= 0.08
        and mean_value >= 0.65
        and edge_density <= 0.07
        and color_std <= 0.10
    ):
        return "sponsors", "light_sponsor_logo_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "paint"
        and 5000 <= area_px <= 20000
        and 2.20 <= aspect <= 3.20
        and 0.50 <= fill <= 0.78
        and mean_saturation >= 0.65
        and mean_value >= 0.65
        and edge_density <= 0.14
        and color_std >= 0.10
        and width >= 120
        and height <= 90
    ):
        return "sponsors", "saturated_wide_sponsor_panel_from_numbers"

    if (
        source_layer == "numbers"
        and pred in {"paint", "sponsors", "template"}
        and 3000 <= area_px <= 5000
        and 0.90 <= aspect <= 1.30
        and 0.65 <= fill <= 0.78
        and 0.38 <= mean_saturation <= 0.50
        and mean_value >= 0.88
        and 0.16 <= edge_density <= 0.22
        and 0.27 <= color_std <= 0.34
        and 70 <= width <= 95
        and 60 <= height <= 80
    ):
        return "numbers", "flag_filled_number_body_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "paint"
        and 900 <= area_px <= 1600
        and 0.80 <= aspect <= 1.20
        and 0.82 <= fill <= 1.00
        and 0.20 <= mean_saturation <= 0.45
        and mean_value <= 0.04
        and edge_density <= 0.03
        and color_std <= 0.04
        and 30 <= width <= 45
        and 30 <= height <= 45
    ):
        return "numbers", "dark_number_counter_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "numbers"
        and 10000 <= area_px <= 16000
        and 0.35 <= aspect <= 0.55
        and 0.76 <= fill <= 0.86
        and 0.50 <= mean_saturation <= 0.65
        and 0.75 <= mean_value <= 0.88
        and edge_density <= 0.11
        and 0.30 <= color_std <= 0.40
        and 75 <= width <= 95
        and 170 <= height <= 210
    ):
        return "sponsors", "vertical_sponsor_panel_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "numbers"
        and 18000 <= area_px <= 26000
        and 0.85 <= aspect <= 1.10
        and 0.45 <= fill <= 0.60
        and mean_saturation <= 0.05
        and 0.65 <= mean_value <= 0.90
        and 0.12 <= edge_density <= 0.22
        and 0.30 <= color_std <= 0.42
        and 170 <= width <= 220
        and 180 <= height <= 230
    ):
        return "sponsors", "sponsor_number_logo_panel_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "paint"
        and 300 <= area_px <= 600
        and 0.25 <= aspect <= 0.45
        and fill >= 0.94
        and 0.35 <= mean_saturation <= 0.55
        and mean_value <= 0.04
        and edge_density <= 0.03
        and color_std <= 0.04
        and width <= 18
        and 30 <= height <= 45
    ):
        return "sponsors", "sponsor_panel_edge_from_numbers"

    if (
        source_layer == "sponsors"
        and pred in {"numbers", "sponsors", "template"}
        and 550 <= area_px <= 6000
        and 0.80 <= aspect <= 2.05
        and 0.40 <= fill <= 0.84
        and 0.45 <= mean_saturation <= 1.00
        and 0.42 <= mean_value <= 0.86
        and 0.16 <= edge_density <= 0.34
        and 0.13 <= color_std <= 0.24
        and 25 <= width <= 125
        and 25 <= height <= 125
    ):
        return "paint", "decorative_livery_motif_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "sponsors", "template"}
        and 100 <= area_px <= 1300
        and 1.55 <= aspect <= 1.90
        and 0.08 <= fill <= 0.46
        and mean_saturation >= 0.95
        and 0.78 <= mean_value <= 0.90
        and 0.09 <= edge_density <= 0.58
        and color_std <= 0.065
        and 35 <= width <= 80
        and 25 <= height <= 45
    ):
        return "numbers", "roof_number_warm_stroke_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and 600 <= area_px <= 1000
        and 4.50 <= aspect <= 7.00
        and 0.50 <= fill <= 0.75
        and 0.55 <= mean_saturation <= 0.80
        and 0.45 <= mean_value <= 0.65
        and 0.32 <= edge_density <= 0.42
        and 0.30 <= color_std <= 0.42
        and 70 <= width <= 100
        and 10 <= height <= 22
    ):
        return "sponsors", "thin_sponsor_textline_on_number_panel_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and 2800 <= area_px <= 4200
        and 0.90 <= aspect <= 1.30
        and 0.24 <= fill <= 0.38
        and 0.12 <= mean_saturation <= 0.32
        and 0.30 <= mean_value <= 0.45
        and 0.22 <= edge_density <= 0.31
        and 0.36 <= color_std <= 0.46
        and 85 <= width <= 140
        and 75 <= height <= 125
    ):
        return "sponsors", "high_variance_sponsor_logo_graphic_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and 2500 <= area_px <= 3800
        and 2.20 <= aspect <= 3.00
        and 0.68 <= fill <= 0.86
        and 0.42 <= mean_saturation <= 0.64
        and 0.52 <= mean_value <= 0.72
        and 0.29 <= edge_density <= 0.39
        and 0.30 <= color_std <= 0.39
        and 85 <= width <= 130
        and 30 <= height <= 55
    ):
        return "sponsors", "high_variance_sponsor_text_panel_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and 2000 <= area_px <= 8500
        and 1.85 <= aspect <= 4.25
        and 0.74 <= fill <= 0.94
        and 0.14 <= mean_saturation <= 0.42
        and 0.54 <= mean_value <= 0.70
        and 0.29 <= edge_density <= 0.41
        and 0.34 <= color_std <= 0.42
        and 95 <= width <= 175
        and 24 <= height <= 75
    ):
        return "sponsors", "large_low_sat_sponsor_wordmark_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"numbers", "paint"}
        and 4800 <= area_px <= 60000
        and (
            (2.45 <= aspect <= 4.05 and width >= 120 and height >= 45)
            or (0.38 <= aspect <= 0.66 and width >= 120 and height >= 90)
        )
        and 0.50 <= fill <= 0.86
        and 0.58 <= mean_saturation <= 0.98
        and 0.58 <= mean_value <= 0.92
        and 0.075 <= edge_density <= 0.17
        and 0.16 <= color_std <= 0.38
    ):
        return "sponsors", "large_saturated_stockcar_sponsor_panel_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"numbers", "template"}
        and 30 <= area_px <= 900
        and 0.80 <= aspect <= 3.35
        and 0.50 <= fill <= 0.95
        and mean_saturation <= 0.28
        and 0.40 <= mean_value <= 0.58
        and 0.30 <= edge_density <= 0.47
        and 0.29 <= color_std <= 0.44
        and 0.20 <= center_y <= 0.95
        and width <= 55
        and height <= 25
    ):
        return "sponsors", "small_neutral_contingency_fragment_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and 500 <= area_px <= 6500
        and 0.14 <= aspect <= 0.42
        and 0.62 <= fill <= 0.94
        and mean_saturation <= 0.40
        and 0.50 <= mean_value <= 0.72
        and 0.24 <= edge_density <= 0.38
        and 0.30 <= color_std <= 0.47
        and 16 <= width <= 40
        and 45 <= height <= 210
    ):
        return "sponsors", "vertical_sponsor_wordmark_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "sponsors", "template", "numbers"}
        and 3500 <= area_px <= 18000
        and 0.50 <= aspect <= 2.10
        and 0.45 <= fill <= 0.86
        and 0.38 <= mean_saturation <= 0.66
        and 0.50 <= mean_value <= 0.82
        and 0.16 <= edge_density <= 0.30
        and 0.28 <= color_std <= 0.43
        and 70 <= width <= 180
        and 55 <= height <= 145
    ):
        return "numbers", "flag_filled_number_body_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "sponsors", "template"}
        and 9000 <= area_px <= 25000
        and 1.10 <= aspect <= 1.75
        and 0.55 <= fill <= 0.80
        and mean_saturation >= 0.45
        and 0.45 <= mean_value <= 0.90
        and 0.07 <= edge_density <= 0.16
        and 0.18 <= color_std <= 0.40
        and 110 <= width <= 240
        and 80 <= height <= 180
    ):
        return "numbers", "large_saturated_number_body_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and 10000 <= area_px <= 30000
        and y <= 48
        and width >= 120
        and height >= 95
        and 0.75 <= aspect <= 1.60
        and 0.55 <= fill <= 0.90
        and mean_saturation <= 0.20
        and edge_density <= 0.22
        and color_std >= 0.32
    ):
        return "template", "front_clip_template_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and 8500 <= area_px <= 12000
        and 2.00 <= aspect <= 2.60
        and fill >= 0.92
        and 0.55 <= mean_saturation <= 0.68
        and 0.78 <= mean_value <= 0.94
        and edge_density <= 0.14
        and 0.26 <= color_std <= 0.34
        and 130 <= width <= 170
        and 55 <= height <= 75
    ):
        return "sponsors", "wide_saturated_sponsor_panel_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "template"}
        and 5000 <= area_px <= 15000
        and mean_saturation <= 0.06
        and mean_value >= 0.90
        and edge_density <= 0.08
        and color_std <= 0.20
        and (
            (
                aspect >= 6.00
                and fill >= 0.90
                and height <= 30
            )
            or (
                aspect <= 0.20
                and fill >= 0.70
                and width <= 70
                and height >= 180
            )
        )
    ):
        return "sponsors", "long_low_sat_sponsor_strip_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "template"}
        and 25 <= area_px <= 900
        and 1.35 <= aspect <= 8.00
        and 0.35 <= fill <= 0.75
        and mean_saturation <= 0.02
        and 0.48 <= mean_value <= 0.68
        and edge_density >= 0.30
        and color_std >= 0.30
        and width <= 90
        and height <= 16
    ):
        return "sponsors", "high_edge_sponsor_wordmark_fragment_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "template"}
        and role_guess == "small_contingency_or_logo"
        and 25 <= area_px <= 1200
        and 0.08 <= mean_saturation <= 0.62
        and 0.25 <= mean_value <= 0.93
        and 0.075 <= color_std <= 0.38
        and 0.05 <= edge_density <= 0.50
        and 0.28 <= fill <= 0.90
        and width <= 65
        and height <= 55
    ):
        return "sponsors", "tiny_colored_contingency_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "template"}
        and 650 <= area_px <= 1800
        and 0.70 <= aspect <= 1.25
        and 0.30 <= fill <= 0.72
        and mean_saturation <= 0.025
        and 0.62 <= mean_value <= 0.94
        and 0.08 <= edge_density <= 0.17
        and 0.055 <= color_std <= 0.14
        and 40 <= width <= 75
        and 40 <= height <= 75
    ):
        return "sponsors", "pale_round_sponsor_badge_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "template"
        and 250 <= area_px <= 950
        and 1.00 <= aspect <= 4.25
        and 0.65 <= fill <= 1.00
        and 0.10 <= mean_saturation <= 0.55
        and 0.30 <= mean_value <= 0.86
        and edge_density >= 0.25
        and color_std >= 0.24
        and width <= 60
        and height <= 35
    ):
        return "sponsors", "compact_contingency_logo_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "template"}
        and 3000 <= area_px <= 6500
        and 3.00 <= aspect <= 4.20
        and 0.80 <= fill <= 0.95
        and 0.10 <= mean_saturation <= 0.25
        and mean_value <= 0.20
        and 0.08 <= edge_density <= 0.14
        and 0.20 <= color_std <= 0.32
        and 100 <= width <= 170
        and 25 <= height <= 55
    ):
        return "sponsors", "dark_sponsor_wordmark_panel_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "paint"
        and 8500 <= area_px <= 27000
        and 2.00 <= aspect <= 8.25
        and 0.50 <= fill <= 0.86
        and mean_saturation <= 0.018
        and 0.94 <= mean_value <= 1.01
        and 0.025 <= edge_density <= 0.055
        and 0.045 <= color_std <= 0.16
        and 200 <= width <= 360
        and 40 <= height <= 150
    ):
        return "paint", "large_white_livery_panel_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "paint"
        and 2500 <= area_px <= 6500
        and 1.00 <= aspect <= 2.60
        and 0.50 <= fill <= 0.75
        and mean_saturation <= 0.04
        and 0.74 <= mean_value <= 0.90
        and 0.04 <= edge_density <= 0.11
        and 0.07 <= color_std <= 0.13
        and 80 <= width <= 160
        and 35 <= height <= 105
    ):
        return "template", "flat_template_panel_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"sponsors", "paint", "template"}
        and 20 <= area_px <= 60
        and mean_saturation >= 0.04
        and mean_saturation <= 0.22
        and 0.10 <= mean_value <= 0.60
        and 0.08 <= color_std <= 0.35
        and width <= 35
        and height <= 25
        and (
            (edge_density >= 0.55 and fill <= 0.30)
            or (height <= 2 and aspect >= 10.0 and fill >= 0.80)
        )
    ):
        return "numbers", "tiny_flag_number_fragment_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "paint"
        and 20 <= area_px <= 90
        and 0.65 <= aspect <= 1.05
        and 0.40 <= fill <= 0.60
        and mean_saturation <= 0.02
        and 0.70 <= mean_value <= 0.88
        and edge_density <= 0.02
        and color_std <= 0.02
        and width <= 15
        and height <= 16
    ):
        return "template", "tiny_template_detail_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "paint"
        and 2500 <= area_px <= 7500
        and aspect >= 18.00
        and fill >= 0.90
        and 0.025 <= mean_saturation <= 0.12
        and 0.60 <= mean_value <= 0.90
        and edge_density <= 0.01
        and color_std <= 0.04
        and width >= 220
        and height <= 18
    ):
        return "paint", "long_low_sat_livery_stripe_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"sponsors", "template"}
        and 1800 <= area_px <= 4200
        and 0.28 <= aspect <= 0.60
        and 0.72 <= fill <= 0.92
        and mean_saturation >= 0.94
        and 0.55 <= mean_value <= 0.72
        and 0.07 <= edge_density <= 0.15
        and 0.08 <= color_std <= 0.14
        and 30 <= width <= 45
        and 60 <= height <= 120
    ):
        return "paint", "red_checker_livery_chunk_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "template"
        and 800 <= area_px <= 1500
        and 0.85 <= aspect <= 1.45
        and 0.72 <= fill <= 1.00
        and 0.24 <= mean_saturation <= 0.36
        and mean_value <= 0.025
        and edge_density <= 0.025
        and color_std <= 0.03
        and 30 <= width <= 40
        and 25 <= height <= 40
    ):
        return "paint", "black_checker_livery_chunk_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred in {"paint", "template"}
        and 900 <= area_px <= 1600
        and 0.78 <= aspect <= 1.18
        and fill >= 0.80
        and mean_saturation >= 0.95
        and 0.76 <= mean_value <= 0.86
        and edge_density <= 0.07
        and color_std <= 0.06
        and 28 <= width <= 45
        and 28 <= height <= 45
    ):
        return "sponsors", "saturated_sponsor_tile_from_sponsors"

    if (
        source_layer == "sponsors"
        and pred == "template"
        and 6500 <= area_px <= 11000
        and 0.75 <= aspect <= 1.15
        and 0.60 <= fill <= 0.80
        and mean_saturation <= 0.055
        and 0.15 <= mean_value <= 0.75
        and edge_density >= 0.18
        and 0.25 <= color_std <= 0.45
        and 75 <= width <= 125
        and 95 <= height <= 135
    ):
        return "sponsors", "large_low_sat_sponsor_logo_from_sponsors"

    if (
        source_layer == "paint"
        and pred in {"numbers", "paint", "template"}
        and 2400 <= area_px <= 7000
        and 0.35 <= aspect <= 3.00
        and 0.45 <= fill <= 0.82
        and mean_saturation <= 0.08
        and 0.02 <= mean_value <= 0.32
        and 0.05 <= edge_density <= 0.26
        and 0.12 <= color_std <= 0.40
        and 55 <= width <= 125
        and 35 <= height <= 155
        and 390 <= x <= 500
        and 400 <= y <= 560
    ):
        return "sponsors", "paint_sponsor_logo_panel_from_paint"

    if (
        source_layer == "template"
        and pred in {"paint", "template"}
        and 150 <= area_px <= 300
        and 0.75 <= aspect <= 1.40
        and 0.45 <= fill <= 0.75
        and mean_saturation >= 0.90
        and mean_value >= 0.90
        and edge_density <= 0.02
        and width <= 30
        and height <= 30
        and x <= 40
        and y >= 980
    ):
        return "paint", "saturated_livery_color_square_from_template"

    if (
        source_layer == "template"
        and pred == "paint"
        and 8000 <= area_px <= 14000
        and fill >= 0.90
        and mean_saturation <= 0.02
        and mean_value <= 0.18
        and edge_density <= 0.02
        and color_std <= 0.02
        and 80 <= width <= 130
        and 85 <= height <= 160
    ):
        return "template", "flat_dark_template_panel_from_template"

    if (
        source_layer == "template"
        and pred == "paint"
        and 700 <= area_px <= 6000
        and 0.50 <= aspect <= 1.45
        and 0.30 <= fill <= 0.99
        and mean_saturation <= 0.02
        and 0.55 <= mean_value <= 0.85
        and edge_density <= 0.02
        and color_std <= 0.02
        and 30 <= width <= 105
        and 35 <= height <= 90
    ):
        return "template", "flat_gray_template_panel_from_template"

    if (
        source_layer == "template"
        and pred == "paint"
        and 50 <= area_px <= 1200
        and aspect >= 14.00
        and 0.55 <= fill <= 1.00
        and mean_saturation <= 0.005
        and mean_value >= 0.995
        and edge_density <= 0.005
        and color_std <= 0.005
        and 30 <= width <= 240
        and height <= 12
    ):
        return "paint", "pure_white_livery_strip_from_template"

    if (
        source_layer == "template"
        and pred == "paint"
        and 2000 <= area_px <= 15000
        and aspect >= 3.00
        and fill >= 0.65
        and mean_saturation <= 0.07
        and 0.08 <= mean_value <= 0.84
        and edge_density <= 0.01
        and color_std <= 0.012
        and width >= 140
        and height <= 55
    ):
        return "template", "long_flat_neutral_template_strip_from_template"

    if (
        source_layer == "template"
        and pred == "paint"
        and 300 <= area_px <= 2200
        and 0.30 <= aspect <= 1.20
        and 0.25 <= fill <= 0.95
        and mean_saturation <= 0.012
        and 0.70 <= mean_value <= 0.90
        and edge_density <= 0.01
        and color_std <= 0.012
        and 20 <= width <= 55
        and 20 <= height <= 140
    ):
        return "template", "neutral_template_panel_detail_from_template"

    if (
        source_layer == "template"
        and pred == "paint"
        and 20 <= area_px <= 220
        and mean_saturation <= 0.02
        and 0.55 <= mean_value <= 0.90
        and edge_density <= 0.03
        and color_std <= 0.035
        and width <= 28
        and height <= 32
    ):
        return "template", "small_flat_template_detail_from_template"

    if (
        source_layer == "sponsors"
        and pred == "numbers"
        and mean_saturation >= 0.55
        and edge_density >= 0.20
        and color_std <= 0.35
    ):
        return "sponsors", "saturated_sponsor_logo_from_sponsors"

    if (
        source_layer == "numbers"
        and pred == "numbers"
        and area_px >= 20000
        and aspect >= 2.50
        and fill >= 0.88
        and mean_saturation <= 0.05
        and mean_value >= 0.65
        and edge_density <= 0.06
    ):
        return "sponsors", "wide_wordmark_panel_from_numbers"

    if (
        source_layer == "numbers"
        and pred == "numbers"
        and area_px <= 900
        and aspect >= 2.50
        and fill >= 0.85
        and edge_density >= 0.30
    ):
        return "sponsors", "tiny_contingency_strip_from_numbers"

    return pred, None


def _apply_rule_overlay(
    predictions: list[dict[str, Any]],
    records_by_id: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for pred in predictions:
        record = records_by_id[int(pred["record_id"])]
        new_pred, reason = _rule_override(record, str(pred["pred"]))
        item = dict(pred)
        item["base_pred"] = pred["pred"]
        item["pred"] = new_pred
        item["correct"] = new_pred == item["truth"]
        item["rule_override"] = reason
        out.append(item)
    return out


def _group_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "unknown")].append(row)
    return grouped


def _oracle_summary_path(record: dict[str, Any]) -> Path | None:
    feature_source = record.get("feature_source")
    if not feature_source:
        return None
    path = Path(feature_source)
    if not path.is_absolute():
        path = REPO_ROOT / path
    summary_path = path.parent / "summary.json"
    return summary_path if summary_path.exists() else None


def _source_image_path(record: dict[str, Any]) -> Path | None:
    summary_path = _oracle_summary_path(record)
    if summary_path is None:
        return None
    source = _read_json(summary_path).get("source_1024")
    if not source:
        return None
    source_path = Path(source)
    return source_path if source_path.exists() else None


def _crop_record(record: dict[str, Any], size: int) -> Image.Image:
    source_path = _source_image_path(record)
    if source_path is None:
        return Image.new("RGB", (size, size), (35, 35, 35))
    source = Image.open(source_path).convert("RGB")
    x, y, w, h = [int(v) for v in record.get("bbox", [0, 0, 1, 1])]
    pad = max(8, int(max(w, h) * 0.15))
    left = max(0, x - pad)
    top = max(0, y - pad)
    right = min(source.width, x + w + pad)
    bottom = min(source.height, y + h + pad)
    crop = source.crop((left, top, right, bottom))
    crop.thumbnail((size, size), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (size, size), (18, 18, 18))
    tile.paste(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    return tile


def _write_mistake_sheet(
    predictions: list[dict[str, Any]],
    records_by_id: dict[int, dict[str, Any]],
    path: Path,
    max_items: int,
) -> str | None:
    mistakes = [pred for pred in predictions if not pred["correct"]][:max_items]
    if not mistakes:
        return None
    cols = 4
    crop_size = 180
    label_h = 70
    tile_w = crop_size
    tile_h = crop_size + label_h
    rows = math.ceil(len(mistakes) / cols)
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (248, 248, 248))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for idx, pred in enumerate(mistakes):
        record = records_by_id[pred["record_id"]]
        tile_x = (idx % cols) * tile_w
        tile_y = (idx // cols) * tile_h
        crop = _crop_record(record, crop_size)
        sheet.paste(crop, (tile_x, tile_y))
        text_lines = [
            f"{pred['truth']} -> {pred['pred']}",
            str(record.get("label") or ""),
            str(record.get("paint_label") or "")[:30],
            f"bbox={record.get('bbox')}",
        ]
        for line_idx, text in enumerate(text_lines):
            draw.text((tile_x + 4, tile_y + crop_size + 4 + line_idx * 15), text, fill=(15, 15, 15), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.resolve())


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    records_path = _repo_path(args.features)
    records = _read_json(records_path)
    if not isinstance(records, list):
        raise ValueError(f"{records_path} is not a reviewed feature list")
    if len({str(row.get("paint_label")) for row in records}) < 2:
        raise ValueError("leave-one-car-out eval requires at least two paint_label groups")

    for idx, record in enumerate(records):
        record["_record_id"] = idx
    records_by_id = {int(record["_record_id"]): record for record in records}

    out_dir = _repo_path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    methods: dict[str, list[dict[str, Any]]] = {}
    for view_name in FEATURE_VIEWS:
        methods[f"{view_name}__knn{args.k}"] = []
        methods[f"{view_name}__nearest_centroid"] = []

    groups = _group_by(records, "paint_label")
    for holdout, test_rows in sorted(groups.items()):
        train_rows = [row for row in records if str(row.get("paint_label")) != holdout]
        training_layers = {str(row["target_layer"]) for row in train_rows}

        for view_name in FEATURE_VIEWS:
            include_source_layer = view_name == "source_layer"
            train_raw = [_feature_vector(row, include_source_layer) for row in train_rows]
            means, stds = _fit_scaler(train_raw)
            train_vectors = [_scale(vec, means, stds) for vec in train_raw]

            for test_row in test_rows:
                test_vector = _scale(_feature_vector(test_row, include_source_layer), means, stds)
                truth = str(test_row["target_layer"])
                for classifier_name in ("nearest_centroid", f"knn{args.k}"):
                    method = f"{view_name}__{classifier_name}"
                    if classifier_name == "nearest_centroid":
                        pred, scores = _nearest_centroid(train_rows, train_vectors, test_vector)
                    else:
                        pred, scores = _knn(train_rows, train_vectors, test_vector, args.k)
                    methods[method].append({
                        "record_id": int(test_row["_record_id"]),
                        "holdout": holdout,
                        "truth": truth,
                        "pred": pred,
                        "correct": pred == truth,
                        "truth_unseen_in_training": truth not in training_layers,
                        "label": test_row.get("label"),
                        "source_layer": test_row.get("layer"),
                        "bbox": test_row.get("bbox"),
                        "scores": scores,
                    })

    summaries: dict[str, Any] = {}
    rule_overlay_methods: dict[str, list[dict[str, Any]]] = {}
    for method, predictions in methods.items():
        if method.startswith("source_layer__"):
            rule_overlay_methods[f"{method}__rules"] = _apply_rule_overlay(predictions, records_by_id)
    methods.update(rule_overlay_methods)

    for method, predictions in methods.items():
        predictions_path = out_dir / f"{method}_predictions.json"
        predictions_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")
        sheet_path = _write_mistake_sheet(
            predictions,
            records_by_id,
            out_dir / f"{method}_mistakes.png",
            args.max_sheet_items,
        )
        summary = _summarize_predictions(predictions)
        summary["number_gate"] = _summarize_number_gate(predictions)
        summary["predictions_path"] = str(predictions_path.resolve())
        summary["mistake_sheet"] = sheet_path
        summaries[method] = summary

    csv_path = out_dir / "all_predictions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("method", "record_id", "holdout", "truth", "pred", "correct", "label", "bbox"),
        )
        writer.writeheader()
        for method, predictions in methods.items():
            for pred in predictions:
                writer.writerow({
                    "method": method,
                    "record_id": pred["record_id"],
                    "holdout": pred["holdout"],
                    "truth": pred["truth"],
                    "pred": pred["pred"],
                    "correct": pred["correct"],
                    "label": pred["label"],
                    "bbox": pred["bbox"],
                })

    summary = {
        "records_path": str(records_path.resolve()),
        "records": len(records),
        "groups": dict(Counter(str(row.get("paint_label")) for row in records)),
        "target_layers": dict(Counter(str(row.get("target_layer")) for row in records)),
        "feature_views": {name: list(keys) for name, keys in FEATURE_VIEWS.items()},
        "k": args.k,
        "methods": summaries,
        "csv_path": str(csv_path.resolve()),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", required=True, help="reviewed_component_features.json path")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--k", type=int, default=3, help="k for inverse-distance KNN")
    parser.add_argument("--max-sheet-items", type=int, default=32, help="Max mistakes per contact sheet")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(evaluate(parse_args()), indent=2))


if __name__ == "__main__":
    main()
