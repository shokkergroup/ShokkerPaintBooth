#!/usr/bin/env python3
"""Render isolated Petri owner-eye evidence without registry mutation."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _short(fid: str) -> str:
    return fid.removeprefix("fpe_")


def _robust(gray):
    a = np.asarray(gray, np.float32)
    lo, hi = np.percentile(a, (1.0, 99.0))
    if hi - lo < 1.0e-6:
        return np.zeros(a.shape, np.float32)
    return np.clip((a - lo) / (hi - lo), 0, 1)


def _card(image, label, size=224, robust=False):
    a = np.asarray(image, np.float32)
    if a.ndim == 2:
        a = _robust(a) if robust else np.clip(a, 0, 1)
        a = np.repeat(a[..., None], 3, axis=2)
    elif float(a.max()) > 1.5:
        a = a / 255.0
    tile = cv2.resize(np.clip(a[:, :, :3], 0, 1), (size, size),
                      interpolation=cv2.INTER_AREA)
    out = np.zeros((size + 28, size, 3), np.uint8)
    out[:size] = np.rint(tile * 255).astype(np.uint8)
    cv2.putText(out, label, (5, size + 19), cv2.FONT_HERSHEY_SIMPLEX,
                .42, (235, 235, 235), 1, cv2.LINE_AA)
    return out


def _contact(cards, columns=5):
    h, w = cards[0].shape[:2]
    rows = (len(cards) + columns - 1) // columns
    sheet = np.zeros((rows * h, columns * w, 3), np.uint8)
    for i, card in enumerate(cards):
        y, x = (i // columns) * h, (i % columns) * w
        sheet[y:y + h, x:x + w] = card
    return sheet


def build(candidate, output: Path, only: set[str] | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    contacts = {name: [] for name in ("paint", "hue_null", "M", "R", "Cc",
                                          "ab_owner", "angle_difference")}
    rows = []
    candidate.clear_cache()
    ids = [fid for fid in candidate.PETRI_IDS if not only or fid in only]
    for fid in ids:
        started = time.perf_counter()
        grammar = candidate.debug_grammar(fid)
        paint, spec = candidate._authored(fid)
        owners = candidate.owner_unions(grammar)
        _aa, _bb, diff = candidate.debug_angle_pair(fid)
        elapsed = time.perf_counter() - started
        label = _short(fid)
        contacts["paint"].append(_card(paint, label))
        contacts["hue_null"].append(_card(candidate.debug_hue_null(fid), label))
        for index, name in enumerate(("M", "R", "Cc")):
            contacts[name].append(_card(spec[:, :, index] / 255.0, label))
        owner_rgb = np.stack((owners["A"], owners["B"], owners["N"]), axis=2)
        contacts["ab_owner"].append(_card(owner_rgb, label))
        contacts["angle_difference"].append(_card(diff, label, robust=True))
        rows.append({
            "id": fid,
            "builder": candidate.BUILDERS[fid].__name__,
            "mark_names": [name for name, _mask, _owner in grammar.marks],
            "mark_count": len(grammar.marks),
            "seconds_512_double_build": round(elapsed, 6),
            "spec_std": [round(float(spec[:, :, i].std()), 4) for i in range(3)],
            "spec_range": [int(np.ptp(spec[:, :, i])) for i in range(3)],
            "a_coverage": round(float(owners["A"].mean()), 6),
            "b_coverage": round(float(owners["B"].mean()), 6),
        })
    for name, cards in contacts.items():
        cv2.imwrite(str(output / f"{name}_contact.png"),
                    cv2.cvtColor(_contact(cards), cv2.COLOR_RGB2BGR))
    report = {
        "status": (
            f"isolated Petri candidate evidence from {candidate.__name__}; "
            "NOT owner accepted"
        ),
        "count": len(rows),
        "unique_builders": len({row["builder"] for row in rows}),
        "rows": rows,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n",
                                         encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--module",
        default="engine.expansions.fractured_wilds_petri_w4_topologies_2026",
        help="isolated candidate module exposing the Petri debug API",
    )
    parser.add_argument("--only", action="append",
                        help="render only this finish ID; may be repeated")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "_wilds_rejection_work" / "petri_w4")
    args = parser.parse_args()
    candidate = importlib.import_module(args.module)
    report = build(candidate, args.output.resolve(), set(args.only or ()))
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
