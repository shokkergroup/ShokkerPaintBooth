"""Owner-eye rejection audit for the 110 Fractured Wilds finishes.

SPB-WILDS-REJECTION-2026-08-24, tick WR-1. Owner verdict: "the biggest
cardinal sin PERIOD of this app - LAZY"; recolored paint topology, repeated
spec topology, and random-noise separation do not create a new finish.

This script deliberately removes palette and channel-level remapping from the
review surfaces. It emits lane-sized contacts for:

* the actual paint;
* palette-invariant paint boundaries at fine and coarse scales;
* percentile-normalized M/R/Cc topology; and
* channel-independent spec edges.

The numeric descriptor is only a candidate sorter. It is not an acceptance
gate and must never overrule the contact sheets or the owner's eye.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.registry import MONOLITHIC_REGISTRY  # noqa: E402
from scripts.spb_wilds_110_bake import _install_and_ids  # noqa: E402


LANE_PREFIX = {
    "cryptid": "fc_",
    "morpho": "fmo_",
    "bloom": "fbl_",
    "petri": "fpe_",
}


def _u8_rgb(value: np.ndarray) -> np.ndarray:
    a = np.asarray(value, np.float32)
    if a.size and float(a.max()) <= 1.5:
        a = a * 255.0
    return np.clip(a[..., :3], 0.0, 255.0).astype(np.uint8)


def _robust_u8(field: np.ndarray, low: float = 2.0, high: float = 98.0) -> np.ndarray:
    a = np.nan_to_num(np.asarray(field, np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    lo, hi = np.percentile(a, (low, high))
    if float(hi - lo) < 1e-6:
        return np.zeros(a.shape, np.uint8)
    return np.clip((a - lo) * (255.0 / float(hi - lo)), 0.0, 255.0).astype(np.uint8)


def _gradient_magnitude(channel: np.ndarray, sigma: float) -> np.ndarray:
    f = np.asarray(channel, np.float32)
    if sigma > 0:
        f = cv2.GaussianBlur(f, (0, 0), sigma)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def _paint_structure(paint_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return fine and coarse boundary maps without preserving the palette."""
    rgb = _u8_rgb(paint_rgb)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    channels = [lab[:, :, index] for index in range(3)]

    # A boundary in any Lab dimension counts. Per-image robust normalization
    # removes the advantage of simply choosing more saturated colors.
    fine = np.maximum.reduce([
        _robust_u8(_gradient_magnitude(channel, 0.65)).astype(np.float32)
        for channel in channels
    ])
    coarse = np.maximum.reduce([
        _robust_u8(_gradient_magnitude(channel, 2.4)).astype(np.float32)
        for channel in channels
    ])
    local_luma = np.abs(channels[0] - cv2.GaussianBlur(channels[0], (0, 0), 4.2))
    fine = np.maximum(fine, _robust_u8(local_luma).astype(np.float32) * 0.72)
    coarse = np.maximum(coarse, _robust_u8(local_luma, 4.0, 96.0).astype(np.float32) * 0.48)
    return np.clip(fine, 0, 255).astype(np.uint8), np.clip(coarse, 0, 255).astype(np.uint8)


def _rank_u8(channel: np.ndarray) -> np.ndarray:
    """Normalize value remaps while retaining the channel's spatial ordering."""
    a = np.asarray(channel, np.uint8)
    hist = np.bincount(a.ravel(), minlength=256).astype(np.int64)
    cumulative = np.cumsum(hist) - hist // 2
    denom = max(1, int(a.size - 1))
    lut = np.clip(np.rint(cumulative * (255.0 / denom)), 0, 255).astype(np.uint8)
    return lut[a]


def _spec_structure(spec: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    s = np.asarray(spec)
    if s.ndim != 3 or s.shape[2] < 3:
        raise ValueError(f"expected M/R/Cc image, got {s.shape!r}")
    rank = np.stack([_rank_u8(s[:, :, index]) for index in range(3)], axis=2)
    edges = np.maximum.reduce([
        _robust_u8(_gradient_magnitude(rank[:, :, index], 1.15)).astype(np.float32)
        for index in range(3)
    ])
    return rank, np.clip(edges, 0, 255).astype(np.uint8)


def _render(finish_id: str, size: int) -> tuple[np.ndarray, np.ndarray]:
    spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_id][:2]
    shape = (size, size)
    mask = np.ones(shape, np.float32)
    source = np.full((*shape, 3), 0.18, np.float32)
    paint = paint_fn(source, shape, mask, 20260824, 1.0, np.zeros(shape, np.float32))
    spec = spec_fn(shape, mask, 20260824, 1.0)
    return _u8_rgb(paint), np.asarray(spec, np.uint8)


def _gray_rgb(image: np.ndarray) -> np.ndarray:
    a = np.asarray(image)
    if a.ndim == 2:
        return np.repeat(a[:, :, None], 3, axis=2).astype(np.uint8)
    return a[:, :, :3].astype(np.uint8)


def _save_contact(items: list[tuple[str, np.ndarray]], target: Path, *, cols: int = 5) -> None:
    if not items:
        return
    tile = int(items[0][1].shape[0])
    label_h = 30
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), (9, 11, 15))
    draw = ImageDraw.Draw(sheet)
    for index, (finish_id, image) in enumerate(items):
        x = (index % cols) * tile
        y = (index // cols) * (tile + label_h)
        sheet.paste(Image.fromarray(_gray_rgb(image)), (x, y))
        draw.text((x + 4, y + tile + 6), finish_id, fill=(238, 241, 245))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def _descriptor(structure: np.ndarray) -> np.ndarray:
    """Palette-invariant texture descriptor used only to sort likely clones."""
    image = cv2.resize(np.asarray(structure, np.uint8), (128, 128), interpolation=cv2.INTER_AREA)
    f = image.astype(np.float32) / 255.0

    # Multi-scale Gabor energy describes dots/lines/cells independent of exact
    # phase. Rotation is discounted by sorting each orientation bank.
    features: list[float] = []
    for wavelength in (4.0, 7.0, 12.0, 20.0):
        bank = []
        for theta in np.linspace(0.0, np.pi, 8, endpoint=False):
            kernel = cv2.getGaborKernel((21, 21), 3.2, float(theta), wavelength, 0.55, 0, ktype=cv2.CV_32F)
            response = np.abs(cv2.filter2D(f, cv2.CV_32F, kernel))
            bank.append((float(response.mean()), float(response.std())))
        for mean, std in sorted(bank):
            features.extend((mean, std))

    # Radial Fourier power ignores translation and discounts phase/seed.
    spectrum = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(f - float(f.mean()))))).astype(np.float32)
    yy, xx = np.mgrid[:128, :128]
    radius = np.hypot(xx - 63.5, yy - 63.5)
    for lo, hi in zip(np.linspace(1, 60, 17)[:-1], np.linspace(1, 60, 17)[1:]):
        band = spectrum[(radius >= lo) & (radius < hi)]
        features.append(float(band.mean()) if band.size else 0.0)

    # Edge occupancy across thresholds separates cellular walls, dots, bands,
    # and filaments without caring which color occupied either side.
    for threshold in (32, 64, 96, 128, 160, 192, 224):
        binary = (image >= threshold).astype(np.uint8)
        count, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        areas = stats[1:, cv2.CC_STAT_AREA] if count > 1 else np.asarray([], np.int32)
        features.extend((
            float(binary.mean()),
            float(np.median(areas)) / image.size if areas.size else 0.0,
            float(np.percentile(areas, 90)) / image.size if areas.size else 0.0,
        ))

    vector = np.asarray(features, np.float32)
    vector -= float(vector.mean())
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-8 else vector


def build(output: Path, size: int) -> dict:
    lanes, finish_ids = _install_and_ids()
    output.mkdir(parents=True, exist_ok=True)
    images: dict[str, dict[str, np.ndarray]] = {}
    descriptors: dict[str, np.ndarray] = {}

    for index, finish_id in enumerate(finish_ids, 1):
        paint, spec = _render(finish_id, size)
        fine, coarse = _paint_structure(paint)
        spec_rank, spec_edges = _spec_structure(spec)
        images[finish_id] = {
            "paint": paint,
            "paint_fine": fine,
            "paint_coarse": coarse,
            "spec_rank": spec_rank,
            "spec_edges": spec_edges,
        }
        descriptors[finish_id] = np.concatenate((_descriptor(fine), _descriptor(coarse), _descriptor(spec_edges)))
        print(f"[wilds-motif-rejection] {index:03d}/{len(finish_ids)} {finish_id}", flush=True)

    for lane, ids in lanes.items():
        lane_dir = output / lane
        lane_dir.mkdir(exist_ok=True)
        for kind in ("paint", "paint_fine", "paint_coarse", "spec_rank", "spec_edges"):
            items = [(finish_id, images[finish_id][kind]) for finish_id in ids]
            _save_contact(items, lane_dir / f"{lane}_{kind}_contact.png")
            individual = lane_dir / kind
            individual.mkdir(exist_ok=True)
            for finish_id, image in items:
                Image.fromarray(_gray_rgb(image)).save(individual / f"{finish_id}.png")

    pairs = []
    for left_index, left in enumerate(finish_ids):
        for right in finish_ids[left_index + 1:]:
            score = float(np.dot(descriptors[left], descriptors[right]))
            pairs.append({"left": left, "right": right, "descriptorSimilarity": round(score, 6)})
    pairs.sort(key=lambda item: item["descriptorSimilarity"], reverse=True)

    report = {
        "schema": 1,
        "ticket": "SPB-WILDS-REJECTION-2026-08-24 WR-1",
        "ownerVerdict": "same paint/spec topology recolored is lazy; random noise does not count",
        "count": len(finish_ids),
        "lanes": {lane: len(ids) for lane, ids in lanes.items()},
        "resolution": size,
        "descriptorWarning": "candidate sorter only; never an acceptance gate",
        "topPairs": pairs[:400],
    }
    (output / "motif_rejection_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=256)
    args = parser.parse_args()
    if args.size < 128 or args.size > 512:
        parser.error("--size must be between 128 and 512")
    report = build(args.output.resolve(), args.size)
    print(json.dumps({key: value for key, value in report.items() if key != "topPairs"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
