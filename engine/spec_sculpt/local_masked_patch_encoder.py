"""Local RGB+shape encoder for immutable Smart TGA candidate masks.

The encoder sees only normalized pixels inside an exact candidate mask plus
intrinsic mask geometry.  Paint IDs and reviewed family IDs may supervise
training, but are never model inputs or runtime authority.
"""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class LocalMaskedPatchHead(nn.Module):
    """Encode explicit D4 views and emit family, semantic, and completion evidence."""

    def __init__(self, input_channels: int = 6, projection_dim: int = 64):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(input_channels, 24, 5, stride=2, padding=2, bias=False),
            nn.GroupNorm(6, 24),
            nn.GELU(),
            nn.Conv2d(24, 48, 3, stride=2, padding=1, bias=False),
            nn.GroupNorm(8, 48),
            nn.GELU(),
            nn.Conv2d(48, 96, 3, stride=2, padding=1, bias=False),
            nn.GroupNorm(12, 96),
            nn.GELU(),
            nn.Conv2d(96, 128, 3, stride=2, padding=1, bias=False),
            nn.GroupNorm(16, 128),
            nn.GELU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
        )
        self.projection = nn.Sequential(
            nn.Linear(128, 96),
            nn.GELU(),
            nn.Linear(96, projection_dim),
        )
        self.semantic = nn.Linear(projection_dim, 1)
        self.complete = nn.Linear(projection_dim, 1)

    def forward(self, patches: torch.Tensor) -> dict[str, torch.Tensor]:
        if patches.ndim != 5:
            raise ValueError("patches must have shape (candidate, D4 view, channel, height, width)")
        candidate_count, view_count, channels, height, width = patches.shape
        if channels != self.encoder[0].in_channels:
            raise ValueError(f"expected {self.encoder[0].in_channels} channels, got {channels}")
        encoded = self.encoder(patches.reshape(candidate_count * view_count, channels, height, width))
        projected = F.normalize(self.projection(encoded), dim=1)
        projected_views = projected.reshape(candidate_count, view_count, -1)
        pooled = F.normalize(projected_views.mean(dim=1), dim=1)
        return {
            "views": projected_views,
            "pooled": pooled,
            "semantic_logit": self.semantic(pooled).squeeze(1),
            "complete_logit": self.complete(pooled).squeeze(1),
        }


def orbit_similarity(
    projected_views: torch.Tensor,
    pairs: torch.Tensor,
) -> torch.Tensor:
    """Maximum cosine across every orientation/mirror view for each pair."""
    if not len(pairs):
        return projected_views.new_empty((0,))
    return torch.einsum(
        "nvd,nwd->nvw",
        projected_views[pairs[:, 0]],
        projected_views[pairs[:, 1]],
    ).amax(dim=(1, 2))


__all__ = ["LocalMaskedPatchHead", "orbit_similarity"]
