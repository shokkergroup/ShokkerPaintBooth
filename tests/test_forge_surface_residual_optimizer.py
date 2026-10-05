from __future__ import annotations

import numpy as np

from _forge_surface_residual_optimizer import (
    backproject_residual,
    backproject_roundtrip_residual,
    residual_grid,
)


def test_identity_backprojection_recovers_supported_rgb_residual() -> None:
    reference = np.full((9, 11, 3), 120, dtype=np.uint8)
    rendered = np.full((9, 11, 3), 80, dtype=np.uint8)
    support = np.ones((9, 11), dtype=bool)
    correction, confidence = backproject_residual(reference, rendered, support, np.eye(3), (11, 9))
    assert np.allclose(correction, 40.0)
    assert np.allclose(confidence, 1.0)


def test_backprojection_never_claims_unsupported_pixels() -> None:
    reference = np.full((7, 7, 3), 200, dtype=np.uint8)
    rendered = np.zeros_like(reference)
    support = np.zeros((7, 7), dtype=bool); support[2:5, 2:5] = True
    correction, confidence = backproject_residual(reference, rendered, support, np.eye(3), (7, 7))
    assert np.count_nonzero(confidence) == 9
    assert not correction[0, 0].any()


def test_residual_grid_labels_interior_photometric_error() -> None:
    reference = np.full((24, 32, 3), (80, 120, 160), dtype=np.uint8)
    rendered = np.full_like(reference, (70, 105, 145))
    rows = residual_grid(reference, rendered, np.ones((24, 32), dtype=bool), rows=2, cols=2)
    assert len(rows) == 4
    assert all(row["diagnosis"] == "interior photometric/resampling" for row in rows)
    assert all(row["mean_lab_delta_8bit"] > 0 for row in rows)


def test_roundtrip_identity_backprojection_recovers_camera_residual() -> None:
    reference = np.full((6, 8, 3), 145, dtype=np.uint8)
    rendered = np.full_like(reference, 95)
    correction, confidence = backproject_roundtrip_residual(
        reference, rendered, np.ones((6, 8), dtype=bool), np.eye(3), (8, 6),
        (0, 0), (8, 6), {"rotate": 0}, [0, 0, 8, 6], (8, 6),
    )
    assert np.allclose(correction, 50.0)
    assert np.allclose(confidence, 1.0)


def test_roundtrip_backprojection_replays_compiler_quarter_turn() -> None:
    values = np.arange(6, dtype=np.uint8).reshape(2, 3) * 20 + 20
    reference = np.repeat(values[:, :, None], 3, axis=2)
    correction, confidence = backproject_roundtrip_residual(
        reference, np.zeros_like(reference), np.ones((2, 3), dtype=bool), np.eye(3), (3, 2),
        (0, 0), (3, 2), {"rotate": 90}, [0, 0, 2, 3], (2, 3),
    )
    assert np.allclose(correction[:, :, 0], np.rot90(values).astype(np.float32))
    assert np.allclose(confidence, 1.0)
