from pathlib import Path

import numpy as np
from PIL import Image

import _forge_semantic_staging as staging


def _save(path: Path, rgba: np.ndarray) -> str:
    Image.fromarray(rgba, "RGBA").save(path)
    return staging._sha256(path)


def _asset(path: Path, usable: bool = True) -> dict:
    with Image.open(path) as opened:
        size = list(opened.size)
    return {
        "id": "source-01",
        "path": str(path),
        "sha256": staging._sha256(path),
        "size": size,
        "usable_for_projection": usable,
        "source_crop_path": str(path),
        "source_crop_sha256": staging._sha256(path),
        "source_bbox_pixels": [0, 0, size[0], size[1]],
        "reference_thumbnail_evidence": "synthetic" if not usable else None,
    }


def _fields(role=None, group=None) -> dict:
    values = {field: None for field in staging.FIELDS}
    values["role"] = role
    values["psd_group"] = group
    return {field: {"value": value, "confidence": 0.9 if value else 0.0, "support": 1.0, "runner_up_support": 0.0, "abstention": None if value else "not proven"} for field, value in values.items()}


def test_stage_pack_uses_verified_split_and_recomposes_exactly(tmp_path: Path) -> None:
    source = np.zeros((50, 80, 4), dtype=np.uint8)
    source[5:45, 5:75] = (22, 90, 50, 255)
    source[15:30, 25:55] = (245, 245, 245, 255)
    isolated = np.zeros_like(source)
    isolated[15:30, 25:55] = source[15:30, 25:55]
    remainder = source.copy()
    remainder[15:30, 25:55] = 0
    source_path, isolated_path, remainder_path = tmp_path / "source.png", tmp_path / "isolated.png", tmp_path / "remainder.png"
    _save(source_path, source)
    _save(isolated_path, isolated)
    _save(remainder_path, remainder)
    asset_pack = {"name": "demo", "assets": [_asset(source_path)]}
    match_pack = {"matches": []}
    split_semantic = {field: {"value": None, "support": 1, "abstention": "not proven"} for field in staging.FIELDS}
    split_semantic["role"] = {"value": "decal", "support": 1, "abstention": None}
    split_semantic["psd_group"] = {"value": "40 SPONSORS & BRAND MARKS", "support": 1, "abstention": None}
    split_pack = {
        "targets": [
            {
                "asset_id": "source-01",
                "accepted_split_count": 1,
                "remainder": {"path": str(remainder_path)},
                "splits": [
                    {
                        "id": "source-01-isolated-01",
                        "path": str(isolated_path),
                        "mask_path": str(isolated_path),
                        "mask_sha256": staging._sha256(isolated_path),
                        "semantic": split_semantic,
                        "localization": {"inlier_ratio": 0.88},
                        "primary_exemplar": {"id": "example"},
                    }
                ],
            }
        ]
    }
    pack = staging.stage_pack(asset_pack, match_pack, split_pack)
    assert pack["staged_layer_count"] == 2
    assert pack["isolated_object_count"] == 1
    assert pack["evidence_routed_layer_count"] == 1
    assert pack["unresolved_layer_count"] == 1
    assert pack["source_recomposition_failure_count"] == 0
    assert pack["sources"][0]["recomposition"]["exact"]


def test_whole_match_routes_only_supported_psd_group(tmp_path: Path) -> None:
    rgba = np.zeros((20, 30, 4), dtype=np.uint8)
    rgba[3:17, 4:26] = (255, 240, 20, 255)
    path = tmp_path / "whole.png"
    _save(path, rgba)
    asset_pack = {"name": "demo", "assets": [_asset(path)]}
    match_pack = {"matches": [{"asset_id": "source-01", "fields": _fields("number", "30 NUMBERS"), "top1_confidence": 0.91, "top1_margin": 0.4, "target_ocr": ["11"]}]}
    pack = staging.stage_pack(asset_pack, match_pack, {"targets": []})
    assert pack["layers"][0]["routing"]["psd_group"] == "30 NUMBERS"
    assert pack["layers"][0]["routing"]["status"] == "evidence_supported"
    assert pack["source_recomposition_failure_count"] == 0


def test_missing_semantics_stays_editable_but_unresolved(tmp_path: Path) -> None:
    rgba = np.zeros((18, 24, 4), dtype=np.uint8)
    rgba[2:16, 2:22] = (180, 20, 30, 255)
    path = tmp_path / "unknown.png"
    _save(path, rgba)
    pack = staging.stage_pack({"name": "demo", "assets": [_asset(path)]}, {"matches": []}, {"targets": []})
    assert pack["staged_layer_count"] == 1
    assert pack["layers"][0]["routing"]["psd_group"] == staging.UNRESOLVED_GROUP
    assert pack["layers"][0]["semantic"]["role"]["value"] is None


def test_nonprojectable_component_is_quarantined(tmp_path: Path) -> None:
    rgba = np.zeros((16, 16, 4), dtype=np.uint8)
    rgba[1:15, 1:15] = (90, 90, 90, 255)
    path = tmp_path / "quarantine.png"
    _save(path, rgba)
    pack = staging.stage_pack({"name": "demo", "assets": [_asset(path, usable=False)]}, {"matches": []}, {"targets": []})
    assert pack["quarantine_layer_count"] == 1
    assert pack["layers"][0]["routing"]["psd_group"] == staging.QUARANTINE_GROUP
    assert pack["source_recomposition_failure_count"] == 0
