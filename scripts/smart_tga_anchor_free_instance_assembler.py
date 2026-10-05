"""Build immutable, owner-neutral decal hypotheses from normalized template panels.

This is an offline/shadow proposal generator.  It deliberately assigns no
semantic ownership and cannot change Smart TGA output.  Its job is to preserve
high-recall visual hypotheses (including thin-attachment splits) for later
review, training, calibration, and constrained adjudication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


DEFAULT_PANEL_MAP = Path(
    "engine/spec_sculpt/models/smart_tga_dlm_panel_map_cycle660_v1.json"
)
OPEN_HEIGHT_FRACTIONS = (0.0, 0.035, 0.06, 0.09, 0.12)
POST_ASSEMBLY_OPEN_FRACTIONS = (0.035, 0.06, 0.09, 0.12, 0.16, 0.20)


def _safe(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


def _expanded_bbox(
    bbox: list[int] | tuple[int, int, int, int],
    image_shape: tuple[int, int],
    pad_x_fraction: float = 0.25,
    pad_y_fraction: float = 0.20,
) -> tuple[int, int, int, int]:
    """Expand a normalized panel box by generic fractions, clipped to image."""
    x, y, width, height = map(int, bbox)
    image_height, image_width = image_shape
    pad_x = int(round(width * pad_x_fraction))
    pad_y = int(round(height * pad_y_fraction))
    left, top = max(0, x - pad_x), max(0, y - pad_y)
    right = min(image_width, x + width + pad_x)
    bottom = min(image_height, y + height + pad_y)
    return left, top, right - left, bottom - top


def _vertical_open(mask: np.ndarray, height_fraction: float) -> tuple[np.ndarray, int]:
    """Remove thin horizontal attachments while retaining tall decal strokes."""
    if height_fraction <= 0:
        return mask.copy(), 1
    kernel_height = max(3, int(round(mask.shape[0] * height_fraction)))
    if kernel_height % 2 == 0:
        kernel_height += 1
    kernel = np.ones((kernel_height, 1), dtype=np.uint8)
    opened = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    return opened.astype(bool), kernel_height


def _tall_components(mask: np.ndarray) -> tuple[np.ndarray, list[dict[str, int]]]:
    """Keep every substantial tall component; never select a semantic owner."""
    binary = mask.astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    height, width = mask.shape
    kept = np.zeros_like(mask, dtype=bool)
    records: list[dict[str, int]] = []
    for index in range(1, count):
        x, y, component_width, component_height, area = map(int, stats[index])
        if component_height < max(5, int(round(0.25 * height))):
            continue
        if area < max(12, int(round(0.0025 * width * height))):
            continue
        kept[labels == index] = True
        records.append({
            "x": x,
            "y": y,
            "width": component_width,
            "height": component_height,
            "area": area,
        })
    return kept, records


def _support_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    left, right = int(xs.min()), int(xs.max()) + 1
    top, bottom = int(ys.min()), int(ys.max()) + 1
    return left, top, right - left, bottom - top


def _contour_silhouette(mask: np.ndarray) -> np.ndarray:
    """Fill closed decal contours while preserving nested transparent holes.

    A palette proposal often contains only an outline color.  The enclosed
    silhouette is a separate immutable assembly hypothesis that can recover
    every source color inside that boundary during exact reconstruction.
    """
    contours, hierarchy = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE,
    )
    if hierarchy is None:
        return mask.copy()
    hierarchy = hierarchy[0]
    filled = np.zeros_like(mask, dtype=np.uint8)
    roots = [index for index in range(len(contours)) if int(hierarchy[index][3]) < 0]
    for index in roots:
        cv2.drawContours(filled, contours, index, 1, thickness=cv2.FILLED)
    # The inner edge of a colored outline is usually almost as large as its
    # outer edge and encloses the face color; filling it is intentional.  Only
    # substantially smaller nested contours are treated as genuine digit
    # holes.  Original outline pixels are restored after hole clearing.
    for index in range(len(contours)):
        parent = int(hierarchy[index][3])
        if parent < 0:
            continue
        root = parent
        while int(hierarchy[root][3]) >= 0:
            root = int(hierarchy[root][3])
        root_area = max(1.0, cv2.contourArea(contours[root]))
        if cv2.contourArea(contours[index]) / root_area <= 0.35:
            cv2.drawContours(filled, contours, index, 0, thickness=cv2.FILLED)
    filled[mask] = 1
    return filled.astype(bool)


def _silhouette_variants(mask: np.ndarray) -> list[tuple[str, np.ndarray, int]]:
    """Preserve the full silhouette and generic thin-attachment splits."""
    silhouette = _contour_silhouette(mask)
    variants = [("enclosed_multicolor_silhouette", silhouette, 1)]
    for fraction in POST_ASSEMBLY_OPEN_FRACTIONS:
        opened, kernel_height = _vertical_open(silhouette, fraction)
        opened, _ = _tall_components(opened)
        if opened.any():
            variants.append((
                "enclosed_silhouette_vertical_open",
                opened,
                kernel_height,
            ))
    return variants


def _intrinsic_score(mask: np.ndarray) -> tuple[float, dict[str, float | int]]:
    """Rank usefulness without assigning Number/Sponsor/Paint ownership."""
    bbox = _support_bbox(mask)
    if bbox is None:
        return -1.0, {}
    x, y, width, height = bbox
    panel_height, panel_width = mask.shape
    area = int(mask.sum())
    bbox_area = max(1, width * height)
    height_fraction = height / panel_height
    width_fraction = width / panel_width
    occupancy = area / bbox_area
    panel_fraction = area / max(1, panel_width * panel_height)
    border_touches = sum((x == 0, y == 0, x + width == panel_width, y + height == panel_height))
    density_preference = max(0.0, 1.0 - abs(occupancy - 0.45) / 0.45)
    score = (
        0.43 * min(1.0, height_fraction / 0.72)
        + 0.21 * min(1.0, width_fraction / 0.55)
        + 0.16 * density_preference
        + 0.12 * (1.0 - border_touches / 4.0)
        + 0.08 * max(0.0, 1.0 - panel_fraction / 0.48)
    )
    if panel_fraction > 0.55:
        score -= 0.30
    return float(score), {
        "pixel_area": area,
        "bbox_area": bbox_area,
        "height_fraction": round(height_fraction, 7),
        "width_fraction": round(width_fraction, 7),
        "bbox_occupancy": round(occupancy, 7),
        "panel_occupancy": round(panel_fraction, 7),
        "border_touches": int(border_touches),
    }


def _edge_enclosed_hypotheses(
    crop: np.ndarray,
    panel_name: str,
    panel_bbox: list[int] | tuple[int, int, int, int],
    expanded: tuple[int, int, int, int],
) -> list[dict]:
    """Propose edge-enclosed regions when decal and body share palette colors."""
    height, width = crop.shape[:2]
    lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
    edges = np.zeros((height, width), dtype=np.uint8)
    for channel in range(3):
        edges = cv2.bitwise_or(edges, cv2.Canny(lab[:, :, channel], 35, 100))
    barrier = cv2.morphologyEx(
        edges, cv2.MORPH_CLOSE, np.ones((3, 3), dtype=np.uint8)
    )
    barrier = cv2.dilate(barrier, np.ones((3, 3), dtype=np.uint8))
    free = (barrier == 0).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(free, 8)
    minimum_area = max(30, int(round(height * width * 0.004)))
    components: list[dict] = []
    for component_id in range(1, count):
        x, y, component_width, component_height, area = map(int, stats[component_id])
        touches_border = (
            x == 0
            or y == 0
            or x + component_width == width
            or y + component_height == height
        )
        if touches_border or area < minimum_area or component_height < 0.18 * height:
            continue
        components.append(
            {
                "component_id": component_id,
                "x": x,
                "y": y,
                "width": component_width,
                "height": component_height,
                "area": area,
            }
        )

    major = [
        component
        for component in components
        if component["height"] >= 0.28 * height
        and component["area"] >= 0.012 * height * width
        and component["width"] >= 0.06 * width
    ]
    proposal_masks: list[tuple[str, np.ndarray, list[dict]]] = []
    for index, component in enumerate(major):
        proposal_masks.append(
            (f"C{index}", labels == component["component_id"], [component])
        )

    # Corroborative geometry groups near-aligned enclosed regions without
    # assigning a digit count, semantic class, or owner.
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(major))}
    for first_index, first in enumerate(major):
        first_right = first["x"] + first["width"]
        first_bottom = first["y"] + first["height"]
        for second_index in range(first_index + 1, len(major)):
            second = major[second_index]
            second_right = second["x"] + second["width"]
            second_bottom = second["y"] + second["height"]
            vertical_overlap = max(
                0,
                min(first_bottom, second_bottom) - max(first["y"], second["y"]),
            )
            overlap_fraction = vertical_overlap / max(
                1, min(first["height"], second["height"])
            )
            horizontal_gap = max(
                0,
                max(first["x"], second["x"]) - min(first_right, second_right),
            )
            height_ratio = min(first["height"], second["height"]) / max(
                1, max(first["height"], second["height"])
            )
            if (
                overlap_fraction >= 0.55
                and horizontal_gap <= 0.25 * width
                and height_ratio >= 0.55
            ):
                adjacency[first_index].add(second_index)
                adjacency[second_index].add(first_index)

    unseen = set(adjacency)
    group_index = 0
    while unseen:
        start = unseen.pop()
        stack, group = [start], {start}
        while stack:
            current = stack.pop()
            for peer in adjacency[current]:
                if peer in unseen:
                    unseen.remove(peer)
                    group.add(peer)
                    stack.append(peer)
        if len(group) < 2:
            continue
        members = [major[index] for index in sorted(group)]
        group_mask = np.isin(
            labels, [component["component_id"] for component in members]
        )
        proposal_masks.append((f"G{group_index}", group_mask, members))
        group_index += 1

    left, top, _, _ = expanded
    hypotheses = []
    for code, support, members in proposal_masks:
        bbox = _support_bbox(support)
        if bbox is None:
            continue
        score, features = _intrinsic_score(support)
        digest = hashlib.sha1(np.packbits(support).tobytes()).hexdigest()[:12]
        sx, sy, sw, sh = bbox
        hypotheses.append(
            {
                "proposal_id": f"{panel_name}:E:{code}:{digest}",
                "panel_name": panel_name,
                "panel_bbox": list(map(int, panel_bbox)),
                "expanded_panel_bbox": list(expanded),
                "proposal_bbox": [left + sx, top + sy, sw, sh],
                "support": support,
                "intrinsic_score": score,
                "rank_score": score,
                "features": features,
                "provenance": {
                    "generator": "lab_edge_enclosed_region_v1",
                    "assembly_variant": (
                        "edge_enclosed_group"
                        if code.startswith("G")
                        else "edge_enclosed_region"
                    ),
                    "canny_low": 35,
                    "canny_high": 100,
                    "barrier_close_kernel": 3,
                    "barrier_dilate_kernel": 3,
                    "enclosed_components": members,
                    "template_position_evidence": "normalized_panel_proposal_only",
                    "relationship_authority": False,
                },
                "owner_neutral": True,
                "semantic_label": None,
                "ownership_authority": False,
                "output_authority": False,
            }
        )
    return hypotheses


def _normalized_mask(mask: np.ndarray, size: int = 64) -> np.ndarray:
    bbox = _support_bbox(mask)
    canvas = np.zeros((size, size), dtype=bool)
    if bbox is None:
        return canvas
    x, y, width, height = bbox
    crop = mask[y:y + height, x:x + width].astype(np.uint8)
    scale = min((size - 6) / max(1, width), (size - 6) / max(1, height))
    out_width = max(1, int(round(width * scale)))
    out_height = max(1, int(round(height * scale)))
    resized = cv2.resize(crop, (out_width, out_height), interpolation=cv2.INTER_NEAREST) > 0
    left, top = (size - out_width) // 2, (size - out_height) // 2
    canvas[top:top + out_height, left:left + out_width] = resized
    return canvas


def _d4_similarity(first: np.ndarray, second: np.ndarray) -> float:
    """Best Dice similarity across rotations and mirrors."""
    first = _normalized_mask(first)
    second = _normalized_mask(second)
    best = 0.0
    for turns in range(4):
        rotated = np.rot90(second, turns)
        for transformed in (rotated, np.fliplr(rotated)):
            overlap = int(np.logical_and(first, transformed).sum())
            denom = int(first.sum() + transformed.sum())
            best = max(best, 2.0 * overlap / max(1, denom))
    return float(best)


def assemble_panel_hypotheses(
    rgb: np.ndarray,
    panel_name: str,
    panel_bbox: list[int] | tuple[int, int, int, int],
    seed: int = 739,
    clusters: int = 8,
) -> list[dict]:
    """Return immutable color-role/stroke hypotheses for one normalized panel."""
    expanded = _expanded_bbox(panel_bbox, rgb.shape[:2])
    left, top, width, height = expanded
    crop = rgb[top:top + height, left:left + width]
    lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
    samples = lab.reshape(-1, 3).astype(np.float32)
    cv2.setRNGSeed(int(seed))
    _, assignments, centers = cv2.kmeans(
        samples,
        clusters,
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 60, 0.2),
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    order = np.argsort(centers[:, 0])
    hypotheses: list[dict] = []
    for lightness_rank, cluster_index in enumerate(order):
        cluster_mask = assignments.reshape(height, width) == int(cluster_index)
        for open_fraction in OPEN_HEIGHT_FRACTIONS:
            opened, kernel_height = _vertical_open(cluster_mask, open_fraction)
            support, components = _tall_components(opened)
            support_bbox = _support_bbox(support)
            if support_bbox is None:
                continue
            score, features = _intrinsic_score(support)
            if features["height_fraction"] < 0.28:
                continue
            variants = [("raw_palette_role", support, 1), *_silhouette_variants(support)]
            for variant, variant_support, post_kernel_height in variants:
                variant_bbox = _support_bbox(variant_support)
                if variant_bbox is None:
                    continue
                variant_score, variant_features = _intrinsic_score(variant_support)
                digest = hashlib.sha1(np.packbits(variant_support).tobytes()).hexdigest()[:12]
                code = {
                    "raw_palette_role": "R",
                    "enclosed_multicolor_silhouette": "S",
                    "enclosed_silhouette_vertical_open": f"T{post_kernel_height}",
                }[variant]
                proposal_id = f"{panel_name}:L{lightness_rank}:V{kernel_height}:{code}:{digest}"
                sx, sy, sw, sh = variant_bbox
                hypotheses.append({
                    "proposal_id": proposal_id,
                    "panel_name": panel_name,
                    "panel_bbox": list(map(int, panel_bbox)),
                    "expanded_panel_bbox": list(expanded),
                    "proposal_bbox": [left + sx, top + sy, sw, sh],
                    "support": variant_support,
                    "intrinsic_score": variant_score,
                    "rank_score": variant_score,
                    "features": variant_features,
                    "provenance": {
                        "generator": "lab_cluster_tall_component_v2",
                        "assembly_variant": variant,
                        "post_assembly_vertical_open_kernel_height": post_kernel_height,
                        "lab_lightness_rank": int(lightness_rank),
                        "lab_center": [round(float(value), 5) for value in centers[cluster_index]],
                        "vertical_open_fraction": open_fraction,
                        "vertical_open_kernel_height": kernel_height,
                        "retained_components": components,
                        "template_position_evidence": "normalized_panel_proposal_only",
                        "relationship_authority": False,
                    },
                    "owner_neutral": True,
                    "semantic_label": None,
                    "ownership_authority": False,
                    "output_authority": False,
                })
    hypotheses.extend(_edge_enclosed_hypotheses(crop, panel_name, panel_bbox, expanded))
    return hypotheses


def _add_cross_panel_corroboration(hypotheses: list[dict]) -> None:
    # Morphology variants often produce byte-identical masks. Compare each
    # panel-local exact family once, then fan the corroborative score back to
    # every immutable member instead of spending O(raw proposals squared).
    families: dict[tuple[str, str], list[dict]] = {}
    for row in hypotheses:
        digest = hashlib.sha1(
            np.asarray(row["support"].shape, dtype=np.int32).tobytes()
            + np.packbits(row["support"]).tobytes()
        ).hexdigest()
        families.setdefault((row["panel_name"], digest), []).append(row)
    representatives = [members[0] for members in families.values()]
    family_results: dict[tuple[str, str], tuple[float, str | None]] = {}
    for family_key, members in families.items():
        row = members[0]
        best_similarity, best_peer = -1.0, None
        for peer in representatives:
            if peer["panel_name"] == row["panel_name"]:
                continue
            similarity = _d4_similarity(row["support"], peer["support"])
            if similarity > best_similarity:
                best_similarity, best_peer = similarity, peer["proposal_id"]
        family_results[family_key] = (best_similarity, best_peer)
    for family_key, members in families.items():
        best_similarity, best_peer = family_results[family_key]
        for row in members:
            row["corroborative_d4_similarity"] = round(max(0.0, best_similarity), 7)
            row["corroborative_peer_id"] = best_peer
            row["rank_score"] = float(
                row["intrinsic_score"] + 0.22 * max(0.0, best_similarity - 0.30)
            )
            row["relationship_authority"] = False


def assemble_image_hypotheses(
    rgb: np.ndarray,
    panel_map: dict,
    seed: int = 739,
) -> list[dict]:
    hypotheses: list[dict] = []
    for panel in panel_map.get("number_blocks", []):
        # The tiny nose block cannot support stable cluster assembly at 1024.
        if int(panel.get("area", 0)) < 4000:
            continue
        hypotheses.extend(assemble_panel_hypotheses(
            rgb,
            panel["name"],
            panel["bbox"],
            seed=seed,
        ))
    _add_cross_panel_corroboration(hypotheses)
    hypotheses.sort(key=lambda row: row["rank_score"], reverse=True)
    return hypotheses


def _store_exact(output: Path, paint: str, hypotheses: list[dict]) -> str:
    packed_parts, offsets, lengths, shapes, bboxes, ids = [], [], [], [], [], []
    cursor = 0
    for row in hypotheses:
        packed = np.packbits(row["support"].reshape(-1))
        packed_parts.append(packed)
        offsets.append(cursor)
        lengths.append(len(packed))
        shapes.append(row["support"].shape)
        bboxes.append(row["expanded_panel_bbox"])
        ids.append(row["proposal_id"])
        cursor += len(packed)
    path = output / f"{_safe(paint)}_anchor_free_exact.npz"
    np.savez_compressed(
        path,
        packed=np.concatenate(packed_parts) if packed_parts else np.zeros(0, np.uint8),
        offsets=np.asarray(offsets, np.int64),
        lengths=np.asarray(lengths, np.int64),
        shapes=np.asarray(shapes, np.int32),
        expanded_panel_bboxes=np.asarray(bboxes, np.int32),
        proposal_ids=np.asarray(ids),
    )
    return str(path.resolve())


def _public_row(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "support"}


def _render_review(rgb: np.ndarray, paint: str, hypotheses: list[dict], output: Path) -> str:
    panels = []
    for panel_name in sorted({row["panel_name"] for row in hypotheses}):
        rows = [row for row in hypotheses if row["panel_name"] == panel_name][:12]
        panels.append((panel_name, rows))
    tile_width, tile_height, columns = 230, 185, 4
    source_height = 430
    rows_total = sum(math.ceil(len(rows) / columns) for _, rows in panels)
    canvas = Image.new("RGB", (tile_width * columns, source_height + rows_total * tile_height), (14, 16, 20))
    draw = ImageDraw.Draw(canvas)
    source = Image.fromarray(rgb)
    source.thumbnail((420, 400), Image.Resampling.LANCZOS)
    canvas.paste(source, (10, 25))
    draw.text((445, 30), f"{paint}\nowner-neutral anchor-free hypotheses\nNO OUTPUT AUTHORITY", fill=(240, 242, 246))
    cursor_y = source_height
    for panel_name, rows in panels:
        for index, row in enumerate(rows):
            x = (index % columns) * tile_width
            y = cursor_y + (index // columns) * tile_height
            left, top, width, height = row["expanded_panel_bbox"]
            crop = rgb[top:top + height, left:left + width].copy()
            crop[~row["support"]] = 0
            tile = Image.fromarray(crop)
            tile.thumbnail((tile_width - 10, tile_height - 49), Image.Resampling.NEAREST)
            canvas.paste(tile, (x + (tile_width - tile.width) // 2, y + 45))
            draw.text(
                (x + 4, y + 3),
                f"{panel_name} #{index}\nrank={row['rank_score']:.3f} D4={row['corroborative_d4_similarity']:.3f}",
                fill=(236, 239, 244),
            )
        cursor_y += math.ceil(len(rows) / columns) * tile_height
    path = output / f"{_safe(paint)}_review.png"
    canvas.save(path)
    return str(path.resolve())


def _render_edge_review(
    rgb: np.ndarray, paint: str, hypotheses: list[dict], output: Path
) -> str | None:
    rows = [
        row
        for row in hypotheses
        if row.get("provenance", {}).get("generator")
        == "lab_edge_enclosed_region_v1"
    ]
    if not rows:
        return None
    tile_width, tile_height, columns = 290, 205, 4
    row_count = math.ceil(len(rows) / columns)
    canvas = Image.new(
        "RGB", (tile_width * columns, tile_height * row_count), (14, 16, 20)
    )
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(rows):
        x = (index % columns) * tile_width
        y = (index // columns) * tile_height
        left, top, width, height = row["expanded_panel_bbox"]
        crop = rgb[top : top + height, left : left + width].copy()
        crop[~row["support"]] = 0
        tile = Image.fromarray(crop)
        tile.thumbnail((tile_width - 12, tile_height - 60), Image.Resampling.NEAREST)
        canvas.paste(tile, (x + (tile_width - tile.width) // 2, y + 55))
        draw.text(
            (x + 4, y + 3),
            f"{row['panel_name']}\n{row['proposal_id'].split(':', 1)[1]}\n"
            f"rank={row['rank_score']:.3f} bbox={row['proposal_bbox']}",
            fill=(236, 239, 244),
        )
    path = output / f"{_safe(paint)}_edge_enclosed_review.png"
    canvas.save(path)
    return str(path.resolve())


def _load_inputs(manifest: Path | None, paint_args: list[str]) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    if manifest:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        for row in payload.get("records", []):
            sources[row["paint_label"]] = Path(row["source_1024"])
    for value in paint_args:
        if "=" not in value:
            raise ValueError("--paint must be LABEL=PATH")
        label, path = value.split("=", 1)
        sources[label] = Path(path)
    if not sources:
        raise ValueError("provide --manifest or at least one --paint LABEL=PATH")
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--paint", action="append", default=[], help="LABEL=PATH; repeatable")
    parser.add_argument("--panel-map", type=Path, default=DEFAULT_PANEL_MAP)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=739)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    panel_map = json.loads(args.panel_map.read_text(encoding="utf-8"))
    records = []
    for paint, source in _load_inputs(args.manifest, args.paint).items():
        pil = Image.open(source).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS)
        rgb = np.asarray(pil)
        hypotheses = assemble_image_hypotheses(rgb, panel_map, seed=args.seed)
        exact_path = _store_exact(args.output, paint, hypotheses)
        review_path = _render_review(rgb, paint, hypotheses, args.output)
        edge_review_path = _render_edge_review(rgb, paint, hypotheses, args.output)
        records.append({
            "paint_label": paint,
            "source": str(source.resolve()),
            "hypothesis_count": len(hypotheses),
            "exact_hypotheses": exact_path,
            "review_sheet": review_path,
            "edge_review_sheet": edge_review_path,
            "hypotheses": [_public_row(row) for row in hypotheses],
        })
    ledger = {
        "schema": "smart_tga_anchor_free_instance_assembler_v2",
        "seed": args.seed,
        "panel_map": str(args.panel_map.resolve()),
        "owner_neutral": True,
        "output_authority": False,
        "relationship_authority": False,
        "records": records,
    }
    path = args.output / "assembly_ledger.json"
    path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(json.dumps({
        "ledger": str(path.resolve()),
        "paints": len(records),
        "hypotheses": sum(row["hypothesis_count"] for row in records),
        "output_authority": False,
    }, indent=2))


if __name__ == "__main__":
    main()
