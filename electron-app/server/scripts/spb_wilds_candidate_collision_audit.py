#!/usr/bin/env python3
"""Cross-family carrier/topology audit for all isolated Fractured Wilds art.

SPB-WILDS WR-COLLISION-1, 2026-08-24.  This specifically targets the owner's
rejection class that ordinary hashes miss: the same paint or spec carrier can
survive recolouring, tier remapping, phase changes, channel swaps and a new
headline overlay.  It emits owner-eye contacts for hue-null paint, paint
fine-carrier ablation, fixed-color semantic anatomy, each spec channel, and
spec fine-carrier ablation, plus translation-insensitive pair descriptors.

Scores are triage, never owner acceptance.  A low score cannot rescue a lazy
finish, random noise is not credited as a design, and every high-ranked pair
must be reviewed directly at original resolution before production wiring.
"""
from __future__ import annotations

import argparse
import importlib
import itertools
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = (
    ("cryptid", "engine.expansions.fractured_wilds_cryptid_rebuild_2026", "CRYPTID_IDS"),
    ("morpho_bio", "engine.expansions.fractured_wilds_morpho_biological_rebuild_2026", "MORPHO_BIO_IDS"),
    ("morpho_material", "engine.expansions.fractured_wilds_morpho_material_rebuild_2026", "MORPHO_MATERIAL_IDS"),
    ("bloom", "engine.expansions.fractured_wilds_bloom_explicit_rebuild_2026", "BLOOM_IDS"),
    ("petri", "engine.expansions.fractured_wilds_petri_explicit_rebuild_2026", "PETRI_IDS"),
)

SEMANTIC_PALETTE = np.asarray([
    (0.96, 0.18, 0.22), (0.08, 0.82, 0.98), (1.00, 0.72, 0.08),
    (0.28, 0.94, 0.34), (0.78, 0.22, 0.96), (1.00, 0.38, 0.04),
    (0.16, 0.96, 0.76), (0.96, 0.18, 0.68), (0.62, 0.78, 1.00),
    (0.84, 1.00, 0.20), (0.56, 0.38, 1.00), (1.00, 0.58, 0.48),
], np.float32)


def _gray(rgb):
    x = np.asarray(rgb, np.float32)
    if x.ndim == 2:
        return x
    if float(x.max()) > 1.5:
        x = x / 255.0
    return cv2.cvtColor(np.clip(x[:, :, :3], 0, 1), cv2.COLOR_RGB2GRAY)


def _robust(x):
    x = np.asarray(x, np.float32)
    lo, hi = np.percentile(x, (1.0, 99.0))
    if hi - lo < 1.0e-6:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0, 1).astype(np.float32)


def _carrier(x):
    """Visible fine-scale substrate after suppressing headline macro forms."""
    x = _robust(x)
    low = cv2.GaussianBlur(x, (0, 0), 0.75)
    high = cv2.GaussianBlur(x, (0, 0), 4.2)
    return _robust(np.abs(low - high))


def _fft_signature(x):
    work = cv2.resize(_carrier(x), (96, 96), interpolation=cv2.INTER_AREA)
    work -= float(work.mean())
    window = np.outer(np.hanning(96), np.hanning(96)).astype(np.float32)
    mag = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(work * window)))).astype(np.float32)
    cy = cx = 48
    mag[cy - 2:cy + 3, cx - 2:cx + 3] = 0
    small = cv2.resize(mag, (32, 32), interpolation=cv2.INTER_AREA).ravel()
    small -= float(small.mean())
    return small / (float(np.linalg.norm(small)) + 1.0e-8)


def _orientation_signature(x):
    x = cv2.resize(_robust(x), (128, 128), interpolation=cv2.INTER_AREA)
    banks = []
    for sigma in (0.7, 2.0, 5.0):
        work = cv2.GaussianBlur(x, (0, 0), sigma)
        gx = cv2.Sobel(work, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(work, cv2.CV_32F, 0, 1, ksize=3)
        mag, angle = cv2.cartToPolar(gx, gy, angleInDegrees=False)
        angle = np.mod(angle, np.pi)
        hist, _ = np.histogram(angle, bins=18, range=(0, np.pi), weights=mag)
        hist = hist.astype(np.float32)
        hist /= max(float(hist.sum()), 1.0e-8)
        banks.append(hist)
    return np.concatenate(banks)


def _morph_signature(x):
    work = cv2.resize(_robust(x), (128, 128), interpolation=cv2.INTER_AREA)
    values = [float(work.mean()), float(work.std())]
    for threshold in (0.25, 0.45, 0.65, 0.82):
        binary = (work > threshold).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float32) if count > 1 else np.zeros(0, np.float32)
        values.extend([
            float(binary.mean()),
            float((count - 1) / work.size),
            float(np.median(areas) / work.size) if areas.size else 0.0,
            float(np.percentile(areas, 90) / work.size) if areas.size else 0.0,
            float(np.max(areas) / work.size) if areas.size else 0.0,
        ])
    return np.asarray(values, np.float32)


def _direct_views(x):
    work = cv2.resize(_carrier(x), (64, 64), interpolation=cv2.INTER_AREA)
    views = []
    for k in range(4):
        r = np.rot90(work, k)
        for v in (r, np.fliplr(r)):
            q = v.ravel().astype(np.float32)
            q -= float(q.mean())
            q /= float(np.linalg.norm(q)) + 1.0e-8
            views.append(q)
    return np.stack(views)


def _descriptor(x):
    return {
        "fft": _fft_signature(x),
        "orientation": _orientation_signature(x),
        "morph": _morph_signature(x),
        "direct": _direct_views(x),
    }


def _similarity(a, b, morph_scale):
    fft = float(np.clip((np.dot(a["fft"], b["fft"]) + 1) * 0.5, 0, 1))
    orientation = float(np.minimum(a["orientation"], b["orientation"]).sum() / 3.0)
    morph = float(np.exp(-np.mean(np.abs(a["morph"] - b["morph"]) / morph_scale)))
    direct = float(np.clip(np.max(a["direct"] @ b["direct"].T), 0, 1))
    return 0.36 * fft + 0.24 * orientation + 0.16 * morph + 0.24 * direct


def _card(gray, label, size=160):
    gray = cv2.resize(_robust(gray), (size, size), interpolation=cv2.INTER_AREA)
    rgb = np.repeat((gray * 255).astype(np.uint8)[..., None], 3, axis=2)
    out = np.zeros((size + 24, size, 3), np.uint8)
    out[:size] = rgb
    cv2.putText(out, label, (4, size + 17), cv2.FONT_HERSHEY_SIMPLEX,
                0.34, (232, 232, 232), 1, cv2.LINE_AA)
    return out


def _color_card(rgb, label, size=160):
    rgb = np.asarray(rgb, np.float32)
    if float(rgb.max()) > 1.5:
        rgb = rgb / 255.0
    im = cv2.resize(np.clip(rgb[:, :, :3], 0, 1), (size, size), interpolation=cv2.INTER_AREA)
    out = np.zeros((size + 24, size, 3), np.uint8)
    out[:size] = (im * 255).astype(np.uint8)
    cv2.putText(out, label, (4, size + 17), cv2.FONT_HERSHEY_SIMPLEX,
                0.34, (232, 232, 232), 1, cv2.LINE_AA)
    return out


def _contact(cards, columns=10):
    if not cards:
        raise ValueError("cannot build an empty Wilds contact sheet")
    columns = max(1, min(int(columns), len(cards)))
    rows = (len(cards) + columns - 1) // columns
    h, w = cards[0].shape[:2]
    out = np.zeros((rows * h, columns * w, 3), np.uint8)
    for i, card in enumerate(cards):
        y, x = (i // columns) * h, (i % columns) * w
        out[y:y + h, x:x + w] = card
    return out


def _short(fid):
    for prefix in ("fmo_", "fbl_", "fpe_", "fc_"):
        if fid.startswith(prefix):
            return fid[len(prefix):]
    return fid


def _iter_marks(grammar):
    for mark in grammar.marks:
        if hasattr(mark, "mask"):
            yield str(mark.name), np.asarray(mark.mask, np.float32)
        else:
            yield str(mark[0]), np.asarray(mark[1], np.float32)


def _semantic_view(grammar):
    marks = list(_iter_marks(grammar))
    if not marks:
        raise ValueError("candidate grammar exposes no semantic marks")
    shape = marks[0][1].shape
    canvas = np.full((*shape, 3), 0.018, np.float32)
    for index, (_name, mask) in enumerate(marks):
        alpha = np.clip(mask, 0, 1)[..., None] * .88
        color = SEMANTIC_PALETTE[index % len(SEMANTIC_PALETTE)]
        canvas = canvas * (1.0 - alpha) + color * alpha
    return np.clip(canvas, 0, 1)


def _manifest_jobs(path):
    manifest_path = path if path.is_absolute() else ROOT / path
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "spb-wilds-retained/1":
        raise ValueError(f"unsupported retained manifest schema in {manifest_path}")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError(f"retained manifest has no candidates: {manifest_path}")
    grouped = {}
    all_ids = set()
    for index, row in enumerate(candidates):
        if not isinstance(row, dict):
            raise ValueError(f"retained manifest candidate {index} is not an object")
        required = ("id", "family", "module", "ids_attr")
        missing = [name for name in required if not row.get(name)]
        if missing:
            raise ValueError(
                f"retained manifest candidate {index} misses {', '.join(missing)}"
            )
        fid = str(row["id"])
        if fid in all_ids:
            raise ValueError(f"duplicate retained candidate ID {fid!r}")
        all_ids.add(fid)
        key = (str(row["family"]), str(row["module"]), str(row["ids_attr"]))
        grouped.setdefault(key, []).append(fid)
    jobs = []
    family_counts = {}
    for (family, module_name, ids_name), ids in grouped.items():
        family_counts[family] = family_counts.get(family, 0) + 1
        suffix = family_counts[family]
        label = family if suffix == 1 else f"{family}_retained_{suffix}"
        jobs.append((label, module_name, ids_name, set(ids)))
    return jobs, all_ids, manifest_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=[row[0] for row in MODULES])
    parser.add_argument(
        "--module-override",
        action="append",
        default=[],
        metavar="FAMILY=MODULE[:IDS_ATTR]",
        help=("replace one candidate family module without editing this audit; "
              "IDS_ATTR defaults to the family's configured ID attribute"),
    )
    parser.add_argument(
        "--extra-module",
        action="append",
        default=[],
        metavar="LABEL=MODULE:IDS_ATTR",
        help=("append an isolated candidate module to the audit without "
              "replacing a configured family; LABEL must be unique"),
    )
    parser.add_argument(
        "--id",
        action="append",
        default=[],
        dest="include_ids",
        metavar="FINISH_ID",
        help="retain only named finish IDs after loading selected modules; may be repeated",
    )
    parser.add_argument(
        "--candidate-manifest",
        type=Path,
        help=("load an exact spb-wilds-retained/1 candidate set; cannot be "
              "combined with module or ID selectors"),
    )
    parser.add_argument("--output", type=Path,
                        default=ROOT / "_wilds_rejection_work" / "combined_candidate_collision")
    parser.add_argument("--top", type=int, default=240)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.candidate_manifest and (args.only or args.module_override
                                    or args.extra_module or args.include_ids):
        parser.error("--candidate-manifest cannot be combined with --only, "
                     "--module-override, --extra-module, or --id")
    selected = set(args.only or [row[0] for row in MODULES])
    configured = {family: [module, ids_attr]
                  for family, module, ids_attr in MODULES}
    for item in args.module_override:
        if "=" not in item:
            parser.error(f"bad --module-override {item!r}; expected FAMILY=MODULE[:IDS_ATTR]")
        family, target = item.split("=", 1)
        if family not in configured:
            parser.error(f"unknown override family {family!r}")
        if ":" in target:
            module_name, ids_attr = target.rsplit(":", 1)
        else:
            module_name, ids_attr = target, configured[family][1]
        configured[family] = [module_name, ids_attr]

    jobs = []
    for family, _default_module, _default_ids_name in MODULES:
        if family in selected:
            module_name, ids_name = configured[family]
            jobs.append((family, module_name, ids_name, None))
    known_labels = {row[0] for row in jobs}
    for item in args.extra_module:
        if "=" not in item or ":" not in item.split("=", 1)[1]:
            parser.error(f"bad --extra-module {item!r}; expected LABEL=MODULE:IDS_ATTR")
        label, target = item.split("=", 1)
        module_name, ids_name = target.rsplit(":", 1)
        if not label or label in known_labels:
            parser.error(f"duplicate or empty extra-module label {label!r}")
        known_labels.add(label)
        jobs.append((label, module_name, ids_name, None))
    include_ids = set(args.include_ids)
    manifest_path = None
    if args.candidate_manifest:
        try:
            jobs, include_ids, manifest_path = _manifest_jobs(args.candidate_manifest)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))

    rows = {}
    contacts = {key: [] for key in ("paint", "hue_null", "paint_carrier",
                                     "semantic", "M", "R", "Cc", "spec_carrier")}
    family_of = {}
    for family, module_name, ids_name, job_ids in jobs:
        module = importlib.import_module(module_name)
        if hasattr(module, "clear_cache"):
            module.clear_cache()
        for fid in tuple(getattr(module, ids_name)):
            if job_ids is not None and fid not in job_ids:
                continue
            if include_ids and fid not in include_ids:
                continue
            if fid in rows:
                raise ValueError(f"duplicate candidate ID {fid!r} from {family!r}")
            paint, spec = module._authored(fid)
            null = module.debug_hue_null(fid) if hasattr(module, "debug_hue_null") else paint
            null_gray = _gray(null)
            paint_carrier = _carrier(null_gray)
            channels = [np.asarray(spec[:, :, i], np.float32) / 255.0 for i in range(3)]
            spec_carrier = np.maximum.reduce([_carrier(ch) for ch in channels])
            rows[fid] = {
                "paint": _descriptor(null_gray),
                "paint_carrier": _descriptor(paint_carrier),
                "spec": [_descriptor(ch) for ch in channels],
                "spec_carrier": _descriptor(spec_carrier),
            }
            family_of[fid] = family
            label = _short(fid)
            contacts["paint"].append(_color_card(paint, label))
            contacts["semantic"].append(
                _color_card(_semantic_view(module.debug_grammar(fid)), label)
            )
            for key, image in (("hue_null", null_gray), ("paint_carrier", paint_carrier),
                               ("M", channels[0]), ("R", channels[1]), ("Cc", channels[2]),
                               ("spec_carrier", spec_carrier)):
                contacts[key].append(_card(image, label))

    if include_ids:
        missing = include_ids.difference(rows)
        if missing:
            raise SystemExit(f"requested IDs not found in selected modules: {sorted(missing)}")
    if not rows:
        raise SystemExit("no candidate IDs selected")
    all_morph = np.stack([d["morph"] for row in rows.values()
                          for d in [row["paint"], row["paint_carrier"], row["spec_carrier"], *row["spec"]]])
    morph_scale = np.maximum(np.percentile(all_morph, 90, axis=0)
                             - np.percentile(all_morph, 10, axis=0), 1.0e-4)

    pairs = []
    for left, right in itertools.combinations(sorted(rows), 2):
        a, b = rows[left], rows[right]
        paint = _similarity(a["paint"], b["paint"], morph_scale)
        paint_carrier = _similarity(a["paint_carrier"], b["paint_carrier"], morph_scale)
        matrix = np.asarray([[_similarity(x, y, morph_scale) for y in b["spec"]]
                             for x in a["spec"]], np.float32)
        rr, cc = linear_sum_assignment(-matrix)
        spec_ordered = float(np.mean(np.diag(matrix)))
        spec_permuted = float(matrix[rr, cc].mean())
        spec_carrier = _similarity(a["spec_carrier"], b["spec_carrier"], morph_scale)
        pairs.append({
            "left": left, "right": right,
            "left_family": family_of[left], "right_family": family_of[right],
            "paint_topology": round(paint, 6),
            "paint_fine_carrier": round(paint_carrier, 6),
            "spec_ordered": round(spec_ordered, 6),
            "spec_channel_permuted": round(spec_permuted, 6),
            "spec_fine_carrier": round(spec_carrier, 6),
            "review_priority": round(max(paint, paint_carrier, spec_permuted, spec_carrier), 6),
            "spec_permutation": [int(v) for v in cc],
        })
    pairs.sort(key=lambda row: row["review_priority"], reverse=True)
    payload = {
        "status": "candidate collision triage only; NOT owner accepted",
        "ticket": "SPB-WILDS WR-COLLISION-1 2026-08-24",
        "audited_ids": len(rows),
        "pair_count": len(pairs),
        "warning": "Scores cannot credit random/noise differences or overrule direct contact review.",
        "top_pairs": pairs[:max(1, args.top)],
    }
    if manifest_path is not None:
        payload["candidate_manifest"] = str(manifest_path.relative_to(ROOT))
    (args.output / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for key, cards in contacts.items():
        cv2.imwrite(str(args.output / f"{key}_contact.png"),
                    cv2.cvtColor(_contact(cards), cv2.COLOR_RGB2BGR))
    print(json.dumps({
        "audited_ids": len(rows), "pair_count": len(pairs),
        "top_pair": pairs[0] if pairs else None,
        "output": str(args.output), "owner_acceptance_claimed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
