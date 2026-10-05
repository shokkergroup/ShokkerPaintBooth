from __future__ import annotations

import numpy as np
import pytest

from engine.spec_sculpt import decal_embeddings


def _logo(text="VP", color=(225, 35, 45)):
    cv2 = decal_embeddings.cv2
    image = np.full((72, 132, 3), 18, np.uint8)
    cv2.rectangle(image, (3, 3), (128, 68), color, 3)
    cv2.putText(image, text, (12, 55), cv2.FONT_HERSHEY_DUPLEX, 1.8, color, 5, cv2.LINE_AA)
    cv2.line(image, (7, 64), (122, 8), (245, 225, 30), 3)
    return image


def test_embedding_is_rotation_mirror_scale_and_recolor_tolerant():
    if decal_embeddings.cv2 is None:
        pytest.skip("OpenCV unavailable")
    base = _logo()
    transformed = np.fliplr(np.rot90(_logo(color=(35, 170, 240)), 2))
    transformed = decal_embeddings.cv2.resize(transformed, (198, 108))
    left = decal_embeddings.embed_decal(base)
    right = decal_embeddings.embed_decal(transformed)
    similarity, _left_view, _right_view = decal_embeddings.embedding_similarity(left, right)
    assert similarity >= 0.84
    assert left.views.flags.writeable is False
    assert not hasattr(left, "owner")


def test_palette_role_embedding_preserves_parent_and_adds_variants():
    image = np.full((70, 150, 3), (220, 20, 30), np.uint8)
    image[20:50, 30:120] = (245, 245, 245)
    mask = np.ones((70, 150), bool)
    base = decal_embeddings.embed_decal(image, mask)
    roles = decal_embeddings.embed_decal(image, mask, include_palette_roles=True)
    assert base.variant_count == 1
    assert roles.variant_count >= 2
    assert roles.views.flags.writeable is False


def test_foreground_subinstance_embedding_is_explicit_and_default_stable():
    image = np.full((90, 220, 3), (220, 18, 30), np.uint8)
    image[:, :8] = 245
    for x in (35, 75, 115, 155):
        image[28:62, x:x + 25] = 245
    mask = np.ones((90, 220), bool)
    base = decal_embeddings.embed_decal(image, mask)
    foreground = decal_embeddings.embed_decal(
        image, mask, include_foreground_subinstances=True
    )
    assert base.variant_count == 1
    assert foreground.variant_count > base.variant_count
    assert foreground.views.flags.writeable is False


def test_reviewed_library_requires_repetition_and_abstains_on_ambiguity():
    if decal_embeddings.cv2 is None:
        pytest.skip("OpenCV unavailable")
    vp1 = decal_embeddings.embed_decal(_logo("VP"))
    vp2 = decal_embeddings.embed_decal(np.fliplr(_logo("VP", (40, 180, 235))))
    refs = [
        decal_embeddings.EmbeddingReference("vp1", "logo:vp", "sponsors", "sponsor_logo", "p1", (0, 0, 1, 1), vp1),
        decal_embeddings.EmbeddingReference("vp2", "logo:vp", "sponsors", "sponsor_logo", "p2", (0, 0, 1, 1), vp2),
    ]
    single = decal_embeddings.query_embedding_library(vp1, refs[:1])
    assert single.status == "abstained"
    assert single.reason == "insufficient_reviewed_family_support"
    match = decal_embeddings.query_embedding_library(vp1, refs)
    assert match.status == "corroborated"
    assert match.family_id == "logo:vp"
    assert match.reviewed_owner == "sponsors"
    assert match.casts_votes is False
    assert match.ownership_authority is False

    ambiguous_refs = refs + [
        decal_embeddings.EmbeddingReference("copy1", "logo:copy", "sponsors", "sponsor_logo", "p3", (0, 0, 1, 1), vp1),
        decal_embeddings.EmbeddingReference("copy2", "logo:copy", "sponsors", "sponsor_logo", "p4", (0, 0, 1, 1), vp2),
    ]
    ambiguous = decal_embeddings.query_embedding_library(vp1, ambiguous_refs)
    assert ambiguous.status == "abstained"
    assert ambiguous.reason == "ambiguous_family_margin"
