# -*- coding: utf-8 -*-
"""Bloom independent BP-I1: echinate pollen atlas.

The rejected Bloom batches repeatedly renamed scalar fields and reused their
spec carriers.  This isolated candidate rebuilds only ``fbl_butter_pollen``.
Its visible carrier is a crowded, non-periodic atlas of unequal pollen grains:
complete echinate crowns, tri-colpate shells, germ pores, exposed reticulum,
cracked exines, contact flats, adhesion bridges, and shed spines.  A smooth
gust field chooses which physical anatomy exists; the field itself is never
painted, added as texture, or used to manufacture uniqueness.

SPB-WILDS BP-I1, tick 1, 2026-08-24.  Owner verdict addressed: no recolor
clones, no shared spec topology, and no random-noise differentiation.  All
drawn primitives remain 2--8 work pixels (8--32 pixels at native 2048).
Candidate only, isolated and unwired; owner acceptance is not claimed.
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


def _gust_state(x: float, y: float):
    """Return a physical pollen state and local transport orientation."""
    xn, yn = x / S, y / S

    def field(px, py):
        qx, qy = px / S, py / S
        return (np.sin(2.0 * np.pi * (1.07 * qx + .31 * qy)
                       + .54 * np.sin(2.0 * np.pi * .83 * qy))
                + .67 * np.cos(2.0 * np.pi * (.43 * qx - 1.21 * qy)
                                + .38 * np.sin(2.0 * np.pi * qx))
                + .31 * np.sin(2.0 * np.pi * (1.73 * qx + 1.39 * qy)))

    phase = float(field(x, y))
    eps = 1.4
    gx = field(x + eps, y) - field(x - eps, y)
    gy = field(x, y + eps) - field(x, y - eps)
    tangent = float(np.degrees(np.arctan2(-gx, gy)))
    # Unequal bands keep the biological states from becoming equal rank fills.
    state = int(np.digitize(phase, (-.82, -.18, .41, 1.03)))
    return state, tangent, phase


def _arc(target, center, radius, angle, start, end, width, value):
    cv2.ellipse(
        target,
        tuple(np.rint(center).astype(int)),
        (max(1, int(round(radius))), max(1, int(round(radius * .88)))),
        float(angle), float(start), float(end), float(value), int(width),
        cv2.LINE_AA,
    )


def _echinate_pollen_atlas() -> Grammar:
    exine_shells = _mask()
    spike_crowns = _mask()
    tri_colpi = _mask()
    germ_pores = _mask()
    reticulum = _mask()
    cracked_exines = _mask()
    contact_flats = _mask()
    adhesion_bridges = _mask()
    shed_spines = _mask()
    collapsed_sacs = _mask()
    pollen_centres = []

    # A warped triangular census supplies coverage, not texture.  Every centre
    # receives topology from the analytic gust state below, and each grain has
    # a different radius, aspect, rotation, opening, and intensity tier.  No
    # RNG or sampled noise enters paint, masks, or spec.
    golden = (5.0 ** .5 - 1.0) * .5
    for row in range(-2, 58):
        for col in range(-2, 58):
            cx = (col * 9.35 + (row & 1) * 4.45
                  + 2.15 * np.sin(.371 * row + .193 * col)
                  + .85 * np.sin(.109 * row * col))
            cy = (row * 9.05
                  + 2.05 * np.sin(.287 * col - .149 * row)
                  + .72 * np.cos(.071 * row * col))
            if not (-10.0 <= cx <= S + 10.0 and -10.0 <= cy <= S + 10.0):
                continue
            state, flow_angle, phase = _gust_state(cx, cy)
            tier = (row * 11 + col * 7 + row * col) % 8
            strength = (.24, .34, .44, .54, .64, .74, .86, .98)[tier]
            radius = 3.15 + .62 * ((row * 3 + col * 5) % 5) / 4.0
            angle = flow_angle + 21.0 * np.sin(2.0 * np.pi * (
                (row * golden + col * golden * golden) % 1.0))
            center = np.asarray((cx, cy), np.float32)
            pollen_centres.append((center, state, angle, radius, strength,
                                   row, col))

            # Complete exine is deliberately an unequal seven-sided sac, not
            # a circle stamp.  State 2 removes the face so fracture is visible.
            local = []
            for k in range(7):
                theta = 2.0 * np.pi * k / 7.0
                radial = radius * (.82 + .13 * np.sin(k * 2.19 + phase)
                                   + .05 * ((tier + 3 * k) % 4))
                local.append((radial * np.cos(theta),
                              .88 * radial * np.sin(theta)))
            shell = _transform(center, angle, local)

            if state != 2:
                _poly(exine_shells, shell, .25 + .48 * strength)
            if state == 4:
                # Collapsed shells keep only an asymmetric folded half-sac.
                folded = _transform(center, angle, (
                    (-radius * .8, -.3 * radius),
                    (-radius * .18, -.72 * radius),
                    (radius * .82, -.18 * radius),
                    (radius * .48, .28 * radius),
                    (-radius * .52, .42 * radius),
                ))
                _poly(collapsed_sacs, folded, .48 + .46 * strength)

            # Echinate crowns are attached to the exine perimeter.  Their
            # varying omissions and lengths make them anatomy, not star noise.
            if state in (0, 1, 3):
                spoke_count = 5 + ((row + 2 * col) % 4)
                for k in range(spoke_count):
                    if state == 3 and (k + tier) % 3 == 0:
                        continue
                    theta = 360.0 * k / spoke_count + 17.0 * np.sin(phase + k)
                    inner, outer = _transform(center, angle + theta, (
                        (radius * .67, 0.0),
                        (radius + 1.45 + .42 * ((k + tier) % 3), 0.0),
                    ))
                    _line(spike_crowns, inner, outer, 2,
                          .38 + .58 * ((tier + k * 3) % 8) / 7.0)

            if state in (0, 1):
                # Three colpi terminate in real germ pores and rotate with the
                # grain.  The grooves are causal B anatomy against A exine.
                for k in range(3):
                    theta = angle + k * 120.0 + 8.0 * np.sin(phase + k * 1.7)
                    start, end = _transform(center, theta, (
                        (-.22 * radius, 0.0), (.70 * radius, 0.0)))
                    _line(tri_colpi, start, end, 2,
                          .42 + .52 * ((tier + 2 * k) % 8) / 7.0)
                    pore = _transform(center, theta, ((.72 * radius, 0.0),))[0]
                    _circle(germ_pores, pore, 1.15 + .14 * ((tier + k) % 3),
                            .54 + .42 * strength)

            if state in (1, 3):
                # Reticulation is a tiny attached triangular exine scaffold.
                tri = _transform(center, angle + 30.0, (
                    (-.58 * radius, -.18 * radius),
                    (.08 * radius, -.61 * radius),
                    (.59 * radius, .16 * radius),
                    (-.11 * radius, .60 * radius),
                ))
                for a, b in zip(tri, np.roll(tri, -1, axis=0)):
                    _line(reticulum, a, b, 2, .40 + .54 * strength)
                _line(reticulum, tri[0], tri[2], 1, .36 + .52 * strength)

            if state == 2:
                # Broken grains retain three edge-cropped shell arcs and a
                # branched crack.  They cannot read as intact circle stamps.
                for k, (start, sweep) in enumerate(((12, 57), (132, 71), (246, 48))):
                    _arc(cracked_exines, center, radius, angle,
                         start + 7 * tier, start + 7 * tier + sweep,
                         2, .48 + .46 * ((tier + k * 2) % 8) / 7.0)
                root, fork, tip_a, tip_b = _transform(center, angle, (
                    (-.75 * radius, -.15 * radius),
                    (.02 * radius, .05 * radius),
                    (.72 * radius, -.54 * radius),
                    (.66 * radius, .62 * radius),
                ))
                _line(cracked_exines, root, fork, 2, .62 + .34 * strength)
                _line(cracked_exines, fork, tip_a, 2, .54 + .40 * strength)
                _line(cracked_exines, fork, tip_b, 2, .46 + .46 * strength)
                for k in range(2):
                    theta = angle + 33.0 + 137.0 * k
                    a, b = _transform(center, theta, (
                        (radius + .4, 0.0), (radius + 2.5 + .5 * k, 0.0)))
                    _line(shed_spines, a, b, 2, .58 + .34 * strength)

    # Only genuine near contacts produce flats/adhesion.  Links are short,
    # terminate on two pollen shells, and never form a free-standing web.
    for index, (center, state, _angle, radius, strength, row, col) in enumerate(
            pollen_centres):
        if state not in (3, 4):
            continue
        # The forward neighbour in census order avoids O(n^2) and makes one
        # bounded biological contact rather than a generic graph carrier.
        for step in (1, 2, 3):
            other_index = index + step
            if other_index >= len(pollen_centres):
                break
            other, other_state, _oa, other_radius, other_strength, orow, ocol = (
                pollen_centres[other_index])
            delta = other - center
            distance = float(np.linalg.norm(delta))
            if distance < radius + other_radius + 4.5 and abs(orow - row) <= 1:
                unit = delta / max(distance, 1.0e-6)
                a = center + unit * radius * .72
                b = other - unit * other_radius * .72
                normal = np.asarray((-unit[1], unit[0]), np.float32)
                _line(contact_flats, a - normal * 1.25, a + normal * 1.25,
                      2, .48 + .46 * strength)
                if other_state in (3, 4) and (row + col + step) % 3:
                    _line(adhesion_bridges, a, b, 2,
                          .44 + .50 * min(strength, other_strength))
                break

    masks = {
        "unequal_exine_sacs": _f(exine_shells),
        "attached_echinate_crowns": _f(spike_crowns),
        "tri_colpate_grooves": _f(tri_colpi),
        "terminal_germ_pores": _f(germ_pores),
        "exposed_exine_reticulum": _f(reticulum),
        "branched_exine_fractures": _f(cracked_exines),
        "deformed_contact_flats": _f(contact_flats),
        "adhesion_bridges": _f(adhesion_bridges),
        "shed_spine_debris": _f(shed_spines),
        "collapsed_pollen_sacs": _f(collapsed_sacs),
    }
    banks = {
        "unequal_exine_sacs": "A", "attached_echinate_crowns": "A",
        "tri_colpate_grooves": "B", "terminal_germ_pores": "B",
        "exposed_exine_reticulum": "A", "branched_exine_fractures": "B",
        "deformed_contact_flats": "N", "adhesion_bridges": "B",
        "shed_spine_debris": "B", "collapsed_pollen_sacs": "A",
    }

    # Paint and all three material channels are written from the named masks.
    # A is hot butter/gold exine; B is cool violet/cyan fracture chemistry.
    paint = np.broadcast_to(_rgb("#08050f"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#ffb000"), .86 * masks["unequal_exine_sacs"])
    paint = _blend(paint, _rgb("#ffe95c"), .97 * masks["attached_echinate_crowns"])
    paint = _blend(paint, _rgb("#ff632e"), .90 * masks["exposed_exine_reticulum"])
    paint = _blend(paint, _rgb("#d78911"), .88 * masks["collapsed_pollen_sacs"])
    paint = _blend(paint, _rgb("#251058"), .96 * masks["tri_colpate_grooves"])
    paint = _blend(paint, _rgb("#18e7ff"), .98 * masks["terminal_germ_pores"])
    paint = _blend(paint, _rgb("#a814ee"), .96 * masks["branched_exine_fractures"])
    paint = _blend(paint, _rgb("#44ffd0"), .94 * masks["adhesion_bridges"])
    paint = _blend(paint, _rgb("#ef54ff"), .92 * masks["shed_spine_debris"])
    paint = _blend(paint, _rgb("#fff0a6"), .90 * masks["deformed_contact_flats"])

    hue_null = np.full((S, S), .025, np.float32)
    levels = (.34, .91, .20, .98, .67, .43, .82, .58, .74, .29)
    for (name, mask), level in zip(masks.items(), levels):
        hue_null = hue_null * (1.0 - mask) + float(level) * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    metal = _write_channel(5, masks, (
        ("unequal_exine_sacs", 188), ("attached_echinate_crowns", 252),
        ("exposed_exine_reticulum", 224), ("collapsed_pollen_sacs", 146),
        ("deformed_contact_flats", 118), ("tri_colpate_grooves", 26),
        ("terminal_germ_pores", 54), ("branched_exine_fractures", 78),
        ("adhesion_bridges", 38), ("shed_spine_debris", 96),
    ))
    rough = _write_channel(242, masks, (
        ("unequal_exine_sacs", 152), ("attached_echinate_crowns", 28),
        ("exposed_exine_reticulum", 68), ("collapsed_pollen_sacs", 198),
        ("deformed_contact_flats", 112), ("tri_colpate_grooves", 218),
        ("terminal_germ_pores", 82), ("branched_exine_fractures", 176),
        ("adhesion_bridges", 46), ("shed_spine_debris", 126),
    ))
    coat = _write_channel(7, masks, (
        ("unequal_exine_sacs", 34), ("attached_echinate_crowns", 62),
        ("exposed_exine_reticulum", 96), ("collapsed_pollen_sacs", 22),
        ("deformed_contact_flats", 136), ("tri_colpate_grooves", 214),
        ("terminal_germ_pores", 254), ("branched_exine_fractures", 232),
        ("adhesion_bridges", 246), ("shed_spine_debris", 188),
    ))

    marks = tuple((name, mask, banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("BP-I1 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fbl_butter_pollen": _echinate_pollen_atlas,
}
HUES = {"fbl_butter_pollen": (.13, .78)}
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
                      + .32 * owners["A"] - .11 * owners["B"], .07, 1.30)
    light_b = np.clip(.08 + 1.08 * coat * aperture
                      + .32 * owners["B"] - .11 * owners["A"], .07, 1.30)
    angle_a = np.clip(paint * light_a[..., None]
                      + np.asarray((.31, .085, .005), np.float32)
                      * (metal * aperture * owners["A"])[..., None], 0, 1)
    angle_b = np.clip(paint * light_b[..., None]
                      + np.asarray((.025, .09, .34), np.float32)
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
    return "fractured-wilds-bloom-butter-pollen-bp-i1: 1 isolated candidate"


__all__ = ["BUILDERS", "BLOOM_IDS", "HUES", "_authored", "_entry",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
