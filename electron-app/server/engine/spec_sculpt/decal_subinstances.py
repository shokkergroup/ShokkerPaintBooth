"""Owner-neutral foreground hypotheses inside immutable Smart TGA instances.

Mixed decal panels are a recurring DLM failure: a proposal may contain a flat
backing panel, the actual glyph/logo ink, and trim. This module preserves the
parent mask and derives strict-subset observations only. It never selects an
owner, casts a vote, or adds pixels.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from engine.spec_sculpt.decal_palette_roles import derive_palette_role_masks


@dataclass(frozen=True)
class IntrinsicSubinstance:
    hypothesis: str
    source_role: str
    local_mask: np.ndarray = field(repr=False, compare=False)
    bbox: tuple[int, int, int, int]
    area: int
    parent_fraction: float
    component_count: int

    def __post_init__(self) -> None:
        mask = np.ascontiguousarray(np.asarray(self.local_mask) > 0)
        if mask.ndim != 2 or int(np.count_nonzero(mask)) != int(self.area):
            raise ValueError("intrinsic subinstance mask area mismatch")
        if self.area <= 0 or not (0.0 < float(self.parent_fraction) < 1.0):
            raise ValueError("intrinsic subinstance must be a strict parent subset")
        ys, xs = np.where(mask)
        expected = (int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
        if tuple(self.bbox) != expected:
            raise ValueError("intrinsic subinstance bbox mismatch")
        mask.setflags(write=False)
        object.__setattr__(self, "local_mask", mask)


def _bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def _connected(mask: np.ndarray) -> list[dict[str, object]]:
    if cv2 is None:
        raise RuntimeError("OpenCV is required for intrinsic decal subinstances")
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    items = []
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        x, y, width, height = [int(value) for value in stats[index, :4]]
        items.append({
            "mask": labels == index,
            "area": area,
            "bbox": (x, y, width, height),
            "center": (float(centroids[index, 0]), float(centroids[index, 1])),
        })
    return items


def _line_groups(items: list[dict[str, object]], parent_width: int) -> list[list[dict[str, object]]]:
    """Group glyph-like components that occupy the same visual text line."""
    if len(items) < 2:
        return []
    adjacency = [set() for _ in items]
    for left_index, left in enumerate(items):
        lx, ly, lw, lh = left["bbox"]
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            rx, ry, rw, rh = right["bbox"]
            vertical_overlap = max(0, min(ly + lh, ry + rh) - max(ly, ry))
            aligned = vertical_overlap / float(max(1, min(lh, rh))) >= 0.28
            horizontal_gap = max(0, max(lx, rx) - min(lx + lw, rx + rw))
            close = horizontal_gap <= max(6.0, parent_width * 0.14, 2.2 * max(lh, rh))
            if aligned and close:
                adjacency[left_index].add(right_index)
                adjacency[right_index].add(left_index)
    groups = []
    seen = set()
    for start in range(len(items)):
        if start in seen:
            continue
        stack = [start]
        group = []
        while stack:
            index = stack.pop()
            if index in seen:
                continue
            seen.add(index)
            group.append(items[index])
            stack.extend(adjacency[index] - seen)
        if len(group) >= 2:
            groups.append(group)
    return groups


def derive_intrinsic_subinstances(
    rgb: np.ndarray,
    parent_mask: np.ndarray,
    *,
    min_pixels: int = 20,
    min_parent_fraction: float = 0.003,
    max_parent_fraction: float = 0.92,
    max_per_role: int = 12,
) -> tuple[IntrinsicSubinstance, ...]:
    """Derive connected and assembled foreground hypotheses from palette roles."""
    image = np.asarray(rgb)
    parent = np.ascontiguousarray(np.asarray(parent_mask) > 0)
    if image.ndim != 3 or image.shape[:2] != parent.shape or image.shape[2] < 3:
        raise ValueError("subinstances require matching RGB and parent mask")
    parent_area = int(np.count_nonzero(parent))
    if parent_area < max(2, int(min_pixels)):
        return ()
    if cv2 is None:
        raise RuntimeError("OpenCV is required for intrinsic decal subinstances")
    eroded = cv2.erode(
        parent.astype(np.uint8), np.ones((3, 3), np.uint8),
        borderType=cv2.BORDER_CONSTANT, borderValue=0,
    ).astype(bool)
    boundary = parent & ~eroded
    candidates: list[tuple[str, str, np.ndarray, int]] = []
    threshold = max(int(min_pixels), int(round(parent_area * float(min_parent_fraction))))
    for role in derive_palette_role_masks(image, parent, min_pixels=min_pixels, min_parent_fraction=min_parent_fraction):
        components = [item for item in _connected(role.local_mask) if int(item["area"]) >= threshold]
        components.sort(key=lambda item: (-int(item["area"]), tuple(item["bbox"])))
        for index, item in enumerate(components[:max_per_role]):
            candidates.append((f"{role.role}:component:{index}", role.role, item["mask"], 1))

        interior = []
        for item in components:
            mask = item["mask"]
            touch_fraction = int(np.count_nonzero(mask & boundary)) / float(max(1, int(item["area"])))
            # Long backing borders can touch only one outer edge, so their
            # boundary ratio may still look numerically modest. Keep this
            # threshold conservative; interior glyphs normally have zero.
            if touch_fraction <= 0.08:
                interior.append(item)
        if len(interior) >= 2:
            union = np.logical_or.reduce([item["mask"] for item in interior])
            candidates.append((f"{role.role}:interior_union", role.role, union, len(interior)))

        for index, group in enumerate(_line_groups(interior or components, parent.shape[1])):
            union = np.logical_or.reduce([item["mask"] for item in group])
            candidates.append((f"{role.role}:line:{index}", role.role, union, len(group)))

    results = []
    seen = set()
    for hypothesis, source_role, mask, component_count in candidates:
        mask = np.ascontiguousarray(mask & parent)
        area = int(np.count_nonzero(mask))
        fraction = area / float(parent_area)
        if area < threshold or not (float(min_parent_fraction) <= fraction <= float(max_parent_fraction)):
            continue
        fingerprint = np.packbits(mask.reshape(-1)).tobytes()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        results.append(IntrinsicSubinstance(
            hypothesis=hypothesis,
            source_role=source_role,
            local_mask=mask,
            bbox=_bbox(mask),
            area=area,
            parent_fraction=round(fraction, 6),
            component_count=int(component_count),
        ))
    results.sort(key=lambda item: (item.source_role, -item.area, item.hypothesis))
    return tuple(results)


__all__ = ["IntrinsicSubinstance", "derive_intrinsic_subinstances"]
