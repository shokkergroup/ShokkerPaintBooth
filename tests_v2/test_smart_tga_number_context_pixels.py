from __future__ import annotations

import numpy as np

from engine.spec_sculpt.number_context_pixels import FEATURE_NAMES, pixel_feature_cube


def test_pixel_features_are_intrinsic_finite_and_owner_neutral() -> None:
    rgb = np.zeros((12, 14, 3), np.uint8)
    rgb[3:9, 4:11] = (230, 70, 35)
    shape = (6, 7)
    hypotheses = {
        "raw_instance_union": np.eye(*shape, dtype=bool),
        "seed_palette": np.ones(shape, bool),
        "border_contrast": np.zeros(shape, bool),
        "hybrid_evidence": np.zeros(shape, bool),
        "seeded_graphcut": np.ones(shape, bool),
    }
    cube = pixel_feature_cube(rgb, [4, 3, 7, 6], hypotheses)
    assert cube.shape == (6, 7, 20)
    assert len(FEATURE_NAMES) == 20
    assert np.all(np.isfinite(cube))
    assert not any("filename" in name or "owner" in name or "car" in name for name in FEATURE_NAMES)

