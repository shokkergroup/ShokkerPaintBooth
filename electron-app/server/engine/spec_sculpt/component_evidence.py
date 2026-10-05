"""Immutable evidence graph for Smart TGA ownership adjudication.

This module is the convergence seam after Smart TGA Cycles 603/604.  The
legacy separator contains valuable accumulated classifier knowledge, but many
helpers directly move pixels and are replayed at multiple pipeline phases.
Here, masks are normalized once into immutable component nodes; relationships
and classifier outputs become evidence votes; ownership is resolved once.

The first integration phase is deliberately SHADOW ONLY.  Nothing in this
module mutates the caller's masks, and ``SPB_SMART_TGA_ADJUDICATOR_MODE`` only
accepts ``off`` (default) or ``shadow``.  There is intentionally no apply mode
until corpus evidence and the full Smart TGA suite authorize it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - shipped runtime includes OpenCV
    cv2 = None


SCHEMA_VERSION = "smart-tga-component-evidence-v1"
ADJUDICATOR_MODE_ENV = "SPB_SMART_TGA_ADJUDICATOR_MODE"
PAIR_BUDGET_ENV = "SPB_SMART_TGA_PAIR_BUDGET"
SPONSOR_NUMBER_RECOVERY_ENV = "SPB_SMART_TGA_SPONSOR_NUMBER_RECOVERY"
NUMBER_PROPOSAL_GROUP_ENV = "SPB_SMART_TGA_NUMBER_PROPOSAL_GROUP"
VISUAL_INSTANCE_SHADOW_ENV = "SPB_SMART_TGA_VISUAL_INSTANCE_SHADOW"
INSTANCE_FEATURE_EXPORT_ENV = "SPB_SMART_TGA_INSTANCE_FEATURE_EXPORT"
NUMBER_FAMILY_MODEL_SHADOW_ENV = "SPB_SMART_TGA_NUMBER_FAMILY_MODEL_SHADOW"
NUMBER_MAP_FAMILY_SHADOW_ENV = "SPB_SMART_TGA_NUMBER_MAP_FAMILY_SHADOW"
NUMBER_CONTEXT_SHADOW_ENV = "SPB_SMART_TGA_NUMBER_CONTEXT_SHADOW"
NUMBER_CONTEXT_SEMANTIC_SHADOW_ENV = "SPB_SMART_TGA_NUMBER_CONTEXT_SEMANTIC_SHADOW"
NUMBER_CONTEXT_POSITION_SHADOW_ENV = "SPB_SMART_TGA_NUMBER_CONTEXT_POSITION_SHADOW"
TEMPLATE_POSITION_SHADOW_ENV = "SPB_SMART_TGA_TEMPLATE_POSITION_SHADOW"
TEMPLATE_POSITION_MAP_ENV = "SPB_SMART_TGA_TEMPLATE_POSITION_MAP"
OWNERS = ("numbers", "sponsors", "template", "brand_graphics", "paint")
# Matches the production route and ``_enforce_smart_tga_layer_priority``.
OWNERSHIP_PRIORITY = ("numbers", "template", "sponsors", "brand_graphics", "paint")
PROPAGATING_OWNERS = frozenset(("numbers", "sponsors", "template"))
MIN_INDEPENDENT_SOURCES_FOR_SOFT_CHANGE = 2
_OWNER_INDEX = {owner: index for index, owner in enumerate(OWNERS)}
_PRIORITY_INDEX = {owner: index for index, owner in enumerate(OWNERSHIP_PRIORITY)}
_FALSE_VALUES = frozenset(("", "0", "false", "off", "no", "none"))
_SHADOW_VALUES = frozenset(("1", "true", "on", "yes", "shadow"))
_SHAPE_SIDE = 12
try:
    DEFAULT_PAIR_BUDGET = max(1, int(os.environ.get(PAIR_BUDGET_ENV, "360000")))
except (TypeError, ValueError):
    DEFAULT_PAIR_BUDGET = 360_000


def _readonly_copy(array: np.ndarray, dtype: np.dtype | type | None = None) -> np.ndarray:
    out = np.array(array, dtype=dtype, copy=True, order="C")
    out.setflags(write=False)
    return out


@dataclass(frozen=True)
class OcrMembership:
    region_id: str
    kind: str
    orientation: str
    mirrored: bool
    text: str
    word_family: str
    confidence: float
    text_quality: float
    overlap_fraction: float
    region_coverage_fraction: float


@dataclass(frozen=True)
class OcrRegionEvidence:
    region_id: str
    kind: str
    orientation: str
    mirrored: bool
    text: str
    word_family: str
    confidence: float
    text_quality: float
    bbox: tuple[int, int, int, int]
    area: int
    polygon: tuple[tuple[float, float], ...]
    cross_view_exact: bool = False
    repeated_mirror_family: bool = False
    quality_basis: str = "untyped"


@dataclass(frozen=True)
class _AtomBoundary:
    bbox: tuple[int, int, int, int]
    local_mask: np.ndarray = field(repr=False, compare=False)


def _is_strong_ocr_membership(membership: OcrMembership) -> bool:
    return bool(
        membership.confidence >= 0.38
        and membership.text_quality >= 0.45
        and len(membership.word_family) >= 2
        and (
            membership.overlap_fraction >= 0.12
            or membership.region_coverage_fraction >= 0.30
        )
    )


def _has_strong_ocr(node: "ComponentNode") -> bool:
    """True only when OCR meaningfully covers a node or its detected word box."""
    return any(_is_strong_ocr_membership(item) for item in node.ocr_memberships)


def _has_strong_alpha_ocr(node: "ComponentNode") -> bool:
    """Protect strong wordmarks without treating digit OCR as Sponsor proof."""
    return any(
        _is_strong_ocr_membership(item)
        and any(character.isalpha() for character in (item.text or item.word_family))
        for item in node.ocr_memberships
    )


@dataclass(frozen=True)
class NumberFamilySignals:
    """Scale-invariant Number-family protection and wordmark evidence."""

    anchor_labels: tuple[int, ...] = ()
    protected_labels: frozenset[int] = frozenset()
    wordmark_labels: frozenset[int] = frozenset()


@dataclass(frozen=True)
class ProposalMembership:
    """Immutable overlap between one ownership atom and one raw proposal."""

    candidate_id: str
    proposed_owner: str
    source_stage: str
    source: str
    confidence: float
    node_overlap_fraction: float
    proposal_overlap_fraction: float


@dataclass(frozen=True)
class ComponentNode:
    node_id: str
    index: int
    source_owner: str
    bbox: tuple[int, int, int, int]
    area: int
    area_fraction: float
    centroid: tuple[float, float]
    fill_ratio: float
    aspect_ratio: float
    mean_rgb: tuple[float, float, float]
    std_rgb: tuple[float, float, float]
    mean_hsv: tuple[float, float, float]
    white_fraction: float
    dark_fraction: float
    colored_fraction: float
    edge_density: float
    strong_gradient_fraction: float
    diagonal_gradient_fraction: float
    axis_gradient_fraction: float
    palette_descriptor: tuple[float, ...] = field(repr=False)
    shape_descriptor: tuple[float, ...] = field(repr=False)
    ocr_memberships: tuple[OcrMembership, ...] = ()
    proposal_memberships: tuple[ProposalMembership, ...] = ()


@dataclass(frozen=True)
class RelationshipEdge:
    left: str
    right: str
    kinds: tuple[str, ...]
    distance: float
    containment: float
    palette_similarity: float
    shape_similarity: float
    mirror_similarity: float
    rotation180_similarity: float

    @property
    def family_strength(self) -> float:
        return max(self.shape_similarity, self.mirror_similarity, self.rotation180_similarity)


@dataclass(frozen=True)
class EvidenceVote:
    node_id: str
    owner: str
    weight: float
    source: str
    reason: str
    hard: bool = False
    support: tuple[str, ...] = ()


@dataclass(frozen=True)
class NodeDecision:
    node_id: str
    source_owner: str
    owner: str
    confidence: float
    margin: float
    scores: tuple[tuple[str, float], ...]
    raw_owner: str
    blocked_reason: str | None = None
    votes: tuple[EvidenceVote, ...] = field(default_factory=tuple, repr=False)

    @property
    def changed(self) -> bool:
        return self.owner != self.source_owner

    @property
    def blocked(self) -> bool:
        return bool(self.blocked_reason) and self.raw_owner != self.source_owner and not self.changed


@dataclass(frozen=True)
class ProposalGroup:
    candidate_id: str
    proposed_owner: str
    source_stage: str
    source: str
    confidence: float
    member_node_ids: tuple[str, ...]
    source_owner_counts: tuple[tuple[str, int], ...]
    bbox: tuple[int, int, int, int]
    covered_pixels: int


@dataclass(frozen=True)
class ProposalFamily:
    """Related raw proposals joined without changing component ownership."""

    family_id: str
    proposed_owner: str
    candidate_ids: tuple[str, ...]
    member_node_ids: tuple[str, ...]
    anchor_node_ids: tuple[str, ...]
    candidate_node_ids: tuple[str, ...]
    relationship_pairs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class NumberAnchorGroup:
    """One local decal-scale composite of immutable owned Number atoms."""

    group_id: str
    member_node_ids: tuple[str, ...]
    bbox: tuple[int, int, int, int]
    area: int
    shape_descriptor: tuple[float, ...] = field(repr=False)
    palette_descriptor: tuple[float, ...] = field(repr=False)


@dataclass(frozen=True)
class EvidenceGraph:
    shape: tuple[int, int]
    nodes: tuple[ComponentNode, ...]
    edges: tuple[RelationshipEdge, ...]
    component_map: np.ndarray = field(repr=False, compare=False)
    owner_map: np.ndarray = field(repr=False, compare=False)
    ocr_regions: tuple[OcrRegionEvidence, ...] = ()
    pair_candidates: int = 0
    pair_truncated: bool = False
    partition_component_count: int = 0
    proposal_split_count: int = 0
    proposal_split_truncated: bool = False

    def __post_init__(self) -> None:
        component_map = _readonly_copy(self.component_map, np.int32)
        owner_map = _readonly_copy(self.owner_map, np.int8)
        if component_map.shape != self.shape or owner_map.shape != self.shape:
            raise ValueError("graph maps must match graph shape")
        object.__setattr__(self, "component_map", component_map)
        object.__setattr__(self, "owner_map", owner_map)

    @property
    def node_by_id(self) -> Mapping[str, ComponentNode]:
        return {node.node_id: node for node in self.nodes}


def visual_instance_node_telemetry(
    graph: EvidenceGraph,
    match: Any,
    *,
    min_pixels: int = 20,
) -> Mapping[str, Any]:
    """Project accepted visual geometry onto existing nodes without voting."""
    from engine.spec_sculpt.decal_instances import visual_match_component_overlaps

    nodes_by_index = {node.index: node for node in graph.nodes}
    mapped = []
    for overlap in visual_match_component_overlaps(
        match, graph.component_map, min_pixels=min_pixels
    ):
        node = nodes_by_index.get(overlap.component_index)
        if node is None:
            continue
        mapped.append({
            "node": node.node_id,
            "source_owner": node.source_owner,
            "bbox": list(node.bbox),
            "matched_pixels": overlap.matched_pixels,
            "polygon_fraction": overlap.polygon_fraction,
            "node_fraction": overlap.component_fraction,
        })
    return {
        "source_bbox": list(match.source_bbox),
        "match_bbox": list(match.bbox),
        "good_match_count": int(match.good_match_count),
        "inlier_count": int(match.inlier_count),
        "inlier_ratio": float(match.inlier_ratio),
        "nodes": mapped,
        "casts_votes": False,
        "ownership_authority": False,
    }


def _independent_visual_seed(group: ProposalGroup) -> tuple[bool, str]:
    """Require raw detector authority before a Number proposal seeds vision."""
    if group.proposed_owner != "numbers":
        return False, "not_number_proposal"
    if group.confidence < 0.70:
        return False, "low_proposal_confidence"
    _x, _y, width, height = group.bbox
    if width < 24 or height < 24 or group.covered_pixels < 64:
        return False, "seed_too_small"
    # Compact multi-digit decals remain fairly block-like.  A shallow raw
    # Number proposal with extreme horizontal aspect is instead the recurring
    # DLM wordmark failure (for example K&H Trucking / BACKDRAFT).  Rejecting
    # that geometry here prevents repetition from laundering a text strip into
    # Number evidence; the visual collector remains telemetry-only either way.
    if height <= 32 and (float(width) / max(1.0, float(height))) >= 2.60:
        return False, "thin_textline_geometry"
    provenance = f"{group.source_stage} {group.source}".strip().lower()
    if not provenance:
        return False, "missing_provenance"
    if any(token in provenance for token in (
        "repair", "final", "current_partition", "materialized", "adjudicat",
    )):
        return False, "circular_provenance"
    if not any(token in provenance for token in ("raw", "detector", "model", "proposal")):
        return False, "not_raw_detector_provenance"
    return True, "authorized_raw_number_proposal"


def visual_instance_shadow_telemetry(
    rgb: np.ndarray,
    graph: EvidenceGraph,
    *,
    max_seeds: int = 12,
    min_component_pixels: int = 20,
) -> Mapping[str, Any]:
    """Search raw-authorized Number proposals for repeated visual instances.

    This collector is deliberately telemetry-only.  Proposal provenance, not
    current ownership, authorizes each seed; visual similarity can then expose
    a relationship but can never manufacture an ownership vote.
    """
    from engine.spec_sculpt.decal_instances import (
        build_visual_feature_index,
        find_visual_instance_match,
    )

    groups = proposal_groups(graph)
    rejected: Counter[str] = Counter()
    rejected_samples = []
    seeds = []
    for group in groups:
        authorized, reason = _independent_visual_seed(group)
        if authorized:
            seeds.append(group)
        elif group.proposed_owner == "numbers":
            rejected[reason] += 1
            if len(rejected_samples) < max(12, int(max_seeds)):
                rejected_samples.append({
                    "candidate_id": group.candidate_id,
                    "bbox": list(group.bbox),
                    "reason": reason,
                    "confidence": round(group.confidence, 6),
                    "covered_pixels": group.covered_pixels,
                })
    seeds.sort(key=lambda item: (-item.confidence, -item.covered_pixels, item.candidate_id))
    seeds = seeds[:max(0, int(max_seeds))]
    if not seeds:
        return {
            "status": "abstained", "reason": "no_authorized_number_proposal",
            "seed_count": 0, "match_count": 0, "matches": [],
            "rejected_seed_reasons": dict(sorted(rejected.items())),
            "rejected_seed_samples": rejected_samples,
            "casts_votes": False, "ownership_authority": False,
        }
    feature_index = build_visual_feature_index(rgb)
    if feature_index is None:
        return {
            "status": "abstained", "reason": "visual_features_unavailable",
            "seed_count": len(seeds), "match_count": 0, "matches": [],
            "rejected_seed_reasons": dict(sorted(rejected.items())),
            "rejected_seed_samples": rejected_samples,
            "casts_votes": False, "ownership_authority": False,
        }
    exclusions = tuple(group.bbox for group in seeds)
    matches = []
    for group in seeds:
        match = find_visual_instance_match(
            rgb,
            group.bbox,
            exclude_bboxes=tuple(bbox for bbox in exclusions if bbox != group.bbox),
            feature_index=feature_index,
        )
        if match is None:
            continue
        item = dict(visual_instance_node_telemetry(
            graph, match, min_pixels=min_component_pixels
        ))
        item.update({
            "seed_proposal": group.candidate_id,
            "seed_source_stage": group.source_stage,
            "seed_source": group.source,
            "seed_confidence": round(group.confidence, 6),
            "seed_member_nodes": list(group.member_node_ids),
        })
        matches.append(item)
    return {
        "status": "observed" if matches else "abstained",
        "reason": "matches_found" if matches else "no_visual_copy",
        "seed_count": len(seeds),
        "match_count": len(matches),
        "matches": matches,
        "rejected_seed_reasons": dict(sorted(rejected.items())),
        "rejected_seed_samples": rejected_samples,
        "feature_index_build_count": 1,
        "casts_votes": False,
        "ownership_authority": False,
    }


def proposal_groups(graph: EvidenceGraph) -> tuple[ProposalGroup, ...]:
    """Aggregate atom memberships by raw proposal without creating authority."""
    grouped: dict[str, list[tuple[ComponentNode, ProposalMembership]]] = defaultdict(list)
    for node in graph.nodes:
        for membership in node.proposal_memberships:
            grouped[membership.candidate_id].append((node, membership))
    groups = []
    for candidate_id in sorted(grouped):
        members = grouped[candidate_id]
        first = members[0][1]
        xs = [node.bbox[0] for node, _item in members]
        ys = [node.bbox[1] for node, _item in members]
        x2s = [node.bbox[0] + node.bbox[2] for node, _item in members]
        y2s = [node.bbox[1] + node.bbox[3] for node, _item in members]
        groups.append(ProposalGroup(
            candidate_id=candidate_id,
            proposed_owner=first.proposed_owner,
            source_stage=first.source_stage,
            source=first.source,
            confidence=max(item.confidence for _node, item in members),
            member_node_ids=tuple(sorted(node.node_id for node, _item in members)),
            source_owner_counts=tuple(sorted(Counter(node.source_owner for node, _item in members).items())),
            bbox=(min(xs), min(ys), max(x2s) - min(xs), max(y2s) - min(ys)),
            covered_pixels=sum(int(round(node.area * item.node_overlap_fraction)) for node, item in members),
        ))
    return tuple(groups)


def proposal_families(graph: EvidenceGraph) -> tuple[ProposalFamily, ...]:
    """Join Number proposal IDs through strong, immutable decal relationships.

    A relationship can only connect proposals that already contain Number
    evidence.  At least one currently-owned Number atom is required, so this
    graph can corroborate a split proposal but can never manufacture Number
    authority from a Sponsor-only logo family.
    """
    node_by_id = graph.node_by_id
    proposal_nodes: dict[str, set[str]] = defaultdict(set)
    node_proposals: dict[str, set[str]] = defaultdict(set)
    for node in graph.nodes:
        for membership in node.proposal_memberships:
            if membership.proposed_owner != "numbers":
                continue
            proposal_nodes[membership.candidate_id].add(node.node_id)
            node_proposals[node.node_id].add(membership.candidate_id)
    if not proposal_nodes:
        return ()

    parents = {candidate_id: candidate_id for candidate_id in proposal_nodes}

    def find(candidate_id: str) -> str:
        while parents[candidate_id] != candidate_id:
            parents[candidate_id] = parents[parents[candidate_id]]
            candidate_id = parents[candidate_id]
        return candidate_id

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    accepted_pairs: list[tuple[str, str]] = []
    for edge in graph.edges:
        left_proposals = node_proposals.get(edge.left, ())
        right_proposals = node_proposals.get(edge.right, ())
        if not left_proposals or not right_proposals:
            continue
        # Shape/mirror/180 agreement is primary.  Palette may corroborate a
        # slightly weaker shape match, but proximity alone never joins a family.
        related = bool(
            edge.family_strength >= 0.88
            or (edge.family_strength >= 0.74 and edge.palette_similarity >= 0.93)
        )
        if not related:
            continue
        for left_id in left_proposals:
            for right_id in right_proposals:
                if left_id != right_id:
                    union(left_id, right_id)
        accepted_pairs.append(tuple(sorted((edge.left, edge.right))))

    grouped: dict[str, set[str]] = defaultdict(set)
    for candidate_id in proposal_nodes:
        grouped[find(candidate_id)].add(candidate_id)
    families = []
    for family_index, candidate_ids in enumerate(
        sorted(grouped.values(), key=lambda value: tuple(sorted(value)))
    ):
        member_ids = set().union(*(proposal_nodes[item] for item in candidate_ids))
        anchors = sorted(
            node_id for node_id in member_ids
            if node_by_id[node_id].source_owner == "numbers"
        )
        candidates = sorted(
            node_id for node_id in member_ids
            if node_by_id[node_id].source_owner == "sponsors"
        )
        if not anchors:
            continue
        family_pairs = sorted({pair for pair in accepted_pairs if pair[0] in member_ids and pair[1] in member_ids})
        families.append(ProposalFamily(
            family_id=f"number-family-{family_index:04d}",
            proposed_owner="numbers",
            candidate_ids=tuple(sorted(candidate_ids)),
            member_node_ids=tuple(sorted(member_ids)),
            anchor_node_ids=tuple(anchors),
            candidate_node_ids=tuple(candidates),
            relationship_pairs=tuple(family_pairs),
        ))
    return tuple(families)


def number_anchor_groups(graph: EvidenceGraph) -> tuple[NumberAnchorGroup, ...]:
    """Compose nearby Number cores/outlines without mutating their atoms."""
    number_nodes = [node for node in graph.nodes if node.source_owner == "numbers"]
    if not number_nodes:
        return ()
    node_ids = {node.node_id for node in number_nodes}
    parents = {node.node_id: node.node_id for node in number_nodes}

    def find(node_id: str) -> str:
        while parents[node_id] != node_id:
            parents[node_id] = parents[parents[node_id]]
            node_id = parents[node_id]
        return node_id

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    for edge in graph.edges:
        if edge.left not in node_ids or edge.right not in node_ids:
            continue
        # Only local decal anatomy may compose. Repeated/mirrored placements
        # elsewhere on the UV map remain distinct anchor groups.
        if edge.distance <= 0.018 or edge.containment >= 0.35:
            union(edge.left, edge.right)

    members_by_root: dict[str, list[ComponentNode]] = defaultdict(list)
    for node in number_nodes:
        members_by_root[find(node.node_id)].append(node)
    groups = []
    for group_index, members in enumerate(
        sorted(members_by_root.values(), key=lambda items: min(node.node_id for node in items))
    ):
        x1 = min(node.bbox[0] for node in members)
        y1 = min(node.bbox[1] for node in members)
        x2 = max(node.bbox[0] + node.bbox[2] for node in members)
        y2 = max(node.bbox[1] + node.bbox[3] for node in members)
        local = np.zeros((y2 - y1, x2 - x1), bool)
        for node in members:
            nx, ny, nw, nh = node.bbox
            local[ny - y1:ny - y1 + nh, nx - x1:nx - x1 + nw] |= (
                graph.component_map[ny:ny + nh, nx:nx + nw] == node.index
            )
        palette = sum(
            np.asarray(node.palette_descriptor, np.float32) * float(node.area)
            for node in members
        )
        palette /= max(1e-6, float(np.linalg.norm(palette)))
        groups.append(NumberAnchorGroup(
            group_id=f"number-anchor-{group_index:04d}",
            member_node_ids=tuple(sorted(node.node_id for node in members)),
            bbox=(x1, y1, x2 - x1, y2 - y1),
            area=sum(node.area for node in members),
            shape_descriptor=_shape_descriptor(local),
            palette_descriptor=tuple(float(value) for value in palette),
        ))
    return tuple(groups)


@dataclass(frozen=True)
class AdjudicationResult:
    assignments: tuple[str, ...]
    decisions: tuple[NodeDecision, ...]
    relationship_vote_count: int

    @property
    def changed_decisions(self) -> tuple[NodeDecision, ...]:
        return tuple(decision for decision in self.decisions if decision.changed)

    @property
    def blocked_decisions(self) -> tuple[NodeDecision, ...]:
        return tuple(decision for decision in self.decisions if decision.blocked)


@dataclass(frozen=True)
class ShadowReport:
    graph: EvidenceGraph = field(repr=False)
    result: AdjudicationResult = field(repr=False)
    elapsed_ms: float
    xor_pixels: tuple[tuple[str, int], ...]
    current_pixels: tuple[tuple[str, int], ...]
    proposed_pixels: tuple[tuple[str, int], ...]
    candidate_telemetry: Mapping[str, Any] = field(default_factory=dict)
    candidate_vote_count: int = 0
    mask_evidence_count: int = 0
    mask_evidence_vote_count: int = 0
    mask_evidence_telemetry: Mapping[str, Any] = field(default_factory=dict)
    semantic_family_vote_count: int = 0
    semantic_family_telemetry: Mapping[str, Any] = field(default_factory=dict)
    semantic_family_votes: tuple[EvidenceVote, ...] = field(default_factory=tuple, repr=False)
    visual_instance_telemetry: Mapping[str, Any] = field(default_factory=dict)
    template_position_telemetry: Mapping[str, Any] = field(default_factory=dict)
    number_map_family_telemetry: Mapping[str, Any] = field(default_factory=dict)

    def to_telemetry(self, max_changes: int = 20) -> dict[str, Any]:
        changes = []
        for decision in self.result.changed_decisions[:max_changes]:
            node = self.graph.nodes[int(decision.node_id[1:])]
            changes.append({
                "node": decision.node_id,
                "bbox": list(node.bbox),
                "area": node.area,
                "from": decision.source_owner,
                "to": decision.owner,
                "confidence": round(decision.confidence, 4),
                "margin": round(decision.margin, 4),
                "scores": {owner: round(score, 4) for owner, score in decision.scores if score},
                "evidence": [
                    {
                        "source": vote.source,
                        "reason": vote.reason,
                        "owner": vote.owner,
                        "weight": round(vote.weight, 4),
                        "support": list(vote.support),
                    }
                    for vote in decision.votes
                    if vote.owner == decision.owner
                ][:8],
            })
        blocked = []
        for decision in self.result.blocked_decisions[:max_changes]:
            node = self.graph.nodes[int(decision.node_id[1:])]
            blocked.append({
                "node": decision.node_id,
                "bbox": list(node.bbox),
                "area": node.area,
                "from": decision.source_owner,
                "proposed": decision.raw_owner,
                "reason": decision.blocked_reason,
                "margin": round(decision.margin, 4),
                "sources": sorted({
                    vote.source for vote in decision.votes
                    if vote.owner == decision.raw_owner and vote.source != "current_partition"
                }),
            })
        ocr_orientation_counts: dict[str, int] = defaultdict(int)
        for node in self.graph.nodes:
            for membership in node.ocr_memberships:
                ocr_orientation_counts[membership.orientation] += 1
        normal_families = {
            region.word_family for region in self.graph.ocr_regions if not region.mirrored
        }
        region_samples = []
        for region in sorted(
            self.graph.ocr_regions,
            key=lambda item: (not item.mirrored, item.region_id),
        )[:24]:
            members = [
                (node, membership)
                for node in self.graph.nodes
                for membership in node.ocr_memberships
                if membership.region_id == region.region_id
            ]
            owner_pixels: dict[str, int] = defaultdict(int)
            covered_pixels = 0
            for node, membership in members:
                overlap = int(round(membership.overlap_fraction * node.area))
                owner_pixels[node.source_owner] += overlap
                covered_pixels += overlap
            region_samples.append({
                "id": region.region_id,
                "text": region.text,
                "word_family": region.word_family,
                "confidence": round(region.confidence, 4),
                "text_quality": round(region.text_quality, 4),
                "orientation": region.orientation,
                "mirrored": region.mirrored,
                "mirror_only": bool(
                    region.mirrored and region.word_family not in normal_families
                ),
                "bbox": list(region.bbox),
                "polygon": [[round(x, 2), round(y, 2)] for x, y in region.polygon],
                "polygon_area": region.area,
                "cross_view_exact": region.cross_view_exact,
                "repeated_mirror_family": region.repeated_mirror_family,
                "quality_basis": region.quality_basis,
                "membership_count": len(members),
                "strong_membership_count": sum(
                    _is_strong_ocr_membership(membership) for _node, membership in members
                ),
                "covered_fraction": round(covered_pixels / max(1, region.area), 4),
                "owner_pixels": dict(sorted(owner_pixels.items())),
            })
        mirrored_region_count = sum(region.mirrored for region in self.graph.ocr_regions)
        mirror_only_region_count = sum(
            region.mirrored and region.word_family not in normal_families
            for region in self.graph.ocr_regions
        )
        evidence_canary = simulate_evidence_canary(
            self.graph,
            self.semantic_family_votes,
            max_samples=max_changes,
        )
        return {
            "status": "shadow",
            "mode": "shadow",
            "schema": SCHEMA_VERSION,
            "elapsed_ms": round(self.elapsed_ms, 3),
            "node_count": len(self.graph.nodes),
            "edge_count": len(self.graph.edges),
            "pair_candidates": self.graph.pair_candidates,
            "pair_truncated": self.graph.pair_truncated,
            "partition_component_count": self.graph.partition_component_count,
            "proposal_split_count": self.graph.proposal_split_count,
            "proposal_split_truncated": self.graph.proposal_split_truncated,
            "ocr_member_node_count": sum(bool(node.ocr_memberships) for node in self.graph.nodes),
            "ocr_membership_count": sum(len(node.ocr_memberships) for node in self.graph.nodes),
            "strong_ocr_member_node_count": sum(_has_strong_ocr(node) for node in self.graph.nodes),
            "mirrored_ocr_membership_count": sum(
                membership.mirrored
                for node in self.graph.nodes
                for membership in node.ocr_memberships
            ),
            "ocr_region_count": len(self.graph.ocr_regions),
            "mirrored_ocr_region_count": mirrored_region_count,
            "mirror_only_ocr_region_count": mirror_only_region_count,
            "ocr_region_samples": region_samples,
            "ocr_region_samples_truncated": len(self.graph.ocr_regions) > len(region_samples),
            "ocr_orientation_counts": dict(sorted(ocr_orientation_counts.items())),
            "candidate_evidence": dict(self.candidate_telemetry),
            "candidate_vote_count": self.candidate_vote_count,
            "mask_evidence_count": self.mask_evidence_count,
            "mask_evidence_vote_count": self.mask_evidence_vote_count,
            "mask_evidence": dict(self.mask_evidence_telemetry),
            "semantic_family_vote_count": self.semantic_family_vote_count,
            "semantic_family": dict(self.semantic_family_telemetry),
            "visual_instances": dict(self.visual_instance_telemetry),
            "template_position": dict(self.template_position_telemetry),
            "number_map_families": dict(self.number_map_family_telemetry),
            "evidence_canary": evidence_canary,
            "relationship_vote_count": self.result.relationship_vote_count,
            "changed_node_count": len(self.result.changed_decisions),
            "changed_nodes_truncated": len(self.result.changed_decisions) > max_changes,
            "blocked_proposal_count": len(self.result.blocked_decisions),
            "blocked_proposals_truncated": len(self.result.blocked_decisions) > max_changes,
            "blocked_proposals": blocked,
            "xor_pixels": dict(self.xor_pixels),
            "current_pixels": dict(self.current_pixels),
            "proposed_pixels": dict(self.proposed_pixels),
            "changes": changes,
            "output_applied": False,
        }


def get_adjudicator_mode(environ: Mapping[str, str] | None = None) -> str:
    """Return ``off`` or ``shadow``; apply mode is intentionally unavailable."""
    env = os.environ if environ is None else environ
    raw = str(env.get(ADJUDICATOR_MODE_ENV, "shadow")).strip().lower()
    if raw in _SHADOW_VALUES:
        return "shadow"
    if raw in _FALSE_VALUES:
        return "off"
    # Fail closed for typos and future/unauthorized modes such as "apply".
    return "off"


def _coerce_rgb(rgb: np.ndarray) -> np.ndarray:
    array = np.asarray(rgb)
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError("rgb must have shape HxWx3+")
    array = array[:, :, :3]
    if array.dtype == np.uint8:
        return np.ascontiguousarray(array)
    values = np.asarray(array, np.float32)
    if values.size and float(np.nanmax(values)) <= 1.5:
        values = values * 255.0
    return np.clip(values, 0.0, 255.0).astype(np.uint8)


def _coerce_masks(masks: Mapping[str, np.ndarray], shape: tuple[int, int]) -> dict[str, np.ndarray]:
    out = {}
    for owner in OWNERS:
        raw = masks.get(owner)
        if raw is None:
            out[owner] = np.zeros(shape, bool)
            continue
        array = np.asarray(raw)
        if array.shape != shape:
            raise ValueError(f"mask {owner!r} has shape {array.shape}, expected {shape}")
        out[owner] = array > 0
    return out


def _normalize_owner_map(masks: Mapping[str, np.ndarray], shape: tuple[int, int]) -> np.ndarray:
    source = _coerce_masks(masks, shape)
    owner_map = np.full(shape, -1, np.int8)
    for owner in OWNERSHIP_PRIORITY:
        take = source[owner] & (owner_map < 0)
        owner_map[take] = _OWNER_INDEX[owner]
    owner_map[owner_map < 0] = _OWNER_INDEX["paint"]
    return owner_map


def normalized_masks(graph: EvidenceGraph) -> dict[str, np.ndarray]:
    return {
        owner: ((graph.owner_map == index).astype(np.uint8) * 255)
        for owner, index in _OWNER_INDEX.items()
    }


def _shape_descriptor(mask: np.ndarray) -> tuple[float, ...]:
    if cv2 is None:
        raise RuntimeError("OpenCV is required for Smart TGA component evidence")
    small = cv2.resize(mask.astype(np.float32), (_SHAPE_SIDE, _SHAPE_SIDE), interpolation=cv2.INTER_AREA)
    norm = float(np.linalg.norm(small))
    if norm > 1e-8:
        small /= norm
    return tuple(float(value) for value in small.reshape(-1))


def _palette_descriptor(hsv_values: np.ndarray) -> tuple[float, ...]:
    descriptors = []
    for channel, bins, value_range in ((0, 6, (0, 180)), (1, 3, (0, 256)), (2, 3, (0, 256))):
        hist, _ = np.histogram(hsv_values[:, channel], bins=bins, range=value_range)
        descriptors.extend(hist.astype(np.float32).tolist())
    vector = np.asarray(descriptors, np.float32)
    norm = float(np.linalg.norm(vector))
    if norm > 1e-8:
        vector /= norm
    return tuple(float(value) for value in vector)


def _decal_palette_descriptor(hsv_values: np.ndarray) -> np.ndarray:
    """Describe decal ink while discounting scale and achromatic background."""
    if hsv_values.size == 0:
        return np.zeros(16, np.float32)
    values = np.asarray(hsv_values, np.float32)
    hue, saturation, value = values[:, 0], values[:, 1], values[:, 2]
    chromatic = (saturation > 50.0) & (value > 70.0)
    histogram, _ = np.histogram(hue[chromatic], bins=np.linspace(0.0, 180.0, 13))
    histogram = histogram.astype(np.float32)
    histogram /= max(1.0, float(histogram.sum()))
    return np.concatenate((
        histogram,
        np.asarray((
            float(np.mean((saturation < 45.0) & (value > 190.0))),
            float(np.mean(value < 62.0)),
            float(np.mean(saturation / 255.0)),
            float(np.mean(value / 255.0)),
        ), np.float32),
    ))


def _island_span(mask: np.ndarray, width: int, height: int) -> tuple[int, float, float]:
    if cv2 is None or not np.any(mask):
        return 0, 0.0, 0.0
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), 8
    )
    kept = [
        index for index in range(1, count)
        if int(stats[index, cv2.CC_STAT_AREA]) >= 8
    ]
    if not kept:
        return 0, 0.0, 0.0
    ys, xs = np.where(np.isin(labels, kept))
    return (
        len(kept),
        float(xs.max() - xs.min() + 1) / max(1, width),
        float(ys.max() - ys.min() + 1) / max(1, height),
    )


def number_family_signals(
    rgb: np.ndarray,
    numbers: np.ndarray,
    *,
    hsv: np.ndarray | None = None,
    edges: np.ndarray | None = None,
    labels: np.ndarray | None = None,
    stats: np.ndarray | None = None,
) -> NumberFamilySignals:
    """Find small scale variants of a repeated Number family and wordmarks.

    Large, mutually palette-consistent Number components become anchors. A
    smaller candidate is protected only when at least two anchors independently
    match its scale-invariant ink palette and its geometry remains compatible.
    Conversely, compact wide components with many separated glyph islands and
    no anchor-family support become Sponsor-wordmark evidence.
    """
    if cv2 is None:
        return NumberFamilySignals()
    numbers_b = np.asarray(numbers) > 0
    if numbers_b.ndim != 2 or not np.any(numbers_b):
        return NumberFamilySignals()
    height, width = numbers_b.shape
    if np.asarray(rgb).shape[:2] != (height, width):
        raise ValueError("RGB and Number masks must have the same shape")
    if hsv is None:
        hsv = cv2.cvtColor(np.asarray(rgb, np.uint8), cv2.COLOR_RGB2HSV)
    if edges is None:
        gray = cv2.cvtColor(np.asarray(rgb, np.uint8), cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 55, 145) > 0
    if labels is None or stats is None:
        _count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            numbers_b.astype(np.uint8), 8
        )

    canvas_area = float(max(1, height * width))
    min_dim = float(max(1, min(height, width)))
    components: list[dict[str, Any]] = []
    for label in range(1, len(stats)):
        x, y, box_width, box_height, area = [int(value) for value in stats[label]]
        if area < 30:
            continue
        component = labels == label
        fill = area / float(max(1, box_width * box_height))
        aspect = max(
            box_width / float(max(1, box_height)),
            box_height / float(max(1, box_width)),
        )
        components.append({
            "label": label,
            "bbox": (x, y, box_width, box_height),
            "area": area,
            "area_fraction": area / canvas_area,
            "fill": fill,
            "aspect": aspect,
            "max_dim_fraction": max(box_width, box_height) / min_dim,
            "min_dim_fraction": min(box_width, box_height) / min_dim,
            "edge_density": float(np.mean(edges[component])),
            "descriptor": _decal_palette_descriptor(hsv[component]),
            "shape_descriptor": _shape_descriptor(
                component[y:y + box_height, x:x + box_width]
            ),
        })

    anchors = [
        item for item in components
        if item["area_fraction"] >= 0.006
        and item["max_dim_fraction"] >= 0.095
        and item["min_dim_fraction"] >= 0.075
        and item["aspect"] <= 2.20
        and item["fill"] >= 0.35
    ]
    anchor_family: list[dict[str, Any]] = []
    for anchor in anchors:
        family = [
            candidate for candidate in anchors
            if float(np.mean(np.abs(anchor["descriptor"] - candidate["descriptor"]))) <= 0.075
        ]
        if len(family) > len(anchor_family):
            anchor_family = family

    protected: set[int] = set()
    # One full-size Number may be the only OCR-owned anchor while two exact
    # scale copies survive as small Number decals. Palette alone is not enough
    # (a sponsor fragment can share the ink), so protect a small pair only when
    # its normalized geometry and dimensions are near-identical. This is
    # protection/abstention only; it never promotes a Sponsor or Paint node.
    if len(anchor_family) == 1:
        anchor = anchor_family[0]
        small_candidates = [
            item for item in components
            if item["label"] != anchor["label"]
            and 0.00045 <= item["area_fraction"] <= 0.0045
            and float(np.mean(np.abs(item["descriptor"] - anchor["descriptor"]))) <= 0.070
            and item["aspect"] <= anchor["aspect"] + 0.40
            and item["fill"] >= max(0.25, anchor["fill"] - 0.40)
            and item["fill"] <= min(1.0, anchor["fill"] + 0.10)
        ]
        for left_index, left in enumerate(small_candidates):
            left_shape = np.asarray(left["shape_descriptor"], np.float32).reshape(
                _SHAPE_SIDE, _SHAPE_SIDE
            )
            for right in small_candidates[left_index + 1:]:
                right_shape = np.asarray(right["shape_descriptor"], np.float32).reshape(
                    _SHAPE_SIDE, _SHAPE_SIDE
                )
                family_strength = max(
                    float(np.sum(left_shape * right_shape)),
                    float(np.sum(left_shape * np.fliplr(right_shape))),
                    float(np.sum(left_shape * np.rot90(right_shape, 2))),
                )
                left_dims = sorted(left["bbox"][2:4])
                right_dims = sorted(right["bbox"][2:4])
                dimension_ratio = (
                    min(left_dims[0], right_dims[0]) / float(max(left_dims[0], right_dims[0]))
                    * min(left_dims[1], right_dims[1]) / float(max(left_dims[1], right_dims[1]))
                )
                palette_distance = float(np.mean(np.abs(
                    left["descriptor"] - right["descriptor"]
                )))
                if (
                    family_strength >= 0.985
                    and dimension_ratio >= 0.85
                    and palette_distance <= 0.025
                ):
                    protected.update((int(left["label"]), int(right["label"])))
    wordmarks: set[int] = set()
    max_anchor_aspect = max((item["aspect"] for item in anchor_family), default=0.0)
    min_anchor_fill = min((item["fill"] for item in anchor_family), default=1.0)
    max_anchor_fill = max((item["fill"] for item in anchor_family), default=0.0)
    anchor_labels = {int(item["label"]) for item in anchor_family}
    for item in components:
        support = sum(
            float(np.mean(np.abs(item["descriptor"] - anchor["descriptor"]))) <= 0.065
            for anchor in anchor_family
        )
        label = int(item["label"])
        if (
            len(anchor_family) >= 2
            and label not in anchor_labels
            and support >= 2
            and item["aspect"] <= max_anchor_aspect + 0.40
            and item["fill"] >= max(0.25, min_anchor_fill - 0.40)
            and item["fill"] <= min(1.0, max_anchor_fill + 0.10)
        ):
            protected.add(label)
            continue

        x, y, box_width, box_height = item["bbox"]
        local_component = labels[y:y + box_height, x:x + box_width] == label
        local_hsv = hsv[y:y + box_height, x:x + box_width]
        white_islands = _island_span(
            local_component & (local_hsv[:, :, 1] < 45) & (local_hsv[:, :, 2] > 190),
            box_width,
            box_height,
        )
        dark_islands = _island_span(
            local_component & (local_hsv[:, :, 2] < 145),
            box_width,
            box_height,
        )
        strongest_islands = max((white_islands, dark_islands), key=lambda value: (value[0], value[1]))
        if (
            item["area_fraction"] >= 0.0007
            and item["area_fraction"] <= 0.0045
            and box_width >= box_height
            and 1.90 <= item["aspect"] <= 6.0
            and 0.050 <= item["max_dim_fraction"] <= 0.150
            and 0.012 <= item["min_dim_fraction"] <= 0.070
            and 0.35 <= item["fill"] <= 0.92
            and 0.14 <= item["edge_density"] <= 0.50
            and strongest_islands[0] >= 5
            and strongest_islands[1] >= 0.55
            and strongest_islands[2] >= 0.30
            and support < 2
        ):
            wordmarks.add(label)

    return NumberFamilySignals(
        anchor_labels=tuple(sorted(anchor_labels)),
        protected_labels=frozenset(protected),
        wordmark_labels=frozenset(wordmarks),
    )


def number_family_template_inlay(
    rgb: np.ndarray,
    numbers: np.ndarray,
    template: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Extract a repeated small Number decal embedded in a Template component.

    This is deliberately a three-part proof: at least two large palette anchors,
    an already-owned small scale variant, and a Template inlay that matches both
    the anchor palette and the small variant's scale. A single shared color can
    never move fixed car hardware into Numbers.
    """
    empty = np.zeros(np.asarray(numbers).shape[:2], np.uint8)
    if cv2 is None:
        return empty, {"status": "skipped", "reason": "cv2_unavailable"}
    numbers_b = np.asarray(numbers) > 0
    template_b = np.asarray(template) > 0
    if not np.any(numbers_b) or not np.any(template_b):
        return empty, {"status": "empty", "reason": "missing_numbers_or_template"}
    height, width = numbers_b.shape
    if template_b.shape != (height, width) or np.asarray(rgb).shape[:2] != (height, width):
        raise ValueError("RGB, Number, and Template masks must have the same shape")

    rgb_u8 = np.asarray(rgb, np.uint8)
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 55, 145) > 0
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        numbers_b.astype(np.uint8), 8
    )
    signals = number_family_signals(
        rgb_u8,
        numbers_b,
        hsv=hsv,
        edges=edges,
        labels=labels,
        stats=stats,
    )
    if len(signals.anchor_labels) < 2 or not signals.protected_labels:
        return empty, {
            "status": "empty",
            "reason": "no_anchor_and_small_scale_family",
            "anchor_count": len(signals.anchor_labels),
            "small_exemplar_count": len(signals.protected_labels),
        }

    anchor_mask = np.isin(labels, signals.anchor_labels)
    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    chromatic_anchor = anchor_mask & (saturation > 50) & (value > 70)
    anchor_histogram, _ = np.histogram(
        hue[chromatic_anchor], bins=np.linspace(0.0, 180.0, 13)
    )
    anchor_histogram = anchor_histogram.astype(np.float32)
    anchor_histogram /= max(1.0, float(anchor_histogram.sum()))
    active_bins = np.where(anchor_histogram >= 0.08)[0]
    if len(active_bins) < 2:
        return empty, {
            "status": "empty",
            "reason": "anchor_palette_not_distinctive",
            "anchor_count": len(signals.anchor_labels),
            "small_exemplar_count": len(signals.protected_labels),
        }

    hue_bins = np.minimum(11, (hue.astype(np.int16) * 12) // 180)
    seed = (
        template_b
        & (saturation > 50)
        & (value > 70)
        & np.isin(hue_bins, active_bins)
    )
    seed = cv2.morphologyEx(
        seed.astype(np.uint8),
        cv2.MORPH_CLOSE,
        np.ones((3, 3), np.uint8),
        iterations=1,
    ) > 0
    seed_count, seed_labels, seed_stats, _seed_centroids = cv2.connectedComponentsWithStats(
        seed.astype(np.uint8), 8
    )
    exemplars = [
        tuple(int(value) for value in stats[label])
        for label in sorted(signals.protected_labels)
    ]
    min_dim = float(max(1, min(height, width)))
    canvas_area = float(max(1, height * width))
    accepted = []
    out = np.zeros((height, width), bool)
    for label in range(1, seed_count):
        x, y, box_width, box_height, area = [int(value) for value in seed_stats[label]]
        if area < 20 or area / canvas_area > 0.0030:
            continue
        if min(box_width, box_height) < 6 or max(box_width, box_height) / min_dim > 0.085:
            continue
        aspect = max(
            box_width / float(max(1, box_height)),
            box_height / float(max(1, box_width)),
        )
        if aspect > 3.20:
            continue
        component = seed_labels == label
        component_bins = np.bincount(hue_bins[component], minlength=12).astype(np.float32)
        active_total = float(component_bins[active_bins].sum())
        if active_total <= 0:
            continue
        component_distribution = component_bins[active_bins] / active_total
        anchor_distribution = anchor_histogram[active_bins]
        anchor_distribution /= max(1e-6, float(anchor_distribution.sum()))
        if np.count_nonzero(component_distribution >= 0.05) < 2:
            continue
        if float(np.mean(np.abs(component_distribution - anchor_distribution))) > 0.16:
            continue

        candidate_dims = sorted((box_width, box_height))
        scale_matches = 0
        for ex_x, ex_y, ex_width, ex_height, ex_area in exemplars:
            exemplar_dims = sorted((ex_width, ex_height))
            area_ratio = min(area, ex_area) / float(max(area, ex_area))
            small_ratio = min(candidate_dims[0], exemplar_dims[0]) / float(
                max(candidate_dims[0], exemplar_dims[0])
            )
            large_ratio = min(candidate_dims[1], exemplar_dims[1]) / float(
                max(candidate_dims[1], exemplar_dims[1])
            )
            if area_ratio >= 0.45 and small_ratio >= 0.65 and large_ratio >= 0.65:
                scale_matches += 1
        if not scale_matches:
            continue

        # The colored family ink is already the editable decal. Include only a
        # one-pixel dark/white outline immediately touching it; never flood the
        # surrounding fixed Template part.
        local_support = cv2.dilate(component.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1) > 0
        immediate_outline = (
            template_b
            & local_support
            & ((value < 110) | ((saturation < 45) & (value > 180)))
        )
        recovered = component | immediate_outline
        out |= recovered
        accepted.append({
            "bbox": [x, y, box_width, box_height],
            "area": int(np.count_nonzero(recovered)),
            "seed_area": area,
            "scale_matches": scale_matches,
            "reason": "repeated_number_palette_template_inlay",
        })

    return out.astype(np.uint8) * 255, {
        "status": "applied" if accepted else "empty",
        "reason": "repeated_number_palette_template_inlay" if accepted else "no_matching_inlay",
        "anchor_count": len(signals.anchor_labels),
        "small_exemplar_count": len(signals.protected_labels),
        "active_palette_bins": [int(value) for value in active_bins],
        "component_count": len(accepted),
        "added_px": int(np.count_nonzero(out)),
        "components": accepted[:8],
    }


def _ocr_region_mask(
    region: Mapping[str, Any],
    shape: tuple[int, int],
) -> tuple[OcrRegionEvidence, np.ndarray] | None:
    height, width = shape
    region_id = str(region.get("id", region.get("region_id", "ocr")))
    kind = str(region.get("kind", region.get("label", "unknown"))).lower()
    orientation = str(region.get("orientation", region.get("view", "unknown"))).lower()
    mirrored = bool(region.get("mirrored", "mirror" in orientation or "reflect" in orientation))
    text = str(region.get("text") or "")[:80]
    word_family = "".join(character.lower() for character in text if character.isalnum())
    if not word_family:  # Preserve authoritative legacy/synthetic OCR regions.
        word_family = "untyped"
    confidence = float(np.clip(float(region.get("confidence", 1.0)), 0.0, 1.0))
    alnum_count = sum(character.isalnum() for character in text)
    alpha_count = sum(character.isalpha() for character in text)
    inferred_quality = (
        min(1.0, alnum_count / 4.0) * (alpha_count / max(1, alnum_count))
        if text else 1.0
    )
    text_quality = float(np.clip(float(region.get("text_quality", inferred_quality)), 0.0, 1.0))
    polygon = region.get("polygon", region.get("poly"))
    bbox = region.get("bbox")
    region_mask = np.zeros(shape, np.uint8)
    if polygon is not None:
        points = np.asarray(polygon, np.float32).reshape(-1, 2)
        if len(points) < 3:
            return None
        points[:, 0] = np.clip(points[:, 0], 0, width - 1)
        points[:, 1] = np.clip(points[:, 1], 0, height - 1)
        cv2.fillPoly(region_mask, [np.rint(points).astype(np.int32)], 1)
    elif bbox is not None and len(bbox) >= 4:
        x, y, box_width, box_height = [int(round(float(value))) for value in bbox[:4]]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(width, x + max(0, box_width)), min(height, y + max(0, box_height))
        if x1 <= x0 or y1 <= y0:
            return None
        region_mask[y0:y1, x0:x1] = 1
        points = np.asarray([
            [x0, y0], [x1 - 1, y0], [x1 - 1, y1 - 1], [x0, y1 - 1],
        ], np.float32)
    else:
        return None
    ys, xs = np.where(region_mask > 0)
    if not len(xs):
        return None
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    evidence = OcrRegionEvidence(
        region_id=region_id,
        kind=kind,
        orientation=orientation,
        mirrored=mirrored,
        text=text,
        word_family=word_family,
        confidence=confidence,
        text_quality=text_quality,
        bbox=(x0, y0, x1 - x0, y1 - y0),
        area=int(np.count_nonzero(region_mask)),
        polygon=tuple((float(point[0]), float(point[1])) for point in points),
        cross_view_exact=bool(region.get("cross_view_exact", False)),
        repeated_mirror_family=bool(region.get("repeated_mirror_family", False)),
        quality_basis=str(region.get("quality_basis") or ("normal_view" if not mirrored else "legacy_mirror")),
    )
    return evidence, region_mask.astype(bool)


def _node_features(
    rgb: np.ndarray,
    hsv: np.ndarray,
    edge_map: np.ndarray,
    gradient_magnitude: np.ndarray,
    gradient_orientation: np.ndarray,
    component: np.ndarray,
    owner: str,
    bbox: tuple[int, int, int, int],
    centroid: tuple[float, float],
    index: int,
    ocr_masks: Sequence[tuple[OcrRegionEvidence, np.ndarray]],
) -> ComponentNode:
    x, y, width, height = bbox
    pixels = rgb[component]
    hsv_pixels = hsv[component]
    area = int(component.sum())
    canvas_area = int(component.size)
    memberships = []
    for region, region_mask in ocr_masks:
        overlap = int(np.count_nonzero(component & region_mask))
        if overlap:
            region_area = int(np.count_nonzero(region_mask))
            memberships.append(OcrMembership(
                region_id=region.region_id,
                kind=region.kind,
                orientation=region.orientation,
                mirrored=region.mirrored,
                text=region.text,
                word_family=region.word_family,
                confidence=round(region.confidence, 6),
                text_quality=round(region.text_quality, 6),
                overlap_fraction=round(overlap / max(1, area), 6),
                region_coverage_fraction=round(overlap / max(1, region_area), 6),
            ))
    crop = component[y:y + height, x:x + width]
    mean_rgb = tuple(float(value) for value in pixels.mean(axis=0))
    std_rgb = tuple(float(value) for value in pixels.std(axis=0))
    mean_hsv = tuple(float(value) for value in hsv_pixels.mean(axis=0))
    saturation = hsv_pixels[:, 1]
    value = hsv_pixels[:, 2]
    strong_gradient = component & (gradient_magnitude >= 32.0)
    strong_gradient_count = int(np.count_nonzero(strong_gradient))
    if strong_gradient_count:
        orientations = gradient_orientation[strong_gradient]
        weights = gradient_magnitude[strong_gradient]
        weight_total = max(1e-8, float(weights.sum()))
        diagonal_distance = np.minimum(
            np.abs(orientations - 45.0),
            np.abs(orientations - 135.0),
        )
        axis_distance = np.minimum.reduce((
            np.abs(orientations),
            np.abs(orientations - 90.0),
            np.abs(orientations - 180.0),
        ))
        diagonal_gradient_fraction = float(weights[diagonal_distance <= 16.0].sum() / weight_total)
        axis_gradient_fraction = float(weights[axis_distance <= 16.0].sum() / weight_total)
    else:
        diagonal_gradient_fraction = 0.0
        axis_gradient_fraction = 0.0
    return ComponentNode(
        node_id=f"n{index:06d}",
        index=index,
        source_owner=owner,
        bbox=bbox,
        area=area,
        area_fraction=area / max(1, canvas_area),
        centroid=(float(centroid[0]), float(centroid[1])),
        fill_ratio=area / max(1, width * height),
        aspect_ratio=width / max(1, height),
        mean_rgb=mean_rgb,
        std_rgb=std_rgb,
        mean_hsv=mean_hsv,
        white_fraction=float(((saturation < 42) & (value > 178)).mean()),
        dark_fraction=float((value < 72).mean()),
        colored_fraction=float(((saturation > 72) & (value > 42)).mean()),
        edge_density=float(edge_map[component].mean()),
        strong_gradient_fraction=strong_gradient_count / max(1, area),
        diagonal_gradient_fraction=diagonal_gradient_fraction,
        axis_gradient_fraction=axis_gradient_fraction,
        palette_descriptor=_palette_descriptor(hsv_pixels),
        shape_descriptor=_shape_descriptor(crop),
        ocr_memberships=tuple(sorted(memberships, key=lambda item: item.region_id)),
    )


def _bbox_relationship(left: ComponentNode, right: ComponentNode, diagonal: float) -> tuple[float, float]:
    lx, ly, lw, lh = left.bbox
    rx, ry, rw, rh = right.bbox
    dx = max(lx - (rx + rw), rx - (lx + lw), 0)
    dy = max(ly - (ry + rh), ry - (ly + lh), 0)
    distance = math.hypot(dx, dy) / max(1.0, diagonal)
    ix = max(0, min(lx + lw, rx + rw) - max(lx, rx))
    iy = max(0, min(ly + lh, ry + rh) - max(ly, ry))
    containment = (ix * iy) / max(1, min(lw * lh, rw * rh))
    return distance, containment


def _relationship_pair_indices(node_count: int, pair_budget: int):
    """Yield a deterministic, index-fair subset of unordered node pairs.

    A lexicographic budget spends every comparison on early components and can
    leave later nodes with no relationship evidence.  Cyclic distance rounds
    give every node coverage before increasing graph depth, while preserving
    the exact all-pairs result whenever it fits the same budget.
    """
    count = max(0, int(node_count))
    budget = max(0, int(pair_budget))
    if count < 2 or budget <= 0:
        return
    total = count * (count - 1) // 2
    emitted = 0
    if total <= budget:
        for left_index in range(count):
            for right_index in range(left_index + 1, count):
                yield left_index, right_index
        return
    half = count // 2
    for offset in range(1, half + 1):
        limit = count // 2 if count % 2 == 0 and offset == half else count
        for left_index in range(limit):
            yield left_index, (left_index + offset) % count
            emitted += 1
            if emitted >= budget:
                return


def _build_relationships(
    nodes: Sequence[ComponentNode],
    shape: tuple[int, int],
    pair_budget: int,
) -> tuple[tuple[RelationshipEdge, ...], int, bool]:
    if not nodes:
        return (), 0, False
    descriptors = np.asarray([node.shape_descriptor for node in nodes], np.float32).reshape(-1, _SHAPE_SIDE, _SHAPE_SIDE)
    palettes = np.asarray([node.palette_descriptor for node in nodes], np.float32)
    diagonal = math.hypot(*shape)
    edges = []
    considered = 0
    total_pairs = len(nodes) * (len(nodes) - 1) // 2
    truncated = total_pairs > pair_budget
    for left_index, right_index in _relationship_pair_indices(len(nodes), pair_budget):
            considered += 1
            left = nodes[left_index]
            right = nodes[right_index]
            distance, containment = _bbox_relationship(left, right, diagonal)
            area_ratio = min(left.area, right.area) / max(left.area, right.area)
            left_dims = sorted(left.bbox[2:4])
            right_dims = sorted(right.bbox[2:4])
            dimension_ratio = min(left_dims[0], right_dims[0]) / max(left_dims[0], right_dims[0])
            dimension_ratio *= min(left_dims[1], right_dims[1]) / max(left_dims[1], right_dims[1])
            palette_similarity = float(np.dot(palettes[left_index], palettes[right_index]))
            shape_similarity = mirror_similarity = rotation_similarity = 0.0
            if area_ratio >= 0.22 and dimension_ratio >= 0.25:
                left_desc = descriptors[left_index]
                right_desc = descriptors[right_index]
                shape_similarity = float(np.sum(left_desc * right_desc))
                mirror_similarity = float(np.sum(left_desc * np.fliplr(right_desc)))
                rotation_similarity = float(np.sum(left_desc * np.rot90(right_desc, 2)))
            kinds = []
            if distance <= 0.032:
                kinds.append("proximity")
            if containment >= 0.60:
                kinds.append("containment")
            if palette_similarity >= 0.92 and area_ratio >= 0.15:
                kinds.append("shared_palette")
            if shape_similarity >= 0.86 and area_ratio >= 0.35:
                kinds.append("repeated_shape")
            if mirror_similarity >= 0.86 and area_ratio >= 0.35:
                kinds.append("mirror_similarity")
            if rotation_similarity >= 0.86 and area_ratio >= 0.35:
                kinds.append("rotation180_similarity")
            separation = math.hypot(
                left.centroid[0] - right.centroid[0],
                left.centroid[1] - right.centroid[1],
            ) / max(1.0, diagonal)
            if (
                separation >= 0.14
                and area_ratio >= 0.40
                and palette_similarity >= 0.72
                and max(shape_similarity, mirror_similarity, rotation_similarity) >= 0.82
            ):
                kinds.append("side_rear_family")
            left_ocr = {membership.region_id for membership in left.ocr_memberships}
            right_ocr = {membership.region_id for membership in right.ocr_memberships}
            if left_ocr & right_ocr:
                kinds.append("shared_ocr_region")
            if kinds:
                edges.append(RelationshipEdge(
                    left=left.node_id,
                    right=right.node_id,
                    kinds=tuple(kinds),
                    distance=distance,
                    containment=containment,
                    palette_similarity=palette_similarity,
                    shape_similarity=shape_similarity,
                    mirror_similarity=mirror_similarity,
                    rotation180_similarity=rotation_similarity,
                ))
    return tuple(edges), considered, truncated


def _local_component_records(
    binary: np.ndarray,
    owner: str,
    *,
    offset_x: int = 0,
    offset_y: int = 0,
    min_area_px: int = 1,
) -> list[dict[str, Any]]:
    """Return bbox-local connected components without retaining full-frame masks."""
    source = (np.asarray(binary) > 0).astype(np.uint8)
    if not source.any():
        return []
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(source, 8)
    records = []
    for label_id in range(1, count):
        x, y, width, height, area = [int(value) for value in stats[label_id]]
        if area < max(1, int(min_area_px)):
            continue
        records.append({
            "owner": owner,
            "bbox": (offset_x + x, offset_y + y, width, height),
            "area": area,
            "centroid": (
                float(offset_x + centroids[label_id][0]),
                float(offset_y + centroids[label_id][1]),
            ),
            "local_mask": labels[y:y + height, x:x + width] == label_id,
        })
    return records


def _bbox_intersection(
    left: tuple[int, int, int, int],
    right: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    left_x, left_y, left_width, left_height = left
    right_x, right_y, right_width, right_height = right
    x0, y0 = max(left_x, right_x), max(left_y, right_y)
    x1 = min(left_x + left_width, right_x + right_width)
    y1 = min(left_y + left_height, right_y + right_height)
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1 - x0, y1 - y0


def _split_components_by_regions(
    components: list[dict[str, Any]],
    regions: Sequence[Any],
    *,
    max_atoms: int,
    owners: frozenset[str] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Refine final-owner components at immutable evidence boundaries."""
    atoms = components
    truncated = False
    for region in regions:
        next_atoms = []
        for atom in atoms:
            if owners is not None and atom["owner"] not in owners:
                next_atoms.append(atom)
                continue
            intersection = _bbox_intersection(atom["bbox"], region.bbox)
            if intersection is None:
                next_atoms.append(atom)
                continue
            x, y, width, height = intersection
            atom_x, atom_y, _atom_width, _atom_height = atom["bbox"]
            region_x, region_y, _region_width, _region_height = region.bbox
            atom_y0, atom_x0 = y - atom_y, x - atom_x
            region_y0, region_x0 = y - region_y, x - region_x
            atom_window = atom["local_mask"][atom_y0:atom_y0 + height, atom_x0:atom_x0 + width]
            region_window = region.local_mask[
                region_y0:region_y0 + height,
                region_x0:region_x0 + width,
            ]
            overlap = atom_window & region_window
            overlap_area = int(np.count_nonzero(overlap))
            if overlap_area <= 0 or overlap_area >= int(atom["area"]):
                next_atoms.append(atom)
                continue
            inside = np.zeros_like(atom["local_mask"], dtype=np.uint8)
            inside[atom_y0:atom_y0 + height, atom_x0:atom_x0 + width][overlap] = 1
            outside = atom["local_mask"] & (inside == 0)
            next_atoms.extend(_local_component_records(
                inside,
                atom["owner"],
                offset_x=atom_x,
                offset_y=atom_y,
            ))
            next_atoms.extend(_local_component_records(
                outside,
                atom["owner"],
                offset_x=atom_x,
                offset_y=atom_y,
            ))
        atoms = next_atoms
        if len(atoms) > max_atoms:
            truncated = True
            break
    return atoms, truncated


def _split_components_by_candidates(
    components: list[dict[str, Any]],
    candidate_snapshot: Any,
    *,
    max_atoms: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Refine final-owner components at every immutable proposal boundary."""
    return _split_components_by_regions(
        components,
        candidate_snapshot.regions,
        max_atoms=max_atoms,
    )


def build_component_graph(
    rgb: np.ndarray,
    masks: Mapping[str, np.ndarray],
    *,
    ocr_regions: Sequence[Mapping[str, Any]] = (),
    candidate_snapshot: Any = None,
    min_area_px: int = 1,
    pair_budget: int = DEFAULT_PAIR_BUDGET,
    atom_budget: int = 8192,
) -> EvidenceGraph:
    """Build immutable ownership atoms and relationship edges exactly once.

    With detector-stage candidates, final-owner components are refined at every
    proposal boundary.  This prevents one giant Paint component from making a
    small missed decal impossible to adjudicate independently.
    """
    if cv2 is None:
        raise RuntimeError("OpenCV is required for Smart TGA component evidence")
    rgb_u8 = _coerce_rgb(rgb)
    shape = rgb_u8.shape[:2]
    owner_map = _normalize_owner_map(masks, shape)
    gray = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2HSV)
    laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    edge_map = laplacian >= 12.0
    gray_f32 = gray.astype(np.float32)
    gradient_x = cv2.Sobel(gray_f32, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(gray_f32, cv2.CV_32F, 0, 1, ksize=3)
    gradient_magnitude = cv2.magnitude(gradient_x, gradient_y)
    gradient_orientation = (
        np.degrees(np.arctan2(gradient_y, gradient_x)) + 180.0
    ) % 180.0
    parsed_ocr = tuple(
        parsed
        for parsed in (_ocr_region_mask(region, shape) for region in ocr_regions)
        if parsed is not None
    )

    raw_components = []
    for owner in OWNERS:
        raw_components.extend(_local_component_records(
            owner_map == _OWNER_INDEX[owner],
            owner,
            min_area_px=min_area_px,
        ))
    partition_component_count = len(raw_components)
    proposal_split_truncated = False
    if candidate_snapshot is not None and getattr(candidate_snapshot, "regions", ()):
        if tuple(candidate_snapshot.shape) != tuple(shape):
            raise ValueError("candidate snapshot and graph shape must match")
        raw_components, proposal_split_truncated = _split_components_by_candidates(
            raw_components,
            candidate_snapshot,
            max_atoms=max(partition_component_count, int(atom_budget)),
        )
    # High-confidence alphabetic OCR is immutable boundary evidence, not owner
    # authority. Split only Number components so a sponsor wordmark absorbed by
    # a protected digit component can be adjudicated as its own atom.
    alpha_ocr_regions = []
    for evidence, region_mask in parsed_ocr:
        if (
            evidence.mirrored
            or evidence.confidence < 0.85
            or evidence.text_quality < 0.75
            or len(evidence.word_family) < 4
            or not evidence.word_family.isalpha()
        ):
            continue
        x, y, width, height = evidence.bbox
        alpha_ocr_regions.append(_AtomBoundary(
            bbox=evidence.bbox,
            local_mask=_readonly_copy(
                region_mask[y:y + height, x:x + width], bool
            ),
        ))
    if alpha_ocr_regions:
        raw_components, ocr_split_truncated = _split_components_by_regions(
            raw_components,
            alpha_ocr_regions,
            max_atoms=max(partition_component_count, int(atom_budget)),
            owners=frozenset(("numbers",)),
        )
        proposal_split_truncated = proposal_split_truncated or ocr_split_truncated
    raw_components.sort(key=lambda item: (
        item["bbox"][1], item["bbox"][0], _OWNER_INDEX[item["owner"]], -item["area"]
    ))

    component_map = np.full(shape, -1, np.int32)
    nodes = []
    for index, item in enumerate(raw_components):
        x, y, width, height = item["bbox"]
        local_mask = item["local_mask"]
        component_map[y:y + height, x:x + width][local_mask] = index
        component = np.zeros(shape, bool)
        component[y:y + height, x:x + width] = local_mask
        nodes.append(_node_features(
            rgb_u8,
            hsv,
            edge_map,
            gradient_magnitude,
            gradient_orientation,
            component,
            item["owner"],
            item["bbox"],
            item["centroid"],
            index,
            parsed_ocr,
        ))
    if candidate_snapshot is not None:
        memberships_by_index: dict[int, list[ProposalMembership]] = defaultdict(list)
        for region in getattr(candidate_snapshot, "regions", ()):
            x, y, width, height = region.bbox
            labels = component_map[y:y + height, x:x + width][region.local_mask]
            labels = labels[labels >= 0]
            if not len(labels):
                continue
            counts = np.bincount(labels.astype(np.int64))
            for node_index in np.flatnonzero(counts):
                overlap = int(counts[node_index])
                node = nodes[int(node_index)]
                memberships_by_index[int(node_index)].append(ProposalMembership(
                    candidate_id=str(region.candidate_id),
                    proposed_owner=str(region.proposed_owner),
                    source_stage=str(region.source_stage),
                    source=str(region.source),
                    confidence=float(region.confidence),
                    node_overlap_fraction=overlap / float(max(1, node.area)),
                    proposal_overlap_fraction=overlap / float(max(1, region.area)),
                ))
        nodes = [
            replace(
                node,
                proposal_memberships=tuple(sorted(
                    memberships_by_index.get(node.index, ()),
                    key=lambda item: (item.proposed_owner, item.candidate_id),
                )),
            )
            for node in nodes
        ]
    # Every pixel belongs to the normalized partition; a skipped tiny component
    # must remain represented, so min_area_px > 1 is currently diagnostic-only.
    if min_area_px <= 1 and np.any(component_map < 0):
        raise AssertionError("component graph did not cover the normalized partition")
    edges, pair_candidates, pair_truncated = _build_relationships(nodes, shape, max(1, int(pair_budget)))
    return EvidenceGraph(
        shape=shape,
        nodes=tuple(nodes),
        edges=edges,
        component_map=component_map,
        owner_map=owner_map,
        ocr_regions=tuple(region for region, _mask in parsed_ocr),
        pair_candidates=pair_candidates,
        pair_truncated=pair_truncated,
        partition_component_count=partition_component_count,
        proposal_split_count=max(0, len(nodes) - partition_component_count),
        proposal_split_truncated=proposal_split_truncated,
    )


def votes_from_mask(
    graph: EvidenceGraph,
    mask: np.ndarray,
    owner: str,
    *,
    source: str,
    reason: str,
    weight: float = 1.0,
    hard: bool = False,
    min_overlap: float = 0.20,
) -> tuple[EvidenceVote, ...]:
    """Translate an existing heuristic mask into node evidence without mutation."""
    if owner not in _OWNER_INDEX:
        raise ValueError(f"unknown owner {owner!r}")
    candidate = np.asarray(mask) > 0
    if candidate.shape != graph.shape:
        raise ValueError("vote mask shape must match graph")
    votes = []
    for node in graph.nodes:
        overlap = int(np.count_nonzero(candidate & (graph.component_map == node.index)))
        fraction = overlap / max(1, node.area)
        if fraction >= min_overlap:
            votes.append(EvidenceVote(
                node_id=node.node_id,
                owner=owner,
                weight=float(weight) * fraction,
                source=source,
                reason=reason,
                hard=hard,
            ))
    return tuple(votes)


def relationship_votes(
    graph: EvidenceGraph,
    *,
    min_support: int = 2,
    per_edge_weight: float = 0.44,
    max_total_weight: float = 0.85,
) -> tuple[EvidenceVote, ...]:
    """Emit corroborating family votes that cannot defeat current ownership alone.

    The cap is intentionally below the default current-partition vote (1.0).
    A relationship family can strengthen classifier/OCR/guard evidence, but a
    visual resemblance echo chamber cannot independently relabel the sheet.
    """
    nodes = graph.node_by_id
    support: dict[tuple[str, str], list[tuple[str, float, tuple[str, ...]]]] = defaultdict(list)
    family_kinds = frozenset(("repeated_shape", "mirror_similarity", "rotation180_similarity", "side_rear_family"))
    for edge in graph.edges:
        matched_kinds = tuple(kind for kind in edge.kinds if kind in family_kinds)
        if not matched_kinds:
            continue
        left, right = nodes[edge.left], nodes[edge.right]
        strength = edge.family_strength
        for target, neighbor in ((left, right), (right, left)):
            if neighbor.source_owner not in PROPAGATING_OWNERS:
                continue
            if target.source_owner == neighbor.source_owner:
                continue
            support[(target.node_id, neighbor.source_owner)].append(
                (neighbor.node_id, strength, matched_kinds)
            )
    votes = []
    for (node_id, owner), evidence in sorted(support.items()):
        unique = {neighbor_id: (strength, kinds) for neighbor_id, strength, kinds in evidence}
        if len(unique) < max(2, int(min_support)):
            continue
        total = sum(per_edge_weight * strength for strength, _kinds in unique.values())
        reasons = sorted({kind for _strength, kinds in unique.values() for kind in kinds})
        votes.append(EvidenceVote(
            node_id=node_id,
            owner=owner,
            weight=min(float(max_total_weight), total),
            source="relationship_graph",
            reason="corroborated:" + "+".join(reasons),
            support=tuple(sorted(unique)),
        ))
    return tuple(votes)


def sponsor_semantic_family_votes(
    graph: EvidenceGraph,
    *,
    max_samples: int = 20,
) -> tuple[tuple[EvidenceVote, ...], Mapping[str, Any]]:
    """Recognize conservative, recurring non-decal Sponsor families.

    These votes adapt universal appearance and relationship evidence; they do
    not contain vehicle, filename, coordinate, or fixed-pixel authority.  Each
    vote is deliberately weaker than current ownership and is only useful when
    a separate evidence source corroborates it during one-pass adjudication.
    """
    sponsor_nodes = [node for node in graph.nodes if node.source_owner == "sponsors"]
    if not sponsor_nodes:
        return (), {"reason_counts": {}, "target_owner_counts": {}, "samples": []}

    height, width = graph.shape
    min_side = float(max(1, min(height, width)))
    node_by_id = graph.node_by_id
    emitted: dict[tuple[str, str, str], EvidenceVote] = {}
    samples: list[dict[str, Any]] = []

    template_ids = {node.node_id for node in graph.nodes if node.source_owner == "template"}
    template_neighbors: dict[str, set[str]] = defaultdict(set)
    pair_edges: dict[frozenset[str], RelationshipEdge] = {}
    edges_by_node: dict[str, list[RelationshipEdge]] = defaultdict(list)
    for edge in graph.edges:
        pair_edges[frozenset((edge.left, edge.right))] = edge
        edges_by_node[edge.left].append(edge)
        edges_by_node[edge.right].append(edge)
        if edge.distance <= 0.025:
            if edge.left in template_ids and node_by_id[edge.right].source_owner == "sponsors":
                template_neighbors[edge.right].add(edge.left)
            if edge.right in template_ids and node_by_id[edge.left].source_owner == "sponsors":
                template_neighbors[edge.left].add(edge.right)

    def emit(
        node: ComponentNode,
        *,
        owner: str,
        source: str,
        reason: str,
        support: Sequence[str],
        metrics: Mapping[str, Any],
    ) -> None:
        key = (node.node_id, owner, source)
        emitted[key] = EvidenceVote(
            node_id=node.node_id,
            owner=owner,
            weight=0.55,
            source=source,
            reason=reason,
            support=tuple(sorted(set(support))),
        )
        if len(samples) < max(0, int(max_samples)):
            samples.append({
                "node": node.node_id,
                "bbox": list(node.bbox),
                "from": node.source_owner,
                "to": owner,
                "reason": reason,
                "support": list(sorted(set(support))),
                **dict(metrics),
            })

    # Flat, nearly black non-text panels are recurring non-decal regions.
    # Repetition is mandatory: a single dark sponsor letter can never qualify.
    # Existing Template adjacency resolves ambiguous dark material toward
    # hardware; otherwise it remains livery/body Paint evidence.
    flat_dark = []
    for node in sponsor_nodes:
        _x, _y, box_width, box_height = node.bbox
        if not (0.00045 <= node.area_fraction <= 0.020):
            continue
        if min(box_width, box_height) / min_side < 0.008:
            continue
        if node.fill_ratio < 0.45 or node.dark_fraction < 0.90:
            continue
        if float(np.mean(node.std_rgb)) > 22.0 or node.edge_density > 0.18:
            continue
        if node.mean_hsv[1] > 60.0 or _has_strong_ocr(node):
            continue
        flat_dark.append(node)
    flat_palettes = {
        node.node_id: np.asarray(node.palette_descriptor, dtype=np.float32)
        for node in flat_dark
    }
    for node in flat_dark:
        support = [
            other.node_id
            for other in flat_dark
            if other.node_id != node.node_id
            and float(np.dot(flat_palettes[node.node_id], flat_palettes[other.node_id])) >= 0.94
        ]
        if not support:
            continue
        nearby_template = sorted(template_neighbors.get(node.node_id, ()))
        target_owner = "template" if nearby_template else "paint"
        reason = (
            "repeated_flat_dark_nontext_hardware_near_template"
            if nearby_template
            else "repeated_flat_dark_nontext_livery_panel"
        )
        emit(
            node,
            owner=target_owner,
            source="semantic_family:flat_dark_context",
            reason=reason,
            support=(*support, *nearby_template),
            metrics={
                "area_fraction": round(node.area_fraction, 6),
                "fill_ratio": round(node.fill_ratio, 4),
                "dark_fraction": round(node.dark_fraction, 4),
                "edge_density": round(node.edge_density, 4),
            },
        )

    # Large colored/light livery surfaces can be mistaken for Sponsors when a
    # segmentation proposal follows a body-color panel boundary.  Generalize
    # the dark-panel rule without treating color alone as authority: require a
    # repeated, widely separated low-texture Sponsor family *and* an existing
    # Paint component with the same palette.  OCR membership vetoes the family
    # so a flat sponsor badge or wordmark background cannot be demoted merely
    # because it shares the car's colors.
    paint_palette_anchors = [
        node for node in graph.nodes
        if node.source_owner == "paint"
        and node.area_fraction >= 0.0010
    ]
    paint_anchor_palettes = {
        node.node_id: np.asarray(node.palette_descriptor, dtype=np.float32)
        for node in paint_palette_anchors
    }
    livery_surfaces = []
    for node in sponsor_nodes:
        _x, _y, box_width, box_height = node.bbox
        if not (0.0015 <= node.area_fraction <= 0.080):
            continue
        if min(box_width, box_height) / min_side < 0.018:
            continue
        if max(box_width, box_height) / min_side < 0.070:
            continue
        if node.fill_ratio < 0.45 or node.edge_density > 0.22:
            continue
        if node.strong_gradient_fraction > 0.38:
            continue
        if float(np.mean(node.std_rgb)) > 38.0 or _has_strong_ocr(node):
            continue
        palette = np.asarray(node.palette_descriptor, dtype=np.float32)
        paint_support = [
            anchor.node_id
            for anchor in paint_palette_anchors
            if float(np.dot(palette, paint_anchor_palettes[anchor.node_id])) >= 0.94
        ]
        if paint_support:
            livery_surfaces.append((node, palette, paint_support))

    graph_diagonal = max(1.0, math.hypot(height, width))
    for node, palette, paint_support in livery_surfaces:
        repeated_support = []
        for other, other_palette, _other_paint_support in livery_surfaces:
            if other.node_id == node.node_id:
                continue
            separation = math.hypot(
                node.centroid[0] - other.centroid[0],
                node.centroid[1] - other.centroid[1],
            ) / graph_diagonal
            if separation < 0.12:
                continue
            area_ratio = min(node.area, other.area) / max(1, max(node.area, other.area))
            if area_ratio < 0.20:
                continue
            if float(np.dot(palette, other_palette)) < 0.94:
                continue
            repeated_support.append(other.node_id)
        if not repeated_support:
            continue
        emit(
            node,
            owner="paint",
            source="semantic_family:paint_palette_livery_surface",
            reason="repeated_paint_palette_livery_surface",
            support=(*repeated_support, *paint_support),
            metrics={
                "area_fraction": round(node.area_fraction, 6),
                "fill_ratio": round(node.fill_ratio, 4),
                "edge_density": round(node.edge_density, 4),
                "strong_gradient_fraction": round(node.strong_gradient_fraction, 4),
                "paint_anchor_count": len(paint_support),
            },
        )

    # Mirrored neutral vent/grille pairs adjacent to existing Template evidence
    # are hardware.  Exact bilateral geometry, palette, and context are all
    # required so isolated sponsor marks and wordmark letters remain untouched.
    neutral_hardware = []
    for node in sponsor_nodes:
        _x, _y, box_width, box_height = node.bbox
        if not (0.0004 <= node.area_fraction <= 0.008):
            continue
        if min(box_width, box_height) / min_side < 0.008:
            continue
        if not (1.5 <= node.aspect_ratio <= 4.0):
            continue
        if node.fill_ratio < 0.45 or node.mean_hsv[1] > 45.0:
            continue
        if node.edge_density > 0.75 or _has_strong_ocr(node):
            continue
        if not template_neighbors.get(node.node_id):
            continue
        neutral_hardware.append(node)
    for index, left in enumerate(neutral_hardware):
        for right in neutral_hardware[index + 1:]:
            edge = pair_edges.get(frozenset((left.node_id, right.node_id)))
            if edge is None:
                continue
            area_ratio = min(left.area, right.area) / max(1, max(left.area, right.area))
            row_delta = abs(left.centroid[1] - right.centroid[1]) / max(1.0, float(height))
            separation = abs(left.centroid[0] - right.centroid[0]) / max(1.0, float(width))
            if (
                edge.mirror_similarity < 0.97
                or edge.palette_similarity < 0.98
                or area_ratio < 0.85
                or row_delta > 0.02
                or separation < 0.18
            ):
                continue
            for node, other in ((left, right), (right, left)):
                emit(
                    node,
                    owner="template",
                    source="semantic_family:paired_neutral_hardware",
                    reason="mirrored_neutral_hardware_pair_near_template",
                    support=(other.node_id, *sorted(template_neighbors[node.node_id])),
                    metrics={
                        "mirror_similarity": round(edge.mirror_similarity, 4),
                        "palette_similarity": round(edge.palette_similarity, 4),
                        "area_ratio": round(area_ratio, 4),
                    },
                )

    # Carbon-fiber aero parts produce a dense, repeated diagonal weave rather
    # than glyph strokes.  Texture alone is insufficient: require a second,
    # widely separated component with the same palette and compatible geometry
    # so a single italic sponsor mark cannot manufacture Template authority.
    carbon_candidates = [
        node for node in sponsor_nodes
        if 0.00045 <= node.area_fraction <= 0.012
        and 0.30 <= node.fill_ratio <= 0.95
        and node.edge_density >= 0.78
        and node.strong_gradient_fraction >= 0.75
        and node.diagonal_gradient_fraction >= 0.35
        and node.diagonal_gradient_fraction - node.axis_gradient_fraction >= 0.10
        and not _has_strong_ocr(node)
    ]
    graph_diagonal = max(1.0, math.hypot(height, width))
    for node in carbon_candidates:
        strict_support = []
        texture_support = []
        node_dims = sorted(node.bbox[2:4])
        for other in carbon_candidates:
            if other.node_id == node.node_id:
                continue
            edge = pair_edges.get(frozenset((node.node_id, other.node_id)))
            if edge is None:
                continue
            other_dims = sorted(other.bbox[2:4])
            dimension_similarity = (
                min(node_dims[0], other_dims[0]) / max(node_dims[0], other_dims[0])
                * min(node_dims[1], other_dims[1]) / max(node_dims[1], other_dims[1])
            )
            separation = math.hypot(
                node.centroid[0] - other.centroid[0],
                node.centroid[1] - other.centroid[1],
            ) / graph_diagonal
            if (
                separation >= 0.18
                and edge.palette_similarity >= 0.88
                and (edge.family_strength >= 0.82 or dimension_similarity >= 0.72)
            ):
                strict_support.append(other.node_id)
            texture_compatible = (
                abs(node.edge_density - other.edge_density) <= 0.12
                and abs(
                    node.diagonal_gradient_fraction - other.diagonal_gradient_fraction
                ) <= 0.18
            )
            if separation >= 0.12 and edge.palette_similarity >= 0.82 and texture_compatible:
                texture_support.append(other.node_id)
        # Preserve the strict mirrored/shape-compatible pair contract. The
        # looser texture-only route requires three distributed components so
        # two italic sponsor marks cannot manufacture Template authority.
        if not strict_support and len(texture_support) < 2:
            continue
        support = sorted(set((*strict_support, *texture_support)))
        emit(
            node,
            owner="template",
            source="semantic_family:carbon_weave_hardware",
            reason="repeated_diagonal_carbon_weave_hardware",
            support=support,
            metrics={
                "area_fraction": round(node.area_fraction, 6),
                "edge_density": round(node.edge_density, 4),
                "strong_gradient_fraction": round(node.strong_gradient_fraction, 4),
                "diagonal_gradient_fraction": round(node.diagonal_gradient_fraction, 4),
                "axis_gradient_fraction": round(node.axis_gradient_fraction, 4),
            },
        )

    # Compact multicolor sponsor badges sometimes leave their dark interior
    # glyph/inlay behind in Paint while the enclosing badge is already owned
    # by Sponsors.  Containment alone is not authority: require a second,
    # widely separated Paint inlay with nearly identical shape/palette and a
    # second compact Sponsor container from the same palette family.
    paint_inlay_containers: dict[str, list[ComponentNode]] = defaultdict(list)
    paint_inlays = []
    for node in graph.nodes:
        if node.source_owner != "paint":
            continue
        _x, _y, box_width, box_height = node.bbox
        if not (0.00008 <= node.area_fraction <= 0.0012):
            continue
        if not (0.55 <= node.fill_ratio <= 0.95):
            continue
        if node.dark_fraction < 0.65 or node.edge_density < 0.25:
            continue
        if not (0.010 <= min(box_width, box_height) / min_side <= 0.055):
            continue
        for edge in edges_by_node.get(node.node_id, ()):
            container_id = edge.right if edge.left == node.node_id else edge.left
            container = node_by_id[container_id]
            if container.source_owner != "sponsors":
                continue
            _cx, _cy, container_width, container_height = container.bbox
            area_ratio = container.area / max(1.0, node.area)
            if (
                edge.containment >= 0.90
                and edge.distance <= 0.005
                and 1.05 <= area_ratio <= 3.0
                and 0.20 <= container.fill_ratio <= 0.80
                and container.edge_density >= 0.45
                and max(container_width, container_height) / min_side <= 0.070
            ):
                paint_inlay_containers[node.node_id].append(container)
        if paint_inlay_containers[node.node_id]:
            paint_inlays.append(node)

    graph_diagonal = max(1.0, math.hypot(height, width))
    for index, left in enumerate(paint_inlays):
        for right in paint_inlays[index + 1:]:
            inlay_edge = pair_edges.get(frozenset((left.node_id, right.node_id)))
            if inlay_edge is None:
                continue
            area_ratio = min(left.area, right.area) / max(1, max(left.area, right.area))
            separation = math.hypot(
                left.centroid[0] - right.centroid[0],
                left.centroid[1] - right.centroid[1],
            ) / graph_diagonal
            if (
                separation < 0.15
                or area_ratio < 0.80
                or inlay_edge.palette_similarity < 0.96
                or inlay_edge.family_strength < 0.94
            ):
                continue
            container_pair = None
            for left_container in paint_inlay_containers[left.node_id]:
                for right_container in paint_inlay_containers[right.node_id]:
                    edge = pair_edges.get(frozenset((
                        left_container.node_id, right_container.node_id,
                    )))
                    if edge is None:
                        continue
                    container_area_ratio = min(
                        left_container.area, right_container.area,
                    ) / max(1, max(left_container.area, right_container.area))
                    left_dims = sorted(left_container.bbox[2:4])
                    right_dims = sorted(right_container.bbox[2:4])
                    dimension_similarity = (
                        min(left_dims[0], right_dims[0]) / max(left_dims[0], right_dims[0])
                        * min(left_dims[1], right_dims[1]) / max(left_dims[1], right_dims[1])
                    )
                    if (
                        edge.palette_similarity >= 0.96
                        and container_area_ratio >= 0.65
                        and dimension_similarity >= 0.65
                    ):
                        container_pair = (left_container, right_container, edge)
                        break
                if container_pair is not None:
                    break
            if container_pair is None:
                continue
            left_container, right_container, container_edge = container_pair
            for node, other, container in (
                (left, right, left_container),
                (right, left, right_container),
            ):
                emit(
                    node,
                    owner="sponsors",
                    source="semantic_family:embedded_sponsor_inlay",
                    reason="repeated_embedded_sponsor_badge_inlay",
                    support=(other.node_id, container.node_id),
                    metrics={
                        "inlay_family_strength": round(inlay_edge.family_strength, 4),
                        "inlay_palette_similarity": round(inlay_edge.palette_similarity, 4),
                        "container_palette_similarity": round(
                            container_edge.palette_similarity, 4,
                        ),
                        "separation": round(separation, 4),
                    },
                )

    # A strongly read Sponsor wordmark can corroborate a separated mirrored,
    # rotated, or repeated-shape copy that legacy ownership left in Paint.
    # OCR never seeds a move by itself: the anchor must already be Sponsor and
    # the target must have an independent high-similarity relationship edge.
    word_anchors: list[tuple[ComponentNode, OcrMembership]] = []
    for node in sponsor_nodes:
        for membership in node.ocr_memberships:
            atom_coverage = (
                membership.overlap_fraction >= 0.45
                and membership.region_coverage_fraction >= 0.08
            ) or membership.region_coverage_fraction >= 0.45
            if (
                _is_strong_ocr_membership(membership)
                and membership.confidence >= 0.55
                and membership.text_quality >= 0.60
                and len(membership.word_family) >= 5
                and atom_coverage
            ):
                word_anchors.append((node, membership))

    word_targets: dict[str, dict[str, Any]] = {}
    graph_diagonal = max(1.0, math.hypot(height, width))
    for anchor, membership in word_anchors:
        for edge in edges_by_node.get(anchor.node_id, ()):
            target_id = edge.right if edge.left == anchor.node_id else edge.left
            target = node_by_id[target_id]
            if target.source_owner != "paint":
                continue
            if not (0.00003 <= target.area_fraction <= 0.020):
                continue
            if not (0.08 <= target.fill_ratio <= 0.96):
                continue
            area_ratio = min(anchor.area, target.area) / max(1, max(anchor.area, target.area))
            separation = math.hypot(
                anchor.centroid[0] - target.centroid[0],
                anchor.centroid[1] - target.centroid[1],
            ) / graph_diagonal
            family_kinds = set(edge.kinds) & {
                "repeated_shape", "mirror_similarity",
                "rotation180_similarity", "side_rear_family",
            }
            if (
                not family_kinds
                or edge.family_strength < 0.88
                or edge.palette_similarity < 0.72
                or area_ratio < 0.45
                or separation < 0.08
            ):
                continue
            target_word_memberships = [
                item for item in target.ocr_memberships
                if _is_strong_ocr_membership(item)
                and item.confidence >= 0.55
                and item.text_quality >= 0.60
                and item.word_family == membership.word_family
                and item.region_id != membership.region_id
                and (
                    (
                        item.overlap_fraction >= 0.45
                        and item.region_coverage_fraction >= 0.08
                    )
                    or item.region_coverage_fraction >= 0.45
                )
            ]
            if not target_word_memberships:
                continue
            conflicting_words = {
                item.word_family
                for item in target.ocr_memberships
                if _is_strong_ocr_membership(item)
                and len(item.word_family) >= 5
                and item.word_family != membership.word_family
            }
            if conflicting_words:
                continue
            entry = word_targets.setdefault(target.node_id, {
                "node": target,
                "support": set(),
                "families": set(),
                "family_strength": 0.0,
                "palette_similarity": 0.0,
            })
            entry["support"].add(anchor.node_id)
            entry["families"].add(membership.word_family)
            entry.setdefault("target_ocr_regions", set()).update(
                item.region_id for item in target_word_memberships
            )
            entry["family_strength"] = max(entry["family_strength"], edge.family_strength)
            entry["palette_similarity"] = max(entry["palette_similarity"], edge.palette_similarity)

    for target_id in sorted(word_targets):
        entry = word_targets[target_id]
        target = entry["node"]
        emit(
            target,
            owner="sponsors",
            source="semantic_family:ocr_anchor_wordmark",
            reason="repeated_ocr_anchor_wordmark_family",
            support=sorted(entry["support"]),
            metrics={
                "word_families": sorted(entry["families"]),
                "target_ocr_regions": sorted(entry["target_ocr_regions"]),
                "family_strength": round(entry["family_strength"], 4),
                "palette_similarity": round(entry["palette_similarity"], 4),
            },
        )

    votes = tuple(emitted[key] for key in sorted(emitted))
    reason_counts: dict[str, int] = defaultdict(int)
    target_counts: dict[str, int] = defaultdict(int)
    for vote in votes:
        reason_counts[vote.reason] += 1
        target_counts[vote.owner] += 1
    return votes, {
        "reason_counts": dict(sorted(reason_counts.items())),
        "target_owner_counts": dict(sorted(target_counts.items())),
        "samples": samples,
        "samples_truncated": len(votes) > len(samples),
    }


def number_false_positive_semantic_votes(
    graph: EvidenceGraph,
    rgb: np.ndarray,
    numbers: np.ndarray,
    *,
    max_samples: int = 20,
) -> tuple[tuple[EvidenceVote, ...], Mapping[str, Any]]:
    """Propose universal false-Number ownership using two-source evidence.

    A Number atom is never challenged when it belongs to the repeated digit
    anchor family or one of its scale variants.  Every emitted change requires
    both an intrinsic appearance observation and independent OCR or cross-owner
    family context. Relationship evidence therefore corroborates an observed
    panel/logo anatomy; it cannot manufacture authority by itself.
    """
    if cv2 is None:
        return (), {"reason_counts": {}, "target_owner_counts": {}, "samples": []}
    number_mask = np.asarray(numbers) > 0
    if not np.any(number_mask):
        return (), {"reason_counts": {}, "target_owner_counts": {}, "samples": []}
    count, labels, _stats, _centroids = cv2.connectedComponentsWithStats(
        number_mask.astype(np.uint8), 8
    )
    if count <= 1:
        return (), {"reason_counts": {}, "target_owner_counts": {}, "samples": []}
    signals = number_family_signals(rgb, number_mask, labels=labels, stats=_stats)
    protected_labels = set(signals.anchor_labels) | set(signals.protected_labels)
    edges_by_node: dict[str, list[RelationshipEdge]] = defaultdict(list)
    for edge in graph.edges:
        edges_by_node[edge.left].append(edge)
        edges_by_node[edge.right].append(edge)

    # Candidate boundaries may split one legacy Number connected component
    # into several immutable atoms. Track that explicitly so a protected
    # parent label can never be challenged as one indivisible digit blob.
    number_label_node_counts: dict[int, int] = defaultdict(int)
    for candidate_node in graph.nodes:
        if candidate_node.source_owner != "numbers":
            continue
        cx, cy, cwidth, cheight = candidate_node.bbox
        candidate_pixels = (
            graph.component_map[cy:cy + cheight, cx:cx + cwidth]
            == candidate_node.index
        )
        candidate_labels = labels[cy:cy + cheight, cx:cx + cwidth][candidate_pixels]
        candidate_labels = candidate_labels[candidate_labels > 0]
        if len(candidate_labels):
            counts = np.bincount(candidate_labels.astype(np.int64))
            number_label_node_counts[int(np.argmax(counts))] += 1

    emitted: dict[tuple[str, str, str], EvidenceVote] = {}
    samples: list[dict[str, Any]] = []
    abstained_samples: list[dict[str, Any]] = []
    abstained_reasons: Counter[str] = Counter()

    def emit_pair(
        node: ComponentNode,
        *,
        owner: str,
        appearance_source: str,
        appearance_reason: str,
        context_source: str,
        context_reason: str,
        support: Sequence[str],
        metrics: Mapping[str, Any],
    ) -> None:
        for source, reason in (
            (appearance_source, appearance_reason),
            (context_source, context_reason),
        ):
            emitted[(node.node_id, owner, source)] = EvidenceVote(
                node_id=node.node_id,
                owner=owner,
                weight=0.56,
                source=source,
                reason=reason,
                support=tuple(sorted(set(support))),
            )
            if len(samples) < max(0, int(max_samples)):
                samples.append({
                    "node": node.node_id,
                    "bbox": list(node.bbox),
                    "from": "numbers",
                    "to": owner,
                    "source": source,
                    "reason": reason,
                    "support": list(sorted(set(support))),
                    "proposal_memberships": [
                        {
                            "candidate": item.candidate_id,
                            "owner": item.proposed_owner,
                            "stage": item.source_stage,
                            "source": item.source,
                            "confidence": round(item.confidence, 4),
                            "node_overlap": round(item.node_overlap_fraction, 4),
                            "proposal_overlap": round(item.proposal_overlap_fraction, 4),
                        }
                        for item in node.proposal_memberships
                    ],
                    "ocr_memberships": [
                        {
                            "text": item.text,
                            "family": item.word_family,
                            "kind": item.kind,
                            "confidence": round(item.confidence, 4),
                            "text_quality": round(item.text_quality, 4),
                            "overlap": round(item.overlap_fraction, 4),
                        }
                        for item in node.ocr_memberships
                    ],
                    **dict(metrics),
                })

    for node in graph.nodes:
        if node.source_owner != "numbers":
            continue
        x, y, box_width, box_height = node.bbox
        node_pixels = graph.component_map[y:y + box_height, x:x + box_width] == node.index
        node_labels = labels[y:y + box_height, x:x + box_width][node_pixels]
        node_labels = node_labels[node_labels > 0]
        if not len(node_labels):
            continue
        label_counts = np.bincount(node_labels.astype(np.int64))
        number_label = int(np.argmax(label_counts))
        is_protected_number = number_label in protected_labels

        symmetric_aspect = max(
            node.aspect_ratio,
            1.0 / max(1e-6, node.aspect_ratio),
        )
        std_mean = float(np.mean(node.std_rgb))
        strong_word_ocr = [
            membership
            for membership in node.ocr_memberships
            if _is_strong_ocr_membership(membership)
            and any(character.isalpha() for character in membership.word_family)
            and membership.kind not in ("number", "numbers", "digit")
        ]
        high_confidence_alpha_conflicts = [
            membership
            for membership in strong_word_ocr
            if membership.confidence >= 0.85
            and membership.text_quality >= 0.75
            and len(membership.word_family) >= 4
            and membership.word_family.isalpha()
            and (
                membership.overlap_fraction >= 0.18
                or membership.region_coverage_fraction >= 0.45
            )
        ]
        neighbors: list[tuple[ComponentNode, RelationshipEdge]] = []
        for edge in edges_by_node.get(node.node_id, ()):
            other_id = edge.right if edge.left == node.node_id else edge.left
            neighbors.append((graph.node_by_id[other_id], edge))

        # Many compact wordmarks are mistakenly promoted as a Number group.
        # Glyph-island anatomy and meaningful OCR are independent observations.
        if (
            not is_protected_number
            and number_label in signals.wordmark_labels
            and strong_word_ocr
        ):
            ocr_support = [
                membership.region_id
                for membership in strong_word_ocr
            ]
            emit_pair(
                node,
                owner="sponsors",
                appearance_source="semantic_number:wordmark_anatomy",
                appearance_reason="number_glyph_island_wordmark_anatomy",
                context_source="semantic_number:ocr_word_membership",
                context_reason="number_strong_ocr_word_membership",
                support=(f"number-label:{number_label}", *ocr_support),
                metrics={"number_label": number_label, "wordmark": True},
            )
            continue

        # A repeated Number connected component can absorb an adjacent sponsor
        # badge/wordmark, causing label-level family protection to cover both.
        # Challenge only the immutable graph atom that has independently
        # observed multicolor/complex badge anatomy and a high-confidence,
        # alphabetic OCR ownership conflict. Numeric or weak OCR never bypasses
        # Number-family protection.
        alpha_conflict_atom_anatomy = bool(
            number_label_node_counts.get(number_label, 0) >= 2
            and high_confidence_alpha_conflicts
            and 0.00005 <= node.area_fraction <= 0.050
            and symmetric_aspect <= 8.0
            and 0.08 <= node.fill_ratio <= 1.0
            and std_mean >= 25.0
            and node.edge_density >= 0.06
        )
        if alpha_conflict_atom_anatomy:
            ocr_support = [
                membership.region_id
                for membership in high_confidence_alpha_conflicts
            ]
            emit_pair(
                node,
                owner="sponsors",
                appearance_source="semantic_number:alpha_conflict_badge_anatomy",
                appearance_reason="alphabetic_number_badge_atom_anatomy",
                context_source="semantic_number:high_confidence_alpha_ocr_conflict",
                context_reason="high_confidence_alphabetic_ocr_owner_conflict",
                support=(f"number-label:{number_label}", *ocr_support),
                metrics={
                    "number_label": number_label,
                    "protected_parent": is_protected_number,
                    "std_mean": round(std_mean, 4),
                },
            )

        # Blank neutral number-panel placeholders behave like fixed Template
        # panels. Flatness is the authority; a matching Template neighbor is
        # mandatory corroboration.
        neutral_panel = bool(
            0.00035 <= node.area_fraction <= 0.030
            and symmetric_aspect <= 4.5
            and node.fill_ratio >= 0.48
            and node.mean_hsv[1] <= 48.0
            and std_mean <= 25.0
            and node.edge_density <= 0.26
            and not _has_strong_ocr(node)
        )
        template_support = [
            neighbor.node_id
            for neighbor, edge in neighbors
            if neighbor.source_owner == "template"
            and edge.palette_similarity >= 0.86
            and (
                edge.family_strength >= 0.58
                or edge.distance <= 0.030
                or edge.containment >= 0.18
            )
        ]
        if neutral_panel and template_support:
            emit_pair(
                node,
                owner="template",
                appearance_source="semantic_number:neutral_panel_anatomy",
                appearance_reason="flat_neutral_number_panel_anatomy",
                context_source="semantic_number:template_family_context",
                context_reason="matching_template_panel_family",
                support=(f"number-label:{number_label}", *template_support),
                metrics={"number_label": number_label, "std_mean": round(std_mean, 4)},
            )
            continue

        if is_protected_number:
            continue

        # OCR frequently misses small rotated contingency logos on DLM skins.
        # Dense micro-logo anatomy supplies intrinsic authority, but only a
        # repeated Sponsor family may corroborate it.  Requiring either two
        # shape-family peers with one palette match or three palette peers
        # keeps a lone stylized digit from being demoted merely because its
        # colors also appear in the sponsor stack.
        dense_micro_logo = bool(
            0.00045 <= node.area_fraction <= 0.012
            and symmetric_aspect <= 4.5
            and 0.25 <= node.fill_ratio <= 0.95
            and std_mean >= 45.0
            and node.edge_density >= 0.55
        )
        sponsor_shape_support = [
            (neighbor, edge)
            for neighbor, edge in neighbors
            if neighbor.source_owner == "sponsors"
            and edge.family_strength >= 0.92
        ]
        sponsor_palette_support = [
            (neighbor, edge)
            for neighbor, edge in neighbors
            if neighbor.source_owner == "sponsors"
            and edge.palette_similarity >= 0.94
        ]
        sponsor_mixed_support = [
            (neighbor, edge)
            for neighbor, edge in sponsor_shape_support
            if edge.palette_similarity >= 0.85
        ]
        repeated_sponsor_context = bool(
            len(sponsor_shape_support) >= 2 and sponsor_mixed_support
        )
        palette_only_context = bool(
            len(sponsor_palette_support) >= 3 and not repeated_sponsor_context
        )
        raw_number_peers = [
            (neighbor, edge)
            for neighbor, edge in neighbors
            if neighbor.source_owner == "numbers"
            and edge.family_strength >= 0.70
            and any(
                item.proposed_owner == "numbers"
                and item.confidence >= 0.70
                and any(token in f"{item.source_stage} {item.source}".lower()
                        for token in ("raw", "detector", "model", "proposal"))
                for item in neighbor.proposal_memberships
            )
        ]
        if dense_micro_logo and palette_only_context:
            abstained_reasons["palette_only_micro_logo_ambiguity"] += 1
            if len(abstained_samples) < max(0, int(max_samples)):
                abstained_samples.append({
                    "node": node.node_id,
                    "bbox": list(node.bbox),
                    "reason": "palette_only_micro_logo_ambiguity",
                    "number_label": number_label,
                    "shape_support_count": len(sponsor_shape_support),
                    "palette_support_count": len(sponsor_palette_support),
                    "raw_number_peer_count": len(raw_number_peers),
                })
        if dense_micro_logo and repeated_sponsor_context:
            sponsor_support = {
                neighbor.node_id
                for neighbor, _edge in (
                    *sponsor_shape_support,
                    *sponsor_palette_support,
                )
            }
            emit_pair(
                node,
                owner="sponsors",
                appearance_source="semantic_number:dense_micro_logo_anatomy",
                appearance_reason="dense_number_micro_logo_anatomy",
                context_source="semantic_number:repeated_sponsor_family_context",
                context_reason="repeated_sponsor_micro_logo_family",
                support=(f"number-label:{number_label}", *sorted(sponsor_support)),
                metrics={
                    "number_label": number_label,
                    "std_mean": round(std_mean, 4),
                    "shape_support_count": len(sponsor_shape_support),
                    "palette_support_count": len(sponsor_palette_support),
                    "raw_number_peer_count": len(raw_number_peers),
                    "raw_number_peer_strengths": [
                        round(edge.family_strength, 4)
                        for _neighbor, edge in sorted(
                            raw_number_peers,
                            key=lambda pair: pair[1].family_strength,
                            reverse=True,
                        )[:6]
                    ],
                    "raw_number_peer_area_ratios": [
                        round(max(node.area, neighbor.area) / max(1, min(node.area, neighbor.area)), 4)
                        for neighbor, edge in sorted(
                            raw_number_peers,
                            key=lambda pair: pair[1].family_strength,
                            reverse=True,
                        )[:6]
                    ],
                    "raw_number_peer_bboxes": [
                        list(neighbor.bbox)
                        for neighbor, edge in sorted(
                            raw_number_peers,
                            key=lambda pair: pair[1].family_strength,
                            reverse=True,
                        )[:6]
                    ],
                },
            )
            continue

        # Smooth colored fragments are livery only when Paint already contains
        # a strongly matching family member. This excludes ornate digit ink.
        livery_fragment = bool(
            0.00020 <= node.area_fraction <= 0.018
            and symmetric_aspect <= 6.0
            and node.fill_ratio >= 0.40
            and node.colored_fraction >= 0.72
            and std_mean <= 30.0
            and node.edge_density <= 0.13
            and not _has_strong_ocr(node)
        )
        paint_support = [
            neighbor.node_id
            for neighbor, edge in neighbors
            if neighbor.source_owner == "paint"
            and edge.palette_similarity >= 0.90
            and (edge.family_strength >= 0.62 or edge.distance <= 0.025)
        ]
        if livery_fragment and paint_support:
            emit_pair(
                node,
                owner="paint",
                appearance_source="semantic_number:flat_livery_anatomy",
                appearance_reason="flat_colored_number_livery_fragment",
                context_source="semantic_number:paint_family_context",
                context_reason="matching_paint_livery_family",
                support=(f"number-label:{number_label}", *paint_support),
                metrics={"number_label": number_label, "std_mean": round(std_mean, 4)},
            )
            continue

        # Complex compact badges/logos require a high-similarity Sponsor family
        # counterpart. A relationship alone emits nothing.
        badge_anatomy = bool(
            0.00045 <= node.area_fraction <= 0.045
            and symmetric_aspect <= 2.15
            and 0.28 <= node.fill_ratio <= 0.95
            and std_mean >= 28.0
            and node.colored_fraction >= 0.18
            and node.edge_density >= 0.10
            and bool(strong_word_ocr)
        )
        sponsor_support = [
            neighbor.node_id
            for neighbor, edge in neighbors
            if neighbor.source_owner == "sponsors"
            and edge.palette_similarity >= 0.82
            and edge.family_strength >= 0.72
        ]
        if badge_anatomy and sponsor_support:
            emit_pair(
                node,
                owner="sponsors",
                appearance_source="semantic_number:badge_logo_anatomy",
                appearance_reason="complex_number_badge_logo_anatomy",
                context_source="semantic_number:sponsor_family_context",
                context_reason="matching_sponsor_badge_family",
                support=(f"number-label:{number_label}", *sponsor_support),
                metrics={"number_label": number_label, "std_mean": round(std_mean, 4)},
            )

    votes = tuple(emitted[key] for key in sorted(emitted))
    reason_counts: dict[str, int] = defaultdict(int)
    target_counts: dict[str, int] = defaultdict(int)
    for vote in votes:
        reason_counts[vote.reason] += 1
        target_counts[vote.owner] += 1
    return votes, {
        "reason_counts": dict(sorted(reason_counts.items())),
        "target_owner_counts": dict(sorted(target_counts.items())),
        "protected_anchor_labels": sorted(protected_labels),
        "abstained_reason_counts": dict(sorted(abstained_reasons.items())),
        "abstained_samples": abstained_samples,
        "abstained_samples_truncated": sum(abstained_reasons.values()) > len(abstained_samples),
        "samples": samples,
        "samples_truncated": len(votes) > len(samples),
    }


def number_proposal_group_votes(
    graph: EvidenceGraph,
    *,
    max_samples: int = 20,
) -> tuple[tuple[EvidenceVote, ...], Mapping[str, Any]]:
    """Corroborate Sponsor atoms sharing one raw proposal with Number atoms."""
    emitted: dict[tuple[str, str], EvidenceVote] = {}
    samples = []
    for group in proposal_groups(graph):
        owner_counts = dict(group.source_owner_counts)
        if (
            group.proposed_owner != "numbers"
            or owner_counts.get("numbers", 0) < 1
            or owner_counts.get("sponsors", 0) < 1
        ):
            continue
        members = [graph.node_by_id[node_id] for node_id in group.member_node_ids]
        number_members = [node for node in members if node.source_owner == "numbers"]
        sponsor_members = [node for node in members if node.source_owner == "sponsors"]
        number_pixels = sum(node.area for node in number_members)
        sponsor_pixels = sum(node.area for node in sponsor_members)
        if number_pixels < max(16, int(0.10 * (number_pixels + sponsor_pixels))):
            continue
        support = tuple(sorted(node.node_id for node in number_members)) + (group.candidate_id,)
        for node in sponsor_members:
            if _has_strong_ocr(node):
                continue
            for source, reason in (
                ("proposal_group:raw_number_continuity", "shared_raw_number_proposal"),
                ("proposal_group:owned_number_member", "same_proposal_contains_number_ink"),
            ):
                emitted[(node.node_id, source)] = EvidenceVote(
                    node_id=node.node_id,
                    owner="numbers",
                    weight=0.56,
                    source=source,
                    reason=reason,
                    support=support,
                )
            if len(samples) < max(0, int(max_samples)):
                samples.append({
                    "node": node.node_id,
                    "bbox": list(node.bbox),
                    "proposal_bbox": list(group.bbox),
                    "proposal": group.candidate_id,
                    "number_member_count": len(number_members),
                    "sponsor_member_count": len(sponsor_members),
                    "number_pixels": number_pixels,
                    "sponsor_pixels": sponsor_pixels,
                })
    votes = tuple(emitted[key] for key in sorted(emitted))
    return votes, {
        "reason_counts": dict(Counter(vote.reason for vote in votes)),
        "target_owner_counts": {"numbers": len(votes)} if votes else {},
        "samples": samples,
        "samples_truncated": len(votes) // 2 > len(samples),
    }


def number_proposal_family_votes(
    graph: EvidenceGraph,
    *,
    max_samples: int = 20,
) -> tuple[tuple[EvidenceVote, ...], Mapping[str, Any]]:
    """Recover split Number proposals only when a trusted family anchors them."""
    emitted: dict[tuple[str, str], EvidenceVote] = {}
    samples: list[dict[str, Any]] = []
    rejected_samples: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()

    def reject(node: ComponentNode, reason: str, **details: Any) -> None:
        rejected[reason] += 1
        if len(rejected_samples) < max(0, int(max_samples)):
            rejected_samples.append({
                "node": node.node_id,
                "bbox": list(node.bbox),
                "reason": reason,
                "ocr": [item.text for item in node.ocr_memberships if _is_strong_ocr_membership(item)],
                **details,
            })
    edges_by_node: dict[str, list[RelationshipEdge]] = defaultdict(list)
    for edge in graph.edges:
        edges_by_node[edge.left].append(edge)
        edges_by_node[edge.right].append(edge)
    for family in proposal_families(graph):
        if not family.candidate_node_ids:
            continue
        for node_id in family.candidate_node_ids:
            node = graph.node_by_id[node_id]
            if _has_strong_alpha_ocr(node):
                reject(node, "strong_alpha_ocr")
                continue
            if not _number_decal_anatomy(node):
                reject(node, "not_number_decal_anatomy")
                continue
            number_proposal_ids = {
                item.candidate_id for item in node.proposal_memberships
                if item.proposed_owner == "numbers"
            }
            nearby_sponsors = []
            for edge in edges_by_node.get(node_id, ()):
                other_id = edge.right if edge.left == node_id else edge.left
                other = graph.node_by_id[other_id]
                same_number_proposal = bool(number_proposal_ids.intersection(
                    item.candidate_id for item in other.proposal_memberships
                    if item.proposed_owner == "numbers"
                ))
                if (
                    other.source_owner == "sponsors"
                    and not same_number_proposal
                    and 0.005 <= edge.distance <= 0.025
                ):
                    nearby_sponsors.append(other_id)
            if nearby_sponsors:
                reject(node, "dense_sponsor_neighborhood", nearby_sponsors=sorted(nearby_sponsors))
                continue
            direct_anchors = sorted({
                other
                for left, right in family.relationship_pairs
                for other in (
                    right if left == node_id else left if right == node_id else "",
                )
                if other in family.anchor_node_ids
            })
            # One relationship is still only corroboration.  Require two
            # independent owned anchors before the family may cast votes.
            if len(direct_anchors) < 2:
                reject(node, "fewer_than_two_direct_anchors", direct_number_anchors=direct_anchors)
                continue
            support = tuple(direct_anchors) + family.candidate_ids
            for source, reason in (
                ("proposal_family:raw_number_membership", "cross_proposal_number_membership"),
                ("proposal_family:owned_number_anchors", "two_owned_number_family_anchors"),
            ):
                emitted[(node_id, source)] = EvidenceVote(
                    node_id=node_id,
                    owner="numbers",
                    weight=0.56,
                    source=source,
                    reason=reason,
                    support=support,
                )
            if len(samples) < max(0, int(max_samples)):
                samples.append({
                    "family": family.family_id,
                    "node": node_id,
                    "bbox": list(node.bbox),
                    "proposal_ids": list(family.candidate_ids),
                    "direct_number_anchors": direct_anchors,
                })
    votes = tuple(emitted[key] for key in sorted(emitted))
    return votes, {
        "family_count": len(proposal_families(graph)),
        "reason_counts": dict(Counter(vote.reason for vote in votes)),
        "rejection_counts": dict(sorted(rejected.items())),
        "rejected_samples": rejected_samples,
        "target_owner_counts": {"numbers": len(votes)} if votes else {},
        "samples": samples,
        "samples_truncated": len(votes) // 2 > len(samples),
    }


def repeated_number_family_votes(
    graph: EvidenceGraph,
    *,
    max_samples: int = 20,
) -> tuple[tuple[EvidenceVote, ...], Mapping[str, Any]]:
    """Recover repeated full-size Number decals missed by raw proposals.

    Intrinsic vivid decal anatomy is the authority.  Cross-owner repetition is
    mandatory corroboration: two owned Number anchors plus a second Sponsor
    copy of the same family.  This deliberately cannot promote an isolated
    logo merely because it resembles one Number atom.
    """
    edges_by_node: dict[str, list[RelationshipEdge]] = defaultdict(list)
    for edge in graph.edges:
        edges_by_node[edge.left].append(edge)
        edges_by_node[edge.right].append(edge)
    composite_anchors = number_anchor_groups(graph)
    emitted: dict[tuple[str, str], EvidenceVote] = {}
    samples: list[dict[str, Any]] = []
    rejected_samples: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()

    def reject(node: ComponentNode, reason: str, **details: Any) -> None:
        rejected[reason] += 1
        if len(rejected_samples) < max(0, int(max_samples)):
            rejected_samples.append({
                "node": node.node_id,
                "bbox": list(node.bbox),
                "reason": reason,
                **details,
            })

    def family_match(edge: RelationshipEdge) -> bool:
        return bool(
            edge.family_strength >= 0.90
            or (edge.family_strength >= 0.78 and edge.palette_similarity >= 0.94)
        )

    for node in graph.nodes:
        if node.source_owner != "sponsors" or _has_strong_alpha_ocr(node):
            continue
        bbox_fraction = (node.bbox[2] * node.bbox[3]) / float(
            max(1, graph.shape[0] * graph.shape[1])
        )
        if (
            node.area_fraction < 0.0015
            or bbox_fraction < 0.014
            or not _number_decal_anatomy(node)
        ):
            continue
        number_anchors = []
        sponsor_peers = []
        related_sponsor_nodes = []
        nearby_sponsors = []
        for edge in edges_by_node.get(node.node_id, ()):
            other_id = edge.right if edge.left == node.node_id else edge.left
            other = graph.node_by_id[other_id]
            if (
                other.source_owner == "sponsors"
                and 0.005 <= edge.distance <= 0.025
            ):
                nearby_sponsors.append(other_id)
            if not family_match(edge):
                continue
            if other.source_owner == "numbers":
                number_anchors.append(other_id)
            elif other.source_owner == "sponsors":
                related_sponsor_nodes.append(other_id)
                if _number_decal_anatomy(other):
                    sponsor_peers.append(other_id)
        number_anchors = sorted(set(number_anchors))
        sponsor_peers = sorted(set(sponsor_peers))
        # A multi-outline digit often survives as different Number atoms at
        # different UV placements. Pool anchors across the repeated Sponsor
        # family, but keep the two-anchor requirement intact.
        pooled_number_anchors = set(number_anchors)
        for peer_id in sponsor_peers:
            for peer_edge in edges_by_node.get(peer_id, ()):
                if not family_match(peer_edge):
                    continue
                peer_other_id = (
                    peer_edge.right if peer_edge.left == peer_id else peer_edge.left
                )
                if graph.node_by_id[peer_other_id].source_owner == "numbers":
                    pooled_number_anchors.add(peer_other_id)
        number_anchors = sorted(pooled_number_anchors)
        node_shape = np.asarray(node.shape_descriptor, np.float32).reshape(_SHAPE_SIDE, _SHAPE_SIDE)
        node_palette = np.asarray(node.palette_descriptor, np.float32)
        composite_matches = []
        for group in composite_anchors:
            group_shape = np.asarray(group.shape_descriptor, np.float32).reshape(_SHAPE_SIDE, _SHAPE_SIDE)
            group_palette = np.asarray(group.palette_descriptor, np.float32)
            family_strength = max(
                float(np.sum(node_shape * group_shape)),
                float(np.sum(node_shape * np.fliplr(group_shape))),
                float(np.sum(node_shape * np.rot90(group_shape, 2))),
            )
            palette_similarity = float(np.dot(node_palette, group_palette))
            area_ratio = min(node.area, group.area) / float(max(node.area, group.area))
            node_dims = sorted(node.bbox[2:4])
            group_dims = sorted(group.bbox[2:4])
            dimension_ratio = (
                min(node_dims[0], group_dims[0]) / float(max(node_dims[0], group_dims[0]))
                * min(node_dims[1], group_dims[1]) / float(max(node_dims[1], group_dims[1]))
            )
            if (
                family_strength >= 0.82
                and palette_similarity >= 0.70
                and area_ratio >= 0.12
                and dimension_ratio >= 0.15
            ):
                composite_matches.append(group.group_id)
        composite_matches = sorted(set(composite_matches))
        large_supported_decal = bool(
            node.area_fraction >= 0.008
            and (node.bbox[2] * node.bbox[3]) / float(max(1, graph.shape[0] * graph.shape[1])) >= 0.014
            and (len(number_anchors) >= 2 or len(composite_matches) >= 2)
        )
        high_detail_neutral_graphic = bool(
            node.mean_hsv[1] <= 150.0
            and node.edge_density >= 0.55
            and node.strong_gradient_fraction >= 0.60
            and node.diagonal_gradient_fraction >= 0.25
        )
        if large_supported_decal and not sponsor_peers and high_detail_neutral_graphic:
            reject(
                node,
                "high_detail_neutral_sponsor_graphic",
                number_anchors=number_anchors,
                composite_anchors=composite_matches,
                saturation=round(node.mean_hsv[1], 4),
                edge_density=round(node.edge_density, 4),
                strong_gradient_fraction=round(node.strong_gradient_fraction, 4),
                diagonal_gradient_fraction=round(node.diagonal_gradient_fraction, 4),
            )
            continue
        if not sponsor_peers and not large_supported_decal:
            reject(
                node,
                "no_repeated_sponsor_copy",
                number_anchors=number_anchors,
                composite_anchors=composite_matches,
            )
            continue
        if len(number_anchors) < 2 and len(composite_matches) < 2:
            reject(
                node,
                "fewer_than_two_number_anchors",
                number_anchors=number_anchors,
                composite_anchors=composite_matches,
                sponsor_peers=sponsor_peers,
            )
            continue
        unrelated_nearby = sorted(set(nearby_sponsors) - set(related_sponsor_nodes))
        if unrelated_nearby and not large_supported_decal:
            reject(
                node,
                "dense_sponsor_neighborhood",
                number_anchors=number_anchors,
                sponsor_peers=sponsor_peers,
                nearby_sponsors=unrelated_nearby,
            )
            continue
        support = tuple(number_anchors + composite_matches + sponsor_peers)
        for source, reason in (
            ("repeated_number_family:vivid_decal_anatomy", "repeated_sponsor_atom_number_anatomy"),
            ("repeated_number_family:cross_owner_repetition", "two_number_anchors_and_sponsor_peer"),
        ):
            emitted[(node.node_id, source)] = EvidenceVote(
                node_id=node.node_id,
                owner="numbers",
                weight=0.56,
                source=source,
                reason=reason,
                support=support,
            )
        if len(samples) < max(0, int(max_samples)):
            samples.append({
                "node": node.node_id,
                "bbox": list(node.bbox),
                "number_anchors": number_anchors,
                "composite_anchors": composite_matches,
                "sponsor_peers": sponsor_peers,
            })
    votes = tuple(emitted[key] for key in sorted(emitted))
    return votes, {
        "reason_counts": dict(Counter(vote.reason for vote in votes)),
        "rejection_counts": dict(sorted(rejected.items())),
        "rejected_samples": rejected_samples,
        "target_owner_counts": {"numbers": len(votes)} if votes else {},
        "samples": samples,
        "samples_truncated": len(votes) // 2 > len(samples),
    }


def _number_decal_anatomy(node: ComponentNode) -> bool:
    """Intrinsic, relationship-independent gate for vivid custom-number ink."""
    symmetric_aspect = max(node.aspect_ratio, 1.0 / max(1e-6, node.aspect_ratio))
    return bool(
        0.00030 <= node.area_fraction <= 0.030
        and symmetric_aspect <= 3.0
        and 0.35 <= node.fill_ratio <= 0.90
        and float(np.mean(node.std_rgb)) >= 25.0
        and 0.15 <= node.edge_density <= 1.0
        # Dark logo plaques are a recurring raw-model Number false positive.
        and node.colored_fraction >= 0.40
        and (node.white_fraction >= 0.10 or node.colored_fraction >= 0.60)
        and node.dark_fraction <= 0.35
    )


def sponsor_number_family_votes(
    graph: EvidenceGraph,
    candidate_votes: Sequence[EvidenceVote] = (),
    *,
    max_samples: int = 20,
) -> tuple[tuple[EvidenceVote, ...], Mapping[str, Any]]:
    """Recover Number-shaped atoms that survived in the Sponsor owner.

    An immutable pre-repair Number proposal and intrinsic compact decal anatomy
    supply two independent authorities. Repeated shape or high-palette
    similarity to existing Number atoms is mandatory corroborating context.
    Strong alphabetic OCR protects real sponsor wordmarks.
    """
    edges_by_node: dict[str, list[RelationshipEdge]] = defaultdict(list)
    for edge in graph.edges:
        edges_by_node[edge.left].append(edge)
        edges_by_node[edge.right].append(edge)
    emitted: dict[tuple[str, str], EvidenceVote] = {}
    samples: list[dict[str, Any]] = []
    rejection_counts: Counter[str] = Counter()
    rejected_samples: list[dict[str, Any]] = []
    raw_number_proposals: dict[str, list[EvidenceVote]] = defaultdict(list)
    for vote in candidate_votes:
        if vote.owner == "numbers" and vote.source.startswith("initial_proposal:"):
            raw_number_proposals[vote.node_id].append(vote)

    for node in graph.nodes:
        if node.source_owner != "sponsors" or _has_strong_ocr(node):
            continue
        proposal_support = raw_number_proposals.get(node.node_id, ())
        if not proposal_support:
            continue
        if not _number_decal_anatomy(node):
            continue
        std_mean = float(np.mean(node.std_rgb))
        number_proposal_ids = {
            item.candidate_id
            for item in node.proposal_memberships
            if item.proposed_owner == "numbers"
        }
        nearby_sponsors: list[dict[str, Any]] = []
        for edge in edges_by_node.get(node.node_id, ()):
            other_id = edge.right if edge.left == node.node_id else edge.left
            other = graph.node_by_id[other_id]
            same_number_proposal = bool(number_proposal_ids.intersection(
                item.candidate_id
                for item in other.proposal_memberships
                if item.proposed_owner == "numbers"
            ))
            if (
                other.source_owner == "sponsors"
                and not same_number_proposal
                # Touching/overlapping atoms are commonly shells or outlines
                # of the same decal. Positive-gap neighbors describe a
                # separate contingency-logo stack.
                and 0.005 <= edge.distance <= 0.025
            ):
                nearby_sponsors.append({
                    "node": other.node_id,
                    "bbox": list(other.bbox),
                    "distance": round(float(edge.distance), 5),
                })
        nearby_sponsor_count = len(nearby_sponsors)
        # Dense contingency stacks routinely fool the raw Number proposal.
        # Treat their spatial Sponsor context as negative evidence; this
        # adapter is only for isolated custom-number decals.
        if nearby_sponsor_count > 0:
            rejection_counts["dense_sponsor_neighborhood"] += 1
            if len(rejected_samples) < max(0, int(max_samples)):
                rejected_samples.append({
                    "node": node.node_id,
                    "bbox": list(node.bbox),
                    "reason": "dense_sponsor_neighborhood",
                    "nearby_sponsor_count": nearby_sponsor_count,
                    "nearby_sponsors": nearby_sponsors[:12],
                    "number_proposal_ids": sorted(number_proposal_ids),
                    "proposal_membership_count": len(node.proposal_memberships),
                })
            continue
        number_support: list[tuple[ComponentNode, RelationshipEdge]] = []
        for edge in edges_by_node.get(node.node_id, ()):
            other_id = edge.right if edge.left == node.node_id else edge.left
            other = graph.node_by_id[other_id]
            if other.source_owner == "numbers":
                number_support.append((other, edge))
        palette_family = [
            other.node_id
            for other, edge in number_support
            if edge.family_strength >= 0.74 and edge.palette_similarity >= 0.93
        ]
        repeated_shape_family = [
            other.node_id
            for other, edge in number_support
            if edge.family_strength >= 0.88
        ]
        if not palette_family and len(repeated_shape_family) < 2:
            continue
        support = tuple(sorted({
            *(item for item in palette_family + repeated_shape_family),
            *(token for vote in proposal_support for token in vote.support),
        }))
        for source, reason in (
            ("semantic_sponsor:number_decal_anatomy", "sponsor_atom_number_decal_anatomy"),
            ("semantic_sponsor:number_family_context", "matching_repeated_number_family"),
        ):
            emitted[(node.node_id, source)] = EvidenceVote(
                node_id=node.node_id,
                owner="numbers",
                weight=0.56,
                source=source,
                reason=reason,
                support=support,
            )
            if len(samples) < max(0, int(max_samples)):
                samples.append({
                    "node": node.node_id,
                    "bbox": list(node.bbox),
                    "from": "sponsors",
                    "to": "numbers",
                    "source": source,
                    "reason": reason,
                    "support": list(support),
                    "std_mean": round(std_mean, 4),
                    "mean_value": round(float(node.mean_hsv[2]), 4),
                    "white_fraction": round(float(node.white_fraction), 4),
                    "dark_fraction": round(float(node.dark_fraction), 4),
                    "colored_fraction": round(float(node.colored_fraction), 4),
                    "fill_ratio": round(float(node.fill_ratio), 4),
                    "edge_density": round(float(node.edge_density), 4),
                    "nearby_sponsor_count": nearby_sponsor_count,
                    "number_proposal_ids": sorted(number_proposal_ids),
                    "max_number_palette": round(max(
                        (edge.palette_similarity for _other, edge in number_support),
                        default=0.0,
                    ), 4),
                    "max_number_family": round(max(
                        (edge.family_strength for _other, edge in number_support),
                        default=0.0,
                    ), 4),
                    "palette_support_count": len(palette_family),
                    "shape_support_count": len(repeated_shape_family),
                    "raw_number_proposal_count": len(proposal_support),
                })
    votes = tuple(emitted[key] for key in sorted(emitted))
    return votes, {
        "reason_counts": dict(Counter(vote.reason for vote in votes)),
        "target_owner_counts": {"numbers": len(votes)} if votes else {},
        "samples": samples,
        "samples_truncated": len(votes) > len(samples),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "rejected_samples": rejected_samples,
        "rejected_samples_truncated": sum(rejection_counts.values()) > len(rejected_samples),
    }


def _winner(scores: Mapping[str, float], source_owner: str) -> tuple[str, float, float]:
    ordered = sorted(
        OWNERS,
        key=lambda owner: (
            -float(scores.get(owner, 0.0)),
            0 if owner == source_owner else 1,
            _PRIORITY_INDEX[owner],
        ),
    )
    winner = ordered[0]
    winner_score = float(scores.get(winner, 0.0))
    runner_score = float(scores.get(ordered[1], 0.0)) if len(ordered) > 1 else 0.0
    return winner, winner_score, winner_score - runner_score


def adjudicate(
    graph: EvidenceGraph,
    votes: Iterable[EvidenceVote] = (),
    *,
    source_weight: float = 1.0,
    min_change_margin: float = 0.05,
    include_relationship_votes: bool = True,
) -> AdjudicationResult:
    """Resolve every node once; soft changes require independent-source quorum."""
    node_ids = {node.node_id for node in graph.nodes}
    all_votes = [
        EvidenceVote(
            node_id=node.node_id,
            owner=node.source_owner,
            weight=float(source_weight),
            source="current_partition",
            reason="current_owner",
        )
        for node in graph.nodes
    ]
    external_votes = tuple(votes)
    for vote in external_votes:
        if vote.node_id not in node_ids:
            raise ValueError(f"vote references unknown node {vote.node_id!r}")
        if vote.owner not in _OWNER_INDEX:
            raise ValueError(f"vote references unknown owner {vote.owner!r}")
        if not math.isfinite(vote.weight) or vote.weight < 0:
            raise ValueError("vote weight must be finite and non-negative")
    all_votes.extend(external_votes)
    family_votes = relationship_votes(graph) if include_relationship_votes else ()
    all_votes.extend(family_votes)

    grouped: dict[str, list[EvidenceVote]] = defaultdict(list)
    for vote in all_votes:
        grouped[vote.node_id].append(vote)
    decisions = []
    assignments = []
    for node in graph.nodes:
        node_votes = grouped[node.node_id]
        hard_votes = [vote for vote in node_votes if vote.hard]
        scoring_votes = hard_votes or node_votes
        scores = {owner: 0.0 for owner in OWNERS}
        for vote in scoring_votes:
            scores[vote.owner] += vote.weight
        raw_owner, raw_winner_score, raw_margin = _winner(scores, node.source_owner)
        owner = raw_owner
        blocked_reason = None
        if owner != node.source_owner and not hard_votes:
            independent_sources = {
                vote.source
                for vote in node_votes
                if vote.owner == owner
                and vote.weight > 0
                and vote.source not in ("current_partition", "relationship_graph")
            }
            # A replayed guard plus relationship similarity is still one idea,
            # not two independent observations.  Requiring quorum for every
            # soft owner change prevents a visually similar sponsor family from
            # pulling a true small number (or vice versa) out of the current
            # partition.  Explicit hard safety contracts remain the only bypass.
            if len(independent_sources) < MIN_INDEPENDENT_SOURCES_FOR_SOFT_CHANGE:
                blocked_reason = "insufficient_independent_sources"
            elif raw_margin < min_change_margin:
                blocked_reason = "insufficient_margin"
            if blocked_reason:
                owner = node.source_owner
        positive_total = sum(max(0.0, score) for score in scores.values())
        confidence = raw_winner_score / positive_total if positive_total else 0.0
        ordered_votes = tuple(sorted(
            node_votes,
            key=lambda vote: (-int(vote.hard), -vote.weight, vote.source, vote.reason, vote.owner),
        ))
        decisions.append(NodeDecision(
            node_id=node.node_id,
            source_owner=node.source_owner,
            owner=owner,
            confidence=confidence,
            margin=raw_margin,
            scores=tuple((candidate, scores[candidate]) for candidate in OWNERS),
            raw_owner=raw_owner,
            blocked_reason=blocked_reason,
            votes=ordered_votes,
        ))
        assignments.append(owner)
    return AdjudicationResult(
        assignments=tuple(assignments),
        decisions=tuple(decisions),
        relationship_vote_count=len(family_votes),
    )


def materialize_masks(graph: EvidenceGraph, assignments: Sequence[str]) -> dict[str, np.ndarray]:
    """Materialize a hard, exhaustive, non-overlapping partition from decisions."""
    if len(assignments) != len(graph.nodes):
        raise ValueError("assignment count must match graph node count")
    owner_for_node = np.empty(len(assignments), np.int8)
    for index, owner in enumerate(assignments):
        if owner not in _OWNER_INDEX:
            raise ValueError(f"unknown assignment owner {owner!r}")
        owner_for_node[index] = _OWNER_INDEX[owner]
    if np.any(graph.component_map < 0):
        raise ValueError("cannot materialize a graph with uncovered pixels")
    adjudicated_map = owner_for_node[graph.component_map]
    masks = {
        owner: ((adjudicated_map == index).astype(np.uint8) * 255)
        for owner, index in _OWNER_INDEX.items()
    }
    coverage = sum((mask > 0).astype(np.uint8) for mask in masks.values())
    if not np.all(coverage == 1):
        raise AssertionError("adjudicated masks must form a hard partition")
    return masks


def simulate_evidence_canary(
    graph: EvidenceGraph,
    votes: Sequence[EvidenceVote],
    *,
    reasons: Sequence[str] = (),
    max_samples: int = 20,
) -> dict[str, Any]:
    """Materialize selected evidence in memory, prove rollback, then discard it.

    This is deliberately not adjudication and never reaches route output masks.
    It answers the review question "what exact atoms would this family move?"
    while production apply remains unavailable.
    """
    allowed_reasons = frozenset(str(reason) for reason in reasons)
    selected = tuple(
        vote for vote in votes
        if not allowed_reasons or vote.reason in allowed_reasons
    )
    source_assignments = tuple(node.source_owner for node in graph.nodes)
    canary_assignments = list(source_assignments)
    selected_by_node: dict[str, EvidenceVote] = {}
    conflict_owners: dict[str, set[str]] = defaultdict(set)
    for vote in selected:
        node = graph.node_by_id.get(vote.node_id)
        if node is None:
            raise ValueError(f"canary vote references unknown node {vote.node_id!r}")
        prior = selected_by_node.get(vote.node_id)
        if prior is not None and prior.owner != vote.owner:
            conflict_owners[vote.node_id].update((prior.owner, vote.owner))
            selected_by_node.pop(vote.node_id, None)
            canary_assignments[node.index] = node.source_owner
            continue
        if vote.node_id in conflict_owners:
            conflict_owners[vote.node_id].add(vote.owner)
            continue
        selected_by_node[vote.node_id] = vote
        canary_assignments[node.index] = vote.owner

    current = normalized_masks(graph)
    canary = materialize_masks(graph, canary_assignments)
    rollback = materialize_masks(graph, source_assignments)
    xor_pixels = {
        owner: int(np.count_nonzero((current[owner] > 0) ^ (canary[owner] > 0)))
        for owner in OWNERS
    }
    rollback_xor = {
        owner: int(np.count_nonzero((current[owner] > 0) ^ (rollback[owner] > 0)))
        for owner in OWNERS
    }
    changed = []
    reason_counts: dict[str, int] = defaultdict(int)
    transition_pixels: dict[str, int] = defaultdict(int)
    for node_id, vote in sorted(selected_by_node.items()):
        node = graph.node_by_id[node_id]
        if node.source_owner == vote.owner:
            continue
        reason_counts[vote.reason] += 1
        transition_pixels[f"{node.source_owner}->{vote.owner}"] += node.area
        if len(changed) < max(0, int(max_samples)):
            changed.append({
                "node": node.node_id,
                "bbox": list(node.bbox),
                "area": node.area,
                "from": node.source_owner,
                "to": vote.owner,
                "reason": vote.reason,
                "support": list(vote.support),
            })
    coverage = sum((mask > 0).astype(np.uint8) for mask in canary.values())
    hard_partition = bool(np.all(coverage == 1))
    return {
        "status": "simulated",
        "output_applied": False,
        "selected_vote_count": len(selected),
        "conflict_node_count": len(conflict_owners),
        "conflicts": [
            {
                "node": node_id,
                "bbox": list(graph.node_by_id[node_id].bbox),
                "source_owner": graph.node_by_id[node_id].source_owner,
                "proposed_owners": sorted(owners),
            }
            for node_id, owners in sorted(conflict_owners.items())[:max(0, int(max_samples))]
        ],
        "conflicts_truncated": len(conflict_owners) > max(0, int(max_samples)),
        "changed_node_count": sum(reason_counts.values()),
        "changed_pixel_count": sum(transition_pixels.values()),
        "reason_counts": dict(sorted(reason_counts.items())),
        "transition_pixels": dict(sorted(transition_pixels.items())),
        "xor_pixels": xor_pixels,
        "hard_partition": hard_partition,
        "reconstruction_mismatch_pixels": int(np.count_nonzero(coverage != 1)),
        "rollback_xor_pixels": rollback_xor,
        "rollback_exact": all(value == 0 for value in rollback_xor.values()),
        "samples_truncated": sum(reason_counts.values()) > len(changed),
        "samples": changed,
    }


def template_position_shadow_evidence(
    graph: EvidenceGraph,
    panel_map: Mapping[str, Any],
    *,
    max_samples: int = 40,
) -> Mapping[str, Any]:
    """Emit learned template-position cues without votes or ownership authority."""
    from engine.spec_sculpt.decal_template_position import compute_template_position_evidence

    reason_counts: dict[str, int] = defaultdict(int)
    samples = []
    for node in graph.nodes:
        proposed_owners = {item.proposed_owner for item in node.proposal_memberships}
        if not proposed_owners:
            continue
        x, y, width, height = node.bbox
        local_mask = graph.component_map[y:y + height, x:x + width] == node.index
        evidence = compute_template_position_evidence(
            node.bbox, local_mask, graph.shape, panel_map,
        )
        reason = ""
        suggested_owner = None
        if "sponsors" in proposed_owners and evidence.best_number_fraction >= 0.50:
            reason = "sponsor_proposal_inside_number_block"
            suggested_owner = "numbers"
        elif (
            "numbers" in proposed_owners
            and evidence.best_number_fraction < 0.35
            and max(evidence.best_sponsor_fraction, evidence.best_mandatory_fraction) >= 0.45
        ):
            reason = "number_proposal_inside_nonnumber_block"
            suggested_owner = "sponsors" if evidence.best_sponsor_fraction >= evidence.best_mandatory_fraction else "template"
        if not reason:
            continue
        reason_counts[reason] += 1
        if len(samples) < max(0, int(max_samples)):
            samples.append({
                "node": node.node_id,
                "bbox": list(node.bbox),
                "source_owner": node.source_owner,
                "proposed_owners": sorted(proposed_owners),
                "suggested_owner": suggested_owner,
                "reason": reason,
                "best_number_fraction": evidence.best_number_fraction,
                "best_sponsor_fraction": evidence.best_sponsor_fraction,
                "best_mandatory_fraction": evidence.best_mandatory_fraction,
            })
    return {
        "status": "shadow",
        "template": str(panel_map.get("template") or "unknown"),
        "cue_count": sum(reason_counts.values()),
        "reason_counts": dict(sorted(reason_counts.items())),
        "samples": samples,
        "samples_truncated": sum(reason_counts.values()) > len(samples),
        "casts_votes": False,
        "ownership_authority": False,
    }


def _runtime_template_position_telemetry(graph: EvidenceGraph) -> Mapping[str, Any]:
    enabled = (
        str(os.environ.get(TEMPLATE_POSITION_SHADOW_ENV, "off")).strip().lower()
        in _SHADOW_VALUES
    )
    if not enabled:
        return {
            "status": "disabled", "reason": "feature_gate_off", "cue_count": 0,
            "casts_votes": False, "ownership_authority": False,
        }
    path_value = str(os.environ.get(TEMPLATE_POSITION_MAP_ENV, "")).strip()
    if not path_value:
        return {
            "status": "disabled", "reason": "template_map_missing", "cue_count": 0,
            "casts_votes": False, "ownership_authority": False,
        }
    try:
        panel_map = json.loads(Path(path_value).read_text(encoding="utf-8"))
        return template_position_shadow_evidence(graph, panel_map)
    except Exception as exc:
        return {
            "status": "error", "reason": type(exc).__name__, "cue_count": 0,
            "casts_votes": False, "ownership_authority": False,
        }


def _runtime_number_map_family_telemetry(
    rgb: np.ndarray,
    masks: Mapping[str, np.ndarray],
    ocr_regions: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    enabled = (
        str(os.environ.get(NUMBER_MAP_FAMILY_SHADOW_ENV, "off")).strip().lower()
        in _SHADOW_VALUES
    )
    if not enabled:
        return {
            "status": "disabled", "reason": "feature_gate_off",
            "family_count": 0, "accepted_family_count": 0,
            "casts_votes": False, "ownership_authority": False,
            "adds_pixels": False, "output_applied": False,
        }
    try:
        from engine.spec_sculpt.number_map_family_shadow import (
            number_map_family_shadow_telemetry,
        )
        return number_map_family_shadow_telemetry(
            rgb, masks, ocr_regions=ocr_regions,
        )
    except Exception as exc:
        return {
            "status": "error", "reason": type(exc).__name__,
            "message": str(exc)[:240],
            "family_count": 0, "accepted_family_count": 0,
            "casts_votes": False, "ownership_authority": False,
            "adds_pixels": False, "output_applied": False,
        }


def run_shadow_adjudication(
    rgb: np.ndarray,
    masks: Mapping[str, np.ndarray],
    *,
    ocr_regions: Sequence[Mapping[str, Any]] = (),
    votes: Iterable[EvidenceVote] = (),
    candidate_snapshot: Any = None,
    mask_evidence: Sequence[Any] = (),
    pair_budget: int = DEFAULT_PAIR_BUDGET,
) -> ShadowReport:
    """Build, propose, and compare without mutating or replacing current masks."""
    started = time.perf_counter()
    graph = build_component_graph(
        rgb,
        masks,
        ocr_regions=ocr_regions,
        candidate_snapshot=candidate_snapshot,
        pair_budget=pair_budget,
    )
    template_position_telemetry = _runtime_template_position_telemetry(graph)
    number_map_family_telemetry = _runtime_number_map_family_telemetry(
        rgb, masks, ocr_regions,
    )
    visual_instance_enabled = (
        str(os.environ.get(VISUAL_INSTANCE_SHADOW_ENV, "off")).strip().lower()
        in _SHADOW_VALUES
    )
    if visual_instance_enabled:
        visual_instance_telemetry = visual_instance_shadow_telemetry(rgb, graph)
    else:
        visual_instance_telemetry = {
            "status": "disabled",
            "reason": "feature_gate_off",
            "seed_count": 0,
            "match_count": 0,
            "matches": [],
            "casts_votes": False,
            "ownership_authority": False,
        }
    candidate_telemetry: Mapping[str, Any] = {}
    candidate_votes: tuple[EvidenceVote, ...] = ()
    evidence_votes: tuple[EvidenceVote, ...] = ()
    if candidate_snapshot is not None or mask_evidence:
        from engine.spec_sculpt.candidate_evidence import (
            candidate_vote_specs,
            mask_evidence_telemetry,
            mask_evidence_vote_specs,
        )
        if candidate_snapshot is not None:
            from engine.spec_sculpt.decal_instances import candidate_instance_telemetry
            candidate_telemetry = dict(candidate_snapshot.to_telemetry())
            candidate_telemetry["decal_instances"] = candidate_instance_telemetry(
                candidate_snapshot,
                rgb=rgb,
                ocr_regions=ocr_regions,
                include_feature_records=(
                    str(os.environ.get(INSTANCE_FEATURE_EXPORT_ENV, "off")).strip().lower()
                    in _SHADOW_VALUES
                ),
                include_number_family_shadow=(
                    str(os.environ.get(NUMBER_FAMILY_MODEL_SHADOW_ENV, "off")).strip().lower()
                    in _SHADOW_VALUES
                ),
                include_number_context_shadow=(
                    str(os.environ.get(NUMBER_CONTEXT_SHADOW_ENV, "off")).strip().lower()
                    in _SHADOW_VALUES
                ),
                include_number_context_semantic_shadow=(
                    str(os.environ.get(NUMBER_CONTEXT_SEMANTIC_SHADOW_ENV, "off")).strip().lower()
                    in _SHADOW_VALUES
                ),
                include_number_context_position_shadow=(
                    str(os.environ.get(NUMBER_CONTEXT_POSITION_SHADOW_ENV, "off")).strip().lower()
                    in _SHADOW_VALUES
                ),
            )
            candidate_votes = tuple(EvidenceVote(**spec) for spec in candidate_vote_specs(graph, candidate_snapshot))
        evidence_votes = tuple(EvidenceVote(**spec) for spec in mask_evidence_vote_specs(graph, mask_evidence))
        evidence_telemetry = mask_evidence_telemetry(mask_evidence)
    else:
        evidence_telemetry = {}
    sponsor_votes, sponsor_telemetry = sponsor_semantic_family_votes(graph)
    sponsor_number_recovery_enabled = (
        str(os.environ.get(SPONSOR_NUMBER_RECOVERY_ENV, "shadow")).strip().lower()
        in _SHADOW_VALUES
    )
    if sponsor_number_recovery_enabled:
        sponsor_number_votes, sponsor_number_telemetry = sponsor_number_family_votes(
            graph,
            candidate_votes,
        )
    else:
        sponsor_number_votes = ()
        sponsor_number_telemetry = {
            "status": "disabled",
            "reason_counts": {},
            "target_owner_counts": {},
            "samples": [],
            "samples_truncated": False,
        }
    group_recovery_enabled = (
        str(os.environ.get(NUMBER_PROPOSAL_GROUP_ENV, "shadow")).strip().lower()
        in _SHADOW_VALUES
    )
    if group_recovery_enabled:
        group_number_votes, group_number_telemetry = number_proposal_group_votes(graph)
        family_number_votes, family_number_telemetry = number_proposal_family_votes(graph)
        repeated_number_votes, repeated_number_telemetry = repeated_number_family_votes(graph)
    else:
        group_number_votes = ()
        family_number_votes = ()
        repeated_number_votes = ()
        group_number_telemetry = {
            "status": "experimental_disabled", "reason_counts": {},
            "target_owner_counts": {}, "samples": [], "samples_truncated": False,
        }
        family_number_telemetry = {
            "status": "experimental_disabled", "reason_counts": {},
            "target_owner_counts": {}, "samples": [], "samples_truncated": False,
        }
        repeated_number_telemetry = {
            "status": "experimental_disabled", "reason_counts": {},
            "target_owner_counts": {}, "samples": [], "samples_truncated": False,
        }
    number_votes, number_telemetry = number_false_positive_semantic_votes(
        graph,
        rgb,
        masks.get("numbers", np.zeros(graph.shape, np.uint8)),
    )
    semantic_votes = sponsor_votes + sponsor_number_votes + group_number_votes + family_number_votes + repeated_number_votes + number_votes
    reason_counts: dict[str, int] = defaultdict(int)
    target_owner_counts: dict[str, int] = defaultdict(int)
    for telemetry in (sponsor_telemetry, sponsor_number_telemetry, group_number_telemetry, family_number_telemetry, repeated_number_telemetry, number_telemetry):
        for reason, count in (telemetry.get("reason_counts") or {}).items():
            reason_counts[str(reason)] += int(count)
        for owner, count in (telemetry.get("target_owner_counts") or {}).items():
            target_owner_counts[str(owner)] += int(count)
    semantic_samples = list(sponsor_telemetry.get("samples") or ())
    semantic_samples.extend(sponsor_number_telemetry.get("samples") or ())
    semantic_samples.extend(group_number_telemetry.get("samples") or ())
    semantic_samples.extend(family_number_telemetry.get("samples") or ())
    semantic_samples.extend(repeated_number_telemetry.get("samples") or ())
    semantic_samples.extend(number_telemetry.get("samples") or ())
    semantic_telemetry = {
        "reason_counts": dict(sorted(reason_counts.items())),
        "target_owner_counts": dict(sorted(target_owner_counts.items())),
        "samples": semantic_samples[:40],
        "samples_truncated": bool(
            sponsor_telemetry.get("samples_truncated")
            or sponsor_number_telemetry.get("samples_truncated")
            or number_telemetry.get("samples_truncated")
            or len(semantic_samples) > 40
        ),
        "number_false_positive": number_telemetry,
        "sponsor_number_family": sponsor_number_telemetry,
        "number_proposal_group": group_number_telemetry,
        "number_proposal_family": family_number_telemetry,
        "repeated_number_family": repeated_number_telemetry,
    }
    result = adjudicate(graph, tuple(votes) + candidate_votes + evidence_votes + semantic_votes)
    current = normalized_masks(graph)
    proposed = materialize_masks(graph, result.assignments)
    xor_pixels = tuple(
        (owner, int(np.count_nonzero((current[owner] > 0) ^ (proposed[owner] > 0))))
        for owner in OWNERS
    )
    current_pixels = tuple((owner, int(np.count_nonzero(current[owner]))) for owner in OWNERS)
    proposed_pixels = tuple((owner, int(np.count_nonzero(proposed[owner]))) for owner in OWNERS)
    return ShadowReport(
        graph=graph,
        result=result,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        xor_pixels=xor_pixels,
        current_pixels=current_pixels,
        proposed_pixels=proposed_pixels,
        candidate_telemetry=candidate_telemetry,
        candidate_vote_count=len(candidate_votes),
        mask_evidence_count=len(mask_evidence),
        mask_evidence_vote_count=len(evidence_votes),
        mask_evidence_telemetry=evidence_telemetry,
        semantic_family_vote_count=len(semantic_votes),
        semantic_family_telemetry=semantic_telemetry,
        semantic_family_votes=semantic_votes,
        visual_instance_telemetry=visual_instance_telemetry,
        template_position_telemetry=template_position_telemetry,
        number_map_family_telemetry=number_map_family_telemetry,
    )


def run_shadow_if_enabled(
    rgb: np.ndarray,
    masks: Mapping[str, np.ndarray],
    *,
    ocr_regions: Sequence[Mapping[str, Any]] = (),
    votes: Iterable[EvidenceVote] = (),
    candidate_snapshot: Any = None,
    mask_evidence: Sequence[Any] = (),
) -> dict[str, Any]:
    mode = get_adjudicator_mode()
    if mode != "shadow":
        return {
            "status": "off",
            "mode": "off",
            "schema": SCHEMA_VERSION,
            "output_applied": False,
        }
    report = run_shadow_adjudication(
        rgb,
        masks,
        ocr_regions=ocr_regions,
        votes=votes,
        candidate_snapshot=candidate_snapshot,
        mask_evidence=mask_evidence,
    )
    return report.to_telemetry()


__all__ = [
    "ADJUDICATOR_MODE_ENV",
    "TEMPLATE_POSITION_MAP_ENV",
    "TEMPLATE_POSITION_SHADOW_ENV",
    "VISUAL_INSTANCE_SHADOW_ENV",
    "NUMBER_MAP_FAMILY_SHADOW_ENV",
    "AdjudicationResult",
    "ComponentNode",
    "EvidenceGraph",
    "EvidenceVote",
    "NodeDecision",
    "NumberFamilySignals",
    "ProposalGroup",
    "OcrMembership",
    "OWNERS",
    "OWNERSHIP_PRIORITY",
    "RelationshipEdge",
    "SCHEMA_VERSION",
    "ShadowReport",
    "adjudicate",
    "build_component_graph",
    "get_adjudicator_mode",
    "materialize_masks",
    "normalized_masks",
    "number_family_signals",
    "number_family_template_inlay",
    "number_false_positive_semantic_votes",
    "number_anchor_groups",
    "number_proposal_group_votes",
    "number_proposal_family_votes",
    "proposal_families",
    "repeated_number_family_votes",
    "proposal_groups",
    "visual_instance_node_telemetry",
    "visual_instance_shadow_telemetry",
    "relationship_votes",
    "run_shadow_adjudication",
    "run_shadow_if_enabled",
    "simulate_evidence_canary",
    "sponsor_semantic_family_votes",
    "sponsor_number_family_votes",
    "template_position_shadow_evidence",
    "votes_from_mask",
]
