# -*- coding: utf-8 -*-
"""Visual-only W-3 evidence for the 70 FRACTURED Cryptid + Morpho finishes.

SPB-WILDS 2026-08-23. Owner verdict: "Too much redundancy way too similar
looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping
stuff." This intentionally computes no similarity or M7 acceptance score. It
creates the full paint contact, native-2048 crops, and paired material-light
A/B views so the owner eye gets the first decision after a renderer change.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.fractured_wilds_signatures_2026 import clear_design_cache
from scripts.spb_wilds_audit import (
    ANGLE_A_WEIGHTS, ANGLE_B_WEIGHTS, _ids_and_entries, _save_sheet, _spec_preview,
)


NATIVE_IDS = (
    "fmo_black_opal", "fmo_luna_dust",
    "fc_dragon_hex_glass", "fmo_jewel_scarab", "fmo_weevil_pit",
    "fc_will_o_wisp", "fmo_tiger_beetle",
    "fmo_ground_beetle", "fmo_hummingbird_gorget",
    "fmo_mussel_shell", "fmo_nacre_brick", "fmo_starling_sheen",
    "fmo_cassowary_quill", "fmo_raven_flash", "fmo_oil_beetle",
    "fc_sasquatch_fur", "fmo_atlas_wing", "fmo_sunset_moth",
    "fc_batwing", "fc_feathered_wing",
    "fmo_labradorite", "fmo_ulysses_flash", "fmo_morpho_blue",
    "fmo_foam_film", "fmo_pearl_oyster", "fmo_soap_bubble",
)

ANGLE_IDS = (
    "fmo_black_opal", "fc_dragon_hex_glass", "fc_will_o_wisp",
    "fmo_hummingbird_gorget", "fmo_starling_sheen", "fmo_raven_flash",
    "fmo_atlas_wing", "fc_batwing", "fmo_ulysses_flash", "fmo_foam_film",
)


def _render(entry, size: int):
    spec_fn, paint_fn = entry
    shape = (size, size)
    mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), 0.18, np.float32)
    bb = np.zeros(shape, np.float32)
    rgb = paint_fn(source, shape, mask, 20260823, 1.0, bb)
    spec = spec_fn(shape, mask, 20260823, 1.0)
    return rgb, spec


def _u8(rgb):
    return np.clip(np.asarray(rgb, np.float32) * 255.0, 0, 255).astype(np.uint8)


def _angle_view(rgb, spec, weights):
    """Material-weighted paint view; weights alter response, never RGB hue."""
    s = spec[:, :, :3].astype(np.float32)
    metal = s[:, :, 0]
    inverse_rough = 255.0 - s[:, :, 1]
    coat = s[:, :, 2]
    response = (weights[0] * metal + weights[1] * inverse_rough + weights[2] * coat) / 255.0
    # A single exposure curve for both angles. Any hue-population change is
    # therefore caused by differently colored authored marks trading material
    # response—not a post-process recolor or independent rainbow overlay.
    lit = np.clip(rgb * (0.24 + 1.58 * response[..., None]), 0.0, 1.0)
    return np.clip(np.power(lit, 0.82), 0.0, 1.0)


def _angle_sheet(items, target: Path, tile=384, label_h=30):
    rows = len(items)
    sheet = Image.new("RGB", (tile * 2, rows * (tile + label_h)), (12, 14, 18))
    draw = ImageDraw.Draw(sheet)
    for row, (fid, a, b) in enumerate(items):
        y = row * (tile + label_h)
        sheet.paste(Image.fromarray(a).resize((tile, tile), Image.Resampling.NEAREST), (0, y))
        sheet.paste(Image.fromarray(b).resize((tile, tile), Image.Resampling.NEAREST), (tile, y))
        draw.text((5, y + tile + 6), f"{fid} — angle A", fill=(238, 241, 245))
        draw.text((tile + 5, y + tile + 6), f"{fid} — angle B", fill=(238, 241, 245))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def build(out_dir: Path) -> None:
    entries = _ids_and_entries()
    out_dir.mkdir(parents=True, exist_ok=True)
    paint_dir = out_dir / "paint"
    angle_dir = out_dir / "angle_ab"
    paint_dir.mkdir(parents=True, exist_ok=True)
    angle_dir.mkdir(parents=True, exist_ok=True)

    contact = []
    for fid, entry in entries.items():
        rgb, _ = _render(entry, 256)
        pu8 = _u8(rgb)
        Image.fromarray(pu8).save(paint_dir / f"{fid}.png")
        contact.append((fid, pu8))
    _save_sheet(contact, out_dir / "paint_contact_sheet.png")

    native_items = []
    for fid in NATIVE_IDS:
        clear_design_cache()
        gc.collect()
        rgb, spec = _render(entries[fid], 2048)
        y0 = x0 = (2048 - 512) // 2
        native_items.append((fid + " paint", _u8(rgb[y0:y0 + 512, x0:x0 + 512])))
        native_items.append((fid + " M/R/CC", _spec_preview(spec[y0:y0 + 512, x0:x0 + 512])))
        del rgb, spec
    _save_sheet(native_items, out_dir / "native_2048_crops.png", cols=4, tile=512, label_h=32)

    angle_items = []
    weights_a = ANGLE_A_WEIGHTS
    weights_b = ANGLE_B_WEIGHTS
    for fid in ANGLE_IDS:
        clear_design_cache()
        rgb, spec = _render(entries[fid], 512)
        a = _u8(_angle_view(rgb, spec, weights_a))
        b = _u8(_angle_view(rgb, spec, weights_b))
        Image.fromarray(a).save(angle_dir / f"{fid}_angle_a.png")
        Image.fromarray(b).save(angle_dir / f"{fid}_angle_b.png")
        angle_items.append((fid, a, b))
    _angle_sheet(angle_items, out_dir / "angle_ab_contact_sheet.png")

    manifest = {
        "schema": 1,
        "ticket": "SPB-WILDS 2026-08-23 W-3",
        "owner_verdict": "Too much redundancy way too similar looks. Must be VERY UNIQUE. And must have the 'Fractured' color flipping stuff.",
        "acceptance": "REJECTED by owner 2026-08-24; this script produced internal evidence only and never establishes owner acceptance",
        "paint_count": len(contact),
        "native_crop_ids": list(NATIVE_IDS),
        "angle_ids": list(ANGLE_IDS),
        "angle_a_weights": {"metal": weights_a[0], "inverse_roughness": weights_a[1], "clearcoat": weights_a[2]},
        "angle_b_weights": {"metal": weights_b[0], "inverse_roughness": weights_b[1], "clearcoat": weights_b[2]},
        "angle_note": "Both views use the same RGB paint and exposure curve; only M/R/CC response weights change.",
    }
    (out_dir / "visual_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    build(args.output.resolve())
    print(str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
