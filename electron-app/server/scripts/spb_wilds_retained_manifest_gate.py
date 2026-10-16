#!/usr/bin/env python3
"""Fail-closed integrity gate for provisional Fractured Wilds keeps.

This gate does not score taste and cannot declare a finish accepted.  It keeps
the small set that survived owner-eye triage bound to its exact source module,
exact ID, literal 96x48 live-render card, semantic A/B grammar, local 8--32 px
evidence, verdict, and retained/global reports. It also refuses the historical failure where an
internal candidate was mislabeled owner accepted or production wired.

SPB-WILDS WR-MANIFEST-1, 2026-08-24.  Owner verdict addressed: recolours,
shared carriers and shared spec maps are wasted finishes; random/noise-only
separation is never credited by this gate.
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_MANIFEST = Path(
    "_wilds_rejection_work/provisional_keeps/retained_manifest.json"
)


def _path(value: str | Path) -> Path:
    value = Path(value)
    return value if value.is_absolute() else ROOT / value


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"required retained evidence is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid retained evidence JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"retained evidence must be an object: {path}")
    return payload


def _marks(grammar):
    rows = []
    for mark in grammar.marks:
        if hasattr(mark, "mask"):
            rows.append((str(mark.name), np.asarray(mark.mask), str(mark.bank)))
        else:
            rows.append((str(mark[0]), np.asarray(mark[1]), str(mark[2])))
    return rows


def _validate_candidate(row: dict, index: int, *, import_modules: bool) -> dict:
    required = (
        "id", "family", "module", "ids_attr", "wave", "evidence_dir",
        "feature_scale_evidence", "buyer_evidence", "verdict", "reservation",
    )
    missing = [name for name in required if not row.get(name)]
    if missing:
        raise ValueError(
            f"retained candidate {index} misses required fields: {', '.join(missing)}"
        )
    fid = str(row["id"])
    evidence_dir = _path(row["evidence_dir"])
    if not evidence_dir.is_dir():
        raise ValueError(f"{fid}: evidence directory is missing: {evidence_dir}")
    if len(list(evidence_dir.glob("*.png"))) < 5:
        raise ValueError(f"{fid}: evidence directory has fewer than five visual contacts")
    if not list(evidence_dir.glob("*.json")):
        raise ValueError(f"{fid}: evidence directory has no JSON evidence")

    buyer_path = _path(row["buyer_evidence"])
    buyer_bgr = cv2.imread(str(buyer_path), cv2.IMREAD_COLOR)
    if buyer_bgr is None:
        raise ValueError(f"{fid}: exact buyer evidence is missing or unreadable: {buyer_path}")
    if buyer_bgr.shape != (48, 96, 3):
        raise ValueError(
            f"{fid}: exact buyer evidence must be literal 96x48 RGB; got "
            f"{buyer_bgr.shape}"
        )

    verdict_path = _path(row["verdict"])
    try:
        verdict = verdict_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"{fid}: verdict is missing: {verdict_path}") from exc
    if "KEEP-CANDIDATE" not in verdict:
        raise ValueError(f"{fid}: verdict does not explicitly say KEEP-CANDIDATE")
    compact = " ".join(verdict.lower().split())
    if not re.search(r"not.{0,90}owner.{0,45}accept", compact):
        raise ValueError(f"{fid}: verdict does not explicitly deny owner acceptance")
    if not re.search(r"not.{0,60}(production|permission to wire|wire production)", compact):
        raise ValueError(f"{fid}: verdict does not explicitly deny production wiring")

    scale_path = _path(row["feature_scale_evidence"])
    scale = _read_json(scale_path)
    ids = scale.get("ids")
    if not isinstance(ids, dict) or set(ids) != {fid}:
        raise ValueError(
            f"{fid}: feature-scale evidence must bind exactly this ID; got "
            f"{sorted(ids) if isinstance(ids, dict) else type(ids).__name__}"
        )
    scale_row = ids[fid]
    if scale_row.get("mark_count", 0) < 5:
        raise ValueError(f"{fid}: fewer than five semantic marks in scale evidence")
    owner_scale = scale_row.get("owner_feature_scale", {})
    if owner_scale.get("pass") is not True:
        raise ValueError(f"{fid}: owner 8--32 px feature-scale evidence fails")
    semantic = scale_row.get("semantic_marks", [])
    if len(semantic) != scale_row["mark_count"]:
        raise ValueError(f"{fid}: semantic mark count/evidence rows disagree")
    failed_marks = [
        mark.get("name", "<unnamed>") for mark in semantic
        if mark.get("owner_8_32_local_scale_pass") is not True
    ]
    if failed_marks:
        raise ValueError(f"{fid}: feature-scale failures: {', '.join(failed_marks)}")
    spec = scale_row.get("spec", {})
    if set(spec) != {"M", "R", "Cc"}:
        raise ValueError(f"{fid}: feature evidence lacks exact M/R/Cc channels")
    weak = [name for name, stats in spec.items() if float(stats.get("std", 0)) < 20.0]
    if weak:
        raise ValueError(f"{fid}: weak spec-channel standard deviation: {', '.join(weak)}")

    source = {"module_imported": False}
    if import_modules:
        module = importlib.import_module(str(row["module"]))
        ids_attr = str(row["ids_attr"])
        if not hasattr(module, ids_attr):
            raise ValueError(f"{fid}: module lacks declared ID attribute {ids_attr!r}")
        module_ids = tuple(getattr(module, ids_attr))
        if fid not in module_ids:
            raise ValueError(f"{fid}: absent from {row['module']}.{ids_attr}")
        if not hasattr(module, "debug_grammar") or not hasattr(module, "_authored"):
            raise ValueError(f"{fid}: module lacks debug_grammar/_authored evidence API")
        marks = _marks(module.debug_grammar(fid))
        if len(marks) < 5:
            raise ValueError(f"{fid}: live source exposes fewer than five semantic marks")
        banks = {bank for _name, _mask, bank in marks}
        if not {"A", "B"}.issubset(banks):
            raise ValueError(f"{fid}: live source lacks literal A and B semantic banks")
        paint, authored_spec = module._authored(fid)
        paint = np.asarray(paint)
        authored_spec = np.asarray(authored_spec)
        if paint.ndim != 3 or paint.shape[2] < 3:
            raise ValueError(f"{fid}: live paint has invalid shape {paint.shape}")
        if authored_spec.ndim != 3 or authored_spec.shape[2] < 3:
            raise ValueError(f"{fid}: live spec has invalid shape {authored_spec.shape}")
        if paint.shape[:2] != authored_spec.shape[:2]:
            raise ValueError(f"{fid}: live paint/spec dimensions disagree")
        paint_rgb = np.asarray(paint[..., :3], np.float32)
        if paint_rgb.size and float(paint_rgb.max()) > 1.5:
            paint_rgb = paint_rgb / 255.0
        expected_buyer = np.rint(cv2.resize(
            np.clip(paint_rgb, 0.0, 1.0), (96, 48), interpolation=cv2.INTER_AREA,
        ) * 255.0).astype(np.uint8)
        buyer_rgb = cv2.cvtColor(buyer_bgr, cv2.COLOR_BGR2RGB)
        if not np.array_equal(expected_buyer, buyer_rgb):
            raise ValueError(f"{fid}: exact 96x48 buyer evidence is stale versus live paint")
        source = {
            "module_imported": True,
            "mark_count": len(marks),
            "banks": sorted(banks),
            "shape": list(paint.shape[:2]),
        }

    return {
        "id": fid,
        "family": str(row["family"]),
        "wave": str(row["wave"]),
        "semantic_mark_count": int(scale_row["mark_count"]),
        "owner_feature_scale_pass": True,
        "buyer_evidence_exact_96x48": True,
        "min_spec_std": round(min(float(stats["std"]) for stats in spec.values()), 3),
        **source,
    }


def _validate_gate_reports(payload: dict, ids: set[str]) -> dict:
    reports = payload.get("gate_reports")
    required = (
        "ab_causal", "retained_collision", "global_catalog_collision",
        "feature_scale_summary",
    )
    if not isinstance(reports, dict) or any(not reports.get(key) for key in required):
        raise ValueError("retained manifest lacks the four required gate_reports paths")
    summary_path = _path(reports["feature_scale_summary"])
    if not summary_path.is_file():
        raise ValueError(f"feature-scale summary is missing: {summary_path}")

    ab = _read_json(_path(reports["ab_causal"]))
    ab_summary = ab.get("summary", {})
    if ab_summary.get("audited") != len(ids) or ab_summary.get("mechanical_failures") != 0:
        raise ValueError("A/B causal report count/failures disagree with retained manifest")
    ab_ids = set()
    for family in ab.get("families", {}).values():
        for fid, row in family.get("ids", {}).items():
            ab_ids.add(fid)
            if row.get("mechanical_pass") is not True:
                raise ValueError(f"{fid}: retained A/B causal row is not green")
            if row.get("owner_acceptance_claimed") is not False:
                raise ValueError(f"{fid}: A/B report improperly claims owner acceptance")
    if ab_ids != ids:
        raise ValueError(f"A/B causal IDs disagree: {sorted(ab_ids ^ ids)}")

    collision = _read_json(_path(reports["retained_collision"]))
    expected_pairs = len(ids) * (len(ids) - 1) // 2
    if collision.get("audited_ids") != len(ids) or collision.get("pair_count") != expected_pairs:
        raise ValueError("retained collision count/pair count disagrees with manifest")

    global_report = _read_json(_path(reports["global_catalog_collision"]))
    if global_report.get("old_wilds_included") is not False:
        raise ValueError("global catalog collision report included rejected old Wilds")
    global_ids = {row.get("id") for row in global_report.get("candidates", [])}
    if global_ids != ids:
        raise ValueError(f"global catalog collision IDs disagree: {sorted(global_ids ^ ids)}")
    if int(global_report.get("catalog_thumbnails", 0)) < 1:
        raise ValueError("global catalog collision report scanned no thumbnails")

    return {
        "ab_causal_ids": len(ab_ids),
        "retained_pairs": expected_pairs,
        "global_catalog_ids": len(global_ids),
        "global_catalog_thumbnails": int(global_report["catalog_thumbnails"]),
    }


def validate_manifest(path: Path, *, import_modules: bool = True) -> dict:
    manifest_path = _path(path)
    payload = _read_json(manifest_path)
    if payload.get("schema") != "spb-wilds-retained/1":
        raise ValueError(f"unsupported retained manifest schema: {payload.get('schema')!r}")
    if payload.get("owner_accepted") is not False:
        raise ValueError("retained manifest must say owner_accepted=false")
    if payload.get("production_wired") is not False:
        raise ValueError("retained manifest must say production_wired=false")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("retained manifest has no candidates")

    rows = [
        _validate_candidate(row, index, import_modules=import_modules)
        for index, row in enumerate(candidates)
    ]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("retained manifest contains duplicate IDs")
    reservations = [str(row["reservation"]).strip().casefold() for row in candidates]
    if len(reservations) != len(set(reservations)):
        raise ValueError("retained manifest reuses a topology reservation")
    gates = _validate_gate_reports(payload, set(ids))
    return {
        "status": "provisional_manifest_integrity_green",
        "owner_accepted": False,
        "production_wired": False,
        "manifest": str(manifest_path.relative_to(ROOT)),
        "candidate_count": len(rows),
        "candidates": rows,
        "gate_reports": gates,
        "warning": (
            "Integrity green is not owner acceptance. Visual owner-eye review "
            "and the eventual combined 110-card board remain mandatory."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--skip-import", action="store_true",
                        help="validate frozen evidence without importing live modules")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = validate_manifest(args.manifest, import_modules=not args.skip_import)
    except (ImportError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        output = _path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
