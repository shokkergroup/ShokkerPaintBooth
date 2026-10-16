"""Compact staged-material evidence for the FRACTURED HOUDINI rebuild.

This is deliberately an offline renderer audit: it proves carrier and M/R/Cc
distribution, plus a simple grazing proxy.  It is *not* a substitute for the
required same-location in-game light captures before a card is promoted live.

SPB-2026-08-30 / Owner direction: repeated hidden material motifs must remain
in M/R/Cc while the paint carrier reads as a complete neutral-light finish.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from engine.expansions.fractured_houdini_2026 import LIVE_PAIRS


OUT = ROOT / "_houdini_proof"
SIZE = 512
SEED = 42


def norm_u8(a: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(a, (1, 99))
    return np.clip((a - lo) * 255.0 / max(hi - lo, 1e-5), 0, 255).astype(np.uint8)


def grazing_proxy(spec: np.ndarray) -> np.ndarray:
    """A diagnostic contrast proxy, not a physical BRDF or track-light claim."""
    metal = spec[..., 0].astype(np.float32) / 255.0
    rough = spec[..., 1].astype(np.float32) / 255.0
    coat = spec[..., 2].astype(np.float32) / 255.0
    response = 0.70 * metal + 0.55 * coat + 0.35 * (1.0 - rough)
    return cv2.applyColorMap(norm_u8(response), cv2.COLORMAP_TURBO)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    source = np.full((SIZE, SIZE, 3), 132, np.uint8)
    mask = np.full((SIZE, SIZE), 255, np.uint8)
    cards: list[np.ndarray] = []
    rows: list[tuple[str, float, float, float, float, float]] = []

    for finish_id, (spec_fn, paint_fn) in LIVE_PAIRS.items():
        spec = spec_fn((SIZE, SIZE), SEED)
        paint = paint_fn(source, (SIZE, SIZE), mask, SEED, 1.0, None)
        # Houdini paint functions return normalized float RGB, whereas cv2
        # proof panels are uint8.  Convert once so the contact sheet and the
        # recorded carrier metrics describe the same pixels.
        if np.issubdtype(paint.dtype, np.floating) and float(paint.max()) <= 1.5:
            paint = paint * 255.0
        paint = np.clip(paint, 0, 255).astype(np.uint8)
        if paint.ndim == 2:
            paint = cv2.cvtColor(paint, cv2.COLOR_GRAY2BGR)
        else:
            # The authored finish returns RGB; proof sheets are written BGR.
            paint = cv2.cvtColor(paint, cv2.COLOR_RGB2BGR)
        combined = cv2.cvtColor(spec, cv2.COLOR_RGB2BGR)
        graze = grazing_proxy(spec)
        label = finish_id.removeprefix("houdini_").replace("_", " ").upper()
        panel = np.concatenate((paint, combined, graze), axis=1)
        cv2.putText(panel, label, (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.56,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(panel, "PAINT / M-R-CC / GRAZING DIAGNOSTIC", (10, 500),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cards.append(panel)
        rows.append((finish_id, float(paint.mean() / 255), float(paint.std() / 255),
                     float(spec[..., 0].std()), float(spec[..., 1].std()),
                     float(spec[..., 2].std())))

    cols = 2
    card_h, card_w = cards[0].shape[:2]
    sheet = np.zeros((((len(cards) + cols - 1) // cols) * card_h, cols * card_w, 3), np.uint8)
    for idx, card in enumerate(cards):
        y, x = divmod(idx, cols)
        sheet[y * card_h:(y + 1) * card_h, x * card_w:(x + 1) * card_w] = card
    out = OUT / "houdini_paint_combined_grazing_r4.png"
    cv2.imwrite(str(out), sheet)

    print("finish\tpaint_mean\tpaint_std\tmetal_std\trough_std\tcoat_std")
    for row in rows:
        print("%s\t%.4f\t%.4f\t%.2f\t%.2f\t%.2f" % row)
    minimum = min(min(row[3:]) for row in rows)
    print(f"minimum_spec_channel_std={minimum:.2f}")
    print(f"contact_sheet={out}")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
