from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_official_uv_landmark_atlas import FALSE_CLAIMS, SCHEMA, sha256_file, validate_atlas


def _manifest() -> dict:
    return {
        "$schema": SCHEMA,
        "canvas": [16, 16],
        "claims": {
            "sparse_official_uv_landmark_atlas_recorded": True,
            **{claim: False for claim in FALSE_CLAIMS},
        },
        "landmarks": [
            {
                "id": "official_uv.left_side.rear_arch_top",
                "type": "wheel_arch_extremum",
                "physical_surface": "left_side",
                "xy": [5, 6],
                "wire_distance_px": 2.0,
                "provenance": {
                    "bbox_inference": False,
                    "mirrored": False,
                    "left_right_independent": True,
                },
                "evidence": {},
            }
        ],
        "abstentions": [
            {
                "id": "front_pair_unknown",
                "type": "side_fender_seam_endpoint",
                "no_coordinate": True,
                "reason": "no direct paired seam evidence",
            }
        ],
    }


def _masks() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    official = np.zeros((16, 16), dtype=bool)
    official[2:14, 2:14] = True
    left = np.zeros_like(official)
    left[4:10, 4:10] = True
    return official, {"left_side": left}


def test_valid_sparse_atlas_passes() -> None:
    official, surfaces = _masks()
    assert validate_atlas(_manifest(), official, surfaces) == []


def test_duplicate_landmark_id_fails() -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    manifest["landmarks"].append(copy.deepcopy(manifest["landmarks"][0]))
    assert any("duplicate landmark id" in error for error in validate_atlas(manifest, official, surfaces))


def test_outside_canvas_fails() -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    manifest["landmarks"][0]["xy"] = [16, 4]
    assert any("outside canvas" in error for error in validate_atlas(manifest, official, surfaces))


def test_official_topology_and_surface_are_independent_gates() -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    manifest["landmarks"][0]["xy"] = [12, 12]
    errors = validate_atlas(manifest, official, surfaces)
    assert any("outside declared surface mask" in error for error in errors)
    manifest["landmarks"][0]["xy"] = [0, 0]
    errors = validate_atlas(manifest, official, surfaces)
    assert any("outside official topology" in error for error in errors)


def test_mirroring_and_bbox_inference_are_rejected() -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    manifest["landmarks"][0]["provenance"]["mirrored"] = True
    manifest["landmarks"][0]["provenance"]["bbox_inference"] = True
    errors = validate_atlas(manifest, official, surfaces)
    assert any("mirrored must be false" in error for error in errors)
    assert any("bbox inference must be false" in error for error in errors)


def test_left_right_independence_is_required() -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    manifest["landmarks"][0]["provenance"]["left_right_independent"] = False
    assert any("left/right independence" in error for error in validate_atlas(manifest, official, surfaces))


def test_dense_and_delivery_claims_cannot_be_promoted() -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    manifest["claims"]["dense_uv_correspondence_proved"] = True
    manifest["claims"]["delivery_ready"] = True
    errors = validate_atlas(manifest, official, surfaces)
    assert any("dense_uv_correspondence_proved" in error for error in errors)
    assert any("delivery_ready" in error for error in errors)


def test_evidence_hash_is_verified(tmp_path: Path) -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    crop = tmp_path / "evidence.png"
    Image.new("RGB", (8, 8), "red").save(crop)
    manifest["landmarks"][0]["evidence"] = {
        "crop_path": crop.name,
        "crop_sha256": sha256_file(crop),
    }
    assert validate_atlas(
        manifest,
        official,
        surfaces,
        evidence_root=tmp_path,
        verify_evidence_hashes=True,
    ) == []
    crop.write_bytes(b"tampered")
    assert any(
        "evidence crop hash mismatch" in error
        for error in validate_atlas(
            manifest,
            official,
            surfaces,
            evidence_root=tmp_path,
            verify_evidence_hashes=True,
        )
    )


def test_abstention_requires_reason_and_no_coordinate() -> None:
    official, surfaces = _masks()
    manifest = _manifest()
    manifest["abstentions"][0]["reason"] = ""
    manifest["abstentions"][0]["no_coordinate"] = False
    errors = validate_atlas(manifest, official, surfaces)
    assert any("missing reason" in error for error in errors)
    assert any("must explicitly have no coordinate" in error for error in errors)
