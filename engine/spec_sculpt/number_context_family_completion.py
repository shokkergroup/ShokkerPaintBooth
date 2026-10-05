"""Owner-neutral local assembly proposals for fragmented decal families."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

import numpy as np


def _gap(left: Sequence[int], right: Sequence[int]) -> tuple[int, int]:
    lx, ly, lw, lh = (int(value) for value in left)
    rx, ry, rw, rh = (int(value) for value in right)
    dx = max(0, max(lx, rx) - min(lx + lw, rx + rw))
    dy = max(0, max(ly, ry) - min(ly + lh, ry + rh))
    return dx, dy


def family_completion_candidates(
    canvas_shape: Sequence[int],
    layer_masks: Mapping[str, np.ndarray],
    components: Sequence[Mapping[str, Any]],
    *,
    min_atom_pixels: int = 20,
    min_group_pixels: int = 400,
    max_members: int = 8,
) -> tuple[dict[str, Any], ...]:
    """Assemble nearby immutable atoms without consulting their proposed owner.

    Geometry creates candidates only.  It never classifies or assigns pixels,
    and source layers survive solely as provenance for review/rollback.
    """
    height, width = int(canvas_shape[0]), int(canvas_shape[1])
    atoms = []
    for item in components:
        source_layer = str(item.get("layer") or "")
        if source_layer not in layer_masks:
            continue
        x, y, box_width, box_height = (int(value) for value in item["bbox"])
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(width, x + box_width), min(height, y + box_height)
        if x1 <= x0 or y1 <= y0:
            continue
        local = np.ascontiguousarray(np.asarray(layer_masks[source_layer], bool)[y0:y1, x0:x1])
        pixels = int(np.count_nonzero(local))
        if pixels < min_atom_pixels:
            continue
        atoms.append({
            "bbox": (x0, y0, x1 - x0, y1 - y0), "mask": local, "pixels": pixels,
            "provenance": {"source_layer": source_layer,
                           "component_index": int(item.get("component_index", -1)),
                           "component_pixels": pixels},
        })

    results: dict[str, dict[str, Any]] = {}
    canvas_area = float(max(1, width * height))
    for seed_index, seed in enumerate(atoms):
        sx, sy, sw, sh = seed["bbox"]
        neighbors = []
        for index, atom in enumerate(atoms):
            if index == seed_index:
                continue
            ax, ay, aw, ah = atom["bbox"]
            dx, dy = _gap(seed["bbox"], atom["bbox"])
            horizontal_gate = max(14, int(0.45 * max(sw, aw)))
            vertical_gate = max(14, int(0.45 * max(sh, ah)))
            if dx > horizontal_gate or dy > vertical_gate:
                continue
            x0, y0 = min(sx, ax), min(sy, ay)
            x1, y1 = max(sx + sw, ax + aw), max(sy + sh, ay + ah)
            if (x1 - x0) * (y1 - y0) / canvas_area > 0.085:
                continue
            distance = float(np.hypot(dx / max(1, horizontal_gate), dy / max(1, vertical_gate)))
            neighbors.append((distance, index))
        if not neighbors:
            continue
        member_indices = [seed_index] + [index for _distance, index in sorted(neighbors)[:max_members - 1]]
        # Emit progressively larger local hypotheses; no single greedy union is authoritative.
        for member_count in range(2, len(member_indices) + 1):
            chosen = [atoms[index] for index in member_indices[:member_count]]
            x0 = min(item["bbox"][0] for item in chosen)
            y0 = min(item["bbox"][1] for item in chosen)
            x1 = max(item["bbox"][0] + item["bbox"][2] for item in chosen)
            y1 = max(item["bbox"][1] + item["bbox"][3] for item in chosen)
            local = np.zeros((y1 - y0, x1 - x0), bool)
            for item in chosen:
                x, y, box_width, box_height = item["bbox"]
                local[y - y0:y - y0 + box_height, x - x0:x - x0 + box_width] |= item["mask"]
            pixels = int(np.count_nonzero(local))
            if pixels < min_group_pixels:
                continue
            digest = hashlib.sha256()
            digest.update(np.ascontiguousarray(local).tobytes())
            digest.update(f"{x0},{y0},{x1-x0},{y1-y0}".encode("utf-8"))
            proposal_id = "ncf:" + digest.hexdigest()[:16]
            if proposal_id in results:
                continue
            local.setflags(write=False)
            results[proposal_id] = {
                "proposal_id": proposal_id,
                "proposal_bbox": [x0, y0, x1 - x0, y1 - y0],
                "raw_support": local,
                "member_count": member_count,
                "member_provenance": tuple(item["provenance"] for item in chosen),
                "owner_neutral": True,
                "ownership_authority": False,
                "assembly_authority": False,
            }
    return tuple(results.values())


__all__ = ["family_completion_candidates"]
