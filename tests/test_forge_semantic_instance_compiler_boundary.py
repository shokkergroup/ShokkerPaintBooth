from __future__ import annotations

import json
from pathlib import Path

from _forge_semantic_instance_compiler_boundary import (
    REQUIRED_CLAIMS,
    create_compiler_job,
    create_synthetic_semantic_case,
    evaluate_compiler_boundary,
)


def _case(tmp_path: Path, mode: str, lineage_mode: str = "valid") -> dict:
    semantic, lineage = create_synthetic_semantic_case(tmp_path / "inputs", mode)
    selected = lineage
    if lineage_mode == "missing":
        selected = None
    elif lineage_mode == "mismatch":
        selected = json.loads(json.dumps(lineage))
        selected["masters"][0]["physical_instances"][0]["master_sha256"] = "0" * 64
    job = create_compiler_job(tmp_path / "compiler_job.json", semantic, selected)
    return evaluate_compiler_boundary(job, tmp_path / "output")


def test_disjoint_master_split_across_adjacent_surfaces_passes(tmp_path: Path) -> None:
    result = _case(tmp_path / "valid", "valid_split")
    assert result["status"] == "PASS"
    assert result["compiler_boundary_ready"] is True
    assert result["semantic_instance_ready"] is True
    assert result["lineage_blockers"] == []
    instance = result["semantic_gate_report"]["instances"][0]
    assert instance["metrics"]["object_overlap_pixels"] == 0
    assert instance["metrics"]["object_missing_pixels"] == 0
    assert instance["checks"]["surface_adjacency"] is True


def test_complete_master_repeated_on_each_surface_rejects(tmp_path: Path) -> None:
    result = _case(tmp_path / "whole", "duplicate_whole")
    assert result["status"] == "REJECT"
    assert result["compiler_boundary_ready"] is False
    instance = result["semantic_gate_report"]["instances"][0]
    assert instance["metrics"]["object_overlap_pixels"] == 960
    assert "instance:hero_object_0:object_overlap" in result["blockers"]


def test_second_whole_physical_object_violates_exact_count_policy(tmp_path: Path) -> None:
    result = _case(tmp_path / "second", "duplicate_second")
    assert result["status"] == "REJECT"
    assert "master:hero_master:physical_cardinality" in result["blockers"]
    assert "master:hero_master:physical_instance_count" in result["lineage_blockers"]


def test_missing_lineage_abstains_instead_of_guessing(tmp_path: Path) -> None:
    result = _case(tmp_path / "missing", "valid_split", "missing")
    assert result["status"] == "ABSTAIN"
    assert result["semantic_instance_ready"] is True
    assert result["lineage_blockers"] == ["lineage_required"]


def test_mismatched_master_sha_rejects(tmp_path: Path) -> None:
    result = _case(tmp_path / "sha", "valid_split", "mismatch")
    assert result["status"] == "REJECT"
    assert "instance:hero_object_0:master_sha_mismatch" in result["lineage_blockers"]


def test_downstream_claims_remain_false() -> None:
    assert REQUIRED_CLAIMS == {
        "semantic_compiler_boundary_only": True,
        "livery_ready": False,
        "psd_ready": False,
        "app_ready": False,
        "delivery_ready": False,
    }


def test_reusable_compiler_boundary_contains_no_livery_identity_literals() -> None:
    source = (Path(__file__).resolve().parents[1] / "_forge_semantic_instance_compiler_boundary.py").read_text(
        encoding="utf-8"
    ).lower()
    for identity in ("waffle", "dominos", "crystal_lake", "sex_wax"):
        assert identity not in source
