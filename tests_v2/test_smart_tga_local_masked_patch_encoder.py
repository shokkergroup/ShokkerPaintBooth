from __future__ import annotations

import pytest
import torch

from engine.spec_sculpt.local_masked_patch_encoder import (
    LocalMaskedPatchHead,
    orbit_similarity,
)


def test_local_masked_patch_head_emits_finite_candidate_evidence() -> None:
    torch.manual_seed(726)
    head = LocalMaskedPatchHead(input_channels=6, projection_dim=24).eval()
    patches = torch.rand(3, 8, 6, 64, 64)

    with torch.inference_mode():
        output = head(patches)

    assert output["views"].shape == (3, 8, 24)
    assert output["pooled"].shape == (3, 24)
    assert output["semantic_logit"].shape == (3,)
    assert output["complete_logit"].shape == (3,)
    assert all(torch.isfinite(value).all() for value in output.values())


def test_candidate_evidence_is_invariant_to_d4_view_order() -> None:
    torch.manual_seed(727)
    head = LocalMaskedPatchHead(input_channels=6, projection_dim=16).eval()
    patches = torch.rand(4, 8, 6, 64, 64)
    permutation = torch.tensor([3, 7, 1, 5, 0, 6, 2, 4])

    with torch.inference_mode():
        original = head(patches)
        reordered = head(patches[:, permutation])

    assert torch.allclose(original["pooled"], reordered["pooled"], atol=1e-6)
    assert torch.allclose(original["semantic_logit"], reordered["semantic_logit"], atol=1e-6)
    assert torch.allclose(original["complete_logit"], reordered["complete_logit"], atol=1e-6)


def test_orbit_similarity_is_invariant_to_each_candidate_view_order() -> None:
    torch.manual_seed(728)
    views = torch.nn.functional.normalize(torch.rand(3, 8, 12), dim=2)
    pairs = torch.tensor([[0, 1], [0, 2], [1, 2]])
    first_order = torch.tensor([5, 0, 7, 3, 1, 6, 4, 2])
    second_order = torch.tensor([2, 4, 0, 7, 6, 1, 3, 5])
    reordered = views.clone()
    reordered[0] = reordered[0, first_order]
    reordered[1] = reordered[1, second_order]

    assert torch.allclose(
        orbit_similarity(views, pairs), orbit_similarity(reordered, pairs), atol=1e-7,
    )


def test_local_masked_patch_head_rejects_wrong_shape_or_channel_count() -> None:
    head = LocalMaskedPatchHead(input_channels=6, projection_dim=16)

    with pytest.raises(ValueError, match="shape"):
        head(torch.rand(8, 6, 64, 64))
    with pytest.raises(ValueError, match="expected 6 channels"):
        head(torch.rand(2, 8, 5, 64, 64))
