# -*- coding: utf-8 -*-
"""Snake Skin I2 — dense, overlapping iridescent scale tissue at native 2048.

The structure is an anatomically specific field of small overlapping scales,
not a generic hex/paver.  Every scale belongs to a changing local direction
field and carries five attached material events: body, lifted overlap rim,
central keel, shed hinge, and rare worn glint.  Deterministic analytic drift
replaces RNG/noise/FBM; palette changes do not define the finish.

SPB-WILDS rebuild / 2026-08-25.  Owner doctrine: 8–32px native detail,
multi-mark causal material, true A/B Fractured flip, never a recolored shared
composer.  M7 / visual promotion evidence is recorded outside this source.
"""
from __future__ import annotations

from functools import lru_cache
import cv2
import numpy as np


ID, WORK = "fc_snakeskin", 1024
A = np.asarray(((3, 8, 16), (10, 22, 37), (24, 42, 69), (53, 60, 105),
                (96, 78, 133), (146, 95, 143), (199, 124, 129),
                (226, 175, 135), (183, 215, 142), (89, 187, 153),
                (27, 119, 144)), np.float32)
B = np.asarray(((7, 5, 15), (27, 12, 39), (58, 22, 75), (99, 37, 105),
                (145, 61, 121), (194, 99, 128), (224, 160, 132),
                (205, 214, 142), (129, 211, 158), (58, 157, 166),
                (24, 81, 139)), np.float32)


def _palette(phase: np.ndarray, bank: np.ndarray) -> np.ndarray:
    value = np.mod(phase, 1.0) * len(bank)
    lo = np.floor(value).astype(np.int16)
    f = (value - lo)[..., None]
    return bank[lo] * (1.0 - f) + bank[(lo + 1) % len(bank)] * f


@lru_cache(maxsize=1)
def _marks() -> dict[str, np.ndarray]:
    """Render a non-uniform, fully covered scale epidermis at WORK resolution."""
    body = np.zeros((WORK, WORK), np.uint8)
    rim = np.zeros_like(body)
    keel = np.zeros_like(body)
    hinge = np.zeros_like(body)
    glint = np.zeros_like(body)
    shed = np.zeros_like(body)
    # At 1024 these 4–7px primitives become 8–14px in the authored 2048
    # canvas.  Row offset is just the overlap relation; sin-derived placement
    # and direction prevent a wallpaper lattice from owning the surface.
    for row, y in enumerate(range(-6, WORK + 12, 8)):
        for col, x in enumerate(range(-7, WORK + 13, 9)):
            cx = int(round(x + (4.5 if row & 1 else 0.0)
                           + 2.15*np.sin(row*.73 + col*1.41)
                           + .90*np.sin(row*1.91 - col*.37)))
            cy = int(round(y + 1.85*np.sin(col*.57 - row*1.17)
                           + .65*np.sin(col*1.71 + row*.23)))
            angle = (24*np.sin(cx/91.0 + cy/137.0)
                     + 14*np.sin(cx/47.0 - cy/79.0)
                     + 8*np.sin((cx + cy)/181.0))
            value = 92 + (row*13 + col*17 + row*col*3) % 158
            axes = (4 + ((row + 2*col) % 2), 6 + ((2*row + col) % 2))
            cv2.ellipse(body, (cx, cy), axes, angle, 0, 360, value, -1, cv2.LINE_AA)
            # The open upper rim is the lifted, overlapping edge—not a
            # complete outline—so scales do not read like stamped coins.
            cv2.ellipse(rim, (cx, cy), axes, angle, 188, 348, value, 1, cv2.LINE_AA)
            r = np.deg2rad(angle)
            p1 = (int(round(cx + np.sin(r)*2)), int(round(cy - np.cos(r)*2)))
            p2 = (int(round(cx - np.sin(r)*3)), int(round(cy + np.cos(r)*3)))
            cv2.line(keel, p1, p2, value, 1, cv2.LINE_AA)
            cv2.ellipse(hinge, (cx, cy), (2, 1), angle, 0, 180, value, 1, cv2.LINE_AA)
            # Worn glints are sparse deterministic reactions of the same
            # growing tissue, not random glitter added to differentiate it.
            if (row*3 + col*5 + row*col) % 13 == 0:
                cv2.circle(glint, (cx, cy), 1, 226, -1, cv2.LINE_AA)
            if (row*7 + col*11) % 19 == 0:
                cv2.ellipse(shed, (cx, cy), (2, 1), angle, 8, 92, value, 1, cv2.LINE_AA)
    return {"scale_body": body.astype(np.float32)/255.0,
            "lifted_overlap_rim": rim.astype(np.float32)/255.0,
            "central_scale_keel": keel.astype(np.float32)/255.0,
            "shed_hinge": hinge.astype(np.float32)/255.0,
            "worn_glint": glint.astype(np.float32)/255.0,
            "shed_crescent": shed.astype(np.float32)/255.0}


def _paint(angle_b: bool) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    marks = _marks()
    body, rim, keel, hinge = (marks[name] for name in ("scale_body", "lifted_overlap_rim", "central_scale_keel", "shed_hinge"))
    glint, shed = marks["worn_glint"], marks["shed_crescent"]
    y, x = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    # Chemistry varies across the continuous sheet independently of individual
    # scales; that is what makes this a living shedded skin rather than a set
    # of recolored icons.
    chemistry = np.mod(.17 + .23*np.sin((x + 1.7*y)/117.0)
                       + .19*np.sin((2*x-y)/71.0) + .11*np.sin((x-y)/43.0), 1.0)
    micro = .5 + .5*np.sin((1.33*x-.87*y)/5.4 + chemistry*4.7)
    if angle_b:
        phase = chemistry + .34 + .25*rim + .17*hinge - .12*keel + .10*micro
        light = .10 + .46*body + .24*rim + .17*glint - .15*hinge
        bank = B
    else:
        phase = chemistry + .09 + .28*keel + .18*body - .14*hinge + .08*micro
        light = .10 + .48*body + .22*keel + .15*glint - .18*hinge
        bank = A
    image = _palette(phase, bank) * np.clip(light[..., None], .04, 1.0)
    image *= 1.0 - .62*hinge[..., None]
    image += rim[..., None] * np.asarray((29, 76, 91) if angle_b else (67, 41, 27), np.float32)
    image += glint[..., None] * np.asarray((58, 192, 205) if angle_b else (125, 106, 71), np.float32)
    image += shed[..., None] * np.asarray((106, 41, 119) if angle_b else (75, 136, 94), np.float32)
    return np.clip(image, 0, 255).astype(np.uint8), marks


def _tier(value: np.ndarray, levels: tuple[int, ...]) -> np.ndarray:
    index = np.clip(np.floor(np.clip(value, 0, .999999)*8), 0, 7).astype(np.int16)
    return np.asarray(levels, np.uint8)[index]


def _spec(marks: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    body, rim, keel, hinge = (marks[name] for name in ("scale_body", "lifted_overlap_rim", "central_scale_keel", "shed_hinge"))
    glint, shed = marks["worn_glint"], marks["shed_crescent"]
    # Independent physical measurements: metal=keel/rim reflectance,
    # roughness=hinge/shed abrasion, clearcoat=body overlap and glints.
    metal = _tier(np.clip(.09+.45*keel+.34*rim+.30*glint+.15*body-.21*hinge, 0, .999), (4, 37, 72, 107, 143, 179, 218, 252))
    rough = _tier(np.clip(.10+.61*hinge+.31*shed+.22*(1-body)-.24*glint, 0, .999), (7, 43, 78, 114, 149, 185, 220, 250))
    coat = _tier(np.clip(.08+.46*body+.32*rim+.35*glint+.17*keel-.18*hinge, 0, .999), (3, 39, 74, 109, 144, 180, 217, 253))
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
        raise ValueError(f"weak Snake Skin material: {std} {ranges}")
    if float(delta.mean()) < .05 or float(np.percentile(delta, 95)) < .14:
        raise ValueError("Snake Skin lacks visible Fractured ownership flip")
    return {"id": ID, "shape": a.shape, "spec_std": std, "spec_ranges": ranges,
            "angle_delta_mean": float(delta.mean()), "angle_delta_p95": float(np.percentile(delta, 95))}
