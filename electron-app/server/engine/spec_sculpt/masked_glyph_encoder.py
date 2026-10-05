"""Trainable masked-glyph evidence head for immutable Smart TGA candidates.

The module consumes visual embeddings only. Paint/family group IDs are allowed
as supervision for contrastive training, never as inference features. Outputs
are corroborative shadow evidence and carry no ownership authority.
"""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class MaskedGlyphHead(nn.Module):
    """Project D4 visual views and predict semantic/completeness evidence."""

    def __init__(self, input_dim: int = 1280, projection_dim: int = 48):
        super().__init__()
        self.projection = nn.Sequential(
            nn.Linear(input_dim, projection_dim),
            nn.GELU(),
            nn.Linear(projection_dim, projection_dim),
        )
        self.semantic = nn.Linear(projection_dim, 1)
        self.complete = nn.Linear(projection_dim, 1)

    def forward(self, views: torch.Tensor):
        if views.ndim != 3:
            raise ValueError("views must have shape (candidate, D4 view, feature)")
        projected_views = F.normalize(self.projection(views), dim=-1)
        pooled = F.normalize(projected_views.mean(dim=1), dim=-1)
        return {
            "views": projected_views,
            "pooled": pooled,
            "semantic_logit": self.semantic(pooled).squeeze(-1),
            "complete_logit": self.complete(pooled).squeeze(-1),
        }


def masked_glyph_loss(
    outputs: dict[str, torch.Tensor],
    semantic_targets: torch.Tensor,
    complete_targets: torch.Tensor,
    positive_pairs: torch.Tensor,
    negative_pairs: torch.Tensor,
    *,
    pair_weight: float = 1.0,
    consistency_weight: float = 0.10,
    negative_margin: float = 0.25,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Return multitask BCE + within-paint contrastive + D4 consistency loss."""
    semantic_valid = semantic_targets >= 0
    complete_valid = complete_targets >= 0
    semantic_values = semantic_targets[semantic_valid]
    complete_values = complete_targets[complete_valid]
    semantic_positive_weight = (
        (semantic_values == 0).sum().float() / (semantic_values == 1).sum().clamp_min(1).float()
    )
    complete_positive_weight = (
        (complete_values == 0).sum().float() / (complete_values == 1).sum().clamp_min(1).float()
    )
    semantic_loss = F.binary_cross_entropy_with_logits(
        outputs["semantic_logit"][semantic_valid], semantic_values.float(),
        pos_weight=semantic_positive_weight,
    )
    complete_loss = F.binary_cross_entropy_with_logits(
        outputs["complete_logit"][complete_valid], complete_values.float(),
        pos_weight=complete_positive_weight,
    )
    pooled = outputs["pooled"]
    if len(positive_pairs):
        positive_similarity = torch.einsum(
            "nvd,nwd->nvw",
            outputs["views"][positive_pairs[:, 0]],
            outputs["views"][positive_pairs[:, 1]],
        ).amax(dim=(1, 2))
        positive_loss = (1.0 - positive_similarity).mean()
    else:
        positive_loss = pooled.sum() * 0.0
    if len(negative_pairs):
        negative_similarity = torch.einsum(
            "nvd,nwd->nvw",
            outputs["views"][negative_pairs[:, 0]],
            outputs["views"][negative_pairs[:, 1]],
        ).amax(dim=(1, 2))
        negative_loss = F.relu(negative_similarity - negative_margin).square().mean()
    else:
        negative_loss = pooled.sum() * 0.0
    view_consistency = 1.0 - (
        outputs["views"] * pooled[:, None, :]
    ).sum(dim=2).mean()
    contrastive = positive_loss + negative_loss
    total = semantic_loss + complete_loss + pair_weight * contrastive + consistency_weight * view_consistency
    return total, {
        "semantic": semantic_loss,
        "complete": complete_loss,
        "positive_pair": positive_loss,
        "negative_pair": negative_loss,
        "view_consistency": view_consistency,
    }


__all__ = ["MaskedGlyphHead", "masked_glyph_loss"]
