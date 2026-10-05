from __future__ import annotations

import numpy as np
import cv2

from scripts.smart_tga_anchor_free_instance_assembler import (
    _add_cross_panel_corroboration,
    _contour_silhouette,
    _d4_similarity,
    _edge_enclosed_hypotheses,
    _expanded_bbox,
    _silhouette_variants,
    _tall_components,
    _vertical_open,
    assemble_image_hypotheses,
)


def test_expanded_bbox_uses_generic_fractions_and_clips() -> None:
    assert _expanded_bbox([20, 30, 40, 50], (100, 100)) == (10, 20, 60, 70)
    assert _expanded_bbox([0, 0, 40, 50], (100, 100)) == (0, 0, 50, 60)


def test_vertical_open_removes_thin_wordmark_attachment_but_keeps_digits() -> None:
    mask = np.zeros((100, 100), dtype=bool)
    mask[20:90, 25:39] = True
    mask[20:90, 58:72] = True
    mask[16:21, 20:78] = True  # thin attached wordmark band

    opened, kernel_height = _vertical_open(mask, 0.09)

    assert kernel_height == 9
    assert not opened[17, 45]
    assert opened[30:80, 25:39].mean() == 1.0
    assert opened[30:80, 58:72].mean() == 1.0


def test_tall_components_keeps_all_digits_and_rejects_short_sponsor() -> None:
    mask = np.zeros((100, 120), dtype=bool)
    mask[20:90, 20:35] = True
    mask[20:90, 50:65] = True
    mask[80:88, 80:115] = True

    kept, components = _tall_components(mask)

    assert len(components) == 2
    assert kept[30, 25]
    assert kept[30, 55]
    assert not kept[83, 95]


def test_contour_silhouette_fills_color_roles_but_preserves_digit_hole() -> None:
    outline = np.zeros((80, 80), dtype=np.uint8)
    cv2 = __import__("cv2")
    cv2.circle(outline, (40, 40), 25, 1, 2)
    cv2.circle(outline, (40, 40), 9, 1, 2)

    silhouette = _contour_silhouette(outline.astype(bool))

    assert silhouette[40, 58]
    assert not bool(silhouette[40, 40])
    assert not silhouette[5, 5]


def test_post_assembly_open_splits_thin_extreme_wordmark() -> None:
    compound = np.zeros((100, 100), dtype=bool)
    compound[20:90, 25:39] = True
    compound[20:90, 58:72] = True
    compound[15:21, 20:78] = True

    variants = _silhouette_variants(compound)
    trimmed = [mask for name, mask, kernel in variants if name.endswith("vertical_open") and kernel >= 7]

    assert trimmed
    assert any(not mask[17, 45] for mask in trimmed)
    assert all(mask[35:80, 25:39].mean() == 1.0 for mask in trimmed)


def test_d4_similarity_is_rotation_and_mirror_invariant() -> None:
    mask = np.zeros((70, 90), dtype=bool)
    mask[8:60, 12:25] = True
    mask[45:60, 12:65] = True
    transformed = np.fliplr(np.rot90(mask))

    # Aspect-preserving raster normalization introduces a few edge pixels.
    assert _d4_similarity(mask, transformed) > 0.95


def test_assembled_hypotheses_remain_zero_authority() -> None:
    rgb = np.full((180, 180, 3), 235, dtype=np.uint8)
    # Eight visual roles keep deterministic k-means well-conditioned.
    colors = (
        (15, 15, 18), (45, 35, 65), (65, 85, 115), (95, 55, 50),
        (125, 120, 70), (155, 90, 145), (190, 175, 160), (220, 210, 195),
    )
    for index, color in enumerate(colors):
        rgb[10 + index * 5:15 + index * 5, 10:170] = color
    rgb[45:145, 55:73] = (18, 18, 20)
    rgb[45:145, 95:113] = (18, 18, 20)
    rgb[40:46, 48:120] = (18, 18, 20)
    panel_map = {
        "number_blocks": [
            {"name": "normalized_test_panel", "bbox": [40, 35, 90, 115], "area": 10350}
        ]
    }

    rows = assemble_image_hypotheses(rgb, panel_map)

    assert rows
    assert all(row["owner_neutral"] is True for row in rows)
    assert all(row["semantic_label"] is None for row in rows)
    assert all(row["ownership_authority"] is False for row in rows)
    assert all(row["output_authority"] is False for row in rows)
    assert all(row["relationship_authority"] is False for row in rows)
    assert all(
        row["provenance"]["template_position_evidence"] == "normalized_panel_proposal_only"
        for row in rows
    )
    assert {
        "raw_palette_role",
        "enclosed_multicolor_silhouette",
        "enclosed_silhouette_vertical_open",
    }.issubset({row["provenance"]["assembly_variant"] for row in rows})


def test_edge_enclosure_recovers_shared_color_digit_interiors_without_body_field() -> None:
    rgb = np.full((120, 180, 3), (120, 240, 30), dtype=np.uint8)
    cv2.putText(rgb, "97", (22, 92), cv2.FONT_HERSHEY_SIMPLEX, 2.8, (0, 0, 0), 12)
    cv2.putText(
        rgb, "97", (22, 92), cv2.FONT_HERSHEY_SIMPLEX, 2.8, (120, 240, 30), 5
    )

    rows = _edge_enclosed_hypotheses(
        rgb,
        "door_number_lower_side",
        [0, 0, 180, 120],
        (0, 0, 180, 120),
    )
    groups = [
        row
        for row in rows
        if row["provenance"]["assembly_variant"] == "edge_enclosed_group"
    ]

    assert groups
    best = max(groups, key=lambda row: row["features"]["pixel_area"])
    assert best["features"]["panel_occupancy"] < 0.55
    assert best["features"]["height_fraction"] > 0.35
    assert best["ownership_authority"] is False
    assert best["output_authority"] is False


def test_edge_enclosure_returns_no_hypothesis_for_flat_field() -> None:
    rgb = np.full((100, 150, 3), 80, dtype=np.uint8)
    assert _edge_enclosed_hypotheses(
        rgb,
        "door_number_lower_side",
        [0, 0, 150, 100],
        (0, 0, 150, 100),
    ) == []


def test_cross_panel_corroboration_preserves_duplicate_members_with_zero_authority() -> None:
    first = np.zeros((40, 40), dtype=bool)
    first[5:35, 10:16] = True
    second = first.copy()
    rows = [
        {
            "proposal_id": "lower:a",
            "panel_name": "lower",
            "support": first.copy(),
            "intrinsic_score": 0.4,
        },
        {
            "proposal_id": "lower:b",
            "panel_name": "lower",
            "support": first.copy(),
            "intrinsic_score": 0.5,
        },
        {
            "proposal_id": "upper:a",
            "panel_name": "upper",
            "support": second,
            "intrinsic_score": 0.6,
        },
    ]

    _add_cross_panel_corroboration(rows)

    assert rows[0]["corroborative_d4_similarity"] == 1.0
    assert rows[1]["corroborative_d4_similarity"] == 1.0
    assert rows[0]["corroborative_peer_id"] == rows[1]["corroborative_peer_id"]
    assert all(row["relationship_authority"] is False for row in rows)
