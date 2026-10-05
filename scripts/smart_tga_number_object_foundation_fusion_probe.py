"""Paint-disjoint fusion of intrinsic, segment, and foundation-object evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from engine.spec_sculpt.number_context_component_features import FEATURE_NAMES
    from scripts.smart_tga_number_context_component_corpus_probe import _cycle, _paint_records, _summary
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_component_features import FEATURE_NAMES  # type: ignore
    from scripts.smart_tga_number_context_component_corpus_probe import _cycle, _paint_records, _summary  # type: ignore


PCA_COMPONENTS = 48


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _proposal_identity(paint_label, source_layer, component_index):
    """Stable proposal identity; component indexes are only unique within an owner layer."""
    return str(paint_label), str(source_layer or "numbers"), int(component_index)


def _prepare(base_train, embedding_train, base_test, embedding_test):
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    count = min(PCA_COMPONENTS, len(base_train) - 1, embedding_train.shape[1])
    pca = PCA(n_components=count, svd_solver="randomized", random_state=711).fit(embedding_train)
    train = np.column_stack((base_train, pca.transform(embedding_train)))
    test = np.column_stack((base_test, pca.transform(embedding_test)))
    scaler = StandardScaler().fit(train)
    return scaler.transform(train), scaler.transform(test), pca, scaler


def _cross_fitted(base, embeddings, truth, groups, c_value):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    output = np.zeros(len(truth), np.float32)
    for train, test in GroupKFold(min(8, len(set(groups)))).split(base, truth, groups):
        train_matrix, test_matrix, _pca, _scaler = _prepare(
            base[train], embeddings[train], base[test], embeddings[test],
        )
        model = LogisticRegression(C=c_value, class_weight="balanced", max_iter=4000, random_state=711)
        model.fit(train_matrix, truth[train])
        output[test] = model.predict_proba(test_matrix)[:, 1]
    return output


def _select(records, base, embeddings, minimum_precision=0.95):
    truth = np.asarray([item["is_number"] for item in records], bool)
    groups = np.asarray([item["paint_label"] for item in records], object)
    candidates = []
    for c_value in (0.01, 0.03, 0.1, 0.3, 1.0):
        probability = _cross_fitted(base, embeddings, truth, groups, c_value)
        for threshold in sorted(set(float(value) for value in probability), reverse=True):
            summary = _summary(records, probability >= threshold)
            if summary["component_precision"] >= minimum_precision:
                hits = int(summary["number_record_hits"].split("/")[0])
                candidates.append((hits, -summary["accepted_controls"], -c_value, threshold, c_value, probability, summary))
    if not candidates:
        raise AssertionError("no high-precision operating point")
    return max(candidates, key=lambda item: item[:3])


def _select_control_budget(records, base, embeddings, maximum_controls):
    truth = np.asarray([item["is_number"] for item in records], bool)
    groups = np.asarray([item["paint_label"] for item in records], object)
    candidates = []
    for c_value in (0.01, 0.03, 0.1, 0.3, 1.0):
        probability = _cross_fitted(base, embeddings, truth, groups, c_value)
        for threshold in sorted(set(float(value) for value in probability), reverse=True):
            summary = _summary(records, probability >= threshold)
            if summary["accepted_controls"] <= maximum_controls:
                hits = int(summary["number_record_hits"].split("/")[0])
                candidates.append((hits, summary["component_precision"], -c_value, threshold, c_value, probability, summary))
    if not candidates:
        raise AssertionError("no control-budget operating point")
    return max(candidates, key=lambda item: item[:3])


def run(
    label_root: Path, segmentation_metrics: Path, transfer_embeddings: Path,
    output: Path, model_output: Path, train_cycles=None, holdout_cycles=None,
):
    import joblib
    from sklearn.linear_model import LogisticRegression

    model_root = Path("engine/spec_sculpt/models")
    family = np.load(model_root / "smart_tga_number_context_family_cycle704_v1.npz")
    prototypes = np.asarray(family["descriptors"], np.float32)
    prototype_labels = np.asarray(family["labels"], bool)
    pixel_models = joblib.load(model_root / "smart_tga_number_context_conformal_cycle703_v1.joblib")["pixel_ensemble"]
    train_cycles = set(train_cycles if train_cycles is not None else range(681, 690))
    holdout_cycles = set(holdout_cycles if holdout_cycles is not None else (690,))
    selected_cycles = train_cycles | holdout_cycles
    paths = [path for path in sorted(label_root.glob("cycle*_numbers_v1.json")) if _cycle(path) in selected_cycles]
    records = []
    for path in paths:
        records.extend(_paint_records(Path.cwd(), path, prototypes, prototype_labels, pixel_models))

    segment_payload = _read(segmentation_metrics)["cross_fitted_precision_floor"]["scores"]
    segment = {
        _proposal_identity(item["paint_label"], item.get("source_layer", "numbers"), item["component_index"]): float(item["score"])
        for item in segment_payload
    }
    transfer = np.load(transfer_embeddings)
    transfer_layers = transfer["source_layers"] if "source_layers" in transfer.files else np.asarray(["numbers"] * len(transfer["paint_labels"]))
    transfer_map = {
        _proposal_identity(paint, layer, index): vector
        for paint, layer, index, vector in zip(
            transfer["paint_labels"], transfer_layers, transfer["component_indexes"], transfer["embeddings"]
        )
    }
    for item in records:
        key = _proposal_identity(item["paint_label"], item["source_layer"], item["component_index"])
        item["segment_score"] = segment[key]
        item["transfer_embedding"] = transfer_map[key]
    train = [item for item in records if item["cycle"] in train_cycles]
    holdout = [item for item in records if item["cycle"] in holdout_cycles]
    base_train = np.column_stack((
        np.asarray([item["vector"] for item in train], np.float32),
        np.asarray([item["segment_score"] for item in train], np.float32),
    ))
    embed_train = np.asarray([item["transfer_embedding"] for item in train], np.float32)
    # Zero-valued pseudo-embedding gives a rigorously identical CV apparatus for the Cycle710 baseline.
    baseline = _select(train, base_train, np.zeros((len(train), 1), np.float32))
    foundation = _select(train, base_train, embed_train)
    _floor_hits, _floor_neg, _floor_c_sort, floor_threshold, floor_c, floor_probability, floor_summary = foundation
    matched = _select_control_budget(train, base_train, embed_train, baseline[-1]["accepted_controls"])
    _hits, _precision, _c_sort, threshold, c_value, matched_probability, train_summary = matched

    base_holdout = np.column_stack((
        np.asarray([item["vector"] for item in holdout], np.float32),
        np.asarray([item["segment_score"] for item in holdout], np.float32),
    ))
    embed_holdout = np.asarray([item["transfer_embedding"] for item in holdout], np.float32)
    train_matrix, holdout_matrix, pca, scaler = _prepare(base_train, embed_train, base_holdout, embed_holdout)
    truth = np.asarray([item["is_number"] for item in train], bool)
    model = LogisticRegression(C=c_value, class_weight="balanced", max_iter=4000, random_state=711)
    model.fit(train_matrix, truth)
    probability = model.predict_proba(holdout_matrix)[:, 1]
    model_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_output,
        intrinsic_feature_names=np.asarray((*FEATURE_NAMES, "number_object_segment_score")),
        pca_mean=pca.mean_.astype(np.float32), pca_components=pca.components_.astype(np.float32),
        mean=scaler.mean_.astype(np.float32), scale=scaler.scale_.astype(np.float32),
        coefficient=model.coef_[0].astype(np.float32), intercept=np.asarray([model.intercept_[0]], np.float32),
        threshold=np.asarray([threshold], np.float32), efficientnet_embedding_dimensions=np.asarray([embed_train.shape[1]]),
    )
    payload = {
        "schema": "smart-tga-number-object-foundation-fusion-v1",
        "validation": "paint-disjoint stacked cross-fit; PCA, scaling, and classifier refit inside each fold",
        "proposal_identity": "paint_label + source_layer + component_index",
        "train_cycles": sorted(train_cycles), "holdout_cycles": sorted(holdout_cycles),
        "train_paints": len({item["paint_label"] for item in train}), "train_records": len(train),
        "cycle710_fusion_same_apparatus": baseline[-1],
        "foundation_fusion_precision_floor": floor_summary,
        "foundation_fusion_matched_control_budget": train_summary,
        "foundation_fusion_holdout_cycle690": _summary(holdout, probability >= threshold),
        "selected_c": c_value, "selected_threshold": threshold, "pca_components": int(pca.n_components_),
        "cross_fitted_scores": [
            {"paint_label": item["paint_label"], "source_layer": item["source_layer"], "component_index": item["component_index"],
             "review_label": item["review_label"], "is_number": item["is_number"],
             "probability": round(float(score), 6), "accepted": bool(score >= threshold)}
            for item, score in zip(train, matched_probability)
        ],
        "holdout_scores": [
            {"paint_label": item["paint_label"], "source_layer": item["source_layer"], "component_index": item["component_index"],
             "review_label": item["review_label"], "is_number": item["is_number"],
             "probability": round(float(score), 6), "accepted": bool(score >= threshold)}
            for item, score in zip(holdout, probability)
        ],
        "model_output": str(model_output).replace("\\", "/"),
        "runtime_integrated": False, "ownership_authority": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label-root", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--segmentation-metrics", type=Path, required=True)
    parser.add_argument("--transfer-embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--train-cycles", nargs="+", type=int, default=list(range(681, 690)))
    parser.add_argument("--holdout-cycles", nargs="+", type=int, default=[690])
    args = parser.parse_args()
    result = run(
        args.label_root, args.segmentation_metrics, args.transfer_embeddings, args.output, args.model_output,
        args.train_cycles, args.holdout_cycles,
    )
    compact = {key: value for key, value in result.items() if key != "holdout_scores"}
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
