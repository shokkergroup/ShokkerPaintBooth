"""Immutable detector-stage evidence for Smart TGA adjudication.

Smart TGA's legacy pipeline repeatedly edits ownership masks.  This module
captures what detectors and guards knew *before* those edits, using compact
bbox-local masks.  The records are shadow-only inputs to the one-pass
adjudicator; they never mutate a caller mask.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, Sequence

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - shipped runtime includes OpenCV
    cv2 = None


OWNERS = ("numbers", "sponsors", "template", "brand_graphics", "paint")
CANDIDATE_OWNERS = OWNERS + ("unassigned",)


def _readonly_local(mask: np.ndarray) -> np.ndarray:
    out = np.ascontiguousarray(np.asarray(mask) > 0)
    out.setflags(write=False)
    return out


@dataclass(frozen=True)
class CandidateRegion:
    candidate_id: str
    source_stage: str
    source: str
    proposed_owner: str
    bbox: tuple[int, int, int, int]
    area: int
    centroid: tuple[float, float]
    local_mask: np.ndarray = field(repr=False, compare=False)
    confidence: float = 1.0
    reason: str = "detector_proposal"

    def __post_init__(self) -> None:
        if self.proposed_owner not in CANDIDATE_OWNERS:
            raise ValueError(f"unknown Smart TGA owner {self.proposed_owner!r}")
        x, y, width, height = self.bbox
        if min(x, y) < 0 or width <= 0 or height <= 0:
            raise ValueError("candidate bbox must be positive and non-negative")
        local = _readonly_local(self.local_mask)
        if local.shape != (height, width):
            raise ValueError("candidate local mask must match bbox")
        if int(np.count_nonzero(local)) != int(self.area):
            raise ValueError("candidate area must match local mask")
        if not np.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("candidate confidence must be in [0, 1]")
        object.__setattr__(self, "local_mask", local)


@dataclass(frozen=True)
class CandidateSnapshot:
    shape: tuple[int, int]
    regions: tuple[CandidateRegion, ...]
    truncated: bool = False
    dropped_regions: int = 0

    def __post_init__(self) -> None:
        height, width = self.shape
        if height <= 0 or width <= 0:
            raise ValueError("snapshot shape must be positive")
        seen = set()
        for region in self.regions:
            if region.candidate_id in seen:
                raise ValueError(f"duplicate candidate id {region.candidate_id!r}")
            seen.add(region.candidate_id)
            x, y, region_width, region_height = region.bbox
            if x + region_width > width or y + region_height > height:
                raise ValueError("candidate bbox exceeds snapshot shape")

    def to_telemetry(self) -> dict[str, Any]:
        owner_counts = {owner: 0 for owner in CANDIDATE_OWNERS}
        owner_pixels = {owner: 0 for owner in CANDIDATE_OWNERS}
        stage_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        for region in self.regions:
            owner_counts[region.proposed_owner] += 1
            owner_pixels[region.proposed_owner] += region.area
            stage_counts[region.source_stage] = stage_counts.get(region.source_stage, 0) + 1
            source_counts[region.source] = source_counts.get(region.source, 0) + 1
        return {
            "region_count": len(self.regions),
            "owner_counts": {key: value for key, value in owner_counts.items() if value},
            "owner_pixels": {key: value for key, value in owner_pixels.items() if value},
            "stage_counts": dict(sorted(stage_counts.items())),
            "source_counts": dict(sorted(source_counts.items())),
            "truncated": self.truncated,
            "dropped_regions": self.dropped_regions,
        }


@dataclass(frozen=True)
class MaskEvidence:
    evidence_id: str
    source_stage: str
    source: str
    target_owner: str
    reason: str
    bbox: tuple[int, int, int, int]
    area: int
    local_mask: np.ndarray = field(repr=False, compare=False)
    weight: float = 0.9
    hard: bool = False

    def __post_init__(self) -> None:
        if self.target_owner not in OWNERS:
            raise ValueError(f"unknown Smart TGA owner {self.target_owner!r}")
        x, y, width, height = self.bbox
        if min(x, y) < 0 or width <= 0 or height <= 0:
            raise ValueError("evidence bbox must be positive and non-negative")
        local = _readonly_local(self.local_mask)
        if local.shape != (height, width):
            raise ValueError("evidence local mask must match bbox")
        if int(np.count_nonzero(local)) != int(self.area):
            raise ValueError("evidence area must match local mask")
        if not np.isfinite(self.weight) or self.weight < 0:
            raise ValueError("evidence weight must be finite and non-negative")
        object.__setattr__(self, "local_mask", local)


def _component_regions(
    mask: np.ndarray,
    *,
    owner: str,
    source_stage: str,
    source: str,
    confidence: float,
    reason: str,
    min_area_px: int,
) -> list[CandidateRegion]:
    binary = (np.asarray(mask) > 0).astype(np.uint8)
    if not binary.any():
        return []
    if cv2 is None:
        raise RuntimeError("OpenCV is required for Smart TGA candidate capture")
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, 8)
    regions = []
    for label_id in range(1, count):
        x, y, width, height, area = [int(value) for value in stats[label_id]]
        if area < max(1, int(min_area_px)):
            continue
        local = labels[y:y + height, x:x + width] == label_id
        candidate_id = f"{source_stage}:{source}:{owner}:{label_id}:{x}:{y}:{width}:{height}"
        regions.append(CandidateRegion(
            candidate_id=candidate_id,
            source_stage=source_stage,
            source=source,
            proposed_owner=owner,
            bbox=(x, y, width, height),
            area=area,
            centroid=(float(centroids[label_id][0]), float(centroids[label_id][1])),
            local_mask=local,
            confidence=float(confidence),
            reason=reason,
        ))
    return regions


def capture_candidate_snapshot(
    masks: Mapping[str, np.ndarray],
    *,
    source_stage: str,
    source: str,
    confidence: float = 1.0,
    reason: str = "detector_proposal",
    min_area_px: int = 1,
    max_regions: int = 4096,
) -> CandidateSnapshot:
    """Capture independent owner proposals without applying priority or mutation."""
    arrays = [np.asarray(mask) for mask in masks.values() if mask is not None]
    if not arrays:
        raise ValueError("at least one proposal mask is required")
    shape = arrays[0].shape
    if len(shape) != 2 or any(array.shape != shape for array in arrays):
        raise ValueError("proposal masks must share one 2D shape")
    regions: list[CandidateRegion] = []
    for owner in CANDIDATE_OWNERS:
        mask = masks.get(owner)
        if mask is None:
            continue
        regions.extend(_component_regions(
            mask,
            owner=owner,
            source_stage=str(source_stage),
            source=str(source),
            confidence=confidence,
            reason=str(reason),
            min_area_px=min_area_px,
        ))
    regions.sort(key=lambda region: (
        region.bbox[1], region.bbox[0], CANDIDATE_OWNERS.index(region.proposed_owner), -region.area,
        region.candidate_id,
    ))
    limit = max(1, int(max_regions))
    dropped = max(0, len(regions) - limit)
    return CandidateSnapshot(
        shape=shape,
        regions=tuple(regions[:limit]),
        truncated=bool(dropped),
        dropped_regions=dropped,
    )


def merge_candidate_snapshots(
    *snapshots: CandidateSnapshot | None,
    max_regions: int = 8192,
) -> CandidateSnapshot | None:
    present = [snapshot for snapshot in snapshots if snapshot is not None]
    if not present:
        return None
    shape = present[0].shape
    if any(snapshot.shape != shape for snapshot in present):
        raise ValueError("candidate snapshots must share one shape")
    by_id: dict[str, CandidateRegion] = {}
    dropped = 0
    truncated = False
    for snapshot in present:
        truncated = truncated or snapshot.truncated
        dropped += snapshot.dropped_regions
        for region in snapshot.regions:
            by_id.setdefault(region.candidate_id, region)
    regions = sorted(by_id.values(), key=lambda region: (
        region.bbox[1], region.bbox[0], CANDIDATE_OWNERS.index(region.proposed_owner),
        region.source_stage, region.candidate_id,
    ))
    limit = max(1, int(max_regions))
    if len(regions) > limit:
        dropped += len(regions) - limit
        truncated = True
        regions = regions[:limit]
    return CandidateSnapshot(shape=shape, regions=tuple(regions), truncated=truncated, dropped_regions=dropped)


def capture_candidate_adapter_snapshot(
    specs: Sequence[Mapping[str, Any]],
    *,
    max_regions: int = 8192,
) -> CandidateSnapshot | None:
    """Freeze legacy proposal masks as non-authoritative candidate evidence.

    This is the migration seam for proven legacy guards: each adapter records
    the exact mask *before* the caller applies it, with its original provenance.
    The returned snapshot has no mutation API and does not itself cast votes or
    own output. Empty/absent proposals are skipped so adapters remain reversible.
    """
    snapshots = []
    for spec in specs:
        mask = spec.get("mask")
        if mask is None or not np.any(np.asarray(mask) > 0):
            continue
        owner = str(spec["proposed_owner"])
        snapshots.append(capture_candidate_snapshot(
            {owner: np.asarray(mask)},
            source_stage=str(spec.get("source_stage") or "legacy_proposal_pre_apply"),
            source=str(spec["source"]),
            confidence=float(spec.get("confidence", 0.9)),
            reason=str(spec.get("reason") or "converted_legacy_evidence_adapter"),
            min_area_px=int(spec.get("min_area_px", 1)),
            max_regions=int(spec.get("max_regions", max_regions)),
        ))
    return merge_candidate_snapshots(*snapshots, max_regions=max_regions)


def capture_owner_neutral_appearance_snapshot(
    rgb: np.ndarray,
    *,
    support_mask: np.ndarray | None = None,
    support_mode: str = "clip",
    min_area_px: int = 32,
    max_area_fraction: float = 0.04,
    max_regions: int = 512,
) -> CandidateSnapshot:
    """Capture high-recall source-color regions without proposing an owner.

    Coarse Lab buckets preserve connected source appearance before Paint's
    complement can swallow an otherwise missed decal.  When ``support_mask``
    is supplied it normally clips to that bounded audit support.  Experimental
    ``support_mode="seed"`` instead uses the support as a relevance seed while
    preserving the complete source-color component across current owner
    boundaries.  This makes proposal conflicts measurable without changing
    ownership, while leaving the faster proven shadow path available.
    These candidates are explicitly ``unassigned`` and therefore cast no
    ownership votes; they only make intrinsic evidence reviewable downstream.
    """
    if cv2 is None:
        raise RuntimeError("OpenCV is required for Smart TGA appearance capture")
    mode = str(support_mode).strip().lower()
    if mode not in {"clip", "seed"}:
        raise ValueError("support_mode must be 'clip' or 'seed'")
    array = np.asarray(rgb)
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError("rgb must have shape HxWx3+")
    array = np.clip(array[:, :, :3], 0, 255).astype(np.uint8, copy=False)
    height, width = array.shape[:2]
    if support_mask is None:
        support = np.ones((height, width), bool)
    else:
        support = np.asarray(support_mask) > 0
        if support.shape != (height, width):
            raise ValueError("support_mask must match rgb height and width")
    lab = cv2.cvtColor(array, cv2.COLOR_RGB2LAB)
    quantized = (
        (lab[:, :, 0].astype(np.uint16) // 64) * 16
        + (lab[:, :, 1].astype(np.uint16) // 64) * 4
        + (lab[:, :, 2].astype(np.uint16) // 64)
    )
    canvas_area = float(max(1, height * width))
    maximum = max(int(min_area_px), int(round(canvas_area * float(max_area_fraction))))
    regions: list[CandidateRegion] = []
    for bucket in np.unique(quantized[support]):
        binary = (
            (quantized == bucket)
            if mode == "seed"
            else ((quantized == bucket) & support)
        ).astype(np.uint8)
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, 8)
        for label_id in range(1, count):
            x, y, region_width, region_height, area = [int(value) for value in stats[label_id]]
            if area < max(1, int(min_area_px)) or area > maximum:
                continue
            local = labels[y:y + region_height, x:x + region_width] == label_id
            if mode == "seed" and not np.any(
                local & support[y:y + region_height, x:x + region_width]
            ):
                continue
            regions.append(CandidateRegion(
                candidate_id=(
                    f"appearance_quantized_raw:source_rgb_lab_quantized:unassigned:"
                    f"{int(bucket)}:{label_id}:{x}:{y}:{region_width}:{region_height}"
                ),
                source_stage="appearance_quantized_raw",
                source="source_rgb_lab_quantized",
                proposed_owner="unassigned",
                bbox=(x, y, region_width, region_height),
                area=area,
                centroid=(float(centroids[label_id][0]), float(centroids[label_id][1])),
                local_mask=local,
                confidence=1.0,
                reason=(
                    "owner_neutral_source_appearance_support_seeded"
                    if mode == "seed"
                    else "owner_neutral_source_appearance"
                ),
            ))
    regions.sort(key=lambda region: (-region.area, region.bbox[1], region.bbox[0], region.candidate_id))
    limit = max(1, int(max_regions))
    dropped = max(0, len(regions) - limit)
    selected = sorted(
        regions[:limit],
        key=lambda region: (region.bbox[1], region.bbox[0], -region.area, region.candidate_id),
    )
    return CandidateSnapshot(
        shape=(height, width),
        regions=tuple(selected),
        truncated=bool(dropped),
        dropped_regions=dropped,
    )


def capture_mask_evidence(
    mask: np.ndarray,
    *,
    target_owner: str,
    source_stage: str,
    source: str,
    reason: str,
    weight: float = 0.9,
    hard: bool = False,
) -> MaskEvidence | None:
    binary = np.asarray(mask) > 0
    if binary.ndim != 2:
        raise ValueError("evidence mask must be 2D")
    ys, xs = np.where(binary)
    if not len(xs):
        return None
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    local = binary[y0:y1, x0:x1]
    digest = hashlib.blake2b(
        f"{source_stage}|{source}|{target_owner}|{reason}|{x0}|{y0}|{x1}|{y1}".encode("utf-8"),
        digest_size=8,
    ).hexdigest()
    return MaskEvidence(
        evidence_id=f"e:{digest}",
        source_stage=str(source_stage),
        source=str(source),
        target_owner=target_owner,
        reason=str(reason),
        bbox=(x0, y0, x1 - x0, y1 - y0),
        area=int(np.count_nonzero(local)),
        local_mask=local,
        weight=float(weight),
        hard=bool(hard),
    )


def capture_mask_evidence_batch(
    specs: Sequence[Mapping[str, Any]],
) -> tuple[MaskEvidence, ...]:
    """Freeze a bounded family ledger, skipping absent and empty masks."""
    evidence = []
    for spec in specs:
        mask = spec.get("mask")
        if mask is None:
            continue
        item = capture_mask_evidence(
            mask,
            target_owner=str(spec["target_owner"]),
            source_stage=str(spec.get("source_stage") or "legacy_accumulated"),
            source=str(spec["source"]),
            reason=str(spec.get("reason") or "converted_guard_evidence"),
            weight=float(spec.get("weight", 0.9)),
            hard=bool(spec.get("hard", False)),
        )
        if item is not None:
            evidence.append(item)
    return tuple(evidence)


def mask_evidence_telemetry(evidence: Sequence[MaskEvidence]) -> dict[str, Any]:
    source_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}
    source_pixels: dict[str, int] = {}
    for item in evidence:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1
        owner_counts[item.target_owner] = owner_counts.get(item.target_owner, 0) + 1
        source_pixels[item.source] = source_pixels.get(item.source, 0) + item.area
    return {
        "family_count": len(evidence),
        "source_counts": dict(sorted(source_counts.items())),
        "target_owner_counts": dict(sorted(owner_counts.items())),
        "source_pixels": dict(sorted(source_pixels.items())),
    }


def proposal_signatures(snapshot: CandidateSnapshot | None, shape: tuple[int, int]) -> np.ndarray | None:
    """Return stable membership signatures used to split final masks into atoms."""
    if snapshot is None or not snapshot.regions:
        return None
    if snapshot.shape != shape:
        raise ValueError("candidate snapshot and graph shape must match")
    signatures = np.zeros(shape, np.uint64)
    for region in snapshot.regions:
        digest = hashlib.blake2b(region.candidate_id.encode("utf-8"), digest_size=8).digest()
        token = np.uint64(int.from_bytes(digest, "little") or 1)
        x, y, width, height = region.bbox
        window = signatures[y:y + height, x:x + width]
        window[region.local_mask] ^= token
    return signatures


def _overlap_counts(component_map: np.ndarray, bbox: tuple[int, int, int, int], local_mask: np.ndarray) -> dict[int, int]:
    x, y, width, height = bbox
    labels = component_map[y:y + height, x:x + width][local_mask]
    labels = labels[labels >= 0]
    if not len(labels):
        return {}
    counts = np.bincount(labels.astype(np.int64))
    return {index: int(count) for index, count in enumerate(counts) if count}


def candidate_vote_specs(
    graph: Any,
    snapshot: CandidateSnapshot | None,
    *,
    base_weight: float = 0.58,
    min_node_overlap: float = 0.80,
    max_votes: int = 8192,
) -> tuple[dict[str, Any], ...]:
    if snapshot is None:
        return ()
    if snapshot.shape != graph.shape:
        raise ValueError("candidate snapshot and graph shape must match")
    specs = []
    for region in snapshot.regions:
        if region.proposed_owner == "unassigned":
            continue
        for node_index, overlap in _overlap_counts(graph.component_map, region.bbox, region.local_mask).items():
            node = graph.nodes[node_index]
            node_overlap = overlap / float(max(1, node.area))
            if node_overlap < min_node_overlap:
                continue
            specs.append({
                "node_id": node.node_id,
                "owner": region.proposed_owner,
                "weight": float(base_weight) * float(region.confidence) * min(1.0, node_overlap),
                "source": f"initial_proposal:{region.source}",
                "reason": f"{region.source_stage}:{region.reason}",
                "hard": False,
                "support": (region.candidate_id,),
            })
            if len(specs) >= max_votes:
                return tuple(specs)
    return tuple(specs)


def mask_evidence_vote_specs(
    graph: Any,
    evidence: Sequence[MaskEvidence],
    *,
    min_node_overlap: float = 0.80,
    max_votes: int = 4096,
) -> tuple[dict[str, Any], ...]:
    # Replayed engine/route guards are correlated evidence. Aggregate by
    # node/owner/source using maximum weight so repetition cannot manufacture
    # confidence or independent-source quorum.
    aggregated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in evidence:
        for node_index, overlap in _overlap_counts(graph.component_map, item.bbox, item.local_mask).items():
            node = graph.nodes[node_index]
            node_overlap = overlap / float(max(1, node.area))
            if node_overlap < min_node_overlap:
                continue
            key = (node.node_id, item.target_owner, item.source)
            weight = float(item.weight) * min(1.0, node_overlap)
            prior = aggregated.get(key)
            reason = f"{item.source_stage}:{item.reason}"
            if prior is None:
                aggregated[key] = {
                    "node_id": node.node_id,
                    "owner": item.target_owner,
                    "weight": weight,
                    "source": item.source,
                    "reasons": {reason},
                    "hard": item.hard,
                    "support": {item.evidence_id},
                }
            else:
                prior["weight"] = max(float(prior["weight"]), weight)
                prior["hard"] = bool(prior["hard"]) or item.hard
                prior["reasons"].add(reason)
                prior["support"].add(item.evidence_id)
    specs = []
    for key in sorted(aggregated):
        item = aggregated[key]
        specs.append({
            "node_id": item["node_id"],
            "owner": item["owner"],
            "weight": item["weight"],
            "source": item["source"],
            "reason": "+".join(sorted(item["reasons"])),
            "hard": item["hard"],
            "support": tuple(sorted(item["support"])),
        })
        if len(specs) >= max_votes:
            break
    return tuple(specs)
