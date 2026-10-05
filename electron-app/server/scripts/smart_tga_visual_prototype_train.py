"""Train/evaluate a paint-disjoint Smart TGA visual prototype margin.

Every held-out paint is compared only with immutable candidate embeddings from
other paints.  Filenames, car families, coordinates, owner masks and template
positions are never inference features.  The resulting bank is corroborative
shadow evidence only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.metrics import average_precision_score
from sklearn.model_selection import LeaveOneGroupOut


METRICS = (
    "number_minus_nonnumber_top1",
    "number_minus_nonnumber_top3",
    "number_minus_sponsor_top1",
    "number_minus_sponsor_top3",
    "number_top1",
    "number_top3",
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", action="append", required=True)
    parser.add_argument("--labels", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True)
    return parser.parse_args()


def _read(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _labels(paths: Iterable[str]) -> dict[tuple[str, str], dict[str, Any]]:
    result = {}
    for path in paths:
        for item in _read(path)["candidate_labels"]:
            key = (str(item["paint"]), str(item["family_id"]))
            if key in result:
                raise ValueError(f"duplicate label: {key}")
            result[key] = item
    return result


def _dataset(runtime_paths: Iterable[str], labels: dict[tuple[str, str], dict[str, Any]]):
    embeddings, is_number, is_sponsor, eligible, groups, records = [], [], [], [], [], []
    seen = set()
    for path in runtime_paths:
        runtime = _read(path)
        for paint in runtime["records"]:
            paint_label = str(paint["paint_label"])
            for row in paint["local_candidates"]:
                key = (paint_label, str(row["family_id"]))
                label = labels.get(key)
                if label is None:
                    raise ValueError(f"embedding candidate has no durable label: {key}")
                if key in seen:
                    raise ValueError(f"embedding candidate repeated: {key}")
                seen.add(key)
                embedding = np.asarray(row.get("visual_embedding"), np.float64)
                if embedding.ndim != 1 or not len(embedding) or not np.isfinite(embedding).all():
                    raise ValueError(f"invalid visual embedding: {key}")
                embedding /= np.linalg.norm(embedding).clip(1e-12)
                semantic = str(label["semantic"])
                embeddings.append(embedding)
                is_number.append(semantic == "Number")
                is_sponsor.append(semantic == "Sponsor")
                eligible.append(bool(row["accepted"]))
                groups.append(paint_label)
                records.append({
                    "paint": paint_label,
                    "family_id": row["family_id"],
                    "semantic": semantic,
                    "current_accepted": bool(row["accepted"]),
                    "complete_copy": bool(label.get("complete_copy", False)),
                })
    missing = sorted(set(labels) - seen)
    if missing:
        raise ValueError(f"{len(missing)} reviewed candidates absent from embedding runtimes")
    matrix = np.asarray(embeddings, np.float64)
    if matrix.ndim != 2 or len({len(item) for item in embeddings}) != 1:
        raise ValueError("embedding dimensions are not stable")
    return (
        matrix, np.asarray(is_number, bool), np.asarray(is_sponsor, bool),
        np.asarray(eligible, bool), np.asarray(groups, object), records,
    )


def _top_mean(similarity: np.ndarray, mask: np.ndarray, count: int) -> np.ndarray:
    values = similarity[:, mask]
    if not values.shape[1]:
        return np.full(similarity.shape[0], -1.0, np.float64)
    count = min(count, values.shape[1])
    partition = np.partition(values, values.shape[1] - count, axis=1)[:, -count:]
    return np.mean(partition, axis=1)


def prototype_features(
    bank: np.ndarray, bank_number: np.ndarray, bank_sponsor: np.ndarray,
    query: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return orientation-invariant visual neighborhood evidence."""
    similarity = np.asarray(query, np.float64) @ np.asarray(bank, np.float64).T
    number1 = _top_mean(similarity, bank_number, 1)
    number3 = _top_mean(similarity, bank_number, 3)
    nonnumber1 = _top_mean(similarity, ~bank_number, 1)
    nonnumber3 = _top_mean(similarity, ~bank_number, 3)
    sponsor1 = _top_mean(similarity, bank_sponsor, 1)
    sponsor3 = _top_mean(similarity, bank_sponsor, 3)
    return {
        "number_minus_nonnumber_top1": number1 - nonnumber1,
        "number_minus_nonnumber_top3": number3 - nonnumber3,
        "number_minus_sponsor_top1": number1 - sponsor1,
        "number_minus_sponsor_top3": number3 - sponsor3,
        "number_top1": number1,
        "number_top3": number3,
        "nearest_number_similarity": number1,
        "nearest_nonnumber_similarity": nonnumber1,
        "nearest_sponsor_similarity": sponsor1,
    }


def _logo_scores(
    embeddings: np.ndarray, is_number: np.ndarray, is_sponsor: np.ndarray,
    groups: np.ndarray,
) -> dict[str, np.ndarray]:
    result = {name: np.zeros(len(groups), np.float64) for name in METRICS}
    for train, test in LeaveOneGroupOut().split(embeddings, is_number, groups):
        features = prototype_features(
            embeddings[train], is_number[train], is_sponsor[train], embeddings[test],
        )
        for name in METRICS:
            result[name][test] = features[name]
    return result


def _threshold(score: np.ndarray, truth: np.ndarray, eligible: np.ndarray) -> float:
    negative = score[~truth & eligible]
    if not len(negative):
        negative = score[~truth]
    return float(np.nextafter(float(np.max(negative)), np.inf))


def _select_metric(
    embeddings: np.ndarray, is_number: np.ndarray, is_sponsor: np.ndarray,
    groups: np.ndarray, eligible: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scores = _logo_scores(embeddings, is_number, is_sponsor, groups)
    candidates = []
    for name in METRICS:
        score = scores[name]
        threshold = _threshold(score, is_number, eligible)
        accepted = score >= threshold
        candidates.append({
            "metric": name,
            "score": score,
            "threshold": threshold,
            "accepted_number": int(np.sum(accepted & is_number & eligible)),
            "accepted_negative": int(np.sum(accepted & ~is_number & eligible)),
            "average_precision": float(average_precision_score(is_number, score)),
        })
    best = max(candidates, key=lambda item: (
        item["accepted_number"], item["average_precision"],
        -METRICS.index(item["metric"]),
    ))
    return best, candidates


def _nested(
    embeddings: np.ndarray, is_number: np.ndarray, is_sponsor: np.ndarray,
    groups: np.ndarray, eligible: np.ndarray,
):
    score = np.zeros(len(groups), np.float64)
    accepted = np.zeros(len(groups), bool)
    features_out = {
        name: np.zeros(len(groups), np.float64)
        for name in METRICS + (
            "nearest_number_similarity", "nearest_nonnumber_similarity",
            "nearest_sponsor_similarity",
        )
    }
    folds = []
    for train, test in LeaveOneGroupOut().split(embeddings, is_number, groups):
        best, _ = _select_metric(
            embeddings[train], is_number[train], is_sponsor[train],
            groups[train], eligible[train],
        )
        features = prototype_features(
            embeddings[train], is_number[train], is_sponsor[train], embeddings[test],
        )
        score[test] = features[best["metric"]]
        accepted[test] = score[test] >= float(best["threshold"])
        for name in features_out:
            features_out[name][test] = features[name]
        folds.append({
            "held_out_paint": str(groups[test][0]),
            "metric": best["metric"],
            "threshold": float(best["threshold"]),
            "accepted_number": int(np.sum(accepted[test] & is_number[test] & eligible[test])),
            "accepted_negative": int(np.sum(accepted[test] & ~is_number[test] & eligible[test])),
        })
    return score, accepted, features_out, folds


def _metrics(accepted: np.ndarray, truth: np.ndarray, eligible: np.ndarray):
    final = accepted & eligible
    positive = int(np.sum(truth & eligible))
    return {
        "eligible_candidates": int(np.sum(eligible)),
        "eligible_number": positive,
        "eligible_negative": int(np.sum(~truth & eligible)),
        "accepted_number": int(np.sum(final & truth)),
        "accepted_negative": int(np.sum(final & ~truth)),
        "number_recall": float(np.sum(final & truth) / max(1, positive)),
        "precision": float(np.sum(final & truth) / max(1, np.sum(final))),
    }


def main() -> None:
    args = _arguments()
    labels = _labels(args.labels)
    embedding, number, sponsor, eligible, groups, records = _dataset(args.runtime, labels)
    nested_score, nested_accept, nested_features, folds = _nested(
        embedding, number, sponsor, groups, eligible,
    )
    best, candidates = _select_metric(
        embedding, number, sponsor, groups, eligible,
    )
    model_path = Path(args.model)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_path,
        schema=np.asarray(["smart-tga-visual-prototype-bank-v1"]),
        embedding=embedding.astype(np.float32),
        is_number=number,
        is_sponsor=sponsor,
        metric=np.asarray([best["metric"]]),
        threshold=np.asarray([best["threshold"]], np.float32),
    )
    report = {
        "schema": "smart-tga-visual-prototype-training-report-v1",
        "candidate_count": len(records),
        "paint_count": len(set(groups.tolist())),
        "embedding_dimension": int(embedding.shape[1]),
        "number_prototype_count": int(np.sum(number)),
        "sponsor_prototype_count": int(np.sum(sponsor)),
        "other_negative_prototype_count": int(np.sum(~number & ~sponsor)),
        "forbidden_authority_features": [],
        "current_gate": _metrics(np.ones(len(number), bool), number, eligible),
        "nested_paint_disjoint_gate": _metrics(nested_accept, number, eligible),
        "nested_folds": folds,
        "final_model": {
            "metric": best["metric"],
            "threshold": float(best["threshold"]),
            "accepted_number": int(best["accepted_number"]),
            "accepted_negative": int(best["accepted_negative"]),
            "model_path": str(model_path),
        },
        "candidate_search": [{
            "metric": item["metric"],
            "threshold": float(item["threshold"]),
            "accepted_number": int(item["accepted_number"]),
            "accepted_negative": int(item["accepted_negative"]),
            "average_precision": float(item["average_precision"]),
        } for item in candidates],
        "records": [{
            **record,
            "nested_score": round(float(score), 7),
            "nested_accepted": bool(accept),
            "nested_final_accepted": bool(accept and record["current_accepted"]),
            **{
                name: round(float(nested_features[name][index]), 7)
                for name in nested_features
            },
        } for index, (record, score, accept) in enumerate(
            zip(records, nested_score, nested_accept)
        )],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "candidate_count": len(records),
        "current_gate": report["current_gate"],
        "nested_paint_disjoint_gate": report["nested_paint_disjoint_gate"],
        "final_model": report["final_model"],
    }, indent=2))


if __name__ == "__main__":
    main()
