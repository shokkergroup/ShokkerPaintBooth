"""Build bounded visual and technical evidence for an explicit Wilds module.

This is a rejection-audit tool, not an acceptance gate.  The owner established
on 2026-08-24 that hashes/metrics cannot bless recolors, noise perturbations, or
shared dominant topology.  The contact sheets exist for direct owner-eye review.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CARD = 256
COLS = 5

# SPB-WILDS WR-VIS-1, 2026-08-24: fixed semantic colors expose whether a
# candidate's claimed mark families are actually visible, or merely names for
# overlapping copies of one carrier.  This is review evidence, never an
# acceptance score and never a source of renderer texture.
SEMANTIC_PALETTE = np.asarray([
    (0.96, 0.22, 0.24), (0.18, 0.78, 0.96), (0.98, 0.78, 0.16),
    (0.42, 0.92, 0.30), (0.78, 0.30, 0.96), (1.00, 0.46, 0.12),
    (0.18, 0.92, 0.70), (0.98, 0.34, 0.70), (0.56, 0.64, 1.00),
    (0.72, 0.92, 0.16), (0.94, 0.62, 0.38), (0.42, 0.82, 0.74),
], np.float32)


def _u8(rgb):
    return np.clip(np.asarray(rgb) * 255.0, 0, 255).astype(np.uint8)


def _card(rgb, fid, prefix):
    image = cv2.resize(_u8(rgb), (CARD, CARD), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((CARD + 28, CARD, 3), np.uint8)
    canvas[:CARD] = image
    label = fid[len(prefix):] if prefix and fid.startswith(prefix) else fid
    cv2.putText(canvas, label, (5, CARD + 19), cv2.FONT_HERSHEY_SIMPLEX,
                0.39, (230, 230, 230), 1, cv2.LINE_AA)
    return canvas


def _gray_card(channel, fid, prefix):
    gray = np.asarray(channel, np.uint8)
    rgb = np.repeat(gray[..., None], 3, axis=2).astype(np.float32) / 255.0
    return _card(rgb, fid, prefix)


def _contact(cards):
    rows = (len(cards) + COLS - 1) // COLS
    height, width = cards[0].shape[:2]
    out = np.zeros((rows * height, COLS * width, 3), np.uint8)
    for index, card in enumerate(cards):
        y = (index // COLS) * height
        x = (index % COLS) * width
        out[y:y + height, x:x + width] = card
    return out


def _sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _corr(left, right):
    a = cv2.resize(left, (96, 96), interpolation=cv2.INTER_AREA).astype(np.float32)
    b = cv2.resize(right, (96, 96), interpolation=cv2.INTER_AREA).astype(np.float32)
    a -= a.mean()
    b -= b.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.sum(a * b) / denominator) if denominator > 1.0e-6 else 1.0


def _iter_marks(grammar):
    for mark in grammar.marks:
        if hasattr(mark, "mask"):
            yield str(mark.name), np.asarray(mark.mask, np.float32), str(mark.bank)
        else:
            name, mask, bank = mark[:3]
            yield str(name), np.asarray(mask, np.float32), str(bank)


def _local_thickness_stats(mask, threshold=0.35):
    """Measure semantic-stroke thickness at medial peaks in native pixels.

    Component bounding boxes misclassify a long fine vein as a macro feature.
    Distance-transform peaks instead measure the local full width of lines,
    cells, patches, and filled territories.  A zero border makes a full-card
    fill finite.  The owner bar is evaluated on median and p90; p99 is reported
    for review because antialiased joins can create a few wider samples.
    """
    src = np.asarray(mask, np.float32)
    binary = (src > float(threshold)).astype(np.uint8)
    if not binary.any():
        return {
            "local_thickness_native_px_p50": 0.0,
            "local_thickness_native_px_p90": 0.0,
            "local_thickness_native_px_p99": 0.0,
            "local_thickness_peak_count": 0,
            "owner_8_32_local_scale_pass": False,
        }
    padded = np.pad(binary, 1, mode="constant")
    distance = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1]
    peaks = ((distance >= cv2.dilate(distance, np.ones((3, 3), np.uint8)) - 1e-6)
             & (distance > 0))
    native_scale = .5 * (2048.0 / src.shape[0] + 2048.0 / src.shape[1])
    widths = 2.0 * distance[peaks] * native_scale
    p50, p90, p99 = np.percentile(widths, (50, 90, 99))
    return {
        "local_thickness_native_px_p50": round(float(p50), 3),
        "local_thickness_native_px_p90": round(float(p90), 3),
        "local_thickness_native_px_p99": round(float(p99), 3),
        "local_thickness_peak_count": int(widths.size),
        "owner_8_32_local_scale_pass": bool(p50 >= 7.5 and p90 <= 32.5),
    }


def _semantic_view_and_stats(grammar):
    marks = list(_iter_marks(grammar))
    if not marks:
        raise ValueError("Wilds candidate grammar has no semantic marks")
    stack = np.stack([np.clip(mask, 0, 1) for _name, mask, _bank in marks])
    winner = np.argmax(stack, axis=0)
    strength = np.max(stack, axis=0)
    view = SEMANTIC_PALETTE[winner % len(SEMANTIC_PALETTE)].copy()
    view *= (0.22 + 0.78 * strength[..., None])
    view[strength <= 0.04] = 0.0

    stats = []
    for index, (name, mask, bank) in enumerate(marks):
        active = mask > 0.04
        strong = mask > 0.35
        dominant = active & (winner == index)
        components, labels, component_stats, _centroids = cv2.connectedComponentsWithStats(
            strong.astype(np.uint8), connectivity=8)
        areas = component_stats[1:, cv2.CC_STAT_AREA] if components > 1 else np.empty(0, np.int32)
        row = {
            "name": name,
            "bank": bank,
            "coverage_gt_0_04": round(float(active.mean()), 6),
            "coverage_gt_0_35": round(float(strong.mean()), 6),
            "dominant_coverage": round(float(dominant.mean()), 6),
            "mean_strength": round(float(mask.mean()), 6),
            "strong_component_count": int(len(areas)),
            "strong_component_median_area": round(float(np.median(areas)), 3) if len(areas) else 0.0,
            "strong_component_largest_fraction": (
                round(float(areas.max() / mask.size), 6) if len(areas) else 0.0),
        }
        row.update(_local_thickness_stats(mask))
        stats.append(row)
    return view, stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True)
    parser.add_argument("--ids-attr", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prefix", default="")
    parser.add_argument(
        "--id", action="append", dest="include_ids",
        help="Exact candidate ID to audit; repeat for a retained subset.",
    )
    args = parser.parse_args()

    module = importlib.import_module(args.module)
    available_ids = tuple(getattr(module, args.ids_attr))
    if args.include_ids:
        requested = tuple(args.include_ids)
        if len(set(requested)) != len(requested):
            parser.error("duplicate --id selector")
        missing = sorted(set(requested).difference(available_ids))
        if missing:
            parser.error(f"requested IDs absent from module: {missing}")
        ids = tuple(fid for fid in available_ids if fid in set(requested))
    else:
        ids = available_ids
    args.out.mkdir(parents=True, exist_ok=True)
    module.clear_cache()

    sheets = {key: [] for key in (
        "paint", "hue_null", "semantic", "metal", "roughness", "clearcoat",
        "angle_a", "angle_b", "angle_difference",
    )}
    null_fields = {}
    report = {
        "status": "candidate evidence; NOT owner accepted",
        "owner_rejection": "LAZY recolors/shared paint and spec topology; random noise is forbidden",
        "module": args.module,
        "ids": {},
    }

    for fid in ids:
        grammar = module.debug_grammar(fid)
        paint, spec = module._authored(fid)
        neutral = module.debug_hue_null(fid)
        angle_a, angle_b, difference = module.debug_angle_pair(fid)
        semantic, semantic_stats = _semantic_view_and_stats(grammar)
        sheets["paint"].append(_card(paint, fid, args.prefix))
        sheets["hue_null"].append(_card(neutral, fid, args.prefix))
        sheets["semantic"].append(_card(semantic, fid, args.prefix))
        sheets["metal"].append(_gray_card(spec[:, :, 0], fid, args.prefix))
        sheets["roughness"].append(_gray_card(spec[:, :, 1], fid, args.prefix))
        sheets["clearcoat"].append(_gray_card(spec[:, :, 2], fid, args.prefix))
        sheets["angle_a"].append(_card(angle_a, fid, args.prefix))
        sheets["angle_b"].append(_card(angle_b, fid, args.prefix))
        sheets["angle_difference"].append(_card(np.clip(difference * 2.0, 0, 1), fid, args.prefix))
        null_fields[fid] = cv2.cvtColor(_u8(neutral), cv2.COLOR_RGB2GRAY)
        report["ids"][fid] = {
            "causal_marks": [row["name"] for row in semantic_stats],
            "mark_count": len(semantic_stats),
            "semantic_marks": semantic_stats,
            "owner_feature_scale": {
                "required_native_px": [8, 32],
                "method": "threshold-0.35 local medial thickness; p50 >=7.5 and p90 <=32.5",
                "pass": all(row["owner_8_32_local_scale_pass"]
                            for row in semantic_stats),
                "too_thin_marks": [
                    row["name"] for row in semantic_stats
                    if row["local_thickness_native_px_p50"] < 7.5
                ],
                "macro_marks": [
                    row["name"] for row in semantic_stats
                    if row["local_thickness_native_px_p90"] > 32.5
                ],
            },
            "paint_sha256": _sha(_u8(paint)),
            "hue_null_sha256": _sha(_u8(neutral)),
            "spec_sha256": _sha(spec),
            "spec": {
                name: {
                    "min": int(spec[:, :, channel].min()),
                    "max": int(spec[:, :, channel].max()),
                    "std": round(float(spec[:, :, channel].std()), 3),
                }
                for channel, name in enumerate(("M", "R", "Cc"))
            },
            "angle_mean_abs_difference": round(float(difference.mean()), 5),
            "angle_changed_fraction_gt_0_10": round(
                float((difference.max(axis=2) > 0.10).mean()), 5),
        }

    pairs = []
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            pairs.append({
                "left": left,
                "right": right,
                "hue_null_correlation": round(_corr(null_fields[left], null_fields[right]), 6),
            })
    pairs.sort(key=lambda row: row["hue_null_correlation"], reverse=True)
    report["hue_null_nearest_pairs"] = pairs[:20]
    for kind in ("paint", "hue_null", "spec"):
        report[f"{kind}_unique_hashes"] = len({
            report["ids"][fid][f"{kind}_sha256"] for fid in ids
        })

    registry = {"unrelated": (None, None)}
    if hasattr(module, "install_into_engine"):
        report["api"] = {
            "install_message": module.install_into_engine(registry),
            "owned_count": sum(fid in registry for fid in ids),
            "unrelated_preserved": "unrelated" in registry,
            "all_entries_spec_paint_pairs": all(
                fid in registry and len(registry[fid]) == 2 for fid in ids),
        }
        shape = (257, 319)
        mask = np.ones(shape, np.float32)
        source = np.zeros((*shape, 3), np.float32)
        spec_fn, paint_fn = registry[ids[0]]
        report["api"]["paint_probe_shape"] = list(
            paint_fn(source, shape, mask, 1, 1.0, None).shape)
        report["api"]["spec_probe_shape"] = list(spec_fn(shape, mask, 1, 1.0).shape)
    else:
        report["api"] = {
            "status": "isolated candidate has no production installer; API probe skipped",
            "owner_acceptance_claimed": False,
        }

    sample_indices = sorted({0, len(ids) // 4, len(ids) // 2, 3 * len(ids) // 4, len(ids) - 1})
    native_shape = (2048, 2048)
    native_mask = np.ones(native_shape, np.float32)
    native_paint = np.zeros((*native_shape, 3), np.float32)
    performance = {}
    if hasattr(module, "_entry"):
        for index in sample_indices:
            fid = ids[index]
            module.clear_cache()
            spec_fn, paint_fn = module._entry(fid)
            start = time.perf_counter()
            paint_out = paint_fn(native_paint, native_shape, native_mask, 7, 1.0, None)
            spec_out = spec_fn(native_shape, native_mask, 7, 1.0)
            performance[fid] = {
                "seconds": round(time.perf_counter() - start, 4),
                "paint_shape": list(paint_out.shape),
                "spec_shape": list(spec_out.shape),
            }
            del paint_out, spec_out
    report["native_2048_cold_samples"] = performance

    for name, cards in sheets.items():
        image = cv2.cvtColor(_contact(cards), cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(args.out / f"{name}_contact.png"), image)
    (args.out / "evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "ids": len(ids),
        "unique": [report["paint_unique_hashes"], report["hue_null_unique_hashes"],
                   report["spec_unique_hashes"]],
        "nearest_hue_null": (
            report["hue_null_nearest_pairs"][0]
            if report["hue_null_nearest_pairs"] else None),
        "minimum_spec_std": min(
            row["std"] for item in report["ids"].values() for row in item["spec"].values()),
        "max_2048_seconds": (
            max(row["seconds"] for row in performance.values()) if performance else None),
        "feature_scale_failures": sum(
            not item["owner_feature_scale"]["pass"]
            for item in report["ids"].values()),
    }, indent=2))


if __name__ == "__main__":
    main()
