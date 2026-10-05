"""Evaluate subtype-aware Smart TGA proposal crops.

This offline tool combines known race-number crops with taxonomy-labeled
Smart TGA false-positive crops, rebuilds clean context crops from the original
iRacing TGA files, and trains a lightweight multiclass OpenCV SVM. It is a
go/no-go diagnostic for a future number/sponsor/template/paint proposal model;
it does not wire anything into Auto-build Layers.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from smart_tga_number_candidate_miner import _read_rgb
from smart_tga_number_detector_eval import FEATURE_VERSIONS, _features


DEFAULT_NUMBER_MANIFEST = Path("_smart_tga_runs/cycle80_side_panel_hardneg_corpus_v1/manifest.json")
DEFAULT_TAXONOMY = [
    Path("_smart_tga_runs/cycle91_taxonomy_pressure_cycle90_v2/taxonomy_records.json"),
    Path("_smart_tga_runs/cycle91_taxonomy_unmatched_cycle90_v2/taxonomy_records.json"),
]
DEFAULT_OUT = Path("_smart_tga_runs/smart_tga_multiclass_proposal_eval")
WORK = 1024
HIERARCHICAL_HEADS = ("feature_svm", "visual_svm", "hybrid_visual_svm")
HIERARCHICAL_VISUAL_VERSION = "rgb_hsv_luma_edge_patch_32_24_v1"


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value)[:110] or "unknown"


def _source_from_record(rec: dict[str, Any]) -> Path | None:
    for key in ("source_path", "source", "paint", "car_num", "car"):
        raw = rec.get(key)
        if raw:
            path = Path(str(raw))
            if path.is_file():
                return path
    return None


def _box_from_record(rec: dict[str, Any]) -> list[int] | None:
    for key in ("analyzed_box", "xyxy", "box", "gt_box"):
        box = rec.get(key)
        if isinstance(box, list) and len(box) == 4:
            return [int(v) for v in box]
    return None


def _crop_from_source(source: Path, box: list[int], pad: int) -> Image.Image | None:
    rgb = _read_rgb(source, size=WORK)
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = [int(v) for v in box]
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(width, x1 + pad)
    y1 = min(height, y1 + pad)
    crop = rgb[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    return Image.fromarray(crop).convert("RGB")


def _normalize_subtype_family(subtype: str) -> str:
    if subtype in {"sponsor_logo", "sponsor_logo_fragment", "sponsor_logo_or_livery_mark"}:
        return "sponsor_logo_or_mark"
    if subtype in {"sponsor_wordmark_fragment", "sponsor_text_or_contingency_stack", "sponsor_contingency_panel"}:
        return "sponsor_text_or_contingency"
    if subtype == "sponsor_panel_or_logo_block":
        return "sponsor_panel_or_block"
    if subtype in {"ocr_digit_false_positive", "number_like_confuser"}:
        return "number_like_confuser"
    if subtype in {"paint_livery_stripe", "misc_paint_or_shape", "paint_or_shape"}:
        return "paint_or_livery_shape"
    return subtype


def _taxonomy_class(subtype: str, class_mode: str, subtype_normalization: str = "none") -> str:
    if subtype_normalization == "family":
        subtype = _normalize_subtype_family(subtype)
    if class_mode == "binary":
        return "non_number"
    if class_mode == "fine":
        return subtype
    if subtype.startswith("sponsor_"):
        return "sponsor_or_logo"
    if subtype == "template_or_body_part":
        return "template_or_body_part"
    if subtype == "ocr_digit_false_positive":
        return "ocr_digit_false_positive"
    if subtype == "number_like_confuser":
        return "number_like_confuser"
    return "paint_or_shape"


def _group_for(rec: dict[str, Any], source: Path | None) -> str:
    folder = str(rec.get("folder") or (source.parent.name if source else "unknown"))
    stem = source.stem if source else Path(str(rec.get("file", "unknown"))).stem
    return f"{folder}/{stem}"


def _materialize_crop(
    source: Path | None,
    box: list[int] | None,
    fallback: Path | None,
    out_path: Path,
    pad: int,
) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if source is not None and box is not None:
        crop = _crop_from_source(source, box, pad)
        if crop is not None:
            crop.save(out_path)
            return True
    if fallback is not None and fallback.is_file():
        shutil.copyfile(fallback, out_path)
        return True
    return False


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_number_records(manifest_path: Path, crop_dir: Path, pad: int, limit: int | None) -> list[dict[str, Any]]:
    source_records = _read_json(manifest_path)
    rows: list[dict[str, Any]] = []
    for idx, rec in enumerate(source_records):
        if rec.get("label") != "number":
            continue
        source = _source_from_record(rec)
        box = _box_from_record(rec)
        fallback = Path(str(rec.get("file", ""))) if rec.get("file") else None
        crop_path = crop_dir / "number" / f"number_{idx:04d}_{_safe_name(str(rec.get('folder') or 'source'))}.png"
        if not _materialize_crop(source, box, fallback, crop_path, pad):
            continue
        rows.append({
            "file": str(crop_path.resolve()),
            "truth": "number",
            "subtype": "number",
            "source": str(source or fallback or ""),
            "group": _group_for(rec, source),
            "origin": "number_manifest",
            "source_index": idx,
        })
        if limit and len(rows) >= limit:
            break
    return rows


def _load_taxonomy_records(
    paths: list[Path],
    crop_dir: Path,
    pad: int,
    class_mode: str,
    subtype_normalization: str = "none",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        source_records = _read_json(path)
        for idx, rec in enumerate(source_records):
            subtype = str(rec.get("subtype") or "unknown")
            truth = _taxonomy_class(subtype, class_mode, subtype_normalization)
            source = _source_from_record(rec)
            box = _box_from_record(rec)
            fallback = Path(str(rec.get("record_file") or rec.get("crop_file") or rec.get("file") or ""))
            crop_path = crop_dir / truth / f"{_safe_name(truth)}_{len(rows):04d}_{_safe_name(str(rec.get('folder') or 'source'))}.png"
            if not _materialize_crop(source, box, fallback if fallback.is_file() else None, crop_path, pad):
                continue
            rows.append({
                "file": str(crop_path.resolve()),
                "truth": truth,
                "subtype": subtype,
                "source": str(source or fallback or ""),
                "source_path": str(source or ""),
                "analyzed_box": box,
                "group": _group_for(rec, source),
                "origin": str(path),
                "source_index": idx,
                "rank": rec.get("best_rank") or rec.get("rank"),
                "score": rec.get("best_score") or rec.get("score"),
                "features": rec.get("features") or {},
                "number_stroke_score": (rec.get("features") or {}).get("number_stroke_score"),
            })
    return rows


def _load_manifest_hard_negatives(
    paths: list[Path],
    crop_dir: Path,
    pad: int,
    class_mode: str,
    subtype_normalization: str = "none",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        source_records = _read_json(path)
        for idx, rec in enumerate(source_records):
            if rec.get("label") == "number":
                continue
            subtype = str(rec.get("subtype") or rec.get("label") or "reviewed_hard_negative")
            truth = _taxonomy_class(subtype, class_mode, subtype_normalization)
            source = _source_from_record(rec)
            box = _box_from_record(rec)
            fallback = Path(str(rec.get("record_file") or rec.get("crop_file") or rec.get("file") or ""))
            crop_path = crop_dir / truth / f"manifest_hard_negative_{len(rows):04d}_{_safe_name(str(rec.get('folder') or 'source'))}.png"
            if not _materialize_crop(source, box, fallback if fallback.is_file() else None, crop_path, pad):
                continue
            rows.append({
                "file": str(crop_path.resolve()),
                "truth": truth,
                "subtype": subtype,
                "source": str(source or fallback or ""),
                "source_path": str(source or ""),
                "analyzed_box": box,
                "group": _group_for(rec, source),
                "origin": str(path),
                "source_index": idx,
                "review_index": rec.get("review_index"),
                "review_source": rec.get("review_source"),
                "features": rec.get("features") or {},
                "number_stroke_score": (rec.get("features") or {}).get("number_stroke_score"),
            })
    return rows


def _balanced_cap(records: list[dict[str, Any]], max_per_class: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_class[str(rec["truth"])].append(rec)
    capped: list[dict[str, Any]] = []
    for label in sorted(by_class):
        items = list(by_class[label])
        rng.shuffle(items)
        capped.extend(items[:max_per_class])
    capped.sort(key=lambda rec: (str(rec["truth"]), str(rec["group"]), str(rec["file"])))
    return capped


def _fold_rare_non_number_classes(
    records: list[dict[str, Any]],
    raw_counts: Counter,
    min_samples: int,
    rare_label: str | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not rare_label:
        return records, {}
    folded: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for rec in records:
        truth = str(rec["truth"])
        if truth != "number" and raw_counts[truth] < min_samples:
            new_rec = dict(rec)
            new_rec["raw_truth"] = truth
            new_rec["truth"] = rare_label
            folded[truth] = folded.get(truth, 0) + 1
            out.append(new_rec)
        else:
            out.append(rec)
    return out, folded


def _normalize_holdout_truths(
    holdout: list[dict[str, Any]],
    label_to_id: dict[str, int],
    rare_label: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for rec in holdout:
        truth = str(rec["truth"])
        if truth in label_to_id:
            normalized.append(rec)
            continue
        if rare_label and truth != "number" and rare_label in label_to_id:
            new_rec = dict(rec)
            new_rec["raw_truth"] = truth
            new_rec["truth"] = rare_label
            normalized.append(new_rec)
            continue
        dropped.append({
            "truth": truth,
            "subtype": rec.get("subtype"),
            "source": rec.get("source") or rec.get("source_path"),
            "file": rec.get("file"),
        })
    return normalized, dropped


def _make_stratified_folds(records: list[dict[str, Any]], fold_count: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    folds: list[list[int]] = [[] for _ in range(fold_count)]
    by_class: dict[str, list[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        by_class[str(rec["truth"])].append(idx)
    for label in sorted(by_class):
        indexes = list(by_class[label])
        rng.shuffle(indexes)
        for offset, idx in enumerate(indexes):
            folds[offset % fold_count].append(idx)
    return [sorted(fold) for fold in folds if fold]


def _make_group_folds(records: list[dict[str, Any]], fold_count: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    group_indexes: dict[str, list[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        group_indexes[str(rec["group"])].append(idx)
    group_rows: list[dict[str, Any]] = []
    for group, indexes in group_indexes.items():
        counts = Counter(str(records[idx]["truth"]) for idx in indexes)
        group_rows.append({"group": group, "indexes": indexes, "count": len(indexes), "classes": counts, "jitter": rng.random()})
    group_rows.sort(key=lambda row: (-int(row["count"]), -len(row["classes"]), float(row["jitter"])))
    folds: list[list[int]] = [[] for _ in range(fold_count)]
    fold_counts = [Counter() for _ in range(fold_count)]
    fold_sizes = [0 for _ in range(fold_count)]
    class_totals = Counter(str(rec["truth"]) for rec in records)
    targets = {label: count / max(1, fold_count) for label, count in class_totals.items()}
    for row in group_rows:
        best = min(
            range(fold_count),
            key=lambda fold: (
                sum(abs((fold_counts[fold][label] + row["classes"].get(label, 0)) - targets[label]) for label in targets),
                fold_sizes[fold],
            ),
        )
        folds[best].extend(row["indexes"])
        fold_counts[best].update(row["classes"])
        fold_sizes[best] += int(row["count"])
    return [sorted(fold) for fold in folds if fold]


def _class_weight_vector(labels: list[str], non_number_weight: float) -> np.ndarray | None:
    if abs(non_number_weight - 1.0) < 1e-6 or "non_number" not in labels:
        return None
    weights = np.ones((len(labels), 1), dtype=np.float32)
    weights[labels.index("non_number"), 0] = float(non_number_weight)
    return weights


def _train_svm(
    x: np.ndarray,
    y: np.ndarray,
    kernel: str,
    c_value: float,
    gamma: float,
    class_weights: np.ndarray | None = None,
) -> cv2.ml_SVM:
    svm = cv2.ml.SVM_create()
    svm.setType(cv2.ml.SVM_C_SVC)
    svm.setC(float(c_value))
    if class_weights is not None:
        svm.setClassWeights(class_weights)
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


def _raw_scores(svm: cv2.ml_SVM, x: np.ndarray) -> np.ndarray:
    _ok, score = svm.predict(x.astype(np.float32), flags=cv2.ml.StatModel_RAW_OUTPUT)
    return score.ravel().astype(np.float32)


def _orient_non_number_scores(
    svm: cv2.ml_SVM,
    x_train: np.ndarray,
    y_train: np.ndarray,
    non_number_id: int,
) -> tuple[np.ndarray, float]:
    raw = _raw_scores(svm, x_train)
    non_number_mean = float(np.mean(raw[y_train == non_number_id])) if np.any(y_train == non_number_id) else 0.0
    other_mean = float(np.mean(raw[y_train != non_number_id])) if np.any(y_train != non_number_id) else 0.0
    direction = 1.0 if non_number_mean >= other_mean else -1.0
    return raw * direction, direction


def _binary_threshold_metrics(
    scores: np.ndarray,
    truth: np.ndarray,
    labels: list[str],
    thresholds: list[float],
) -> list[dict[str, Any]]:
    non_number_id = labels.index("non_number")
    number_id = labels.index("number")
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        pred = np.where(scores >= threshold, non_number_id, number_id).astype(np.int32)
        nn_truth = truth == non_number_id
        num_truth = truth == number_id
        nn_pred = pred == non_number_id
        num_pred = pred == number_id
        nn_tp = int(np.logical_and(nn_truth, nn_pred).sum())
        num_tp = int(np.logical_and(num_truth, num_pred).sum())
        nn_fp = int(np.logical_and(num_truth, nn_pred).sum())
        num_fp = int(np.logical_and(nn_truth, num_pred).sum())
        correct = int((pred == truth).sum())
        nn_recall = nn_tp / max(1, int(nn_truth.sum()))
        num_recall = num_tp / max(1, int(num_truth.sum()))
        nn_precision = nn_tp / max(1, nn_tp + nn_fp)
        num_precision = num_tp / max(1, num_tp + num_fp)
        rows.append({
            "threshold": round(float(threshold), 6),
            "accuracy": round(correct / max(1, len(truth)), 6),
            "non_number_recall": round(nn_recall, 6),
            "number_recall": round(num_recall, 6),
            "non_number_precision": round(nn_precision, 6),
            "number_precision": round(num_precision, 6),
            "non_number_caught": nn_tp,
            "number_kept": num_tp,
            "non_number_total": int(nn_truth.sum()),
            "number_total": int(num_truth.sum()),
            "number_false_non_number": nn_fp,
            "non_number_missed": num_fp,
        })
    return rows


def _binary_labels_from_records(records: list[dict[str, Any]]) -> tuple[list[str], np.ndarray]:
    labels = ["non_number", "number"]
    y = np.asarray([1 if str(rec["truth"]) == "number" else 0 for rec in records], dtype=np.int32)
    return labels, y


def _non_number_gate_summary(
    truth_binary: np.ndarray,
    pred_binary: np.ndarray,
) -> dict[str, Any]:
    non_number_truth = truth_binary == 0
    number_truth = truth_binary == 1
    non_number_pred = pred_binary == 0
    number_pred = pred_binary == 1
    non_number_caught = int(np.logical_and(non_number_truth, non_number_pred).sum())
    non_number_missed_as_number = int(np.logical_and(non_number_truth, number_pred).sum())
    number_kept = int(np.logical_and(number_truth, number_pred).sum())
    number_lost = int(np.logical_and(number_truth, non_number_pred).sum())
    correct = int((truth_binary == pred_binary).sum())
    return {
        "samples": int(len(truth_binary)),
        "accuracy": round(correct / max(1, int(len(truth_binary))), 6),
        "non_number_caught": non_number_caught,
        "non_number_total": int(non_number_truth.sum()),
        "non_number_recall": round(non_number_caught / max(1, int(non_number_truth.sum())), 6),
        "non_number_missed_as_number": non_number_missed_as_number,
        "number_kept": number_kept,
        "number_total": int(number_truth.sum()),
        "number_recall": round(number_kept / max(1, int(number_truth.sum())), 6),
        "number_lost_to_non_number": number_lost,
    }


def _visual_patch_features(path: str | Path) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("RGB").resize((48, 48), Image.Resampling.LANCZOS), dtype=np.uint8)
    rgb32 = cv2.resize(arr, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32).reshape(-1) / 255.0
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 0] /= 179.0
    hsv[:, :, 1] /= 255.0
    hsv[:, :, 2] /= 255.0
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 35, 130)
    hsv24 = cv2.resize(hsv, (24, 24), interpolation=cv2.INTER_AREA).astype(np.float32).reshape(-1)
    gray24 = cv2.resize(gray, (24, 24), interpolation=cv2.INTER_AREA).astype(np.float32).reshape(-1) / 255.0
    edge24 = cv2.resize(edges, (24, 24), interpolation=cv2.INTER_AREA).astype(np.float32).reshape(-1) / 255.0
    global_stats = np.concatenate([
        arr.reshape(-1, 3).mean(axis=0) / 255.0,
        arr.reshape(-1, 3).std(axis=0) / 128.0,
        hsv.reshape(-1, 3).mean(axis=0),
        hsv.reshape(-1, 3).std(axis=0),
        np.asarray([gray.mean() / 255.0, gray.std() / 128.0, edges.mean() / 255.0], dtype=np.float32),
    ]).astype(np.float32)
    quadrant_stats: list[float] = []
    for y0, y1 in ((0, 24), (24, 48)):
        for x0, x1 in ((0, 24), (24, 48)):
            qgray = gray[y0:y1, x0:x1]
            qedges = edges[y0:y1, x0:x1]
            qhsv = hsv[y0:y1, x0:x1]
            quadrant_stats.extend([
                float(qgray.mean()) / 255.0,
                float(qgray.std()) / 128.0,
                float(qedges.mean()) / 255.0,
                float(qhsv[:, :, 1].mean()),
                float(qhsv[:, :, 2].mean()),
            ])
    return np.concatenate([
        rgb32,
        hsv24,
        gray24,
        edge24,
        global_stats,
        np.asarray(quadrant_stats, dtype=np.float32),
    ]).astype(np.float32)


def _standardize_pair(train_x: np.ndarray, holdout_x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0)
    std = train_x.std(axis=0)
    std[std < 1e-6] = 1.0
    return ((train_x - mean) / std).astype(np.float32), ((holdout_x - mean) / std).astype(np.float32)


def _hierarchical_head_matrix(
    args: argparse.Namespace,
    records: list[dict[str, Any]],
    x: np.ndarray,
    holdout: list[dict[str, Any]],
    holdout_x: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
    head: str,
) -> tuple[np.ndarray, np.ndarray, str]:
    feature_train = ((x - mean) / std).astype(np.float32)
    feature_holdout = ((holdout_x - mean) / std).astype(np.float32)
    if head == "feature_svm":
        return feature_train, feature_holdout, FEATURE_VERSIONS[args.feature_set]
    visual_train = np.stack([_visual_patch_features(rec["file"]) for rec in records]).astype(np.float32)
    visual_holdout = np.stack([_visual_patch_features(rec["file"]) for rec in holdout]).astype(np.float32)
    if head == "visual_svm":
        train_head, holdout_head = _standardize_pair(visual_train, visual_holdout)
        return train_head, holdout_head, HIERARCHICAL_VISUAL_VERSION
    if head == "hybrid_visual_svm":
        train_head = np.concatenate([feature_train, visual_train], axis=1).astype(np.float32)
        holdout_head = np.concatenate([feature_holdout, visual_holdout], axis=1).astype(np.float32)
        train_head, holdout_head = _standardize_pair(train_head, holdout_head)
        return train_head, holdout_head, f"{FEATURE_VERSIONS[args.feature_set]}+{HIERARCHICAL_VISUAL_VERSION}"
    raise ValueError(f"unsupported hierarchical head: {head}")


def _hierarchical_holdout_report(
    args: argparse.Namespace,
    records: list[dict[str, Any]],
    x: np.ndarray,
    holdout: list[dict[str, Any]],
    holdout_x: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
) -> dict[str, Any] | None:
    if not args.hierarchical_report or not holdout:
        return None
    binary_labels, binary_y = _binary_labels_from_records(records)
    truth_binary = np.asarray([1 if str(rec["truth"]) == "number" else 0 for rec in holdout], dtype=np.int32)
    heads = list(HIERARCHICAL_HEADS) if args.hierarchical_head == "all" else [args.hierarchical_head]
    summaries: dict[str, dict[str, Any]] = {}
    train_predictions: dict[str, np.ndarray] = {}
    holdout_predictions: dict[str, np.ndarray] = {}

    def _write_head_summary(
        head: str,
        head_version: str,
        pred_binary: np.ndarray,
        pred_train: np.ndarray | None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        records_out: list[dict[str, Any]] = []
        misses: list[dict[str, Any]] = []
        for idx, rec in enumerate(holdout):
            item = dict(rec)
            item["hier_truth"] = "number" if int(truth_binary[idx]) == 1 else "non_number"
            item["hier_pred"] = "number" if int(pred_binary[idx]) == 1 else "non_number"
            item["hierarchical_head"] = head
            item["pred"] = item["hier_pred"]
            records_out.append(item)
            if int(pred_binary[idx]) != int(truth_binary[idx]):
                misses.append(item)
        suffix = "" if len(heads) == 1 and head == "feature_svm" else f"_{head}"
        records_path = args.output / f"holdout_hierarchical{suffix}_records.json"
        mistakes_path = args.output / f"holdout_hierarchical{suffix}_mistakes_contact_sheet.png"
        records_path.write_text(json.dumps(records_out, indent=2), encoding="utf-8")
        _contact_sheet(
            misses,
            mistakes_path,
            f"Smart TGA hierarchical {head} number-gate mistakes",
            max_items=args.sheet_items,
        )
        summary = _non_number_gate_summary(truth_binary, pred_binary)
        summary.update({
            "mode": "binary_number_gate_then_existing_family_labels",
            "hierarchical_head": head,
            "head_feature_version": head_version,
            "records": str(records_path.resolve()),
            "mistakes": len(misses),
            "mistakes_sheet": str(mistakes_path.resolve()) if misses else None,
        })
        if extra:
            summary.update(extra)
        if pred_train is not None:
            summary["train_gate_summary"] = _non_number_gate_summary(binary_y, pred_train)
        return summary

    for head in heads:
        train_x, holdout_head_x, head_version = _hierarchical_head_matrix(args, records, x, holdout, holdout_x, mean, std, head)
        binary_svm = _train_svm(
            train_x,
            binary_y,
            args.svm_kernel,
            args.svm_c,
            args.svm_gamma,
            _class_weight_vector(binary_labels, args.non_number_weight),
        )
        pred_binary = _predict(binary_svm, holdout_head_x)
        pred_train = _predict(binary_svm, train_x)
        train_predictions[head] = pred_train
        holdout_predictions[head] = pred_binary
        if head == "feature_svm":
            train_scores, feature_score_direction = _orient_non_number_scores(binary_svm, train_x, binary_y, 0)
            holdout_predictions["_feature_non_number_scores"] = _raw_scores(binary_svm, holdout_head_x) * feature_score_direction
            train_predictions["_feature_non_number_scores"] = train_scores
        summaries[head] = _write_head_summary(head, head_version, pred_binary, pred_train)
    if args.hierarchical_head == "all" and {"feature_svm", "visual_svm"}.issubset(holdout_predictions):
        ensemble_version = f"{FEATURE_VERSIONS[args.feature_set]}|{HIERARCHICAL_VISUAL_VERSION}"
        feature_holdout = holdout_predictions["feature_svm"]
        visual_holdout = holdout_predictions["visual_svm"]
        feature_train = train_predictions["feature_svm"]
        visual_train = train_predictions["visual_svm"]
        feature_holdout_scores = holdout_predictions.get("_feature_non_number_scores")
        feature_train_scores = train_predictions.get("_feature_non_number_scores")
        ensemble_defs = {
            "feature_or_visual_svm": (
                np.where((feature_holdout == 0) | (visual_holdout == 0), 0, 1).astype(np.int32),
                np.where((feature_train == 0) | (visual_train == 0), 0, 1).astype(np.int32),
                None,
            ),
            "feature_and_visual_svm": (
                np.where((feature_holdout == 0) & (visual_holdout == 0), 0, 1).astype(np.int32),
                np.where((feature_train == 0) & (visual_train == 0), 0, 1).astype(np.int32),
                None,
            ),
        }
        if feature_holdout_scores is not None and feature_train_scores is not None:
            number_train_scores = np.asarray(feature_train_scores)[binary_y == 1]
            if number_train_scores.size:
                for quantile, suffix in ((100.0, "p100"), (99.0, "p99"), (95.0, "p95")):
                    threshold = float(np.percentile(number_train_scores, quantile))
                    guarded_holdout = np.where(
                        (feature_holdout == 0) | ((visual_holdout == 0) & (feature_holdout_scores >= threshold)),
                        0,
                        1,
                    ).astype(np.int32)
                    guarded_train = np.where(
                        (feature_train == 0) | ((visual_train == 0) & (feature_train_scores >= threshold)),
                        0,
                        1,
                    ).astype(np.int32)
                    ensemble_defs[f"feature_guarded_visual_svm_{suffix}"] = (
                        guarded_holdout,
                        guarded_train,
                        {
                            "feature_guard_quantile": quantile,
                            "feature_non_number_score_threshold": round(threshold, 6),
                            "guard_rule": (
                                "non_number if feature head says non_number, or visual head says non_number "
                                "and feature non-number score is at/above the selected train-number quantile"
                            ),
                        },
                    )
        for head, (pred_binary, pred_train, extra) in ensemble_defs.items():
            summaries[head] = _write_head_summary(head, ensemble_version, pred_binary, pred_train, extra)
    if len(summaries) == 1:
        return next(iter(summaries.values()))
    best_head, best_summary = max(
        summaries.items(),
        key=lambda item: (
            float(item[1].get("non_number_recall", 0.0)),
            float(item[1].get("number_recall", 0.0)),
            float(item[1].get("accuracy", 0.0)),
        ),
    )
    return {
        "mode": "binary_number_gate_head_comparison",
        "heads": summaries,
        "best_head_by_non_number_recall": best_head,
        "best_head_summary": best_summary,
    }


def _thresholds_from_scores(scores: np.ndarray, steps: int) -> list[float]:
    if scores.size == 0:
        return [0.0]
    lo = float(np.min(scores))
    hi = float(np.max(scores))
    if abs(hi - lo) < 1e-6:
        return [lo]
    values = np.linspace(lo - 1e-6, hi + 1e-6, max(3, int(steps)))
    return [float(value) for value in values]


def _summarize_frontier(rows: list[dict[str, Any]], min_number_recall: float) -> dict[str, Any]:
    if not rows:
        return {}
    best_accuracy = max(rows, key=lambda row: (float(row["accuracy"]), float(row["non_number_recall"]), float(row["number_recall"])))
    safe_rows = [row for row in rows if float(row.get("number_recall", 0.0)) >= min_number_recall]
    best_safe = max(safe_rows, key=lambda row: (float(row["non_number_recall"]), float(row["accuracy"]))) if safe_rows else None
    balanced = max(rows, key=lambda row: (min(float(row["non_number_recall"]), float(row["number_recall"])), float(row["accuracy"])))
    return {
        "min_number_recall": round(float(min_number_recall), 6),
        "best_accuracy": best_accuracy,
        "best_balanced_recall": balanced,
        "best_safe_number_recall": best_safe,
    }


def _compact_for_stdout(value: Any) -> Any:
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, item in value.items():
            if key == "rows" and isinstance(item, list):
                compact["rows_count"] = len(item)
                continue
            compact[key] = _compact_for_stdout(item)
        return compact
    if isinstance(value, list):
        return [_compact_for_stdout(item) for item in value]
    return value


def _contact_sheet(rows: list[dict[str, Any]], out_path: Path, title: str, max_items: int = 120) -> None:
    rows = rows[:max_items]
    if not rows:
        return
    cols = 5
    cell_w = 230
    cell_h = 210
    sheet = Image.new("RGB", (cols * cell_w, int(np.ceil(len(rows) / cols)) * cell_h), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(rows):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        img = Image.open(rec["file"]).convert("RGB")
        img.thumbnail((176, 146), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 24, y + 34))
        draw.text((x + 6, y + 5), f"{idx:02d} {rec['truth']} -> {rec.get('pred', '-')}", fill=(255, 225, 120))
        draw.text((x + 6, y + 19), str(rec.get("subtype", ""))[:34], fill=(170, 220, 255))
        draw.text((x + 6, y + 184), str(rec.get("group", ""))[:34], fill=(220, 220, 220))
    draw.text((8, 8), title, fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def _holdout_eval(
    args: argparse.Namespace,
    records: list[dict[str, Any]],
    x: np.ndarray,
    y: np.ndarray,
    labels: list[str],
    label_to_id: dict[str, int],
    selected_threshold: float | None = None,
) -> dict[str, Any] | None:
    if not args.holdout_taxonomy:
        return None
    holdout_dir = args.output / "holdout_clean_crops"
    holdout = _load_taxonomy_records(
        args.holdout_taxonomy,
        holdout_dir,
        args.context_pad,
        args.class_mode,
        args.subtype_normalization,
    )
    holdout = [rec for rec in holdout if Path(str(rec["file"])).is_file()]
    holdout, dropped_holdout = _normalize_holdout_truths(holdout, label_to_id, args.rare_non_number_label)
    if not holdout:
        return {
            "taxonomy": [str(path) for path in args.holdout_taxonomy],
            "samples": 0,
            "reason": "no usable holdout records",
            "dropped_holdout_records": dropped_holdout,
        }
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1e-5] = 1.0
    train_x = (x - mean) / std
    svm = _train_svm(train_x, y, args.svm_kernel, args.svm_c, args.svm_gamma, _class_weight_vector(labels, args.non_number_weight))
    holdout_x = np.stack([_features(rec["file"], args.feature_set) for rec in holdout]).astype(np.float32)
    holdout_y = np.asarray([label_to_id[str(rec["truth"])] for rec in holdout], dtype=np.int32)
    holdout_x_norm = (holdout_x - mean) / std
    pred = _predict(svm, holdout_x_norm)
    confusion = np.zeros((len(labels), len(labels)), dtype=np.int32)
    mistakes: list[dict[str, Any]] = []
    for idx, rec in enumerate(holdout):
        truth_id = int(holdout_y[idx])
        pred_id = int(pred[idx])
        confusion[truth_id, pred_id] += 1
        rec["pred"] = labels[pred_id]
        if pred_id != truth_id:
            mistakes.append(dict(rec))
    total = int(confusion.sum())
    correct = int(np.trace(confusion))
    per_class: dict[str, dict[str, float | int]] = {}
    for idx, label in enumerate(labels):
        tp = int(confusion[idx, idx])
        fp = int(confusion[:, idx].sum() - tp)
        fn = int(confusion[idx, :].sum() - tp)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-8, precision + recall)
        per_class[label] = {
            "samples": int(confusion[idx, :].sum()),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }
    (args.output / "holdout_records.json").write_text(json.dumps(holdout, indent=2), encoding="utf-8")
    _contact_sheet(mistakes, args.output / "holdout_mistakes_contact_sheet.png", "Smart TGA external holdout mistakes", max_items=args.sheet_items)
    summary = {
        "taxonomy": [str(path) for path in args.holdout_taxonomy],
        "samples": len(holdout),
        "class_counts": dict(Counter(str(rec["truth"]) for rec in holdout)),
        "dropped_holdout_records": dropped_holdout,
        "accuracy": round(correct / max(1, total), 6),
        "confusion": confusion.tolist(),
        "per_class": per_class,
        "mistakes": len(mistakes),
        "records": str((args.output / "holdout_records.json").resolve()),
        "mistakes_sheet": str((args.output / "holdout_mistakes_contact_sheet.png").resolve()) if mistakes else None,
    }
    hierarchical_summary = _hierarchical_holdout_report(args, records, x, holdout, holdout_x_norm, mean, std)
    if hierarchical_summary is not None:
        summary["hierarchical_report"] = hierarchical_summary
    if args.binary_frontier and args.class_mode == "binary" and {"non_number", "number"}.issubset(set(labels)):
        train_scores, direction = _orient_non_number_scores(svm, train_x, y, label_to_id["non_number"])
        holdout_scores = _raw_scores(svm, holdout_x_norm) * direction
        thresholds = _thresholds_from_scores(train_scores, args.frontier_steps)
        train_frontier_rows = _binary_threshold_metrics(train_scores, y, labels, thresholds)
        train_frontier_summary = _summarize_frontier(train_frontier_rows, args.frontier_min_number_recall)
        rows = []
        non_number_id = label_to_id["non_number"]
        number_id = label_to_id["number"]
        for threshold in thresholds:
            pred_at_threshold = np.where(holdout_scores >= threshold, non_number_id, number_id).astype(np.int32)
            caught = int(np.logical_and(holdout_y == non_number_id, pred_at_threshold == non_number_id).sum())
            missed = int(np.logical_and(holdout_y == non_number_id, pred_at_threshold == number_id).sum())
            false_non_number = int(np.logical_and(holdout_y == number_id, pred_at_threshold == non_number_id).sum())
            number_kept = int(np.logical_and(holdout_y == number_id, pred_at_threshold == number_id).sum())
            rows.append({
                "threshold": round(float(threshold), 6),
                "accuracy": round(float(np.mean(pred_at_threshold == holdout_y)), 6),
                "non_number_recall": round(caught / max(1, int((holdout_y == non_number_id).sum())), 6),
                "non_number_caught": caught,
                "non_number_total": int((holdout_y == non_number_id).sum()),
                "non_number_missed": missed,
                "number_kept": number_kept,
                "number_total": int((holdout_y == number_id).sum()),
                "number_false_non_number": false_non_number,
            })
        frontier_path = args.output / "holdout_binary_threshold_frontier.json"
        frontier_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        selected = train_frontier_summary.get("best_safe_number_recall") or train_frontier_summary.get("best_balanced_recall")
        threshold_source = "cross_validated_frontier" if selected_threshold is not None else "training_scores"
        effective_threshold = float(selected_threshold) if selected_threshold is not None else (float(selected["threshold"]) if selected else float(thresholds[len(thresholds) // 2]))
        selected_pred = np.where(holdout_scores >= effective_threshold, non_number_id, number_id).astype(np.int32)
        selected_records: list[dict[str, Any]] = []
        selected_mistakes: list[dict[str, Any]] = []
        for idx, rec in enumerate(holdout):
            item = dict(rec)
            item["frontier_score"] = round(float(holdout_scores[idx]), 6)
            item["frontier_threshold"] = round(float(effective_threshold), 6)
            item["pred"] = labels[int(selected_pred[idx])]
            selected_records.append(item)
            if int(selected_pred[idx]) != int(holdout_y[idx]):
                selected_mistakes.append(item)
        selected_records_path = args.output / "holdout_selected_threshold_records.json"
        selected_records_path.write_text(json.dumps(selected_records, indent=2), encoding="utf-8")
        selected_mistakes_path = args.output / "holdout_selected_threshold_mistakes_contact_sheet.png"
        _contact_sheet(
            selected_mistakes,
            selected_mistakes_path,
            "Smart TGA selected-threshold external holdout mistakes",
            max_items=args.sheet_items,
        )
        summary["binary_threshold_frontier"] = {
            "direction": direction,
            "threshold_source": "training_scores",
            "training_summary": train_frontier_summary,
            "selected_threshold": round(float(effective_threshold), 6),
            "selected_threshold_source": threshold_source,
            "selected_records": str(selected_records_path.resolve()),
            "selected_mistakes": len(selected_mistakes),
            "selected_mistakes_sheet": str(selected_mistakes_path.resolve()) if selected_mistakes else None,
            "rows": rows,
            "frontier_file": str(frontier_path.resolve()),
        }
    return summary


def _evaluate(args: argparse.Namespace) -> dict[str, Any]:
    out = args.output
    crop_dir = out / "clean_crops"
    out.mkdir(parents=True, exist_ok=True)
    records = _load_number_records(args.number_manifest, crop_dir, args.context_pad, args.max_numbers)
    records.extend(_load_taxonomy_records(
        args.taxonomy,
        crop_dir,
        args.context_pad,
        args.class_mode,
        args.subtype_normalization,
    ))
    records.extend(_load_manifest_hard_negatives(
        args.hard_negative_manifest,
        crop_dir,
        args.context_pad,
        args.class_mode,
        args.subtype_normalization,
    ))
    records = [rec for rec in records if Path(str(rec["file"])).is_file()]
    raw_counts = Counter(str(rec["truth"]) for rec in records)
    records, folded_rare_classes = _fold_rare_non_number_classes(
        records,
        raw_counts,
        args.min_class_samples,
        args.rare_non_number_label,
    )
    folded_counts = Counter(str(rec["truth"]) for rec in records)
    records = [rec for rec in records if folded_counts[str(rec["truth"])] >= args.min_class_samples]
    records = _balanced_cap(records, args.max_per_class, args.seed)
    labels = sorted({str(rec["truth"]) for rec in records})
    label_to_id = {label: idx for idx, label in enumerate(labels)}
    if len(labels) < 2:
        raise ValueError(f"need at least two classes after filtering; got {labels}")
    manifest_path = out / "multiclass_manifest.json"
    manifest_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    x = np.stack([_features(rec["file"], args.feature_set) for rec in records]).astype(np.float32)
    y = np.asarray([label_to_id[str(rec["truth"])] for rec in records], dtype=np.int32)
    folds = _make_group_folds(records, args.fold_count, args.seed) if args.fold_mode == "group" else _make_stratified_folds(records, args.fold_count, args.seed)
    confusion = np.zeros((len(labels), len(labels)), dtype=np.int32)
    mistakes: list[dict[str, Any]] = []
    skipped_folds: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    frontier_scores: list[float] = []
    frontier_truth: list[int] = []
    frontier_enabled = args.binary_frontier and args.class_mode == "binary" and {"non_number", "number"}.issubset(set(labels))
    for fold_index, test_idx in enumerate(folds):
        train_idx = [idx for idx in range(len(records)) if idx not in test_idx]
        train_labels = set(int(y[idx]) for idx in train_idx)
        test_labels = set(int(y[idx]) for idx in test_idx)
        if len(train_labels) < 2 or len(test_labels) < 1:
            skipped_folds.append({"fold": fold_index, "reason": "not_enough_labels", "train_labels": sorted(train_labels), "test_labels": sorted(test_labels)})
            continue
        mean = x[train_idx].mean(axis=0)
        std = x[train_idx].std(axis=0)
        std[std < 1e-5] = 1.0
        x_train = (x[train_idx] - mean) / std
        x_test = (x[test_idx] - mean) / std
        svm = _train_svm(x_train, y[train_idx], args.svm_kernel, args.svm_c, args.svm_gamma, _class_weight_vector(labels, args.non_number_weight))
        pred = _predict(svm, x_test)
        if frontier_enabled:
            _train_scores, direction = _orient_non_number_scores(svm, x_train, y[train_idx], label_to_id["non_number"])
            test_scores = _raw_scores(svm, x_test) * direction
            frontier_scores.extend(float(score) for score in test_scores)
            frontier_truth.extend(int(y[idx]) for idx in test_idx)
        fold_correct = 0
        for local, idx in enumerate(test_idx):
            truth_id = int(y[idx])
            pred_id = int(pred[local])
            confusion[truth_id, pred_id] += 1
            if truth_id == pred_id:
                fold_correct += 1
            else:
                item = dict(records[idx])
                item["pred"] = labels[pred_id]
                item["fold"] = fold_index
                mistakes.append(item)
        fold_summaries.append({
            "fold": fold_index,
            "test_samples": len(test_idx),
            "accuracy": round(fold_correct / max(1, len(test_idx)), 6),
            "test_counts": dict(Counter(labels[int(y[idx])] for idx in test_idx)),
        })

    total = int(confusion.sum())
    correct = int(np.trace(confusion))
    per_class: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    recall_values: list[float] = []
    for idx, label in enumerate(labels):
        tp = int(confusion[idx, idx])
        fp = int(confusion[:, idx].sum() - tp)
        fn = int(confusion[idx, :].sum() - tp)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-8, precision + recall)
        recall_values.append(recall)
        f1_values.append(f1)
        per_class[label] = {
            "samples": int(confusion[idx, :].sum()),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }
    summary = {
        "number_manifest": str(args.number_manifest),
        "taxonomy": [str(path) for path in args.taxonomy],
        "hard_negative_manifest": [str(path) for path in args.hard_negative_manifest],
        "output": str(out.resolve()),
        "manifest": str(manifest_path.resolve()),
        "class_mode": args.class_mode,
        "subtype_normalization": args.subtype_normalization,
        "feature_set": args.feature_set,
        "feature_version": FEATURE_VERSIONS[args.feature_set],
        "fold_mode": args.fold_mode,
        "fold_count": args.fold_count,
        "svm_kernel": args.svm_kernel,
        "non_number_weight": args.non_number_weight,
        "samples": len(records),
        "class_counts": dict(Counter(str(rec["truth"]) for rec in records)),
        "raw_class_counts": dict(raw_counts),
        "folded_rare_classes": folded_rare_classes,
        "rare_non_number_label": args.rare_non_number_label,
        "labels": labels,
        "accuracy": round(correct / max(1, total), 6),
        "macro_recall": round(float(np.mean(recall_values)), 6),
        "macro_f1": round(float(np.mean(f1_values)), 6),
        "confusion": confusion.tolist(),
        "per_class": per_class,
        "folds": fold_summaries,
        "skipped_folds": skipped_folds,
        "mistakes": len(mistakes),
    }
    holdout_selected_threshold: float | None = None
    if frontier_enabled and frontier_scores:
        scores = np.asarray(frontier_scores, dtype=np.float32)
        truth = np.asarray(frontier_truth, dtype=np.int32)
        thresholds = _thresholds_from_scores(scores, args.frontier_steps)
        rows = _binary_threshold_metrics(scores, truth, labels, thresholds)
        frontier_path = out / "binary_threshold_frontier.json"
        frontier_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        frontier_summary = _summarize_frontier(rows, args.frontier_min_number_recall)
        selected = frontier_summary.get("best_safe_number_recall") or frontier_summary.get("best_balanced_recall")
        holdout_selected_threshold = float(selected["threshold"]) if selected else None
        summary["binary_threshold_frontier"] = {
            "threshold_source": "cross_validated_fold_scores",
            "frontier_file": str(frontier_path.resolve()),
            "summary": frontier_summary,
            "rows": rows,
        }
    holdout_summary = _holdout_eval(args, records, x, y, labels, label_to_id, holdout_selected_threshold)
    if holdout_summary is not None:
        summary["external_holdout"] = holdout_summary
    (out / "multiclass_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _contact_sheet(mistakes, out / "mistakes_contact_sheet.png", "Smart TGA multiclass proposal mistakes", max_items=args.sheet_items)
    _contact_sheet(records, out / "manifest_contact_sheet.png", "Smart TGA multiclass proposal manifest", max_items=args.sheet_items)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--number-manifest", type=Path, default=DEFAULT_NUMBER_MANIFEST)
    parser.add_argument("--taxonomy", type=Path, action="append", default=None)
    parser.add_argument("--hard-negative-manifest", type=Path, action="append", default=None)
    parser.add_argument("--holdout-taxonomy", type=Path, action="append", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--class-mode", choices=["binary", "coarse", "fine"], default="coarse")
    parser.add_argument(
        "--subtype-normalization",
        choices=["none", "family"],
        default="none",
        help="Optional fine/coarse taxonomy normalizer; 'family' folds equivalent sponsor/logo/paint subtype names.",
    )
    parser.add_argument("--feature-set", choices=sorted(FEATURE_VERSIONS), default="geom")
    parser.add_argument("--fold-mode", choices=["stratified", "group"], default="stratified")
    parser.add_argument("--fold-count", type=int, default=5)
    parser.add_argument("--context-pad", type=int, default=24)
    parser.add_argument("--max-per-class", type=int, default=80)
    parser.add_argument("--max-numbers", type=int, default=0, help="Optional cap on positive number crops before class balancing.")
    parser.add_argument("--min-class-samples", type=int, default=2)
    parser.add_argument(
        "--rare-non-number-label",
        default=None,
        help="Optional diagnostic label for non-number classes below --min-class-samples instead of dropping them.",
    )
    parser.add_argument("--svm-kernel", choices=["linear", "rbf"], default="linear")
    parser.add_argument("--svm-c", type=float, default=0.8)
    parser.add_argument("--svm-gamma", type=float, default=0.01)
    parser.add_argument("--non-number-weight", type=float, default=1.0, help="Optional binary-SVM class weight for non_number.")
    parser.add_argument("--binary-frontier", action="store_true", help="For binary runs, write threshold frontiers for non_number-vs-number tradeoffs.")
    parser.add_argument(
        "--hierarchical-report",
        action="store_true",
        help="For non-binary class modes, also evaluate a separate number-vs-non-number gate on the external holdout.",
    )
    parser.add_argument(
        "--hierarchical-head",
        choices=[*HIERARCHICAL_HEADS, "all"],
        default="feature_svm",
        help="Feature head for --hierarchical-report. 'all' compares feature, visual, hybrid, and feature/visual ensemble gates.",
    )
    parser.add_argument("--frontier-steps", type=int, default=41)
    parser.add_argument("--frontier-min-number-recall", type=float, default=0.90)
    parser.add_argument("--seed", type=int, default=92)
    parser.add_argument("--sheet-items", type=int, default=120)
    args = parser.parse_args()
    args.taxonomy = args.taxonomy or DEFAULT_TAXONOMY
    args.hard_negative_manifest = args.hard_negative_manifest or []
    args.max_numbers = args.max_numbers or None
    result = _evaluate(args)
    print(json.dumps(_compact_for_stdout(result), indent=2))


if __name__ == "__main__":
    main()
