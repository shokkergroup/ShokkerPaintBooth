import numpy as np

from engine.spec_sculpt.number_object_transfer import VIEW_SIZE, isolated_object_views
from scripts.smart_tga_number_object_foundation_fusion_probe import _proposal_identity


def test_views_discard_position_and_emit_appearance_plus_silhouette_d4():
    rgb_a = np.zeros((80, 100, 3), np.uint8)
    rgb_b = np.zeros_like(rgb_a)
    mask_a = np.zeros((80, 100), bool)
    mask_b = np.zeros_like(mask_a)
    mask_a[8:28, 10:30] = True
    mask_b[48:68, 60:80] = True
    rgb_a[mask_a] = (240, 30, 80)
    rgb_b[mask_b] = (240, 30, 80)
    views_a = isolated_object_views(rgb_a, mask_a)
    views_b = isolated_object_views(rgb_b, mask_b)
    assert views_a.shape == (16, 3, VIEW_SIZE, VIEW_SIZE)
    assert np.allclose(views_a, views_b)
    assert views_a.min() == 0.0 and views_a.max() == 1.0


def test_empty_mask_is_rejected():
    import pytest
    with pytest.raises(ValueError, match="empty"):
        isolated_object_views(np.zeros((8, 8, 3), np.uint8), np.zeros((8, 8), bool))


def test_proposal_identity_keeps_reused_owner_indexes_distinct():
    number = _proposal_identity("paint.tga", "numbers", 0)
    sponsor = _proposal_identity("paint.tga", "sponsors", 0)
    assert number != sponsor
    assert _proposal_identity("paint.tga", None, 0) == number
