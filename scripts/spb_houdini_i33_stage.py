"""Staging-only visual proof for H1-I33 Midnight Filigree.

Does not touch a catalog manifest, live static assets, or runtime routing.
It renders the isolated candidate at effective preview fidelity and writes a
standard card, buyer-split card, literal M/R/Cc view, and a deliberately
labelled diagnostic grazing proxy for owner-eye iteration.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.expansions.fractured_houdini_veiled_skull_i33_2026 import (  # noqa: E402
    paint_veiled_skull_i33, spec_veiled_skull_i33,
)


def _lit(spec: np.ndarray) -> np.ndarray:
    """Literal channel swatches, left-to-right M / Rough / Cc."""
    return np.concatenate([np.dstack([spec[..., 0]]*3), np.dstack([spec[..., 1]]*3), np.dstack([spec[..., 2]]*3)], axis=1)


def _grazing(spec: np.ndarray) -> np.ndarray:
    """Diagnostic only: emphasizes opposing M/R/Cc states, not track proof."""
    m, r, c = (spec[..., n].astype(np.float32)/255.0 for n in range(3))
    cool = np.clip(1.25*m*(1-r) + .35*c, 0, 1)
    warm = np.clip(1.15*c*(1-r) + .22*m, 0, 1)
    dark = np.clip(.88*r*(1-m), 0, 1)
    return np.dstack([warm, cool, dark])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--master', type=int, default=1024)
    p.add_argument('--out', type=Path, default=ROOT / '_houdini_i33_p1_dev')
    a = p.parse_args(); size = int(a.master); a.out.mkdir(parents=True, exist_ok=True)
    source = np.full((size, size, 3), 132, np.uint8); mask = np.full((size, size), 255, np.uint8)
    paint = paint_veiled_skull_i33(source, (size, size), mask, a.seed, 1.0, None)
    spec = spec_veiled_skull_i33((size, size), a.seed, 1.0, 0, 0)
    paint8 = np.clip(paint*255, 0, 255).astype(np.uint8)
    standard = cv2.resize(paint8, (256, 256), interpolation=cv2.INTER_AREA)
    picker = np.concatenate((cv2.resize(paint8, (48, 48), interpolation=cv2.INTER_AREA), cv2.resize(spec, (48, 48), interpolation=cv2.INTER_AREA)), axis=1)
    picker[:, 47:49] = 20
    def save(name: str, rgb: np.ndarray) -> None:
        if rgb.dtype.kind == 'f': rgb = np.clip(rgb*255, 0, 255).astype(np.uint8)
        if not cv2.imwrite(str(a.out/name), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
            raise RuntimeError(name)
    save('standard.png', standard); save('picker_split.png', picker)
    save('literal_mrc.png', cv2.resize(_lit(spec), (1536, 512), interpolation=cv2.INTER_NEAREST))
    save('grazing_diagnostic_not_track.png', cv2.resize(_grazing(spec), (1024, 512), interpolation=cv2.INTER_LINEAR))
    print('stage=', a.out)
    print('paint_std=%.4f mrc_std=%.2f/%.2f/%.2f' % (paint.std(), *(spec[..., n].std() for n in range(3))))


if __name__ == '__main__':
    main()
