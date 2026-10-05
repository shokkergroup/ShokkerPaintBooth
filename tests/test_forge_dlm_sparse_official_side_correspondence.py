from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import _forge_dlm_sparse_official_side_correspondence as subject


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_sparse_official_side_correspondence" / "run106_job.json"


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_point_in_triangle_is_local_and_rejects_extrapolation() -> None:
    triangle = np.asarray([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]])
    assert subject.point_in_triangle([2.0, 3.0], triangle)
    assert subject.point_in_triangle([0.0, 0.0], triangle)
    assert not subject.point_in_triangle([9.0, 9.0], triangle)
    assert not subject.point_in_triangle([-0.1, 2.0], triangle)


def test_three_point_affine_reports_orientation_without_repairing_it() -> None:
    uv = np.asarray([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]])
    positive = subject.fit_affine_three(uv, np.asarray([[4.0, 5.0], [24.0, 5.0], [4.0, 35.0]]))
    negative = subject.fit_affine_three(uv, np.asarray([[4.0, 5.0], [-16.0, 5.0], [4.0, 35.0]]))
    assert positive["determinant"] == 6.0
    assert negative["determinant"] == -6.0
    assert positive["anchor_residual_max_px"] == 0.0
    assert negative["anchor_residual_max_px"] == 0.0


def test_normalized_screen_coordinates_use_pixel_extent() -> None:
    record = {
        "view": {"source_size": [101, 51]},
        "active": {"xy_normalized": [0.25, 0.8]},
    }
    assert subject.normalized_screen_xy(record) == [25.0, 40.0]


def test_label_sets_are_augmented_only_by_exact_atlas_landmarks() -> None:
    inventory = {
        "islands": [
            {"physical_surface": "side_a", "topology_class": "paintable", "label_value": 7},
            {"physical_surface": "side_a", "topology_class": "unknown_abstain", "label_value": 8},
            {"physical_surface": "side_b", "topology_class": "paintable", "label_value": 9},
        ]
    }
    atlas = {
        "landmarks": [
            {"physical_surface": "side_a", "topology": {"label_value": 8}},
            {"physical_surface": "other", "topology": {"label_value": 10}},
        ]
    }
    assert subject._label_sets(inventory, atlas, ["side_a", "side_b"]) == {
        "side_a": {7, 8},
        "side_b": {9},
    }


def test_appearance_classification_never_side_relabels() -> None:
    labels = np.asarray([[0, 4, 5], [4, 4, 5]], dtype=np.uint16)
    view = {
        "physical_side": "a",
        "piece_maps": [
            {
                "map_id": "m",
                "surface_hint": "side",
                "fit_status": "fit",
                "cross_version_status": "cross",
                "physical_side": "a",
                "correspondences": [
                    {"uv_xy": [1, 0], "screen_xy": [3, 4], "split": "TRAIN"},
                    {"uv_xy": [2, 1], "screen_xy": [5, 6], "split": "HELDOUT"},
                    {"uv_xy": [0, 0], "screen_xy": [7, 8], "split": "TRAIN"},
                ],
            }
        ],
    }
    policy = {
        "side_surface_hint": "side",
        "accepted_piece_fit_status": "fit",
        "accepted_piece_cross_version_status": "cross",
    }
    result = subject._appearance_correspondences(
        view,
        labels,
        {"official_surface_id": "surface_a", "opposite_surface_id": "surface_b"},
        {"surface_a": {4}, "surface_b": {5}},
        policy,
    )
    assert [item["topology_classification"] for item in result] == [
        "TARGET_SIDE_TOPOLOGY",
        "OPPOSITE_SIDE_TOPOLOGY",
        "OUTSIDE_OFFICIAL_TOPOLOGY",
    ]


def test_report_validator_forbids_dense_or_delivery_claims() -> None:
    policy = {
        "minimum_positive_determinant": 0.1,
        "minimum_independent_points_per_piece": 3,
        "required_train_variant_ids": ["train_a", "train_b"],
        "required_heldout_variant_ids": ["holdout"],
    }
    report = {
        "$schema": subject.REPORT_SCHEMA,
        "side_contracts": {"a": {}},
        "views": [],
        "cross_version_groups": [],
        "metrics": {"promoted_cross_version_piece_count": 0},
        "claims": {
            "promoted_sparse_official_side_map": False,
            "dense_mapping": True,
            "whole_surface_mapping": False,
            "projector": False,
            "livery": False,
            "psd": False,
            "app": False,
            "delivery": True,
        },
    }
    errors = subject.validate_report(report, policy)
    assert "forbidden_claim_enabled:dense_mapping" in errors
    assert "forbidden_claim_enabled:delivery" in errors


def test_reusable_module_contains_no_scheme_or_variant_identity() -> None:
    source = (ROOT / "_forge_dlm_sparse_official_side_correspondence.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal lake", "sex wax", "v13", "v19", "v20"):
        assert forbidden not in source


def test_real_run_abstains_on_cross_version_side_polarity_contradiction(tmp_path: Path) -> None:
    output = tmp_path / "run106"
    result = subject.run(JOB, output)
    report = result["report"]
    audit = result["audit"]
    metrics = report["metrics"]

    assert audit["status"] == "PASS"
    assert report["promotion_status"] == "ABSTAIN_SIDE_POLARITY_CONTRADICTION"
    assert report["claims"]["side_polarity_contradiction_detected"] is True
    assert report["claims"]["promoted_sparse_official_side_map"] is False
    assert metrics["eligible_known_flat_side_view_count"] == 9
    assert metrics["exact_active_landmark_instance_count"] == 54
    assert metrics["distinct_exact_official_landmark_count"] == 12
    assert metrics["raw_known_flat_appearance_count"] == 409
    assert metrics["raw_known_flat_unique_uv_pixel_count"] == 344
    assert metrics["appearance_topology_classification_counts"] == {"OPPOSITE_SIDE_TOPOLOGY": 409}
    assert metrics["target_side_unique_uv_pixel_count"] == 0
    assert metrics["promoted_cross_version_piece_count"] == 0
    assert metrics["mirror_or_side_relabel_count"] == 0
    assert metrics["timestamp_only_pair_count"] == 0
    assert metrics["variant_metrics"] == {
        "v13": {
            "view_count": 3,
            "exact_anchor_instance_count": 18,
            "appearance_count": 111,
            "target_side_appearance_count": 0,
            "opposite_side_appearance_count": 111,
        },
        "v19": {
            "view_count": 3,
            "exact_anchor_instance_count": 18,
            "appearance_count": 171,
            "target_side_appearance_count": 0,
            "opposite_side_appearance_count": 171,
        },
        "v20": {
            "view_count": 3,
            "exact_anchor_instance_count": 18,
            "appearance_count": 127,
            "target_side_appearance_count": 0,
            "opposite_side_appearance_count": 127,
        },
    }
    assert all(group["status"] == "ABSTAIN_CROSS_VERSION_PIECE" for group in report["cross_version_groups"])
    assert audit["proof_hash_valid"] is True
    assert (output / "RUN106_SPARSE_OFFICIAL_SIDE_CONTACT.png").is_file()
    assert (output / "EXACT_OFFICIAL_SIDE_LANDMARK_PAIRS.csv").read_text(encoding="utf-8").count("\n") == 55


def test_real_run_is_byte_deterministic_in_place(tmp_path: Path) -> None:
    output = tmp_path / "run106"
    subject.run(JOB, output)
    before = file_hashes(output)
    subject.run(JOB, output)
    after = file_hashes(output)
    assert before == after

