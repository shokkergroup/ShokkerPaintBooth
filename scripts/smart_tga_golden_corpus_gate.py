"""Qualify Smart TGA off/shadow route artifacts against a reviewed golden manifest.

The route inspector remains responsible for executing expensive real-TGA runs.
This gate consumes one or more off and shadow inspector directories, proves the
hard partition/reconstruction contracts, compares every owner mask exactly, and
checks reviewed component expectations.  It deliberately separates technical
correctness from corpus-review completeness so a tiny green smoke set cannot be
mistaken for beta release readiness.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw


OWNERS = ("numbers", "sponsors", "template", "brand_graphics", "paint")
DEFAULT_MANIFEST = Path("tests_v2/smart_tga_golden_corpus_v1.json")
DEFAULT_OUTPUT = Path("_smart_tga_runs/golden_corpus_gate")
OCR_REGION_LABELS = {
    "readable_wordmark", "garbled", "already_sponsor",
    "missed_paint_template", "unsafe_overlap",
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest_entries(manifest: Mapping[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    """Load bounded entry shards without allowing recursive manifest sprawl."""
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("golden-corpus manifest entries must be a list")
    merged = [dict(entry) for entry in entries]
    for value in manifest.get("entry_manifests") or []:
        shard_path = Path(str(value))
        if not shard_path.is_absolute():
            shard_path = manifest_path.parent / shard_path
        shard = _read_json(shard_path)
        if shard.get("schema") != "spb-smart-tga-golden-entries-v1":
            raise ValueError(f"unsupported golden entry-manifest schema: {shard_path}")
        if shard.get("entry_manifests"):
            raise ValueError(f"nested golden entry manifests are not allowed: {shard_path}")
        shard_entries = shard.get("entries")
        if not isinstance(shard_entries, list) or not shard_entries:
            raise ValueError(f"golden entry manifest has no entries: {shard_path}")
        merged.extend(dict(entry) for entry in shard_entries)
    return merged


def _ocr_region_review_report(manifest: Mapping[str, Any], manifest_path: Path) -> dict[str, Any]:
    relative = str(manifest.get("ocr_region_review_manifest") or "").strip()
    if not relative:
        return {"configured": False, "passed": True, "prediction_count": 0, "reviewed_count": 0}
    path = (manifest_path.parent / relative).resolve()
    payload = _read_json(path)
    if payload.get("schema") != "spb-smart-tga-ocr-region-review-v1":
        raise ValueError("unsupported Smart TGA OCR-region review schema")
    reviews = list(payload.get("reviews") or ())
    reviewed = [item for item in reviews if item.get("label") in OCR_REGION_LABELS]
    readable_labels = {"readable_wordmark", "already_sponsor", "missed_paint_template"}
    readable = [item for item in reviewed if item.get("label") in readable_labels]
    by_basis = {}
    for basis in sorted({str(item.get("quality_basis") or "untyped") for item in reviews}):
        entries = [item for item in reviews if str(item.get("quality_basis") or "untyped") == basis]
        done = [item for item in entries if item.get("label") in OCR_REGION_LABELS]
        good = [item for item in done if item.get("label") in readable_labels]
        by_basis[basis] = {
            "predictions": len(entries), "reviewed": len(done), "readable": len(good),
            "readable_precision": len(good) / max(1, len(done)),
        }
    all_reviewed = bool(reviews) and len(reviewed) == len(reviews)
    unsafe_count = sum(item.get("label") == "unsafe_overlap" for item in reviewed)
    return {
        "configured": True, "manifest": str(path),
        "passed": all_reviewed and len(reviews) >= 10,
        "prediction_count": len(reviews), "reviewed_count": len(reviewed),
        "all_predictions_reviewed": all_reviewed,
        "readable_count": len(readable),
        "readable_precision": len(readable) / max(1, len(reviewed)),
        "unsafe_overlap_count": unsafe_count,
        "unsafe_overlap_rate": unsafe_count / max(1, len(reviewed)),
        "labels": dict(sorted(Counter(str(item.get("label")) for item in reviewed).items())),
        "dominant_owner_predictions": dict(sorted(Counter(str(item.get("dominant_owner") or "unknown") for item in reviews).items())),
        "by_quality_basis": by_basis,
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_mask(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        mask = np.asarray(image.convert("L")) > 0
    return np.ascontiguousarray(mask)


def _load_records(run_dirs: Sequence[Path], role: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for run_dir in run_dirs:
        path = Path(run_dir) / "inspection_records.json"
        if not path.is_file():
            raise FileNotFoundError(f"{role} run has no inspection_records.json: {run_dir}")
        payload = _read_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"expected a record list in {path}")
        for record in payload:
            label = str(record.get("paint_label") or "").replace("\\", "/")
            if not label:
                raise ValueError(f"record without paint_label in {path}")
            if label in records:
                prior_success = bool(records[label].get("success"))
                new_success = bool(record.get("success"))
                if prior_success and new_success:
                    raise ValueError(f"duplicate successful {role} record for {label}")
                if prior_success and not new_success:
                    continue
                if not prior_success and not new_success:
                    continue
            copied = dict(record)
            copied["_run_dir"] = str(Path(run_dir).resolve())
            records[label] = copied
    return records


def _component_bboxes(mask: np.ndarray, min_area: int = 1) -> list[list[int]]:
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    boxes = [
        [int(value) for value in stats[label_id, :4]]
        for label_id in range(1, count)
        if int(stats[label_id, cv2.CC_STAT_AREA]) >= max(1, int(min_area))
    ]
    return sorted(boxes, key=lambda box: (box[1], box[0], box[2], box[3]))


def _bbox_set_matches(actual: Sequence[Sequence[int]], expected: Sequence[Sequence[int]], tolerance: int) -> bool:
    unmatched = [tuple(int(value) for value in box) for box in actual]
    for expected_box in expected:
        target = tuple(int(value) for value in expected_box)
        match_index = next((
            index for index, box in enumerate(unmatched)
            if all(abs(left - right) <= tolerance for left, right in zip(box, target))
        ), None)
        if match_index is None:
            return False
        unmatched.pop(match_index)
    return not unmatched


def _bbox_iou(left: Sequence[int], right: Sequence[int]) -> float:
    lx, ly, lw, lh = (int(value) for value in left)
    rx, ry, rw, rh = (int(value) for value in right)
    x0, y0 = max(lx, rx), max(ly, ry)
    x1, y1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    union = max(0, lw) * max(0, lh) + max(0, rw) * max(0, rh) - intersection
    return intersection / float(max(1, union))


def _instance_metrics(
    actual: Sequence[Sequence[int]],
    expected: Sequence[Sequence[int]],
    iou_threshold: float,
) -> dict[str, Any]:
    threshold = float(iou_threshold)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("instance IoU threshold must be in [0, 1]")
    candidates = sorted((
        (_bbox_iou(actual_box, expected_box), actual_index, expected_index)
        for actual_index, actual_box in enumerate(actual)
        for expected_index, expected_box in enumerate(expected)
    ), key=lambda item: (-item[0], item[1], item[2]))
    used_actual: set[int] = set()
    used_expected: set[int] = set()
    matches = []
    for iou, actual_index, expected_index in candidates:
        if iou < threshold or actual_index in used_actual or expected_index in used_expected:
            continue
        used_actual.add(actual_index)
        used_expected.add(expected_index)
        matches.append({
            "actual_index": actual_index,
            "expected_index": expected_index,
            "iou": round(float(iou), 6),
        })
    true_positive = len(matches)
    false_positive = len(actual) - true_positive
    false_negative = len(expected) - true_positive
    predicted_count = true_positive + false_positive
    expected_count = true_positive + false_negative
    precision = true_positive / float(predicted_count) if predicted_count else 1.0
    recall = true_positive / float(expected_count) if expected_count else 1.0
    return {
        "iou_threshold": threshold,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "f1": round(float(2.0 * precision * recall / max(1e-12, precision + recall)), 6),
        "matches": matches,
    }


def _partition_report(record: Mapping[str, Any]) -> dict[str, Any]:
    mask_paths = record.get("mask_paths") or {}
    missing = [owner for owner in OWNERS if not Path(str(mask_paths.get(owner) or "")).is_file()]
    if missing:
        return {"passed": False, "missing_masks": missing}
    masks = {owner: _load_mask(mask_paths[owner]) for owner in OWNERS}
    shapes = {mask.shape for mask in masks.values()}
    if len(shapes) != 1:
        return {"passed": False, "shape_mismatch": [list(shape) for shape in sorted(shapes)]}
    ownership = np.sum(np.stack([masks[owner] for owner in OWNERS], axis=0), axis=0)
    gap_pixels = int(np.count_nonzero(ownership == 0))
    overlap_pixels = int(np.count_nonzero(ownership > 1))

    source_path = Path(str(record.get("source_1024") or ""))
    reconstruction_mismatch = None
    if source_path.is_file():
        with Image.open(source_path) as image:
            source = np.asarray(image.convert("RGBA"))
        if source.shape[:2] == next(iter(shapes)):
            rebuilt = np.zeros_like(source)
            for owner in OWNERS:
                rebuilt[masks[owner]] = source[masks[owner]]
            reconstruction_mismatch = int(np.count_nonzero(np.any(rebuilt != source, axis=2)))

    passed = gap_pixels == 0 and overlap_pixels == 0 and reconstruction_mismatch == 0
    return {
        "passed": passed,
        "shape": list(next(iter(shapes))),
        "gap_pixels": gap_pixels,
        "overlap_pixels": overlap_pixels,
        "reconstruction_mismatch_pixels": reconstruction_mismatch,
        "owner_pixels": {owner: int(np.count_nonzero(masks[owner])) for owner in OWNERS},
    }


def _shadow_report(record: Mapping[str, Any]) -> dict[str, Any]:
    shadow = record.get("route_adjudicator_shadow") or {}
    xor_pixels = {str(owner): int(count) for owner, count in (shadow.get("xor_pixels") or {}).items()}
    changed_node_count = int(shadow.get("changed_node_count") or 0)
    proposal_neutral = changed_node_count == 0 and all(count == 0 for count in xor_pixels.values())
    passed = (
        shadow.get("mode") == "shadow"
        and shadow.get("status") == "shadow"
        and shadow.get("output_applied") is False
    )
    return {
        "passed": passed,
        "mode": shadow.get("mode"),
        "status": shadow.get("status"),
        "output_applied": shadow.get("output_applied"),
        "changed_node_count": changed_node_count,
        "xor_pixels": xor_pixels,
        "proposal_neutral": proposal_neutral,
        "proposal_changed": not proposal_neutral,
        "blocked_proposal_count": int(shadow.get("blocked_proposal_count") or 0),
        "elapsed_ms": shadow.get("elapsed_ms"),
    }


def _off_report(record: Mapping[str, Any]) -> dict[str, Any]:
    off = record.get("route_adjudicator_shadow") or {}
    passed = (
        off.get("mode") == "off"
        and off.get("status") == "off"
        and off.get("output_applied") is False
    )
    return {
        "passed": passed,
        "mode": off.get("mode"),
        "status": off.get("status"),
        "output_applied": off.get("output_applied"),
    }


def _expectation_report(record: Mapping[str, Any], entry: Mapping[str, Any]) -> dict[str, Any]:
    expected = entry.get("expected") or {}
    mask_paths = record.get("mask_paths") or {}
    checks: dict[str, Any] = {}
    passed = True
    for owner, spec in expected.items():
        if owner not in OWNERS:
            checks[owner] = {"passed": False, "error": "unknown owner"}
            passed = False
            continue
        mask_path = Path(str(mask_paths.get(owner) or ""))
        if not mask_path.is_file():
            checks[owner] = {"passed": False, "error": "missing mask"}
            passed = False
            continue
        mask = _load_mask(mask_path)
        min_area = int(spec.get("component_min_area", 1))
        boxes = _component_bboxes(mask, min_area=min_area)
        owner_pass = True
        details: dict[str, Any] = {
            "actual_component_count": len(boxes),
            "actual_component_bboxes": boxes,
            "actual_pixels": int(np.count_nonzero(mask)),
        }
        if "component_count" in spec:
            details["expected_component_count"] = int(spec["component_count"])
            owner_pass &= len(boxes) == int(spec["component_count"])
        if "component_bboxes" in spec:
            tolerance = int(spec.get("bbox_tolerance", 0))
            expected_boxes = spec["component_bboxes"]
            details["expected_component_bboxes"] = expected_boxes
            details["bbox_tolerance"] = tolerance
            details["bbox_match"] = _bbox_set_matches(boxes, expected_boxes, tolerance)
            owner_pass &= details["bbox_match"]
            metrics = _instance_metrics(boxes, expected_boxes, float(spec.get("instance_iou_threshold", 0.5)))
            details["instance_metrics"] = metrics
            if "min_instance_precision" in spec:
                details["min_instance_precision"] = float(spec["min_instance_precision"])
                owner_pass &= metrics["precision"] >= float(spec["min_instance_precision"])
            if "min_instance_recall" in spec:
                details["min_instance_recall"] = float(spec["min_instance_recall"])
                owner_pass &= metrics["recall"] >= float(spec["min_instance_recall"])
        if "min_pixels" in spec:
            details["min_pixels"] = int(spec["min_pixels"])
            owner_pass &= details["actual_pixels"] >= int(spec["min_pixels"])
        if "max_pixels" in spec:
            details["max_pixels"] = int(spec["max_pixels"])
            owner_pass &= details["actual_pixels"] <= int(spec["max_pixels"])
        details["passed"] = bool(owner_pass)
        checks[owner] = details
        passed &= owner_pass
    return {"passed": bool(passed), "owners": checks}


def _component_review_report(record: Mapping[str, Any], entry: Mapping[str, Any]) -> dict[str, Any]:
    review_specs = entry.get("component_reviews") or {}
    mask_paths = record.get("mask_paths") or {}
    owner_reports: dict[str, Any] = {}
    passed = True
    for owner, spec in review_specs.items():
        if owner not in OWNERS:
            raise ValueError(f"unknown component-review owner {owner!r}")
        mask_path = Path(str(mask_paths.get(owner) or ""))
        if not mask_path.is_file():
            owner_reports[owner] = {"passed": False, "error": "missing mask"}
            passed = False
            continue
        actual = _component_bboxes(_load_mask(mask_path), int(spec.get("component_min_area", 1)))
        annotations = []
        for verdict in ("true", "false", "mixed"):
            for bbox in spec.get(f"{verdict}_bboxes", []):
                annotations.append({"verdict": verdict, "bbox": [int(value) for value in bbox]})
        threshold = float(spec.get("iou_threshold", 0.90))
        candidates = sorted((
            (_bbox_iou(actual_box, annotation["bbox"]), actual_index, annotation_index)
            for actual_index, actual_box in enumerate(actual)
            for annotation_index, annotation in enumerate(annotations)
        ), key=lambda item: (-item[0], item[1], item[2]))
        used_actual: set[int] = set()
        used_annotations: set[int] = set()
        matches = []
        for iou, actual_index, annotation_index in candidates:
            if iou < threshold or actual_index in used_actual or annotation_index in used_annotations:
                continue
            used_actual.add(actual_index)
            used_annotations.add(annotation_index)
            matches.append({
                "actual_index": actual_index,
                "annotation_index": annotation_index,
                "verdict": annotations[annotation_index]["verdict"],
                "bbox": actual[actual_index],
                "iou": round(float(iou), 6),
            })
        missing_source_annotations = []
        recovered_count = 0
        missing_iou_threshold = float(spec.get("missing_iou_threshold", threshold))
        for missing_bbox_value in spec.get("missing_bboxes", []):
            missing_bbox = [int(value) for value in missing_bbox_value]
            available = sorted((
                (_bbox_iou(actual_box, missing_bbox), actual_index)
                for actual_index, actual_box in enumerate(actual)
                if actual_index not in used_actual
            ), key=lambda item: (-item[0], item[1]))
            best_iou, best_index = available[0] if available else (0.0, None)
            recovered = bool(best_index is not None and best_iou >= missing_iou_threshold)
            if recovered:
                used_actual.add(int(best_index))
                recovered_count += 1
            missing_source_annotations.append({
                "bbox": missing_bbox,
                "recovered": recovered,
                "matched_actual_index": int(best_index) if recovered else None,
                "iou": round(float(best_iou), 6),
            })
        verdict_counts = {
            verdict: sum(match["verdict"] == verdict for match in matches)
            for verdict in ("true", "false", "mixed")
        }
        verdict_counts["true"] += recovered_count
        reviewed_binary = verdict_counts["true"] + verdict_counts["false"]
        precision = verdict_counts["true"] / float(reviewed_binary) if reviewed_binary else 1.0
        false_negative_count = sum(not annotation["recovered"] for annotation in missing_source_annotations)
        recall = verdict_counts["true"] / float(verdict_counts["true"] + false_negative_count) if (verdict_counts["true"] + false_negative_count) else 1.0
        unmatched_annotations = [
            annotations[index] for index in range(len(annotations)) if index not in used_annotations
        ]
        unreviewed_predictions = [
            actual[index] for index in range(len(actual)) if index not in used_actual
        ]
        require_all = bool(spec.get("require_all_predictions_reviewed", True))
        min_precision = float(spec.get("min_reviewed_precision", 0.0))
        min_recall = float(spec.get("min_reviewed_recall", 0.0))
        owner_pass = (
            not unmatched_annotations
            and (not require_all or not unreviewed_predictions)
            and precision >= min_precision
            and recall >= min_recall
        )
        owner_reports[owner] = {
            "passed": owner_pass,
            "prediction_count": len(actual),
            "annotation_count": len(annotations),
            "matched_count": len(matches),
            "true_count": verdict_counts["true"],
            "false_count": verdict_counts["false"],
            "mixed_count": verdict_counts["mixed"],
            "false_negative_count": false_negative_count,
            "reviewed_precision": round(float(precision), 6),
            "min_reviewed_precision": min_precision,
            "reviewed_recall": round(float(recall), 6),
            "min_reviewed_recall": min_recall,
            "require_all_predictions_reviewed": require_all,
            "unmatched_annotations": unmatched_annotations,
            "unreviewed_predictions": unreviewed_predictions,
            "missing_source_annotations": missing_source_annotations,
            "matches": matches,
        }
        passed &= owner_pass
    return {"passed": bool(passed), "owners": owner_reports}


def _semantic_evidence_review_report(
    specification: Mapping[str, Any],
    shadow_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Check reviewed evidence votes without turning relationships into authority."""
    reviews = specification.get("records") or []
    if not reviews:
        return {
            "configured": False,
            "passed": True,
            "coverage_pass": True,
            "review_count": 0,
            "covered_count": 0,
            "matched_count": 0,
            "records": [],
        }
    if not isinstance(reviews, list):
        raise ValueError("semantic_evidence_reviews.records must be a list")
    default_threshold = float(specification.get("iou_threshold", 0.90))
    results: list[dict[str, Any]] = []
    for review in reviews:
        verdict = str(review.get("verdict") or "")
        if verdict not in {"vote", "hard_negative"}:
            raise ValueError(f"unknown semantic-evidence verdict {verdict!r}")
        label = str(review.get("paint_label") or "").replace("\\", "/")
        bbox = [int(value) for value in (review.get("bbox") or [])]
        if not label or len(bbox) != 4:
            raise ValueError("semantic-evidence reviews require paint_label and four-value bbox")
        threshold = float(review.get("iou_threshold", default_threshold))
        record = shadow_records.get(label)
        samples = ((((record or {}).get("route_adjudicator_shadow") or {}).get("semantic_family") or {}).get("samples") or [])
        candidates = sorted(
            (
                (_bbox_iou(bbox, sample.get("bbox") or []), sample)
                for sample in samples
                if len(sample.get("bbox") or []) == 4
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        # One component may legitimately carry multiple independent semantic
        # votes. For a positive review, resolve geometry together with the
        # requested owner/reason instead of accepting whichever equal-IoU
        # sample happened to be serialized first. Hard negatives remain
        # geometry-only: any semantic vote overlapping a protected region is
        # still a failure.
        if verdict == "vote":
            identity_candidates = [
                item for item in candidates
                if str(item[1].get("to") or "") == str(review.get("target_owner") or "")
                and str(item[1].get("reason") or "") == str(review.get("reason") or "")
            ]
            best_iou, best_sample = (
                identity_candidates[0]
                if identity_candidates
                else (candidates[0] if candidates else (0.0, None))
            )
        else:
            best_iou, best_sample = candidates[0] if candidates else (0.0, None)
        overlapping = best_sample is not None and best_iou >= threshold
        if verdict == "vote":
            matched = bool(
                overlapping
                and str(best_sample.get("to") or "") == str(review.get("target_owner") or "")
                and str(best_sample.get("reason") or "") == str(review.get("reason") or "")
            )
        else:
            matched = not overlapping
        results.append({
            "paint_label": label,
            "bbox": bbox,
            "verdict": verdict,
            "covered": record is not None,
            "matched": bool(record is not None and matched),
            "best_iou": round(float(best_iou), 6),
            "expected_target_owner": review.get("target_owner"),
            "expected_reason": review.get("reason"),
            "actual_target_owner": (best_sample or {}).get("to"),
            "actual_reason": (best_sample or {}).get("reason"),
        })
    covered = [result for result in results if result["covered"]]
    reason_acceptance: dict[str, Any] = {}
    for reason, gate in sorted((specification.get("reason_acceptance") or {}).items()):
        target_owner = str(gate.get("target_owner") or "")
        predictions = []
        truncated_records = []
        for label, record in sorted(shadow_records.items()):
            semantic = ((record.get("route_adjudicator_shadow") or {}).get("semantic_family") or {})
            if semantic.get("samples_truncated"):
                truncated_records.append(label)
            for sample in semantic.get("samples") or []:
                if str(sample.get("reason") or "") != reason:
                    continue
                if target_owner and str(sample.get("to") or "") != target_owner:
                    continue
                predictions.append((label, sample))
        positive_reviews = [
            review for review in reviews
            if str(review.get("verdict") or "") == "vote"
            and str(review.get("reason") or "") == reason
            and (not target_owner or str(review.get("target_owner") or "") == target_owner)
        ]
        matched_predictions = 0
        for label, sample in predictions:
            sample_bbox = sample.get("bbox") or []
            matched_predictions += any(
                str(review.get("paint_label") or "").replace("\\", "/") == label
                and _bbox_iou(review.get("bbox") or [], sample_bbox)
                >= float(review.get("iou_threshold", default_threshold))
                for review in positive_reviews
            )
        prediction_count = len(predictions)
        reviewed_precision = matched_predictions / float(max(1, prediction_count))
        # Annotation volume is a review-set requirement; missing run coverage
        # is reported independently by ``coverage_pass`` below.
        hard_negative_count = sum(
            str(review.get("verdict") or "") == "hard_negative"
            for review in reviews
        )
        min_predictions = int(gate.get("min_reviewed_predictions", 1))
        min_precision = float(gate.get("min_reviewed_precision", 1.0))
        min_hard_negatives = int(gate.get("min_hard_negatives", 0))
        require_all = bool(gate.get("require_all_predictions_reviewed", True))
        passed = bool(
            prediction_count >= min_predictions
            and reviewed_precision >= min_precision
            and hard_negative_count >= min_hard_negatives
            and (not require_all or matched_predictions == prediction_count)
            and not truncated_records
        )
        reason_acceptance[reason] = {
            "passed": passed,
            "target_owner": target_owner or None,
            "prediction_count": prediction_count,
            "reviewed_prediction_count": matched_predictions,
            "reviewed_precision": round(float(reviewed_precision), 6),
            "min_reviewed_predictions": min_predictions,
            "min_reviewed_precision": min_precision,
            "hard_negative_count": hard_negative_count,
            "min_hard_negatives": min_hard_negatives,
            "require_all_predictions_reviewed": require_all,
            "truncated_records": truncated_records,
        }
    annotation_pass = all(result["matched"] for result in covered)
    return {
        "configured": True,
        "passed": annotation_pass and all(
            report["passed"] for report in reason_acceptance.values()
        ),
        "coverage_pass": len(covered) == len(results),
        "review_count": len(results),
        "covered_count": len(covered),
        "matched_count": sum(bool(result["matched"]) for result in results),
        "reason_acceptance": reason_acceptance,
        "records": results,
    }


def _canary_component_review_report(
    specification: Mapping[str, Any],
    shadow_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate review-only materialization, reconstruction, and rollback."""
    reviews = specification.get("records") or []
    if not reviews:
        return {
            "configured": False, "passed": True, "coverage_pass": True,
            "review_count": 0, "covered_count": 0, "matched_count": 0,
            "records": [],
        }
    if not isinstance(reviews, list):
        raise ValueError("canary_component_reviews.records must be a list")
    default_threshold = float(specification.get("iou_threshold", 0.90))
    results = []
    for review in reviews:
        verdict = str(review.get("verdict") or "")
        if verdict not in {"move", "protected"}:
            raise ValueError(f"unknown canary-component verdict {verdict!r}")
        label = str(review.get("paint_label") or "").replace("\\", "/")
        bbox = [int(value) for value in (review.get("bbox") or [])]
        if not label or len(bbox) != 4:
            raise ValueError("canary-component reviews require paint_label and four-value bbox")
        record = shadow_records.get(label)
        canary = ((record or {}).get("route_adjudicator_shadow") or {}).get("evidence_canary") or {}
        safe = bool(
            canary.get("status") == "simulated"
            and canary.get("output_applied") is False
            and canary.get("hard_partition") is True
            and int(canary.get("reconstruction_mismatch_pixels") or 0) == 0
            and canary.get("rollback_exact") is True
            and all(int(value) == 0 for value in (canary.get("rollback_xor_pixels") or {}).values())
        )
        candidates = sorted(
            (
                (_bbox_iou(bbox, sample.get("bbox") or []), sample)
                for sample in (canary.get("samples") or [])
                if len(sample.get("bbox") or []) == 4
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        best_iou, sample = candidates[0] if candidates else (0.0, None)
        overlapping = sample is not None and best_iou >= float(review.get("iou_threshold", default_threshold))
        if verdict == "move":
            matched = bool(
                overlapping
                and sample.get("from") == review.get("from")
                and sample.get("to") == review.get("to")
                and sample.get("reason") == review.get("reason")
            )
        else:
            matched = not overlapping
        results.append({
            "paint_label": label,
            "bbox": bbox,
            "verdict": verdict,
            "covered": record is not None,
            "safe": safe,
            "matched": bool(record is not None and safe and matched),
            "best_iou": round(float(best_iou), 6),
            "actual_from": (sample or {}).get("from"),
            "actual_to": (sample or {}).get("to"),
            "actual_reason": (sample or {}).get("reason"),
        })
    covered = [result for result in results if result["covered"]]
    return {
        "configured": True,
        "passed": all(result["matched"] for result in covered),
        "coverage_pass": len(covered) == len(results),
        "review_count": len(results),
        "covered_count": len(covered),
        "matched_count": sum(bool(result["matched"]) for result in results),
        "records": results,
    }


def _pair_report(off: Mapping[str, Any], shadow: Mapping[str, Any]) -> dict[str, Any]:
    owner_records: dict[str, Any] = {}
    all_pixel_identical = True
    all_byte_identical = True
    for owner in OWNERS:
        off_path = Path(str((off.get("mask_paths") or {}).get(owner) or ""))
        shadow_path = Path(str((shadow.get("mask_paths") or {}).get(owner) or ""))
        if not off_path.is_file() or not shadow_path.is_file():
            owner_records[owner] = {"passed": False, "error": "missing mask"}
            all_pixel_identical = False
            all_byte_identical = False
            continue
        off_mask, shadow_mask = _load_mask(off_path), _load_mask(shadow_path)
        xor = int(np.count_nonzero(off_mask ^ shadow_mask)) if off_mask.shape == shadow_mask.shape else -1
        byte_identical = _file_sha256(off_path) == _file_sha256(shadow_path)
        owner_records[owner] = {
            "passed": xor == 0 and byte_identical,
            "xor_pixels": xor,
            "byte_identical": byte_identical,
            "off_sha256": _file_sha256(off_path),
            "shadow_sha256": _file_sha256(shadow_path),
        }
        all_pixel_identical &= xor == 0
        all_byte_identical &= byte_identical
    off_source = Path(str(off.get("source_1024") or ""))
    shadow_source = Path(str(shadow.get("source_1024") or ""))
    source_byte_identical = (
        off_source.is_file()
        and shadow_source.is_file()
        and _file_sha256(off_source) == _file_sha256(shadow_source)
    )
    return {
        "passed": all_pixel_identical and all_byte_identical and source_byte_identical,
        "pixel_identical": all_pixel_identical,
        "byte_identical": all_byte_identical,
        "source_byte_identical": source_byte_identical,
        "owners": owner_records,
    }


def _record_build(record: Mapping[str, Any]) -> str:
    return str((record.get("route_smart_tga") or {}).get("build") or "")


def _aggregate_instance_metrics(
    records: Sequence[Mapping[str, Any]],
    requirements: Mapping[str, Any],
) -> dict[str, Any]:
    owners: dict[str, Any] = {}
    passed = True
    for owner, requirement in requirements.items():
        if owner not in OWNERS:
            raise ValueError(f"unknown metric requirement owner {owner!r}")
        labeled = []
        for record in records:
            metrics = (((record.get("expectations") or {}).get("owners") or {}).get(owner) or {}).get("instance_metrics")
            if metrics is not None:
                labeled.append(metrics)
        true_positive = sum(int(metric["true_positive"]) for metric in labeled)
        false_positive = sum(int(metric["false_positive"]) for metric in labeled)
        false_negative = sum(int(metric["false_negative"]) for metric in labeled)
        predicted_count = true_positive + false_positive
        expected_count = true_positive + false_negative
        precision = true_positive / float(predicted_count) if predicted_count else 1.0
        recall = true_positive / float(expected_count) if expected_count else 1.0
        min_entries = max(1, int(requirement.get("min_labeled_entries", 1)))
        min_precision = float(requirement.get("min_precision", 0.0))
        min_recall = float(requirement.get("min_recall", 0.0))
        owner_pass = (
            len(labeled) >= min_entries
            and precision >= min_precision
            and recall >= min_recall
        )
        owners[owner] = {
            "passed": owner_pass,
            "labeled_entries": len(labeled),
            "min_labeled_entries": min_entries,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": round(float(precision), 6),
            "min_precision": min_precision,
            "recall": round(float(recall), 6),
            "min_recall": min_recall,
        }
        passed &= owner_pass
    return {"passed": bool(passed), "owners": owners}


def _aggregate_component_reviews(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    owners: dict[str, Any] = {}
    for owner in OWNERS:
        reports = [
            ((record.get("component_reviews") or {}).get("owners") or {}).get(owner)
            for record in records
        ]
        reports = [report for report in reports if report is not None]
        if not reports:
            continue
        true_count = sum(int(report["true_count"]) for report in reports)
        false_count = sum(int(report["false_count"]) for report in reports)
        mixed_count = sum(int(report["mixed_count"]) for report in reports)
        false_negative_count = sum(int(report["false_negative_count"]) for report in reports)
        precision = true_count / float(max(1, true_count + false_count))
        recall = true_count / float(max(1, true_count + false_negative_count))
        owners[owner] = {
            "entries": len(reports),
            "prediction_count": sum(int(report["prediction_count"]) for report in reports),
            "true_count": true_count,
            "false_count": false_count,
            "mixed_count": mixed_count,
            "false_negative_count": false_negative_count,
            "reviewed_precision": round(float(precision), 6),
            "reviewed_recall": round(float(recall), 6),
            "all_annotations_matched": all(not report["unmatched_annotations"] for report in reports),
            "all_predictions_reviewed": all(not report["unreviewed_predictions"] for report in reports),
        }
    return {"owners": owners}


def _entry_record(
    entry: Mapping[str, Any],
    off: Mapping[str, Any] | None,
    shadow: Mapping[str, Any] | None,
) -> dict[str, Any]:
    label = str(entry["paint_label"]).replace("\\", "/")
    known_issues = [str(issue) for issue in entry.get("known_issues", [])]
    reviewed_owners = sorted(set(str(owner) for owner in entry.get("reviewed_owners", [])))
    fully_reviewed = set(reviewed_owners) == set(OWNERS) and not known_issues
    result: dict[str, Any] = {
        "id": str(entry["id"]),
        "family": str(entry.get("family") or "unknown"),
        "paint_label": label,
        "review_status": str(entry.get("review_status") or "unreviewed"),
        "reviewed_owners": reviewed_owners,
        "fully_reviewed": fully_reviewed,
        "known_issues": known_issues,
    }
    if off is None or shadow is None:
        result.update({"technical_pass": False, "missing_run": "off" if off is None else "shadow"})
        return result

    expected_prefix = str(entry.get("expected_build_prefix") or "smart-tga-cycle")
    builds = {"off": _record_build(off), "shadow": _record_build(shadow)}
    route_pass = (
        bool(off.get("success"))
        and bool(shadow.get("success"))
        and all(build.startswith(expected_prefix) for build in builds.values())
        and builds["off"] == builds["shadow"]
        and str(off.get("route_engine") or "") == str(shadow.get("route_engine") or "")
    )
    off_partition = _partition_report(off)
    shadow_partition = _partition_report(shadow)
    off_neutral = _off_report(off)
    shadow_neutral = _shadow_report(shadow)
    pair = _pair_report(off, shadow)
    expectations = _expectation_report(shadow, entry)
    component_reviews = _component_review_report(shadow, entry)
    technical_pass = all((route_pass, off_partition["passed"], shadow_partition["passed"], off_neutral["passed"], shadow_neutral["passed"], pair["passed"], expectations["passed"], component_reviews["passed"]))
    result.update({
        "technical_pass": bool(technical_pass),
        "route": {
            "passed": route_pass,
            "builds": builds,
            "engine": shadow.get("route_engine"),
            "off_elapsed_sec": off.get("elapsed_sec"),
            "shadow_elapsed_sec": shadow.get("elapsed_sec"),
        },
        "off_partition": off_partition,
        "shadow_partition": shadow_partition,
        "off_neutral": off_neutral,
        "shadow_neutral": shadow_neutral,
        "off_shadow_equivalence": pair,
        "expectations": expectations,
        "component_reviews": component_reviews,
        "artifacts": {
            "source": shadow.get("source_1024"),
            "off_overlay": off.get("overlay"),
            "shadow_overlay": shadow.get("overlay"),
            "numbers_sheet": shadow.get("numbers_components_sheet"),
            "sponsors_sheet": shadow.get("sponsors_components_sheet"),
            "template_sheet": shadow.get("template_components_sheet"),
            "paint_sheet": shadow.get("paint_components_sheet"),
            "suspect_sheet": shadow.get("suspect_review_sheet"),
            "ocr_region_overlay": shadow.get("ocr_region_overlay"),
        },
    })
    return result


def _artifact_link(path: Any, label: str) -> str:
    candidate = Path(str(path or ""))
    if not candidate.is_file():
        return ""
    return f'<a href="{html.escape(candidate.resolve().as_uri())}">{html.escape(label)}</a>'


def _write_component_review_overlay(record: Mapping[str, Any], output: Path) -> str | None:
    owner_reports = (record.get("component_reviews") or {}).get("owners") or {}
    source_path = Path(str((record.get("artifacts") or {}).get("source") or ""))
    if not owner_reports or not source_path.is_file():
        return None
    with Image.open(source_path) as source_image:
        canvas = source_image.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    colors = {
        "true": (40, 220, 110, 255),
        "false": (255, 70, 80, 255),
        "mixed": (255, 205, 45, 255),
        "missing": (75, 185, 255, 255),
    }
    for owner, report in owner_reports.items():
        for match in report.get("matches", []):
            x, y, width, height = (int(value) for value in match["bbox"])
            verdict = str(match["verdict"])
            color = colors[verdict]
            draw.rectangle((x, y, x + width - 1, y + height - 1), outline=color, width=3)
            label = f"{owner}:{verdict}"
            text_box = draw.textbbox((x, y), label)
            text_width = text_box[2] - text_box[0]
            text_height = text_box[3] - text_box[1]
            label_y = max(0, y - text_height - 3)
            draw.rectangle((x, label_y, x + text_width + 4, label_y + text_height + 3), fill=(8, 12, 18, 220))
            draw.text((x + 2, label_y + 1), label, fill=color)
        for missing in report.get("missing_source_annotations", []):
            if missing.get("recovered"):
                continue
            x, y, width, height = (int(value) for value in missing["bbox"])
            color = colors["missing"]
            draw.rectangle((x, y, x + width - 1, y + height - 1), outline=color, width=3)
            label = f"{owner}:missing"
            text_box = draw.textbbox((x, y), label)
            text_width = text_box[2] - text_box[0]
            text_height = text_box[3] - text_box[1]
            label_y = max(0, y - text_height - 3)
            draw.rectangle((x, label_y, x + text_width + 4, label_y + text_height + 3), fill=(8, 12, 18, 220))
            draw.text((x + 2, label_y + 1), label, fill=color)
    safe_id = "".join(character if character.isalnum() or character in "-_" else "_" for character in str(record["id"]))
    path = output / f"{safe_id}_component_review.png"
    canvas.save(path)
    return str(path.resolve())


def _write_html(path: Path, summary: Mapping[str, Any]) -> None:
    rows = []
    for record in summary["records"]:
        artifacts = record.get("artifacts") or {}
        links = " ".join(filter(None, (
            _artifact_link(artifacts.get("shadow_overlay"), "overlay"),
            _artifact_link(artifacts.get("numbers_sheet"), "numbers"),
            _artifact_link(artifacts.get("sponsors_sheet"), "sponsors"),
            _artifact_link(artifacts.get("template_sheet"), "template"),
            _artifact_link(artifacts.get("suspect_sheet"), "suspects"),
            _artifact_link(artifacts.get("component_review_overlay"), "semantic review"),
            _artifact_link(artifacts.get("ocr_region_overlay"), "OCR regions"),
        )))
        issues = "<br>".join(html.escape(issue) for issue in record.get("known_issues", [])) or "—"
        rows.append(
            "<tr>"
            f"<td>{html.escape(record['id'])}</td>"
            f"<td>{html.escape(record['family'])}</td>"
            f"<td>{'PASS' if record.get('technical_pass') else 'FAIL'}</td>"
            f"<td>{html.escape(record.get('review_status', ''))}</td>"
            f"<td>{issues}</td><td>{links}</td></tr>"
        )
    metric_rows = []
    for owner, metric in (summary.get("instance_metrics") or {}).get("owners", {}).items():
        metric_rows.append(
            "<tr>"
            f"<td>{html.escape(owner)}</td>"
            f"<td>{'PASS' if metric['passed'] else 'FAIL'}</td>"
            f"<td>{metric['labeled_entries']}/{metric['min_labeled_entries']}</td>"
            f"<td>{metric['true_positive']}</td><td>{metric['false_positive']}</td><td>{metric['false_negative']}</td>"
            f"<td>{metric['precision']:.3f} / {metric['min_precision']:.3f}</td>"
            f"<td>{metric['recall']:.3f} / {metric['min_recall']:.3f}</td></tr>"
        )
    component_review_rows = []
    for owner, metric in (summary.get("component_review_metrics") or {}).get("owners", {}).items():
        component_review_rows.append(
            "<tr>"
            f"<td>{html.escape(owner)}</td><td>{metric['entries']}</td><td>{metric['prediction_count']}</td>"
            f"<td>{metric['true_count']}</td><td>{metric['false_count']}</td><td>{metric['false_negative_count']}</td><td>{metric['mixed_count']}</td>"
            f"<td>{metric['reviewed_precision']:.3f}</td><td>{metric['reviewed_recall']:.3f}</td>"
            f"<td>{metric['all_annotations_matched']}</td><td>{metric['all_predictions_reviewed']}</td></tr>"
        )
    reason_acceptance_rows = []
    reason_acceptance = (
        (summary.get("semantic_evidence_reviews") or {}).get("reason_acceptance") or {}
    )
    for reason, report in reason_acceptance.items():
        reason_acceptance_rows.append(
            "<tr>"
            f"<td>{html.escape(reason)}</td>"
            f"<td>{'PASS' if report['passed'] else 'FAIL'}</td>"
            f"<td>{html.escape(str(report.get('target_owner') or ''))}</td>"
            f"<td>{report['reviewed_prediction_count']}/{report['prediction_count']}</td>"
            f"<td>{report['reviewed_precision']:.3f} / {report['min_reviewed_precision']:.3f}</td>"
            f"<td>{report['hard_negative_count']}/{report['min_hard_negatives']}</td>"
            f"<td>{html.escape(', '.join(report.get('truncated_records') or []) or 'none')}</td>"
            "</tr>"
        )
    verdict = "PASS" if summary["release_pass"] else "NOT READY"
    document = f"""<!doctype html>
<meta charset="utf-8"><title>Smart TGA Golden Corpus Gate</title>
<style>body{{font:15px system-ui;background:#10151d;color:#e8edf5;margin:24px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #354153;padding:8px;vertical-align:top}}th{{background:#1d2938}}a{{color:#79c8ff}}.bad{{color:#ff8d8d}}</style>
<h1>Smart TGA Golden Corpus Gate — <span class="{'bad' if not summary['release_pass'] else ''}">{verdict}</span></h1>
<p>Technical: {summary['technical_pass']} · Metrics: {summary['metric_pass']} · Review: {summary['review_pass']} · Semantic evidence: {summary.get('semantic_review_pass')} · Canary: {summary.get('canary_review_pass')} · Entries: {summary['entry_count']}/{summary['required_entry_count']} · Fully reviewed: {summary['fully_reviewed_count']}</p>
<p>{html.escape('; '.join(summary['blockers']) or 'No blockers')}</p>
<h2>OCR region review</h2><pre>{html.escape(json.dumps(summary.get('ocr_region_reviews') or {}, indent=2))}</pre>
<h2>Instance metrics and label coverage</h2>
<table><thead><tr><th>Owner</th><th>Gate</th><th>Labeled entries</th><th>TP</th><th>FP</th><th>FN</th><th>Precision / floor</th><th>Recall / floor</th></tr></thead><tbody>{''.join(metric_rows)}</tbody></table>
<h2>Reviewed prediction precision</h2>
<table><thead><tr><th>Owner</th><th>Entries</th><th>Predictions</th><th>True</th><th>False</th><th>FN</th><th>Mixed</th><th>Precision</th><th>Recall</th><th>Annotations matched</th><th>Predictions reviewed</th></tr></thead><tbody>{''.join(component_review_rows)}</tbody></table>
<h2>Semantic reason acceptance</h2>
<table><thead><tr><th>Reason</th><th>Gate</th><th>Target owner</th><th>Reviewed predictions</th><th>Precision / floor</th><th>Hard negatives / floor</th><th>Truncated records</th></tr></thead><tbody>{''.join(reason_acceptance_rows)}</tbody></table>
<h2>Corpus review</h2>
<table><thead><tr><th>ID</th><th>Family</th><th>Technical</th><th>Review</th><th>Known issues</th><th>Artifacts</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
"""
    path.write_text(document, encoding="utf-8")


def evaluate_corpus(
    manifest_path: Path,
    off_runs: Sequence[Path],
    shadow_runs: Sequence[Path],
    output: Path,
    *,
    min_entries: int = 100,
) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != "spb-smart-tga-golden-corpus-v1":
        raise ValueError("unsupported Smart TGA golden-corpus schema")
    entries = _load_manifest_entries(manifest, manifest_path)
    if not entries:
        raise ValueError("golden-corpus manifest must contain entries")
    ids = [str(entry.get("id") or "") for entry in entries]
    labels = [str(entry.get("paint_label") or "").replace("\\", "/") for entry in entries]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("golden-corpus entry ids must be non-empty and unique")
    if not all(labels) or len(set(labels)) != len(labels):
        raise ValueError("golden-corpus paint labels must be non-empty and unique")

    off_records = _load_records(off_runs, "off")
    shadow_records = _load_records(shadow_runs, "shadow")
    records = [
        _entry_record(entry, off_records.get(label), shadow_records.get(label))
        for entry, label in zip(entries, labels)
    ]
    output.mkdir(parents=True, exist_ok=True)
    for record in records:
        overlay = _write_component_review_overlay(record, output)
        if overlay:
            record.setdefault("artifacts", {})["component_review_overlay"] = overlay
    technical_pass = all(record.get("technical_pass") for record in records)
    metric_report = _aggregate_instance_metrics(records, manifest.get("metric_requirements") or {})
    metric_pass = bool(metric_report["passed"])
    component_review_metrics = _aggregate_component_reviews(records)
    semantic_review = _semantic_evidence_review_report(
        manifest.get("semantic_evidence_reviews") or {}, shadow_records
    )
    semantic_review_pass = bool(semantic_review["passed"] and semantic_review["coverage_pass"])
    canary_review = _canary_component_review_report(
        manifest.get("canary_component_reviews") or {}, shadow_records
    )
    canary_review_pass = bool(canary_review["passed"] and canary_review["coverage_pass"])
    ocr_region_review = _ocr_region_review_report(manifest, manifest_path)
    ocr_region_review_pass = bool(ocr_region_review["passed"])
    fully_reviewed_count = sum(bool(record.get("fully_reviewed")) for record in records)
    required = max(1, int(min_entries))
    review_pass = len(records) >= required and fully_reviewed_count == len(records)
    blockers = []
    if not technical_pass:
        blockers.append("one or more entries failed route, partition, reconstruction, shadow-neutrality, equivalence, or reviewed expectations")
    if not metric_pass:
        failed_metrics = [owner for owner, report in metric_report["owners"].items() if not report["passed"]]
        blockers.append(f"instance precision/recall or labeled-entry coverage is below gate for: {', '.join(failed_metrics)}")
    if len(records) < required:
        blockers.append(f"golden corpus has {len(records)} entries; release gate requires at least {required}")
    if fully_reviewed_count != len(records):
        blockers.append(f"only {fully_reviewed_count}/{len(records)} entries are fully reviewed across all five owners with no known issues")
    if not semantic_review["passed"]:
        blockers.append("one or more covered semantic-evidence annotations disagree with shadow telemetry")
    if not semantic_review["coverage_pass"]:
        blockers.append(
            f"semantic-evidence coverage is {semantic_review['covered_count']}/{semantic_review['review_count']} reviewed records"
        )
    if not canary_review["passed"]:
        blockers.append("one or more canary component annotations failed move/protection or rollback safety")
    if not canary_review["coverage_pass"]:
        blockers.append(
            f"canary-component coverage is {canary_review['covered_count']}/{canary_review['review_count']} reviewed records"
        )
    if not ocr_region_review_pass:
        blockers.append(
            f"OCR-region review coverage is {ocr_region_review.get('reviewed_count', 0)}/{ocr_region_review.get('prediction_count', 0)}"
        )
    release_pass = (
        technical_pass and metric_pass and review_pass
        and semantic_review_pass and canary_review_pass and ocr_region_review_pass
    )
    summary: dict[str, Any] = {
        "schema": "spb-smart-tga-golden-gate-v1",
        "manifest": str(manifest_path.resolve()),
        "off_runs": [str(Path(path).resolve()) for path in off_runs],
        "shadow_runs": [str(Path(path).resolve()) for path in shadow_runs],
        "entry_count": len(records),
        "required_entry_count": required,
        "technical_pass": bool(technical_pass),
        "instance_metrics": metric_report,
        "component_review_metrics": component_review_metrics,
        "metric_pass": metric_pass,
        "fully_reviewed_count": fully_reviewed_count,
        "review_pass": bool(review_pass),
        "semantic_evidence_reviews": semantic_review,
        "semantic_review_pass": semantic_review_pass,
        "canary_component_reviews": canary_review,
        "canary_review_pass": canary_review_pass,
        "ocr_region_reviews": ocr_region_review,
        "ocr_region_review_pass": ocr_region_review_pass,
        "release_pass": bool(release_pass),
        "blockers": blockers,
        "records": records,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_html(output / "review.html", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--off-run", action="append", type=Path, required=True)
    parser.add_argument("--shadow-run", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-entries", type=int, default=100)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero unless the complete release gate passes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = evaluate_corpus(
        args.manifest,
        args.off_run,
        args.shadow_run,
        args.output,
        min_entries=args.min_entries,
    )
    print(json.dumps({key: summary[key] for key in (
        "entry_count", "required_entry_count", "technical_pass", "metric_pass",
        "fully_reviewed_count", "review_pass", "semantic_review_pass",
        "canary_review_pass", "ocr_region_review_pass", "release_pass", "blockers",
    )}, indent=2))
    if args.strict and not summary["release_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
