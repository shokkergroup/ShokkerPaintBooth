#!/usr/bin/env python3
"""Render picker spec overlays as lit stock-car material review cards.

SPB-105 Round 4, 2026-07-13.  This is an owner-eye companion to the numeric
gate: it renders the real 2048 M/R/CC arrays, then previews their material
response on a car silhouette instead of judging only square debug maps.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_IDS = (
    "spec_chrome_oval_chain", "spec_knurled_socket_grip",
    "cc_wet_zone", "spec_rain_bead_aero",
    "spec_black_emboss_mandala", "vinyl_stretched",
    "spec_noir_houndstooth_star", "spec_ceramic_brake_sinter",
    "spec_mud_crackle_dried", "spec_ice_facet_shatter",
    "spec_holographic_oil_circuit", "spec_weld_stack_rainbow",
    "spec_carbon_2x2_twill", "spec_nomex_honeycomb_core",
    "spec_exhaust_soot_gradient", "salt_spray_corrosion",
)

RENDER = 2048
CARD_W, CARD_H = 620, 350


def _car_mask(h: int, w: int) -> np.ndarray:
    mask = np.zeros((h, w), dtype=np.uint8)
    points = np.asarray([
        (20, 245), (55, 215), (175, 195), (225, 138), (274, 92),
        (382, 92), (430, 139), (475, 184), (562, 205), (602, 238),
        (596, 278), (528, 294), (90, 294), (32, 274),
    ], dtype=np.int32)
    cv2.fillPoly(mask, [points], 255)
    for cx in (150, 480):
        cv2.circle(mask, (cx, 283), 56, 0, thickness=-1)
    return mask


def _lit_card(pid: str, arr: np.ndarray) -> np.ndarray:
    card = np.full((CARD_H, CARD_W, 3), np.asarray((18, 21, 28), dtype=np.float32) / 255.0, dtype=np.float32)
    view = cv2.resize(arr[:, :, :3], (CARD_W, CARD_H), interpolation=cv2.INTER_AREA)
    m, rough, cc = (view[:, :, index] for index in range(3))
    yy, xx = np.mgrid[0:CARD_H, 0:CARD_W].astype(np.float32)
    nx = (xx / CARD_W - .5) * 1.4
    ny = (yy / CARD_H - .52) * 1.7
    body_light = np.clip(.78 - np.hypot(nx * .55, ny), .10, .88)
    ribbon = np.exp(-((ny + .45 + nx * .17) / .16) ** 2)
    gloss = np.clip(1.0 - rough, 0.0, 1.0)
    base = np.asarray((.62, .035, .055), dtype=np.float32)
    metal = np.asarray((.72, .77, .86), dtype=np.float32)
    rgb = base[None, None, :] * (.28 + body_light[:, :, None] * .62)
    rgb = rgb * (1.0 - m[:, :, None] * .62) + metal[None, None, :] * m[:, :, None] * (.40 + body_light[:, :, None] * .50)
    response = ribbon * (gloss ** 1.7 * .78 + cc ** 1.5 * .58)
    rgb += response[:, :, None] * np.asarray((1.0, .92, .82), dtype=np.float32)
    rgb += (cc * .08)[:, :, None] * np.asarray((.30, .48, 1.0), dtype=np.float32)
    mask = _car_mask(CARD_H, CARD_W)
    card[mask > 0] = np.clip(rgb[mask > 0], 0.0, 1.0)

    for cx in (150, 480):
        cv2.circle(card, (cx, 283), 51, (.025, .028, .035), thickness=-1)
        cv2.circle(card, (cx, 283), 27, (.24, .27, .31), thickness=-1)
        cv2.circle(card, (cx, 283), 11, (.06, .07, .08), thickness=-1)
    cv2.polylines(card, [np.asarray([(20, 245), (55, 215), (175, 195), (225, 138), (274, 92),
                                            (382, 92), (430, 139), (475, 184), (562, 205), (602, 238)], np.int32)],
                  False, (.72, .74, .78), 2, cv2.LINE_AA)
    cv2.putText(card, pid, (18, 30), cv2.FONT_HERSHEY_SIMPLEX, .62, (.93, .94, .97), 1, cv2.LINE_AA)
    return np.clip(card * 255.0, 0, 255).astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids", default=",".join(DEFAULT_IDS))
    ap.add_argument("--seed", type=int, default=7301)
    ap.add_argument("--columns", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "_spec_overlay_overhaul" / "round4_car_review.png"))
    args = ap.parse_args()
    ids = [value.strip() for value in args.ids.split(",") if value.strip()]

    with io.StringIO() as quiet:
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout = sys.stderr = quiet
            from engine.spec_patterns import PATTERN_CATALOG
        finally:
            sys.stdout, sys.stderr = old_out, old_err

    cards = []
    for pid in ids:
        fn = PATTERN_CATALOG.get(pid)
        if fn is None:
            raise KeyError(f"missing spec overlay: {pid}")
        arr = np.asarray(fn((RENDER, RENDER), args.seed, 1.0), dtype=np.float32)
        if arr.ndim == 2:
            arr = np.repeat(arr[:, :, None], 3, axis=2)
        cards.append(_lit_card(pid, np.clip(arr, 0.0, 1.0)))

    columns = max(1, int(args.columns))
    rows = (len(cards) + columns - 1) // columns
    sheet = np.full((rows * CARD_H, columns * CARD_W, 3), (12, 14, 19), dtype=np.uint8)
    for index, card in enumerate(cards):
        y, x = divmod(index, columns)
        sheet[y * CARD_H:(y + 1) * CARD_H, x * CARD_W:(x + 1) * CARD_W] = card
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), sheet[:, :, ::-1]):
        raise OSError(f"failed to write {out}")
    print(f"Rendered {len(cards)} 2048 spec overlays -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
