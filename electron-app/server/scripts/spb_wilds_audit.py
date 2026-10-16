# -*- coding: utf-8 -*-
"""Bounded visual/quantitative audit for the 70 FRACTURED Wilds finishes.

This is intentionally independent of the live server.  It can fingerprint the
currently baked thumbnails (the immutable "before" evidence) or render the root
engine factories into a separate evidence directory.  It never writes runtime
mirrors, catalog metadata, or the live :59876 process.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SIZE = 256
ANGLE_A_WEIGHTS = (0.68, 0.26, 0.06)
ANGLE_B_WEIGHTS = (0.06, 0.14, 0.80)
FLIP_MIN_SATURATION = 0.18
FLIP_MIN_VALUE = 0.08


def _ids_and_entries():
    from engine.expansions import fractured_themes_2026 as themes
    from engine.expansions import fractured_themes_fix_2026 as fixes
    from engine.expansions import fractured_morpho_2026 as morpho

    entries = {}
    for fid in sorted(themes.CRYPTID):
        entries[fid] = fixes._mk(fid) if fid in fixes.FIX else themes._mk(fid)
    for fid in sorted(morpho.ALL):
        entries[fid] = morpho._mk(fid)
    return entries


def _phash_bits(luma):
    g = cv2.resize(luma.astype(np.float32), (64, 64))
    d = cv2.dct(g)[:16, :16]
    d[0, 0] = 0.0
    return np.packbits((d > np.median(d)).astype(np.uint8).ravel())


def _struct(luma):
    g = cv2.resize(luma.astype(np.float32), (64, 64))

    def z(a):
        a = np.asarray(a, np.float32)
        return (a - a.mean()) / (a.std() + 1e-6)

    macro = z(cv2.resize(g, (16, 16)))
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    edge = z(cv2.resize(np.hypot(gx, gy), (16, 16)))
    freq = z(cv2.resize(np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(g)))), (16, 16)))
    v = np.concatenate((macro.ravel(), edge.ravel(), 0.6 * freq.ravel())).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def _hsv_hist(rgb):
    u8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256]).ravel().astype(np.float32)
    return hist / (np.linalg.norm(hist) + 1e-9)


def _fine_energy(luma):
    return float(np.std(luma - cv2.GaussianBlur(luma.astype(np.float32), (0, 0), 2.0)))


def _color_population(rgb):
    hsv = cv2.cvtColor(np.clip(rgb * 255.0, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    code = ((hsv[:, :, 0] // 15).astype(np.int32) * 32
            + (hsv[:, :, 1] // 32).astype(np.int32) * 4
            + (hsv[:, :, 2] // 64).astype(np.int32))
    vals, counts = np.unique(code, return_counts=True)
    return int(np.count_nonzero(counts >= max(8, rgb.shape[0] * rgb.shape[1] // 1000)))


def _spec_preview(spec):
    s = spec[:, :, :3].astype(np.float32)
    # RGB proof makes independently authored M/R/CC populations visible rather
    # than collapsing them into one grayscale score.
    return np.stack((s[:, :, 0], 255.0 - s[:, :, 1], s[:, :, 2]), axis=2).clip(0, 255).astype(np.uint8)


def _save_sheet(items, target, cols=7, tile=256, label_h=28):
    rows = int(math.ceil(len(items) / cols))
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), (15, 17, 21))
    draw = ImageDraw.Draw(sheet)
    for i, (fid, img) in enumerate(items):
        x, y = (i % cols) * tile, (i // cols) * (tile + label_h)
        sheet.paste(Image.fromarray(img).resize((tile, tile), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 4, y + tile + 5), fid, fill=(235, 238, 242))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def _similarity(rows):
    ids = [r["id"] for r in rows]
    struct = np.stack([r.pop("_struct") for r in rows])
    phash = np.stack([r.pop("_phash") for r in rows])
    hist = np.stack([r.pop("_hist") for r in rows])
    cos = struct @ struct.T
    bits = np.unpackbits(phash, axis=1).astype(np.int16) * 2 - 1
    psim = (bits @ bits.T).astype(np.float32)
    psim = (psim + 256.0) / 512.0
    structural = 0.5 * cos + 0.5 * psim
    color = hist @ hist.T
    look = structural * 0.75 + color * 0.25
    np.fill_diagonal(structural, -1.0)
    np.fill_diagonal(color, -1.0)
    np.fill_diagonal(look, -1.0)

    nearest = []
    for i, fid in enumerate(ids):
        j = int(np.argmax(look[i]))
        nearest.append({
            "id": fid,
            "nearest": ids[j],
            "look_similarity": round(float(look[i, j]), 6),
            "structural_similarity": round(float(structural[i, j]), 6),
            "color_similarity": round(float(color[i, j]), 6),
        })
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            pairs.append((float(look[i, j]), float(structural[i, j]), ids[i], ids[j]))
    pairs.sort(reverse=True)
    look_vals = np.asarray([p[0] for p in pairs], np.float32)
    struct_vals = np.asarray([p[1] for p in pairs], np.float32)
    return {
        "pair_count": len(pairs),
        "look_ge_0_80": int(np.count_nonzero(look_vals >= 0.80)),
        "structural_ge_0_80": int(np.count_nonzero(struct_vals >= 0.80)),
        "max_look_similarity": round(float(look_vals.max()), 6),
        "median_look_similarity": round(float(np.median(look_vals)), 6),
        "p95_look_similarity": round(float(np.percentile(look_vals, 95)), 6),
        "max_structural_similarity": round(float(struct_vals.max()), 6),
        "median_structural_similarity": round(float(np.median(struct_vals)), 6),
        "p95_structural_similarity": round(float(np.percentile(struct_vals, 95)), 6),
        "nearest": nearest,
        "top_pairs": [
            {"a": a, "b": b, "look_similarity": round(ls, 6),
             "structural_similarity": round(ss, 6)}
            for ls, ss, a, b in pairs[:20]
        ],
    }


def _row(fid, rgb, spec=None, seconds=None):
    luma = rgb[:, :, :3].mean(axis=2).astype(np.float32)
    row = {
        "id": fid,
        "family": "cryptid" if fid.startswith("fc_") else "morpho",
        "paint_std": round(float(luma.std()), 6),
        "paint_fine_energy": round(_fine_energy(luma), 6),
        "color_population": _color_population(rgb),
        "_struct": _struct(luma),
        "_phash": _phash_bits(luma),
        "_hist": _hsv_hist(rgb),
    }
    if seconds is not None:
        row["cold_seconds_256"] = round(float(seconds), 6)
    if spec is not None:
        channels = []
        for i, name in enumerate(("M", "R", "CC")):
            a = spec[:, :, i].astype(np.float32)
            values, counts = np.unique(a.astype(np.uint8), return_counts=True)
            channels.append({"name": name, "min": int(a.min()), "max": int(a.max()),
                             "mean": round(float(a.mean()), 6),
                             "std": round(float(a.std()), 6), "levels": int(values.size),
                             "tier_values": [int(v) for v in values],
                             "tier_counts": [int(v) for v in counts],
                             "tier_fractions": [round(float(v / a.size), 8) for v in counts],
                             "min_tier_fraction": round(float(counts.min() / a.size), 8)})
        corr = np.corrcoef(spec[:, :, :3].reshape(-1, 3), rowvar=False)
        row["spec_channels"] = channels
        row["spec_pairwise_corr"] = {
            "M_R": round(float(corr[0, 1]), 6),
            "M_CC": round(float(corr[0, 2]), 6),
            "R_CC": round(float(corr[1, 2]), 6),
        }
        row["spec_max_abs_corr"] = round(float(np.max(np.abs(corr[np.triu_indices(3, 1)]))), 6)
        metal = spec[:, :, 0].astype(np.float32)
        inverse_rough = 255.0 - spec[:, :, 1].astype(np.float32)
        coat = spec[:, :, 2].astype(np.float32)
        light_a = (ANGLE_A_WEIGHTS[0] * metal + ANGLE_A_WEIGHTS[1] * inverse_rough
                   + ANGLE_A_WEIGHTS[2] * coat)
        light_b = (ANGLE_B_WEIGHTS[0] * metal + ANGLE_B_WEIGHTS[1] * inverse_rough
                   + ANGLE_B_WEIGHTS[2] * coat)
        row["flip_response_delta"] = round(float(np.mean(np.abs(light_a - light_b))), 6)
        # Chroma proof, not a brightness-only proxy: compare saturation-weighted
        # hue populations revealed by two material-angle response mixes.
        pu8 = np.clip(rgb[:, :, :3] * 255.0, 0, 255).astype(np.uint8)
        hsv = cv2.cvtColor(pu8, cv2.COLOR_RGB2HSV).astype(np.float32)
        hue_bin = np.clip((hsv[:, :, 0] / 180.0 * 24.0).astype(np.int16), 0, 23)
        chroma = hsv[:, :, 1] / 255.0
        value = hsv[:, :, 2] / 255.0
        colored = (chroma >= FLIP_MIN_SATURATION) & (value >= FLIP_MIN_VALUE)
        row["flip_colored_pixel_fraction"] = round(float(colored.mean()), 6)
        wa = np.maximum(light_a, 1.0) * chroma * value * colored
        wb = np.maximum(light_b, 1.0) * chroma * value * colored
        ha = np.bincount(hue_bin.ravel(), weights=wa.ravel(), minlength=24).astype(np.float64)
        hb = np.bincount(hue_bin.ravel(), weights=wb.ravel(), minlength=24).astype(np.float64)
        ha /= max(float(ha.sum()), 1e-9)
        hb /= max(float(hb.sum()), 1e-9)
        row["flip_hue_histogram_tv"] = round(float(0.5 * np.abs(ha - hb).sum()), 6)
        ca = float(np.sum(chroma * light_a * colored) / max(float(np.sum(light_a * colored)), 1e-9))
        cb = float(np.sum(chroma * light_b * colored) / max(float(np.sum(light_b * colored)), 1e-9))
        row["flip_weighted_chroma_delta"] = round(abs(ca - cb), 6)
    return row


def audit_existing(source, out_dir):
    paths = sorted(source.glob("fc_*.png")) + sorted(source.glob("fmo_*.png"))
    rows, sheet = [], []
    for p in paths:
        rgb = np.asarray(Image.open(p).convert("RGB").resize((SIZE, SIZE), Image.Resampling.LANCZOS), np.float32) / 255.0
        rows.append(_row(p.stem, rgb))
        sheet.append((p.stem, (rgb * 255).astype(np.uint8)))
    _save_sheet(sheet, out_dir / "contact_sheet.png")
    return rows


def audit_render(out_dir):
    entries = _ids_and_entries()
    rows, paint_sheet, spec_sheet = [], [], []
    paint_dir, spec_dir = out_dir / "paint", out_dir / "spec"
    paint_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)
    shape = (SIZE, SIZE)
    mask = np.ones(shape, np.float32)
    paint = np.full((*shape, 3), 0.18, np.float32)
    bb = np.zeros(shape, np.float32)
    for fid, (spec_fn, paint_fn) in entries.items():
        start = time.perf_counter()
        rgb = paint_fn(paint.copy(), shape, mask, 7777, 1.0, bb)
        spec = spec_fn(shape, mask, 7777, 1.0)
        seconds = time.perf_counter() - start
        pu8 = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        su8 = _spec_preview(spec)
        Image.fromarray(pu8).save(paint_dir / f"{fid}.png")
        Image.fromarray(su8).save(spec_dir / f"{fid}.png")
        rows.append(_row(fid, rgb, spec, seconds))
        paint_sheet.append((fid, pu8))
        spec_sheet.append((fid, su8))
    _save_sheet(paint_sheet, out_dir / "paint_contact_sheet.png")
    _save_sheet(spec_sheet, out_dir / "spec_contact_sheet.png")
    return rows


def audit_native_perf(out_dir):
    """Cold-render every finish at native 2048 without retaining giant files."""
    from engine.expansions.fractured_wilds_signatures_2026 import clear_design_cache

    entries = _ids_and_entries()
    shape = (2048, 2048)
    mask = np.ones(shape, np.float32)
    paint = np.full((*shape, 3), 0.18, np.float32)
    bb = np.zeros(shape, np.float32)
    crop_ids = {
        "fc_sasquatch_fur", "fc_eyeshine", "fc_webbed_membrane", "fc_dragon_hex_glass",
        "fmo_glasswing", "fmo_fire_agate", "fmo_oil_beetle", "fmo_spectrolite_vein",
        "fmo_paua_storm", "fmo_swallowtail",
    }
    crop_items = []
    rows = []
    for fid, (spec_fn, paint_fn) in entries.items():
        clear_design_cache()
        gc.collect()
        started = time.perf_counter()
        rgb = paint_fn(paint, shape, mask, 7777, 1.0, bb)
        spec = spec_fn(shape, mask, 7777, 1.0)
        elapsed = time.perf_counter() - started
        rows.append({"id": fid, "family": "cryptid" if fid.startswith("fc_") else "morpho",
                     "cold_seconds_2048": round(float(elapsed), 6)})
        if fid in crop_ids:
            y0 = (shape[0] - 512) // 2
            x0 = (shape[1] - 512) // 2
            pu8 = np.clip(rgb[y0:y0 + 512, x0:x0 + 512] * 255.0, 0, 255).astype(np.uint8)
            su8 = _spec_preview(spec[y0:y0 + 512, x0:x0 + 512])
            crop_items.append((fid + " paint", pu8))
            crop_items.append((fid + " material", su8))
        del rgb, spec
    times = np.asarray([r["cold_seconds_2048"] for r in rows], np.float64)
    report = {
        "schema": 1,
        "count": len(rows),
        "seconds_total": round(float(times.sum()), 6),
        "median_seconds_2048": round(float(np.median(times)), 6),
        "p95_seconds_2048": round(float(np.percentile(times, 95)), 6),
        "max_seconds_2048": round(float(times.max()), 6),
        "count_over_3_seconds": int(np.count_nonzero(times > 3.0)),
        "finishes": rows,
    }
    (out_dir / "native_perf.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _save_sheet(crop_items, out_dir / "native_2048_crops.png", cols=4, tile=512, label_h=32)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("existing", "render", "native-perf"), required=True)
    ap.add_argument("--source", type=Path, default=ROOT / "thumbnails" / "monolithic")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    if args.mode == "native-perf":
        report = audit_native_perf(out_dir)
        print(json.dumps({k: report[k] for k in (
            "count", "seconds_total", "median_seconds_2048", "p95_seconds_2048",
            "max_seconds_2048", "count_over_3_seconds")}, indent=2))
        return 0 if report["count"] == 70 and report["count_over_3_seconds"] == 0 else 2
    rows = audit_existing(args.source.resolve(), out_dir) if args.mode == "existing" else audit_render(out_dir)
    sim = _similarity(rows)
    report = {
        "schema": 1,
        "mode": args.mode,
        "count": len(rows),
        "cryptid_count": sum(r["family"] == "cryptid" for r in rows),
        "morpho_count": sum(r["family"] == "morpho" for r in rows),
        "seconds": round(time.perf_counter() - started, 3),
        "similarity": sim,
        "finishes": rows,
    }
    (out_dir / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("mode", "count", "cryptid_count", "morpho_count", "seconds")}, indent=2))
    print(json.dumps({k: sim[k] for k in (
        "look_ge_0_80", "structural_ge_0_80", "max_look_similarity",
        "median_look_similarity", "p95_look_similarity", "max_structural_similarity",
        "median_structural_similarity", "p95_structural_similarity")}, indent=2))
    return 0 if len(rows) == 70 else 2


if __name__ == "__main__":
    raise SystemExit(main())
