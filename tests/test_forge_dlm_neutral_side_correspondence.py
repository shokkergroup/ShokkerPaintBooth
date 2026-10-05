from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_dlm_neutral_side_correspondence import (
    EXPECTED_RUN106_APPEARANCES,
    JOB_SCHEMA,
    OPAQUE_SIDE_IDS,
    build,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data/dlm_neutral_side_correspondence/run117_job.json"
MODULE = ROOT / "_forge_dlm_neutral_side_correspondence.py"
RUN113 = ROOT / "_forge_out/codex_full_uv_recovery/run_113_full_topology_calibration_v2"
LABELS = ROOT / "_forge_out/codex_full_uv_recovery/run_70_v7_exact_topology/dlm_exact_topology_labels.png"


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _mutated_job(tmp_path: Path, source_name: str, value: object) -> Path:
    job = json.loads(JOB.read_text(encoding="utf-8"))
    source_path = _write_json(tmp_path / f"{source_name}.json", value)
    job["workspace_root"] = str(ROOT)
    job["sources"][source_name] = {
        "path": str(source_path),
        "sha256": sha256_file(source_path),
    }
    return _write_json(tmp_path / "job.json", job)


def test_run117_promotes_two_opaque_groups_from_all_409_direct_matches(
    tmp_path: Path,
) -> None:
    report = build(JOB, tmp_path / "out")

    assert report["status"] == "PASS_NEUTRAL_DIRECT_SPARSE_CORRESPONDENCE_NOT_DELIVERY"
    assert report["global_failures"] == []
    metrics = report["metrics"]
    assert metrics["selected_view_count"] == 9
    assert metrics["selected_piece_count"] == 9
    assert metrics["positive_determinant_piece_count"] == 9
    assert metrics["reflected_piece_count"] == 0
    assert metrics["direct_match_count"] == EXPECTED_RUN106_APPEARANCES
    assert metrics["train_match_count"] == 282
    assert metrics["heldout_match_count"] == 127
    assert metrics["unique_uv_pixel_count"] == 344
    assert metrics["observed_component_token_count"] == 48
    assert metrics["unobserved_component_token_count"] == 517
    assert metrics["promoted_neutral_group_count"] == 2
    assert metrics["semantic_side_claim_count"] == 0
    assert metrics["mirror_or_relabel_count"] == 0


def test_v13_v19_train_and_v20_holdout_support_gates_are_explicit(
    tmp_path: Path,
) -> None:
    report = build(JOB, tmp_path / "out")
    groups = {item["neutral_side_id"]: item for item in report["groups"]}
    assert set(groups) == set(OPAQUE_SIDE_IDS)
    for group in groups.values():
        assert group["status"] == "PROMOTED_NEUTRAL_DIRECT_SPARSE_CORRESPONDENCE"
        assert group["train_variant_ids"] == ["v13", "v19"]
        assert group["heldout_variant_ids"] == ["v20"]
        assert group["reasons"] == []
    assert groups["physical_side_a"]["heldout_component_token_support_fraction"] == 0.761904762
    assert groups["physical_side_b"]["heldout_component_token_support_fraction"] == 1.0
    assert groups["physical_side_a"]["residual_envelope"]["heldout_piece_heldout_p95_px_max"] == 4.985703
    assert groups["physical_side_b"]["residual_envelope"]["heldout_piece_heldout_p95_px_max"] == 2.495758


def test_every_match_is_classified_by_exact_run113_label_and_token(
    tmp_path: Path,
) -> None:
    build(JOB, tmp_path / "out")
    matches = json.loads(
        (tmp_path / "out/NEUTRAL_SIDE_DIRECT_MATCHES.json").read_text(
            encoding="utf-8"
        )
    )
    decoder = json.loads(
        (RUN113 / "FULL_TOPOLOGY_COMPONENT_DECODER_V2.json").read_text(
            encoding="utf-8"
        )
    )
    token_by_label = {
        int(item["label_value"]): item["component_token"]
        for item in decoder["components"]
    }
    labels = np.asarray(Image.open(LABELS))
    assert len(matches) == 409
    assert len({(item["uv_x"], item["uv_y"]) for item in matches}) == 344
    for item in matches:
        label = int(labels[item["uv_y"], item["uv_x"]])
        assert item["label_value"] == label
        assert item["component_token"] == token_by_label[label]
        assert item["classification_status"] == "EXACT_RUN113_COMPONENT_TOKEN"


def test_run106_contradiction_is_locked_as_regression_input(tmp_path: Path) -> None:
    report = build(JOB, tmp_path / "out")
    regression = report["run106_regression"]
    assert regression["status"] == "ABSTAIN_SIDE_POLARITY_CONTRADICTION"
    assert regression["raw_appearance_count"] == 409
    assert regression["opposite_classification_count"] == 409
    assert regression["target_classification_count"] == 0
    assert regression["neutral_direct_match_count"] == 409


def test_run106_metric_drift_fails_closed(tmp_path: Path) -> None:
    original = json.loads(
        (
            ROOT
            / "_forge_out/codex_full_uv_recovery/run_106_sparse_official_side_correspondence/SPARSE_OFFICIAL_SIDE_CORRESPONDENCE_REPORT.json"
        ).read_text(encoding="utf-8")
    )
    original["metrics"]["appearance_topology_classification_counts"][
        "OPPOSITE_SIDE_TOPOLOGY"
    ] = 408
    job_path = _mutated_job(tmp_path, "run106_contradiction_report", original)

    report = build(job_path, tmp_path / "out")

    assert report["status"] == "ABSTAIN_NEUTRAL_CORRESPONDENCE_NOT_DELIVERY"
    assert "run106_regression_mismatch:opposite_side_appearance_count" in report[
        "global_failures"
    ]


def test_source_semantic_side_fields_are_not_used_for_neutral_roles(
    tmp_path: Path,
) -> None:
    original = json.loads(
        (
            ROOT
            / "_forge_out/codex_full_uv_recovery/run_101_known_flat_calibration/known_flat_calibration_report.json"
        ).read_text(encoding="utf-8")
    )
    for view in original["views"]:
        view["physical_side"] = "source_semantics_quarantined"
        for piece in view.get("piece_maps", []):
            piece["physical_side"] = "source_semantics_quarantined"
    job_path = _mutated_job(tmp_path, "run101_known_flat_report", original)

    report = build(job_path, tmp_path / "out")

    assert report["status"] == "PASS_NEUTRAL_DIRECT_SPARSE_CORRESPONDENCE_NOT_DELIVERY"
    assert report["metrics"]["direct_match_count"] == 409
    assert report["metrics"]["promoted_neutral_group_count"] == 2


def test_reflection_or_nonpositive_local_piece_is_not_promoted(tmp_path: Path) -> None:
    original = json.loads(
        (
            ROOT
            / "_forge_out/codex_full_uv_recovery/run_101_known_flat_calibration/known_flat_calibration_report.json"
        ).read_text(encoding="utf-8")
    )
    selected = next(item for item in original["views"] if item["view_id"] == "view_05")
    piece = next(item for item in selected["piece_maps"] if item["piece_id"] == "side_center")
    piece["matrix_uv_to_screen"][0][0] *= -1
    piece["determinant"] = -abs(piece["determinant"])
    piece["reflection"] = True
    job_path = _mutated_job(tmp_path, "run101_known_flat_report", original)

    report = build(job_path, tmp_path / "out")

    assert report["status"] == "ABSTAIN_NEUTRAL_CORRESPONDENCE_NOT_DELIVERY"
    rejected = report["abstentions"]["rejected_selected_pieces"]
    target = next(item for item in rejected if item["view_id"] == "view_05")
    assert "reflection_forbidden" in target["reasons"]
    assert "non_positive_determinant" in target["reasons"]
    assert report["claims"]["delivery"] is False


def test_module_has_no_named_side_polarity_literals() -> None:
    source = MODULE.read_text(encoding="utf-8").lower()
    assert "left_side" not in source
    assert "right_side" not in source
    assert "physical_side_a" in source
    assert "physical_side_b" in source


def test_artifacts_are_visible_and_rebuild_is_deterministic(tmp_path: Path) -> None:
    first = build(JOB, tmp_path / "first")
    second = build(JOB, tmp_path / "second")
    assert first["proof_sha256"] == second["proof_sha256"]
    for name in (
        "NEUTRAL_SIDE_CORRESPONDENCE_REPORT.json",
        "NEUTRAL_SIDE_CORRESPONDENCE_AUDIT.json",
        "NEUTRAL_SIDE_COVERAGE_RESIDUAL_LEDGER.json",
        "NEUTRAL_SIDE_DIRECT_MATCHES.csv",
        "RUN117_NEUTRAL_SIDE_CONTACT.png",
        "PHYSICAL_SIDE_A_UV_SUPPORT.png",
        "PHYSICAL_SIDE_B_UV_SUPPORT.png",
    ):
        assert (tmp_path / "first" / name).stat().st_size > 0
    with Image.open(tmp_path / "first/RUN117_NEUTRAL_SIDE_CONTACT.png") as contact:
        assert contact.size == (2200, 1700)
    assert first["claims"]["surface_ownership"] is False
    assert first["claims"]["global_projector"] is False
    assert first["claims"]["livery"] is False
    assert first["claims"]["psd"] is False
    assert first["claims"]["delivery"] is False

