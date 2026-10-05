# -*- coding: utf-8 -*-
"""Bloom independent MW-I2: dual-parastichy vascular fabric.

MW-I1 was rejected because its detailed cups collapsed to generic bright-dot
phyllotaxis.  MW-I2 changes the dominant visible topology: only a quiet bed of
unequal cups remains, while selected Fibonacci ancestry classes become two
continuous, countable vascular spiral families.  Broken florets, ligules,
hooks, rims, pins, and cross-arcs remain locally attached.  The centre stays
off-canvas, so no hub or bullseye survives.

SPB-WILDS MW-I2, tick 2, 2026-08-24.  Isolated and unwired.  Reject if the
contact reads as a generic line lattice rather than a capitulum fabric.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_morpho_bio_independent_w1_2026 import (
    CALM_SPEC, Grammar, S, _blend, _f, _line, _rgb, _write_channel,
)
from .fractured_wilds_bloom_magenta_whorl_i1_2026 import (
    _vogel_capitulum as _mw_i1_grammar,
)


def _vogel_vascular_fabric() -> Grammar:
    prior = _mw_i1_grammar()
    masks = {name: np.asarray(mask, np.float32).copy()
             for name, mask, _bank in prior.marks}
    banks = {name: bank for name, _mask, bank in prior.marks}

    dextral = np.zeros((S, S), np.float32)
    sinistral = np.zeros((S, S), np.float32)
    cross_arcs = np.zeros((S, S), np.float32)
    origin = np.asarray((-118.0, 278.0), np.float32)
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    points = {}
    tiers = {}
    for n in range(28, 11800):
        radius = 6.72 * np.sqrt(float(n))
        theta = n * golden_angle
        radial_warp = 1.0 + .026 * np.sin(.037 * n) + .014 * np.sin(.113 * n)
        center = np.asarray((
            origin[0] + radius * radial_warp * np.cos(theta),
            origin[1] + .91 * radius * np.sin(theta),
        ), np.float32)
        if -12.0 <= center[0] <= S + 12.0 and -12.0 <= center[1] <= S + 12.0:
            points[n] = center
            tiers[n] = (n * 7 + (n // 13) * 3) % 8

    # Residue classes are literal parastichy strands.  Connecting n -> n+34
    # or n -> n+55 preserves each strand across the crop instead of sprinkling
    # disconnected links around points.  Unequal residue sets prevent a mesh.
    dextral_residues = {1, 4, 8, 13, 19, 26, 31}
    sinistral_residues = {2, 9, 17, 28, 39, 48}
    for n, center in points.items():
        if n % 34 in dextral_residues:
            other = points.get(n + 34)
            if other is not None:
                distance = float(np.linalg.norm(other - center))
                if 4.0 <= distance <= 16.0:
                    value = (.34, .43, .52, .61, .70, .79, .89, .98)[tiers[n]]
                    _line(dextral, center, other, 2, value)
        if n % 55 in sinistral_residues:
            other = points.get(n + 55)
            if other is not None:
                distance = float(np.linalg.norm(other - center))
                if 4.0 <= distance <= 16.0:
                    value = (.98, .87, .76, .65, .55, .46, .38, .30)[tiers[n]]
                    _line(sinistral, center, other, 2, value)

    # Cross-arcs exist only where the two living vessel families approach.
    # They are short perpendicular septa, not a third global carrier.
    d_bin = dextral > .38
    s_bin = sinistral > .38
    near = cv2.dilate(d_bin.astype(np.uint8), np.ones((5, 5), np.uint8)) & s_bin
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        near.astype(np.uint8), 8)
    for component in range(1, count):
        area = int(stats[component, cv2.CC_STAT_AREA])
        if not (2 <= area <= 80) or component % 3:
            continue
        center = np.asarray(centroids[component], np.float32)
        angle = .73 * component
        normal = np.asarray((np.cos(angle), np.sin(angle)), np.float32)
        _line(cross_arcs, center - normal * 2.4, center + normal * 2.4,
              2, .46 + .08 * (component % 7))

    masks["dextral_parastichy_vessels"] = _f(dextral)
    masks["sinistral_parastichy_vessels"] = _f(sinistral)
    masks["vascular_cross_arcs"] = _f(cross_arcs)

    # Quiet the rejected point read.  Cups/rims/pins supply biological context,
    # but the two continuous spiral families now own the silhouette.
    paint = np.broadcast_to(_rgb("#08020f"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#421033"), .46 * masks["mature_seed_cups"])
    paint = _blend(paint, _rgb("#161030"), .52 * masks["recessed_seed_cups"])
    paint = _blend(paint, _rgb("#8a315e"), .40 * masks["individual_cup_rims"])
    paint = _blend(paint, _rgb("#7f6890"), .36 * masks["offset_stamen_pins"])
    paint = _blend(paint, _rgb("#ff1f88"), .99 * masks["dextral_parastichy_vessels"])
    paint = _blend(paint, _rgb("#15eaff"), .99 * masks["sinistral_parastichy_vessels"])
    paint = _blend(paint, _rgb("#ffd34e"), .95 * masks["vascular_cross_arcs"])
    paint = _blend(paint, _rgb("#8d4aff"), .94 * masks["attached_bract_hooks"])
    paint = _blend(paint, _rgb("#ff7b32"), .94 * masks["age_banded_ligule_blades"])
    paint = _blend(paint, _rgb("#23e5a0"), .96 * masks["broken_floret_wedges"])
    paint = _blend(paint, _rgb("#020006"), .98 * masks["missing_cup_scars"])

    hue_null = np.full((S, S), .025, np.float32)
    levels = {
        "mature_seed_cups": .25, "recessed_seed_cups": .13,
        "dextral_parastichy_vessels": .91,
        "sinistral_parastichy_vessels": .68,
        "individual_cup_rims": .42, "vascular_cross_arcs": .98,
        "attached_bract_hooks": .74, "age_banded_ligule_blades": .56,
        "offset_stamen_pins": .47, "broken_floret_wedges": .82,
        "missing_cup_scars": .06,
    }
    for name, mask in masks.items():
        level = levels[name]
        hue_null = hue_null * (1.0 - mask) + level * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write_channel(5, masks, (
        ("mature_seed_cups", 154), ("individual_cup_rims", 118),
        ("dextral_parastichy_vessels", 252), ("vascular_cross_arcs", 224),
        ("age_banded_ligule_blades", 188), ("recessed_seed_cups", 24),
        ("sinistral_parastichy_vessels", 52), ("attached_bract_hooks", 78),
        ("offset_stamen_pins", 102), ("broken_floret_wedges", 66),
        ("missing_cup_scars", 14),
    ))
    rough = _write_channel(244, masks, (
        ("mature_seed_cups", 166), ("individual_cup_rims", 116),
        ("dextral_parastichy_vessels", 24), ("vascular_cross_arcs", 52),
        ("age_banded_ligule_blades", 84), ("recessed_seed_cups", 218),
        ("sinistral_parastichy_vessels", 76), ("attached_bract_hooks", 138),
        ("offset_stamen_pins", 38), ("broken_floret_wedges", 104),
        ("missing_cup_scars", 232),
    ))
    coat = _write_channel(6, masks, (
        ("mature_seed_cups", 34), ("individual_cup_rims", 96),
        ("dextral_parastichy_vessels", 70), ("vascular_cross_arcs", 118),
        ("age_banded_ligule_blades", 146), ("recessed_seed_cups", 222),
        ("sinistral_parastichy_vessels", 252), ("attached_bract_hooks", 238),
        ("offset_stamen_pins", 246), ("broken_floret_wedges", 194),
        ("missing_cup_scars", 16),
    ))

    marks = tuple((name, _f(mask), banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("MW-I2 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_magenta_whorl": _vogel_vascular_fabric,
}
HUES = {"fbl_magenta_whorl": (.92, .52)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=2)
def _authored(fid):
    grammar = BUILDERS[fid]()
    return grammar.paint, np.clip(np.stack(grammar.explicit_spec, axis=2),
                                  0, 255).astype(np.uint8)


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid):
    return BUILDERS[fid]()


def debug_hue_null(fid):
    return debug_grammar(fid).hue_null


def owner_unions(grammar):
    unions = {key: np.zeros((S, S), np.float32) for key in ("A", "B", "N")}
    for _name, mask, bank in grammar.marks:
        unions[bank] = np.maximum(unions[bank], mask)
    return unions


def debug_angle_pair(fid):
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .54 * rough, .20, 1.0)
    la = np.clip(.08 + 1.08 * metal * aperture + .34 * owners["A"]
                 - .12 * owners["B"], .07, 1.31)
    lb = np.clip(.08 + 1.08 * coat * aperture + .34 * owners["B"]
                 - .12 * owners["A"], .07, 1.31)
    angle_a = np.clip(paint * la[..., None]
                      + np.asarray((.35, .015, .13), np.float32)
                      * (metal * aperture * owners["A"])[..., None], 0, 1)
    angle_b = np.clip(paint * lb[..., None]
                      + np.asarray((.01, .22, .36), np.float32)
                      * (coat * aperture * owners["B"])[..., None], 0, 1)
    return (angle_a.astype(np.float32), angle_b.astype(np.float32),
            np.abs(angle_a - angle_b).astype(np.float32))


def _entry(fid):
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
        active = np.clip(CALM_SPEC + (authored - CALM_SPEC)
                         * max(0.0, float(sm)), 0, 255)
        alpha = np.clip(zone, 0, 1)[..., None]
        out = np.empty((h, w, 4), np.uint8)
        out[:, :, :3] = np.clip(active * alpha + CALM_SPEC * (1.0 - alpha),
                                0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out
    return spec_fn, paint_fn


def install_into_engine(registry, base_registry=None):
    for fid in BLOOM_IDS:
        registry[fid] = _entry(fid)
    return "fractured-wilds-bloom-magenta-whorl-mw-i2: 1 isolated candidate"


__all__ = ["BUILDERS", "BLOOM_IDS", "HUES", "_authored", "_entry",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
