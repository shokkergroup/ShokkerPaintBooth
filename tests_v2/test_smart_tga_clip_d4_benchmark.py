from __future__ import annotations

import inspect
import numpy as np

from scripts.smart_tga_clip_complete_train import (
    _candidate_features,
    _safe_threshold,
)
from scripts.smart_tga_clip_d4_benchmark import _build_embeddings, _clip_inputs, _equal_fusion
from scripts.smart_tga_clip_family_adjudicator import (
    _features_for_pairs,
    _zero_error_threshold,
)


def test_clip_inputs_preserve_only_exact_masked_appearance() -> None:
    patches = np.zeros((8, 6, 4, 4), dtype=np.float32)
    patches[:, :3] = 0.9
    patches[:, 3, 1:3, 1:3] = 1.0

    appearance, silhouette = _clip_inputs(patches)

    assert appearance.shape == silhouette.shape == (8, 3, 4, 4)
    assert np.allclose(appearance[:, :, 1:3, 1:3], 0.9)
    assert np.allclose(appearance[:, :, 0, 0], 0.5)
    assert np.allclose(silhouette[:, :, 1:3, 1:3], 1.0)
    assert np.allclose(silhouette[:, :, 0, 0], 0.0)


def test_embedding_benchmark_keeps_silhouette_by_default() -> None:
    parameter = inspect.signature(_build_embeddings).parameters["include_silhouette"]
    assert parameter.default is True


def test_equal_fusion_is_unit_normalized_and_d4_order_equivariant() -> None:
    rng = np.random.default_rng(727)
    appearance = rng.normal(size=(3, 8, 12)).astype(np.float32)
    silhouette = rng.normal(size=(3, 8, 7)).astype(np.float32)
    appearance /= np.linalg.norm(appearance, axis=2, keepdims=True)
    silhouette /= np.linalg.norm(silhouette, axis=2, keepdims=True)
    permutation = np.asarray([5, 1, 7, 0, 4, 2, 6, 3])

    fused = _equal_fusion(appearance, silhouette)
    reordered = _equal_fusion(appearance[:, permutation], silhouette[:, permutation])

    assert np.allclose(np.linalg.norm(fused, axis=2), 1.0, atol=1e-6)
    assert np.allclose(reordered, fused[:, permutation], atol=1e-6)


def test_candidate_features_and_safe_threshold_preserve_abstention_contract() -> None:
    rng = np.random.default_rng(728)
    appearance = rng.normal(size=(6, 8, 10)).astype(np.float32)
    silhouette = rng.normal(size=(6, 8, 5)).astype(np.float32)
    features = _candidate_features(appearance, silhouette)

    assert features["appearance"].shape == (6, 10)
    assert features["appearance_silhouette_equal"].shape == (6, 15)
    assert np.allclose(np.linalg.norm(features["appearance"], axis=1), 1.0, atol=1e-6)
    truth = np.asarray([True, True, False, True, False])
    probability = np.asarray([0.95, 0.90, 0.89, 0.70, 0.10])
    stress = np.asarray([False, False, True, False, False])
    threshold = _safe_threshold(truth, probability, stress)
    accepted = probability >= threshold

    assert not np.any(accepted & stress)
    assert truth[accepted].mean() >= 0.80


def test_family_link_features_are_intrinsic_and_zero_error_threshold_abstains() -> None:
    rng = np.random.default_rng(729)
    appearance = rng.normal(size=(4, 8, 9)).astype(np.float32)
    silhouette = rng.normal(size=(4, 8, 7)).astype(np.float32)
    efficientnet = rng.normal(size=(4, 8, 11)).astype(np.float32)
    for values in (appearance, silhouette, efficientnet):
        values /= np.linalg.norm(values, axis=2, keepdims=True)
    pairs = np.asarray([[0, 1], [0, 2], [1, 3]], dtype=np.int64)

    features = _features_for_pairs(pairs, appearance, silhouette, efficientnet)
    truth = np.asarray([True, False, True, False])
    probability = np.asarray([0.98, 0.97, 0.91, 0.20])
    threshold = _zero_error_threshold(truth, probability)
    accepted = probability >= threshold

    assert features.shape == (3, 3)
    assert np.all(np.isfinite(features))
    assert not np.any(accepted & ~truth)
