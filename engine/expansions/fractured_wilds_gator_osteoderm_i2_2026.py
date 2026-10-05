# -*- coding: utf-8 -*-
"""Gator Hide I2 — dense connected osteoderm tissue at 2048 output.

A non-row-ordered field of irregular micro osteoderms fills the entire surface.
Ligament seams, raised facets, pressure pits, and worn keels are measured from
the same nearest-osteoderm ownership field, so no detached scute or decorative
noise layer is used.  This replaces the rejected sparse Scute I1.

SPB-WILDS rebuild / 2026-08-25.  Owner doctrine: fine 8–32px features,
multi-mark causal material, true Fractured A/B colour ownership, no shared
Wilds compositor or palette-only substitute.  Candidate pending gates/review.
"""
from __future__ import annotations

from functools import lru_cache
import cv2
import numpy as np


ID, WORK = "fc_gator_hide", 512
A = np.asarray(((5, 9, 9), (18, 28, 23), (44, 55, 37), (78, 85, 48),
                (124, 119, 56), (172, 132, 67), (205, 102, 83),
                (173, 52, 101), (98, 48, 111), (37, 98, 113)), np.float32)
B = np.asarray(((7, 6, 14), (24, 16, 34), (49, 27, 60), (82, 43, 91),
                (124, 68, 112), (171, 105, 122), (214, 155, 126),
                (201, 204, 134), (117, 195, 153), (43, 141, 160)), np.float32)


def _hash(index: np.ndarray, a: float, b: float) -> np.ndarray:
    return np.mod(np.sin(index*a+b)*43758.5453, 1.0).astype(np.float32)


def _palette(phase: np.ndarray, bank: np.ndarray) -> np.ndarray:
    value = np.mod(phase, 1.0) * len(bank)
    lo = np.floor(value).astype(np.int16)
    f = (value - lo)[..., None]
    return bank[lo] * (1.0 - f) + bank[(lo + 1) % len(bank)] * f


@lru_cache(maxsize=1)
def _marks() -> dict[str, np.ndarray]:
    """Build one connected dermal ownership field and its causal reactions."""
    count = 5100
    index = np.arange(count, dtype=np.float32)
    seed = np.full((WORK, WORK), 255, np.uint8)
    xs = (_hash(index, 17.131, 3.17)*(WORK-2)+1).astype(np.int32)
    ys = (_hash(index, 71.923, 9.81)*(WORK-2)+1).astype(np.int32)
    seed[ys, xs] = 0
    distance, labels = cv2.distanceTransformWithLabels(
        seed, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    labels = labels.astype(np.int32)
    boundary = ((labels != np.roll(labels, 1, 0)) | (labels != np.roll(labels, -1, 0)) |
                (labels != np.roll(labels, 1, 1)) | (labels != np.roll(labels, -1, 1))).astype(np.uint8)
    ligament = cv2.GaussianBlur(cv2.dilate(boundary, np.ones((2, 2), np.uint8)),
                                 (0, 0), .65)
    facet = np.clip(cv2.distanceTransform(1-boundary, cv2.DIST_L2, 5)/4.2, 0, 1)
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    key = _hash(labels.astype(np.float32), 12.9898, .0)
    # A pressure pit occurs inside—not on top of—the owning osteoderm.
    pit = np.clip(1-np.abs(distance-(1.1+1.3*key))/1.15, 0, 1)*facet
    keel = np.clip(.5+.5*np.sin((x*.81+y*.47)+key*6.2831853), 0, 1)*facet
    healed = np.clip(ligament*(.42+.58*(.5+.5*np.sin(x*.37-y*.61+key*3.1))), 0, 1)
    return {"osteoderm_facet": facet.astype(np.float32),
            "interstitial_ligament": np.clip(ligament, 0, 1).astype(np.float32),
            "pressure_pit": pit.astype(np.float32),
            "raised_keel": keel.astype(np.float32),
            "healed_ligament": healed.astype(np.float32),
            "cell_key": key.astype(np.float32)}


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    marks = _marks()
    facet, ligament = marks["osteoderm_facet"], marks["interstitial_ligament"]
    pit, keel, healed = marks["pressure_pit"], marks["raised_keel"], marks["healed_ligament"]
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    chemistry = np.mod(.14+.22*np.sin((x+1.6*y)/101.0)
                       +.19*np.sin((2*x-y)/67.0)+.10*marks["cell_key"], 1.0)
    if angle_b:
        phase = chemistry+.34+.26*ligament+.22*healed-.18*keel+.14*pit
        light = .13+.43*facet+.25*ligament+.18*healed-.17*pit
        bank = B
    else:
        phase = chemistry+.09+.28*keel+.19*facet-.17*ligament+.10*pit
        light = .13+.45*facet+.21*keel+.17*healed-.20*pit
        bank = A
    image = _palette(phase, bank)*np.clip(light[..., None], .04, 1.0)
    image *= 1-.44*pit[..., None]
    image += ligament[..., None]*np.asarray((30, 85, 92) if angle_b else (26, 63, 58), np.float32)
    image += keel[..., None]*np.asarray((87, 57, 112) if angle_b else (45, 63, 29), np.float32)
    image += healed[..., None]*np.asarray((44, 141, 151) if angle_b else (94, 72, 39), np.float32)
    return np.clip(image, 0, 255).astype(np.uint8), marks


def _tier(value: np.ndarray, levels: tuple[int, ...]) -> np.ndarray:
    index = np.clip(np.floor(np.clip(value, 0, .999999)*8), 0, 7).astype(np.int16)
    return np.asarray(levels, np.uint8)[index]


def _spec(marks: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    facet, ligament = marks["osteoderm_facet"], marks["interstitial_ligament"]
    pit, keel, healed = marks["pressure_pit"], marks["raised_keel"], marks["healed_ligament"]
    # M = raised mineral keel; R = porous pit/ligament weathering;
    # Cc = broad facet and healed-wet ligament.  These remain independent.
    metal = _tier(np.clip(.08+.48*keel+.29*facet+.23*healed-.33*pit, 0, .999), (4, 37, 72, 107, 142, 179, 217, 252))
    rough = _tier(np.clip(.10+.53*pit+.38*ligament+.19*(1-facet)-.19*healed, 0, .999), (7, 43, 78, 113, 149, 185, 220, 250))
    coat = _tier(np.clip(.08+.49*facet+.29*healed+.24*keel-.22*pit, 0, .999), (3, 39, 73, 108, 143, 180, 217, 253))
    # Local wear extremes keep every material measurement spanning the full
    # physical range without copying another channel's topology.
    metal[pit > .42] = 4; metal[keel > .76] = 252
    rough[healed > .62] = 7; rough[(pit > .43) | (ligament > .66)] = 250
    coat[pit > .46] = 3; coat[(healed > .68) | (keel > .82)] = 253
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
        raise ValueError(f"weak Gator Hide material: {std} {ranges}")
    if float(delta.mean()) < .05 or float(np.percentile(delta, 95)) < .14:
        raise ValueError("Gator Hide lacks visible Fractured ownership flip")
    return {"id": ID, "shape": a.shape, "spec_std": std, "spec_ranges": ranges,
            "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.percentile(delta, 95))}
