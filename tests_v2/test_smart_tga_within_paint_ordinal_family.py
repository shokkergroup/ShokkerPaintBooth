import cv2
import numpy as np

from scripts.smart_tga_clip_full_bank_embed import _bank_rows
from scripts.smart_tga_within_paint_ordinal_family import (
    FEATURE_NAMES,
    _cohort_statistics,
    _fine_shape_features,
    _mask_anatomy,
    _top_two,
)


def test_full_bank_rows_preserve_bank_order_without_semantic_authority():
    bank = {
        "records": [
            {
                "paint": "paint-a",
                "candidates": [
                    {
                        "proposal_id": "p0",
                        "dominant_number_block": "upper",
                        "palette_role": "light_ink",
                    },
                    {
                        "proposal_id": "p1",
                        "dominant_number_block": "deck",
                        "palette_role": "dark_ink",
                    },
                ],
            }
        ]
    }
    rows = _bank_rows(bank)
    assert [(row["candidate_index"], row["proposal_id"]) for row in rows] == [
        (0, "p0"), (1, "p1"),
    ]
    assert all("semantic" not in row and "bbox" not in row for row in rows)


def test_multiscale_anatomy_is_d4_invariant():
    mask = np.zeros((29, 41), dtype=np.uint8)
    mask[3:25, 5:10] = 1
    mask[19:25, 5:35] = 1
    mask[8:13, 24:35] = 1
    expected = _mask_anatomy(mask)
    for variant in (
        np.rot90(mask, 1), np.rot90(mask, 2), np.rot90(mask, 3),
        np.fliplr(mask), np.flipud(mask),
    ):
        np.testing.assert_allclose(_mask_anatomy(variant), expected, atol=2e-3, rtol=2e-3)


def test_multiscale_anatomy_handles_tiny_exact_masks():
    mask = np.zeros((3, 7), dtype=np.uint8)
    mask[1, 1:6] = 1
    values = _mask_anatomy(mask)
    assert np.all(np.isfinite(values))


def test_fine_shape_correspondence_is_d4_invariant_and_discriminative():
    anchor = np.zeros((64, 64), dtype=np.uint8)
    anchor[10:54, 12:18] = 1
    anchor[46:54, 12:50] = 1
    same = np.rot90(anchor)
    different = np.zeros_like(anchor)
    cv2.circle(different, (32, 32), 17, 1, thickness=5)
    matched = _fine_shape_features(anchor, same)
    mismatch = _fine_shape_features(anchor, different)
    assert matched.mean() > 0.99
    assert matched.mean() > mismatch.mean() + 0.20


def test_cohort_statistics_rank_only_inside_supplied_cohort():
    percentile, robust_z = _cohort_statistics(np.asarray([0.5, 0.9, 0.7], dtype=np.float32))
    np.testing.assert_allclose(percentile, [0.0, 1.0, 0.5])
    assert robust_z[1] > robust_z[2] > robust_z[0]


def test_top_two_adjudication_is_per_paint_block():
    score = np.asarray([0.9, 0.8, 0.7, 0.95, 0.1])
    keys = np.asarray(["a|upper", "a|upper", "a|upper", "a|deck", "a|deck"])
    accepted = _top_two(score, np.ones(5, dtype=bool), keys)
    assert accepted.tolist() == [True, True, False, True, True]


def test_model_features_exclude_identity_and_bbox_authority():
    joined = " ".join(FEATURE_NAMES).lower()
    assert "paint" not in joined
    assert "filename" not in joined
    assert "bbox" not in joined
    assert "candidate_index" not in joined
