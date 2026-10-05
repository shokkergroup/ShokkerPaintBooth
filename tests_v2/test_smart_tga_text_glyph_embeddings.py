import numpy as np

from engine.spec_sculpt.text_glyph_embeddings import prepare_text_glyph_views


def test_text_glyph_views_preserve_all_d4_transforms_and_normalize_range():
    square = np.zeros((18, 18, 3), dtype=np.uint8)
    square[2:8, 4:11] = (250, 80, 20)
    values = prepare_text_glyph_views([square], width=20, height=16)
    assert values.shape == (1, 8, 1, 16, 20)
    assert values.min() >= -1.0
    assert values.max() <= 1.0
    assert not np.array_equal(values[0, 0], values[0, 2])
