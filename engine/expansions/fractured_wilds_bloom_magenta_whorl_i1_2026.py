# -*- coding: utf-8 -*-
"""Bloom independent MW-I1: edge-cropped Vogel capitulum fabric.

This candidate owns one off-canvas capitulum rather than a repeated flower
stamp or a visible bullseye.  Two literal, countable parastichy families bend
through unequal seed cups; cup rims, vascular arcs, bract hooks, ligules,
stamen pins, broken florets, and missing-cup scars remain attached to that
growth history.  No RNG, noise texture, grid, generic dot field, or shared
material carrier is used.

SPB-WILDS MW-I1, tick 1, 2026-08-24.  Isolated and unwired.  Owner-eye review,
not mechanical uniqueness, decides whether this survives.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping

import cv2
import numpy as np

from .fractured_wilds_morpho_bio_independent_w1_2026 import (
    CALM_SPEC, Grammar, S, _blend, _circle, _f, _line, _mask, _poly, _rgb,
    _transform, _write_channel,
)


def _open_hook(target, center, axes, angle, start, end, value):
    cv2.ellipse(
        target, tuple(np.rint(center).astype(int)),
        tuple(max(1, int(round(v))) for v in axes), float(angle),
        float(start), float(end), float(value), 2, cv2.LINE_AA,
    )


def _vogel_capitulum() -> Grammar:
    mature_cups = _mask()
    shadow_cups = _mask()
    dextral_parastichy = _mask()
    sinistral_parastichy = _mask()
    cup_rims = _mask()
    vascular_arcs = _mask()
    bract_hooks = _mask()
    ligule_blades = _mask()
    stamen_pins = _mask()
    broken_florets = _mask()
    missing_cup_scars = _mask()

    origin = np.asarray((-118.0, 278.0), np.float32)
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    points = {}
    rows = []

    # One phyllotactic history fills the crop.  Its centre remains off canvas,
    # so no logo-like hub or giant bullseye can appear.  Individual seed cups
    # are 8--32 native pixels; larger visible sweeps arise only from their
    # ancestry along the two neighbour-index families.
    for n in range(28, 11800):
        radius = 6.72 * np.sqrt(float(n))
        theta = n * golden_angle
        radial_warp = 1.0 + .026 * np.sin(.037 * n) + .014 * np.sin(.113 * n)
        x = origin[0] + radius * radial_warp * np.cos(theta)
        y = origin[1] + .91 * radius * np.sin(theta)
        if not (-12.0 <= x <= S + 12.0 and -12.0 <= y <= S + 12.0):
            continue
        center = np.asarray((x, y), np.float32)
        angle = np.degrees(theta) + 90.0 + 7.0 * np.sin(.071 * n)
        tier = (n * 7 + (n // 13) * 3) % 8
        strength = (.24, .34, .44, .54, .64, .74, .86, .98)[tier]
        state = (n + n // 21 + n // 55) % 17
        points[n] = center
        rows.append((n, center, angle, radius, strength, tier, state))

        half_w = 2.15 + .32 * ((n // 8) % 4)
        half_h = 2.75 + .28 * (n % 5)
        cup = _transform(center, angle, (
            (0.0, -half_h), (-half_w, -.55 * half_h),
            (-.84 * half_w, .58 * half_h), (0.0, half_h),
            (.84 * half_w, .58 * half_h), (half_w, -.55 * half_h),
        ))

        if state in (0, 9):
            # Broken florets are three attached wedge fragments, never debris.
            core, left, right, tip = _transform(center, angle, (
                (0.0, -.20 * half_h), (-half_w, -.38 * half_h),
                (half_w, -.38 * half_h), (0.0, half_h),
            ))
            _poly(broken_florets, (core, left, tip), .54 + .42 * strength)
            _poly(broken_florets, (core, tip, right), .36 + .48 * strength)
            _line(missing_cup_scars, left, right, 2, .50 + .44 * strength)
        else:
            target = shadow_cups if state in (4, 5, 12) else mature_cups
            _poly(target, cup, .30 + .58 * strength)
            for a, b in zip(cup, np.roll(cup, -1, axis=0)):
                _line(cup_rims, a, b, 2, .40 + .54 * strength)

        # The pin is offset toward the growing face, not centered like a dot.
        pin = _transform(center, angle, ((0.0, -.42 * half_h),))[0]
        _circle(stamen_pins, pin, 1.10 + .16 * (tier % 3),
                .50 + .46 * strength)

        # Bract hooks and ligules occur at age intervals, stay attached to a
        # cup, and use short 8--32-native primitives.
        if n % 13 in (1, 2, 7):
            hook_center = _transform(center, angle, ((0.0, .58 * half_h),))[0]
            _open_hook(bract_hooks, hook_center,
                       (2.0 + .25 * (tier % 3), 1.5 + .2 * (state % 3)),
                       angle, 18, 282, .42 + .52 * strength)
        if n % 47 in (3, 11, 29):
            base, left, tip, right = _transform(center, angle, (
                (0.0, .55 * half_h), (-1.45, 1.6),
                (0.0, 5.4 + .45 * (tier % 4)), (1.45, 1.6),
            ))
            _poly(ligule_blades, (base, left, tip, right),
                  .38 + .54 * strength)

    # Fibonacci neighbour offsets trace the two actual parastichy families.
    # Segments are short cup-to-cup vascular connections, never a free mesh.
    for n, center, _angle, _radius, strength, tier, state in rows:
        for offset, target, selector in (
                (34, dextral_parastichy, (0, 1, 5)),
                (55, sinistral_parastichy, (0, 3))):
            other = points.get(n + offset)
            if other is None or (n + tier) % 7 not in selector:
                continue
            distance = float(np.linalg.norm(other - center))
            if not (4.0 <= distance <= 15.0):
                continue
            _line(target, center, other, 2, .34 + .58 * strength)
            if (n + offset + state) % 11 == 0:
                midpoint = .5 * (center + other)
                tangent = (other - center) / max(distance, 1.0e-6)
                normal = np.asarray((-tangent[1], tangent[0]), np.float32)
                _line(vascular_arcs, midpoint - normal * 2.2,
                      midpoint + normal * 2.2, 2, .44 + .50 * strength)

    masks = {
        "mature_seed_cups": _f(mature_cups),
        "recessed_seed_cups": _f(shadow_cups),
        "dextral_parastichy_vessels": _f(dextral_parastichy),
        "sinistral_parastichy_vessels": _f(sinistral_parastichy),
        "individual_cup_rims": _f(cup_rims),
        "vascular_cross_arcs": _f(vascular_arcs),
        "attached_bract_hooks": _f(bract_hooks),
        "age_banded_ligule_blades": _f(ligule_blades),
        "offset_stamen_pins": _f(stamen_pins),
        "broken_floret_wedges": _f(broken_florets),
        "missing_cup_scars": _f(missing_cup_scars),
    }
    banks = {
        "mature_seed_cups": "A", "recessed_seed_cups": "B",
        "dextral_parastichy_vessels": "A",
        "sinistral_parastichy_vessels": "B", "individual_cup_rims": "N",
        "vascular_cross_arcs": "A", "attached_bract_hooks": "B",
        "age_banded_ligule_blades": "A", "offset_stamen_pins": "B",
        "broken_floret_wedges": "B", "missing_cup_scars": "N",
    }

    paint = np.broadcast_to(_rgb("#090312"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#a80665"), .92 * masks["mature_seed_cups"])
    paint = _blend(paint, _rgb("#441184"), .95 * masks["recessed_seed_cups"])
    paint = _blend(paint, _rgb("#ff2e9d"), .97 * masks["dextral_parastichy_vessels"])
    paint = _blend(paint, _rgb("#24e3ff"), .98 * masks["sinistral_parastichy_vessels"])
    paint = _blend(paint, _rgb("#ffcf45"), .91 * masks["individual_cup_rims"])
    paint = _blend(paint, _rgb("#ff732e"), .94 * masks["vascular_cross_arcs"])
    paint = _blend(paint, _rgb("#844cff"), .96 * masks["attached_bract_hooks"])
    paint = _blend(paint, _rgb("#ff685e"), .93 * masks["age_banded_ligule_blades"])
    paint = _blend(paint, _rgb("#eaffff"), .98 * masks["offset_stamen_pins"])
    paint = _blend(paint, _rgb("#13d39d"), .97 * masks["broken_floret_wedges"])
    paint = _blend(paint, _rgb("#150526"), .98 * masks["missing_cup_scars"])

    hue_null = np.full((S, S), .025, np.float32)
    levels = (.38, .18, .84, .67, .94, .58, .73, .47, .99, .31, .08)
    for (name, mask), level in zip(masks.items(), levels):
        hue_null = hue_null * (1.0 - mask) + float(level) * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write_channel(5, masks, (
        ("mature_seed_cups", 198), ("dextral_parastichy_vessels", 252),
        ("vascular_cross_arcs", 226), ("age_banded_ligule_blades", 176),
        ("individual_cup_rims", 132), ("missing_cup_scars", 84),
        ("recessed_seed_cups", 24), ("sinistral_parastichy_vessels", 48),
        ("attached_bract_hooks", 72), ("offset_stamen_pins", 102),
        ("broken_floret_wedges", 58),
    ))
    rough = _write_channel(244, masks, (
        ("mature_seed_cups", 142), ("dextral_parastichy_vessels", 28),
        ("vascular_cross_arcs", 64), ("age_banded_ligule_blades", 96),
        ("individual_cup_rims", 44), ("missing_cup_scars", 214),
        ("recessed_seed_cups", 202), ("sinistral_parastichy_vessels", 82),
        ("attached_bract_hooks", 168), ("offset_stamen_pins", 18),
        ("broken_floret_wedges", 116),
    ))
    coat = _write_channel(6, masks, (
        ("mature_seed_cups", 38), ("dextral_parastichy_vessels", 72),
        ("vascular_cross_arcs", 98), ("age_banded_ligule_blades", 126),
        ("individual_cup_rims", 154), ("missing_cup_scars", 22),
        ("recessed_seed_cups", 218), ("sinistral_parastichy_vessels", 252),
        ("attached_bract_hooks", 236), ("offset_stamen_pins", 246),
        ("broken_floret_wedges", 188),
    ))

    marks = tuple((name, mask, banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("MW-I1 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_magenta_whorl": _vogel_capitulum,
}
HUES = {"fbl_magenta_whorl": (.90, .52)}
BLOOM_IDS = tuple(BUILDERS)


@lru_cache(maxsize=2)
def _authored(fid):
    grammar = BUILDERS[fid]()
    spec = np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)
    return grammar.paint, spec


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
    light_a = np.clip(.08 + 1.08 * metal * aperture
                      + .34 * owners["A"] - .12 * owners["B"], .07, 1.31)
    light_b = np.clip(.08 + 1.08 * coat * aperture
                      + .34 * owners["B"] - .12 * owners["A"], .07, 1.31)
    angle_a = np.clip(paint * light_a[..., None]
                      + np.asarray((.34, .015, .12), np.float32)
                      * (metal * aperture * owners["A"])[..., None], 0, 1)
    angle_b = np.clip(paint * light_b[..., None]
                      + np.asarray((.015, .20, .35), np.float32)
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
    return "fractured-wilds-bloom-magenta-whorl-mw-i1: 1 isolated candidate"


__all__ = ["BUILDERS", "BLOOM_IDS", "HUES", "_authored", "_entry",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
