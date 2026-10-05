import cv2
import numpy as np

from engine.spec_sculpt.number_tiled_palette_proposals import (
    assemble_adjacent_tiled_palette_companions,
    corroborate_tiled_number_families,
    multiscale_tiled_palette_proposals,
    position_ranked_tiled_shortlist,
    repeated_tiled_palette_shortlist,
)


def test_tiled_palette_proposals_are_probability_independent_and_immutable():
    image = np.zeros((256, 256, 3), np.uint8)
    cv2.putText(image, "64", (20, 92), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (30, 240, 80), 8)
    cv2.putText(image, "64", (140, 220), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (30, 240, 80), 8)
    proposals = multiscale_tiled_palette_proposals(
        image, tile_sizes=(128,), overlap_fraction=0.5, min_pixels=8,
    )
    assert proposals
    assert all(item["owner_neutral"] for item in proposals)
    assert all(not item["ownership_authority"] for item in proposals)
    assert all(item["provenance"]["probability_independent"] for item in proposals)
    assert all(not item["raw_support"].flags.writeable for item in proposals)

    shortlist = repeated_tiled_palette_shortlist(
        image, proposals, maximum=12, maximum_inputs=64,
    )
    assert 0 < len(shortlist) <= 12
    assert all(
        item["provenance"]["relationship_is_corroborative_only"]
        for item in shortlist
    )
    panel_map = {
        "space": "256x256",
        "number_blocks": [{"name": "number", "bbox": [0, 0, 256, 256]}],
        "sponsor_blocks": [],
        "mandatory_template_blocks": [],
    }
    ranked = position_ranked_tiled_shortlist(
        shortlist, image.shape[:2], panel_map, maximum=6,
    )
    assert len(ranked) == 6
    assert all(item["provenance"]["position_is_corroborative_only"] for item in ranked)


def test_adjacent_palette_companions_preserve_members_without_authority():
    first_mask = np.ones((30, 20), bool)
    second_mask = np.ones((32, 22), bool)
    first_mask.setflags(write=False)
    second_mask.setflags(write=False)
    common = {
        "owner_neutral": True,
        "ownership_authority": False,
    }
    proposals = ({
        **common,
        "proposal_id": "first",
        "proposal_bbox": [10, 20, 20, 30],
        "raw_support": first_mask,
        "provenance": {
            "palette_role": "chromatic_ink", "component_count": 1,
            "tile_origin_count": 2, "peer_d4_similarity": 0.9,
            "peer_count_at_0_82": 2,
        },
    }, {
        **common,
        "proposal_id": "second",
        "proposal_bbox": [34, 19, 22, 32],
        "raw_support": second_mask,
        "provenance": {
            "palette_role": "chromatic_ink", "component_count": 1,
            "tile_origin_count": 2, "peer_d4_similarity": 0.88,
            "peer_count_at_0_82": 2,
        },
    })
    assembled = assemble_adjacent_tiled_palette_companions(proposals)
    assert len(assembled) == 1
    candidate = assembled[0]
    assert candidate["proposal_bbox"] == [10, 19, 46, 32]
    assert candidate["raw_support"].sum() == first_mask.sum() + second_mask.sum()
    assert not candidate["raw_support"].flags.writeable
    assert not candidate["ownership_authority"]
    assert candidate["provenance"]["assembly_creates_no_ownership"]
    assert candidate["provenance"]["member_proposal_ids"] == ["first", "second"]


def test_cross_block_family_evidence_is_corroborative_only():
    image = np.zeros((128, 128, 3), np.uint8)
    mask = np.zeros((24, 18), bool)
    mask[2:22, 3:7] = True
    mask[16:22, 3:15] = True
    image[10:34, 10:28][mask] = (220, 40, 30)
    image[82:106, 82:100][np.rot90(mask, 2)] = (220, 40, 30)
    first = _candidate = {
        "proposal_id": "upper",
        "proposal_bbox": [10, 10, 18, 24],
        "raw_support": mask,
        "owner_neutral": True,
        "ownership_authority": False,
        "provenance": {"palette_role": "chromatic_ink"},
    }
    rotated = np.rot90(mask, 2).copy()
    rotated.setflags(write=False)
    second = {
        **first,
        "proposal_id": "lower",
        "proposal_bbox": [82, 82, 18, 24],
        "raw_support": rotated,
    }
    mask.setflags(write=False)
    panel_map = {
        "number_blocks": [
            {"name": "upper", "bbox": [0, 0, 64, 64]},
            {"name": "lower", "bbox": [64, 64, 64, 64]},
        ]
    }
    enriched = corroborate_tiled_number_families(image, (first, second), panel_map)
    assert enriched[0]["provenance"]["cross_block_best_d4_similarity"] > 0.99
    assert enriched[0]["provenance"]["cross_block_distinct_peer_blocks"] == 1
    assert enriched[0]["provenance"]["family_relationship_creates_no_ownership"]
    assert not enriched[0]["ownership_authority"]
