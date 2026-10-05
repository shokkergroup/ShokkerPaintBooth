from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_neutral_multisurface_correspondence import (
    DIRECT_FIT_STATUS,
    EvidenceError,
    build,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_JOB = (
    ROOT
    / "_forge_data"
    / "dlm_neutral_multisurface_correspondence"
    / "run119_job.json"
)
RUN101 = (
    ROOT
    / "_forge_out"
    / "codex_full_uv_recovery"
    / "run_101_known_flat_calibration"
    / "known_flat_calibration_report.json"
)
LABELS = (
    ROOT
    / "_forge_out"
    / "codex_full_uv_recovery"
    / "run_70_v7_exact_topology"
    / "dlm_exact_topology_labels.png"
)
DECODER = (
    ROOT
    / "_forge_out"
    / "codex_full_uv_recovery"
    / "run_113_full_topology_calibration_v2"
    / "FULL_TOPOLOGY_COMPONENT_DECODER_V2.json"
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    return path


def _direct_counts(run101: dict) -> tuple[int, int]:
    pieces = [
        piece
        for view in run101["views"]
        for piece in view.get("piece_maps", [])
        if piece.get("fit_status") == DIRECT_FIT_STATUS
    ]
    return len(pieces), sum(len(piece.get("correspondences", [])) for piece in pieces)


def _job_for_run101(tmp_path: Path, run101: dict, name: str = "run101.json") -> Path:
    source = _write_json(tmp_path / name, run101)
    job = _read_json(ACTIVE_JOB)
    job["sources"]["run101_known_flat_report"] = {
        "path": str(source),
        "sha256": sha256_file(source),
    }
    piece_count, match_count = _direct_counts(run101)
    job["run101_direct_lock"] = {
        "direct_piece_count": piece_count,
        "direct_match_count": match_count,
    }
    return _write_json(tmp_path / f"job_{name}", job)


def _clone_direct_view(
    source_view: dict,
    view_id: str,
    variant_id: str,
    piece_ids: set[str],
) -> dict:
    clone = copy.deepcopy(source_view)
    clone["view_id"] = view_id
    clone["expected_variant_id"] = variant_id
    clone["variant_role"] = "TRAIN_VARIANT" if variant_id != "v20" else "HELDOUT_VARIANT"
    clone["camera_role"] = f"opaque_camera_{view_id}"
    clone["piece_maps"] = [
        piece for piece in clone["piece_maps"] if piece.get("piece_id") in piece_ids
    ]
    for index, piece in enumerate(clone["piece_maps"]):
        piece["variant_id"] = variant_id
        piece["variant_role"] = clone["variant_role"]
        piece["camera_role"] = clone["camera_role"]
        piece["surface_hint"] = f"opaque_hint_{index}"
        piece["map_id"] = f"{view_id}::direct_{index}"
    return clone


def _expanded_hood_control(include_v20: bool) -> dict:
    run101 = _read_json(RUN101)
    source_view = next(view for view in run101["views"] if view["view_id"] == "view_10")
    piece_ids = {"hood_upper", "hood_lower"}
    run101["views"].append(
        _clone_direct_view(source_view, "synthetic_train_v19", "v19", piece_ids)
    )
    if include_v20:
        run101["views"].append(
            _clone_direct_view(source_view, "synthetic_heldout_v20", "v20", piece_ids)
        )
    return run101


def test_active_run119_consumes_all_direct_records_and_abstains_unsupported(
    tmp_path: Path,
) -> None:
    report = build(ACTIVE_JOB, tmp_path / "active")
    metrics = report["metrics"]

    assert report["status"] == "PASS_NEUTRAL_MULTISURFACE_DIRECT_SUPPORT_NOT_DELIVERY"
    assert report["global_failures"] == []
    assert metrics["direct_piece_count"] == 13
    assert metrics["direct_match_count"] == 463
    assert metrics["exactly_classified_direct_match_count"] == 463
    assert metrics["unclassified_direct_match_count"] == 0
    assert metrics["observed_component_token_count"] == 51
    assert metrics["unique_uv_pixel_count"] == 393
    assert metrics["promoted_match_count"] == 409
    assert metrics["promoted_component_token_count"] == 48
    assert metrics["abstained_match_count"] == 54
    assert metrics["new_abstained_component_token_count"] == 3
    assert metrics["exact_token_cluster_count"] == 4
    assert metrics["promoted_token_cluster_count"] == 2
    assert metrics["abstained_token_cluster_count"] == 2
    assert report["run117_deltas"] == {
        "direct_match_count_delta": 54,
        "observed_component_token_count_delta": 3,
        "promoted_component_token_count_delta": 0,
        "promoted_match_count_delta": 0,
        "unique_uv_pixel_count_delta": 49,
    }
    assert report["claims"]["named_physical_surface_authority"] is False
    assert report["claims"]["physical_view_polarity"] is False
    assert report["claims"]["livery"] is False
    assert report["claims"]["psd"] is False


def test_active_contact_exposes_four_untrusted_observation_buckets(
    tmp_path: Path,
) -> None:
    report = build(ACTIVE_JOB, tmp_path / "contact")
    buckets = report["observation_display_buckets_untrusted"]

    assert {key: value["direct_match_count"] for key, value in buckets.items()} == {
        "side": 325,
        "front": 84,
        "top": 32,
        "rear": 22,
    }
    assert all(value["display_bucket_is_authority"] is False for value in buckets.values())
    contact = tmp_path / "contact" / "RUN119_NEUTRAL_MULTISURFACE_CONTACT.png"
    with Image.open(contact) as image:
        assert image.size == (2500, 1900)
    assert contact.stat().st_size > 100_000


def test_every_direct_match_uses_exact_run113_label_and_token(tmp_path: Path) -> None:
    build(ACTIVE_JOB, tmp_path / "exact")
    matches = _read_json(
        tmp_path / "exact" / "NEUTRAL_MULTISURFACE_DIRECT_MATCHES.json"
    )
    with Image.open(LABELS) as image:
        labels = np.asarray(image.copy())
    if labels.ndim == 3:
        labels = labels[:, :, 0].astype(np.uint32) + (
            labels[:, :, 1].astype(np.uint32) << 8
        )
    decoder = _read_json(DECODER)
    token_by_label = {
        int(item["label_value"]): item["component_token"]
        for item in decoder["components"]
    }

    assert len(matches) == 463
    for item in matches:
        label = int(labels[item["uv_y"], item["uv_x"]])
        assert item["label_value"] == label
        assert item["component_token"] == token_by_label[label]
        assert item["classification_status"] == "EXACT_RUN113_COMPONENT_TOKEN"


def test_synthetic_control_untrusted_labels_do_not_change_promotion(
    tmp_path: Path,
) -> None:
    baseline = build(ACTIVE_JOB, tmp_path / "baseline")
    run101 = _read_json(RUN101)
    for view_index, view in enumerate(run101["views"]):
        view["camera_role"] = f"opaque_camera_label_{view_index}"
        for piece_index, piece in enumerate(view.get("piece_maps", [])):
            piece["camera_role"] = view["camera_role"]
            piece["surface_hint"] = f"opaque_surface_label_{piece_index}"
    job = _job_for_run101(tmp_path, run101, "relabeled_run101.json")
    relabeled = build(job, tmp_path / "relabeled")

    keys = (
        "direct_match_count",
        "observed_component_token_count",
        "promoted_match_count",
        "promoted_component_token_count",
        "exact_token_cluster_count",
        "promoted_token_cluster_count",
    )
    assert {key: baseline["metrics"][key] for key in keys} == {
        key: relabeled["metrics"][key] for key in keys
    }
    baseline_clusters = sorted(
        (item["cluster_id"], item["status"], item["component_tokens"])
        for item in baseline["clusters"]
    )
    relabeled_clusters = sorted(
        (item["cluster_id"], item["status"], item["component_tokens"])
        for item in relabeled["clusters"]
    )
    assert relabeled_clusters == baseline_clusters


def test_synthetic_control_exact_token_multiversion_cluster_can_promote(
    tmp_path: Path,
) -> None:
    run101 = _expanded_hood_control(include_v20=True)
    job = _job_for_run101(tmp_path, run101, "supported_run101.json")
    report = build(job, tmp_path / "supported")

    assert report["status"] == "PASS_NEUTRAL_MULTISURFACE_DIRECT_SUPPORT_NOT_DELIVERY"
    assert report["metrics"]["direct_piece_count"] == 17
    assert report["metrics"]["direct_match_count"] == 527
    assert report["metrics"]["promoted_token_cluster_count"] == 3
    assert report["metrics"]["promoted_match_count"] == 505
    promoted = [
        item
        for item in report["clusters"]
        if item["status"] == "PROMOTED_DIRECT_TOKEN_CLUSTER"
    ]
    assert any(
        {"v13", "v19"} == set(item["train_variant_ids"])
        and item["heldout_variant_ids"] == ["v20"]
        and len(item["component_tokens"]) == 2
        for item in promoted
    )


def test_withheld_variant_missing_keeps_synthetic_cluster_abstained(
    tmp_path: Path,
) -> None:
    run101 = _expanded_hood_control(include_v20=False)
    job = _job_for_run101(tmp_path, run101, "missing_holdout_run101.json")
    report = build(job, tmp_path / "missing_holdout")

    two_token_clusters = [
        item for item in report["clusters"] if len(item["component_tokens"]) == 2
    ]
    assert len(two_token_clusters) == 1
    cluster = two_token_clusters[0]
    assert cluster["status"] == "ABSTAIN_DIRECT_TOKEN_CLUSTER"
    assert "required_heldout_variants_not_all_supported" in cluster["reasons"]
    assert cluster["train_variant_ids"] == ["v13", "v19"]
    assert cluster["heldout_variant_ids"] == []


def test_reflected_withheld_piece_fails_local_and_cluster_gates(tmp_path: Path) -> None:
    run101 = _read_json(RUN101)
    view = next(item for item in run101["views"] if item["view_id"] == "view_04")
    piece = next(
        item
        for item in view["piece_maps"]
        if item.get("fit_status") == DIRECT_FIT_STATUS
    )
    piece["reflection"] = True
    job = _job_for_run101(tmp_path, run101, "reflected_run101.json")
    report = build(job, tmp_path / "reflected")

    rejected_piece = next(
        item for item in report["piecewise_correspondences"] if item["view_id"] == "view_04"
    )
    assert rejected_piece["local_status"] == "ABSTAIN"
    assert rejected_piece["piece_status"] == "ABSTAIN_DIRECT_LOCAL_PIECE"
    assert "reflection_forbidden" in rejected_piece["reasons"]
    assert report["metrics"]["reflected_piece_count"] == 1
    assert report["metrics"]["promoted_token_cluster_count"] == 1


def test_hash_drift_fails_closed(tmp_path: Path) -> None:
    job = _read_json(ACTIVE_JOB)
    job["sources"]["run101_known_flat_report"]["sha256"] = "0" * 64
    job_path = _write_json(tmp_path / "stale_job.json", job)

    with pytest.raises(EvidenceError, match="run101_known_flat_report_sha256_mismatch"):
        build(job_path, tmp_path / "stale")


def test_run106_contradiction_drift_is_not_reinterpreted(tmp_path: Path) -> None:
    run106_path = Path(
        _read_json(ACTIVE_JOB)["sources"]["run106_contradiction_report"]["path"]
    )
    run106 = _read_json(ROOT / run106_path)
    run106["metrics"]["raw_known_flat_appearance_count"] = 408
    source = _write_json(tmp_path / "mutated_run106.json", run106)
    job = _read_json(ACTIVE_JOB)
    job["sources"]["run106_contradiction_report"] = {
        "path": str(source),
        "sha256": sha256_file(source),
    }
    job_path = _write_json(tmp_path / "run106_drift_job.json", job)
    report = build(job_path, tmp_path / "run106_drift")

    assert report["status"] == "ABSTAIN_NEUTRAL_MULTISURFACE_DIRECT_SUPPORT_NOT_DELIVERY"
    assert "run106_quarantine_mismatch:raw_known_flat_appearance_count" in report[
        "global_failures"
    ]
    assert report["claims"]["physical_view_polarity"] is False
    assert report["claims"]["reflection"] is False


def test_new_text_artifacts_are_ascii_clean(tmp_path: Path) -> None:
    build(ACTIVE_JOB, tmp_path / "ascii")
    source_files = [
        ROOT / "_forge_dlm_neutral_multisurface_correspondence.py",
        Path(__file__),
        ACTIVE_JOB,
        ACTIVE_JOB.parent / "README.md",
    ]
    generated = [
        path
        for path in (tmp_path / "ascii").rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".csv", ".md"}
    ]
    for path in source_files + generated:
        assert all(byte < 128 for byte in path.read_bytes()), path
