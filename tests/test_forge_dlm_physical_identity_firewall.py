import json
from pathlib import Path

import pytest

from _forge_dlm_physical_identity_firewall import PhysicalIdentityError, audit_physical_identity, require_physical_identity
from _forge_dlm_surface_local_manifest_compose import SurfaceLocalComposeError, build


ROOT = Path(__file__).resolve().parents[1]


def _row(surface: str, geometry: str, seed: str = "a") -> dict:
    return {
        "surface_id": surface,
        "geometry_id": geometry,
        "render_validated": True,
        "physical_readable_direction_validated": True,
        "physical_identity": {
            "role": surface,
            "authority": "owner_matched_wire_iracing",
            "evidence_sha256": [seed * 64, ("b" if seed != "b" else "c") * 64],
        },
    }


def test_direct_hash_bound_distinct_geometry_is_accepted():
    registry = {"surface_projectors": [_row("hood", "geom_014"), _row("driver_tub", "geom_015", "c")]}
    report = require_physical_identity(registry, {"hood", "driver_tub"})
    assert report["accepted"] is True
    assert report["accepted_surfaces"] == ["driver_tub", "hood"]


def test_geometry_validity_cannot_substitute_for_physical_identity():
    registry = {"valid": True, "surface_projectors": [{"surface_id": "hood", "geometry_id": "geom_014"}]}
    report = audit_physical_identity(registry, {"hood"})
    assert report["accepted"] is False
    assert "hood:missing_physical_identity" in report["issues"]


def test_unvalidated_alias_and_duplicate_geometry_fail_closed():
    first = _row("hood", "geom_shared")
    second = _row("driver_tub", "geom_shared", "c")
    second["physical_identity"]["role"] = "hood"
    with pytest.raises(PhysicalIdentityError) as caught:
        require_physical_identity({"surface_projectors": [first, second]}, {"hood", "driver_tub"})
    assert "physical_role_mismatch" in str(caught.value)
    assert "duplicate_permanent_geometry_id" in str(caught.value)


@pytest.mark.parametrize("manifest_name", ["waffle_top_rear_v1.json", "dominos_top_rear_v1.json", "crystal_lake_top_rear_v1.json", "sex_wax_top_rear_v1.json"])
def test_revoked_run187_top_registry_cannot_compile_semantic_art(manifest_name, tmp_path):
    manifest = ROOT / "_forge_data" / "dlm_surface_local_liveries" / manifest_name
    with pytest.raises(SurfaceLocalComposeError, match="physical_identity_firewall"):
        build(manifest, tmp_path / manifest.stem)


@pytest.mark.parametrize("manifest_name", ["waffle_front_v1.json", "dominos_front_v1.json", "crystal_lake_front_v1.json", "sex_wax_front_v1.json"])
def test_legacy_run179_front_manifest_cannot_bypass_proof(manifest_name, tmp_path):
    manifest = ROOT / "_forge_data" / "dlm_surface_local_liveries" / manifest_name
    with pytest.raises(SurfaceLocalComposeError, match="legacy_v1_manifest_evidence_only"):
        build(manifest, tmp_path / manifest.stem)
