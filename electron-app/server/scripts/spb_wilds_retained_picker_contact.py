#!/usr/bin/env python3
"""Build a picker-first visual board for retained Fractured Wilds candidates.

The board puts the buyer-scale read beside the native crop, hue-null topology,
fixed-palette semantics and each absolute M/R/Cc channel.  It is deliberately
human evidence: no score on this page can accept a finish, and loss of anatomy
at 128/64 or actual 96x48 is a reason to demote a mechanically green candidate.

SPB-WILDS WR-PICKER-1, 2026-08-24.  Isolated evidence only.
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

from scripts.spb_wilds_candidate_collision_audit import _semantic_view


DEFAULT_MANIFEST = Path(
    "_wilds_rejection_work/provisional_keeps/retained_manifest.json"
)
CARD = 160
LABEL = 24


def _root_path(value: str | Path) -> Path:
    value = Path(value)
    return value if value.is_absolute() else ROOT / value


def _rgb(value):
    value = np.asarray(value, np.float32)
    if value.ndim == 2:
        value = np.repeat(value[..., None], 3, axis=2)
    if float(value.max()) > 1.5:
        value = value / 255.0
    return np.clip(value[:, :, :3], 0, 1)


def _display_reconstruction(value, width, height=None):
    value = _rgb(value)
    height = width if height is None else int(height)
    reduced = cv2.resize(value, (int(width), height), interpolation=cv2.INTER_AREA)
    if width == height:
        return cv2.resize(reduced, (CARD, CARD), interpolation=cv2.INTER_NEAREST)
    # Preserve the buyer card's actual 2:1 aspect inside a square review tile.
    fitted_h = CARD // 2
    fitted = cv2.resize(reduced, (CARD, fitted_h), interpolation=cv2.INTER_NEAREST)
    out = np.full((CARD, CARD, 3), .018, np.float32)
    y0 = (CARD - fitted_h) // 2
    out[y0:y0 + fitted_h] = fitted
    return out


def _native_crop(value):
    value = _rgb(value)
    h, w = value.shape[:2]
    size = min(CARD, h, w)
    y0 = max(0, (h - size) // 2)
    x0 = max(0, (w - size) // 2)
    crop = value[y0:y0 + size, x0:x0 + size]
    return cv2.resize(crop, (CARD, CARD), interpolation=cv2.INTER_NEAREST)


def _card(value, label, *, source_size=None, native_crop=False):
    if native_crop:
        image = _native_crop(value)
    elif isinstance(source_size, tuple):
        image = _display_reconstruction(value, source_size[0], source_size[1])
    elif source_size is not None:
        image = _display_reconstruction(value, source_size)
    else:
        image = cv2.resize(_rgb(value), (CARD, CARD), interpolation=cv2.INTER_AREA)
    out = np.zeros((CARD + LABEL, CARD, 3), np.uint8)
    out[:CARD] = np.rint(image[:, :, ::-1] * 255).astype(np.uint8)
    cv2.putText(out, label, (4, CARD + 17), cv2.FONT_HERSHEY_SIMPLEX,
                .36, (232, 232, 232), 1, cv2.LINE_AA)
    return out


def _load_candidates(path: Path):
    manifest_path = _root_path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "spb-wilds-retained/1":
        raise ValueError("unsupported retained manifest schema")
    if payload.get("owner_accepted") is not False:
        raise ValueError("picker evidence refuses an owner-accepted manifest")
    rows = []
    for item in payload.get("candidates", []):
        fid = str(item["id"])
        module = importlib.import_module(str(item["module"]))
        ids = tuple(getattr(module, str(item["ids_attr"])))
        if fid not in ids:
            raise ValueError(f"{fid} absent from declared source module")
        grammar = module.debug_grammar(fid)
        paint, spec = module._authored(fid)
        rows.append((fid, _rgb(paint), _rgb(module.debug_hue_null(fid)),
                     _rgb(_semantic_view(grammar)), np.asarray(spec, np.float32)))
    if not rows:
        raise ValueError("retained manifest has no candidates")
    return manifest_path, rows


def build_board(path: Path):
    manifest_path, rows = _load_candidates(path)
    labels = (
        "paint full->160", "native center 160", "paint picker128",
        "paint picker64", "buyer 96x48", "hue-null 64",
        "semantic 64", "M absolute 64", "R absolute 64", "Cc absolute 64",
    )
    board = np.zeros((len(rows) * (CARD + LABEL), len(labels) * CARD, 3), np.uint8)
    report_rows = []
    for row_index, (fid, paint, hue_null, semantic, spec) in enumerate(rows):
        channel = [np.repeat((spec[:, :, i] / 255.0)[..., None], 3, axis=2)
                   for i in range(3)]
        cards = (
            _card(paint, f"{fid} | {labels[0]}"),
            _card(paint, labels[1], native_crop=True),
            _card(paint, labels[2], source_size=128),
            _card(paint, labels[3], source_size=64),
            _card(paint, labels[4], source_size=(96, 48)),
            _card(hue_null, labels[5], source_size=64),
            _card(semantic, labels[6], source_size=64),
            _card(channel[0], labels[7], source_size=64),
            _card(channel[1], labels[8], source_size=64),
            _card(channel[2], labels[9], source_size=64),
        )
        y0 = row_index * (CARD + LABEL)
        for column, card in enumerate(cards):
            x0 = column * CARD
            board[y0:y0 + CARD + LABEL, x0:x0 + CARD] = card
        report_rows.append({
            "id": fid,
            "paint_native_std": round(float(paint.std()), 6),
            "paint_picker64_std": round(float(
                cv2.resize(paint, (64, 64), interpolation=cv2.INTER_AREA).std()), 6),
            "buyer_96x48_std": round(float(
                cv2.resize(paint, (96, 48), interpolation=cv2.INTER_AREA).std()), 6),
            "spec_std_m_r_cc": [round(float(spec[:, :, i].std()), 3) for i in range(3)],
        })
    return manifest_path, board, report_rows


def _write_exact_buyer_cards(path: Path, output: Path):
    """Persist the literal 96x48 decision surface and a nearest-neighbour zoom.

    The contact board preserves aspect but expands each card for comparison.
    Keeping the exact raster beside an 8x nearest zoom prevents a reviewer from
    accidentally judging the native crop when the buyer only sees 4,608 pixels.
    """
    _manifest_path, rows = _load_candidates(path)
    individual = output / "buyer_exact"
    individual.mkdir(parents=True, exist_ok=True)
    paths = {}
    for fid, paint, _hue_null, _semantic, _spec in rows:
        buyer = cv2.resize(paint, (96, 48), interpolation=cv2.INTER_AREA)
        exact = individual / f"{fid}_buyer96x48.png"
        zoom = individual / f"{fid}_buyer96x48_nearest8x.png"
        cv2.imwrite(str(exact), np.rint(buyer[:, :, ::-1] * 255).astype(np.uint8))
        cv2.imwrite(str(zoom), cv2.resize(
            np.rint(buyer[:, :, ::-1] * 255).astype(np.uint8),
            (768, 384), interpolation=cv2.INTER_NEAREST,
        ))
        paths[fid] = {
            "buyer96x48": str(exact.relative_to(ROOT)),
            "buyer96x48Nearest8x": str(zoom.relative_to(ROOT)),
        }
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--output", type=Path,
        default=Path("_wilds_rejection_work/provisional_keeps/picker_first"),
    )
    args = parser.parse_args()
    output = _root_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    try:
        manifest_path, board, rows = build_board(args.manifest)
    except (AttributeError, ImportError, KeyError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    image_path = output / "retained_picker_first_contact.png"
    cv2.imwrite(str(image_path), board)
    exact_cards = _write_exact_buyer_cards(args.manifest, output)
    for row in rows:
        row["exact_buyer_evidence"] = exact_cards[row["id"]]
    report = {
        "schema": "spb-wilds-retained-picker-contact/1",
        "status": "visual evidence only; no owner acceptance",
        "manifest": str(manifest_path.relative_to(ROOT)),
        "candidate_count": len(rows),
        "contact": str(image_path.relative_to(ROOT)),
        "rows": rows,
        "warning": "Picker survival is reviewed by eye; numeric std is not acceptance.",
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
