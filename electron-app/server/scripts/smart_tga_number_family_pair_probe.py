"""Paint-disjoint offline evaluation for DLM same-number-family retrieval.

The model ranks immutable raw candidates as possible sibling copies of a
reviewed number anchor.  It is shadow-only and cannot change masks or owners.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _matrix(rows: Sequence[Mapping[str, Any]], names: Sequence[str]) -> np.ndarray:
    return np.asarray([[float(row.get(name) or 0.0) for name in names] for row in rows], dtype=np.float64)


def _model(kind: str) -> Any:
    if kind == "extra_trees":
        return ExtraTreesClassifier(
            n_estimators=500, min_samples_leaf=2, max_features=0.7,
            class_weight="balanced", random_state=0, n_jobs=-1,
        )
    if kind == "random_forest":
        return RandomForestClassifier(
            n_estimators=500, min_samples_leaf=2, max_features=0.7,
            class_weight="balanced_subsample", random_state=0, n_jobs=-1,
        )
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=3000, class_weight="balanced", random_state=0),
    )


def _metrics(truth: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, Any]:
    predicted = scores >= threshold
    tp = int(np.sum(predicted & truth))
    fp = int(np.sum(predicted & ~truth))
    fn = int(np.sum(~predicted & truth))
    return {
        "true_positive": tp, "false_positive": fp, "false_negative": fn,
        "precision": round(tp / (tp + fp), 6) if tp + fp else None,
        "recall": round(tp / (tp + fn), 6) if tp + fn else None,
    }


def choose_threshold(
    truth: np.ndarray, scores: np.ndarray, *, min_precision: float,
) -> tuple[float, dict[str, Any]]:
    candidates = sorted({float(value) for value in scores}, reverse=True)
    best: tuple[tuple[float, float, float], float, dict[str, Any]] | None = None
    for threshold in candidates:
        metrics = _metrics(truth, scores, threshold)
        precision = metrics["precision"]
        if precision is None or precision < min_precision or metrics["true_positive"] < 2:
            continue
        key = (float(metrics["recall"] or 0.0), float(precision), threshold)
        if best is None or key > best[0]:
            best = (key, threshold, metrics)
    if best is None:
        return 1.0, _metrics(truth, scores, 1.0)
    return best[1], best[2]


def _ranking(rows: Sequence[Mapping[str, Any]], scores: np.ndarray) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[tuple[bool, float]]] = defaultdict(list)
    for row, score in zip(rows, scores):
        key = (str(row["paint_label"]), str(row["family_id"]), str(row["left_instance_id"]))
        groups[key].append((bool(row["truth_same_number_family"]), float(score)))
    ranks = []
    for items in groups.values():
        if not any(truth for truth, _ in items) or not any(not truth for truth, _ in items):
            continue
        ordered = sorted(items, key=lambda item: item[1], reverse=True)
        ranks.append(next(index + 1 for index, (truth, _) in enumerate(ordered) if truth))
    return {
        "anchor_count": len(ranks),
        "recall_at_1": round(sum(rank <= 1 for rank in ranks) / len(ranks), 6) if ranks else None,
        "recall_at_3": round(sum(rank <= 3 for rank in ranks) / len(ranks), 6) if ranks else None,
        "mean_reciprocal_rank": round(sum(1.0 / rank for rank in ranks) / len(ranks), 6) if ranks else None,
    }


def _top_candidates(
    rows: Sequence[Mapping[str, Any]], scores: np.ndarray,
) -> list[tuple[dict[str, Any], bool, float]]:
    groups: dict[tuple[str, str, str], list[tuple[dict[str, Any], bool, float]]] = defaultdict(list)
    for row, score in zip(rows, scores):
        key = (str(row["paint_label"]), str(row["family_id"]), str(row["left_instance_id"]))
        groups[key].append((dict(row), bool(row["truth_same_number_family"]), float(score)))
    selected = []
    for items in groups.values():
        if not any(truth for _, truth, _ in items):
            continue
        selected.append(max(items, key=lambda item: item[2]))
    return selected


def _reverse_feature_rows(
    rows: Sequence[Mapping[str, Any]], names: Sequence[str],
) -> list[dict[str, Any]]:
    """Swap intrinsic anchor/candidate fields for reverse-direction scoring."""
    reversed_rows = []
    for row in rows:
        item = dict(row)
        for name in names:
            if name.startswith("anchor_"):
                item[name] = row.get(f"candidate_{name[7:]}", 0.0)
            elif name.startswith("candidate_"):
                item[name] = row.get(f"anchor_{name[10:]}", 0.0)
        reversed_rows.append(item)
    return reversed_rows


def _mutual_top_candidates(
    rows: Sequence[Mapping[str, Any]],
    forward_scores: np.ndarray,
    reverse_scores: np.ndarray,
) -> tuple[list[tuple[dict[str, Any], bool, float]], list[dict[str, Any]]]:
    """Keep A->B only when B's best reviewed-anchor return is B->A."""
    forward_by_anchor: dict[tuple[tuple[str, str], str], list[tuple[float, dict[str, Any]]]] = defaultdict(list)
    reverse_by_candidate: dict[tuple[tuple[str, str], str], list[tuple[float, str]]] = defaultdict(list)
    for raw_row, forward, reverse in zip(rows, forward_scores, reverse_scores):
        row = dict(raw_row)
        family_key = (str(row["paint_label"]), str(row["family_id"]))
        anchor_id = str(row["left_instance_id"])
        candidate_id = str(row["right_instance_id"])
        forward_by_anchor[(family_key, anchor_id)].append((float(forward), row))
        reverse_by_candidate[(family_key, candidate_id)].append((float(reverse), anchor_id))
    selected = []
    diagnostics = []
    for (family_key, anchor_id), items in forward_by_anchor.items():
        if not any(bool(row["truth_same_number_family"]) for _, row in items):
            continue
        forward, row = max(items, key=lambda item: item[0])
        candidate_id = str(row["right_instance_id"])
        reverse, return_anchor = max(
            reverse_by_candidate[(family_key, candidate_id)], key=lambda item: item[0],
        )
        mutual = return_anchor == anchor_id
        mutual_score = min(forward, reverse) if mutual else -1.0
        truth = bool(row["truth_same_number_family"])
        selected.append((row, truth, mutual_score))
        diagnostics.append({
            "paint_label": row["paint_label"],
            "family_id": row["family_id"],
            "anchor_instance_id": anchor_id,
            "candidate_instance_id": candidate_id,
            "truth_same_number_family": truth,
            "mutual": mutual,
            "forward_score": round(forward, 6),
            "reverse_score": round(reverse, 6),
            "mutual_score": round(mutual_score, 6),
        })
    return selected, diagnostics


def _retrieval_metrics(
    selected: Sequence[tuple[Mapping[str, Any], bool, float]], threshold: float,
) -> dict[str, Any]:
    accepted = [item for item in selected if item[2] >= threshold]
    tp = sum(truth for _, truth, _ in accepted)
    fp = len(accepted) - tp
    return {
        "anchor_count": len(selected), "accepted_anchor_count": len(accepted),
        "true_positive": tp, "false_positive": fp,
        "false_negative": len(selected) - tp,
        "precision": round(tp / len(accepted), 6) if accepted else None,
        "recall": round(tp / len(selected), 6) if selected else None,
    }


def choose_retrieval_threshold(
    selected: Sequence[tuple[Mapping[str, Any], bool, float]], *, min_precision: float,
) -> tuple[float, dict[str, Any]]:
    candidates = sorted({score for _, _, score in selected}, reverse=True)
    best: tuple[tuple[float, float, float], float, dict[str, Any]] | None = None
    for threshold in candidates:
        metrics = _retrieval_metrics(selected, threshold)
        precision = metrics["precision"]
        if precision is None or precision < min_precision or metrics["true_positive"] < 2:
            continue
        key = (float(metrics["recall"] or 0.0), float(precision), threshold)
        if best is None or key > best[0]:
            best = (key, threshold, metrics)
    if best is None:
        return 1.0, _retrieval_metrics(selected, 1.0)
    return best[1], best[2]


def _descriptor_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(
        key for key in rows[0]
        if key.startswith("candidate_")
        and not key.startswith("candidate_group_")
        and key not in {"candidate_instance_id"}
        and isinstance(rows[0].get(key), (int, float))
    ) if rows else []


def _prototype_library(
    rows: Sequence[Mapping[str, Any]], descriptor_names: Sequence[str],
    *, excluded_paint: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique: dict[tuple[str, str, str], np.ndarray] = {}
    for row in rows:
        paint = str(row["paint_label"])
        if excluded_paint is not None and paint == excluded_paint:
            continue
        label = "numbers" if row["truth_same_number_family"] else (
            "sponsors" if row.get("negative_owner") == "sponsors" else ""
        )
        if not label:
            continue
        instance_id = str(row["right_instance_id"])
        unique[(paint, instance_id, label)] = np.asarray(
            [float(row.get(name) or 0.0) for name in descriptor_names], dtype=np.float64,
        )
    values = np.asarray(list(unique.values()), dtype=np.float64)
    labels = np.asarray([key[2] for key in unique])
    scale = np.std(values, axis=0) if len(values) else np.ones(len(descriptor_names))
    scale[scale < 1e-6] = 1.0
    return values, labels, scale


def _prototype_advantage(
    query: Mapping[str, Any], library: np.ndarray, labels: np.ndarray,
    scale: np.ndarray, descriptor_names: Sequence[str],
) -> float:
    vector = np.asarray([float(query.get(name) or 0.0) for name in descriptor_names])
    distances = np.sqrt(np.mean(((library - vector) / scale) ** 2, axis=1))
    class_distances = {}
    for owner in ("numbers", "sponsors"):
        owned = np.sort(distances[labels == owner])
        class_distances[owner] = float(np.mean(owned[:min(3, len(owned))])) if len(owned) else 1e6
    # Positive means the candidate resembles Sponsor/logo prototypes more
    # closely than reviewed Number-copy prototypes.
    return class_distances["numbers"] - class_distances["sponsors"]


def _prototype_advantages(
    source_rows: Sequence[Mapping[str, Any]],
    selected: Sequence[tuple[Mapping[str, Any], bool, float]],
    *, exclude_query_paint: bool,
) -> list[float]:
    names = _descriptor_names(source_rows)
    shared = _prototype_library(source_rows, names)
    result = []
    for row, _, _ in selected:
        library = shared
        if exclude_query_paint:
            library = _prototype_library(
                source_rows, names, excluded_paint=str(row["paint_label"]),
            )
        result.append(_prototype_advantage(row, *library, names))
    return result


def choose_sponsor_veto(
    selected: Sequence[tuple[Mapping[str, Any], bool, float]],
    advantages: Sequence[float], *, base_threshold: float,
    min_precision: float = 1.0,
) -> tuple[float, dict[str, Any]]:
    candidates = sorted({float(value) for value in advantages}) + [float("inf")]
    best: tuple[tuple[float, float, float], float, dict[str, Any]] | None = None
    for veto_threshold in candidates:
        kept = [
            item for item, advantage in zip(selected, advantages)
            if item[2] >= base_threshold and advantage < veto_threshold
        ]
        tp = sum(truth for _, truth, _ in kept)
        fp = len(kept) - tp
        anchor_count = len(selected)
        precision = tp / len(kept) if kept else None
        metrics = {
            "anchor_count": anchor_count, "accepted_anchor_count": len(kept),
            "true_positive": tp, "false_positive": fp,
            "false_negative": anchor_count - tp,
            "precision": round(precision, 6) if precision is not None else None,
            "recall": round(tp / anchor_count, 6) if anchor_count else None,
        }
        if precision is None or precision < min_precision or tp < 2:
            continue
        key = (float(metrics["recall"] or 0.0), float(precision), veto_threshold)
        if best is None or key > best[0]:
            best = (key, veto_threshold, metrics)
    if best is None:
        return float("-inf"), {
            "anchor_count": len(selected), "accepted_anchor_count": 0,
            "true_positive": 0, "false_positive": 0,
            "false_negative": len(selected), "precision": None, "recall": 0.0,
        }
    return best[1], best[2]


def _apply_sponsor_veto(
    selected: Sequence[tuple[Mapping[str, Any], bool, float]],
    advantages: Sequence[float], *, base_threshold: float, veto_threshold: float,
) -> tuple[dict[str, Any], list[tuple[Mapping[str, Any], bool, float, float]]]:
    kept = [
        (*item, advantage) for item, advantage in zip(selected, advantages)
        if item[2] >= base_threshold and advantage < veto_threshold
    ]
    tp = sum(truth for _, truth, _, _ in kept)
    fp = len(kept) - tp
    metrics = {
        "anchor_count": len(selected), "accepted_anchor_count": len(kept),
        "true_positive": tp, "false_positive": fp,
        "false_negative": len(selected) - tp,
        "precision": round(tp / len(kept), 6) if kept else None,
        "recall": round(tp / len(selected), 6) if selected else None,
    }
    return metrics, kept


def evaluate(
    bank: Mapping[str, Any], *, train_cycles: set[str], canary_cycles: set[str],
    min_train_precision: float = 0.95, model_kind: str = "logistic",
    include_group_features: bool = True,
) -> dict[str, Any]:
    summary = bank.get("summary") or {}
    if summary.get("casts_votes") or summary.get("ownership_authority"):
        raise ValueError("pair bank claimed runtime authority")
    names = [str(name) for name in bank.get("feature_names") or ()]
    if not include_group_features:
        names = [
            name for name in names
            if not name.startswith("anchor_group_")
            and not name.startswith("candidate_group_")
        ]
    rows = [dict(row) for row in bank.get("records") or ()]
    train = [row for row in rows if str(row.get("cycle")) in train_cycles]
    canary = [row for row in rows if str(row.get("cycle")) in canary_cycles]
    train_paints = {str(row["paint_label"]) for row in train}
    canary_paints = {str(row["paint_label"]) for row in canary}
    overlap = train_paints & canary_paints
    if overlap:
        raise ValueError(f"train/canary paint overlap: {sorted(overlap)[:5]}")
    if len(train_paints) < 8 or len(canary_paints) < 3:
        raise ValueError("insufficient paint-disjoint coverage")
    y_train = np.asarray([bool(row["truth_same_number_family"]) for row in train])
    y_canary = np.asarray([bool(row["truth_same_number_family"]) for row in canary])
    if min(np.sum(y_train), np.sum(y_canary)) < 12:
        raise ValueError("insufficient positive pair coverage")
    x_train = _matrix(train, names)
    x_train_reverse = _matrix(_reverse_feature_rows(train, names), names)
    x_canary = _matrix(canary, names)
    x_canary_reverse = _matrix(_reverse_feature_rows(canary, names), names)
    groups = np.asarray([str(row["paint_label"]) for row in train])
    fold_count = min(5, len(train_paints))
    oof = np.zeros(len(train), dtype=np.float64)
    oof_reverse = np.zeros(len(train), dtype=np.float64)
    for fit, validation in GroupKFold(n_splits=fold_count).split(x_train, y_train, groups):
        model = _model(model_kind)
        model.fit(x_train[fit], y_train[fit])
        oof[validation] = model.predict_proba(x_train[validation])[:, 1]
        oof_reverse[validation] = model.predict_proba(x_train_reverse[validation])[:, 1]
    train_top = _top_candidates(train, oof)
    threshold, train_metrics = choose_retrieval_threshold(
        train_top, min_precision=min_train_precision,
    )
    model = _model(model_kind)
    model.fit(x_train, y_train)
    scores = model.predict_proba(x_canary)[:, 1]
    reverse_scores = model.predict_proba(x_canary_reverse)[:, 1]
    pair_metrics = _metrics(y_canary, scores, threshold)
    canary_top = _top_candidates(canary, scores)
    canary_metrics = _retrieval_metrics(canary_top, threshold)
    train_advantages = _prototype_advantages(train, train_top, exclude_query_paint=True)
    sponsor_veto_threshold, sponsor_train_metrics = choose_sponsor_veto(
        train_top, train_advantages, base_threshold=threshold,
    )
    canary_advantages = _prototype_advantages(train, canary_top, exclude_query_paint=False)
    sponsor_canary_metrics, sponsor_kept = _apply_sponsor_veto(
        canary_top, canary_advantages, base_threshold=threshold,
        veto_threshold=sponsor_veto_threshold,
    )
    train_mutual, _ = _mutual_top_candidates(train, oof, oof_reverse)
    mutual_threshold, mutual_train_metrics = choose_retrieval_threshold(
        train_mutual, min_precision=min_train_precision,
    )
    canary_mutual, mutual_diagnostics = _mutual_top_candidates(
        canary, scores, reverse_scores,
    )
    mutual_canary_metrics = _retrieval_metrics(canary_mutual, mutual_threshold)
    mutual_accepted = [item for item in mutual_diagnostics if item["mutual_score"] >= mutual_threshold]
    mutual_family_count = len({
        (str(item["paint_label"]), str(item["family_id"]))
        for item in mutual_accepted if item["truth_same_number_family"]
    })
    false_positives = []
    recovered = []
    for row, truth, score in canary_top:
        if score < threshold:
            continue
        item = {
            "paint_label": row["paint_label"], "family_id": row["family_id"],
            "anchor_instance_id": row["left_instance_id"],
            "candidate_instance_id": row["right_instance_id"],
            "score": round(float(score), 6),
        }
        (recovered if truth else false_positives).append(item)
    baseline_scores = np.asarray([
        0.5 * float(row.get("shape_d4_cosine") or 0.0)
        + 0.5 * (1.0 - float(row.get("shape_d4_l1") or 0.0))
        for row in canary
    ])
    return {
        "schema": "smart-tga-number-family-pair-probe-v1",
        "model_kind": model_kind,
        "feature_set": "group_context" if include_group_features else "intrinsic_only",
        "feature_names": names,
        "train_cycles": sorted(train_cycles), "canary_cycles": sorted(canary_cycles),
        "train_paint_count": len(train_paints), "canary_paint_count": len(canary_paints),
        "train_pair_count": len(train), "canary_pair_count": len(canary),
        "train_positive_pair_count": int(np.sum(y_train)),
        "canary_positive_pair_count": int(np.sum(y_canary)),
        "threshold_selection": {
            "source": "paint-grouped out-of-fold training predictions",
            "minimum_precision": min_train_precision,
            "threshold": round(float(threshold), 6),
            "metrics": train_metrics,
        },
        "canary": {
            **canary_metrics,
            "pair_threshold_diagnostic": pair_metrics,
            "average_precision": round(float(average_precision_score(y_canary, scores)), 6),
            "roc_auc": round(float(roc_auc_score(y_canary, scores)), 6),
            "learned_ranking": _ranking(canary, scores),
            "shape_only_ranking": _ranking(canary, baseline_scores),
            "recovered_pair_count": len(recovered),
            "recovered_pairs": recovered,
            "false_positives": false_positives,
        },
        "logo_prototype_veto": {
            "role": "sponsor-only corroborative veto; never promotes",
            "prototype_source": "training paints only; OOF selection excludes query paint",
            "veto_threshold": round(float(sponsor_veto_threshold), 6),
            "train_oof": sponsor_train_metrics,
            "canary": sponsor_canary_metrics,
            "canary_false_positives": [
                {
                    "paint_label": row["paint_label"],
                    "candidate_instance_id": row["right_instance_id"],
                    "score": round(float(score), 6),
                    "sponsor_advantage": round(float(advantage), 6),
                }
                for row, truth, score, advantage in sponsor_kept if not truth
            ],
        },
        "mutual_family_consistency": {
            "role": "bidirectional corroboration only; never creates an anchor or ownership",
            "threshold_source": "paint-grouped OOF training predictions",
            "threshold": round(float(mutual_threshold), 6),
            "train_oof": mutual_train_metrics,
            "canary": mutual_canary_metrics,
            "recovered_family_count": mutual_family_count,
            "accepted": mutual_accepted,
            "diagnostics": mutual_diagnostics,
        },
        "baseline_no_family_assembler": {
            "true_positive": 0, "false_positive": 0,
            "false_negative": int(np.sum(y_canary)), "precision": None, "recall": 0.0,
        },
        "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        "shadow_integration_ready": (
            sponsor_canary_metrics["true_positive"] >= 2
            and sponsor_canary_metrics["false_positive"] == 0
        ),
        "mutual_shadow_integration_ready": (
            mutual_family_count >= 2
            and mutual_canary_metrics["true_positive"] >= 2
            and mutual_canary_metrics["false_positive"] == 0
        ),
    }


def load_banks(paths: Sequence[str | Path]) -> dict[str, Any]:
    """Combine independently built cycle banks without altering their rows."""
    banks = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]
    if not banks:
        raise ValueError("at least one pair bank is required")
    feature_names = list(banks[0].get("feature_names") or ())
    records: list[dict[str, Any]] = []
    for bank in banks:
        if list(bank.get("feature_names") or ()) != feature_names:
            raise ValueError("pair bank feature schemas do not match")
        summary = bank.get("summary") or {}
        if summary.get("casts_votes") or summary.get("ownership_authority"):
            raise ValueError("pair bank claimed runtime authority")
        records.extend(dict(row) for row in bank.get("records") or ())
    return {
        "schema": banks[0].get("schema"),
        "feature_names": feature_names,
        "records": records,
        "summary": {"casts_votes": False, "ownership_authority": False},
    }


def export_extra_trees_npz(
    model: ExtraTreesClassifier,
    feature_names: Sequence[str],
    *,
    decision_threshold: float,
    mutual_threshold: float,
    single_pair_enabled: bool = True,
    output: str | Path,
    version: str,
) -> None:
    """Serialize a sklearn forest as portable numeric arrays, never pickle."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    offsets = [0]
    children_left: list[int] = []
    children_right: list[int] = []
    split_feature: list[int] = []
    split_threshold: list[float] = []
    positive_probability: list[float] = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        node_count = int(tree.node_count)
        base = offsets[-1]
        children_left.extend(
            int(value + base) if value >= 0 else -1 for value in tree.children_left
        )
        children_right.extend(
            int(value + base) if value >= 0 else -1 for value in tree.children_right
        )
        split_feature.extend(int(value) for value in tree.feature)
        split_threshold.extend(float(value) for value in tree.threshold)
        for values in tree.value[:, 0, :]:
            total = float(np.sum(values))
            positive_probability.append(float(values[1] / total) if total else 0.0)
        offsets.append(base + node_count)
    metadata = {
        "schema": "smart-tga-number-family-extra-trees-v1",
        "version": version,
        "decision_threshold": float(decision_threshold),
        "mutual_threshold": float(mutual_threshold),
        "single_pair_enabled": bool(single_pair_enabled),
        "tree_count": len(model.estimators_),
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }
    np.savez_compressed(
        output_path,
        metadata_json=np.asarray(json.dumps(metadata), dtype=np.str_),
        feature_names=np.asarray(list(feature_names), dtype=np.str_),
        tree_offsets=np.asarray(offsets, dtype=np.int32),
        children_left=np.asarray(children_left, dtype=np.int32),
        children_right=np.asarray(children_right, dtype=np.int32),
        split_feature=np.asarray(split_feature, dtype=np.int32),
        split_threshold=np.asarray(split_threshold, dtype=np.float64),
        positive_probability=np.asarray(positive_probability, dtype=np.float64),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", action="append", required=True)
    parser.add_argument("--train-cycle", action="append", required=True)
    parser.add_argument("--canary-cycle", action="append", required=True)
    parser.add_argument("--min-train-precision", type=float, default=0.95)
    parser.add_argument(
        "--model", choices=("logistic", "extra_trees", "random_forest"),
        default="logistic",
    )
    parser.add_argument("--exclude-group-features", action="store_true")
    parser.add_argument("--portable-model-output")
    parser.add_argument("--model-version", default="development")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bank = load_banks(args.bank)
    report = evaluate(
        bank,
        train_cycles=set(args.train_cycle), canary_cycles=set(args.canary_cycle),
        min_train_precision=args.min_train_precision, model_kind=args.model,
        include_group_features=not args.exclude_group_features,
    )
    if args.portable_model_output:
        if args.model != "extra_trees":
            raise ValueError("portable model export currently requires extra_trees")
        names = list(report["feature_names"])
        train_rows = [
            row for row in bank.get("records") or ()
            if str(row.get("cycle")) in set(args.train_cycle)
        ]
        portable_model = _model("extra_trees")
        portable_model.fit(
            _matrix(train_rows, names),
            np.asarray([bool(row["truth_same_number_family"]) for row in train_rows]),
        )
        export_extra_trees_npz(
            portable_model,
            names,
            decision_threshold=float(report["threshold_selection"]["threshold"]),
            mutual_threshold=float(report["mutual_family_consistency"]["threshold"]),
            single_pair_enabled=(report["canary"]["false_positive"] == 0),
            output=args.portable_model_output,
            version=args.model_version,
        )
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "feature_names"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
