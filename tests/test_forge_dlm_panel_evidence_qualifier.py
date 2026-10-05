import copy
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from _forge_dlm_panel_evidence_qualifier import (
    MANIFEST_SCHEMA,
    PLACEMENT_CROP_SCHEMA,
    REFERENCE_SCHEMA,
    REQUIRED_POLICY_CLASSES,
    evaluate_manifest,
    write_report,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_MANIFEST = (
    ROOT
    / "_forge_data"
    / "dlm_panel_evidence_qualifier"
    / "run123_core4_reference_evidence_v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_image(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (64, 32), color).save(path)


def _policies() -> list[dict]:
    return copy.deepcopy(json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))["projection_policies"])


def _synthetic_manifest(tmp_path: Path) -> Path:
    roles = [
        ("side_a", "left_profile", "direct_physical_view"),
        ("side_b", "right_profile", "direct_physical_view"),
        ("top", "top_view", "direct_physical_view"),
        ("front", "front_view", "direct_physical_view"),
        ("rear", "rear_view", "direct_physical_view"),
        ("semantic", "number_sheet", "semantic_asset_sheet"),
        ("placement", "left_profile", "composite_multiview_sheet"),
    ]
    sources = []
    shas = {}
    for index, (source_id, primary, scope) in enumerate(roles):
        image_path = tmp_path / f"{source_id}.png"
        _make_image(image_path, (20 + index * 20, 40, 80))
        digest = _sha(image_path)
        shas[source_id] = digest
        sources.append(
            {
                "filename": image_path.name,
                "sha256": digest,
                "width": 64,
                "height": 32,
                "primary_evidence": primary,
                "evidence_scope": scope,
            }
        )
    inventory = {
        "$schema": REFERENCE_SCHEMA,
        "source_root": tmp_path.as_posix(),
        "sources": sources,
    }
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    crop_job = {
        "$schema": PLACEMENT_CROP_SCHEMA,
        "source": (tmp_path / "placement.png").as_posix(),
        "panels": [
            {"id": "left", "bbox": [0, 0, 20, 20]},
            {"id": "right", "bbox": [30, 0, 50, 20]},
        ],
    }
    crop_path = tmp_path / "crops.json"
    crop_path.write_text(json.dumps(crop_job), encoding="utf-8")
    pack = {
        "pack_id": "synthetic_pack",
        "display_name": "Synthetic",
        "reference_inventory": {"path": inventory_path.name, "sha256": _sha(inventory_path)},
        "side_bindings": [
            {"physical_side": "physical_side_a", "source_sha256": shas["side_a"], "allow_mirror": False},
            {"physical_side": "physical_side_b", "source_sha256": shas["side_b"], "allow_mirror": False},
        ],
        "isolated_panel_sources": [
            {
                "source_sha256": shas[source_id],
                "sheet_role": f"{source_id}_mixed_sheet",
                "source_purity": "mixed_assembled_and_isolated_panels",
                "whole_source_delivery_pixels_allowed": False,
                "segmentation_required": True,
                "allow_mirror": False,
                "expected_panel_roles": [source_id],
            }
            for source_id in ("top", "front", "rear")
        ],
        "physical_art_ownership": [
            {
                "physical_art_id": "front_partition",
                "surfaces": ["hood", "nose", "left_front_fender", "right_front_fender"],
                "max_instances": 1,
                "duplicate_forbidden": True,
                "allow_mirror": False,
                "split_across_surfaces": True,
                "single_source_partition_required": True,
            }
        ],
        "required_constraints": [],
        "placement_crop_manifest": {"path": crop_path.name, "sha256": _sha(crop_path)},
        "placement_crop_policy": {
            "mode": "strict_nonoverlap",
            "max_smaller_crop_fraction": 0.0,
            "delivery_pixels_allowed": False,
        },
        "legacy_segmented_assets": [],
    }
    manifest = {"$schema": MANIFEST_SCHEMA, "projection_policies": _policies(), "packs": [pack]}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


@pytest.fixture(scope="module")
def real_report() -> dict:
    return evaluate_manifest(REAL_MANIFEST)


def test_real_core4_manifest_passes_fail_closed(real_report: dict) -> None:
    assert real_report["status"] == "PASS_REFERENCE_EVIDENCE_FIREWALL_NOT_DELIVERY"
    assert real_report["counts"]["pack_count"] == 4
    assert real_report["counts"]["source_count"] == 41
    assert real_report["counts"]["whole_vehicle_evidence_only_count"] == 20
    assert real_report["counts"]["whole_source_delivery_eligible_count"] == 0
    assert real_report["counts"]["legacy_segmented_delivery_eligible_count"] == 0
    assert real_report["counts"]["quarantined_inventory_source_count"] == 1


def test_real_pack_inventory_has_direct_panels_and_unique_waffle_front(real_report: dict) -> None:
    assert real_report["counts"]["expected_isolated_panel_role_count"] == 55
    assert real_report["counts"]["placement_crop_count"] == 45
    waffle = real_report["pack_reports"][0]
    constraint = waffle["required_constraints"][0]
    assert constraint["physical_art_id"] == "front_continuous_treatment"
    assert constraint["max_instances"] == 1
    assert constraint["duplicate_nose_object_forbidden"] is True
    front = next(
        item for item in waffle["physical_art_ownership"]
        if item["physical_art_id"] == "front_continuous_treatment"
    )
    assert front["surfaces"] == ["hood", "nose", "left_front_fender", "right_front_fender"]
    assert front["single_source_partition_required"] is True


def test_projection_policy_covers_all_surface_classes(real_report: dict) -> None:
    classes = {item["surface_class"] for item in real_report["projection_policies"]}
    assert classes == REQUIRED_POLICY_CLASSES
    assert all(item["allow_mirror"] is False for item in real_report["projection_policies"])
    assert all(item["independent_physical_holdout_required"] is True for item in real_report["projection_policies"])
    assert all(item["self_roundtrip_may_promote"] is False for item in real_report["projection_policies"])


def test_mixed_sheet_cannot_be_declared_delivery_source(tmp_path: Path) -> None:
    manifest_path = _synthetic_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["packs"][0]["isolated_panel_sources"][0]["whole_source_delivery_pixels_allowed"] = True
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_manifest(manifest_path)
    assert report["status"] == "REJECT_REFERENCE_EVIDENCE_MANIFEST"
    assert any("mixed_sheet_must_be_evidence_only" in item for item in report["contradictions"])


def test_side_mirroring_is_rejected(tmp_path: Path) -> None:
    manifest_path = _synthetic_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["packs"][0]["side_bindings"][1]["allow_mirror"] = True
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_manifest(manifest_path)
    assert report["status"] == "REJECT_REFERENCE_EVIDENCE_MANIFEST"
    assert any("mirroring_forbidden" in item for item in report["contradictions"])


def test_stale_inventory_binding_rejects(tmp_path: Path) -> None:
    manifest_path = _synthetic_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["packs"][0]["reference_inventory"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_manifest(manifest_path)
    assert report["status"] == "REJECT_REFERENCE_EVIDENCE_MANIFEST"
    assert any("sha256_mismatch" in item for item in report["contradictions"])


def test_out_of_bounds_placement_crop_rejects_even_when_rehashed(tmp_path: Path) -> None:
    manifest_path = _synthetic_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    crop_path = tmp_path / "crops.json"
    crops = json.loads(crop_path.read_text(encoding="utf-8"))
    crops["panels"][0]["bbox"] = [0, 0, 65, 32]
    crop_path.write_text(json.dumps(crops), encoding="utf-8")
    payload["packs"][0]["placement_crop_manifest"]["sha256"] = _sha(crop_path)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_manifest(manifest_path)
    assert report["status"] == "REJECT_REFERENCE_EVIDENCE_MANIFEST"
    assert any("bbox_out_of_bounds" in item for item in report["contradictions"])


def test_unproved_segmented_asset_cannot_deliver(tmp_path: Path) -> None:
    manifest_path = _synthetic_manifest(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset = tmp_path / "legacy.png"
    _make_image(asset, (100, 120, 140))
    payload["packs"][0]["legacy_segmented_assets"] = [
        {
            "role": "hood",
            "path": asset.name,
            "sha256": _sha(asset),
            "size": [64, 32],
            "segmentation_proof": False,
            "delivery_pixels_allowed": True,
        }
    ]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_manifest(manifest_path)
    assert report["status"] == "REJECT_REFERENCE_EVIDENCE_MANIFEST"
    assert any("unproved_segmentation_cannot_deliver" in item for item in report["contradictions"])


def test_contact_and_reports_are_written(tmp_path: Path, real_report: dict) -> None:
    outputs = write_report(real_report, tmp_path / "out")
    assert outputs["json"].is_file()
    assert outputs["md"].is_file()
    assert outputs["contact"].is_file()
    with Image.open(outputs["contact"]) as image:
        assert image.width == 1920
        assert image.height > 1000
