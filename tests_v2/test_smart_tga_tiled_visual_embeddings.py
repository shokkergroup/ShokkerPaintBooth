import numpy as np
import torch

from engine.spec_sculpt.tiled_visual_embeddings import (
    d4_views,
    d4_orbit_similarity,
    embed_d4_candidate_views,
    exact_masked_square,
)


def test_exact_masked_square_uses_only_supported_pixels_and_d4_is_complete():
    image = np.zeros((32, 32, 3), dtype=np.uint8)
    image[5:9, 7:13] = (240, 20, 10)
    image[5:9, 13:17] = (10, 240, 20)
    support = np.zeros((4, 10), dtype=bool)
    support[:, :6] = True
    square = exact_masked_square(image, [7, 5, 10, 4], support, size=32)
    assert square.shape == (32, 32, 3)
    assert np.any(square[..., 0] > 200)
    # Unsupported green pixels must not survive the neutral-canvas adapter.
    assert not np.any((square[..., 1] > 200) & (square[..., 0] < 50))
    views = d4_views(square)
    assert len(views) == 8
    assert all(view.shape == square.shape for view in views)


def test_d4_candidate_views_are_preserved_and_normalized():
    class TinyEncoder(torch.nn.Module):
        def forward(self, values):
            pooled = values.mean(dim=(2, 3))
            return torch.cat((pooled, pooled[:, :1]), dim=1)

    square = np.zeros((16, 16, 3), dtype=np.uint8)
    square[2:7, 4:9] = (255, 80, 10)
    values = embed_d4_candidate_views(TinyEncoder(), [square], batch_size=3)
    assert values.shape == (1, 8, 4)
    assert np.allclose(np.linalg.norm(values, axis=2), 1.0)


def test_d4_orbit_similarity_is_symmetric_and_uses_relative_views():
    views = np.zeros((2, 8, 3), dtype=np.float32)
    views[0, :, 0] = 1.0
    views[1, :, 1] = 1.0
    views[1, 3] = (1.0, 0.0, 0.0)
    values = d4_orbit_similarity(views)
    assert np.array_equal(values, values.T)
    assert np.allclose(np.diag(values), 1.0)
    assert values[0, 1] == 1.0
