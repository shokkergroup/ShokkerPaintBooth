"""Apply the frozen Cycle732/733 DLM family stack to one untouched paint.

The five source-disjoint development folds are deterministic committee members.
Each member reuses its persisted raw threshold, completeness/certainty heads,
assembly configuration, pretrained appearance head and appearance threshold.
The untouched paint contributes one directly reviewed complete Number anchor but
no candidate outcomes. A candidate needs at least three of five votes. This is
zero-output-authority research inference and cannot alter runtime ownership.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np
from sklearn.model_selection import GroupKFold

try:
    from scripts.smart_tga_fragment_completeness_head import (
        HEAD_CONFIGS, _arrays, _fit_predict as _fit_head,
    )
    from scripts.smart_tga_fragment_purity_veto import (
        MODEL_CONFIGS as APPEARANCE_CONFIGS,
        _appearance_matrix, _fit_predict as _fit_appearance,
        _load_appearance, _load_pretrained_appearance,
    )
    from scripts.smart_tga_baseline_purity_veto import _calibration_dataset
    from scripts.smart_tga_number_family_set_assembler import (
        _assemble_from_reviewed_anchor,
    )
    from scripts.smart_tga_within_paint_ordinal_family import (
        _build_rows, _load_candidate_table, _top_two,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_fragment_completeness_head import (  # type: ignore
        HEAD_CONFIGS, _arrays, _fit_predict as _fit_head,
    )
    from scripts.smart_tga_fragment_purity_veto import (  # type: ignore
        MODEL_CONFIGS as APPEARANCE_CONFIGS,
        _appearance_matrix, _fit_predict as _fit_appearance,
        _load_appearance, _load_pretrained_appearance,
    )
    from scripts.smart_tga_baseline_purity_veto import (  # type: ignore
        _calibration_dataset,
    )
    from scripts.smart_tga_number_family_set_assembler import (  # type: ignore
        _assemble_from_reviewed_anchor,
    )
    from scripts.smart_tga_within_paint_ordinal_family import (  # type: ignore
        _build_rows, _load_candidate_table, _top_two,
    )


COMMITTEE_SIZE = 5
VOTES_REQUIRED = 3


def _by_name(configs: tuple[dict, ...], name: str) -> dict:
    return next(config for config in configs if config["name"] == name)


def _majority_top_two(
    votes: np.ndarray, score: np.ndarray, keys: np.ndarray,
    required: int = VOTES_REQUIRED,
) -> np.ndarray:
    """Preserve the raw top-two-per-block constraint after majority voting."""
    eligible = votes.sum(axis=0) >= required
    return _top_two(score, eligible, keys)


def _apply_fragment_rescue(
    baseline: np.ndarray, purity_retained: np.ndarray,
    complete_probability: np.ndarray, threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Protect only already-raw candidates; never manufacture a nomination."""
    rescue = baseline & ~purity_retained & (complete_probability >= threshold)
    return purity_retained | rescue, rescue


def _trace(row: dict) -> tuple[str, int, str]:
    return row["paint"], int(row["candidate_index"]), str(row["proposal_id"])


def _json_number(value: float) -> float | str:
    if np.isposinf(value):
        return "infinity"
    if np.isneginf(value):
        return "-infinity"
    return round(float(value), 8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-bank", type=Path, required=True)
    parser.add_argument("--development-labels", type=Path, required=True)
    parser.add_argument("--development-embeddings", type=Path, required=True)
    parser.add_argument("--holdout-bank", type=Path, required=True)
    parser.add_argument("--holdout-anchor-labels", type=Path, required=True)
    parser.add_argument("--holdout-embeddings", type=Path, required=True)
    parser.add_argument("--pretrained-appearance", type=Path, required=True)
    parser.add_argument("--development-semantic", type=Path)
    parser.add_argument("--holdout-semantic", type=Path)
    parser.add_argument("--assembly-ledger", type=Path, required=True)
    parser.add_argument("--appearance-ledger", type=Path, required=True)
    parser.add_argument("--baseline-purity-ledger", type=Path)
    parser.add_argument("--baseline-fragment-rescue-ledger", type=Path)
    parser.add_argument("--calibration-bank", type=Path)
    parser.add_argument("--calibration-outcomes", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=734)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)

    assembly_ledger = json.loads(args.assembly_ledger.read_text(encoding="utf-8"))
    appearance_ledger = json.loads(args.appearance_ledger.read_text(encoding="utf-8"))
    baseline_purity_ledger = (
        None if args.baseline_purity_ledger is None
        else json.loads(args.baseline_purity_ledger.read_text(encoding="utf-8"))
    )
    fragment_rescue_ledger = (
        None if args.baseline_fragment_rescue_ledger is None
        else json.loads(args.baseline_fragment_rescue_ledger.read_text(encoding="utf-8"))
    )
    if len(assembly_ledger["folds"]) != COMMITTEE_SIZE:
        raise RuntimeError("frozen assembly fold count drift")
    if len(appearance_ledger["folds"]) != COMMITTEE_SIZE:
        raise RuntimeError("frozen appearance fold count drift")
    if baseline_purity_ledger is not None:
        if args.calibration_bank is None or args.calibration_outcomes is None:
            raise ValueError("baseline purity requires calibration bank and outcomes")
        if len(baseline_purity_ledger["folds"]) != COMMITTEE_SIZE:
            raise RuntimeError("baseline purity fold count drift")
        if not baseline_purity_ledger["gates"]["baseline_purity_calibration_gate_passed"]:
            raise RuntimeError("refusing an unaccepted baseline purity calibrator")
    if fragment_rescue_ledger is not None:
        if baseline_purity_ledger is None:
            raise ValueError("fragment rescue requires baseline purity")
        if not fragment_rescue_ledger["gates"][
            "fragment_rescue_calibration_gate_passed"
        ]:
            raise RuntimeError("refusing an unaccepted fragment rescue calibrator")

    development_table = _load_candidate_table(
        args.development_bank, args.development_embeddings, args.development_labels,
    )
    development_rows = _build_rows(development_table)
    development_indices = np.asarray([
        offset for offset, row in enumerate(development_rows)
        if row["semantic"] is not None
    ], dtype=np.int64)
    development_groups = np.asarray([
        development_rows[int(index)]["content_group"]
        for index in development_indices
    ])
    folds = list(GroupKFold(n_splits=COMMITTEE_SIZE).split(
        development_indices, groups=development_groups,
    ))

    holdout_table = _load_candidate_table(
        args.holdout_bank, args.holdout_embeddings, args.holdout_anchor_labels,
    )
    holdout_rows = _build_rows(holdout_table)
    holdout_indices = np.arange(len(holdout_rows), dtype=np.int64)
    holdout_data = _arrays(holdout_rows, holdout_indices)
    pretrained = _load_pretrained_appearance(args.pretrained_appearance)
    appearance_mode = str(appearance_ledger.get(
        "appearance_mode", "pretrained-anchor-relative",
    ))
    semantic = None
    semantic_names = None
    if appearance_mode == "pretrained-anchor-relative-semantic":
        if args.development_semantic is None or args.holdout_semantic is None:
            raise ValueError("semantic appearance ledger requires both semantic banks")
        semantic, semantic_names = _load_appearance(args.development_semantic)
        holdout_semantic, holdout_semantic_names = _load_appearance(args.holdout_semantic)
        if semantic_names != holdout_semantic_names:
            raise RuntimeError("semantic mask feature schema drift")
        overlap = set(semantic).intersection(holdout_semantic)
        if any(not np.array_equal(semantic[key], holdout_semantic[key]) for key in overlap):
            raise RuntimeError("development/holdout semantic trace value drift")
        semantic.update(holdout_semantic)
    development_appearance, appearance_names = _appearance_matrix(
        development_rows, development_indices, development_table,
        {}, [], appearance_mode, pretrained, semantic, semantic_names,
    )
    holdout_appearance, holdout_names = _appearance_matrix(
        holdout_rows, holdout_indices, holdout_table,
        {}, [], appearance_mode, pretrained, semantic, semantic_names,
    )
    if appearance_names != holdout_names:
        raise RuntimeError("pretrained appearance feature schema drift")

    calibration_features = None
    calibration_target = None
    if baseline_purity_ledger is not None:
        calibration = baseline_purity_ledger["active_learning_calibration"]
        calibration_features, calibration_target, _, _ = _calibration_dataset(
            args.calibration_bank, args.calibration_outcomes,
            str(calibration["paint"]), int(calibration["anchor_candidate_index"]),
            pretrained, semantic,
        )
        if calibration_features.shape[1] != development_appearance.shape[1]:
            raise RuntimeError("baseline purity calibration feature schema drift")

    count = len(holdout_rows)
    baseline_votes = np.zeros((COMMITTEE_SIZE, count), dtype=bool)
    assembly_votes = np.zeros((COMMITTEE_SIZE, count), dtype=bool)
    appearance_votes = np.zeros((COMMITTEE_SIZE, count), dtype=bool)
    baseline_purity_votes = np.zeros((COMMITTEE_SIZE, count), dtype=bool)
    fragment_rescue_votes = np.zeros((COMMITTEE_SIZE, count), dtype=bool)
    complete_probability = np.empty((COMMITTEE_SIZE, count), dtype=np.float64)
    certainty_probability = np.empty((COMMITTEE_SIZE, count), dtype=np.float64)
    appearance_probability = np.empty((COMMITTEE_SIZE, count), dtype=np.float64)
    baseline_purity_probability = np.full(
        (COMMITTEE_SIZE, count), np.nan, dtype=np.float64,
    )
    fold_summaries = []

    for fold, (train_offset, test_offset) in enumerate(folds):
        assembly = assembly_ledger["folds"][fold]
        appearance = appearance_ledger["folds"][fold]
        expected_test = sorted({
            development_rows[int(development_indices[value])]["paint"]
            for value in test_offset
        })
        if expected_test != assembly["test_paints"] or expected_test != appearance["test_paints"]:
            raise RuntimeError(f"frozen fold ordering drift at fold {fold}")
        train_indices = development_indices[train_offset]
        train_data = _arrays(development_rows, train_indices)
        complete_config = _by_name(
            HEAD_CONFIGS, assembly["selected_completeness_head"],
        )
        certainty_config = _by_name(
            HEAD_CONFIGS, assembly["selected_certainty_head"],
        )
        complete_probability[fold] = _fit_head(
            train_data, holdout_data, complete_config,
            "complete_copy_description", 7420 + fold,
        )
        certainty_probability[fold] = _fit_head(
            train_data, holdout_data, certainty_config,
            "review_certainty_veto", 7430 + fold,
        )
        raw_threshold = float(assembly["raw_safe_threshold"])
        baseline = _top_two(
            holdout_data["raw_score"],
            holdout_data["raw_score"] >= raw_threshold,
            holdout_data["keys"],
        )
        config = assembly["assembly_config"]
        assembled, sets = _assemble_from_reviewed_anchor(
            holdout_rows, holdout_indices, holdout_data, baseline,
            complete_probability[fold], float(config["fragment_score_threshold"]),
            float(config["fragment_complete_max"]), int(config["fragment_cap"]),
            certainty_probability[fold], float(config["certainty_min"]),
        )
        additions = assembled & ~baseline
        appearance_config = _by_name(
            APPEARANCE_CONFIGS, appearance["selected_appearance_head"],
        )
        appearance_probability[fold] = _fit_appearance(
            development_appearance[train_offset], train_data["family"],
            train_data["known"], holdout_appearance, appearance_config,
            appearance_names, 7430 + fold,
        )
        appearance_threshold = float(appearance["purity_veto_threshold"])
        baseline_votes[fold] = baseline
        if baseline_purity_ledger is None:
            baseline_purity_votes[fold] = baseline
        else:
            baseline_purity = baseline_purity_ledger["folds"][fold]
            if expected_test != baseline_purity["test_paints"]:
                raise RuntimeError(f"baseline purity fold ordering drift at fold {fold}")
            baseline_config = _by_name(
                APPEARANCE_CONFIGS,
                baseline_purity["selected_baseline_purity_head"],
            )
            fit_features = np.concatenate((
                development_appearance[train_offset], calibration_features,
            ))
            fit_target = np.concatenate((
                train_data["family"], calibration_target,
            ))
            fit_known = np.concatenate((
                train_data["known"],
                np.ones(len(calibration_target), dtype=bool),
            ))
            baseline_purity_probability[fold] = _fit_appearance(
                fit_features, fit_target, fit_known, holdout_appearance,
                baseline_config, appearance_names, 7460 + fold,
            )
            baseline_threshold = float(
                baseline_purity["baseline_purity_threshold"]
            )
            baseline_purity_votes[fold] = baseline & (
                baseline_purity_probability[fold] >= baseline_threshold
            )
            if fragment_rescue_ledger is not None:
                rescue_threshold = float(
                    fragment_rescue_ledger["active_learning_calibration"][
                        "completeness_rescue_threshold"
                    ]
                )
                baseline_purity_votes[fold], fragment_rescue_votes[fold] = (
                    _apply_fragment_rescue(
                        baseline, baseline_purity_votes[fold],
                        complete_probability[fold], rescue_threshold,
                    )
                )
        assembly_votes[fold] = additions
        appearance_votes[fold] = additions & (
            appearance_probability[fold] >= appearance_threshold
        )
        fold_summaries.append({
            "fold": fold,
            "development_test_paints": expected_test,
            "raw_threshold": _json_number(raw_threshold),
            "baseline_count": int(baseline.sum()),
            "baseline_purity_retained_count": int(
                baseline_purity_votes[fold].sum()
            ),
            "assembly_addition_count": int(additions.sum()),
            "appearance_retained_addition_count": int(appearance_votes[fold].sum()),
            "completeness_head": complete_config["name"],
            "certainty_head": certainty_config["name"],
            "assembly_config": config,
            "appearance_head": appearance_config["name"],
            "appearance_threshold": _json_number(appearance_threshold),
            "baseline_purity_head": (
                None if baseline_purity_ledger is None else baseline_config["name"]
            ),
            "baseline_purity_threshold": (
                None if baseline_purity_ledger is None
                else _json_number(baseline_threshold)
            ),
            "baseline_fragment_rescue_threshold": (
                None if fragment_rescue_ledger is None
                else _json_number(rescue_threshold)
            ),
            "baseline_fragment_rescue_count": int(
                fragment_rescue_votes[fold].sum()
            ),
            "assembled_set_count": len(sets),
        })

    baseline_committee = _majority_top_two(
        baseline_purity_votes, holdout_data["raw_score"], holdout_data["keys"],
    )
    addition_committee = appearance_votes.sum(axis=0) >= VOTES_REQUIRED
    addition_committee &= ~baseline_committee
    accepted = baseline_committee | addition_committee
    decisions = []
    queue_items = []
    for offset, row in enumerate(holdout_rows):
        raw_count = int(baseline_votes[:, offset].sum())
        assembly_count = int(assembly_votes[:, offset].sum())
        retained_count = int(appearance_votes[:, offset].sum())
        baseline_purity_count = int(baseline_purity_votes[:, offset].sum())
        fragment_rescue_count = int(fragment_rescue_votes[:, offset].sum())
        decision = (
            "raw_baseline" if baseline_committee[offset]
            else "family_addition" if addition_committee[offset]
            else "rejected"
        )
        decisions.append({
            "paint": row["paint"],
            "candidate_index": int(row["candidate_index"]),
            "proposal_id": row["proposal_id"],
            "block_for_review_only": row["block"],
            "raw_score": round(float(holdout_data["raw_score"][offset]), 8),
            "frozen_family_score": round(float(holdout_data["family_score"][offset]), 8),
            "baseline_votes": raw_count,
            "baseline_purity_retained_votes": baseline_purity_count,
            "baseline_fragment_rescue_votes": fragment_rescue_count,
            "assembly_votes": assembly_count,
            "appearance_retained_votes": retained_count,
            "median_complete_probability": round(float(np.median(complete_probability[:, offset])), 8),
            "median_certainty_probability": round(float(np.median(certainty_probability[:, offset])), 8),
            "median_appearance_probability": round(float(np.median(appearance_probability[:, offset])), 8),
            "median_baseline_purity_probability": (
                None if baseline_purity_ledger is None
                else round(float(np.median(baseline_purity_probability[:, offset])), 8)
            ),
            "decision": decision,
            "ownership_authority": False,
        })
        queue_items.append({
            "paint": row["paint"],
            "candidate_index": int(row["candidate_index"]),
            "proposal_id": row["proposal_id"],
            "block": row["block"],
            "ordinal_score": round(float(holdout_data["family_score"][offset]), 8),
            "certainty_probability": round(retained_count / COMMITTEE_SIZE, 8),
            "nearest_boundary": decision,
        })

    payload = {
        "schema": "smart-tga-frozen-holdout-committee-v1",
        "cycle": args.cycle,
        "contract": "Five frozen source-disjoint fold members; >=3 votes; raw top-two preserved; appearance and optional calibrated raw-baseline semantics are veto-only; one direct complete anchor; zero output authority.",
        "holdout_paint": holdout_rows[0]["paint"] if holdout_rows else None,
        "direct_anchor_review_codes": sorted(set(
            row["anchor_review_code"] for row in holdout_rows
        )),
        "candidate_decision_count": count,
        "appearance_mode": appearance_mode,
        "baseline_purity_enabled": baseline_purity_ledger is not None,
        "baseline_fragment_rescue_enabled": fragment_rescue_ledger is not None,
        "baseline_fragment_rescue_calibration_paint": (
            None if fragment_rescue_ledger is None
            else fragment_rescue_ledger["active_learning_calibration"]["paint"]
        ),
        "committee": {
            "size": COMMITTEE_SIZE,
            "votes_required": VOTES_REQUIRED,
            "baseline_accepted": int(baseline_committee.sum()),
            "family_additions_accepted": int(addition_committee.sum()),
            "total_accepted": int(accepted.sum()),
        },
        "folds": fold_summaries,
        "decisions": decisions,
        "safety": {
            "holdout_non_anchor_truth_consumed": False,
            "filename_or_car_feature": False,
            "absolute_bbox_model_feature": False,
            "relationship_manufactures_authority": False,
            "semantic_evidence_is_veto_only": semantic is not None,
            "baseline_purity_can_only_remove_raw_candidates": (
                baseline_purity_ledger is not None
            ),
            "baseline_fragment_rescue_can_only_protect_existing_raw_candidates": (
                fragment_rescue_ledger is not None
            ),
            "baseline_fragment_rescue_calibration_is_not_holdout_evaluation": (
                fragment_rescue_ledger is not None
            ),
            "baseline_purity_calibration_is_not_holdout_evaluation": (
                baseline_purity_ledger is not None
            ),
            "runtime_integrated": False,
            "ownership_authority": False,
            "apply_locked": True,
            "exact_reconstruction_affected": False,
            "ocr_changed": False,
        },
        "elapsed_sec": round(time.perf_counter() - started, 3),
    }
    (args.output / "frozen_predictions.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "review_queue.json").write_text(
        json.dumps({
            "schema": "smart-tga-frozen-holdout-review-queue-v1",
            "truth_opened_before_predictions": False,
            "items": queue_items,
        }, indent=2) + "\n", encoding="utf-8",
    )
    for page, start in enumerate(range(0, len(queue_items), 12)):
        (args.output / f"review_queue_page_{page:02d}.json").write_text(
            json.dumps({"items": queue_items[start:start + 12]}, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "holdout": payload["holdout_paint"],
        "candidate_decisions": count,
        "committee": payload["committee"],
        "review_pages": (len(queue_items) + 11) // 12,
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
