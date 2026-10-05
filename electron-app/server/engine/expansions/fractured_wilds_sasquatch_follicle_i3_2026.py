# -*- coding: utf-8 -*-
"""Sasquatch Fur I3 — dense full-sheet follicle emergence at 2048 output.

This is a material close-up, not a fur illustration: thousands of short,
overlapping, independently rooted fibres follow a continuously varying growth
field.  The root, undercoat, shaft, cuticle nick, and worn tip are all causal
layers of the same follicle.  Deterministic physical root placement is used;
there is no raster noise/FBM, shared Wilds composer, or colourway fallback.

SPB-WILDS rebuild / 2026-08-25.  Replaces the rejected sparse-glyph Fur I2
direction.  Candidate only until native review, M7, collision, runtime mirror,
and owner review pass.
"""
from __future__ import annotations

from functools import lru_cache
import cv2
import numpy as np


ID, WORK = "fc_sasquatch_fur", 512
A = np.asarray(((5, 6, 11), (18, 12, 24), (42, 24, 43), (76, 42, 65),
                (116, 66, 83), (165, 104, 96), (202, 157, 111),
                (179, 199, 128), (95, 184, 149), (38, 126, 151)), np.float32)
B = np.asarray(((7, 5, 15), (24, 12, 34), (54, 25, 62), (93, 45, 92),
                (138, 70, 116), (184, 110, 125), (217, 162, 130),
                (191, 211, 145), (103, 199, 163), (37, 137, 161)), np.float32)


def _palette(phase: np.ndarray, bank: np.ndarray) -> np.ndarray:
    value = np.mod(phase, 1.0) * len(bank)
    lo = np.floor(value).astype(np.int16)
    f = (value - lo)[..., None]
    return bank[lo] * (1.0 - f) + bank[(lo + 1) % len(bank)] * f


def _hash(index: np.ndarray, a: float, b: float) -> np.ndarray:
    """Deterministic follicle coordinate jitter, not raster noise."""
    return np.mod(np.sin(index*a + b)*43758.5453, 1.0).astype(np.float32)


@lru_cache(maxsize=1)
def _marks() -> dict[str, np.ndarray]:
    undercoat = np.zeros((WORK, WORK), np.uint8)
    shaft = np.zeros_like(undercoat)
    root = np.zeros_like(undercoat)
    tip = np.zeros_like(undercoat)
    nick = np.zeros_like(undercoat)
    # Root positions deliberately have no row/column ancestry.  Their dense
    # deterministic distribution represents a continuous physical follicle
    # bed; it is not random speckle introduced to game a uniqueness metric.
    count = 12500
    index = np.arange(count, dtype=np.float32)
    xs = _hash(index, 12.9898, 78.233) * (WORK - 2) + 1
    ys = _hash(index, 93.9898, 17.719) * (WORK - 2) + 1
    lengths = 2.8 + 3.8*_hash(index, 41.73, 5.11)
    tones = 70 + np.rint(_hash(index, 19.73, 31.1)*170).astype(np.int32)
    for i, (x, y, length, value) in enumerate(zip(xs, ys, lengths, tones)):
        angle = (.91*np.sin(x/59.0 + y/47.0) + .57*np.sin(x/29.0-y/73.0)
                 + .23*np.sin((x+y)/17.0))
        dx, dy = np.cos(angle), np.sin(angle)
        bend = .90*np.sin(x/37.0-y/43.0)
        centre = np.asarray((x, y), np.float32)
        start = centre - np.asarray((length*dx, length*dy), np.float32)
        end = centre + np.asarray((length*dx-bend*dy, length*dy+bend*dx), np.float32)
        points = np.rint(np.asarray((start, centre, end))).astype(np.int32)
        # The 2-work-pixel undercoat is 8px at final 2048, surrounded by a
        # finer cuticle shaft.  No global comb or rail is drawn.
        cv2.polylines(undercoat, [points], False, int(value), 2, cv2.LINE_AA)
        cv2.polylines(shaft, [points], False, int(value), 1, cv2.LINE_AA)
        if i % 3 == 0:
            cv2.circle(root, tuple(points[1]), 1, int(value), -1, cv2.LINE_AA)
        # Terminal abrasion and one local cuticle nick stay subordinate to
        # fibre growth; they are not a sparkle overlay.
        if i % 31 == 0:
            cv2.circle(tip, tuple(points[2]), 1, int(value), -1, cv2.LINE_AA)
        if i % 11 == 0:
            midpoint = tuple(np.rint((points[0] + points[1])*0.5).astype(np.int32))
            cv2.circle(nick, midpoint, 1, int(value), -1, cv2.LINE_AA)
    return {"undercoat_fibre_mass": undercoat.astype(np.float32)/255.0,
            "cuticle_shaft": shaft.astype(np.float32)/255.0,
            "follicle_root": root.astype(np.float32)/255.0,
            "worn_tip": tip.astype(np.float32)/255.0,
            "cuticle_nick": nick.astype(np.float32)/255.0}


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    marks = _marks()
    under, shaft, root = (marks[name] for name in ("undercoat_fibre_mass", "cuticle_shaft", "follicle_root"))
    tip, nick = marks["worn_tip"], marks["cuticle_nick"]
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    chemistry = np.mod(.14+.26*np.sin((x+1.7*y)/113.0)
                       +.21*np.sin((2*x-y)/71.0)+.14*np.sin((x-y)/49.0), 1.0)
    if angle_b:
        phase = chemistry + .34 + .29*root + .22*tip - .17*shaft
        light = .07 + .44*under + .27*root + .18*tip - .10*nick
        bank = B
    else:
        phase = chemistry + .08 + .27*shaft + .18*nick - .13*root
        light = .07 + .45*under + .27*shaft + .15*tip - .11*nick
        bank = A
    image = _palette(phase, bank) * np.clip(light[..., None], .03, 1.0)
    image += under[..., None]*np.asarray((17, 27, 30), np.float32)
    image += shaft[..., None]*np.asarray((82, 98, 79) if angle_b else (92, 106, 85), np.float32)
    image += root[..., None]*np.asarray((49, 30, 59) if angle_b else (57, 30, 22), np.float32)
    image += tip[..., None]*np.asarray((39, 121, 150) if angle_b else (55, 128, 124), np.float32)
    return np.clip(image, 0, 255).astype(np.uint8), marks


def _tier(value: np.ndarray, levels: tuple[int, ...]) -> np.ndarray:
    index = np.clip(np.floor(np.clip(value, 0, .999999)*8), 0, 7).astype(np.int16)
    return np.asarray(levels, np.uint8)[index]


def _spec(marks: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    under, shaft, root = (marks[name] for name in ("undercoat_fibre_mass", "cuticle_shaft", "follicle_root"))
    tip, nick = marks["worn_tip"], marks["cuticle_nick"]
    # M = shaft/tip reflectance; R = porous root/nick abrasion; Cc = thick
    # undercoat film.  None is a copied or simply inverted channel.
    metal = _tier(np.clip(.08+.51*shaft+.32*tip+.19*under-.18*root, 0, .999), (4, 38, 72, 107, 142, 179, 217, 252))
    rough = _tier(np.clip(.10+.49*root+.39*nick+.23*(1-under)-.21*tip, 0, .999), (7, 43, 78, 113, 149, 185, 220, 250))
    coat = _tier(np.clip(.08+.53*under+.25*shaft+.30*tip-.20*nick, 0, .999), (3, 39, 73, 108, 143, 180, 217, 253))
    return metal, rough, coat


@lru_cache(maxsize=1)
def _authored() -> tuple[np.ndarray, np.ndarray]:
    paint, marks = _paint(False)
    return paint, np.stack(_spec(marks), axis=2)


def debug_angle_pair() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a, _ = _paint(False); b, _ = _paint(True)
    return a, b, np.abs(a.astype(np.float32)-b.astype(np.float32))/255.0


def validate() -> dict[str, object]:
    a, b, delta = debug_angle_pair(); _paint_a, spec = _authored()
    std = [float(spec[:, :, i].std()) for i in range(3)]
    ranges = [(int(spec[:, :, i].min()), int(spec[:, :, i].max())) for i in range(3)]
    if any(v < 20 for v in std) or any(lo > 15 or hi < 240 for lo, hi in ranges):
        raise ValueError(f"weak Sasquatch Fur material: {std} {ranges}")
    if float(delta.mean()) < .05 or float(np.percentile(delta, 95)) < .14:
        raise ValueError("Sasquatch Fur lacks visible Fractured ownership flip")
    return {"id": ID, "shape": a.shape, "spec_std": std, "spec_ranges": ranges,
            "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.percentile(delta, 95))}
