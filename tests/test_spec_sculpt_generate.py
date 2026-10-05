"""Spec Sculpt fusion and paint-link helpers."""

import numpy as np
import pytest

from engine.spec_sculpt.generate import (
    FUSION_STRATEGY_GLOSS_WIN,
    FUSION_STRATEGY_LINEAR,
    fuse_registry_and_scratch_specs,
)


def test_fuse_linear_metallic_avg():
    cat = np.zeros((2, 2, 4), dtype=np.float32)
    scr = np.zeros((2, 2, 4), dtype=np.float32)
    cat[:, :, 0] = 200.0
    scr[:, :, 0] = 100.0
    out = fuse_registry_and_scratch_specs(
        cat, scr, 0.5, 0.5, 0.5, strategy=FUSION_STRATEGY_LINEAR
    )
    assert out.shape == (2, 2, 4)
    assert abs(float(out[0, 0, 0]) - 150.0) < 0.01


def test_fuse_gloss_win_takes_shinier_branch():
    cat = np.zeros((2, 2, 4), dtype=np.float32)
    scr = np.zeros((2, 2, 4), dtype=np.float32)
    cat[:, :, 0] = 200.0
    scr[:, :, 0] = 100.0
    out = fuse_registry_and_scratch_specs(
        cat, scr, 0.5, 0.5, 0.5, strategy=FUSION_STRATEGY_GLOSS_WIN
    )
    # max(200*0.5, 100*0.5) = 100
    assert abs(float(out[0, 0, 0]) - 100.0) < 0.01


def test_fuse_roughness_always_linear():
    cat = np.zeros((2, 2, 4), dtype=np.float32)
    scr = np.zeros((2, 2, 4), dtype=np.float32)
    cat[:, :, 1] = 80.0
    scr[:, :, 1] = 120.0
    out = fuse_registry_and_scratch_specs(
        cat, scr, 0.5, 0.5, 0.5, strategy=FUSION_STRATEGY_GLOSS_WIN
    )
    assert abs(float(out[0, 0, 1]) - 100.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
