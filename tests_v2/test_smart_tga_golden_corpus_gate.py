import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts.smart_tga_golden_corpus_gate import (
    OWNERS,
    _canary_component_review_report,
    _instance_metrics,
    _load_manifest_entries,
    _semantic_evidence_review_report,
    evaluate_corpus,
)


def test_entry_manifests_merge_once_and_duplicate_validation_remains_central(tmp_path):
    shard = tmp_path / "shard.json"
    shard.write_text(json.dumps({
        "schema": "spb-smart-tga-golden-entries-v1",
        "entries": [{"id": "external", "paint_label": "family/external.tga"}],
    }), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    entries = _load_manifest_entries(
        {
            "entries": [{"id": "base", "paint_label": "family/base.tga"}],
            "entry_manifests": ["shard.json"],
        },
        manifest_path,
    )
    assert [entry["id"] for entry in entries] == ["base", "external"]

    shard.write_text(json.dumps({
        "schema": "spb-smart-tga-golden-entries-v1",
        "entry_manifests": ["nested.json"],
        "entries": [{"id": "external", "paint_label": "family/external.tga"}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="nested golden entry manifests"):
        _load_manifest_entries({"entries": [], "entry_manifests": ["shard.json"]}, manifest_path)


def _write_run(root: Path, role: str, *, changed: bool = False) -> Path:
    run = root / role
    sample = run / "sample"
    masks_dir = sample / "masks"
    masks_dir.mkdir(parents=True)
    source = np.zeros((8, 8, 4), np.uint8)
    source[:, :, :3] = np.arange(8, dtype=np.uint8)[None, :, None] * 20
    source[:, :, 3] = 255
    source_path = sample / "source_1024.png"
    Image.fromarray(source, "RGBA").save(source_path)

    owner_masks = {owner: np.zeros((8, 8), bool) for owner in OWNERS}
    owner_masks["numbers"][1:3, 1:3] = True
    owner_masks["template"][0, :] = True
    owner_masks["paint"] = ~np.logical_or(owner_masks["numbers"], owner_masks["template"])
    if changed:
        owner_masks["paint"][6, 6] = False
        owner_masks["sponsors"][6, 6] = True
    mask_paths = {}
    for owner, mask in owner_masks.items():
        path = masks_dir / f"{owner}.png"
        Image.fromarray(mask.astype(np.uint8) * 255, "L").save(path)
        mask_paths[owner] = str(path.resolve())

    shadow = {
        "mode": "shadow" if role == "shadow" else "off",
        "status": "shadow" if role == "shadow" else "off",
        "output_applied": False,
        "changed_node_count": 0,
        "xor_pixels": {owner: 0 for owner in OWNERS},
    }
    records = [{
        "paint_label": "test/sample.tga",
        "success": True,
        "elapsed_sec": 0.1,
        "route_engine": "test",
        "route_smart_tga": {"build": "smart-tga-cycle-test"},
        "route_adjudicator_shadow": shadow,
        "source_1024": str(source_path.resolve()),
        "mask_paths": mask_paths,
    }]
    (run / "inspection_records.json").write_text(json.dumps(records), encoding="utf-8")
    return run


def _write_manifest(root: Path) -> Path:
    path = root / "manifest.json"
    path.write_text(json.dumps({
        "schema": "spb-smart-tga-golden-corpus-v1",
        "entries": [{
            "id": "sample",
            "family": "test",
            "paint_label": "test/sample.tga",
            "expected_build_prefix": "smart-tga-cycle-",
            "review_status": "approved",
            "reviewed_owners": list(OWNERS),
            "known_issues": [],
            "expected": {
                "numbers": {
                    "component_count": 1,
                    "component_bboxes": [[1, 1, 2, 2]],
                },
            },
        }],
    }), encoding="utf-8")
    return path


def test_smart_tga_golden_gate_proves_partition_reconstruction_equivalence_and_review(tmp_path):
    manifest = _write_manifest(tmp_path)
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow")

    summary = evaluate_corpus(manifest, [off], [shadow], tmp_path / "report", min_entries=1)

    assert summary["technical_pass"] is True
    assert summary["metric_pass"] is True
    assert summary["review_pass"] is True
    assert summary["release_pass"] is True
    assert summary["records"][0]["off_partition"]["gap_pixels"] == 0
    assert summary["records"][0]["off_partition"]["overlap_pixels"] == 0
    assert summary["records"][0]["off_partition"]["reconstruction_mismatch_pixels"] == 0
    assert summary["records"][0]["off_shadow_equivalence"]["byte_identical"] is True
    metrics = summary["records"][0]["expectations"]["owners"]["numbers"]["instance_metrics"]
    assert metrics["true_positive"] == 1
    assert metrics["false_positive"] == 0
    assert metrics["false_negative"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert (tmp_path / "report" / "review.html").is_file()


def test_smart_tga_instance_metrics_scores_an_explicit_empty_control_as_correct():
    metrics = _instance_metrics([], [], 0.95)

    assert metrics["true_positive"] == 0
    assert metrics["false_positive"] == 0
    assert metrics["false_negative"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0


def test_smart_tga_instance_metrics_counts_unmatched_predictions_and_labels():
    metrics = _instance_metrics(
        [[0, 0, 10, 10], [30, 0, 5, 5]],
        [[0, 0, 10, 10], [15, 0, 10, 10]],
        0.50,
    )

    assert metrics["true_positive"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5


def test_smart_tga_golden_gate_rejects_one_pixel_off_shadow_drift(tmp_path):
    manifest = _write_manifest(tmp_path)
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow", changed=True)

    summary = evaluate_corpus(manifest, [off], [shadow], tmp_path / "report", min_entries=1)

    assert summary["technical_pass"] is False
    assert summary["release_pass"] is False
    assert summary["records"][0]["off_shadow_equivalence"]["pixel_identical"] is False
    assert summary["records"][0]["off_shadow_equivalence"]["owners"]["sponsors"]["xor_pixels"] == 1
    assert summary["records"][0]["off_shadow_equivalence"]["owners"]["paint"]["xor_pixels"] == 1


def test_shadow_proposals_are_telemetry_not_output_mutation(tmp_path):
    manifest = _write_manifest(tmp_path)
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow")
    records_path = shadow / "inspection_records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    records[0]["route_adjudicator_shadow"].update({
        "changed_node_count": 2,
        "xor_pixels": {**{owner: 0 for owner in OWNERS}, "numbers": 12, "template": 12},
    })
    records_path.write_text(json.dumps(records), encoding="utf-8")

    summary = evaluate_corpus(manifest, [off], [shadow], tmp_path / "report", min_entries=1)

    report = summary["records"][0]["shadow_neutral"]
    assert summary["technical_pass"] is True
    assert report["passed"] is True
    assert report["proposal_changed"] is True
    assert report["proposal_neutral"] is False


def test_smart_tga_golden_gate_keeps_small_partial_corpus_out_of_release(tmp_path):
    manifest = _write_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["entries"][0]["review_status"] = "partial"
    payload["entries"][0]["reviewed_owners"] = ["numbers"]
    payload["entries"][0]["known_issues"] = ["semantic review incomplete"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow")

    summary = evaluate_corpus(manifest, [off], [shadow], tmp_path / "report", min_entries=100)

    assert summary["technical_pass"] is True
    assert summary["review_pass"] is False
    assert summary["release_pass"] is False
    assert summary["fully_reviewed_count"] == 0
    assert any("requires at least 100" in blocker for blocker in summary["blockers"])


def test_smart_tga_golden_gate_allows_successful_partial_rerun_to_replace_failure(tmp_path):
    manifest = _write_manifest(tmp_path)
    failed_run = tmp_path / "off_failed"
    failed_run.mkdir()
    (failed_run / "inspection_records.json").write_text(json.dumps([{
        "paint_label": "test/sample.tga",
        "success": False,
        "error": "paint_file not found",
    }]), encoding="utf-8")
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow")

    summary = evaluate_corpus(manifest, [failed_run, off], [shadow], tmp_path / "report", min_entries=1)

    assert summary["technical_pass"] is True
    assert summary["release_pass"] is True


def test_smart_tga_golden_gate_enforces_metric_label_coverage(tmp_path):
    manifest = _write_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["metric_requirements"] = {
        "numbers": {"min_labeled_entries": 2, "min_precision": 0.98, "min_recall": 0.90},
        "sponsors": {"min_labeled_entries": 1, "min_precision": 0.95, "min_recall": 0.85},
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow")

    summary = evaluate_corpus(manifest, [off], [shadow], tmp_path / "report", min_entries=1)

    assert summary["technical_pass"] is True
    assert summary["instance_metrics"]["owners"]["numbers"]["precision"] == 1.0
    assert summary["instance_metrics"]["owners"]["numbers"]["recall"] == 1.0
    assert summary["instance_metrics"]["owners"]["numbers"]["labeled_entries"] == 1
    assert summary["instance_metrics"]["owners"]["sponsors"]["labeled_entries"] == 0
    assert summary["metric_pass"] is False
    assert summary["release_pass"] is False
    assert any("numbers, sponsors" in blocker for blocker in summary["blockers"])


def test_smart_tga_golden_gate_scores_reviewed_true_and_false_predictions(tmp_path):
    manifest = _write_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["entries"][0]["component_reviews"] = {
        "numbers": {
            "component_min_area": 1,
            "iou_threshold": 0.95,
            "require_all_predictions_reviewed": True,
            "min_reviewed_precision": 0.95,
            "true_bboxes": [],
            "false_bboxes": [[1, 1, 2, 2]],
            "mixed_bboxes": [],
        },
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow")

    summary = evaluate_corpus(manifest, [off], [shadow], tmp_path / "report", min_entries=1)

    review = summary["records"][0]["component_reviews"]["owners"]["numbers"]
    assert review["matched_count"] == 1
    assert review["true_count"] == 0
    assert review["false_count"] == 1
    assert review["mixed_count"] == 0
    assert review["false_negative_count"] == 0
    assert review["reviewed_precision"] == 0.0
    assert review["reviewed_recall"] == 1.0
    assert review["unmatched_annotations"] == []
    assert review["unreviewed_predictions"] == []
    assert review["passed"] is False
    assert summary["technical_pass"] is False
    assert summary["component_review_metrics"]["owners"]["numbers"]["false_count"] == 1
    overlay = Path(summary["records"][0]["artifacts"]["component_review_overlay"])
    assert overlay.is_file()
    assert overlay.stat().st_size > 0


def test_smart_tga_golden_gate_counts_missing_source_instances_as_false_negatives(tmp_path):
    manifest = _write_manifest(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["entries"][0]["component_reviews"] = {
        "numbers": {
            "component_min_area": 1,
            "iou_threshold": 0.95,
            "missing_iou_threshold": 0.50,
            "require_all_predictions_reviewed": True,
            "min_reviewed_precision": 0.95,
            "min_reviewed_recall": 0.75,
            "true_bboxes": [[1, 1, 2, 2]],
            "false_bboxes": [],
            "mixed_bboxes": [],
            "missing_bboxes": [[5, 5, 2, 2]],
        },
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    off = _write_run(tmp_path, "off")
    shadow = _write_run(tmp_path, "shadow")

    summary = evaluate_corpus(manifest, [off], [shadow], tmp_path / "report", min_entries=1)

    review = summary["records"][0]["component_reviews"]["owners"]["numbers"]
    assert review["true_count"] == 1
    assert review["false_count"] == 0
    assert review["false_negative_count"] == 1
    assert review["reviewed_precision"] == 1.0
    assert review["reviewed_recall"] == 0.5
    assert review["missing_source_annotations"] == [{
        "bbox": [5, 5, 2, 2],
        "recovered": False,
        "matched_actual_index": None,
        "iou": 0.0,
    }]
    assert review["passed"] is False
    assert summary["component_review_metrics"]["owners"]["numbers"]["false_negative_count"] == 1


def test_semantic_evidence_reviews_gate_votes_hard_negatives_and_coverage():
    label = "test/semantic.tga"
    shadow_records = {label: {
        "route_adjudicator_shadow": {
            "semantic_family": {"samples": [{
                "bbox": [10, 20, 30, 40],
                "to": "template",
                "reason": "repeated_hardware",
            }]},
        },
    }}
    specification = {
        "iou_threshold": 0.9,
        "reason_acceptance": {
            "repeated_hardware": {
                "target_owner": "template",
                "min_reviewed_predictions": 1,
                "min_reviewed_precision": 1.0,
                "min_hard_negatives": 1,
                "require_all_predictions_reviewed": True,
            },
        },
        "records": [
            {
                "paint_label": label,
                "bbox": [10, 20, 30, 40],
                "verdict": "vote",
                "target_owner": "template",
                "reason": "repeated_hardware",
            },
            {
                "paint_label": label,
                "bbox": [70, 80, 10, 10],
                "verdict": "hard_negative",
            },
        ],
    }

    report = _semantic_evidence_review_report(specification, shadow_records)

    assert report["passed"] is True
    assert report["coverage_pass"] is True
    assert report["matched_count"] == 2
    reason_gate = report["reason_acceptance"]["repeated_hardware"]
    assert reason_gate["passed"] is True
    assert reason_gate["prediction_count"] == 1
    assert reason_gate["reviewed_prediction_count"] == 1
    assert reason_gate["hard_negative_count"] == 1

    unreviewed_prediction = json.loads(json.dumps(shadow_records))
    unreviewed_prediction[label]["route_adjudicator_shadow"]["semantic_family"]["samples"].append({
        "bbox": [100, 100, 10, 10],
        "to": "template",
        "reason": "repeated_hardware",
    })
    rejected = _semantic_evidence_review_report(specification, unreviewed_prediction)
    assert rejected["passed"] is False
    assert rejected["reason_acceptance"]["repeated_hardware"]["reviewed_precision"] == 0.5

    wrong_target = json.loads(json.dumps(specification))
    wrong_target["records"][0]["target_owner"] = "paint"
    assert _semantic_evidence_review_report(wrong_target, shadow_records)["passed"] is False

    missing = json.loads(json.dumps(specification))
    missing["records"][1]["paint_label"] = "missing/control.tga"
    missing_report = _semantic_evidence_review_report(missing, shadow_records)
    assert missing_report["passed"] is True
    assert missing_report["coverage_pass"] is False


def test_semantic_review_resolves_same_bbox_by_owner_and_reason():
    label = "family/car.tga"
    shadow_records = {label: {"route_adjudicator_shadow": {"semantic_family": {
        "samples": [
            {
                "bbox": [10, 12, 30, 18],
                "to": "paint",
                "reason": "older_flat_dark_reason",
            },
            {
                "bbox": [10, 12, 30, 18],
                "to": "paint",
                "reason": "paint_palette_livery_surface",
            },
        ],
    }}}}
    specification = {"records": [{
        "paint_label": label,
        "bbox": [10, 12, 30, 18],
        "verdict": "vote",
        "target_owner": "paint",
        "reason": "paint_palette_livery_surface",
    }]}

    report = _semantic_evidence_review_report(specification, shadow_records)

    assert report["passed"] is True
    assert report["matched_count"] == 1
    assert report["records"][0]["actual_reason"] == "paint_palette_livery_surface"


def test_canary_component_reviews_require_safe_move_protection_and_coverage():
    label = "test/canary.tga"
    records = {label: {"route_adjudicator_shadow": {"evidence_canary": {
        "status": "simulated",
        "output_applied": False,
        "hard_partition": True,
        "reconstruction_mismatch_pixels": 0,
        "rollback_exact": True,
        "rollback_xor_pixels": {owner: 0 for owner in OWNERS},
        "samples": [{
            "bbox": [10, 20, 30, 40],
            "from": "sponsors",
            "to": "template",
            "reason": "carbon_family",
        }],
    }}}}
    specification = {"records": [
        {
            "paint_label": label,
            "bbox": [10, 20, 30, 40],
            "verdict": "move",
            "from": "sponsors",
            "to": "template",
            "reason": "carbon_family",
        },
        {
            "paint_label": label,
            "bbox": [70, 80, 10, 10],
            "verdict": "protected",
            "owner": "sponsors",
        },
    ]}

    report = _canary_component_review_report(specification, records)

    assert report["passed"] is True
    assert report["coverage_pass"] is True
    assert report["matched_count"] == 2

    unsafe = json.loads(json.dumps(records))
    unsafe[label]["route_adjudicator_shadow"]["evidence_canary"]["rollback_exact"] = False
    assert _canary_component_review_report(specification, unsafe)["passed"] is False

    missing = json.loads(json.dumps(specification))
    missing["records"][1]["paint_label"] = "missing/canary.tga"
    assert _canary_component_review_report(missing, records)["coverage_pass"] is False
