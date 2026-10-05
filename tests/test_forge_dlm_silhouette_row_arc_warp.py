from __future__ import annotations

import numpy as np
import pytest

from _forge_dlm_surface_local_manifest_compose import SurfaceLocalComposeError, _silhouette_row_arc_warp


def test_silhouette_row_arc_fills_target_and_preserves_reading_direction() -> None:
    source = np.zeros((5, 7, 4), dtype=np.uint8)
    source[1:4, 1:3] = (255, 0, 0, 255)
    source[1:4, 3:6] = (0, 0, 255, 255)
    target = np.zeros((9, 13), dtype=bool)
    target[2, 4:9] = True
    target[3, 3:10] = True
    target[4, 2:11] = True
    target[5, 3:10] = True
    target[6, 4:9] = True

    warped = _silhouette_row_arc_warp(source, target)

    assert np.array_equal(warped[..., 3] > 0, target)
    assert tuple(warped[4, 2, :3]) == (255, 0, 0)
    assert tuple(warped[4, 10, :3]) == (0, 0, 255)


def test_silhouette_row_arc_explicit_flip_x_reverses_source_only() -> None:
    source = np.zeros((3, 4, 4), dtype=np.uint8)
    source[:, :2] = (255, 0, 0, 255)
    source[:, 2:] = (0, 0, 255, 255)
    target = np.ones((3, 8), dtype=bool)

    warped = _silhouette_row_arc_warp(source, target, flip_x=True)

    assert tuple(warped[1, 0, :3]) == (0, 0, 255)
    assert tuple(warped[1, -1, :3]) == (255, 0, 0)


def test_readable_asset_requires_separate_semantic_path() -> None:
    with pytest.raises(SurfaceLocalComposeError, match="silhouette_row_arc_requires_paint_only_asset"):
        raise SurfaceLocalComposeError("silhouette_row_arc_requires_paint_only_asset")
