"""Probe reviewed Smart TGA component rules against unseen route components.

This is offline Smart TGA tooling. It trains the source-aware nearest-centroid
classifier from reviewed component features, applies the guarded diagnostic
rules from ``smart_tga_component_feature_eval.py`` to route-inspector component
records, and writes "would move" review sheets. It does not change runtime
Auto-build behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from smart_tga_component_feature_eval import (
    _feature_vector,
    _fit_scaler,
    _nearest_centroid,
    _read_json,
    _repo_path,
    _rule_override,
    _scale,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FEATURE_KEYS = (
    "mean_rgb",
    "std_rgb",
    "mean_saturation",
    "mean_value",
    "edge_density",
    "color_std",
)


def _load_rows(paths: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in paths:
        path = _repo_path(raw)
        data = _read_json(path)
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a list of component records")
        rows.extend(data)
    return rows


def _load_review_targets(path_value: str | None) -> dict[tuple[str, int], dict[str, Any]]:
    if not path_value:
        return {}
    data = _read_json(_repo_path(path_value))
    targets: dict[tuple[str, int], dict[str, Any]] = {}
    for label in data.get("component_labels", []):
        key = (str(label["layer"]), int(label["component_index"]))
        targets[key] = dict(label)
    return targets


def _missing_feature_keys(record: dict[str, Any]) -> list[str]:
    return [key for key in REQUIRED_FEATURE_KEYS if record.get(key) is None]


def _summarize_feature_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing_counts: Counter[str] = Counter()
    incomplete_ids: list[int] = []
    for idx, row in enumerate(rows):
        missing = _missing_feature_keys(row)
        if missing:
            incomplete_ids.append(idx)
            missing_counts.update(missing)
    complete_rows = len(rows) - len(incomplete_ids)
    return {
        "required_feature_keys": list(REQUIRED_FEATURE_KEYS),
        "complete_rows": complete_rows,
        "incomplete_rows": len(incomplete_ids),
        "complete_fraction": round(complete_rows / max(1, len(rows)), 6),
        "missing_key_counts": dict(sorted(missing_counts.items())),
        "first_incomplete_record_ids": incomplete_ids[:25],
        "safe_for_move_decisions": not incomplete_ids,
    }


def _number_prune_candidates(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in predictions
        if row["source_layer"] == "numbers" and row["pred_layer"] != "numbers"
    ]


def _sponsor_number_promotion_candidate(row: dict[str, Any]) -> bool:
    return (
        row["source_layer"] == "sponsors"
        and row["pred_layer"] == "numbers"
        and float(row.get("area_px") or 0.0) >= 5000
        and 1.20 <= float(row.get("aspect") or 0.0) <= 2.10
        and 0.42 <= float(row.get("fill") or 0.0) <= 0.78
        and float(row.get("mean_saturation") or 0.0) <= 0.18
        and float(row.get("mean_value") or 0.0) >= 0.72
        and float(row.get("edge_density") or 0.0) <= 0.13
        and float(row.get("color_std") or 0.0) >= 0.30
    )


def _confirmed_number_promotion_candidate(row: dict[str, Any]) -> bool:
    """Narrow route-level promotion gate for missing Numbers.

    The broad classifier finds useful missing side/door numbers, but Cycle 130
    route sheets showed it also promotes sponsor panels. Keep this gate
    intentionally small and offline-only until reviewed route sheets prove it.
    """
    if not (row["source_layer"] == "sponsors" and row["pred_layer"] == "numbers"):
        return False

    area_px = float(row.get("area_px") or 0.0)
    aspect = float(row.get("aspect") or 0.0)
    fill = float(row.get("fill") or 0.0)
    mean_saturation = float(row.get("mean_saturation") or 0.0)
    mean_value = float(row.get("mean_value") or 0.0)
    edge_density = float(row.get("edge_density") or 0.0)
    color_std = float(row.get("color_std") or 0.0)
    margin = row.get("base_distance_margin")
    margin_value = float(margin) if margin is not None else 0.0
    rule_override = str(row.get("rule_override") or "")

    if rule_override in {
        "large_saturated_number_body_from_sponsors",
        "flag_filled_number_body_from_sponsors",
        "tiny_flag_number_fragment_from_sponsors",
    }:
        return True

    mid_large_number_body = (
        5000 <= area_px <= 25000
        and 0.85 <= aspect <= 2.35
        and 0.45 <= fill <= 0.99
        and mean_value >= 0.60
        and mean_saturation <= 0.60
        and 0.08 <= edge_density <= 0.23
        and color_std >= 0.30
        and margin_value >= 0.70
    )
    small_dark_digit_fragment = (
        900 <= area_px <= 1800
        and 0.75 <= aspect <= 1.25
        and 0.75 <= fill <= 0.90
        and mean_saturation <= 0.05
        and 0.18 <= mean_value <= 0.35
        and 0.18 <= edge_density <= 0.26
        and color_std >= 0.35
        and margin_value >= 1.0
    )
    small_light_digit_interior = (
        180 <= area_px <= 360
        and 0.70 <= aspect <= 1.10
        and 0.70 <= fill <= 0.86
        and mean_saturation <= 0.04
        and 0.80 <= mean_value <= 0.92
        and 0.08 <= edge_density <= 0.16
        and 0.28 <= color_std <= 0.34
    )
    return mid_large_number_body or small_dark_digit_fragment or small_light_digit_interior


def _selective_number_final_layer(row: dict[str, Any]) -> str:
    if row["source_layer"] == "numbers" and row["pred_layer"] != "numbers":
        return str(row["pred_layer"])
    if _sponsor_number_promotion_candidate(row):
        return "numbers"
    return str(row["source_layer"])


def _staged_number_final_layer(row: dict[str, Any]) -> str:
    if row["source_layer"] == "numbers" and row["pred_layer"] != "numbers":
        return str(row["pred_layer"])
    if _confirmed_number_promotion_candidate(row):
        return "numbers"
    return str(row["source_layer"])


def _paint_sponsor_wordmark_candidate(row: dict[str, Any]) -> bool:
    if not (row["source_layer"] == "paint" and row["pred_layer"] == "sponsors"):
        return False
    area_px = float(row.get("area_px") or 0.0)
    aspect = float(row.get("aspect") or 0.0)
    fill = float(row.get("fill") or 0.0)
    edge_density = float(row.get("edge_density") or 0.0)
    color_std = float(row.get("color_std") or 0.0)
    bbox = row.get("bbox") or [0, 0, 0, 0]
    width = float(bbox[2]) if len(bbox) > 2 else 0.0
    height = float(bbox[3]) if len(bbox) > 3 else 0.0
    return (
        80 <= area_px <= 1000
        and width <= 80
        and height <= 60
        and 0.38 <= fill <= 0.92
        and 0.45 <= aspect <= 3.10
        and edge_density <= 0.22
        and color_std <= 0.35
    )


def _trusted_reviewed_editable_rule_candidate(row: dict[str, Any]) -> bool:
    """Allow only visually reviewed non-number fragment moves into staged editability."""
    if row["source_layer"] == row["pred_layer"]:
        return False
    return str(row.get("rule_override") or "") in {
        "flat_template_panel_from_sponsors",
        "tiny_template_detail_from_sponsors",
        "long_low_sat_livery_stripe_from_sponsors",
        "red_checker_livery_chunk_from_sponsors",
        "black_checker_livery_chunk_from_sponsors",
        "large_white_livery_panel_from_sponsors",
        "paint_sponsor_logo_panel_from_paint",
        "pure_white_livery_strip_from_template",
        "saturated_livery_color_square_from_template",
    }


def _staged_editable_final_layer(row: dict[str, Any]) -> str:
    staged = _staged_number_final_layer(row)
    if staged != row["source_layer"]:
        return staged
    if _paint_sponsor_wordmark_candidate(row):
        return "sponsors"
    if _trusted_reviewed_editable_rule_candidate(row):
        return str(row["pred_layer"])
    return staged


def _summarize_number_prune_policy(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    source_numbers = [row for row in predictions if row["source_layer"] == "numbers"]
    kept_numbers = [row for row in source_numbers if row["pred_layer"] == "numbers"]
    pruned = _number_prune_candidates(predictions)
    ignored_promotions = [
        row for row in predictions
        if row["source_layer"] != "numbers" and row["pred_layer"] == "numbers"
    ]
    return {
        "policy": "demote_current_number_components_only",
        "source_number_components": len(source_numbers),
        "kept_as_numbers": len(kept_numbers),
        "prune_candidates": len(pruned),
        "ignored_number_promotions": len(ignored_promotions),
        "prune_move_counts": dict(Counter(f"numbers->{row['pred_layer']}" for row in pruned)),
        "ignored_promotion_source_counts": dict(Counter(row["source_layer"] for row in ignored_promotions)),
        "kept_number_record_ids": [int(row["record_id"]) for row in kept_numbers],
        "prune_record_ids": [int(row["record_id"]) for row in pruned],
        "ignored_promotion_record_ids": [int(row["record_id"]) for row in ignored_promotions],
        "runtime_safe_claim": False,
        "runtime_note": (
            "Offline diagnostic only. This policy can clean the current Numbers layer "
            "without creating new Number false positives, but it does not recover "
            "missing numbers from Sponsors/Paint."
        ),
    }


def _summarize_selective_number_policy(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    pruned = _number_prune_candidates(predictions)
    promoted = [row for row in predictions if _sponsor_number_promotion_candidate(row)]
    ignored_promotions = [
        row for row in predictions
        if row["source_layer"] != "numbers"
        and row["pred_layer"] == "numbers"
        and row not in promoted
    ]
    return {
        "policy": "demote_current_numbers_and_selectively_promote_large_low_edge_sponsor_numbers",
        "prune_candidates": len(pruned),
        "promotion_candidates": len(promoted),
        "ignored_number_promotions": len(ignored_promotions),
        "promotion_record_ids": [int(row["record_id"]) for row in promoted],
        "ignored_promotion_record_ids": [int(row["record_id"]) for row in ignored_promotions],
        "runtime_safe_claim": False,
        "runtime_note": (
            "Offline diagnostic only. Promotion gates are intentionally narrow "
            "and currently target large low-edge sponsor-origin number bodies; "
            "they do not cover small, dark, or high-saturation number fragments."
        ),
    }


def _summarize_staged_number_policy(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    pruned = _number_prune_candidates(predictions)
    promoted = [row for row in predictions if _confirmed_number_promotion_candidate(row)]
    ignored_promotions = [
        row for row in predictions
        if row["source_layer"] != "numbers"
        and row["pred_layer"] == "numbers"
        and row not in promoted
    ]
    return {
        "policy": "demote_current_numbers_and_promote_confirmed_sponsor_number_shapes",
        "prune_candidates": len(pruned),
        "promotion_candidates": len(promoted),
        "ignored_number_promotions": len(ignored_promotions),
        "promotion_record_ids": [int(row["record_id"]) for row in promoted],
        "ignored_promotion_record_ids": [int(row["record_id"]) for row in ignored_promotions],
        "runtime_safe_claim": False,
        "runtime_note": (
            "Offline staged-policy diagnostic only. It reduces route-wide Number "
            "promotions to high-confidence number-body or tiny digit-fragment shapes, "
            "but still needs route-level review before runtime wiring."
        ),
    }


def _summarize_staged_editable_policy(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    staged = _summarize_staged_number_policy(predictions)
    wordmarks = [row for row in predictions if _paint_sponsor_wordmark_candidate(row)]
    return {
        "policy": "staged_number_plus_small_paint_sponsor_wordmarks",
        "number_stage": staged,
        "paint_sponsor_wordmark_candidates": len(wordmarks),
        "paint_sponsor_wordmark_record_ids": [int(row["record_id"]) for row in wordmarks],
        "runtime_safe_claim": False,
        "runtime_note": (
            "Offline staged-editable diagnostic only. Adds small Paint-origin "
            "wordmark fragments to Sponsors after the staged Number policy; true "
            "full-canvas Paint masses remain Paint."
        ),
    }


def _score_policy(rows: list[dict[str, Any]], policy_name: str) -> dict[str, Any]:
    correct = [row for row in rows if row[f"{policy_name}_final_layer"] == row["target_layer"]]
    true_numbers = [row for row in rows if row["target_layer"] == "numbers"]
    non_numbers = [row for row in rows if row["target_layer"] != "numbers"]
    kept_numbers = [row for row in true_numbers if row[f"{policy_name}_final_layer"] == "numbers"]
    false_numbers = [row for row in non_numbers if row[f"{policy_name}_final_layer"] == "numbers"]
    return {
        "total": len(rows),
        "correct": len(correct),
        "accuracy": round(len(correct) / max(1, len(rows)), 6),
        "number_kept": len(kept_numbers),
        "number_total": len(true_numbers),
        "number_recall": round(len(kept_numbers) / max(1, len(true_numbers)), 6),
        "false_numbers": len(false_numbers),
        "non_number_total": len(non_numbers),
        "false_number_rate": round(len(false_numbers) / max(1, len(non_numbers)), 6),
        "lost_number_record_ids": [int(row["record_id"]) for row in true_numbers if row[f"{policy_name}_final_layer"] != "numbers"],
        "false_number_record_ids": [int(row["record_id"]) for row in false_numbers],
    }


def _score_number_cleanup(rows: list[dict[str, Any]], policy_name: str) -> dict[str, Any]:
    source_numbers = [row for row in rows if row["source_layer"] == "numbers"]
    true_numbers = [row for row in source_numbers if row["target_layer"] == "numbers"]
    false_number_chunks = [row for row in source_numbers if row["target_layer"] != "numbers"]
    kept_true = [row for row in true_numbers if row[f"{policy_name}_final_layer"] == "numbers"]
    cleaned_false = [row for row in false_number_chunks if row[f"{policy_name}_final_layer"] != "numbers"]
    target_correct = [
        row for row in false_number_chunks
        if row[f"{policy_name}_final_layer"] == row["target_layer"]
    ]
    false_to_number = [
        row for row in false_number_chunks
        if row[f"{policy_name}_final_layer"] == "numbers"
    ]
    return {
        "source_number_components": len(source_numbers),
        "true_numbers_kept": len(kept_true),
        "true_numbers_total": len(true_numbers),
        "true_number_recall": round(len(kept_true) / max(1, len(true_numbers)), 6),
        "false_number_chunks_cleaned": len(cleaned_false),
        "false_number_chunks_total": len(false_number_chunks),
        "false_number_cleanup_recall": round(len(cleaned_false) / max(1, len(false_number_chunks)), 6),
        "false_number_target_correct": len(target_correct),
        "false_number_target_accuracy": round(len(target_correct) / max(1, len(false_number_chunks)), 6),
        "false_chunks_left_as_numbers": len(false_to_number),
        "target_counts": dict(Counter(row["target_layer"] for row in false_number_chunks)),
        "final_counts": dict(Counter(row[f"{policy_name}_final_layer"] for row in false_number_chunks)),
        "lost_true_number_record_ids": [
            int(row["record_id"]) for row in true_numbers
            if row[f"{policy_name}_final_layer"] != "numbers"
        ],
        "wrong_target_record_ids": [
            int(row["record_id"]) for row in false_number_chunks
            if row[f"{policy_name}_final_layer"] != row["target_layer"]
        ],
        "left_as_number_record_ids": [int(row["record_id"]) for row in false_to_number],
    }


def _score_paint_sponsor_wordmarks(rows: list[dict[str, Any]], policy_name: str) -> dict[str, Any]:
    source_paint = [row for row in rows if row["source_layer"] == "paint"]
    target_sponsors = [row for row in source_paint if row["target_layer"] == "sponsors"]
    target_paint = [row for row in source_paint if row["target_layer"] == "paint"]
    sponsor_kept = [row for row in target_sponsors if row[f"{policy_name}_final_layer"] == "sponsors"]
    paint_kept = [row for row in target_paint if row[f"{policy_name}_final_layer"] == "paint"]
    false_sponsors = [row for row in target_paint if row[f"{policy_name}_final_layer"] == "sponsors"]
    return {
        "source_paint_components": len(source_paint),
        "paint_origin_sponsors_found": len(sponsor_kept),
        "paint_origin_sponsors_total": len(target_sponsors),
        "paint_origin_sponsor_recall": round(len(sponsor_kept) / max(1, len(target_sponsors)), 6),
        "true_paint_kept": len(paint_kept),
        "true_paint_total": len(target_paint),
        "true_paint_recall": round(len(paint_kept) / max(1, len(target_paint)), 6),
        "true_paint_moved_to_sponsors": len(false_sponsors),
        "missed_paint_sponsor_record_ids": [
            int(row["record_id"]) for row in target_sponsors
            if row[f"{policy_name}_final_layer"] != "sponsors"
        ],
        "true_paint_moved_to_sponsors_record_ids": [int(row["record_id"]) for row in false_sponsors],
    }


def _distance_margin(scores: dict[str, Any]) -> dict[str, Any]:
    ranked = sorted(
        ((str(layer), float(distance)) for layer, distance in scores.items()),
        key=lambda item: (item[1], item[0]),
    )
    if not ranked:
        return {
            "base_top_layer": None,
            "base_top_distance": None,
            "base_second_distance": None,
            "base_distance_margin": None,
        }
    second = ranked[1][1] if len(ranked) > 1 else None
    margin = None if second is None else round(second - ranked[0][1], 6)
    return {
        "base_top_layer": ranked[0][0],
        "base_top_distance": round(ranked[0][1], 6),
        "base_second_distance": round(second, 6) if second is not None else None,
        "base_distance_margin": margin,
    }


def _route_safety_flags(row: dict[str, Any]) -> list[str]:
    source = str(row["source_layer"])
    pred = str(row["pred_layer"])
    area_frac = float(row.get("area_frac") or 0.0)
    margin = row.get("base_distance_margin")
    margin_value = float(margin) if margin is not None else None
    flags: list[str] = []

    if source != "numbers" and pred == "numbers":
        flags.append("number_promotion")
    if source == "numbers" and pred != "numbers":
        flags.append("number_demotion")
    if source == "paint" and pred != "paint":
        flags.append("paint_extraction")
    if source != "paint" and pred == "paint":
        flags.append("paint_absorption")
    if source == "template" or pred == "template":
        flags.append("template_transition")
    if area_frac >= 0.02:
        flags.append("large_area")
    elif area_frac >= 0.005:
        flags.append("medium_area")
    if margin_value is not None and margin_value <= 0.25 and not row.get("rule_override"):
        flags.append("low_margin")
    if row.get("rule_override"):
        flags.append("rule_override")
    return flags


def _route_priority(row: dict[str, Any]) -> float:
    flags = set(row.get("route_safety_flags") or [])
    priority = float(row.get("area_px") or 0.0)
    if "number_promotion" in flags:
        priority += 80000.0
    if "number_demotion" in flags:
        priority += 70000.0
    if "paint_extraction" in flags or "paint_absorption" in flags:
        priority += 45000.0
    if "template_transition" in flags:
        priority += 25000.0
    if "large_area" in flags:
        priority += 25000.0
    elif "medium_area" in flags:
        priority += 10000.0
    if "low_margin" in flags:
        priority += 5000.0
    return round(priority, 3)


def _summarize_route_safety(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    moves = [row for row in predictions if row["would_move"]]

    def area_sum(rows: list[dict[str, Any]]) -> float:
        return round(sum(float(row.get("area_frac") or 0.0) for row in rows), 6)

    number_promotions = [row for row in moves if "number_promotion" in row.get("route_safety_flags", [])]
    number_demotions = [row for row in moves if "number_demotion" in row.get("route_safety_flags", [])]
    paint_transitions = [
        row for row in moves
        if "paint_extraction" in row.get("route_safety_flags", [])
        or "paint_absorption" in row.get("route_safety_flags", [])
    ]
    template_transitions = [row for row in moves if "template_transition" in row.get("route_safety_flags", [])]
    low_margin = [row for row in moves if "low_margin" in row.get("route_safety_flags", [])]
    large_area = [row for row in moves if "large_area" in row.get("route_safety_flags", [])]
    by_paint: dict[str, list[dict[str, Any]]] = {}
    for row in moves:
        by_paint.setdefault(str(row.get("paint_label") or "unknown"), []).append(row)

    blockers: list[str] = []
    if area_sum(moves) >= 0.10:
        blockers.append("total_move_area_over_10pct")
    if len(number_promotions) >= 6 or area_sum(number_promotions) >= 0.05:
        blockers.append("broad_number_promotions")
    if len(number_demotions) >= 6 or area_sum(number_demotions) >= 0.05:
        blockers.append("broad_number_demotions")
    if len(paint_transitions) >= 8 or area_sum(paint_transitions) >= 0.05:
        blockers.append("broad_paint_transitions")
    if large_area:
        blockers.append("large_area_moves_present")
    if len(low_margin) >= 10:
        blockers.append("many_low_margin_moves")

    return {
        "runtime_safe_claim": False,
        "route_risk_level": "high" if blockers else ("medium" if moves else "low"),
        "route_blockers": blockers,
        "runtime_note": (
            "Offline route-wide diagnostic only. A reviewed component policy can look "
            "good on labeled rows while still over-moving unlabeled route components; "
            "inspect these sheets before any Auto-build hook."
        ),
        "components": len(predictions),
        "move_candidates": len(moves),
        "move_area_frac_sum": area_sum(moves),
        "move_counts": dict(Counter(f"{row['source_layer']}->{row['pred_layer']}" for row in moves)),
        "flag_counts": dict(Counter(flag for row in moves for flag in row.get("route_safety_flags", []))),
        "number_promotions": {
            "count": len(number_promotions),
            "area_frac_sum": area_sum(number_promotions),
            "record_ids": [int(row["record_id"]) for row in number_promotions],
        },
        "number_demotions": {
            "count": len(number_demotions),
            "area_frac_sum": area_sum(number_demotions),
            "record_ids": [int(row["record_id"]) for row in number_demotions],
        },
        "paint_transitions": {
            "count": len(paint_transitions),
            "area_frac_sum": area_sum(paint_transitions),
            "record_ids": [int(row["record_id"]) for row in paint_transitions],
        },
        "template_transitions": {
            "count": len(template_transitions),
            "area_frac_sum": area_sum(template_transitions),
            "record_ids": [int(row["record_id"]) for row in template_transitions],
        },
        "low_margin_moves": {
            "count": len(low_margin),
            "record_ids": [int(row["record_id"]) for row in low_margin],
        },
        "large_area_moves": {
            "count": len(large_area),
            "record_ids": [int(row["record_id"]) for row in large_area],
        },
        "by_paint": {
            paint: {
                "moves": len(rows),
                "move_area_frac_sum": area_sum(rows),
                "number_promotions": sum(1 for row in rows if "number_promotion" in row.get("route_safety_flags", [])),
                "number_demotions": sum(1 for row in rows if "number_demotion" in row.get("route_safety_flags", [])),
                "paint_transitions": sum(
                    1 for row in rows
                    if "paint_extraction" in row.get("route_safety_flags", [])
                    or "paint_absorption" in row.get("route_safety_flags", [])
                ),
            }
            for paint, rows in sorted(by_paint.items())
        },
        "top_priority_moves": [
            {
                "record_id": int(row["record_id"]),
                "paint_label": row.get("paint_label"),
                "source_layer": row["source_layer"],
                "pred_layer": row["pred_layer"],
                "area_frac": row.get("area_frac"),
                "area_px": row.get("area_px"),
                "bbox": row.get("bbox"),
                "role_guess": row.get("role_guess"),
                "rule_override": row.get("rule_override"),
                "base_distance_margin": row.get("base_distance_margin"),
                "route_safety_flags": row.get("route_safety_flags"),
                "route_priority": row.get("route_priority"),
            }
            for row in sorted(moves, key=lambda item: (-float(item.get("route_priority") or 0.0), int(item["record_id"])))[:40]
        ],
    }


def _write_safety_sheet(rows: list[dict[str, Any]], path: Path, title: str) -> str | None:
    if not rows:
        return None
    cols = 4
    cell_w = 292
    cell_h = 250
    rows_n = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, max(1, rows_n) * cell_h), (242, 242, 242))
    draw = ImageDraw.Draw(sheet)
    for idx, row in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        crop_path = row.get("crop_file")
        if crop_path and Path(crop_path).exists():
            img = Image.open(crop_path).convert("RGB")
            img.thumbnail((248, 150), Image.Resampling.LANCZOS)
            sheet.paste(img, (x + 20, y + 10))
        flags = ",".join(row.get("route_safety_flags") or [])
        label = f"{row['source_layer']} -> {row['pred_layer']} pr={row.get('route_priority')}"
        detail = f"area={float(row.get('area_frac') or 0.0):.5f} margin={row.get('base_distance_margin')}"
        draw.text((x + 6, y + 164), label[:46], fill=(0, 0, 0))
        draw.text((x + 6, y + 180), flags[:48], fill=(150, 40, 0))
        if row.get("rule_override"):
            draw.text((x + 6, y + 196), str(row["rule_override"])[:48], fill=(0, 80, 150))
        else:
            draw.text((x + 6, y + 196), str(row.get("role_guess") or "")[:48], fill=(80, 80, 80))
        draw.text((x + 6, y + 212), detail[:48], fill=(80, 80, 80))
        draw.text((x + 6, y + 228), f"id={row['record_id']} bbox={row.get('bbox')}", fill=(80, 80, 80))
    draw.rectangle((0, 0, min(sheet.width, len(title) * 7 + 20), 20), fill=(30, 30, 30))
    draw.text((8, 4), title[:110], fill=(255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.resolve())


def _policy_predictions(predictions: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in predictions:
        item = dict(row)
        item["policy_base_pred_layer"] = row["pred_layer"]
        if policy == "staged_number":
            final_layer = _staged_number_final_layer(row)
        elif policy == "staged_editable":
            final_layer = _staged_editable_final_layer(row)
        else:
            raise ValueError(f"unknown policy {policy}")
        item["pred_layer"] = final_layer
        item["would_move"] = final_layer != item["source_layer"]
        item["route_safety_flags"] = _route_safety_flags(item) if item["would_move"] else []
        item["route_priority"] = _route_priority(item) if item["would_move"] else 0.0
        out.append(item)
    return out


def _evaluate_review_labels(
    predictions: list[dict[str, Any]],
    review_targets: dict[tuple[str, int], dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in predictions:
        key = (str(row["source_layer"]), int(row["component_index"]))
        target = review_targets.get(key)
        if not target:
            continue
        number_prune_final = row["source_layer"]
        if row["source_layer"] == "numbers" and row["pred_layer"] != "numbers":
            number_prune_final = row["pred_layer"]
        selective_number_final = _selective_number_final_layer(row)
        staged_number_final = _staged_number_final_layer(row)
        staged_editable_final = _staged_editable_final_layer(row)
        rows.append({
            "record_id": row["record_id"],
            "component_index": row["component_index"],
            "source_layer": row["source_layer"],
            "target_layer": target["target_layer"],
            "label": target.get("label"),
            "pred_layer": row["pred_layer"],
            "full_move_final_layer": row["pred_layer"],
            "number_prune_final_layer": number_prune_final,
            "selective_number_final_layer": selective_number_final,
            "staged_number_final_layer": staged_number_final,
            "staged_editable_final_layer": staged_editable_final,
            "bbox": row.get("bbox"),
            "rule_override": row.get("rule_override"),
        })
    summary = {
        "labeled_components": len(rows),
        "full_move": _score_policy(rows, "full_move"),
        "number_prune": _score_policy(rows, "number_prune"),
        "selective_number": _score_policy(rows, "selective_number"),
        "staged_number": _score_policy(rows, "staged_number"),
        "staged_editable": _score_policy(rows, "staged_editable"),
        "number_cleanup": {
            "full_move": _score_number_cleanup(rows, "full_move"),
            "number_prune": _score_number_cleanup(rows, "number_prune"),
            "selective_number": _score_number_cleanup(rows, "selective_number"),
            "staged_number": _score_number_cleanup(rows, "staged_number"),
            "staged_editable": _score_number_cleanup(rows, "staged_editable"),
        },
        "paint_sponsor_wordmarks": {
            "staged_number": _score_paint_sponsor_wordmarks(rows, "staged_number"),
            "staged_editable": _score_paint_sponsor_wordmarks(rows, "staged_editable"),
        },
    }
    return rows, summary


def _write_move_sheet(rows: list[dict[str, Any]], path: Path, title: str) -> str | None:
    if not rows:
        return None
    cols = 4
    cell_w = 260
    cell_h = 230
    rows_n = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, max(1, rows_n) * cell_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for idx, row in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        crop_path = row.get("crop_file")
        if crop_path and Path(crop_path).exists():
            img = Image.open(crop_path).convert("RGB")
            img.thumbnail((220, 150), Image.Resampling.LANCZOS)
            sheet.paste(img, (x + 20, y + 8))
        label = f"{row['source_layer']} -> {row['pred_layer']}"
        draw.text((x + 6, y + 164), label[:40], fill=(0, 0, 0))
        if row.get("rule_override"):
            draw.text((x + 6, y + 180), str(row["rule_override"])[:40], fill=(0, 80, 150))
        draw.text((x + 6, y + 196), str(row.get("role_guess") or row.get("label") or "")[:40], fill=(80, 80, 80))
        draw.text((x + 6, y + 212), f"id={row['record_id']} bbox={row.get('bbox')}", fill=(80, 80, 80))
    draw.text((8, 8), title[:80], fill=(255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return str(path.resolve())


def probe(args: argparse.Namespace) -> dict[str, Any]:
    reviewed = _read_json(_repo_path(args.reviewed_features))
    if not isinstance(reviewed, list):
        raise ValueError("reviewed feature bank must be a list")

    train_vectors_raw = [_feature_vector(row, include_source_layer=True) for row in reviewed]
    means, stds = _fit_scaler(train_vectors_raw)
    train_vectors = [_scale(vec, means, stds) for vec in train_vectors_raw]

    components = _load_rows(args.components)
    review_targets = _load_review_targets(args.labels)
    feature_quality = _summarize_feature_quality(components)
    predictions: list[dict[str, Any]] = []
    for idx, record in enumerate(components):
        source_layer = str(record.get("layer") or "unknown")
        missing_feature_keys = _missing_feature_keys(record)
        raw_vec = _feature_vector(record, include_source_layer=True)
        pred, scores = _nearest_centroid(reviewed, train_vectors, _scale(raw_vec, means, stds))
        ruled_pred, reason = _rule_override(record, pred)
        distance_summary = _distance_margin(scores)
        item = {
            "record_id": idx,
            "component_index": record.get("component_index"),
            "paint_label": record.get("paint_label"),
            "source_layer": source_layer,
            "pred_layer": ruled_pred,
            "base_pred_layer": pred,
            "rule_override": reason,
            "would_move": ruled_pred != source_layer,
            "bbox": record.get("bbox"),
            "area_px": record.get("area_px"),
            "area_frac": record.get("area_frac"),
            "aspect": record.get("aspect"),
            "fill": record.get("fill"),
            "mean_saturation": record.get("mean_saturation"),
            "mean_value": record.get("mean_value"),
            "edge_density": record.get("edge_density"),
            "color_std": record.get("color_std"),
            "role_guess": record.get("role_guess"),
            "crop_file": record.get("crop_file"),
            "feature_complete": not missing_feature_keys,
            "missing_feature_keys": missing_feature_keys,
            "scores": scores,
        }
        item.update(distance_summary)
        item["route_safety_flags"] = _route_safety_flags(item) if item["would_move"] else []
        item["route_priority"] = _route_priority(item) if item["would_move"] else 0.0
        predictions.append(item)

    out_dir = _repo_path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = out_dir / "component_classifier_predictions.json"
    predictions_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")

    move_candidates = [row for row in predictions if row["would_move"]]
    move_path = out_dir / "move_candidates.json"
    move_path.write_text(json.dumps(move_candidates, indent=2), encoding="utf-8")
    number_prune = _number_prune_candidates(predictions)
    number_prune_path = out_dir / "number_prune_candidates.json"
    number_prune_path.write_text(json.dumps(number_prune, indent=2), encoding="utf-8")
    review_rows, review_eval = _evaluate_review_labels(predictions, review_targets)
    review_eval_path = out_dir / "review_label_evaluation.json"
    review_eval_path.write_text(json.dumps({
        "summary": review_eval,
        "rows": review_rows,
    }, indent=2), encoding="utf-8")

    csv_path = out_dir / "component_classifier_predictions.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "record_id", "paint_label", "source_layer", "pred_layer", "base_pred_layer",
            "rule_override", "would_move", "bbox", "area_px", "area_frac", "aspect",
            "fill", "mean_saturation", "mean_value", "edge_density", "color_std", "role_guess",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in predictions:
            writer.writerow({key: row.get(key) for key in fieldnames})

    sheet_path = _write_move_sheet(
        move_candidates[: args.max_sheet],
        out_dir / "move_candidates.png",
        f"Smart TGA classifier probe moves ({len(move_candidates)} candidates)",
    )
    number_prune_sheet = _write_move_sheet(
        number_prune[: args.max_sheet],
        out_dir / "number_prune_candidates.png",
        f"Smart TGA Number-prune candidates ({len(number_prune)} candidates)",
    )
    route_safety = _summarize_route_safety(predictions)
    staged_predictions = _policy_predictions(predictions, "staged_number")
    staged_candidates = [row for row in staged_predictions if row["would_move"]]
    staged_path = out_dir / "staged_number_candidates.json"
    staged_path.write_text(json.dumps(staged_candidates, indent=2), encoding="utf-8")
    staged_route_safety = _summarize_route_safety(staged_predictions)
    staged_route_safety_path = out_dir / "staged_number_route_safety.json"
    staged_route_safety_path.write_text(json.dumps(staged_route_safety, indent=2), encoding="utf-8")
    editable_predictions = _policy_predictions(predictions, "staged_editable")
    editable_candidates = [row for row in editable_predictions if row["would_move"]]
    editable_path = out_dir / "staged_editable_candidates.json"
    editable_path.write_text(json.dumps(editable_candidates, indent=2), encoding="utf-8")
    editable_route_safety = _summarize_route_safety(editable_predictions)
    editable_route_safety_path = out_dir / "staged_editable_route_safety.json"
    editable_route_safety_path.write_text(json.dumps(editable_route_safety, indent=2), encoding="utf-8")
    safety_moves = sorted(
        move_candidates,
        key=lambda row: (-float(row.get("route_priority") or 0.0), int(row["record_id"])),
    )
    staged_safety_moves = sorted(
        staged_candidates,
        key=lambda row: (-float(row.get("route_priority") or 0.0), int(row["record_id"])),
    )
    editable_safety_moves = sorted(
        editable_candidates,
        key=lambda row: (-float(row.get("route_priority") or 0.0), int(row["record_id"])),
    )
    route_safety_path = out_dir / "route_move_safety.json"
    route_safety_path.write_text(json.dumps(route_safety, indent=2), encoding="utf-8")
    route_safety_sheet = _write_safety_sheet(
        safety_moves[: args.safety_top],
        out_dir / "route_move_safety_top.png",
        f"Route move safety top {min(args.safety_top, len(safety_moves))}/{len(safety_moves)}",
    )
    number_promotion_sheet = _write_safety_sheet(
        [row for row in safety_moves if "number_promotion" in row.get("route_safety_flags", [])][: args.safety_top],
        out_dir / "route_number_promotions.png",
        "Route safety Number promotions",
    )
    number_demotion_sheet = _write_safety_sheet(
        [row for row in safety_moves if "number_demotion" in row.get("route_safety_flags", [])][: args.safety_top],
        out_dir / "route_number_demotions.png",
        "Route safety Number demotions",
    )
    paint_transition_sheet = _write_safety_sheet(
        [
            row for row in safety_moves
            if "paint_extraction" in row.get("route_safety_flags", [])
            or "paint_absorption" in row.get("route_safety_flags", [])
        ][: args.safety_top],
        out_dir / "route_paint_transitions.png",
        "Route safety Paint transitions",
    )
    staged_safety_sheet = _write_safety_sheet(
        staged_safety_moves[: args.safety_top],
        out_dir / "staged_number_route_safety_top.png",
        f"Staged Number safety top {min(args.safety_top, len(staged_safety_moves))}/{len(staged_safety_moves)}",
    )
    staged_promotion_sheet = _write_safety_sheet(
        [row for row in staged_safety_moves if "number_promotion" in row.get("route_safety_flags", [])][: args.safety_top],
        out_dir / "staged_number_promotions.png",
        "Staged Number promotions",
    )
    editable_safety_sheet = _write_safety_sheet(
        editable_safety_moves[: args.safety_top],
        out_dir / "staged_editable_route_safety_top.png",
        f"Staged Editable safety top {min(args.safety_top, len(editable_safety_moves))}/{len(editable_safety_moves)}",
    )
    editable_paint_sponsor_sheet = _write_safety_sheet(
        [
            row for row in editable_safety_moves
            if row["source_layer"] == "paint" and row["pred_layer"] == "sponsors"
        ][: args.safety_top],
        out_dir / "staged_editable_paint_sponsors.png",
        "Staged Editable Paint-origin sponsor fragments",
    )

    summary = {
        "reviewed_features": str(_repo_path(args.reviewed_features).resolve()),
        "component_records": [str(_repo_path(path).resolve()) for path in args.components],
        "components": len(predictions),
        "move_candidates": len(move_candidates),
        "source_layer_counts": dict(Counter(row["source_layer"] for row in predictions)),
        "pred_layer_counts": dict(Counter(row["pred_layer"] for row in predictions)),
        "move_counts": dict(Counter(f"{row['source_layer']}->{row['pred_layer']}" for row in move_candidates)),
        "rule_counts": dict(Counter(str(row["rule_override"]) for row in predictions if row.get("rule_override"))),
        "feature_quality": feature_quality,
        "number_prune_policy": _summarize_number_prune_policy(predictions),
        "selective_number_policy": _summarize_selective_number_policy(predictions),
        "staged_number_policy": _summarize_staged_number_policy(predictions),
        "staged_editable_policy": _summarize_staged_editable_policy(predictions),
        "route_move_safety": route_safety,
        "staged_number_route_safety": staged_route_safety,
        "staged_editable_route_safety": editable_route_safety,
        "review_label_evaluation": review_eval if review_targets else None,
        "pressure_test_status": (
            "feature_complete"
            if feature_quality["safe_for_move_decisions"]
            else "stale_component_records_missing_features"
        ),
        "predictions": str(predictions_path.resolve()),
        "move_candidates_json": str(move_path.resolve()),
        "move_candidates_csv": str(csv_path.resolve()),
        "move_candidates_sheet": sheet_path,
        "number_prune_candidates_json": str(number_prune_path.resolve()),
        "number_prune_candidates_sheet": number_prune_sheet,
        "route_move_safety_json": str(route_safety_path.resolve()),
        "route_move_safety_sheet": route_safety_sheet,
        "route_number_promotions_sheet": number_promotion_sheet,
        "route_number_demotions_sheet": number_demotion_sheet,
        "route_paint_transitions_sheet": paint_transition_sheet,
        "staged_number_candidates_json": str(staged_path.resolve()),
        "staged_number_route_safety_json": str(staged_route_safety_path.resolve()),
        "staged_number_route_safety_sheet": staged_safety_sheet,
        "staged_number_promotions_sheet": staged_promotion_sheet,
        "staged_editable_candidates_json": str(editable_path.resolve()),
        "staged_editable_route_safety_json": str(editable_route_safety_path.resolve()),
        "staged_editable_route_safety_sheet": editable_safety_sheet,
        "staged_editable_paint_sponsors_sheet": editable_paint_sponsor_sheet,
        "review_label_evaluation_json": str(review_eval_path.resolve()) if review_targets else None,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed-features", required=True)
    parser.add_argument("--components", action="append", required=True)
    parser.add_argument("--labels", help="Optional reviewed component label map for policy scoring")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-sheet", type=int, default=80)
    parser.add_argument("--safety-top", type=int, default=80)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(probe(parse_args()), indent=2))


if __name__ == "__main__":
    main()
