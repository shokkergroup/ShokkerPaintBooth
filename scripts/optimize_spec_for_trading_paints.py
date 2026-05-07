#!/usr/bin/env python
"""Create Trading Paints-friendly spec-map variants.

Trading Paints appears to serve back aggressively recompressed spec MIPs in at
least one real repro. This prototype keeps material data in the spec map, but
reduces the kind of high-frequency entropy that gets destroyed by heavy MIP
compression.

The script outputs several 2048x2048 spec TGAs. Copy one variant to
``car_spec_<id>.tga``, let iRacing generate the MIP, then compare the generated
MIP size and visual result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.core import write_tga_32bit


@dataclass(frozen=True)
class Variant:
    name: str
    base_size: int
    median: int
    blur_sigma: float
    bilateral: bool
    levels_m: int
    levels_r: int
    levels_c: int
    detail_strength: float
    detail_threshold: float


VARIANTS = (
    Variant("tp_quality", 1536, 3, 0.55, True, 48, 36, 28, 0.22, 10.0),
    Variant("tp_balanced", 1024, 3, 0.85, True, 32, 28, 20, 0.16, 14.0),
    Variant("tp_compact", 768, 5, 1.05, False, 24, 20, 16, 0.10, 18.0),
    Variant("tp_hardcap", 512, 5, 1.35, False, 18, 16, 12, 0.06, 24.0),
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_rgba(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.asarray(img.convert("RGBA"), dtype=np.uint8)


def _quantize(ch: np.ndarray, levels: int, lo: int | None = None, hi: int | None = None) -> np.ndarray:
    levels = max(2, int(levels))
    src = ch.astype(np.float32)
    if lo is None:
        lo = int(src.min())
    if hi is None:
        hi = int(src.max())
    if hi <= lo:
        return np.full_like(ch, lo, dtype=np.uint8)
    norm = np.clip((src - lo) / float(hi - lo), 0.0, 1.0)
    q = np.round(norm * (levels - 1)) / float(levels - 1)
    return np.clip(lo + q * (hi - lo), 0, 255).astype(np.uint8)


def _smooth_channel(ch: np.ndarray, variant: Variant) -> np.ndarray:
    out = ch
    if variant.base_size and variant.base_size < ch.shape[0]:
        out = cv2.resize(out, (variant.base_size, variant.base_size), interpolation=cv2.INTER_AREA)
        out = cv2.resize(out, (ch.shape[1], ch.shape[0]), interpolation=cv2.INTER_CUBIC)
    if variant.bilateral:
        out = cv2.bilateralFilter(out, 7, 22, 13)
    if variant.median > 1:
        out = cv2.medianBlur(out, int(variant.median))
    if variant.blur_sigma > 0:
        out = cv2.GaussianBlur(out, (0, 0), variant.blur_sigma)
    return out.astype(np.uint8)


def _coherent_detail(original: np.ndarray, smooth: np.ndarray, strength: float, threshold: float) -> np.ndarray:
    if strength <= 0:
        return smooth
    detail = original.astype(np.float32) - cv2.GaussianBlur(original, (0, 0), 2.2).astype(np.float32)
    mask = np.abs(detail) >= float(threshold)
    # Keep only stronger, coherent detail. Weak per-pixel shimmer is exactly
    # what makes the MIP expensive and then gets flattened by TP.
    out = smooth.astype(np.float32)
    out[mask] += detail[mask] * float(strength)
    return np.clip(out, 0, 255).astype(np.uint8)


def _optimize(arr: np.ndarray, variant: Variant) -> np.ndarray:
    m, r, c, a = (arr[:, :, idx] for idx in range(4))

    m_s = _smooth_channel(m, variant)
    r_s = _smooth_channel(r, variant)
    c_s = _smooth_channel(c, variant)

    m_q = _quantize(_coherent_detail(m, m_s, variant.detail_strength, variant.detail_threshold), variant.levels_m)
    r_q = _quantize(_coherent_detail(r, r_s, variant.detail_strength * 0.55, variant.detail_threshold), variant.levels_r, lo=15, hi=max(16, int(r.max())))
    c_q = _quantize(_coherent_detail(c, c_s, variant.detail_strength * 0.45, variant.detail_threshold), variant.levels_c, lo=16, hi=max(17, int(c.max())))

    # Preserve iRacing's roughness/clearcoat floors and make alpha fully opaque.
    r_q = np.where(m_q < 240, np.maximum(r_q, 15), r_q).astype(np.uint8)
    c_q = np.maximum(c_q, 16).astype(np.uint8)
    a_q = np.full_like(a, 255, dtype=np.uint8)
    return np.dstack([m_q, r_q, c_q, a_q]).astype(np.uint8)


def _entropy(ch: np.ndarray) -> float:
    counts = np.bincount(ch.ravel(), minlength=256).astype(np.float64)
    p = counts[counts > 0] / float(ch.size)
    return float(-(p * np.log2(p)).sum())


def _mip_zlib_estimate(arr: np.ndarray) -> int:
    total = 0
    cur = arr
    while True:
        total += len(zlib.compress(np.ascontiguousarray(cur).tobytes(), 9))
        h, w = cur.shape[:2]
        if h <= 1 and w <= 1:
            break
        cur = cv2.resize(cur, (max(1, w // 2), max(1, h // 2)), interpolation=cv2.INTER_AREA)
    return int(total)


def _stats(arr: np.ndarray, original: np.ndarray | None = None) -> dict[str, Any]:
    names = ("M", "R", "C", "A")
    channels: dict[str, Any] = {}
    for idx, name in enumerate(names):
        ch = arr[:, :, idx]
        item: dict[str, Any] = {
            "min": int(ch.min()),
            "max": int(ch.max()),
            "mean": float(ch.mean()),
            "std": float(ch.std()),
            "unique": int(np.unique(ch).size),
            "entropy_bits": _entropy(ch),
        }
        if original is not None:
            diff = ch.astype(np.float32) - original[:, :, idx].astype(np.float32)
            item["mae_vs_original"] = float(np.mean(np.abs(diff)))
            item["rmse_vs_original"] = float(math.sqrt(float(np.mean(diff * diff))))
        channels[name] = item
    return {
        "channels": channels,
        "mip_chain_zlib_estimate_bytes": _mip_zlib_estimate(arr),
    }


def _write_contact_sheet(original: np.ndarray, variants: list[tuple[str, np.ndarray]], out_path: Path) -> None:
    # RGB visualization of M/R/C channels side by side. This is diagnostic,
    # not a paint preview.
    thumbs = []
    for name, arr in [("original", original)] + variants:
        rgb = arr[:, :, :3]
        thumb = cv2.resize(rgb, (320, 320), interpolation=cv2.INTER_AREA)
        label = np.zeros((46, 320, 3), dtype=np.uint8)
        cv2.putText(label, name, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        thumbs.append(np.vstack([thumb, label]))
    sheet = np.hstack(thumbs)
    Image.fromarray(sheet, "RGB").save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path, help="Input SPB/iRacing car_spec_<id>.tga")
    parser.add_argument("--out-dir", required=True, type=Path, help="Directory for optimized TGA variants")
    parser.add_argument("--prefix", default="car_spec_23371", help="Output filename prefix")
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    original = _load_rgba(args.spec)
    report: dict[str, Any] = {
        "source": str(args.spec),
        "source_sha256": _sha256(args.spec),
        "source_stats": _stats(original),
        "variants": {},
    }

    variant_images: list[tuple[str, np.ndarray]] = []
    for variant in VARIANTS:
        optimized = _optimize(original, variant)
        path = out_dir / f"{args.prefix}_{variant.name}.tga"
        write_tga_32bit(str(path), optimized)
        png_path = out_dir / f"{args.prefix}_{variant.name}_channels.png"
        Image.fromarray(optimized[:, :, :3], "RGB").save(png_path)
        variant_images.append((variant.name, optimized))
        report["variants"][variant.name] = {
            "tga": str(path),
            "channels_png": str(png_path),
            "sha256": _sha256(path),
            "tga_size_bytes": int(path.stat().st_size),
            "settings": variant.__dict__,
            "stats": _stats(optimized, original),
        }

    contact_sheet = out_dir / "tp_spec_optimizer_contact_sheet.png"
    _write_contact_sheet(original, variant_images, contact_sheet)
    report["contact_sheet"] = str(contact_sheet)

    report_path = out_dir / "tp_spec_optimizer_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {len(VARIANTS)} optimized spec variants to {out_dir}")
    print(f"Report: {report_path}")
    print(f"Contact sheet: {contact_sheet}")
    print("\nNext:")
    print("1. Pick a variant, copy it to the iRacing car folder as car_spec_<id>.tga.")
    print("2. Remove the old car_spec_<id>.mip.")
    print("3. Open iRacing so it generates a new MIP.")
    print("4. Check the MIP size and visual quality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
