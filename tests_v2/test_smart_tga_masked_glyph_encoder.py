import torch

from engine.spec_sculpt.masked_glyph_encoder import MaskedGlyphHead, masked_glyph_loss


def test_masked_glyph_head_is_d4_order_invariant_after_pooling():
    torch.manual_seed(4)
    head = MaskedGlyphHead(input_dim=6, projection_dim=4)
    views = torch.randn(3, 8, 6)
    first = head(views)
    second = head(views[:, torch.tensor([3, 1, 7, 0, 5, 2, 6, 4])])
    assert torch.allclose(first["pooled"], second["pooled"], atol=1e-6)
    assert torch.allclose(first["complete_logit"], second["complete_logit"], atol=1e-6)


def test_masked_glyph_loss_ignores_uncertain_labels_and_backpropagates():
    torch.manual_seed(8)
    head = MaskedGlyphHead(input_dim=5, projection_dim=3)
    outputs = head(torch.randn(4, 8, 5))
    loss, parts = masked_glyph_loss(
        outputs,
        torch.tensor([1, 1, 0, -1]),
        torch.tensor([1, 0, 0, -1]),
        torch.tensor([[0, 1]]),
        torch.tensor([[0, 2]]),
    )
    loss.backward()
    assert torch.isfinite(loss)
    assert set(parts) == {"semantic", "complete", "positive_pair", "negative_pair", "view_consistency"}
    assert all(parameter.grad is not None for parameter in head.parameters())


def test_masked_glyph_pair_loss_is_d4_orbit_order_invariant():
    torch.manual_seed(12)
    head = MaskedGlyphHead(input_dim=7, projection_dim=5)
    views = torch.randn(4, 8, 7)
    first = head(views)
    # Each candidate receives a different D4 ordering.  Family similarity is
    # the best view-to-view match and therefore cannot depend on view order.
    reordered = torch.stack([
        views[0, torch.tensor([3, 1, 7, 0, 5, 2, 6, 4])],
        views[1, torch.tensor([6, 0, 2, 4, 7, 1, 5, 3])],
        views[2, torch.tensor([1, 4, 0, 7, 2, 6, 3, 5])],
        views[3, torch.tensor([7, 6, 5, 4, 3, 2, 1, 0])],
    ])
    second = head(reordered)
    args = (
        torch.tensor([1, 1, 0, 0]),
        torch.tensor([1, 0, 0, 0]),
        torch.tensor([[0, 1]]),
        torch.tensor([[0, 2], [1, 3]]),
    )
    loss_a, parts_a = masked_glyph_loss(first, *args)
    loss_b, parts_b = masked_glyph_loss(second, *args)
    assert torch.allclose(loss_a, loss_b, atol=1e-6)
    assert torch.allclose(parts_a["positive_pair"], parts_b["positive_pair"], atol=1e-6)
    assert torch.allclose(parts_a["negative_pair"], parts_b["negative_pair"], atol=1e-6)
