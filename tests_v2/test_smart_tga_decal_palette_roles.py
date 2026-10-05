from __future__ import annotations

import numpy as np

from engine.spec_sculpt.decal_palette_roles import derive_palette_role_masks


def test_palette_roles_isolate_white_ink_from_red_parent_panel():
    image = np.full((80, 180, 3), (225, 20, 30), np.uint8)
    image[20:60, 35:145] = (245, 245, 245)
    parent = np.ones((80, 180), bool)
    roles = {item.role: item for item in derive_palette_role_masks(image, parent)}
    assert "light_ink" in roles
    light = roles["light_ink"]
    assert light.local_mask[30, 80]
    assert not light.local_mask[5, 5]
    assert light.local_mask.flags.writeable is False
    assert 0.20 < light.parent_fraction < 0.60


def test_uniform_white_foreground_preserves_whole_parent_as_light_role():
    image = np.full((40, 100, 3), (245, 245, 245), np.uint8)
    parent = np.zeros((40, 100), bool)
    parent[5:35, 10:90] = True
    roles = {item.role: item for item in derive_palette_role_masks(image, parent)}
    assert np.array_equal(roles["light_ink"].local_mask, parent)
