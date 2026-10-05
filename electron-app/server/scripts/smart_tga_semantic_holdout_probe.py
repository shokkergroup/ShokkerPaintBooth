"""Paint-stratified offline probe for reviewed Smart TGA semantic objects.

The probe measures whether intrinsic object evidence generalizes to unseen
paint files.  Scores are diagnostic only: they are not probability-calibrated,
cast no votes, and have no runtime ownership authority.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


CLASSES = ("numbers", "sponsors", "template", "paint")
BASE_FEATURES = (
    "member_count", "area_fraction", "bbox_fraction", "fill_ratio", "aspect_ratio",
    "mean_edge_density", "max_edge_density", "mean_texture_entropy", "max_texture_entropy",
    "max_ocr_coverage", "max_digit_coverage", "palette_role_count", "palette_role_entropy",
    "lightness_span", "chroma_span", "proposed_owner_count", "number_member_fraction",
    "sponsor_member_fraction", "template_member_fraction", "brand_graphics_member_fraction",
    "proposal_conflict_fraction", "cross_owner",
)
POSITION_FEATURES = (
    "bbox_x_fraction", "bbox_y_fraction", "bbox_width_fraction", "bbox_height_fraction",
    "border_distance_fraction",
)
LEGACY_PROVENANCE_FEATURES = (
    "candidate_count", "source_stage_count", "source_count", "merge_reason_count",
    "gpu_model_member_fraction", "template_raw_member_fraction", "multi_proposal_member_fraction",
)
ASSEMBLY_PROVENANCE_FEATURES = (
    "physical_group_indicator", "candidate_member_ratio", "candidate_member_excess",
)
INSTANCE_ORIGIN_FEATURES = (
    "instance_origin_feature_available", "appearance_quantized_instance_fraction",
    "unassigned_instance_fraction", "appearance_unassigned_instance_fraction",
)
CROSS_COPY_FEATURES = (
    "cross_copy_max_similarity", "cross_copy_shape_similarity",
    "cross_copy_palette_similarity", "cross_copy_peer_count_070",
    "cross_copy_mean_top3_similarity",
)
CROSS_COPY_PROPOSAL_ANCHOR_FEATURES = (
    "cross_copy_number_anchor_max_similarity", "cross_copy_number_anchor_peer_count_070",
    "cross_copy_sponsor_anchor_max_similarity", "cross_copy_sponsor_anchor_peer_count_070",
    "cross_copy_template_anchor_max_similarity", "cross_copy_template_anchor_peer_count_070",
)
COMPLETION_FEATURES = (
    "completion_feature_available", "largest_member_fraction",
    "smallest_member_fraction", "member_area_balance", "member_fragmentation",
)
DOMINANT_MEMBER_FEATURES = ("largest_member_fraction",)
GROUP_COMPLETION_FEATURES = (
    "physical_group_indicator", "group_completion_feature_available",
    "group_largest_member_fraction", "group_smallest_member_fraction",
    "group_member_area_balance", "group_member_fragmentation",
)
GROUP_DOMINANT_MEMBER_FEATURES = (
    "physical_group_indicator", "group_largest_member_fraction",
)
PROVENANCE_FEATURES = LEGACY_PROVENANCE_FEATURES
INTRINSIC_FEATURES = (
    "mean_strong_gradient_fraction", "max_strong_gradient_fraction",
    "max_ocr_alpha_coverage", "max_ocr_token_count",
    "mean_perceptual_lightness", "mean_perceptual_chroma",
)
TOPOLOGY_FEATURES = (
    "topology_component_count", "topology_largest_component_fraction",
    "topology_hole_count", "topology_boundary_fraction",
    "topology_full_row_fraction", "topology_full_column_fraction",
    "topology_rectangular_component_fraction",
)
GEOMETRY_FEATURES = (
    "geometry_hu_log_1", "geometry_hu_log_2", "geometry_hu_log_3",
    "geometry_hu_log_4", "geometry_hu_log_5", "geometry_hu_log_6",
    "geometry_hu_log_7", "geometry_solidity", "geometry_perimeter_sqrt_area",
    "geometry_compactness", "geometry_horizontal_symmetry",
    "geometry_vertical_symmetry", "geometry_thickness_mean", "geometry_thickness_max",
)
FEATURE_SETS = {
    "legacy": BASE_FEATURES,
    "position": BASE_FEATURES + POSITION_FEATURES,
    "provenance": BASE_FEATURES + PROVENANCE_FEATURES,
    "provenance_position": BASE_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES,
    "intrinsic": BASE_FEATURES + INTRINSIC_FEATURES,
    "topology": BASE_FEATURES + TOPOLOGY_FEATURES,
    "geometry": BASE_FEATURES + TOPOLOGY_FEATURES + GEOMETRY_FEATURES,
    "geometry_position": (
        BASE_FEATURES + TOPOLOGY_FEATURES + GEOMETRY_FEATURES + POSITION_FEATURES
    ),
    "geometry_provenance_position": (
        BASE_FEATURES + TOPOLOGY_FEATURES + GEOMETRY_FEATURES
        + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "topology_provenance_position": (
        BASE_FEATURES + TOPOLOGY_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_assembly_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + PROVENANCE_FEATURES + ASSEMBLY_PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_instance_origin_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + PROVENANCE_FEATURES + INSTANCE_ORIGIN_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_cross_copy_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + CROSS_COPY_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_cross_copy_anchor_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + CROSS_COPY_FEATURES + CROSS_COPY_PROPOSAL_ANCHOR_FEATURES
        + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_instance_origin_cross_copy_anchor_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + INSTANCE_ORIGIN_FEATURES + CROSS_COPY_FEATURES
        + CROSS_COPY_PROPOSAL_ANCHOR_FEATURES
        + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_completion_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + COMPLETION_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_dominant_member_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + DOMINANT_MEMBER_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_group_completion_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + GROUP_COMPLETION_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_group_dominant_member_provenance_position": (
        BASE_FEATURES + INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + GROUP_DOMINANT_MEMBER_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
}

OPTIONAL_FEATURE_REQUIREMENTS = {
    "position": POSITION_FEATURES,
    "provenance": PROVENANCE_FEATURES,
    "provenance_position": PROVENANCE_FEATURES + POSITION_FEATURES,
    "intrinsic": INTRINSIC_FEATURES,
    "topology": TOPOLOGY_FEATURES,
    "geometry": TOPOLOGY_FEATURES + GEOMETRY_FEATURES,
    "geometry_position": TOPOLOGY_FEATURES + GEOMETRY_FEATURES + POSITION_FEATURES,
    "geometry_provenance_position": (
        TOPOLOGY_FEATURES + GEOMETRY_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "topology_provenance_position": TOPOLOGY_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES,
    "intrinsic_provenance_position": (
        INTRINSIC_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_assembly_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + PROVENANCE_FEATURES + ASSEMBLY_PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_instance_origin_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + PROVENANCE_FEATURES + INSTANCE_ORIGIN_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_cross_copy_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + CROSS_COPY_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_cross_copy_anchor_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + CROSS_COPY_FEATURES + CROSS_COPY_PROPOSAL_ANCHOR_FEATURES
        + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_instance_origin_cross_copy_anchor_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + INSTANCE_ORIGIN_FEATURES + CROSS_COPY_FEATURES
        + CROSS_COPY_PROPOSAL_ANCHOR_FEATURES
        + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_completion_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + COMPLETION_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
    "intrinsic_topology_dominant_member_provenance_position": (
        INTRINSIC_FEATURES + TOPOLOGY_FEATURES
        + DOMINANT_MEMBER_FEATURES + PROVENANCE_FEATURES + POSITION_FEATURES
    ),
}

NUMBER_CORROBORATION_POLICIES = ("none", "strict_intrinsic")


def number_corroboration_abstention_reason(record: dict, *, policy: str) -> str | None:
    """Return why an offline Number prediction must abstain.

    The strict policy is deliberately one-way: it can only remove a Number
    prediction, never create one.  Cycle 673's content-isolated DLM review
    found that reliable full-number objects were sizeable, wide singleton
    decals supported by more than one independent proposal path.  Cycle 684's
    expanded DLM bank also showed that smooth, OCR-free owner-neutral shapes
    were overwhelmingly hardware/paint/sponsor noise; this evidence may only
    abstain and never manufacture Number authority.  Template proposal
    membership is treated as contradictory evidence rather than semantic
    authority.
    """
    if policy == "none":
        return None
    if policy != "strict_intrinsic":
        raise ValueError(f"unknown Number corroboration policy: {policy}")
    if record.get("object_kind") != "singleton":
        return "not_singleton"
    if float(record.get("multi_proposal_member_fraction", 0.0)) < 1.0:
        return "no_independent_proposal_corroboration"
    if float(record.get("area_fraction", 0.0)) < 0.008:
        return "insufficient_decal_area"
    if float(record.get("aspect_ratio", 0.0)) < 1.5:
        return "insufficient_digit_family_width"
    if float(record.get("template_member_fraction", 0.0)) >= 1.0:
        return "unresolved_template_contradiction"
    if (
        float(record.get("appearance_unassigned_instance_fraction", 0.0)) >= 0.99
        and float(record.get("max_ocr_alpha_coverage", 0.0)) <= 0.0
        and float(record.get("max_strong_gradient_fraction", 1.0)) < 0.16
    ):
        return "smooth_owner_neutral_shape"
    return None


def summarize_number_corroboration_abstentions(predictions: list[dict]) -> dict:
    """Explain whether each strict Number abstention rejected truth or noise.

    Review subtypes are immutable audit evidence only.  They never alter a
    score, create a vote, or grant ownership; the summary exists so candidate
    recall failures are not confused with adjudication precision failures.
    """
    truth_by_reason: dict[str, Counter] = defaultdict(Counter)
    labels_by_reason: dict[str, Counter] = defaultdict(Counter)
    true_number_labels = Counter()
    false_number_labels = Counter()
    for item in predictions:
        reason = item.get("abstention_reason")
        if not reason:
            continue
        truth = str(item.get("truth") or "uncertain")
        truth_by_reason[str(reason)][truth] += 1
        labels = item.get("review_labels") or (
            [item["review_label"]] if item.get("review_label") else ["unlabeled"]
        )
        for label in labels:
            label = str(label)
            labels_by_reason[str(reason)][label] += 1
            if truth == "numbers":
                true_number_labels[label] += 1
            else:
                false_number_labels[label] += 1
    return {
        "number_corroboration_abstention_truth_counts_by_reason": {
            reason: dict(sorted(counts.items()))
            for reason, counts in sorted(truth_by_reason.items())
        },
        "number_corroboration_abstention_review_label_counts_by_reason": {
            reason: dict(sorted(counts.items()))
            for reason, counts in sorted(labels_by_reason.items())
        },
        "number_corroboration_abstained_true_number_review_label_counts": dict(
            sorted(true_number_labels.items())
        ),
        "number_corroboration_rejected_false_number_review_label_counts": dict(
            sorted(false_number_labels.items())
        ),
    }


def assert_feature_set_complete(rows: list[dict], *, feature_set: str, bank_role: str) -> None:
    """Reject ablations whose reviewed records predate the requested schema.

    Legacy fields intentionally keep their historical zero-fill behavior, but
    newer ablation families must be present on every row.  Otherwise an old
    training bank and new canary silently turn schema age into a feature.
    """
    required = OPTIONAL_FEATURE_REQUIREMENTS.get(feature_set, ())
    missing = {
        name: sum(name not in row for row in rows)
        for name in required
        if any(name not in row for row in rows)
    }
    if missing:
        details = ", ".join(f"{name}:{count}" for name, count in sorted(missing.items()))
        raise ValueError(
            f"{bank_role} bank missing requested {feature_set} feature schema ({details})"
        )


def _vector(record: dict, *, feature_set: str = "legacy") -> list[float]:
    values = [float(record.get(name, 0.0)) for name in FEATURE_SETS[feature_set]]
    values.extend(float(value) for value in (record.get("shape_occupancy") or [0.0] * 16))
    values.append(float(record.get("object_kind") == "physical_group"))
    return values


def evaluate_paint_holdout(
    bank: dict,
    *,
    min_score: float = 0.80,
    min_margin: float = 0.25,
    feature_set: str = "legacy",
    number_corroboration_policy: str = "none",
) -> dict:
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"unknown semantic feature set: {feature_set}")
    rows = [item for item in bank.get("reviewed_objects") or () if item.get("review_target_layer") in CLASSES]
    assert_feature_set_complete(rows, feature_set=feature_set, bank_role="holdout")
    paints = sorted({str(item["paint_label"]) for item in rows})
    content_groups = sorted({
        str(item.get("source_content_id") or ("paint:" + str(item["paint_label"])))
        for item in rows
    })
    predictions = []
    skipped = []
    for held_content in content_groups:
        def content_id(item):
            return str(item.get("source_content_id") or ("paint:" + str(item["paint_label"])))

        train = [item for item in rows if content_id(item) != held_content]
        test = [item for item in rows if content_id(item) == held_content]
        held_paints = sorted({str(item["paint_label"]) for item in test})
        train_classes = {str(item["review_target_layer"]) for item in train}
        if set(CLASSES).difference(train_classes):
            skipped.append({
                "source_content_id": held_content,
                "paint_labels": held_paints,
                "reason": "training_fold_missing_class",
            })
            continue
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0),
        )
        model.fit(
            np.asarray([_vector(item, feature_set=feature_set) for item in train]),
            [item["review_target_layer"] for item in train],
        )
        probabilities = model.predict_proba(
            np.asarray([_vector(item, feature_set=feature_set) for item in test])
        )
        model_classes = list(model.classes_)
        for item, scores in zip(test, probabilities):
            order = np.argsort(scores)[::-1]
            best, second = int(order[0]), int(order[1])
            score, margin = float(scores[best]), float(scores[best] - scores[second])
            emitted = score >= min_score and margin >= min_margin
            top_class = str(model_classes[best])
            abstention_reason = None
            if emitted and top_class == "numbers":
                abstention_reason = number_corroboration_abstention_reason(
                    item, policy=number_corroboration_policy,
                )
                if abstention_reason:
                    emitted = False
            predicted = top_class if emitted else "abstain"
            predictions.append({
                "paint_label": str(item["paint_label"]),
                "source_content_id": held_content,
                "object_id": item["object_id"],
                "truth": item["review_target_layer"], "prediction": predicted,
                "top_class": top_class, "top_score": round(score, 6),
                "margin": round(margin, 6), "emitted": emitted,
                "abstention_reason": abstention_reason,
                "review_label": item.get("review_label"),
                "review_labels": list(item.get("review_labels") or ()),
                "review_target_proposal_support_state": item.get(
                    "review_target_proposal_support_state", "unknown"
                ),
            })
    emitted = [item for item in predictions if item["emitted"]]
    correct = [item for item in emitted if item["prediction"] == item["truth"]]
    per_class = {}
    for owner in CLASSES:
        owner_emitted = [item for item in emitted if item["prediction"] == owner]
        owner_truth = [item for item in predictions if item["truth"] == owner]
        owner_correct = [item for item in owner_emitted if item["truth"] == owner]
        per_class[owner] = {
            "emitted": len(owner_emitted),
            "truth": len(owner_truth),
            "precision": round(len(owner_correct) / len(owner_emitted), 6) if owner_emitted else None,
            "recall_at_threshold": round(len(owner_correct) / len(owner_truth), 6) if owner_truth else None,
        }
    precision = len(correct) / len(emitted) if emitted else 0.0
    coverage = len(emitted) / len(predictions) if predictions else 0.0
    number_false_positive_count = sum(item["prediction"] == "numbers" and item["truth"] != "numbers" for item in emitted)
    acceptance_ready = bool(
        len(predictions) >= 40 and len(emitted) >= 20 and precision >= 0.98
        and number_false_positive_count == 0
        and all(per_class[owner]["precision"] in (None, 1.0) or per_class[owner]["precision"] >= 0.95 for owner in CLASSES)
    )
    abstention_review_audit = summarize_number_corroboration_abstentions(predictions)
    return {
        "schema": "smart-tga-semantic-object-holdout-probe-v1",
        "paint_count": len(paints), "evaluated_object_count": len(predictions),
        "source_content_count": len(content_groups),
        "emitted_count": len(emitted), "correct_count": len(correct),
        "precision": round(precision, 6), "coverage": round(coverage, 6),
        "number_false_positive_count": number_false_positive_count,
        "number_truth_proposal_support_counts": dict(sorted(Counter(
            str(item.get("review_target_proposal_support_state") or "unknown")
            for item in predictions if item["truth"] == "numbers"
        ).items())),
        "number_correct_emission_proposal_support_counts": dict(sorted(Counter(
            str(item.get("review_target_proposal_support_state") or "unknown")
            for item in emitted
            if item["prediction"] == "numbers" and item["truth"] == "numbers"
        ).items())),
        "per_class": per_class, "skipped_folds": skipped,
        "min_score": min_score, "min_margin": min_margin,
        "feature_set": feature_set, "feature_names": list(FEATURE_SETS[feature_set]),
        "number_corroboration_policy": number_corroboration_policy,
        "number_corroboration_abstention_counts": dict(Counter(
            item["abstention_reason"] for item in predictions if item.get("abstention_reason")
        )),
        **abstention_review_audit,
        "acceptance_ready": acceptance_ready,
        "calibration_ready": False,
        "calibration_blockers": (
            ([] if acceptance_ready else ["paint_stratified_precision_or_coverage_gate"])
            + ["scores_not_probability_calibrated", "no_independent_canary_corpus"]
        ),
        "casts_votes": False, "ownership_authority": False,
        "class_counts": dict(Counter(str(item["review_target_layer"]) for item in rows)),
        "class_paint_counts": {
            owner: len({str(item["paint_label"]) for item in rows if item["review_target_layer"] == owner})
            for owner in CLASSES
        },
        "predictions": predictions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-score", type=float, default=0.80)
    parser.add_argument("--min-margin", type=float, default=0.25)
    parser.add_argument("--feature-set", choices=sorted(FEATURE_SETS), default="legacy")
    parser.add_argument(
        "--number-corroboration-policy",
        choices=NUMBER_CORROBORATION_POLICIES,
        default="none",
        help="Audit-only one-way Number abstention policy; never creates ownership votes.",
    )
    args = parser.parse_args()
    bank = json.loads(Path(args.bank).read_text(encoding="utf-8"))
    report = evaluate_paint_holdout(
        bank, min_score=args.min_score, min_margin=args.min_margin, feature_set=args.feature_set,
        number_corroboration_policy=args.number_corroboration_policy,
    )
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "predictions"}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
