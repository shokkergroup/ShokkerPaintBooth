from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

from forge_service.evidence import sha256_file
from forge_service.surface_executor import execute_ready_surfaces


def _case(tmp_path: Path) -> dict:
    root = tmp_path / uuid.uuid4().hex
    job = root / "job"
    package = root / "adapter"
    (job / "sources").mkdir(parents=True)
    (package / "masks").mkdir(parents=True)

    source = np.full((120, 240, 3), 246, dtype=np.uint8)
    source[22:104, 18:222] = (34, 146, 211)
    source[38:86, 70:190] = (238, 84, 31)
    yy, xx = np.ogrid[:120, :240]
    for cx in (76, 176):
        source[(xx - cx) ** 2 + (yy - 88) ** 2 < 17 ** 2] = 12
    source_path = job / "sources" / "left.png"
    Image.fromarray(source, "RGB").save(source_path)

    mask = np.zeros((128, 128), dtype=np.uint8)
    mask[18:70, 14:118] = 255
    mask_path = package / "masks" / "left_strip.png"
    Image.fromarray(mask, "L").save(mask_path)
    adapter_path = package / "adapter.json"
    adapter_path.write_text("{}\n", encoding="utf-8")
    surface = {
        "family": "side",
        "side": "left",
        "paintable": True,
        "projector": "wheelbase_profile",
        "inverse_ready": True,
        "upright_rotation_deg": 0,
        "bbox": [14, 18, 118, 70],
        "car_space_extent": {"x_min": -0.7, "x_max": 1.7, "y_bottom": -0.15, "y_top": 0.95},
        "mask_path": "masks/left_strip.png",
        "mask_sha256": sha256_file(mask_path),
    }
    adapter = {"canvas": [128, 128], "surfaces": {"left_strip": surface}}
    inputs = [
        {
            "id": "left-direct",
            "role": "left",
            "stored_path": "sources/left.png",
            "sha256": sha256_file(source_path),
            "duplicate_of": None,
        }
    ]
    proposals = {
        "roles": {
            "left": {
                "primary_object_bbox": [0.05, 0.12, 0.95, 0.93],
                "diagnostics": {
                    "measured_wheels": {
                        "front_wheel_center": {"radius_pixels": 17.0},
                        "rear_wheel_center": {"radius_pixels": 17.0},
                    }
                },
            }
        }
    }
    anchors = {
        "left": {
            "front_wheel_center": [176 / 240, 88 / 120],
            "rear_wheel_center": [76 / 240, 88 / 120],
            "body_top_y": 0.20,
            "rocker_y": 0.88,
        }
    }
    plans = [
        {
            "surface": "left_strip",
            "family": "side",
            "role": "left",
            "projector": "wheelbase_profile",
            "status": "ready",
        }
    ]
    return {
        "job": job,
        "adapter_path": adapter_path,
        "adapter": adapter,
        "inputs": inputs,
        "proposals": proposals,
        "anchors": anchors,
        "plans": plans,
        "mask_path": mask_path,
    }


def _top_case(tmp_path: Path) -> dict:
    root = tmp_path / uuid.uuid4().hex
    job = root / "job"
    package = root / "adapter"
    (job / "sources").mkdir(parents=True)
    (package / "masks").mkdir(parents=True)

    source = np.full((180, 260, 3), 246, dtype=np.uint8)
    quad = np.asarray([[39, 32], [213, 39], [202, 136], [49, 143]], dtype=np.int32)
    cv_mask = np.zeros((180, 260), dtype=np.uint8)
    import cv2

    cv2.fillConvexPoly(cv_mask, quad, 1)
    source[cv_mask > 0] = (218, 41, 52)
    source[62:112, 88:164] = (239, 239, 230)
    source_path = job / "sources" / "top.png"
    Image.fromarray(source, "RGB").save(source_path)

    mask = np.zeros((128, 128), dtype=np.uint8)
    mask[18:116, 20:96] = 255
    mask_path = package / "masks" / "hood.png"
    Image.fromarray(mask, "L").save(mask_path)
    adapter_path = package / "adapter.json"
    adapter_path.write_text("{}\n", encoding="utf-8")
    surface = {
        "family": "top",
        "side": "center",
        "paintable": True,
        "projector": "direct_top_quad",
        "source_anchor": "hood_quad",
        "inverse_ready": True,
        "upright_rotation_deg": 90,
        "bbox": [20, 18, 96, 116],
        "mask_path": "masks/hood.png",
        "mask_sha256": sha256_file(mask_path),
    }
    return {
        "job": job,
        "adapter_path": adapter_path,
        "adapter": {"canvas": [128, 128], "surfaces": {"hood": surface}},
        "inputs": [{"id": "top-direct", "role": "top", "stored_path": "sources/top.png", "sha256": sha256_file(source_path), "duplicate_of": None}],
        "proposals": {"roles": {"top": {"primary_object_bbox": [0.1, 0.1, 0.9, 0.9], "fields": {"hood_quad": {"provenance": "direct_isolated_panel_component+sheet_layout/v1"}}}}},
        "anchors": {"top": {"hood_quad": [[39 / 260, 32 / 180], [213 / 260, 39 / 180], [202 / 260, 136 / 180], [49 / 260, 143 / 180]]}},
        "plans": [{"surface": "hood", "family": "top", "role": "top", "projector": "direct_top_quad", "source_anchor": "hood_quad", "status": "ready"}],
        "mask_path": mask_path,
    }


def test_executor_emits_hash_bound_contained_editable_surface(tmp_path: Path) -> None:
    case = _case(tmp_path)
    result = execute_ready_surfaces(
        job_dir=case["job"],
        adapter_path=case["adapter_path"],
        adapter=case["adapter"],
        inputs=case["inputs"],
        proposals=case["proposals"],
        resolved_anchors=case["anchors"],
        plans=case["plans"],
        authority="a" * 64,
    )

    assert result["valid"] is True
    assert result["summary"]["executed_surface_count"] == 1
    assert result["summary"]["cross_surface_overlap_pixels"] == 0
    assert result["summary"]["duplicate_physical_instances"] is False
    record = result["records"][0]
    assert record["status"] == "complete"
    assert record["containment"] == 1.0
    assert record["owned_uv_pixels"] > 250
    assert record["owned_mask_coverage"] > 0.05
    assert record["reflection_used"] is False

    layer_path = case["job"] / record["layer_path"]
    assert record["layer_sha256"] == sha256_file(layer_path)
    rgba = np.asarray(Image.open(layer_path).convert("RGBA"))
    mask = np.asarray(Image.open(case["mask_path"]).convert("L")) > 0
    assert rgba.shape == (128, 128, 4)
    assert np.count_nonzero(rgba[:, :, 3] & (~mask).astype(np.uint8)) == 0
    assert np.count_nonzero(rgba[:, :, 3]) == record["owned_uv_pixels"]


def test_executor_abstains_when_adapter_mask_authority_changes(tmp_path: Path) -> None:
    case = _case(tmp_path)
    Image.new("L", (128, 128), 255).save(case["mask_path"])

    result = execute_ready_surfaces(
        job_dir=case["job"],
        adapter_path=case["adapter_path"],
        adapter=case["adapter"],
        inputs=case["inputs"],
        proposals=case["proposals"],
        resolved_anchors=case["anchors"],
        plans=case["plans"],
        authority=hashlib.sha256(b"tampered").hexdigest(),
    )

    assert result["valid"] is False
    assert result["summary"]["executed_surface_count"] == 0
    assert result["summary"]["abstained_execution_count"] == 1
    assert "hash does not match authority" in result["records"][0]["reason"]


def test_executor_maps_direct_top_quad_without_reflection(tmp_path: Path) -> None:
    case = _top_case(tmp_path)
    result = execute_ready_surfaces(
        job_dir=case["job"],
        adapter_path=case["adapter_path"],
        adapter=case["adapter"],
        inputs=case["inputs"],
        proposals=case["proposals"],
        resolved_anchors=case["anchors"],
        plans=case["plans"],
        authority="b" * 64,
    )

    assert result["valid"] is True
    record = result["records"][0]
    assert record["projector"] == "direct_top_quad"
    assert record["source_anchor"] == "hood_quad"
    assert record["stored_rotation_deg"] == 90
    assert record["source_domain"] == "direct_top_orthographic_panel_quad"
    assert record["source_support"]["support_mode"] == "isolated_largest_component"
    assert record["containment"] == 1.0
    assert record["owned_mask_coverage"] > 0.95
    assert record["reflection_used"] is False


def test_executor_abstains_when_top_corner_order_would_reflect(tmp_path: Path) -> None:
    case = _top_case(tmp_path)
    case["anchors"]["top"]["hood_quad"] = list(reversed(case["anchors"]["top"]["hood_quad"]))
    result = execute_ready_surfaces(
        job_dir=case["job"],
        adapter_path=case["adapter_path"],
        adapter=case["adapter"],
        inputs=case["inputs"],
        proposals=case["proposals"],
        resolved_anchors=case["anchors"],
        plans=case["plans"],
        authority="c" * 64,
    )

    assert result["valid"] is False
    assert "reflect readable artwork" in result["records"][0]["reason"]


def test_executor_maps_isolated_spoiler_face_without_inside_face_evidence(tmp_path: Path) -> None:
    case = _top_case(tmp_path)
    hood = case["adapter"]["surfaces"].pop("hood")
    spoiler = {
        **hood,
        "family": "rear_aero",
        "side": "outside",
        "projector": "direct_quad",
        "source_anchor": "spoiler_outside_quad",
        "source_domain": "direct_isolated_spoiler_face_or_confirmed_rear_quad",
        "upright_rotation_deg": 0,
    }
    case["adapter"]["surfaces"] = {"spoiler_outside": spoiler}
    case["inputs"][0]["role"] = "rear"
    quad = case["anchors"].pop("top")["hood_quad"]
    case["anchors"] = {"rear": {"spoiler_outside_quad": quad}}
    case["proposals"] = {
        "roles": {
            "rear": {
                "fields": {
                    "spoiler_outside_quad": {
                        "provenance": "direct_isolated_spoiler_face_component/v1"
                    }
                }
            }
        }
    }
    case["plans"] = [
        {
            "surface": "spoiler_outside",
            "family": "rear_aero",
            "role": "rear",
            "projector": "direct_quad",
            "source_anchor": "spoiler_outside_quad",
            "status": "ready",
        }
    ]
    result = execute_ready_surfaces(
        job_dir=case["job"],
        adapter_path=case["adapter_path"],
        adapter=case["adapter"],
        inputs=case["inputs"],
        proposals=case["proposals"],
        resolved_anchors=case["anchors"],
        plans=case["plans"],
        authority="d" * 64,
    )

    assert result["valid"] is True
    record = result["records"][0]
    assert record["projector"] == "direct_quad"
    assert record["source_anchor"] == "spoiler_outside_quad"
    assert record["stored_rotation_deg"] == 0
    assert record["source_domain"] == "direct_isolated_spoiler_face_or_confirmed_rear_quad"
    assert record["source_support"]["support_mode"] == "isolated_panel_quad_interior"
    assert record["containment"] == 1.0
    assert record["reflection_used"] is False


def test_executor_maps_only_isolated_front_valance_and_excludes_mandatory(tmp_path: Path) -> None:
    root = tmp_path / uuid.uuid4().hex
    job = root / "job"
    package = root / "adapter"
    (job / "sources").mkdir(parents=True)
    (package / "masks").mkdir(parents=True)

    source = np.full((120, 240, 3), 246, dtype=np.uint8)
    source[18:72, 48:192] = (220, 35, 45)  # unrelated isolated hood artwork
    source[94:108, 20:220] = (30, 120, 215)  # qualified valance only
    source_path = job / "sources" / "front.png"
    Image.fromarray(source, "RGB").save(source_path)

    mask = np.zeros((128, 128), dtype=np.uint8)
    mask[10:118, 70:120] = 255
    mask_path = package / "masks" / "nose.png"
    Image.fromarray(mask, "L").save(mask_path)
    mandatory = np.zeros((64, 64, 4), dtype=np.uint8)
    mandatory[5:59, 58:60, 3] = 255
    mandatory_path = package / "mandatory.png"
    Image.fromarray(mandatory, "RGBA").save(mandatory_path)
    adapter_path = package / "adapter.json"
    adapter_path.write_text("{}\n", encoding="utf-8")

    base_surface = {
        "family": "front",
        "side": "center",
        "paintable": True,
        "projector": "front_car_space",
        "upright_rotation_deg": 90,
        "inverse_ready": False,
        "bbox": [70, 10, 120, 118],
        "mask_path": "masks/nose.png",
        "mask_sha256": sha256_file(mask_path),
    }
    qualified = {
        "projector": "front_valance_scanline",
        "inverse_ready": True,
        "source_anchor": "front_valance_quad",
        "required_anchors": ["center_x", "half_width", "ground_y", "valance_top_y", "front_valance_quad"],
        "surface_v_range": [0.0, 0.4],
        "qualified_scope": "front_valance_only",
        "coverage_contract": "partial_surface/v1",
        "satisfies_full_surface": False,
        "remaining_scope": "upper_nose_and_both_front_corner_transitions",
        "source_domain": "direct_isolated_front_valance_component",
        "source_support_excludes": ["assembled_front_car", "isolated_hood_artwork"],
    }
    adapter = {
        "canvas": [128, 128],
        "guides": {"mandatory": {"source_path": str(mandatory_path), "source_sha256": sha256_file(mandatory_path)}},
        "surfaces": {"nose": base_surface},
    }
    inputs = [{
        "id": "front-direct",
        "role": "front",
        "stored_path": "sources/front.png",
        "sha256": sha256_file(source_path),
        "duplicate_of": None,
    }]
    anchors = {"front": {
        "center_x": 0.5,
        "half_width": 0.35,
        "ground_y": 0.9,
        "valance_top_y": 0.83,
        "front_valance_quad": [[20 / 240, 94 / 120], [220 / 240, 94 / 120], [220 / 240, 108 / 120], [20 / 240, 108 / 120]],
    }}
    plans = [{
        "surface": "nose",
        "family": "front",
        "role": "front",
        "projector": "front_valance_scanline",
        "source_anchor": "front_valance_quad",
        "qualified_projector_config": qualified,
        "status": "ready",
    }]
    proposals = {"roles": {"front": {"fields": {"front_valance_quad": {"provenance": "direct_isolated_front_valance_component/v1"}}}}}
    result = execute_ready_surfaces(
        job_dir=job,
        adapter_path=adapter_path,
        adapter=adapter,
        inputs=inputs,
        proposals=proposals,
        resolved_anchors=anchors,
        plans=plans,
        authority="e" * 64,
    )

    assert result["valid"] is True
    record = result["records"][0]
    assert record["projector"] == "front_valance_scanline"
    assert record["qualified_scope"] == "front_valance_only"
    assert record["full_surface_inverse_ready"] is False
    assert record["surface_completion"] == "partial"
    assert record["satisfies_full_surface"] is False
    assert record["completed_scope"] == "front_valance_only"
    assert record["remaining_scope"] == "upper_nose_and_both_front_corner_transitions"
    assert result["summary"]["partial_surface_count"] == 1
    assert result["summary"]["fully_complete_surface_count"] == 0
    assert result["summary"]["partial_uv_pixels"] == record["owned_uv_pixels"]
    assert record["mandatory_contamination_after_exclusion"] == 0
    assert record["reflection_used"] is False
    assert "isolated_hood_artwork" in record["source_support"]["source_support_excludes"]
    layer = np.asarray(Image.open(job / record["layer_path"]).convert("RGBA"), dtype=np.uint8)
    painted = layer[:, :, 3] > 0
    assert painted.any()
    assert int(layer[painted, 2].mean()) > int(layer[painted, 0].mean()) * 2
