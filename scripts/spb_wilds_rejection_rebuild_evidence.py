#!/usr/bin/env python3
"""Build owner-eye evidence for the 2026-08-24 Fractured Wilds rebuild.

The contacts intentionally suppress palette as an acceptance crutch.  They
are evidence for human rejection/iteration, never an automatic ship gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _labelled_contact(items, path: Path, *, cols=5, cell=256, title=""):
    label_h = 34
    top = 38 if title else 0
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, top + rows * (cell + label_h)), (8, 8, 10))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    if title:
        draw.text((10, 10), title, fill=(240, 240, 240), font=font)
    for i, (fid, rgb) in enumerate(items):
        x = (i % cols) * cell
        y = top + (i // cols) * (cell + label_h)
        im = Image.fromarray(np.asarray(rgb, np.uint8), "RGB")
        sheet.paste(im.resize((cell, cell), Image.Resampling.NEAREST), (x, y))
        draw.text((x + 5, y + cell + 5), fid, fill=(230, 230, 230), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def _fixed_hue(rgb):
    f = np.asarray(rgb, np.float32) / 255.0
    luma = np.clip(f[:, :, 0] * 0.299 + f[:, :, 1] * 0.587 + f[:, :, 2] * 0.114, 0.0, 1.0)
    # Fixed cyan-blue hue. Only source luma/topology survives.
    out = np.stack((luma * 0.18, luma * 0.76, luma), axis=2)
    return np.clip(out * 255.0, 0, 255).astype(np.uint8)


def _channel_rgb(channel):
    return np.repeat(np.asarray(channel, np.uint8)[:, :, None], 3, axis=2)


def _angle_views(paint, spec):
    p = np.asarray(paint, np.float32) / 255.0
    m = np.asarray(spec[:, :, 0], np.float32) / 255.0
    r = np.asarray(spec[:, :, 1], np.float32) / 255.0
    c = np.asarray(spec[:, :, 2], np.float32) / 255.0
    a_gain = 0.18 + 0.74 * m * (1.0 - 0.38 * r)
    b_gain = 0.18 + 0.74 * c * (0.68 + 0.32 * r)
    a = np.clip(p * a_gain[:, :, None] * 1.65, 0.0, 1.0)
    b = np.clip(p * b_gain[:, :, None] * 1.65, 0.0, 1.0)
    diff = np.abs(a - b)
    diff = diff / max(float(diff.max()), 1e-6)
    return tuple(np.clip(x * 255.0, 0, 255).astype(np.uint8) for x in (a, b, diff))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="_wilds_rejection_work/bloom_petri_rebuild")
    ap.add_argument("--size", type=int, default=256)
    args = ap.parse_args()
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    from engine.expansions import fractured_wilds_bloom_petri_rebuild_2026 as rebuild

    ids = tuple(rebuild._IDS)
    paint_items = []
    hue_null_items = []
    m_items, r_items, c_items = [], [], []
    a_items, b_items, d_items = [], [], []
    records = []
    for i, fid in enumerate(ids, 1):
        shape = (args.size, args.size)
        mask = np.ones(shape, np.float32)
        base = np.zeros((args.size, args.size, 3), np.float32)
        spec_fn, paint_fn = rebuild.make_entry(fid)
        rebuild.clear_design_cache()
        started = time.perf_counter()
        paint = paint_fn(base, shape, mask, 1, 1.0, None)
        spec = spec_fn(shape, mask, 1, 1.0)
        elapsed = time.perf_counter() - started
        p8 = np.clip(paint * 255.0, 0, 255).astype(np.uint8)
        rgb_spec = spec[:, :, :3]
        a, b, d = _angle_views(p8, rgb_spec)
        paint_items.append((fid, p8))
        hue_null_items.append((fid, _fixed_hue(p8)))
        m_items.append((fid, _channel_rgb(rgb_spec[:, :, 0])))
        r_items.append((fid, _channel_rgb(rgb_spec[:, :, 1])))
        c_items.append((fid, _channel_rgb(rgb_spec[:, :, 2])))
        a_items.append((fid, a)); b_items.append((fid, b)); d_items.append((fid, d))
        corrs = np.corrcoef(rgb_spec.reshape(-1, 3), rowvar=False)
        records.append({
            "id": fid,
            "paint_sha256": hashlib.sha256(p8.tobytes()).hexdigest(),
            "spec_sha256": hashlib.sha256(rgb_spec.tobytes()).hexdigest(),
            "seconds_cold_design": round(elapsed, 6),
            "tiers": [int(len(np.unique(rgb_spec[:, :, ch]))) for ch in range(3)],
            "std": [round(float(rgb_spec[:, :, ch].std()), 4) for ch in range(3)],
            "channel_corr_abs_max": round(float(np.max(np.abs(corrs[np.triu_indices(3, 1)]))), 6),
            "semantic_marks": list(rebuild._SEMANTIC_MARKS[fid]),
            "mode": rebuild._MODE_BY_ID[fid],
        })
        print(f"[wilds-rebuild-evidence] {i:03d}/{len(ids):03d} {fid} {elapsed:.3f}s")

    _labelled_contact(paint_items, outdir / "paint_color_contact.png", title="Bloom + Petri rebuilt paint (color)")
    _labelled_contact(hue_null_items, outdir / "paint_hue_null_contact.png", title="HUE-NULL: same fixed hue, topology/luma only")
    _labelled_contact(m_items, outdir / "spec_m_contact.png", title="Metalness only")
    _labelled_contact(r_items, outdir / "spec_r_contact.png", title="Roughness only")
    _labelled_contact(c_items, outdir / "spec_cc_contact.png", title="Clearcoat only")
    _labelled_contact(a_items, outdir / "angle_a_contact.png", title="Material response proxy: angle A")
    _labelled_contact(b_items, outdir / "angle_b_contact.png", title="Material response proxy: angle B")
    _labelled_contact(d_items, outdir / "angle_difference_contact.png", title="A/B absolute difference, normalized per finish")
    payload = {
        "schema": 1,
        "ticket": "SPB-WILDS-REJECTION 2026-08-24 WR-2",
        "acceptance": "UNREVIEWED evidence; never owner-accepted by script",
        "count": len(records),
        "records": records,
    }
    (outdir / "evidence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(records), "output": str(outdir)}, indent=2))


if __name__ == "__main__":
    main()
