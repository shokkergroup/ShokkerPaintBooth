from __future__ import annotations

import json
from dataclasses import replace
import numpy as np
import pytest
from PIL import Image

from conftest import REPO_ROOT

from engine.spec_sculpt import component_evidence
from engine.spec_sculpt.component_evidence import (
    ADJUDICATOR_MODE_ENV,
    EvidenceVote,
    NUMBER_MAP_FAMILY_SHADOW_ENV,
    NUMBER_PROPOSAL_GROUP_ENV,
    OWNERS,
    ProposalMembership,
    RelationshipEdge,
    adjudicate,
    build_component_graph,
    get_adjudicator_mode,
    materialize_masks,
    normalized_masks,
    number_false_positive_semantic_votes,
    number_anchor_groups,
    number_proposal_family_votes,
    proposal_families,
    proposal_groups,
    repeated_number_family_votes,
    relationship_votes,
    run_shadow_adjudication,
    run_shadow_if_enabled,
    simulate_evidence_canary,
    sponsor_semantic_family_votes,
    sponsor_number_family_votes,
    template_position_shadow_evidence,
    votes_from_mask,
    _relationship_pair_indices,
)
from engine.spec_sculpt.candidate_evidence import (
    capture_candidate_adapter_snapshot,
    capture_candidate_snapshot,
    capture_owner_neutral_appearance_snapshot,
    capture_mask_evidence,
    capture_mask_evidence_batch,
    candidate_vote_specs,
    mask_evidence_vote_specs,
)


def test_candidate_adapter_snapshot_preserves_pre_apply_masks_without_authority():
    first = np.zeros((32, 32), np.uint8)
    first[3:10, 4:12] = 255
    second = np.zeros((32, 32), np.uint8)
    second[18:25, 20:29] = 255
    snapshot = capture_candidate_adapter_snapshot([
        {
            "mask": first, "proposed_owner": "numbers",
            "source_stage": "legacy_proposal_pre_apply",
            "source": "legacy_guard:hot_pink_paint_number",
            "reason": "hot_pink_paint_number",
        },
        {"mask": np.zeros_like(first), "proposed_owner": "paint", "source": "empty"},
        {
            "mask": second, "proposed_owner": "sponsors",
            "source_stage": "legacy_proposal_pre_apply",
            "source": "legacy_guard:panel_text_residual",
        },
    ])
    assert snapshot is not None
    assert len(snapshot.regions) == 2
    assert {region.proposed_owner for region in snapshot.regions} == {"numbers", "sponsors"}
    assert {region.source for region in snapshot.regions} == {
        "legacy_guard:hot_pink_paint_number", "legacy_guard:panel_text_residual",
    }
    assert all(region.source_stage == "legacy_proposal_pre_apply" for region in snapshot.regions)
    assert snapshot.to_telemetry()["dropped_regions"] == 0


def _l_shape(canvas: np.ndarray, x: int, y: int, *, mirror: bool = False) -> None:
    shape = np.zeros((14, 10), bool)
    shape[1:13, 1:4] = True
    shape[10:13, 1:9] = True
    if mirror:
        shape = np.fliplr(shape)
    canvas[y:y + shape.shape[0], x:x + shape.shape[1]][shape] = 255


def _fixture(*, three_number_anchors: bool = True):
    height = width = 96
    rgb = np.full((height, width, 3), 32, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    anchors = ((8, 8), (8, 42), (72, 72)) if three_number_anchors else ((8, 8),)
    for x, y in anchors:
        _l_shape(masks["numbers"], x, y)
        rgb[masks["numbers"] > 0] = np.array([218, 28, 42], np.uint8)
    _l_shape(masks["sponsors"], 72, 10, mirror=True)
    rgb[masks["sponsors"] > 0] = np.array([218, 28, 42], np.uint8)
    masks["template"][60:68, 8:24] = 255
    rgb[masks["template"] > 0] = np.array([205, 205, 205], np.uint8)
    occupied = np.zeros((height, width), bool)
    for owner in ("numbers", "sponsors", "template", "brand_graphics"):
        occupied |= masks[owner] > 0
    masks["paint"][~occupied] = 255
    return rgb, masks


def test_owner_neutral_appearance_candidates_add_recall_without_ownership_votes():
    rgb, masks = _fixture()
    rgb[24:40, 28:44] = np.array([244, 54, 146], np.uint8)
    snapshot = capture_owner_neutral_appearance_snapshot(
        rgb,
        min_area_px=8,
        max_area_fraction=0.10,
    )
    assert snapshot.regions
    assert {region.proposed_owner for region in snapshot.regions} == {"unassigned"}
    assert snapshot.to_telemetry()["owner_counts"]["unassigned"] == len(snapshot.regions)
    graph = build_component_graph(rgb, masks)
    assert candidate_vote_specs(graph, snapshot) == ()


def test_owner_neutral_appearance_support_seeds_complete_cross_owner_component():
    rgb = np.full((32, 32, 3), 16, np.uint8)
    rgb[8:16, 6:26] = np.array([230, 40, 120], np.uint8)
    support = np.zeros((32, 32), np.uint8)
    support[8:16, 16:26] = 255

    snapshot = capture_owner_neutral_appearance_snapshot(
        rgb,
        support_mask=support,
        support_mode="seed",
        min_area_px=8,
        max_area_fraction=0.25,
    )

    decal = next(region for region in snapshot.regions if region.bbox == (6, 8, 20, 8))
    assert decal.area == 160
    assert np.all(decal.local_mask)
    assert decal.proposed_owner == "unassigned"
    assert decal.reason == "owner_neutral_source_appearance_support_seeded"

    clipped = capture_owner_neutral_appearance_snapshot(
        rgb,
        support_mask=support,
        support_mode="clip",
        min_area_px=8,
        max_area_fraction=0.25,
    )
    assert any(region.bbox == (16, 8, 10, 8) for region in clipped.regions)
    assert all(region.reason == "owner_neutral_source_appearance" for region in clipped.regions)


def _node(graph, owner):
    return next(node for node in graph.nodes if node.source_owner == owner)


def test_template_position_shadow_adapter_emits_cues_without_votes():
    rgb, masks = _fixture()
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    sponsor = _node(graph, "sponsors")
    number = _node(graph, "numbers")
    memberships = {
        sponsor.node_id: ProposalMembership("s", "sponsors", "raw", "test", 0.9, 1.0, 1.0),
        number.node_id: ProposalMembership("n", "numbers", "raw", "test", 0.9, 1.0, 1.0),
    }
    graph = replace(graph, nodes=tuple(
        replace(node, proposal_memberships=(memberships[node.node_id],))
        if node.node_id in memberships else node
        for node in graph.nodes
    ))
    sx, sy, sw, sh = sponsor.bbox
    nx, ny, nw, nh = number.bbox
    panel_map = {
        "template": "test", "space": "96x96",
        "number_blocks": [{"name": "door", "bbox": [sx, sy, sw, sh]}],
        "sponsor_blocks": [{"name": "strip", "bbox": [nx, ny, nw, nh]}],
    }
    telemetry = template_position_shadow_evidence(graph, panel_map)
    assert telemetry["cue_count"] == 2
    assert telemetry["reason_counts"] == {
        "number_proposal_inside_nonnumber_block": 1,
        "sponsor_proposal_inside_number_block": 1,
    }
    assert telemetry["casts_votes"] is False
    assert telemetry["ownership_authority"] is False


def test_visual_instance_telemetry_maps_existing_nodes_but_casts_no_votes():
    from engine.spec_sculpt.decal_instances import VisualInstanceMatch

    rgb, masks = _fixture()
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    sponsor = _node(graph, "sponsors")
    x, y, width, height = sponsor.bbox
    match = VisualInstanceMatch(
        source_bbox=(8, 8, 10, 14),
        polygon=((x, y), (x + width, y), (x + width, y + height), (x, y + height)),
        good_match_count=9,
        inlier_count=8,
        inlier_ratio=0.888889,
        projected_area_ratio=1.0,
    )
    telemetry = component_evidence.visual_instance_node_telemetry(
        graph, match, min_pixels=2
    )
    sponsor_entry = next(
        item for item in telemetry["nodes"] if item["node"] == sponsor.node_id
    )
    assert sponsor_entry["source_owner"] == "sponsors"
    assert sponsor_entry["matched_pixels"] > 0
    assert telemetry["casts_votes"] is False
    assert telemetry["ownership_authority"] is False


def test_visual_instance_shadow_uses_one_index_for_raw_number_proposals(monkeypatch):
    from engine.spec_sculpt import decal_instances
    from engine.spec_sculpt.decal_instances import VisualInstanceMatch

    rgb = np.full((96, 96, 3), 30, np.uint8)
    masks = {owner: np.zeros((96, 96), np.uint8) for owner in OWNERS}
    masks["numbers"][8:40, 8:40] = 255
    masks["sponsors"][52:84, 52:84] = 255
    occupied = (masks["numbers"] > 0) | (masks["sponsors"] > 0)
    masks["paint"][~occupied] = 255
    snapshot = capture_candidate_snapshot(
        {"numbers": masks["numbers"]},
        source_stage="gpu_model_raw",
        source="smart_tga_gpu_hybrid",
    )
    graph = build_component_graph(rgb, masks, candidate_snapshot=snapshot)
    sentinel = object()
    calls = {"build": 0, "find": 0}

    def fake_build(_rgb):
        calls["build"] += 1
        return sentinel

    def fake_find(_rgb, source_bbox, **kwargs):
        calls["find"] += 1
        assert kwargs["feature_index"] is sentinel
        return VisualInstanceMatch(
            source_bbox=tuple(source_bbox),
            polygon=((52, 52), (84, 52), (84, 84), (52, 84)),
            good_match_count=12,
            inlier_count=10,
            inlier_ratio=0.833333,
            projected_area_ratio=1.0,
        )

    monkeypatch.setattr(decal_instances, "build_visual_feature_index", fake_build)
    monkeypatch.setattr(decal_instances, "find_visual_instance_match", fake_find)
    telemetry = component_evidence.visual_instance_shadow_telemetry(rgb, graph)
    assert calls == {"build": 1, "find": 1}
    assert telemetry["status"] == "observed"
    assert telemetry["feature_index_build_count"] == 1
    assert telemetry["casts_votes"] is False
    assert telemetry["ownership_authority"] is False
    assert telemetry["matches"][0]["nodes"][0]["source_owner"] == "sponsors"


def test_visual_instance_shadow_rejects_circular_repair_provenance(monkeypatch):
    from engine.spec_sculpt import decal_instances

    rgb = np.full((64, 64, 3), 30, np.uint8)
    masks = {owner: np.zeros((64, 64), np.uint8) for owner in OWNERS}
    masks["numbers"][8:40, 8:40] = 255
    masks["paint"][masks["numbers"] == 0] = 255
    snapshot = capture_candidate_snapshot(
        {"numbers": masks["numbers"]},
        source_stage="final_repair",
        source="materialized_owner_repair",
    )
    graph = build_component_graph(rgb, masks, candidate_snapshot=snapshot)
    monkeypatch.setattr(
        decal_instances,
        "build_visual_feature_index",
        lambda _rgb: pytest.fail("circular proposal must not build visual index"),
    )
    telemetry = component_evidence.visual_instance_shadow_telemetry(rgb, graph)
    assert telemetry["status"] == "abstained"
    assert telemetry["rejected_seed_reasons"] == {"circular_provenance": 1}
    assert telemetry["casts_votes"] is False


def test_visual_instance_shadow_rejects_thin_raw_number_textline(monkeypatch):
    from engine.spec_sculpt import decal_instances

    rgb = np.full((80, 128, 3), 30, np.uint8)
    masks = {owner: np.zeros((80, 128), np.uint8) for owner in OWNERS}
    masks["numbers"][16:40, 12:84] = 255
    masks["paint"][masks["numbers"] == 0] = 255
    snapshot = capture_candidate_snapshot(
        {"numbers": masks["numbers"]},
        source_stage="gpu_model_raw",
        source="smart_tga_gpu_hybrid",
    )
    graph = build_component_graph(rgb, masks, candidate_snapshot=snapshot)
    monkeypatch.setattr(
        decal_instances,
        "build_visual_feature_index",
        lambda _rgb: pytest.fail("thin textline seed must not build visual index"),
    )
    telemetry = component_evidence.visual_instance_shadow_telemetry(rgb, graph)
    assert telemetry["status"] == "abstained"
    assert telemetry["rejected_seed_reasons"] == {"thin_textline_geometry": 1}
    assert telemetry["rejected_seed_samples"] == [{
        "candidate_id": telemetry["rejected_seed_samples"][0]["candidate_id"],
        "bbox": [12, 16, 72, 24],
        "reason": "thin_textline_geometry",
        "confidence": 1.0,
        "covered_pixels": 1728,
    }]
    assert telemetry["casts_votes"] is False
    assert telemetry["ownership_authority"] is False


def test_visual_instance_shadow_gate_is_default_off_and_telemetry_only(monkeypatch):
    rgb, masks = _fixture()
    monkeypatch.delenv(component_evidence.VISUAL_INSTANCE_SHADOW_ENV, raising=False)
    default_report = run_shadow_adjudication(rgb, masks).to_telemetry()
    assert default_report["visual_instances"]["status"] == "disabled"
    default_xor = default_report["xor_pixels"]

    observed = {
        "status": "observed", "seed_count": 1, "match_count": 1,
        "matches": [], "casts_votes": False, "ownership_authority": False,
    }
    monkeypatch.setenv(component_evidence.VISUAL_INSTANCE_SHADOW_ENV, "shadow")
    monkeypatch.setattr(
        component_evidence,
        "visual_instance_shadow_telemetry",
        lambda _rgb, _graph: observed,
    )
    enabled_report = run_shadow_adjudication(rgb, masks).to_telemetry()
    assert enabled_report["visual_instances"] == observed
    assert enabled_report["xor_pixels"] == default_xor


def test_cross_proposal_number_family_requires_owned_anchors():
    rgb, masks = _fixture(three_number_anchors=True)
    sponsor_ink = masks["sponsors"] > 0
    yy, xx = np.indices(sponsor_ink.shape)
    rgb[sponsor_ink & ((xx + yy) % 2 == 0)] = np.array([250, 245, 245], np.uint8)
    rgb[sponsor_ink & ((xx + yy) % 2 == 1)] = np.array([210, 30, 45], np.uint8)
    raw_numbers = ((masks["numbers"] > 0) | (masks["sponsors"] > 0)).astype(np.uint8) * 255
    snapshot = capture_candidate_snapshot(
        {"numbers": raw_numbers},
        source_stage="gpu_raw",
        source="synthetic_split_number_proposals",
    )
    graph = build_component_graph(rgb, masks, candidate_snapshot=snapshot, pair_budget=100000)
    families = proposal_families(graph)
    family = next(item for item in families if item.candidate_node_ids)
    assert len(family.candidate_ids) >= 3
    assert len(family.anchor_node_ids) >= 2
    votes, telemetry = number_proposal_family_votes(graph)
    sponsor = _node(graph, "sponsors")
    assert {vote.node_id for vote in votes} == {sponsor.node_id}
    assert len(votes) == 2
    assert telemetry["target_owner_counts"] == {"numbers": 2}

    numeric_ocr_graph = build_component_graph(
        rgb,
        masks,
        candidate_snapshot=snapshot,
        ocr_regions=[{
            "id": "ocr-number", "kind": "sponsor", "bbox": list(sponsor.bbox),
            "text": "16", "confidence": 0.99, "text_quality": 1.0,
        }],
        pair_budget=100000,
    )
    assert len(number_proposal_family_votes(numeric_ocr_graph)[0]) == 2
    alpha_ocr_graph = build_component_graph(
        rgb,
        masks,
        candidate_snapshot=snapshot,
        ocr_regions=[{
            "id": "ocr-word", "kind": "sponsor", "bbox": list(sponsor.bbox),
            "text": "LOGO", "confidence": 0.99, "text_quality": 1.0,
        }],
        pair_budget=100000,
    )
    alpha_votes, alpha_telemetry = number_proposal_family_votes(alpha_ocr_graph)
    assert alpha_votes == ()
    assert alpha_telemetry["rejection_counts"]["strong_alpha_ocr"] == 1

    sponsor_only_masks = {owner: mask.copy() for owner, mask in masks.items()}
    sponsor_only_masks["sponsors"] |= sponsor_only_masks["numbers"]
    sponsor_only_masks["numbers"][:] = 0
    sponsor_only_graph = build_component_graph(
        rgb, sponsor_only_masks, candidate_snapshot=snapshot, pair_budget=100000
    )
    assert proposal_families(sponsor_only_graph) == ()
    assert number_proposal_family_votes(sponsor_only_graph)[0] == ()


def test_repeated_number_family_requires_two_number_anchors_and_sponsor_peer():
    rgb, masks = _fixture(three_number_anchors=True)
    _l_shape(masks["sponsors"], 44, 70, mirror=True)
    for owner in ("numbers", "sponsors"):
        source = masks[owner] > 0
        expanded = np.zeros_like(source)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                expanded |= np.roll(source, (dy, dx), axis=(0, 1))
        masks[owner][:] = expanded.astype(np.uint8) * 255
    masks["paint"][:] = 0
    masks["paint"][(masks["numbers"] == 0) & (masks["sponsors"] == 0)] = 255
    ink = (masks["numbers"] > 0) | (masks["sponsors"] > 0)
    yy, xx = np.indices(ink.shape)
    rgb[ink & ((xx + yy) % 2 == 0)] = np.array([250, 245, 245], np.uint8)
    rgb[ink & ((xx + yy) % 2 == 1)] = np.array([210, 30, 45], np.uint8)
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    votes, telemetry = repeated_number_family_votes(graph)
    sponsor_ids = {node.node_id for node in graph.nodes if node.source_owner == "sponsors"}
    assert {vote.node_id for vote in votes} == sponsor_ids
    assert len(votes) == 2 * len(sponsor_ids)
    assert telemetry["target_owner_counts"] == {"numbers": len(votes)}

    one_sponsor_masks = {owner: mask.copy() for owner, mask in masks.items()}
    one_sponsor_masks["sponsors"][66:90, 40:60] = 0
    one_sponsor_masks["paint"][66:90, 40:60] = 255
    one_sponsor_graph = build_component_graph(rgb, one_sponsor_masks, pair_budget=100000)
    one_sponsor_votes, _ = repeated_number_family_votes(one_sponsor_graph)
    assert len(one_sponsor_votes) == 2

    # A detailed neutral illustration may resemble two digit shapes but cannot
    # use the full-size bypass without a second Sponsor-owned decal peer.
    neutral_rgb = rgb.copy()
    sponsor_ink = one_sponsor_masks["sponsors"] > 0
    yy, xx = np.indices(sponsor_ink.shape)
    neutral_rgb[sponsor_ink & ((xx + yy) % 2 == 0)] = np.array([245, 245, 245], np.uint8)
    neutral_rgb[sponsor_ink & ((xx + yy) % 2 == 1)] = np.array([35, 35, 35], np.uint8)
    neutral_graph = build_component_graph(
        neutral_rgb, one_sponsor_masks, pair_budget=100000
    )
    neutral_votes, _neutral_telemetry = repeated_number_family_votes(neutral_graph)
    assert neutral_votes == ()


def test_number_anchor_groups_compose_only_local_number_atoms():
    rgb = np.full((64, 64, 3), 24, np.uint8)
    masks = {owner: np.zeros((64, 64), np.uint8) for owner in OWNERS}
    masks["numbers"][10:20, 10:15] = 255
    masks["numbers"][10:20, 16:21] = 255
    masks["numbers"][46:56, 46:51] = 255
    rgb[masks["numbers"] > 0] = np.array([225, 35, 50], np.uint8)
    masks["paint"][masks["numbers"] == 0] = 255
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    groups = number_anchor_groups(graph)
    assert sorted(len(group.member_node_ids) for group in groups) == [1, 2]
    assert all(group.shape_descriptor for group in groups)
    assert all(group.palette_descriptor for group in groups)


def test_number_semantics_require_panel_anatomy_plus_template_family_context():
    height = width = 128
    rgb = np.full((height, width, 3), 24, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["numbers"][28:40, 24:54] = 255
    masks["template"][42:54, 24:54] = 255
    rgb[masks["numbers"] > 0] = np.array([168, 168, 168], np.uint8)
    rgb[masks["template"] > 0] = np.array([168, 168, 168], np.uint8)
    occupied = (masks["numbers"] > 0) | (masks["template"] > 0)
    masks["paint"][~occupied] = 255
    graph = build_component_graph(rgb, masks, pair_budget=100000)

    votes, telemetry = number_false_positive_semantic_votes(
        graph, rgb, masks["numbers"]
    )

    assert {vote.source for vote in votes} == {
        "semantic_number:neutral_panel_anatomy",
        "semantic_number:template_family_context",
    }
    assert {vote.owner for vote in votes} == {"template"}
    assert telemetry["target_owner_counts"] == {"template": 2}
    result = adjudicate(graph, votes, include_relationship_votes=False)
    number_node = _node(graph, "numbers")
    assert result.assignments[number_node.index] == "template"


def test_number_semantics_do_not_move_true_repeated_digit_family():
    rgb, masks = _fixture()
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    votes, _telemetry = number_false_positive_semantic_votes(
        graph, rgb, masks["numbers"]
    )
    assert votes == ()


def test_single_full_number_anchor_protects_only_near_exact_small_copy_pair():
    cv2 = component_evidence.cv2
    if cv2 is None:
        pytest.skip("OpenCV unavailable")
    size = 320
    rgb = np.full((size, size, 3), 20, np.uint8)
    numbers = np.zeros((size, size), np.uint8)

    small = np.zeros((34, 26), np.uint8)
    cv2.circle(small, (13, 9), 8, 255, 4)
    cv2.circle(small, (13, 24), 8, 255, 4)
    anchor = cv2.resize(small, (78, 102), interpolation=cv2.INTER_NEAREST)
    false = np.zeros_like(small)
    cv2.line(false, (3, 3), (22, 30), 255, 5)
    cv2.line(false, (22, 3), (3, 30), 255, 5)

    placements = (
        (anchor, 20, 20),
        (small, 155, 45),
        (small, 220, 45),
        (false, 160, 115),
    )
    for local, x, y in placements:
        height, width = local.shape
        numbers[y:y + height, x:x + width][local > 0] = 255
        region = rgb[y:y + height, x:x + width]
        rows = np.indices(local.shape)[0]
        region[(local > 0) & (rows < height // 2)] = np.array([238, 238, 225], np.uint8)
        region[(local > 0) & (rows >= height // 2)] = np.array([205, 35, 48], np.uint8)

    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(numbers, 8)
    assert count == 5
    signals = component_evidence.number_family_signals(
        rgb, numbers, labels=labels, stats=stats
    )
    bbox_to_label = {
        tuple(int(value) for value in stats[label, :4]): label
        for label in range(1, count)
    }
    first_small = bbox_to_label[(158, 45, 21, 34)]
    second_small = bbox_to_label[(223, 45, 21, 34)]
    false_label = bbox_to_label[(160, 115, 26, 34)]
    assert signals.anchor_labels
    assert {first_small, second_small}.issubset(signals.protected_labels)
    assert false_label not in signals.protected_labels


def test_number_semantics_do_not_call_neutral_placeholder_a_sponsor_badge():
    height = width = 128
    rgb = np.full((height, width, 3), 20, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["numbers"][20:48, 20:48] = 255
    masks["sponsors"][20:48, 54:82] = 255
    for owner in ("numbers", "sponsors"):
        region = masks[owner] > 0
        rgb[region] = np.array([190, 190, 190], np.uint8)
    rgb[28:40, 28:40] = np.array([70, 70, 70], np.uint8)
    rgb[28:40, 62:74] = np.array([70, 70, 70], np.uint8)
    occupied = (masks["numbers"] > 0) | (masks["sponsors"] > 0)
    masks["paint"][~occupied] = 255
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    votes, _telemetry = number_false_positive_semantic_votes(
        graph, rgb, masks["numbers"]
    )
    assert votes == ()


def test_number_semantics_require_alphabetic_ocr_for_sponsor_badge_family():
    height = width = 128
    rgb = np.full((height, width, 3), 18, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["numbers"][20:28, 20:32] = 255
    masks["sponsors"][20:28, 42:54] = 255
    masks["numbers"][22:26, 24:28] = 0
    masks["sponsors"][22:26, 46:50] = 0
    for x in (20, 42):
        rgb[20:24, x:x + 12] = np.array([225, 35, 45], np.uint8)
        rgb[24:28, x:x + 12] = np.array([35, 95, 225], np.uint8)
    occupied = (masks["numbers"] > 0) | (masks["sponsors"] > 0)
    masks["paint"][~occupied] = 255

    def votes_for(text: str):
        graph = build_component_graph(rgb, masks, ocr_regions=[{
            "id": f"ocr-{text}", "kind": "sponsor", "bbox": [20, 20, 12, 8],
            "text": text, "confidence": 0.95, "text_quality": 0.9,
        }], pair_budget=100000)
        return number_false_positive_semantic_votes(graph, rgb, masks["numbers"])[0]

    alpha_votes = votes_for("KOBALT")
    assert {vote.source for vote in alpha_votes} == {
        "semantic_number:badge_logo_anatomy",
        "semantic_number:sponsor_family_context",
    }
    assert {vote.owner for vote in alpha_votes} == {"sponsors"}
    assert votes_for("48") == ()


def test_number_semantics_recover_repeated_dense_micro_logo_without_ocr(monkeypatch):
    height = width = 192
    rgb = np.full((height, width, 3), 18, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}

    def micro_logo(mask: np.ndarray, x: int, y: int) -> None:
        mask[y:y + 18, x:x + 36] = 255
        mask[y + 3:y + 8, x + 4:x + 32] = 0
        mask[y + 11:y + 15, x + 8:x + 28] = 0
        rgb[y:y + 9, x:x + 36] = np.array([235, 230, 220], np.uint8)
        rgb[y + 9:y + 18, x:x + 36] = np.array([205, 35, 48], np.uint8)
        rgb[y + 3:y + 8, x + 4:x + 32] = np.array([18, 18, 18], np.uint8)
        rgb[y + 11:y + 15, x + 8:x + 28] = np.array([18, 18, 18], np.uint8)

    micro_logo(masks["numbers"], 20, 24)
    micro_logo(masks["sponsors"], 82, 24)
    micro_logo(masks["sponsors"], 82, 76)
    occupied = (masks["numbers"] > 0) | (masks["sponsors"] > 0)
    masks["paint"][~occupied] = 255
    monkeypatch.setattr(
        "engine.spec_sculpt.component_evidence.number_family_signals",
        lambda *_args, **_kwargs: __import__(
            "engine.spec_sculpt.component_evidence", fromlist=["NumberFamilySignals"]
        ).NumberFamilySignals(),
    )
    graph = build_component_graph(rgb, masks, pair_budget=100000)

    votes, telemetry = number_false_positive_semantic_votes(
        graph, rgb, masks["numbers"]
    )

    assert {vote.source for vote in votes} == {
        "semantic_number:dense_micro_logo_anatomy",
        "semantic_number:repeated_sponsor_family_context",
    }
    assert {vote.owner for vote in votes} == {"sponsors"}
    assert telemetry["target_owner_counts"] == {"sponsors": 2}


def test_dense_micro_logo_palette_only_context_abstains(monkeypatch):
    height = width = 192
    rgb = np.full((height, width, 3), 18, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    for owner, x, y in (
        ("numbers", 20, 24),
        ("sponsors", 82, 24),
        ("sponsors", 82, 76),
        ("sponsors", 20, 76),
    ):
        masks[owner][y:y + 16, x:x + 32] = 255
        masks[owner][y + 4:y + 8, x + 5:x + 27] = 0
        yy, xx = np.indices((16, 32))
        crop = rgb[y:y + 16, x:x + 32]
        crop[(xx // 3 + yy // 3) % 2 == 0] = np.array([235, 230, 220], np.uint8)
        crop[(xx // 3 + yy // 3) % 2 == 1] = np.array([205, 35, 48], np.uint8)
    masks["paint"][~((masks["numbers"] > 0) | (masks["sponsors"] > 0))] = 255
    monkeypatch.setattr(
        component_evidence,
        "number_family_signals",
        lambda *_args, **_kwargs: component_evidence.NumberFamilySignals(),
    )
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    number_node = next(node for node in graph.nodes if node.source_owner == "numbers")
    weakened = tuple(
        edge for edge in graph.edges
        if number_node.node_id not in (edge.left, edge.right)
    ) + tuple(
        RelationshipEdge(
            left=number_node.node_id,
            right=node.node_id,
            kinds=("shared_palette",),
            distance=0.10,
            containment=0.0,
            palette_similarity=1.0,
            shape_similarity=0.50,
            mirror_similarity=0.50,
            rotation180_similarity=0.50,
        )
        for node in graph.nodes if node.source_owner == "sponsors"
    )
    graph = replace(graph, edges=weakened)
    votes, telemetry = number_false_positive_semantic_votes(
        graph, rgb, masks["numbers"]
    )
    assert votes == ()
    assert telemetry["abstained_reason_counts"] == {
        "palette_only_micro_logo_ambiguity": 1
    }
    assert telemetry["abstained_samples"][0]["bbox"] == list(number_node.bbox)


def test_protected_number_parent_allows_only_complex_high_confidence_alpha_atom(monkeypatch):
    height = width = 160
    rgb = np.full((height, width, 3), 18, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    for x in (12, 70, 122):
        _l_shape(masks["numbers"], x, 18)
    # Join a complex badge atom into the first repeated-number component so
    # label-level Number protection covers both the true digit and the badge.
    masks["numbers"][24:27, 20:52] = 255
    masks["numbers"][18:34, 48:64] = 255
    rgb[masks["numbers"] > 0] = np.array([225, 225, 210], np.uint8)
    rgb[18:26, 48:64] = np.array([225, 35, 45], np.uint8)
    rgb[26:34, 48:64] = np.array([35, 95, 225], np.uint8)
    masks["paint"][masks["numbers"] == 0] = 255
    monkeypatch.setattr(
        "engine.spec_sculpt.component_evidence.number_family_signals",
        lambda *_args, **_kwargs: __import__(
            "engine.spec_sculpt.component_evidence", fromlist=["NumberFamilySignals"]
        ).NumberFamilySignals(protected_labels=frozenset({2})),
    )

    def vote_sources(text: str, confidence: float = 0.98):
        graph = build_component_graph(rgb, masks, ocr_regions=[{
            "id": f"ocr-{text}", "kind": "sponsor", "bbox": [48, 18, 16, 16],
            "text": text, "confidence": confidence, "text_quality": 1.0,
        }], pair_budget=100000)
        if text == "PRIDE" and confidence >= 0.85:
            assert graph.proposal_split_count >= 1
        if text == "48" or confidence < 0.85:
            assert graph.proposal_split_count == 0
        votes, _telemetry = number_false_positive_semantic_votes(
            graph, rgb, masks["numbers"]
        )
        return {vote.source for vote in votes}

    assert vote_sources("PRIDE") == {
        "semantic_number:alpha_conflict_badge_anatomy",
        "semantic_number:high_confidence_alpha_ocr_conflict",
    }
    assert vote_sources("48") == set()
    assert vote_sources("PRIDE", confidence=0.60) == set()


def test_number_semantic_telemetry_exposes_each_independent_reason():
    height = width = 128
    rgb = np.full((height, width, 3), 24, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["numbers"][28:40, 24:54] = 255
    masks["template"][42:54, 24:54] = 255
    rgb[masks["numbers"] > 0] = np.array([168, 168, 168], np.uint8)
    rgb[masks["template"] > 0] = np.array([168, 168, 168], np.uint8)
    occupied = (masks["numbers"] > 0) | (masks["template"] > 0)
    masks["paint"][~occupied] = 255
    graph = build_component_graph(rgb, masks, pair_budget=100000)
    votes, telemetry = number_false_positive_semantic_votes(
        graph, rgb, masks["numbers"]
    )
    assert len(votes) == 2
    assert {sample["reason"] for sample in telemetry["samples"]} == {
        "flat_neutral_number_panel_anatomy",
        "matching_template_panel_family",
    }
    assert telemetry["samples_truncated"] is False


def test_sponsor_number_family_requires_decal_anatomy_and_protects_alpha_ocr():
    rgb, masks = _fixture()
    ink = (masks["numbers"] > 0) | (masks["sponsors"] > 0)
    yy, _xx = np.indices(ink.shape)
    rgb[ink & (yy % 4 < 2)] = np.array([225, 245, 250], np.uint8)
    rgb[ink & (yy % 4 >= 2)] = np.array([25, 210, 95], np.uint8)
    graph = build_component_graph(rgb, masks, pair_budget=100000)

    sponsor = _node(graph, "sponsors")
    raw_proposal = EvidenceVote(
        node_id=sponsor.node_id,
        owner="numbers",
        weight=0.58,
        source="initial_proposal:smart_separate",
        reason="ocr_raw:unrepaired_ocr_partition",
        support=("candidate-number",),
    )
    votes, telemetry = sponsor_number_family_votes(graph, (raw_proposal,))

    assert {vote.source for vote in votes} == {
        "semantic_sponsor:number_decal_anatomy",
        "semantic_sponsor:number_family_context",
    }
    assert {vote.owner for vote in votes} == {"numbers"}
    assert telemetry["target_owner_counts"] == {"numbers": 2}

    assert sponsor_number_family_votes(graph)[0] == ()
    assert all(sample["raw_number_proposal_count"] == 1 for sample in telemetry["samples"])
    protected_graph = build_component_graph(rgb, masks, ocr_regions=[{
        "id": "ocr-logo", "kind": "sponsor", "bbox": list(sponsor.bbox),
        "text": "LOGO", "confidence": 0.99, "text_quality": 1.0,
    }], pair_budget=100000)
    protected_sponsor = _node(protected_graph, "sponsors")
    protected_proposal = EvidenceVote(
        node_id=protected_sponsor.node_id,
        owner="numbers",
        weight=0.58,
        source="initial_proposal:smart_separate",
        reason="ocr_raw:unrepaired_ocr_partition",
    )
    protected_votes, _ = sponsor_number_family_votes(protected_graph, (protected_proposal,))
    assert protected_votes == ()


def test_relationship_pair_budget_is_index_fair_and_duplicate_free():
    pairs = list(_relationship_pair_indices(101, 202))
    assert len(pairs) == 202
    assert len({frozenset(pair) for pair in pairs}) == 202
    assert {index for pair in pairs for index in pair} == set(range(101))

    complete = list(_relationship_pair_indices(6, 15))
    assert len(complete) == 15
    assert {frozenset(pair) for pair in complete} == {
        frozenset((left, right))
        for left in range(6)
        for right in range(left + 1, 6)
    }


def test_component_graph_is_immutable_and_preserves_partition():
    rgb, masks = _fixture()
    originals = {owner: mask.copy() for owner, mask in masks.items()}
    graph = build_component_graph(rgb, masks)

    assert graph.component_map.flags.writeable is False
    assert graph.owner_map.flags.writeable is False
    with pytest.raises(ValueError):
        graph.owner_map[0, 0] = 3

    current = normalized_masks(graph)
    coverage = sum((mask > 0).astype(np.uint8) for mask in current.values())
    assert np.all(coverage == 1)
    for owner in OWNERS:
        assert np.array_equal(masks[owner], originals[owner])
        assert np.array_equal(current[owner], originals[owner])


def test_graph_records_mirror_family_and_ocr_provenance():
    rgb, masks = _fixture()
    graph = build_component_graph(
        rgb,
        masks,
        ocr_regions=[{
            "id": "mirror-wordmark-1",
            "kind": "sponsor",
            "orientation": "mirror-r90",
            "mirrored": True,
            "bbox": [70, 8, 16, 20],
            "text": "MOTUL",
            "confidence": 0.91,
        }],
    )
    sponsor = _node(graph, "sponsors")
    assert sponsor.ocr_memberships
    assert sponsor.ocr_memberships[0].region_id == "mirror-wordmark-1"
    assert sponsor.ocr_memberships[0].mirrored is True
    assert sponsor.ocr_memberships[0].word_family == "motul"
    assert sponsor.ocr_memberships[0].confidence == 0.91
    assert sponsor.ocr_memberships[0].text_quality == 1.0
    assert sponsor.ocr_memberships[0].region_coverage_fraction > 0

    family_edges = [
        edge for edge in graph.edges
        if sponsor.node_id in (edge.left, edge.right)
        and set(edge.kinds) & {"mirror_similarity", "rotation180_similarity", "side_rear_family"}
    ]
    assert len(family_edges) >= 3

    report = run_shadow_adjudication(
        rgb,
        masks,
        ocr_regions=[{
            "id": "mirror-wordmark-1",
            "kind": "sponsor",
            "orientation": "mirror-r90",
            "mirrored": True,
            "bbox": [70, 8, 16, 20],
            "text": "MOTUL",
            "confidence": 0.91,
        }],
    ).to_telemetry()
    assert report["ocr_member_node_count"] == 2
    assert report["ocr_membership_count"] == 2
    assert report["strong_ocr_member_node_count"] == 2
    assert report["mirrored_ocr_membership_count"] == 2
    assert report["ocr_region_count"] == 1
    assert report["mirrored_ocr_region_count"] == 1
    assert report["mirror_only_ocr_region_count"] == 1
    region = report["ocr_region_samples"][0]
    assert region["id"] == "mirror-wordmark-1"
    assert region["bbox"] == [70, 8, 16, 20]
    assert region["polygon_area"] == 320
    assert region["membership_count"] == 2
    assert region["owner_pixels"] == {"paint": 269, "sponsors": 51}
    assert region["covered_fraction"] == 1.0
    assert region["quality_basis"] == "legacy_mirror"
    assert report["ocr_orientation_counts"] == {"mirror-r90": 2}


def test_relationship_votes_need_corroboration_and_classifier_evidence_before_owner_change():
    rgb, masks = _fixture(three_number_anchors=True)
    graph = build_component_graph(rgb, masks)
    sponsor = _node(graph, "sponsors")
    votes = relationship_votes(graph)
    assert any(vote.node_id == sponsor.node_id and vote.owner == "numbers" for vote in votes)

    relationship_only = adjudicate(graph)
    assert relationship_only.decisions[sponsor.index].owner == "sponsors"

    classifier_vote = EvidenceVote(
        node_id=sponsor.node_id,
        owner="numbers",
        weight=0.30,
        source="number_family_classifier",
        reason="digit_core_evidence",
    )
    one_source = adjudicate(graph, [classifier_vote])
    blocked = one_source.decisions[sponsor.index]
    assert blocked.owner == "sponsors"
    assert blocked.raw_owner == "numbers"
    assert blocked.blocked_reason == "insufficient_independent_sources"
    independent_ocr_vote = EvidenceVote(
        node_id=sponsor.node_id,
        owner="numbers",
        weight=0.05,
        source="ocr_digit_anchor",
        reason="recognized_digit",
    )
    corroborated = adjudicate(graph, [classifier_vote, independent_ocr_vote])
    decision = corroborated.decisions[sponsor.index]
    assert decision.source_owner == "sponsors"
    assert decision.owner == "numbers"
    assert decision.changed

    rgb_single, masks_single = _fixture(three_number_anchors=False)
    graph_single = build_component_graph(rgb_single, masks_single)
    sponsor_single = _node(graph_single, "sponsors")
    result_single = adjudicate(graph_single)
    assert result_single.decisions[sponsor_single.index].owner == "sponsors"


def test_sponsor_promotion_also_requires_two_independent_non_relationship_sources():
    height = width = 96
    rgb = np.full((height, width, 3), 32, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    for x, y in ((8, 8), (8, 42), (72, 72)):
        _l_shape(masks["sponsors"], x, y)
    target = np.zeros((height, width), np.uint8)
    _l_shape(target, 72, 10, mirror=True)
    occupied = masks["sponsors"] > 0
    masks["paint"][~occupied] = 255
    rgb[(masks["sponsors"] > 0) | (target > 0)] = np.array([218, 28, 42], np.uint8)
    snapshot = capture_candidate_snapshot(
        {"sponsors": target},
        source_stage="raw_sponsor",
        source="synthetic_detector",
    )
    graph = build_component_graph(rgb, masks, candidate_snapshot=snapshot)
    target_node = next(
        node for node in graph.nodes
        if node.source_owner == "paint"
        and node.area == int(np.count_nonzero(target))
        and node.bbox[0] >= 70
        and node.bbox[1] < 30
    )
    assert target_node.source_owner == "paint"
    assert any(
        vote.node_id == target_node.node_id and vote.owner == "sponsors"
        for vote in relationship_votes(graph)
    )

    legacy_guard = EvidenceVote(
        node_id=target_node.node_id,
        owner="sponsors",
        weight=0.30,
        source="legacy_guard:number_logo_false_positive",
        reason="tiny_dense_logo_fragment",
    )
    one_source = adjudicate(graph, [legacy_guard])
    blocked = one_source.decisions[target_node.index]
    assert blocked.owner == "paint"
    assert blocked.raw_owner == "sponsors"
    assert blocked.blocked_reason == "insufficient_independent_sources"

    independent_text = EvidenceVote(
        node_id=target_node.node_id,
        owner="sponsors",
        weight=0.05,
        source="ocr_wordmark",
        reason="recognized_non_numeric_text",
    )
    corroborated = adjudicate(graph, [legacy_guard, independent_text])
    assert corroborated.decisions[target_node.index].owner == "sponsors"


def test_source_only_adjudication_is_byte_identical():
    rgb, masks = _fixture()
    graph = build_component_graph(rgb, masks)
    result = adjudicate(graph, include_relationship_votes=False)
    materialized = materialize_masks(graph, result.assignments)
    for owner in OWNERS:
        assert np.array_equal(materialized[owner], masks[owner])


def test_existing_guard_mask_becomes_evidence_not_mutation():
    rgb, masks = _fixture(three_number_anchors=False)
    graph = build_component_graph(rgb, masks)
    sponsor = _node(graph, "sponsors")
    guard_mask = np.zeros(graph.shape, np.uint8)
    x, y, width, height = sponsor.bbox
    guard_mask[y:y + height, x:x + width] = 255
    votes = votes_from_mask(
        graph,
        guard_mask,
        "numbers",
        source="legacy_large_number_shell",
        reason="converted_guard_evidence",
        weight=2.0,
    )
    assert len(votes) == 1

    votes += (EvidenceVote(
        node_id=sponsor.node_id,
        owner="numbers",
        weight=0.1,
        source="number_ocr_anchor",
        reason="independent_digit_anchor",
    ),)

    result = adjudicate(graph, votes, include_relationship_votes=False)
    assert result.decisions[sponsor.index].owner == "numbers"
    # The graph's immutable current partition still says Sponsor.
    sample_y, sample_x = np.argwhere(graph.component_map == sponsor.index)[0]
    assert graph.owner_map[sample_y, sample_x] == OWNERS.index("sponsors")


def test_hard_vote_wins_deterministically_and_partition_stays_exclusive():
    rgb, masks = _fixture()
    graph = build_component_graph(rgb, masks)
    sponsor = _node(graph, "sponsors")
    hard = EvidenceVote(
        node_id=sponsor.node_id,
        owner="paint",
        weight=0.1,
        source="safety_contract",
        reason="known_textless_livery",
        hard=True,
    )
    result = adjudicate(graph, [hard])
    assert result.decisions[sponsor.index].owner == "paint"
    proposed = materialize_masks(graph, result.assignments)
    coverage = sum((mask > 0).astype(np.uint8) for mask in proposed.values())
    assert np.all(coverage == 1)


def test_shadow_report_proposes_but_never_applies_or_mutates():
    rgb, masks = _fixture()
    original_rgb = rgb.copy()
    originals = {owner: mask.copy() for owner, mask in masks.items()}
    graph = build_component_graph(rgb, masks)
    sponsor = _node(graph, "sponsors")
    classifier_vote = EvidenceVote(
        node_id=sponsor.node_id,
        owner="numbers",
        weight=0.30,
        source="number_family_classifier",
        reason="digit_core_evidence",
    )
    independent_ocr_vote = EvidenceVote(
        node_id=sponsor.node_id,
        owner="numbers",
        weight=0.05,
        source="ocr_digit_anchor",
        reason="recognized_digit",
    )
    report = run_shadow_adjudication(rgb, masks, votes=[classifier_vote, independent_ocr_vote])
    telemetry = report.to_telemetry()

    assert telemetry["status"] == "shadow"
    assert telemetry["output_applied"] is False
    assert telemetry["changed_node_count"] >= 1
    assert telemetry["xor_pixels"]["numbers"] > 0
    assert np.array_equal(rgb, original_rgb)
    for owner in OWNERS:
        assert np.array_equal(masks[owner], originals[owner])


def test_pre_repair_candidate_boundary_splits_giant_paint_into_stable_atom():
    height = width = 64
    rgb = np.full((height, width, 3), 80, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["paint"][:] = 255
    raw_sponsor = np.zeros((height, width), np.uint8)
    raw_sponsor[18:28, 22:34] = 255
    snapshot = capture_candidate_snapshot(
        {"sponsors": raw_sponsor},
        source_stage="ocr_raw",
        source="synthetic_ocr",
    )

    graph = build_component_graph(rgb, masks, candidate_snapshot=snapshot)
    assert graph.partition_component_count == 1
    assert graph.proposal_split_count >= 1
    candidate_atom = next(
        node for node in graph.nodes
        if node.source_owner == "paint" and node.bbox == (22, 18, 12, 10)
    )
    assert candidate_atom.area == 120
    assert len(candidate_atom.proposal_memberships) == 1
    membership = candidate_atom.proposal_memberships[0]
    assert membership.candidate_id == snapshot.regions[0].candidate_id
    assert membership.proposed_owner == "sponsors"
    assert membership.node_overlap_fraction == pytest.approx(1.0)
    assert membership.proposal_overlap_fraction == pytest.approx(1.0)
    groups = proposal_groups(graph)
    assert len(groups) == 1
    assert groups[0].candidate_id == snapshot.regions[0].candidate_id
    assert groups[0].member_node_ids == (candidate_atom.node_id,)
    assert groups[0].source_owner_counts == (("paint", 1),)
    assert groups[0].bbox == candidate_atom.bbox
    assert groups[0].covered_pixels == 120
    assert snapshot.regions[0].local_mask.flags.writeable is False

    corroborating = capture_mask_evidence(
        raw_sponsor,
        target_owner="sponsors",
        source_stage="classifier_raw",
        source="synthetic_sponsor_classifier",
        reason="text_anatomy",
        weight=0.60,
    )
    report = run_shadow_adjudication(
        rgb,
        masks,
        candidate_snapshot=snapshot,
        mask_evidence=[corroborating],
    )
    telemetry = report.to_telemetry()
    assert telemetry["candidate_evidence"]["region_count"] == 1
    assert telemetry["candidate_evidence"]["decal_instances"]["instance_count"] == 1
    assert telemetry["candidate_evidence"]["decal_instances"]["ownership_authority"] is False
    assert telemetry["candidate_evidence"]["decal_instances"]["features"]["feature_count"] == 1
    assert telemetry["candidate_evidence"]["decal_instances"]["features"]["ownership_authority"] is False
    assert telemetry["candidate_vote_count"] == 1
    assert telemetry["mask_evidence_vote_count"] == 1
    assert telemetry["xor_pixels"]["sponsors"] == 120
    assert telemetry["xor_pixels"]["paint"] == 120
    assert telemetry["output_applied"] is False


def test_replayed_guard_evidence_is_batched_and_cannot_double_vote():
    height = width = 48
    rgb = np.full((height, width, 3), 70, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["paint"][:] = 255
    proposal = np.zeros((height, width), np.uint8)
    proposal[12:20, 14:24] = 255
    snapshot = capture_candidate_snapshot(
        {"sponsors": proposal},
        source_stage="ocr_raw",
        source="synthetic_ocr",
    )
    empty = np.zeros_like(proposal)
    batch = capture_mask_evidence_batch([
        {
            "mask": proposal,
            "target_owner": "sponsors",
            "source_stage": "engine_final",
            "source": "legacy_guard:panel_text_residual",
            "reason": "panel_text_residual",
            "weight": 0.60,
        },
        {
            "mask": proposal,
            "target_owner": "sponsors",
            "source_stage": "route_final",
            "source": "legacy_guard:panel_text_residual",
            "reason": "panel_text_residual",
            "weight": 0.40,
        },
        {
            "mask": empty,
            "target_owner": "numbers",
            "source": "legacy_guard:number_trim_fragment",
        },
    ])
    assert len(batch) == 2
    graph = build_component_graph(rgb, masks, candidate_snapshot=snapshot)
    vote_specs = mask_evidence_vote_specs(graph, batch)
    assert len(vote_specs) == 1
    assert vote_specs[0]["weight"] == pytest.approx(0.60)
    assert len(vote_specs[0]["support"]) == 2

    report = run_shadow_adjudication(
        rgb,
        masks,
        candidate_snapshot=snapshot,
        mask_evidence=batch,
    )
    telemetry = report.to_telemetry()
    assert telemetry["mask_evidence_count"] == 2
    assert telemetry["mask_evidence_vote_count"] == 1
    assert telemetry["mask_evidence"]["source_counts"] == {
        "legacy_guard:panel_text_residual": 2,
    }


def test_feature_gate_defaults_to_shadow_and_refuses_apply(monkeypatch):
    monkeypatch.delenv(ADJUDICATOR_MODE_ENV, raising=False)
    assert get_adjudicator_mode() == "shadow"
    monkeypatch.setenv(ADJUDICATOR_MODE_ENV, "shadow")
    assert get_adjudicator_mode() == "shadow"
    monkeypatch.setenv(ADJUDICATOR_MODE_ENV, "off")
    assert get_adjudicator_mode() == "off"
    monkeypatch.setenv(ADJUDICATOR_MODE_ENV, "apply")
    assert get_adjudicator_mode() == "off"


def test_semantic_family_relabels_only_repeated_flat_dark_nontext_panels_as_evidence():
    height = width = 256
    rgb = np.full((height, width, 3), 190, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["sponsors"][20:44, 18:48] = 255
    masks["sponsors"][172:196, 182:212] = 255
    # Appearance-identical, but OCR membership must veto a true dark wordmark.
    masks["sponsors"][104:128, 112:142] = 255
    rgb[masks["sponsors"] > 0] = np.array([18, 18, 18], np.uint8)
    masks["paint"][masks["sponsors"] == 0] = 255
    graph = build_component_graph(
        rgb,
        masks,
        ocr_regions=[{
            "id": "dark-wordmark",
            "kind": "sponsor",
            "orientation": "r0",
            "mirrored": False,
            "bbox": [112, 104, 30, 24],
        }],
    )

    votes, telemetry = sponsor_semantic_family_votes(graph)
    paint_votes = [vote for vote in votes if vote.owner == "paint"]
    assert len(paint_votes) == 2
    assert {vote.reason for vote in paint_votes} == {
        "repeated_flat_dark_nontext_livery_panel",
    }
    assert telemetry["reason_counts"] == {
        "repeated_flat_dark_nontext_livery_panel": 2,
    }
    protected = next(
        node for node in graph.nodes
        if node.source_owner == "sponsors" and node.ocr_memberships
    )
    assert protected.node_id not in {vote.node_id for vote in votes}


def test_semantic_family_recognizes_only_strict_mirrored_hardware_near_template():
    height = width = 160
    rgb = np.full((height, width, 3), 175, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    for x in (20, 112):
        masks["sponsors"][24:32, x:x + 20] = 255
        masks["template"][34:40, x - 2:x + 22] = 255
    # A matching neutral shape without Template context cannot join the family.
    masks["sponsors"][80:88, 66:86] = 255
    rgb[masks["sponsors"] > 0] = np.array([76, 76, 76], np.uint8)
    rgb[masks["template"] > 0] = np.array([132, 132, 132], np.uint8)
    occupied = (masks["sponsors"] > 0) | (masks["template"] > 0)
    masks["paint"][~occupied] = 255
    graph = build_component_graph(rgb, masks)

    votes, telemetry = sponsor_semantic_family_votes(graph)
    template_votes = [vote for vote in votes if vote.owner == "template"]
    assert len(template_votes) == 2
    assert {vote.reason for vote in template_votes} == {
        "mirrored_neutral_hardware_pair_near_template",
    }
    assert telemetry["target_owner_counts"] == {"template": 2}


def test_semantic_family_recognizes_repeated_paint_palette_livery_surfaces():
    height = width = 256
    rgb = np.full((height, width, 3), 34, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["template"][:] = 255

    # Two separated flat body-color panels incorrectly owned by Sponsors.
    for y, x in ((24, 22), (174, 180)):
        masks["sponsors"][y:y + 24, x:x + 42] = 255
        rgb[y:y + 24, x:x + 42] = np.array([48, 132, 210], np.uint8)

    # Existing Paint palette anchors independently establish body-color
    # ownership. They are separated by Template so each remains a component.
    for y, x in ((88, 24), (116, 188)):
        masks["paint"][y:y + 18, x:x + 42] = 255
        rgb[y:y + 18, x:x + 42] = np.array([48, 132, 210], np.uint8)

    # Appearance-identical but OCR-covered Sponsor content must stay protected.
    masks["sponsors"][100:124, 94:136] = 255
    rgb[100:124, 94:136] = np.array([48, 132, 210], np.uint8)
    occupied = (masks["sponsors"] > 0) | (masks["paint"] > 0)
    masks["template"][occupied] = 0

    graph = build_component_graph(
        rgb,
        masks,
        ocr_regions=[{
            "id": "flat-sponsor-badge",
            "kind": "sponsor",
            "orientation": "r0",
            "mirrored": False,
            "bbox": [94, 100, 42, 24],
        }],
    )
    votes, telemetry = sponsor_semantic_family_votes(graph)
    livery_votes = [
        vote for vote in votes
        if vote.reason == "repeated_paint_palette_livery_surface"
    ]
    assert len(livery_votes) == 2
    assert {vote.owner for vote in livery_votes} == {"paint"}
    assert telemetry["reason_counts"]["repeated_paint_palette_livery_surface"] == 2
    protected = next(
        node for node in graph.nodes
        if node.source_owner == "sponsors" and node.ocr_memberships
    )
    assert protected.node_id not in {vote.node_id for vote in livery_votes}


def test_semantic_family_does_not_invent_livery_surface_without_repeat_or_paint_anchor():
    height = width = 192
    rgb = np.full((height, width, 3), 30, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["template"][:] = 255
    masks["sponsors"][20:42, 18:54] = 255
    masks["sponsors"][128:150, 132:168] = 255
    rgb[masks["sponsors"] > 0] = np.array([42, 118, 205], np.uint8)
    # A Paint component exists, but its palette is deliberately unrelated.
    masks["paint"][78:98, 74:118] = 255
    rgb[masks["paint"] > 0] = np.array([210, 52, 45], np.uint8)
    masks["template"][(masks["sponsors"] > 0) | (masks["paint"] > 0)] = 0

    graph = build_component_graph(rgb, masks)
    votes, telemetry = sponsor_semantic_family_votes(graph)
    assert not any(
        vote.reason == "repeated_paint_palette_livery_surface" for vote in votes
    )
    assert "repeated_paint_palette_livery_surface" not in telemetry["reason_counts"]


def test_semantic_family_uses_template_context_to_resolve_repeated_dark_hardware():
    height = width = 256
    rgb = np.full((height, width, 3), 180, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    for x in (24, 184):
        masks["sponsors"][30:54, x:x + 30] = 255
        masks["template"][56:68, x - 2:x + 32] = 255
    rgb[masks["sponsors"] > 0] = np.array([16, 16, 16], np.uint8)
    rgb[masks["template"] > 0] = np.array([110, 110, 110], np.uint8)
    occupied = (masks["sponsors"] > 0) | (masks["template"] > 0)
    masks["paint"][~occupied] = 255

    graph = build_component_graph(rgb, masks)
    votes, telemetry = sponsor_semantic_family_votes(graph)
    contextual = [
        vote for vote in votes
        if vote.reason == "repeated_flat_dark_nontext_hardware_near_template"
    ]
    assert len(contextual) == 2
    assert {vote.owner for vote in contextual} == {"template"}
    assert telemetry["target_owner_counts"]["template"] >= 2


def test_semantic_family_recognizes_repeated_diagonal_carbon_weave_as_hardware():
    height = width = 512
    rgb = np.full((height, width, 3), 180, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    local = np.ones((28, 38), bool)
    local[5:10, 8:30] = False
    local[16:21, 8:30] = False
    yy, xx = np.indices(local.shape)
    weave = np.where(((xx + yy) // 2) % 2, 88, 18).astype(np.uint8)
    for x, y in ((42, 48), (392, 406)):
        view = masks["sponsors"][y:y + 28, x:x + 38]
        view[local] = 255
        rgb_view = rgb[y:y + 28, x:x + 38]
        rgb_view[local] = np.repeat(weave[:, :, None], 3, axis=2)[local]
    masks["paint"][masks["sponsors"] == 0] = 255

    graph = build_component_graph(rgb, masks)
    votes, telemetry = sponsor_semantic_family_votes(graph)
    carbon_votes = [
        vote for vote in votes
        if vote.reason == "repeated_diagonal_carbon_weave_hardware"
    ]
    assert len(carbon_votes) == 2
    assert {vote.owner for vote in carbon_votes} == {"template"}
    assert all(vote.support for vote in carbon_votes)
    assert telemetry["reason_counts"]["repeated_diagonal_carbon_weave_hardware"] == 2

    report = run_shadow_adjudication(rgb, masks)
    shadow = report.to_telemetry()
    assert shadow["semantic_family_vote_count"] == 2
    assert shadow["changed_node_count"] == 0
    assert all(value == 0 for value in shadow["xor_pixels"].values())
    canary = shadow["evidence_canary"]
    assert canary["status"] == "simulated"
    assert canary["output_applied"] is False
    assert canary["changed_node_count"] == 2
    assert canary["changed_pixel_count"] > 0
    assert canary["reason_counts"] == {
        "repeated_diagonal_carbon_weave_hardware": 2,
    }
    assert canary["transition_pixels"]["sponsors->template"] == canary["changed_pixel_count"]
    assert canary["xor_pixels"]["sponsors"] == canary["changed_pixel_count"]
    assert canary["xor_pixels"]["template"] == canary["changed_pixel_count"]
    assert canary["hard_partition"] is True
    assert canary["reconstruction_mismatch_pixels"] == 0
    assert canary["rollback_exact"] is True
    assert all(value == 0 for value in canary["rollback_xor_pixels"].values())

    empty_canary = simulate_evidence_canary(
        report.graph,
        report.semantic_family_votes,
        reasons=("not_this_family",),
    )
    assert empty_canary["changed_node_count"] == 0
    assert empty_canary["rollback_exact"] is True

    conflict_node = graph.node_by_id[carbon_votes[0].node_id]
    conflict_canary = simulate_evidence_canary(graph, (
        EvidenceVote(
            node_id=conflict_node.node_id, owner="template", weight=0.8,
            source="family:a", reason="conflict_a",
        ),
        EvidenceVote(
            node_id=conflict_node.node_id, owner="paint", weight=0.8,
            source="family:b", reason="conflict_b",
        ),
    ))
    assert conflict_canary["conflict_node_count"] == 1
    assert conflict_canary["changed_node_count"] == 0
    assert conflict_canary["conflicts"][0]["proposed_owners"] == ["paint", "template"]
    assert conflict_canary["rollback_exact"] is True
    assert all(value == 0 for value in conflict_canary["xor_pixels"].values())


def test_semantic_family_completes_only_repeated_embedded_sponsor_badge_inlays():
    height = width = 512
    rgb = np.full((height, width, 3), 42, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    inlay_boxes = []
    for x, y in ((54, 62), (414, 418)):
        # Compact multicolor Sponsor container surrounding a disconnected dark
        # glyph inlay that legacy ownership left in Paint.
        masks["sponsors"][y:y + 28, x:x + 28] = 255
        masks["sponsors"][y + 5:y + 23, x + 5:x + 23] = 0
        inlay = masks["paint"][y + 6:y + 22, x + 6:x + 22]
        inlay[:] = 255
        inlay[:2, :2] = inlay[:2, -2:] = 0
        inlay[-2:, :2] = inlay[-2:, -2:] = 0
        inlay_boxes.append((x + 6, y + 6, 16, 16))
        outer = masks["sponsors"][y:y + 28, x:x + 28] > 0
        local = rgb[y:y + 28, x:x + 28]
        yy, xx = np.indices((28, 28))
        local[outer] = np.where(((xx + yy) % 4 < 2)[outer, None], 238, 72)
        inner = rgb[y + 6:y + 22, x + 6:x + 22]
        inner[:] = 18
        inner[:, 5:7] = 220
        inner[:, 10:12] = 220
    occupied = (masks["sponsors"] > 0) | (masks["paint"] > 0)
    masks["template"][~occupied] = 255

    graph = build_component_graph(rgb, masks, pair_budget=100000)
    votes, telemetry = sponsor_semantic_family_votes(graph)
    recovered = [
        vote for vote in votes
        if vote.reason == "repeated_embedded_sponsor_badge_inlay"
    ]
    assert len(recovered) == 2
    recovered_nodes = [graph.node_by_id[vote.node_id] for vote in recovered]
    assert {node.source_owner for node in recovered_nodes} == {"paint"}
    assert {node.bbox for node in recovered_nodes} == set(inlay_boxes)
    assert all(vote.owner == "sponsors" and len(vote.support) == 2 for vote in recovered)
    assert telemetry["reason_counts"]["repeated_embedded_sponsor_badge_inlay"] == 2

    report = run_shadow_adjudication(
        rgb, {owner: mask.copy() for owner, mask in masks.items()}, pair_budget=100000
    )
    shadow = report.to_telemetry()
    assert all(value == 0 for value in shadow["xor_pixels"].values())
    inlay_canary = simulate_evidence_canary(
        report.graph,
        report.semantic_family_votes,
        reasons=("repeated_embedded_sponsor_badge_inlay",),
    )
    assert inlay_canary["changed_node_count"] == 2
    assert inlay_canary["transition_pixels"]["paint->sponsors"] == 480
    assert inlay_canary["rollback_exact"] is True

    # A lone embedded dark atom has containment but no repeated-family proof.
    masks["paint"][inlay_boxes[1][1]:inlay_boxes[1][1] + 16,
                   inlay_boxes[1][0]:inlay_boxes[1][0] + 16] = 0
    masks["template"][inlay_boxes[1][1]:inlay_boxes[1][1] + 16,
                      inlay_boxes[1][0]:inlay_boxes[1][0] + 16] = 255
    single_graph = build_component_graph(rgb, masks, pair_budget=100000)
    single_votes, _single_telemetry = sponsor_semantic_family_votes(single_graph)
    assert not any(
        vote.reason == "repeated_embedded_sponsor_badge_inlay"
        for vote in single_votes
    )

def test_semantic_family_uses_sponsor_ocr_anchor_and_shape_to_recover_mirrored_wordmark():
    height = width = 256
    rgb = np.full((height, width, 3), 28, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    _l_shape(masks["sponsors"], 20, 24)
    _l_shape(masks["paint"], 218, 210, mirror=True)
    occupied = (masks["sponsors"] > 0) | (masks["paint"] > 0)
    masks["template"][~occupied] = 255
    rgb[masks["sponsors"] > 0] = np.array([230, 230, 230], np.uint8)
    rgb[masks["paint"] > 0] = np.array([230, 230, 230], np.uint8)

    ocr_regions = [{
        "id": "wordmark-anchor",
        "kind": "sponsor",
        "orientation": "upright",
        "mirrored": False,
        "bbox": [20, 24, 10, 14],
        "text": "McLaren",
        "confidence": 0.94,
    }, {
        "id": "wordmark-mirrored-copy",
        "kind": "sponsor",
        "orientation": "mirror-r180",
        "mirrored": True,
        "bbox": [218, 210, 10, 14],
        "text": "McLaren",
        "confidence": 0.91,
    }]
    graph = build_component_graph(rgb, masks, ocr_regions=ocr_regions)
    votes, telemetry = sponsor_semantic_family_votes(graph)
    recovered = [
        vote for vote in votes
        if vote.reason == "repeated_ocr_anchor_wordmark_family"
    ]

    assert len(recovered) == 1
    target = graph.node_by_id[recovered[0].node_id]
    assert target.source_owner == "paint"
    assert recovered[0].owner == "sponsors"
    assert recovered[0].support
    assert telemetry["reason_counts"]["repeated_ocr_anchor_wordmark_family"] == 1

    anchor_only = build_component_graph(rgb, masks, ocr_regions=ocr_regions[:1])
    unsafe_votes, _unsafe_telemetry = sponsor_semantic_family_votes(anchor_only)
    assert not any(
        vote.reason == "repeated_ocr_anchor_wordmark_family"
        for vote in unsafe_votes
    )

    report = run_shadow_adjudication(rgb, masks, ocr_regions=ocr_regions)
    canary = report.to_telemetry()["evidence_canary"]
    assert canary["changed_node_count"] == 1
    assert canary["transition_pixels"]["paint->sponsors"] == target.area
    assert canary["rollback_exact"] is True


def test_semantic_family_is_shadow_only_and_preserves_exact_output():
    height = width = 256
    rgb = np.full((height, width, 3), 200, np.uint8)
    masks = {owner: np.zeros((height, width), np.uint8) for owner in OWNERS}
    masks["sponsors"][16:40, 12:42] = 255
    masks["sponsors"][188:212, 202:232] = 255
    rgb[masks["sponsors"] > 0] = np.array([20, 20, 20], np.uint8)
    masks["paint"][masks["sponsors"] == 0] = 255

    report = run_shadow_adjudication(rgb, masks)
    telemetry = report.to_telemetry()
    assert telemetry["semantic_family_vote_count"] == 2
    assert telemetry["semantic_family"]["target_owner_counts"] == {"paint": 2}
    assert telemetry["changed_node_count"] == 0
    assert all(value == 0 for value in telemetry["xor_pixels"].values())
    assert telemetry["output_applied"] is False


def test_run_shadow_if_enabled_has_instant_fallback(monkeypatch):
    rgb, masks = _fixture()
    monkeypatch.delenv(ADJUDICATOR_MODE_ENV, raising=False)
    shadow = run_shadow_if_enabled(rgb, masks)
    assert shadow["status"] == "shadow"
    assert shadow["output_applied"] is False

    monkeypatch.setenv(ADJUDICATOR_MODE_ENV, "off")
    off = run_shadow_if_enabled(rgb, masks)
    assert off == {
        "status": "off",
        "mode": "off",
        "schema": "smart-tga-component-evidence-v1",
        "output_applied": False,
    }
    monkeypatch.setenv(ADJUDICATOR_MODE_ENV, "shadow")
    explicit_shadow = run_shadow_if_enabled(rgb, masks)
    assert explicit_shadow["status"] == "shadow"
    assert explicit_shadow["output_applied"] is False


def test_number_map_family_runtime_is_telemetry_only_and_fail_closed(monkeypatch):
    from engine.spec_sculpt import number_map_family_shadow

    rgb, masks = _fixture()
    before = {owner: mask.copy() for owner, mask in masks.items()}
    monkeypatch.delenv(NUMBER_MAP_FAMILY_SHADOW_ENV, raising=False)
    disabled = run_shadow_adjudication(rgb, masks).to_telemetry()["number_map_families"]
    assert disabled["status"] == "disabled"
    assert disabled["casts_votes"] is False
    assert disabled["ownership_authority"] is False

    def fake_shadow(_rgb, _masks, *, ocr_regions=()):
        assert not ocr_regions
        return {
            "status": "shadow_only", "family_count": 2,
            "accepted_family_count": 1, "casts_votes": False,
            "ownership_authority": False, "adds_pixels": False,
            "output_applied": False,
        }

    monkeypatch.setattr(number_map_family_shadow, "number_map_family_shadow_telemetry", fake_shadow)
    monkeypatch.setenv(NUMBER_MAP_FAMILY_SHADOW_ENV, "shadow")
    telemetry = run_shadow_adjudication(rgb, masks).to_telemetry()
    assert telemetry["number_map_families"]["accepted_family_count"] == 1
    assert telemetry["number_map_families"]["output_applied"] is False
    assert telemetry["output_applied"] is False
    assert all(np.array_equal(masks[owner], before[owner]) for owner in masks)


def test_number_proposal_group_defaults_to_shadow_with_instant_fallback(monkeypatch):
    rgb, masks = _fixture()
    monkeypatch.delenv(NUMBER_PROPOSAL_GROUP_ENV, raising=False)
    default = run_shadow_adjudication(rgb, masks).to_telemetry()
    assert default["semantic_family"]["number_proposal_group"].get("status") != (
        "experimental_disabled"
    )

    monkeypatch.setenv(NUMBER_PROPOSAL_GROUP_ENV, "0")
    fallback = run_shadow_adjudication(rgb, masks).to_telemetry()
    assert fallback["semantic_family"]["number_proposal_group"]["status"] == (
        "experimental_disabled"
    )


def test_car_layers_final_boundary_shadow_hook_is_byte_identical(monkeypatch):
    from engine.spec_sculpt.car_layers import separate_into_layers

    rgb = np.full((64, 64, 3), 120, np.uint8)
    monkeypatch.setenv(ADJUDICATOR_MODE_ENV, "off")
    current = separate_into_layers(
        rgb,
        auto_id=False,
        use_template=False,
        use_ocr=False,
        brand_graphics_merge="paint",
    )
    monkeypatch.setenv(ADJUDICATOR_MODE_ENV, "shadow")
    shadowed = separate_into_layers(
        rgb,
        auto_id=False,
        use_template=False,
        use_ocr=False,
        brand_graphics_merge="paint",
    )

    assert current["adjudicator_shadow"]["status"] == "off"
    assert shadowed["adjudicator_shadow"]["status"] == "shadow"
    assert shadowed["adjudicator_shadow"]["output_applied"] is False
    for owner in OWNERS:
        assert np.array_equal(current["layers"][owner], shadowed["layers"][owner])

    with_context = separate_into_layers(
        rgb,
        auto_id=False,
        use_template=False,
        use_ocr=False,
        brand_graphics_merge="paint",
        include_adjudicator_context=True,
    )
    assert "_adjudicator_context" in with_context
    assert "_adjudicator_context" not in shadowed
    assert with_context["_adjudicator_context"]["candidate_snapshot"].shape == (64, 64)


def test_component_evidence_is_mirrored_manifest_managed_and_context_indexed():
    relative = "engine/spec_sculpt/component_evidence.py"
    candidate_relative = "engine/spec_sculpt/candidate_evidence.py"
    gpu_bridge_relative = "engine/spec_sculpt/smart_tga_gpu_bridge.py"
    manifest = json.loads((REPO_ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8"))
    assert relative in manifest["files"]
    assert candidate_relative in manifest["files"]
    assert gpu_bridge_relative in manifest["files"]
    root_bytes = (REPO_ROOT / relative).read_bytes()
    mirror_bytes = (REPO_ROOT / "electron-app" / "server" / relative).read_bytes()
    assert root_bytes == mirror_bytes
    candidate_root_bytes = (REPO_ROOT / candidate_relative).read_bytes()
    candidate_mirror_bytes = (REPO_ROOT / "electron-app" / "server" / candidate_relative).read_bytes()
    assert candidate_root_bytes == candidate_mirror_bytes
    gpu_root_bytes = (REPO_ROOT / gpu_bridge_relative).read_bytes()
    gpu_mirror_bytes = (REPO_ROOT / "electron-app" / "server" / gpu_bridge_relative).read_bytes()
    assert gpu_root_bytes == gpu_mirror_bytes

    context = json.loads((REPO_ROOT / "scripts" / "spb_context_targets.json").read_text(encoding="utf-8"))
    target = context["targets"]["smart-tga-adjudicator"]
    assert target["domain"] == "smart-tga"
    assert any(slice_spec[0] == relative for slice_spec in target["slices"])
    assert any(slice_spec[0] == candidate_relative for slice_spec in target["slices"])


def test_gpu_bridge_cache_roundtrip_preserves_ocr_provenance(tmp_path):
    from engine.spec_sculpt import smart_tga_gpu_bridge as gpu_bridge

    source = tmp_path / "source"
    cache = tmp_path / "cache"
    source.mkdir()
    mask = np.zeros((16, 16), np.uint8)
    mask[2:8, 3:11] = 255
    for owner in ("numbers", "text", "logos", "paint"):
        Image.fromarray(mask, "L").save(source / f"{owner}.png")
    regions = [{
        "id": "gpu-word-0",
        "kind": "sponsor",
        "orientation": "multi_rotation",
        "mirrored": False,
        "bbox": [3, 2, 8, 6],
        "polygon": [[3, 2], [11, 2], [11, 8], [3, 8]],
        "text": "MOTUL",
        "confidence": 0.93,
        "source": "easyocr_gpu",
        "cross_view_exact": True,
        "repeated_mirror_family": False,
        "quality_basis": "cross_view_exact",
    }]
    (source / "ocr_regions.json").write_text(json.dumps({
        "shape": [32, 32],
        "regions": regions,
    }), encoding="utf-8")

    gpu_bridge._write_cached_masks(cache, source)
    restored = gpu_bridge._read_cached_masks(cache, (16, 16))
    assert restored is not None
    assert restored["_ocr_regions"][0]["bbox"] == [2, 1, 4, 3]
    assert restored["_ocr_regions"][0]["polygon"] == [
        [1.5, 1.0], [5.5, 1.0], [5.5, 4.0], [1.5, 4.0],
    ]
    assert restored["_ocr_regions"][0]["text"] == "MOTUL"
    assert restored["_ocr_regions"][0]["confidence"] == 0.93
    assert restored["_ocr_regions"][0]["source"] == "easyocr_gpu"
    assert restored["_ocr_regions"][0]["quality_basis"] == "cross_view_exact"
    assert np.array_equal(restored["text"], mask)


def test_gpu_worker_mirror_ocr_is_provenance_only_and_reversible():
    source = (REPO_ROOT / "_separate_image.py").read_text(encoding="utf-8")
    assert '"SEP_MIRROR_OCR", os.environ.get("SPB_SMART_TGA_MIRROR_OCR", "1")' in source
    assert 'SEP_MIRROR_OCR_SCALE", "1.0"' in source
    assert 'SEP_MIRROR_OCR_ALLOW_SINGLETON", "0"' in source
    assert "MIRROR_OCR_ALLOW_SINGLETON\n            and item[\"confidence\"]" in source
    assert "_LAST_MIRROR_WORD_REGIONS = _read_mirror_word_regions(rgb, scale=MIRROR_OCR_SCALE)" in source
    assert '"mirrored": True' in source
    assert '"source": "easyocr_gpu_mirror"' in source
    assert 'SEP_MIRROR_OCR_BROAD_MAX_DIM' in source
    assert 'SEP_MIRROR_OCR_BROAD_MIN_CONF' in source
    assert 'SEP_MIRROR_OCR_SINGLETON_MIN_CONF' in source
    assert '"cross_view_exact" if cross_view_exact' in source
    assert '"repeated_mirror_family" if repeated_mirror_family' in source
    classification_end = source.index("_LAST_WORD_TEXT_BOXES = word_text")
    mirror_start = source.index("_LAST_MIRROR_WORD_REGIONS = _read_mirror_word_regions(rgb, scale=MIRROR_OCR_SCALE)")
    return_masks = source.index("return digit, word", classification_end)
    assert classification_end < mirror_start < return_masks
