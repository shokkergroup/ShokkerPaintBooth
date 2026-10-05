"""Bootstrap visually auditable pixel labels inside reviewed Number boxes.

Reviewed boxes are annotation supervision only.  They are never exported as
runtime features.  Raw immutable proposal masks provide foreground seeds;
GrabCut completes connected number ink while the reviewed box intersection
constrains annotation background.  Controls receive an explicit empty mask.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw

try:
    from engine.spec_sculpt.decal_instances import (
        decode_instance_mask_rle, encode_instance_mask_rle,
    )
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import (  # type: ignore
        decode_instance_mask_rle, encode_instance_mask_rle,
    )
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches  # type: ignore


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _intersection(left: Sequence[int], right: Sequence[int]) -> tuple[int, int, int, int] | None:
    lx, ly, lw, lh = (int(value) for value in left)
    rx, ry, rw, rh = (int(value) for value in right)
    x0, y0 = max(lx, rx), max(ly, ry)
    x1, y1 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _connected_to_seed(candidate: np.ndarray, seed: np.ndarray) -> np.ndarray:
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        np.asarray(candidate, np.uint8), 8,
    )
    result = np.zeros(candidate.shape, bool)
    for label in range(1, count):
        component = labels == label
        if int(stats[label, cv2.CC_STAT_AREA]) >= 4 and np.any(component & seed):
            result |= component
    return result


def _prune_annotation_components(mask: np.ndarray, roi: np.ndarray) -> np.ndarray:
    """Drop detached sponsor letters, strips, and crumbs from a Number label."""
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        np.asarray(mask, np.uint8), 8,
    )
    if count <= 1:
        return np.asarray(mask, bool)
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest_label = int(np.argmax(areas)) + 1
    largest_area = int(areas[largest_label - 1])
    rows, columns = np.nonzero(roi)
    roi_x0, roi_x1 = int(columns.min()), int(columns.max())
    roi_y0, roi_y1 = int(rows.min()), int(rows.max())
    roi_center = np.asarray([(roi_x0 + roi_x1) / 2.0, (roi_y0 + roi_y1) / 2.0])
    roi_diagonal = max(1.0, float(np.hypot(roi_x1 - roi_x0, roi_y1 - roi_y0)))
    result = np.zeros(mask.shape, bool)
    for label in range(1, count):
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])
        area = int(stats[label, cv2.CC_STAT_AREA])
        distance = float(np.linalg.norm(centroids[label] - roi_center)) / roi_diagonal
        touches_roi_edge = (
            x <= roi_x0 + 1 or y <= roi_y0 + 1
            or x + width >= roi_x1 or y + height >= roi_y1
        )
        thin_strip = min(width, height) / max(width, height) < 0.08
        keep = label == largest_label or (
            area >= max(12, int(largest_area * 0.12))
            and distance <= 0.42
            and not thin_strip
            and not (touches_roi_edge and area < largest_area * 0.50)
        )
        if keep:
            result |= labels == label
    return result


def bootstrap_mask(
    rgb: np.ndarray, proposal_bbox: Sequence[int], reviewed_bbox: Sequence[int],
    raw_seed: np.ndarray, border_seed: np.ndarray | None = None, *, iterations: int = 7,
) -> np.ndarray:
    """Return an immutable proposal-local annotation mask."""
    px, py, width, height = (int(value) for value in proposal_bbox)
    crop = np.ascontiguousarray(rgb[py:py + height, px:px + width, :3], dtype=np.uint8)
    if crop.shape[:2] != (height, width):
        raise ValueError("proposal bbox must be inside source")
    overlap = _intersection(proposal_bbox, reviewed_bbox)
    if overlap is None:
        result = np.zeros((height, width), bool)
        result.setflags(write=False)
        return result
    x0, y0, x1, y1 = overlap
    roi = np.zeros((height, width), bool)
    roi[y0 - py:y1 - py, x0 - px:x1 - px] = True
    raw = np.asarray(raw_seed, bool) & roi
    seed = raw.copy()
    if border_seed is not None and np.any(raw):
        near_raw = cv2.dilate(raw.astype(np.uint8), np.ones((55, 55), np.uint8)) > 0
        seed |= np.asarray(border_seed, bool) & roi & near_raw
    if not np.any(seed):
        result = np.zeros((height, width), bool)
        result.setflags(write=False)
        return result

    labels = np.full((height, width), cv2.GC_BGD, np.uint8)
    labels[roi] = cv2.GC_PR_BGD
    # A small expansion makes anti-aliased outline pixels eligible without
    # claiming unrelated regions.  Only seed-connected output survives.
    eligible = cv2.dilate(seed.astype(np.uint8), np.ones((39, 39), np.uint8)) > 0
    labels[roi & eligible] = cv2.GC_PR_FGD
    labels[seed] = cv2.GC_FGD
    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(
        crop, labels, None, background_model, foreground_model,
        max(1, int(iterations)), cv2.GC_INIT_WITH_MASK,
    )
    candidate = ((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD)) & roi
    result = _connected_to_seed(candidate, seed) | seed
    result = cv2.morphologyEx(
        result.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8),
    ) > 0
    result &= roi
    result = _prune_annotation_components(result, roi)
    result = np.ascontiguousarray(result)
    result.setflags(write=False)
    return result


def _render(source: Image.Image, bbox: Sequence[int], mask: np.ndarray, output: Path) -> None:
    x, y, width, height = (int(value) for value in bbox)
    crop = source.crop((x, y, x + width, y + height)).convert("RGB")
    rgb = np.asarray(crop).copy()
    tint = np.zeros_like(rgb)
    tint[..., 0], tint[..., 1], tint[..., 2] = 30, 240, 100
    rgb[mask] = (0.38 * rgb[mask] + 0.62 * tint[mask]).astype(np.uint8)
    overlay = Image.fromarray(rgb)
    canvas = Image.new("RGB", (width * 2, height + 28), (15, 17, 22))
    canvas.paste(crop, (0, 28))
    canvas.paste(overlay, (width, 28))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 7), "SOURCE", fill=(245, 220, 100))
    draw.text((width + 8, 7), "BOOTSTRAPPED EXACT-NUMBER LABEL", fill=(110, 245, 150))
    canvas.save(output)


def run(
    queue_path: Path, probe_paths: Sequence[Path], labels_dir: Path, output_dir: Path,
    review_manifest: Path | None = None,
) -> dict[str, Any]:
    queue = _read(queue_path)["queue"]
    review_modes = {
        (int(item["cycle"]), str(item["paint_label"]), str(item["proposal_id"])): str(item["mode"])
        for item in (_read(review_manifest).get("records", []) if review_manifest else [])
    }
    masks_by_key = {
        (int(probe["cycle"]), str(record["paint_label"]), str(record["proposal_id"])):
            record["mask_rle"]
        for probe in (_read(path) for path in probe_paths)
        for record in probe["records"]
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for index, item in enumerate(queue, 1):
        cycle = int(item["cycle"])
        positives, _negatives = _labels(labels_dir, cycle)
        matching = [
            label for label in positives
            if label["paint_label"] == item["paint_label"]
            and _matches(item["proposal_bbox"], label["bbox"])
        ]
        source = Image.open(item["source_1024"]).convert("RGB")
        mode = review_modes.get(
            (cycle, item["paint_label"], item["proposal_id"]),
            "raw_core" if item["target_bbox_matches"] > 0 else "empty_control",
        )
        if item["target_bbox_matches"] > 0 and matching and mode != "exclude_uncertain":
            reviewed = max(
                matching,
                key=lambda label: np.prod(
                    (lambda overlap: (overlap[2] - overlap[0], overlap[3] - overlap[1]))(
                        _intersection(item["proposal_bbox"], label["bbox"])
                    )
                ),
            )
            hypothesis_rle = masks_by_key[(cycle, item["paint_label"], item["proposal_id"])]
            raw = decode_instance_mask_rle(hypothesis_rle["raw_instance_union"])
            if mode == "bbox_guided_completion":
                border = decode_instance_mask_rle(hypothesis_rle["border_contrast"])
                mask = bootstrap_mask(
                    np.asarray(source), item["proposal_bbox"], reviewed["bbox"], raw, border,
                )
            else:
                px, py, width, height = (int(value) for value in item["proposal_bbox"])
                overlap = _intersection(item["proposal_bbox"], reviewed["bbox"])
                roi = np.zeros((height, width), bool)
                if overlap is not None:
                    x0, y0, x1, y1 = overlap
                    roi[y0 - py:y1 - py, x0 - px:x1 - px] = True
                mask = _prune_annotation_components(np.asarray(raw, bool) & roi, roi)
                mask = np.ascontiguousarray(mask)
                mask.setflags(write=False)
            reviewed_bbox = reviewed["bbox"]
            label_kind = "number_core"
        elif mode == "exclude_uncertain":
            hypothesis_rle = masks_by_key[(cycle, item["paint_label"], item["proposal_id"])]
            height, width = decode_instance_mask_rle(hypothesis_rle["raw_instance_union"]).shape
            mask = np.zeros((height, width), bool)
            mask.setflags(write=False)
            reviewed_bbox = matching[0]["bbox"] if matching else None
            label_kind = "uncertain_excluded"
        else:
            hypothesis_rle = masks_by_key[(cycle, item["paint_label"], item["proposal_id"])]
            height, width = decode_instance_mask_rle(hypothesis_rle["raw_instance_union"]).shape
            mask = np.zeros((height, width), bool)
            mask.setflags(write=False)
            reviewed_bbox = None
            label_kind = "empty_control"
        sheet = output_dir / f'{index:02d}_cycle{cycle}_{item["proposal_id"].split(":")[-1]}.png'
        _render(source, item["proposal_bbox"], mask, sheet)
        records.append({
            "cycle": cycle,
            "paint_label": item["paint_label"],
            "proposal_id": item["proposal_id"],
            "proposal_bbox": item["proposal_bbox"],
            "reviewed_number_bbox": reviewed_bbox,
            "label_kind": label_kind,
            "number_pixels": int(np.count_nonzero(mask)),
            "mask_rle": encode_instance_mask_rle(mask),
            "review_sheet": str(sheet).replace("\\", "/"),
            "annotation_only_bbox_supervision": True,
            "review_mode": mode,
        })
    result = {
        "schema": "smart-tga-number-context-pixel-labels-v1",
        "source_queue": str(queue_path).replace("\\", "/"),
        "record_count": len(records),
        "number_label_count": sum(item["label_kind"] == "number_core" for item in records),
        "empty_control_count": sum(item["label_kind"] == "empty_control" for item in records),
        "uncertain_excluded_count": sum(item["label_kind"] == "uncertain_excluded" for item in records),
        "records": records,
    }
    (output_dir / "pixel_labels.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--probes", nargs="+", type=Path, required=True)
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--review-manifest", type=Path)
    args = parser.parse_args()
    result = run(
        args.queue, args.probes, args.labels_dir, args.output_dir, args.review_manifest,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
