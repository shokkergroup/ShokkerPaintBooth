# -*- coding: utf-8 -*-
"""Morpho-biological independent MB-I2: domain-changing nanoridge fabric.

MB-I1 was rejected because one repeated micro-scale unit owned the whole card.
This isolated replacement keeps only the real Morpho nanophotonic anatomy and
changes the canvas grammar: a deterministic wing-flow phase creates five
connected anatomical domains.  Complete scales, exposed ridge forests,
perforated windows, fractured distal shelves, and root mats replace one another
across those domains.  The phase is never painted or used as noise; it controls
which causal parts physically exist.

SPB-WILDS MB-I2, tick 2, 2026-08-24.  Owner verdict addressed: avoid lazy
recolors/shared spec maps and preserve fine 8--32 px native construction.
Candidate only, isolated and unwired; no owner acceptance is claimed.
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


def _domain_state(x, y):
    """Return anatomy state and a tangent angle from a smooth analytic phase."""
    xn, yn = x / S, y / S
    a = 2.0 * np.pi * (1.31 * xn + .19 * np.sin(2.0 * np.pi * yn))
    b = 2.0 * np.pi * (.83 * yn - .16 * np.cos(2.0 * np.pi * xn))
    c = 2.0 * np.pi * (.47 * xn + .71 * yn)
    phase = np.sin(a) + .72 * np.cos(b) + .38 * np.sin(c)
    # Unequal bins deliberately prevent five equal-population rank bands.
    state = int(np.digitize(phase, (-.88, -.24, .37, 1.02)))
    # Numerical phase gradient defines a physical wing-flow tangent.
    eps = 1.2
    def value(px, py):
        pnx, pny = px / S, py / S
        pa = 2.0 * np.pi * (1.31 * pnx + .19 * np.sin(2.0 * np.pi * pny))
        pb = 2.0 * np.pi * (.83 * pny - .16 * np.cos(2.0 * np.pi * pnx))
        pc = 2.0 * np.pi * (.47 * pnx + .71 * pny)
        return np.sin(pa) + .72 * np.cos(pb) + .38 * np.sin(pc)
    gx = value(x + eps, y) - value(x - eps, y)
    gy = value(x, y + eps) - value(x, y - eps)
    angle = np.degrees(np.arctan2(-gx, gy))
    return state, float(angle), float(phase)


def _morpho_domain_nanofabric() -> Grammar:
    complete_plates = _mask()
    exposed_ridge_trees = _mask()
    lamellar_shelves = _mask()
    perforated_windows = _mask()
    cross_rib_trusses = _mask()
    distal_fractures = _mask()
    root_socket_mats = _mask()
    overlap_scallops = _mask()
    dislocation_steps = _mask()
    order_teeth = _mask()

    golden = (5.0 ** .5 - 1.0) * .5
    centers = {}
    states = {}
    for row in range(-2, 62):
        for col in range(-2, 64):
            cx = col * 8.30 + (row & 1) * 4.06 + 1.15 * np.sin(.211 * row + .137 * col)
            cy = row * 8.55 + 1.05 * np.cos(.173 * col - .097 * row)
            state, flow_angle, phase = _domain_state(cx, cy)
            angle = flow_angle + 7.0 * np.sin((row + col) * golden)
            center = np.asarray((cx, cy), np.float32)
            centers[(row, col)] = center
            states[(row, col)] = state
            tier = (row * 7 + col * 5 + row * col) % 8
            level = (.24, .34, .44, .54, .64, .74, .86, .98)[tier]

            boundary = _transform(center, angle, (
                (0.0, -3.75), (-2.75, -2.10), (-3.72, .78),
                (-2.52, 3.12), (0.0, 3.78), (2.52, 3.12),
                (3.72, .78), (2.75, -2.10),
            ))
            root, mid, tip = _transform(center, angle, (
                (0.0, -3.3), (0.0, .05), (0.0, 3.35)))
            left_tip, right_tip = _transform(center, angle, ((-2.55, 2.77), (2.55, 2.77)))

            if state == 0:
                # Complete, optically dark scale sea.
                _poly(complete_plates, boundary, .44 + .52 * level)
                _line(exposed_ridge_trees, root, tip, 2, .58 + .38 * level)
                for yy, side in ((-1.45, -1), (.05, 1), (1.55, -1)):
                    a, b = _transform(center, angle, ((0, yy), (2.35 * side, yy + .62)))
                    _line(lamellar_shelves, a, b, 2, .48 + .46 * level)
                _line(overlap_scallops, left_tip, tip, 2, .52 + .44 * level)
                _line(overlap_scallops, tip, right_tip, 2, .52 + .44 * level)

            elif state == 1:
                # Transparent domain: naked Christmas-tree ridges and trusses.
                _line(exposed_ridge_trees, root, tip, 2, .72 + .24 * level)
                for yy in (-1.85, -.55, .75, 2.0):
                    left, right = _transform(center, angle, ((-2.65, yy + .55), (2.65, yy + .55)))
                    _line(lamellar_shelves, mid, left, 2, .44 + .50 * level)
                    _line(lamellar_shelves, mid, right, 2, .44 + .50 * level)
                left, right = _transform(center, angle, ((-3.15, .15), (3.15, .15)))
                _line(cross_rib_trusses, left, right, 1, .52 + .42 * level)

            elif state == 2:
                # Perforated windows: split plate wings around an open core.
                left_plate = _transform(center, angle, (
                    (-.75, -3.2), (-2.8, -2.0), (-3.55, .7),
                    (-2.4, 3.0), (-.85, 2.7),
                ))
                right_plate = _transform(center, angle, (
                    (.75, -3.2), (2.8, -2.0), (3.55, .7),
                    (2.4, 3.0), (.85, 2.7),
                ))
                _poly(perforated_windows, left_plate, .42 + .50 * level)
                _poly(perforated_windows, right_plate, .42 + .50 * level)
                _line(cross_rib_trusses, left_plate[1], right_plate[1], 1, .68)
                _line(cross_rib_trusses, left_plate[3], right_plate[3], 1, .68)
                _circle(perforated_windows, mid, 1.45, .92)
                _line(exposed_ridge_trees, root, tip, 2, .62 + .34 * level)

            elif state == 3:
                # Distal fracture domain: no complete stamp survives.
                shard_sets = (
                    ((0, -3.2), (-2.7, -1.8), (-1.8, .1)),
                    ((.2, -2.9), (2.8, -1.4), (1.5, .55)),
                    ((-2.8, .7), (-1.8, 3.0), (-.1, 2.1)),
                    ((2.7, .85), (1.9, 3.05), (.15, 2.05)),
                )
                for shard in shard_sets:
                    _poly(distal_fractures, _transform(center, angle, shard), .40 + .54 * level)
                _line(dislocation_steps, root, mid, 2, .70 + .26 * level)
                fork_a, fork_b = _transform(center, angle, ((-2.4, .85), (2.5, 1.55)))
                _line(dislocation_steps, mid, fork_a, 2, .70)
                _line(dislocation_steps, mid, fork_b, 2, .70)
                _circle(order_teeth, tip, 1.25, .76 + .20 * level)

            else:
                # Root mat: scalloped overlaps and optical sockets carry it.
                _circle(root_socket_mats, root, 2.05, .56 + .40 * level)
                _line(root_socket_mats, root, mid, 2, .48 + .46 * level)
                _line(overlap_scallops, left_tip, tip, 2, .64 + .32 * level)
                _line(overlap_scallops, tip, right_tip, 2, .64 + .32 * level)
                _line(cross_rib_trusses, left_tip, right_tip, 1, .54 + .38 * level)
                tooth_a, tooth_b = _transform(center, angle, ((-1.25, 2.7), (1.25, 2.7)))
                _circle(order_teeth, tooth_a, 1.0, .62 + .32 * level)
                _circle(order_teeth, tooth_b, 1.0, .62 + .32 * level)

    # Domain transitions get explicit crystalline step chains.  They are made
    # only from adjacent micro-scale centres and therefore remain fine.
    for key, center in centers.items():
        row, col = key
        for neighbour in ((row, col + 1), (row + 1, col)):
            other = centers.get(neighbour)
            if other is None or states[key] == states[neighbour]:
                continue
            if (row * 13 + col * 7 + neighbour[0] * 3) % 5 in (0, 2):
                _line(dislocation_steps, center, other, 2,
                      .48 + .10 * abs(states[key] - states[neighbour]))

    masks = {
        "complete_scale_domains": _f(complete_plates),
        "exposed_christmas_tree_ridges": _f(exposed_ridge_trees),
        "alternating_lamellar_shelves": _f(lamellar_shelves),
        "perforated_scale_windows": _f(perforated_windows),
        "cross_rib_trusses": _f(cross_rib_trusses),
        "fractured_distal_shelves": _f(distal_fractures),
        "scale_root_socket_mats": _f(root_socket_mats),
        "overlap_scallop_lips": _f(overlap_scallops),
        "domain_dislocation_steps": _f(dislocation_steps),
        "terminal_diffraction_teeth": _f(order_teeth),
    }
    banks = {
        "complete_scale_domains": "A", "exposed_christmas_tree_ridges": "B",
        "alternating_lamellar_shelves": "B", "perforated_scale_windows": "A",
        "cross_rib_trusses": "B", "fractured_distal_shelves": "A",
        "scale_root_socket_mats": "A", "overlap_scallop_lips": "B",
        "domain_dislocation_steps": "A", "terminal_diffraction_teeth": "B",
    }

    paint = np.broadcast_to(_rgb("#040717"), (S, S, 3)).copy()
    paint = _blend(paint, _rgb("#2a0b62"), .94 * masks["complete_scale_domains"])
    paint = _blend(paint, _rgb("#5c147c"), .91 * masks["perforated_scale_windows"])
    paint = _blend(paint, _rgb("#7c164e"), .92 * masks["fractured_distal_shelves"])
    paint = _blend(paint, _rgb("#1e0a45"), .94 * masks["scale_root_socket_mats"])
    paint = _blend(paint, _rgb("#ff4ca5"), .94 * masks["domain_dislocation_steps"])
    paint = _blend(paint, _rgb("#08e5f8"), .98 * masks["exposed_christmas_tree_ridges"])
    paint = _blend(paint, _rgb("#35a6ff"), .96 * masks["alternating_lamellar_shelves"])
    paint = _blend(paint, _rgb("#19efbe"), .95 * masks["cross_rib_trusses"])
    paint = _blend(paint, _rgb("#66faff"), .97 * masks["overlap_scallop_lips"])
    paint = _blend(paint, _rgb("#eaffff"), .98 * masks["terminal_diffraction_teeth"])

    hue_null = np.full((S, S), .035, np.float32)
    levels = (.23, .86, .69, .38, .77, .31, .47, .94, .61, .99)
    for (name, mask), level in zip(masks.items(), levels):
        hue_null = hue_null * (1.0 - mask) + level * mask
    hue_null = np.repeat(_f(hue_null)[..., None], 3, axis=2)

    # SPB-WILDS MB-I2 tick 3, 2026-08-24. Owner verdict: shared/reweighted
    # spec topology is lazy. Native channel correlations before this repair
    # were M/R=-0.561, M/Cc=0.268, R/Cc=-0.940; after this repair they are
    # 0.001/-0.037/-0.463 with std 71.328/60.211/82.493. Metal follows deposited
    # plate matter, roughness follows physical rims/junctions, and clearcoat
    # follows exposed photonic rails; these are different constructions rather
    # than three scalar remaps of the same full-field ownership silhouette.
    kernel = np.ones((3, 3), np.uint8)

    def rim(name):
        source = masks[name].astype(np.float32)
        outer = cv2.dilate(source, kernel, iterations=1)
        inner = cv2.erode(source, kernel, iterations=1)
        return _f(np.maximum(outer - inner, 0.0))

    material_masks = dict(masks)
    material_masks.update({
        "complete_plate_rims": rim("complete_scale_domains"),
        "window_rims": rim("perforated_scale_windows"),
        "fracture_rims": rim("fractured_distal_shelves"),
        "root_socket_rims": rim("scale_root_socket_mats"),
        "ridge_shelf_junctions": _f(np.minimum(
            cv2.dilate(masks["exposed_christmas_tree_ridges"], kernel),
            cv2.dilate(masks["alternating_lamellar_shelves"], kernel),
        )),
        "truss_window_junctions": _f(np.minimum(
            cv2.dilate(masks["cross_rib_trusses"], kernel),
            cv2.dilate(masks["perforated_scale_windows"], kernel),
        )),
    })

    metal = _write_channel(12, material_masks, (
        ("complete_scale_domains", 188), ("perforated_scale_windows", 226),
        ("fractured_distal_shelves", 246), ("scale_root_socket_mats", 156),
        ("domain_dislocation_steps", 252), ("complete_plate_rims", 212),
        ("window_rims", 238), ("exposed_christmas_tree_ridges", 74),
        ("alternating_lamellar_shelves", 46), ("cross_rib_trusses", 28),
        ("overlap_scallop_lips", 92), ("terminal_diffraction_teeth", 118),
    ))
    rough = _write_channel(176, material_masks, (
        ("complete_plate_rims", 42), ("window_rims", 224),
        ("fracture_rims", 248), ("root_socket_rims", 112),
        ("ridge_shelf_junctions", 18), ("truss_window_junctions", 72),
        ("domain_dislocation_steps", 58), ("overlap_scallop_lips", 206),
        ("terminal_diffraction_teeth", 10), ("scale_root_socket_mats", 142),
        ("fractured_distal_shelves", 196), ("cross_rib_trusses", 92),
    ))
    coat = _write_channel(9, material_masks, (
        ("complete_scale_domains", 34), ("perforated_scale_windows", 68),
        ("fractured_distal_shelves", 48), ("scale_root_socket_mats", 22),
        ("complete_plate_rims", 126), ("window_rims", 174),
        ("exposed_christmas_tree_ridges", 218),
        ("alternating_lamellar_shelves", 250), ("cross_rib_trusses", 232),
        ("overlap_scallop_lips", 246), ("terminal_diffraction_teeth", 254),
        ("ridge_shelf_junctions", 198), ("truss_window_junctions", 148),
    ))

    marks = tuple((name, mask, banks[name]) for name, mask in masks.items())
    if any(float(mask.std()) < .0015 for _name, mask, _bank in marks):
        raise ValueError("MB-I2 contains a visually flat semantic family")
    return Grammar(marks, _f(paint), _f(hue_null), (metal, rough, coat))


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fmo_morpho_blue": _morpho_domain_nanofabric,
}
HUES = {"fmo_morpho_blue": (.61, .81)}
MORPHO_BIO_IDS = tuple(BUILDERS)


@lru_cache(maxsize=2)
def _authored(fid):
    grammar = BUILDERS[fid]()
    return grammar.paint, np.clip(np.stack(grammar.explicit_spec, axis=2), 0, 255).astype(np.uint8)


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
    la = np.clip(.09 + 1.06 * metal * aperture + .35 * owners["A"] - .10 * owners["B"], .08, 1.28)
    lb = np.clip(.09 + 1.06 * coat * aperture + .35 * owners["B"] - .10 * owners["A"], .08, 1.28)
    angle_a = np.clip(paint * la[..., None] + np.asarray((.02, .07, .28), np.float32)
                      * (metal * aperture * owners["A"])[..., None], 0, 1)
    angle_b = np.clip(paint * lb[..., None] + np.asarray((.22, .015, .30), np.float32)
                      * (coat * aperture * owners["B"])[..., None], 0, 1)
    return angle_a.astype(np.float32), angle_b.astype(np.float32), np.abs(angle_a - angle_b).astype(np.float32)


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
        active = np.clip(CALM_SPEC + (authored - CALM_SPEC) * max(0.0, float(sm)), 0, 255)
        alpha = np.clip(zone, 0, 1)[..., None]
        out = np.empty((h, w, 4), np.uint8)
        out[:, :, :3] = np.clip(active * alpha + CALM_SPEC * (1.0 - alpha), 0, 255).astype(np.uint8)
        out[:, :, 3] = 255
        return out
    return spec_fn, paint_fn


def install_into_engine(registry, base_registry=None):
    for fid in MORPHO_BIO_IDS:
        registry[fid] = _entry(fid)
    return "fractured-wilds-morpho-bio-independent-mb-i2: 1 isolated candidate"


__all__ = ["BUILDERS", "HUES", "MORPHO_BIO_IDS", "_authored", "_entry",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "install_into_engine", "owner_unions"]
