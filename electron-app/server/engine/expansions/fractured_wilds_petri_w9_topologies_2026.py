# -*- coding: utf-8 -*-
"""WR-P9 one-finish Petri repair: Violet Garden branch-truth pass.

W8's thresholded scalar DLA crop hid the process inside a fuzzy mass.  This
module exposes the simulated occupied cells, neighbour topology and recorded
attachment age directly.  One irregular edge-to-edge rhizome seeds the
aggregate, so no floating specimen, tile, paver, radial hub or blur carrier is
available to dominate the card.

SPB-WILDS 2026-08-24, WR-P9.  Isolated candidate; not production-wired and no
owner acceptance is claimed.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable, Mapping, Tuple

import cv2
import numpy as np

from engine.expansions import fractured_wilds_petri_w8_topologies_2026 as w8


w7, w6, w5, w4 = w8.w7, w8.w6, w8.w5, w8.w4
S, X, Y, U, V, TAU = w4.S, w4.X, w4.Y, w4.U, w4.V, w4.TAU
Grammar = w4.Grammar
_f, _n = w4._f, w4._n
_soft_gt, _band, _phase_band = w4._soft_gt, w4._band, w4._phase_band
_edge, _dilate, _erode, _halo = w4._edge, w4._dilate, w4._erode, w4._halo
_curve, _line, _circle, _ellipse, _bezier = (
    w4._curve, w4._line, w4._circle, w4._ellipse, w4._bezier
)
_literal_spec, _finish = w4._literal_spec, w4._finish


def _dla_rhizome_history(res=288, walkers=62000, max_steps=920,
                         seed=0xD1A71):
    rng = np.random.default_rng(seed)
    occupied = np.zeros((res, res), np.uint8)
    age = np.zeros((res, res), np.float32)

    # The inoculation substrate is one non-focal, asymmetric rhizome crossing
    # the frame. DLA growth is allowed to attach anywhere on this lineage.
    t = np.linspace(-.08, 1.08, 520, dtype=np.float32)
    x = t * (res - 1)
    y = (res * (.18 + .63 * t)
         + res * .055 * np.sin(TAU * (1.37 * t + .11))
         + res * .026 * np.sin(TAU * (3.61 * t + .39)))
    points = np.rint(np.stack((x, y), axis=1)).astype(np.int32).reshape((-1, 1, 2))
    cv2.polylines(occupied, [points], False, 1, 1, cv2.LINE_8)
    seed_pixels = np.argwhere(occupied > 0)
    for i, (yy, xx) in enumerate(seed_pixels):
        age[yy, xx] = .02 + .10 * (i / max(1, len(seed_pixels) - 1))

    px = rng.integers(0, res, walkers, dtype=np.int32)
    py = rng.integers(0, res, walkers, dtype=np.int32)
    alive = np.ones(walkers, bool)
    attach_count = 1
    for step in range(max_steps):
        if not alive.any():
            break
        idx = np.flatnonzero(alive)
        xx, yy = px[idx], py[idx]
        touch = (
            occupied[(yy - 1) % res, xx]
            | occupied[(yy + 1) % res, xx]
            | occupied[yy, (xx - 1) % res]
            | occupied[yy, (xx + 1) % res]
        ).astype(bool)
        if touch.any():
            touched_idx = idx[touch]
            tx, ty = px[touched_idx], py[touched_idx]
            linear = ty.astype(np.int64) * res + tx.astype(np.int64)
            unique = np.unique(linear)
            uy = (unique // res).astype(np.int32)
            ux = (unique % res).astype(np.int32)
            fresh = occupied[uy, ux] == 0
            uy, ux = uy[fresh], ux[fresh]
            if len(uy):
                occupied[uy, ux] = 1
                ages = np.linspace(attach_count, attach_count + len(uy) - 1,
                                   len(uy), dtype=np.float32)
                age[uy, ux] = ages
                attach_count += len(uy)
            alive[touched_idx] = False
            idx = np.flatnonzero(alive)
        if not len(idx):
            break
        direction = rng.integers(0, 4, len(idx), dtype=np.int8)
        px[idx] = (px[idx] + (direction == 0) - (direction == 1)) % res
        py[idx] = (py[idx] + (direction == 2) - (direction == 3)) % res
        if step and step % 115 == 0:
            # Re-launch surviving walkers from the frame, where diffusion feed
            # enters the culture. This changes future attachments only.
            side = rng.integers(0, 4, len(idx))
            along = rng.integers(0, res, len(idx))
            px[idx] = np.where(side == 0, 0,
                               np.where(side == 1, res - 1, along))
            py[idx] = np.where(side == 2, 0,
                               np.where(side == 3, res - 1, along))
    return occupied, age


def _up(field, interpolation=cv2.INTER_NEAREST):
    return cv2.resize(np.asarray(field, np.float32), (S, S),
                      interpolation=interpolation).astype(np.float32)


def w9_violet_garden() -> Grammar:
    occupied_small, age_small = _dla_rhizome_history()
    occupied = _up(occupied_small)
    age = _up(_n(age_small), cv2.INTER_LINEAR)

    neighbour_count = np.zeros_like(occupied_small, np.int16)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                neighbour_count += np.roll(np.roll(occupied_small, dy, 0), dx, 1)
    tips = _up(((occupied_small > 0) & (neighbour_count <= 2)).astype(np.float32))
    junctions = _up(((occupied_small > 0) & (neighbour_count >= 5)).astype(np.float32))

    branch_body = _dilate(occupied, 1)
    old_trunks = _f(branch_body * _soft_gt(.58 - age, .11, .09))
    young_twigs = _f(branch_body * _soft_gt(age, .58, .10))
    branch_cortex = _f(_dilate(occupied, 2) - occupied)
    diffusion_sheath = _f(_dilate(occupied, 5) - _dilate(occupied, 2))
    active_tips = _dilate(tips, 2)
    fusion_junctions = _dilate(junctions, 2)
    tip_crowns = _f(_dilate(active_tips, 3) - _dilate(active_tips, 1))

    # Age scar bands exist only on recorded occupied branches. They cannot
    # become a full-frame contour or background carrier.
    age_phase = np.mod(age * 8.0, 1.0)
    age_scars = (_phase_band(age_phase * TAU, .17 * TAU, .075 * TAU)
                 * branch_body)
    dead_end_scars = _f(_edge(_soft_gt(.38 - age, .08, .07), 1) * branch_body)
    trapped_voids = _f(1.0 - _dilate(occupied, 5))
    nutrient_capture = _f(_halo(branch_body, 4.2) * (1.0 - trapped_voids))
    spore_bulbs = _f(active_tips * (.45 + .55 * _halo(active_tips, 2.4)))

    masks = dict(
        recorded_old_dla_trunks=old_trunks,
        recorded_young_dla_twigs=young_twigs,
        occupied_branch_cortex=branch_cortex,
        diffusion_capture_sheaths=diffusion_sheath,
        recorded_active_growth_tips=active_tips,
        high_degree_fusion_junctions=fusion_junctions,
        active_tip_crowns=tip_crowns,
        attachment_age_scars=age_scars,
        dead_end_branch_scars=dead_end_scars,
        trapped_aggregation_voids=trapped_voids,
        nutrient_capture_halos=nutrient_capture,
        fruiting_spore_bulbs=spore_bulbs,
    )
    banks = dict(
        recorded_old_dla_trunks="A", recorded_young_dla_twigs="B",
        occupied_branch_cortex="A", diffusion_capture_sheaths="B",
        recorded_active_growth_tips="B", high_degree_fusion_junctions="A",
        active_tip_crowns="B", attachment_age_scars="A",
        dead_end_branch_scars="N", trapped_aggregation_voids="N",
        nutrient_capture_halos="A", fruiting_spore_bulbs="B",
    )
    spec = _literal_spec(
        masks,
        (("recorded_old_dla_trunks", 226), ("recorded_young_dla_twigs", 38),
         ("occupied_branch_cortex", 174), ("recorded_active_growth_tips", 246),
         ("high_degree_fusion_junctions", 112), ("dead_end_branch_scars", 78),
         ("fruiting_spore_bulbs", 198)),
        (("trapped_aggregation_voids", 238), ("recorded_old_dla_trunks", 62),
         ("recorded_young_dla_twigs", 182), ("diffusion_capture_sheaths", 126),
         ("recorded_active_growth_tips", 34), ("attachment_age_scars", 212),
         ("nutrient_capture_halos", 158)),
        (("trapped_aggregation_voids", 18), ("recorded_old_dla_trunks", 74),
         ("recorded_young_dla_twigs", 224), ("diffusion_capture_sheaths", 246),
         ("active_tip_crowns", 178), ("high_degree_fusion_junctions", 132),
         ("fruiting_spore_bulbs", 252)),
    )
    tone = age + .31 * active_tips + .24 * fusion_junctions
    return _finish(masks, banks, tone, spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = dict(w8.BUILDERS)
BUILDERS["fpe_violet_garden"] = w9_violet_garden
HUES = w8.HUES
PETRI_IDS: Tuple[str, ...] = tuple(BUILDERS)


@lru_cache(maxsize=20)
def _authored(fid: str):
    return w4._compose(BUILDERS[fid](), HUES[fid])


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid: str):
    return BUILDERS[fid]()


def owner_unions(grammar):
    return w4.owner_unions(grammar)


def debug_hue_null(fid: str):
    grammar = debug_grammar(fid)
    out = np.full((S, S), .06, np.float32)
    levels = (.18, .32, .47, .61, .74, .86, .96, .55, .27, .68, .81, .42)
    for index, (_name, mask, owner) in enumerate(grammar.marks):
        j = index if owner != "B" else len(levels) - 1 - (index % len(levels))
        out = out * (1.0 - mask) + levels[j % len(levels)] * mask
    return np.repeat(_f(out)[..., None], 3, axis=2).astype(np.float32)


def debug_angle_pair(fid: str):
    paint, spec = _authored(fid)
    owners = owner_unions(debug_grammar(fid))
    metal = spec[:, :, 0].astype(np.float32) / 255.0
    rough = spec[:, :, 1].astype(np.float32) / 255.0
    coat = spec[:, :, 2].astype(np.float32) / 255.0
    aperture = np.clip(1.0 - .52 * rough, .22, 1.0)
    la = np.clip(.10 + 1.12 * metal * aperture + .34 * owners["A"]
                 - .10 * owners["B"], .09, 1.25)
    lb = np.clip(.10 + 1.12 * coat * aperture + .34 * owners["B"]
                 - .10 * owners["A"], .09, 1.25)
    warm = np.asarray((.24, .07, .01), np.float32)
    cool = np.asarray((.01, .10, .25), np.float32)
    a = np.clip(paint * la[..., None]
                + warm * (metal * aperture * (.45 + .55 * owners["A"]))[..., None], 0, 1)
    b = np.clip(paint * lb[..., None]
                + cool * (coat * aperture * (.45 + .55 * owners["B"]))[..., None], 0, 1)
    return a.astype(np.float32), b.astype(np.float32), np.abs(a - b).astype(np.float32)


__all__ = ["BUILDERS", "Grammar", "HUES", "PETRI_IDS", "_authored",
           "clear_cache", "debug_angle_pair", "debug_grammar",
           "debug_hue_null", "owner_unions"]
