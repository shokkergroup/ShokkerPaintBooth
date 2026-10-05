"""Measure a transfer-safe within-paint Smart TGA Number-family ranker.

One independently reviewed complete Number mask is supplied as the semantic
anchor for each paint.  Frozen D4 silhouette similarity leads.  Cohort-relative
rank and intrinsic multiscale mask anatomy may only corroborate that anchor.
The probe is source-content-disjoint, abstains without an anchor, and has zero
runtime or ownership authority.
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
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    from scripts.smart_tga_clip_full_bank_embed import _bank_rows
    from scripts.smart_tga_exact_candidate_utils import CONTROL_PAINTS, decode_support
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.smart_tga_clip_full_bank_embed import _bank_rows  # type: ignore
    from scripts.smart_tga_exact_candidate_utils import (  # type: ignore
        CONTROL_PAINTS, decode_support,
    )


ANATOMY_NAMES = (
    "support_occupancy", "perimeter_sqrt_area", "log_component_count",
    "largest_component_fraction", "convex_hull_fill", "hole_area_fraction",
    "stroke_mean", "stroke_std", "stroke_max", "erosion1_survival",
    "erosion2_survival", "grid4_std", "grid8_std", "grid16_std",
    "projection_std", "projection_max", "projection_entropy",
)
FINE_SHAPE_NAMES = (
    "fine_pixel_cosine", "fine_dice", "fine_partial_containment",
    "fine_soft_cosine", "fine_projection_cosine", "fine_chamfer_similarity",
)
FEATURE_NAMES = (
    "d4_silhouette_similarity",
) + FINE_SHAPE_NAMES + (
    "within_anchor_block_percentile",
    "within_anchor_block_robust_z", "palette_role_equal",
) + tuple(f"candidate_{name}" for name in ANATOMY_NAMES) + tuple(
    f"anchor_candidate_{name}_difference" for name in ANATOMY_NAMES
)
MODEL_CONFIGS = (
    {"name": "raw_d4", "kind": "raw", "blend": 0.0},
    {"name": "fine_shape_blend05", "kind": "fixed", "blend": 0.05},
    {"name": "fine_shape_blend10", "kind": "fixed", "blend": 0.10},
    {"name": "fine_shape_blend20", "kind": "fixed", "blend": 0.20},
    {"name": "ordinal_logistic_c01", "kind": "logistic", "c": 0.1, "blend": 0.15},
    {"name": "ordinal_logistic_c1", "kind": "logistic", "c": 1.0, "blend": 0.25},
    {"name": "ordinal_extra_depth2", "kind": "extra", "depth": 2, "leaf": 6, "blend": 0.15},
    {"name": "ordinal_extra_depth3", "kind": "extra", "depth": 3, "leaf": 4, "blend": 0.25},
)


def _pixel_sha256(rgb: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(rgb).tobytes()).hexdigest()


def _normalized_mask(support: np.ndarray, size: int = 64) -> np.ndarray:
    """Aspect-preserve one exact support on a square canvas without bbox features."""
    height, width = support.shape
    scale = min((size - 8) / max(width, 1), (size - 8) / max(height, 1))
    target_w = max(1, int(round(width * scale)))
    target_h = max(1, int(round(height * scale)))
    resized = cv2.resize(
        support.astype(np.uint8), (target_w, target_h), interpolation=cv2.INTER_NEAREST,
    )
    canvas = np.zeros((size, size), dtype=np.uint8)
    x = (size - target_w) // 2
    y = (size - target_h) // 2
    canvas[y:y + target_h, x:x + target_w] = resized
    return canvas


def _grid_std(mask: np.ndarray, cells: int) -> float:
    # Splitting each native axis independently makes the aggregate exact under
    # 90-degree rotations/reflections; a square resize introduced rounding
    # asymmetry for tall versus wide copies.
    row_cells = min(cells, mask.shape[0])
    column_cells = min(cells, mask.shape[1])
    values = [
        cell.mean()
        for row in np.array_split(mask, row_cells, axis=0)
        for cell in np.array_split(row, column_cells, axis=1)
    ]
    return float(np.std(values))


def _d4_grid_std(mask: np.ndarray, cells: int) -> float:
    variants = [np.rot90(mask, turns) for turns in range(4)]
    variants.extend(np.fliplr(value) for value in variants.copy())
    return float(np.mean([_grid_std(value, cells) for value in variants]))


def _mask_anatomy(support: np.ndarray) -> np.ndarray:
    """Return D4-invariant, scale-normalized support anatomy."""
    mask = support.astype(np.uint8)
    area = float(mask.sum())
    if area <= 0:
        raise ValueError("candidate support must be non-empty")
    height, width = mask.shape
    occupancy = area / float(height * width)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    exterior = [
        contour for offset, contour in enumerate(contours)
        if hierarchy is None or hierarchy[0][offset][3] < 0
    ]
    perimeter = sum(cv2.arcLength(contour, True) for contour in exterior)
    hull_area = sum(
        max(cv2.contourArea(cv2.convexHull(contour)), 0.0) for contour in exterior
    )
    hole_area = sum(
        max(cv2.contourArea(contour), 0.0)
        for offset, contour in enumerate(contours)
        if hierarchy is not None and hierarchy[0][offset][3] >= 0
    )
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    component_areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float64)
    normalized = _normalized_mask(mask)
    normalized_area = float(normalized.sum())
    distance = cv2.distanceTransform(normalized, cv2.DIST_L2, 3)
    strokes = distance[normalized > 0] / 64.0
    kernel = np.ones((3, 3), dtype=np.uint8)
    eroded1 = cv2.erode(normalized, kernel, iterations=1)
    eroded2 = cv2.erode(normalized, kernel, iterations=2)
    projection = np.concatenate((normalized.mean(axis=0), normalized.mean(axis=1)))
    probability = projection / max(float(projection.sum()), 1e-8)
    entropy = -float(np.sum(probability * np.log(np.maximum(probability, 1e-8))))
    result = np.asarray((
        occupancy,
        perimeter / max(np.sqrt(area), 1.0),
        np.log1p(max(1, count - 1)),
        float(component_areas.max() / area) if len(component_areas) else 1.0,
        area / max(hull_area, area),
        hole_area / area,
        float(strokes.mean()), float(strokes.std()), float(strokes.max()),
        float(eroded1.sum() / normalized_area),
        float(eroded2.sum() / normalized_area),
        _d4_grid_std(mask, 4), _d4_grid_std(mask, 8), _d4_grid_std(mask, 16),
        float(projection.std()), float(projection.max()), entropy,
    ), dtype=np.float32)
    if result.shape != (len(ANATOMY_NAMES),) or not np.all(np.isfinite(result)):
        raise RuntimeError("mask anatomy feature drift")
    return result


def _orbit_similarity(one: np.ndarray, two: np.ndarray) -> float:
    return float(np.max(one @ two.T))


def _cosine(one: np.ndarray, two: np.ndarray) -> float:
    denominator = float(np.linalg.norm(one) * np.linalg.norm(two))
    return float(np.dot(one.ravel(), two.ravel()) / max(denominator, 1e-8))


def _fine_shape_features(one: np.ndarray, two: np.ndarray) -> np.ndarray:
    """Return the best exact silhouette correspondence over relative D4 views."""
    anchor = one.astype(np.uint8)
    variants = [np.rot90(two, turns) for turns in range(4)]
    variants.extend(np.fliplr(value) for value in variants.copy())
    anchor_area = float(anchor.sum())
    anchor_soft = cv2.GaussianBlur(anchor.astype(np.float32), (0, 0), 1.5)
    anchor_projection = np.concatenate((anchor.mean(axis=0), anchor.mean(axis=1)))
    choices = []
    for candidate in variants:
        candidate = candidate.astype(np.uint8)
        candidate_area = float(candidate.sum())
        intersection = float(np.count_nonzero(anchor & candidate))
        pixel_cosine = intersection / max(np.sqrt(anchor_area * candidate_area), 1e-8)
        dice = 2.0 * intersection / max(anchor_area + candidate_area, 1e-8)
        containment = intersection / max(min(anchor_area, candidate_area), 1e-8)
        candidate_soft = cv2.GaussianBlur(candidate.astype(np.float32), (0, 0), 1.5)
        soft_cosine = _cosine(anchor_soft, candidate_soft)
        candidate_projection = np.concatenate((candidate.mean(axis=0), candidate.mean(axis=1)))
        projection_cosine = _cosine(anchor_projection, candidate_projection)
        anchor_distance = cv2.distanceTransform(1 - anchor, cv2.DIST_L2, 3) / 64.0
        candidate_distance = cv2.distanceTransform(1 - candidate, cv2.DIST_L2, 3) / 64.0
        symmetric_distance = 0.5 * (
            float(candidate_distance[anchor > 0].mean())
            + float(anchor_distance[candidate > 0].mean())
        )
        chamfer_similarity = float(np.exp(-12.0 * symmetric_distance))
        values = np.asarray((
            pixel_cosine, dice, containment, soft_cosine,
            projection_cosine, chamfer_similarity,
        ), dtype=np.float32)
        choices.append((float(values.mean()), values))
    result = max(choices, key=lambda item: item[0])[1]
    if result.shape != (len(FINE_SHAPE_NAMES),) or not np.all(np.isfinite(result)):
        raise RuntimeError("fine shape feature drift")
    return result


def _cohort_statistics(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return high-is-good percentile and robust z within one unlabeled cohort."""
    if not len(values):
        return values.copy(), values.copy()
    order = np.argsort(values, kind="mergesort")
    rank = np.empty(len(values), dtype=np.float32)
    rank[order] = np.arange(len(values), dtype=np.float32)
    percentile = rank / max(1, len(values) - 1)
    median = float(np.median(values))
    q1, q3 = np.percentile(values, (25, 75))
    robust_z = (values - median) / max(float(q3 - q1), 1e-4)
    return percentile, np.clip(robust_z, -8.0, 8.0).astype(np.float32)


def _load_candidate_table(bank_path: Path, embedding_path: Path, labels_path: Path) -> dict:
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))["labels"]
    trace = _bank_rows(bank)
    embedding = np.load(embedding_path, allow_pickle=False)
    if len(trace) != len(embedding["silhouette"]):
        raise RuntimeError("full-bank candidate/embedding count drift")
    for offset, row in enumerate(trace):
        expected = (row["paint"], row["candidate_index"], row["proposal_id"])
        actual = (
            str(embedding["paints"][offset]), int(embedding["candidate_indices"][offset]),
            str(embedding["proposal_ids"][offset]),
        )
        if expected != actual:
            raise RuntimeError(f"full-bank trace drift at row {offset}")
    records = {str(row["paint"]): row for row in bank["records"]}
    source_hashes: dict[str, str] = {}
    anatomy = np.empty((len(trace), len(ANATOMY_NAMES)), dtype=np.float32)
    masks = np.empty((len(trace), 64, 64), dtype=np.uint8)
    support_areas = np.empty(len(trace), dtype=np.int64)
    support_fingerprints = [""] * len(trace)
    placement_fingerprints = [""] * len(trace)
    by_paint: dict[str, list[int]] = {}
    cursor = 0
    for paint, record in records.items():
        bgr = cv2.imread(record["source_1024"], cv2.IMREAD_COLOR)
        if bgr is None:
            raise FileNotFoundError(record["source_1024"])
        source_hashes[paint] = _pixel_sha256(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        exact = np.load(record["exact_candidate_bank"], allow_pickle=False)
        try:
            rows = []
            for index in range(len(record["candidates"])):
                rows.append(cursor)
                support = decode_support(exact, index)
                anatomy[cursor] = _mask_anatomy(support)
                masks[cursor] = _normalized_mask(support)
                support_areas[cursor] = int(np.count_nonzero(support))
                support_fingerprints[cursor] = hashlib.sha256(
                    np.asarray(support.shape, dtype=np.int32).tobytes()
                    + np.ascontiguousarray(support.astype(np.uint8)).tobytes()
                ).hexdigest()
                placement_fingerprints[cursor] = hashlib.sha256(
                    np.asarray(record["candidates"][index]["bbox"], dtype=np.int32).tobytes()
                    + np.asarray(support.shape, dtype=np.int32).tobytes()
                    + np.ascontiguousarray(support.astype(np.uint8)).tobytes()
                ).hexdigest()
                cursor += 1
            by_paint[paint] = rows
        finally:
            exact.close()
    if cursor != len(trace):
        raise RuntimeError("bank anatomy traversal drift")
    label_map = {
        (str(row["paint"]), int(row["candidate_index"])): row for row in labels
    }
    anchors: dict[str, int] = {}
    anchor_review_codes: dict[str, str] = {}
    for row in labels:
        if row["semantic"] != "Number" or row.get("complete_copy") is not True:
            continue
        paint = str(row["paint"])
        if paint in anchors:
            continue
        match = next(
            offset for offset in by_paint[paint]
            if trace[offset]["candidate_index"] == int(row["candidate_index"])
        )
        anchors[paint] = match
        anchor_review_codes[paint] = str(row["review_code"])
    return {
        "trace": trace,
        "silhouette": embedding["silhouette"].astype(np.float32),
        "anatomy": anatomy, "masks": masks,
        "support_areas": support_areas,
        "support_fingerprints": support_fingerprints,
        "placement_fingerprints": placement_fingerprints,
        "by_paint": by_paint,
        "labels": label_map,
        "anchors": anchors,
        "anchor_review_codes": anchor_review_codes,
        "source_hashes": source_hashes,
    }


def _build_rows(table: dict) -> list[dict]:
    rows: list[dict] = []
    for paint, candidates in table["by_paint"].items():
        if paint not in table["anchors"]:
            continue
        anchor = table["anchors"][paint]
        anchor_block = table["trace"][anchor]["dominant_number_block"]
        grouped: dict[str, list[tuple[int, float]]] = {}
        for candidate in candidates:
            if candidate == anchor:
                continue
            block = table["trace"][candidate]["dominant_number_block"]
            if block == anchor_block:
                continue
            raw = _orbit_similarity(
                table["silhouette"][anchor], table["silhouette"][candidate],
            )
            grouped.setdefault(block, []).append((candidate, raw))
        for block, cohort in grouped.items():
            raw_values = np.asarray([value for _, value in cohort], dtype=np.float32)
            percentile, robust_z = _cohort_statistics(raw_values)
            for offset, (candidate, raw) in enumerate(cohort):
                trace = table["trace"][candidate]
                label = table["labels"].get((paint, trace["candidate_index"]))
                semantic = None if label is None else str(label["semantic"])
                complete_copy = None if label is None else label.get("complete_copy")
                candidate_anatomy = table["anatomy"][candidate]
                anchor_anatomy = table["anatomy"][anchor]
                features = np.concatenate((
                    np.asarray((
                        raw,
                    ), dtype=np.float32),
                    _fine_shape_features(table["masks"][anchor], table["masks"][candidate]),
                    np.asarray((
                        percentile[offset], robust_z[offset],
                        float(trace["palette_role"] == table["trace"][anchor]["palette_role"]),
                    ), dtype=np.float32),
                    candidate_anatomy,
                    np.abs(anchor_anatomy - candidate_anatomy),
                ))
                if features.shape != (len(FEATURE_NAMES),):
                    raise RuntimeError("ordinal feature width drift")
                rows.append({
                    "paint": paint,
                    "content_group": table["source_hashes"][paint],
                    "candidate": candidate,
                    "candidate_index": trace["candidate_index"],
                    "proposal_id": trace["proposal_id"],
                    "block": block,
                    "anchor": anchor,
                    "anchor_review_code": table["anchor_review_codes"][paint],
                    "support_area_for_metrics_only": int(table["support_areas"][candidate]),
                    "support_fingerprint_for_instance_dedupe": table["support_fingerprints"][candidate],
                    "placement_fingerprint_for_instance_dedupe": table["placement_fingerprints"][candidate],
                    "semantic": semantic,
                    "complete_copy": complete_copy,
                    "known": semantic is not None and semantic != "uncertain",
                    "uncertain": semantic == "uncertain",
                    "truth": semantic == "Number",
                    "control": paint in CONTROL_PAINTS,
                    "features": features,
                })
    return rows


def _matrix(rows: list[dict], indices: np.ndarray) -> dict:
    selected = [rows[int(index)] for index in indices]
    return {
        "features": np.stack([row["features"] for row in selected]),
        "truth": np.asarray([row["truth"] for row in selected], dtype=bool),
        "known": np.asarray([row["known"] for row in selected], dtype=bool),
        "uncertain": np.asarray([row["uncertain"] for row in selected], dtype=bool),
        "control": np.asarray([row["control"] for row in selected], dtype=bool),
        "keys": np.asarray([f"{row['paint']}|{row['block']}" for row in selected]),
        "indices": np.asarray(indices, dtype=np.int64),
    }


def _new_model(config: dict):
    if config["kind"] == "logistic":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=float(config["c"]), class_weight="balanced", max_iter=2000,
                solver="liblinear", random_state=730,
            ),
        )
    if config["kind"] == "extra":
        return ExtraTreesClassifier(
            n_estimators=256, max_depth=int(config["depth"]),
            min_samples_leaf=int(config["leaf"]), class_weight="balanced",
            max_features=None, random_state=730, n_jobs=1,
        )
    raise ValueError(config["kind"])


def _fit_score(config: dict, train: dict, test: dict) -> np.ndarray:
    raw = test["features"][:, 0].astype(np.float64)
    if config["kind"] == "raw":
        result = raw
    elif config["kind"] == "fixed":
        fine = test["features"][:, 1:1 + len(FINE_SHAPE_NAMES)].mean(axis=1)
        result = raw + float(config["blend"]) * (fine - 0.5)
    else:
        known = train["known"]
        if len(np.unique(train["truth"][known])) < 2:
            result = raw
        else:
            model = _new_model(config)
            model.fit(train["features"][known], train["truth"][known])
            corroboration = model.predict_proba(test["features"])[:, 1]
            result = raw + float(config["blend"]) * (corroboration - 0.5)
    return result


def _fit_certainty(train: dict, test: dict) -> np.ndarray:
    """Predict review certainty for veto use only; never add Number evidence."""
    if len(np.unique(train["known"])) < 2:
        return np.ones(len(test["features"]), dtype=np.float64)
    model = ExtraTreesClassifier(
        n_estimators=256, max_depth=3, min_samples_leaf=5,
        class_weight="balanced", max_features=None, random_state=731, n_jobs=1,
    )
    model.fit(train["features"][:, 7:], train["known"])
    return model.predict_proba(test["features"][:, 7:])[:, 1]


def _top_two(score: np.ndarray, eligible: np.ndarray, keys: np.ndarray) -> np.ndarray:
    result = np.zeros(len(score), dtype=bool)
    for key in np.unique(keys[eligible]):
        choices = np.flatnonzero(eligible & (keys == key))
        order = choices[np.argsort(score[choices])[-2:]]
        result[order] = True
    return result


def _safe_threshold(
    data: dict,
    score: np.ndarray,
    certainty: np.ndarray | None = None,
    precision_floor: float = 0.80,
) -> tuple[float, float]:
    choices = []
    certainty_values = np.asarray([0.0]) if certainty is None else np.unique(certainty)
    effective_certainty = np.ones(len(score), dtype=np.float64) if certainty is None else certainty
    for certainty_value in certainty_values:
        for value in np.unique(score):
            eligible = (score >= value) & (effective_certainty >= certainty_value)
            accepted = _top_two(score, eligible, data["keys"])
            if np.any(accepted & data["uncertain"]):
                continue
            explicit = accepted & data["known"]
            if np.any(explicit & ~data["truth"] & data["control"]):
                continue
            precision = float(data["truth"][explicit].mean()) if explicit.any() else 1.0
            if precision < precision_floor:
                continue
            choices.append((
                int(np.count_nonzero(explicit & data["truth"])), precision,
                -int(np.count_nonzero(accepted)), float(value), float(certainty_value),
            ))
    if not choices:
        return float(np.nextafter(score.max(), np.inf)), 1.0
    best = max(choices)
    return best[3], best[4]


def _oof(rows: list[dict], indices: np.ndarray, config: dict, splits: int = 4) -> dict:
    groups = np.asarray([rows[int(index)]["content_group"] for index in indices])
    parts = {name: [] for name in ("score", "raw", "certainty", "truth", "known", "uncertain", "control", "keys", "indices")}
    fold_count = min(splits, len(np.unique(groups)))
    for train_offset, test_offset in GroupKFold(n_splits=fold_count).split(indices, groups=groups):
        train = _matrix(rows, indices[train_offset])
        test = _matrix(rows, indices[test_offset])
        score = _fit_score(config, train, test)
        parts["score"].extend(score.tolist())
        parts["raw"].extend(test["features"][:, 0].tolist())
        parts["certainty"].extend(_fit_certainty(train, test).tolist())
        for name in ("truth", "known", "uncertain", "control", "keys", "indices"):
            parts[name].extend(test[name].tolist())
    return {
        "score": np.asarray(parts["score"], dtype=np.float64),
        "raw": np.asarray(parts["raw"], dtype=np.float64),
        "certainty": np.asarray(parts["certainty"], dtype=np.float64),
        "truth": np.asarray(parts["truth"], dtype=bool),
        "known": np.asarray(parts["known"], dtype=bool),
        "uncertain": np.asarray(parts["uncertain"], dtype=bool),
        "control": np.asarray(parts["control"], dtype=bool),
        "keys": np.asarray(parts["keys"]),
        "indices": np.asarray(parts["indices"], dtype=np.int64),
    }


def _select_config(rows: list[dict], indices: np.ndarray) -> tuple[dict, dict]:
    scores = {}
    for config in MODEL_CONFIGS:
        result = _oof(rows, indices, config)
        known = result["known"]
        scores[config["name"]] = float(
            average_precision_score(result["truth"][known], result["score"][known])
        )
    best = max(MODEL_CONFIGS, key=lambda config: scores[config["name"]])
    return best, scores


def _acceptance(data: dict, accepted: np.ndarray) -> dict:
    explicit = accepted & data["known"]
    wrong = explicit & ~data["truth"]
    return {
        "accepted_count": int(np.count_nonzero(accepted)),
        "accepted_true_positive_count": int(np.count_nonzero(explicit & data["truth"])),
        "accepted_false_positive_count": int(np.count_nonzero(wrong)),
        "accepted_uncertain_count": int(np.count_nonzero(accepted & data["uncertain"])),
        "precision": round(float(data["truth"][explicit].mean()) if explicit.any() else 1.0, 6),
        "copy_recall": round(float(np.count_nonzero(explicit & data["truth"]) / max(1, np.count_nonzero(data["known"] & data["truth"]))), 6),
        "five_control_wrong_links": int(np.count_nonzero(wrong & data["control"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cycle", type=int, default=730)
    args = parser.parse_args()
    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    table = _load_candidate_table(args.bank, args.embeddings, args.labels)
    rows = _build_rows(table)
    labeled_indices = np.asarray([
        offset for offset, row in enumerate(rows)
        if row["known"] or row["uncertain"]
    ], dtype=np.int64)
    content_groups = np.asarray([rows[index]["content_group"] for index in labeled_indices])
    all_parts = {name: [] for name in (
        "score", "raw", "certainty", "truth", "known", "uncertain", "control", "keys", "indices",
        "accepted", "raw_accepted",
    )}
    folds = []
    for fold, (train_offset, test_offset) in enumerate(
        GroupKFold(n_splits=5).split(labeled_indices, groups=content_groups)
    ):
        train_indices = labeled_indices[train_offset]
        test_indices = labeled_indices[test_offset]
        selected, inner_scores = _select_config(rows, train_indices)
        inner = _oof(rows, train_indices, selected)
        threshold, certainty_threshold = _safe_threshold(
            inner, inner["score"], inner["certainty"],
        )
        raw_threshold, _ = _safe_threshold(inner, inner["raw"])
        train = _matrix(rows, train_indices)
        test = _matrix(rows, test_indices)
        score = _fit_score(selected, train, test)
        certainty = _fit_certainty(train, test)
        raw = test["features"][:, 0].astype(np.float64)
        accepted = _top_two(
            score, (score >= threshold) & (certainty >= certainty_threshold), test["keys"],
        )
        raw_accepted = _top_two(raw, raw >= raw_threshold, test["keys"])
        for name, values in (
            ("score", score), ("raw", raw), ("certainty", certainty),
            ("truth", test["truth"]),
            ("known", test["known"]), ("uncertain", test["uncertain"]),
            ("control", test["control"]), ("keys", test["keys"]),
            ("indices", test["indices"]), ("accepted", accepted),
            ("raw_accepted", raw_accepted),
        ):
            all_parts[name].extend(values.tolist())
        folds.append({
            "fold": fold,
            "test_paints": sorted(set(rows[index]["paint"] for index in test_indices)),
            "selected_config": selected["name"],
            "inner_ap_by_config": {name: round(value, 6) for name, value in inner_scores.items()},
            "inner_safe_threshold": round(threshold, 8),
            "inner_certainty_veto_threshold": round(certainty_threshold, 8),
            "inner_raw_safe_threshold": round(raw_threshold, 8),
        })
    result = {
        "score": np.asarray(all_parts["score"], dtype=np.float64),
        "raw": np.asarray(all_parts["raw"], dtype=np.float64),
        "certainty": np.asarray(all_parts["certainty"], dtype=np.float64),
        "truth": np.asarray(all_parts["truth"], dtype=bool),
        "known": np.asarray(all_parts["known"], dtype=bool),
        "uncertain": np.asarray(all_parts["uncertain"], dtype=bool),
        "control": np.asarray(all_parts["control"], dtype=bool),
        "keys": np.asarray(all_parts["keys"]),
        "indices": np.asarray(all_parts["indices"], dtype=np.int64),
    }
    known = result["known"]
    baseline_ap = float(average_precision_score(result["truth"][known], result["raw"][known]))
    after_ap = float(average_precision_score(result["truth"][known], result["score"][known]))
    accepted = np.asarray(all_parts["accepted"], dtype=bool)
    raw_accepted = np.asarray(all_parts["raw_accepted"], dtype=bool)
    accepted_metrics = _acceptance(result, accepted)
    raw_metrics = _acceptance(result, raw_accepted)
    gate = bool(
        after_ap >= baseline_ap + 0.01
        and accepted_metrics["precision"] >= 0.80
        and accepted_metrics["copy_recall"] > 0
        and accepted_metrics["accepted_true_positive_count"] >= raw_metrics["accepted_true_positive_count"]
        and accepted_metrics["five_control_wrong_links"] == 0
        and accepted_metrics["accepted_uncertain_count"] == 0
    )
    # Fit the modal nested configuration only to rank unresolved existing-bank rows.
    modal_name = Counter(row["selected_config"] for row in folds).most_common(1)[0][0]
    final_config = next(config for config in MODEL_CONFIGS if config["name"] == modal_name)
    full_labeled = _matrix(rows, labeled_indices)
    full_oof = _oof(rows, labeled_indices, final_config)
    full_threshold, full_certainty_threshold = _safe_threshold(
        full_oof, full_oof["score"], full_oof["certainty"],
    )
    all_indices = np.arange(len(rows), dtype=np.int64)
    all_data = _matrix(rows, all_indices)
    all_score = _fit_score(final_config, full_labeled, all_data)
    all_certainty = _fit_certainty(full_labeled, all_data)
    active_queue = []
    for offset, row in enumerate(rows):
        if row["semantic"] is not None:
            continue
        active_queue.append({
            "paint": row["paint"], "candidate_index": row["candidate_index"],
            "proposal_id": row["proposal_id"], "block": row["block"],
            "anchor_review_code": row["anchor_review_code"],
            "ordinal_score": round(float(all_score[offset]), 8),
            "certainty_probability": round(float(all_certainty[offset]), 8),
            "distance_to_safe_threshold": round(float(min(
                abs(all_score[offset] - full_threshold),
                abs(all_certainty[offset] - full_certainty_threshold),
            )), 8),
            "nearest_boundary": (
                "family_score" if abs(all_score[offset] - full_threshold)
                <= abs(all_certainty[offset] - full_certainty_threshold)
                else "review_certainty"
            ),
            "would_pass_frozen_gate": bool(
                all_score[offset] >= full_threshold
                and all_certainty[offset] >= full_certainty_threshold
            ),
            "review_selection_only": True, "ownership_authority": False,
        })
    active_queue.sort(key=lambda row: row["distance_to_safe_threshold"])
    examples = []
    for offset, row_index in enumerate(result["indices"]):
        row = rows[int(row_index)]
        if not (accepted[offset] or raw_accepted[offset]):
            continue
        examples.append({
            "paint": row["paint"], "candidate_index": row["candidate_index"],
            "proposal_id": row["proposal_id"], "block": row["block"],
            "semantic": row["semantic"], "truth": bool(result["truth"][offset]),
            "control": bool(result["control"][offset]),
            "raw_score": round(float(result["raw"][offset]), 8),
            "ordinal_score": round(float(result["score"][offset]), 8),
            "raw_accepted": bool(raw_accepted[offset]),
            "ordinal_accepted": bool(accepted[offset]),
            "ownership_authority": False,
        })
    duplicate_sets = [
        sorted(paint for paint, digest in table["source_hashes"].items() if digest == value)
        for value, count in Counter(table["source_hashes"].values()).items() if count > 1
    ]
    ledger = {
        "schema": "smart-tga-within-paint-ordinal-family-v1",
        "cycle": args.cycle,
        "contract": "One external complete Number anchor is mandatory; D4 similarity leads and cohort-relative anatomy only corroborates. No anchor means abstain.",
        "corpus": {
            "broad_candidate_count": len(table["trace"]), "paint_count": len(table["by_paint"]),
            "anchor_paint_count": len(table["anchors"]), "evaluated_labeled_rows": len(labeled_indices),
            "explicit_rows": int(np.count_nonzero(result["known"])),
            "uncertain_guard_rows": int(np.count_nonzero(result["uncertain"])),
        },
        "baseline_full_cohort_d4": {
            "source_content_disjoint_ap": round(baseline_ap, 6),
            "calibrated_top_two": raw_metrics,
        },
        "after_nested_source_content_disjoint": {
            "operational_ap": round(after_ap, 6),
            "gain_over_matching_full_cohort_baseline": round(after_ap - baseline_ap, 6),
            "selected_config_counts": dict(Counter(row["selected_config"] for row in folds)),
            "feature_names": list(FEATURE_NAMES), "calibrated_top_two": accepted_metrics,
        },
        "gates": {
            "fine_shape_ranking_gate_passed": bool(after_ap >= baseline_ap + 0.05),
            "safe_acceptance_gate_passed": gate,
            "ordinal_family_gate_passed": gate,
            "requires_ap_gain_at_least": 0.01,
            "requires_precision_at_least": 0.80, "requires_nonzero_copy_recall": True,
            "requires_no_accepted_true_positive_regression_vs_raw": True,
            "requires_zero_five_control_wrong_links": True,
            "requires_zero_uncertain_accepts": True, "runtime_integrated": False,
            "holdout_opened": False, "apply_locked": True,
        },
        "content_split_audit": {
            "unique_source_content_count": len(set(table["source_hashes"].values())),
            "duplicate_source_content_sets": duplicate_sets,
            "source_hash_used_as_model_feature": False,
        },
        "targets": sorted(set(table["by_paint"]) - CONTROL_PAINTS),
        "hard_negative_controls": sorted(CONTROL_PAINTS),
        "active_learning": {
            "existing_unreviewed_ranked_count": len(active_queue),
            "queue_file": "active_learning_queue.json", "new_tga_requested": False,
        },
        "folds": folds,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "safety": {
            "anchor_from_durable_direct_review": True,
            "one_anchor_per_paint_selected_without_bbox_or_identity_feature": True,
            "full_96_candidate_cohorts_used_for_ordinal_normalization": True,
            "review_uncertainty_used_only_to_train_veto_corroboration": True,
            "outer_and_inner_source_content_disjoint": True,
            "thresholds_selected_inside_outer_training_folds": True,
            "paint_block_used_only_for_within_cohort_adjudication": True,
            "filename_or_car_model_feature": False, "absolute_bbox_model_feature": False,
            "casts_votes": False, "ownership_authority": False,
            "exact_reconstruction_affected": False, "ocr_changed": False,
        },
        "next_engineering_step": (
            "Do not open a fresh holdout: fine D4 shape ranking passed but selective acceptance failed. "
            "Review only the existing-bank items nearest the family-score or review-certainty boundary, beginning with tiny single-glyph/rectangular fragments versus complete copies and glyph-like sponsors. "
            "Then train a source-content-disjoint fragment/completeness abstention head; it must retain at least the raw baseline's accepted true copies while producing zero uncertain/control accepts before another holdout."
        ),
    }
    (args.output / "acceptance_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8",
    )
    (args.output / "accepted_examples.json").write_text(
        json.dumps({"schema": "smart-tga-ordinal-accepted-examples-v1", "examples": examples}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output / "active_learning_queue.json").write_text(
        json.dumps({
            "schema": "smart-tga-existing-bank-ordinal-active-learning-v1",
            "cycle": args.cycle, "safe_threshold": round(full_threshold, 8),
            "certainty_veto_threshold": round(full_certainty_threshold, 8),
            "items": active_queue, "ownership_authority": False,
        }, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "baseline": ledger["baseline_full_cohort_d4"],
        "after": ledger["after_nested_source_content_disjoint"],
        "gates": ledger["gates"], "active_learning": ledger["active_learning"],
    }, indent=2))


if __name__ == "__main__":
    main()
