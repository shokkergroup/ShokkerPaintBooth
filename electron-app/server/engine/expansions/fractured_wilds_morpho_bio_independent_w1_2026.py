# -*- coding: utf-8 -*-
"""Independent Morpho-biological Fractured candidate -- MB-I1.

This module is intentionally isolated from the production registry.  W14 was
rejected because twenty-five named finishes shared one periodic-line carrier.
MB-I1 rebuilds one finish only so a bad visual idea cannot spread across a
batch before paint, hue-null, semantic, M/R/Cc and A/B evidence is reviewed.

``fmo_morpho_blue`` uses the real Christmas-tree nanoridge idea behind Morpho
structural colour: overlapping micro-scales carry a ridge trunk, alternating
lamellar shelves, cross-ribs, perforation pores, root sockets, overlap lips,
missing-shelf defects and dislocation forks.  Placement is a deterministic
quasiperiodic wing-flow construction, not random noise, a generic scalar field,
or the rejected W14 periodic-line compositor.

SPB-WILDS MB-I1, tick 1, 2026-08-24.  Owner verdict addressed: "EXACT SAME
pattern just recolored or exact same spec maps".  Candidate only; metrics and
hashes cannot mark it owner accepted and no production wiring is performed.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np


S = 512
CALM_SPEC = np.asarray((4.0, 120.0, 16.0), np.float32)


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    paint: np.ndarray
    hue_null: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]


def _f(value):
    return np.clip(np.asarray(value, np.float32), 0.0, 1.0)


def _mask():
    return np.zeros((S, S), np.float32)


def _rgb(hex_value):
    value = hex_value.removeprefix("#")
    return np.asarray(tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)),
                      np.float32) / 255.0


def _blend(canvas, color, alpha):
    alpha = _f(alpha)[..., None]
    return canvas * (1.0 - alpha) + np.asarray(color, np.float32) * alpha


def _transform(center, angle, points):
    angle = np.deg2rad(float(angle))
    c, s = np.cos(angle), np.sin(angle)
    rotation = np.asarray(((c, -s), (s, c)), np.float32)
    return np.asarray(center, np.float32) + np.asarray(points, np.float32) @ rotation.T


def _poly(target, points, value):
    pts = np.rint(points).astype(np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(target, [pts], float(value), lineType=cv2.LINE_AA)


def _line(target, a, b, width, value):
    cv2.line(target, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
             float(value), max(1, min(8, int(width))), cv2.LINE_AA)


def _circle(target, center, radius, value):
    cv2.circle(target, tuple(np.rint(center).astype(int)),
               max(1, int(round(radius))), float(value), -1, cv2.LINE_AA)


def _write_channel(base, masks, recipe):
    out = np.full((S, S), float(base), np.float32)
    for name, target in recipe:
        alpha = _f(masks[name])
        out = out * (1.0 - alpha) + float(target) * alpha
    return np.clip(out, 0.0, 255.0).astype(np.float32)


def _morpho_nanoscales() -> Grammar:
    """Dense 8--32-native-pixel nanoridge anatomy without an RNG carrier."""
    plate = _mask()
    overlap_lip = _mask()
    ridge_trunk = _mask()
    lamellar_shelves = _mask()
    cross_ribs = _mask()
    root_sockets = _mask()
    perforation_pores = _mask()
    dislocation_forks = _mask()
    missing_shelves = _mask()
    order_teeth = _mask()

    # Every scale fits inside roughly 8x8 work pixels (32x32 at 2048).  The
    # integer/quasiperiodic laws alter placement and anatomy but inject no
    # texture noise.  Eight unequal strength tiers survive into paint/spec.
    golden = (5.0 ** .5 - 1.0) * .5
    roots = {}
    rows = range(-2, 60)
    columns = range(-2, 64)
    for row in rows:
        for col in columns:
            phase = 2.0 * np.pi * ((row * golden + col * golden * golden) % 1.0)
            cx = (col * 8.35 + (row & 1) * 4.1
                  + 1.45 * np.sin(.29 * row + .17 * col))
            cy = row * 8.72 + 1.20 * np.cos(.23 * col - .11 * row)
            angle = (16.0 * np.sin(.117 * row + .071 * col)
                     + 9.0 * np.cos(.053 * row - .137 * col))
            center = np.asarray((cx, cy), np.float32)
            roots[(row, col)] = _transform(center, angle, ((0.0, -3.7),))[0]
            tier = (row * 5 + col * 3 + (row * col) % 7) % 8
            strength = (.28, .38, .48, .58, .68, .78, .88, .98)[tier]

            outline = _transform(center, angle, (
                (0.0, -3.8), (-2.8, -2.2), (-3.8, .9),
                (-2.7, 3.25), (0.0, 3.85), (2.7, 3.25),
                (3.8, .9), (2.8, -2.2),
            ))
            _poly(plate, outline, .42 + .54 * strength)

            root, tip = _transform(center, angle, ((0.0, -3.35), (0.0, 3.35)))
            left_lip, mid_lip, right_lip = _transform(
                center, angle, ((-2.65, 2.75), (0.0, 3.62), (2.65, 2.75)))
            _line(overlap_lip, left_lip, mid_lip, 2, .50 + .48 * strength)
            _line(overlap_lip, mid_lip, right_lip, 2, .50 + .48 * strength)
            _line(ridge_trunk, root, tip, 2, .58 + .40 * strength)

            # Alternating lamellae are the Morpho-specific Christmas-tree
            # cross-section.  They are attached to the trunk, never scattered.
            for shelf_index, local_y in enumerate((-1.55, .10, 1.72)):
                side = -1.0 if (shelf_index + row + col) & 1 else 1.0
                extent = 2.15 + .42 * np.sin(phase + shelf_index * 1.9)
                base, end = _transform(center, angle, (
                    (0.0, local_y), (side * extent, local_y + .68)))
                _line(lamellar_shelves, base, end, 2,
                      .44 + .50 * ((tier + 2 * shelf_index) % 8) / 7.0)
                if shelf_index != 1:
                    rib_end = _transform(center, angle, ((side * extent, local_y - .62),))[0]
                    _line(cross_ribs, end, rib_end, 1,
                          .38 + .54 * ((tier + shelf_index + 3) % 8) / 7.0)

            _circle(root_sockets, root, 1.45, .52 + .46 * strength)
            pore_a, pore_b = _transform(center, angle, ((-1.7, -.25), (1.7, 1.15)))
            _circle(perforation_pores, pore_a, 1.0, .42 + .50 * strength)
            if (row + 2 * col) % 3:
                _circle(perforation_pores, pore_b, 1.0, .36 + .56 * strength)

            # Defects follow exact integer crystallography, not RNG/noise.
            defect_code = (row * row + 3 * col * col + 5 * row * col) % 29
            if defect_code in (0, 3, 11):
                a, b, c = _transform(center, angle, (
                    (0.0, -.15), (2.65, -.95), (3.25, .35)))
                _line(dislocation_forks, a, b, 2, .62 + .34 * strength)
                _line(dislocation_forks, b, c, 2, .62 + .34 * strength)
            if defect_code in (7, 19):
                a, b = _transform(center, angle, ((-2.4, .05), (2.4, .05)))
                _line(missing_shelves, a, b, 2, .72 + .24 * strength)
            if defect_code in (13, 23):
                tooth_a, tooth_b = _transform(center, angle, ((-1.25, 3.0), (1.25, 3.0)))
                _circle(order_teeth, tooth_a, 1.0, .62 + .34 * strength)
                _circle(order_teeth, tooth_b, 1.0, .62 + .34 * strength)

    # Sparse physical bridges couple neighbouring roots only where the modular
    # dislocation rule says adjacent micro-scales share a cross-rib.
    for (row, col), root in roots.items():
        other = roots.get((row, col + 1))
        if other is not None and (row * 7 + col * 11) % 17 in (0, 5):
            _line(cross_ribs, root, other, 1, .64)

    masks = {
        "overlapping_scale_plates": _f(plate),
        "distal_overlap_lips": _f(overlap_lip),
        "nanoridge_trunks": _f(ridge_trunk),
        "alternating_lamellar_shelves": _f(lamellar_shelves),
        "cross_rib_bridges": _f(cross_ribs),
        "scale_root_sockets": _f(root_sockets),
        "perforation_pores": _f(perforation_pores),
        "dislocation_forks": _f(dislocation_forks),
        "missing_shelf_notches": _f(missing_shelves),
        "terminal_order_teeth": _f(order_teeth),
    }
    banks = {
        "overlapping_scale_plates": "A",
        "distal_overlap_lips": "B",
        "nanoridge_trunks": "B",
        "alternating_lamellar_shelves": "B",
        "cross_rib_bridges": "A",
        "scale_root_sockets": "A",
        "perforation_pores": "N",
        "dislocation_forks": "A",
        "missing_shelf_notches": "N",
        "terminal_order_teeth": "B",
    }

    # Literal per-anatomy colors.  There is no common palette router or field
    # ranker; opponent cobalt plates and cyan/violet optical shelves own the
    # Fractured handoff.
    paint = np.broadcast_to(_rgb("#050817"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#101e64"), .91 * masks["overlapping_scale_plates"])
    paint = _blend(paint, _rgb("#283cc7"), .74 * masks["cross_rib_bridges"])
    paint = _blend(paint, _rgb("#4f178d"), .86 * masks["scale_root_sockets"])
    paint = _blend(paint, _rgb("#06dff5"), .96 * masks["nanoridge_trunks"])
    paint = _blend(paint, _rgb("#a93eff"), .94 * masks["alternating_lamellar_shelves"])
    paint = _blend(paint, _rgb("#50f8ff"), .96 * masks["distal_overlap_lips"])
    paint = _blend(paint, _rgb("#040615"), .98 * masks["perforation_pores"])
    paint = _blend(paint, _rgb("#ffb52c"), .94 * masks["dislocation_forks"])
    paint = _blend(paint, _rgb("#02030a"), .99 * masks["missing_shelf_notches"])
    paint = _blend(paint, _rgb("#e9f8ff"), .97 * masks["terminal_order_teeth"])

    hue_null = np.full((S, S), .045, np.float32)
    for name, level in (
        ("overlapping_scale_plates", .24), ("cross_rib_bridges", .47),
        ("scale_root_sockets", .34), ("nanoridge_trunks", .82),
        ("alternating_lamellar_shelves", .66), ("distal_overlap_lips", .94),
        ("perforation_pores", .025), ("dislocation_forks", .73),
        ("missing_shelf_notches", .015), ("terminal_order_teeth", .99),
    ):
        alpha = masks[name]
        hue_null = hue_null * (1.0 - alpha) + float(level) * alpha
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write_channel(8, masks, (
        ("overlapping_scale_plates", 94), ("cross_rib_bridges", 172),
        ("scale_root_sockets", 126), ("nanoridge_trunks", 244),
        ("alternating_lamellar_shelves", 218), ("distal_overlap_lips", 252),
        ("perforation_pores", 3), ("dislocation_forks", 196),
        ("missing_shelf_notches", 5), ("terminal_order_teeth", 232),
    ))
    rough = _write_channel(238, masks, (
        ("overlapping_scale_plates", 154), ("cross_rib_bridges", 102),
        ("scale_root_sockets", 184), ("nanoridge_trunks", 28),
        ("alternating_lamellar_shelves", 48), ("distal_overlap_lips", 18),
        ("perforation_pores", 250), ("dislocation_forks", 74),
        ("missing_shelf_notches", 246), ("terminal_order_teeth", 36),
    ))
    coat = _write_channel(6, masks, (
        ("overlapping_scale_plates", 76), ("cross_rib_bridges", 134),
        ("scale_root_sockets", 44), ("nanoridge_trunks", 204),
        ("alternating_lamellar_shelves", 246), ("distal_overlap_lips", 254),
        ("perforation_pores", 4), ("dislocation_forks", 182),
        ("missing_shelf_notches", 3), ("terminal_order_teeth", 234),
    ))

    marks = tuple((name, mask, banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("MB-I1 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fmo_morpho_blue": _morpho_nanoscales,
}
HUES = {"fmo_morpho_blue": (.61, .81)}
MORPHO_BIO_IDS = tuple(BUILDERS)


@lru_cache(maxsize=2)
def _authored(fid: str):
    grammar = BUILDERS[fid]()
    spec = np.stack(grammar.explicit_spec, axis=2)
    return grammar.paint, np.clip(spec, 0, 255).astype(np.uint8)


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid: str) -> Grammar:
    return BUILDERS[fid]()


def debug_hue_null(fid: str):
    return debug_grammar(fid).hue_null


def owner_unions(grammar: Grammar):
    unions = {key: np.zeros((S, S), np.float32) for key in ("A", "B", "N")}
    for _name, mask, owner in grammar.marks:
        unions[owner] = np.maximum(unions[owner], mask)
    return unions


def debug_angle_pair(fid: str):
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .54 * rough, .20, 1.0)
    light_a = np.clip(.10 + 1.04 * metal * aperture + .34 * owners["A"]
                      - .10 * owners["B"], .08, 1.26)
    light_b = np.clip(.10 + 1.04 * coat * aperture + .34 * owners["B"]
                      - .10 * owners["A"], .08, 1.26)
    cobalt = np.asarray((.018, .075, .27), np.float32)
    violet = np.asarray((.20, .018, .29), np.float32)
    angle_a = np.clip(paint * light_a[..., None]
                      + cobalt * (metal * aperture * owners["A"])[..., None], 0, 1)
    angle_b = np.clip(paint * light_b[..., None]
                      + violet * (coat * aperture * owners["B"])[..., None], 0, 1)
    return (angle_a.astype(np.float32), angle_b.astype(np.float32),
            np.abs(angle_a - angle_b).astype(np.float32))


def _entry(fid: str):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        h, w = int(shape[0]), int(shape[1])
        source = np.asarray(paint, np.float32)
        if source.ndim != 3 or source.shape[2] < 3:
            source = np.zeros((h, w, 3), np.float32)
        else:
            source = source[:, :, :3]
            if source.size and float(source.max()) > 1.5:
                source = source / 255.0
            if source.shape[:2] != (h, w):
                source = cv2.resize(source, (w, h), interpolation=cv2.INTER_LINEAR)
        zone = np.asarray(mask, np.float32)
        if zone.ndim == 3:
            zone = zone[:, :, 0]
        if zone.shape != (h, w):
            zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
        authored, _spec = _authored(fid)
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_NEAREST)
        alpha = np.clip(zone * max(0.0, float(pm)), 0, 1)[..., None]
        return np.clip(source * (1.0 - alpha) + authored * alpha, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        h, w = int(shape[0]), int(shape[1])
        zone = np.asarray(mask, np.float32)
        if zone.ndim == 3:
            zone = zone[:, :, 0]
        if zone.shape != (h, w):
            zone = cv2.resize(zone, (w, h), interpolation=cv2.INTER_LINEAR)
        _paint, authored = _authored(fid)
        authored = cv2.resize(authored, (w, h), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(CALM_SPEC + (authored - CALM_SPEC) * max(0.0, float(sm)), 0, 255)
        rgb = active * np.clip(zone, 0, 1)[..., None] + CALM_SPEC * (1.0 - np.clip(zone, 0, 1)[..., None])
        out = np.empty((h, w, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    return spec_fn, paint_fn


def install_into_engine(registry, base_registry=None):
    """Install into an explicitly supplied registry only; module is not imported by production."""
    for fid in MORPHO_BIO_IDS:
        registry[fid] = _entry(fid)
    return "fractured-wilds-morpho-bio-independent-mb-i1: 1 isolated candidate"


__all__ = ["BUILDERS", "Grammar", "HUES", "MORPHO_BIO_IDS", "_authored",
           "_entry", "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
