#!/usr/bin/env python3
"""Compare isolated Fractured Wilds candidates with the existing app catalog.

WR-GLOBAL-COLLISION-1, 2026-08-24.  The local retained-only audit prevents a
new Wilds finish from cloning another retained Wilds finish.  This companion
audit scans the existing base/monolithic/pattern thumbnail corpus after color
removal, so a supposedly new construction cannot quietly reproduce a pattern
that already exists elsewhere in SPB.

Scores are review routing only.  They cannot prove acceptance, and random
noise is never credited as a design.  Every reported neighbour is emitted in
an aligned contact row for direct owner-eye inspection.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from spb_wilds_candidate_collision_audit import (  # noqa: E402
    _card, _carrier, _color_card, _contact, _descriptor, _gray, _similarity,
)


DEFAULT_THUMB_DIRS = ("base", "monolithic", "pattern")
WILDS_PREFIXES = ("fc_", "fmo_", "fbl_", "fpe_")


def _manifest_candidates(path: Path):
    manifest_path = path if path.is_absolute() else ROOT / path
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "spb-wilds-retained/1":
        raise ValueError(f"unsupported candidate manifest schema in {manifest_path}")
    rows = []
    seen = set()
    for item in payload.get("candidates", []):
        required = ("id", "module", "ids_attr")
        missing = [key for key in required if not item.get(key)]
        if missing:
            raise ValueError(f"manifest candidate missing {missing}: {item!r}")
        fid = str(item["id"])
        if fid in seen:
            raise ValueError(f"duplicate candidate ID {fid!r}")
        seen.add(fid)
        module = importlib.import_module(str(item["module"]))
        ids = tuple(getattr(module, str(item["ids_attr"])))
        if fid not in ids:
            raise ValueError(f"{fid!r} absent from {item['module']}:{item['ids_attr']}")
        if hasattr(module, "clear_cache"):
            module.clear_cache()
        paint, _spec = module._authored(fid)
        neutral = module.debug_hue_null(fid) if hasattr(module, "debug_hue_null") else paint
        gray = _gray(neutral)
        rows.append({
            "id": fid,
            "paint": np.asarray(paint, np.float32),
            "gray": gray,
            "carrier": _carrier(gray),
            "descriptor": _descriptor(gray),
            "carrier_descriptor": _descriptor(_carrier(gray)),
        })
    if not rows:
        raise ValueError("candidate manifest is empty")
    return manifest_path, rows


def _catalog_rows(directories, include_wilds=False):
    rows = []
    for directory in directories:
        root = ROOT / "thumbnails" / directory
        if not root.is_dir():
            raise ValueError(f"missing thumbnail directory {root}")
        for path in sorted(root.glob("*.png")):
            stem = path.stem
            if not include_wilds and stem.startswith(WILDS_PREFIXES):
                continue
            bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            gray = _gray(rgb)
            carrier = _carrier(gray)
            rows.append({
                "key": f"{directory}/{stem}",
                "stem": stem,
                "rgb": rgb,
                "gray": gray,
                "carrier": carrier,
                "descriptor": _descriptor(gray),
                "carrier_descriptor": _descriptor(carrier),
            })
    if not rows:
        raise ValueError("no catalog thumbnails loaded")
    return rows


def _label(value: str, limit=24):
    return value if len(value) <= limit else value[:limit - 1] + "~"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--thumb-dir", action="append", dest="thumb_dirs")
    parser.add_argument("--include-old-wilds", action="store_true")
    args = parser.parse_args()
    args.output = args.output if args.output.is_absolute() else ROOT / args.output
    args.output.mkdir(parents=True, exist_ok=True)

    manifest_path, candidates = _manifest_candidates(args.candidate_manifest)
    catalog = _catalog_rows(tuple(args.thumb_dirs or DEFAULT_THUMB_DIRS),
                            include_wilds=args.include_old_wilds)

    all_morph = np.stack([
        row[k]["morph"]
        for row in (
            [{"paint": c["descriptor"], "carrier": c["carrier_descriptor"]}
             for c in candidates]
            + [{"paint": c["descriptor"], "carrier": c["carrier_descriptor"]}
               for c in catalog]
        )
        for k in ("paint", "carrier")
    ])
    morph_scale = np.maximum(np.percentile(all_morph, 90, axis=0)
                             - np.percentile(all_morph, 10, axis=0), 1.0e-4)

    report_rows = []
    color_cards = []
    null_cards = []
    carrier_cards = []
    top_n = max(1, int(args.top))
    for candidate in candidates:
        matches = []
        for item in catalog:
            if item["stem"] == candidate["id"]:
                continue
            topology = _similarity(candidate["descriptor"], item["descriptor"], morph_scale)
            fine = _similarity(candidate["carrier_descriptor"],
                               item["carrier_descriptor"], morph_scale)
            matches.append({
                "catalog": item["key"],
                "paint_topology": round(float(topology), 6),
                "paint_fine_carrier": round(float(fine), 6),
                "review_priority": round(float(max(topology, fine)), 6),
                "_item": item,
            })
        matches.sort(key=lambda row: row["review_priority"], reverse=True)
        retained = matches[:top_n]
        report_rows.append({
            "id": candidate["id"],
            "nearest": [{k: v for k, v in row.items() if k != "_item"}
                        for row in retained],
        })

        label = _label(candidate["id"])
        color_cards.append(_color_card(candidate["paint"], label))
        null_cards.append(_card(candidate["gray"], label))
        carrier_cards.append(_card(candidate["carrier"], label))
        for match in retained:
            item = match["_item"]
            match_label = _label(item["key"])
            color_cards.append(_color_card(item["rgb"], match_label))
            null_cards.append(_card(item["gray"], match_label))
            carrier_cards.append(_card(item["carrier"], match_label))

    columns = top_n + 1
    for name, cards in (("paint", color_cards), ("hue_null", null_cards),
                        ("fine_carrier", carrier_cards)):
        rgb = _contact(cards, columns=columns)
        cv2.imwrite(str(args.output / f"{name}_nearest_contact.png"),
                    cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    payload = {
        "status": "global catalog collision triage only; NOT owner accepted",
        "ticket": "SPB-WILDS WR-GLOBAL-COLLISION-1 2026-08-24",
        "candidate_manifest": str(manifest_path.relative_to(ROOT)),
        "thumbnail_directories": list(args.thumb_dirs or DEFAULT_THUMB_DIRS),
        "old_wilds_included": bool(args.include_old_wilds),
        "catalog_thumbnails": len(catalog),
        "candidates": report_rows,
        "warning": "Scores route direct review; they cannot credit noise or prove uniqueness.",
    }
    (args.output / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary = {
        "candidates": len(candidates),
        "catalog_thumbnails": len(catalog),
        "nearest": [
            {"id": row["id"], **row["nearest"][0]} for row in report_rows
        ],
        "output": str(args.output),
        "owner_acceptance_claimed": False,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
