from __future__ import annotations

import numpy as np

from engine.spec_sculpt.number_context_relative_pixels import (
    FEATURE_NAMES, relative_pixel_feature_cube,
)


def test_relative_pixel_features_are_finite_d4_and_owner_neutral() -> None:
    rgb = np.zeros((14, 16, 3), np.uint8)
    rgb[3:11, 4:13] = (210, 50, 170)
    shape = (8, 9)
    raw = np.zeros(shape, bool)
    raw[2:7, 2:7] = True
    hypotheses = {
        "raw_instance_union": raw,
        "seed_palette": np.ones(shape, bool),
        "border_contrast": np.eye(*shape, dtype=bool),
        "hybrid_evidence": raw.copy(),
        "seeded_graphcut": np.ones(shape, bool),
    }
    cube = relative_pixel_feature_cube(rgb, [4, 3, 9, 8], hypotheses)
    assert cube.shape == (8, 9, 32)
    assert len(FEATURE_NAMES) == 32
    assert np.all(np.isfinite(cube))
    assert not any("filename" in name or "owner" in name or "car" in name for name in FEATURE_NAMES)
    # D4 edge features are invariant under horizontal reflection.
    assert np.allclose(cube[:, :, 15], np.fliplr(cube[:, :, 15]))
    assert np.allclose(cube[:, :, 16], np.fliplr(cube[:, :, 16]))

