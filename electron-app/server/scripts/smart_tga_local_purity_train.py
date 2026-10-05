"""Train/evaluate a paint-disjoint Smart TGA local proposal-purity scorer.

The scorer consumes only intrinsic candidate/support, visual-semantic and
candidate/context conflict evidence.  Paint filename, car family, coordinates,
legacy owners and template-position priors are deliberately excluded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = (
    "probability",
    "intrinsic_fill_ratio",
    "intrinsic_log_orientation_free_aspect",
    "edge_density",
    "strong_gradient_fraction",
    "texture_entropy",
    "family_log_member_count",
    "family_shape_instability",
    "family_texture_instability",
    "family_palette_instability",
    "support_log_component_count",
    "support_largest_component_fraction",
    "support_component_area_entropy",
    "proposal_smaller_peer_containment",
    "proposal_smaller_peer_area_ratio",
    "proposal_overlap_count_log",
    "clip_digit_evidence",
    "clip_alpha_evidence",
    "clip_graphic_evidence",
    "clip_digit_minus_alpha_margin",
    "clip_digit_minus_all_negative_margin",
    "context_clip_digit_evidence",
    "context_clip_alpha_evidence",
    "context_clip_graphic_evidence",
    "context_clip_digit_minus_all_negative_margin",
    "context_minus_candidate_digit",
    "context_minus_candidate_alpha",
    "context_minus_candidate_graphic",
    "peer_d4_similarity",
    "ocr_alpha_family_coverage",
    "ocr_digit_family_coverage",
    "local_ocr_token_count_log",
    "local_ocr_alpha_character_count_log",
    "local_ocr_weighted_alpha_confidence",
    "local_ocr_short_alpha_confidence",
    "local_ocr_long_alpha_confidence",
    "local_ocr_multitoken_short_alpha_conflict",
)

PURITY_CORE_FEATURES = (
    "probability",
    "intrinsic_fill_ratio",
    "intrinsic_log_orientation_free_aspect",
    "edge_density",
    "strong_gradient_fraction",
    "texture_entropy",
    "support_log_component_count",
    "support_largest_component_fraction",
    "support_component_area_entropy",
    "proposal_smaller_peer_containment",
    "proposal_smaller_peer_area_ratio",
    "proposal_overlap_count_log",
)
SEMANTIC_COMPACT_FEATURES = PURITY_CORE_FEATURES + (
    "clip_digit_minus_alpha_margin",
    "clip_digit_minus_all_negative_margin",
    "context_clip_digit_minus_all_negative_margin",
    "context_minus_candidate_digit",
    "context_minus_candidate_alpha",
    "context_minus_candidate_graphic",
    "peer_d4_similarity",
    "ocr_alpha_family_coverage",
    "ocr_digit_family_coverage",
    "local_ocr_token_count_log",
    "local_ocr_alpha_character_count_log",
    "local_ocr_weighted_alpha_confidence",
    "local_ocr_short_alpha_confidence",
    "local_ocr_long_alpha_confidence",
    "local_ocr_multitoken_short_alpha_conflict",
)
LEGACY_V1_FEATURES = tuple(
    name for name in FEATURE_NAMES
    if not name.startswith("support_") and not name.startswith("proposal_")
)
FEATURE_SETS = {
    "purity_core": PURITY_CORE_FEATURES,
    "semantic_compact": SEMANTIC_COMPACT_FEATURES,
    "legacy_v1": LEGACY_V1_FEATURES,
    "full": FEATURE_NAMES,
}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", action="append", required=True)
    parser.add_argument("--labels", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--allow-unreviewed-runtime", action="store_true",
        help="Skip probe-only paints that active learning did not select for review.",
    )
    return parser.parse_args()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _label_index(paths: Iterable[str]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path in paths:
        for item in _load_json(path)["candidate_labels"]:
            key = (str(item["paint"]), str(item["family_id"]))
            if key in result:
                raise ValueError(f"duplicate reviewed candidate: {key}")
            result[key] = item
    return result


def _feature_row(row: dict[str, Any]) -> list[float]:
    intrinsic = row.get("intrinsic_purity_features") or {}
    candidate_digit = float(row.get("clip_digit_evidence", 0.0))
    candidate_alpha = float(row.get("clip_alpha_evidence", 0.0))
    candidate_graphic = float(row.get("clip_graphic_evidence", 0.0))
    context_digit = float(row.get("context_clip_digit_evidence", 0.0))
    context_alpha = float(row.get("context_clip_alpha_evidence", 0.0))
    context_graphic = float(row.get("context_clip_graphic_evidence", 0.0))
    ocr_tokens = list(row.get("local_ocr_tokens") or ())
    alpha_characters = np.asarray([
        max(0, int(token.get("alpha_characters", 0))) for token in ocr_tokens
    ], np.float64)
    token_confidence = np.asarray([
        max(0.0, float(token.get("confidence", 0.0))) for token in ocr_tokens
    ], np.float64)
    alpha_total = float(np.sum(alpha_characters))
    short_alpha = (
        token_confidence[(alpha_characters > 0) & (alpha_characters <= 3)]
        if len(ocr_tokens) else np.asarray([], np.float64)
    )
    values = {
        "probability": row.get("probability", 0.0),
        "intrinsic_fill_ratio": row.get("intrinsic_fill_ratio", 0.0),
        "intrinsic_log_orientation_free_aspect": row.get(
            "intrinsic_log_orientation_free_aspect", 0.0,
        ),
        **{name: intrinsic.get(name, 0.0) for name in (
            "edge_density", "strong_gradient_fraction", "texture_entropy",
            "family_log_member_count", "family_shape_instability",
            "family_texture_instability", "family_palette_instability",
            "support_log_component_count",
            "support_largest_component_fraction",
            "support_component_area_entropy",
            "proposal_smaller_peer_containment",
            "proposal_smaller_peer_area_ratio",
            "proposal_overlap_count_log",
        )},
        "clip_digit_evidence": candidate_digit,
        "clip_alpha_evidence": candidate_alpha,
        "clip_graphic_evidence": candidate_graphic,
        "clip_digit_minus_alpha_margin": row.get("clip_digit_minus_alpha_margin", 0.0),
        "clip_digit_minus_all_negative_margin": row.get(
            "clip_digit_minus_all_negative_margin", 0.0,
        ),
        "context_clip_digit_evidence": context_digit,
        "context_clip_alpha_evidence": context_alpha,
        "context_clip_graphic_evidence": context_graphic,
        "context_clip_digit_minus_all_negative_margin": row.get(
            "context_clip_digit_minus_all_negative_margin", 0.0,
        ),
        "context_minus_candidate_digit": context_digit - candidate_digit,
        "context_minus_candidate_alpha": context_alpha - candidate_alpha,
        "context_minus_candidate_graphic": context_graphic - candidate_graphic,
        "peer_d4_similarity": row.get("peer_d4_similarity", 0.0),
        "ocr_alpha_family_coverage": row.get("ocr_alpha_family_coverage", 0.0),
        "ocr_digit_family_coverage": row.get("ocr_digit_family_coverage", 0.0),
        "local_ocr_token_count_log": np.log1p(len(ocr_tokens)),
        "local_ocr_alpha_character_count_log": np.log1p(alpha_total),
        "local_ocr_weighted_alpha_confidence": (
            float(np.sum(token_confidence * alpha_characters) / alpha_total)
            if alpha_total else 0.0
        ),
        "local_ocr_short_alpha_confidence": (
            float(np.max(short_alpha)) if len(short_alpha) else 0.0
        ),
        "local_ocr_long_alpha_confidence": row.get(
            "local_ocr_max_alpha_confidence", 0.0,
        ),
        "local_ocr_multitoken_short_alpha_conflict": (
            float(np.max(short_alpha)) * max(0, len(ocr_tokens) - 2)
            if len(short_alpha) else 0.0
        ),
    }
    return [float(values[name]) for name in FEATURE_NAMES]


def _dataset(
    runtime_paths: Iterable[str], labels: dict[tuple[str, str], dict[str, Any]],
    *, allow_unreviewed: bool = False,
):
    features, truth, groups, eligible, records = [], [], [], [], []
    seen: set[tuple[str, str]] = set()
    for path in runtime_paths:
        runtime = _load_json(path)
        for paint in runtime["records"]:
            paint_label = str(paint["paint_label"])
            for row in paint["local_candidates"]:
                key = (paint_label, str(row["family_id"]))
                label = labels.get(key)
                if label is None:
                    if allow_unreviewed:
                        continue
                    raise ValueError(f"runtime candidate has no durable review: {key}")
                if key in seen:
                    raise ValueError(f"runtime candidate repeated: {key}")
                seen.add(key)
                semantic = str(label["semantic"])
                features.append(_feature_row(row))
                truth.append(semantic == "Number")
                groups.append(paint_label)
                eligible.append(bool(row["accepted"]))
                records.append({
                    "paint": paint_label,
                    "family_id": row["family_id"],
                    "semantic": semantic,
                    "current_accepted": bool(row["accepted"]),
                    "complete_copy": bool(label.get("complete_copy", False)),
                    "physical_copy": label.get("physical_copy"),
                })
    missing = sorted(set(labels) - seen)
    if missing:
        raise ValueError(f"{len(missing)} reviewed candidates absent from runtimes")
    matrix = np.asarray(features, np.float64)
    if matrix.shape != (len(records), len(FEATURE_NAMES)) or not np.isfinite(matrix).all():
        raise ValueError("invalid purity feature matrix")
    return (
        matrix,
        np.asarray(truth, bool),
        np.asarray(groups, object),
        np.asarray(eligible, bool),
        records,
    )


def _fit(x: np.ndarray, y: np.ndarray, c_value: float):
    scaler = StandardScaler().fit(x)
    model = LogisticRegression(
        C=c_value, class_weight="balanced", max_iter=5000,
        solver="liblinear", random_state=718,
    ).fit(scaler.transform(x), y)
    return scaler, model


def _predict(fitted, x: np.ndarray) -> np.ndarray:
    scaler, model = fitted
    return model.predict_proba(scaler.transform(x))[:, 1]


def _zero_negative_threshold(
    probability: np.ndarray, truth: np.ndarray, eligible: np.ndarray | None = None,
) -> float:
    relevant = np.ones(len(truth), bool) if eligible is None else eligible
    negatives = probability[~truth & relevant]
    # A fold can contain no post-gate negative.  In that case all reviewed
    # negatives remain a conservative calibration fallback.
    if not len(negatives) and eligible is not None:
        negatives = probability[~truth]
    if not len(negatives):
        return 0.5
    return float(np.nextafter(float(np.max(negatives)), np.inf))


def _logo_probabilities(x: np.ndarray, y: np.ndarray, groups: np.ndarray, c_value: float):
    result = np.zeros(len(y), np.float64)
    for train, test in LeaveOneGroupOut().split(x, y, groups):
        result[test] = _predict(_fit(x[train], y[train], c_value), x[test])
    return result


def _feature_indices(names: Iterable[str]) -> np.ndarray:
    return np.asarray([FEATURE_NAMES.index(name) for name in names], np.int64)


def _select_model(
    x: np.ndarray, y: np.ndarray, groups: np.ndarray, eligible: np.ndarray,
):
    candidates = []
    for feature_set, names in FEATURE_SETS.items():
        indices = _feature_indices(names)
        for c_value in (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0):
            probability = _logo_probabilities(x[:, indices], y, groups, c_value)
            threshold = _zero_negative_threshold(probability, y, eligible)
            accepted = probability >= threshold
            candidates.append({
                "feature_set": feature_set,
                "feature_names": names,
                "feature_indices": indices,
                "c": c_value,
                "probability": probability,
                "threshold": threshold,
                "positive_accepts": int(np.sum(accepted & y & eligible)),
                "negative_accepts": int(np.sum(accepted & ~y & eligible)),
                "average_precision": float(average_precision_score(y, probability)),
            })
    best = max(
        candidates,
        key=lambda item: (
            item["positive_accepts"], item["average_precision"],
            -len(item["feature_names"]), -item["c"],
        ),
    )
    return best, candidates


def _nested_group_predictions(
    x: np.ndarray, y: np.ndarray, groups: np.ndarray, eligible: np.ndarray,
):
    probability = np.zeros(len(y), np.float64)
    accepted = np.zeros(len(y), bool)
    folds = []
    for outer_train, outer_test in LeaveOneGroupOut().split(x, y, groups):
        best, _candidates = _select_model(
            x[outer_train], y[outer_train], groups[outer_train],
            eligible[outer_train],
        )
        indices = best["feature_indices"]
        fitted = _fit(
            x[outer_train][:, indices], y[outer_train], float(best["c"]),
        )
        probability[outer_test] = _predict(fitted, x[outer_test][:, indices])
        accepted[outer_test] = probability[outer_test] >= float(best["threshold"])
        folds.append({
            "held_out_paint": str(groups[outer_test][0]),
            "feature_set": str(best["feature_set"]),
            "c": float(best["c"]),
            "threshold": float(best["threshold"]),
            "accepted_positive": int(np.sum(
                accepted[outer_test] & y[outer_test] & eligible[outer_test]
            )),
            "accepted_negative": int(np.sum(
                accepted[outer_test] & ~y[outer_test] & eligible[outer_test]
            )),
        })
    return probability, accepted, folds


def _metrics(accepted: np.ndarray, truth: np.ndarray, eligible: np.ndarray):
    final = accepted & eligible
    positive_total = int(np.sum(truth & eligible))
    return {
        "eligible_candidates": int(np.sum(eligible)),
        "eligible_positive": positive_total,
        "eligible_negative": int(np.sum(~truth & eligible)),
        "accepted_positive": int(np.sum(final & truth)),
        "accepted_negative": int(np.sum(final & ~truth)),
        "positive_recall": float(np.sum(final & truth) / max(1, positive_total)),
        "precision": float(np.sum(final & truth) / max(1, np.sum(final))),
    }


def main() -> None:
    args = _arguments()
    labels = _label_index(args.labels)
    x, y, groups, eligible, records = _dataset(
        args.runtime, labels, allow_unreviewed=args.allow_unreviewed_runtime,
    )
    nested_probability, nested_accept, folds = _nested_group_predictions(
        x, y, groups, eligible,
    )
    best, candidates = _select_model(x, y, groups, eligible)
    selected_indices = best["feature_indices"]
    fitted = _fit(x[:, selected_indices], y, float(best["c"]))
    scaler, model = fitted
    model_path = Path(args.model)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_path,
        schema=np.asarray(["smart-tga-local-purity-linear-v1"]),
        feature_names=np.asarray(best["feature_names"]),
        mean=scaler.mean_.astype(np.float32),
        scale=scaler.scale_.astype(np.float32),
        coefficient=model.coef_[0].astype(np.float32),
        intercept=np.asarray(model.intercept_, np.float32),
        threshold=np.asarray([best["threshold"]], np.float32),
        c=np.asarray([best["c"]], np.float32),
    )
    report = {
        "schema": "smart-tga-local-purity-training-report-v1",
        "candidate_count": len(records),
        "paint_count": len(set(groups.tolist())),
        "positive_number_candidates": int(np.sum(y)),
        "negative_or_uncertain_candidates": int(np.sum(~y)),
        "feature_names": list(FEATURE_NAMES),
        "forbidden_authority_features": [],
        "current_gate": _metrics(np.ones(len(y), bool), y, eligible),
        "nested_paint_disjoint_gate": _metrics(nested_accept, y, eligible),
        "nested_all_candidate_auc": float(roc_auc_score(y, nested_probability)),
        "nested_all_candidate_average_precision": float(
            average_precision_score(y, nested_probability)
        ),
        "nested_folds": folds,
        "final_model": {
            "feature_set": str(best["feature_set"]),
            "feature_names": list(best["feature_names"]),
            "c": float(best["c"]),
            "threshold": float(best["threshold"]),
            "eligible_positive_accepts_at_zero_negative_threshold": int(
                best["positive_accepts"]
            ),
            "eligible_negative_accepts_at_threshold": int(best["negative_accepts"]),
            "model_path": str(model_path),
        },
        "candidate_search": [{
            "feature_set": str(item["feature_set"]),
            "feature_count": len(item["feature_names"]),
            "c": float(item["c"]),
            "threshold": float(item["threshold"]),
            "positive_accepts": int(item["positive_accepts"]),
            "negative_accepts": int(item["negative_accepts"]),
            "average_precision": float(item["average_precision"]),
        } for item in candidates],
        "records": [{
            **record,
            "nested_probability": round(float(probability), 6),
            "nested_purity_accepted": bool(accept),
            "nested_final_accepted": bool(accept and current),
        } for record, probability, accept, current in zip(
            records, nested_probability, nested_accept, eligible,
        )],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "candidate_count": report["candidate_count"],
        "current_gate": report["current_gate"],
        "nested_paint_disjoint_gate": report["nested_paint_disjoint_gate"],
        "final_model": report["final_model"],
    }, indent=2))


if __name__ == "__main__":
    main()
