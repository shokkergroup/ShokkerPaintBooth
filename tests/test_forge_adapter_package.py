from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def test_promoted_dlm_adapter_masks_are_hash_bound_and_exclusive() -> None:
    root = Path(__file__).resolve().parents[1] / "_dlm_dossier" / "template_adapter_v1"
    adapter = json.loads((root / "adapter.json").read_text(encoding="utf-8"))
    assert adapter["package_version"] == "10"
    assert adapter["exclusive_ownership"]["overlap_pixels_before"] == 35080
    assert adapter["exclusive_ownership"]["overlap_pixels_after"] == 0
    masks = []
    for surface in adapter["surfaces"].values():
        if not surface.get("paintable"):
            continue
        path = root / surface["mask_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == surface["mask_sha256"]
        mask = np.asarray(Image.open(path).convert("L")) > 0
        assert mask.shape == (2048, 2048)
        assert int(mask.sum()) == surface["mask_pixels"]
        assert surface["ownership_contract"] == "exclusive_nearest_unique_core/v1"
        masks.append(mask)
    stack = np.stack(masks, axis=0)
    assert int(np.count_nonzero(stack.sum(axis=0) > 1)) == 0
    assert {
        name: (adapter["surfaces"][name]["projector"], adapter["surfaces"][name]["source_anchor"])
        for name in ("hood", "roof", "rear_deck_lid")
    } == {
        "hood": ("direct_top_quad", "hood_quad"),
        "roof": ("direct_top_quad", "roof_quad"),
        "rear_deck_lid": ("direct_top_quad", "rear_deck_quad"),
    }
    assert all(adapter["surfaces"][name]["inverse_ready"] for name in ("hood", "roof", "rear_deck_lid"))
    outside = adapter["surfaces"]["spoiler_outside"]
    assert (outside["projector"], outside["source_anchor"], outside["required_anchors"]) == (
        "direct_quad",
        "spoiler_outside_quad",
        ["spoiler_outside_quad"],
    )
    assert outside["inverse_ready"] is True
    assert adapter["surfaces"]["spoiler_inside"]["required_anchors"] == ["spoiler_inside_quad"]
    assert adapter["surfaces"]["spoiler_inside"]["inverse_ready"] is False
    nose = adapter["surfaces"]["nose"]
    assert nose["inverse_ready"] is False
    valance = nose["qualified_subprojectors"]["front_valance"]
    assert valance["projector"] == "front_valance_scanline"
    assert valance["qualified_scope"] == "front_valance_only"
    assert valance["full_surface_inverse_ready"] is False
    assert valance["coverage_contract"] == "partial_surface/v1"
    assert valance["satisfies_full_surface"] is False
    assert valance["remaining_scope"] == "upper_nose_and_both_front_corner_transitions"
    assert valance["reflection_allowed"] is False
    assert "isolated_hood_artwork" in valance["source_support_excludes"]
    evidence = adapter["optional_evidence_roles"]
    assert set(evidence) == {"front_corner_left", "front_corner_right", "rear_inside"}
    assert evidence["front_corner_left"]["surface"] == "nose"
    assert evidence["front_corner_right"]["surface"] == "nose"
    assert evidence["rear_inside"]["surface"] == "spoiler_inside"
    assert all(role["minimum_confidence"] == 0.85 for role in evidence.values())
    assert all(role["slot_confidence"] == 0.65 for role in evidence.values())
    assert all(role["confirmed_confidence"] == 0.9 for role in evidence.values())
    assert all(role["requires_user_attestation"] is True for role in evidence.values())
    assert all(role["prohibited_substitute_roles"] for role in evidence.values())
    assert {role["review_contract"]["anchor_field"] for role in evidence.values()} == {
        "front_corner_left_quad", "front_corner_right_quad", "spoiler_inside_quad"
    }
    assert all(role["review_contract"]["point_order"] == "screen_tl_tr_br_bl" for role in evidence.values())
    assert all(role["review_contract"]["seed_is_authority"] is False for role in evidence.values())
    assert all(role["capture_quality_contract"]["$schema"] == "shokk-forge.surface-capture-quality-contract/v1" for role in evidence.values())
    assert all(role["capture_quality_contract"]["minimum_short_edge"] == 360 for role in evidence.values())
    assert all(role["capture_quality_contract"]["review_minimum_quad_pixels"] == 12000 for role in evidence.values())
