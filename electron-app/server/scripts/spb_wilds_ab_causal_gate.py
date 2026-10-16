#!/usr/bin/env python3
"""Audit genuine Fractured A/B paint-to-spec coupling for Wilds candidates.

SPB-WILDS WR-FLIP-1, 2026-08-24.  Owner requirement: Wilds must retain the
``Fractured`` colour-flipping character, and random/noise-only separation does
not count.  This gate follows SPB's documented iRacing PBR contract: a static
paint texture must contain substantial, genuinely different A/B colour zones,
and those exact causal features must drive materially different M/R/Cc
responses.  A debug-only angle mockup can illustrate the result but cannot
prove it.

This is an isolated candidate audit.  It imports no production installer,
writes no registry, and never labels a finish owner accepted.  Visual contact
sheets remain mandatory because these measurements cannot detect taste,
semantic dishonesty, repeated carrier families, or oversized icons by
themselves.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


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

CALM = np.asarray([4.0, 120.0, 16.0], np.float32)


def _iter_marks(grammar) -> Iterable[tuple[str, np.ndarray, str]]:
    for mark in grammar.marks:
        if hasattr(mark, "mask"):
            yield str(mark.name), np.asarray(mark.mask, np.float32), str(mark.bank)
        else:
            name, mask, bank = mark[:3]
            yield str(name), np.asarray(mask, np.float32), str(bank)


def _owner_masks(grammar):
    shape = np.asarray(next(iter(grammar.marks)).mask if hasattr(next(iter(grammar.marks)), "mask")
                       else next(iter(grammar.marks))[1]).shape
    owners = {key: np.zeros(shape, np.float32) for key in ("A", "B", "N")}
    names = {key: [] for key in owners}
    for name, mask, bank in _iter_marks(grammar):
        mask = np.clip(mask, 0, 1)
        owners[bank] = np.maximum(owners[bank], mask)
        names[bank].append(name)
    return owners, names


def _weighted_mean(values, weight):
    weight = np.clip(np.asarray(weight, np.float32), 0, 1)
    den = float(weight.sum())
    if den < 1.0e-6:
        return np.zeros(values.shape[2] if values.ndim == 3 else 1, np.float32)
    if values.ndim == 3:
        return (values * weight[..., None]).sum(axis=(0, 1)) / den
    return np.asarray([(values * weight).sum() / den], np.float32)


def _circular_hue_mean(paint, weight):
    hsv = cv2.cvtColor(np.clip(paint, 0, 1).astype(np.float32), cv2.COLOR_RGB2HSV)
    hue = hsv[:, :, 0] * (np.pi / 180.0)
    reliability = np.clip(weight, 0, 1) * hsv[:, :, 1] * np.sqrt(hsv[:, :, 2])
    den = float(reliability.sum())
    if den < 1.0e-6:
        return 0.0, 0.0
    z = np.sum(reliability * np.exp(1j * hue)) / den
    return float(np.angle(z) % (2 * np.pi)), float(abs(z))


def _hue_distance_turns(a, b):
    d = abs(float(a) - float(b)) / (2 * np.pi)
    return min(d, 1.0 - d)


def _lab_delta(paint, wa, wb):
    lab = cv2.cvtColor(np.clip(paint, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
    la = _weighted_mean(lab, wa)
    lb = _weighted_mean(lab, wb)
    # A 100-unit CIE Lab separation is an intentionally conservative 1.0.
    return float(np.linalg.norm(la - lb) / 100.0)


def _spec_causal_fraction(spec, union):
    spec = np.asarray(spec[:, :, :3], np.float32)
    outside = union < 0.04
    # A finish may legitimately choose a constant material ground different
    # from the API's out-of-zone calm vector.  Only *variation* has to descend
    # from anatomy, so estimate that finish-local ground from untouched pixels.
    baseline = (np.median(spec[outside], axis=0) if np.any(outside)
                else np.median(spec.reshape(-1, 3), axis=0))
    deviation = np.linalg.norm(spec - baseline, axis=2)
    near = cv2.dilate((union > 0.04).astype(np.uint8), np.ones((11, 11), np.uint8)) > 0
    total = float(deviation.sum())
    return 1.0 if total < 1.0e-6 else float(deviation[near].sum() / total)


def _gradient_causal_fraction(spec, union):
    gray = np.mean(np.asarray(spec[:, :, :3], np.float32), axis=2)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    energy = np.hypot(gx, gy)
    near = cv2.dilate((union > 0.04).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    total = float(energy.sum())
    return 1.0 if total < 1.0e-6 else float(energy[near].sum() / total)


def _angle_metric(module, fid):
    if not hasattr(module, "debug_angle_pair"):
        return None
    pair = module.debug_angle_pair(fid)
    if len(pair) < 3:
        return None
    diff = np.asarray(pair[2], np.float32)
    return {
        "mean_absolute_rgb": round(float(diff.mean()), 6),
        "changed_fraction_gt_0_10": round(float((diff.max(axis=2) > 0.10).mean()), 6),
        "advisory_only": True,
    }


def audit_one(module, fid):
    grammar = module.debug_grammar(fid)
    paint, spec = module._authored(fid)
    paint = np.asarray(paint[:, :, :3], np.float32)
    spec = np.asarray(spec[:, :, :3], np.float32)
    owners, names = _owner_masks(grammar)
    a, b, n = owners["A"], owners["B"], owners["N"]
    # Exclusive weights prevent overlapping masks from manufacturing both
    # sides of the flip at the same pixels.
    wa = np.clip(a * (1.0 - 0.82 * b), 0, 1)
    wb = np.clip(b * (1.0 - 0.82 * a), 0, 1)
    union = np.maximum.reduce((a, b, n))

    rgb_a = _weighted_mean(paint, wa)
    rgb_b = _weighted_mean(paint, wb)
    hue_a, hue_coherence_a = _circular_hue_mean(paint, wa)
    hue_b, hue_coherence_b = _circular_hue_mean(paint, wb)
    spec_a = _weighted_mean(spec / 255.0, wa)
    spec_b = _weighted_mean(spec / 255.0, wb)
    spec_sep = float(np.linalg.norm(spec_a - spec_b))
    channel_ranges = np.ptp(spec, axis=(0, 1))
    channel_std = spec.std(axis=(0, 1))
    angle = _angle_metric(module, fid)

    values = {
        "a_feature_names": names["A"],
        "b_feature_names": names["B"],
        "neutral_feature_names": names["N"],
        "a_effective_coverage": round(float(wa.mean()), 6),
        "b_effective_coverage": round(float(wb.mean()), 6),
        "union_coverage": round(float(union.mean()), 6),
        "a_mean_rgb": [round(float(v), 6) for v in rgb_a],
        "b_mean_rgb": [round(float(v), 6) for v in rgb_b],
        "ab_lab_delta_over_100": round(_lab_delta(paint, wa, wb), 6),
        "ab_hue_distance_turns": round(_hue_distance_turns(hue_a, hue_b), 6),
        "a_hue_coherence": round(hue_coherence_a, 6),
        "b_hue_coherence": round(hue_coherence_b, 6),
        "a_mean_spec_m_r_cc": [round(float(v), 6) for v in spec_a],
        "b_mean_spec_m_r_cc": [round(float(v), 6) for v in spec_b],
        "ab_spec_vector_separation": round(spec_sep, 6),
        "spec_causal_deviation_fraction": round(_spec_causal_fraction(spec, union), 6),
        "spec_causal_gradient_fraction": round(_gradient_causal_fraction(spec, union), 6),
        "spec_channel_ranges": [round(float(v), 3) for v in channel_ranges],
        "spec_channel_std": [round(float(v), 3) for v in channel_std],
        "angle_mockup": angle,
    }
    gates = {
        "a_coverage_ge_0_04": values["a_effective_coverage"] >= 0.04,
        "b_coverage_ge_0_04": values["b_effective_coverage"] >= 0.04,
        "paint_lab_delta_ge_0_12": values["ab_lab_delta_over_100"] >= 0.12,
        "paint_hue_distance_ge_0_055": values["ab_hue_distance_turns"] >= 0.055,
        "spec_lobe_separation_ge_0_12": values["ab_spec_vector_separation"] >= 0.12,
        "spec_deviation_causal_ge_0_90": values["spec_causal_deviation_fraction"] >= 0.90,
        "spec_gradient_causal_ge_0_85": values["spec_causal_gradient_fraction"] >= 0.85,
        # The reveal lobes need near-full M/Cc travel.  Roughness still needs
        # a broad multi-shade aperture, but forcing its range to 180 would
        # reject valid smooth-shift materials and is not part of the doctrine.
        "spec_ranges_m180_r96_cc180": bool(channel_ranges[0] >= 180.0
                                             and channel_ranges[1] >= 96.0
                                             and channel_ranges[2] >= 180.0),
        "all_spec_std_gt_20": bool(np.all(channel_std > 20.0)),
    }
    values["gates"] = gates
    values["mechanical_pass"] = all(gates.values())
    values["owner_acceptance_claimed"] = False
    return values, paint, spec, owners


def _card(image, label, size=160):
    image = np.clip(np.asarray(image, np.float32), 0, 1)
    im = cv2.resize((image * 255).astype(np.uint8), (size, size), interpolation=cv2.INTER_AREA)
    out = np.zeros((size + 24, size, 3), np.uint8)
    out[:size] = im
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
        jobs.append((label, family, module_name, ids_name, set(ids)))
    return jobs, all_ids, manifest_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=[row[0] for row in MODULES],
                        help="Audit only selected family; may be repeated")
    parser.add_argument(
        "--module-override",
        action="append",
        default=[],
        metavar="FAMILY=MODULE[:IDS_ATTR]",
        help=("replace one candidate family module without editing this audit; "
              "IDS_ATTR defaults to the family's configured ID attribute"),
    )
    parser.add_argument(
        "--id",
        action="append",
        default=[],
        metavar="FINISH_ID",
        help=("audit only the requested finish ID; may be repeated across "
              "selected families and isolated module overrides"),
    )
    parser.add_argument(
        "--candidate-manifest",
        type=Path,
        help=("load an exact spb-wilds-retained/1 candidate set; cannot be "
              "combined with family/module/ID selectors"),
    )
    parser.add_argument("--output", type=Path,
                        default=ROOT / "_wilds_rejection_work" / "combined_ab_causal")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    if args.candidate_manifest and (args.only or args.module_override or args.id):
        parser.error("--candidate-manifest cannot be combined with --only, "
                     "--module-override, or --id")
    selected = set(args.only or [row[0] for row in MODULES])
    requested_ids = set(args.id)
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
    manifest_path = None
    if args.candidate_manifest:
        try:
            jobs, requested_ids, manifest_path = _manifest_jobs(args.candidate_manifest)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))
    else:
        jobs = []
        for family, _default_module, _default_ids_name in MODULES:
            if family not in selected:
                continue
            module_name, ids_name = configured[family]
            jobs.append((family, family, module_name, ids_name, None))
    report = {
        "status": "mechanical candidate evidence only; NOT owner accepted",
        "ticket": "SPB-WILDS WR-FLIP-1 2026-08-24",
        "contract": "static A/B paint zones causally married to PBR M/R/Cc response",
        "families": {},
    }
    owner_cards, spec_cards, drive_cards = [], [], []
    failures = []
    seen_ids = {}
    for label, family, module_name, ids_name, job_ids in jobs:
        module = importlib.import_module(module_name)
        if hasattr(module, "clear_cache"):
            module.clear_cache()
        ids = tuple(fid for fid in getattr(module, ids_name)
                    if ((job_ids is None or fid in job_ids)
                        and (not requested_ids or fid in requested_ids)))
        rows = {}
        for fid in ids:
            if fid in seen_ids:
                parser.error(
                    f"finish ID {fid!r} is exposed by both {seen_ids[fid]!r} "
                    f"and {family!r}; use non-overlapping overrides"
                )
            seen_ids[fid] = family
            values, paint, spec, owners = audit_one(module, fid)
            rows[fid] = values
            if not values["mechanical_pass"]:
                failures.append({"family": family, "id": fid,
                                 "failed": [key for key, ok in values["gates"].items() if not ok]})
            a, b, n = owners["A"], owners["B"], owners["N"]
            owner_view = np.dstack([a, b, np.maximum(n, np.minimum(a, b))])
            spec_view = spec / 255.0
            drive = np.abs(spec[:, :, 0] - spec[:, :, 2]) / 255.0
            drive_view = np.dstack([drive * a, drive * b, drive * n])
            short = fid.replace("fmo_", "").replace("fbl_", "").replace("fpe_", "").replace("fc_", "")
            owner_cards.append(_card(owner_view, short))
            spec_cards.append(_card(spec_view, short))
            drive_cards.append(_card(drive_view, short))
        report["families"][label] = {
            "family": family, "module": module_name,
            "count": len(ids), "ids": rows,
        }

    missing_ids = sorted(requested_ids - set(seen_ids))
    if missing_ids:
        parser.error("requested finish IDs were not found: " + ", ".join(missing_ids))

    report["summary"] = {
        "audited": sum(row["count"] for row in report["families"].values()),
        "mechanical_failures": len(failures),
        "failure_rows": failures,
        "owner_acceptance_claimed": False,
    }
    if manifest_path is not None:
        report["candidate_manifest"] = str(manifest_path.relative_to(ROOT))
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if owner_cards:
        cv2.imwrite(str(args.output / "ab_owner_contact.png"),
                    cv2.cvtColor(_contact(owner_cards), cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(args.output / "spec_rgb_contact.png"),
                    cv2.cvtColor(_contact(spec_cards), cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(args.output / "flip_drive_contact.png"),
                    cv2.cvtColor(_contact(drive_cards), cv2.COLOR_RGB2BGR))
    print(json.dumps(report["summary"], indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
