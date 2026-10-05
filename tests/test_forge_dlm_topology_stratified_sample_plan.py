from __future__ import annotations

import json
from pathlib import Path

import pytest

from _forge_dlm_topology_stratified_sample_plan import (
    TopologySamplePlanError,
    build,
)

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data/dlm_topology_stratified_sample_plan/run135_job.json"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build(JOB, tmp_path_factory.mktemp("run135"))


def test_exact_run121_container_census_is_reproduced(built):
    metrics = built["report"]["container_metrics"]
    assert metrics["retained_container_count"] == 4719
    assert metrics["region_pixels"] == 2_658_729
    assert metrics["coverage_pixel_sha256"] == "1dc3ea77cdc8486f3d6ab2c3a1295299408a88061c0b95632680b0ed23a5e81f"


def test_old_uniform_decode_sample_is_objectively_too_sparse(built):
    current = built["report"]["current_run133_sample_coverage"]
    assert current["sample_count"] == 1024
    assert current["represented_container_count"] == 634
    assert current["containers_meeting_minimum_count"] == 14
    assert current["outside_container_sample_count"] == 0


def test_plan_covers_every_diagnostic_container_with_six_unique_points(built):
    plan = built["plan"]
    assert plan["container_count"] == 4719
    assert plan["sample_count"] == 28_314
    assert plan["unique_sample_count"] == 28_314
    assert plan["inside_bound_container_sample_count"] == 28_314
    assert all(row["sample_count"] == 6 for row in plan["containers"])
    planned = built["report"]["planned_sample_coverage"]
    assert planned["represented_container_count"] == 4719
    assert planned["containers_meeting_minimum_count"] == 4719


def test_rank1_slivers_are_explicit_fusion_or_abstention_obligations(built):
    plan = built["plan"]
    assert plan["two_dimensional_container_count"] == 4476
    assert plan["rank1_container_count"] == 243
    assert len(plan["rank1_requires_parent_surface_fusion_ids"]) == 243
    assert plan["claims"]["complete_2d_jacobian_plan"] is False
    assert plan["minimum_maximum_triangle_area2_px"] == pytest.approx(6.0)


def test_global_sign_mixture_is_exposed_not_misreported_as_one_view_failure(built):
    global_row = built["synthetic"]["global_whole_view_analysis"]
    assert global_row["accepted"] is False
    assert global_row["dominant_orientation_fraction"] == pytest.approx(0.5)
    assert "VIEW_CHIRALITY_FOLDOVER_OR_MIXED_ORIENTATION" in global_row["reasons"]


def test_oppositely_stored_containers_pass_only_after_stratification(built):
    correct = built["synthetic"]["correct_container_witnesses"]
    assert correct["accepted"] is True
    assert correct["accepted_container_count"] == 2
    signs = {row["container_id"]: row["dominant_orientation_sign"] for row in correct["container_results"]}
    assert signs == {1: "positive", 2: "negative"}


def test_swapped_and_missing_container_witnesses_reject(built):
    assert built["synthetic"]["swapped_container_witnesses"]["accepted"] is False
    assert built["synthetic"]["missing_container_witnesses"]["accepted"] is False
    swapped_reasons = {reason for row in built["synthetic"]["swapped_container_witnesses"]["container_results"] for reason in row["reasons"]}
    missing_reasons = {reason for row in built["synthetic"]["missing_container_witnesses"]["container_results"] for reason in row["reasons"]}
    assert "VIEW_CHIRALITY_UNEXPECTED_REFLECTION" in swapped_reasons
    assert "VIEW_CHIRALITY_INDEPENDENT_SIGN_WITNESS_REQUIRED" in missing_reasons


def test_witness_template_covers_all_roles_without_invented_landmarks(built):
    template = built["witness_template"]
    assert len(template["role_templates"]) == 10
    assert all(row["container_witnesses"] == [] for row in template["role_templates"])
    assert template["claims"]["completed_witnesses"] is False


def test_live_core4_remains_fail_closed(built):
    report = built["report"]
    assert report["live_counts"] == {
        "run134_decoded_role_count": 0,
        "run134_global_chirality_accepted_role_count": 0,
        "container_witness_count": 0,
        "topology_stratified_role_count": 0,
    }
    assert all(row["psd_allowed"] is False for row in report["core4_release_status"])
    for key in ("physical_uv_islands", "physical_surface_ownership", "physical_side_polarity", "readable_direction", "projector", "psd", "delivery", "app", "fidelity_95"):
        assert report["claims"][key] is False


def test_plan_generation_is_deterministic(built, tmp_path):
    repeat = build(JOB, tmp_path / "repeat")
    assert repeat["plan"]["report_content_sha256"] == built["plan"]["report_content_sha256"]
    assert repeat["report"]["container_metrics"]["container_label_pixel_sha256"] == built["report"]["container_metrics"]["container_label_pixel_sha256"]


def test_hash_bound_run134_source_rejects_tamper(tmp_path):
    job = json.loads(JOB.read_text(encoding="utf-8"))
    job["sources"]["run134_report"]["sha256"] = "0" * 64
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(TopologySamplePlanError, match="run134_report_sha256_mismatch"):
        build(bad, tmp_path / "bad_out")


def test_reusable_module_has_no_livery_identity_branches():
    source = (ROOT / "_forge_dlm_topology_stratified_sample_plan.py").read_text(encoding="utf-8").lower()
    forbidden = ("waffle", "domino", "crystal", "jason", "wax", "miller", "dew", "spider")
    assert not any(token in source for token in forbidden)