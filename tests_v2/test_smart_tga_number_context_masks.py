import numpy as np

from engine.spec_sculpt.number_context_masks import number_context_mask_hypotheses


def test_context_mask_hypotheses_preserve_competing_zero_authority_masks():
    rgb = np.full((32, 32, 3), 100, dtype=np.uint8)
    rgb[4:10, 4:10] = (220, 20, 20)
    rgb[16:26, 16:26] = (220, 20, 20)
    seed_mask = np.ones((6, 6), bool)
    instance_mask = np.ones((5, 5), bool)
    result = number_context_mask_hypotheses(
        rgb,
        {"proposal_id": "ncp:test", "seed_instance_id": "di:seed", "bbox": [12, 12, 16, 16]},
        {"instance_id": "di:seed", "bbox": [4, 4, 6, 6], "local_mask": seed_mask},
        [{"instance_id": "di:member", "bbox": [18, 18, 5, 5], "local_mask": instance_mask}],
    )
    assert set(result["masks"]) == {
        "raw_instance_union", "seed_palette", "border_contrast",
        "hybrid_evidence", "seeded_graphcut",
    }
    assert result["raw_member_instance_ids"] == ["di:member"]
    assert np.count_nonzero(result["masks"]["raw_instance_union"]) == 25
    assert all(mask.shape == (16, 16) and not mask.flags.writeable for mask in result["masks"].values())
    assert result["casts_votes"] is False
    assert result["ownership_authority"] is False
    assert result["adds_pixels"] is False
