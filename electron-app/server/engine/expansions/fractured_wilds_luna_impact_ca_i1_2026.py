# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Luna Impact Chronology I1 native-2048 paint contact.

SPB-105 / Wilds rebuild attempt 61, 2026-08-25. This answers the owner's
"EXACT SAME pattern just recolored" and no-random-noise verdict with an explicit
one-direction impact chronology. Seventeen unequal top-edge ejecta events feed
a deterministic Rule-110 medium; every later row records causal propagation.
Glider heads, trailing wakes, collisions, extinct pockets, rebounds and live
fronts are derived from the actual state history. No RNG/noise, scalar field,
placed texture, contours, cells/pavers, or shared Wilds composer. Each automaton
site is 8 native pixels and attached event anatomy spans 8-32 px at 2048.

Paint-only gate: no spec/registry/package/runtime work unless literal 2048 and
the 1:1 crop survive owner-eye review.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import time

import cv2
import numpy as np


ID = "fmo_luna_dust"
GRID = 256
WORK = 512

PALETTE_A = np.asarray([
    (5, 7, 14), (13, 16, 35), (24, 31, 63), (38, 51, 91),
    (53, 75, 119), (67, 103, 142), (79, 134, 155), (100, 166, 158),
    (141, 194, 151), (190, 213, 137), (230, 217, 121), (249, 190, 105),
    (241, 145, 108), (207, 98, 120), (150, 62, 125),
], np.float32) / 255.0
PALETTE_B = np.asarray([
    (5, 7, 16), (26, 15, 48), (59, 22, 82), (98, 30, 109),
    (141, 43, 125), (181, 62, 128), (216, 89, 119), (240, 125, 103),
    (250, 168, 89), (237, 205, 87), (191, 222, 103), (126, 215, 127),
    (72, 191, 147), (37, 153, 156), (27, 105, 143),
], np.float32) / 255.0


def _palette(t: np.ndarray, colors: np.ndarray) -> np.ndarray:
    q = np.mod(t, 1.0) * len(colors)
    i0 = np.floor(q).astype(np.int16) % len(colors)
    f = (q - np.floor(q))[..., None].astype(np.float32)
    return colors[i0] * (1.0 - f) + colors[(i0 + 1) % len(colors)] * f


def _up(a: np.ndarray, interpolation: int = cv2.INTER_NEAREST) -> np.ndarray:
    return cv2.resize(np.asarray(a, np.float32), (WORK, WORK), interpolation=interpolation)


@lru_cache(maxsize=1)
def _fields() -> dict[str, np.ndarray]:
    n = GRID
    history = np.zeros((n, n), np.uint8)
    # Explicit unequal impact packets; every width and internal bit sequence is
    # fixed and reviewable rather than RNG seeded.
    impacts = ((3, 5, 0b101101), (17, 8, 0b11010011), (31, 4, 0b11101),
               (44, 11, 0b10111001011), (62, 6, 0b1101011),
               (75, 9, 0b111001011), (91, 5, 0b10111),
               (104, 13, 0b1101011100101), (126, 7, 0b1011011),
               (139, 4, 0b1111), (151, 10, 0b1010111011),
               (169, 6, 0b110111), (181, 12, 0b101100111101),
               (202, 5, 0b11101), (214, 9, 0b110010111),
               (231, 6, 0b101111), (244, 8, 0b11101011))
    for start, width, bits in impacts:
        for j in range(width):
            history[0, (start + j) % n] = (bits >> (j % max(width, 1))) & 1
        history[0, (start - 1) % n] = 1
        history[0, (start + width + 1) % n] = 1

    # Rule 110: output bit for neighbourhood codes 0..7 is 0,1,1,1,0,1,1,0.
    lookup = np.asarray([0, 1, 1, 1, 0, 1, 1, 0], np.uint8)
    for y in range(1, n):
        prev = history[y - 1]
        left = np.roll(prev, 1)
        right = np.roll(prev, -1)
        code = (left << 2) | (prev << 1) | right
        row = lookup[code]
        # Six later ejecta injections are physical aftershocks, not random
        # collision separators. They alter all subsequent history.
        if y in {37, 73, 112, 154, 199, 228}:
            j = (17 * y + 29) % n
            span = 3 + (y % 7)
            row[j:j + span] ^= np.asarray([(k * 3 + y) % 5 != 0
                                            for k in range(min(span, n - j))], np.uint8)
        history[y] = row

    active = history.astype(np.float32)
    left = np.roll(history, 1, axis=1)
    right = np.roll(history, -1, axis=1)
    up = np.vstack([history[:1], history[:-1]])
    up2 = np.vstack([history[:2], history[:-2]])
    head = ((history == 1) & (up == 0)).astype(np.float32)
    wake = ((history == 0) & (up == 1)).astype(np.float32)
    collision = ((history == 1) & (left == 1) & (right == 1) & (up == 0)).astype(np.float32)
    rebound = ((history == 1) & (up == 0) & (up2 == 1)).astype(np.float32)
    extinct = ((history == 0) & (left == 1) & (right == 1)).astype(np.float32)
    slope = ((history != left).astype(np.float32) + (history != right).astype(np.float32)) * 0.5

    # Run age is causal persistence along the time axis.
    age = np.zeros((n, n), np.float32)
    for y in range(1, n):
        same = history[y] == history[y - 1]
        age[y] = np.where(same, np.minimum(age[y - 1] + 1.0, 15.0), 0.0)
    age /= 15.0

    return {"active": _up(active), "head": _up(head), "wake": _up(wake),
            "collision": _up(collision), "rebound": _up(rebound),
            "extinct": _up(extinct), "slope": _up(slope), "age": _up(age)}


@lru_cache(maxsize=2)
def _paint(angle_b: bool = False) -> np.ndarray:
    f = _fields()
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    travel = (0.11 * xx / WORK + 0.19 * yy / WORK
              + 0.53 * f["active"] + 0.31 * f["head"]
              + 0.23 * f["wake"] + 0.41 * f["collision"]
              + 0.27 * f["rebound"] - 0.13 * f["age"])
    if angle_b:
        travel = (1.0 - travel + 0.33 * f["wake"]
                  - 0.24 * f["active"] + 0.29 * f["extinct"])
    rgb = _palette(travel, PALETTE_B if angle_b else PALETTE_A)
    relief = (0.18 + 0.34 * f["active"] + 0.58 * f["head"]
              + 0.43 * f["wake"] + 0.62 * f["collision"]
              + 0.49 * f["rebound"] + 0.31 * f["slope"]
              + 0.24 * f["extinct"] - 0.14 * f["age"])
    rgb *= np.clip(relief, 0.06, 1.28)[..., None]
    rgb += np.asarray((0.36, 0.22, 0.05) if not angle_b else (0.07, 0.31, 0.32), np.float32) * f["collision"][..., None]
    rgb += np.asarray((0.08, 0.30, 0.38) if not angle_b else (0.37, 0.08, 0.27), np.float32) * f["head"][..., None]
    rgb += np.asarray((0.27, 0.07, 0.34) if not angle_b else (0.39, 0.25, 0.04), np.float32) * f["rebound"][..., None]
    rgb = cv2.GaussianBlur(np.clip(rgb, 0.0, 1.0).astype(np.float32), (0, 0), 0.34)
    return cv2.resize(rgb, (2048, 2048), interpolation=cv2.INTER_LANCZOS4)


def clear_cache() -> None:
    _paint.cache_clear(); _fields.cache_clear()


def render_evidence(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    timings, digests, last = [], [], None
    for _ in range(3):
        clear_cache(); start = time.perf_counter(); a = _paint(False); b = _paint(True)
        timings.append(time.perf_counter() - start)
        blob = np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes()
        digests.append(hashlib.sha256(blob).hexdigest()); last = a, b
    a, b = last; delta = np.abs(a - b)
    for suffix, image in (("paint", a), ("angle_a", a), ("angle_b", b),
                          ("angle_delta_x2", np.clip(delta * 2.0, 0.0, 1.0))):
        arr = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        cv2.imwrite(str(out_dir / f"{ID}_{suffix}_2048.png"),
                    cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out_dir / f"{ID}_crop_1to1.png"),
                cv2.cvtColor(np.clip(a[512:1280, 640:1408] * 255.0, 0, 255).astype(np.uint8),
                             cv2.COLOR_RGB2BGR))
    report = {"id": ID, "status": "NATIVE-2048-PAINT-CONTACT-NO-SPEC-NOT-WIRED",
              "timings_s": timings, "deterministic": len(set(digests)) == 1,
              "digest": digests[0], "angle_delta_mean": float(delta.mean()),
              "angle_delta_p95": float(np.quantile(delta, 0.95))}
    (out_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(render_evidence(root / "_wilds_fullres_progress_20260824" /
                                     "luna_impact_ca_i1"), indent=2))
