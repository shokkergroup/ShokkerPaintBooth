# -*- coding: utf-8 -*-
"""Frozen native-2048 Leafvine Drape I2 rejection (never wired).

SPB-105 / Wilds attempt 65 / 2026-08-25. Owner verdict controlling this edit:
native 2048, fine 8-32 px detail, many causal mark families, strong Fractured
travel, no repeated recolor laziness, and no random noise as uniqueness proof.

I1's sparse vertical rails, trellis and tiny repeated glyphs are frozen. I2 is
an explicit deterministic vector assembly: hundreds of overlapping ovate,
lanceolate, split and serrated leaves form the area-carrying canopy. Leaf veins,
short graft bridges, collars, pods, tendril curls and thorn tips remain attached
to the same growth chronology. Long stems are subordinate and mostly occluded.
No RNG, noise, FBM, scalar texture field, stamp image, or shared composer.

Native verdict: the four coded leaf types collapse into repeated bead/gem
glyphs on long looping rails over large empty ground, repeating I1's visible
failure in a brighter form. A/B mean is only 0.028700. No parameter, density,
palette, spec or runtime repair is authorized; see the colocated REJECTION.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

import cv2
import numpy as np


ID = "fbl_leafvine_drape"
WORK = 512


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]
    topology: str


def _f(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def _tier(field: np.ndarray, levels: Tuple[int, ...]) -> np.ndarray:
    idx = np.clip(np.floor(_f(field) * len(levels)), 0, len(levels) - 1)
    return np.asarray(levels, np.uint8)[idx.astype(np.int32)]


def _palette(index: int, bank: str) -> Tuple[int, int, int]:
    a = (
        (20, 84, 54), (27, 129, 70), (49, 174, 79), (107, 202, 76),
        (187, 207, 63), (235, 175, 52), (242, 111, 62),
    )
    b = (
        (60, 29, 97), (91, 34, 139), (132, 41, 166), (177, 48, 154),
        (214, 61, 120), (231, 82, 82), (87, 72, 177),
    )
    table = a if bank == "A" else b
    return table[index % len(table)]


def _leaf_points(cx: float, cy: float, angle: float, length: float,
                 width: float, kind: int) -> np.ndarray:
    tangent = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
    normal = np.asarray((-np.sin(angle), np.cos(angle)), np.float32)
    points = []
    samples = 7 if kind == 3 else 5
    for side in (1.0, -1.0):
        seq = range(samples + 1) if side > 0 else range(samples, -1, -1)
        for j in seq:
            t = j / samples
            axis = (t - 0.47) * length
            if kind == 0:       # ovate
                profile = np.sin(np.pi * t) ** 0.72
            elif kind == 1:     # lanceolate
                profile = np.sin(np.pi * t) ** 1.35
            elif kind == 2:     # split/lobed
                profile = np.sin(np.pi * t) ** 0.82 * (0.78 + 0.26 * np.cos(4 * np.pi * t))
            else:               # serrated
                profile = np.sin(np.pi * t) ** 0.72 * (0.82 + 0.18 * (-1 if j % 2 else 1))
            # Heart-like base notch only on some ovate leaves.
            if kind == 0 and t < 0.22:
                profile *= 0.72 + 1.2 * t
            p = np.asarray((cx, cy), np.float32) + tangent * axis + normal * side * width * profile
            points.append(p)
    return np.rint(points).astype(np.int32)


def _draw_leaf(mask: np.ndarray, color: np.ndarray, cx: float, cy: float,
               angle: float, length: float, width: float, kind: int,
               rgb: Tuple[int, int, int]) -> np.ndarray:
    points = _leaf_points(cx, cy, angle, length, width, kind)
    cv2.fillPoly(mask, [points], 255, cv2.LINE_AA)
    cv2.fillPoly(color, [points], rgb, cv2.LINE_AA)
    return points


def _build() -> Grammar:
    masks_u8 = {name: np.zeros((WORK, WORK), np.uint8) for name in (
        "stems", "ovate", "lanceolate", "split", "serrated", "veins",
        "collars", "pods", "tendrils", "thorns", "bridges",
    )}
    color = np.zeros((WORK, WORK, 3), np.uint8)
    color[:] = (5, 12, 11)

    # Sixteen unequal off-canvas growth histories. Golden-ratio phase offsets
    # keep them deterministic and aperiodic; only short inter-node segments are
    # drawn, and dense foliage later occludes most stem rail length.
    phi = 0.61803398875
    nodes_by_stem = []
    for stem in range(16):
        side = stem % 4
        phase = 2.0 * np.pi * ((stem * phi) % 1.0)
        node_count = 38 + (stem * 7) % 9
        nodes = []
        for j in range(node_count):
            t = (j + 0.35) / node_count
            if side == 0:
                cx = -12 + t * 548
                cy = 18 + ((stem * 31) % 470) + 31 * np.sin(2.1 * np.pi * t + phase)
            elif side == 1:
                cx = 524 - t * 548
                cy = 12 + ((stem * 29) % 476) + 27 * np.sin(2.5 * np.pi * t + phase)
            elif side == 2:
                cx = 17 + ((stem * 37) % 474) + 29 * np.sin(2.3 * np.pi * t + phase)
                cy = -12 + t * 548
            else:
                cx = 11 + ((stem * 41) % 478) + 25 * np.sin(2.7 * np.pi * t + phase)
                cy = 524 - t * 548
            nodes.append((cx, cy))
        nodes_by_stem.append(nodes)
        for j in range(len(nodes) - 1):
            p0 = tuple(np.rint(nodes[j]).astype(int))
            p1 = tuple(np.rint(nodes[j + 1]).astype(int))
            shade = 66 + (stem * 13 + j * 5) % 72
            cv2.line(masks_u8["stems"], p0, p1, 255, 2, cv2.LINE_AA)
            cv2.line(color, p0, p1, (30, shade, 48), 2, cv2.LINE_AA)

    # Every node grows one primary leaf and selected nodes grow a different
    # secondary consequence. Shape, handedness and size all follow chronology.
    for stem, nodes in enumerate(nodes_by_stem):
        for j, (cx, cy) in enumerate(nodes):
            if not (-10 <= cx < WORK + 10 and -10 <= cy < WORK + 10):
                continue
            if j + 1 < len(nodes):
                dx, dy = nodes[j + 1][0] - cx, nodes[j + 1][1] - cy
            else:
                dx, dy = cx - nodes[j - 1][0], cy - nodes[j - 1][1]
            tangent = np.arctan2(dy, dx)
            handed = -1.0 if (stem + j) % 2 else 1.0
            angle = tangent + handed * (0.72 + 0.20 * np.sin(0.41 * j + stem))
            length = 4.6 + 3.2 * (0.5 + 0.5 * np.sin(j * 2.399963 + stem * 0.73))
            width = 1.8 + 1.9 * (0.5 + 0.5 * np.sin(j * 1.73 - stem * 0.51))
            kind = (j + 2 * stem + (j // 7)) % 4
            bank = "A" if (stem + j + kind) % 2 == 0 else "B"
            name = ("ovate", "lanceolate", "split", "serrated")[kind]
            rgb = _palette(stem * 3 + j + kind, bank)
            points = _draw_leaf(masks_u8[name], color, cx, cy, angle,
                                length, width, kind, rgb)

            # Midrib/vein is a distinct short primitive confined to leaf mass.
            ta = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
            p0 = tuple(np.rint(np.asarray((cx, cy)) - ta * length * 0.34).astype(int))
            p1 = tuple(np.rint(np.asarray((cx, cy)) + ta * length * 0.42).astype(int))
            cv2.line(masks_u8["veins"], p0, p1, 255, 1, cv2.LINE_AA)
            vein_rgb = (191, 220, 116) if bank == "A" else (225, 128, 205)
            cv2.line(color, p0, p1, vein_rgb, 1, cv2.LINE_AA)

            # Collars are short transverse joints, not rings or free dots.
            if j % 6 == (stem % 3):
                nn = np.asarray((-np.sin(tangent), np.cos(tangent)), np.float32)
                q0 = tuple(np.rint(np.asarray((cx, cy)) - nn * 2.3).astype(int))
                q1 = tuple(np.rint(np.asarray((cx, cy)) + nn * 2.3).astype(int))
                cv2.line(masks_u8["collars"], q0, q1, 255, 2, cv2.LINE_AA)
                cv2.line(color, q0, q1, (237, 177, 72), 2, cv2.LINE_AA)

            # Two-lobed pods occur at unequal chronological intervals.
            if (j * 5 + stem * 3) % 17 == 2:
                center = np.asarray((cx, cy)) + ta * 3.1 - np.asarray((-ta[1], ta[0])) * handed * 2.1
                axes = (3 + (j % 2), 2)
                c = tuple(np.rint(center).astype(int))
                cv2.ellipse(masks_u8["pods"], c, axes, np.degrees(angle), 0, 360, 255, -1, cv2.LINE_AA)
                cv2.ellipse(color, c, axes, np.degrees(angle), 0, 360,
                            (224, 103, 73) if bank == "A" else (107, 82, 214), -1, cv2.LINE_AA)
                cv2.line(color, c, tuple(np.rint(center + ta * 3.0).astype(int)), (245, 190, 97), 1, cv2.LINE_AA)

            # Tendrils are compact 8-28 native-px curls, attached at nodes.
            if (j * 7 + stem) % 19 == 4:
                pts = []
                for k in range(9):
                    u = k / 8.0
                    radius = 0.8 + 2.5 * u
                    ang = tangent + handed * (1.4 + 3.7 * u)
                    pts.append((int(round(cx + radius * np.cos(ang))),
                                int(round(cy + radius * np.sin(ang)))))
                arr = np.asarray(pts, np.int32)
                cv2.polylines(masks_u8["tendrils"], [arr], False, 255, 1, cv2.LINE_AA)
                cv2.polylines(color, [arr], False, (93, 220, 202), 1, cv2.LINE_AA)

            if (j * 11 + 2 * stem) % 23 == 5:
                nn = np.asarray((-np.sin(tangent), np.cos(tangent)), np.float32) * handed
                q0 = tuple(np.rint((cx, cy)).astype(int))
                q1 = tuple(np.rint(np.asarray((cx, cy)) + nn * 3.1 + ta * 1.1).astype(int))
                cv2.line(masks_u8["thorns"], q0, q1, 255, 1, cv2.LINE_AA)
                cv2.line(color, q0, q1, (244, 153, 73), 1, cv2.LINE_AA)

    # Short graft bridges only connect genuinely nearby chronologies. Their
    # local cap prevents the old horizontal trellis carrier from reappearing.
    for stem in range(16):
        a = nodes_by_stem[stem]
        other = [p for other_stem, row in enumerate(nodes_by_stem)
                 if other_stem != stem for p in row]
        for j in range(3 + stem % 5, len(a), 13):
            pa = np.asarray(a[j], np.float32)
            candidates = sorted(other, key=lambda p: float(np.linalg.norm(np.asarray(p) - pa)))
            for candidate in candidates[:12]:
                pb = np.asarray(candidate, np.float32)
                distance = float(np.linalg.norm(pb - pa))
                if 3.5 <= distance <= 10.0:
                    p0, p1 = tuple(np.rint(pa).astype(int)), tuple(np.rint(pb).astype(int))
                    cv2.line(masks_u8["bridges"], p0, p1, 255, 2, cv2.LINE_AA)
                    cv2.line(color, p0, p1, (127, 215, 116), 2, cv2.LINE_AA)
                    break

    # Convert explicit masks and add subtle edge relief without inventing grain.
    masks = {name: arr.astype(np.float32) / 255.0 for name, arr in masks_u8.items()}
    leaf_union = np.maximum.reduce(tuple(masks[name] for name in ("ovate", "lanceolate", "split", "serrated")))
    gx = cv2.Sobel(leaf_union, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(leaf_union, cv2.CV_32F, 0, 1, ksize=3)
    edge = _f(np.hypot(gx, gy) * 0.42)
    paint = color.astype(np.float32) / 255.0
    paint += edge[..., None] * np.asarray((0.18, 0.24, 0.13), np.float32)
    paint = _f(paint)

    neutral = _f(0.08 + 0.44 * leaf_union + 0.24 * masks["veins"]
                 + 0.30 * masks["pods"] + 0.22 * masks["collars"]
                 + 0.23 * masks["tendrils"] + 0.21 * masks["thorns"]
                 + 0.25 * masks["bridges"] + 0.16 * edge)
    hue_null = np.repeat(neutral[..., None], 3, axis=2)

    a_leaf = np.maximum(masks["ovate"], masks["serrated"])
    b_leaf = np.maximum(masks["lanceolate"], masks["split"])
    metal_field = _f(0.03 + 0.69 * a_leaf + 0.61 * masks["pods"]
                     + 0.47 * masks["collars"] + 0.31 * edge - 0.22 * masks["stems"])
    rough_field = _f(0.10 + 0.59 * b_leaf + 0.54 * masks["thorns"]
                     + 0.41 * masks["stems"] - 0.34 * masks["veins"] - 0.25 * masks["pods"])
    coat_field = _f(0.04 + 0.65 * masks["veins"] + 0.57 * masks["tendrils"]
                    + 0.49 * masks["bridges"] + 0.35 * edge - 0.28 * masks["stems"])
    metal = _tier(metal_field, (7, 30, 57, 90, 126, 166, 209, 249))
    rough = _tier(rough_field, (14, 41, 70, 104, 140, 178, 217, 250))
    coat = _tier(coat_field, (6, 28, 55, 88, 125, 166, 210, 252))

    marks = (
        ("ovate_leaves", masks["ovate"], "A"),
        ("lanceolate_leaves", masks["lanceolate"], "B"),
        ("split_leaves", masks["split"], "B"),
        ("serrated_leaves", masks["serrated"], "A"),
        ("leaf_veins", masks["veins"], "A"),
        ("short_stems", masks["stems"], "N"),
        ("growth_collars", masks["collars"], "A"),
        ("two_lobed_pods", masks["pods"], "B"),
        ("tendril_curls", masks["tendrils"], "B"),
        ("thorn_tips", masks["thorns"], "A"),
        ("graft_bridges", masks["bridges"], "B"),
    )
    absent = [name for name, mask, _bank in marks if float(mask.std()) < 0.003]
    if absent:
        raise ValueError(f"Leafvine I2 has absent causal marks: {absent}")
    return Grammar(
        marks=marks,
        paint=paint,
        hue_null=hue_null,
        explicit_spec=(metal, rough, coat),
        topology="dense overlapping explicit leaf canopy on sixteen subordinate growth histories",
    )


@lru_cache(maxsize=1)
def _cached() -> Tuple[np.ndarray, np.ndarray]:
    grammar = _build()
    return grammar.paint, np.stack(grammar.explicit_spec, axis=2).astype(np.uint8)


def _authored(fid: str = ID) -> Tuple[np.ndarray, np.ndarray]:
    if fid != ID:
        raise KeyError(fid)
    paint, spec = _cached()
    return paint.copy(), spec.copy()


def clear_cache() -> None:
    _cached.cache_clear()


def debug_grammar() -> Grammar:
    return _build()


def owner_unions(grammar: Grammar) -> Dict[str, np.ndarray]:
    out = {key: np.zeros((WORK, WORK), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        out[bank] = np.maximum(out[bank], mask)
    return out


def debug_angle_pair(fid: str = ID) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if fid != ID:
        raise KeyError(fid)
    grammar = _build()
    owners = owner_unions(grammar)
    a = grammar.paint * (0.37 + 0.61 * owners["A"])[..., None]
    a += owners["A"][..., None] * np.asarray((0.08, 0.48, 0.38), np.float32)
    a += owners["B"][..., None] * np.asarray((0.19, 0.03, 0.24), np.float32)
    b = grammar.paint * (0.36 + 0.62 * owners["B"])[..., None]
    b += owners["B"][..., None] * np.asarray((0.57, 0.08, 0.41), np.float32)
    b += owners["A"][..., None] * np.asarray((0.30, 0.27, 0.04), np.float32)
    a, b = _f(a), _f(b)
    return a, b, np.abs(a - b).astype(np.float32)


BUILDERS = {ID: _build}
