from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from _forge_panel_pack_reconstructor import (
    _apply_source_scope_assignments,
    _shift_bbox_inside,
    alpha_retention,
    base_fill_mask,
    composite_group_layers,
    defringe_neutral_edge,
    filter_alpha_components,
    foreground_border_fraction,
    load_manifest_asset,
    load_manifest,
    mandatory_contamination_pixels,
    physical_placement_issues,
    remove_connected_background,
    remove_border_connected_neutral,
    resolve_placement_bbox,
    render_asset,
    semantic_visibility_conflict_pixels,
    trim_alpha,
    validate_semantic_contract,
    validate_manifest_front_authority,
)
from _forge_source_purity import evaluate_panel_manifest


def test_delivery_source_purity_requires_explicit_isolated_asset_authority() -> None:
    manifest = {
        "enforce_delivery_source_purity": True,
        "assets": [{"id": "bad", "source_pixel_scope": "direct_physical_view", "crop": [1, 1, 9, 9]}],
    }
    proof = evaluate_panel_manifest(manifest)
    assert not proof["valid"]
    assert proof["issues"][0]["code"] == "asset_source_scope_not_delivery_safe"


def test_front_manifest_authority_rejects_duplicate_or_unidentified_art() -> None:
    adapter = {
        "physical_assemblies": {
            "front": {"surface": "hood_nose", "semantic_authority_cardinality": 1}
        }
    }
    missing = validate_manifest_front_authority(
        {
            "enforce_front_artwork_authority": True,
            "assets": [
                {"id": "hood_logo", "surface": "hood_nose", "semantic_role": "sponsor"}
            ],
        },
        adapter,
    )
    assert not missing["valid"]

    single = validate_manifest_front_authority(
        {
            "enforce_front_artwork_authority": True,
            "assets": [
                {
                    "id": "front_logo",
                    "surface": "hood_nose",
                    "semantic_role": "sponsor",
                    "semantic_authority_id": "front_brand",
                }
            ],
        },
        adapter,
    )
    assert single["valid"]


def test_delivery_source_purity_accepts_isolated_crop_and_exact_derived_asset() -> None:
    manifest = {
        "enforce_delivery_source_purity": True,
        "assets": [
            {"id": "panel", "source_pixel_scope": "direct_orthographic_isolated_panel", "crop": [1, 1, 9, 9]},
            {"id": "number", "source_pixel_scope": "uv_exact_derived_paint_asset", "placement_mode": "uv_exact"},
        ],
    }
    proof = evaluate_panel_manifest(manifest)
    assert proof["valid"], proof["issues"]


def test_delivery_source_purity_accepts_same_surface_semantic_correction_lineage() -> None:
    manifest = {
        "enforce_delivery_source_purity": True,
        "assets": [
            {
                "id": "panel",
                "source_pixel_scope": "uv_exact_derived_paint_asset",
                "placement_mode": "uv_exact",
                "surface": "left_strip",
                "semantic_role": "paint",
            },
            {
                "id": "panel_residual",
                "source_pixel_scope": "uv_exact_derived_paint_asset",
                "placement_mode": "uv_exact",
                "surface": "left_strip",
                "semantic_role": "paint",
                "correction_of": "panel",
            },
        ],
    }
    proof = evaluate_panel_manifest(manifest)
    assert proof["valid"], proof["issues"]
    assert proof["correction_count"] == 1


def test_delivery_source_purity_rejects_correction_that_crosses_surface_or_role() -> None:
    manifest = {
        "enforce_delivery_source_purity": True,
        "assets": [
            {
                "id": "panel",
                "source_pixel_scope": "uv_exact_derived_paint_asset",
                "placement_mode": "uv_exact",
                "surface": "left_strip",
                "semantic_role": "paint",
            },
            {
                "id": "bad_residual",
                "source_pixel_scope": "uv_exact_derived_paint_asset",
                "placement_mode": "uv_exact",
                "surface": "left_front_fender",
                "semantic_role": "sponsor",
                "correction_of": "panel",
            },
        ],
    }
    proof = evaluate_panel_manifest(manifest)
    assert not proof["valid"]
    assert {issue["code"] for issue in proof["issues"]} == {
        "correction_crosses_surface",
        "correction_changes_semantic_role",
    }


def test_compact_source_scope_assignments_are_explicit_and_disjoint() -> None:
    manifest = {
        "assets": [{"id": "paint"}, {"id": "number"}],
        "source_scope_assignments": {
            "isolated_paint_panel": ["paint"],
            "uv_exact_derived_paint_asset": ["number"],
        },
    }
    resolved = _apply_source_scope_assignments(manifest)
    assert [row["source_pixel_scope"] for row in resolved["assets"]] == [
        "isolated_paint_panel",
        "uv_exact_derived_paint_asset",
    ]


def test_connected_background_removal_preserves_enclosed_white_fill() -> None:
    image = Image.new("RGB", (80, 60), "white")
    pixels = image.load()
    for x in range(15, 65):
        for y in range(10, 50):
            if x in {15, 64} or y in {10, 49}:
                pixels[x, y] = (0, 0, 0)
    result = remove_connected_background(image)
    alpha = np.asarray(result)[:, :, 3]
    assert alpha[0, 0] == 0
    assert alpha[30, 40] == 255
    assert alpha[10, 15] == 255


def test_neutral_studio_removal_preserves_enclosed_white_number() -> None:
    image = Image.new("RGBA", (80, 60), (150, 150, 150, 255))
    for x in range(15, 65):
        for y in range(10, 50):
            image.putpixel((x, y), (245, 195, 15, 255))
    for x in range(30, 50):
        for y in range(20, 40):
            image.putpixel((x, y), (245, 245, 245, 255))
    result = remove_border_connected_neutral(image, min_luma=100, max_chroma=20)
    alpha = np.asarray(result)[:, :, 3]
    assert alpha[0, 0] == 0
    assert alpha[25, 35] == 255


def test_trim_alpha_returns_foreground_bounds() -> None:
    image = Image.new("RGBA", (50, 40), (0, 0, 0, 0))
    for x in range(7, 31):
        for y in range(9, 27):
            image.putpixel((x, y), (10, 20, 30, 255))
    assert trim_alpha(image).size == (24, 18)


def test_component_filter_removes_disconnected_caption_but_keeps_art() -> None:
    image = Image.new("RGBA", (120, 80), (0, 0, 0, 0))
    for x in range(10, 91):
        for y in range(10, 61):
            image.putpixel((x, y), (20, 80, 180, 255))
    for x in range(100, 116):
        for y in range(70, 75):
            image.putpixel((x, y), (0, 0, 0, 255))
    result = filter_alpha_components(image, keep_largest=1)
    alpha = np.asarray(result)[:, :, 3]
    assert alpha[30, 30] == 255
    assert alpha[72, 108] == 0


def test_component_filter_keeps_two_disconnected_digits_by_area() -> None:
    image = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
    for x0 in (10, 55):
        for x in range(x0, x0 + 30):
            for y in range(10, 50):
                image.putpixel((x, y), (235, 240, 245, 255))
    image.putpixel((98, 58), (0, 0, 0, 255))
    result = filter_alpha_components(image, min_area_fraction=0.25)
    alpha = np.asarray(result)[:, :, 3]
    assert alpha[30, 20] == 255
    assert alpha[30, 65] == 255
    assert alpha[58, 98] == 0


def test_border_fraction_detects_crop_cutting_foreground() -> None:
    clean = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    cut = clean.copy()
    for x in range(0, 8):
        for y in range(5, 15):
            cut.putpixel((x, y), (20, 30, 40, 255))
    assert foreground_border_fraction(clean) == 0.0
    assert foreground_border_fraction(cut) > 0.0


def test_neutral_edge_defringe_preserves_colored_edge_and_enclosed_white() -> None:
    image = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    for x in range(4, 26):
        for y in range(4, 26):
            image.putpixel((x, y), (70, 70, 70, 255))
    for x in range(4, 10):
        image.putpixel((x, 4), (20, 120, 220, 255))
    for x in range(12, 18):
        for y in range(12, 18):
            image.putpixel((x, y), (245, 245, 245, 255))
    result = defringe_neutral_edge(image, width_px=2, max_chroma=20, min_luma=35)
    alpha = np.asarray(result)[:, :, 3]
    assert alpha[4, 20] == 0
    assert alpha[4, 6] == 255
    assert alpha[14, 14] == 255


def test_neutral_edge_inpaint_removes_gray_without_reducing_coverage() -> None:
    image = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    for x in range(4, 26):
        for y in range(4, 26):
            color = (90, 90, 90, 255) if x in {4, 25} or y in {4, 25} else (5, 30, 70, 255)
            image.putpixel((x, y), color)
    before = np.asarray(image)[:, :, 3].copy()
    result = defringe_neutral_edge(image, width_px=2, max_chroma=20, min_luma=20, mode="inpaint")
    array = np.asarray(result)
    assert np.array_equal(array[:, :, 3], before)
    assert tuple(array[4, 15, :3]) != (90, 90, 90)


def test_anchor_resolution_scales_and_shifts_inside_surface() -> None:
    adapter = {
        "placement_anchors": {"sponsor": {"bbox": [10, 5, 50, 25]}},
        "surfaces": {"panel": {"bbox": [0, 10, 80, 60]}},
    }
    row = {"id": "logo", "anchor": "sponsor", "surface": "panel"}
    assert resolve_placement_bbox(row, adapter) == [10, 10, 50, 30]
    assert _shift_bbox_inside([70, 50, 80, 60], [0, 0, 100, 100]) == [70, 50, 80, 60]


def test_full_canvas_base_is_independent_of_projection_support(tmp_path: Path) -> None:
    projection = np.zeros((2048, 2048), dtype=bool)
    projection[0:2, 0:2] = True
    mask = base_fill_mask({"base_fill": {"mode": "full_canvas"}}, tmp_path, projection)
    assert int(mask.sum()) == 2048 * 2048
    assert int(projection.sum()) == 4


def test_manifest_revision_overlay_preserves_base_and_can_delete_fields(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    revision = tmp_path / "revision.json"
    base.write_text('{"design_name":"base","assets":[{"id":"number","bbox":[1,2,3,4],"fit":"stretch"}]}', encoding="utf-8")
    revision.write_text(
        '{"extends":"base.json","design_name":"v2","asset_overrides":{"number":{"bbox":null,"anchor":"door","fit":"contain"}}}',
        encoding="utf-8",
    )
    loaded = load_manifest(revision, tmp_path)
    assert loaded["design_name"] == "v2"
    assert loaded["assets"] == [{"id": "number", "anchor": "door", "fit": "contain"}]


def test_composite_group_layers_uses_manifest_group_selection() -> None:
    red = Image.new("RGBA", (4, 4), (255, 0, 0, 255))
    blue = Image.new("RGBA", (4, 4), (0, 0, 255, 255))
    grouped = {"paint": [("red", red)], "numbers": [("blue", blue)]}
    result = composite_group_layers(grouped, ["numbers"], (4, 4))
    assert result.getpixel((2, 2)) == (0, 0, 255, 255)


def test_uv_exact_preserves_pixels_and_clips_to_declared_surface(tmp_path: Path) -> None:
    source = tmp_path / "observed.png"
    mask_path = tmp_path / "surface.png"
    Image.new("RGBA", (2048, 2048), (12, 34, 56, 201)).save(source)
    mask = Image.new("L", (2048, 2048), 0)
    for x in range(100, 140):
        for y in range(200, 240):
            mask.putpixel((x, y), 255)
    mask.save(mask_path)
    row = {"id": "observed", "placement_mode": "uv_exact", "surface": "side", "protect_mandatory": False}
    loaded = load_manifest_asset(source, row)
    rendered = render_asset(
        loaded,
        row,
        {"surfaces": {"side": {"mask_path": mask_path.name}}},
        tmp_path,
        np.zeros((2048, 2048), dtype=bool),
    )
    array = np.asarray(rendered)
    assert tuple(array[220, 120]) == (12, 34, 56, 201)
    assert array[0, 0, 3] == 0
    assert resolve_placement_bbox(row, {}) == [0, 0, 2048, 2048]


def test_uv_exact_rejects_resampling_instructions(tmp_path: Path) -> None:
    source = tmp_path / "observed.png"
    Image.new("RGBA", (2048, 2048), (0, 0, 0, 0)).save(source)
    row = {"id": "observed", "placement_mode": "uv_exact", "fit": "stretch"}
    try:
        load_manifest_asset(source, row)
    except ValueError as exc:
        assert "cannot use transform fields" in str(exc)
    else:
        raise AssertionError("uv_exact accepted a lossy transform")


def test_alpha_preserved_asset_keeps_transparency_before_resampling(tmp_path: Path) -> None:
    source = tmp_path / "panel.png"
    image = Image.new("RGBA", (8, 6), (17, 23, 31, 0))
    for x in range(2, 6):
        for y in range(1, 5):
            image.putpixel((x, y), (240, 190, 8, 173))
    image.save(source)
    loaded = load_manifest_asset(
        source,
        {
            "id": "clean_panel",
            "crop": [0, 0, 8, 6],
            "preserve_source_alpha": True,
        },
    )
    assert loaded.size == (4, 4)
    assert loaded.getpixel((1, 1)) == (240, 190, 8, 173)


def test_alpha_preserved_asset_requires_explicit_crop(tmp_path: Path) -> None:
    source = tmp_path / "panel.png"
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(source)
    try:
        load_manifest_asset(source, {"id": "panel", "preserve_source_alpha": True})
    except ValueError as exc:
        assert "requires an explicit crop" in str(exc)
    else:
        raise AssertionError("alpha-preserved asset accepted an implicit full-sheet crop")


def test_alpha_retention_detects_artwork_cut_by_a_surface_opening() -> None:
    placed = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    for x in range(2, 18):
        for y in range(4, 16):
            placed.putpixel((x, y), (255, 220, 10, 255))
    clipped = placed.copy()
    for x in range(14, 18):
        for y in range(4, 16):
            clipped.putpixel((x, y), (255, 220, 10, 0))
    metrics = alpha_retention(placed, clipped)
    assert metrics["retained_alpha_pct"] == 75.0
    issues = physical_placement_issues(
        [{"id": "logo", "semantic_role": "sponsor", **metrics}],
        {"gate_readable_semantics": True, "semantic_min_retention_pct": 99.5},
    )
    assert "after official surface clipping" in issues[0]


def test_physical_scope_rejects_duplicate_front_artwork() -> None:
    records = [
        {
            "id": "hood_logo",
            "surface": "hood",
            "physical_scope": "hood_nose_front_assembly",
            "artwork_instance_id": "front_primary_wordmark",
            "physical_multiplicity": 1,
        },
        {
            "id": "nose_logo",
            "surface": "nose",
            "physical_scope": "hood_nose_front_assembly",
            "artwork_instance_id": "front_primary_wordmark",
            "physical_multiplicity": 1,
        },
    ]
    issues = physical_placement_issues(records, {})
    assert len(issues) == 1
    assert "occurs 2 times" in issues[0]


def test_physical_piece_identity_rejects_wrong_panel_even_when_contained() -> None:
    records = [
        {
            "id": "hood_art_squeezed_into_fender",
            "surface": "left_front_fender",
            "physical_piece_id": "hood",
            "target_physical_piece_id": "left_front_fender",
        }
    ]
    issues = physical_placement_issues(
        records,
        {"require_physical_piece_identity_surfaces": ["left_front_fender"]},
    )
    assert len(issues) == 1
    assert "does not match target physical piece" in issues[0]


def test_physical_piece_identity_requires_evidence_declaration() -> None:
    records = [
        {
            "id": "unqualified_front_crop",
            "surface": "nose",
            "target_physical_piece_id": "nose",
        }
    ]
    issues = physical_placement_issues(
        records,
        {"require_physical_piece_identity_surfaces": ["nose"]},
    )
    assert len(issues) == 1
    assert "without a declared physical_piece_id" in issues[0]


def test_non_affine_surface_rejects_unmapped_stretch_even_when_piece_matches() -> None:
    records = [
        {
            "id": "labeled_fender_crop",
            "surface": "left_front_fender",
            "physical_piece_id": "left_front_fender",
            "target_physical_piece_id": "left_front_fender",
            "placement_mode": "crop_project",
            "fit": "stretch",
        }
    ]
    issues = physical_placement_issues(
        records,
        {"reject_affine_projection_surfaces": ["left_front_fender"]},
    )
    assert len(issues) == 1
    assert "without calibrated dense UV/piecewise/sim-decoded mapping lineage" in issues[0]


def test_non_affine_surface_accepts_dense_sim_uv_mapping() -> None:
    records = [
        {
            "id": "decoded_fender_crop",
            "surface": "left_front_fender",
            "placement_mode": "crop_project",
            "fit": "stretch",
            "mapping_evidence": {"kind": "sim_uv_decode", "calibration_id": "dlm-438-v1"},
        }
    ]
    issues = physical_placement_issues(
        records,
        {"reject_affine_projection_surfaces": ["left_front_fender"]},
    )
    assert issues == []


def test_non_affine_surface_rejects_uv_exact_without_mapping_lineage() -> None:
    issues = physical_placement_issues(
        [
            {
                "id": "unproven_uv_fender",
                "surface": "left_front_fender",
                "placement_mode": "uv_exact",
            }
        ],
        {"reject_affine_projection_surfaces": ["left_front_fender"]},
    )
    assert len(issues) == 1
    assert "without calibrated" in issues[0]


def test_non_affine_surface_accepts_uv_exact_with_sim_decode_lineage() -> None:
    issues = physical_placement_issues(
        [
            {
                "id": "decoded_uv_fender",
                "surface": "left_front_fender",
                "placement_mode": "uv_exact",
                "mapping_evidence": {"kind": "sim_uv_decode", "calibration_id": "dlm-fixed-cameras-v1"},
            }
        ],
        {"reject_affine_projection_surfaces": ["left_front_fender"]},
    )
    assert issues == []


def test_non_affine_surface_rejects_self_roundtrip_as_mapping_lineage() -> None:
    issues = physical_placement_issues(
        [
            {
                "id": "roundtrip_only_fender",
                "surface": "left_front_fender",
                "placement_mode": "uv_exact",
                "mapping_evidence": {"kind": "render_inverse", "calibration_id": "self-roundtrip"},
            }
        ],
        {"reject_affine_projection_surfaces": ["left_front_fender"]},
    )
    assert len(issues) == 1
    assert "without calibrated" in issues[0]


def test_sim_visibility_keepout_rejects_rocker_text_even_inside_uv_surface() -> None:
    placed = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    for x in range(700, 800):
        for y in range(1710, 1730):
            placed.putpixel((x, y), (255, 255, 255, 255))
    adapter = {
        "semantic_visibility": {
            "right_strip": {"hidden_rects": [{"bbox": [0, 1705, 1310, 1755], "reason": "rocker tuck"}]}
        }
    }
    conflict = semantic_visibility_conflict_pixels(placed, {"surface": "right_strip"}, adapter)
    assert conflict == 2000
    issues = physical_placement_issues(
        [
            {
                "id": "rocker_logo",
                "semantic_role": "sponsor",
                "visibility_keepout_pixels": conflict,
            }
        ],
        {"gate_visibility_keepouts": True},
    )
    assert "3D visibility keepout" in issues[0]


def test_semantic_contract_rejects_mixed_aggregate_group() -> None:
    manifest = {
        "assets": [
            {"id": "paint", "group": "Paint", "semantic_role": "paint"},
            {"id": "number", "group": "Numbers", "semantic_role": "number"},
        ],
        "aggregate_groups": {"layer_numbers.png": ["Numbers", "Paint"]},
        "semantic_contract": {
            "require_all_assets": True,
            "required_roles": ["paint", "number"],
            "group_semantics": {"Paint": "paint", "Numbers": "number"},
            "aggregate_allowed_group_semantics": {"layer_numbers.png": ["number"]},
        },
    }
    result = validate_semantic_contract(manifest)
    assert not result["valid"]
    assert "disallowed semantic paint" in result["issues"][0]


def test_semantic_contract_accepts_pure_groups_and_aggregates() -> None:
    manifest = {
        "assets": [
            {"id": "paint", "group": "Paint", "semantic_role": "paint"},
            {"id": "number", "group": "Numbers", "semantic_role": "number"},
        ],
        "aggregate_groups": {"layer_paint.png": ["Paint"], "layer_numbers.png": ["Numbers"]},
        "semantic_contract": {
            "require_all_assets": True,
            "required_roles": ["paint", "number"],
            "group_semantics": {"Paint": "paint", "Numbers": "number"},
            "aggregate_allowed_group_semantics": {
                "layer_paint.png": ["paint"],
                "layer_numbers.png": ["number"],
            },
        },
    }
    result = validate_semantic_contract(manifest)
    assert result["valid"]
    assert result["asset_role_counts"] == {"paint": 1, "number": 1}


def test_semantic_contract_counts_visually_inert_spec_editing_layer() -> None:
    manifest = {
        "assets": [{"id": "paint", "group": "Paint", "semantic_role": "paint"}],
        "blank_layers": [{"id": "spec", "group": "Spec", "semantic_role": "spec"}],
        "semantic_contract": {
            "require_all_assets": True,
            "required_roles": ["paint", "spec"],
            "group_semantics": {"Paint": "paint", "Spec": "spec"},
        },
    }
    result = validate_semantic_contract(manifest)
    assert result["valid"]
    assert result["asset_role_counts"] == {"paint": 1, "spec": 1}


def test_mandatory_contamination_audits_rendered_alpha() -> None:
    image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    image.putpixel((2, 1), (255, 255, 255, 255))
    mandatory = np.zeros((4, 4), dtype=bool)
    mandatory[1, 2] = True
    assert mandatory_contamination_pixels(image, mandatory) == 1


def test_renderer_source_contains_no_holdout_identity() -> None:
    source = Path("_forge_panel_pack_reconstructor.py").read_text(encoding="utf-8").lower()
    assert "spiderman" not in source
    assert "ghost spider" not in source
