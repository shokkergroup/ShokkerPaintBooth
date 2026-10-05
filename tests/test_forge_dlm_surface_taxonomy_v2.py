from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from _forge_dlm_surface_taxonomy_v2 import REQUIRED_CLAIMS, run_migration, validate_manifest


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_out/codex_full_uv_recovery/run_111_surface_taxonomy_v2/surface_taxonomy_v2_migration_job.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _surface(manifest: dict, surface_id: str) -> dict:
    return next(row for row in manifest["surfaces"] if row["surface_id"] == surface_id)


def test_taxonomy_v2_has_exactly_thirteen_unique_canonical_surfaces(tmp_path: Path) -> None:
    manifest, validation = run_migration(JOB, tmp_path / "output")
    ids = manifest["canonical_surface_ids"]
    assert validation["status"] == "PASS"
    assert manifest["canonical_surface_count"] == 13
    assert len(ids) == len(set(ids)) == 13
    assert "hood_nose" not in ids
    assert ids[:2] == ["hood", "nose"]
    assert {"hood", "nose", "left_front_fender", "right_front_fender", "left_side", "right_side", "rear_deck_lid", "roof", "spoiler_inside", "spoiler_outside", "spoiler_left_endplate", "spoiler_right_endplate", "tub"} == set(ids)


def test_split_children_never_inherit_false_readiness(tmp_path: Path) -> None:
    manifest, _ = run_migration(JOB, tmp_path / "output")
    for child_id in ("hood", "nose"):
        child = _surface(manifest, child_id)
        assert child["migration_mode"] == "split_child"
        assert child["legacy_source_ids"] == ["hood_nose"]
        assert child["status"] == "ABSTAIN"
        assert child["ready"] is False
        assert child["readiness_inheritance"]["allowed"] is False
        assert child["readiness_inheritance"]["inherited_ready"] is False
        assert child["readiness_inheritance"]["inherited_passed_check_ids"] == []
        assert len(child["exact_evidence_still_lacking"]) >= 6
        assert len(child["child_specific_evidence"]["exact_additional_capture_required"]) >= 3
    assert manifest["readiness"]["split_child_ready_count"] == 0
    assert manifest["readiness"]["taxonomy_runtime_ready"] is False


def test_native_parent_landmarks_partition_disjointly(tmp_path: Path) -> None:
    manifest, _ = run_migration(JOB, tmp_path / "output")
    hood = set(_surface(manifest, "hood")["child_specific_evidence"]["official_native_landmark_ids"])
    nose = set(_surface(manifest, "nose")["child_specific_evidence"]["official_native_landmark_ids"])
    assert len(hood) == 6
    assert len(nose) == 6
    assert hood.isdisjoint(nose)
    assert all(".hood_" in item for item in hood)
    assert all(".nose_" in item for item in nose)


def test_all_other_surfaces_preserve_run107_evidence_and_status(tmp_path: Path) -> None:
    manifest, _ = run_migration(JOB, tmp_path / "output")
    identity = [row for row in manifest["surfaces"] if row["migration_mode"] == "identity_preserved"]
    assert len(identity) == 11
    for row in identity:
        legacy = row["legacy_evidence"]["run107"]
        assert row["status"] == legacy["status"]
        assert row["ready"] == legacy["ready"]
        assert row["preservation"]["run107_record_sha256"] == legacy["record_sha256"]
        assert all(row["preservation"][key] is True for key in ("run107_status_preserved", "run107_ready_preserved", "run107_passed_check_count_preserved", "run107_required_check_count_preserved"))


def test_alias_contract_has_no_collision_and_parent_is_not_runtime_alias(tmp_path: Path) -> None:
    manifest, validation = run_migration(JOB, tmp_path / "output")
    assert manifest["runtime_aliases"] == []
    split = next(row for row in manifest["legacy_migrations"] if row["legacy_surface_id"] == "hood_nose")
    assert split["targets"] == ["hood", "nose"]
    assert split["runtime_alias_created"] is False
    assert split["singular_runtime_resolution"] == "ABSTAIN_AMBIGUOUS_LEGACY_PARENT"
    assert next(row for row in validation["checks"] if row["check_id"] == "runtime_aliases_have_no_collision")["pass"] is True


def test_hood_nose_adjacency_and_one_object_law_are_bound(tmp_path: Path) -> None:
    manifest, _ = run_migration(JOB, tmp_path / "output")
    edge = manifest["adjacency_edges_added_by_migration"]
    assert len(edge) == 1
    assert {edge[0]["surface_a"], edge[0]["surface_b"]} == {"hood", "nose"}
    assert edge[0]["direction"] == "UNDIRECTED"
    policy = manifest["front_object_fragmentation_policy"]
    assert policy["physical_object_count_mode"] == "exact"
    assert policy["physical_object_count"] == 1
    assert policy["master_may_split_across_adjacent_children"] is True
    assert policy["whole_master_repetition_per_child"] == "FORBIDDEN"
    assert policy["fragment_union"] == "EXACT"
    assert policy["fragment_overlap_pixels"] == 0
    assert policy["source_law"]["valid_disjoint_split_status"] == "PASS"
    assert policy["source_law"]["whole_master_repetition_status"] == "REJECT"
    assert policy["source_law"]["second_physical_object_status"] == "REJECT"


def test_validator_rejects_alias_collision_false_readiness_and_duplicate_front(tmp_path: Path) -> None:
    manifest, _ = run_migration(JOB, tmp_path / "output")
    alias_bad = copy.deepcopy(manifest)
    alias_bad["runtime_aliases"] = [{"alias": "hood", "target": "nose"}]
    assert validate_manifest(alias_bad)["status"] == "REJECT"
    readiness_bad = copy.deepcopy(manifest)
    _surface(readiness_bad, "hood")["ready"] = True
    assert validate_manifest(readiness_bad)["status"] == "REJECT"
    duplicate_bad = copy.deepcopy(manifest)
    duplicate_bad["front_object_fragmentation_policy"]["whole_master_repetition_per_child"] = "ALLOWED"
    assert validate_manifest(duplicate_bad)["status"] == "REJECT"


def test_visible_contact_and_all_recorded_hashes_are_exact(tmp_path: Path) -> None:
    manifest, validation = run_migration(JOB, tmp_path / "output")
    contact = Path(validation["contact"]["path"])
    manifest_path = Path(validation["manifest"]["path"])
    assert contact.is_file() and contact.stat().st_size > 50_000
    assert _sha(contact) == validation["contact"]["sha256"]
    assert _sha(manifest_path) == validation["manifest"]["sha256"]
    for record in manifest["sources"].values():
        path = Path(record["path"])
        assert path.is_file()
        assert _sha(path) == record["sha256"]


def test_claims_and_source_remain_livery_neutral(tmp_path: Path) -> None:
    manifest, _ = run_migration(JOB, tmp_path / "output")
    assert manifest["claims"] == REQUIRED_CLAIMS
    assert all(manifest["claims"][key] is False for key in ("existing_adapter_modified", "legacy_maturity_ledger_modified", "livery_ready", "psd_ready", "app_ready", "delivery_ready"))
    source = (ROOT / "_forge_dlm_surface_taxonomy_v2.py").read_text(encoding="utf-8").lower()
    for identity in ("waffle", "domino", "crystal_lake", "sex_wax", "miller", "mountain_dew", "spider"):
        assert identity not in source
