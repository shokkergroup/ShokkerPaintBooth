"""Train a source-content-disjoint, anchor-required Smart TGA family linker.

An independently established Number candidate is the only semantic authority.
Frozen D4 CLIP silhouette similarity supplies recall; appearance and intrinsic
mask/palette/texture agreement can only corroborate a link.  This research
probe never writes layer ownership or changes runtime output.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from scripts.smart_tga_local_masked_patch_train import (
        CONTROL_PAINTS,
        _decode_support,
        _load_data,
        _orbit_scores,
        _pair_sets,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_local_masked_patch_train import (  # type: ignore
        CONTROL_PAINTS,
        _decode_support,
        _load_data,
        _orbit_scores,
        _pair_sets,
    )


FEATURE_NAMES = (
    "clip_silhouette_orbit_similarity",
    "clip_appearance_orbit_similarity",
    "efficientnet_orbit_similarity",
    "palette_role_equal",
    "support_log_area_difference",
    "support_occupancy_difference",
    "orientation_invariant_elongation_difference",
    "support_compactness_difference",
    "hu_moment_distance",
    "component_log_count_difference",
    "masked_lab_mean_distance",
    "masked_lab_std_distance",
    "masked_edge_mean_difference",
    "masked_edge_std_difference",
)

MODEL_CONFIGS = (
    {"name": "raw_silhouette", "model": "raw", "blend": 0.0},
    {"name": "logistic_c01_blend025", "model": "logistic", "c": 0.1, "blend": 0.25},
    {"name": "logistic_c1_blend050", "model": "logistic", "c": 1.0, "blend": 0.50},
    {"name": "extra_depth2_blend025", "model": "extra", "depth": 2, "leaf": 6, "blend": 0.25},
    {"name": "extra_depth3_blend050", "model": "extra", "depth": 3, "leaf": 4, "blend": 0.50},
    {"name": "hist_leaf5_blend025", "model": "hist", "leaves": 5, "blend": 0.25},
    {"name": "hist_leaf7_blend050", "model": "hist", "leaves": 7, "blend": 0.50},
)


def _pixel_sha256(rgb: np.ndarray) -> str:
    """Hash decoded pixels, excluding path, filename, and container metadata."""
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("source pixels must be HxWx3 RGB")
    return hashlib.sha256(np.ascontiguousarray(rgb).tobytes()).hexdigest()


def _mask_intrinsics(rgb: np.ndarray, support: np.ndarray, component_count: int) -> np.ndarray:
    """Return translation/rotation-neutral evidence for one exact candidate."""
    if rgb.shape[:2] != support.shape or not np.any(support):
        raise ValueError("non-empty support must align with candidate RGB")
    height, width = support.shape
    area = float(np.count_nonzero(support))
    occupancy = area / float(height * width)
    elongation = abs(float(np.log(max(width, height) / max(1.0, min(width, height)))))
    contours, _ = cv2.findContours(
        support.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE,
    )
    perimeter = sum(cv2.arcLength(contour, True) for contour in contours)
    compactness = float(perimeter / max(np.sqrt(area), 1.0))
    moments = cv2.HuMoments(cv2.moments(support.astype(np.uint8))).ravel()
    hu = -np.sign(moments) * np.log10(np.maximum(np.abs(moments), 1e-30))
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_pixels = lab[support]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.magnitude(grad_x, grad_y)[support]
    return np.concatenate((
        np.asarray((
            np.log1p(area), occupancy, elongation, compactness,
            np.log1p(max(1, component_count)), edge.mean(), edge.std(),
        ), dtype=np.float32),
        hu.astype(np.float32),
        lab_pixels.mean(axis=0).astype(np.float32),
        lab_pixels.std(axis=0).astype(np.float32),
    ))


def _load_intrinsics(bank_path: Path, labels_path: Path, trace: list[dict]) -> dict:
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
    records = {row["paint"]: row for row in bank["records"]}
    source_cache: dict[str, np.ndarray] = {}
    exact_cache = {}
    source_hashes: dict[str, str] = {}
    values, palette_roles = [], []
    if len(labels) != len(trace):
        raise RuntimeError("label/metadata trace length drift")
    for row, traced in zip(labels, trace):
        paint, index = row["paint"], int(row["candidate_index"])
        if (paint, index, row["proposal_id"]) != (
            traced["paint"], traced["candidate_index"], traced["proposal_id"],
        ):
            raise RuntimeError(f"candidate trace drift at {row['review_code']}")
        record = records[paint]
        if paint not in source_cache:
            bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
            if bgr is None:
                raise FileNotFoundError(record["source_1024"])
            source_cache[paint] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            source_hashes[paint] = _pixel_sha256(source_cache[paint])
            exact_cache[paint] = np.load(record["exact_candidate_bank"], allow_pickle=False)
        exact = exact_cache[paint]
        if str(exact["proposal_ids"][index]) != row["proposal_id"]:
            raise RuntimeError(f"exact candidate ID drift at {row['review_code']}")
        x, y, width, height = map(int, exact["bboxes"][index])
        support = _decode_support(exact, index)
        rgb = source_cache[paint][y:y + height, x:x + width]
        candidate = record["candidates"][index]
        values.append(_mask_intrinsics(rgb, support, int(candidate["component_count"])))
        palette_roles.append(str(candidate["palette_role"]))
    for exact in exact_cache.values():
        exact.close()
    return {
        "values": np.asarray(values, dtype=np.float32),
        "palette_roles": np.asarray(palette_roles),
        "source_hashes": source_hashes,
        "content_groups": np.asarray([source_hashes[row["paint"]] for row in labels]),
    }


def _operational_pairs(indices: np.ndarray, data: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return Number-family positives and anchor-first Number/non-Number negatives."""
    positive, _, negative = _pair_sets(indices, data, local=False)
    anchored_negative = negative.copy()
    for row in anchored_negative:
        if data["semantic"][row[0]] != 1:
            row[0], row[1] = row[1], row[0]
        if data["semantic"][row[0]] != 1 or data["semantic"][row[1]] != 0:
            raise RuntimeError("semantic negative did not normalize to Number anchor first")
    return positive, anchored_negative


def _pair_features(
    pairs: np.ndarray,
    data: dict,
    appearance: np.ndarray,
    silhouette: np.ndarray,
    intrinsics: dict,
) -> np.ndarray:
    if not len(pairs):
        return np.empty((0, len(FEATURE_NAMES)), dtype=np.float32)
    first, second = pairs[:, 0], pairs[:, 1]
    one, two = intrinsics["values"][first], intrinsics["values"][second]
    palette_equal = (
        intrinsics["palette_roles"][first] == intrinsics["palette_roles"][second]
    ).astype(np.float32)
    # Layout: scalar geometry 0:7, Hu 7:14, Lab mean 14:17, Lab std 17:20.
    result = np.column_stack((
        _orbit_scores(silhouette, pairs),
        _orbit_scores(appearance, pairs),
        _orbit_scores(data["baseline_views"], pairs),
        palette_equal,
        np.abs(one[:, 0] - two[:, 0]),
        np.abs(one[:, 1] - two[:, 1]),
        np.abs(one[:, 2] - two[:, 2]),
        np.abs(one[:, 3] - two[:, 3]),
        np.mean(np.abs(one[:, 7:14] - two[:, 7:14]), axis=1),
        np.abs(one[:, 4] - two[:, 4]),
        np.linalg.norm(one[:, 14:17] - two[:, 14:17], axis=1) / 255.0,
        np.linalg.norm(one[:, 17:20] - two[:, 17:20], axis=1) / 255.0,
        np.abs(one[:, 5] - two[:, 5]),
        np.abs(one[:, 6] - two[:, 6]),
    )).astype(np.float32)
    if result.shape[1] != len(FEATURE_NAMES) or not np.all(np.isfinite(result)):
        raise RuntimeError("intrinsic pair feature drift")
    return result


def _pair_dataset(indices, data, appearance, silhouette, intrinsics) -> dict:
    positive, negative = _operational_pairs(np.asarray(indices, dtype=np.int64), data)
    pairs = np.concatenate((positive, negative), axis=0)
    truth = np.concatenate((
        np.ones(len(positive), dtype=bool), np.zeros(len(negative), dtype=bool),
    ))
    pair_paints = data["groups"][pairs[:, 0]]
    keys = np.asarray([
        f"{paint}|{'|'.join(sorted((str(data['blocks'][first]), str(data['blocks'][second]))))}"
        for paint, (first, second) in zip(pair_paints, pairs)
    ])
    return {
        "pairs": pairs,
        "features": _pair_features(pairs, data, appearance, silhouette, intrinsics),
        "truth": truth,
        "keys": keys,
        "control": np.asarray([paint in CONTROL_PAINTS for paint in pair_paints], dtype=bool),
        "groups": intrinsics["content_groups"][pairs[:, 0]],
    }


def _new_model(config: dict):
    if config["model"] == "logistic":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=float(config["c"]), class_weight="balanced", max_iter=2000,
                solver="liblinear", random_state=728,
            ),
        )
    if config["model"] == "extra":
        return ExtraTreesClassifier(
            n_estimators=256, max_depth=int(config["depth"]),
            min_samples_leaf=int(config["leaf"]), class_weight="balanced",
            max_features=None, random_state=728, n_jobs=1,
        )
    if config["model"] == "hist":
        return HistGradientBoostingClassifier(
            max_iter=120, learning_rate=0.05, max_leaf_nodes=int(config["leaves"]),
            min_samples_leaf=8, l2_regularization=3.0, random_state=728,
        )
    raise ValueError(f"unknown model kind: {config['model']}")


def _fit_score(config: dict, train: dict, test: dict) -> np.ndarray:
    raw = test["features"][:, 0].astype(np.float64)
    if config["model"] == "raw":
        return raw
    model = _new_model(config)
    model.fit(train["features"], train["truth"])
    corroboration = model.predict_proba(test["features"])[:, 1]
    blend = float(config["blend"])
    return raw + blend * (corroboration - 0.5)


def _constrain_one_best(score: np.ndarray, accepted: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """Keep at most one proposed family link for each normalized block pair."""
    result = np.zeros(len(score), dtype=bool)
    for key in np.unique(keys[accepted]):
        choices = np.flatnonzero(accepted & (keys == key))
        if len(choices):
            result[choices[np.argmax(score[choices])]] = True
    return result


def _safe_threshold(
    truth: np.ndarray,
    score: np.ndarray,
    keys: np.ndarray,
    control: np.ndarray,
    *,
    precision_floor: float = 0.95,
) -> float:
    choices = []
    for value in np.unique(score):
        accepted = _constrain_one_best(score, score >= value, keys)
        false = accepted & ~truth
        if np.any(false & control):
            continue
        precision = float(truth[accepted].mean()) if accepted.any() else 1.0
        if precision < precision_floor:
            continue
        choices.append((int(np.count_nonzero(accepted & truth)), precision, float(value)))
    return max(choices)[2] if choices else float(np.nextafter(score.max(), np.inf))


def _inner_oof(train_indices, data, appearance, silhouette, intrinsics, config) -> dict:
    train_indices = np.asarray(train_indices, dtype=np.int64)
    candidate_groups = intrinsics["content_groups"][train_indices]
    split = GroupKFold(n_splits=min(4, len(np.unique(candidate_groups))))
    parts = {name: [] for name in ("score", "raw", "truth", "keys", "control")}
    for fit_offset, test_offset in split.split(train_indices, groups=candidate_groups):
        fit = _pair_dataset(
            train_indices[fit_offset], data, appearance, silhouette, intrinsics,
        )
        test = _pair_dataset(
            train_indices[test_offset], data, appearance, silhouette, intrinsics,
        )
        parts["score"].extend(_fit_score(config, fit, test).tolist())
        parts["raw"].extend(test["features"][:, 0].tolist())
        for name in ("truth", "keys", "control"):
            parts[name].extend(test[name].tolist())
    return {
        "score": np.asarray(parts["score"], dtype=np.float64),
        "raw": np.asarray(parts["raw"], dtype=np.float64),
        "truth": np.asarray(parts["truth"], dtype=bool),
        "keys": np.asarray(parts["keys"]),
        "control": np.asarray(parts["control"], dtype=bool),
    }


def _select_config(train_indices, data, appearance, silhouette, intrinsics):
    candidates = []
    cached = {}
    for config in MODEL_CONFIGS:
        oof = _inner_oof(train_indices, data, appearance, silhouette, intrinsics, config)
        ap = float(average_precision_score(oof["truth"], oof["score"]))
        candidates.append((ap, config["name"]))
        cached[config["name"]] = oof
    _, selected_name = max(candidates)
    selected = next(config for config in MODEL_CONFIGS if config["name"] == selected_name)
    return selected, cached[selected_name], {name: ap for ap, name in candidates}


def _acceptance_metrics(truth, accepted, control) -> dict:
    false = accepted & ~truth
    return {
        "accepted_count": int(np.count_nonzero(accepted)),
        "accepted_true_positive_count": int(np.count_nonzero(accepted & truth)),
        "accepted_false_positive_count": int(np.count_nonzero(false)),
        "precision": round(float(truth[accepted].mean()) if accepted.any() else 1.0, 6),
        "recall": round(float(np.count_nonzero(accepted & truth) / max(1, np.count_nonzero(truth))), 6),
        "five_control_wrong_links": int(np.count_nonzero(false & control)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--baseline-embeddings", type=Path, required=True)
    parser.add_argument("--clip-embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=728)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    data = _load_data(args.bank, args.labels, args.baseline_embeddings, size=64)
    clip = np.load(args.clip_embeddings, allow_pickle=False)
    appearance = clip["appearance"].astype(np.float32)
    silhouette = clip["silhouette"].astype(np.float32)
    intrinsics = _load_intrinsics(args.bank, args.labels, data["trace"])
    indices = np.arange(len(data["groups"]), dtype=np.int64)
    content_groups = intrinsics["content_groups"]
    all_parts = {name: [] for name in (
        "score", "raw", "truth", "keys", "control", "accepted", "raw_accepted", "pairs",
    )}
    folds = []
    outer = GroupKFold(n_splits=5)
    for fold, (train, test) in enumerate(outer.split(indices, groups=content_groups)):
        selected, inner, inner_ap = _select_config(
            train, data, appearance, silhouette, intrinsics,
        )
        threshold = _safe_threshold(
            inner["truth"], inner["score"], inner["keys"], inner["control"],
        )
        raw_threshold = _safe_threshold(
            inner["truth"], inner["raw"], inner["keys"], inner["control"],
        )
        train_data = _pair_dataset(train, data, appearance, silhouette, intrinsics)
        test_data = _pair_dataset(test, data, appearance, silhouette, intrinsics)
        score = _fit_score(selected, train_data, test_data)
        raw = test_data["features"][:, 0].astype(np.float64)
        accepted = _constrain_one_best(score, score >= threshold, test_data["keys"])
        raw_accepted = _constrain_one_best(raw, raw >= raw_threshold, test_data["keys"])
        for name, values in (
            ("score", score), ("raw", raw), ("truth", test_data["truth"]),
            ("keys", test_data["keys"]), ("control", test_data["control"]),
            ("accepted", accepted), ("raw_accepted", raw_accepted),
            ("pairs", test_data["pairs"]),
        ):
            all_parts[name].extend(values.tolist())
        folds.append({
            "fold": fold,
            "test_paints": sorted(set(data["groups"][test])),
            "test_source_content_groups": len(set(content_groups[test])),
            "selected_config": selected["name"],
            "inner_ap_by_config": {name: round(value, 6) for name, value in inner_ap.items()},
            "inner_selected_ap": round(float(average_precision_score(inner["truth"], inner["score"])), 6),
            "inner_safe_threshold": round(threshold, 8),
            "inner_raw_safe_threshold": round(raw_threshold, 8),
            "test_pair_count": len(score),
            "test_accepted_count": int(np.count_nonzero(accepted)),
            "test_raw_accepted_count": int(np.count_nonzero(raw_accepted)),
        })
    score = np.asarray(all_parts["score"], dtype=np.float64)
    raw = np.asarray(all_parts["raw"], dtype=np.float64)
    truth = np.asarray(all_parts["truth"], dtype=bool)
    control = np.asarray(all_parts["control"], dtype=bool)
    accepted = np.asarray(all_parts["accepted"], dtype=bool)
    raw_accepted = np.asarray(all_parts["raw_accepted"], dtype=bool)
    pairs = np.asarray(all_parts["pairs"], dtype=np.int64)
    raw_ap = float(average_precision_score(truth, raw))
    after_ap = float(average_precision_score(truth, score))
    accepted_metrics = _acceptance_metrics(truth, accepted, control)
    raw_accepted_metrics = _acceptance_metrics(truth, raw_accepted, control)
    duplicate_sets = [
        sorted(paint for paint, value in intrinsics["source_hashes"].items() if value == digest)
        for digest, count in Counter(intrinsics["source_hashes"].values()).items() if count > 1
    ]
    learned_metric_gate = bool(
        after_ap > 0.672250
        and accepted_metrics["precision"] >= 0.90
        and accepted_metrics["five_control_wrong_links"] == 0
        and accepted_metrics["accepted_true_positive_count"] > 0
    )
    raw_metric_gate = bool(
        raw_ap > 0.672250
        and raw_accepted_metrics["precision"] >= 0.90
        and raw_accepted_metrics["five_control_wrong_links"] == 0
        and raw_accepted_metrics["accepted_true_positive_count"] > 0
    )
    metric_gate = raw_metric_gate or learned_metric_gate
    link_rows = []
    for offset, (first, second) in enumerate(pairs):
        if not (accepted[offset] or raw_accepted[offset]):
            continue
        link_rows.append({
            "paint": str(data["groups"][first]),
            "first_review_code": data["trace"][first]["review_code"],
            "second_review_code": data["trace"][second]["review_code"],
            "first_block": str(data["blocks"][first]),
            "second_block": str(data["blocks"][second]),
            "truth": bool(truth[offset]),
            "control": bool(control[offset]),
            "raw_silhouette_score": round(float(raw[offset]), 8),
            "raw_silhouette_accepted": bool(raw_accepted[offset]),
            "learned_score": round(float(score[offset]), 8),
            "learned_accepted": bool(accepted[offset]),
            "ownership_authority": False,
        })
    ledger = {
        "schema": "smart-tga-source-disjoint-anchor-extension-v1",
        "cycle": args.cycle,
        "contract": "An existing independent Number anchor is mandatory. Similarity and intrinsic agreement corroborate one cross-block family link but never create semantic or ownership authority.",
        "baseline": {
            "frozen_clip_silhouette_operational_ap_required_reference": 0.672250,
            "source_content_disjoint_oof_ap": round(raw_ap, 6),
            "calibrated_one_best": raw_accepted_metrics,
        },
        "after_nested_source_content_disjoint": {
            "operational_ap": round(after_ap, 6),
            "gain_over_source_disjoint_raw_silhouette": round(after_ap - raw_ap, 6),
            "gain_over_required_reference": round(after_ap - 0.672250, 6),
            "pair_count": len(truth),
            "positive_pair_count": int(np.count_nonzero(truth)),
            "selected_config_counts": dict(Counter(row["selected_config"] for row in folds)),
            "feature_names": list(FEATURE_NAMES),
            "calibrated_one_best": accepted_metrics,
        },
        "content_split_audit": {
            "paint_count": len(set(data["groups"])),
            "unique_source_content_count": len(set(content_groups)),
            "duplicate_source_content_sets": duplicate_sets,
            "source_hash_used_as_model_feature": False,
        },
        "gates": {
            "anchor_extension_metric_gate_passed": metric_gate,
            "frozen_silhouette_anchor_gate_passed": raw_metric_gate,
            "learned_corroborator_gate_passed": learned_metric_gate,
            "recommended_scorer": (
                "frozen_silhouette_plus_one_best_adjudication" if raw_metric_gate else
                "learned_corroborator" if learned_metric_gate else "none"
            ),
            "requires_ap_greater_than": 0.672250,
            "requires_precision_at_least": 0.90,
            "requires_zero_five_control_wrong_links": True,
            "requires_nonzero_recall": True,
            "requires_existing_number_anchor": True,
            "candidate_completeness_gate_passed": False,
            "holdout_opened": False,
            "runtime_integrated": False,
        },
        "targets": sorted(set(data["groups"]) - CONTROL_PAINTS),
        "hard_negative_controls": sorted(set(data["groups"]) & CONTROL_PAINTS),
        "folds": folds,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "clip_weights_frozen": True,
            "outer_and_inner_source_content_disjoint": True,
            "thresholds_selected_inside_outer_training_folds": True,
            "one_best_link_per_normalized_block_pair": True,
            "casts_votes": False,
            "ownership_authority": False,
            "apply_locked": True,
            "holdout_consumed": False,
            "filename_or_car_features": False,
            "source_hash_inference_feature": False,
            "absolute_bbox_inference_feature": False,
            "ocr_changed": False,
            "exact_reconstruction_affected": False,
        },
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "accepted_links.json").write_text(
        json.dumps({
            "schema": "smart-tga-anchor-extension-oof-links-v1",
            "cycle": args.cycle,
            "links": link_rows,
            "ownership_authority": False,
        }, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": ledger["baseline"],
        "after": ledger["after_nested_source_content_disjoint"],
        "content_split_audit": ledger["content_split_audit"],
        "gates": ledger["gates"],
        "elapsed_sec": ledger["elapsed_sec"],
    }, indent=2))


if __name__ == "__main__":
    main()
