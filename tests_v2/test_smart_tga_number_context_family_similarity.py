import numpy as np

from engine.spec_sculpt.number_context_family_similarity import (
    d4_cosine_similarity,
    mask_iou,
    normalized_score_topology,
    normalized_visual_descriptor,
    prototype_margin,
)


def test_descriptor_is_tight_palette_relative_and_immutable():
    rgb = np.zeros((12, 18, 3), np.uint8)
    rgb[3:9, 5:14] = np.asarray([190, 120, 40], np.uint8)
    rgb[4:8, 7:12] = np.asarray([30, 230, 210], np.uint8)
    support = np.zeros((12, 18), bool)
    support[3:9, 5:14] = True
    descriptor = normalized_visual_descriptor(rgb, support, 16)
    assert descriptor.shape == (16, 16)
    assert np.isfinite(descriptor).all()
    assert descriptor.flags.writeable is False


def test_d4_similarity_is_rotation_and_mirror_invariant():
    shape = np.zeros((16, 16), np.float32)
    shape[2:13, 3:6] = 0.7
    shape[9:13, 3:12] = 1.0
    assert d4_cosine_similarity(shape, np.rot90(shape)) > 0.99999
    assert d4_cosine_similarity(shape, np.fliplr(shape)) > 0.99999


def test_prototype_margin_prefers_number_family():
    number = np.zeros((8, 8), np.float32)
    number[1:7, 2:4] = 1.0
    control = np.zeros((8, 8), np.float32)
    control[3:5, 1:7] = 1.0
    query = number.copy()
    assert prototype_margin(query, [number], [control]) > 0.2


def test_score_topology_and_mask_overlap_are_intrinsic():
    support = np.zeros((10, 12), bool)
    support[2:8, 3:10] = True
    scores = np.linspace(0.0, 1.0, 120, dtype=np.float32).reshape(10, 12)
    topology = normalized_score_topology(scores, support, 16)
    assert topology.shape == (16, 16)
    assert topology.flags.writeable is False
    shifted = np.roll(support, 1, axis=1)
    assert 0.0 < mask_iou(support, shifted) < 1.0
