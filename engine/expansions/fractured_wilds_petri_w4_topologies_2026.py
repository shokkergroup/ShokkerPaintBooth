# -*- coding: utf-8 -*-
"""WR-P4 ground-up, full-domain Petri topology candidates.

The W2/W3 Petri contact boards were rejected because they read as twenty
isolated logos on black: trees, balls, loops, a triangle and an S.  This
module is deliberately isolated and unwired.  It replaces that entire visual
language with twenty deterministic biological/material processes that fill
the car canvas.  A process family is used once; palette, seed, rotation,
noise, or a headline glyph never counts as a new finish.

Every constructor authors at 512 square, owns at least seven literal masks,
and writes its own M/R/Cc arrays from those named masks.  Fine strokes are
2--8 work pixels (8--32 pixels at 2048).  Low-level raster helpers are shared;
there is no shared carrier, rank texture, tile, row/grid compositor, RNG, or
generic field-to-finish router.

SPB-WILDS 2026-08-24, WR-P4.  Candidate only: no owner acceptance is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Mapping, Sequence, Tuple

import cv2
import numpy as np


S = 512
Y, X = np.mgrid[0:S, 0:S].astype(np.float32)
U = (X + 0.5) / S
V = (Y + 0.5) / S
TAU = np.float32(2.0 * np.pi)


@dataclass(frozen=True)
class Grammar:
    marks: Tuple[Tuple[str, np.ndarray, str], ...]
    tone: np.ndarray
    explicit_spec: Tuple[np.ndarray, np.ndarray, np.ndarray]


def _f(a):
    return np.clip(np.asarray(a, np.float32), 0.0, 1.0)


def _n(a):
    a = np.nan_to_num(np.asarray(a, np.float32))
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < 1.0e-7:
        return np.zeros_like(a)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _soft_gt(a, threshold, feather=0.035):
    return _f((np.asarray(a, np.float32) - float(threshold)) / float(feather) + 0.5)


def _band(a, centre, width, feather=0.025):
    d = np.abs(np.asarray(a, np.float32) - float(centre))
    return _f((float(width) - d) / float(feather) + 0.5)


def _phase_band(phase, centre, width):
    d = np.abs(np.angle(np.exp(1j * (np.asarray(phase) - float(centre)))))
    return _f((float(width) - d) / max(0.015, float(width) * 0.32) + 0.5)


def _edge(a, radius=1):
    u = _f(a)
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(u, k) - cv2.erode(u, k))


def _dilate(a, radius=1):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.dilate(_f(a), k))


def _erode(a, radius=1):
    k = np.ones((2 * int(radius) + 1,) * 2, np.uint8)
    return _f(cv2.erode(_f(a), k))


def _halo(a, sigma=2.0):
    return _f(cv2.GaussianBlur(_f(a), (0, 0), float(sigma)) - 0.16 * _f(a))


def _curve(mask, points, width=2, value=1.0, closed=False):
    pts = np.rint(np.asarray(points, np.float32)).astype(np.int32).reshape((-1, 1, 2))
    if len(pts) > 1:
        cv2.polylines(mask, [pts], bool(closed), float(value),
                      max(2, min(8, int(width))), cv2.LINE_AA)


def _line(mask, a, b, width=2, value=1.0):
    cv2.line(mask, tuple(np.rint(a).astype(int)), tuple(np.rint(b).astype(int)),
             float(value), max(2, min(8, int(width))), cv2.LINE_AA)


def _circle(mask, centre, radius, width=2, value=1.0):
    cv2.circle(mask, tuple(np.rint(centre).astype(int)), max(1, int(round(radius))),
               float(value), int(width), cv2.LINE_AA)


def _ellipse(mask, centre, axes, angle=0.0, width=2, value=1.0,
             start=0.0, end=360.0):
    cv2.ellipse(mask, tuple(np.rint(centre).astype(int)),
                tuple(np.maximum(1, np.rint(axes).astype(int))), float(angle),
                float(start), float(end), float(value), int(width), cv2.LINE_AA)


def _bezier(p0, p1, p2, p3, count=96):
    t = np.linspace(0.0, 1.0, int(count), dtype=np.float32)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, np.float32) for p in (p0, p1, p2, p3))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def _halton(index, base):
    value, scale, n = 0.0, 1.0, int(index)
    while n:
        scale /= float(base)
        value += scale * (n % base)
        n //= base
    return value


def _sites(count, phase=0, margin=6.0):
    span = S - 2.0 * float(margin)
    rows = []
    for i in range(1, int(count) + 1):
        # Low-discrepancy placement is deterministic structure, never a noise layer.
        hx = (_halton(i + 5 * phase, 2) + 0.071 * np.sin(i * 1.713 + phase)) % 1.0
        hy = (_halton(i + 9 * phase, 3) + 0.059 * np.cos(i * 1.337 + phase)) % 1.0
        rows.append((margin + span * hx, margin + span * hy))
    return np.asarray(rows, np.float32)


def _power_labels(points, weights=None):
    points = np.asarray(points, np.float32)
    weights = np.zeros(len(points), np.float32) if weights is None else np.asarray(weights, np.float32)
    first = np.full((S, S), np.inf, np.float32)
    second = np.full((S, S), np.inf, np.float32)
    labels = np.zeros((S, S), np.int16)
    for index, ((px, py), weight) in enumerate(zip(points, weights)):
        d = (X - px) ** 2 + (Y - py) ** 2 - float(weight)
        take = d < first
        second = np.where(take, first, np.minimum(second, d))
        labels = np.where(take, index, labels)
        first = np.where(take, d, first)
    return labels, _n(first), _n(np.maximum(second - first, 0.0))


def _label_edges(labels, radius=1):
    lab = np.asarray(labels)
    e = np.zeros(lab.shape, np.float32)
    e[:, 1:] = np.maximum(e[:, 1:], lab[:, 1:] != lab[:, :-1])
    e[1:, :] = np.maximum(e[1:, :], lab[1:, :] != lab[:-1, :])
    return _dilate(e, radius)


def _channel(base: float, masks: Mapping[str, np.ndarray], recipe):
    out = np.full((S, S), float(base), np.float32)
    for name, target in recipe:
        u = _f(masks[name])
        out = out * (1.0 - u) + float(target) * u
    return np.clip(out, 0.0, 255.0).astype(np.float32)


def _literal_spec(masks, metal, rough, coat, bases=(8.0, 220.0, 10.0)):
    return (_channel(bases[0], masks, metal),
            _channel(bases[1], masks, rough),
            _channel(bases[2], masks, coat))


def _finish(masks: Mapping[str, np.ndarray], banks: Mapping[str, str], tone,
            explicit_spec) -> Grammar:
    if len(masks) < 7:
        raise ValueError("WR-P4 lazy grammar: fewer than seven causal marks")
    if set(masks) != set(banks):
        raise ValueError("WR-P4 ownership mismatch")
    rows = []
    for name, mask in masks.items():
        u = _f(mask)
        if float(u.std()) < 0.0015:
            raise ValueError(f"WR-P4 flat causal mark {name!r}")
        owner = banks[name]
        if owner not in {"A", "B", "N"}:
            raise ValueError(f"WR-P4 bad owner {owner!r}")
        rows.append((name, u.astype(np.float32), owner))
    if not {"A", "B"}.issubset({owner for _name, _mask, owner in rows}):
        raise ValueError("WR-P4 lacks opponent A/B anatomy")
    spec = tuple(np.clip(np.asarray(ch, np.float32), 0.0, 255.0)
                 for ch in explicit_spec)
    if len(spec) != 3 or any(ch.shape != (S, S) for ch in spec):
        raise ValueError("WR-P4 explicit spec shape mismatch")
    ranges = tuple(float(np.ptp(ch)) for ch in spec)
    if (any(float(ch.std()) <= 20.0 for ch in spec)
            or ranges[0] < 180.0 or ranges[1] < 96.0 or ranges[2] < 180.0):
        raise ValueError("WR-P4 weak literal spec channel")
    return Grammar(tuple(rows), _n(tone), spec)


def _domain_specs(masks, a_name, b_name, accents_a, accents_b, neutral=()):
    """Low-level channel writer; every caller still names its own anatomy."""
    metal = [(a_name, 202), (b_name, 34)]
    coat = [(a_name, 28), (b_name, 220)]
    rough = [(a_name, 72), (b_name, 188)]
    metal.extend((name, value) for name, value in accents_a)
    coat.extend((name, value) for name, value in accents_b)
    rough.extend((name, value) for name, value in neutral)
    return _literal_spec(masks, metal, rough, coat)


# ---------------------------------------------------------------------------
# 01. Lenia-like living droplets: continuous cell bodies and annular exchange.


def p4_magenta_bloom() -> Grammar:
    phase = (np.sin(TAU * (5.0 * U + 2.0 * V + 0.11 * np.sin(TAU * 3.0 * V)))
             + np.sin(TAU * (-2.0 * U + 6.0 * V + 0.09 * np.cos(TAU * 4.0 * U)))
             + 0.72 * np.cos(TAU * (7.0 * U - 5.0 * V)))
    tissue = _n(phase)
    bodies = _soft_gt(tissue, 0.54, 0.045)
    intercellular = _f(1.0 - bodies)
    membranes = _edge(bodies, 1)
    cores = _soft_gt(tissue, 0.79, 0.035)
    annuli = _f(_dilate(cores, 5) - _dilate(cores, 2))
    necks = _f(_soft_gt(tissue, 0.47, 0.022) * _soft_gt(0.62 - tissue, 0.0, 0.028))
    buds = _f(_soft_gt(tissue, 0.69, 0.025) * (1.0 - _dilate(cores, 4)))
    rupture = _f(membranes * _soft_gt(np.sin(TAU * (13 * U - 9 * V)), 0.58, 0.18))
    contact = _f(_halo(membranes, 2.2) * intercellular)
    masks = dict(living_cell_bodies=bodies, intercellular_medium=intercellular,
                 lipid_membranes=membranes, replicating_cores=cores,
                 division_annuli=annuli, cytokinesis_necks=necks,
                 daughter_buds=buds, ruptured_membrane_lips=rupture,
                 contact_inhibition_saddles=contact)
    banks = dict(living_cell_bodies="A", intercellular_medium="B",
                 lipid_membranes="B", replicating_cores="A",
                 division_annuli="B", cytokinesis_necks="A",
                 daughter_buds="B", ruptured_membrane_lips="N",
                 contact_inhibition_saddles="N")
    spec = _domain_specs(masks, "living_cell_bodies", "intercellular_medium",
                         (("replicating_cores", 246), ("cytokinesis_necks", 166),
                          ("ruptured_membrane_lips", 112)),
                         (("lipid_membranes", 244), ("division_annuli", 178),
                          ("daughter_buds", 132)),
                         (("contact_inhibition_saddles", 246),
                          ("ruptured_membrane_lips", 210)))
    return _finish(masks, banks, tissue + 0.23 * annuli, spec)


# ---------------------------------------------------------------------------
# 02. Gray-Scott bilayer labyrinth: signed membrane sides and protein machinery.


def p4_cyan_membrane() -> Grammar:
    warp_u = U + 0.047 * np.sin(TAU * (3.0 * V + 0.4 * np.sin(TAU * 2.0 * U)))
    warp_v = V + 0.039 * np.sin(TAU * (4.0 * U - 0.3 * np.cos(TAU * 3.0 * V)))
    field = (np.sin(TAU * (9.0 * warp_u + 2.0 * warp_v))
             + 0.86 * np.sin(TAU * (-4.0 * warp_u + 11.0 * warp_v))
             + 0.48 * np.cos(TAU * (13.0 * warp_u - 7.0 * warp_v)))
    signed = np.tanh(field * 2.1)
    cytosol = _soft_gt(signed, 0.08, 0.16)
    lumen = _soft_gt(-signed, 0.08, 0.16)
    bilayer = _band(signed, 0.0, 0.13, 0.07)
    outer_leaflet = _band(signed, 0.22, 0.08, 0.045)
    inner_leaflet = _band(signed, -0.22, 0.08, 0.045)
    gate_phase = np.sin(TAU * (17.0 * U + 19.0 * V))
    channels = _f(bilayer * _soft_gt(gate_phase, 0.72, 0.12))
    rafts = _f(outer_leaflet * _soft_gt(np.cos(TAU * (7.0 * U - 5.0 * V)), 0.46, 0.16))
    fusion_necks = _f(inner_leaflet * _soft_gt(np.sin(TAU * (8.0 * U + 3.0 * V)), 0.52, 0.14))
    cleavage = _f(bilayer * _soft_gt(-np.cos(TAU * (5.0 * U + 9.0 * V)), 0.66, 0.13))
    masks = dict(cytosol_domain=cytosol, lumen_domain=lumen,
                 phospholipid_bilayer=bilayer, outer_leaflet=outer_leaflet,
                 inner_leaflet=inner_leaflet, transmembrane_channels=channels,
                 protein_rafts=rafts, fusion_necks=fusion_necks,
                 cleavage_breaks=cleavage)
    banks = dict(cytosol_domain="A", lumen_domain="B",
                 phospholipid_bilayer="N", outer_leaflet="A",
                 inner_leaflet="B", transmembrane_channels="A",
                 protein_rafts="B", fusion_necks="B", cleavage_breaks="N")
    spec = _literal_spec(
        masks,
        (("cytosol_domain", 184), ("lumen_domain", 24),
         ("outer_leaflet", 232), ("transmembrane_channels", 118),
         ("cleavage_breaks", 64)),
        (("cytosol_domain", 64), ("lumen_domain", 196),
         ("phospholipid_bilayer", 116), ("protein_rafts", 38),
         ("cleavage_breaks", 246)),
        (("cytosol_domain", 34), ("lumen_domain", 212),
         ("inner_leaflet", 244), ("fusion_necks", 164),
         ("transmembrane_channels", 92)),
    )
    return _finish(masks, banks, _n(signed) + 0.31 * channels, spec)


# ---------------------------------------------------------------------------
# 03. Competing clonal sectors: weighted growth lineage, not a random colony.


def p4_lime_culture() -> Grammar:
    sites = np.asarray([(-42, 92), (108, -28), (286, 34), (552, 126),
                        (486, 346), (318, 544), (98, 492), (-36, 318)], np.float32)
    weights = np.asarray([1200, -900, 650, -350, 980, -760, 420, -520], np.float32)
    labels, radial, gap = _power_labels(sites, weights)
    parity = (labels % 2).astype(np.float32)
    clone_a = _f((labels % 3 != 1).astype(np.float32) * (1.0 - 0.28 * parity))
    clone_b = _f(1.0 - clone_a)
    sector_walls = _label_edges(labels, 1)
    growth_fronts = _f(_phase_band(TAU * (8.7 * np.sqrt(radial + 0.003)), 0.0, 0.32)
                       * (1.0 - sector_walls))
    mutation_fans = _f((labels == 2) * _soft_gt(np.sin(TAU * (12 * U - 5 * V)), 0.35, 0.15)
                       + (labels == 5) * _soft_gt(np.cos(TAU * (7 * U + 11 * V)), 0.44, 0.14))
    nutrient_channels = _f(sector_walls * _soft_gt(np.sin(TAU * (9 * U + 13 * V)), -0.12, 0.20))
    division_septa = _f(growth_fronts * _soft_gt(np.cos(TAU * (19 * U - 17 * V)), 0.42, 0.12))
    inhibition_gaps = _f(_soft_gt(gap, 0.82, 0.045) * (1.0 - growth_fronts))
    satellites = _f(growth_fronts
                    * _soft_gt(np.cos(TAU * (23 * U))
                               + .72 * np.sin(TAU * (29 * V)), 1.02, 0.20))
    masks = dict(parent_clone_sectors=clone_a, mutant_clone_sectors=clone_b,
                 clonal_sector_walls=sector_walls, young_growth_fronts=growth_fronts,
                 mutation_fans=mutation_fans, nutrient_channels=nutrient_channels,
                 division_septa=division_septa, inhibition_gaps=inhibition_gaps,
                 satellite_colonies=satellites)
    banks = dict(parent_clone_sectors="A", mutant_clone_sectors="B",
                 clonal_sector_walls="N", young_growth_fronts="B",
                 mutation_fans="B", nutrient_channels="A", division_septa="A",
                 inhibition_gaps="N", satellite_colonies="B")
    spec = _literal_spec(
        masks,
        (("parent_clone_sectors", 210), ("mutant_clone_sectors", 28),
         ("division_septa", 248), ("nutrient_channels", 146),
         ("satellite_colonies", 82)),
        (("parent_clone_sectors", 78), ("mutant_clone_sectors", 174),
         ("inhibition_gaps", 246), ("clonal_sector_walls", 124),
         ("young_growth_fronts", 36)),
        (("parent_clone_sectors", 22), ("mutant_clone_sectors", 224),
         ("young_growth_fronts", 248), ("mutation_fans", 172),
         ("satellite_colonies", 106)),
    )
    return _finish(masks, banks, radial + 0.33 * growth_fronts + 0.17 * labels, spec)


# ---------------------------------------------------------------------------
# 04. Agar diffusion interference: fronts, inhibition lenses and gel cracks.


def p4_amber_agar() -> Grammar:
    sources = np.asarray([(-28, 70), (132, -36), (278, 74), (520, 18),
                          (548, 286), (404, 538), (178, 556), (-44, 400)], np.float32)
    waves = []
    distances = []
    for index, (cx, cy) in enumerate(sources):
        d = np.hypot(X - cx, Y - cy) / (38.0 + 3.0 * (index % 3))
        distances.append(d)
        waves.append(np.cos(TAU * d + index * 0.73))
    wave = np.sum(waves, axis=0)
    near = np.min(np.stack(distances), axis=0)
    agar_a = _soft_gt(wave, 0.12, 0.38)
    agar_b = _soft_gt(-wave, 0.12, 0.38)
    diffusion_fronts = _band(np.mod(near, 1.0), 0.0, 0.075, 0.03)
    interference_lenses = _band(_n(wave), 0.50, 0.055, 0.025)
    inhibition_zones = _f(_soft_gt(np.abs(wave), 3.7, 0.35) * (1.0 - diffusion_fronts))
    gel_cracks = _f(interference_lenses * _soft_gt(np.sin(TAU * (11 * U - 7 * V)), 0.32, 0.14))
    inoculation_rims = np.zeros((S, S), np.float32)
    satellite_drops = np.zeros_like(inoculation_rims)
    for i, p in enumerate(sources):
        _circle(inoculation_rims, p, 11 + 3 * (i % 3), 3)
        _circle(satellite_drops, p + np.asarray((18 - 5 * (i % 3), 12 + 4 * (i % 2))),
                3 + (i % 2), -1)
    precipitation_beads = _f(diffusion_fronts * _soft_gt(np.cos(TAU * (21 * U + 17 * V)), 0.71, 0.11))
    masks = dict(oxidized_agar_phase=agar_a, reduced_agar_phase=agar_b,
                 diffusion_fronts=diffusion_fronts,
                 interference_lenses=interference_lenses,
                 inhibition_zones=inhibition_zones, gel_crack_lips=gel_cracks,
                 inoculation_rims=inoculation_rims,
                 satellite_drops=satellite_drops,
                 precipitation_beads=precipitation_beads)
    banks = dict(oxidized_agar_phase="A", reduced_agar_phase="B",
                 diffusion_fronts="A", interference_lenses="B",
                 inhibition_zones="N", gel_crack_lips="N",
                 inoculation_rims="B", satellite_drops="A",
                 precipitation_beads="B")
    spec = _literal_spec(
        masks,
        (("oxidized_agar_phase", 188), ("reduced_agar_phase", 26),
         ("diffusion_fronts", 246), ("gel_crack_lips", 116),
         ("precipitation_beads", 72)),
        (("oxidized_agar_phase", 92), ("reduced_agar_phase", 202),
         ("inhibition_zones", 244), ("satellite_drops", 38),
         ("gel_crack_lips", 158)),
        (("oxidized_agar_phase", 18), ("reduced_agar_phase", 218),
         ("interference_lenses", 246), ("inoculation_rims", 152),
         ("precipitation_beads", 104)),
    )
    return _finish(masks, banks, _n(wave) + 0.27 * diffusion_fronts, spec)


# ---------------------------------------------------------------------------
# 05. Diffusion-limited garden: six off-canvas arbors interlock full-frame.


def p4_violet_garden() -> Grammar:
    trunk = np.zeros((S, S), np.float32)
    branch = np.zeros_like(trunk)
    active = np.zeros_like(trunk)
    buds = np.zeros_like(trunk)
    bridges = np.zeros_like(trunk)
    scars = np.zeros_like(trunk)
    roots = np.zeros_like(trunk)
    spore_cups = np.zeros_like(trunk)
    starts = [((-24, 84), 0.17), ((536, 134), np.pi - 0.20),
              ((94, 536), -1.31), ((420, -24), 1.77),
              ((-22, 390), -0.18), ((536, 448), np.pi + 0.29)]
    endpoints = []
    for tree, (start, heading) in enumerate(starts):
        frontier = [(np.asarray(start, np.float32), heading, 0)]
        for depth in range(6):
            nxt = []
            for node, angle, lineage in frontier:
                length = 34.0 - 3.1 * depth + 3.0 * np.sin(lineage + tree)
                bend = 0.15 * np.sin((tree + 1) * (depth + 1) + lineage * 0.7)
                end = node + length * np.asarray((np.cos(angle + bend), np.sin(angle + bend)))
                path = _bezier(node, node + (end - node) * .28 + (0, 4 - tree),
                               node + (end - node) * .72 + (3 - depth, -2), end, 22)
                _curve(trunk if depth < 2 else branch, path,
                       4 if depth == 0 else 2)
                if depth == 0:
                    # Entry cups sit just inside the crop even when the causal
                    # inoculation point itself is off-canvas.
                    _circle(roots, path[12], 5 + tree % 3, 2)
                if 3 <= depth <= 5:
                    _circle(active, end, 2 + (lineage + tree) % 2, -1)
                    _circle(buds, end + (4 * np.cos(angle + 1.4),
                                         4 * np.sin(angle + 1.4)), 3, 2)
                if (depth + lineage + tree) % 3 == 0:
                    _ellipse(spore_cups, (node + end) * .5, (5, 2),
                             np.degrees(angle), 2, start=20, end=320)
                if (depth + lineage) % 4 == 1:
                    tangent = np.asarray((np.cos(angle), np.sin(angle)))
                    normal = np.asarray((-tangent[1], tangent[0]))
                    _line(scars, end - normal * 4, end + normal * 4, 2)
                endpoints.append(end)
                if depth < 5:
                    spread = 0.42 - depth * 0.031
                    nxt.append((end, angle - spread, lineage * 2 + 1))
                    if (lineage + depth + tree) % 5 != 0:
                        nxt.append((end, angle + spread * .88, lineage * 2 + 2))
            frontier = nxt
    # Anastomosis bridges connect recorded branches, never a generic web field.
    for i in range(13, len(endpoints) - 37, 29):
        a, b = endpoints[i], endpoints[(i * 7 + 41) % len(endpoints)]
        if np.linalg.norm(a - b) < 88:
            _curve(bridges, _bezier(a, a + (8, -5), b + (-8, 5), b, 24), 2)
    substrate = _f(1.0 - _dilate(np.maximum(trunk, branch), 7))
    masks = dict(old_aggregate_trunks=trunk, young_dendrite_branches=branch,
                 active_growth_tips=active, spore_buds=buds,
                 anastomosis_bridges=bridges, arrested_tip_scars=scars,
                 inoculation_root_cups=roots, sporulation_cups=spore_cups,
                 depleted_substrate=substrate)
    banks = dict(old_aggregate_trunks="A", young_dendrite_branches="B",
                 active_growth_tips="B", spore_buds="A",
                 anastomosis_bridges="B", arrested_tip_scars="N",
                 inoculation_root_cups="A", sporulation_cups="B",
                 depleted_substrate="N")
    spec = _literal_spec(
        masks,
        (("old_aggregate_trunks", 224), ("young_dendrite_branches", 72),
         ("active_growth_tips", 246), ("inoculation_root_cups", 156),
         ("arrested_tip_scars", 104)),
        (("depleted_substrate", 238), ("old_aggregate_trunks", 86),
         ("spore_buds", 34), ("arrested_tip_scars", 188),
         ("sporulation_cups", 122)),
        (("depleted_substrate", 18), ("young_dendrite_branches", 204),
         ("anastomosis_bridges", 246), ("spore_buds", 146),
         ("sporulation_cups", 96)),
    )
    return _finish(masks, banks, _halo(np.maximum(trunk, branch), 5.0)
                   + .26 * active, spec)


# ---------------------------------------------------------------------------
# 06. Pennate silica fabric: overlapping valve rails with literal anatomy.


def p4_lime_diatom() -> Grammar:
    valve_a = np.zeros((S, S), np.float32)
    valve_b = np.zeros_like(valve_a)
    raphe = np.zeros_like(valve_a)
    striae = np.zeros_like(valve_a)
    costae = np.zeros_like(valve_a)
    nodules = np.zeros_like(valve_a)
    terminal_pores = np.zeros_like(valve_a)
    girdles = np.zeros_like(valve_a)
    chips = np.zeros_like(valve_a)
    # Twenty-three individually bent, overlapping valve fragments cross the
    # crop; none is a complete card-scale capsule or a repeated row stamp.
    for j in range(23):
        side = -1 if j & 1 else 1
        p0 = np.asarray((-46 + (j * 83) % 604, -34), np.float32)
        p3 = np.asarray((558 - (j * 61) % 590, 546), np.float32)
        p1 = np.asarray((80 + (j * 97) % 370, 112 + side * (24 + j % 31)), np.float32)
        p2 = np.asarray((432 - (j * 71) % 350, 368 - side * (19 + (j * 3) % 37)), np.float32)
        path = _bezier(p0, p1, p2, p3, 145)
        body = valve_a if j % 3 else valve_b
        _curve(body, path, 7 if j % 4 else 8, 0.72)
        _curve(raphe, path, 2)
        offset_path = []
        for k in range(4, 141, 5):
            p = path[k]
            t = path[min(144, k + 2)] - path[max(0, k - 2)]
            t /= np.linalg.norm(t) + 1.0e-6
            normal = np.asarray((-t[1], t[0]))
            span = 4.0 + (j + k) % 4
            _line(striae, p - normal * span, p + normal * span, 2)
            if (k // 5 + j) % 5 == 0:
                _line(costae, p - normal * (span + 2), p + normal * (span + 2), 3)
            if (k // 5 + j) % 11 == 3:
                _circle(nodules, p, 2 + (j % 2), -1)
            if (k // 5 + j) % 13 == 6:
                q = p + normal * (span + 2)
                _circle(chips, q, 2, 2)
            offset_path.append(p + normal * (5.0 + (j % 2)))
        _curve(girdles, offset_path, 2)
        for p in (path[12], path[-13]):
            _circle(terminal_pores, p, 3, 2)
    dark_medium = _f(1.0 - _dilate(np.maximum(valve_a, valve_b), 3))
    masks = dict(silica_valves_a=valve_a, silica_valves_b=valve_b,
                 central_raphe_slits=raphe, transverse_striae=striae,
                 load_bearing_costae=costae, central_nodules=nodules,
                 terminal_pores=terminal_pores, girdle_band_seams=girdles,
                 broken_valve_chips=chips, dark_culture_medium=dark_medium)
    banks = dict(silica_valves_a="A", silica_valves_b="B",
                 central_raphe_slits="B", transverse_striae="A",
                 load_bearing_costae="B", central_nodules="A",
                 terminal_pores="B", girdle_band_seams="N",
                 broken_valve_chips="N", dark_culture_medium="N")
    spec = _literal_spec(
        masks,
        (("silica_valves_a", 218), ("silica_valves_b", 38),
         ("central_raphe_slits", 94), ("load_bearing_costae", 246),
         ("broken_valve_chips", 156)),
        (("dark_culture_medium", 238), ("silica_valves_a", 82),
         ("silica_valves_b", 164), ("terminal_pores", 34),
         ("broken_valve_chips", 206)),
        (("dark_culture_medium", 16), ("silica_valves_b", 224),
         ("transverse_striae", 246), ("girdle_band_seams", 148),
         ("central_nodules", 96)),
    )
    return _finish(masks, banks, _halo(np.maximum(valve_a, valve_b), 3.0)
                   + .35 * striae, spec)


# ---------------------------------------------------------------------------
# 07. Aperiodic tissue mosaic: power-cell lineage and junction mechanics.


def p4_magenta_mosaic() -> Grammar:
    points = _sites(138, phase=17, margin=-18)
    weights = 190.0 * np.sin(np.arange(len(points), dtype=np.float32) * 2.399963)
    labels, radius, gap = _power_labels(points, weights)
    parity = ((labels * 5 + labels // 7) % 2).astype(np.float32)
    tissue_a = _f(parity)
    tissue_b = _f(1.0 - parity)
    walls = _label_edges(labels, 1)
    belts = _f(_dilate(walls, 3) - _dilate(walls, 1))
    nuclei = np.zeros((S, S), np.float32)
    nucleoli = np.zeros_like(nuclei)
    polarity = np.zeros_like(nuclei)
    apoptotic = np.zeros_like(nuclei)
    junctions = np.zeros_like(nuclei)
    for i, p in enumerate(points):
        _ellipse(nuclei, p, (3 + i % 4, 2 + (i * 3) % 3), (i * 47) % 180, -1)
        if i % 3 == 0:
            _circle(nucleoli, p + ((i % 5) - 2, ((i * 2) % 5) - 2), 2, -1)
        angle = i * 2.399963 + 0.31
        _line(polarity, p, p + 7 * np.asarray((np.cos(angle), np.sin(angle))), 2)
        if i % 17 == 4:
            _circle(apoptotic, p, 6, 2)
            _line(apoptotic, p + (-4, -4), p + (4, 4), 2)
            _line(apoptotic, p + (-4, 4), p + (4, -4), 2)
    # Triple-junction contact is derived from local edge multiplicity.
    junction_score = cv2.boxFilter(walls, cv2.CV_32F, (7, 7), normalize=False)
    junctions[:] = _soft_gt(junction_score, 13.0, 3.0)
    cleavage = _f(belts * _soft_gt(np.sin(TAU * (13 * U - 17 * V)), .57, .13))
    masks = dict(parent_tissue_cells=tissue_a, daughter_tissue_cells=tissue_b,
                 adherens_cell_walls=walls, cortical_actin_belts=belts,
                 offset_nuclei=nuclei, nucleoli=nucleoli,
                 polarity_axes=polarity, triple_junction_nodes=junctions,
                 apoptotic_cells=apoptotic, cleavage_furrows=cleavage)
    banks = dict(parent_tissue_cells="A", daughter_tissue_cells="B",
                 adherens_cell_walls="N", cortical_actin_belts="B",
                 offset_nuclei="A", nucleoli="B", polarity_axes="A",
                 triple_junction_nodes="B", apoptotic_cells="N",
                 cleavage_furrows="N")
    spec = _literal_spec(
        masks,
        (("parent_tissue_cells", 196), ("daughter_tissue_cells", 26),
         ("polarity_axes", 244), ("offset_nuclei", 136),
         ("cleavage_furrows", 78)),
        (("parent_tissue_cells", 74), ("daughter_tissue_cells", 186),
         ("adherens_cell_walls", 228), ("apoptotic_cells", 36),
         ("nucleoli", 124)),
        (("parent_tissue_cells", 24), ("daughter_tissue_cells", 222),
         ("cortical_actin_belts", 246), ("triple_junction_nodes", 164),
         ("nucleoli", 96)),
    )
    return _finish(masks, banks, radius + 0.21 * labels + .31 * belts, spec)


# ---------------------------------------------------------------------------
# 08. Hyperbolic radiolarian mesh: conformal arcs without a circular hero.


def p4_cyan_spineball() -> Grammar:
    z = (U - 0.47) + 1j * (V - 0.53)
    # Three unequal Mobius coordinates create a Poincare-like cage whose
    # centres live outside the crop; the result is an edge-to-edge web, not a ball.
    q1 = (z - (0.58 + 0.19j)) / (1.0 - (0.58 - 0.19j) * z)
    q2 = (z + (0.37 - 0.42j)) / (1.0 + (0.37 + 0.42j) * z)
    q3 = (z - (-0.16 + 0.71j)) / (1.0 - (-0.16 - 0.71j) * z)
    p1, p2, p3 = np.angle(q1), np.angle(q2), np.log(np.abs(q3) + 0.035)
    tri = np.cos(8 * p1) + np.cos(11 * p2) + np.cos(10.5 * p3)
    face_a = _soft_gt(tri, 0.12, 0.24)
    face_b = _soft_gt(-tri, 0.12, 0.24)
    geodesics = _f(_band(np.cos(8 * p1), 0.0, .13, .055)
                   + _band(np.cos(11 * p2), 0.0, .13, .055))
    pore_rims = _band(np.cos(10.5 * p3), 0.0, .11, .045)
    junctions = _soft_gt(geodesics * pore_rims, .43, .13)
    spine_roots = _f(junctions * _soft_gt(np.sin(17 * p1 - 13 * p2), .37, .16))
    radial_spines = _f(_dilate(spine_roots, 5) - _dilate(spine_roots, 2))
    aperture_collars = _f(pore_rims * _soft_gt(np.cos(19 * p2 + 7 * p3), .58, .13))
    broken_sockets = _f(junctions * _soft_gt(-np.sin(23 * p1 + 9 * p3), .66, .12))
    inner_shell = _phase_band(13 * p1 - 7 * p2 + 4 * p3, 0.0, .18)
    masks = dict(concave_shell_faces=face_a, convex_shell_faces=face_b,
                 geodesic_struts=geodesics, polygon_pore_rims=pore_rims,
                 multiway_junctions=junctions, spine_roots=spine_roots,
                 tapering_radial_spines=radial_spines,
                 aperture_collars=aperture_collars,
                 broken_spine_sockets=broken_sockets,
                 nested_inner_shell=inner_shell)
    banks = dict(concave_shell_faces="A", convex_shell_faces="B",
                 geodesic_struts="A", polygon_pore_rims="B",
                 multiway_junctions="N", spine_roots="A",
                 tapering_radial_spines="B", aperture_collars="B",
                 broken_spine_sockets="N", nested_inner_shell="A")
    spec = _literal_spec(
        masks,
        (("concave_shell_faces", 214), ("convex_shell_faces", 30),
         ("geodesic_struts", 246), ("spine_roots", 152),
         ("broken_spine_sockets", 84)),
        (("concave_shell_faces", 72), ("convex_shell_faces", 182),
         ("polygon_pore_rims", 38), ("multiway_junctions", 228),
         ("broken_spine_sockets", 132)),
        (("concave_shell_faces", 20), ("convex_shell_faces", 224),
         ("nested_inner_shell", 246), ("aperture_collars", 164),
         ("tapering_radial_spines", 104)),
    )
    return _finish(masks, banks, _n(tri) + .25 * inner_shell, spec)


# ---------------------------------------------------------------------------
# 09. Liesegang precipitation: intersecting chemical fronts and failure lips.


def p4_amber_moldring() -> Grammar:
    centres = np.asarray([(-72, 116), (98, -54), (326, -86), (582, 82),
                          (606, 356), (374, 584), (126, 620), (-84, 414)], np.float32)
    phase_terms = []
    nearest = np.full((S, S), np.inf, np.float32)
    for i, (cx, cy) in enumerate(centres):
        dx, dy = X - cx, Y - cy
        r = np.hypot(dx * (1.0 + .05 * (i % 3)), dy * (0.88 + .04 * (i % 4)))
        q = np.log1p(r / (7.0 + i % 4)) * (7.2 + .31 * i)
        phase_terms.append(np.cos(q + i * .61))
        nearest = np.minimum(nearest, r)
    chemistry = np.sum(phase_terms, axis=0)
    precipitate_a = _soft_gt(chemistry, .18, .36)
    precipitate_b = _soft_gt(-chemistry, .18, .36)
    ring_fronts = _band(np.cos(np.log1p(nearest) * 8.6), 0.0, .12, .05)
    supersaturation_lips = _f(_edge(precipitate_a, 1) * (1.0 - ring_fronts))
    depleted_troughs = _f((1.0 - _dilate(ring_fronts, 2)) * _soft_gt(np.abs(chemistry), 2.9, .32))
    bridge_hyphae = _f(_phase_band(13 * np.arctan2(V - .52, U - .48)
                                  + 7 * np.log(np.hypot(U - .48, V - .52) + .03),
                                  0.0, .13) * precipitate_b)
    burst_gaps = _f(ring_fronts * _soft_gt(np.sin(TAU * (17 * U - 12 * V)), .61, .12))
    crystal_beads = _f(ring_fronts * _soft_gt(np.cos(TAU * (29 * U + 23 * V)), .77, .08))
    collision_seams = _f(_band(_n(chemistry), .50, .035, .018))
    masks = dict(early_precipitate_phase=precipitate_a,
                 late_precipitate_phase=precipitate_b,
                 logarithmic_ring_fronts=ring_fronts,
                 supersaturation_lips=supersaturation_lips,
                 depleted_reaction_troughs=depleted_troughs,
                 bridge_hyphae=bridge_hyphae, burst_ring_gaps=burst_gaps,
                 crystal_beads=crystal_beads, collision_seams=collision_seams)
    banks = dict(early_precipitate_phase="A", late_precipitate_phase="B",
                 logarithmic_ring_fronts="A", supersaturation_lips="B",
                 depleted_reaction_troughs="N", bridge_hyphae="B",
                 burst_ring_gaps="N", crystal_beads="A",
                 collision_seams="B")
    spec = _literal_spec(
        masks,
        (("early_precipitate_phase", 196), ("late_precipitate_phase", 24),
         ("logarithmic_ring_fronts", 246), ("crystal_beads", 154),
         ("burst_ring_gaps", 76)),
        (("early_precipitate_phase", 86), ("late_precipitate_phase", 186),
         ("depleted_reaction_troughs", 244), ("bridge_hyphae", 38),
         ("collision_seams", 132)),
        (("early_precipitate_phase", 18), ("late_precipitate_phase", 224),
         ("supersaturation_lips", 246), ("bridge_hyphae", 166),
         ("crystal_beads", 98)),
    )
    return _finish(masks, banks, _n(chemistry) + .29 * ring_fronts, spec)


# ---------------------------------------------------------------------------
# 10. Deterministic neural CA chains: annular competition from a quasi seed.


def p4_violet_chains() -> Grammar:
    state = _n(np.cos(TAU * (7 * U + 3 * V))
               + np.cos(TAU * (-4 * U + 9 * V))
               + np.cos(TAU * (11 * U - 8 * V)))
    yy, xx = np.mgrid[-8:9, -8:9]
    rr = np.hypot(xx, yy)
    kin = (rr <= 3.0).astype(np.float32)
    kout = ((rr > 3.0) & (rr <= 8.0)).astype(np.float32)
    kin /= kin.sum()
    kout /= kout.sum()
    for _ in range(68):
        inside = cv2.filter2D(state, cv2.CV_32F, kin, borderType=cv2.BORDER_WRAP)
        outside = cv2.filter2D(state, cv2.CV_32F, kout, borderType=cv2.BORDER_WRAP)
        activation = .5 + .5 * np.tanh(8.5 * (inside - outside - .012))
        state = _f(.54 * state + .46 * activation)
    worm_a = _soft_gt(state, .57, .055)
    worm_b = _soft_gt(.43 - state, 0.0, .055)
    chain_skin = _edge(worm_a, 1)
    refractory_halo = _f(_dilate(worm_a, 4) - _dilate(worm_a, 2))
    bead_nodes = _f(worm_a * _soft_gt(np.cos(TAU * (23 * U + 17 * V)), .76, .09))
    fork_nodes = _soft_gt(cv2.boxFilter(chain_skin, cv2.CV_32F, (7, 7), normalize=False),
                          27.0, 2.5)
    side_buds = _f(refractory_halo * _soft_gt(np.sin(TAU * (19 * U - 29 * V)), .69, .10))
    dead_ends = _f(chain_skin * _soft_gt(np.cos(TAU * (31 * U + 5 * V)), .72, .10))
    crosslinks = _f(worm_b * _phase_band(TAU * (13 * U + 21 * V), 0.0, .13))
    masks = dict(excited_chain_bodies=worm_a, refractory_channels=worm_b,
                 chain_membrane_skin=chain_skin,
                 refractory_shoulders=refractory_halo, bead_nodes=bead_nodes,
                 branch_fork_nodes=fork_nodes, lateral_buds=side_buds,
                 arrested_chain_ends=dead_ends, conjugate_crosslinks=crosslinks)
    banks = dict(excited_chain_bodies="A", refractory_channels="B",
                 chain_membrane_skin="A", refractory_shoulders="B",
                 bead_nodes="A", branch_fork_nodes="B", lateral_buds="B",
                 arrested_chain_ends="N", conjugate_crosslinks="N")
    spec = _literal_spec(
        masks,
        (("excited_chain_bodies", 212), ("refractory_channels", 24),
         ("bead_nodes", 246), ("chain_membrane_skin", 148),
         ("arrested_chain_ends", 86)),
        (("excited_chain_bodies", 72), ("refractory_channels", 190),
         ("refractory_shoulders", 232), ("branch_fork_nodes", 36),
         ("arrested_chain_ends", 134)),
        (("excited_chain_bodies", 20), ("refractory_channels", 222),
         ("conjugate_crosslinks", 246), ("lateral_buds", 164),
         ("branch_fork_nodes", 102)),
    )
    return _finish(masks, banks, state + .28 * chain_skin, spec)


# ---------------------------------------------------------------------------
# 11. Nematode-like bacterial mat: coherent director domains and conjugation.


def p4_cyan_colony() -> Grammar:
    theta = (1.18 * np.sin(TAU * (1.7 * U + .8 * V))
             + .73 * np.cos(TAU * (-.6 * U + 2.1 * V)))
    director = U * np.cos(theta) + V * np.sin(theta)
    transverse = -U * np.sin(theta) + V * np.cos(theta)
    rod_phase = TAU * (33.0 * director + 2.2 * np.sin(TAU * 4.0 * transverse))
    septum_phase = TAU * (24.0 * transverse + 1.7 * np.sin(TAU * 3.0 * director))
    rods_a = _soft_gt(np.cos(rod_phase), .05, .16)
    rods_b = _soft_gt(-np.cos(rod_phase), .05, .16)
    cell_walls = _band(np.cos(rod_phase), 0.0, .12, .045)
    division_septa = _f(cell_walls * _soft_gt(np.cos(septum_phase), .61, .12))
    chromosome_bands = _f(rods_a * _phase_band(rod_phase * .5 + septum_phase, 0.0, .18))
    conjugation_pili = _f(rods_b * _phase_band(rod_phase - .43 * septum_phase, 0.0, .12))
    motility_fringes = _f(cell_walls * _soft_gt(np.sin(TAU * (27 * U - 19 * V)), .66, .11))
    spore_endcaps = _f(rods_a * _soft_gt(np.cos(TAU * (41 * U + 7 * V)), .78, .08))
    lysis_gaps = _f(rods_b * _soft_gt(np.sin(TAU * (11 * U + 37 * V)), .73, .09))
    quorum_fronts = _phase_band(8.0 * theta + TAU * (3 * U - 2 * V), 0.0, .15)
    masks = dict(clockwise_rod_domains=rods_a, counterclockwise_rod_domains=rods_b,
                 peptidoglycan_cell_walls=cell_walls,
                 cytokinesis_septa=division_septa,
                 chromosome_condensation_bands=chromosome_bands,
                 conjugation_pili=conjugation_pili,
                 motility_fringes=motility_fringes, spore_endcaps=spore_endcaps,
                 lysis_gaps=lysis_gaps, quorum_sensing_fronts=quorum_fronts)
    banks = dict(clockwise_rod_domains="A", counterclockwise_rod_domains="B",
                 peptidoglycan_cell_walls="N", cytokinesis_septa="A",
                 chromosome_condensation_bands="B", conjugation_pili="B",
                 motility_fringes="A", spore_endcaps="B",
                 lysis_gaps="N", quorum_sensing_fronts="A")
    spec = _literal_spec(
        masks,
        (("clockwise_rod_domains", 214), ("counterclockwise_rod_domains", 28),
         ("cytokinesis_septa", 246), ("motility_fringes", 154),
         ("lysis_gaps", 84)),
        (("clockwise_rod_domains", 68), ("counterclockwise_rod_domains", 188),
         ("peptidoglycan_cell_walls", 226), ("lysis_gaps", 36),
         ("spore_endcaps", 132)),
        (("clockwise_rod_domains", 20), ("counterclockwise_rod_domains", 224),
         ("conjugation_pili", 246), ("chromosome_condensation_bands", 164),
         ("quorum_sensing_fronts", 102)),
    )
    return _finish(masks, banks, _n(director) + .31 * cell_walls, spec)


# ---------------------------------------------------------------------------
# 12. Viscous fingering: pressure-driven branched invasion with active tips.


def p4_lime_mold() -> Grammar:
    z = (X - 236.0) + 1j * (Y - 278.0)
    potential = np.zeros((S, S), np.complex64)
    poles = [(-108 - 32j, 1.0), (286 - 214j, -.83),
             (344 + 286j, .71), (-266 + 212j, -.62),
             (44 + 19j, .44)]
    for pole, strength in poles:
        potential += strength * np.log(z - pole + 1.0e-3)
    potential += .00000092 * z ** 3 - .00018j * z ** 2
    pressure = np.real(potential)
    stream = np.imag(potential)
    invading = _soft_gt(np.sin(5.7 * pressure + .27 * np.sin(9.0 * stream)), .04, .17)
    displaced = _soft_gt(-np.sin(5.7 * pressure + .27 * np.sin(9.0 * stream)), .04, .17)
    finger_walls = _band(np.sin(5.7 * pressure + .27 * np.sin(9.0 * stream)), 0.0, .11, .045)
    active_tips = _f(finger_walls * _soft_gt(np.cos(12.0 * stream - 2.1 * pressure), .69, .10))
    side_branches = _phase_band(7.4 * stream + 3.1 * pressure, 0.0, .13)
    trapped_bays = _f(displaced * _soft_gt(np.cos(8.0 * pressure - 4.3 * stream), .72, .09))
    pressure_ribs = _f(invading * _phase_band(13.0 * pressure, 0.0, .15))
    anastomoses = _f(side_branches * finger_walls)
    spore_caps = _f(active_tips * _soft_gt(np.sin(TAU * (31 * U + 23 * V)), .63, .12))
    masks = dict(invading_mold_phase=invading, displaced_nutrient_phase=displaced,
                 viscous_finger_walls=finger_walls, active_finger_tips=active_tips,
                 lateral_side_branches=side_branches,
                 trapped_nutrient_bays=trapped_bays,
                 pressure_growth_ribs=pressure_ribs,
                 anastomosis_crossings=anastomoses, spore_tip_caps=spore_caps)
    banks = dict(invading_mold_phase="A", displaced_nutrient_phase="B",
                 viscous_finger_walls="A", active_finger_tips="B",
                 lateral_side_branches="B", trapped_nutrient_bays="N",
                 pressure_growth_ribs="A", anastomosis_crossings="N",
                 spore_tip_caps="B")
    spec = _literal_spec(
        masks,
        (("invading_mold_phase", 208), ("displaced_nutrient_phase", 26),
         ("pressure_growth_ribs", 246), ("viscous_finger_walls", 146),
         ("trapped_nutrient_bays", 78)),
        (("invading_mold_phase", 74), ("displaced_nutrient_phase", 190),
         ("trapped_nutrient_bays", 242), ("spore_tip_caps", 34),
         ("anastomosis_crossings", 128)),
        (("invading_mold_phase", 18), ("displaced_nutrient_phase", 224),
         ("active_finger_tips", 246), ("lateral_side_branches", 166),
         ("spore_tip_caps", 102)),
    )
    return _finish(masks, banks, _n(pressure) + .27 * finger_walls, spec)


# ---------------------------------------------------------------------------
# 13. Twelve-fold centric frustule: quasicrystal ribs and silica apertures.


def p4_amber_diatom() -> Grammar:
    q = np.zeros((S, S), np.float32)
    q2 = np.zeros_like(q)
    for k in range(12):
        a = np.pi * k / 12.0
        phase = TAU * (19.0 * (U * np.cos(a) + V * np.sin(a)))
        q += np.cos(phase + .31 * np.sin((k + 1) * .73))
        q2 += np.cos(phase * (1.0 + .015 * (-1) ** k) + k * .47)
    q /= 12.0
    q2 /= 12.0
    silica_a = _soft_gt(q, .035, .085)
    silica_b = _soft_gt(-q, .035, .085)
    radial_costae = _band(q, 0.0, .065, .025)
    areola_pores = _soft_gt(q2, .43, .055)
    pore_rims = _f(_edge(areola_pores, 1))
    rimoportula = _f(radial_costae * _soft_gt(np.cos(TAU * (31 * U - 29 * V)), .76, .08))
    fault_raphe = _phase_band(TAU * (7.0 * U + 3.0 * V)
                              + 1.4 * np.sin(TAU * 2.0 * V), 0.0, .12)
    central_nodules = _f(silica_a * _soft_gt(q2 - q, .38, .06))
    broken_sectors = _f(silica_b * _soft_gt(np.sin(TAU * (5 * U + 11 * V)), .73, .09))
    marginal_spines = _f(radial_costae * _soft_gt(np.cos(TAU * (37 * U + 41 * V)), .78, .075))
    masks = dict(ascending_silica_planes=silica_a,
                 descending_silica_planes=silica_b,
                 twelvefold_radial_costae=radial_costae,
                 logarithmic_areola_pores=areola_pores, pore_bevel_rims=pore_rims,
                 rimoportula_ports=rimoportula, eccentric_raphe_fault=fault_raphe,
                 silica_nodules=central_nodules, broken_valve_sectors=broken_sectors,
                 marginal_microspines=marginal_spines)
    banks = dict(ascending_silica_planes="A", descending_silica_planes="B",
                 twelvefold_radial_costae="A", logarithmic_areola_pores="B",
                 pore_bevel_rims="B", rimoportula_ports="A",
                 eccentric_raphe_fault="N", silica_nodules="A",
                 broken_valve_sectors="N", marginal_microspines="B")
    spec = _literal_spec(
        masks,
        (("ascending_silica_planes", 216), ("descending_silica_planes", 28),
         ("twelvefold_radial_costae", 246), ("silica_nodules", 156),
         ("broken_valve_sectors", 84)),
        (("ascending_silica_planes", 70), ("descending_silica_planes", 186),
         ("logarithmic_areola_pores", 232), ("broken_valve_sectors", 36),
         ("rimoportula_ports", 126)),
        (("ascending_silica_planes", 20), ("descending_silica_planes", 224),
         ("pore_bevel_rims", 246), ("marginal_microspines", 166),
         ("eccentric_raphe_fault", 104)),
    )
    return _finish(masks, banks, _n(q) + .32 * pore_rims, spec)


# ---------------------------------------------------------------------------
# 14. Hierarchical radiolarian pores: tangent-circle generations and struts.


def p4_magenta_radiolaria() -> Grammar:
    shells_a = np.zeros((S, S), np.float32)
    shells_b = np.zeros_like(shells_a)
    pores = np.zeros_like(shells_a)
    struts = np.zeros_like(shells_a)
    collars = np.zeros_like(shells_a)
    spines = np.zeros_like(shells_a)
    sockets = np.zeros_like(shells_a)
    inner_rings = np.zeros_like(shells_a)
    fractured = np.zeros_like(shells_a)
    queue = [(np.asarray((-18.0, 96.0)), 54.0, 0),
             (np.asarray((168.0, -14.0)), 48.0, 0),
             (np.asarray((420.0, 28.0)), 62.0, 0),
             (np.asarray((536.0, 274.0)), 56.0, 0),
             (np.asarray((324.0, 528.0)), 60.0, 0),
             (np.asarray((72.0, 486.0)), 51.0, 0)]
    while queue:
        centre, radius, depth = queue.pop(0)
        target = shells_a if depth % 2 == 0 else shells_b
        _circle(target, centre, radius, 3)
        _circle(inner_rings, centre, radius * .63, 2)
        child_count = 5 + depth
        for j in range(child_count):
            a = TAU * (j / child_count) + depth * .37 + radius * .013
            p = centre + radius * .72 * np.asarray((np.cos(a), np.sin(a)))
            pr = max(2.2, radius * (.16 if j % 2 else .20))
            _circle(pores, p, pr, 2)
            _line(struts, centre + radius * .22 * np.asarray((np.cos(a), np.sin(a))),
                  p - pr * np.asarray((np.cos(a), np.sin(a))), 2)
            if j % 2 == depth % 2:
                _circle(collars, p, pr + 2.4, 2)
            if (j + depth) % 3 == 0:
                tip = centre + radius * 1.16 * np.asarray((np.cos(a), np.sin(a)))
                _line(spines, p + pr * np.asarray((np.cos(a), np.sin(a))), tip, 2)
                _circle(sockets, p, 2, -1)
            if depth < 2 and (j + depth) % 2 == 0:
                child = centre + radius * .93 * np.asarray((np.cos(a), np.sin(a)))
                queue.append((child, radius * .43, depth + 1))
        if depth == 1:
            _ellipse(fractured, centre + (.19 * radius, -.11 * radius),
                     (.48 * radius, .23 * radius), depth * 37, 2, start=22, end=258)
    shell_void = _f(1.0 - _dilate(np.maximum(shells_a, shells_b), 4))
    masks = dict(primary_shell_generations=shells_a,
                 conjugate_shell_generations=shells_b,
                 polygonal_pore_openings=pores, load_bearing_struts=struts,
                 aperture_bevel_collars=collars, radial_spines=spines,
                 spine_root_sockets=sockets, nested_inner_shell_rings=inner_rings,
                 fractured_shell_arcs=fractured, culture_void=shell_void)
    banks = dict(primary_shell_generations="A", conjugate_shell_generations="B",
                 polygonal_pore_openings="B", load_bearing_struts="A",
                 aperture_bevel_collars="B", radial_spines="B",
                 spine_root_sockets="A", nested_inner_shell_rings="A",
                 fractured_shell_arcs="N", culture_void="N")
    spec = _literal_spec(
        masks,
        (("primary_shell_generations", 222), ("conjugate_shell_generations", 34),
         ("load_bearing_struts", 246), ("spine_root_sockets", 154),
         ("fractured_shell_arcs", 84)),
        (("culture_void", 238), ("primary_shell_generations", 76),
         ("polygonal_pore_openings", 34), ("fractured_shell_arcs", 198),
         ("radial_spines", 122)),
        (("culture_void", 16), ("conjugate_shell_generations", 224),
         ("aperture_bevel_collars", 246), ("radial_spines", 166),
         ("nested_inner_shell_rings", 102)),
    )
    return _finish(masks, banks, _halo(np.maximum(shells_a, shells_b), 3.2)
                   + .31 * pores, spec)


# ---------------------------------------------------------------------------
# 15. Cyclic excitable chemistry: deterministic spiral states and collisions.


def p4_cyan_mold() -> Grammar:
    states = 13
    phase0 = _n(np.sin(TAU * (4 * U + 7 * V))
                + np.sin(TAU * (-9 * U + 3 * V))
                + .7 * np.cos(TAU * (11 * U - 8 * V)))
    grid = np.floor(phase0 * states).astype(np.int16) % states
    for _ in range(62):
        nxt = (grid + 1) % states
        count = ((np.roll(grid, 1, 0) == nxt).astype(np.int16)
                 + (np.roll(grid, -1, 0) == nxt)
                 + (np.roll(grid, 1, 1) == nxt)
                 + (np.roll(grid, -1, 1) == nxt))
        grid = np.where(count >= 2, nxt, grid)
    phase = grid.astype(np.float32) * (TAU / states)
    activator = _soft_gt(np.cos(phase), .05, .16)
    inhibitor = _soft_gt(-np.cos(phase), .05, .16)
    excitation_fronts = _band(np.cos(phase), 0.0, .12, .05)
    refractory_backs = _band(np.sin(phase), -.62, .10, .045)
    spiral_cores = _f(excitation_fronts
                      * _soft_gt(np.cos(TAU * (17 * U - 23 * V)), .58, .13))
    collision_seams = _soft_gt(cv2.boxFilter(excitation_fronts, cv2.CV_32F,
                                             (7, 7), normalize=False), 18.0, 3.0)
    wavelet_buds = _f(refractory_backs * _soft_gt(np.sin(TAU * (23 * U - 19 * V)), .71, .09))
    catalyst_islands = _f(activator * _soft_gt(np.cos(TAU * (17 * U + 29 * V)), .76, .08))
    extinct_pockets = _f(inhibitor * _soft_gt(np.sin(TAU * (31 * U + 11 * V)), .74, .09))
    masks = dict(activator_chemical_phase=activator, inhibitor_chemical_phase=inhibitor,
                 excitation_wavefronts=excitation_fronts,
                 refractory_wave_backs=refractory_backs,
                 rotating_spiral_cores=spiral_cores,
                 wave_collision_seams=collision_seams,
                 daughter_wavelets=wavelet_buds, catalyst_islands=catalyst_islands,
                 extinguished_reaction_pockets=extinct_pockets)
    banks = dict(activator_chemical_phase="A", inhibitor_chemical_phase="B",
                 excitation_wavefronts="A", refractory_wave_backs="B",
                 rotating_spiral_cores="B", wave_collision_seams="N",
                 daughter_wavelets="A", catalyst_islands="B",
                 extinguished_reaction_pockets="N")
    spec = _literal_spec(
        masks,
        (("activator_chemical_phase", 210), ("inhibitor_chemical_phase", 26),
         ("excitation_wavefronts", 246), ("daughter_wavelets", 154),
         ("extinguished_reaction_pockets", 82)),
        (("activator_chemical_phase", 72), ("inhibitor_chemical_phase", 190),
         ("refractory_wave_backs", 232), ("catalyst_islands", 36),
         ("wave_collision_seams", 128)),
        (("activator_chemical_phase", 18), ("inhibitor_chemical_phase", 224),
         ("rotating_spiral_cores", 246), ("catalyst_islands", 166),
         ("daughter_wavelets", 104)),
    )
    return _finish(masks, banks, _n(phase) + .29 * excitation_fronts, spec)


# ---------------------------------------------------------------------------
# 16. Potential-flow plankton: organisms occupy wakes, not random positions.


def p4_amber_plankton() -> Grammar:
    z = (X + 1j * Y).astype(np.complex64)
    potential = z.astype(np.complex64)
    obstacles = [(82 + 74j, 19.0), (238 + 122j, 25.0), (414 + 68j, 17.0),
                 (128 + 286j, 22.0), (338 + 258j, 27.0), (472 + 350j, 20.0),
                 (246 + 442j, 18.0), (42 + 456j, 15.0)]
    body = np.zeros((S, S), np.float32)
    collars = np.zeros_like(body)
    for i, (centre, radius) in enumerate(obstacles):
        dz = z - centre + 1.0e-3
        potential += (radius ** 2) / dz * np.exp(1j * (i * .19 - .42))
        cxy = (float(np.real(centre)), float(np.imag(centre)))
        _ellipse(body, cxy, (radius * .52, radius * .28), i * 29 - 18, -1)
        _ellipse(collars, cxy, (radius * .68, radius * .39), i * 29 - 18, 2)
    stream = np.imag(potential) / 34.0
    pressure = _n(np.real(potential))
    fast_water = _soft_gt(np.sin(stream), .03, .17)
    slow_water = _soft_gt(-np.sin(stream), .03, .17)
    streamlines = _band(np.sin(stream), 0.0, .11, .045)
    wake_sheets = _f(slow_water * _phase_band(stream * 2.7 - pressure * 8.0, 0.0, .14))
    flagella = _f(streamlines * _soft_gt(np.sin(TAU * (27 * U + 13 * V)), .63, .12))
    feeding_combs = _f(collars * _soft_gt(np.cos(TAU * (19 * U - 23 * V)), .56, .14))
    vortex_eggs = _f(wake_sheets * _soft_gt(np.cos(TAU * (31 * U + 29 * V)), .72, .09))
    stagnation_pits = _f(collars
                         * _soft_gt(np.cos(TAU * (7 * U + 5 * V)), .48, .15))
    masks = dict(fast_current_domain=fast_water, lee_current_domain=slow_water,
                 potential_streamlines=streamlines, plankton_cell_bodies=body,
                 pressure_sensing_collars=collars, advected_wake_sheets=wake_sheets,
                 locomotion_flagella=flagella, feeding_cilia_combs=feeding_combs,
                 vortex_trapped_eggs=vortex_eggs,
                 stagnation_vacuole_pits=stagnation_pits)
    banks = dict(fast_current_domain="A", lee_current_domain="B",
                 potential_streamlines="A", plankton_cell_bodies="B",
                 pressure_sensing_collars="B", advected_wake_sheets="A",
                 locomotion_flagella="B", feeding_cilia_combs="A",
                 vortex_trapped_eggs="B", stagnation_vacuole_pits="N")
    spec = _literal_spec(
        masks,
        (("fast_current_domain", 206), ("lee_current_domain", 26),
         ("potential_streamlines", 246), ("feeding_cilia_combs", 156),
         ("stagnation_vacuole_pits", 82)),
        (("fast_current_domain", 70), ("lee_current_domain", 190),
         ("plankton_cell_bodies", 42), ("advected_wake_sheets", 226),
         ("stagnation_vacuole_pits", 132)),
        (("fast_current_domain", 18), ("lee_current_domain", 224),
         ("pressure_sensing_collars", 246), ("locomotion_flagella", 164),
         ("vortex_trapped_eggs", 102)),
    )
    return _finish(masks, banks, _n(stream) + .28 * collars, spec)


# ---------------------------------------------------------------------------
# 17. Cubic membrane: gyroid saddle channels and embedded transmembrane parts.


def p4_violet_membrane() -> Grammar:
    x = TAU * (4.7 * U + .18 * np.sin(TAU * 2.0 * V))
    y = TAU * (4.3 * V + .16 * np.sin(TAU * 3.0 * U))
    z = TAU * (.62 * U - .47 * V + .21 * np.sin(TAU * (U + V)))
    gyroid = (np.sin(x) * np.cos(y) + np.sin(y) * np.cos(z)
              + np.sin(z) * np.cos(x))
    channel_a = _soft_gt(gyroid, .12, .20)
    channel_b = _soft_gt(-gyroid, .12, .20)
    saddle_membrane = _band(gyroid, 0.0, .15, .07)
    positive_necks = _band(gyroid, .42, .10, .05)
    negative_necks = _band(gyroid, -.42, .10, .05)
    transmembrane_rods = _f(saddle_membrane
                           * _soft_gt(np.cos(TAU * (23 * U + 17 * V)), .71, .10))
    pore_collars = _f(positive_necks
                      * _soft_gt(np.sin(TAU * (19 * U - 29 * V)), .66, .11))
    cleavage_domains = _phase_band(5.0 * x - 3.0 * y + 2.0 * z, 0.0, .14)
    vesicle_buds = _f(negative_necks
                      * _soft_gt(np.cos(TAU * (31 * U + 7 * V)), .73, .09))
    drainage_rills = _f(saddle_membrane
                        * _phase_band(3.0 * x + 4.0 * y - z, 0.0, .11))
    masks = dict(positive_labyrinth_channel=channel_a,
                 negative_labyrinth_channel=channel_b,
                 minimal_saddle_membrane=saddle_membrane,
                 positive_channel_necks=positive_necks,
                 negative_channel_necks=negative_necks,
                 transmembrane_protein_rods=transmembrane_rods,
                 pore_bevel_collars=pore_collars,
                 cleavage_phase_domains=cleavage_domains,
                 vesicle_buds=vesicle_buds, drainage_micro_rills=drainage_rills)
    banks = dict(positive_labyrinth_channel="A", negative_labyrinth_channel="B",
                 minimal_saddle_membrane="N", positive_channel_necks="A",
                 negative_channel_necks="B", transmembrane_protein_rods="A",
                 pore_bevel_collars="B", cleavage_phase_domains="B",
                 vesicle_buds="A", drainage_micro_rills="N")
    spec = _literal_spec(
        masks,
        (("positive_labyrinth_channel", 214), ("negative_labyrinth_channel", 28),
         ("positive_channel_necks", 246), ("transmembrane_protein_rods", 154),
         ("drainage_micro_rills", 82)),
        (("positive_labyrinth_channel", 72), ("negative_labyrinth_channel", 188),
         ("minimal_saddle_membrane", 228), ("vesicle_buds", 36),
         ("drainage_micro_rills", 132)),
        (("positive_labyrinth_channel", 18), ("negative_labyrinth_channel", 224),
         ("negative_channel_necks", 246), ("pore_bevel_collars", 166),
         ("cleavage_phase_domains", 104)),
    )
    return _finish(masks, banks, _n(gyroid) + .28 * saddle_membrane, spec)


# ---------------------------------------------------------------------------
# 18. Rule-110 ancestry: a causal spacetime fabric, not a chain stamp.


def p4_lime_chains() -> Grammar:
    rule = 110
    table = np.asarray([(rule >> k) & 1 for k in range(8)], np.uint8)
    cellular_res = 192
    rows = np.zeros((cellular_res, cellular_res), np.uint8)
    x = np.arange(cellular_res, dtype=np.float32)
    rows[0] = ((np.sin(x * .173) + np.sin(x * .071 + .8)
                + .55 * np.cos(x * .291)) > .14).astype(np.uint8)
    cur = rows[0].copy()
    births = np.zeros((cellular_res, cellular_res), np.uint8)
    for y in range(1, cellular_res):
        left, right = np.roll(cur, 1), np.roll(cur, -1)
        nxt = table[(left << 2) | (cur << 1) | right]
        births[y] = (nxt > cur).astype(np.uint8)
        rows[y] = nxt
        cur = nxt
    live = cv2.resize(rows.astype(np.float32), (S, S), interpolation=cv2.INTER_NEAREST)
    births = cv2.resize(births.astype(np.float32), (S, S), interpolation=cv2.INTER_NEAREST)
    void = 1.0 - live
    lineage_edges = _edge(live, 1)
    birth_fronts = births
    diagonal_gliders = _f(live * _soft_gt(np.sin(TAU * (U * 37 - V * 19)), .72, .09))
    ancestor_columns = _f(live * _soft_gt(np.cos(TAU * (U * 23 + V * 3)), .74, .09))
    branch_nodes = _f(birth_fronts
                      * _soft_gt(np.cos(TAU * (29 * U + 11 * V)), .64, .11))
    extinction_scars = _f(void * _soft_gt(np.sin(TAU * (U * 17 + V * 31)), .73, .09))
    crossover_cells = _f(birth_fronts * _soft_gt(np.cos(TAU * (U * 29 - V * 37)), .67, .11))
    refractory_shadow = _f(_dilate(live, 2) - live)
    masks = dict(live_lineage_cells=live, extinct_spacetime_cells=void,
                 lineage_boundary_edges=lineage_edges, causal_birth_fronts=birth_fronts,
                 diagonal_glider_packets=diagonal_gliders,
                 persistent_ancestor_columns=ancestor_columns,
                 branching_computation_nodes=branch_nodes,
                 extinction_scars=extinction_scars,
                 crossover_birth_cells=crossover_cells,
                 refractory_lineage_shadow=refractory_shadow)
    banks = dict(live_lineage_cells="A", extinct_spacetime_cells="B",
                 lineage_boundary_edges="A", causal_birth_fronts="B",
                 diagonal_glider_packets="B", persistent_ancestor_columns="A",
                 branching_computation_nodes="B", extinction_scars="N",
                 crossover_birth_cells="A", refractory_lineage_shadow="N")
    spec = _literal_spec(
        masks,
        (("live_lineage_cells", 212), ("extinct_spacetime_cells", 26),
         ("persistent_ancestor_columns", 246), ("crossover_birth_cells", 154),
         ("extinction_scars", 82)),
        (("live_lineage_cells", 70), ("extinct_spacetime_cells", 190),
         ("refractory_lineage_shadow", 232), ("diagonal_glider_packets", 36),
         ("branching_computation_nodes", 128)),
        (("live_lineage_cells", 18), ("extinct_spacetime_cells", 224),
         ("causal_birth_fronts", 246), ("diagonal_glider_packets", 166),
         ("lineage_boundary_edges", 104)),
    )
    return _finish(masks, banks, live + .29 * birth_fronts, spec)


# ---------------------------------------------------------------------------
# 19. Confocal silica frustule: elliptic coordinates, chirped ribs and defects.


def p4_violet_frustule() -> Grammar:
    f1 = np.asarray((-96.0, 122.0), np.float32)
    f2 = np.asarray((602.0, 394.0), np.float32)
    d1 = np.hypot(X - f1[0], Y - f1[1])
    d2 = np.hypot(X - f2[0], Y - f2[1])
    elliptic = (d1 + d2) / 24.0
    hyperbolic = (d1 - d2) / 19.0
    valve_a = _soft_gt(np.cos(elliptic + .31 * np.sin(hyperbolic)), .04, .16)
    valve_b = _soft_gt(-np.cos(elliptic + .31 * np.sin(hyperbolic)), .04, .16)
    growth_costae = _band(np.cos(elliptic), 0.0, .11, .045)
    raphe_slit = _band(np.sin(hyperbolic * .53 + .4 * np.sin(elliptic)), 0.0, .095, .04)
    areola_rows = _f(valve_a * _phase_band(2.7 * elliptic - 3.9 * hyperbolic, 0.0, .13))
    central_nodules = _f(growth_costae * raphe_slit)
    terminal_pores = _f(raphe_slit * _soft_gt(np.cos(TAU * (31 * U + 17 * V)), .72, .09))
    silica_faults = _phase_band(.83 * elliptic + 5.2 * hyperbolic, 0.0, .11)
    chipped_costae = _f(growth_costae * _soft_gt(np.sin(TAU * (19 * U - 23 * V)), .69, .10))
    girdle_bands = _band(np.cos(elliptic * .47 - hyperbolic * .21), 0.0, .09, .04)
    masks = dict(outer_valve_lamellae=valve_a, inner_valve_lamellae=valve_b,
                 confocal_growth_costae=growth_costae,
                 eccentric_raphe_slit=raphe_slit,
                 ordered_areola_rows=areola_rows, central_silica_nodules=central_nodules,
                 terminal_raphe_pores=terminal_pores,
                 conjugate_silica_faults=silica_faults,
                 chipped_costa_segments=chipped_costae,
                 girdle_band_overlaps=girdle_bands)
    banks = dict(outer_valve_lamellae="A", inner_valve_lamellae="B",
                 confocal_growth_costae="A", eccentric_raphe_slit="B",
                 ordered_areola_rows="B", central_silica_nodules="A",
                 terminal_raphe_pores="B", conjugate_silica_faults="N",
                 chipped_costa_segments="N", girdle_band_overlaps="A")
    spec = _literal_spec(
        masks,
        (("outer_valve_lamellae", 216), ("inner_valve_lamellae", 28),
         ("confocal_growth_costae", 246), ("central_silica_nodules", 154),
         ("chipped_costa_segments", 82)),
        (("outer_valve_lamellae", 70), ("inner_valve_lamellae", 188),
         ("ordered_areola_rows", 36), ("conjugate_silica_faults", 232),
         ("terminal_raphe_pores", 128)),
        (("outer_valve_lamellae", 18), ("inner_valve_lamellae", 224),
         ("eccentric_raphe_slit", 246), ("girdle_band_overlaps", 166),
         ("terminal_raphe_pores", 104)),
    )
    return _finish(masks, banks, _n(elliptic - .37 * hyperbolic)
                   + .29 * raphe_slit, spec)


# ---------------------------------------------------------------------------
# 20. Metachronal plankton phase: coupled cilia waves and topological defects.


def p4_magenta_plankton() -> Grammar:
    # A deterministic phase-oscillator sheet; vortices are zeros of the two
    # coupled waves, not random specks added for a uniqueness score.
    pa = (TAU * (8.0 * U + 3.0 * V)
          + 1.31 * np.sin(TAU * (2.0 * U - 1.3 * V))
          + .62 * np.sin(TAU * (5.0 * V)))
    pb = (TAU * (-3.0 * U + 9.0 * V)
          + 1.07 * np.cos(TAU * (1.7 * U + 2.2 * V))
          + .55 * np.sin(TAU * (4.0 * U)))
    order = np.cos(pa) + np.sin(pb)
    phase_a = _soft_gt(order, .08, .20)
    phase_b = _soft_gt(-order, .08, .20)
    metachronal_fronts = _band(order, 0.0, .15, .065)
    cilia_combs = _f(phase_a * _phase_band(pa * 1.7 - pb * .6, 0.0, .13))
    oral_grooves = _phase_band(pa + pb * .44, 0.0, .11)
    contractile_spokes = _f(phase_b * _phase_band(pa * .52 - pb * 1.9, 0.0, .12))
    vortex_defects = _f(_band(np.cos(pa), 0.0, .10, .04)
                        * _band(np.sin(pb), 0.0, .10, .04))
    feeding_vacuoles = _f(phase_a * _soft_gt(np.cos(pa - pb), .72, .09))
    daughter_wave_buds = _f(metachronal_fronts
                            * _soft_gt(np.sin(TAU * (29 * U + 31 * V)), .68, .10))
    stalled_cilia_pockets = _f(phase_b
                               * _soft_gt(np.cos(TAU * (17 * U - 23 * V)), .73, .09))
    masks = dict(leading_cilia_phase=phase_a, lagging_cilia_phase=phase_b,
                 metachronal_wavefronts=metachronal_fronts,
                 locomotor_cilia_combs=cilia_combs, oral_feeding_grooves=oral_grooves,
                 contractile_vacuole_spokes=contractile_spokes,
                 topological_vortex_defects=vortex_defects,
                 feeding_vacuoles=feeding_vacuoles,
                 daughter_wave_buds=daughter_wave_buds,
                 stalled_cilia_pockets=stalled_cilia_pockets)
    banks = dict(leading_cilia_phase="A", lagging_cilia_phase="B",
                 metachronal_wavefronts="A", locomotor_cilia_combs="B",
                 oral_feeding_grooves="B", contractile_vacuole_spokes="A",
                 topological_vortex_defects="N", feeding_vacuoles="B",
                 daughter_wave_buds="A", stalled_cilia_pockets="N")
    spec = _literal_spec(
        masks,
        (("leading_cilia_phase", 212), ("lagging_cilia_phase", 26),
         ("metachronal_wavefronts", 246), ("contractile_vacuole_spokes", 154),
         ("stalled_cilia_pockets", 82)),
        (("leading_cilia_phase", 70), ("lagging_cilia_phase", 190),
         ("oral_feeding_grooves", 232), ("feeding_vacuoles", 36),
         ("topological_vortex_defects", 128)),
        (("leading_cilia_phase", 18), ("lagging_cilia_phase", 224),
         ("locomotor_cilia_combs", 246), ("daughter_wave_buds", 166),
         ("feeding_vacuoles", 104)),
    )
    return _finish(masks, banks, _n(pa - .67 * pb) + .29 * metachronal_fronts, spec)


BUILDERS: Mapping[str, Callable[[], Grammar]] = {
    "fpe_magenta_bloom": p4_magenta_bloom,
    "fpe_cyan_membrane": p4_cyan_membrane,
    "fpe_lime_culture": p4_lime_culture,
    "fpe_amber_agar": p4_amber_agar,
    "fpe_violet_garden": p4_violet_garden,
    "fpe_lime_diatom": p4_lime_diatom,
    "fpe_magenta_mosaic": p4_magenta_mosaic,
    "fpe_cyan_spineball": p4_cyan_spineball,
    "fpe_amber_moldring": p4_amber_moldring,
    "fpe_violet_chains": p4_violet_chains,
    "fpe_cyan_colony": p4_cyan_colony,
    "fpe_lime_mold": p4_lime_mold,
    "fpe_amber_diatom": p4_amber_diatom,
    "fpe_magenta_radiolaria": p4_magenta_radiolaria,
    "fpe_cyan_mold": p4_cyan_mold,
    "fpe_amber_plankton": p4_amber_plankton,
    "fpe_violet_membrane": p4_violet_membrane,
    "fpe_lime_chains": p4_lime_chains,
    "fpe_violet_frustule": p4_violet_frustule,
    "fpe_magenta_plankton": p4_magenta_plankton,
}


HUES: Mapping[str, Tuple[float, float]] = {
    "fpe_magenta_bloom": (.88, .42), "fpe_cyan_membrane": (.50, .91),
    "fpe_lime_culture": (.27, .77), "fpe_amber_agar": (.09, .55),
    "fpe_violet_garden": (.76, .34), "fpe_lime_diatom": (.25, .79),
    "fpe_magenta_mosaic": (.89, .44), "fpe_cyan_spineball": (.52, .97),
    "fpe_amber_moldring": (.10, .56), "fpe_violet_chains": (.77, .30),
    "fpe_cyan_colony": (.51, .91), "fpe_lime_mold": (.28, .82),
    "fpe_amber_diatom": (.08, .55), "fpe_magenta_radiolaria": (.87, .47),
    "fpe_cyan_mold": (.50, .94), "fpe_amber_plankton": (.09, .51),
    "fpe_violet_membrane": (.78, .37), "fpe_lime_chains": (.27, .80),
    "fpe_violet_frustule": (.75, .31), "fpe_magenta_plankton": (.90, .46),
}

PETRI_IDS: Tuple[str, ...] = tuple(BUILDERS)
if len(BUILDERS) != 20 or len({fn.__name__ for fn in BUILDERS.values()}) != 20:
    raise AssertionError("WR-P4 must own twenty distinct topology constructors")


def _hsv(hue, sat, value):
    px = np.uint8([[[int((float(hue) % 1.0) * 179.0),
                     int(np.clip(sat, 0, 1) * 255), int(np.clip(value, 0, 1) * 255)]]])
    return cv2.cvtColor(px, cv2.COLOR_HSV2RGB)[0, 0].astype(np.float32) / 255.0


def _palettes(hues: Sequence[float]):
    offsets = (-.074, -.049, -.027, -.009, .014, .038, .067, .101)
    values = (.18, .27, .37, .48, .60, .72, .84, .97)
    a = np.stack([_hsv(hues[0] + offsets[i], .91 - .035 * (i % 4), values[i])
                  for i in range(8)])
    b = np.stack([_hsv(hues[1] - offsets[7 - i], .88 - .03 * ((i + 2) % 5), values[i])
                  for i in range(8)])
    neutral = np.stack((_hsv((hues[0] + hues[1]) * .5, .16, .10),
                        _hsv((hues[0] + hues[1]) * .5 + .5, .24, .44)))
    return a.astype(np.float32), b.astype(np.float32), neutral.astype(np.float32)


def _compose(grammar: Grammar, hues: Sequence[float]):
    bank_a, bank_b, neutral = _palettes(hues)
    paint = np.broadcast_to(neutral[0], (S, S, 3)).copy()
    tone = _n(grammar.tone)
    for index, (_name, mask, owner) in enumerate(grammar.marks):
        if owner == "A":
            levels = np.digitize(np.mod(tone + index * .137, 1.0),
                                 (.11, .23, .36, .49, .62, .75, .88))
            color = bank_a[levels]
        elif owner == "B":
            levels = np.digitize(np.mod(1.0 - tone + index * .173, 1.0),
                                 (.11, .23, .36, .49, .62, .75, .88))
            color = bank_b[levels]
        else:
            color = np.broadcast_to(neutral[(index + 1) & 1], paint.shape)
        alpha = np.clip(mask * (.66 + .045 * (index % 6)), 0.0, .96)[..., None]
        paint = paint * (1.0 - alpha) + color * alpha
    spec = np.stack(grammar.explicit_spec, axis=2)
    return np.clip(paint, 0, 1).astype(np.float32), np.clip(spec, 0, 255).astype(np.uint8)


@lru_cache(maxsize=20)
def _authored(fid: str):
    return _compose(BUILDERS[fid](), HUES[fid])


def clear_cache():
    _authored.cache_clear()


def debug_grammar(fid: str) -> Grammar:
    return BUILDERS[fid]()


def owner_unions(grammar: Grammar):
    out = {key: np.zeros((S, S), np.float32) for key in ("A", "B", "N")}
    for _name, mask, owner in grammar.marks:
        out[owner] = np.maximum(out[owner], mask)
    return out


def debug_hue_null(fid: str):
    grammar = debug_grammar(fid)
    out = np.full((S, S), .06, np.float32)
    levels = (.18, .32, .47, .61, .74, .86, .96, .55, .27, .68)
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
