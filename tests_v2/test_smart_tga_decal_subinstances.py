from __future__ import annotations

import numpy as np

from engine.spec_sculpt.decal_subinstances import derive_intrinsic_subinstances


def test_intrinsic_subinstances_separate_interior_wordmark_from_backing_panel():
    image = np.full((90, 220, 3), (220, 18, 30), np.uint8)
    parent = np.ones((90, 220), bool)
    image[:, :8] = 245
    image[28:62, 35:60] = 245
    image[28:62, 75:100] = 245
    image[28:62, 115:140] = 245
    image[28:62, 155:180] = 245
    items = derive_intrinsic_subinstances(image, parent)
    interior = [item for item in items if item.hypothesis == "light_ink:interior_union"]
    assert interior
    mask = interior[0].local_mask
    assert mask[40, 45] and mask[40, 165]
    assert not mask[40, 2]
    assert mask.flags.writeable is False
    assert np.all(mask <= parent)


def test_uniform_parent_does_not_manufacture_foreground_subinstance():
    image = np.full((50, 100, 3), 245, np.uint8)
    parent = np.ones((50, 100), bool)
    assert derive_intrinsic_subinstances(image, parent) == ()
